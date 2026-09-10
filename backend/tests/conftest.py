from __future__ import annotations

import os
import sys
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

sys.path.insert(0, os.path.abspath("backend/src"))

from ctg_go.db.base import Base  # noqa: E402
from ctg_go.db.models import import_models  # noqa: E402
from ctg_go.main import create_app  # noqa: E402
from ctg_go.modules.clients.models import Client  # noqa: E402
from ctg_go.modules.cpe.models import CPEDraft  # noqa: E402
from ctg_go.modules.gestions.models import Gestion  # noqa: E402
from ctg_go.modules.identity.models import Organization, User  # noqa: E402


@pytest.fixture()
def client() -> TestClient:
    import_models()
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(engine)

    app = create_app(engine=engine, token_secret="test-secret")

    session = app.state.session_factory()
    try:
        org1 = Organization(id=uuid.uuid4(), name="Org1")
        org2 = Organization(id=uuid.uuid4(), name="Org2")
        session.add_all([org1, org2])
        session.flush()

        admin1 = User(
            id=uuid.uuid4(),
            organization_id=org1.id,
            email="admin1@test.local",
            password_hash="adminpass",
            full_name="Admin 1",
            role="admin",
            is_active=True,
        )
        op1 = User(
            id=uuid.uuid4(),
            organization_id=org1.id,
            email="op1@test.local",
            password_hash="op1pass",
            full_name="Operator 1",
            role="operator",
            is_active=True,
        )
        op2 = User(
            id=uuid.uuid4(),
            organization_id=org1.id,
            email="op2@test.local",
            password_hash="op2pass",
            full_name="Operator 2",
            role="operator",
            is_active=True,
        )
        admin2 = User(
            id=uuid.uuid4(),
            organization_id=org2.id,
            email="admin2@test.local",
            password_hash="admin2pass",
            full_name="Admin 2",
            role="admin",
            is_active=True,
        )
        session.add_all([admin1, op1, op2, admin2])
        session.flush()

        cli = Client(
            id=uuid.uuid4(),
            organization_id=org1.id,
            cuit="20123456789",
            business_name="Cliente Uno",
            alias="C1",
        )
        session.add(cli)
        session.flush()

        gestion = Gestion(
            id=uuid.uuid4(),
            organization_id=org1.id,
            client_id=cli.id,
            code="G-001",
            status="open",
            created_by_user_id=op1.id,
        )
        session.add(gestion)
        session.flush()

        cpe = CPEDraft(
            id=uuid.uuid4(),
            organization_id=org1.id,
            gestion_id=gestion.id,
            title="Borrador",
            payload_json={"k": "v"},
            status="draft",
            created_by_user_id=op1.id,
            responsible_user_id=op1.id,
            version=2,
        )
        session.add(cpe)
        session.commit()

        app.state.seed_ids = {
            "org1": str(org1.id),
            "org2": str(org2.id),
            "admin1": str(admin1.id),
            "admin2": str(admin2.id),
            "op1": str(op1.id),
            "op2": str(op2.id),
            "gestion1": str(gestion.id),
            "cpe1": str(cpe.id),
        }
    finally:
        session.close()

    return TestClient(app)


@pytest.fixture()
def auth_header(client: TestClient):
    def _auth_header(user_key: str) -> dict[str, str]:
        user_id = client.app.state.seed_ids[user_key]
        token = client.app.state.token_service.encode({"sub": user_id})
        return {"Authorization": "Bearer " + token}

    return _auth_header
