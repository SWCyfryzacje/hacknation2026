import copy

import pytest

from app.analysis.llm import EXAMPLE_OUTPUT
from app.generator.checks import check_form
from app.mcp_server import find_personal_data, pobierz_standardy, sprawdz_formularz, zbuduj_formularz


def test_standards_describe_schema_and_rules():
    s = pobierz_standardy()
    assert "pages" in s["schematOpisu"]["properties"] and "REQUIRED" in s["walidatory"]
    assert s["przykladOpisu"]["title"] and "Kraje" in s["slowniki"] and "MLPZ.name" in s["daneInicjalne"]


def test_build_form_from_external_description_is_compliant():
    result = zbuduj_formularz(copy.deepcopy(EXAMPLE_OUTPUT))
    assert result["problemy"] == []
    form = result["formularz"]
    assert form["title"] == EXAMPLE_OUTPUT["title"]
    assert [t["type"] for t in form["tabs"]][-1] == "FINISH"
    assert check_form(form) == []
    assert zbuduj_formularz(copy.deepcopy(EXAMPLE_OUTPUT))["formularz"] == form  # deterministycznie


def test_invalid_description_returns_schema_errors():
    result = zbuduj_formularz({"title": "Wniosek"})  # brak `pages`
    assert "blad" in result and result["szczegoly"]


@pytest.mark.parametrize(("text", "kind"), [
    ("PESEL: 44051401359", "numer PESEL"), ("NIP 526-025-09-95", "numer NIP"),
    ("konto PL61 1090 1014 0000 0712 1981 2874", "numer rachunku bankowego"),
    ("dowód ABC123456", "seria i numer dokumentu tożsamości"), ("jan.kowalski@example.pl", "adres e-mail"),
    ("tel. 600 100 200", "numer telefonu"),
])
def test_guard_detects_personal_data(text, kind):
    assert kind in find_personal_data({"pages": [{"title": text}]})


def test_guard_allows_blank_form_labels():
    blank = {"label": "Numer PESEL", "description": "Wpisz 11 cyfr numeru PESEL i adres e-mail", "x": "12345678901"}
    assert find_personal_data(blank) == []  # etykiety i nieprawidłowa suma kontrolna to nie dane osobowe


def test_tools_refuse_personal_data_and_point_to_gov_app():
    opis = copy.deepcopy(EXAMPLE_OUTPUT)
    opis["pages"][0]["sections"][0]["fields"][0]["description"] = "Jan Kowalski, PESEL 44051401359"
    result = zbuduj_formularz(opis)
    assert result["odmowa"] is True and "PESEL" in result["powod"] and result["bezpiecznaAplikacja"]
    assert "formularz" not in result
    assert sprawdz_formularz({"tabs": [], "note": "tel. 600 100 200"})["odmowa"] is True


def test_check_form_tool():
    form = zbuduj_formularz(copy.deepcopy(EXAMPLE_OUTPUT))["formularz"]
    assert sprawdz_formularz(form) == {"problemy": []}
    assert "blad" in sprawdz_formularz({"title": "x"})
