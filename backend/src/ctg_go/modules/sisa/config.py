from __future__ import annotations

import os
from dataclasses import dataclass, field

from sqlalchemy.engine import URL, Engine, create_engine

# Enlace "Descargar el listado completo" de https://servicioscf.afip.gob.ar/publico/registroSISA/
URL_SISA_OFICIAL = "https://serviciosweb.afip.gob.ar/genericos/Registros/op_granos/Archivos/RG_4310.zip"

# El diseño oficial menciona RG4310.txt; el archivo real publicado se llama RG_4310.txt.
NOMBRES_TXT_ACEPTADOS = ("rg4310.txt", "rg_4310.txt")


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    return int(raw) if raw not in (None, "") else default


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    return float(raw) if raw not in (None, "") else default


@dataclass(frozen=True)
class SisaConfig:
    url: str = URL_SISA_OFICIAL
    timeout_segundos: int = 30
    reintentos: int = 3
    espera_reintento_segundos: float = 5.0
    max_bytes_zip: int = 200 * 1024 * 1024
    max_bytes_txt: int = 1024 * 1024 * 1024
    # Umbrales de revisión. Los porcentajes se calculan contra el padrón actual.
    min_filas: int = 10_000
    umbral_variacion_total_pct: float = 20.0
    umbral_ausentes_pct: float = 10.0
    umbral_modificadas_pct: float = 30.0
    lote_filas: int = 5_000
    ejecucion_vencida_horas: int = 6
    retencion_staging_dias: int = 7
    nombres_txt: tuple[str, ...] = field(default=NOMBRES_TXT_ACEPTADOS)

    @classmethod
    def from_env(cls) -> "SisaConfig":
        d = cls()
        return cls(
            url=os.getenv("URL_SISA") or d.url,
            timeout_segundos=_env_int("TIMEOUT_SISA", d.timeout_segundos),
            reintentos=_env_int("REINTENTOS_SISA", d.reintentos),
            espera_reintento_segundos=_env_float("ESPERA_REINTENTO_SISA", d.espera_reintento_segundos),
            max_bytes_zip=_env_int("MAX_BYTES_ZIP_SISA", d.max_bytes_zip),
            max_bytes_txt=_env_int("MAX_BYTES_TXT_SISA", d.max_bytes_txt),
            min_filas=_env_int("MIN_FILAS_SISA", d.min_filas),
            umbral_variacion_total_pct=_env_float("UMBRAL_VARIACION_SISA", d.umbral_variacion_total_pct),
            umbral_ausentes_pct=_env_float("UMBRAL_AUSENTES_SISA", d.umbral_ausentes_pct),
            umbral_modificadas_pct=_env_float("UMBRAL_MODIFICADAS_SISA", d.umbral_modificadas_pct),
            lote_filas=_env_int("LOTE_SISA", d.lote_filas),
            ejecucion_vencida_horas=_env_int("EJECUCION_VENCIDA_HORAS_SISA", d.ejecucion_vencida_horas),
            retencion_staging_dias=_env_int("RETENCION_STAGING_DIAS_SISA", d.retencion_staging_dias),
        )


def build_datosafip_url() -> URL | str:
    """URL de la base independiente DatosAfip (usa la base principal solo como default de servidor/credenciales)."""
    explicit = os.getenv("URL_DATOSAFIP")
    if explicit:
        return explicit
    return URL.create(
        "postgresql+psycopg",
        username=os.getenv("USR_DATOSAFIP") or os.getenv("USR_DB", "postgres"),
        password=os.getenv("PASS_DATOSAFIP") or os.getenv("PASS_DB", "postgres"),
        host=os.getenv("HOST_DATOSAFIP") or os.getenv("HOST_DB", "localhost"),
        port=int(os.getenv("PORT_DATOSAFIP") or os.getenv("PORT_DB", "5432")),
        database=os.getenv("NAME_DATOSAFIP", "DatosAfip"),
    )


def create_datosafip_engine(url: URL | str | None = None) -> Engine:
    return create_engine(url or build_datosafip_url(), future=True, pool_pre_ping=True)
