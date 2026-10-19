"""Fachada para integrar ARCA (WSAA + WSCPE) en otro sistema.

Uso:
    from arca_cpe import ArcaCPE
    arca = ArcaCPE()                      # toma la config de .env
    arca.autorizar_cpe_automotor(solicitud)
    arca.llamar("anularCPE", {...})       # cualquier operación del WSDL
"""
import json
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from zeep.exceptions import Fault
from zeep.helpers import serialize_object

from config import configs
from config.logging import logging
from wsaa_client import WSAAClient
from wscpe_client import WSCPEClient


class ArcaError(Exception):
    """Error devuelto por ARCA (Fault SOAP o lista `errores` en la respuesta)."""

    def __init__(self, mensaje: str, errores: Optional[List[dict]] = None):
        super().__init__(mensaje)
        self.errores = errores or []


@dataclass
class ArcaConfig:
    cuit: str = configs.CUIT
    certificado: str = configs.CERTIFICADO
    clave: str = configs.CLAVE
    servicio: str = "wscpe"
    wsaa_wsdl: str = configs.WSAA_WSDL
    wscpe_wsdl: str = configs.WSCPE_WSDL
    ta_cache: Path = field(default_factory=lambda: Path("tickets") / "ta_cache.json")


class ArcaCPE:
    def __init__(self, config: Optional[ArcaConfig] = None):
        self.config = config or ArcaConfig()
        self._wsaa = WSAAClient(
            cert_path=self.config.certificado,
            key_path=self.config.clave,
            wsdl_url=self.config.wsaa_wsdl,
        )
        self._cliente = WSCPEClient(wsdl_url=self.config.wscpe_wsdl, cuit=self.config.cuit)

    # --- Ticket de acceso (se reutiliza hasta que vence) ---
    def _leer_cache(self) -> Optional[Dict[str, str]]:
        ruta = Path(self.config.ta_cache)
        if not ruta.exists():
            return None
        try:
            datos = json.loads(ruta.read_text(encoding="utf-8"))
            clave = f"{self.config.servicio}:{self.config.cuit}:{self.config.wsaa_wsdl}"
            ta = datos.get(clave)
            if ta and datetime.fromisoformat(ta["expira"]) > datetime.now(timezone.utc):
                return ta
        except (ValueError, KeyError, OSError):
            pass
        return None

    def _guardar_cache(self, ta: Dict[str, str]) -> None:
        ruta = Path(self.config.ta_cache)
        ruta.parent.mkdir(parents=True, exist_ok=True)
        try:
            datos = json.loads(ruta.read_text(encoding="utf-8")) if ruta.exists() else {}
        except (ValueError, OSError):
            datos = {}
        datos[f"{self.config.servicio}:{self.config.cuit}:{self.config.wsaa_wsdl}"] = ta
        ruta.write_text(json.dumps(datos), encoding="utf-8")

    def _login(self, forzar: bool = False) -> None:
        ta = None if forzar else self._leer_cache()
        if not ta:
            tra = self._wsaa.generar_login_ticket_request(int(time.time()), self.config.servicio)
            respuesta = self._wsaa.enviar_login_cms(self._wsaa.firmar_ticket_request(tra))
            token, sign = WSAAClient.extract_credentials(respuesta)
            if not token or not sign:
                raise ArcaError("WSAA no devolvió token/sign.")
            expira = ET.fromstring(respuesta).findtext(".//expirationTime")
            expira_dt = datetime.fromisoformat(expira).astimezone(timezone.utc)
            # Margen de 5 minutos para no usar un TA a punto de vencer
            vence = datetime.fromtimestamp(expira_dt.timestamp() - 300, timezone.utc)
            ta = {"token": token, "sign": sign, "expira": vence.isoformat()}
            self._guardar_cache(ta)
        self._cliente.set_credentials(ta["token"], ta["sign"], self.config.cuit)

    # --- Llamada genérica ---
    def llamar(self, operacion: str, solicitud: Optional[Dict[str, Any]] = None, _reintento: bool = True) -> Dict[str, Any]:
        """Ejecuta cualquier operación de WSCPE y devuelve dict. Lanza ArcaError si ARCA informa errores."""
        self._login()
        auth = self._cliente._get_auth_header()
        kwargs: Dict[str, Any] = {"auth": auth}
        if solicitud is not None:
            kwargs["solicitud"] = solicitud
        try:
            bruto = getattr(self._cliente.client.service, operacion)(**kwargs)
        except Fault as fault:
            texto = str(fault.message)
            if _reintento and "expir" in texto.lower():
                self._login(forzar=True)
                return self.llamar(operacion, solicitud, _reintento=False)
            raise ArcaError(texto) from fault

        respuesta = serialize_object(bruto, target_cls=dict)
        self._validar(respuesta)
        return respuesta

    @staticmethod
    def _validar(respuesta: Any) -> None:
        errores = respuesta.get("errores") if isinstance(respuesta, dict) else None
        if not errores:
            return
        lista = errores.get("error", errores) if isinstance(errores, dict) else errores
        lista = lista if isinstance(lista, list) else [lista]
        mensaje = "; ".join(f"{e.get('codigo', '')}: {e.get('descripcion', e)}" if isinstance(e, dict) else str(e) for e in lista)
        raise ArcaError(mensaje, lista)

    # --- Operaciones frecuentes ---
    def estado(self) -> Dict[str, Any]:
        return serialize_object(self._cliente.dummy(), target_cls=dict)

    def autorizar_cpe_automotor(self, solicitud: Dict[str, Any]) -> Dict[str, Any]:
        return self.llamar("autorizarCPEAutomotor", solicitud)

    def consultar_cpe_automotor(self, **solicitud: Any) -> Dict[str, Any]:
        return self.llamar("consultarCPEAutomotor", solicitud)

    def ultimo_nro_orden(self, sucursal: int, tipo_cpe: int) -> Dict[str, Any]:
        return self.llamar("consultarUltNroOrden", {"sucursal": sucursal, "tipoCPE": tipo_cpe})

    def anular_cpe(self, **solicitud: Any) -> Dict[str, Any]:
        return self.llamar("anularCPE", solicitud)

    def confirmar_arribo(self, **solicitud: Any) -> Dict[str, Any]:
        return self.llamar("confirmarArriboCPE", solicitud)

    def rechazar_cpe(self, **solicitud: Any) -> Dict[str, Any]:
        return self.llamar("rechazoCPE", solicitud)

    def descargado_destino(self, **solicitud: Any) -> Dict[str, Any]:
        return self.llamar("descargadoDestinoCPE", solicitud)

    def desvio_automotor(self, **solicitud: Any) -> Dict[str, Any]:
        return self.llamar("desvioCPEAutomotor", solicitud)

    def confirmacion_definitiva_automotor(self, **solicitud: Any) -> Dict[str, Any]:
        return self.llamar("confirmacionDefinitivaCPEAutomotor", solicitud)

    def editar_cpe_automotor(self, **solicitud: Any) -> Dict[str, Any]:
        return self.llamar("editarCPEAutomotor", solicitud)

    def nuevo_destino_destinatario_automotor(self, **solicitud: Any) -> Dict[str, Any]:
        return self.llamar("nuevoDestinoDestinatarioCPEAutomotor", solicitud)

    def regreso_origen_automotor(self, **solicitud: Any) -> Dict[str, Any]:
        return self.llamar("regresoOrigenCPEAutomotor", solicitud)

    def informar_contingencia(self, **solicitud: Any) -> Dict[str, Any]:
        return self.llamar("informarContingencia", solicitud)

    def cerrar_contingencia(self, **solicitud: Any) -> Dict[str, Any]:
        return self.llamar("cerrarContingenciaCPE", solicitud)

    def consultar_cpe_por_destino(self, **solicitud: Any) -> Dict[str, Any]:
        return self.llamar("consultarCPEPorDestino", solicitud)

    def consultar_pendientes_resolucion(self, **solicitud: Any) -> Dict[str, Any]:
        return self.llamar("consultarCPEPPendientesDeResolucion", solicitud)

    # --- Catálogos ---
    def provincias(self) -> Dict[str, Any]:
        return self.llamar("consultarProvincias")

    def localidades(self, cod_provincia: int) -> Dict[str, Any]:
        return self.llamar("consultarLocalidadesPorProvincia", {"codProvincia": cod_provincia})

    def tipos_grano(self) -> Dict[str, Any]:
        return self.llamar("consultarTiposGrano")

    def plantas(self, cuit: Optional[str] = None) -> Dict[str, Any]:
        return self.llamar("consultarPlantas", {"cuit": int(cuit or self.config.cuit)})

    def renspa(self, **solicitud: Any) -> Dict[str, Any]:
        return self.llamar("consultarRenspa", solicitud)
