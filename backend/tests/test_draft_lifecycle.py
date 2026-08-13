from fastapi.testclient import TestClient

from tests.conftest import auth_headers


def test_draft_update_copy_delete_and_immutability_boundary(
    client: TestClient,
    admin_token: str,
    company_ids,
    journal_payload,
) -> None:
    headers = auth_headers(admin_token, company_ids["ACME"])
    created = client.post("/api/v1/journals", headers=headers, json=journal_payload)
    assert created.status_code == 201
    batch_id = created.json()["id"]

    copied = client.post(f"/api/v1/journals/{batch_id}/copy", headers=headers)
    assert copied.status_code == 201, copied.text
    assert copied.json()["description"].startswith("Copy of")
    copy_id = copied.json()["id"]
    deleted = client.delete(f"/api/v1/journals/{copy_id}", headers=headers)
    assert deleted.status_code == 204
    assert client.get(f"/api/v1/journals/{copy_id}", headers=headers).status_code == 404

    revised_payload = {**journal_payload, "description": "Revised controlled draft"}
    revised_payload["entries"][0]["description"] = "Revised controlled draft"
    updated = client.put(f"/api/v1/journals/{batch_id}", headers=headers, json=revised_payload)
    assert updated.status_code == 200, updated.text
    assert updated.json()["description"] == "Revised controlled draft"

    validated = client.post(f"/api/v1/journals/{batch_id}/validate", headers=headers)
    assert validated.status_code == 200
    assert (
        client.put(
            f"/api/v1/journals/{batch_id}", headers=headers, json=revised_payload
        ).status_code
        == 409
    )
    assert client.delete(f"/api/v1/journals/{batch_id}", headers=headers).status_code == 409
