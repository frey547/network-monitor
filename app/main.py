import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.ai.analyzer import AIAnalyzer
from app.api.routes import router
from app.api.webhook import router as webhook_router
from app.core.metrics import REQUEST_COUNT
from app.detectors.zscore import AnomalyDetector
from app.engine.enricher import AlertEnricher
from app.engine.rule_engine import RuleEngine
from app.knowledge.history import AlertHistory
from app.notify.feishu import FeishuNotifier
from app.services.alerting import AlertManager
from app.services.simulation import SimulationService
from app.storage.database import Base, engine
from app.storage.repository import SQLiteRepository

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)

    repository = SQLiteRepository()
    detector = AnomalyDetector()
    alert_manager = AlertManager(limit_per_minute=2, window_seconds=5)
    simulation_service = SimulationService(repository, detector, alert_manager)

    app.state.repository = repository
    app.state.detector = detector
    app.state.alert_manager = alert_manager
    app.state.simulation_service = simulation_service

    alert_history = AlertHistory()
    app.state.rule_engine = RuleEngine()
    app.state.ai_analyzer = AIAnalyzer()
    app.state.enricher = AlertEnricher(alert_history)
    app.state.feishu = FeishuNotifier()
    logger = logging.getLogger(__name__)
    logger.info("AIOps Monitor starting — components initialised")

    simulation_service.start()
    try:
        yield
    finally:
        simulation_service.stop()


def create_app() -> FastAPI:
    app = FastAPI(title="AIOps Monitor", lifespan=lifespan)

    @app.middleware("http")
    async def count_requests(request, call_next):
        REQUEST_COUNT.inc()
        response = await call_next(request)
        return response

    app.include_router(router)
    app.include_router(webhook_router)
    return app


app = create_app()
