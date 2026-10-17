from __future__ import annotations

import base64
import json
import os
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import UUID

from ctg_go.api.errors import ApiError
from ctg_go.modules.gestions.schemas import CpeSuggestion, GestionMessageCreateRequest

CPE_FIELDS = {
    "ctg", "nro_cpe", "fecha", "vencimiento", "titular", "rte_productor",
    "rte_venta_primaria", "rte_venta_secundaria", "rte_venta_secundaria_2",
    "mercado_termino", "corredor_primaria", "corredor_secundaria",
    "representante_entregador", "representante_recibidor", "destinatario",
    "destino", "transportista", "chofer", "flete_pagador", "intermediario_flete",
    "grano", "tipo", "campana", "calidad", "peso_bruto", "peso_tara", "peso_neto",
    "observaciones", "proc_localidad", "proc_provincia", "proc_es_campo", "proc_renspa",
    "proc_latitud", "proc_longitud", "proc_descripcion", "dest_planta",
    "dest_localidad", "dest_provincia", "dest_direccion", "dest_es_campo",
    "dominios", "kms", "partida", "tarifa", "tarifa_referencia", "contingencia",
    "contingencia_otro", "desactivacion", "desactivacion_otro", "desc_fecha",
    "desc_arribo", "desc_turno", "desc_peso_bruto", "desc_peso_tara",
    "desc_peso_neto", "desc_localidad", "desc_provincia",
}

SYSTEM_PROMPT = f"""Sos un asistente para preparar borradores de Cartas de Porte Electrónicas.
Analizá el texto y, si existe, la imagen adjunta junto con las CPE de la Gestión.
Respondé exclusivamente JSON válido con este formato:
{{"reply":"respuesta breve en español","suggestions":[{{"cpe_id":"UUID existente o null","title":"título","fields":{{"campo":"valor"}}}}]}}
Usá solo estos nombres de campo: {", ".join(sorted(CPE_FIELDS))}.
Asigná datos a una CPE existente solo si el contexto permite identificarla; si es una carta nueva, usá cpe_id null.
No inventes datos ni completes campos inciertos. Dejá fuera los datos dudosos y preguntá por ellos en reply.
No afirmes que se guardaron cambios: las sugerencias requieren confirmación explícita del operador.
Podés devolver varias sugerencias cuando el mensaje incluya varias cartas."""


def _decode_image(attachment: Any) -> str | None:
    if attachment is None:
        return None
    try:
        image = base64.b64decode(attachment.content_base64, validate=True)
    except (ValueError, base64.binascii.Error) as exc:
        raise ApiError(status_code=422, code="validation_error", message="Invalid image encoding.") from exc
    if not image or len(image) > 5 * 1024 * 1024:
        raise ApiError(status_code=422, code="validation_error", message="Image must be no larger than 5 MB.")
    return f"data:{attachment.media_type};base64,{base64.b64encode(image).decode('ascii')}"


def request_assistant_reply(
    payload: GestionMessageCreateRequest,
    *,
    messages: list[dict[str, str]],
    cpes: list[dict[str, Any]],
) -> tuple[str, list[dict[str, Any]]]:
    token = os.getenv("TOKEN_AI")
    if not token:
        raise ApiError(
            status_code=503,
            code="assistant_not_configured",
            message="El asistente no está configurado. Definí TOKEN_AI y MODEL_AI en el entorno de la API.",
        )
    if not payload.content.strip() and payload.attachment is None:
        raise ApiError(status_code=422, code="validation_error", message="Escribí un mensaje o adjuntá una imagen.")

    user_content: Any = payload.content.strip()
    image_url = _decode_image(payload.attachment)
    if image_url:
        user_content = [
            {"type": "text", "text": payload.content.strip() or "Analizá esta imagen para la Gestión."},
            {"type": "image_url", "image_url": {"url": image_url}},
        ]
    conversation: list[dict[str, Any]] = [{"role": "system", "content": SYSTEM_PROMPT}]
    conversation.extend({"role": item["role"], "content": item["content"]} for item in messages[-12:])
    context = "CPE existentes de esta Gestión: " + json.dumps(cpes, ensure_ascii=False)
    conversation.append({"role": "user", "content": context})
    conversation.append({"role": "user", "content": user_content})
    body = json.dumps({
        "model": os.getenv("MODEL_AI", "gpt-4o-mini"),
        "messages": conversation,
        "response_format": {"type": "json_object"},
        "temperature": 0.1,
    }).encode("utf-8")
    url = os.getenv("URL_AI", "https://api.openai.com/v1/chat/completions").rstrip("/")
    request = Request(
        f"{url}/chat/completions",
        data=body,
        headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=45) as response:
            result = json.loads(response.read())
        raw_reply = result["choices"][0]["message"]["content"]
        decoded = json.loads(raw_reply)
        reply = str(decoded.get("reply", "")).strip()[:4000]
        suggestions: list[dict[str, Any]] = []
        allowed_cpe_ids = {str(item["id"]) for item in cpes}
        for item in decoded.get("suggestions", []):
            suggestion = CpeSuggestion.model_validate(item)
            if suggestion.cpe_id is not None and str(suggestion.cpe_id) not in allowed_cpe_ids:
                continue
            fields = {key: value for key, value in suggestion.fields.items() if key in CPE_FIELDS}
            if fields:
                suggestions.append({
                    "cpe_id": str(suggestion.cpe_id) if suggestion.cpe_id else None,
                    "title": suggestion.title,
                    "fields": fields,
                })
        return reply or "No pude interpretar los datos. ¿Podés darme más contexto?", suggestions
    except (HTTPError, URLError, TimeoutError, KeyError, IndexError, TypeError, ValueError) as exc:
        raise ApiError(
            status_code=502,
            code="assistant_request_failed",
            message="No se pudo procesar el mensaje con el asistente. Revisá la configuración e intentá nuevamente.",
        ) from exc
