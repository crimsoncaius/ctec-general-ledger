import io

from fastapi.testclient import TestClient

from tests.conftest import auth_headers


def upload(name: str, content: str) -> dict[str, tuple[str, io.BytesIO, str]]:
    return {"file": (name, io.BytesIO(content.encode()), "text/csv")}


def test_account_and_journal_imports_are_previewed_atomic_and_repeat_safe(
    client: TestClient,
    admin_token: str,
    company_ids,
    acme_ledger,
) -> None:
    headers = auth_headers(admin_token, company_ids["ACME"])
    accounts_csv = (
        "code,name,account_type,currency_code,postable\n"
        "7770,Imported clearing,balance_sheet,SGD,true\n"
    )
    preview = client.post(
        "/api/v1/imports/accounts/preview",
        headers=headers,
        files=upload("accounts.csv", accounts_csv),
    )
    assert preview.status_code == 200
    assert preview.json()["valid"] == 1 and not preview.json()["errors"]
    applied = client.post(
        "/api/v1/imports/accounts/apply",
        headers=headers,
        files=upload("accounts.csv", accounts_csv),
    )
    assert applied.status_code == 200, applied.text
    assert applied.json()["created"] == 1
    assert (
        client.post(
            "/api/v1/imports/accounts/apply",
            headers=headers,
            files=upload("accounts.csv", accounts_csv),
        ).status_code
        == 409
    )

    journal_csv = (
        "group_key,entry_date,posting_date,fiscal_period_id,reference,description,"
        "account_code,currency_code,exchange_rate,debit,credit,line_description\n"
        f"IMP-1,{acme_ledger['period_start']},{acme_ledger['period_start']},"
        f"{acme_ledger['period_id']},CSV-1,Imported balanced journal,1000,SGD,1,88.25,0,Debit\n"
        f"IMP-1,{acme_ledger['period_start']},{acme_ledger['period_start']},"
        f"{acme_ledger['period_id']},CSV-1,Imported balanced journal,4000,SGD,1,0,88.25,Credit\n"
    )
    preview = client.post(
        "/api/v1/imports/journals/preview",
        headers=headers,
        files=upload("journals.csv", journal_csv),
    )
    assert preview.status_code == 200, preview.text
    assert preview.json()["entries"] == 1 and not preview.json()["errors"]
    applied = client.post(
        "/api/v1/imports/journals/apply",
        headers=headers,
        files=upload("journals.csv", journal_csv),
    )
    assert applied.status_code == 200, applied.text
    batch_id = applied.json()["batch_id"]

    for action in ("validate", "approve", "post"):
        result = client.post(
            "/api/v1/journals/bulk",
            headers=headers,
            json={"batch_ids": [batch_id], "action": action},
        )
        assert result.status_code == 200, result.text
        assert result.json()["succeeded"] == [batch_id]
    assert client.post("/api/v1/ledger/integrity", headers=headers).json()["ok"] is True
    assert (
        client.post(
            "/api/v1/imports/journals/apply",
            headers=headers,
            files=upload("journals.csv", journal_csv),
        ).status_code
        == 409
    )


def test_user_roles_saved_views_preferences_audit_and_background_jobs(
    client: TestClient,
    admin_token: str,
    company_ids,
    acme_ledger,
) -> None:
    headers = auth_headers(admin_token, company_ids["ACME"])
    role = client.post(
        "/api/v1/administration/roles",
        headers=headers,
        json={"name": "Read-only analyst", "permissions": ["accounts.view", "reports.run"]},
    )
    assert role.status_code == 201, role.text
    user = client.post(
        "/api/v1/administration/users",
        headers=headers,
        json={
            "email": "analyst@example.com",
            "display_name": "Avery Analyst",
            "password": "Local-Analyst-2026!",
            "role_id": role.json()["id"],
        },
    )
    assert user.status_code == 201, user.text
    assert user.json()["role_name"] == "Read-only analyst"

    view = client.post(
        "/api/v1/administration/saved-views",
        headers=headers,
        json={
            "resource": "general_ledger",
            "name": "First-period activity",
            "definition": {"period_id": str(acme_ledger["period_id"]), "include_zero": False},
            "shared": True,
        },
    )
    assert view.status_code == 201
    preference = client.put(
        "/api/v1/administration/preferences/display",
        headers=headers,
        json={"value": {"density": "compact", "date_format": "YYYY-MM-DD"}},
    )
    assert preference.status_code == 200
    assert preference.json()["value"]["density"] == "compact"

    operation = client.post(
        "/api/v1/administration/operations",
        headers=headers,
        json={"kind": "integrity", "parameters": {}},
    )
    assert operation.status_code == 202
    operations = client.get("/api/v1/administration/operations", headers=headers)
    completed = next(item for item in operations.json() if item["id"] == operation.json()["id"])
    assert completed["status"] == "succeeded"
    assert completed["result"]["ok"] is True

    audit = client.get("/api/v1/administration/audit", headers=headers)
    assert audit.status_code == 200
    actions = {event["action"] for event in audit.json()}
    assert "administration.role_created" in actions
    assert "administration.user_added" in actions
