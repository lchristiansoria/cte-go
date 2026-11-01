from __future__ import annotations

import logging
import shutil
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

from ctg_go.modules.sisa.config import SisaConfig

logger = logging.getLogger("ctg_go.sisa")

_CHUNK = 1024 * 256


class SisaDescargaError(Exception):
    """Fallo de descarga, ZIP inválido o TXT ausente. El mensaje nunca incluye datos del padrón."""


def descargar_zip(config: SisaConfig, destino: Path, *, sleep=time.sleep) -> None:
    """Descarga el ZIP a `destino` con timeout y reintentos limitados."""
    ultimo_error = "desconocido"
    intentos = max(1, config.reintentos)
    for intento in range(1, intentos + 1):
        try:
            _descargar_una_vez(config, destino)
            return
        except SisaDescargaError as exc:
            ultimo_error = str(exc)
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as exc:
            ultimo_error = f"{type(exc).__name__}: {exc}"
        logger.warning("SISA descarga intento %s/%s fallido: %s", intento, intentos, ultimo_error)
        if intento < intentos:
            sleep(config.espera_reintento_segundos * intento)
    raise SisaDescargaError(f"Descarga fallida tras {intentos} intentos: {ultimo_error}")


def _descargar_una_vez(config: SisaConfig, destino: Path) -> None:
    if not config.url.lower().startswith(("https://", "http://")):
        raise SisaDescargaError("URL_SISA debe ser http(s)")
    request = urllib.request.Request(config.url, headers={"User-Agent": "ctg-go-sisa/1.0"})
    with urllib.request.urlopen(request, timeout=config.timeout_segundos) as response:
        status = getattr(response, "status", 200)
        if status != 200:
            raise SisaDescargaError(f"HTTP {status}")
        content_type = (response.headers.get("Content-Type") or "").lower()
        if "html" in content_type:
            raise SisaDescargaError(f"Content-Type inesperado: {content_type}")
        expected = response.headers.get("Content-Length")
        expected_len = int(expected) if expected and expected.isdigit() else None
        if expected_len is not None and expected_len > config.max_bytes_zip:
            raise SisaDescargaError("El ZIP supera el tamaño máximo permitido")
        total = 0
        with destino.open("wb") as out:
            while chunk := response.read(_CHUNK):
                total += len(chunk)
                if total > config.max_bytes_zip:
                    raise SisaDescargaError("El ZIP supera el tamaño máximo permitido")
                out.write(chunk)
    if total == 0:
        raise SisaDescargaError("Respuesta vacía")
    if expected_len is not None and total != expected_len:
        raise SisaDescargaError(f"Descarga incompleta ({total} de {expected_len} bytes)")


def extraer_txt(zip_path: Path, destino_dir: Path, config: SisaConfig) -> Path:
    """Valida el ZIP y extrae únicamente el TXT esperado, con nombre fijo y tope de tamaño."""
    if not zipfile.is_zipfile(zip_path):
        raise SisaDescargaError("El archivo descargado no es un ZIP válido")
    try:
        with zipfile.ZipFile(zip_path) as zf:
            malo = zf.testzip()
            if malo is not None:
                raise SisaDescargaError("ZIP corrupto (falla de CRC)")
            candidatos = [
                info
                for info in zf.infolist()
                if not info.is_dir() and Path(info.filename).name.lower() in config.nombres_txt
            ]
            if len(candidatos) != 1:
                raise SisaDescargaError(f"El ZIP debe contener exactamente un TXT esperado ({len(candidatos)} encontrados)")
            info = candidatos[0]
            if info.file_size == 0:
                raise SisaDescargaError("El TXT del ZIP está vacío")
            if info.file_size > config.max_bytes_txt:
                raise SisaDescargaError("El TXT supera el tamaño máximo permitido")
            # Nunca se usa el nombre del miembro como ruta (evita path traversal / zip slip).
            salida = destino_dir / "padron_sisa.txt"
            escrito = 0
            with zf.open(info) as src, salida.open("wb") as dst:
                while chunk := src.read(_CHUNK):
                    escrito += len(chunk)
                    if escrito > config.max_bytes_txt:
                        raise SisaDescargaError("El TXT supera el tamaño máximo permitido")
                    dst.write(chunk)
            return salida
    except zipfile.BadZipFile as exc:
        raise SisaDescargaError("ZIP corrupto") from exc


def limpiar(directorio: Path) -> None:
    shutil.rmtree(directorio, ignore_errors=True)
