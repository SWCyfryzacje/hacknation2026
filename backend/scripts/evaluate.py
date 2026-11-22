"""Ocena wyników względem klucza odpowiedzi (formularze wygenerowane, testy/formularze/*.expected.json).

    python scripts/evaluate.py [--keys ../testy/formularze] [--results ../wyniki/testy/02-nowe-formularze]

Dla każdego wyniku `T<n>…json` w katalogu modelu porównuje część specyficzną dla wniosku (sekcje predefiniowane
— strona „Dane”, kontakt, zgody, strona końcowa — są identyczne z założenia i pomijane) z kluczem:
  * tytuł i urząd, warianty wnioskodawcy (osoba / podmiot),
  * pola: kompletność (ile oczekiwanych pól znaleziono) i precyzja (ile znalezionych jest oczekiwanych) —
    etykiety dopasowywane po podobieństwie (model może je sformułować inaczej),
  * zgodność typów (dokładna oraz „zgodna”: TEXT_FIELD≈TEXTAREA, RADIO≈SELECT≈CHECKBOX), opcje pól wyboru,
  * zależności: czy pole pokazywane warunkowo ma warunek `states` wskazujący pole sterujące i wartość.
Wynik: `ocena.md` i `ocena.json` w katalogu wyników (bez wywołań modeli).
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
COMPATIBLE = [{"TEXT_FIELD", "TEXTAREA"}, {"RADIO", "SELECT", "CHECKBOX"}, {"NUMBER"}, {"DATEPICKER"},
              {"FILE_UPLOADER"}]
STOP = {"w", "z", "na", "do", "o", "i", "lub", "dla", "od", "jakie", "podaj", "przypadku", "wyboru", "numer", "nr"}
PREDEFINED_TABS = {"dane", "strona koncowa"}


def norm(text: str) -> str:
    text = unicodedata.normalize("NFKD", (text or "").replace("ł", "l").replace("Ł", "L"))
    text = text.encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def similarity(a: str, b: str) -> float:
    na, nb = norm(a), norm(b)
    ta, tb = set(na.split()) - STOP, set(nb.split()) - STOP
    overlap = len(ta & tb) / max(min(len(ta), len(tb)), 1) if ta and tb else 0.0
    return max(SequenceMatcher(None, na, nb).ratio(), overlap * 0.95)


def compatible(a: str, b: str) -> bool:
    return a == b or any(a in g and b in g for g in COMPATIBLE)


def domain_fields(form: dict) -> list[dict]:
    """Pola części specyficznej dla wniosku (bez stron predefiniowanych i bloków tekstu)."""
    out = []
    for tab in form.get("tabs", []):
        sections = [q["field"] for q in tab.get("questions", [])]
        if norm(tab.get("title", "")) in PREDEFINED_TABS or tab.get("type") == "FINISH":
            continue
        if any(s.get("techName") == "dane_do_kontaktu" for s in sections):
            continue  # strona kontaktu / zgód / opłaty
        for s in sections:
            for c in s.get("repeatingSectionGrid") or []:
                f = c["field"]
                if f.get("type") in ("TEXT_BLOCK", "INFO_SECTION"):
                    continue
                queries = [st.get("query", "") for st in (f.get("states") or []) + (s.get("states") or [])]
                out.append({"label": f.get("title") or f.get("techName", ""), "type": f.get("type"),
                            "tech": f.get("techName"), "options": [o.get("name", "") for o in f.get("options") or []],
                            "queries": queries})
    return out


def match_fields(expected: list[dict], found: list[dict], threshold: float = 0.6) -> dict[int, int]:
    """Zachłanne dopasowanie oczekiwane → znalezione po malejącym podobieństwie etykiet."""
    pairs = sorted(((similarity(e["label"], f["label"]), i, j) for i, e in enumerate(expected)
                    for j, f in enumerate(found)), reverse=True)
    used_e, used_f, result = set(), set(), {}
    for score, i, j in pairs:
        if score < threshold:
            break
        if i not in used_e and j not in used_f:
            used_e.add(i), used_f.add(j)
            result[i] = j
    return result


def applicant(form: dict) -> dict[str, bool]:
    for tab in form.get("tabs", []):
        for q in tab.get("questions", []):
            for c in q["field"].get("repeatingSectionGrid") or []:
                f = c["field"]
                if f.get("techName") == "wybierz_w_czyim_imieniu_wnioskujesz":
                    names = {o.get("name") for o in f.get("options") or []}
                    return {"person": "Swoim" in names, "company": any("prawnej" in (n or "") for n in names)}
    return {"person": False, "company": False}


def authority(form: dict) -> str:
    first = form.get("tabs", [{}])[0]
    for q in first.get("questions", []):
        for c in q["field"].get("repeatingSectionGrid") or []:
            if c["field"].get("techName") in ("nazwa_urzedu", "nazwa_organu"):
                return str(c["field"].get("defaultValue") or "")
    return ""


def evaluate(form: dict, key: dict) -> dict:
    found = domain_fields(form)
    expected = key["fields"]
    matched = match_fields(expected, found)
    types_exact = sum(found[j]["type"] == expected[i]["kind"] for i, j in matched.items())
    types_ok = sum(compatible(found[j]["type"], expected[i]["kind"]) for i, j in matched.items())
    opt_total = opt_hit = 0
    for i, j in matched.items():
        for option in expected[i]["options"]:
            opt_total += 1
            opt_hit += any(similarity(option, o) >= 0.7 for o in found[j]["options"])
    deps_hit = 0
    by_label = {e["label"]: i for i, e in enumerate(expected)}
    for dep in key["dependencies"]:
        shows, ctrl = by_label.get(dep["shows"]), by_label.get(dep["field"])
        if shows in matched and ctrl in matched:
            f_shows, f_ctrl = found[matched[shows]], found[matched[ctrl]]
            deps_hit += any(f_ctrl["tech"] and f"'{f_ctrl['tech']}'" in q and norm(dep["value"]) in norm(q)
                            for q in f_shows["queries"])
    app = applicant(form)
    return {
        "title": similarity(form.get("title", ""), key["title"]) >= 0.8,
        "authority": similarity(authority(form), key["authority"]) >= 0.8,
        "applicant": app == key["applicant"],
        "expected": len(expected), "found": len(found), "matched": len(matched),
        "recall": len(matched) / len(expected) if expected else 1.0,
        "precision": len(matched) / len(found) if found else 0.0,
        "typesExact": types_exact, "typesCompatible": types_ok,
        "options": opt_hit, "optionsTotal": opt_total,
        "dependencies": deps_hit, "dependenciesTotal": len(key["dependencies"]),
        "missing": [expected[i]["label"] for i in range(len(expected)) if i not in matched],
    }


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Ocena wyników względem klucza odpowiedzi.")
    ap.add_argument("--keys", type=Path, default=ROOT / "testy" / "formularze")
    ap.add_argument("--results", type=Path, default=ROOT / "wyniki" / "testy" / "02-nowe-formularze")
    args = ap.parse_args()
    keys = {p.name.split(".")[0]: json.loads(p.read_text(encoding="utf-8")) for p in args.keys.glob("T*.expected.json")}

    per_file, summary = [], []
    for model_dir in sorted(d for d in args.results.iterdir() if d.is_dir()):
        rows = []
        for path in sorted(model_dir.glob("T*.json")):
            if path.name.endswith((".report.json", ".slowniki.json")):
                continue
            key = keys.get(re.match(r"(T\d+)", path.name).group(1))
            report_path = path.with_name(path.name[:-5] + ".report.json")
            report = json.loads(report_path.read_text(encoding="utf-8")) if report_path.exists() else {}
            if not key or report.get("analysis", {}).get("analyzer") != "llm":
                continue  # oceniamy tylko wyniki modelu (nie awaryjną analizę regułową)
            r = evaluate(json.loads(path.read_text(encoding="utf-8")), key) | {"file": path.name,
                                                                              "model": model_dir.name}
            rows.append(r)
            per_file.append(r)
        if not rows:
            continue
        def tot(k: str, rows: list[dict] = rows) -> float:
            return sum(r[k] for r in rows)

        summary.append({
            "model": model_dir.name, "files": len(rows),
            "recall": statistics.mean(r["recall"] for r in rows),
            "precision": statistics.mean(r["precision"] for r in rows),
            "types": tot("typesCompatible") / max(tot("matched"), 1),
            "typesExact": tot("typesExact") / max(tot("matched"), 1),
            "options": tot("options") / max(tot("optionsTotal"), 1),
            "dependencies": tot("dependencies") / max(tot("dependenciesTotal"), 1),
            "title": tot("title") / len(rows), "authority": tot("authority") / len(rows),
            "applicant": tot("applicant") / len(rows),
        })

    lines = ["# Ocena względem klucza odpowiedzi (formularze wygenerowane T1–T8)", "",
             "Generator: `backend/scripts/evaluate.py`. Klucz: `testy/formularze/T*.expected.json`. "
             "Oceniana jest część "
             "specyficzna dla wniosku; etykiety dopasowywane po podobieństwie. Tylko wyniki modelu językowego.", "",
             "| Model | Plików | Kompletność pól | Precyzja pól | Typy (zgodne / dokładne) | Opcje wyboru | Zależności "
             "| Tytuł | Urząd | Wnioskodawca |", "|---|---|---|---|---|---|---|---|---|---|"]
    for s in summary:
        lines.append(f"| {s['model']} | {s['files']} | {s['recall']:.0%} | {s['precision']:.0%} | {s['types']:.0%} / "
                     f"{s['typesExact']:.0%} | {s['options']:.0%} | {s['dependencies']:.0%} | {s['title']:.0%} | "
                     f"{s['authority']:.0%} | {s['applicant']:.0%} |")
    lines += ["", "## Szczegóły (pliki)", "",
              "| Model | Plik | Pola (znalezione / oczekiwane) | Kompletność | Precyzja | Zależności "
              "| Brakujące pola |",
              "|---|---|---|---|---|---|---|"]
    for r in per_file:
        lines.append(f"| {r['model']} | {r['file']} | {r['matched']} / {r['expected']} (wszystkich {r['found']}) | "
                     f"{r['recall']:.0%} | {r['precision']:.0%} | {r['dependencies']}/{r['dependenciesTotal']} | "
                     f"{', '.join(r['missing']) or '—'} |")
    lines += ["", "## Uwagi do interpretacji", "",
              "- Pola z potwierdzeniem opłaty (T3, T5) generator umieszcza w sekcji opłat na stronie „Opłaty, kontakt i zgody”, "
              "którą ocena pomija jako predefiniowaną — ich „brak” to głównie wynik fałszywie ujemny.",
              "- Wnioskodawca: dla T1 (informacja publiczna) i T4 (podatek od nieruchomości) modele dopuszczają także podmiot "
              "(firmę), a klucz — tylko osobę; to rozbieżność interpretacji, a nie oczywisty błąd.",
              "- Formularze wygenerowane mają proste, jednoznaczne etykiety, więc modele często je powtarzają — prawdziwe "
              "formularze (BIP, materiały wyzwania) są trudniejsze i nie mają klucza odpowiedzi."]
    (args.results / "ocena.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (args.results / "ocena.json").write_text(json.dumps({"summary": summary, "files": per_file}, ensure_ascii=False,
                                                        indent=2), encoding="utf-8")
    print("\n".join(lines[:6 + len(summary)]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
