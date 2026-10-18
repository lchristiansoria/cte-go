import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from ctg_go.db.session import create_engine_from_env, session_scope
from ctg_go.modules.audit.models import AuditEvent
from ctg_go.modules.clients.models import Client
from ctg_go.modules.cpe.models import CPEDraft, CPEOperation, CPEReassignment
from ctg_go.modules.gestions.models import Gestion
from ctg_go.modules.identity.models import Organization, User, UserRole


@dataclass(frozen=True)
class SeedContext:
    organization_id: uuid.UUID
    admin_id: uuid.UUID
    operator_ids: tuple[uuid.UUID, ...]


def _ensure_arca_example(session: Session, seed_context: SeedContext) -> None:
    client = session.scalar(
        select(Client).where(
            Client.organization_id == seed_context.organization_id,
            Client.cuit == "20131082283",
        )
    )
    if client is None:
        client = Client(
            organization_id=seed_context.organization_id,
            cuit="20131082283",
            business_name="COLAGROSSI DOMINGO ANTONIO",
        )
        session.add(client)
        session.flush()

    gestion_code = "GES-DEMO-CARTA-ARCA"
    gestion = session.scalar(
        select(Gestion).where(
            Gestion.organization_id == seed_context.organization_id,
            Gestion.code == gestion_code,
        )
    )
    if gestion is None:
        gestion = Gestion(
            organization_id=seed_context.organization_id,
            client_id=client.id,
            code=gestion_code,
            status="open",
            created_by_user_id=seed_context.operator_ids[0],
        )
        session.add(gestion)
        session.flush()

    title = "Ejemplo PDF ARCA - CPE 00000-00000327"
    if session.scalar(
        select(CPEDraft.id).where(
            CPEDraft.organization_id == seed_context.organization_id,
            CPEDraft.gestion_id == gestion.id,
            CPEDraft.title == title,
        )
    ):
        return

    session.add(
        CPEDraft(
            organization_id=seed_context.organization_id,
            gestion_id=gestion.id,
            title=title,
            payload_json={
                "cpe": {
                    "ctg": "10130509594",
                    "nro_cpe": "00000-00000327",
                    "fecha": "2026-03-26",
                    "vencimiento": "2026-03-28T03:00",
                    "titular": "20131082283 - COLAGROSSI DOMINGO ANTONIO",
                    "rte_venta_primaria": "30709708674 - AGRO KOM KAWA SRL",
                    "rte_venta_secundaria": "30711855641 - FYO ACOPIO S.A.",
                    "corredor_primaria": "30703605105 - FUTUROS Y OPCIONES.COM S.A.",
                    "corredor_secundaria": "30703605105 - FUTUROS Y OPCIONES.COM S.A.",
                    "representante_entregador": "30712320008 - LA COSTA CEREALES SRL",
                    "destinatario": "30700869918 - BUNGE ARGENTINA S. A.",
                    "destino": "30709590894 - RENOVA S.A",
                    "transportista": "20228302261 - VARAS JOSE MARIA",
                    "flete_pagador": "20131082283 - COLAGROSSI DOMINGO ANTONIO",
                    "chofer": "20396103967 - MARFIL ANDR S ALBERTO",
                    "grano": "Maíz",
                    "tipo": "Maiz",
                    "campana": "2526",
                    "peso_bruto": "45000",
                    "peso_tara": "14500",
                    "peso_neto": "30500",
                    "observaciones": "KILOS ESTIMADOS",
                    "proc_localidad": "BELL VILLE",
                    "proc_provincia": "CORDOBA",
                    "proc_es_campo": "Si",
                    "dest_planta": "19265",
                    "dest_localidad": "TIMBUES JOSE MARIA",
                    "dest_provincia": "SANTA FE",
                    "dest_direccion": "Brigadier López 10500",
                    "dest_es_campo": "No",
                    "dominios": "AJV636 - GRP753",
                    "kms": "220",
                    "partida": "2026-03-26T15:00",
                    "tarifa": "38000",
                    "desc_localidad": "TIMBUES JOSE MARIA",
                    "desc_provincia": "SANTA FE",
                },
                "field_status": {},
            },
            status="draft",
            created_by_user_id=seed_context.operator_ids[0],
            responsible_user_id=seed_context.operator_ids[0],
            version=1,
        )
    )


def _ensure_seed_identity(session: Session) -> SeedContext:
    org = session.scalar(select(Organization).where(Organization.name == "CTG GO Demo"))
    if org:
        users = session.scalars(select(User).where(User.organization_id == org.id)).all()
        admin = next((u for u in users if u.role == UserRole.ADMIN.value), users[0])
        operators = tuple(u.id for u in users if u.role == UserRole.OPERATOR.value)
        return SeedContext(org.id, admin.id, operators)

    org = Organization(name="CTG GO Demo")
    session.add(org)
    session.flush()

    admin = User(
        organization_id=org.id,
        email="admin@ctg-go.local",
        password_hash="dev-only-admin-hash",
        full_name="Admin CTG GO",
        role=UserRole.ADMIN.value,
        is_active=True,
    )
    operators = [
        User(
            organization_id=org.id,
            email=f"operator{i}@ctg-go.local",
            password_hash=f"dev-only-operator-{i}-hash",
            full_name=f"Operador {i}",
            role=UserRole.OPERATOR.value,
            is_active=True,
        )
        for i in range(1, 4)
    ]
    session.add_all([admin, *operators])
    session.flush()
    return SeedContext(org.id, admin.id, tuple(op.id for op in operators))


def seed_synthetic_data(engine: Engine | None = None) -> None:
    db_engine = engine or create_engine_from_env()
    with session_scope(db_engine) as session:
        seed_context = _ensure_seed_identity(session)
        if session.scalar(
            select(Gestion.id).where(Gestion.organization_id == seed_context.organization_id).limit(1)
        ):
            _ensure_arca_example(session, seed_context)
            return

        clients = [
            Client(
                organization_id=seed_context.organization_id,
                cuit=f"3071234500{i}",
                business_name=f"Cliente Demo {i}",
                alias=f"CD-{i}",
            )
            for i in range(1, 4)
        ]
        session.add_all(clients)
        session.flush()

        gestions = [
            Gestion(
                organization_id=seed_context.organization_id,
                client_id=client.id,
                code=f"GST-{index:04d}",
                status="open",
                created_by_user_id=seed_context.operator_ids[0],
            )
            for index, client in enumerate(clients, start=1)
        ]
        session.add_all(gestions)
        session.flush()

        drafts: list[CPEDraft] = []
        for index, gestion in enumerate(gestions, start=1):
            responsible_id = seed_context.operator_ids[(index - 1) % len(seed_context.operator_ids)]
            draft = CPEDraft(
                organization_id=seed_context.organization_id,
                gestion_id=gestion.id,
                title=f"CPE borrador {index}",
                payload_json={"distance_km": 120 + index, "observations": "dato sintético"},
                status="draft",
                created_by_user_id=seed_context.operator_ids[0],
                responsible_user_id=responsible_id,
                version=1,
            )
            drafts.append(draft)
        session.add_all(drafts)
        session.flush()

        pending_operation = CPEOperation(
            organization_id=seed_context.organization_id,
            cpe_draft_id=drafts[0].id,
            status="pending",
        )
        session.add(pending_operation)

        reassignment = CPEReassignment(
            organization_id=seed_context.organization_id,
            cpe_draft_id=drafts[1].id,
            actor_user_id=seed_context.admin_id,
            previous_responsible_user_id=seed_context.operator_ids[1],
            new_responsible_user_id=seed_context.operator_ids[2],
            reason="Cobertura de guardia (datos sintéticos)",
        )
        drafts[1].responsible_user_id = seed_context.operator_ids[2]
        session.add(reassignment)

        audit_event = AuditEvent(
            organization_id=seed_context.organization_id,
            actor_user_id=seed_context.admin_id,
            entity_type="cpe_draft",
            entity_id=str(drafts[1].id),
            action="reassigned",
            details_json={"reason": reassignment.reason},
        )
        session.add(audit_event)
        _ensure_arca_example(session, seed_context)
