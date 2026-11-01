from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime
from typing import Iterator

# Campos que generan una nueva versión del registro. `fecha_generacion` queda afuera a propósito:
# cambia en todo el archivo cada día y no es un cambio del registro.
CAMPOS_VERSIONADOS = (
    "razon_social",
    "estado",
    "fecha_vigencia_estado",
    "fecha_notificacion_estado",
    "cbu",
    "fecha_actualizacion_cbu",
    "consumo_propio",
    "categoria",
    "situacion_categoria",
    "fecha_vigencia_categoria",
    "fecha_notificacion_categoria",
    "observaciones",
)
CLAVE = ("cuit", "cod_categoria")
CAMPOS_PADRON = CLAVE + CAMPOS_VERSIONADOS + ("fecha_generacion",)

# Orden oficial de columnas (diseñoRegistro.aspx), normalizado sin espacios/acentos/mayúsculas.
_COLUMNAS_ARCHIVO = (
    "cuit",
    "razonsocial/denominacion",
    "estadodelacuit",
    "fechavigenciadelestado",
    "fechanotificaciondfeestado",
    "cbu",
    "fechaactualizacioncbu",
    "consumopropio",
    "codcategoria",
    "categoria",
    "situacioncategoria",
    "fechavigenciacategoria",
    "fechanotificaciondfecategoria",
    "observaciones",
    "fechageneracion",
)
_MESES = {m: i for i, m in enumerate(
    ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"], start=1)}
_MESES_ES = {"ENE": 1, "ABR": 4, "AGO": 8, "SET": 9, "DIC": 12}

_RE_FECHA_ARCHIVO = re.compile(r"fecha\s+de\s+actualizacion\s*:\s*(\d{2}/\d{2}/\d{4})", re.I)


class SisaEstructuraError(Exception):
    """Estructura inesperada del archivo (encabezado, vacío, codificación)."""


@dataclass
class Cabecera:
    fecha_archivo: date | None
    codificacion: str
    primera_fila: int  # nro de línea (1-based) de la primera fila de datos


def decodificar(data: bytes) -> tuple[str, str]:
    """El archivo real viene en cp1252/latin-1; se prueba UTF-8 estricto primero."""
    for encoding in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return data.decode(encoding), encoding
        except UnicodeDecodeError:
            continue
    raise SisaEstructuraError("No se pudo decodificar el archivo")  # latin-1 nunca falla; defensivo


def _normalizar(nombre: str) -> str:
    sin_acentos = unicodedata.normalize("NFKD", nombre).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", "", sin_acentos).lower()


def leer(texto: str, codificacion: str) -> tuple[Cabecera, Iterator[tuple[int, str]]]:
    """Valida el encabezado y devuelve un iterador de (nro_linea, linea) de datos no vacías."""
    lineas = texto.split("\n")  # no splitlines(): separaría por caracteres propios de latin-1
    idx = 0
    fecha_archivo: date | None = None

    def siguiente_no_vacia(desde: int) -> int | None:
        for i in range(desde, len(lineas)):
            if lineas[i].strip():
                return i
        return None

    idx_cab = siguiente_no_vacia(0)
    if idx_cab is None:
        raise SisaEstructuraError("archivo_vacio")
    m = _RE_FECHA_ARCHIVO.match(lineas[idx_cab].strip())
    if m:
        fecha_archivo = datetime.strptime(m.group(1), "%d/%m/%Y").date()
        idx_cab = siguiente_no_vacia(idx_cab + 1)
        if idx_cab is None:
            raise SisaEstructuraError("archivo_sin_encabezado")
    columnas = tuple(_normalizar(c) for c in lineas[idx_cab].rstrip("\r").split(";"))
    if columnas != _COLUMNAS_ARCHIVO:
        raise SisaEstructuraError("encabezado_inesperado")
    idx = idx_cab + 1

    def filas() -> Iterator[tuple[int, str]]:
        for i in range(idx, len(lineas)):
            linea = lineas[i].rstrip("\r")
            if linea.strip():
                yield i + 1, linea

    return Cabecera(fecha_archivo, codificacion, idx + 1), filas()


def _texto(valor: str, maximo: int, campo: str, errores: list[str]) -> str | None:
    valor = valor.strip()
    if not valor:
        return None
    if len(valor) > maximo:
        errores.append(f"{campo}_longitud")
        return None
    return valor


def _fecha(valor: str, campo: str, errores: list[str]) -> date | None:
    valor = valor.strip()
    if not valor:
        return None
    try:
        return datetime.strptime(valor, "%d/%m/%Y").date()
    except ValueError:
        errores.append(f"{campo}_formato")
        return None


def _fecha_hora(valor: str, campo: str, errores: list[str]) -> datetime | None:
    valor = valor.strip()
    if not valor:
        return None
    try:
        return datetime.strptime(valor, "%d/%m/%Y %H:%M:%S")
    except ValueError:
        errores.append(f"{campo}_formato")
        return None


def _fecha_generacion(valor: str, errores: list[str]) -> date | None:
    """dd-mmm-yy con mes abreviado, independiente del locale del servidor."""
    valor = valor.strip()
    if not valor:
        return None
    m = re.fullmatch(r"(\d{1,2})-([A-Za-z]{3})-(\d{2}|\d{4})", valor)
    if m:
        mes = _MESES.get(m.group(2).upper()) or _MESES_ES.get(m.group(2).upper())
        anio = int(m.group(3))
        anio = anio + 2000 if anio < 100 else anio
        if mes:
            try:
                return date(anio, mes, int(m.group(1)))
            except ValueError:
                pass
    errores.append("fecha_generacion_formato")
    return None


def _entero(valor: str, campo: str, digitos: int, errores: list[str], *, requerido: bool) -> int | None:
    valor = valor.strip()
    if not valor:
        if requerido:
            errores.append(f"{campo}_requerido")
        return None
    if not valor.isascii() or not valor.isdigit() or len(valor) > digitos:
        errores.append(f"{campo}_formato")
        return None
    return int(valor)


def calcular_hash_version(registro: dict) -> str:
    partes = []
    for campo in CAMPOS_VERSIONADOS:
        v = registro.get(campo)
        if isinstance(v, datetime):
            v = v.isoformat()
        elif isinstance(v, date):
            v = v.isoformat()
        partes.append("" if v is None else str(v))
    return hashlib.sha256("\x1f".join(partes).encode("utf-8")).hexdigest()


def parsear_linea(linea: str) -> tuple[dict | None, list[str]]:
    """Devuelve (registro, errores). Los errores son códigos; nunca incluyen contenido de la fila."""
    campos = linea.split(";")
    if len(campos) != len(_COLUMNAS_ARCHIVO):
        return None, ["cantidad_columnas"]
    errores: list[str] = []
    (cuit_raw, razon, estado_raw, f_vig_est, f_not_est, cbu_raw, f_cbu, consumo, cod_raw,
     categoria, situacion, f_vig_cat, f_not_cat, obs, f_gen) = campos

    cuit = cuit_raw.strip()
    if not (len(cuit) == 11 and cuit.isascii() and cuit.isdigit()):
        errores.append("cuit_formato")
        cuit = None
    estado = _entero(estado_raw, "estado", 1, errores, requerido=True)
    if estado is not None and estado > 3:
        errores.append("estado_valor")
    cod = _entero(cod_raw, "cod_categoria", 2, errores, requerido=True)
    cbu = _texto(cbu_raw, 22, "cbu", errores)
    if cbu is not None and not (len(cbu) == 22 and cbu.isascii() and cbu.isdigit()):
        errores.append("cbu_formato")
    consumo_v = _texto(consumo, 2, "consumo_propio", errores)
    if consumo_v is not None and consumo_v.upper() not in ("SI", "NO"):
        errores.append("consumo_propio_valor")
    situacion_v = _texto(situacion, 2, "situacion_categoria", errores)
    if situacion_v is not None and situacion_v.upper() not in ("AL", "BA"):
        errores.append("situacion_categoria_valor")

    registro = {
        "cuit": cuit,
        "cod_categoria": cod,
        "razon_social": _texto(razon, 200, "razon_social", errores),
        "estado": estado,
        "fecha_vigencia_estado": _fecha(f_vig_est, "fecha_vigencia_estado", errores),
        "fecha_notificacion_estado": _fecha(f_not_est, "fecha_notificacion_estado", errores),
        "cbu": cbu,
        "fecha_actualizacion_cbu": _fecha_hora(f_cbu, "fecha_actualizacion_cbu", errores),
        "consumo_propio": consumo_v.upper() if consumo_v else None,
        "categoria": _texto(categoria, 200, "categoria", errores),
        "situacion_categoria": situacion_v.upper() if situacion_v else None,
        "fecha_vigencia_categoria": _fecha(f_vig_cat, "fecha_vigencia_categoria", errores),
        "fecha_notificacion_categoria": _fecha(f_not_cat, "fecha_notificacion_categoria", errores),
        "observaciones": _texto(obs, 1000, "observaciones", errores),
        "fecha_generacion": _fecha_generacion(f_gen, errores),
    }
    if errores:
        return registro, errores
    registro["hash_version"] = calcular_hash_version(registro)
    return registro, []
