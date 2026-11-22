"""Analiza formularza modelem językowym (Eden AI, format OpenAI Chat Completions).

Model zwraca wyłącznie część specyficzną dla wniosku (przedmiot wniosku, oświadczenia, opłaty,
kto może złożyć wniosek). Sekcje predefiniowane ze „Standardów” dokłada deterministyczny generator,
więc wynik jest zgodny ze standardem niezależnie od „kreatywności” modelu. Odpowiedź jest walidowana
schematem Pydantic; przy błędzie model dostaje komunikat i jedną szansę na poprawkę.
"""

import json
import re
from typing import Literal

from pydantic import BaseModel, Field, ValidationError, field_validator

from app.ai.edenai import AIError, EdenAIClient
from app.analysis.model import (
    Applicant,
    Condition,
    FieldSpec,
    FormAnalysis,
    Kind,
    PageSpec,
    ProposedDictionary,
    SectionSpec,
)
from app.extraction.model import ExtractedDocument

VALIDATORS = ("REQUIRED", "EMAIL", "PESEL", "NIP", "REGON", "ZIP_CODE", "EPUAP", "ADE", "SERIAL_NUMBER_ID_CARD")
# Tylko słowniki faktycznie występujące w eksportach referencyjnych — reszta trafia do propozycji nowych słowników.
DICTIONARIES = ("Kraje", "TERYT_DOWODOWY", "TERYT_4G_DOWODOWY")
INITIAL_DATA = {
    "PESEL": ["pesel", "name", "surname", "birthDate", "citizenship", "motherName", "birthPlace", "motherSurname",
              "sex", "fatherName", "secondName", "birthCountry", "foreignBirthUSC", "familyName", "fatherSurname",
              "maritalStatus"],
    "PESEL_ADDRESS": [f"{kind}Address{part}" for kind in ("temporary", "permanent")
                      for part in ("Voivodeship", "District", "Community", "Place", "StreetType", "Street",
                                   "HouseNumber", "ApartmentNumber", "PostalCode")],
    "MLPZ": ["name", "secondName", "surname", "pesel", "phoneNumber", "email", "country", "voivodeship", "district",
             "community", "place", "postCode", "street", "building", "apartment", "institutionName",
             "descriptiveOrganizationName"],
}
_INITIAL_DATA_VALUES = {f"{src}.{attr}" for src, attrs in INITIAL_DATA.items() for attr in attrs}

# ---------------------------------------------------------------- schemat odpowiedzi modelu


class _Cond(BaseModel):
    field: str = Field(description="Etykieta pola sterującego (dokładnie jak w 'label').")
    value: str = Field(description="Opcja, której wybranie pokazuje element.")


class _Field(BaseModel):
    label: str
    kind: Literal["TEXT_FIELD", "TEXTAREA", "NUMBER", "DATEPICKER", "RADIO", "CHECKBOX", "SELECT",
                  "FILE_UPLOADER", "TEXT_BLOCK"]
    options: list[str] = []
    required: bool = True
    validators: list[str] = []
    dictionary: str | None = None
    initial_data: str | None = None
    description: str | None = None
    show_if: _Cond | None = None

    @field_validator("validators")
    @classmethod
    def _known_validators(cls, v: list[str]) -> list[str]:
        return [x for x in v if x in VALIDATORS and x != "REQUIRED"]

    @field_validator("initial_data")
    @classmethod
    def _known_initial(cls, v: str | None) -> str | None:
        return v if v in _INITIAL_DATA_VALUES else None


class _Section(BaseModel):
    title: str
    description: str | None = None
    show_if: _Cond | None = None
    fields: list[_Field]


class _Page(BaseModel):
    title: str
    sections: list[_Section]


class _Dictionary(BaseModel):
    name: str
    description: str
    values: list[str]
    used_by: list[str] = []


class _Answer(BaseModel):
    @field_validator("pages", "statements", "fee_info", "proposed_dictionaries", mode="before")
    @classmethod
    def _null_as_empty(cls, v: object) -> object:
        return [] if v is None else v  # część modeli zwraca null zamiast pustej listy

    title: str
    authority: str | None = None
    authority_is_organ: bool = False
    applicant_person: bool = True
    applicant_company: bool = False
    pages: list[_Page]
    statements: list[str] = []
    fee_info: list[str] = []
    proposed_dictionaries: list[_Dictionary] = []


# ---------------------------------------------------------------- prompt

SYSTEM_PROMPT = f"""Jesteś ekspertem Centralnego Ośrodka Informatyki od cyfryzacji formularzy urzędowych.
Dostajesz tekst papierowego formularza (wyciągnięty z PDF/DOC/arkusza albo z OCR skanu).
Projektujesz jego elektroniczną wersję (eUsługę) zgodnie ze „Standardami i dobrymi praktykami projektowania formularzy”.

PODZIAŁ PRACY — to bardzo ważne:
System SAM dodaje sekcje predefiniowane: urząd/organ adresat, „Podmiot wniosku” (swoim / innej osoby / osoby prawnej),
„Twoje dane” (imię, nazwisko, PESEL wnioskodawcy), adres zamieszkania wnioskodawcy, dane i adres innej osoby, dane i adres
siedziby podmiotu (nazwa, NIP, REGON, KRS), pełnomocnictwo, opłatę skarbową ZA PEŁNOMOCNICTWO, dane do kontaktu (telefon,
e-mail wnioskodawcy), zgodę RODO oraz stronę z podglądem.
NIE powielaj tych danych. Pomiń też: miejsce na podpis, miejscowość i datę wypełnienia, klauzulę informacyjną RODO,
nagłówki „Załącznik nr … do uchwały”, pouczenia o przepisach.

TWOJE ZADANIE — zwróć tylko część specyficzną dla tego wniosku:
1. title — tytuł usługi: zaczyna się od „Wniosek”, „Zgłoszenie”, „Deklaracja” lub „Oświadczenie”, krótki, bez odwołań do
   przepisów, zwykła pisownia (nie wersaliki), maks. 255 znaków. Np. „Wniosek o wydanie zaświadczenia”.
2. authority — nazwa urzędu lub organu, do którego składa się wniosek (np. „Wójt Gminy Elbląg”, „Urząd Miasta i Gminy
   Młynary”), null jeśli brak; authority_is_organ = true dla organu (Wójt, Burmistrz, Prezydent, Starosta, Rada…).
3. applicant_person / applicant_company — czy formularz przewiduje dane osoby fizycznej / firmy lub instytucji
   (nazwa firmy, siedziba, NIP, REGON, KRS). Jeśli tylko osoba — person=true, company=false.
4. pages — strony przedmiotu wniosku. Strona = temat (np. „Informacje o budynku”, „Informacje o nadpłacie”,
   „Szczegóły najmu”). Na stronie sekcje tematyczne, w sekcjach pola. Krótki formularz = jedna strona.
   Dane osób trzecich występujących w sprawie (np. osoba odpowiedzialna, wykonawca robót, poprzedni właściciel)
   umieść w osobnej sekcji z polami.
5. statements — treści oświadczeń z formularza („Oświadczam, że…”), w formie neutralnej płciowo i w czasie teraźniejszym
   (np. „zapoznałem/am się” → „Znam warunki…”). Trafią do sekcji zgód.
6. fee_info — informacje o opłacie za samą usługę (kwota, rachunek, termin), jeśli formularz ją przewiduje. Nie opłata za
   pełnomocnictwo.
7. proposed_dictionaries — jeśli pole ma zamknięty zbiór wartości, którego nie ma w słownikach systemowych, zaproponuj
   nowy słownik: name (np. „Rasy psów uznawanych za agresywne”), description, values, used_by (etykiety pól).
   Pole korzystające z takiego słownika: kind SELECT, dictionary = nazwa słownika, options = [].

ZASADY PÓL:
- label: krótka, zrozumiała etykieta prostym językiem, bez form płciowych, bez numeracji i gwiazdek (np. „Miejscowość”,
  „Numer ewidencyjny działki”, „Przewidywana liczba uczestników”). Etykiety unikalne w całym formularzu.
- kind: TEXT_FIELD (krótki tekst), TEXTAREA (opis, uzasadnienie, cel), NUMBER (wyłącznie liczby: kwota, powierzchnia,
  liczba), DATEPICKER (data), RADIO (jedna opcja z maks. 5), CHECKBOX (można zaznaczyć kilka), SELECT (jedna opcja z więcej
  niż 5 lub słownik), FILE_UPLOADER (załącznik — każdy wymagany załącznik jako osobne pole), TEXT_BLOCK (informacja dla
  użytkownika, treść w description, label pusty).
- options: dla RADIO/CHECKBOX/SELECT bez słownika — pełne nazwy opcji z wielkiej litery. „wynajem/użyczenie*”
  (niepotrzebne skreślić) to RADIO z opcjami „Wynajem”, „Użyczenie”.
- required: false dla pól oznaczonych jako „jeżeli dotyczy”, „w przypadku…”, „**” itp.
- validators (oprócz wymagalności): {", ".join(v for v in VALIDATORS if v != "REQUIRED")}.
- dictionary: jeden ze słowników systemowych {", ".join(DICTIONARIES)} albo nazwa zaproponowanego słownika.
- initial_data: jeśli pole dotyczy danych wnioskodawcy dostępnych w rejestrze, podaj źródło, np. „PESEL.birthDate”.
  Dostępne: {", ".join(sorted(_INITIAL_DATA_VALUES))}.
- description: krótka podpowiedź (np. z dopisku pod wykropkowaniem „( rodzaj uroczystości, np. wesele )”), opcjonalna.
- show_if: zależność — pole/sekcja widoczne tylko po wybraniu opcji w innym polu, np. pole „Inne – podaj jakie” z
  show_if {{"field": "<etykieta pola wyboru>", "value": "Inne"}}. Pole sterujące musi występować wcześniej.

ZWIĘZŁOŚĆ: pomijaj klucze o wartościach domyślnych — "options": [], "validators": [], "required": true,
"dictionary" / "initial_data" / "description" / "show_if": null. Duże formularze muszą zmieścić się w odpowiedzi.

Odpowiedz WYŁĄCZNIE obiektem json (JSON, bez komentarzy i bez bloku kodu) o strukturze:
{{"title": str, "authority": str|null, "authority_is_organ": bool, "applicant_person": bool, "applicant_company": bool,
 "pages": [{{"title": str, "sections": [{{"title": str, "description": str|null, "show_if": null|{{"field": str, "value": str}},
   "fields": [{{"label": str, "kind": str, "options": [str], "required": bool, "validators": [str], "dictionary": str|null,
     "initial_data": str|null, "description": str|null, "show_if": null|{{"field": str, "value": str}}}}]}}]}}],
 "statements": [str], "fee_info": [str],
 "proposed_dictionaries": [{{"name": str, "description": str, "values": [str], "used_by": [str]}}]}}"""

EXAMPLE_INPUT = """WNIOSEK O USTALENIE NUMERU PORZĄDKOWEGO
Wnoszę o ustalenie numeru porządkowego budynkowi zlokalizowanemu
w miejscowości……………….……………… przy ulicy1)……………….…………………
nr ewidencyjny działki ……………w obrębie ………………………….……………………
…………………………
(podpis wnioskodawcy))"""

EXAMPLE_OUTPUT = {
    "title": "Wniosek o ustalenie numeru porządkowego nieruchomości", "authority": "Wójt Gminy Elbląg",
    "authority_is_organ": True, "applicant_person": True, "applicant_company": True,
    "pages": [{"title": "Informacje o budynku", "sections": [{"title": "Lokalizacja budynku", "fields": [
        {"label": "Miejscowość", "kind": "TEXT_FIELD"},
        {"label": "Ulica", "kind": "TEXT_FIELD"},
        {"label": "Numer ewidencyjny działki", "kind": "TEXT_FIELD"},
        {"label": "Obręb", "kind": "TEXT_FIELD"}]}]}],
}  # zwięzły styl: klucze o wartościach domyślnych pominięte


def _document_text(document: ExtractedDocument, limit: int) -> str:
    rows = []
    for line in document.lines:
        prefix = "• " if line.list_item else ""
        rows.append(prefix + (" | ".join(line.cells) if line.cells else line.text))
    text = "\n".join(rows)
    return text if len(text) <= limit else text[:limit] + "\n[… tekst skrócony …]"


def analyze_with_llm(document: ExtractedDocument, *, client: EdenAIClient, model: str, max_chars: int,
                     filename: str, fallbacks: list[str] | None = None, max_tokens: int = 32_000) -> FormAnalysis:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Przykładowy formularz (adresat w nagłówku: Wójt Gminy Elbląg):\n{EXAMPLE_INPUT}"},
        {"role": "assistant", "content": json.dumps(EXAMPLE_OUTPUT, ensure_ascii=False)},
        {"role": "user", "content": f"Nazwa pliku: {filename}\n\nTekst formularza:\n"
                                    f"{_document_text(document, max_chars)}"},
    ]
    raw = client.chat(model, messages, fallbacks=fallbacks, max_tokens=max_tokens)
    try:
        answer = _parse(raw)
    except (ValueError, ValidationError) as exc:
        # Ucięta odpowiedź (limit długości) to najczęstsza przyczyna — nie odsyłamy jej, prosimy o zwięźlejszą.
        messages.append({"role": "user", "content": (
            f"Poprzednia odpowiedź była niepoprawna: {str(exc)[:800]}\n"
            "Zwróć kompletny, poprawny obiekt JSON dla tego samego formularza. Pisz zwięźle: pomijaj klucze "
            "o wartościach domyślnych, skracaj opisy, nie powtarzaj danych z sekcji predefiniowanych.")})
        raw = client.chat(model, messages, fallbacks=fallbacks, max_tokens=max_tokens)
        try:
            answer = _parse(raw)
        except (ValueError, ValidationError) as exc2:
            raise AIError(f"Model zwrócił niepoprawny JSON: {str(exc2)[:300]}") from exc2
    analysis = _to_analysis(answer)
    analysis.warnings += document.warnings
    return analysis


def _parse(raw: str) -> _Answer:
    text = raw.strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if fenced:
        text = fenced.group(1)
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < start:
        raise ValueError("Brak obiektu JSON w odpowiedzi.")
    return _Answer.model_validate_json(text[start:end + 1])


def _to_analysis(answer: _Answer) -> FormAnalysis:
    by_label: dict[str, FieldSpec] = {}
    known_dicts = {*DICTIONARIES, *(d.name for d in answer.proposed_dictionaries)}
    pending: list[tuple[FieldSpec | SectionSpec, _Cond]] = []
    pages: list[PageSpec] = []
    for page in answer.pages:
        sections = []
        for sec in page.sections:
            fields = []
            for f in sec.fields:
                kind = Kind(f.kind)
                dictionary = f.dictionary if f.dictionary in known_dicts else None  # zmyślony słownik → zwykłe pole
                options = [] if dictionary else [o.strip() for o in f.options if o.strip()]
                if kind in (Kind.RADIO, Kind.CHECKBOX, Kind.SELECT) and not options and not dictionary:
                    kind = Kind.TEXT  # pole wyboru bez opcji nie przejdzie importu
                spec = FieldSpec(label=f.label.strip()[:200], kind=kind, options=options, required=f.required,
                                 validators=f.validators, dictionary=dictionary, description=f.description,
                                 initial_data=f.initial_data, search=len(options) > 15 or bool(dictionary))
                by_label.setdefault(spec.label.lower(), spec)
                if f.show_if:
                    pending.append((spec, f.show_if))
                fields.append(spec)
            if fields:
                section = SectionSpec(title=sec.title.strip(), fields=fields, description=sec.description)
                if sec.show_if:
                    pending.append((section, sec.show_if))
                sections.append(section)
        if sections:
            pages.append(PageSpec(title=page.title.strip(), sections=sections))

    warnings: list[str] = []
    for target, cond in pending:  # warunki adresują pola po etykiecie — zamieniamy na referencje
        controller = by_label.get(cond.field.strip().lower())
        if controller is None or controller is target:
            warnings.append(f"Pominięto zależność od nieznanego pola „{cond.field}”.")
            continue
        target.show_if = Condition(controller, cond.value)

    return FormAnalysis(
        title=answer.title.strip()[:255],
        authority=answer.authority,
        authority_is_organ=answer.authority_is_organ,
        applicant=Applicant(person=answer.applicant_person or not answer.applicant_company,
                            company=answer.applicant_company),
        pages=pages,
        statements=[s.strip() for s in answer.statements if s.strip()],
        fee_info=[s.strip() for s in answer.fee_info if s.strip()],
        proposed_dictionaries=[ProposedDictionary(d.name, d.description, d.values, d.used_by)
                               for d in answer.proposed_dictionaries],
        warnings=warnings,
        analyzer="llm",
    )
