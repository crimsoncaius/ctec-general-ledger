from decimal import Decimal

from fastapi.testclient import TestClient

from tests.conftest import auth_headers


def post_test_journal(
    client: TestClient, headers: dict[str, str], journal_payload: dict[str, object]
) -> None:
    batch = client.post("/api/v1/journals", headers=headers, json=journal_payload)
    assert batch.status_code == 201, batch.text
    batch_id = batch.json()["id"]
    for action in ("validate", "approve", "post"):
        response = client.post(f"/api/v1/journals/{batch_id}/{action}", headers=headers)
        assert response.status_code == 200, response.text


def structured_definition(period_id: object) -> dict[str, object]:
    return {
        "title": "Management statement — {company_name} — {period_label}",
        "columns": [
            {
                "key": "actual",
                "label": "Actual",
                "kind": "balance",
                "period_id": str(period_id),
                "scope": "period",
            },
            {
                "key": "double_actual",
                "label": "Double actual",
                "kind": "formula",
                "formula": "actual * 2",
            },
        ],
        "rows": [
            {"key": "cash", "label": "Cash", "kind": "account", "account_code": "1000"},
            {
                "key": "sales",
                "label": "Sales",
                "kind": "account",
                "account_code": "4000",
            },
            {
                "key": "net",
                "label": "Net movement",
                "kind": "formula",
                "formula": "cash + sales",
                "bold": True,
            },
        ],
        "sections": [{"title": "Operating result", "row_keys": ["cash", "sales", "net"]}],
        "formatting": {"decimals": 2},
    }


def test_structured_designer_matrix_lifecycle_exports_and_isolation(
    client: TestClient,
    admin_token: str,
    company_ids,
    acme_ledger,
    journal_payload,
) -> None:
    headers = auth_headers(admin_token, company_ids["ACME"])
    post_test_journal(client, headers, journal_payload)
    definition = structured_definition(acme_ledger["period_id"])

    preview = client.post(
        "/api/v1/custom-reports/designer/preview",
        headers=headers,
        json={"definition": definition, "parameters": {}},
    )
    assert preview.status_code == 200, preview.text
    preview_rows = {row["label"]: row for row in preview.json()["rows"]}
    cash = Decimal(preview_rows["Cash"]["actual"])
    sales = Decimal(preview_rows["Sales"]["actual"])
    assert cash >= Decimal("125.55")
    assert sales == -cash
    assert Decimal(preview_rows["Cash"]["double_actual"]) == cash * 2
    assert Decimal(preview_rows["Net movement"]["actual"]) == Decimal("0.00")

    created = client.post(
        "/api/v1/custom-reports",
        headers=headers,
        json={"name": "Management statement", "definition": definition, "is_template": True},
    )
    assert created.status_code == 201, created.text
    report_id = created.json()["id"]
    assert created.json()["version"] == 1

    run = client.post(
        f"/api/v1/custom-reports/{report_id}/run",
        headers=headers,
        json={"parameters": {}, "format": "json"},
    )
    assert run.status_code == 200, run.text
    assert run.json()["digest"] == preview.json()["digest"]
    for output_format, signature in (("csv", b"\xef\xbb\xbf"), ("xlsx", b"PK"), ("pdf", b"%PDF")):
        exported = client.post(
            f"/api/v1/custom-reports/{report_id}/run",
            headers=headers,
            json={"parameters": {}, "format": output_format},
        )
        assert exported.status_code == 200, exported.text
        assert exported.content.startswith(signature)

    stale = client.put(
        f"/api/v1/custom-reports/{report_id}",
        headers=headers,
        json={
            "name": "Management statement revised",
            "definition": definition,
            "is_template": False,
            "version": 0,
        },
    )
    assert stale.status_code == 422
    revised = client.put(
        f"/api/v1/custom-reports/{report_id}",
        headers=headers,
        json={
            "name": "Management statement revised",
            "definition": definition,
            "is_template": False,
            "version": 1,
        },
    )
    assert revised.status_code == 200 and revised.json()["version"] == 2
    repeated = client.put(
        f"/api/v1/custom-reports/{report_id}",
        headers=headers,
        json={
            "name": "Stale update",
            "definition": definition,
            "is_template": False,
            "version": 1,
        },
    )
    assert repeated.status_code == 409

    clone = client.post(f"/api/v1/custom-reports/{report_id}/clone", headers=headers)
    assert clone.status_code == 201 and clone.json()["is_template"] is False
    north = client.get(
        f"/api/v1/custom-reports/{report_id}",
        headers=auth_headers(admin_token, company_ids["NORTH"]),
    )
    assert north.status_code == 404


def test_formula_sandbox_and_legacy_compatibility_flags(
    client: TestClient,
    admin_token: str,
    company_ids,
    acme_ledger,
) -> None:
    headers = auth_headers(admin_token, company_ids["ACME"])
    unsafe = structured_definition(acme_ledger["period_id"])
    columns = unsafe["columns"]
    assert isinstance(columns, list) and isinstance(columns[1], dict)
    columns[1]["formula"] = "__import__('os')"
    rejected = client.post(
        "/api/v1/custom-reports",
        headers=headers,
        json={"name": "Unsafe", "definition": unsafe},
    )
    assert rejected.status_code == 422

    bad_title = structured_definition(acme_ledger["period_id"])
    bad_title["title"] = "Unsupported {secret_value}"
    rejected_title = client.post(
        "/api/v1/custom-reports/designer/preview",
        headers=headers,
        json={"definition": bad_title, "parameters": {}},
    )
    assert rejected_title.status_code == 422

    legacy = {
        "name": "Legacy balance",
        "spec": "* Title: Legacy balance\nA: [BP1]\n0: 1000\n1: 4000\n2: =",
        "template": "",
    }
    preview = client.post("/api/v1/custom-reports/legacy/preview", headers=headers, json=legacy)
    assert preview.status_code == 200, preview.text
    assert preview.json()["status"] == "compatible"
    imported = client.post("/api/v1/custom-reports/legacy/import", headers=headers, json=legacy)
    assert imported.status_code == 201, imported.text
    assert imported.json()["conversion_status"] == "compatible"

    manual = client.post(
        "/api/v1/custom-reports/legacy/preview",
        headers=headers,
        json={"name": "Manual", "spec": "A: [BO]\n0: nonsense + malformed", "template": "{\\rtf1}"},
    )
    assert manual.status_code == 200
    assert manual.json()["status"] == "manual"
    assert manual.json()["warnings"]
