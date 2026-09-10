from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ctg_go.api.errors import ApiError
from ctg_go.modules.identity.models import User
from ctg_go.modules.identity.schemas import LoginRequest, LoginResponse
from ctg_go.modules.identity.services import TokenService, verify_password


class LoginUseCase:
    def __init__(self, db: Session, token_service: TokenService) -> None:
        self.db = db
        self.token_service = token_service

    def execute(self, payload: LoginRequest) -> LoginResponse:
        user = self.db.scalar(select(User).where(User.email == payload.email))
        if user is None or not user.is_active or not verify_password(payload.password, user.password_hash):
            raise ApiError(status_code=401, code="unauthorized", message="Invalid credentials.")

        access_token = self.token_service.encode(
            {
                "sub": str(user.id),
                "org": str(user.organization_id),
                "role": user.role,
            }
        )
        return LoginResponse(
            access_token=access_token,
            user_id=str(user.id),
            organization_id=str(user.organization_id),
            role=user.role,
        )
