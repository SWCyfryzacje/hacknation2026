"""Analiza formularza oparta na regułach (bez modelu językowego).

Papierowe formularze mają powtarzalne wzorce:
  * wykropkowanie „………” = miejsce na odpowiedź, a podpis pod nim „( imię i nazwisko )” = etykieta,
  * lista punktowana po zdaniu zakończonym „:” = opcje wyboru, załączniki albo oświadczenia,
  * „☐ opcja ☐ opcja” w jednej linii = pole jednokrotnego wyboru,
  * „wynajem/użyczenie*” = wybór jednej z opcji („niepotrzebne skreślić”),
  * nagłówek przed tytułem = dane wnioskodawcy i adresat (obsługiwane sekcjami predefiniowanymi),
  * klauzula RODO, miejsce na podpis i datę — nie trafiają do formularza elektronicznego.
"""

import re
from dataclasses import dataclass

from app.analysis.lexicon import hint_for, is_optional
from app.analysis.model import (
    Applicant,
    Condition,
    FieldSpec,
    FormAnalysis,
    Kind,
    PageSpec,
    SectionSpec,
)
from app.extraction.model import ExtractedDocument, Line
from app.extraction.text import CHECKBOX

SLOT = "▁"  # znacznik miejsca na odpowiedź
_SLOT_RE = re.compile(r"(?:[.…_]\s?){4,}|…{2,}|_{3,}")
_CAPTION_RE = re.compile(r"^[(/]\s*([^()]+?)\s*[)/]?$")
_TITLE_RE = re.compile(r"^(wniosek|deklaracja|zgłoszenie|oświadczenie|podanie|informacja|zawiadomienie)\b", re.I)
_TITLE_STOP_RE = re.compile(r"^(proszę|wnoszę|zgodnie|na podstawie|niniejszym|\d+[.)]|[a-z][.)/])", re.I)
_AUTHORITY_RE = re.compile(
    r"\b(Urząd|URZĄD|Wójt|WÓJT|Burmistrz|BURMISTRZ|Prezydent|PREZYDENT|Starost[ao]|STAROST[AO]|Marszałek|MARSZAŁEK|"
    r"Zarząd|ZARZĄD|Rada|RADA|Dyrektor|DYREKTOR|Kierownik|KIEROWNIK|Starostwo|STAROSTWO)\b[^()|\t,;]*")
_ORGAN_RE = re.compile(r"^(wójt|burmistrz|prezydent|starosta|marszałek|zarząd|rada|dyrektor|kierownik)", re.I)
_STOP_RE = re.compile(
    r"klauzula informacyjna|zgodnie z art\.?\s*13|administratorem (pani|pana|państwa|twoich|pan)|"
    r"^\s*(rodo|pouczenie|objaśnienia)\b|ogólne rozporządzenie o ochronie danych", re.I)
_SKIP_RE = re.compile(r"podpis|miejscowość i data|miejscowość, data|^\(?data\)?$|^załącznik nr|^\s*\d+\)\s", re.I)
# „Młynary, dnia ……” / „…… dnia ……” — miejscowość i data wypełnienia (zastępuje je data złożenia w systemie)
_DATE_PLACE_RE = re.compile(rf"^\s*(\S+\s*){{0,2}},?\s*dnia\s*{SLOT}?\s*(r\.?)?\s*$", re.I)
_REQUEST_VERB_RE = re.compile(r"^(proszę|wnoszę|wnioskuję|zwracam się)( uprzejmie)?( o| z prośbą o)?\s+", re.I)
_TRAILING_PREP_RE = re.compile(r"\s+(w|we|na|do|o|od|przy|z|ze|dla|pod|nr|i|oraz|lub|celem)$", re.I)
_LEADING_NUM_RE = re.compile(r"^\s*(\d+|[IVX]+|[a-zA-Z])\s*[.)/]\s*")
_ALT_STAR_RE = re.compile(r"\b([a-ząćęłńóśźż]{3,})/([a-ząćęłńóśźż]{3,})\*", re.I)
_FEE_RE = re.compile(r"opłat\w*.*\d+\s*zł|\d+\s*zł.*opłat", re.I)

_APPLICANT_RE = re.compile(
    r"imię|nazwisk|adres|pesel|telefon|\btel\b|e-?mail|wnioskodaw|nazwa (firmy|podmiotu)|siedzib|\bnip\b|regon|krs",
    re.I)
_COMPANY_RE = re.compile(r"nazwa (firmy|podmiotu|wnioskodawcy|przedsiębior)|/\s*nazwa|lub nazwa|siedzib|\bnip\b|"
                         r"regon|\bkrs\b|przedsiębior|osob[ay] prawn", re.I)

_GROUP_ATTACH_RE = re.compile(r"załącz|dołącz|dokument", re.I)
_GROUP_STATEMENT_RE = re.compile(r"oświadczam|zobowiązuj|wyrażam zgodę", re.I)
_GROUP_INFO_RE = re.compile(r"^(informacj|uwag|pouczeni|objaśnieni)", re.I)
_MULTI_RE = re.compile(r"zaznacz|można wybrać|właściwe|wielokrotn", re.I)
_MINOR_WORDS = {"i", "w", "we", "z", "ze", "na", "do", "o", "od", "dla", "pod", "przy", "oraz", "lub"}


@dataclass
class _Line:
    text: str  # z wykropkowaniami zamienionymi na SLOT
    list_item: bool
    cells: list[str] | None
    raw: str

    @property
    def has_slot(self) -> bool:
        return SLOT in self.text

    @property
    def only_slot(self) -> bool:
        return self.text.replace(SLOT, "").strip(" .:,") == ""

    @property
    def caption(self) -> str | None:
        m = _CAPTION_RE.match(self.text)
        return m.group(1).strip() if m and not self.has_slot and len(self.text) < 120 else None


def analyze(document: ExtractedDocument, *, fallback_title: str) -> FormAnalysis:
    lines = _prepare(document.lines)
    title_idx = _find_title(lines)
    if title_idx is None:
        title, header, body = _title_from_filename(fallback_title), [], lines
        warnings = ["Nie znaleziono tytułu formularza — użyto nazwy pliku."]
    else:
        title, end = _assemble_title(lines, title_idx)
        header, body = lines[:title_idx], lines[end:]
        warnings = []

    authority = _find_authority(header) or _find_authority(lines[:12])
    applicant = _detect_applicant(header, title)
    parser = _BodyParser(title)
    parser.parse_header(header)
    parser.parse(body)

    analysis = FormAnalysis(
        title=title,
        authority=authority,
        authority_is_organ=bool(authority and _ORGAN_RE.match(authority)),
        applicant=applicant,
        pages=parser.pages(),
        statements=parser.statements,
        fee_info=parser.fee_info,
        warnings=warnings + document.warnings,
    )
    if authority is None:
        analysis.warnings.append("Nie rozpoznano urzędu — uzupełnij nazwę urzędu w konfiguracji.")
    if analysis.field_count == 0:
        analysis.warnings.append("Nie rozpoznano pól przedmiotu wniosku — sprawdź jakość dokumentu.")
    return analysis


# --------------------------------------------------------------------------- przygotowanie


def _prepare(raw: list[Line]) -> list[_Line]:
    out: list[_Line] = []
    for line in raw:
        text = line.text
        if line.cells:
            text = " ".join(c for c in line.cells if c)
        text = _SLOT_RE.sub(f" {SLOT} ", text)
        text = re.sub(rf"{SLOT}(\s*{SLOT})+", SLOT, text)
        text = re.sub(r"\s+", " ", text).strip()
        if text:
            out.append(_Line(text=text, list_item=line.list_item, cells=line.cells, raw=line.text))
    return out


def _find_title(lines: list[_Line]) -> int | None:
    for i, line in enumerate(lines):
        if _TITLE_RE.match(line.text) and not line.has_slot and len(line.text) < 160:
            return i
    return None


def _assemble_title(lines: list[_Line], start: int) -> tuple[str, int]:
    parts = [lines[start].text]
    end = start + 1
    while end < len(lines) and len(parts) < 4:
        nxt = lines[end]
        if nxt.has_slot or nxt.list_item or nxt.caption or _TITLE_STOP_RE.match(nxt.text) or len(nxt.text) > 90:
            break
        if not (nxt.text.isupper() or nxt.text[:1].islower() or len(parts) == 1 and len(parts[0].split()) == 1):
            break
        parts.append(nxt.text)
        end += 1
    return _normalize_title(" ".join(parts)), end


def _normalize_title(title: str) -> str:
    title = re.sub(r"\*+", "", title)
    title = _ALT_STAR_RE.sub(lambda m: f"{m[1]} lub {m[2]}", title)
    title = re.sub(r"\b([a-ząćęłńóśźż]{3,})/([a-ząćęłńóśźż]{3,})\b", r"\1 lub \2", title, flags=re.I)
    title = re.sub(r"\s+", " ", title).strip(" .:")
    if title.isupper() or sum(c.isupper() for c in title) > len(title) / 2:
        title = title.lower()
    else:  # „WNIOSEK o wydanie …” — słowa pisane wersalikami sprowadzamy do zwykłej pisowni
        title = " ".join(w.lower() if w.isupper() and len(w) > 3 else w for w in title.split())
    return title[:1].upper() + title[1:255]


def _title_from_filename(name: str) -> str:
    stem = re.sub(r"\.[^.]+$", "", name)
    stem = re.sub(r"[_\-]+", " ", stem).strip()
    return (stem[:1].upper() + stem[1:])[:255] or "Wniosek"


def _find_authority(lines: list[_Line]) -> str | None:
    for line in lines:
        if line.caption or _STOP_RE.search(line.text):
            continue
        m = _AUTHORITY_RE.search(line.text.replace(SLOT, "|"))
        if m:
            name = re.sub(r"\s+", " ", m.group(0)).strip(" .")
            if len(name.split()) >= 2:
                return _smart_title_case(name)
    return None


def _smart_title_case(name: str) -> str:
    if not name.isupper():
        return name
    words = name.lower().split()
    return " ".join(w if (i and w in _MINOR_WORDS) else w[:1].upper() + w[1:] for i, w in enumerate(words))


def _detect_applicant(header: list[_Line], title: str) -> Applicant:
    text = " ".join(line.text for line in header) + " " + title
    company = bool(_COMPANY_RE.search(text))
    person = bool(re.search(r"imię|nazwisk|pesel|zamieszka", text, re.I)) or not company
    return Applicant(person=person, company=company)


# --------------------------------------------------------------------------- treść


def _sentence(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip(" :;,.-–*")
    return text[:1].upper() + text[1:] if text else text


def _shorten_label(text: str) -> str:
    """Z kontekstu przed wykropkowaniem robi krótką etykietę pola."""
    text = text.replace(SLOT, " ").strip()
    text = _LEADING_NUM_RE.sub("", text)
    text = _REQUEST_VERB_RE.sub("", text)
    text = re.sub(r"\*+|\b\d\)", "", text)  # gwiazdki i odnośniki do przypisów („ulicy1)”)
    text = re.sub(r"\([^)]*\)", "", text)
    clauses = [c for c in re.split(r"[,;:]| - | – ", text) if c.strip()]
    text = clauses[-1] if clauses else text
    words = text.split()
    if len(words) > 8:
        text = " ".join(words[-6:])
    prev = None
    while prev != text:
        prev, text = text, _TRAILING_PREP_RE.sub("", text.strip())
    return _sentence(text)


def _date_range_label(prefix: str, connector: str) -> str:
    base = "Termin" if re.search(r"termin", prefix, re.I) else "Okres" if re.search(r"okres", prefix, re.I) else "Data"
    return f"{base} {connector.lower()}"


def _html_text(text: str) -> str:
    return text.replace(SLOT, "…")


class _BodyParser:
    def __init__(self, title: str) -> None:
        self.title = title
        self._sections: list[SectionSpec] = [SectionSpec(title="Szczegóły wniosku")]
        self.statements: list[str] = []
        self.fee_info: list[str] = []
        self._seen_alternatives: set[tuple[str, str]] = set()
        for m in _ALT_STAR_RE.finditer(title):
            self._seen_alternatives.add((m[1].lower(), m[2].lower()))

    @property
    def _current(self) -> SectionSpec:
        return self._sections[-1]

    def _add(self, spec: FieldSpec) -> FieldSpec:
        self._current.fields.append(spec)
        return spec

    # -- nagłówek: dane wnioskodawcy pokrywają sekcje predefiniowane, resztę zachowujemy
    def parse_header(self, header: list[_Line]) -> None:
        for i, line in enumerate(header):
            if not line.only_slot:
                continue
            caption = header[i + 1].caption if i + 1 < len(header) else None
            if caption and not _APPLICANT_RE.search(caption) and not _SKIP_RE.search(caption):
                self._add(self._make_field(_sentence(caption), context=caption))

    # -- treść właściwa
    def parse(self, body: list[_Line]) -> None:
        i = 0
        while i < len(body):
            line = body[i]
            if _STOP_RE.search(line.text):
                break
            if _SKIP_RE.search(line.text) or _DATE_PLACE_RE.match(line.text) or line.caption:
                i += 1
                continue
            if _FEE_RE.search(line.text) and not re.search(r"pełnomoc", line.text, re.I):
                self.fee_info.append(_sentence(line.text))
            if line.only_slot:
                i += 1  # samotne wykropkowanie bez etykiety (kontynuacja poprzedniego pola)
                continue

            items, j = self._collect_list(body, i + 1)
            if items and not line.list_item and (line.text.rstrip().endswith((":", ":*", "*")) or not line.has_slot):
                self._group(line, items)
                i = j
                continue
            if line.text.count(CHECKBOX) >= 2:
                self._inline_choice(line)
            elif line.has_slot:
                caption = self._caption_after(body, i)
                multiline = (i + 1 < len(body) and body[i + 1].only_slot
                             and not (caption and _SKIP_RE.search(caption)))
                self._slots(line, caption=caption, multiline=multiline)
            elif i + 1 < len(body) and body[i + 1].only_slot and len(line.text) < 200:
                # „3. Osoba odpowiedzialna …:” + wykropkowanie w kolejnej linii (+ podpis pod nim)
                caption = self._caption_after(body, i)
                if not (caption and _SKIP_RE.search(caption)):
                    self._slots(_Line(text=f"{line.text} {SLOT}", list_item=False, cells=None, raw=line.raw),
                                caption=caption, multiline=False)
            elif self._is_heading(line):
                self._sections.append(SectionSpec(title=_sentence(_LEADING_NUM_RE.sub("", line.text))))
            elif line.cells and len([c for c in line.cells if c]) >= 2:
                self._table_header(line)
            self._alternatives(line)
            i += 1

    def _caption_after(self, body: list[_Line], i: int) -> str | None:
        for k in (i + 1, i + 2):
            if k < len(body):
                if body[k].caption:
                    return body[k].caption
                if not body[k].only_slot:
                    return None
        return None

    @staticmethod
    def _collect_list(body: list[_Line], start: int) -> tuple[list[_Line], int]:
        items: list[_Line] = []
        k = start
        while k < len(body) and (body[k].list_item or (items and body[k].only_slot)):
            if body[k].list_item:
                items.append(body[k])
            k += 1
        return items, k

    @staticmethod
    def _is_heading(line: _Line) -> bool:
        return (len(line.text) < 120 and not line.list_item
                and (line.text.endswith(":") or bool(_LEADING_NUM_RE.match(line.text)) and line.text[:1].isdigit()))

    # -- grupy: lista po zdaniu wprowadzającym
    def _group(self, intro: _Line, items: list[_Line]) -> None:
        intro_text = intro.text
        if _GROUP_STATEMENT_RE.search(intro_text):
            lead = _sentence(_LEADING_NUM_RE.sub("", intro_text.split("(")[0])).rstrip(",")
            for item in items:
                self.statements.append(f"{lead} {item.text.rstrip(',;.')}." if lead.lower().endswith("że")
                                       else _sentence(item.text) + ".")
            return
        if _GROUP_ATTACH_RE.search(intro_text):
            self._sections.append(SectionSpec(title="Załączniki"))
            for item in items:
                if re.search(r"pełnomocnict", item.text, re.I):
                    continue  # obsługuje predefiniowana sekcja „Pełnomocnictwo”
                label = _attachment_label(item.text)
                self._add(FieldSpec(label=label, kind=Kind.FILE, required=not is_optional(item.text),
                                    description=_sentence(item.text) if label != _sentence(item.text) else None))
            return
        if _GROUP_INFO_RE.search(intro_text):
            for item in items:
                if _FEE_RE.search(item.text):
                    self.fee_info.append(_sentence(item.text))
            return
        if self._is_heading(intro) and all(it.has_slot for it in items):
            self._sections.append(SectionSpec(title=_sentence(_LEADING_NUM_RE.sub("", intro_text))))
            for it in items:
                self._slots(it, caption=None, multiline=False)
            return
        self._choice(intro, items)

    def _choice(self, intro: _Line, items: list[_Line]) -> None:
        options, other_slot = [], False
        for it in items:
            name = _sentence(it.text.replace(SLOT, ""))
            if it.has_slot:
                other_slot = True
            if name:
                options.append(name)
        if not options:
            return
        label = _shorten_label(intro.text) or "Wybierz opcję"
        multi = bool(_MULTI_RE.search(intro.text))
        kind = Kind.CHECKBOX if multi else (Kind.SELECT if len(options) > 5 else Kind.RADIO)
        choice = self._add(FieldSpec(label=label, kind=kind, options=options, search=len(options) > 15,
                                     description=_sentence(intro.text) if len(intro.text) > len(label) + 15 else None))
        if other_slot:
            other = next((o for o in options if re.match(r"inn", o, re.I)), options[-1])
            self._add(FieldSpec(label=f"{other} – podaj jakie", kind=Kind.TEXTAREA,
                                show_if=Condition(choice, other)))

    def _inline_choice(self, line: _Line) -> None:
        head, *opts = [p.strip(" :,;") for p in line.text.split(CHECKBOX)]
        options = [_sentence(o.replace(SLOT, "")) for o in opts if o.replace(SLOT, "").strip()]
        if options:
            self._add(FieldSpec(label=_sentence(head) or "Wybierz opcję",
                                kind=Kind.RADIO if len(options) <= 5 else Kind.SELECT, options=options))

    def _alternatives(self, line: _Line) -> None:
        """„wynajem/użyczenie*” w treści — użytkownik wybiera jedną z opcji."""
        for m in _ALT_STAR_RE.finditer(line.text):
            key = (m[1].lower(), m[2].lower())
            stems = tuple(w[:5] for w in key)
            if any(tuple(w[:5] for w in seen) == stems for seen in self._seen_alternatives):
                continue
            self._seen_alternatives.add(key)
            self._current.fields.insert(0, FieldSpec(
                label="Czego dotyczy wniosek?", kind=Kind.RADIO, options=[_sentence(m[1]), _sentence(m[2])]))

    def _table_header(self, line: _Line) -> None:
        existing = {f.label.lower() for f in self._current.fields}
        for cell in line.cells or []:
            label = _sentence(cell)
            is_unit = re.fullmatch(r"m2|zł|lp\.?", label, re.I)
            if label and len(label) < 60 and label.lower() not in existing and not is_unit:
                existing.add(label.lower())
                self._add(self._make_field(label))

    # -- pola z wykropkowaniem
    def _slots(self, line: _Line, *, caption: str | None, multiline: bool) -> None:
        segments = line.text.split(SLOT)
        prefixes = segments[:-1]
        trailing = segments[-1].strip()
        context = _html_text(line.text)
        for idx, prefix in enumerate(prefixes):
            raw = prefix.strip()
            connector = re.search(r"\b(od|do)( dnia)?$", raw, re.I)
            if connector and (idx > 0 or re.search(r"termin|okres|dnia|data", raw, re.I)):
                full = " ".join(prefixes[: idx + 1])
                spec = FieldSpec(label=_date_range_label(full, connector[1]), kind=Kind.DATE)
            else:
                label = _shorten_label(raw)
                if not label and caption:
                    label = _sentence(caption)
                if not label and trailing and idx == len(prefixes) - 1:
                    label = _sentence(trailing)
                if not label:
                    continue
                if _SKIP_RE.search(label):
                    continue
                spec = self._make_field(label, context=f"{raw} {caption or ''} {trailing}",
                                        multiline=multiline and idx == len(prefixes) - 1)
                if caption and spec.description is None and _sentence(caption).lower() != label.lower():
                    spec.description = _sentence(caption)
            if len(prefixes) > 1 or len(raw) > len(spec.label) + 25:
                spec.description = spec.description or _sentence(context)
            self._add(spec)

    def _make_field(self, label: str, *, context: str = "", multiline: bool = False) -> FieldSpec:
        hint = hint_for(label, context)
        kind = hint.kind or (Kind.TEXTAREA if multiline else Kind.TEXT)
        if multiline and kind == Kind.TEXT and not hint.validators:
            kind = Kind.TEXTAREA
        return FieldSpec(label=label[:120], kind=kind, validators=list(hint.validators), dictionary=hint.dictionary,
                         required=not (hint.optional or is_optional(context)), description=hint.description,
                         search=hint.dictionary is not None)

    # -- podział na strony
    def pages(self) -> list[PageSpec]:
        sections = [s for s in self._sections if s.fields]
        for s in sections:  # unikalne etykiety w sekcji
            seen: dict[str, int] = {}
            for f in s.fields:
                n = seen.get(f.label.lower(), 0)
                seen[f.label.lower()] = n + 1
                if n:
                    f.label = f"{f.label} ({n + 1})"
        if not sections:
            return []
        total = sum(len(s.fields) for s in sections)
        if total <= 15 or len(sections) == 1:
            return [PageSpec(title="Przedmiot wniosku", sections=sections)]
        pages: list[PageSpec] = []
        bucket: list[SectionSpec] = []
        for s in sections:
            if bucket and sum(len(b.fields) for b in bucket) + len(s.fields) > 12:
                pages.append(PageSpec(title=bucket[0].title, sections=bucket))
                bucket = []
            bucket.append(s)
        if bucket:
            pages.append(PageSpec(title=bucket[0].title, sections=bucket))
        if pages and pages[0].title == "Szczegóły wniosku":
            pages[0].title = "Przedmiot wniosku"
        return pages


def _attachment_label(text: str) -> str:
    text = re.sub(r"\(.*?\)", "", text)
    text = re.split(r",| w skali | jeżeli | jeśli | z zaznaczeniem | stosownie | wraz z ", text, maxsplit=1)[0]
    words = text.split()
    label = " ".join(words[:8])
    return _sentence(label)
