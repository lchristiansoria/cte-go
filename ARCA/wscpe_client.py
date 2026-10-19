from typing import Any, Dict, Optional
from zeep import Client
from zeep.exceptions import Fault

from config import configs
from config.logging import logging


class WSCPEClient:
    """
    Cliente SOAP para el Web Service CPE (Carta de Porte Electrónica) de ARCA / AFIP.
    Referencia oficial: https://www.arca.gob.ar/ws/documentos/manual-wscpe.pdf (v2.2.1)
    """

    def __init__(
        self,
        token: Optional[str] = None,
        sign: Optional[str] = None,
        cuit: Optional[str] = None,
        wsdl_url: str = configs.WSCPE_WSDL,
    ):
        self.wsdl_url = wsdl_url
        self.token = token
        self.sign = sign
        self.cuit = cuit or configs.CUIT
        logging.info(f"Inicializando cliente WSCPE con WSDL: {self.wsdl_url}")
        self.client = Client(wsdl=self.wsdl_url)

    def set_credentials(self, token: str, sign: str, cuit: Optional[str] = None):
        """
        Actualiza credenciales devueltas por WSAA.
        """
        self.token = token
        self.sign = sign
        if cuit:
            self.cuit = cuit

    def _get_auth_header(self, cuit: Optional[str] = None) -> Dict[str, Any]:
        """
        Construye la estructura Auth requerida por las operaciones de WSCPE:
        <auth>
            <token>...</token>
            <sign>...</sign>
            <cuitRepresentada>...</cuitRepresentada>
        </auth>
        """
        if not self.token or not self.sign:
            raise ValueError("Token y Sign son requeridos. Obtenga primero el ticket con WSAA.")

        cuit_final = int(cuit or self.cuit)
        return {
            "token": self.token,
            "sign": self.sign,
            "cuitRepresentada": cuit_final,
        }

    # =========================================================================
    # 2.10.1 Verificación del servicio (no requiere autenticación)
    # =========================================================================
    def dummy(self) -> Dict[str, Any]:
        """
        Verifica el estado y la disponibilidad del servicio (appserver, authserver, dbserver).
        No requiere token/sign.
        """
        logging.info("Ejecutando método dummy() en WSCPE...")
        return self.client.service.dummy()

    # =========================================================================
    # Consultas de tablas maestras y parámetros
    # =========================================================================
    def consultar_provincias(self, cuit: Optional[str] = None) -> Any:
        """
        2.10.2 Consulta de provincias.
        """
        auth = self._get_auth_header(cuit)
        logging.info("Consultando catálogo de provincias...")
        return self.client.service.consultarProvincias(auth=auth)

    def consultar_localidades_por_provincia(self, cod_provincia: int, cuit: Optional[str] = None) -> Any:
        """
        2.10.3 Consulta de localidades por código de provincia.
        """
        auth = self._get_auth_header(cuit)
        logging.info(f"Consultando localidades de provincia {cod_provincia}...")
        solicitud = {"codProvincia": cod_provincia}
        return self.client.service.consultarLocalidadesPorProvincia(auth=auth, solicitud=solicitud)

    def consultar_tipos_grano(self, cuit: Optional[str] = None) -> Any:
        """
        2.10.4 Consulta de tipos de grano permitidos.
        """
        auth = self._get_auth_header(cuit)
        logging.info("Consultando tipos de grano...")
        return self.client.service.consultarTiposGrano(auth=auth)

    def consultar_tipos_embalaje(self, cuit: Optional[str] = None) -> Any:
        """
        Consulta de tipos de embalaje.
        """
        auth = self._get_auth_header(cuit)
        logging.info("Consultando tipos de embalaje...")
        return self.client.service.consultarTiposEmbalaje(auth=auth)

    def consultar_unidades_medida(self, cuit: Optional[str] = None) -> Any:
        """
        Consulta de unidades de medida.
        """
        auth = self._get_auth_header(cuit)
        logging.info("Consultando unidades de medida...")
        return self.client.service.consultarUnidadesMedida(auth=auth)

    def consultar_plantas(self, cuit_planta: Optional[str] = None, cuit_representada: Optional[str] = None) -> Any:
        """
        Consulta de plantas activas para una CUIT.
        """
        auth = self._get_auth_header(cuit_representada)
        target_cuit = int(cuit_planta or self.cuit)
        logging.info(f"Consultando plantas para CUIT {target_cuit}...")
        solicitud = {"cuit": target_cuit}
        return self.client.service.consultarPlantas(auth=auth, solicitud=solicitud)

    # =========================================================================
    # Consultas de gestión de Cartas de Porte Electrónicas
    # =========================================================================
    def consultar_ultimo_nro_orden(self, sucursal: int, tipo_cpe: int, cuit: Optional[str] = None) -> Any:
        """
        2.10.5 Consultar último número de orden emitido y aprobado por sucursal y tipo de CPE.
        """
        auth = self._get_auth_header(cuit)
        logging.info(f"Consultando último número de orden para sucursal {sucursal}, tipo {tipo_cpe}...")
        solicitud = {
            "sucursal": sucursal,
            "tipoCPE": tipo_cpe,
        }
        return self.client.service.consultarUltNroOrden(auth=auth, solicitud=solicitud)

    def consultar_cpe_automotor(
        self,
        cuit_solicitante: Optional[str] = None,
        tipo_cpe: Optional[int] = None,
        sucursal: Optional[int] = None,
        nro_orden: Optional[int] = None,
        nro_ctg: Optional[int] = None,
        cuit: Optional[str] = None,
    ) -> Any:
        """
        2.10.21 Consultar CPE Automotor por CUIT/Orden o por número de CTG.
        """
        auth = self._get_auth_header(cuit)
        solicitud: Dict[str, Any] = {}
        if cuit_solicitante:
            solicitud["cuitSolicitante"] = int(cuit_solicitante)
        if tipo_cpe is not None and sucursal is not None and nro_orden is not None:
            solicitud["cartaPorte"] = {
                "tipoCPE": tipo_cpe,
                "sucursal": sucursal,
                "nroOrden": nro_orden,
            }
        if nro_ctg is not None:
            solicitud["nroCTG"] = int(nro_ctg)

        logging.info(f"Consultando CPE automotor con parámetros: {solicitud}")
        return self.client.service.consultarCPEAutomotor(auth=auth, solicitud=solicitud)

    def consultar_cpe_ferroviaria(
        self,
        cuit_solicitante: Optional[str] = None,
        tipo_cpe: Optional[int] = None,
        sucursal: Optional[int] = None,
        nro_orden: Optional[int] = None,
        nro_ctg: Optional[int] = None,
        cuit: Optional[str] = None,
    ) -> Any:
        """
        Consultar CPE Ferroviaria.
        """
        auth = self._get_auth_header(cuit)
        solicitud: Dict[str, Any] = {}
        if cuit_solicitante:
            solicitud["cuitSolicitante"] = int(cuit_solicitante)
        if tipo_cpe is not None and sucursal is not None and nro_orden is not None:
            solicitud["cartaPorte"] = {
                "tipoCPE": tipo_cpe,
                "sucursal": sucursal,
                "nroOrden": nro_orden,
            }
        if nro_ctg is not None:
            solicitud["nroCTG"] = int(nro_ctg)

        logging.info(f"Consultando CPE ferroviaria con parámetros: {solicitud}")
        return self.client.service.consultarCPEFerroviaria(auth=auth, solicitud=solicitud)

    def previsualizar_autorizacion_cpe_automotor(self, solicitud: Dict[str, Any]) -> str:
        """Serializa la solicitud SOAP sin conectarse ni autorizar una carta de porte."""
        from lxml import etree

        mensaje = self.client.create_message(
            self.client.service,
            "autorizarCPEAutomotor",
            auth={
                "token": "TOKEN_SOLO_SIMULACION",
                "sign": "SIGN_SOLO_SIMULACION",
                "cuitRepresentada": int(self.cuit),
            },
            solicitud=solicitud,
        )
        return etree.tostring(mensaje, pretty_print=True, encoding="unicode")

    def autorizar_cpe_automotor(self, solicitud: Dict[str, Any], cuit: Optional[str] = None) -> Any:
        """Solicita una nueva Carta de Porte Electrónica automotor a WSCPE."""
        auth = self._get_auth_header(cuit)
        logging.info("Enviando solicitud para autorizar CPE automotor a WSCPE.")
        return self.client.service.autorizarCPEAutomotor(auth=auth, solicitud=solicitud)
