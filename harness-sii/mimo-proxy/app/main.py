"""FastAPI entrypoint for the mimo-proxy."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from .config import settings
from .routes import router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("mimo-proxy")


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: D401, ARG001
    logger.info(
        "mimo-proxy listening on %s:%d (auth=%s, mimo_url=%s)",
        settings.host,
        settings.port,
        "on" if settings.api_token else "off",
        settings.mimo_base_url,
    )
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="mimo-proxy",
        version="0.1.0",
        description=(
            "HTTP proxy that lets an air-gapped GPU host access mimo API via "
            "an internet-connected CPU host. Designed to be reached over an "
            "SSH (or VS Code) port-forward."
        ),
        lifespan=lifespan,
    )
    app.include_router(router)
    return app


app = create_app()
