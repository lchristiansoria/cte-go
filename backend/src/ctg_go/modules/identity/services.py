from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Any

from ctg_go.api.errors import ApiError
from ctg_go.modules.identity.models import User


class TokenService:
    def __init__(self, *, secret: str, expires_seconds: int = 3600) -> None:
        self.secret = secret.encode("utf-8")
        self.expires_seconds = expires_seconds

    def encode(self, payload: dict[str, Any]) -> str:
        body = payload.copy()
        body["exp"] = int(time.time()) + self.expires_seconds
        raw = json.dumps(body, separators=(",", ":"), sort_keys=True).encode("utf-8")
        signature = hmac.new(self.secret, raw, hashlib.sha256).digest()
        return f"{_b64(raw)}.{_b64(signature)}"

    def decode(self, token: str) -> dict[str, Any]:
        try:
            body_part, sig_part = token.split(".", 1)
            raw = _b64d(body_part)
            signature = _b64d(sig_part)
        except Exception as exc:  # noqa: BLE001
            raise ApiError(status_code=401, code="unauthorized", message="Invalid token.") from exc

        expected = hmac.new(self.secret, raw, hashlib.sha256).digest()
        if not hmac.compare_digest(signature, expected):
            raise ApiError(status_code=401, code="unauthorized", message="Invalid token signature.")

        payload = json.loads(raw.decode("utf-8"))
        if int(payload.get("exp", 0)) < int(time.time()):
            raise ApiError(status_code=401, code="unauthorized", message="Token expired.")
        return payload


def verify_password(plain_password: str, password_hash: str) -> bool:
    if password_hash.startswith("pbkdf2_sha256$"):
        try:
            _, iterations, salt, expected = password_hash.split("$", 3)
            derived = hashlib.pbkdf2_hmac(
                "sha256",
                plain_password.encode("utf-8"),
                salt.encode("utf-8"),
                int(iterations),
            ).hex()
        except (TypeError, ValueError):
            return False
        return hmac.compare_digest(expected, derived)
    return hmac.compare_digest(plain_password, password_hash)


def assert_operator_or_admin(actor: User) -> None:
    if actor.role not in {"operator", "admin"}:
        raise ApiError(status_code=403, code="forbidden", message="Insufficient permissions.")


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("utf-8").rstrip("=")


def _b64d(raw: str) -> bytes:
    return base64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4))
