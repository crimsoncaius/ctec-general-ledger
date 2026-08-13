from decimal import Decimal

from fastapi.testclient import TestClient

from tests.conftest import auth_headers


def test_standard_reports_reconcile_export_and_reproduce(
    client: TestClient,
    admin_token: str,
    company_ids,
    acme_ledger,
) -> None:
    headers = auth_headers(admin_token, company_ids["ACME"])
    request = {
        "report_type": "trial_balance",
        "parameters": {"period_id": str(acme_ledger["period_id"]), "include_zero": True},
        "format": "json",
    }
    trial = client.post("/api/v1/reports/run", headers=headers, json=request)
    assert trial.status_code == 200, trial.text
    body = trial.json()
    debits = sum(
        (Decimal(row["debit"]) for row in body["rows"] if not row.get("title")), Decimal("0")
    )
    credits = sum(
        (Decimal(row["credit"]) for row in body["rows"] if not row.get("title")), Decimal("0")
    )
    assert debits == credits

    reproduced = client.post(f"/api/v1/reports/runs/{body['run_id']}/reproduce", headers=headers)
    assert reproduced.status_code == 200
    assert reproduced.json()["digest"] == body["digest"]

    chart_request = {
        "report_type": "chart_of_accounts",
        "parameters": {"code_from": "1000", "code_to": "9000"},
    }
    for output_format, signature in (
        ("csv", b"\xef\xbb\xbf"),
        ("xlsx", b"PK"),
        ("pdf", b"%PDF"),
    ):
        exported = client.post(
            "/api/v1/reports/run",
            headers=headers,
            json={**chart_request, "format": output_format},
        )
        assert exported.status_code == 200, exported.text
        assert exported.content.startswith(signature)
        assert exported.headers["x-report-run-id"]
        assert exported.headers["x-report-digest"]

    groups = client.post(
        "/api/v1/reports/run",
        headers=headers,
        json={"report_type": "transaction_groups", "parameters": {}, "format": "json"},
    )
    assert groups.status_code == 200
    assert all(row["balanced"] for row in groups.json()["rows"])

    runs = client.get("/api/v1/reports/runs", headers=headers)
    assert runs.status_code == 200
    assert len(runs.json()) >= 6


def test_report_runs_are_company_isolated(
    client: TestClient,
    admin_token: str,
    company_ids,
) -> None:
    acme_headers = auth_headers(admin_token, company_ids["ACME"])
    north_headers = auth_headers(admin_token, company_ids["NORTH"])
    created = client.post(
        "/api/v1/reports/run",
        headers=acme_headers,
        json={"report_type": "chart_of_accounts", "parameters": {}, "format": "json"},
    ).json()
    response = client.post(
        f"/api/v1/reports/runs/{created['run_id']}/reproduce", headers=north_headers
    )
    assert response.status_code == 404
