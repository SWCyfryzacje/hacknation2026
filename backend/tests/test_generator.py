import pytest

from app.analysis.model import (
    Applicant,
    Condition,
    FieldSpec,
    FormAnalysis,
    Kind,
    PageSpec,
    SectionSpec,
)
from app.analysis.rules import analyze
from app.config import FinishComponent, ValidationMode
from app.extraction.word import extract_docx
from app.generator.builder import BuildOptions, build_form
from app.generator.checks import check_form
from app.generator.fields import slugify
from tests.conftest import load_json, reference_jsons


def _analysis(**kw) -> FormAnalysis:
    choice = FieldSpec("Rodzaj", Kind.RADIO, options=["Tak", "Inne"])
    other = FieldSpec("Inne – podaj jakie", Kind.TEXTAREA, show_if=Condition(choice, "Inne"))
    defaults = dict(title="Wniosek o test", authority="Wójt Gminy Test", authority_is_organ=True,
                    pages=[PageSpec("Przedmiot wniosku", [SectionSpec("Szczegóły", [choice, other])])])
    return FormAnalysis(**(defaults | kw))


def _fields(form):
    for tab in form["tabs"]:
        for q in tab["questions"]:
            yield tab, q["field"]
            for c in q["field"]["repeatingSectionGrid"]:
                yield tab, c["field"]


def test_rules_analysis_of_sample(sample_docx):
    a = analyze(extract_docx(sample_docx), fallback_title="x.docx")
    assert a.title == "Wniosek o wydanie zaświadczenia"
    assert a.authority == "Urząd Miasta i Gminy Młynary" and not a.authority_is_organ
    fields = {f.label: f for p in a.pages for s in p.sections for f in s.fields}
    choice = next(f for f in fields.values() if f.kind is Kind.RADIO)
    assert choice.options == ["Okresie posiadania gospodarstwa rolnego", "Nieposiadaniu gospodarstwa rolnego", "Inne"]
    assert fields["Inne – podaj jakie"].show_if.field is choice
    assert fields["Przewidywana ilość egzemplarzy"].kind is Kind.NUMBER
    assert fields["Termin od"].kind is Kind.DATE and fields["Termin do"].kind is Kind.DATE
    assert not any("PESEL" in label or "imię" in label.lower() for label in fields)  # dane wnioskodawcy → sekcje stałe
    assert a.fee_info == ["Opłata za wydanie zaświadczenia wynosi 17 zł"]


def test_built_form_follows_rules_and_reference_layout():
    form = build_form(_analysis(), seed="s")
    assert check_form(form) == []
    titles = [t["title"] for t in form["tabs"]]
    assert titles == ["Dane", "Przedmiot wniosku", "Kontakt i zgody", "Strona końcowa"]
    first = form["tabs"][0]["questions"][0]["field"]
    assert first["techName"] == "organ_do_ktorego_jest_skladany_wniosek"
    authority = first["repeatingSectionGrid"][0]["field"]
    assert authority["defaultValue"] == "Wójt Gminy Test" and authority["readOnly"] is True
    # kolejność kluczy jak w eksportach z systemu
    assert list(authority)[:5] == ["id", "type", "techName", "title", "description"]
    assert list(authority)[-3:] == ["states", "questionOrder", "tooltipMessage"]


def test_condition_points_to_controller():
    form = build_form(_analysis(), seed="s")
    other = next(f for _, f in _fields(form) if f["title"] == "Inne – podaj jakie")
    query = other["states"][0]["query"]
    assert query.startswith('("Inne" in tabs[\'Przedmiot wniosku\' in title]')
    assert "['rodzaj' in field.techName]" in query


def test_applicant_variants_control_predefined_sections():
    person = build_form(_analysis(applicant=Applicant(person=True, company=False)), seed="s")
    company = build_form(_analysis(applicant=Applicant(person=False, company=True)), seed="s")
    p_names = {f["techName"] for _, f in _fields(person)}
    c_names = {f["techName"] for _, f in _fields(company)}
    assert "dane_innej_osoby" in p_names and "dane_podmiotu" not in p_names
    assert "dane_podmiotu" in c_names and "dane_innej_osoby" not in c_names
    assert check_form(person) == [] and check_form(company) == []


def test_output_is_deterministic():
    assert build_form(_analysis(), seed="abc") == build_form(_analysis(), seed="abc")
    assert build_form(_analysis(), seed="abc") != build_form(_analysis(), seed="xyz")


def test_options_validation_and_finish_component():
    form = build_form(_analysis(), seed="s", options=BuildOptions(FinishComponent.INFO_SECTION, ValidationMode.EMPTY))
    assert all(f["validation"] == [] for _, f in _fields(form))
    finish = form["tabs"][-1]["questions"][0]["field"]["repeatingSectionGrid"][0]["field"]
    assert finish["type"] == "INFO_SECTION"
    pesel = next(f for _, f in _fields(build_form(_analysis(), seed="s")) if f["techName"] == "numer_pesel")
    assert pesel["validation"] == ["REQUIRED", "PESEL"]
    assert pesel["defaultValue"] == "MLPZ.pesel" and pesel["defaultValueType"] == "EXTERNAL_SYSTEM"


def test_initial_data_and_dictionary_fields():
    fields = [FieldSpec("Data urodzenia", Kind.DATE, initial_data="PESEL.birthDate"),
              FieldSpec("Kraj pochodzenia", Kind.TEXT, dictionary="Kraje")]
    form = build_form(_analysis(pages=[PageSpec("Dane dodatkowe", [SectionSpec("Osoba", fields)])]), seed="s")
    by_title = {f["title"]: f for _, f in _fields(form)}
    assert by_title["Data urodzenia"]["readOnly"] is True
    assert by_title["Kraj pochodzenia"]["type"] == "SELECT"
    assert by_title["Kraj pochodzenia"]["dictionaryName"] == "Kraje"
    assert check_form(form) == []


def test_slugify_polish():
    assert slugify("Numer ewidencyjny działki – Łódź") == "numer_ewidencyjny_dzialki_lodz"


def test_checker_detects_violations():
    form = build_form(_analysis(), seed="s")
    form["tabs"][-1]["type"] = "MAIN"
    form["tabs"][1]["questions"][0]["field"]["repeatingSectionGrid"][1]["field"]["states"][0]["query"] = \
        "(\"x\" in tabs['Nie ma' in title].questions['brak' in field.techName])"
    issues = check_form(form)
    assert any("FINISH" in i for i in issues)
    assert any("nieistniejącej strony" in i for i in issues)


@pytest.mark.parametrize("path", reference_jsons(), ids=lambda p: p.name)
def test_reference_exports_pass_checker(path):
    """Checker nie może być surowszy niż prawdziwy system."""
    assert check_form(load_json(path)) == []
