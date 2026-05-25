"""
SQLite storage layer — hardened for multi-thread FastAPI usage.

WAL mode + single-connection pool serialises all writes through one
connection, eliminating "database is locked" errors from the background
SimulationService thread competing with FastAPI request handlers.

This is a temporary stabilisation step.  SQLite is not designed for high
write-concurrency; a production deployment under sustained load should
migrate to PostgreSQL.
"""

import logging

from sqlalchemy import JSON, Boolean, Column, Float, Integer, String, create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import QueuePool

logger = logging.getLogger(__name__)

DB_PATH = "./app.db"

# ── Engine configuration ────────────────────────────────────────────
#
# pool_size=1, max_overflow=0
#   QueuePool will hand out at most 1 connection.  Any second thread
#   that needs a connection blocks (up to pool_timeout seconds) until
#   the first one is returned.  This serialises all database access
#   and avoids SQLite's coarse-grained write lock.
#
# timeout=30
#   SQLite-level busy timeout (seconds).  If another *OS process*
#   holds the database lock, the driver retries for up to 30 s before
#   raising "database is locked".  Inside a single-process QueuePool
#   this is a safety net, not the primary mechanism.
#
# check_same_thread=False
#   Required because SimulationService runs in a daemon thread while
#   FastAPI handlers run on the main asyncio thread.  SQLAlchemy's
#   QueuePool already serialises access; the flag just lifts Python's
#   per-thread ownership check on the raw sqlite3 connection.
#
# pool_pre_ping=True
#   Emits a lightweight SELECT 1 before reusing a pooled connection,
#   transparently replacing connections that went stale (e.g. after a
#   disk error or file replacement).

engine = create_engine(
    f"sqlite:///{DB_PATH}",
    connect_args={
        "timeout": 30,
        "check_same_thread": False,
    },
    poolclass=QueuePool,
    pool_size=1,
    max_overflow=0,
    pool_pre_ping=True,
)


# ── PRAGMAs applied on every new connection ─────────────────────────

@event.listens_for(engine, "connect")
def _set_sqlite_pragmas(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("PRAGMA journal_mode=WAL")
        wal_result = cursor.fetchone()
        cursor.execute("PRAGMA synchronous=NORMAL")

        logger.info(
            "SQLite PRAGMAs applied — journal_mode=%s synchronous=NORMAL path=%s",
            wal_result[0] if wal_result else "unknown",
            DB_PATH,
        )
    except Exception:
        logger.exception("Failed to set SQLite PRAGMAs — database may be unstable")
    finally:
        cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# ── ORM models ──────────────────────────────────────────────────────

class MetricORM(Base):
    __tablename__ = "metrics"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(Float, nullable=False, index=True)
    name = Column(String, nullable=False, index=True)
    value = Column(Float, nullable=False)
    labels = Column(JSON, nullable=False, default=dict)


class AnomalyORM(Base):
    __tablename__ = "anomalies"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(Float, nullable=False, index=True)
    metric = Column(String, nullable=False, index=True)
    value = Column(Float, nullable=False)
    is_anomaly = Column(Boolean, nullable=False)
    score = Column(Float, nullable=False)
    baseline = Column(Float, nullable=False)


class EventORM(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(String, nullable=False, unique=True, index=True)
    metric = Column(String, nullable=False, index=True)
    source = Column(String, nullable=False)
    severity = Column(String, nullable=False)
    status = Column(String, nullable=False)
    timestamp = Column(Float, nullable=False, index=True)
