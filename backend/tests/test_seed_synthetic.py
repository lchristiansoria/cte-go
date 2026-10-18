import uuid

from ctg_go.modules.clients.models import Client
from ctg_go.modules.cpe.models import CPEDraft
from ctg_go.modules.gestions.models import Gestion
from ctg_go.seed.synthetic import SeedContext, _ensure_arca_example


def test_existing_arca_example_is_completed_without_overwriting_values(client):
    seed_ids = client.app.state.seed_ids
    organization_id = uuid.UUID(seed_ids["org1"])
    operator_id = uuid.UUID(seed_ids["op1"])
    session = client.app.state.session_factory()
    try:
        demo_client = Client(
            organization_id=organization_id,
            cuit="20131082283",
            business_name="COLAGROSSI DOMINGO ANTONIO",
        )
        session.add(demo_client)
        session.flush()
        gestion = Gestion(
            organization_id=organization_id,
            client_id=demo_client.id,
            code="GES-DEMO-CARTA-ARCA",
            status="open",
            created_by_user_id=operator_id,
        )
        session.add(gestion)
        session.flush()
        cpe = CPEDraft(
            organization_id=organization_id,
            gestion_id=gestion.id,
            title="Ejemplo PDF ARCA - CPE 00000-00000327",
            payload_json={
                "cpe": {"titular": "Nombre previamente guardado", "grano": ""},
                "field_status": {"titular": "confirmed"},
                "source": "existing",
            },
            status="draft",
            created_by_user_id=operator_id,
            responsible_user_id=operator_id,
            version=1,
        )
        session.add(cpe)
        session.flush()

        seed_context = SeedContext(organization_id, operator_id, (operator_id,))
        _ensure_arca_example(session, seed_context)
        session.commit()

        assert cpe.payload_json["cpe"]["titular"] == "Nombre previamente guardado"
        assert cpe.payload_json["cpe"]["grano"] == "Maíz"
        assert cpe.payload_json["cpe"]["ctg"] == "10130509594"
        assert cpe.payload_json["field_status"] == {"titular": "confirmed"}
        assert cpe.payload_json["source"] == "existing"
        assert cpe.version == 2

        _ensure_arca_example(session, seed_context)
        assert cpe.version == 2
    finally:
        session.close()
