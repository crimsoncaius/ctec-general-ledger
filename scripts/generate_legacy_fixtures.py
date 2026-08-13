# ruff: noqa: FURB157
"""Generate deterministic, synthetic DBF migration fixtures and signed control totals."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import struct
import zipfile
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PROFILE_FILE = ROOT / "backend/tests/fixtures/legacy_dbf/profiles.json"
DEFAULT_OUTPUT = ROOT / "artifacts/legacy-fixtures"
Field = tuple[str, str, int, int]

ACCOUNT_FIELDS: list[Field] = [
    ("A_ACC_CODE", "C", 10, 0),
    ("DESC", "C", 40, 0),
    ("ACC_TYPE", "C", 1, 0),
    ("OPEN_BAL", "N", 17, 3),
    ("CURR_BAL", "N", 17, 3),
    *[(f"BAL_{number}", "N", 17, 3) for number in range(1, 19)],
    *[(f"BUG_{number}", "N", 17, 3) for number in range(1, 19)],
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
REPORT_FIELDS: list[Field] = [
    ("NAME", "C", 30, 0),
    ("SPEC", "C", 120, 0),
    ("REP", "C", 80, 0),
]


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
            else:
                text = f"{Decimal(str(value)):.{decimals}f}" if value != "" else ""
                encoded = text.encode("ascii").rjust(width, b" ")
            body.extend(encoded)
    return bytes(header + descriptors + b"\r" + body + b"\x1a")


def build_profile(name: str, profile: dict[str, Any]) -> tuple[bytes, dict[str, Any]]:
    periods = int(profile["periods"])
    pair_count = int(profile["account_pairs"])
    group_count = int(profile["posted_groups"])
    faults = set(profile.get("faults", []))
    accounts: list[dict[str, object]] = []
    for pair in range(pair_count):
        debit_code = f"1{pair:03d}"
        credit_code = f"4{pair:03d}"
        debit = {
            "A_ACC_CODE": debit_code,
            "DESC": f"Synthetic asset {pair}",
            "ACC_TYPE": "B",
            "OPEN_BAL": 0,
            "CURR": "SGD",
        }
        credit = {
            "A_ACC_CODE": credit_code,
            "DESC": f"Synthetic income {pair}",
            "ACC_TYPE": "I",
            "OPEN_BAL": 0,
            "CURR": "SGD",
        }
        for period in range(1, 19):
            debit[f"BAL_{period}"] = Decimal("0")
            credit[f"BAL_{period}"] = Decimal("0")
            debit[f"BUG_{period}"] = (
                Decimal(period) if period <= periods else Decimal("0")
            )
            credit[f"BUG_{period}"] = (
                -Decimal(period) if period <= periods else Decimal("0")
            )
        accounts.extend((debit, credit))
    transactions: list[dict[str, object]] = []
    for group in range(group_count):
        pair = group % pair_count
        period = group % periods + 1
        amount = Decimal(group % 97 + 1)
        when = date(2026, 1, 1) + timedelta(days=period - 1)
        key = f"K{group:06d}"
        common = {
            "M_PERIOD": period,
            "M_DATE": when.isoformat(),
            "M_TRANS_DE": "Synthetic migration fixture",
            "M_REF": f"R{group:06d}",
            "M_GNAME": "SYNTH",
            "M_CURR": "SGD",
            "M_EXRATE": 1,
            "KEY": key,
        }
        transactions.extend(
            (
                {
                    **common,
                    "M_ACC_CODE": f"1{pair:03d}",
                    "M_DEBIT": amount,
                    "M_CREDIT": 0,
                    "M_DEBITX": amount,
                    "M_CREDITX": 0,
                    "RECNO": group * 2 + 1,
                },
                {
                    **common,
                    "M_ACC_CODE": f"4{pair:03d}",
                    "M_DEBIT": 0,
                    "M_CREDIT": amount,
                    "M_DEBITX": 0,
                    "M_CREDITX": amount,
                    "RECNO": group * 2 + 2,
                },
            )
        )
        accounts[pair * 2][f"BAL_{period}"] = (
            Decimal(str(accounts[pair * 2][f"BAL_{period}"])) + amount
        )
        accounts[pair * 2 + 1][f"BAL_{period}"] = (
            Decimal(str(accounts[pair * 2 + 1][f"BAL_{period}"])) - amount
        )
    for account in accounts:
        account["CURR_BAL"] = sum(
            (
                Decimal(str(account[f"BAL_{period}"]))
                for period in range(1, periods + 1)
            ),
            Decimal("0"),
        )
    if "duplicate_account" in faults:
        accounts[1]["A_ACC_CODE"] = accounts[0]["A_ACC_CODE"]
    if "orphan_transaction" in faults:
        transactions[-1]["M_ACC_CODE"] = "9999"
    if "invalid_period" in faults:
        transactions[0]["M_PERIOD"] = periods + 1
    if "unbalanced_group" in faults:
        transactions[-1]["M_CREDIT"] = Decimal(
            str(transactions[-1]["M_CREDIT"])
        ) - Decimal("0.5")

    files = {
        "GLACCNT.DAT": dbf_bytes(ACCOUNT_FIELDS, accounts),
        "GLMAIN.DAT": dbf_bytes(MAIN_FIELDS, transactions),
    }
    draft_count = 0
    if profile.get("include_drafts"):
        draft_count = 1
        files["GLGP.DAT"] = dbf_bytes(
            GROUP_FIELDS, [{"GNAME": "SYNTHDR", "KEY": "D000001"}]
        )
        files["GLTRANS.DAT"] = dbf_bytes(
            DRAFT_FIELDS,
            [
                {
                    "T_ACC_CODE": "1000",
                    "T_PERIOD": 1,
                    "T_DATE": "2026-01-01",
                    "T_TRANS_DE": "Synthetic draft",
                    "T_REF": "DRAFT",
                    "T_DEBIT": 10,
                    "T_CREDIT": 0,
                    "T_CURR": "SGD",
                    "T_EXRATE": 1,
                    "KEY": "D000001",
                    "GNAME": "SYNTHDR",
                },
                {
                    "T_ACC_CODE": "4000",
                    "T_PERIOD": 1,
                    "T_DATE": "2026-01-01",
                    "T_TRANS_DE": "Synthetic draft",
                    "T_REF": "DRAFT",
                    "T_DEBIT": 0,
                    "T_CREDIT": 10,
                    "T_CURR": "SGD",
                    "T_EXRATE": 1,
                    "KEY": "D000001",
                    "GNAME": "SYNTHDR",
                },
            ],
        )
    if profile.get("include_title_and_retained_earnings"):
        title = {
            "A_ACC_CODE": "0000",
            "DESC": "Synthetic title",
            "ACC_TYPE": "T",
            "OPEN_BAL": 0,
            "CURR_BAL": 0,
            "CURR": "SGD",
        }
        retained = {
            "A_ACC_CODE": "3999",
            "DESC": "Synthetic retained earnings",
            "ACC_TYPE": "R",
            "OPEN_BAL": 0,
            "CURR_BAL": 0,
            "CURR": "SGD",
        }
        accounts.extend((title, retained))
        files["GLACCNT.DAT"] = dbf_bytes(ACCOUNT_FIELDS, accounts)
    if profile.get("include_reports"):
        files["GLREP.DAT"] = dbf_bytes(
            REPORT_FIELDS,
            [
                {
                    "NAME": "Synthetic trial balance",
                    "SPEC": "A: [BP1] [BP2]\\n1: [1000,4999]",
                    "REP": "Synthetic only",
                }
            ],
        )

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for filename, content in sorted(files.items()):
            archive.writestr(filename, content)
    archive_bytes = buffer.getvalue()
    total_debit = sum(
        (Decimal(str(row["M_DEBIT"])) for row in transactions), Decimal("0")
    )
    total_credit = sum(
        (Decimal(str(row["M_CREDIT"])) for row in transactions), Decimal("0")
    )
    controls = {
        "schema_version": 1,
        "profile": name,
        "source_kind": "synthetic",
        "archive_sha256": hashlib.sha256(archive_bytes).hexdigest(),
        "expected_status": profile["expected_status"],
        "counts": {
            "accounts": len(accounts),
            "posted_groups": group_count,
            "posted_lines": len(transactions),
            "draft_groups": draft_count,
        },
        "totals": {
            "opening_net": "0",
            "ledger_debits": str(total_debit),
            "ledger_credits": str(total_credit),
        },
        "periods": periods,
        "expected_faults": sorted(faults),
    }
    return archive_bytes, controls


def generate(output: Path, *, write: bool) -> dict[str, Any]:
    configuration = json.loads(PROFILE_FILE.read_text(encoding="utf-8"))
    result: dict[str, Any] = {
        "schema_version": 1,
        "profile_source_sha256": hashlib.sha256(PROFILE_FILE.read_bytes()).hexdigest(),
        "fixtures": {},
    }
    for name, profile in configuration["profiles"].items():
        archive, controls = build_profile(name, profile)
        result["fixtures"][name] = controls
        if write:
            output.mkdir(parents=True, exist_ok=True)
            (output / f"{name}.zip").write_bytes(archive)
            (output / f"{name}.controls.json").write_text(
                json.dumps(controls, indent=2) + "\n", encoding="utf-8"
            )
    if write:
        (output / "manifest.json").write_text(
            json.dumps(result, indent=2) + "\n", encoding="utf-8"
        )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Generate in memory and validate determinism without writing files",
    )
    args = parser.parse_args()
    first = generate(args.output, write=not args.check)
    second = generate(args.output, write=False)
    if first != second:
        raise SystemExit("Fixture generation is not deterministic")
    print(
        json.dumps(
            {
                "status": "ok",
                "mode": "check" if args.check else "write",
                "profiles": sorted(first["fixtures"]),
                "output": str(args.output) if not args.check else None,
            }
        )
    )


if __name__ == "__main__":
    main()
