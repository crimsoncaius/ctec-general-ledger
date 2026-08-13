from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
from fastapi import HTTPException

from app.db import SessionLocal
from app.schemas import CustomReportDefinitionData
from app.services.custom_reports import FormulaError, build_custom_report, evaluate_formula
from app.services.legacy_reports import convert_legacy_report


def test_formula_arithmetic_functions_and_rejection_boundaries() -> None:
    resolver = {"a": Decimal("8"), "b": Decimal("2")}.get
    expressions = {
        "a + b": Decimal("10"),
        "a - b": Decimal("6"),
        "a * b": Decimal("16"),
        "a / b": Decimal("4"),
        "-a": Decimal("-8"),
        "+b": Decimal("2"),
        "abs(-a)": Decimal("8"),
        "min(a, b)": Decimal("2"),
        "max(a, b)": Decimal("8"),
        "round('1.235', 2)": Decimal("1.24"),
        "round('1.6')": Decimal("2"),
    }
    for expression, expected in expressions.items():
        assert evaluate_formula(expression, resolver) == expected

    rejected = [
        "a +",
        "True",
        "1.2",
        "__import__('os')",
        "a ** b",
        "'not-decimal'",
        "a / 0",
        "round(a, 7)",
        "abs(a, b)",
        "+".join("a" for _ in range(60)),
    ]
    for expression in rejected:
        with pytest.raises(FormulaError):
            evaluate_formula(expression, resolver)


def _definition(**overrides: object) -> CustomReportDefinitionData:
    values: dict[str, object] = {
        "title": "Boundary {company_code} {period_label} {as_of_date}",
        "columns": [
            {
                "key": "actual",
                "label": "Actual",
                "kind": "balance",
                "scope": "ytd",
            },
            {
                "key": "budget",
                "label": "Budget",
                "kind": "budget",
                "scope": "range",
                "period_from": 1,
                "scenario": "Approved FY2026",
            },
            {
                "key": "variance",
                "label": "Variance",
                "kind": "formula",
                "formula": "actual - budget",
            },
        ],
        "rows": [
            {"key": "heading", "label": "Heading", "kind": "heading"},
            {"key": "space", "label": "", "kind": "spacer"},
            {
                "key": "range",
                "label": "Range",
                "kind": "range",
                "account_from": "1000",
                "account_to": "4999",
            },
            {
                "key": "double",
                "label": "Double",
                "kind": "formula",
                "formula": "range * 2",
            },
        ],
        "sections": [{"title": "Boundary section", "row_keys": ["heading", "range"]}],
        "formatting": {"decimals": 9},
    }
    if "rows" in overrides and "sections" not in overrides:
        values["sections"] = []
    values.update(overrides)
    return CustomReportDefinitionData.model_validate(values)


def test_custom_report_source_formula_layout_and_error_paths(acme_ledger) -> None:
    with SessionLocal() as db:
        report = build_custom_report(
            db,
            acme_ledger["company_id"],
            _definition(),
            {"period_id": str(acme_ledger["period_id"])},
        )
        assert report.title.startswith("Boundary ACME P01")
        assert report.rows[0] == {"label": "Boundary section", "kind": "section"}
        assert report.rows[-1]["kind"] == "formula"
        assert str(report.rows[-1]["variance"]).count(".") == 1
        assert len(str(report.rows[-1]["variance"]).split(".")[1]) == 6

        with pytest.raises(HTTPException, match="Company not found"):
            build_custom_report(db, uuid.uuid4(), _definition(), {})
        with pytest.raises(HTTPException, match="Invalid period identifier"):
            build_custom_report(
                db,
                acme_ledger["company_id"],
                _definition(),
                {"period_id": "bad-period"},
            )

        legacy_missing = _definition(
            columns=[
                {
                    "key": "actual",
                    "label": "Actual",
                    "kind": "balance",
                    "legacy_period_no": 18,
                }
            ]
        )
        with pytest.raises(HTTPException, match="Legacy period is not configured"):
            build_custom_report(
                db,
                acme_ledger["company_id"],
                legacy_missing,
                {"period_id": str(acme_ledger["period_id"])},
            )

        missing_account = _definition(
            rows=[
                {
                    "key": "missing",
                    "label": "Missing",
                    "kind": "account",
                    "account_code": "DOES-NOT-EXIST",
                }
            ]
        )
        with pytest.raises(HTTPException, match="does not exist"):
            build_custom_report(
                db,
                acme_ledger["company_id"],
                missing_account,
                {"period_id": str(acme_ledger["period_id"])},
            )

        circular = _definition(
            columns=[{"key": "actual", "label": "Actual", "kind": "balance"}],
            rows=[
                {"key": "one", "label": "One", "kind": "formula", "formula": "two"},
                {"key": "two", "label": "Two", "kind": "formula", "formula": "one"},
            ],
        )
        with pytest.raises(HTTPException, match="Circular formula"):
            build_custom_report(
                db,
                acme_ledger["company_id"],
                circular,
                {"period_id": str(acme_ledger["period_id"])},
            )


def test_unknown_row_and_column_formula_references_are_rejected(acme_ledger) -> None:
    unknown_row = _definition(
        rows=[{"key": "value", "label": "Value", "kind": "formula", "formula": "unknown"}]
    )
    unknown_column = _definition(
        columns=[{"key": "value", "label": "Value", "kind": "formula", "formula": "unknown"}],
        rows=[{"key": "space", "label": "", "kind": "spacer"}],
    )
    with SessionLocal() as db:
        for definition in (unknown_row, unknown_column):
            with pytest.raises(HTTPException, match="references unknown"):
                build_custom_report(db, acme_ledger["company_id"], definition, {})


def test_legacy_report_parser_covers_supported_partial_and_manual_constructs() -> None:
    compatible = convert_legacy_report(
        "\n".join(
            [
                "* Title: Parser matrix",
                "A: [BP1] [UL1] [BT1,2] [C1+C2] [C1-C2] [C1%C2] [BC] [HBP1]",
                "0:",
                "1: 1000",
                "2: [1000,4999]",
                "3: ^1A-2A",
                "4: =",
            ]
        )
    )
    assert compatible.status == "partial"
    assert compatible.definition is not None
    assert {row.kind for row in compatible.definition.rows} == {
        "spacer",
        "account",
        "range",
        "formula",
    }
    assert any("historical marker" in warning for warning in compatible.warnings)

    manual = convert_legacy_report(
        "\n".join(
            [
                "A:",
                "1: =",
                "2: ^nonsense",
                "3: 1000 + 2000",
                "not recognized",
                "b: [BO] [C1%R2] [UNKNOWN]",
            ]
        ),
        template="{\\rtf1 &Z}",
    )
    assert manual.status == "manual"
    assert manual.definition is None
    warnings = " ".join(manual.warnings)
    for expected in (
        "has no columns",
        "total has no preceding rows",
        "unsupported row formula",
        "multiple or malformed",
        "unrecognized legacy statement",
        "opening-only balance",
        "cross-row percentage",
        "unsupported legacy specification",
        "RTF styling",
        "Unmapped template placeholders",
    ):
        assert expected in warnings

    different_matrices = convert_legacy_report("A: [BP1]\n1: 1000\nb: [BP2]\n2: 2000")
    assert different_matrices.status == "partial"
    assert any("different column definitions" in item for item in different_matrices.warnings)
