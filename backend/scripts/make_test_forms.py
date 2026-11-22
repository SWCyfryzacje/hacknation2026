"""Generator testowych formularzy urzędowych z kluczem odpowiedzi (dowód działania na nowych dokumentach).

    python scripts/make_test_forms.py ../testy/formularze

Każdy formularz jest opisany danymi (SPECS) w stylu papierowego wniosku: nagłówek z danymi wnioskodawcy,
adresat, tytuł, pola z wykropkowaniem, wybory z kratkami ☐, zależności („jeśli…, podaj…”), oświadczenia,
załączniki. Z tego samego opisu powstają:
  * pliki w 7 formatach: DOCX, DOC (zawartość DOCX — jak w materiałach wyzwania), PDF (LibreOffice
    w kontenerze aplikacji), XLSX, ODS, PNG i JPG („skany” z szumem, obrotem i kompresją),
  * klucz odpowiedzi `<id>.expected.json` do automatycznej oceny (scripts/evaluate.py).
PDF i skany wymagają Dockera z obrazem formularze-ai:0.1.0 (LibreOffice); bez niego powstaje 5 formatów.
"""

from __future__ import annotations

import io
import json
import random
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

import docx
import openpyxl
from PIL import Image, ImageFilter

DOTS = "…………………………………"
IMAGE = "formularze-ai:0.1.0"

# Typy pól zgodne z konfiguracją eUsługi: TEXT_FIELD, TEXTAREA, NUMBER, DATEPICKER, RADIO, CHECKBOX, SELECT, FILE_UPLOADER.
SPECS: list[dict] = [
    {
        "id": "T1", "title": "WNIOSEK O UDOSTĘPNIENIE INFORMACJI PUBLICZNEJ",
        "authority": "Burmistrz Miasta Kruszwica", "person": True, "company": False,
        "header": ["imię i nazwisko", "adres", "telefon"],
        "intro": "Na podstawie ustawy o dostępie do informacji publicznej wnoszę o udostępnienie informacji:",
        "items": [
            {"label": "Zakres wnioskowanej informacji", "kind": "TEXTAREA", "multiline": True},
            {"label": "Sposób udostępnienia informacji", "kind": "RADIO",
             "options": ["Przesłanie pocztą elektroniczną", "Przesłanie pocztą tradycyjną", "Wgląd w urzędzie"]},
            {"label": "Adres e-mail do przesłania informacji", "kind": "TEXT_FIELD",
             "if": ("Sposób udostępnienia informacji", "Przesłanie pocztą elektroniczną")},
            {"label": "Adres do korespondencji", "kind": "TEXT_FIELD",
             "if": ("Sposób udostępnienia informacji", "Przesłanie pocztą tradycyjną")},
            {"label": "Forma przekazania informacji", "kind": "RADIO", "options": ["Kopia papierowa", "Plik elektroniczny"]},
        ],
        "statements": [], "attachments": [], "fee": False,
    },
    {
        "id": "T2", "title": "WNIOSEK O WYDANIE ZEZWOLENIA NA USUNIĘCIE DRZEWA LUB KRZEWU",
        "authority": "Wójt Gminy Lubicz", "person": True, "company": True,
        "header": ["imię i nazwisko / nazwa wnioskodawcy", "adres zamieszkania / siedziby", "NIP (dotyczy firm)"],
        "intro": "Wnoszę o wydanie zezwolenia na usunięcie drzew lub krzewów rosnących na nieruchomości:",
        "items": [
            {"label": "Adres nieruchomości", "kind": "TEXT_FIELD"},
            {"label": "Numer ewidencyjny działki", "kind": "TEXT_FIELD"},
            {"label": "Tytuł prawny do nieruchomości", "kind": "RADIO",
             "options": ["Własność", "Współwłasność", "Użytkowanie wieczyste", "Inny"]},
            {"label": "Inny tytuł prawny – opis", "kind": "TEXT_FIELD", "if": ("Tytuł prawny do nieruchomości", "Inny")},
            {"label": "Gatunek drzewa lub krzewu", "kind": "TEXT_FIELD"},
            {"label": "Obwód pnia na wysokości 130 cm (cm)", "kind": "NUMBER"},
            {"label": "Przyczyna usunięcia", "kind": "TEXTAREA", "multiline": True},
            {"label": "Planowany termin usunięcia", "kind": "DATEPICKER"},
        ],
        "statements": ["Oświadczam, że posiadam tytuł prawny władania nieruchomością."],
        "attachments": ["Rysunek lub mapa określająca usytuowanie drzewa", "Zgoda współwłaściciela nieruchomości (jeżeli dotyczy)"],
        "fee": False,
    },
    {
        "id": "T3", "title": "WNIOSEK O WPIS DO REJESTRU DZIAŁALNOŚCI REGULOWANEJ W ZAKRESIE ODBIERANIA ODPADÓW KOMUNALNYCH",
        "authority": "Urząd Miasta Grudziądz", "person": False, "company": True,
        "header": ["nazwa przedsiębiorcy", "adres siedziby", "NIP", "REGON", "numer KRS"],
        "intro": "Wnoszę o wpis do rejestru działalności regulowanej:",
        "items": [
            {"label": "Rodzaje odbieranych odpadów komunalnych", "kind": "CHECKBOX",
             "options": ["Zmieszane", "Papier", "Szkło", "Tworzywa sztuczne i metale", "Bioodpady"]},
            {"label": "Numer rejestrowy w BDO", "kind": "TEXT_FIELD"},
            {"label": "Data rozpoczęcia działalności", "kind": "DATEPICKER"},
        ],
        "statements": ["Oświadczam, że dane zawarte we wniosku są kompletne i zgodne z prawdą.",
                       "Oświadczam, że znane mi są i spełniam warunki wykonywania działalności."],
        "attachments": ["Dowód uiszczenia opłaty skarbowej"], "fee": True,
        "fee_text": "Opłata skarbowa za wpis do rejestru wynosi 50 zł.",
    },
    {
        "id": "T4", "title": "DEKLARACJA NA PODATEK OD NIERUCHOMOŚCI",
        "authority": "Prezydent Miasta Włocławek", "person": True, "company": False,
        "header": ["imię i nazwisko podatnika", "PESEL", "adres zamieszkania"],
        "intro": "Okoliczności powodujące obowiązek złożenia deklaracji:",
        "items": [
            {"label": "Rodzaj deklaracji", "kind": "RADIO", "options": ["Deklaracja roczna", "Korekta deklaracji"]},
            {"label": "Przyczyna korekty", "kind": "TEXTAREA", "if": ("Rodzaj deklaracji", "Korekta deklaracji")},
            {"label": "Powierzchnia gruntów (m2)", "kind": "NUMBER"},
            {"label": "Powierzchnia użytkowa budynków mieszkalnych (m2)", "kind": "NUMBER"},
            {"label": "Powierzchnia budynków związanych z działalnością gospodarczą (m2)", "kind": "NUMBER"},
            {"label": "Wartość budowli (zł)", "kind": "NUMBER"},
        ],
        "statements": ["Oświadczam, że podane przeze mnie dane są zgodne z prawdą."], "attachments": [], "fee": False,
    },
    {
        "id": "T5", "title": "WNIOSEK O WYDANIE ZAŚWIADCZENIA O ZAMELDOWANIU",
        "authority": "Urząd Gminy Obrowo", "person": True, "company": False,
        "header": ["imię i nazwisko", "PESEL", "adres"],
        "intro": "Proszę o wydanie zaświadczenia o zameldowaniu:",
        "items": [
            {"label": "Rodzaj pobytu", "kind": "RADIO", "options": ["Stały", "Czasowy"]},
            {"label": "Data zameldowania od", "kind": "DATEPICKER"},
            {"label": "Cel wydania zaświadczenia", "kind": "TEXT_FIELD"},
            {"label": "Liczba egzemplarzy", "kind": "NUMBER"},
        ],
        "statements": [], "attachments": ["Potwierdzenie zapłaty opłaty skarbowej"], "fee": True,
        "fee_text": "Opłata skarbowa za wydanie zaświadczenia wynosi 17 zł.",
    },
    {
        "id": "T6", "title": "WNIOSEK O WYDANIE IDENTYFIKATORA MIESZKAŃCA STREFY PŁATNEGO PARKOWANIA",
        "authority": "Zarząd Dróg Miejskich w Bydgoszczy", "person": True, "company": False,
        "header": ["imię i nazwisko", "adres zamieszkania", "telefon"],
        "intro": "Wnoszę o wydanie identyfikatora mieszkańca dla pojazdu:",
        "items": [
            {"label": "Numer rejestracyjny pojazdu", "kind": "TEXT_FIELD"},
            {"label": "Marka i model pojazdu", "kind": "TEXT_FIELD"},
            {"label": "Tytuł do pojazdu", "kind": "RADIO", "options": ["Właściciel", "Współwłaściciel", "Leasing"]},
            {"label": "Okres ważności identyfikatora", "kind": "RADIO", "options": ["Miesiąc", "Kwartał", "Rok"]},
        ],
        "statements": ["Oświadczam, że zamieszkuję na obszarze strefy płatnego parkowania."],
        "attachments": ["Kopia dowodu rejestracyjnego"], "fee": False,
    },
    {
        "id": "T7", "title": "ZGŁOSZENIE IMPREZY PLENEROWEJ",
        "authority": "Burmistrz Miasta Chełmża", "person": True, "company": True,
        "header": ["nazwa organizatora / imię i nazwisko", "adres", "telefon"],
        "intro": "Zgłaszam zamiar zorganizowania imprezy plenerowej:",
        "items": [
            {"label": "Nazwa imprezy", "kind": "TEXT_FIELD"},
            {"label": "Miejsce imprezy", "kind": "TEXT_FIELD"},
            {"label": "Data rozpoczęcia imprezy", "kind": "DATEPICKER"},
            {"label": "Data zakończenia imprezy", "kind": "DATEPICKER"},
            {"label": "Przewidywana liczba uczestników", "kind": "NUMBER"},
            {"label": "Czy impreza obejmuje sprzedaż alkoholu", "kind": "RADIO", "options": ["Tak", "Nie"]},
            {"label": "Numer zezwolenia na sprzedaż alkoholu", "kind": "TEXT_FIELD",
             "if": ("Czy impreza obejmuje sprzedaż alkoholu", "Tak")},
        ],
        "statements": ["Zobowiązuję się do zapewnienia porządku i bezpieczeństwa uczestników.",
                       "Zobowiązuję się do uporządkowania terenu po zakończeniu imprezy."],
        "attachments": ["Plan sytuacyjny terenu imprezy"], "fee": False,
    },
    {
        "id": "T8", "title": "WNIOSEK O ZWROT PODATKU AKCYZOWEGO ZAWARTEGO W CENIE OLEJU NAPĘDOWEGO",
        "authority": "Wójt Gminy Łysomice", "person": True, "company": False,
        "header": ["imię i nazwisko producenta rolnego", "PESEL", "adres zamieszkania"],
        "intro": "Wnoszę o zwrot podatku akcyzowego zawartego w cenie oleju napędowego wykorzystywanego do produkcji rolnej:",
        "items": [
            {"label": "Powierzchnia użytków rolnych (ha)", "kind": "NUMBER"},
            {"label": "Liczba dużych jednostek przeliczeniowych bydła", "kind": "NUMBER"},
            {"label": "Sposób wypłaty zwrotu", "kind": "RADIO", "options": ["Przelew na rachunek bankowy", "Gotówka w kasie urzędu"]},
            {"label": "Numer rachunku bankowego", "kind": "TEXT_FIELD",
             "if": ("Sposób wypłaty zwrotu", "Przelew na rachunek bankowy")},
        ],
        "statements": ["Oświadczam, że olej napędowy został wykorzystany do produkcji rolnej."],
        "attachments": ["Faktury VAT stanowiące dowód zakupu oleju napędowego"], "fee": False,
    },
]


# ------------------------------------------------------------------ treść „papierowa”


def paper_lines(spec: dict) -> list[tuple[str, str]]:
    """Linie dokumentu: (rodzaj, tekst); rodzaj: p (akapit), opt (kratka ☐), cap (podpis pod polem), h (nagłówek)."""
    out: list[tuple[str, str]] = [("p", "……………………, dnia ………………"), ("cap", "(miejscowość i data)")]
    for caption in spec["header"]:
        out += [("p", DOTS), ("cap", f"({caption})")]
    out += [("p", spec["authority"]), ("h", spec["title"]), ("p", spec["intro"])]
    for n, item in enumerate(spec["items"], 1):
        label = item["label"]
        if "if" in item:
            label = f"W przypadku wyboru „{item['if'][1]}” – {label[:1].lower() + label[1:]}"
        if item["kind"] in ("RADIO", "CHECKBOX"):
            note = " (można zaznaczyć kilka)" if item["kind"] == "CHECKBOX" else " (zaznaczyć właściwe)"
            out.append(("p", f"{n}. {label}{note}:"))
            out += [("opt", o) for o in item["options"]]
        else:
            out.append(("p", f"{n}. {label}: {DOTS}"))
            if item.get("multiline"):
                out += [("p", DOTS * 2), ("p", DOTS * 2)]
    if spec.get("fee"):
        out.append(("p", spec["fee_text"]))
    for s in spec["statements"]:
        out.append(("p", s))
    if spec["attachments"]:
        out.append(("p", "Załączniki:"))
        out += [("opt", a) for a in spec["attachments"]]
    out += [("p", DOTS), ("cap", "(podpis wnioskodawcy)"),
            ("p", "Klauzula informacyjna: administratorem danych osobowych jest " + spec["authority"] + ".")]
    return out


def expected(spec: dict) -> dict:
    title = spec["title"][:1] + spec["title"][1:].lower()
    return {
        "id": spec["id"], "title": title, "authority": spec["authority"],
        "applicant": {"person": spec["person"], "company": spec["company"]},
        "fields": [{"label": i["label"], "kind": i["kind"], "options": i.get("options", [])}
                   for i in spec["items"]] + [{"label": a, "kind": "FILE_UPLOADER", "options": []}
                                              for a in spec["attachments"]],
        "dependencies": [{"field": i["if"][0], "value": i["if"][1], "shows": i["label"]}
                         for i in spec["items"] if "if" in i],
        "statements": len(spec["statements"]), "fee": bool(spec.get("fee")),
    }


# ------------------------------------------------------------------ formaty


def write_docx(lines, path: Path) -> None:
    d = docx.Document()
    for kind, text in lines:
        if kind == "h":
            d.add_heading(text, level=1)
        elif kind == "opt":
            d.add_paragraph(f"☐ {text}")
        elif kind == "cap":
            d.add_paragraph(text).runs[0].italic = True
        else:
            d.add_paragraph(text)
    d.save(path)


def write_xlsx(lines, path: Path) -> None:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Wniosek"
    for kind, text in lines:
        if kind == "opt":
            ws.append(["☐", text])
        elif text.endswith(DOTS) and ": " in text:
            label, _, dots = text.rpartition(": ")
            ws.append([label + ":", dots])
        else:
            ws.append([text])
    ws.column_dimensions["A"].width = 90
    wb.save(path)


def write_ods(lines, path: Path) -> None:
    rows = []
    for kind, text in lines:
        cells = ["☐", text] if kind == "opt" else [text]
        rows.append("<table:table-row>" + "".join(
            f'<table:table-cell office:value-type="string"><text:p>{escape(c)}</text:p></table:table-cell>'
            for c in cells) + "</table:table-row>")
    content = (
        '<?xml version="1.0" encoding="UTF-8"?><office:document-content '
        'xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" '
        'xmlns:table="urn:oasis:names:tc:opendocument:xmlns:table:1.0" '
        'xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0" office:version="1.2"><office:body>'
        f'<office:spreadsheet><table:table table:name="Wniosek">{"".join(rows)}</table:table>'
        '</office:spreadsheet></office:body></office:document-content>')
    manifest = ('<?xml version="1.0" encoding="UTF-8"?><manifest:manifest '
                'xmlns:manifest="urn:oasis:names:tc:opendocument:xmlns:manifest:1.0" manifest:version="1.2">'
                '<manifest:file-entry manifest:full-path="/" '
                'manifest:media-type="application/vnd.oasis.opendocument.spreadsheet"/>'
                '<manifest:file-entry manifest:full-path="content.xml" manifest:media-type="text/xml"/>'
                '</manifest:manifest>')
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("mimetype", "application/vnd.oasis.opendocument.spreadsheet", compress_type=zipfile.ZIP_STORED)
        z.writestr("content.xml", content, compress_type=zipfile.ZIP_DEFLATED)
        z.writestr("META-INF/manifest.xml", manifest, compress_type=zipfile.ZIP_DEFLATED)


def docx_to_pdf(folder: Path) -> bool:
    """Konwersja wszystkich DOCX w katalogu do PDF LibreOffice'em z obrazu aplikacji (bez instalacji lokalnej)."""
    if not shutil.which("docker"):
        return False
    cmd = ["docker", "run", "--rm", "--entrypoint", "sh", "-v", f"{folder.resolve()}:/work", IMAGE, "-c",
           "cd /work && for f in *.docx; do soffice -env:UserInstallation=file:///tmp/lo --headless "
           "--convert-to pdf --outdir /work \"$f\" >/dev/null 2>&1; done"]
    return subprocess.run(cmd, check=False).returncode == 0


def scan_from_pdf(pdf: Path, out: Path, seed: int, fmt: str) -> None:
    """„Skan”: render pierwszej strony, lekki obrót, szum, rozmycie i kompresja — jak telefon/skaner."""
    import pypdfium2 as pdfium

    rnd = random.Random(seed)
    doc = pdfium.PdfDocument(pdf)
    try:
        img = doc[0].render(scale=150 / 72).to_pil().convert("L")
    finally:
        doc.close()
    img = img.rotate(rnd.uniform(-1.8, 1.8), expand=True, fillcolor=245)
    noise = Image.effect_noise(img.size, rnd.uniform(18, 30)).convert("L")
    img = Image.blend(img, noise, 0.08).filter(ImageFilter.GaussianBlur(0.6))
    buf = io.BytesIO()
    if fmt == "JPEG":
        img.save(buf, "JPEG", quality=55)
    else:
        img.save(buf, "PNG")
    out.write_bytes(buf.getvalue())


def main(dst: Path) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    dst.mkdir(parents=True, exist_ok=True)
    for spec in SPECS:
        lines = paper_lines(spec)
        base = dst / spec["id"]
        write_docx(lines, base.with_suffix(".docx"))
        shutil.copyfile(base.with_suffix(".docx"), base.with_name(base.name + "_word97").with_suffix(".doc"))
        write_xlsx(lines, base.with_suffix(".xlsx"))
        write_ods(lines, base.with_suffix(".ods"))
        (dst / f"{spec['id']}.expected.json").write_text(json.dumps(expected(spec), ensure_ascii=False, indent=2),
                                                         encoding="utf-8")
    if docx_to_pdf(dst):
        for n, spec in enumerate(SPECS):
            pdf = dst / f"{spec['id']}.pdf"
            if pdf.exists():
                scan_from_pdf(pdf, dst / f"{spec['id']}_skan.png", n, "PNG")
                scan_from_pdf(pdf, dst / f"{spec['id']}_skan.jpg", 100 + n, "JPEG")
    else:
        print("Uwaga: brak Dockera/obrazu — pominięto PDF i skany.")
    files = sorted(p.name for p in dst.iterdir() if not p.name.endswith(".expected.json"))
    print(f"Formularze: {len(SPECS)}, plików wejściowych: {len(files)} → {dst}")
    return 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1]) if len(sys.argv) > 1 else Path("../testy/formularze")))
