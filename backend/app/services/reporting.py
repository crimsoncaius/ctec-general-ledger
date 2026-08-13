from __future__ import annotations

import csv
import hashlib
import io
import json
import uuid
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from fastapi import HTTPException, status
from openpyxl import Workbook
from openpyxl.styles import Font
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    Account,
    AccountType,
    ClosingEvent,
    FiscalPeriod,
    JournalBatch,
    JournalEntry,
    JournalLine,
    JournalStatus,
    PeriodBalance,
)
from app.services.integrity import run_integrity_checks


@dataclass(frozen=True)
class ReportData:
    title: str
    columns: list[str]
    rows: list[dict[str, Any]]

    @property
    def digest(self) -> str:
        payload = json.dumps(self.rows, sort_keys=True, default=str, separators=(",", ":"))
        return hashlib.sha256(payload.encode()).hexdigest()


def _period(db: Session, company_id: uuid.UUID, value: str | None) -> FiscalPeriod | None:
    if not value:
        return None
    try:
        period_id = uuid.UUID(value)
    except ValueError as exc:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "Invalid period identifier"
        ) from exc
    period = db.scalar(
        select(FiscalPeriod).where(
            FiscalPeriod.company_id == company_id, FiscalPeriod.id == period_id
        )
    )
    if period is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Fiscal period not found")
    return period


def _chart(db: Session, company_id: uuid.UUID, parameters: dict[str, Any]) -> ReportData:
    statement = select(Account).where(Account.company_id == company_id)
    if parameters.get("code_from"):
        statement = statement.where(Account.code >= str(parameters["code_from"]))
    if parameters.get("code_to"):
        statement = statement.where(Account.code <= str(parameters["code_to"]))
    if not parameters.get("include_inactive", False):
        statement = statement.where(Account.active.is_(True))
    accounts = db.scalars(statement.order_by(Account.code)).all()
    rows = [
        {
            "code": account.code,
            "name": account.name,
            "type": account.account_type.value,
            "currency": account.currency_code,
            "postable": account.postable,
            "active": account.active,
        }
        for account in accounts
    ]
    return ReportData("Chart of Accounts", list(rows[0]) if rows else ["code", "name"], rows)


def _trial_balance(db: Session, company_id: uuid.UUID, parameters: dict[str, Any]) -> ReportData:
    target = _period(db, company_id, parameters.get("period_id"))
    if target is None:
        target = db.scalar(
            select(FiscalPeriod)
            .where(FiscalPeriod.company_id == company_id)
            .order_by(FiscalPeriod.start_date.desc())
            .limit(1)
        )
    if target is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "No fiscal period is configured")
    period_ids = db.scalars(
        select(FiscalPeriod.id).where(
            FiscalPeriod.company_id == company_id,
            FiscalPeriod.fiscal_year_id == target.fiscal_year_id,
            FiscalPeriod.period_no <= target.period_no,
        )
    ).all()
    aggregates = db.execute(
        select(
            PeriodBalance.account_id,
            func.sum(PeriodBalance.debit_base),
            func.sum(PeriodBalance.credit_base),
            func.sum(PeriodBalance.debit_original),
            func.sum(PeriodBalance.credit_original),
        )
        .where(
            PeriodBalance.company_id == company_id,
            PeriodBalance.fiscal_period_id.in_(period_ids),
        )
        .group_by(PeriodBalance.account_id)
    ).all()
    values = {row[0]: tuple(Decimal(value or 0) for value in row[1:]) for row in aggregates}
    include_zero = bool(parameters.get("include_zero", False))
    include_titles = bool(parameters.get("include_titles", True))
    rows: list[dict[str, Any]] = []
    accounts = db.scalars(
        select(Account).where(Account.company_id == company_id).order_by(Account.code)
    ).all()
    for account in accounts:
        if account.account_type == AccountType.TITLE:
            if include_titles:
                rows.append(
                    {
                        "code": account.code,
                        "name": account.name,
                        "currency": "",
                        "debit": "0.000000",
                        "credit": "0.000000",
                        "original_debit": "0.000000",
                        "original_credit": "0.000000",
                        "title": True,
                    }
                )
            continue
        debit_movement, credit_movement, debit_original, credit_original = values.get(
            account.id, (Decimal("0"),) * 4
        )
        net = debit_movement - credit_movement
        if not include_zero and net == 0:
            continue
        rows.append(
            {
                "code": account.code,
                "name": account.name,
                "currency": account.currency_code,
                "debit": str(max(net, Decimal("0"))),
                "credit": str(max(-net, Decimal("0"))),
                "original_debit": str(max(debit_original - credit_original, Decimal("0"))),
                "original_credit": str(max(credit_original - debit_original, Decimal("0"))),
                "title": False,
            }
        )
    return ReportData(
        f"Trial Balance — {target.label}",
        ["code", "name", "currency", "debit", "credit", "original_debit", "original_credit"],
        rows,
    )


def _ledger(db: Session, company_id: uuid.UUID, parameters: dict[str, Any]) -> ReportData:
    from_period = _period(db, company_id, parameters.get("from_period_id"))
    to_period = _period(db, company_id, parameters.get("to_period_id"))
    statement = (
        select(JournalEntry, JournalLine, Account, JournalBatch)
        .join(JournalLine, JournalLine.entry_id == JournalEntry.id)
        .join(Account, Account.id == JournalLine.account_id)
        .join(JournalBatch, JournalBatch.id == JournalEntry.batch_id)
        .where(
            JournalEntry.company_id == company_id,
            JournalEntry.status == JournalStatus.POSTED,
        )
    )
    if from_period:
        statement = statement.where(JournalEntry.posting_date >= from_period.start_date)
    if to_period:
        statement = statement.where(JournalEntry.posting_date <= to_period.end_date)
    if parameters.get("code_from"):
        statement = statement.where(Account.code >= str(parameters["code_from"]))
    if parameters.get("code_to"):
        statement = statement.where(Account.code <= str(parameters["code_to"]))
    results = db.execute(
        statement.order_by(
            Account.code, JournalEntry.posting_date, JournalEntry.entry_no, JournalLine.line_no
        )
    ).all()
    running: dict[uuid.UUID, Decimal] = {}
    if from_period:
        prior = db.execute(
            select(
                JournalLine.account_id,
                func.sum(JournalLine.debit_base - JournalLine.credit_base),
            )
            .join(JournalEntry, JournalEntry.id == JournalLine.entry_id)
            .where(
                JournalEntry.company_id == company_id,
                JournalEntry.status == JournalStatus.POSTED,
                JournalEntry.posting_date < from_period.start_date,
            )
            .group_by(JournalLine.account_id)
        ).all()
        running = {account_id: Decimal(net or 0) for account_id, net in prior}
    rows = []
    for entry, line, account, batch in results:
        movement = line.debit_base - line.credit_base
        running[account.id] = running.get(account.id, Decimal("0")) + movement
        rows.append(
            {
                "account": account.code,
                "account_name": account.name,
                "batch": batch.batch_no,
                "entry": entry.entry_no,
                "period": entry.fiscal_period_id,
                "date": entry.posting_date,
                "reference": entry.reference,
                "description": line.description or entry.description,
                "currency": line.currency_code,
                "exchange_rate": line.exchange_rate,
                "original_debit": line.debit_original,
                "original_credit": line.credit_original,
                "base_debit": line.debit_base,
                "base_credit": line.credit_base,
                "balance": running[account.id],
            }
        )
    columns = list(rows[0]) if rows else ["account", "entry", "date", "base_debit", "base_credit"]
    return ReportData("General Ledger Listing", columns, rows)


def _groups(
    db: Session, company_id: uuid.UUID, parameters: dict[str, Any], *, pre_post: bool
) -> ReportData:
    statuses = (
        [
            JournalStatus.DRAFT,
            JournalStatus.VALIDATED,
            JournalStatus.APPROVED,
            JournalStatus.REJECTED,
        ]
        if pre_post
        else list(JournalStatus)
    )
    statement = (
        select(
            JournalBatch,
            func.count(func.distinct(JournalEntry.id)),
            func.coalesce(func.sum(JournalLine.debit_base), 0),
            func.coalesce(func.sum(JournalLine.credit_base), 0),
        )
        .join(JournalEntry, JournalEntry.batch_id == JournalBatch.id)
        .join(JournalLine, JournalLine.entry_id == JournalEntry.id)
        .where(JournalBatch.company_id == company_id, JournalBatch.status.in_(statuses))
        .group_by(JournalBatch.id)
        .order_by(JournalBatch.created_at.desc())
    )
    if parameters.get("batch_id"):
        try:
            statement = statement.where(JournalBatch.id == uuid.UUID(str(parameters["batch_id"])))
        except ValueError as exc:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT, "Invalid batch identifier"
            ) from exc
    rows = [
        {
            "batch": batch.batch_no,
            "description": batch.description,
            "status": batch.status.value,
            "entries": count,
            "debit": debit,
            "credit": credit,
            "balanced": Decimal(debit) == Decimal(credit),
            "created_at": batch.created_at,
            "posted_at": batch.posted_at,
        }
        for batch, count, debit, credit in db.execute(statement).all()
    ]
    title = "Pre-post Journal Report" if pre_post else "Transaction Group Report"
    return ReportData(
        title, list(rows[0]) if rows else ["batch", "status", "debit", "credit"], rows
    )


def _close_history(db: Session, company_id: uuid.UUID) -> ReportData:
    events = db.scalars(
        select(ClosingEvent)
        .where(ClosingEvent.company_id == company_id)
        .order_by(ClosingEvent.created_at)
    ).all()
    rows = [
        {
            "event_id": event.id,
            "fiscal_year_id": event.fiscal_year_id,
            "closed_at": event.created_at,
            "closing_entry_id": event.closing_entry_id,
            "opening_entry_id": event.opening_entry_id,
            "compensated_by": event.reversed_by_entry_id,
            "profit_loss": event.reconciliation.get("profit_loss", "0"),
            "balanced": event.reconciliation.get("balanced", False),
        }
        for event in events
    ]
    return ReportData("Fiscal Closing History", list(rows[0]) if rows else ["event_id"], rows)


def build_report(
    db: Session, company_id: uuid.UUID, report_type: str, parameters: dict[str, Any]
) -> ReportData:
    if report_type == "chart_of_accounts":
        return _chart(db, company_id, parameters)
    if report_type == "trial_balance":
        return _trial_balance(db, company_id, parameters)
    if report_type == "general_ledger":
        return _ledger(db, company_id, parameters)
    if report_type == "transaction_groups":
        return _groups(db, company_id, parameters, pre_post=False)
    if report_type == "pre_post":
        return _groups(db, company_id, parameters, pre_post=True)
    if report_type == "close_history":
        return _close_history(db, company_id)
    if report_type == "integrity":
        rows = run_integrity_checks(db, company_id)
        return ReportData(
            "Ledger Integrity",
            ["name", "ok", "details"],
            [
                {"name": row["name"], "ok": row["ok"], "details": json.dumps(row, default=str)}
                for row in rows
            ],
        )
    raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Unsupported report type")


def export_report(report: ReportData, output_format: str) -> tuple[bytes, str, str]:
    if output_format == "csv":
        stream = io.StringIO(newline="")
        writer = csv.DictWriter(stream, fieldnames=report.columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(report.rows)
        return stream.getvalue().encode("utf-8-sig"), "text/csv; charset=utf-8", "csv"
    if output_format == "xlsx":
        workbook = Workbook()
        sheet = workbook.active
        assert sheet is not None
        sheet.title = "Report"
        sheet.append(report.columns)
        for row in report.rows:
            sheet.append(
                [
                    str(row.get(column, "")) if row.get(column) is not None else ""
                    for column in report.columns
                ]
            )
        sheet.freeze_panes = "A2"
        sheet.auto_filter.ref = sheet.dimensions
        for cell in sheet[1]:
            cell.font = Font(bold=True)
        output = io.BytesIO()
        workbook.save(output)
        return (
            output.getvalue(),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "xlsx",
        )
    if output_format == "pdf":
        output = io.BytesIO()
        document = SimpleDocTemplate(output, pagesize=landscape(A4), leftMargin=24, rightMargin=24)
        styles = getSampleStyleSheet()
        story = [Paragraph(report.title, styles["Title"]), Spacer(1, 12)]
        display_columns = report.columns[:10]
        data = [display_columns] + [
            [str(row.get(column, ""))[:60] for column in display_columns] for row in report.rows
        ]
        table = Table(data, repeatRows=1)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#173e32")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 7),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cfd6d1")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
            )
        )
        story.append(table)
        document.build(story)
        return output.getvalue(), "application/pdf", "pdf"
    raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Unsupported export format")
