from __future__ import annotations

from collections.abc import Generator
import uuid

from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from ctg_go.api.errors import ApiError
from ctg_go.modules.identity.models import User
from ctg_go.modules.identity.services import TokenService


def get_db(request: Request) -> Generator[Session, None, None]:
    session_factory = request.app.state.session_factory
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


def get_token_service(request: Request) -> TokenService:
    return request.app.state.token_service


def get_current_actor(
    request: Request,
    db: Session = Depends(get_db),
    token_service: TokenService = Depends(get_token_service),
) -> User:
    auth = request.headers.get("authorization", "")
    if not auth.startswith("Bearer "):
        raise ApiError(status_code=401, code="unauthorized", message="Missing bearer token.")

    token = auth.removeprefix("Bearer ").strip()
    payload = token_service.decode(token)
    user_id = payload.get("sub")
    if not user_id:
        raise ApiError(status_code=401, code="unauthorized", message="Invalid token subject.")
    try:
        user_uuid = uuid.UUID(str(user_id))
    except ValueError as exc:
        raise ApiError(status_code=401, code="unauthorized", message="Invalid token subject.") from exc

    actor = db.scalar(select(User).where(User.id == user_uuid))
    if actor is None or not actor.is_active:
        raise ApiError(status_code=401, code="unauthorized", message="Invalid or inactive session.")
    return actor
