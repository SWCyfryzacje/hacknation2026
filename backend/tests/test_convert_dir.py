import importlib.util
import json
from pathlib import Path

from app.analysis.model import FieldSpec, FormAnalysis, Kind, PageSpec, ProposedDictionary, SectionSpec
from app.config import Settings
from tests.conftest import make_docx

_spec = importlib.util.spec_from_file_location("convert_dir", Path(__file__).parents[1] / "scripts" / "convert_dir.py")
convert_dir = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(convert_dir)


def fake_llm(document, *, client, **kwargs):
    """Atrapa modelu: liczy „wywołania” tak jak prawdziwy klient i proponuje słownik."""
    client.usage["calls"] += 1
    client.usage["prompt_tokens"] += 1000
    field = FieldSpec("Rasa psa", Kind.SELECT, dictionary="Rasy psów")
    return FormAnalysis(title="Wniosek o test", pages=[PageSpec("Pies", [SectionSpec("Dane psa", [field])])],
                        proposed_dictionaries=[ProposedDictionary("Rasy psów", "opis", ["Akbash"], ["Rasa psa"])],
                        analyzer="llm")


def test_batch_respects_llm_call_limit_and_writes_dictionaries(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr("app.service.analyze_with_llm", fake_llm)
    src, dst = tmp_path / "in", tmp_path / "out"
    src.mkdir()
    for name in ("a", "b", "c"):
        (src / f"{name}.docx").write_bytes(make_docx(["WNIOSEK O TEST", "Liczba osób: ……………"]))

    settings = Settings(auth_enabled=False, edenai_api_key="klucz-testowy")
    assert convert_dir.main(src, dst, max_llm_calls=2, settings=settings) == 0

    out = capsys.readouterr().out
    assert "STOP" in out and "wywołania modelu: 2" in out
    assert sorted(p.name for p in dst.glob("*.docx.json")) == ["a.docx.json", "b.docx.json"]
    dictionaries = json.loads((dst / "a.docx.slowniki.json").read_text(encoding="utf-8"))
    assert dictionaries == {"dictionaries": [{"name": "Rasy psów", "description": "opis", "values": ["Akbash"],
                                              "used_by": ["Rasa psa"]}]}
    report = json.loads((dst / "a.docx.report.json").read_text(encoding="utf-8"))
    assert report["analysis"]["llmUsage"]["calls"] == 1
