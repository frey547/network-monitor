from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import router
from app.core.metrics import REQUEST_COUNT
from app.detectors.zscore import AnomalyDetector
from app.services.alerting import AlertManager
from app.services.simulation import SimulationService
from app.storage.database import Base, engine
from app.storage.repository import SQLiteRepository

Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    repository = SQLiteRepository()
    detector = AnomalyDetector()
    alert_manager = AlertManager(limit_per_minute=2, window_seconds=5)
    simulation_service = SimulationService(repository, detector, alert_manager)
    app.state.repository = repository
    app.state.detector = detector
    app.state.alert_manager = alert_manager
    app.state.simulation_service = simulation_service
    simulation_service.start()
    try:
        yield
    finally:
        simulation_service.stop()


def create_app() -> FastAPI:
    app = FastAPI(lifespan=lifespan)

    @app.middleware("http")
    async def count_requests(request, call_next):
        REQUEST_COUNT.inc()
        response = await call_next(request)
        return response

    app.include_router(router)
    return app


app = create_app()
