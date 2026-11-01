from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    SmallInteger,
    String,
    Text,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from ctg_go.db.base import NAMING_CONVENTION

BigId = BigInteger().with_variant(Integer, "sqlite")

ESTADO_EN_CURSO = "en_curso"
ESTADO_COMPLETADA = "completada"
ESTADO_REVISION = "revision"
ESTADO_FALLIDA = "fallida"


class DatosAfipBase(DeclarativeBase):
    """Metadata separada: estas tablas viven en la base DatosAfip, no en la principal."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class _CamposPadron:
    """Campos publicados por SISA (longitudes según el diseño oficial), sin la clave."""

    razon_social: Mapped[str | None] = mapped_column(String(200))
    estado: Mapped[int | None] = mapped_column(SmallInteger)
    fecha_vigencia_estado: Mapped[date | None] = mapped_column(Date)
    fecha_notificacion_estado: Mapped[date | None] = mapped_column(Date)
    cbu: Mapped[str | None] = mapped_column(String(22))
    fecha_actualizacion_cbu: Mapped[datetime | None] = mapped_column(DateTime)
    consumo_propio: Mapped[str | None] = mapped_column(String(2))
    categoria: Mapped[str | None] = mapped_column(String(200))
    situacion_categoria: Mapped[str | None] = mapped_column(String(2))
    fecha_vigencia_categoria: Mapped[date | None] = mapped_column(Date)
    fecha_notificacion_categoria: Mapped[date | None] = mapped_column(Date)
    observaciones: Mapped[str | None] = mapped_column(String(1000))
    fecha_generacion: Mapped[date | None] = mapped_column(Date)


class Ejecucion(DatosAfipBase):
    __tablename__ = "SISA_Ejecuciones"
    __table_args__ = (
        # Una sola ejecución en curso a la vez (índice parcial: PostgreSQL y SQLite).
        Index(
            "uq_SISA_Ejecuciones_en_curso",
            "estado",
            unique=True,
            postgresql_where=text("estado = 'en_curso'"),
            sqlite_where=text("estado = 'en_curso'"),
        ),
        Index("ix_SISA_Ejecuciones_estado_fin", "estado", "fin"),
    )

    id: Mapped[int] = mapped_column(BigId, primary_key=True, autoincrement=True)
    estado: Mapped[str] = mapped_column(String(20))
    origen: Mapped[str] = mapped_column(String(20))
    inicio: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    fin: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    url_origen: Mapped[str | None] = mapped_column(String(500))
    archivo_hash: Mapped[str | None] = mapped_column(String(64))
    archivo_bytes: Mapped[int | None] = mapped_column(BigInteger)
    archivo_codificacion: Mapped[str | None] = mapped_column(String(20))
    fecha_archivo: Mapped[date | None] = mapped_column(Date)
    filas_descargadas: Mapped[int | None] = mapped_column(Integer)
    filas_validas: Mapped[int | None] = mapped_column(Integer)
    filas_rechazadas: Mapped[int | None] = mapped_column(Integer)
    filas_nuevas: Mapped[int | None] = mapped_column(Integer)
    filas_modificadas: Mapped[int | None] = mapped_column(Integer)
    filas_ausentes: Mapped[int | None] = mapped_column(Integer)
    filas_sin_cambios: Mapped[int | None] = mapped_column(Integer)
    filas_actual_previas: Mapped[int | None] = mapped_column(Integer)
    motivo_revision: Mapped[str | None] = mapped_column(String(100))
    mensaje_error: Mapped[str | None] = mapped_column(Text)
    detalle: Mapped[dict | None] = mapped_column(JSON)


class Actual(_CamposPadron, DatosAfipBase):
    __tablename__ = "SISA_Actual"
    # La PK (cuit, cod_categoria) cubre la consulta por CUIT (prefijo) y la comparación por clave.

    cuit: Mapped[str] = mapped_column(String(11), primary_key=True)
    cod_categoria: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    hash_version: Mapped[str] = mapped_column(String(64))
    vigente_desde: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ejecucion_id: Mapped[int] = mapped_column(BigId, ForeignKey("SISA_Ejecuciones.id"))


class Historial(_CamposPadron, DatosAfipBase):
    __tablename__ = "SISA_Historial"
    __table_args__ = (Index("ix_SISA_Historial_clave", "cuit", "cod_categoria", "vigente_desde"),)

    id: Mapped[int] = mapped_column(BigId, primary_key=True, autoincrement=True)
    cuit: Mapped[str] = mapped_column(String(11))
    cod_categoria: Mapped[int] = mapped_column(SmallInteger)
    hash_version: Mapped[str] = mapped_column(String(64))
    vigente_desde: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    vigente_hasta: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ejecucion_alta_id: Mapped[int] = mapped_column(BigId, ForeignKey("SISA_Ejecuciones.id"))
    ejecucion_cierre_id: Mapped[int] = mapped_column(BigId, ForeignKey("SISA_Ejecuciones.id"))
    motivo_cierre: Mapped[str] = mapped_column(String(20))  # modificacion | ausencia


class Temporal(_CamposPadron, DatosAfipBase):
    __tablename__ = "SISA_Temporal"
    __table_args__ = (Index("ix_SISA_Temporal_clave", "ejecucion_id", "cuit", "cod_categoria"),)

    id: Mapped[int] = mapped_column(BigId, primary_key=True, autoincrement=True)
    ejecucion_id: Mapped[int] = mapped_column(BigId, ForeignKey("SISA_Ejecuciones.id"))
    nro_linea: Mapped[int] = mapped_column(Integer)
    valido: Mapped[bool] = mapped_column(Boolean, default=True)
    errores: Mapped[str | None] = mapped_column(String(500))  # solo códigos de error, nunca contenido
    cuit: Mapped[str | None] = mapped_column(String(11))
    cod_categoria: Mapped[int | None] = mapped_column(SmallInteger)
    hash_version: Mapped[str | None] = mapped_column(String(64))
