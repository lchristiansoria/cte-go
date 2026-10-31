from __future__ import annotations

import sys
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, select

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from ctg_go.modules.gestions.models import Gestion  # noqa: E402
from ctg_go.modules.clients.models import Client  # noqa: E402
from ctg_go.modules.cpe.models import CPEDraft  # noqa: E402
from ctg_go.seed.synthetic import seed_synthetic_data  # noqa: E402


def _alembic_config() -> Config:
    config = Config(str(PROJECT_ROOT / "migrations" / "alembic.ini"))
    config.set_main_option("script_location", str(PROJECT_ROOT / "migrations"))
    return config


def test_migrations_upgrade_head_creates_tables() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    with engine.connect() as connection:
        config = _alembic_config()
        config.attributes["connection"] = connection
        command.upgrade(config, "head")

        table_names = set(inspect(connection).get_table_names())
        assert {
            "organizations",
            "users",
            "clients",
            "gestions",
            "gestion_messages",
            "cpe_drafts",
            "cpe_operations",
            "cpe_reassignments",
            "audit_events",
        }.issubset(table_names)
        operation_columns = {
            column["name"] for column in inspect(connection).get_columns("cpe_operations")
        }
        assert {"request_json", "response_json", "error_message"}.issubset(operation_columns)


def test_seed_demo_data_is_idempotent() -> None:
    db_path = PROJECT_ROOT / "migrations" / "tests" / ".artifacts" / "seed_test.sqlite"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()

    engine = create_engine(f"sqlite+pysqlite:///{db_path}", future=True)
    try:
        with engine.connect() as connection:
            config = _alembic_config()
            config.attributes["connection"] = connection
            command.upgrade(config, "head")

        seed_synthetic_data(engine)
        seed_synthetic_data(engine)

        with engine.connect() as connection:
            rows = connection.execute(select(Gestion.id)).all()
            assert len(rows) == 4
            client_name = connection.execute(
                select(Client.business_name).where(Client.cuit == "20131082283")
            ).scalar_one()
            assert client_name == "COLAGROSSI DOMINGO ANTONIO"
            example_payload = connection.execute(
                select(CPEDraft.payload_json).where(
                    CPEDraft.title == "Ejemplo PDF ARCA - CPE 00000-00000327"
                )
            ).scalar_one()
            assert example_payload["cpe"]["ctg"] == "10130509594"
            assert example_payload["cpe"]["peso_neto"] == "30500"
    finally:
        engine.dispose()
        if db_path.exists():
            db_path.unlink()
