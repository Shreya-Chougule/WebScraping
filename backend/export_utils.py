
"""
Export utilities for ScrapeScout.

Provides dependency-free CSV/XLSX support helpers, including spreadsheet
formula-injection mitigation and safe OpenXML worksheet-name handling.
"""

import io
import re
import zipfile
import xml.sax.saxutils
from datetime import datetime
from typing import Any, Dict, List

try:
    from backend.security import sanitize_csv_cell
except ImportError:
    from security import sanitize_csv_cell


_INVALID_XML_CHARS = re.compile(
    "[\\x00-\\x08\\x0b\\x0c\\x0e-\\x1f]"
)
_INVALID_SHEET_CHARS = re.compile(r'[\\/*?:\[\]]')


def col_to_letter(col_idx: int) -> str:
    """Convert a 1-based column index to an Excel column letter."""
    if col_idx < 1:
        raise ValueError("Column index must be greater than zero.")

    letters = ""
    while col_idx > 0:
        col_idx, remainder = divmod(col_idx - 1, 26)
        letters = chr(65 + remainder) + letters
    return letters


def _clean_xml_text(value: Any) -> str:
    """Convert a value to text and remove XML 1.0 forbidden control chars."""
    text = "" if value is None else str(value)
    return _INVALID_XML_CHARS.sub("", text)


def _safe_sheet_name(sheet_name: str) -> str:
    """Return a valid, XML-safe Excel worksheet name."""
    name = _INVALID_SHEET_CHARS.sub("_", str(sheet_name))
    name = _clean_xml_text(name).strip().strip("'")
    name = name[:31].strip().strip("'")
    return name or "Projects"


def _inline_string_cell(cell_ref: str, value: Any) -> str:
    """Build a safe inline-string worksheet cell."""
    clean_value = _clean_xml_text(value)
    escaped_value = xml.sax.saxutils.escape(clean_value)

    # Preserve leading/trailing whitespace when Excel reads the cell.
    return (
        f'      <c r="{cell_ref}" t="inlineStr">'
        f'<is><t xml:space="preserve">{escaped_value}</t></is></c>\n'
    )


def generate_projects_xlsx(
    columns: List[str],
    projects: List[Dict[str, Any]],
    sheet_name: str = "Projects",
) -> bytes:
    """Generate an XLSX workbook in memory using only the standard library."""
    buffer = io.BytesIO()
    safe_sheet_name = _safe_sheet_name(sheet_name)
    escaped_sheet_name = xml.sax.saxutils.escape(safe_sheet_name, {'"': "&quot;"})

    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "[Content_Types].xml",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">\n'
            '  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>\n'
            '  <Default Extension="xml" ContentType="application/xml"/>\n'
            '  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>\n'
            '  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>\n'
            '</Types>',
        )

        archive.writestr(
            "_rels/.rels",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n'
            '  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>\n'
            '</Relationships>',
        )

        archive.writestr(
            "xl/_rels/workbook.xml.rels",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n'
            '  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>\n'
            '</Relationships>',
        )

        archive.writestr(
            "xl/workbook.xml",
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">\n'
            '  <sheets>\n'
            f'    <sheet name="{escaped_sheet_name}" sheetId="1" r:id="rId1"/>\n'
            '  </sheets>\n'
            '</workbook>',
        )

        sheet_parts = [
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n',
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">\n',
            '  <sheetData>\n',
            '    <row r="1">\n',
        ]

        for col_idx, col_name in enumerate(columns, start=1):
            cell_ref = f"{col_to_letter(col_idx)}1"
            sheet_parts.append(_inline_string_cell(cell_ref, col_name))

        sheet_parts.append('    </row>\n')

        for row_idx, project in enumerate(projects, start=2):
            sheet_parts.append(f'    <row r="{row_idx}">\n')

            for col_idx, col_name in enumerate(columns, start=1):
                cell_ref = f"{col_to_letter(col_idx)}{row_idx}"
                raw_value = project.get(col_name)
                safe_value = sanitize_csv_cell(raw_value)
                sheet_parts.append(_inline_string_cell(cell_ref, safe_value))

            sheet_parts.append('    </row>\n')

        sheet_parts.append('  </sheetData>\n</worksheet>')

        archive.writestr(
            "xl/worksheets/sheet1.xml",
            "".join(sheet_parts),
        )

    buffer.seek(0)
    return buffer.getvalue()


def get_export_filename(
    extension: str,
    prefix: str = "scrapescout_projects",
) -> str:
    """Generate a timestamped export filename."""
    safe_prefix = re.sub(r"[^A-Za-z0-9_-]", "_", prefix).strip("_")
    safe_prefix = safe_prefix or "scrapescout_projects"

    ext = re.sub(r"[^A-Za-z0-9]", "", extension.lstrip(".")).lower()
    if not ext:
        raise ValueError("A valid file extension is required.")

    date_str = datetime.now().strftime("%Y-%m-%d")
    return f"{safe_prefix}_{date_str}.{ext}"
