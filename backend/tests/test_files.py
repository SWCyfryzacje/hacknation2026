import pytest

from app.errors import EmptyFile, FileTooLarge, InvalidFileName, UnsupportedFileType
from app.files.formats import Mime
from app.files.mime import detect_mime
from app.files.validation import validate_filename, validate_upload
from tests.conftest import PDF_BYTES, make_docx, make_image, make_ods, make_xlsx

LIMITS = {"max_size": 1024 * 1024, "max_uncompressed": 50 * 1024 * 1024}


@pytest.mark.parametrize(("data", "mime"), [
    (PDF_BYTES, Mime.PDF),
    (make_image("PNG"), Mime.PNG),
    (make_image("JPEG"), Mime.JPEG),
    (make_docx(["test"]), Mime.DOCX),
    (make_xlsx([["a", "b"]]), Mime.XLSX),
    (make_ods([["a"]]), Mime.ODS),
])
def test_detects_supported_formats(data, mime):
    assert detect_mime(data) is mime


@pytest.mark.parametrize("data", [b"", b"hello world", b"GIF89a....", b"PK\x03\x04garbage", b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1x"])
def test_rejects_unknown_content(data):
    assert detect_mime(data) is None


@pytest.mark.parametrize("name", ["a;b.pdf", "a:b.pdf", "a>b.pdf", "a<b.pdf", "a/b.pdf", "a\\b.pdf", "a|b.pdf",
                                  "a'b.pdf", "a*b.pdf", "a%b.pdf", "a$b.pdf", "x" * 247 + ".pdf", "", "  "])
def test_invalid_filenames(name):
    with pytest.raises(InvalidFileName):
        validate_filename(name)


def test_filename_with_polish_letters_and_spaces_is_ok():
    assert validate_filename("Wniosek o zwrot opłaty (1).pdf")
    assert validate_filename("x" * 246 + ".pdf")  # dokładnie 250 znaków


def test_extension_must_match_content():
    with pytest.raises(UnsupportedFileType, match="nie pasuje"):
        validate_upload("skan.pdf", make_image("PNG"), None, **LIMITS)


def test_doc_and_docx_are_one_word_format():
    """Pliki .doc z zawartością DOCX występują w materiałach wyzwania — przetwarzamy je wg zawartości."""
    docx_bytes = make_docx(["test"])
    assert validate_upload("wniosek.DOC", docx_bytes, "application/msword", **LIMITS).mime is Mime.DOCX
    with pytest.raises(UnsupportedFileType):
        validate_upload("wniosek.doc", make_image("PNG"), None, **LIMITS)
    with pytest.raises(UnsupportedFileType):
        validate_upload("arkusz.xlsx", docx_bytes, None, **LIMITS)


def test_unsupported_extension():
    with pytest.raises(UnsupportedFileType, match="rozszerzenie"):
        validate_upload("plik.txt", b"abc", None, **LIMITS)


def test_declared_type_must_match():
    with pytest.raises(UnsupportedFileType, match="Zadeklarowany"):
        validate_upload("a.png", make_image("PNG"), "application/pdf", **LIMITS)


def test_generic_and_alias_declared_types_are_accepted():
    png = make_image("PNG")
    assert validate_upload("a.png", png, "application/octet-stream", **LIMITS).mime is Mime.PNG
    assert validate_upload("a.jpg", make_image("JPEG"), "image/jpg", **LIMITS).mime is Mime.JPEG
    assert validate_upload("A.PNG", png, "image/png; charset=binary", **LIMITS).mime is Mime.PNG


def test_size_limits():
    with pytest.raises(FileTooLarge):
        validate_upload("a.pdf", PDF_BYTES + b" " * 2000, None, max_size=1000, max_uncompressed=10**9)
    with pytest.raises(EmptyFile):
        validate_upload("a.pdf", b"", None, **LIMITS)


def test_zip_bomb_guard():
    with pytest.raises(FileTooLarge, match="rozpakowaniu"):
        validate_upload("a.docx", make_docx(["x" * 10_000]), None, max_size=10**7, max_uncompressed=1000)
