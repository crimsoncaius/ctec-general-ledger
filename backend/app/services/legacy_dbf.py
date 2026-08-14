from __future__ import annotations

import hashlib
import io
import json
import tempfile
import uuid
import zipfile
from collections import defaultdict
from collections.abc import Iterable
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path, PurePosixPath
from typing import Any

from dbfread import DBF  # type: ignore[import-untyped]
from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    Account,
    AccountType,
    Budget,
    Company,
    Currency,
    FiscalPeriod,
    FiscalYear,
    JournalBatch,
    JournalEntry,
    JournalLine,
    JournalStatus,
    MigrationRun,
    MigrationStagingRecord,
    ReportDefinition,
    RunStatus,
)
from app.services.accounting import post_batch
from app.services.audit import record_audit
from app.services.legacy_reports import convert_legacy_report

SUPPORTED_TABLES = {"GLACCNT", "GLACCNX", "GLMAIN", "GLTRANS", "GLGP", "GLREP"}
TABLE_FILES = {f"{name}.{ext}" for name in SUPPORTED_TABLES for ext in ("DAT", "DBF")}
CONFIG_FILE = "GLCOMP.SET"
REPORT_TEMPLATE_DELIMITER = "$------------------REPORT STARTS BELOW-----------------------"
CURRENCY_ALIASES = {"S$": "SGD", "US$": "USD"}
MAX_ARCHIVE_BYTES = 100 * 1024 * 1024
MAX_EXPANDED_BYTES = 250 * 1024 * 1024
MAX_FILES = 40
TYPE_MAP = {
    "I": AccountType.REVENUE_EXPENSE,
    "B": AccountType.BALANCE_SHEET,
    "R": AccountType.RETAINED_EARNINGS,
    "T": AccountType.TITLE,
}


def _decimal(value: object, field: str, issues: list[dict[str, Any]]) -> Decimal:
    if value in (None, ""):
        return Decimal("0")
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        issues.append(_issue("malformed_number", f"{field} is not a valid decimal", field))
        return Decimal("0")


def _issue(
    code: str, message: str, field: str | None = None, *, blocking: bool = True
) -> dict[str, Any]:
    return {"code": code, "message": message, "field": field, "blocking": blocking}


def _json_value(value: object) -> object:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, bytes):
        return value.decode("cp1252", errors="replace")
    return value


def _normalize(record: dict[str, object]) -> dict[str, Any]:
    return {str(key).upper(): _json_value(value) for key, value in record.items()}


def _canonical_digest(files: dict[str, bytes]) -> str:
    digest = hashlib.sha256()
    for name in sorted(files):
        digest.update(name.encode("ascii", errors="ignore"))
        digest.update(b"\0")
        digest.update(hashlib.sha256(files[name]).digest())
    return digest.hexdigest()


def _split_legacy_format(value: str) -> tuple[str, str]:
    spec, delimiter, template = value.partition(REPORT_TEMPLATE_DELIMITER)
    return spec.rstrip(), template.lstrip("\r\n") if delimiter else ""


def extract_archive(
    archive: bytes,
) -> tuple[str, list[dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    if not archive or len(archive) > MAX_ARCHIVE_BYTES:
        raise HTTPException(
            status.HTTP_413_CONTENT_TOO_LARGE, "Archive must be between 1 byte and 100 MB"
        )
    try:
        source = zipfile.ZipFile(io.BytesIO(archive))
    except zipfile.BadZipFile as exc:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "Legacy source must be a ZIP archive"
        ) from exc

    members = [member for member in source.infolist() if not member.is_dir()]
    if len(members) > MAX_FILES or sum(member.file_size for member in members) > MAX_EXPANDED_BYTES:
        raise HTTPException(
            status.HTTP_413_CONTENT_TOO_LARGE, "Archive expands beyond the migration safety limit"
        )
    files: dict[str, bytes] = {}
    for member in members:
        path = PurePosixPath(member.filename.replace("\\", "/"))
        if path.name != str(path) or path.name in {"", ".", ".."}:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT, "Archive must contain flat filenames only"
            )
        name = path.name.upper()
        if name in files:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT, f"Duplicate archive member {name}"
            )
        files[name] = source.read(member)

    table_names = sorted({name.rsplit(".", 1)[0] for name in files if name in TABLE_FILES})
    if "GLACCNT" not in table_names or "GLMAIN" not in table_names:
        raise HTTPException(422, "Archive must contain GLACCNT.DAT/DBF and GLMAIN.DAT/DBF")
    relevant = {}
    for name, content in files.items():
        stem, _, extension = name.rpartition(".")
        if (
            (stem in table_names and extension in {"DAT", "DBF", "DBT", "FPT"})
            or name == CONFIG_FILE
            or extension == "FMT"
        ):
            relevant[name] = content
    manifest = [
        {"name": name, "bytes": len(content), "sha256": hashlib.sha256(content).hexdigest()}
        for name, content in sorted(relevant.items())
    ]
    tables: dict[str, list[dict[str, Any]]] = {}
    with tempfile.TemporaryDirectory(prefix="ctec-dbf-readonly-") as temp_name:
        temp = Path(temp_name)
        for name, content in relevant.items():
            (temp / name).write_bytes(content)
        for table_name in table_names:
            filename = next(
                name for name in relevant if name in {f"{table_name}.DAT", f"{table_name}.DBF"}
            )
            try:
                table = DBF(
                    str(temp / filename),
                    load=True,
                    ignore_missing_memofile=True,
                    char_decode_errors="replace",
                )
                tables[table_name] = [_normalize(dict(record)) for record in table]
            except Exception as exc:
                raise HTTPException(422, f"Unable to read {filename}: {exc}") from exc
    for name, content in sorted(relevant.items()):
        if not name.endswith(".FMT"):
            continue
        raw = content.decode("cp1252", errors="replace").rstrip("\x1a")
        spec, template = _split_legacy_format(raw)
        tables.setdefault("GLREP", []).append(
            {
                "NAME": Path(name).stem,
                "SOURCE_FILENAME": name,
                "SPEC": spec,
                "REP": template,
            }
        )
    return _canonical_digest(relevant), manifest, tables


def _severity(issues: list[dict[str, Any]]) -> str:
    if any(bool(issue["blocking"]) for issue in issues):
        return "error"
    return "warning" if issues else "ok"


def _currency(record: dict[str, Any], prefix: str, base: str) -> str:
    value = str(record.get(f"{prefix}_CURR" if prefix else "CURR", "") or "").strip().upper()
    return CURRENCY_ALIASES.get(value, value) or base


def _raw_currency(record: dict[str, Any], prefix: str) -> str:
    return str(record.get(f"{prefix}_CURR" if prefix else "CURR", "") or "").strip().upper()


def _effective_group_key(payload: dict[str, Any], prefix: str = "") -> str:
    migration_key = f"{prefix}_MIGRATION_KEY" if prefix else "MIGRATION_KEY"
    return str(payload.get(migration_key) or payload.get("KEY") or "").strip()


def _derive_posted_group_keys(
    rows: list[MigrationStagingRecord],
) -> dict[int, str]:
    buckets: defaultdict[tuple[str, str, str, str], list[MigrationStagingRecord]] = defaultdict(
        list
    )
    for row in rows:
        if str(row.payload.get("KEY", "") or "").strip():
            continue
        signature = (
            str(row.payload.get("M_PERIOD", "") or "").strip(),
            str(row.payload.get("M_DATE", "") or "").strip(),
            str(row.payload.get("M_REF", "") or "").strip(),
            str(row.payload.get("M_GNAME", "") or "").strip(),
        )
        buckets[signature].append(row)
    derived: dict[int, str] = {}
    for signature, group in buckets.items():
        debit = sum(
            (_decimal(row.payload.get("M_DEBIT"), "M_DEBIT", []) for row in group), Decimal("0")
        )
        credit = sum(
            (_decimal(row.payload.get("M_CREDIT"), "M_CREDIT", []) for row in group),
            Decimal("0"),
        )
        if debit != credit or debit <= 0:
            continue
        material = json.dumps(signature, separators=(",", ":"), ensure_ascii=True)
        key = f"AUTO-{hashlib.sha256(material.encode('ascii')).hexdigest()[:12].upper()}"
        for row in group:
            derived[row.source_record] = key
    return derived


def _records(
    run: MigrationRun, table: str, values: Iterable[dict[str, Any]]
) -> list[MigrationStagingRecord]:
    return [
        MigrationStagingRecord(
            company_id=run.company_id,
            migration_run_id=run.id,
            source_table=table,
            source_record=index,
            natural_key=None,
            payload=value,
            severity="ok",
            issues=[],
        )
        for index, value in enumerate(values, 1)
    ]


def stage_archive(
    db: Session,
    *,
    company_id: uuid.UUID,
    user_id: uuid.UUID,
    source_name: str,
    archive: bytes,
) -> MigrationRun:
    digest, manifest, tables = extract_archive(archive)
    existing = db.scalar(
        select(MigrationRun).where(
            MigrationRun.company_id == company_id,
            MigrationRun.source_digest == digest,
            MigrationRun.dry_run.is_(True),
        )
    )
    if existing is not None:
        return existing

    company = db.get(Company, company_id)
    if company is None:
        raise HTTPException(404, "Company not found")
    periods = list(
        db.scalars(
            select(FiscalPeriod)
            .join(FiscalYear, FiscalYear.id == FiscalPeriod.fiscal_year_id)
            .where(FiscalPeriod.company_id == company_id)
            .order_by(FiscalYear.start_date.desc(), FiscalPeriod.period_no)
        ).all()
    )
    if not periods:
        raise HTTPException(409, "Configure the target fiscal calendar before staging migration")
    target_year_id = periods[0].fiscal_year_id
    period_map = {
        period.period_no: period for period in periods if period.fiscal_year_id == target_year_id
    }
    currencies = set(db.scalars(select(Currency.code)).all())
    run = MigrationRun(
        company_id=company_id,
        source_path=Path(source_name).name[:1000],
        source_digest=digest,
        status=RunStatus.RUNNING,
        dry_run=True,
        requested_by_id=user_id,
        counts={"manifest": manifest, "target_fiscal_year_id": str(target_year_id)},
        reconciliation={},
    )
    db.add(run)
    db.flush()
    staged = [record for table, values in tables.items() for record in _records(run, table, values)]
    db.add_all(staged)
    db.flush()
    by_table: dict[str, list[MigrationStagingRecord]] = defaultdict(list)
    for row in staged:
        by_table[row.source_table].append(row)

    account_codes: set[str] = set()
    retained = 0
    account_period_values: dict[tuple[str, int], Decimal] = {}
    opening_total = Decimal("0")
    recorded_current_total = Decimal("0")
    for row in by_table["GLACCNT"]:
        payload = row.payload
        issues: list[dict[str, Any]] = []
        code = str(payload.get("A_ACC_CODE", "") or "").strip()
        row.natural_key = code or None
        if not code:
            issues.append(_issue("missing_account_code", "Account code is blank", "A_ACC_CODE"))
        elif code in account_codes:
            issues.append(
                _issue("duplicate_account", f"Duplicate account code {code}", "A_ACC_CODE")
            )
        account_codes.add(code)
        legacy_type = str(payload.get("ACC_TYPE", "") or "").strip().upper()
        if legacy_type not in TYPE_MAP:
            issues.append(
                _issue("invalid_account_type", f"Unknown account type {legacy_type!r}", "ACC_TYPE")
            )
        if legacy_type == "R":
            retained += 1
        currency = _currency(payload, "", company.base_currency_code)
        raw_currency = _raw_currency(payload, "")
        if raw_currency and raw_currency != currency:
            issues.append(
                _issue(
                    "currency_normalized",
                    f"Legacy currency {raw_currency!r} is imported as {currency}",
                    "CURR",
                    blocking=False,
                )
            )
        if len(currency) != 3 or currency not in currencies:
            issues.append(
                _issue("unknown_currency", f"Currency {currency!r} is not configured", "CURR")
            )
        opening = _decimal(payload.get("OPEN_BAL"), "OPEN_BAL", issues)
        current = _decimal(payload.get("CURR_BAL"), "CURR_BAL", issues)
        period_sum = Decimal("0")
        for period_no in range(1, len(period_map) + 1):
            amount = _decimal(payload.get(f"BAL_{period_no}"), f"BAL_{period_no}", issues)
            account_period_values[(code, period_no)] = amount
            period_sum += amount
        if current != opening + period_sum:
            issues.append(
                _issue(
                    "account_current_mismatch",
                    "CURR_BAL does not equal OPEN_BAL plus periods "
                    f"({current} versus {opening + period_sum})",
                )
            )
        opening_total += opening
        recorded_current_total += current
        row.issues = issues
        row.severity = _severity(issues)
    if retained > 1:
        for row in by_table["GLACCNT"]:
            if str(row.payload.get("ACC_TYPE", "")).strip().upper() == "R":
                row.issues = [
                    *row.issues,
                    _issue(
                        "duplicate_retained_earnings",
                        "More than one retained-earnings account exists",
                    ),
                ]
                row.severity = "error"

    transaction_period_values: defaultdict[tuple[str, int], Decimal] = defaultdict(Decimal)
    total_debit = Decimal("0")
    total_credit = Decimal("0")
    groups: defaultdict[str, list[MigrationStagingRecord]] = defaultdict(list)
    seen_recno: set[str] = set()
    fingerprints: set[str] = set()
    derived_group_keys = _derive_posted_group_keys(by_table["GLMAIN"])
    for row in by_table["GLMAIN"]:
        payload = row.payload
        transaction_issues: list[dict[str, Any]] = []
        code = str(payload.get("M_ACC_CODE", "") or "").strip()
        source_key = str(payload.get("KEY", "") or "").strip()
        key = source_key or derived_group_keys.get(row.source_record, "")
        if key and not source_key:
            payload = {**payload, "MIGRATION_KEY": key}
            row.payload = payload
            transaction_issues.append(
                _issue(
                    "derived_group_key",
                    f"Blank legacy KEY is imported as deterministic group {key}",
                    "KEY",
                    blocking=False,
                )
            )
        row.natural_key = key or None
        if code not in account_codes:
            transaction_issues.append(
                _issue("orphan_transaction", f"Account {code!r} does not exist", "M_ACC_CODE")
            )
        try:
            period_no = int(payload.get("M_PERIOD", 0) or 0)
        except (TypeError, ValueError):
            period_no = 0
        period = period_map.get(period_no)
        if period is None:
            transaction_issues.append(
                _issue("invalid_period", f"Period {period_no} is not configured", "M_PERIOD")
            )
        trans_date = payload.get("M_DATE")
        if not isinstance(trans_date, str) or not trans_date:
            transaction_issues.append(
                _issue("malformed_date", "Transaction date is missing or malformed", "M_DATE")
            )
        elif period is not None and not (
            period.start_date.isoformat() <= trans_date <= period.end_date.isoformat()
        ):
            transaction_issues.append(
                _issue(
                    "date_period_mismatch",
                    f"Date {trans_date} falls outside period {period_no}",
                    "M_DATE",
                )
            )
        debit = _decimal(payload.get("M_DEBIT"), "M_DEBIT", transaction_issues)
        credit = _decimal(payload.get("M_CREDIT"), "M_CREDIT", transaction_issues)
        if debit < 0 or credit < 0 or (debit > 0) == (credit > 0):
            transaction_issues.append(
                _issue(
                    "invalid_line_sides",
                    "Exactly one non-negative debit or credit must be positive",
                )
            )
        currency = _currency(payload, "M", company.base_currency_code)
        raw_currency = _raw_currency(payload, "M")
        if raw_currency and raw_currency != currency:
            transaction_issues.append(
                _issue(
                    "currency_normalized",
                    f"Legacy currency {raw_currency!r} is imported as {currency}",
                    "M_CURR",
                    blocking=False,
                )
            )
        if len(currency) != 3 or currency not in currencies:
            transaction_issues.append(
                _issue("unknown_currency", f"Currency {currency!r} is not configured", "M_CURR")
            )
        rate = _decimal(payload.get("M_EXRATE") or 1, "M_EXRATE", transaction_issues)
        if rate <= 0:
            transaction_issues.append(
                _issue("invalid_exchange_rate", "Exchange rate must be positive", "M_EXRATE")
            )
        elif currency == company.base_currency_code and rate != 1:
            payload = {**payload, "MIGRATION_EXRATE": "1"}
            row.payload = payload
            transaction_issues.append(
                _issue(
                    "base_currency_rate_normalized",
                    f"Base-currency rate {rate} is imported as 1",
                    "M_EXRATE",
                    blocking=False,
                )
            )
        if not key:
            transaction_issues.append(
                _issue(
                    "missing_group_key",
                    "Posted row has no stable group KEY and cannot be applied safely",
                    "KEY",
                )
            )
        recno = str(payload.get("RECNO", "") or "").strip()
        if recno and recno in seen_recno:
            transaction_issues.append(
                _issue("duplicate_record_number", f"Duplicate legacy RECNO {recno}", "RECNO")
            )
        if recno:
            seen_recno.add(recno)
        fingerprint = json.dumps(payload, sort_keys=True, default=str)
        if fingerprint in fingerprints:
            transaction_issues.append(
                _issue("duplicate_transaction", "Exact duplicate posted record", blocking=False)
            )
        fingerprints.add(fingerprint)
        total_debit += debit
        total_credit += credit
        transaction_period_values[(code, period_no)] += debit - credit
        if key:
            groups[key].append(row)
        row.issues = transaction_issues
        row.severity = _severity(transaction_issues)

    for key, rows in groups.items():
        periods_dates = {
            (str(row.payload.get("M_PERIOD")), str(row.payload.get("M_DATE"))) for row in rows
        }
        debit = sum(
            (_decimal(row.payload.get("M_DEBIT"), "M_DEBIT", []) for row in rows), Decimal("0")
        )
        credit = sum(
            (_decimal(row.payload.get("M_CREDIT"), "M_CREDIT", []) for row in rows), Decimal("0")
        )
        group_issues: list[dict[str, Any]] = []
        if len(periods_dates) != 1:
            group_issues.append(
                _issue(
                    "mixed_group_period", f"Group {key} spans dates or periods and needs regrouping"
                )
            )
        if debit != credit or debit <= 0:
            group_issues.append(
                _issue(
                    "unbalanced_group", f"Group {key} debits {debit} do not equal credits {credit}"
                )
            )
        for row in rows:
            row.issues = [*row.issues, *group_issues]
            row.severity = _severity(row.issues)

    for row in by_table.get("GLACCNX", []):
        code = str(row.payload.get("A_ACC_CODE", "") or "").strip()
        row.natural_key = code or None
        if code not in account_codes:
            row.issues = [
                _issue(
                    "orphan_currency_mirror",
                    f"Currency mirror account {code!r} has no base account",
                )
            ]
            row.severity = "error"

    gp_keys = {str(row.payload.get("KEY", "") or "").strip() for row in by_table.get("GLGP", [])}
    trans_keys = {
        str(row.payload.get("KEY", "") or "").strip() for row in by_table.get("GLTRANS", [])
    }
    for row in by_table.get("GLGP", []):
        key = str(row.payload.get("KEY", "") or "").strip()
        row.natural_key = key or None
        if not key or key not in trans_keys:
            row.issues = [
                _issue("orphan_group_header", "Pre-post group has no matching transaction detail")
            ]
            row.severity = "error"
    for row in by_table.get("GLTRANS", []):
        key = str(row.payload.get("KEY", "") or "").strip()
        code = str(row.payload.get("T_ACC_CODE", "") or "").strip()
        row.natural_key = key or None
        issues = []
        if not key or key not in gp_keys:
            issues.append(
                _issue("orphan_group_detail", "Pre-post detail has no matching group header")
            )
        if code not in account_codes:
            issues.append(
                _issue("orphan_draft_transaction", f"Account {code!r} does not exist", "T_ACC_CODE")
            )
        try:
            period_no = int(row.payload.get("T_PERIOD", 0) or 0)
        except (TypeError, ValueError):
            period_no = 0
        period = period_map.get(period_no)
        if period is None:
            issues.append(
                _issue("invalid_draft_period", f"Period {period_no} is not configured", "T_PERIOD")
            )
        trans_date = row.payload.get("T_DATE")
        if not isinstance(trans_date, str) or not trans_date:
            issues.append(
                _issue("malformed_draft_date", "Draft transaction date is missing", "T_DATE")
            )
        elif period is not None and not (
            period.start_date.isoformat() <= trans_date <= period.end_date.isoformat()
        ):
            issues.append(
                _issue(
                    "draft_date_period_mismatch",
                    f"Date {trans_date} falls outside period {period_no}",
                    "T_DATE",
                )
            )
        debit = _decimal(row.payload.get("T_DEBIT"), "T_DEBIT", issues)
        credit = _decimal(row.payload.get("T_CREDIT"), "T_CREDIT", issues)
        if debit < 0 or credit < 0 or (debit > 0) == (credit > 0):
            issues.append(
                _issue(
                    "invalid_draft_line_sides",
                    "Exactly one non-negative draft debit or credit must be positive",
                )
            )
        currency = _currency(row.payload, "T", company.base_currency_code)
        rate = _decimal(row.payload.get("T_EXRATE") or 1, "T_EXRATE", issues)
        if currency != company.base_currency_code or rate != 1:
            issues.append(
                _issue(
                    "foreign_draft_manual",
                    "Foreign-currency draft requires manual review because the legacy base "
                    "conversion implementation is unavailable",
                )
            )
        row.issues = issues
        row.severity = _severity(issues)

    draft_groups: defaultdict[str, list[MigrationStagingRecord]] = defaultdict(list)
    for row in by_table.get("GLTRANS", []):
        key = str(row.payload.get("KEY", "") or "").strip()
        if key:
            draft_groups[key].append(row)
    for key, rows in draft_groups.items():
        dates_periods = {
            (str(row.payload.get("T_PERIOD")), str(row.payload.get("T_DATE"))) for row in rows
        }
        debit = sum(
            (_decimal(row.payload.get("T_DEBIT"), "T_DEBIT", []) for row in rows), Decimal("0")
        )
        credit = sum(
            (_decimal(row.payload.get("T_CREDIT"), "T_CREDIT", []) for row in rows),
            Decimal("0"),
        )
        draft_group_issues: list[dict[str, Any]] = []
        if len(dates_periods) != 1:
            draft_group_issues.append(
                _issue("mixed_draft_period", f"Draft group {key} spans dates or periods")
            )
        if debit != credit or debit <= 0:
            draft_group_issues.append(
                _issue(
                    "unbalanced_draft_group",
                    f"Draft group {key} debits {debit} do not equal credits {credit}",
                )
            )
        for row in rows:
            row.issues = [*row.issues, *draft_group_issues]
            row.severity = _severity(row.issues)

    for row in by_table.get("GLREP", []):
        name = str(row.payload.get("NAME", "") or "").strip()
        row.natural_key = name or None
        conversion = convert_legacy_report(
            f"* Title: {name or 'Imported legacy report'}\n"
            f"{str(row.payload.get('SPEC', '') or '')}",
            str(row.payload.get("REP", "") or ""),
        )
        row.payload = {
            **row.payload,
            "CONVERSION_STATUS": conversion.status,
            "CONVERTED_DEFINITION": conversion.definition.model_dump(mode="json")
            if conversion.definition
            else None,
        }
        row.issues = [
            _issue("legacy_report_warning", warning, blocking=False)
            for warning in conversion.warnings
        ]
        row.severity = _severity(row.issues)

    for (code, period_no), recorded in account_period_values.items():
        actual = transaction_period_values[(code, period_no)]
        if recorded != actual:
            account_row = next(
                (candidate for candidate in by_table["GLACCNT"] if candidate.natural_key == code),
                None,
            )
            if account_row is not None:
                account_row.issues = [
                    *account_row.issues,
                    _issue(
                        "period_reconciliation_mismatch",
                        f"Period {period_no}: account records {recorded}, ledger totals {actual}",
                    ),
                ]
                account_row.severity = "error"

    error_count = sum(row.severity == "error" for row in staged)
    warning_count = sum(row.severity == "warning" for row in staged)
    run.counts = {
        **run.counts,
        "tables": {name: len(values) for name, values in tables.items()},
        "records": len(staged),
        "errors": error_count,
        "warnings": warning_count,
    }
    run.reconciliation = {
        "opening_balance_net": str(opening_total),
        "recorded_current_net": str(recorded_current_total),
        "ledger_debits": str(total_debit),
        "ledger_credits": str(total_credit),
        "ledger_balanced": total_debit == total_credit,
        "account_periods_match": not any(
            any(issue["code"] == "period_reconciliation_mismatch" for issue in row.issues)
            for row in by_table["GLACCNT"]
        ),
        "apply_ready": error_count == 0 and total_debit == total_credit and opening_total == 0,
    }
    if total_debit != total_credit:
        run.reconciliation["blocking_reason"] = "Global posted ledger is unbalanced"
    elif opening_total != 0:
        run.reconciliation["blocking_reason"] = "Global opening balances are unbalanced"
    run.status = RunStatus.SUCCEEDED
    record_audit(
        db,
        company_id=company_id,
        actor_id=user_id,
        action="migration.staged",
        entity_type="migration_run",
        entity_id=str(run.id),
        after={"digest": digest, "counts": run.counts, "reconciliation": run.reconciliation},
    )
    db.commit()
    return run


def apply_run(db: Session, source: MigrationRun, user_id: uuid.UUID) -> MigrationRun:
    if not source.dry_run or source.status != RunStatus.SUCCEEDED:
        raise HTTPException(409, "Only a successful dry run can be applied")
    if not bool(source.reconciliation.get("apply_ready")):
        raise HTTPException(
            409, "Resolve every blocking exception and reconciliation difference before apply"
        )
    existing = db.scalar(
        select(MigrationRun).where(
            MigrationRun.company_id == source.company_id,
            MigrationRun.source_digest == source.source_digest,
            MigrationRun.dry_run.is_(False),
        )
    )
    if existing is not None:
        return existing
    if db.scalar(
        select(func.count(Account.id)).where(Account.company_id == source.company_id)
    ) or db.scalar(
        select(func.count(JournalBatch.id)).where(JournalBatch.company_id == source.company_id)
    ):
        raise HTTPException(409, "Apply requires an empty target company to prevent ledger mixing")
    rows = list(
        db.scalars(
            select(MigrationStagingRecord)
            .where(
                MigrationStagingRecord.company_id == source.company_id,
                MigrationStagingRecord.migration_run_id == source.id,
            )
            .order_by(MigrationStagingRecord.source_table, MigrationStagingRecord.source_record)
        ).all()
    )
    by_table: defaultdict[str, list[MigrationStagingRecord]] = defaultdict(list)
    for row in rows:
        by_table[row.source_table].append(row)
    company = db.get(Company, source.company_id)
    assert company is not None
    periods = list(
        db.scalars(
            select(FiscalPeriod)
            .where(FiscalPeriod.company_id == source.company_id)
            .order_by(FiscalPeriod.start_date.desc(), FiscalPeriod.period_no)
        ).all()
    )
    target_year = periods[0].fiscal_year_id
    period_map = {
        period.period_no: period for period in periods if period.fiscal_year_id == target_year
    }
    applied = MigrationRun(
        company_id=source.company_id,
        source_path=source.source_path,
        source_digest=source.source_digest,
        status=RunStatus.RUNNING,
        dry_run=False,
        requested_by_id=user_id,
        counts=source.counts,
        reconciliation=source.reconciliation,
    )
    db.add(applied)
    db.flush()
    for row in rows:
        db.add(
            MigrationStagingRecord(
                company_id=source.company_id,
                migration_run_id=applied.id,
                source_table=row.source_table,
                source_record=row.source_record,
                natural_key=row.natural_key,
                payload=row.payload,
                severity=row.severity,
                issues=row.issues,
            )
        )

    account_map: dict[str, Account] = {}
    for row in by_table["GLACCNT"]:
        payload = row.payload
        code = str(payload["A_ACC_CODE"]).strip()
        account = Account(
            company_id=source.company_id,
            code=code,
            name=str(payload.get("DESC", "") or code).strip() or code,
            account_type=TYPE_MAP[str(payload["ACC_TYPE"]).strip().upper()],
            currency_code=_currency(payload, "", company.base_currency_code),
            postable=str(payload["ACC_TYPE"]).strip().upper() != "T",
            active=True,
        )
        db.add(account)
        account_map[code] = account
    db.flush()
    for row in by_table["GLACCNT"]:
        code = str(row.payload["A_ACC_CODE"]).strip()
        for period_no, period in period_map.items():
            amount = Decimal(str(row.payload.get(f"BUG_{period_no}", "0") or "0"))
            if amount:
                db.add(
                    Budget(
                        company_id=source.company_id,
                        fiscal_period_id=period.id,
                        account_id=account_map[code].id,
                        scenario="Legacy imported",
                        currency_code=company.base_currency_code,
                        amount=amount,
                    )
                )

    mirrors = {
        str(row.payload.get("A_ACC_CODE", "") or "").strip(): row.payload
        for row in by_table.get("GLACCNX", [])
    }
    opening_lines: list[tuple[Account, Decimal, Decimal, Decimal]] = []
    for row in by_table["GLACCNT"]:
        amount = Decimal(str(row.payload.get("OPEN_BAL", "0") or "0"))
        if amount:
            code = str(row.payload["A_ACC_CODE"]).strip()
            account = account_map[code]
            original = amount
            rate = Decimal("1")
            if account.currency_code != company.base_currency_code:
                mirror = mirrors.get(code, {})
                mirror_amount = Decimal(str(mirror.get("OPEN_BAL", "0") or "0"))
                if mirror_amount and (mirror_amount > 0) == (amount > 0):
                    original = mirror_amount
                    rate = abs(amount / mirror_amount)
            opening_lines.append((account, amount, original, rate))
    posted_batches = 0
    if opening_lines:
        first_period = min(period_map.values(), key=lambda value: value.period_no)
        batch = JournalBatch(
            company_id=source.company_id,
            batch_no=f"MIG-{source.source_digest[:10]}-OPEN",
            description="Legacy opening balances",
            status=JournalStatus.APPROVED,
            created_by_id=user_id,
            approved_by_id=user_id,
            approved_at=datetime.now(UTC),
        )
        db.add(batch)
        db.flush()
        entry = JournalEntry(
            company_id=source.company_id,
            batch_id=batch.id,
            entry_no=f"MIG-OPEN-{source.source_digest[:10]}",
            entry_date=first_period.start_date,
            posting_date=first_period.start_date,
            fiscal_period_id=first_period.id,
            reference="LEGACY-OPEN",
            description="Imported legacy opening balances",
            status=JournalStatus.APPROVED,
            created_by_id=user_id,
        )
        db.add(entry)
        db.flush()
        for index, (account, amount, original, rate) in enumerate(opening_lines, 1):
            db.add(
                JournalLine(
                    company_id=source.company_id,
                    entry_id=entry.id,
                    line_no=index,
                    account_id=account.id,
                    description="Legacy opening balance",
                    currency_code=account.currency_code,
                    exchange_rate=rate,
                    debit_original=max(original, Decimal("0")),
                    credit_original=max(-original, Decimal("0")),
                    debit_base=max(amount, Decimal("0")),
                    credit_base=max(-amount, Decimal("0")),
                )
            )
        db.flush()
        post_batch(db, source.company_id, batch.id, user_id, commit=False)
        posted_batches += 1

    headers_by_key = {
        str(row.payload.get("KEY", "") or "").strip(): row for row in by_table.get("GLGP", [])
    }
    draft_rows: defaultdict[str, list[MigrationStagingRecord]] = defaultdict(list)
    for row in by_table.get("GLTRANS", []):
        draft_rows[str(row.payload.get("KEY", "") or "").strip()].append(row)
    draft_batches = 0
    for sequence, (key, group) in enumerate(sorted(draft_rows.items()), 1):
        header = headers_by_key[key].payload
        sample = group[0].payload
        period = period_map[int(sample["T_PERIOD"])]
        entry_date = date.fromisoformat(str(sample["T_DATE"]))
        batch = JournalBatch(
            company_id=source.company_id,
            batch_no=f"MIG-DRAFT-{source.source_digest[:6]}-{sequence:05d}",
            description=f"Imported pre-post group {header.get('GNAME') or key}",
            status=JournalStatus.DRAFT,
            created_by_id=user_id,
        )
        db.add(batch)
        db.flush()
        entry = JournalEntry(
            company_id=source.company_id,
            batch_id=batch.id,
            entry_no=f"MIG-DRAFT-{source.source_digest[:6]}-{sequence:05d}",
            entry_date=entry_date,
            posting_date=entry_date,
            fiscal_period_id=period.id,
            reference=str(sample.get("T_REF", ""))[:80],
            description=f"Imported pre-post group {header.get('GNAME') or key}",
            status=JournalStatus.DRAFT,
            created_by_id=user_id,
        )
        db.add(entry)
        db.flush()
        for line_no, row in enumerate(group, 1):
            payload = row.payload
            debit = Decimal(str(payload.get("T_DEBIT", "0") or "0"))
            credit = Decimal(str(payload.get("T_CREDIT", "0") or "0"))
            db.add(
                JournalLine(
                    company_id=source.company_id,
                    entry_id=entry.id,
                    line_no=line_no,
                    account_id=account_map[str(payload["T_ACC_CODE"]).strip()].id,
                    description=str(payload.get("T_TRANS_DE", ""))[:250],
                    currency_code=company.base_currency_code,
                    exchange_rate=Decimal("1"),
                    debit_original=debit,
                    credit_original=credit,
                    debit_base=debit,
                    credit_base=credit,
                )
            )
        draft_batches += 1

    groups: defaultdict[str, list[MigrationStagingRecord]] = defaultdict(list)
    for row in by_table["GLMAIN"]:
        groups[_effective_group_key(row.payload)].append(row)
    for sequence, (key, group) in enumerate(sorted(groups.items()), 1):
        sample = group[0].payload
        period = period_map[int(sample["M_PERIOD"])]
        posting_date = date.fromisoformat(str(sample["M_DATE"]))
        batch = JournalBatch(
            company_id=source.company_id,
            batch_no=f"MIG-{source.source_digest[:8]}-{sequence:05d}",
            description=f"Legacy group {sample.get('M_GNAME') or key}",
            status=JournalStatus.APPROVED,
            created_by_id=user_id,
            approved_by_id=user_id,
            approved_at=datetime.now(UTC),
        )
        db.add(batch)
        db.flush()
        entry = JournalEntry(
            company_id=source.company_id,
            batch_id=batch.id,
            entry_no=f"MIG-{source.source_digest[:8]}-{sequence:05d}",
            entry_date=posting_date,
            posting_date=posting_date,
            fiscal_period_id=period.id,
            reference=str(sample.get("M_REF", ""))[:80],
            description=f"Imported legacy group {sample.get('M_GNAME') or key}",
            status=JournalStatus.APPROVED,
            created_by_id=user_id,
        )
        db.add(entry)
        db.flush()
        for line_no, row in enumerate(group, 1):
            payload = row.payload
            debit = Decimal(str(payload.get("M_DEBIT", "0") or "0"))
            credit = Decimal(str(payload.get("M_CREDIT", "0") or "0"))
            currency = _currency(payload, "M", company.base_currency_code)
            rate = Decimal(
                str(payload.get("MIGRATION_EXRATE") or payload.get("M_EXRATE", "1") or "1")
            )
            debit_original = (
                Decimal(str(payload.get("M_DEBITX", "0") or "0"))
                if currency != company.base_currency_code
                else debit
            )
            credit_original = (
                Decimal(str(payload.get("M_CREDITX", "0") or "0"))
                if currency != company.base_currency_code
                else credit
            )
            if debit and not debit_original:
                debit_original = debit / rate
            if credit and not credit_original:
                credit_original = credit / rate
            db.add(
                JournalLine(
                    company_id=source.company_id,
                    entry_id=entry.id,
                    line_no=line_no,
                    account_id=account_map[str(payload["M_ACC_CODE"]).strip()].id,
                    description=str(payload.get("M_TRANS_DE", ""))[:250],
                    currency_code=currency,
                    exchange_rate=rate,
                    debit_original=debit_original,
                    credit_original=credit_original,
                    debit_base=debit,
                    credit_base=credit,
                )
            )
        db.flush()
        post_batch(db, source.company_id, batch.id, user_id, commit=False)
        posted_batches += 1

    imported_reports = 0
    for row in by_table.get("GLREP", []):
        definition = row.payload.get("CONVERTED_DEFINITION")
        db.add(
            ReportDefinition(
                company_id=source.company_id,
                name=str(row.payload.get("NAME") or "Legacy report")[:160],
                report_type="legacy",
                definition=definition or {},
                legacy_spec=str(row.payload.get("SPEC", "") or ""),
                legacy_template=str(row.payload.get("REP", "") or ""),
                conversion_status=str(row.payload["CONVERSION_STATUS"]),
                is_template=False,
                version=1,
                created_by_id=user_id,
            )
        )
        imported_reports += 1
    applied.counts = {
        **source.counts,
        "applied_accounts": len(account_map),
        "applied_posted_batches": posted_batches,
        "applied_draft_batches": draft_batches,
        "applied_reports": imported_reports,
    }
    applied.status = RunStatus.SUCCEEDED
    record_audit(
        db,
        company_id=source.company_id,
        actor_id=user_id,
        action="migration.applied",
        entity_type="migration_run",
        entity_id=str(applied.id),
        after={"digest": applied.source_digest, "counts": applied.counts},
    )
    db.commit()
    return applied
