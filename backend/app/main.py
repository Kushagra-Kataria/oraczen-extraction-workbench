"""Application factory: startup owns resources, shutdown cleans background tasks."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import Settings
from .jobs import JobManager
from .providers.base import ExtractionProvider
from .providers.gemini import GeminiProvider
from .providers.mock import MockProvider
from .routes import router
from .store import Store
from .tickets import load_tickets


def create_app(settings: Settings | None = None, provider: ExtractionProvider | None = None):
    configuration = settings or Settings()

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        selected = provider or (
            MockProvider(configuration.mock_delay_ms)
            if configuration.extraction_provider == "mock"
            else GeminiProvider(configuration)
        )
        service = JobManager(
            Store(load_tickets(configuration.dataset_path())),
            selected,
            configuration,
        )
        application.state.manager = service
        try:
            yield
        finally:
            await service.close()
            if isinstance(selected, GeminiProvider):
                await selected.close()

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
