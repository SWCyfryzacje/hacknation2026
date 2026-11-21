"""Składanie konfiguracji eUsługi: sekcje predefiniowane („Standardy”) + przedmiot wniosku z analizy.

Układ formularza (Standardy, „Ogólne zasady” pkt 11):
  1. „Dane” — adresat, podmiot wniosku, wnioskodawca, pełnomocnik, opłata za pełnomocnictwo,
  2. strony przedmiotu wniosku (z analizy dokumentu),
  3. przedostatnia — opłaty, dane do kontaktu, zgody i oświadczenia,
  4. „Strona końcowa” (FINISH) — wyłącznie podgląd.
"""

from dataclasses import dataclass, field
from itertools import pairwise
from typing import Any

from app.analysis.model import Condition, FieldSpec, FormAnalysis, Kind, SectionSpec
from app.config import FinishComponent, ValidationMode
from app.generator import jsonata as q
from app.generator.fields import IdFactory, html_list, node, placed, to_html

TAB_DATA = "Dane"
TAB_FINISH = "Strona końcowa"
OPT_SELF, OPT_OTHER, OPT_COMPANY = "Swoim", "Innej osoby", "Osoby prawnej lub jednostki organizacyjnej"
OPT_PROXY, OPT_REPRESENTATIVE = "Pełnomocnik", "Reprezentant"
EXTERNAL = "EXTERNAL_SYSTEM"
STAMP_DUTY_TEXT = (
    "Opłata skarbowa za pełnomocnictwo wynosi 17 zł.\n"
    "Przelej ją na konto urzędu miasta lub gminy właściwego dla adresu {who}. "
    "Jeśli adres nie jest w Polsce, opłatę przelej na konto Urzędu Miasta Stołecznego Warszawy "
    "– Centrum Obsługi Podatnika.\n"
    "W tytule przelewu wpisz „{title} – opłata skarbowa za pełnomocnictwo”.\n"
    "Dodaj plik z potwierdzeniem przelewu. Znajdziesz go na stronie lub w aplikacji swojego banku."
)
CONTACT_TEXT = (
    "Wpisanie danych do kontaktu może przyspieszyć załatwienie sprawy. Urzędnik będzie mógł skontaktować się "
    "z Tobą w przypadku pytań lub wątpliwości.\nJeśli widzisz uzupełnione dane, sprawdź, czy są poprawne. "
    "Możesz je zmienić lub usunąć."
)
RODO_CONSENT = "Wyrażam zgodę na przetwarzanie moich danych osobowych zgodnie z klauzulą informacyjną."
PREVIEW_TEXT = ("Zanim przejdziesz do wyboru sposobu podpisu, sprawdź dane na podglądzie. "
                "Jeśli zobaczysz błędy, wróć do edycji.")


@dataclass
class _Tab:
    id: str
    title: str
    type: str
    questions: list[dict[str, Any]] = field(default_factory=list)
    y: int = 0


@dataclass
class BuildOptions:
    finish_component: FinishComponent = FinishComponent.TEXT_BLOCK
    validation_mode: ValidationMode = ValidationMode.FILLED


class FormBuilder:
    def __init__(self, analysis: FormAnalysis, seed: str, options: BuildOptions | None = None) -> None:
        self.a = analysis
        self.ids = IdFactory(seed)
        self.opts = options or BuildOptions()
        self.tabs: list[_Tab] = []
        self._refs: dict[int, q.FieldRef] = {}  # id(FieldSpec) -> adres w formularzu
        self._verb = _verb_for(analysis.title)

    # ------------------------------------------------------------------ API

    def build(self) -> dict[str, Any]:
        self._data_tab()
        for page in self.a.pages:
            tab = self._tab(page.title)
            for section in page.sections:
                self._domain_section(tab, section)
        self._contact_tab()
        self._finish_tab()
        return {
            "title": self.a.title[:255],
            "tabs": [{"id": t.id, "title": t.title, "type": t.type, "questions": t.questions} for t in self.tabs],
            "flow": {"links": [
                {"id": self.ids.uuid("flow", a.id), "source": a.id, "target": b.id}
                for a, b in pairwise(self.tabs)
            ]},
        }

    # ------------------------------------------------------------------ infrastruktura

    def _tab(self, title: str, type_: str = "MAIN") -> _Tab:
        existing = {t.title for t in self.tabs}
        base, n = title, 2
        while title in existing:  # JSONata adresuje strony po tytule — muszą być unikalne
            title, n = f"{base} ({n})", n + 1
        tab = _Tab(id=self.ids.uuid("tab", title), title=title, type=type_)
        self.tabs.append(tab)
        return tab

    def _validation(self, required: bool, extra: list[str] | tuple[str, ...] = ()) -> list[str]:
        if self.opts.validation_mode is ValidationMode.EMPTY:
            return []
        return (["REQUIRED"] if required else []) + [v for v in extra if v != "REQUIRED"]

    def _field(self, type_: str, tech: str, title: str = "", **kw: Any) -> dict[str, Any]:
        required = kw.pop("required", False)
        validators = kw.pop("validators", ())
        tech = self.ids.reserve(tech)
        return node(id=self.ids.uuid("field", tech), type=type_, tech_name=tech, title=title,
                    validation=self._validation(required, validators), **kw)

    def _section(self, tab: _Tab, tech: str, title: str, children: list[dict[str, Any]],
                 *, description: str | None = None, states: list[dict[str, str]] | None = None) -> str:
        tech = self.ids.reserve(tech)
        grid = []
        for i, child in enumerate(children):
            child["questionOrder"] = i
            grid.append(placed(child, y=i))
        rows = len(children) + 1
        section = node(id=self.ids.uuid("section", tech), type="SECTION", tech_name=tech, title=title,
                       description=to_html(description) if description else None, grid=grid,
                       states=states, order=tab.y)
        tab.questions.append(placed(section, y=tab.y, rows=rows))
        tab.y += rows
        return tech

    # ------------------------------------------------------------------ strona „Dane”

    def _data_tab(self) -> None:
        tab = self._tab(TAB_DATA)
        a = self.a

        organ = a.authority_is_organ
        authority_section = "organ" if organ else "urzad"
        self._section(tab, f"{authority_section}_do_ktorego_jest_skladany_wniosek",
                      f"{'Organ' if organ else 'Urząd'}, do którego jest składany wniosek", [
            self._field("TEXT_FIELD", "nazwa_organu" if organ else "nazwa_urzedu",
                        "Nazwa organu" if organ else "Nazwa urzędu", read_only=bool(a.authority),
                        default_value=a.authority, required=True),
        ])

        choices = ([OPT_SELF, OPT_OTHER] if a.applicant.person else []) + ([OPT_COMPANY] if a.applicant.company else [])
        who = q.FieldRef(TAB_DATA, "podmiot_wniosku", "wybierz_w_czyim_imieniu_wnioskujesz")
        role = q.FieldRef(TAB_DATA, "podmiot_wniosku", "wybierz_jako_kto_wnioskujesz")
        is_company = q.equals(who, OPT_COMPANY)
        is_other = q.equals(who, OPT_OTHER)
        podmiot = [self._field("RADIO", who.field, f"Wybierz, w czyim imieniu {self._verb}", options=choices,
                               required=True)]
        if a.applicant.company:
            podmiot.append(self._field("RADIO", role.field, f"Wybierz, jako kto {self._verb}",
                                       options=[OPT_PROXY, OPT_REPRESENTATIVE], required=True,
                                       states=q.show(is_company)))
        self._section(tab, "podmiot_wniosku", "Podmiot wniosku", podmiot)

        self._section(tab, "twoje_dane", "Twoje dane", [
            self._mlpz("imie", "Imię", "MLPZ.name", read_only=True),
            self._mlpz("nazwisko", "Nazwisko", "MLPZ.surname", read_only=True),
            self._mlpz("numer_pesel", "Numer PESEL", "MLPZ.pesel", read_only=True, validators=("PESEL",)),
        ])
        self._address(tab, "adres_zamieszkania", "Adres zamieszkania", suffix="", prefill=True)

        if a.applicant.company:
            company_states = q.show(is_company)
            self._section(tab, "dane_podmiotu", "Dane podmiotu", [
                self._field("TEXT_FIELD", "nazwa", "Nazwa", required=True),
                self._field("TEXT_FIELD", "nip", "NIP", required=True, validators=("NIP",)),
                self._field("TEXT_FIELD", "regon", "REGON", required=True, validators=("REGON",)),
                self._field("TEXT_FIELD", "numer_krs", "Numer KRS", tooltip="Wpisz 10 cyfr."),
            ], states=company_states)
            self._address(tab, "adres_siedziby", "Adres siedziby", suffix="_siedziba", states=company_states)
            self._section(tab, "potwierdzenie_ze_jestes_reprezentantem", "Potwierdzenie, że jesteś reprezentantem", [
                self._field("FILE_UPLOADER", "plik_z_odpisem_danych", "Plik z odpisem danych", required=True),
            ], description="Dołącz aktualny odpis danych z Krajowego Rejestru Sądowego lub innego rejestru. "
                           "Odpis powinien potwierdzać, że jesteś reprezentantem podmiotu lub instytucji.",
               states=q.show(q.all_of(is_company, q.equals(role, OPT_REPRESENTATIVE))))

        if a.applicant.person:
            other_states = q.show(is_other)
            self._section(tab, "dane_innej_osoby", "Dane innej osoby", [
                self._field("TEXT_FIELD", "imie_inna_osoba", "Imię", required=True),
                self._field("TEXT_FIELD", "nazwisko_inna_osoba", "Nazwisko", required=True),
                self._field("TEXT_FIELD", "numer_pesel_inna_osoba", "Numer PESEL", required=True,
                            validators=("PESEL",)),
            ], states=other_states)
            self._address(tab, "adres_zamieszkania_osoby_ktorej_jestes_pelnomocnikiem",
                          "Adres zamieszkania innej osoby", suffix="_inna_osoba", states=other_states)

        proxy_conditions = ([is_other] if a.applicant.person else []) + (
            [q.all_of(is_company, q.equals(role, OPT_PROXY))] if a.applicant.company else [])
        self._section(tab, "pelnomocnictwo", "Pełnomocnictwo", [
            self._field("FILE_UPLOADER", "plik_dokumentu_z_pelnomocnictwem", "Plik dokumentu z pełnomocnictwem",
                        required=True),
        ], description="Dodaj dokument potwierdzający, że jesteś pełnomocnikiem.",
           states=q.show(proxy_conditions[0] if len(proxy_conditions) == 1 else q.any_of(*proxy_conditions)))

        if a.applicant.person:
            fee = q.FieldRef(TAB_DATA, "oplata_skarbowa_pelnomocnictwo_1",
                             "czy_zlozenie_pelnomocnictwa_wymaga_oplaty_skarbowej")
            pays = q.show(q.equals(fee, "Tak"))
            self._section(tab, fee.section, "Opłata skarbowa", [
                self._field("RADIO", fee.field, "Czy złożenie pełnomocnictwa wymaga opłaty skarbowej?",
                            options=["Tak", "Nie"], required=True),
                self._field("TEXT_BLOCK", "oplata_info_1", description=to_html(STAMP_DUTY_TEXT.format(
                    who="zamieszkania osoby, która udzieliła pełnomocnictwa", title=a.title)), states=pays),
                self._field("FILE_UPLOADER", "plik_z_potwierdzeniem_przelewu", "Plik z potwierdzeniem przelewu",
                            required=True, states=pays),
            ], description="Nie musisz płacić za złożenie pełnomocnictwa wystawionego przez najbliższą rodzinę: "
                           "małżonka, dzieci, rodziców, dziadków, wnuków, rodzeństwo. "
                           "Więcej informacji na stronie biznes.gov.pl", states=other_states)
        if a.applicant.company:
            self._section(tab, "oplata_skarbowa_pelnomocnictwo_2", "Opłata skarbowa za pełnomocnictwo", [
                self._field("TEXT_BLOCK", "oplata_info", description=to_html(STAMP_DUTY_TEXT.format(
                    who="siedziby podmiotu, który udzielił pełnomocnictwa", title=a.title))),
                self._field("FILE_UPLOADER", "plik_z_potwierdzeniem_przelewu_2", "Plik z potwierdzeniem przelewu",
                            required=True),
            ], states=q.show(q.all_of(is_company, q.equals(role, OPT_PROXY))))

    def _mlpz(self, tech: str, title: str, source: str, *, read_only: bool = False,
              required: bool = True, validators: tuple[str, ...] = (), states=None) -> dict[str, Any]:
        """Pole zasilane danymi inicjalnymi z profilu zalogowanego użytkownika (MLPZ)."""
        return self._field("TEXT_FIELD", tech, title, read_only=read_only, default_value=source,
                           default_value_type=EXTERNAL, required=required, validators=validators, states=states)

    def _address(self, tab: _Tab, tech: str, title: str, *, suffix: str, prefill: bool = False,
                 states: list[dict[str, str]] | None = None) -> None:
        """Adres według jednolitego schematu ze „Standardów” (s. 11–15)."""
        country = q.FieldRef(TAB_DATA, tech, f"kraj{suffix}")
        poland, abroad = q.show(q.equals(country, "Polska")), q.show(q.not_equals(country, "Polska"))

        def pre(attr: str) -> dict[str, Any]:
            return {"default_value": f"MLPZ.{attr}", "default_value_type": EXTERNAL} if prefill else {}

        self._section(tab, tech, title, [
            self._field("SELECT", country.field, "Kraj", dictionary="Kraje", search_enabled=True,
                        default_value=["Polska"], required=True),
            self._field("TEXT_FIELD", f"miejscowosc{suffix}_zagranica", "Miejscowość", required=True, states=abroad),
            self._field("TEXT_FIELD", f"kod_pocztowy{suffix}_zagranica", "Kod pocztowy", required=True, states=abroad),
            self._field("TEXT_FIELD", f"ulica{suffix}_zagranica", "Ulica", required=True, states=abroad),
            self._field("SELECT", f"wojewodztwo{suffix}", "TERYT_4G_DOWODOWY",  # etykieta jak w eksportach z systemu
                        dictionary="TERYT_4G_DOWODOWY", multi_level_tree=True, search_enabled=True,
                        required=True, states=poland),
            self._field("TEXT_FIELD", f"kod_pocztowy{suffix}", "Kod pocztowy", required=True,
                        validators=("ZIP_CODE",), tooltip="__-___", states=poland, **pre("postCode")),
            self._field("TEXT_FIELD", f"ulica{suffix}", "Ulica", required=True, states=poland,
                        tooltip="Np. Polna, Aleja Leśna, Plac Lipowy, Skwer Słoneczny", **pre("street")),
            self._field("TEXT_FIELD", f"numer_budynku{suffix}", "Numer budynku", required=True, **pre("building")),
            self._field("TEXT_FIELD", f"numer_lokalu{suffix}", "Numer lokalu", **pre("apartment")),
        ], states=states)

    # ------------------------------------------------------------------ przedmiot wniosku

    def _domain_section(self, tab: _Tab, section: SectionSpec) -> None:
        sec_tech = self.ids.tech_name(section.title)
        children = []
        for spec in section.fields:
            tech = self.ids.tech_name(spec.label)
            self._refs[id(spec)] = q.FieldRef(tab.title, sec_tech, tech)
            children.append(self._domain_field(spec, tech))
        self.ids._tech.discard(sec_tech)  # _section rezerwuje nazwę ponownie
        self._section(tab, sec_tech, section.title, children, description=section.description,
                      states=self._states(section.show_if))

    def _domain_field(self, spec: FieldSpec, tech: str) -> dict[str, Any]:
        self.ids._tech.discard(tech)
        common: dict[str, Any] = {"states": self._states(spec.show_if),
                                  "description": to_html(spec.description) if spec.description else None}
        if spec.kind is Kind.TEXT_BLOCK:
            return self._field("TEXT_BLOCK", tech, **common)
        kind = spec.kind
        if spec.dictionary:
            # Słownik można podpiąć tylko pod listę rozwijaną, radio lub checkbox („Słowniki”).
            kind = kind if kind in (Kind.RADIO, Kind.CHECKBOX, Kind.SELECT) else Kind.SELECT
            common["dictionary"] = spec.dictionary
            if kind is Kind.SELECT:
                common["search_enabled"] = True
            if spec.dictionary == "Kraje":
                common["default_value"] = ["Polska"]
        elif kind is Kind.SELECT:
            common["search_enabled"] = spec.search
        if spec.initial_data:
            # Dane inicjalne z rejestru: pole tylko do odczytu („Dane inicjalne”, s. 1).
            common.update(read_only=True, default_value=spec.initial_data, default_value_type=EXTERNAL)
        return self._field(kind.value, tech, spec.label, options=spec.options, required=spec.required,
                           validators=spec.validators, **common)

    def _states(self, cond: Condition | None) -> list[dict[str, str]] | None:
        if cond is None:
            return None
        ref = self._refs.get(id(cond.field))
        return q.show(q.equals(ref, cond.value)) if ref else None

    # ------------------------------------------------------------------ kontakt, zgody, podgląd

    def _contact_tab(self) -> None:
        fee = bool(self.a.fee_info)
        tab = self._tab("Opłaty, kontakt i zgody" if fee else "Kontakt i zgody")
        if fee:
            self._section(tab, "oplata_za_wniosek", "Opłata", [
                self._field("TEXT_BLOCK", "informacja_o_oplacie", description=html_list(self.a.fee_info)),
                self._field("FILE_UPLOADER", "plik_z_potwierdzeniem_oplaty", "Plik z potwierdzeniem opłaty",
                            required=True),
            ])
        self._section(tab, "dane_do_kontaktu", "Dane do kontaktu", [
            self._mlpz("numer_telefonu", "Numer telefonu", "MLPZ.phoneNumber", required=False),
            self._mlpz("adres_e_mail", "Adres e-mail", "MLPZ.email", required=False, validators=("EMAIL",)),
        ], description=CONTACT_TEXT)
        consents = [{"description": to_html(s), "required": True} for s in self.a.statements]
        consents.append({"description": to_html(RODO_CONSENT), "required": True})
        self._section(tab, "zgody_i_oswiadczenia" if self.a.statements else "zgoda_wyrazenie",
                      "Zgody i oświadczenia" if self.a.statements else "Zgoda", [
            self._field("CONSENT_SECTION", "zgoda", consent_config={"consents": consents, "files": []}),
        ])

    def _finish_tab(self) -> None:
        tab = self._tab(TAB_FINISH, "FINISH")
        self._section(tab, "podglad_uzupelnionego_wniosku", "Podgląd uzupełnionego wniosku", [
            self._field(self.opts.finish_component.value, "podglad_1", description=to_html(PREVIEW_TEXT)),
        ])


def _verb_for(title: str) -> str:
    lowered = title.lower()
    if lowered.startswith("deklaracja"):
        return "deklarujesz"
    if lowered.startswith(("zgłoszenie", "zawiadomienie")):
        return "zgłaszasz"
    return "wnioskujesz"


def build_form(analysis: FormAnalysis, seed: str, options: BuildOptions | None = None) -> dict[str, Any]:
    return FormBuilder(analysis, seed, options).build()
