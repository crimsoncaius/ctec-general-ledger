from __future__ import annotations

import pytest
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from pydantic import ValidationError

from app.config import Settings
from app.db import engine
from app.main import app


def test_production_configuration_rejects_default_secrets_and_wildcard_cors() -> None:
    with pytest.raises(ValidationError, match="independently generated JWT_SECRET"):
        Settings(
            environment="production",
            jwt_secret="development-secret-change-before-use-123456",
            _env_file=None,
        )
    with pytest.raises(ValidationError, match="cannot contain a wildcard"):
        Settings(
            environment="production",
            jwt_secret="production-only-secret-with-at-least-32-characters",
            cors_origins="*",
            _env_file=None,
        )

    settings = Settings(
        environment="production",
        jwt_secret="production-only-secret-with-at-least-32-characters",
        cors_origins="https://ledger.example.com, https://admin.example.com",
        _env_file=None,
    )
    assert settings.cors_origin_list == [
        "https://ledger.example.com",
        "https://admin.example.com",
    ]


def test_openapi_contract_keeps_critical_secured_workflows() -> None:
    document = app.openapi()
    paths = document["paths"]
    expected_operations = {
        "/api/v1/auth/token": "post",
        "/api/v1/auth/me": "get",
        "/api/v1/accounts": "post",
        "/api/v1/fiscal/years": "post",
        "/api/v1/journals": "post",
        "/api/v1/journals/{batch_id}/post": "post",
        "/api/v1/journals/entries/{entry_id}/reverse": "post",
        "/api/v1/ledger/integrity": "post",
        "/api/v1/reports/run": "post",
        "/api/v1/migration/stage": "post",
    }
    for path, method in expected_operations.items():
        assert method in paths[path]
        if path != "/api/v1/auth/token":
            assert paths[path][method]["security"] == [{"HTTPBearer": []}]


def test_database_revision_matches_the_single_alembic_head(migrated_database: None) -> None:
    config = Config("backend/alembic.ini")
    script = ScriptDirectory.from_config(config)
    heads = script.get_heads()
    assert len(heads) == 1
    with engine.connect() as connection:
        assert MigrationContext.configure(connection).get_current_revision() == heads[0]
