from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from pydantic import ValidationError

from app.schemas import (
    CustomReportColumn,
    CustomReportDefinitionData,
    CustomReportRow,
    LegacyConversionPreview,
)

MATRIX_HEADER = re.compile(r"^([Aabc])\s*:\s*(.*)$")
ROW = re.compile(r"^(\d{1,2})\s*:\s*(.*)$")
COLUMN_SPEC = re.compile(r"\[([^\]]+)\]")
ACCOUNT_RANGE = re.compile(r"^\[\s*([^,]+)\s*,\s*([^\]]+)\s*\]$")
COLUMN_FORMULA = re.compile(r"^C(\d{1,2})([+\-%])C(\d{1,2})$", re.IGNORECASE)
UNSUPPORTED_ROW_FORMULA = re.compile(r"^\^(.+)$")


@dataclass
class LegacyParseState:
    columns: list[CustomReportColumn]
    rows: list[CustomReportRow]
    warnings: list[str]
    matrix: str = "A"
    last_total_index: int = 0


def _row_key(matrix: str, number: int) -> str:
    matrix_name = {"A": "a", "a": "la", "b": "b", "c": "c"}[matrix]
    return f"r_{matrix_name}_{number}"


def _column(spec: str, number: int, warnings: list[str]) -> CustomReportColumn | None:
    compact = re.sub(r"\s+", "", spec)
    formula = COLUMN_FORMULA.fullmatch(compact)
    if formula:
        left, operator, right = formula.groups()
        op = "/" if operator == "%" else operator
        return CustomReportColumn(
            key=f"c{number}",
            label=f"Column {number}",
            kind="formula",
            formula=f"c{int(left)} {op} c{int(right)}" + (" * 100" if operator == "%" else ""),
        )
    if re.fullmatch(r"C\d{1,2}%R\d{1,2}", compact, re.IGNORECASE):
        warnings.append(f"Column {number}: cross-row percentage requires manual conversion")
        return None
    historical = compact.startswith("H")
    if historical:
        compact = compact[1:]
    match = re.fullmatch(r"([BU])([PFLT])(\d{1,2})(?:,(\d{1,2}))?", compact)
    if match:
        source, mode, first, second = match.groups()
        target = int(second or first)
        scope: Literal["period", "ytd", "range"] = "period" if mode == "P" else "ytd"
        period_from = int(first) if mode == "T" else None
        if mode == "T":
            scope = "range"
        if historical:
            warnings.append(
                f"Column {number}: historical marker is represented by selecting the "
                "historical fiscal period at run time"
            )
        return CustomReportColumn(
            key=f"c{number}",
            label=f"Column {number}",
            kind="budget" if source == "U" else "balance",
            legacy_period_no=target,
            period_from=period_from,
            scope=scope,
        )
    if compact in {"BC", "BO", "HBC", "HBO"}:
        if compact.endswith("O"):
            warnings.append(f"Column {number}: opening-only balance requires manual conversion")
            return None
        return CustomReportColumn(
            key=f"c{number}", label=f"Column {number}", kind="balance", scope="ytd"
        )
    warnings.append(f"Column {number}: unsupported legacy specification [{spec}]")
    return None


def _parse_columns(text: str, state: LegacyParseState, line_no: int) -> None:
    specs = COLUMN_SPEC.findall(text)
    if not specs:
        state.warnings.append(f"Line {line_no}: matrix header has no columns")
        return
    parsed = [_column(spec, index, state.warnings) for index, spec in enumerate(specs, 1)]
    if any(column is None for column in parsed):
        return
    columns = [column for column in parsed if column is not None]
    if not state.columns:
        state.columns = columns
    elif [column.model_dump() for column in state.columns] != [
        column.model_dump() for column in columns
    ]:
        state.warnings.append(
            f"Line {line_no}: matrices with different column definitions require manual conversion"
        )


def _parse_row(number: int, text: str, state: LegacyParseState, line_no: int) -> None:
    content = text.split("*", 1)[0].strip()
    key = _row_key(state.matrix, number)
    if not content:
        state.rows.append(CustomReportRow(key=key, label="", kind="spacer"))
        return
    if content == "=" or content == f"{state.matrix}=":
        referenced = [
            row.key for row in state.rows[state.last_total_index :] if row.kind != "spacer"
        ]
        if not referenced:
            state.warnings.append(f"Line {line_no}: total has no preceding rows")
            return
        state.rows.append(
            CustomReportRow(
                key=key, label="Total", kind="formula", formula=" + ".join(referenced), bold=True
            )
        )
        state.last_total_index = len(state.rows)
        return
    if UNSUPPORTED_ROW_FORMULA.fullmatch(content):
        expression = content[1:].strip()
        tokens = re.findall(r"([+-]?)\s*(\d{1,2})([Aabc])", expression)
        if not tokens:
            state.warnings.append(f"Line {line_no}: unsupported row formula {content}")
            return
        converted: list[str] = []
        for operator, row_no, matrix in tokens:
            prefix = "- " if operator == "-" else "+ " if converted else ""
            converted.append(f"{prefix}{_row_key(matrix, int(row_no))}")
        state.rows.append(
            CustomReportRow(
                key=key,
                label="Calculated row",
                kind="formula",
                formula=" ".join(converted),
                bold=True,
            )
        )
        return
    range_match = ACCOUNT_RANGE.fullmatch(content.lstrip("+ "))
    if range_match:
        state.rows.append(
            CustomReportRow(
                key=key,
                label=f"Accounts {range_match.group(1).strip()}–{range_match.group(2).strip()}",
                kind="range",
                account_from=range_match.group(1).strip(),
                account_to=range_match.group(2).strip(),
            )
        )
        return
    accounts = [part.strip() for part in content.lstrip("+ ").split("+") if part.strip()]
    if len(accounts) == 1 and re.fullmatch(r"[A-Za-z0-9_.-]{1,30}", accounts[0]):
        state.rows.append(
            CustomReportRow(key=key, label=accounts[0], kind="account", account_code=accounts[0])
        )
        return
    state.warnings.append(
        f"Line {line_no}: multiple or malformed account expression requires manual conversion"
    )


def convert_legacy_report(spec: str, template: str = "") -> LegacyConversionPreview:
    state = LegacyParseState(columns=[], rows=[], warnings=[])
    title = "Imported legacy report"
    for line_no, raw_line in enumerate(spec.splitlines(), 1):
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("*"):
            if line.lower().startswith("* title:"):
                title = line.split(":", 1)[1].strip() or title
            continue
        header = MATRIX_HEADER.fullmatch(line)
        if header:
            state.matrix = header.group(1)
            state.last_total_index = len(state.rows)
            _parse_columns(header.group(2), state, line_no)
            continue
        row = ROW.fullmatch(line)
        if row:
            _parse_row(int(row.group(1)), row.group(2), state, line_no)
            continue
        state.warnings.append(f"Line {line_no}: unrecognized legacy statement")
    if template:
        if "\\rtf" in template.lower():
            state.warnings.append(
                "RTF styling and embedded objects are not executed; structured formatting is used"
            )
        unsupported_symbols = sorted(set(re.findall(r"&([^0-4CDEABTPa-t])", template)))
        if unsupported_symbols:
            state.warnings.append(
                "Unmapped template placeholders: "
                + ", ".join(f"&{value}" for value in unsupported_symbols)
            )
    if not state.columns or not state.rows:
        return LegacyConversionPreview(status="manual", definition=None, warnings=state.warnings)
    try:
        definition = CustomReportDefinitionData(
            title=title,
            columns=state.columns,
            rows=state.rows,
            formatting={"decimals": 2, "legacy_source": True},
        )
    except ValidationError:
        state.warnings.append("Legacy report exceeds the structured report safety limits")
        return LegacyConversionPreview(status="manual", definition=None, warnings=state.warnings)
    return LegacyConversionPreview(
        status="partial" if state.warnings else "compatible",
        definition=definition,
        warnings=state.warnings,
    )
