import importlib.util
import sys
from pathlib import Path

_spec = importlib.util.spec_from_file_location("api_batch", Path(__file__).parents[1] / "scripts" / "api_batch.py")
api_batch = importlib.util.module_from_spec(_spec)
sys.modules["api_batch"] = api_batch  # wymagane przez dataclasses przy ładowaniu z pliku
_spec.loader.exec_module(api_batch)


def _files(tmp_path, n):
    paths = []
    for i in range(n):
        p = tmp_path / f"f{i}.docx"
        p.write_bytes(f"plik {i}".encode())
        paths.append(p)
    return paths


def test_each_file_once_per_model_and_same_model_targets_share_work(tmp_path):
    files = _files(tmp_path, 4)
    a = api_batch.Target("a", "http://a", 1, model="large")
    b = api_batch.Target("b", "http://b", 1, model="large")  # ten sam model co a → dzielą pliki
    c = api_batch.Target("c", "http://c", 1, model="medium")
    registry = api_batch.Registry(tmp_path / "rejestr.json")

    jobs, skipped = api_batch.plan_jobs(files, [a, b, c], registry)

    assert skipped == 0
    assert len(jobs) == 8  # 4 pliki × 2 różne modele, a nie × 3 serwery
    assert len({j.key for j in jobs}) == 8  # żadna para plik × model się nie powtarza
    assert sum(j.target is a for j in jobs) == 2 and sum(j.target is b for j in jobs) == 2
    assert sum(j.target is c for j in jobs) == 4


def test_registry_skips_existing_pairs_across_runs(tmp_path):
    files = _files(tmp_path, 3)
    target = api_batch.Target("a", "http://a", 1, model="large")
    path = tmp_path / "rejestr.json"
    registry = api_batch.Registry(path)
    registry.put(f"{api_batch.sha256(files[0])}:large", {"status": "ok"})
    registry.put(f"{api_batch.sha256(files[1])}:large", {"status": "fallback"})  # wynik reguł → powtórzyć

    jobs, skipped = api_batch.plan_jobs(files, [target], api_batch.Registry(path))  # nowy odczyt z dysku

    assert skipped == 1
    assert sorted(j.path.name for j in jobs) == ["f1.docx", "f2.docx"]


def test_summary_table_has_times_per_model(tmp_path):
    rows = [
        {"file": "x", "target": "lokalny", "model": "large", "status": "ok", "clientSeconds": 10.0,
         "serverSeconds": 9.0, "fields": 50, "promptTokens": 100, "completionTokens": 200},
        {"file": "y", "target": "lokalny", "model": "large", "status": "ok", "clientSeconds": 30.0,
         "serverSeconds": 28.0, "fields": 60, "promptTokens": 100, "completionTokens": 200},
        {"file": "x", "target": "serwer", "model": "medium", "status": "error", "error": "timeout"},
    ]
    table = api_batch.summarize(rows, tmp_path)  # bez etykiety → podsumowanie.csv
    assert "| lokalny | `large` | 2 / 2 | 20.0 / 20.0 / 30.0 | 18.5 | 55 | 200 + 400 | 0 |" in table
    assert "| serwer | `medium` | 0 / 1 |" in table
    assert (tmp_path / "podsumowanie.csv").read_text(encoding="utf-8").startswith("file,target,model")


def test_registry_merges_writes_from_separate_processes(tmp_path):
    path = tmp_path / "rejestr.json"
    first, second = api_batch.Registry(path), api_batch.Registry(path)  # dwa „procesy” z tym samym plikiem
    first.put("a:large", {"status": "ok"})
    second.put("b:gemma", {"status": "ok"})  # nie może nadpisać wpisu pierwszego
    assert set(api_batch.Registry(path).entries) == {"a:large", "b:gemma"}
    assert not path.with_suffix(".lock").exists()
