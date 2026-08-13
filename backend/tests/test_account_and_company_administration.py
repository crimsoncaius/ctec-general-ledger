from fastapi.testclient import TestClient

from tests.conftest import auth_headers


def test_account_lifecycle_company_settings_and_capability_editor(
    client: TestClient,
    admin_token: str,
    company_ids,
    acme_ledger,
) -> None:
    headers = auth_headers(admin_token, company_ids["ACME"])
    created = client.post(
        "/api/v1/accounts",
        headers=headers,
        json={
            "code": "7200",
            "name": "Lifecycle account",
            "account_type": "balance_sheet",
            "currency_code": "SGD",
            "postable": True,
        },
    )
    assert created.status_code == 201, created.text
    account_id = created.json()["id"]
    updated = client.put(
        f"/api/v1/accounts/{account_id}",
        headers=headers,
        json={"name": "Lifecycle account revised", "postable": True, "active": True},
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Lifecycle account revised"

    period_id = acme_ledger["period_id"]
    posting_date = acme_ledger["period_start"]
    cash_id = acme_ledger["accounts"]["1000"]
    draft = client.post(
        "/api/v1/journals",
        headers=headers,
        json={
            "description": "Account deactivation guard",
            "entries": [
                {
                    "entry_date": posting_date,
                    "posting_date": posting_date,
                    "fiscal_period_id": str(period_id),
                    "reference": "ACCOUNT-GUARD",
                    "description": "Account deactivation guard",
                    "lines": [
                        {
                            "account_id": account_id,
                            "currency_code": "SGD",
                            "debit": "1.00",
                            "credit": "0",
                        },
                        {
                            "account_id": str(cash_id),
                            "currency_code": "SGD",
                            "debit": "0",
                            "credit": "1.00",
                        },
                    ],
                }
            ],
        },
    )
    assert draft.status_code == 201, draft.text
    protected = client.put(
        f"/api/v1/accounts/{account_id}",
        headers=headers,
        json={"name": "Lifecycle account revised", "postable": True, "active": False},
    )
    assert protected.status_code == 409

    company = client.get("/api/v1/administration/company", headers=headers)
    assert company.status_code == 200
    settings = client.put(
        "/api/v1/administration/company",
        headers=headers,
        json={
            "name": company.json()["name"],
            "timezone": "Asia/Singapore",
            "rounding_places": 2,
            "use_bankers_rounding": True,
        },
    )
    assert settings.status_code == 200
    assert settings.json()["base_currency_code"] == "SGD"

    permissions = client.get("/api/v1/administration/permissions", headers=headers)
    assert permissions.status_code == 200
    assert any(item["code"] == "reports.run" for item in permissions.json())
    role = client.post(
        "/api/v1/administration/roles",
        headers=headers,
        json={"name": "Lifecycle test analyst", "permissions": ["reports.run"]},
    )
    assert role.status_code == 201
    role_id = role.json()["id"]
    saved = client.put(
        f"/api/v1/administration/roles/{role_id}/permissions",
        headers=headers,
        json={"permissions": ["accounts.view", "reports.run"]},
    )
    assert saved.status_code == 200
    current = client.get(f"/api/v1/administration/roles/{role_id}/permissions", headers=headers)
    assert current.json()["permissions"] == ["accounts.view", "reports.run"]

    north_account = client.get(
        "/api/v1/accounts", headers=auth_headers(admin_token, company_ids["NORTH"])
    ).json()[0]
    isolated = client.put(
        f"/api/v1/accounts/{north_account['id']}",
        headers=headers,
        json={"name": "Cross-company", "postable": True, "active": True},
    )
    assert isolated.status_code == 404
