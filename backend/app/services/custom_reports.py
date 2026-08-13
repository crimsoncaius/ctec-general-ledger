from __future__ import annotations

import ast
import uuid
from collections.abc import Callable
from decimal import ROUND_HALF_UP, Decimal, DivisionByZero, InvalidOperation

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Account, Budget, Company, FiscalPeriod, PeriodBalance
from app.schemas import CustomReportColumn, CustomReportDefinitionData
from app.services.reporting import ReportData

MAX_FORMULA_NODES = 100
ALLOWED_FUNCTIONS = {"abs", "min", "max", "round"}


class FormulaError(ValueError):
    pass


def _formula_names(expression: str) -> set[str]:
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise FormulaError(f"Invalid formula syntax: {exc.msg}") from exc
    nodes = list(ast.walk(tree))
    if len(nodes) > MAX_FORMULA_NODES:
        raise FormulaError("Formula is too complex")
    for node in nodes:
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name) or node.func.id not in ALLOWED_FUNCTIONS:
                raise FormulaError("Only abs, min, max, and round functions are allowed")
        elif not isinstance(
            node,
            (
                ast.Expression,
                ast.BinOp,
                ast.UnaryOp,
                ast.Add,
                ast.Sub,
                ast.Mult,
                ast.Div,
                ast.USub,
                ast.UAdd,
                ast.Name,
                ast.Load,
                ast.Constant,
                ast.Call,
            ),
        ):
            raise FormulaError(f"Unsupported formula element: {type(node).__name__}")
        if isinstance(node, ast.Constant) and (
            isinstance(node.value, bool) or not isinstance(node.value, (int, str))
        ):
            raise FormulaError("Only integer or decimal-string constants are allowed")
    return {
        node.id for node in nodes if isinstance(node, ast.Name) and node.id not in ALLOWED_FUNCTIONS
    }


def evaluate_formula(expression: str, resolver: Callable[[str], Decimal]) -> Decimal:
    _formula_names(expression)
    tree = ast.parse(expression, mode="eval")

    def evaluate(node: ast.AST) -> Decimal:
        if isinstance(node, ast.Expression):
            return evaluate(node.body)
        if isinstance(node, ast.Name):
            return resolver(node.id)
        if isinstance(node, ast.Constant):
            try:
                return Decimal(str(node.value))
            except InvalidOperation as exc:
                raise FormulaError("Invalid decimal constant") from exc
        if isinstance(node, ast.UnaryOp):
            value = evaluate(node.operand)
            return -value if isinstance(node.op, ast.USub) else value
        if isinstance(node, ast.BinOp):
            left, right = evaluate(node.left), evaluate(node.right)
            try:
                if isinstance(node.op, ast.Add):
                    return left + right
                if isinstance(node.op, ast.Sub):
                    return left - right
                if isinstance(node.op, ast.Mult):
                    return left * right
                if isinstance(node.op, ast.Div):
                    if right == 0:
                        raise FormulaError("Division by zero")
                    return left / right
            except (DivisionByZero, InvalidOperation) as exc:
                raise FormulaError("Invalid decimal operation") from exc
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            values = [evaluate(argument) for argument in node.args]
            if node.func.id == "abs" and len(values) == 1:
                return abs(values[0])
            if node.func.id == "min" and values:
                return min(values)
            if node.func.id == "max" and values:
                return max(values)
            if node.func.id == "round" and len(values) in {1, 2}:
                places = int(values[1]) if len(values) == 2 else 0
                if places < 0 or places > 6:
                    raise FormulaError("round places must be from 0 to 6")
                return values[0].quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP)
        raise FormulaError("Unsupported formula operation")

    return evaluate(tree)


def validate_definition_formulas(definition: CustomReportDefinitionData) -> None:
    row_keys = {row.key for row in definition.rows}
    column_keys = {column.key for column in definition.columns}
    for row in definition.rows:
        if row.formula:
            unknown = _formula_names(row.formula) - row_keys
            if unknown:
                raise FormulaError(
                    f"Row {row.key} references unknown rows: {', '.join(sorted(unknown))}"
                )
    for column in definition.columns:
        if column.formula:
            unknown = _formula_names(column.formula) - column_keys
            if unknown:
                raise FormulaError(
                    f"Column {column.key} references unknown columns: {', '.join(sorted(unknown))}"
                )


def _target_period(
    db: Session,
    company_id: uuid.UUID,
    column: CustomReportColumn,
    parameters: dict[str, object],
) -> FiscalPeriod:
    value = column.period_id or parameters.get("period_id")
    target: FiscalPeriod | None = None
    if value:
        try:
            period_id = value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))
        except ValueError as exc:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT, "Invalid period identifier"
            ) from exc
        target = db.scalar(
            select(FiscalPeriod).where(
                FiscalPeriod.company_id == company_id, FiscalPeriod.id == period_id
            )
        )
    if target is None:
        target = db.scalar(
            select(FiscalPeriod)
            .where(FiscalPeriod.company_id == company_id)
            .order_by(FiscalPeriod.start_date.desc())
            .limit(1)
        )
    if target is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "No fiscal period is configured")
    if column.legacy_period_no is not None:
        target = db.scalar(
            select(FiscalPeriod).where(
                FiscalPeriod.company_id == company_id,
                FiscalPeriod.fiscal_year_id == target.fiscal_year_id,
                FiscalPeriod.period_no == column.legacy_period_no,
            )
        )
        if target is None:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT, "Legacy period is not configured"
            )
    return target


def _source_values(
    db: Session,
    company_id: uuid.UUID,
    column: CustomReportColumn,
    parameters: dict[str, object],
) -> dict[uuid.UUID, Decimal]:
    target = _target_period(db, company_id, column, parameters)
    if column.scope == "period":
        period_ids = [target.id]
    else:
        from_no = column.period_from or 1
        period_ids = list(
            db.scalars(
                select(FiscalPeriod.id).where(
                    FiscalPeriod.company_id == company_id,
                    FiscalPeriod.fiscal_year_id == target.fiscal_year_id,
                    FiscalPeriod.period_no >= from_no,
                    FiscalPeriod.period_no <= target.period_no,
                )
            ).all()
        )
    if column.kind == "budget":
        rows = db.execute(
            select(Budget.account_id, func.coalesce(func.sum(Budget.amount), 0))
            .where(
                Budget.company_id == company_id,
                Budget.fiscal_period_id.in_(period_ids),
                Budget.scenario == column.scenario,
            )
            .group_by(Budget.account_id)
        ).all()
    else:
        rows = db.execute(
            select(
                PeriodBalance.account_id,
                func.coalesce(func.sum(PeriodBalance.debit_base - PeriodBalance.credit_base), 0),
            )
            .where(
                PeriodBalance.company_id == company_id,
                PeriodBalance.fiscal_period_id.in_(period_ids),
            )
            .group_by(PeriodBalance.account_id)
        ).all()
    return {account_id: Decimal(value or 0) for account_id, value in rows}


def build_custom_report(
    db: Session,
    company_id: uuid.UUID,
    definition: CustomReportDefinitionData,
    parameters: dict[str, object],
) -> ReportData:
    try:
        validate_definition_formulas(definition)
    except FormulaError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
    company = db.get(Company, company_id)
    if company is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Company not found")
    accounts = list(
        db.scalars(
            select(Account).where(Account.company_id == company_id).order_by(Account.code)
        ).all()
    )
    accounts_by_code = {account.code: account for account in accounts}
    source_maps = {
        column.key: _source_values(db, company_id, column, parameters)
        for column in definition.columns
        if column.kind != "formula"
    }
    rows_by_key = {row.key: row for row in definition.rows}
    columns_by_key = {column.key: column for column in definition.columns}
    cache: dict[tuple[str, str], Decimal] = {}
    visiting: set[tuple[str, str]] = set()

    def cell(row_key: str, column_key: str) -> Decimal:
        identity = (row_key, column_key)
        if identity in cache:
            return cache[identity]
        if identity in visiting:
            raise FormulaError(f"Circular formula at {row_key}/{column_key}")
        visiting.add(identity)
        row, column = rows_by_key[row_key], columns_by_key[column_key]
        if row.kind in {"heading", "spacer"}:
            value = Decimal("0")
        elif column.kind == "formula":
            value = evaluate_formula(column.formula or "0", lambda name: cell(row_key, name))
        elif row.kind == "formula":
            value = evaluate_formula(row.formula or "0", lambda name: cell(name, column_key))
        elif row.kind == "account":
            account = accounts_by_code.get(row.account_code or "")
            if account is None:
                raise FormulaError(f"Account {row.account_code} does not exist")
            value = source_maps[column_key].get(account.id, Decimal("0"))
        elif row.kind == "range":
            selected = [
                account
                for account in accounts
                if (row.account_from or "") <= account.code <= (row.account_to or "")
            ]
            value = sum(
                (source_maps[column_key].get(account.id, Decimal("0")) for account in selected),
                Decimal("0"),
            )
        else:
            value = Decimal("0")
        visiting.remove(identity)
        cache[identity] = value
        return value

    decimals = min(max(int(definition.formatting.get("decimals", 2)), 0), 6)
    quantum = Decimal(1).scaleb(-decimals)
    section_for_row = {
        row_key: section.title for section in definition.sections for row_key in section.row_keys
    }
    emitted_sections: set[str] = set()
    output: list[dict[str, object]] = []
    try:
        for row in definition.rows:
            section = section_for_row.get(row.key, "")
            if section and section not in emitted_sections:
                output.append({"label": section, "kind": "section"})
                emitted_sections.add(section)
            rendered: dict[str, object] = {
                "label": row.label,
                "kind": row.kind,
                "bold": row.bold,
                "indent": row.indent,
            }
            for column in definition.columns:
                value = cell(row.key, column.key).quantize(quantum, rounding=ROUND_HALF_UP)
                rendered[column.key] = format(value, f".{decimals}f")
            output.append(rendered)
    except FormulaError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc

    selected_period = _target_period(db, company_id, definition.columns[0], parameters)
    try:
        title = definition.title.format_map(
            {
                "company_name": company.name,
                "company_code": company.code,
                "period_label": selected_period.label,
                "as_of_date": selected_period.end_date.isoformat(),
            }
        )
    except (KeyError, ValueError) as exc:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            f"Unsupported report title placeholder: {exc}",
        ) from exc
    return ReportData(title, ["label", *[column.key for column in definition.columns]], output)
