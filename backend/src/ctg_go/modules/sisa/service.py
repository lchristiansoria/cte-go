from __future__ import annotations

import hashlib
import logging
import shutil
import tempfile
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Iterable

from sqlalchemy import and_, delete, exists, func, insert, literal, select, update
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError

from ctg_go.modules.sisa import parser
from ctg_go.modules.sisa.config import SisaConfig
from ctg_go.modules.sisa.download import SisaDescargaError, descargar_zip, extraer_txt
from ctg_go.modules.sisa.models import (
    ESTADO_COMPLETADA,
    ESTADO_EN_CURSO,
    ESTADO_FALLIDA,
    ESTADO_REVISION,
    Actual,
    Ejecucion,
    Historial,
    Temporal,
)

logger = logging.getLogger("ctg_go.sisa")

A, H, S, E = Actual.__table__, Historial.__table__, Temporal.__table__, Ejecucion.__table__
MUESTRAS_RECHAZO = 20

Fetch = Callable[[SisaConfig, Path], None]


class SisaEjecucionEnCurso(Exception):
    """Ya hay una ejecución en curso; esta invocación no hizo nada."""


@dataclass
class ResultadoEjecucion:
    ejecucion_id: int
    estado: str
    motivo: str | None = None
    error: str | None = None
    metricas: dict = field(default_factory=dict)


def _ahora() -> datetime:
    return datetime.now(timezone.utc)


# --------------------------------------------------------------------------- ejecución / bloqueo

def _iniciar(engine: Engine, config: SisaConfig, origen: str, ahora: datetime) -> int:
    """Registra el inicio. El índice único parcial impide dos ejecuciones simultáneas."""
    with engine.begin() as conn:
        limite = ahora - timedelta(hours=config.ejecucion_vencida_horas)
        conn.execute(
            update(E)
            .where(E.c.estado == ESTADO_EN_CURSO, E.c.inicio < limite)
            .values(
                estado=ESTADO_FALLIDA,
                fin=ahora,
                mensaje_error="Ejecución abandonada: superó el tiempo máximo y fue reemplazada",
            )
        )
    try:
        with engine.begin() as conn:
            res = conn.execute(
                insert(E).values(estado=ESTADO_EN_CURSO, origen=origen, inicio=ahora, url_origen=config.url[:500])
            )
            return int(res.inserted_primary_key[0])
    except IntegrityError as exc:
        raise SisaEjecucionEnCurso("Ya existe una ejecución SISA en curso") from exc


def _purgar_staging(engine: Engine, config: SisaConfig, ahora: datetime) -> None:
    limite = ahora - timedelta(days=config.retencion_staging_dias)
    with engine.begin() as conn:
        viejas = select(E.c.id).where(E.c.estado != ESTADO_EN_CURSO, E.c.fin < limite)
        conn.execute(delete(S).where(S.c.ejecucion_id.in_(viejas)))


def _finalizar(engine: Engine, ejecucion_id: int, estado: str, ahora: datetime, **campos) -> None:
    with engine.begin() as conn:
        conn.execute(update(E).where(E.c.id == ejecucion_id).values(estado=estado, fin=ahora, **campos))


# --------------------------------------------------------------------------- staging

def _fila_staging(ejecucion_id: int, nro: int, registro: dict | None, errores: list[str]) -> dict:
    fila = {c.name: None for c in S.columns if c.name != "id"}
    fila.update(ejecucion_id=ejecucion_id, nro_linea=nro, valido=not errores)
    if errores:
        fila["errores"] = ",".join(dict.fromkeys(errores))[:500]
        if registro:  # solo la clave, para diagnosticar sin persistir el resto del contenido
            fila["cuit"] = registro.get("cuit")
            fila["cod_categoria"] = registro.get("cod_categoria")
    else:
        for k, v in registro.items():
            fila[k] = v
    return fila


def _cargar_staging(engine: Engine, ejecucion_id: int, filas: Iterable[tuple[int, str]], config: SisaConfig) -> dict:
    total = 0
    razones: Counter[str] = Counter()
    muestras: list[dict] = []
    lote: list[dict] = []

    def volcar() -> None:
        if lote:
            with engine.begin() as conn:
                conn.execute(insert(S), lote)
            lote.clear()

    for nro, linea in filas:
        total += 1
        registro, errores = parser.parsear_linea(linea)
        if errores:
            razones.update(set(errores))
            if len(muestras) < MUESTRAS_RECHAZO:
                muestras.append({"linea": nro, "errores": sorted(set(errores))})
        lote.append(_fila_staging(ejecucion_id, nro, registro, errores))
        if len(lote) >= config.lote_filas:
            volcar()
    volcar()
    return {"descargadas": total, "razones": dict(razones), "muestras": muestras}


def _marcar_duplicados(engine: Engine, ejecucion_id: int) -> int:
    t2 = S.alias("t2")
    dup = exists().where(
        and_(
            t2.c.ejecucion_id == ejecucion_id,
            t2.c.cuit == S.c.cuit,
            t2.c.cod_categoria == S.c.cod_categoria,
            t2.c.id != S.c.id,
        )
    )
    with engine.begin() as conn:
        res = conn.execute(
            update(S)
            .where(S.c.ejecucion_id == ejecucion_id, S.c.valido.is_(True), dup)
            .values(valido=False, errores="clave_duplicada")
        )
        return res.rowcount or 0


# --------------------------------------------------------------------------- comparación

def _misma_clave():
    return and_(A.c.cuit == S.c.cuit, A.c.cod_categoria == S.c.cod_categoria)


def _staging_ok(ejecucion_id: int):
    return and_(S.c.ejecucion_id == ejecucion_id, S.c.valido.is_(True))


def _contar(conn, ejecucion_id: int) -> dict:
    ok = _staging_ok(ejecucion_id)
    previas = conn.scalar(select(func.count()).select_from(A)) or 0
    validas = conn.scalar(select(func.count()).select_from(S).where(ok)) or 0
    rechazadas = conn.scalar(
        select(func.count()).select_from(S).where(S.c.ejecucion_id == ejecucion_id, S.c.valido.is_(False))
    ) or 0
    nuevas = conn.scalar(
        select(func.count()).select_from(S).where(ok, ~exists().where(_misma_clave()))
    ) or 0
    modificadas = conn.scalar(
        select(func.count()).select_from(S.join(A, _misma_clave())).where(ok, A.c.hash_version != S.c.hash_version)
    ) or 0
    sin_cambios = conn.scalar(
        select(func.count()).select_from(S.join(A, _misma_clave())).where(ok, A.c.hash_version == S.c.hash_version)
    ) or 0
    ausentes = conn.scalar(select(func.count()).select_from(A).where(~exists().where(and_(ok, _misma_clave())))) or 0
    return {
        "filas_actual_previas": previas,
        "filas_validas": validas,
        "filas_rechazadas": rechazadas,
        "filas_nuevas": nuevas,
        "filas_modificadas": modificadas,
        "filas_sin_cambios": sin_cambios,
        "filas_ausentes": ausentes,
    }


def _evaluar(m: dict, config: SisaConfig) -> str | None:
    """Devuelve el motivo de revisión, o None si el archivo puede publicarse."""
    if m["filas_validas"] + m["filas_rechazadas"] == 0:
        return "archivo_vacio"
    if m["filas_rechazadas"] > 0:
        return "filas_rechazadas"
    if m["filas_validas"] < config.min_filas:
        return "volumen_minimo"
    previas = m["filas_actual_previas"]
    if previas > 0:
        if abs(m["filas_validas"] - previas) * 100 / previas > config.umbral_variacion_total_pct:
            return "variacion_volumen"
        if m["filas_ausentes"] * 100 / previas > config.umbral_ausentes_pct:
            return "ausentes_excesivas"
        if m["filas_modificadas"] * 100 / previas > config.umbral_modificadas_pct:
            return "modificaciones_excesivas"
    return None


# --------------------------------------------------------------------------- publicación

_COLS_DATOS = [c for c in parser.CAMPOS_PADRON] + ["hash_version"]


def _cerrar_versiones(conn, ejecucion_id: int, ahora: datetime) -> None:
    """Copia a historial las versiones modificadas y las ausentes del padrón actual."""
    ok = _staging_ok(ejecucion_id)
    destino = _COLS_DATOS + ["vigente_desde", "vigente_hasta", "ejecucion_alta_id", "ejecucion_cierre_id", "motivo_cierre"]

    def origen(motivo: str):
        return [A.c[c] for c in _COLS_DATOS] + [
            A.c.vigente_desde, literal(ahora), A.c.ejecucion_id, literal(ejecucion_id), literal(motivo)
        ]

    conn.execute(
        insert(H).from_select(
            destino,
            select(*origen("modificacion"))
            .select_from(A.join(S, _misma_clave()))
            .where(ok, A.c.hash_version != S.c.hash_version),
        )
    )
    conn.execute(
        insert(H).from_select(
            destino,
            select(*origen("ausencia")).where(~exists().where(and_(ok, _misma_clave()))),
        )
    )


def _retirar_de_actual(conn, ejecucion_id: int) -> None:
    """Quita de la tabla actual lo modificado o ausente (lo no modificado se conserva intacto)."""
    mismo = and_(_staging_ok(ejecucion_id), _misma_clave(), S.c.hash_version == A.c.hash_version)
    conn.execute(delete(A).where(~exists().where(mismo)))


def _insertar_nuevas_versiones(conn, ejecucion_id: int, ahora: datetime) -> None:
    conn.execute(
        insert(A).from_select(
            _COLS_DATOS + ["vigente_desde", "ejecucion_id"],
            select(*[S.c[c] for c in _COLS_DATOS], literal(ahora), literal(ejecucion_id))
            .where(_staging_ok(ejecucion_id), ~exists().where(_misma_clave())),
        )
    )


def _publicar(engine: Engine, ejecucion_id: int, ahora: datetime, campos_finales: dict) -> dict:
    """Altas, modificaciones y ausencias + resultado de la ejecución, en una única transacción."""
    with engine.begin() as conn:
        metricas = _contar(conn, ejecucion_id)
        _cerrar_versiones(conn, ejecucion_id, ahora)
        _retirar_de_actual(conn, ejecucion_id)
        _insertar_nuevas_versiones(conn, ejecucion_id, ahora)
        conn.execute(delete(S).where(S.c.ejecucion_id == ejecucion_id))
        conn.execute(
            update(E)
            .where(E.c.id == ejecucion_id)
            .values(estado=ESTADO_COMPLETADA, fin=ahora, **metricas, **campos_finales)
        )
    return metricas


# --------------------------------------------------------------------------- orquestación

def ejecutar_sincronizacion(
    engine: Engine,
    config: SisaConfig | None = None,
    *,
    origen: str = "manual",
    fetch: Fetch = descargar_zip,
    ahora: Callable[[], datetime] = _ahora,
) -> ResultadoEjecucion:
    config = config or SisaConfig.from_env()
    inicio = ahora()
    ejecucion_id = _iniciar(engine, config, origen, inicio)
    logger.info("SISA ejecucion=%s iniciada origen=%s", ejecucion_id, origen)
    _purgar_staging(engine, config, inicio)

    campos: dict = {}
    tmp = Path(tempfile.mkdtemp(prefix="sisa_"))
    try:
        zip_path = tmp / "RG_4310.zip"
        fetch(config, zip_path)
        txt = extraer_txt(zip_path, tmp, config)
        data = txt.read_bytes()
        campos["archivo_hash"] = hashlib.sha256(data).hexdigest()
        campos["archivo_bytes"] = len(data)
        texto, codificacion = parser.decodificar(data)
        del data
        campos["archivo_codificacion"] = codificacion
        cabecera, filas = parser.leer(texto, codificacion)
        campos["fecha_archivo"] = cabecera.fecha_archivo

        carga = _cargar_staging(engine, ejecucion_id, filas, config)
        del texto
        campos["filas_descargadas"] = carga["descargadas"]
        duplicadas = _marcar_duplicados(engine, ejecucion_id)
        detalle = {
            "razones_rechazo": carga["razones"],
            "muestras_rechazo": carga["muestras"],
            "filas_clave_duplicada": duplicadas,
        }

        with engine.connect() as conn:
            metricas = _contar(conn, ejecucion_id)
        motivo = _evaluar(metricas, config)
        if motivo:
            _finalizar(
                engine, ejecucion_id, ESTADO_REVISION, ahora(),
                motivo_revision=motivo, detalle=detalle, **campos, **metricas,
            )
            logger.warning("SISA ejecucion=%s requiere revision motivo=%s %s", ejecucion_id, motivo, metricas)
            return ResultadoEjecucion(ejecucion_id, ESTADO_REVISION, motivo=motivo, metricas=metricas)

        metricas = _publicar(engine, ejecucion_id, ahora(), {**campos, "detalle": detalle})
        logger.info("SISA ejecucion=%s completada %s", ejecucion_id, metricas)
        return ResultadoEjecucion(ejecucion_id, ESTADO_COMPLETADA, metricas=metricas)

    except parser.SisaEstructuraError as exc:
        _finalizar(engine, ejecucion_id, ESTADO_REVISION, ahora(), motivo_revision=str(exc), **campos)
        logger.warning("SISA ejecucion=%s requiere revision motivo=%s", ejecucion_id, exc)
        return ResultadoEjecucion(ejecucion_id, ESTADO_REVISION, motivo=str(exc))
    except SisaDescargaError as exc:
        _finalizar(engine, ejecucion_id, ESTADO_FALLIDA, ahora(), mensaje_error=str(exc)[:1000], **campos)
        logger.error("SISA ejecucion=%s fallida: %s", ejecucion_id, exc)
        return ResultadoEjecucion(ejecucion_id, ESTADO_FALLIDA, error=str(exc))
    except Exception as exc:
        # Solo el tipo: los mensajes de la base pueden incluir parámetros (p. ej. CBU).
        mensaje = f"Error inesperado: {type(exc).__name__}"
        _finalizar(engine, ejecucion_id, ESTADO_FALLIDA, ahora(), mensaje_error=mensaje, **campos)
        logger.error("SISA ejecucion=%s fallida: %s", ejecucion_id, mensaje)
        return ResultadoEjecucion(ejecucion_id, ESTADO_FALLIDA, error=mensaje)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
