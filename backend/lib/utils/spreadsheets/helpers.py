"""Spreadsheet and CSV helpers — parsing, transformation, comparison, and I/O."""

import csv
import html
import io
import json
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, TextIO, cast

from validator_collection import is_email


@dataclass
class TabInfo:
    """Metadata for a sheet tab."""

    gid: int
    title: str
    row_count: int | None


# ── Row / cell access ───────────────────────────────────────────────────────


def get_cell(row: list[str], index: int, default: str = "") -> str:
    """Safely get a stripped cell value, or ``default`` if missing/empty."""
    if index < len(row) and row[index]:
        return row[index].strip()
    return default


def rows_to_dicts(
    rows: list[list[str]],
    headers: list[str] | None = None,
    skip_header: bool = True,
) -> list[dict[str, str]]:
    """Convert rows to dicts keyed by header names (headers preserve casing)."""
    if headers is None:
        if not rows:
            return []
        headers = rows[0]
        data_rows = rows[1:] if skip_header else rows
    else:
        data_rows = rows

    result: list[dict[str, str]] = []
    for row in data_rows:
        record = {header: get_cell(row, i) for i, header in enumerate(headers)}
        result.append(record)
    return result


def filter_blank_rows(
    rows: list[list[str]],
    required_columns: list[int] | None = None,
) -> list[list[str]]:
    """Drop rows that are blank (all columns, or only ``required_columns``)."""
    result: list[list[str]] = []
    for row in rows:
        if required_columns is not None:
            has_value = any(get_cell(row, i) for i in required_columns)
        else:
            has_value = any(cell.strip() for cell in row if cell)
        if has_value:
            result.append(row)
    return result


def parse_tabs_metadata(api_response: dict) -> list[TabInfo]:
    """Parse tab metadata from a Sheets API ``spreadsheets.get`` response."""
    tabs: list[TabInfo] = []
    for sheet in api_response.get("sheets", []):
        props = sheet.get("properties", {})
        tabs.append(
            TabInfo(
                gid=props.get("sheetId", 0),
                title=props.get("title", ""),
                row_count=props.get("gridProperties", {}).get("rowCount"),
            ),
        )
    return tabs


# ── Column / cell references ──────────────────────────────────────────────────


def column_index_to_letter(col_idx: int) -> str:
    """Convert a 0-based column index to Excel-style letters (0 → A, 26 → AA)."""
    result = ""
    col_idx += 1
    while col_idx > 0:
        col_idx -= 1
        result = chr(col_idx % 26 + ord("A")) + result
        col_idx //= 26
    return result


def cell_reference(row: int, col_idx: int) -> str:
    """Excel-style cell reference (1-based row, 0-based column index)."""
    return f"{column_index_to_letter(col_idx)}{row}"


def find_column(header_row: list[str], keywords: list[str]) -> int | None:
    """Return the first column index whose header contains any keyword (case-insensitive)."""
    for idx, cell in enumerate(header_row):
        cell_lower = cell.strip().lower()
        for keyword in keywords:
            if keyword.lower() in cell_lower:
                return idx
    return None


# ── Text cleaning ─────────────────────────────────────────────────────────────


def clean_unicode_control_chars(text: str) -> str:
    """Remove invisible Unicode control and formatting characters."""
    return re.sub(
        r"[\u0000-\u001f\u007f-\u009f\u200b-\u200f\u202a-\u202e]",
        "",
        text,
    )


# ── CSV text / file I/O ───────────────────────────────────────────────────────


def parse_csv_text(csv_text: str) -> list[list[str]]:
    """Parse CSV text into a list of rows."""
    return list(csv.reader(io.StringIO(csv_text)))


def _open_csv_file(file_path: str, mode: str = "r") -> TextIO:
    if mode == "w":
        return cast(TextIO, open(file_path, mode, newline="", encoding="utf-8"))
    return cast(TextIO, open(file_path, mode, encoding="utf-8"))


def read_csv_file(file_path: str) -> tuple[list[str], list[dict[str, str]]]:
    """Read a CSV file; return ``(headers, rows)`` as dicts keyed by header name."""
    with _open_csv_file(file_path, "r") as f:
        reader = csv.DictReader(f)
        headers = list(reader.fieldnames or [])
        rows = [dict(row) for row in reader]
    return headers, rows


def write_csv_file(
    data: list[dict[str, Any]],
    file_path: str | None = None,
    output_stream: TextIO | None = None,
) -> None:
    """Write dict rows to a file, stream, or stdout."""
    if not data:
        return

    fieldnames = sorted({key for row in data for key in row})

    if output_stream:
        stream = output_stream
        should_close = False
    elif file_path:
        stream = _open_csv_file(file_path, "w")
        should_close = True
    else:
        stream = sys.stdout
        should_close = False

    try:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)
    finally:
        if should_close:
            stream.close()


# ── CSV comparison ────────────────────────────────────────────────────────────


def extract_order_id(order_number: str) -> str:
    """Strip leading ``#`` from an order number."""
    if not order_number:
        return ""
    return order_number.strip().lstrip("#").strip()


def normalize_header(header: str) -> str:
    """Decode HTML entities in a header for comparison."""
    if not header:
        return ""
    return html.unescape(header.strip())


def normalize_phone_number(phone: str) -> str:
    """Normalize a phone number: digits only, drop leading US country code."""
    if not phone:
        return ""
    digits_only = "".join(c for c in phone if c.isdigit())
    if digits_only.startswith("1") and len(digits_only) == 11:
        digits_only = digits_only[1:]
    return digits_only


def normalize_value(value: str, column_name: str) -> str:
    """Normalize a cell value for comparison (price, phone, default strip)."""
    normalized_column_name = normalize_header(column_name)

    if normalized_column_name.lower() == "total price":
        value = value.strip() if value else ""
        if not value or value.lower() in ("null", "none"):
            return "0.00"
        cleaned = value.replace("$", "").replace(",", "").strip()
        try:
            return f"{float(cleaned):.2f}"
        except (ValueError, TypeError):
            return value

    if normalized_column_name in {
        "Phone",
        "Line items: Custom attributes Best Contact Number (Cell Phone Number Preferred)",
    }:
        return normalize_phone_number(value)

    return value.strip() if value else ""


def build_keyed_dict(
    headers: list[str],
    rows: list[dict[str, str]],
    key_column: str = "Order Number",
    header_normalization_map: dict[str, str] | None = None,
) -> tuple[dict[str, dict[str, str]], list[str]]:
    """Build an order-id-keyed dict from CSV rows."""
    del header_normalization_map  # preserved for API compatibility

    keyed_dict: dict[str, dict[str, str]] = {}
    missing_key_rows: list[str] = []

    normalized_headers = [normalize_header(h) for h in headers]
    normalized_key_column = normalize_header(key_column)
    orig_to_norm = dict(zip(headers, normalized_headers))

    key_header_orig: str | None = None
    for orig_header in headers:
        if normalize_header(orig_header) == normalized_key_column:
            key_header_orig = orig_header
            break
    if key_header_orig is None:
        for orig_header in headers:
            if normalize_header(orig_header).lower() == normalized_key_column.lower():
                key_header_orig = orig_header
                break

    if key_header_orig is None:
        raise ValueError(
            f"Key column {key_column!r} (normalized: {normalized_key_column!r}) "
            f"not found in headers: {headers}",
        )

    for row_idx, row in enumerate(rows, start=2):
        order_id = extract_order_id(row.get(key_header_orig, "").strip())
        if not order_id:
            missing_key_rows.append(f"Row {row_idx}")
            continue

        row_obj: dict[str, str] = {}
        for orig_header in headers:
            value = row.get(orig_header, "").strip()
            normalized_header = orig_to_norm.get(orig_header, normalize_header(orig_header))
            row_obj[normalized_header] = value
        keyed_dict[order_id] = row_obj

    return keyed_dict, missing_key_rows


def compare_csvs(file1: str, file2: str) -> dict[str, Any]:
    """Compare two CSV files by order ID and return detailed differences."""
    headers1_raw, rows1 = read_csv_file(file1)
    headers2_raw, rows2 = read_csv_file(file2)

    headers1 = [h.strip() for h in headers1_raw]
    headers2 = [h.strip() for h in headers2_raw]

    stripped_to_orig1 = dict(zip(headers1, headers1_raw))
    stripped_to_orig2 = dict(zip(headers2, headers2_raw))

    normalized_headers1 = [normalize_header(h) for h in headers1]
    normalized_headers2 = [normalize_header(h) for h in headers2]

    norm_to_orig1 = dict(zip(normalized_headers1, headers1))
    norm_to_orig2 = dict(zip(normalized_headers2, headers2))

    header_differences: list[dict[str, Any]] = []
    normalized_headers1_set = set(normalized_headers1)
    normalized_headers2_set = set(normalized_headers2)

    for norm_header in sorted(normalized_headers1_set - normalized_headers2_set):
        orig_header = norm_to_orig1.get(norm_header, norm_header)
        header_differences.append(
            {
                "type": "header",
                "column_name": orig_header,
                "file1_value": orig_header,
                "file2_value": "<missing>",
            },
        )

    for norm_header in sorted(normalized_headers2_set - normalized_headers1_set):
        orig_header = norm_to_orig2.get(norm_header, norm_header)
        header_differences.append(
            {
                "type": "header",
                "column_name": orig_header,
                "file1_value": "<missing>",
                "file2_value": orig_header,
            },
        )

    try:
        dict1, missing_keys1 = build_keyed_dict(
            headers1_raw, rows1, key_column="Order Number",
            header_normalization_map=stripped_to_orig1,
        )
        dict2, missing_keys2 = build_keyed_dict(
            headers2_raw, rows2, key_column="Order Number",
            header_normalization_map=stripped_to_orig2,
        )
    except ValueError as exc:
        return {
            "error": str(exc),
            "file1": file1,
            "file2": file2,
            "total_differences": 0,
            "header_differences": header_differences,
            "row_breakdown": {},
            "column_breakdown": {},
            "differences": [],
        }

    all_ids = set(dict1.keys()) | set(dict2.keys())
    differences: list[dict[str, Any]] = []
    total_differences = 0
    row_differences: dict[str, int] = defaultdict(int)
    col_differences: dict[str, int] = defaultdict(int)
    all_normalized_headers = sorted(normalized_headers1_set | normalized_headers2_set)

    for order_id in sorted(all_ids):
        row1 = dict1.get(order_id)
        row2 = dict2.get(order_id)

        if row1 is None:
            differences.append(
                {
                    "type": "missing_order",
                    "order_id": order_id,
                    "column_name": None,
                    "file1_value": "<missing>",
                    "file2_value": f"Order #{order_id} present",
                },
            )
            total_differences += 1
            row_differences[order_id] = len(all_normalized_headers)
            continue

        if row2 is None:
            differences.append(
                {
                    "type": "missing_order",
                    "order_id": order_id,
                    "column_name": None,
                    "file1_value": f"Order #{order_id} present",
                    "file2_value": "<missing>",
                },
            )
            total_differences += 1
            row_differences[order_id] = len(all_normalized_headers)
            continue

        row_diff_count = 0
        for norm_header in all_normalized_headers:
            if norm_header.lower() == "updated at":
                continue

            val1_raw = row1.get(norm_header, "")
            val2_raw = row2.get(norm_header, "")
            val1_normalized = normalize_value(val1_raw, norm_header)
            val2_normalized = normalize_value(val2_raw, norm_header)

            if val1_normalized != val2_normalized:
                display_header = (
                    norm_to_orig1.get(norm_header)
                    or norm_to_orig2.get(norm_header)
                    or norm_header
                )
                differences.append(
                    {
                        "type": "cell",
                        "order_id": order_id,
                        "column_name": display_header,
                        "file1_value": val1_raw,
                        "file2_value": val2_raw,
                    },
                )
                total_differences += 1
                row_diff_count += 1
                col_differences[display_header] += 1

        if row_diff_count > 0:
            row_differences[order_id] = row_diff_count

    return {
        "total_differences": total_differences,
        "file1": file1,
        "file2": file2,
        "file1_rows": len(rows1),
        "file2_rows": len(rows2),
        "file1_orders": len(dict1),
        "file2_orders": len(dict2),
        "file1_missing_keys": missing_keys1,
        "file2_missing_keys": missing_keys2,
        "header_differences": header_differences,
        "row_breakdown": dict(row_differences),
        "column_breakdown": dict(col_differences),
        "differences": differences,
    }


def format_differences(result: dict[str, Any], json_output: bool = False) -> str:
    """Format a :func:`compare_csvs` result for display."""
    if json_output:
        return json.dumps(result, indent=2)

    output: list[str] = []
    output.append("=" * 80)
    output.append("CSV Comparison Report")
    output.append("=" * 80)
    output.append(f"\nFile 1: {result['file1']}")
    output.append(f"  Rows: {result['file1_rows']}, Orders: {result.get('file1_orders', 'N/A')}")
    output.append(f"\nFile 2: {result['file2']}")
    output.append(f"  Rows: {result['file2_rows']}, Orders: {result.get('file2_orders', 'N/A')}")

    if result.get("file1_missing_keys"):
        output.append(
            f"\n⚠️  File 1 rows missing Order Number: {', '.join(result['file1_missing_keys'])}",
        )
    if result.get("file2_missing_keys"):
        output.append(
            f"\n⚠️  File 2 rows missing Order Number: {', '.join(result['file2_missing_keys'])}",
        )

    output.append("\n" + "=" * 80)

    if result.get("header_differences"):
        output.append(f"\n📋 Header Differences: {len(result['header_differences'])}")
        output.append("-" * 80)
        for diff in result["header_differences"]:
            output.append(f"  Column '{diff['column_name']}':")
            output.append(f"    File 1: {diff['file1_value']}")
            output.append(f"    File 2: {diff['file2_value']}")
        output.append("")

    output.append(f"\n📊 Total Differences: {result['total_differences']}")
    output.append("")

    if result["row_breakdown"]:
        output.append("📋 Differences by Order ID:")
        output.append("-" * 80)
        for order_id in sorted(
            result["row_breakdown"].keys(),
            key=lambda x: int(x) if x.isdigit() else 0,
        ):
            count = result["row_breakdown"][order_id]
            output.append(f"  Order #{order_id}: {count} difference(s)")
        output.append("")

    if result["column_breakdown"]:
        output.append("📊 Differences by Column:")
        output.append("-" * 80)
        for col_name in sorted(
            result["column_breakdown"].keys(),
            key=lambda x: result["column_breakdown"][x],
            reverse=True,
        ):
            count = result["column_breakdown"][col_name]
            output.append(f"  {col_name}: {count} difference(s)")
        output.append("")

    if result["differences"]:
        output.append("🔍 Detailed Differences (Cell by Cell):")
        output.append("-" * 80)
        column_counts = result["column_breakdown"]
        sorted_differences = sorted(
            result["differences"],
            key=lambda d: (
                -column_counts.get(d.get("column_name", ""), 0),
                int(d.get("order_id", "0")) if d.get("order_id", "").isdigit() else 0,
            ),
        )
        for diff in sorted_differences:
            if diff["type"] == "header":
                output.append(f"\nHeader - {diff['column_name']}:")
            elif diff["type"] == "missing_order":
                output.append(f"\nOrder #{diff['order_id']} - Missing in one file:")
            else:
                output.append(f"\nOrder #{diff['order_id']}, Column '{diff['column_name']}':")
            output.append(f"  File 1: {diff['file1_value']!r}")
            output.append(f"  File 2: {diff['file2_value']!r}")

    return "\n".join(output)


# ── CSVProcessor (email extraction / object conversion) ───────────────────────


class CSVProcessor:
    """CSV row processing: object conversion, email extraction, metadata."""

    def _has_min_rows(self, csv_data: list[list[str]], min_rows: int = 2) -> bool:
        return bool(csv_data and len(csv_data) >= min_rows)

    def _collect_unique_emails(self, emails: list[str]) -> list[str]:
        seen: set[str] = set()
        unique: list[str] = []
        for email in emails:
            if email not in seen:
                seen.add(email)
                unique.append(email)
        return unique

    def _find_email_column_indices(
        self,
        headers: list[str],
        keywords: list[str] | None = None,
    ) -> list[int]:
        if keywords is None:
            keywords = ["personal email"]
        return [
            i
            for i, header in enumerate(headers)
            if header and any(keyword in header.lower() for keyword in keywords)
        ]

    def _extract_email_from_cell(self, cell: str) -> str | None:
        if not cell:
            return None
        return self._is_valid_and_normalize_email(cell.strip())

    def _extract_emails_from_columns(
        self,
        data_rows: list[list[str]],
        column_indices: list[int],
    ) -> list[str]:
        emails: list[str] = []
        for row in data_rows:
            for col_index in column_indices:
                if col_index < len(row):
                    email = self._extract_email_from_cell(row[col_index])
                    if email:
                        emails.append(email)
        return emails

    def _scan_all_cells_for_emails(self, data_rows: list[list[str]]) -> list[str]:
        emails: list[str] = []
        for row in data_rows:
            for cell in row:
                email = self._extract_email_from_cell(cell)
                if email:
                    emails.append(email)
        return emails

    def process_csv_input(self, csv_data: list[list[str]]) -> list[dict[str, Any]]:
        """Convert CSV rows to dicts with lowercased header keys."""
        if not self._has_min_rows(csv_data):
            return []

        headers = [header.strip().lower() for header in csv_data[0]]
        objects: list[dict[str, Any]] = []
        for row in csv_data[1:]:
            if not row or all(not cell.strip() for cell in row):
                continue
            objects.append(
                {
                    headers[i]: value.strip() if value else ""
                    for i, value in enumerate(row)
                    if i < len(headers)
                },
            )
        return objects

    def extract_emails_from_objects(
        self,
        objects: list[dict[str, Any]],
        email_column: str = "personal email",
    ) -> list[str]:
        emails = {
            self._is_valid_and_normalize_email(obj.get(email_column, ""))
            for obj in objects
        }
        return [email for email in emails if email is not None]

    def extract_emails_from_csv(self, csv_data: list[list[str]]) -> list[str]:
        if not self._has_min_rows(csv_data):
            return []

        headers = csv_data[0]
        data_rows = csv_data[1:]
        email_column_indices = self._find_email_column_indices(headers)
        emails = (
            self._extract_emails_from_columns(data_rows, email_column_indices)
            if email_column_indices
            else self._scan_all_cells_for_emails(data_rows)
        )
        return self._collect_unique_emails(emails)

    def get_csv_info(self, csv_data: list[list[str]]) -> dict[str, Any]:
        if not csv_data:
            return {
                "total_rows": 0,
                "data_rows_count": 0,
                "total_columns": 0,
                "email_columns": [],
            }

        headers = csv_data[0]
        email_keywords = ["email", "mail", "e-mail"]
        email_columns = [
            {"index": i, "name": header.strip(), "type": "email"}
            for i, header in enumerate(headers)
            if header and any(keyword in header.strip().lower() for keyword in email_keywords)
        ]
        return {
            "total_rows": len(csv_data),
            "data_rows_count": max(0, len(csv_data) - 1),
            "total_columns": len(headers),
            "email_columns": email_columns,
        }

    def extract_year_from_title(self, title: str) -> int | None:
        if not title:
            return None
        matches = re.findall(r"\b(20\d{2})\b", title)
        return max((int(year) for year in matches), default=None) if matches else None

    def filter_valid_emails(self, emails: list[str]) -> list[str]:
        return [
            normalized
            for email in emails
            if (normalized := self._is_valid_and_normalize_email(email))
        ]

    def extract_column_values(self, csv_data: list[list[str]], column_index: int) -> list[str]:
        if not self._has_min_rows(csv_data):
            return []
        return [
            value
            for row in csv_data[1:]
            if column_index < len(row)
            and (value := row[column_index].strip())
        ]
