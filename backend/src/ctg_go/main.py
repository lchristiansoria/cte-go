from __future__ import annotations

from fastapi import FastAPI
from sqlalchemy.engine import Engine

from ctg_go.api.errors import install_error_handlers
from ctg_go.db.models import import_models
from ctg_go.db.session import create_engine_from_env, get_session_factory
from ctg_go.modules.clients.router import router as clients_router
from ctg_go.modules.cpe.router import router as cpe_router
from ctg_go.modules.gestions.router import router as gestions_router
from ctg_go.modules.identity.router import router as identity_router
from ctg_go.modules.identity.services import TokenService


def create_app(*, engine: Engine | None = None, token_secret: str = "dev-secret") -> FastAPI:
    import_models()
    app = FastAPI(title="CTG GO API", version="0.1.0")
    app.state.engine = engine or create_engine_from_env()
    app.state.session_factory = get_session_factory(app.state.engine)
    app.state.token_service = TokenService(secret=token_secret)

    install_error_handlers(app)

    app.include_router(identity_router)
    app.include_router(clients_router)
    app.include_router(gestions_router)
    app.include_router(cpe_router)

    @app.get("/health", tags=["health"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
