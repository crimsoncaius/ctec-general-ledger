import io
import struct
import zipfile
from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db import SessionLocal
from app.models import (
    Account,
    Company,
    Currency,
    FiscalPeriod,
    FiscalYear,
    Membership,
    PeriodStatus,
    Permission,
    Role,
    RolePermission,
    User,
)
from tests.conftest import auth_headers

Field = tuple[str, str, int, int]


def dbf_bytes(fields: list[Field], records: list[dict[str, object]]) -> bytes:
    header_length = 32 + 32 * len(fields) + 1
    record_length = 1 + sum(field[2] for field in fields)
    header = bytearray(32)
    header[0] = 0x03
    header[1:4] = bytes((126, 8, 10))
    header[4:8] = struct.pack("<I", len(records))
    header[8:10] = struct.pack("<H", header_length)
    header[10:12] = struct.pack("<H", record_length)
    descriptors = bytearray()
    for name, kind, width, decimals in fields:
        descriptor = bytearray(32)
        encoded_name = name.encode("ascii")[:10]
        descriptor[: len(encoded_name)] = encoded_name
        descriptor[11] = ord(kind)
        descriptor[16] = width
        descriptor[17] = decimals
        descriptors.extend(descriptor)
    body = bytearray()
    for record in records:
        body.extend(b" ")
        for name, kind, width, decimals in fields:
            value = record.get(name, "")
            if kind == "C":
                encoded = str(value).encode("cp1252")[:width].ljust(width, b" ")
            elif kind == "D":
                encoded = str(value).replace("-", "").encode("ascii").ljust(width, b" ")
            elif kind == "L":
                encoded = (b"T" if bool(value) else b"F").ljust(width, b" ")
            else:
                text = f"{Decimal(str(value)):.{decimals}f}" if value != "" else ""
                encoded = text.encode("ascii").rjust(width, b" ")
            body.extend(encoded)
    return bytes(header + descriptors + b"\r" + body + b"\x1a")


ACCOUNT_FIELDS: list[Field] = [
    ("A_ACC_CODE", "C", 10, 0),
    ("DESC", "C", 40, 0),
    ("ACC_TYPE", "C", 1, 0),
    ("OPEN_BAL", "N", 17, 3),
    ("CURR_BAL", "N", 17, 3),
    ("BAL_1", "N", 17, 3),
    ("BUG_1", "N", 17, 3),
    ("CURR", "C", 5, 0),
]
MAIN_FIELDS: list[Field] = [
    ("M_ACC_CODE", "C", 10, 0),
    ("M_PERIOD", "N", 2, 0),
    ("M_DATE", "D", 8, 0),
    ("M_TRANS_DE", "C", 40, 0),
    ("M_REF", "C", 10, 0),
    ("M_DEBIT", "N", 17, 3),
    ("M_CREDIT", "N", 17, 3),
    ("M_GNAME", "C", 10, 0),
    ("M_CURR", "C", 5, 0),
    ("M_EXRATE", "N", 14, 7),
    ("M_CREDITX", "N", 17, 3),
    ("M_DEBITX", "N", 17, 3),
    ("KEY", "C", 10, 0),
    ("RECNO", "N", 10, 0),
]
GROUP_FIELDS: list[Field] = [("GNAME", "C", 10, 0), ("KEY", "C", 10, 0)]
DRAFT_FIELDS: list[Field] = [
    ("T_ACC_CODE", "C", 10, 0),
    ("T_PERIOD", "N", 2, 0),
    ("T_DATE", "D", 8, 0),
    ("T_TRANS_DE", "C", 40, 0),
    ("T_REF", "C", 10, 0),
    ("T_DEBIT", "N", 17, 3),
    ("T_CREDIT", "N", 17, 3),
    ("T_CURR", "C", 5, 0),
    ("T_EXRATE", "N", 14, 7),
    ("KEY", "C", 10, 0),
    ("GNAME", "C", 10, 0),
]


def legacy_archive(*, corrupt: bool = False, include_drafts: bool = False) -> bytes:
    accounts = [
        {
            "A_ACC_CODE": "1000",
            "DESC": "Cash",
            "ACC_TYPE": "B",
            "OPEN_BAL": 0,
            "CURR_BAL": Decimal("125.55"),
            "BAL_1": Decimal("125.55"),
            "BUG_1": Decimal("120"),
            "CURR": "SGD",
        },
        {
            "A_ACC_CODE": "4000" if not corrupt else "1000",
            "DESC": "Sales",
            "ACC_TYPE": "I",
            "OPEN_BAL": 0,
            "CURR_BAL": Decimal("-125.55"),
            "BAL_1": Decimal("-125.55"),
            "BUG_1": Decimal("-100"),
            "CURR": "SGD",
        },
    ]
    transactions = [
        {
            "M_ACC_CODE": "1000",
            "M_PERIOD": 1,
            "M_DATE": "2026-01-15",
            "M_TRANS_DE": "Legacy sale",
            "M_REF": "INV-1",
            "M_DEBIT": Decimal("125.55"),
            "M_CREDIT": 0,
            "M_GNAME": "SALES",
            "M_CURR": "SGD",
            "M_EXRATE": 1,
            "M_DEBITX": Decimal("125.55"),
            "M_CREDITX": 0,
            "KEY": "K0001",
            "RECNO": 1,
        },
        {
            "M_ACC_CODE": "4000" if not corrupt else "9999",
            "M_PERIOD": 1,
            "M_DATE": "2026-01-15",
            "M_TRANS_DE": "Legacy sale",
            "M_REF": "INV-1",
            "M_DEBIT": 0,
            "M_CREDIT": Decimal("125.55") if not corrupt else Decimal("120"),
            "M_GNAME": "SALES",
            "M_CURR": "SGD",
            "M_EXRATE": 1,
            "M_DEBITX": 0,
            "M_CREDITX": Decimal("125.55"),
            "KEY": "K0001",
            "RECNO": 2,
        },
    ]
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("GLACCNT.DAT", dbf_bytes(ACCOUNT_FIELDS, accounts))
        archive.writestr("GLMAIN.DAT", dbf_bytes(MAIN_FIELDS, transactions))
        if include_drafts:
            archive.writestr(
                "GLGP.DAT", dbf_bytes(GROUP_FIELDS, [{"GNAME": "ACCRUAL", "KEY": "D0001"}])
            )
            draft_common = {
                "T_PERIOD": 1,
                "T_DATE": "2026-01-20",
                "T_TRANS_DE": "Unposted accrual",
                "T_REF": "DRAFT-1",
                "T_CURR": "SGD",
                "T_EXRATE": 1,
                "KEY": "D0001",
                "GNAME": "ACCRUAL",
            }
            archive.writestr(
                "GLTRANS.DAT",
                dbf_bytes(
                    DRAFT_FIELDS,
                    [
                        {**draft_common, "T_ACC_CODE": "1000", "T_DEBIT": 50, "T_CREDIT": 0},
                        {**draft_common, "T_ACC_CODE": "4000", "T_DEBIT": 0, "T_CREDIT": 50},
                    ],
                ),
            )
    return buffer.getvalue()


def migration_company(admin_email: str, code: str = "MIGTEST") -> str:
    with SessionLocal() as db:
        existing = db.scalar(select(Company).where(Company.code == code))
        if existing is not None:
            return str(existing.id)
        assert db.get(Currency, "SGD") is not None
        company = Company(code=code, name=f"Migration Test {code}", base_currency_code="SGD")
        db.add(company)
        db.flush()
        role = Role(company_id=company.id, name="Migration administrator", system=True)
        db.add(role)
        db.flush()
        permission = db.get(Permission, "migration.run")
        assert permission is not None
        db.add(
            RolePermission(
                company_id=company.id,
                role_id=role.id,
                permission_code=permission.code,
            )
        )
        user = db.scalar(select(User).where(User.email == admin_email))
        assert user is not None
        db.add(Membership(company_id=company.id, user_id=user.id, role_id=role.id, active=True))
        year = FiscalYear(
            company_id=company.id,
            label="FY2026 migration",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
        )
        db.add(year)
        db.flush()
        db.add(
            FiscalPeriod(
                company_id=company.id,
                fiscal_year_id=year.id,
                period_no=1,
                label="P01",
                start_date=date(2026, 1, 1),
                end_date=date(2026, 1, 31),
            )
        )
        db.commit()
        return str(company.id)


def test_repeatable_read_only_stage_reconcile_apply_and_isolate(
    client: TestClient,
    admin_token: str,
    company_ids,
) -> None:
    company_id = migration_company("admin@example.com")
    headers = auth_headers(admin_token, company_id)
    source = legacy_archive(include_drafts=True)
    staged = client.post(
        "/api/v1/migration/stage",
        headers=headers,
        files={"archive": ("snapshot.zip", source, "application/zip")},
    )
    assert staged.status_code == 201, staged.text
    body = staged.json()
    assert body["counts"]["tables"] == {
        "GLACCNT": 2,
        "GLGP": 1,
        "GLMAIN": 2,
        "GLTRANS": 2,
    }
    assert body["counts"]["errors"] == 0
    assert body["reconciliation"]["apply_ready"] is True
    assert body["reconciliation"]["ledger_balanced"] is True

    repeated = client.post(
        "/api/v1/migration/stage",
        headers=headers,
        files={"archive": ("renamed.zip", source, "application/zip")},
    )
    assert repeated.status_code == 201
    assert repeated.json()["id"] == body["id"]

    applied = client.post(
        f"/api/v1/migration/runs/{body['id']}/apply",
        headers=headers,
        json={"source_digest": body["source_digest"], "confirmation": "APPLY"},
    )
    assert applied.status_code == 200, applied.text
    assert applied.json()["dry_run"] is False
    assert applied.json()["counts"]["applied_accounts"] == 2
    assert applied.json()["counts"]["applied_posted_batches"] == 1
    assert applied.json()["counts"]["applied_draft_batches"] == 1

    same_apply = client.post(
        f"/api/v1/migration/runs/{body['id']}/apply",
        headers=headers,
        json={"source_digest": body["source_digest"], "confirmation": "APPLY"},
    )
    assert same_apply.status_code == 200
    assert same_apply.json()["id"] == applied.json()["id"]
    isolated = client.get(
        f"/api/v1/migration/runs/{body['id']}",
        headers=auth_headers(admin_token, company_ids["NORTH"]),
    )
    assert isolated.status_code == 404


def test_corrupt_dbfs_produce_exceptions_and_never_apply(
    client: TestClient,
    admin_token: str,
    company_ids,
) -> None:
    headers = auth_headers(admin_token, company_ids["ACME"])
    staged = client.post(
        "/api/v1/migration/stage",
        headers=headers,
        files={"archive": ("corrupt.zip", legacy_archive(corrupt=True), "application/zip")},
    )
    assert staged.status_code == 201, staged.text
    body = staged.json()
    assert body["counts"]["errors"] > 0
    assert body["reconciliation"]["apply_ready"] is False
    assert any(row["severity"] == "error" for row in body["staging_records"])
    report = client.get(f"/api/v1/migration/runs/{body['id']}/exceptions.csv", headers=headers)
    assert report.status_code == 200
    assert b"duplicate_account" in report.content
    refused = client.post(
        f"/api/v1/migration/runs/{body['id']}/apply",
        headers=headers,
        json={"source_digest": body["source_digest"], "confirmation": "APPLY"},
    )
    assert refused.status_code == 409

    nested = io.BytesIO()
    with zipfile.ZipFile(nested, "w") as archive:
        archive.writestr("unsafe/GLACCNT.DAT", b"x")
        archive.writestr("GLMAIN.DAT", b"x")
    rejected = client.post(
        "/api/v1/migration/stage",
        headers=headers,
        files={"archive": ("nested.zip", nested.getvalue(), "application/zip")},
    )
    assert rejected.status_code == 422


def test_apply_failure_rolls_back_every_target_mutation(
    client: TestClient,
    admin_token: str,
) -> None:
    company_id = migration_company("admin@example.com", "MIGFAIL")
    headers = auth_headers(admin_token, company_id)
    staged = client.post(
        "/api/v1/migration/stage",
        headers=headers,
        files={"archive": ("failure-snapshot.zip", legacy_archive(), "application/zip")},
    )
    assert staged.status_code == 201
    body = staged.json()
    with SessionLocal() as db:
        period = db.scalar(select(FiscalPeriod).where(FiscalPeriod.company_id == company_id))
        assert period is not None
        period.status = PeriodStatus.CLOSED
        db.commit()

    refused = client.post(
        f"/api/v1/migration/runs/{body['id']}/apply",
        headers=headers,
        json={"source_digest": body["source_digest"], "confirmation": "APPLY"},
    )
    assert refused.status_code == 409
    assert "not open" in refused.text.lower()
    with SessionLocal() as db:
        assert not db.scalars(select(Account).where(Account.company_id == company_id)).all()
