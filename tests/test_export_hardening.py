
import io
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from security import sanitize_csv_cell
from export_utils import generate_projects_xlsx, get_export_filename


def test_csv_sanitizer_detects_formula_after_leading_whitespace():
    values = [
        " =1+1",
        "  +SUM(A1:A2)",
        "\t=cmd",
        "\r@SUM(A1)",
        "\n-1+1",
    ]

    for value in values:
        assert sanitize_csv_cell(value).startswith("'")


def test_csv_sanitizer_preserves_normal_text():
    assert sanitize_csv_cell("Python Developer") == "Python Developer"
    assert sanitize_csv_cell("https://example.com") == "https://example.com"
    assert sanitize_csv_cell(None) == ""


def test_csv_sanitizer_handles_lists_and_dictionaries():
    assert sanitize_csv_cell(["Python", "FastAPI"]) == '["Python", "FastAPI"]'
    assert sanitize_csv_cell({"role": "developer"}) == '{"role": "developer"}'


def test_xlsx_sheet_name_is_xml_escaped_and_valid():
    content = generate_projects_xlsx(
        columns=["title"],
        projects=[{"title": "Sample project"}],
        sheet_name='Sales & "Projects"',
    )

    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        workbook_xml = archive.read("xl/workbook.xml")

    root = ET.fromstring(workbook_xml)
    namespace = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    sheet = root.find(".//x:sheet", namespace)

    assert sheet is not None
    assert sheet.attrib["name"] == 'Sales & "Projects"'


def test_xlsx_sheet_name_removes_invalid_characters_and_limits_length():
    content = generate_projects_xlsx(
        columns=["title"],
        projects=[],
        sheet_name="Bad/Name:*?[]'VeryLongWorksheetName",
    )

    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        workbook_xml = archive.read("xl/workbook.xml")

    root = ET.fromstring(workbook_xml)
    namespace = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    sheet = root.find(".//x:sheet", namespace)

    assert sheet is not None
    assert len(sheet.attrib["name"]) <= 31
    assert not any(char in sheet.attrib["name"] for char in r'\/:*?[]')


def test_xlsx_cell_content_is_xml_escaped_and_formula_safe():
    malicious = "  =HYPERLINK('https://example.com','click')"
    content = generate_projects_xlsx(
        columns=["title"],
        projects=[{"title": malicious}],
    )

    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        worksheet_xml = archive.read("xl/worksheets/sheet1.xml")

    root = ET.fromstring(worksheet_xml)
    namespace = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    cell = root.find(".//x:sheetData/x:row[@r='2']/x:c", namespace)

    assert cell is not None
    assert cell.attrib["t"] == "inlineStr"
    value = cell.find(".//x:t", namespace)
    assert value is not None
    assert value.text == "'" + malicious


def test_xlsx_removes_invalid_xml_control_characters():
    content = generate_projects_xlsx(
        columns=["title"],
        projects=[{"title": "Python\x00Developer\x01"}],
    )

    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        worksheet_xml = archive.read("xl/worksheets/sheet1.xml")

    root = ET.fromstring(worksheet_xml)
    namespace = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    values = [
        element.text or ""
        for element in root.findall(".//x:t", namespace)
    ]

    assert "PythonDeveloper" in values


def test_export_filename_sanitizes_prefix_and_extension():
    filename = get_export_filename("../unsafe name", "my project/report")

    assert filename.startswith("my_project_report_")
    assert filename.endswith(".unsafe name".replace(" ", ""))
    assert "/" not in filename
    assert "\\" not in filename
