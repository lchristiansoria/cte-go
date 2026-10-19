"""Complete blank fields in the seeded ARCA example CPE through the local API."""

from __future__ import annotations

import argparse
import getpass
import json
import os
import sys
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from ctg_go.seed.synthetic import ARCA_EXAMPLE_CPE_DATA

CLIENT_CUIT = "20131082283"


def api_request(
    base_url: str,
    method: str,
    path: str,
    *,
    token: str | None = None,
    body: dict[str, Any] | None = None,
) -> Any:
    headers = {"Accept": "application/json"}
    data = None
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(f"{base_url.rstrip('/')}{path}", data=data, headers=headers, method=method)
    try:
        with urlopen(request, timeout=20) as response:
            content = response.read()
        return json.loads(content) if content else None
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"La API respondió HTTP {exc.code}: {detail}") from exc
    except URLError as exc:
        raise RuntimeError(f"No se pudo conectar con la API: {exc.reason}") from exc


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=os.getenv("CTG_GO_API_URL", "http://localhost:8000"))
    parser.add_argument("--email", default=os.getenv("CTG_GO_API_EMAIL", "operator1@ctg-go.local"))
    parser.add_argument("--cpe-id", help="ID del borrador a completar si hay más de uno para el cliente")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="guardar los campos vacíos; sin esta opción solo muestra una vista previa",
    )
    args = parser.parse_args()
    password = os.getenv("CTG_GO_API_PASSWORD") or getpass.getpass("Contraseña del operador responsable: ")
    if not password:
        parser.error("La contraseña no puede estar vacía.")

    try:
        login = api_request(
            args.base_url,
            "POST",
            "/api/v1/auth/login",
            body={"email": args.email, "password": password},
        )
        token = login["access_token"]
        actor_id = login["user_id"]
        organization_id = login["organization_id"]

        clients = api_request(args.base_url, "GET", "/api/v1/clients", token=token)
        client = next((item for item in clients if item["cuit"] == CLIENT_CUIT), None)
        if client is None:
            raise RuntimeError(f"No encontré el cliente con CUIT {CLIENT_CUIT}.")

        gestions = api_request(args.base_url, "GET", "/api/v1/gestions", token=token)
        client_gestion_ids = {
            item["id"] for item in gestions if item["client_id"] == client["id"]
        }

        cpes = api_request(
            args.base_url,
            "GET",
            f"/api/v1/organizations/{organization_id}/cpes",
            token=token,
        )
        client_cpes = [item for item in cpes if item["gestion_id"] in client_gestion_ids]
        if args.cpe_id:
            cpe = next((item for item in client_cpes if item["id"] == args.cpe_id), None)
            if cpe is None:
                raise RuntimeError("El ID indicado no corresponde a una CPE de ese cliente.")
        else:
            incomplete_drafts = [
                item for item in client_cpes
                if item["status"] == "draft"
                and any(
                    not str(((item.get("payload_json") or {}).get("cpe") or {}).get(key, "")).strip()
                    for key in ARCA_EXAMPLE_CPE_DATA
                )
            ]
            if len(incomplete_drafts) != 1:
                if not incomplete_drafts:
                    print(
                        "No encontré un borrador vacío guardado para ese CUIT. "
                        "El ejemplo del PDF ya está completo; guardá el nuevo borrador "
                        "en la app y volvé a ejecutar el script."
                    )
                    return 0
                print("Hay varios borradores incompletos. Indicá el destino con --cpe-id:")
                for item in incomplete_drafts:
                    print(f"{item['id']}  {item['title']}")
                return 2
            cpe = incomplete_drafts[0]

        if cpe["status"] != "draft":
            raise RuntimeError("Solo se pueden completar borradores con estado draft.")
        if cpe["responsible_user_id"] != actor_id:
            raise RuntimeError(
                f"La CPE «{cpe['title']}» está asignada a otro operador "
                f"(responsable {cpe['responsible_user_id']}). Iniciá sesión como responsable; "
                "el script no reasigna ni evita permisos."
            )

        payload = dict(cpe.get("payload_json") or {})
        fields = dict(payload.get("cpe") or {})
        additions = {
            key: value
            for key, value in ARCA_EXAMPLE_CPE_DATA.items()
            if fields.get(key) is None or not str(fields[key]).strip()
        }
        merged_payload = {**payload, "cpe": {**fields, **additions}}

        print(f"Cliente: {client['business_name']} ({CLIENT_CUIT})")
        print(f"CPE: {cpe['title']} ({cpe['id']})")
        print(f"Campos vacíos que se completarían: {len(additions)}")
        print(json.dumps(additions, ensure_ascii=False, indent=2))
        if not additions:
            print("No hay campos vacíos para completar.")
            return 0
        if not args.apply:
            print("Vista previa únicamente. Repetí el comando con --apply para guardar.")
            return 0

        api_request(
            args.base_url,
            "PATCH",
            f"/api/v1/cpes/{cpe['id']}",
            token=token,
            body={"expected_version": cpe["version"], "payload_json": merged_payload},
        )
        print("CPE actualizada. Los valores existentes y los estados de revisión se conservaron.")
        return 0
    except (KeyError, TypeError, RuntimeError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())