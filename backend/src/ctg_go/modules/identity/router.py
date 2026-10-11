from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ctg_go.api.dependencies import get_db, get_token_service
from ctg_go.modules.identity.schemas import LoginRequest, LoginResponse
from ctg_go.modules.identity.services import TokenService
from ctg_go.modules.identity.use_cases import LoginUseCase

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(
    payload: LoginRequest,
    db: Session = Depends(get_db),
    token_service: TokenService = Depends(get_token_service),
) -> LoginResponse:
    return LoginUseCase(db, token_service).execute(payload)
