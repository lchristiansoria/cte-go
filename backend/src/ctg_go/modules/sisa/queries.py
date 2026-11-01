from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ctg_go.modules.sisa.models import ESTADO_COMPLETADA, Actual, Ejecucion


@dataclass(frozen=True)
class CategoriaSisa:
    cod_categoria: int
    categoria: str | None
    situacion_categoria: str | None
    fecha_vigencia_categoria: date | None
    fecha_notificacion_categoria: date | None
    consumo_propio: str | None
    observaciones: str | None


@dataclass(frozen=True)
class ConsultaSisa:
    cuit: str
    encontrado: bool
    razon_social: str | None
    estado: int | None  # scoring SISA: 0 = inactivo
    fecha_vigencia_estado: date | None
    fecha_notificacion_estado: date | None
    cbu: str | None
    fecha_actualizacion_cbu: datetime | None
    categorias: tuple[CategoriaSisa, ...]
    ultima_actualizacion: datetime | None  # fin de la última ejecución exitosa


def normalizar_cuit(cuit: str) -> str:
    digitos = re.sub(r"\D", "", cuit or "")
    if len(digitos) != 11:
        raise ValueError("CUIT inválido: debe tener 11 dígitos")
    return digitos


def ultima_actualizacion_exitosa(session: Session) -> datetime | None:
    return session.scalar(select(func.max(Ejecucion.fin)).where(Ejecucion.estado == ESTADO_COMPLETADA))


def consultar_por_cuit(session: Session, cuit: str) -> ConsultaSisa:
    """Devuelve todas las categorías vigentes del CUIT en el padrón y cuándo se actualizó por última vez."""
    cuit = normalizar_cuit(cuit)
    filas = session.scalars(select(Actual).where(Actual.cuit == cuit).order_by(Actual.cod_categoria)).all()
    categorias = tuple(
        CategoriaSisa(
            f.cod_categoria, f.categoria, f.situacion_categoria, f.fecha_vigencia_categoria,
            f.fecha_notificacion_categoria, f.consumo_propio, f.observaciones,
        )
        for f in filas
    )
    base = filas[0] if filas else None
    return ConsultaSisa(
        cuit=cuit,
        encontrado=base is not None,
        razon_social=base.razon_social if base else None,
        estado=base.estado if base else None,
        fecha_vigencia_estado=base.fecha_vigencia_estado if base else None,
        fecha_notificacion_estado=base.fecha_notificacion_estado if base else None,
        cbu=base.cbu if base else None,
        fecha_actualizacion_cbu=base.fecha_actualizacion_cbu if base else None,
        categorias=categorias,
        ultima_actualizacion=ultima_actualizacion_exitosa(session),
    )
