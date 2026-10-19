from __future__ import annotations

import base64
import binascii
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import os
import threading
import time
import xml.etree.ElementTree as ET
from typing import Any

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.serialization import pkcs7
from zeep import Client
from zeep.exceptions import Fault
from zeep.helpers import serialize_object
from zeep.transports import Transport


class ArcaConfigurationError(Exception):
    pass


class ArcaServiceError(Exception):
    pass


@dataclass(frozen=True)
class ArcaSettings:
    wsaa_wsdl: str
    wscpe_wsdl: str
    cuit: str
    certificate_base64: str
    private_key_base64: str
    private_key_password: str | None = None
    timeout: int = 30

    @classmethod
    def from_env(cls) -> ArcaSettings:
        required = {
            "URL_ARCA_WSAA": os.getenv("URL_ARCA_WSAA"),
            "URL_ARCA_WS": os.getenv("URL_ARCA_WS"),
            "CUIT_ARCA": os.getenv("CUIT_ARCA"),
            "CERT_ARCA_BASE64": os.getenv("CERT_ARCA_BASE64"),
            "KEY_ARCA_BASE64": os.getenv("KEY_ARCA_BASE64"),
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            raise ArcaConfigurationError(
                "ARCA configuration is incomplete: " + ", ".join(missing)
            )

        cuit = required["CUIT_ARCA"]
        if not cuit.isdigit() or len(cuit) != 11:
            raise ArcaConfigurationError("CUIT_ARCA must contain 11 digits.")

        try:
            timeout = int(os.getenv("TIMEOUT_ARCA", "30"))
        except ValueError as exc:
            raise ArcaConfigurationError("TIMEOUT_ARCA must be an integer.") from exc
        if timeout < 1:
            raise ArcaConfigurationError("TIMEOUT_ARCA must be greater than zero.")

        return cls(
            wsaa_wsdl=required["URL_ARCA_WSAA"],
            wscpe_wsdl=required["URL_ARCA_WS"],
            cuit=cuit,
            certificate_base64=required["CERT_ARCA_BASE64"],
            private_key_base64=required["KEY_ARCA_BASE64"],
            private_key_password=os.getenv("PASS_ARCA") or None,
            timeout=timeout,
        )


class ArcaCPEClient:
    def __init__(self, settings: ArcaSettings) -> None:
        self.settings = settings
        self._certificate, self._private_key = self._load_credentials()
        self._wsaa_client: Client | None = None
        self._wscpe_client: Client | None = None
        self._ticket: tuple[str, str, datetime] | None = None
        self._ticket_lock = threading.Lock()

    def _load_credentials(self):
        try:
            certificate_bytes = base64.b64decode(
                self.settings.certificate_base64, validate=True
            )
            private_key_bytes = base64.b64decode(
                self.settings.private_key_base64, validate=True
            )
            certificate = x509.load_pem_x509_certificate(certificate_bytes)
            passphrase = (
                self.settings.private_key_password.encode()
                if self.settings.private_key_password
                else None
            )
            private_key = serialization.load_pem_private_key(
                private_key_bytes, passphrase
            )
        except (ValueError, TypeError, binascii.Error) as exc:
            raise ArcaConfigurationError(
                "ARCA certificate or private key is invalid."
            ) from exc
        return certificate, private_key

    def _soap_client(self, *, wsaa: bool = False) -> Client:
        if wsaa:
            if self._wsaa_client is None:
                self._wsaa_client = Client(
                    wsdl=self.settings.wsaa_wsdl,
                    transport=Transport(timeout=self.settings.timeout),
                )
            return self._wsaa_client
        if self._wscpe_client is None:
            self._wscpe_client = Client(
                wsdl=self.settings.wscpe_wsdl,
                transport=Transport(timeout=self.settings.timeout),
            )
        return self._wscpe_client

    def _get_ticket(self, *, force: bool = False) -> tuple[str, str]:
        with self._ticket_lock:
            now = datetime.now(timezone.utc)
            if not force and self._ticket and self._ticket[2] > now:
                return self._ticket[0], self._ticket[1]

            generation_time = now - timedelta(minutes=10)
            expiration_time = now + timedelta(minutes=10)
            root = ET.Element("loginTicketRequest", version="1.0")
            header = ET.SubElement(root, "header")
            ET.SubElement(header, "uniqueId").text = str(int(time.time()))
            ET.SubElement(header, "generationTime").text = generation_time.strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            )
            ET.SubElement(header, "expirationTime").text = expiration_time.strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            )
            ET.SubElement(root, "service").text = "wscpe"
            tra = ET.tostring(root, encoding="utf-8", xml_declaration=True)

            cms = (
                pkcs7.PKCS7SignatureBuilder()
                .set_data(tra)
                .add_signer(self._certificate, self._private_key, hashes.SHA256())
                .sign(serialization.Encoding.PEM, [pkcs7.PKCS7Options.Binary])
            )
            cms_content = b"".join(
                line
                for line in cms.splitlines()
                if not line.startswith(b"-----")
            ).decode("ascii")
            response = self._soap_client(wsaa=True).service.loginCms(cms_content)
            token, sign, expires = self._parse_login_ticket(response)
            self._ticket = (token, sign, expires - timedelta(minutes=5))
            return token, sign

    @staticmethod
    def _parse_login_ticket(response: str) -> tuple[str, str, datetime]:
        try:
            root = ET.fromstring(response)
            fields = {
                element.tag.rsplit("}", 1)[-1]: element.text
                for element in root.iter()
                if element.tag.rsplit("}", 1)[-1]
                in {"token", "sign", "expirationTime"}
            }
            token = fields["token"]
            sign = fields["sign"]
            expires = datetime.fromisoformat(
                fields["expirationTime"].replace("Z", "+00:00")
            )
            if expires.tzinfo is None:
                expires = expires.replace(tzinfo=timezone.utc)
            return token, sign, expires.astimezone(timezone.utc)
        except (ET.ParseError, KeyError, TypeError, ValueError) as exc:
            raise ArcaServiceError("WSAA returned an invalid login ticket.") from exc

    def _call(self, operation: str, solicitud: dict[str, Any] | None = None) -> Any:
        for attempt in range(2):
            try:
                token, sign = self._get_ticket(force=attempt > 0)
                auth = {
                    "token": token,
                    "sign": sign,
                    "cuitRepresentada": int(self.settings.cuit),
                }
                kwargs: dict[str, Any] = {"auth": auth}
                if solicitud is not None:
                    kwargs["solicitud"] = solicitud
                response = getattr(self._soap_client().service, operation)(**kwargs)
                result = serialize_object(response, target_cls=dict)
                self._raise_response_errors(result)
                return result
            except Fault as exc:
                if attempt == 0 and "expir" in str(exc).lower():
                    self._ticket = None
                    continue
                raise ArcaServiceError("ARCA rejected the query.") from exc
            except ArcaServiceError:
                raise
            except Exception as exc:
                raise ArcaServiceError("ARCA query failed.") from exc
        raise ArcaServiceError("ARCA query failed.")

    @staticmethod
    def _raise_response_errors(response: Any) -> None:
        if not isinstance(response, dict):
            return
        errors = response.get("errores")
        if not errors:
            return
        if isinstance(errors, dict):
            errors = errors.get("error", errors)
        error_list = errors if isinstance(errors, list) else [errors]
        message = "; ".join(
            f"{error.get('codigo', '')}: {error.get('descripcion', '')}".strip(": ")
            if isinstance(error, dict)
            else str(error)
            for error in error_list
        )
        raise ArcaServiceError(message or "ARCA rejected the query.")

    def consultar_provincias(self) -> Any:
        return self._call("consultarProvincias")

    def consultar_localidades(self, cod_provincia: int) -> Any:
        return self._call(
            "consultarLocalidadesPorProvincia", {"codProvincia": cod_provincia}
        )

    def consultar_tipos_grano(self) -> Any:
        return self._call("consultarTiposGrano")

    def consultar_plantas(self, cuit: str | None = None) -> Any:
        return self._call(
            "consultarPlantas", {"cuit": int(cuit or self.settings.cuit)}
        )

    def consultar_ultimo_nro_orden(self, sucursal: int, tipo_cpe: int) -> Any:
        return self._call(
            "consultarUltNroOrden", {"sucursal": sucursal, "tipoCPE": tipo_cpe}
        )

    def consultar_cpe_automotor(
        self,
        *,
        cuit_solicitante: str | None = None,
        tipo_cpe: int | None = None,
        sucursal: int | None = None,
        nro_orden: int | None = None,
        nro_ctg: int | None = None,
    ) -> Any:
        solicitud: dict[str, Any] = {}
        if cuit_solicitante:
            solicitud["cuitSolicitante"] = int(cuit_solicitante)
        if tipo_cpe is not None and sucursal is not None and nro_orden is not None:
            solicitud["cartaPorte"] = {
                "tipoCPE": tipo_cpe,
                "sucursal": sucursal,
                "nroOrden": nro_orden,
            }
        if nro_ctg is not None:
            solicitud["nroCTG"] = nro_ctg
        return self._call("consultarCPEAutomotor", solicitud)
