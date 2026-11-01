from __future__ import annotations

import logging

from ctg_go.modules.sisa.config import SisaConfig, create_datosafip_engine
from ctg_go.modules.sisa.service import ResultadoEjecucion, SisaEjecucionEnCurso, ejecutar_sincronizacion

logger = logging.getLogger("ctg_go.sisa")


def sincronizar_padron_sisa(origen: str = "programada") -> dict:
    """Entrada única para tareas programadas y ejecución manual. No propaga ejecuciones concurrentes."""
    engine = create_datosafip_engine()
    try:
        resultado: ResultadoEjecucion = ejecutar_sincronizacion(engine, SisaConfig.from_env(), origen=origen)
    except SisaEjecucionEnCurso:
        logger.warning("SISA: ejecución omitida, ya hay una en curso")
        return {"estado": "omitida", "motivo": "ejecucion_en_curso"}
    finally:
        engine.dispose()
    return {
        "ejecucion_id": resultado.ejecucion_id,
        "estado": resultado.estado,
        "motivo": resultado.motivo,
        "error": resultado.error,
        "metricas": resultado.metricas,
    }
