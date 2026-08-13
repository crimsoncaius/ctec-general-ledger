from __future__ import annotations

import io
import zipfile
from datetime import date
from decimal import Decimal

import pytest
from fastapi import HTTPException

import app.services.legacy_dbf as legacy_dbf


def _zip(files: list[tuple[str, bytes]]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, content in files:
            archive.writestr(name, content)
    return buffer.getvalue()


def test_archive_size_type_flatness_duplicates_and_required_tables(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(HTTPException) as empty:
        legacy_dbf.extract_archive(b"")
    assert empty.value.status_code == 413

    monkeypatch.setattr(legacy_dbf, "MAX_ARCHIVE_BYTES", 1)
    with pytest.raises(HTTPException) as oversized:
        legacy_dbf.extract_archive(b"ab")
    assert oversized.value.status_code == 413
    monkeypatch.setattr(legacy_dbf, "MAX_ARCHIVE_BYTES", 100 * 1024 * 1024)

    with pytest.raises(HTTPException, match="must be a ZIP archive"):
        legacy_dbf.extract_archive(b"not-a-zip")
    with pytest.raises(HTTPException, match="flat filenames"):
        legacy_dbf.extract_archive(_zip([("../GLACCNT.DAT", b"bad"), ("GLMAIN.DAT", b"bad")]))
    with pytest.raises(HTTPException, match="Duplicate archive member"):
        legacy_dbf.extract_archive(
            _zip(
                [
                    ("GLACCNT.DAT", b"bad"),
                    ("glaccnt.dat", b"bad"),
                    ("GLMAIN.DAT", b"bad"),
                ]
            )
        )
    with pytest.raises(HTTPException, match="must contain GLACCNT"):
        legacy_dbf.extract_archive(_zip([("GLMAIN.DAT", b"bad")]))


def test_archive_expansion_file_count_and_unreadable_dbf_guards(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    too_many = [("GLACCNT.DAT", b"bad"), ("GLMAIN.DAT", b"bad")]
    too_many.extend((f"IGNORED-{index}.TXT", b"x") for index in range(legacy_dbf.MAX_FILES))
    with pytest.raises(HTTPException) as count_error:
        legacy_dbf.extract_archive(_zip(too_many))
    assert count_error.value.status_code == 413

    monkeypatch.setattr(legacy_dbf, "MAX_EXPANDED_BYTES", 3)
    with pytest.raises(HTTPException) as expansion_error:
        legacy_dbf.extract_archive(_zip([("GLACCNT.DAT", b"aa"), ("GLMAIN.DAT", b"bb")]))
    assert expansion_error.value.status_code == 413
    monkeypatch.setattr(legacy_dbf, "MAX_EXPANDED_BYTES", 250 * 1024 * 1024)

    with pytest.raises(HTTPException, match="Unable to read GLACCNT.DAT"):
        legacy_dbf.extract_archive(_zip([("GLACCNT.DAT", b"bad"), ("GLMAIN.DAT", b"bad")]))


def test_legacy_normalization_decimal_currency_and_severity_helpers() -> None:
    issues: list[dict[str, object]] = []
    assert legacy_dbf._decimal(None, "VALUE", issues) == 0
    assert legacy_dbf._decimal("12.50", "VALUE", issues) == Decimal("12.50")
    assert legacy_dbf._decimal("bad", "VALUE", issues) == 0
    assert issues[0]["code"] == "malformed_number"

    normalized = legacy_dbf._normalize(
        {
            "decimal": Decimal("1.25"),
            "date": date(2026, 1, 1),
            "bytes": "cafÃ©".encode("cp1252"),
            "plain": 7,
        }
    )
    assert normalized == {
        "DECIMAL": "1.25",
        "DATE": "2026-01-01",
        "BYTES": "cafÃ©",
        "PLAIN": 7,
    }
    assert legacy_dbf._currency({}, "", "SGD") == "SGD"
    assert legacy_dbf._currency({"M_CURR": " usd "}, "M", "SGD") == "USD"
    assert legacy_dbf._severity([]) == "ok"
    assert legacy_dbf._severity([legacy_dbf._issue("warn", "warning", blocking=False)]) == "warning"
    assert legacy_dbf._severity([legacy_dbf._issue("error", "error")]) == "error"
