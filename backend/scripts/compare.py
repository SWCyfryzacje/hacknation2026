"""Porównanie wygenerowanej konfiguracji z referencyjnym eksportem z systemu.

    python scripts/compare.py <wynik.json> <referencja.json>

Porównuje strony, sekcje (po nazwie technicznej) i pola (po etykiecie w obrębie sekcji) i podaje
precyzję / kompletność, typy pól oraz zależności (states).
"""

import json
import re
import sys
import unicodedata
from pathlib import Path


def norm(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.replace("ł", "l")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def flatten(form: dict) -> dict[tuple[str, str], dict]:
    """(sekcja, etykieta pola) → pole; sekcje identyfikowane tytułem, nie nazwą techniczną."""
    out = {}
    for tab in form["tabs"]:
        for q in tab["questions"]:
            sec = q["field"]
            for c in sec.get("repeatingSectionGrid") or []:
                f = c["field"]
                label = f.get("title") or f.get("techName")
                out[(norm(sec["title"]), norm(label))] = f | {"_tab": tab["title"]}
    return out


def main(ours_path: Path, ref_path: Path) -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ours = json.loads(ours_path.read_text(encoding="utf-8-sig"))
    ref = json.loads(ref_path.read_text(encoding="utf-8-sig"))
    print(f"Tytuł:   {ours['title']!r}\n  ref:   {ref['title']!r}")
    print(f"Strony:  {[t['title'] for t in ours['tabs']]}\n  ref:   {[t['title'] for t in ref['tabs']]}")

    o_sec = {norm(q['field']['title']) for t in ours['tabs'] for q in t['questions']}
    r_sec = {norm(q['field']['title']) for t in ref['tabs'] for q in t['questions']}
    print(f"Sekcje:  wspólne {len(o_sec & r_sec)}/{len(r_sec)}; brakujące: {sorted(r_sec - o_sec)}; "
          f"dodatkowe: {sorted(o_sec - r_sec)}")

    o, r = flatten(ours), flatten(ref)
    common = o.keys() & r.keys()
    by_label_o = {k[1] for k in o}
    loose = {k for k in r if k[1] in by_label_o}  # ta sama etykieta, inna sekcja
    print(f"Pola:    dokładnie {len(common)}/{len(r)} (kompletność {len(common) / len(r):.0%}, "
          f"precyzja {len(common) / max(len(o), 1):.0%}); po samej etykiecie {len(loose)}/{len(r)}")
    type_ok = sum(o[k]["type"] == r[k]["type"] for k in common)
    print(f"Typy:    zgodne {type_ok}/{len(common)}")
    for k in sorted(common):
        if o[k]["type"] != r[k]["type"]:
            print(f"   typ  {k[0]} / {k[1]}: {o[k]['type']} ≠ ref {r[k]['type']}")
    cond_o = sum(bool(f.get("states")) for f in o.values())
    cond_r = sum(bool(f.get("states")) for f in r.values())
    print(f"Warunki: pola z states — wynik {cond_o}, ref {cond_r}")
    missing = sorted(r.keys() - o.keys())
    if missing:
        print("Brakujące pola (sekcja / etykieta):")
        for k in missing:
            print(f"   - {k[0]} / {k[1]}  [{r[k]['type']}]")
    extra = sorted(o.keys() - r.keys())
    if extra:
        print("Dodatkowe pola:")
        for k in extra:
            print(f"   + {k[0]} / {k[1]}  [{o[k]['type']}]")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(Path(sys.argv[1]), Path(sys.argv[2]))
