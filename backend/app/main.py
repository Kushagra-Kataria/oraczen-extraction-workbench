"""Application factory: startup owns resources, shutdown cleans background tasks."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import Settings
from .jobs import JobManager
from .providers.base import ExtractionProvider
from .providers.mock import MockProvider
from .routes import router
from .store import Store
from .tickets import load_tickets


def create_app(settings: Settings | None = None, provider: ExtractionProvider | None = None):
    configuration = settings or Settings()

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        service = JobManager(
            Store(load_tickets(configuration.dataset_path())),
            provider or MockProvider(configuration.mock_delay_ms),
            configuration,
        )
        application.state.manager = service
        yield
        await service.close()

    application = FastAPI(title="Extraction Workbench", version="0.1.0", lifespan=lifespan)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_methods=["GET", "POST", "PATCH"],
        allow_headers=["Content-Type"],
    )
    application.include_router(router)
    return application


app = create_app()
