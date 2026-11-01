"""create SISA tables in DatosAfip

Revision ID: 20261101_0001
Revises:
Create Date: 2026-11-01 00:00:00
"""
from typing import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20261101_0001"
down_revision: str | None = None
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

BigId = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def _campos_padron() -> list[sa.Column]:
    return [
        sa.Column("razon_social", sa.String(200)),
        sa.Column("estado", sa.SmallInteger()),
        sa.Column("fecha_vigencia_estado", sa.Date()),
        sa.Column("fecha_notificacion_estado", sa.Date()),
        sa.Column("cbu", sa.String(22)),
        sa.Column("fecha_actualizacion_cbu", sa.DateTime()),
        sa.Column("consumo_propio", sa.String(2)),
        sa.Column("categoria", sa.String(200)),
        sa.Column("situacion_categoria", sa.String(2)),
        sa.Column("fecha_vigencia_categoria", sa.Date()),
        sa.Column("fecha_notificacion_categoria", sa.Date()),
        sa.Column("observaciones", sa.String(1000)),
        sa.Column("fecha_generacion", sa.Date()),
    ]


def upgrade() -> None:
    op.create_table(
        "SISA_Ejecuciones",
        sa.Column("id", BigId, primary_key=True, autoincrement=True),
        sa.Column("estado", sa.String(20), nullable=False),
        sa.Column("origen", sa.String(20), nullable=False),
        sa.Column("inicio", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fin", sa.DateTime(timezone=True)),
        sa.Column("url_origen", sa.String(500)),
        sa.Column("archivo_hash", sa.String(64)),
        sa.Column("archivo_bytes", sa.BigInteger()),
        sa.Column("archivo_codificacion", sa.String(20)),
        sa.Column("fecha_archivo", sa.Date()),
        sa.Column("filas_descargadas", sa.Integer()),
        sa.Column("filas_validas", sa.Integer()),
        sa.Column("filas_rechazadas", sa.Integer()),
        sa.Column("filas_nuevas", sa.Integer()),
        sa.Column("filas_modificadas", sa.Integer()),
        sa.Column("filas_ausentes", sa.Integer()),
        sa.Column("filas_sin_cambios", sa.Integer()),
        sa.Column("filas_actual_previas", sa.Integer()),
        sa.Column("motivo_revision", sa.String(100)),
        sa.Column("mensaje_error", sa.Text()),
        sa.Column("detalle", sa.JSON()),
        sa.PrimaryKeyConstraint("id", name="pk_SISA_Ejecuciones"),
    )
    op.create_index(
        "uq_SISA_Ejecuciones_en_curso",
        "SISA_Ejecuciones",
        ["estado"],
        unique=True,
        postgresql_where=sa.text("estado = 'en_curso'"),
        sqlite_where=sa.text("estado = 'en_curso'"),
    )
    op.create_index("ix_SISA_Ejecuciones_estado_fin", "SISA_Ejecuciones", ["estado", "fin"])

    op.create_table(
        "SISA_Actual",
        sa.Column("cuit", sa.String(11), nullable=False),
        sa.Column("cod_categoria", sa.SmallInteger(), nullable=False),
        *_campos_padron(),
        sa.Column("hash_version", sa.String(64), nullable=False),
        sa.Column("vigente_desde", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ejecucion_id", BigId, nullable=False),
        sa.PrimaryKeyConstraint("cuit", "cod_categoria", name="pk_SISA_Actual"),
        sa.ForeignKeyConstraint(["ejecucion_id"], ["SISA_Ejecuciones.id"],
                                name="fk_SISA_Actual_ejecucion_id_SISA_Ejecuciones"),
    )

    op.create_table(
        "SISA_Historial",
        sa.Column("id", BigId, primary_key=True, autoincrement=True),
        sa.Column("cuit", sa.String(11), nullable=False),
        sa.Column("cod_categoria", sa.SmallInteger(), nullable=False),
        *_campos_padron(),
        sa.Column("hash_version", sa.String(64), nullable=False),
        sa.Column("vigente_desde", sa.DateTime(timezone=True), nullable=False),
        sa.Column("vigente_hasta", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ejecucion_alta_id", BigId, nullable=False),
        sa.Column("ejecucion_cierre_id", BigId, nullable=False),
        sa.Column("motivo_cierre", sa.String(20), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_SISA_Historial"),
        sa.ForeignKeyConstraint(["ejecucion_alta_id"], ["SISA_Ejecuciones.id"],
                                name="fk_SISA_Historial_ejecucion_alta_id_SISA_Ejecuciones"),
        sa.ForeignKeyConstraint(["ejecucion_cierre_id"], ["SISA_Ejecuciones.id"],
                                name="fk_SISA_Historial_ejecucion_cierre_id_SISA_Ejecuciones"),
    )
    op.create_index("ix_SISA_Historial_clave", "SISA_Historial", ["cuit", "cod_categoria", "vigente_desde"])

    op.create_table(
        "SISA_Temporal",
        sa.Column("id", BigId, primary_key=True, autoincrement=True),
        sa.Column("ejecucion_id", BigId, nullable=False),
        sa.Column("nro_linea", sa.Integer(), nullable=False),
        sa.Column("valido", sa.Boolean(), nullable=False),
        sa.Column("errores", sa.String(500)),
        sa.Column("cuit", sa.String(11)),
        sa.Column("cod_categoria", sa.SmallInteger()),
        *_campos_padron(),
        sa.Column("hash_version", sa.String(64)),
        sa.PrimaryKeyConstraint("id", name="pk_SISA_Temporal"),
        sa.ForeignKeyConstraint(["ejecucion_id"], ["SISA_Ejecuciones.id"],
                                name="fk_SISA_Temporal_ejecucion_id_SISA_Ejecuciones"),
    )
    op.create_index("ix_SISA_Temporal_clave", "SISA_Temporal", ["ejecucion_id", "cuit", "cod_categoria"])


def downgrade() -> None:
    op.drop_table("SISA_Temporal")
    op.drop_table("SISA_Historial")
    op.drop_table("SISA_Actual")
    op.drop_table("SISA_Ejecuciones")
