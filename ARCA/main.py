import argparse
import json
from pathlib import Path
from typing import Optional

from config import configs
from config.logging import logging
from wsaa_client import WSAAClient
from wscpe_client import WSCPEClient


PLANTILLA_CPE_AUTOMOTOR = {
    "cabecera": {
        "tipoCP": None,
        "cuitSolicitante": None,
        "sucursal": None,
        "nroOrden": None,
    },
    "origen": {
        "operador": None,
        "productor": {
            "codProvincia": None,
            "codLocalidad": None,
            "nroRenspa": None,
            "coordenadasGPS": None,
        },
    },
    "correspondeRetiroProductor": None,
    "esSolicitanteCampo": None,
    "retiroProductor": None,
    "intervinientes": None,
    "datosCarga": {
        "codGrano": None,
        "cosecha": None,
        "pesoBruto": None,
        "pesoTara": None,
    },
    "destino": {
        "cuit": None,
        "esDestinoCampo": None,
        "codProvincia": None,
        "codLocalidad": None,
        "planta": None,
    },
    "destinatario": {"cuit": None},
    "transporte": {
        "cuitTransportista": None,
        "dominio": [],
        "fechaHoraPartida": None,
        "kmRecorrer": None,
        "codigoTurno": None,
        "cuitChofer": None,
        "tarifa": None,
        "cuitPagadorFlete": None,
        "cuitIntermediarioFlete": None,
        "mercaderiaFumigada": None,
    },
    "observaciones": None,
}


def cargar_solicitud_cpe(ruta: str) -> dict:
    with Path(ruta).open("r", encoding="utf-8") as archivo:
        solicitud = json.load(archivo)
    if not isinstance(solicitud, dict):
        raise ValueError("El JSON debe contener un objeto con los campos de la solicitud.")
    return _quitar_valores_vacios(solicitud)


def _quitar_valores_vacios(valor):
    if isinstance(valor, dict):
        return {clave: _quitar_valores_vacios(item) for clave, item in valor.items() if item is not None}
    if isinstance(valor, list):
        return [_quitar_valores_vacios(item) for item in valor if item is not None]
    return valor


def validar_solicitud_cpe(solicitud: dict) -> None:
    campos_obligatorios = (
        "cabecera.tipoCP",
        "cabecera.cuitSolicitante",
        "cabecera.sucursal",
        "cabecera.nroOrden",
        "correspondeRetiroProductor",
        "esSolicitanteCampo",
        "datosCarga.codGrano",
        "datosCarga.cosecha",
        "datosCarga.pesoBruto",
        "datosCarga.pesoTara",
        "destino.cuit",
        "destino.esDestinoCampo",
        "destino.codProvincia",
        "destino.codLocalidad",
        "destinatario.cuit",
        "transporte.cuitTransportista",
        "transporte.fechaHoraPartida",
        "transporte.kmRecorrer",
        "transporte.cuitChofer",
        "transporte.cuitPagadorFlete",
        "transporte.mercaderiaFumigada",
    )
    pendientes = []
    for campo in campos_obligatorios:
        valor = solicitud
        for parte in campo.split("."):
            valor = valor.get(parte) if isinstance(valor, dict) else None
        if valor is None or valor == "":
            pendientes.append(campo)

    dominios = solicitud.get("transporte", {}).get("dominio", [])
    if not isinstance(dominios, list) or not dominios:
        pendientes.append("transporte.dominio (al menos un vehículo)")

    origen = solicitud.get("origen", {})
    if not isinstance(origen, dict) or not any(origen.get(tipo) for tipo in ("operador", "productor")):
        pendientes.append("origen.operador o origen.productor")
    else:
        origen_requerido = {
            "operador": ("codProvincia", "codLocalidad", "planta"),
            "productor": ("codProvincia", "codLocalidad"),
        }
        for tipo, campos in origen_requerido.items():
            datos_origen = origen.get(tipo)
            if datos_origen:
                for campo in campos:
                    if datos_origen.get(campo) is None or datos_origen.get(campo) == "":
                        pendientes.append(f"origen.{tipo}.{campo}")

    if pendientes:
        raise ValueError("Completa estos campos antes de simular o enviar: " + ", ".join(pendientes))


def crear_plantilla_cpe(ruta: str) -> None:
    destino = Path(ruta)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(PLANTILLA_CPE_AUTOMOTOR, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Plantilla creada: {destino}")


def simular_cpe_automotor(ruta: str, cuit: Optional[str] = None) -> None:
    solicitud = cargar_solicitud_cpe(ruta)
    validar_solicitud_cpe(solicitud)
    cliente = WSCPEClient(cuit=cuit or configs.CUIT, wsdl_url=configs.WSCPE_WSDL)
    soap = cliente.previsualizar_autorizacion_cpe_automotor(solicitud)
    print("Vista previa local: no se solicitó autorización y no se envió ninguna CPE.")
    print(soap)


def crear_cpe_automotor(ruta: str, cuit: Optional[str] = None) -> None:
    cuit_activo = cuit or configs.CUIT
    solicitud = cargar_solicitud_cpe(ruta)
    validar_solicitud_cpe(solicitud)
    wsaa = WSAAClient(wsdl_url=configs.WSAA_WSDL)
    try:
        token, sign = wsaa.obtener_ticket("wscpe")
    finally:
        configs.incrementa_id()

    if not token or not sign:
        raise RuntimeError("WSAA no devolvió token/sign para wscpe.")

    cliente = WSCPEClient(token=token, sign=sign, cuit=cuit_activo, wsdl_url=configs.WSCPE_WSDL)
    respuesta = cliente.autorizar_cpe_automotor(solicitud)
    print(json.dumps(respuesta, default=str, ensure_ascii=False, indent=2))


def ejecutar_flujo(
    servicio_negocio: str = configs.SERVICIO,
    cuit: Optional[str] = None,
    probar_dummy_cpe: bool = True,
):
    """
    Flujo principal:
    1. Verifica conectividad con el Web Service WSCPE mediante dummy()
    2. Obtiene ticket de acceso (token y sign) ante WSAA para el servicio indicado
    3. Si el ticket es exitoso y el servicio es 'wscpe', ejecuta consultas al servicio CPE
    """
    logging.info("=" * 80)
    logging.info(f"Iniciando flujo para servicio: {servicio_negocio} (Ambiente: {configs.AMBIENTE})")
    cuit_activo = cuit or configs.CUIT

    # 1. Instanciar cliente WSCPE y probar estado del servidor (dummy no requiere auth)
    cpe_client = WSCPEClient(wsdl_url=configs.WSCPE_WSDL, cuit=cuit_activo)
    if probar_dummy_cpe:
        try:
            estado_cpe = cpe_client.dummy()
            logging.info(f"Estado WSCPE dummy(): {estado_cpe}")
            print(f"[OK] WSCPE dummy: {estado_cpe}")
        except Exception as e:
            logging.error(f"Falla al ejecutar dummy() en WSCPE: {e}")
            print(f"[ERROR] WSCPE dummy: {e}")

    # 2. Obtener credenciales desde WSAA
    wsaa = WSAAClient(
        cert_path=configs.CERTIFICADO,
        key_path=configs.CLAVE,
        wsdl_url=configs.WSAA_WSDL,
    )

    token, sign = None, None
    try:
        logging.info(f"Solicitando Ticket de Acceso (TRA) para servicio '{servicio_negocio}' con ID {configs.ID_CONSULTA}...")
        token, sign = wsaa.obtener_ticket(service=servicio_negocio)
        configs.incrementa_id()
        logging.info("Ticket obtenido correctamente desde WSAA.")
        print(f"[OK] WSAA Ticket obtenido para '{servicio_negocio}'. Token y Sign listos.")
    except Exception as e:
        configs.incrementa_id()
        logging.error(f"Error al obtener ticket de acceso en WSAA: {e}")
        print(f"[AVISO WSAA] No se pudo obtener ticket para '{servicio_negocio}': {e}")
        if "Computador no autorizado" in str(e):
            print(
                "\n--> NOTA: Este certificado (CUIT 20361814305) aún no tiene asociado el servicio "
                f"'{servicio_negocio}' en WSASS (Administración de certificados de homologación/testing)."
                "\n    Para habilitarlo en testing: ingresar con Clave Fiscal a WSASS y asociar el computador "
                f"fiscal a '{servicio_negocio}'."
            )
        return

    # 3. Consumir consultas del servicio WSCPE con las credenciales
    if servicio_negocio == "wscpe" and token and sign:
        cpe_client.set_credentials(token=token, sign=sign, cuit=cuit_activo)
        try:
            logging.info("Consultando catálogo de provincias en WSCPE...")
            provincias = cpe_client.consultar_provincias()
            print(f"[OK] Provincias obtenidas: {provincias}")
        except Exception as e:
            logging.error(f"Error al consultar provincias en WSCPE: {e}")
            print(f"[ERROR WSCPE] {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Cliente ARCA / AFIP WSAA + WSCPE")
    acciones = parser.add_mutually_exclusive_group()
    acciones.add_argument("--plantilla-cpe", metavar="ARCHIVO", help="Crea una plantilla JSON vacía para CPE automotor.")
    acciones.add_argument("--simular-cpe", metavar="JSON", help="Valida y muestra el SOAP de una CPE sin enviarlo.")
    acciones.add_argument("--crear-cpe", metavar="JSON", help="Envía una solicitud para autorizar una CPE automotor.")
    parser.add_argument(
        "--confirmar-envio",
        action="store_true",
        help="Confirma el envío real de la CPE al ambiente configurado.",
    )
    parser.add_argument(
        "--servicio",
        default=configs.SERVICIO,
        help="Servicio a autenticar en WSAA (ej: wscpe, wsfe)",
    )
    parser.add_argument(
        "--cuit",
        default=configs.CUIT,
        help="CUIT de la representada (por defecto la del certificado)",
    )
    args = parser.parse_args()

    try:
        if args.plantilla_cpe:
            if args.confirmar_envio:
                parser.error("--confirmar-envio solo se utiliza con --crear-cpe.")
            crear_plantilla_cpe(args.plantilla_cpe)
        elif args.simular_cpe:
            if args.confirmar_envio:
                parser.error("--confirmar-envio no se utiliza con --simular-cpe.")
            simular_cpe_automotor(args.simular_cpe, cuit=args.cuit)
        elif args.crear_cpe:
            if not args.confirmar_envio:
                parser.error("El envío de una CPE requiere --confirmar-envio explícito.")
            if configs.ES_PRODUCCION:
                parser.error("El envío real está bloqueado en producción desde esta herramienta; use homologación.")
            crear_cpe_automotor(args.crear_cpe, cuit=args.cuit)
        else:
            if args.confirmar_envio:
                parser.error("--confirmar-envio requiere --crear-cpe ARCHIVO.json.")
            ejecutar_flujo(servicio_negocio=args.servicio, cuit=args.cuit)
    except Exception as error:
        logging.error(f"Falló la operación solicitada: {error}")
        parser.exit(1, f"[ERROR] {error}\n")


