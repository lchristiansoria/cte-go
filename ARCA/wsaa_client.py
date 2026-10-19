import datetime
import os
import shutil
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional, Tuple

from zeep import Client
from zeep.exceptions import Fault

from config import configs
from config.logging import logging

try:
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.serialization import pkcs7

    HAS_CRYPTOGRAPHY = True
except ImportError:
    HAS_CRYPTOGRAPHY = False


class WSAAClient:
    """
    Cliente para el Web Service de Autenticación y Autorización (WSAA) de ARCA/AFIP.
    Referencia: https://www.arca.gob.ar/ws/WSAA/WSAAmanualDev.pdf
    """

    def __init__(
        self,
        cert_path: str = configs.CERTIFICADO,
        key_path: str = configs.CLAVE,
        wsdl_url: str = configs.WSAA_WSDL,
    ):
        self.cert_path = Path(cert_path)
        self.key_path = Path(key_path)
        self.wsdl_url = wsdl_url
        self.tickets_dir = Path("tickets")
        self.tickets_firmados_dir = Path("tickets_firmados")
        self.tickets_dir.mkdir(parents=True, exist_ok=True)
        self.tickets_firmados_dir.mkdir(parents=True, exist_ok=True)

    def generar_login_ticket_request(self, unique_id: int, service: str) -> Path:
        """
        Crea el archivo XML LoginTicketRequest (TRA) con generación y expiración.
        """
        now = datetime.datetime.now(datetime.timezone.utc)
        generation_time = now - datetime.timedelta(minutes=10)
        expiration_time = now + datetime.timedelta(minutes=10)

        root = ET.Element("loginTicketRequest", version="1.0")
        header = ET.SubElement(root, "header")
        ET.SubElement(header, "uniqueId").text = str(unique_id)
        ET.SubElement(header, "generationTime").text = generation_time.strftime("%Y-%m-%dT%H:%M:%SZ")
        ET.SubElement(header, "expirationTime").text = expiration_time.strftime("%Y-%m-%dT%H:%M:%SZ")
        ET.SubElement(root, "service").text = service

        tree = ET.ElementTree(root)
        file_name = self.tickets_dir / f"LoginTicketRequest_{service}_{unique_id}.xml"
        tree.write(file_name, encoding="utf-8", xml_declaration=True)
        logging.info(f"TRA generado en: {file_name}")
        return file_name

    def firmar_ticket_request(self, input_file: Path) -> str:
        """
        Genera el CMS/PKCS#7 firmado. Prefiere la biblioteca `cryptography`
        (sin dependencia de openssl externo en Windows) con fallback a `openssl`.
        """
        xml_bytes = input_file.read_bytes()

        if HAS_CRYPTOGRAPHY:
            try:
                cert = x509.load_pem_x509_certificate(self.cert_path.read_bytes())
                key = serialization.load_pem_private_key(self.key_path.read_bytes(), password=None)
                signed_pem = (
                    pkcs7.PKCS7SignatureBuilder()
                    .set_data(xml_bytes)
                    .add_signer(cert, key, hashes.SHA256())
                    .sign(serialization.Encoding.PEM, [pkcs7.PKCS7Options.Binary])
                )
                output_file = self.tickets_firmados_dir / f"{input_file.name}.cms"
                output_file.write_bytes(signed_pem)

                cms_text = signed_pem.decode("utf-8")
                if "-----BEGIN PKCS7-----" in cms_text:
                    return cms_text.split("-----BEGIN PKCS7-----")[1].split("-----END PKCS7-----")[0].strip()
                if "-----BEGIN CMS-----" in cms_text:
                    return cms_text.split("-----BEGIN CMS-----")[1].split("-----END CMS-----")[0].strip()
                return cms_text.strip()
            except Exception as e:
                logging.warning(f"Falla al firmar con cryptography, probando OpenSSL: {e}")

        openssl_bin = shutil.which("openssl")
        if not openssl_bin:
            # Ubicaciones comunes de Git en Windows
            git_openssl = Path("C:/Program Files/Git/mingw64/bin/openssl.exe")
            if git_openssl.exists():
                openssl_bin = str(git_openssl)

        if not openssl_bin:
            raise RuntimeError("No se encontró 'openssl' ni módulo cryptography para firmar el TRA.")

        output_file = self.tickets_firmados_dir / f"{input_file.name}.cms"
        comando = [
            openssl_bin,
            "cms",
            "-sign",
            "-in",
            str(input_file),
            "-out",
            str(output_file),
            "-signer",
            str(self.cert_path),
            "-inkey",
            str(self.key_path),
            "-nodetach",
            "-outform",
            "PEM",
        ]
        subprocess.run(comando, check=True)
        cms_data = output_file.read_text(encoding="utf-8")
        if "-----BEGIN CMS-----" in cms_data:
            return cms_data.split("-----BEGIN CMS-----")[1].split("-----END CMS-----")[0].strip()
        if "-----BEGIN PKCS7-----" in cms_data:
            return cms_data.split("-----BEGIN PKCS7-----")[1].split("-----END PKCS7-----")[0].strip()
        return cms_data.strip()

    def enviar_login_cms(self, cms_content: str) -> str:
        """
        Invoca la operación loginCms en el endpoint de WSAA.
        """
        logging.info(f"Enviando loginCms a WSAA ({self.wsdl_url})...")
        client = Client(wsdl=self.wsdl_url)
        response = client.service.loginCms(cms_content)
        return response

    @staticmethod
    def extract_credentials(xml_response: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Extrae token y sign del XML de LoginTicketResponse.
        """
        try:
            root = ET.fromstring(xml_response)
            token_elem = root.find(".//credentials/token")
            sign_elem = root.find(".//credentials/sign")
            token = token_elem.text if token_elem is not None else None
            sign = sign_elem.text if sign_elem is not None else None
            return token, sign
        except ET.ParseError as e:
            logging.error(f"Error al parsear respuesta XML de WSAA: {e}")
            return None, None

    def obtener_ticket(self, service: str, unique_id: Optional[int] = None) -> Tuple[Optional[str], Optional[str]]:
        """
        Ejecuta el ciclo completo de autenticación ante WSAA para el servicio solicitado.
        """
        if unique_id is None:
            unique_id = int(configs.ID_CONSULTA)

        tra_file = self.generar_login_ticket_request(unique_id=unique_id, service=service)
        cms_content = self.firmar_ticket_request(tra_file)
        respuesta_xml = self.enviar_login_cms(cms_content)
        return self.extract_credentials(respuesta_xml)
