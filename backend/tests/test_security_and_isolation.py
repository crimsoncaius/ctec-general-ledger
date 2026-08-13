from fastapi.testclient import TestClient

from tests.conftest import auth_headers


def test_authentication_and_capabilities(
    client: TestClient,
    preparer_token: str,
    company_ids,
) -> None:
    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {preparer_token}"})
    assert response.status_code == 200
    assert len(response.json()["companies"]) == 2

    response = client.post(
        "/api/v1/accounts",
        headers=auth_headers(preparer_token, company_ids["ACME"]),
        json={
            "code": "7777",
            "name": "Should be denied",
            "account_type": "balance_sheet",
            "currency_code": "SGD",
        },
    )
    assert response.status_code == 403


def test_company_context_prevents_cross_tenant_reads(
    client: TestClient,
    admin_token: str,
    company_ids,
    journal_payload,
) -> None:
    created = client.post(
        "/api/v1/journals",
        headers=auth_headers(admin_token, company_ids["ACME"]),
        json=journal_payload,
    )
    assert created.status_code == 201, created.text

    response = client.get(
        f"/api/v1/journals/{created.json()['id']}",
        headers=auth_headers(admin_token, company_ids["NORTH"]),
    )
    assert response.status_code == 404


def test_company_header_is_mandatory(client: TestClient, admin_token: str) -> None:
    response = client.get("/api/v1/accounts", headers={"Authorization": f"Bearer {admin_token}"})
    assert response.status_code == 400
