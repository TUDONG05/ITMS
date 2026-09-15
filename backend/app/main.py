from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.settings import API_PREFIX, get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="ITMS Backend", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_credentials=False,
        allow_methods=["GET"],
        allow_headers=["*"],
    )
    app.include_router(api_router, prefix=API_PREFIX)
    return app


app = create_app()
