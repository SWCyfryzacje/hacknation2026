import json

import pytest

from app.ai.edenai import AIError
from app.analysis.llm import EXAMPLE_OUTPUT, analyze_with_llm
from app.analysis.model import Kind
from app.config import Settings
from app.extraction.model import ExtractedDocument, Line
from app.files.formats import Mime
from app.files.validation import ValidatedFile
from app.generator.checks import check_form
from app.service import convert
from tests.conftest import make_docx

DOC = ExtractedDocument(lines=[Line("WNIOSEK O TEST")], source_format="docx")


class FakeClient:
    def __init__(self, *answers: str) -> None:
        self.answers = list(answers)
        self.calls: list[list[dict]] = []

    def chat(self, model, messages, **kw):  # noqa: ARG002
        self.calls.append(messages)
        if not self.answers:
            raise AIError("brak odpowiedzi")
        return self.answers.pop(0)


def _answer(**overrides) -> str:
    data = json.loads(json.dumps(EXAMPLE_OUTPUT)) | overrides
    return json.dumps(data, ensure_ascii=False)


def test_llm_answer_is_mapped_to_analysis():
    fields = [{"label": "Rodzaj", "kind": "RADIO", "options": ["Tak", "Inne"]},
              {"label": "Inne – opis", "kind": "TEXTAREA", "show_if": {"field": "rodzaj", "value": "Inne"}},
              {"label": "Rasa psa", "kind": "SELECT", "dictionary": "Rasy psów agresywnych"},
              {"label": "Data urodzenia", "kind": "DATEPICKER", "initial_data": "PESEL.birthDate",
               "validators": ["PESEL", "NIEZNANY"]}]
    answer = _answer(pages=[{"title": "Pies", "sections": [{"title": "Dane psa", "fields": fields}]}],
                     proposed_dictionaries=[{"name": "Rasy psów agresywnych", "description": "d",
                                             "values": ["Akbash"], "used_by": ["Rasa psa"]}])
    a = analyze_with_llm(DOC, client=FakeClient(f"```json\n{answer}\n```"), model="m", max_chars=10_000,
                         filename="f.docx")
    f = {x.label: x for x in a.pages[0].sections[0].fields}
    assert a.analyzer == "llm"
    assert f["Inne – opis"].show_if.field is f["Rodzaj"]
    assert f["Rasa psa"].dictionary == "Rasy psów agresywnych" and f["Rasa psa"].options == []
    assert f["Data urodzenia"].initial_data == "PESEL.birthDate"
    assert f["Data urodzenia"].validators == ["PESEL"]  # nieznane walidatory odrzucone
    assert a.proposed_dictionaries[0].values == ["Akbash"]


def test_llm_gets_second_chance_after_invalid_json():
    client = FakeClient("to nie jest json", _answer())
    a = analyze_with_llm(DOC, client=client, model="m", max_chars=10_000, filename="f.docx")
    assert len(client.calls) == 2
    assert "niepoprawna" in client.calls[1][-1]["content"]
    assert client.calls[1][-2]["role"] == "user"  # ucięta odpowiedź nie jest odsyłana
    assert a.pages[0].sections[0].fields[0].label == "Miejscowość"


def test_llm_choice_without_options_degrades_to_text():
    answer = _answer(pages=[{"title": "P", "sections": [{"title": "S", "fields": [
        {"label": "Wybór", "kind": "RADIO", "options": []}]}]}])
    a = analyze_with_llm(DOC, client=FakeClient(answer), model="m", max_chars=10_000, filename="f.docx")
    assert a.pages[0].sections[0].fields[0].kind is Kind.TEXT


def test_llm_failure_raises_ai_error():
    with pytest.raises(AIError):
        analyze_with_llm(DOC, client=FakeClient("x", "y"), model="m", max_chars=10_000, filename="f.docx")


def test_service_falls_back_to_rules_when_llm_fails(monkeypatch):
    def broken(*a, **kw):
        raise AIError("HTTP 500")

    monkeypatch.setattr("app.service.analyze_with_llm", broken)
    settings = Settings(auth_enabled=False, edenai_api_key="klucz-testowy")
    data = make_docx(["WNIOSEK O TEST", "Liczba osób: ……………"])
    result = convert(ValidatedFile("w.docx", Mime.DOCX, data), settings)
    assert result.report["analysis"]["analyzer"] == "rules"
    assert any("Model językowy niedostępny" in w for w in result.report["warnings"])
    assert check_form(result.form) == []


def test_service_uses_llm_when_configured(monkeypatch):
    from app.analysis import llm

    monkeypatch.setattr("app.service.analyze_with_llm",
                        lambda doc, **kw: llm._to_analysis(llm._Answer.model_validate(EXAMPLE_OUTPUT)))
    settings = Settings(auth_enabled=False, edenai_api_key="klucz-testowy")
    result = convert(ValidatedFile("w.docx", Mime.DOCX, make_docx(["WNIOSEK"])), settings)
    assert result.report["analysis"]["analyzer"] == "llm"
    assert result.form["title"] == "Wniosek o ustalenie numeru porządkowego nieruchomości"
    assert check_form(result.form) == []


def test_client_accumulates_token_usage(monkeypatch):
    from app.ai.edenai import EdenAIClient

    client = EdenAIClient(api_key="k")
    reply = {"choices": [{"message": {"content": "{}"}}], "usage": {"prompt_tokens": 100, "completion_tokens": 40}}
    monkeypatch.setattr(EdenAIClient, "_post", lambda self, path, **kw: reply)
    client.chat("m", [])
    client.chat("m", [])
    assert client.usage == {"calls": 2, "prompt_tokens": 200, "completion_tokens": 80}


def test_client_retries_rate_limit_and_drops_unsupported_json_mode(monkeypatch):
    from app.ai.edenai import AIError, EdenAIClient

    client = EdenAIClient(api_key="k", retry_base_s=0)
    calls = []

    def fake_post(self, path, **kw):
        calls.append(kw["json"])
        if len(calls) == 1:
            raise AIError("HTTP 429: rate limit", status=429)
        if len(calls) == 2:
            raise AIError('HTTP 400: must contain "json" to use "response_format"', status=400)
        return {"choices": [{"message": {"content": "{}"}}], "usage": {}}

    monkeypatch.setattr(EdenAIClient, "_post", fake_post)
    assert client.chat("m", []) == "{}"
    assert len(calls) == 3 and "response_format" in calls[1] and "response_format" not in calls[2]


def test_client_lowers_max_tokens_to_model_limit(monkeypatch):
    from app.ai.edenai import AIError, EdenAIClient

    client = EdenAIClient(api_key="k", retry_base_s=0)
    seen = []

    def fake_post(self, path, **kw):
        seen.append(kw["json"]["max_tokens"])
        if len(seen) == 1:
            raise AIError("HTTP 400: max_new_tokens 32000 cannot be greater than max_output_tokens 25000.", status=400)
        return {"choices": [{"message": {"content": "{}"}}], "usage": {}}

    monkeypatch.setattr(EdenAIClient, "_post", fake_post)
    client.chat("m", [], max_tokens=32000)
    assert seen == [32000, 25000]


def test_client_gives_up_after_retries(monkeypatch):
    import pytest as _pytest

    from app.ai.edenai import AIError, EdenAIClient

    client = EdenAIClient(api_key="k", retry_base_s=0, max_retries=2)

    def always_limited(self, path, **kw):
        raise AIError("HTTP 429", status=429)

    monkeypatch.setattr(EdenAIClient, "_post", always_limited)
    with _pytest.raises(AIError):
        client.chat("m", [])


def test_null_lists_from_model_are_accepted():
    a = analyze_with_llm(DOC, client=FakeClient(_answer(fee_info=None, proposed_dictionaries=None)), model="m",
                         max_chars=10_000, filename="f.docx")
    assert a.fee_info == [] and a.proposed_dictionaries == []
