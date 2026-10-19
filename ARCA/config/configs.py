import os
from pathlib import Path
from dotenv import load_dotenv
#from config.logging import logging

# Load the .env file
load_dotenv(override=True)

BASE_DIR = Path(__file__).resolve().parent.parent

# Access environment variables
LOGS = os.getenv("LOGS", "./demyn-afip.log")
ID_CONSULTA = os.getenv("ID_CONSULTA", "1")
CERTIFICADO = os.getenv("CERTIFICADO", "MiCertificado.pem")
CLAVE = os.getenv("CLAVE", "MiClavePrivada.key")
SERVICIO = os.getenv("SERVICIO", "wscpe")
CUIT = os.getenv("CUIT", "20361814305")

AMBIENTE = os.getenv("AMBIENTE", "homo").lower()
ES_PRODUCCION = AMBIENTE in ("prod", "produccion", "production")

# URLs oficiales según documentación de ARCA / AFIP
# WSAA: https://www.arca.gob.ar/ws/documentacion/wsaa.asp
WSAA_WSDL_HOMO = "https://wsaahomo.afip.gov.ar/ws/services/LoginCms?wsdl"
WSAA_WSDL_PROD = "https://wsaa.afip.gov.ar/ws/services/LoginCms?wsdl"

# WSCPE: https://www.arca.gob.ar/ws/documentos/manual-wscpe.pdf (Tabla 1)
WSCPE_WSDL_HOMO = "https://cpea-ws-qaext.afip.gob.ar/wscpe/services/soap?wsdl"
WSCPE_WSDL_PROD = "https://cpea-ws.afip.gob.ar/wscpe/services/soap?wsdl"

WSAA_WSDL = WSAA_WSDL_PROD if ES_PRODUCCION else WSAA_WSDL_HOMO
WSCPE_WSDL = WSCPE_WSDL_PROD if ES_PRODUCCION else WSCPE_WSDL_HOMO


def incrementa_id():
    """
    Modifica una variable en el archivo .env y actualiza las variables cargadas.
    """
    variable = "ID_CONSULTA"
    archivo_env = BASE_DIR / ".env"
    try:
        lineas = []
        if archivo_env.exists():
            with open(archivo_env, "r", encoding="utf-8") as file:
                lineas = file.readlines()

        nuevo_valor = str(int(os.getenv(variable, "1")) + 1)
        nueva_configuracion = []
        encontrada = False
        for linea in lineas:
            if linea.strip().startswith(f"{variable}="):
                if not encontrada:
                    nueva_configuracion.append(f"{variable}={nuevo_valor}\n")
                    encontrada = True
            else:
                nueva_configuracion.append(linea)

        if not encontrada:
            nueva_configuracion.append(f"{variable}={nuevo_valor}\n")

        with open(archivo_env, "w", encoding="utf-8") as file:
            file.writelines(nueva_configuracion)

        load_dotenv(override=True)
        valor_actualizado = os.getenv(variable)
        return valor_actualizado
    except Exception as e:
        print(f"Error al modificar el archivo .env: {e}")
        return None
