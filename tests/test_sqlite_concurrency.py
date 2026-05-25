"""
Concurrency stress test for the hardened SQLite layer.

Spawns multiple threads doing concurrent writes and reads against the
real SQLite engine to verify that WAL mode + QueuePool(pool_size=1)
eliminates "database is locked" errors under contention.
"""

import threading
import time
import uuid

import pytest

from app.storage.database import Base, SessionLocal, engine, MetricORM, AnomalyORM, EventORM

WRITERS = 8
WRITES_PER_THREAD = 50


@pytest.fixture(autouse=True)
def _fresh_db():
    Base.metadata.create_all(bind=engine)
    yield
    with SessionLocal() as session:
        session.query(MetricORM).delete()
        session.query(AnomalyORM).delete()
        session.query(EventORM).delete()
        session.commit()


def _writer(thread_id: int, results: dict):
    ok = 0
    fail = 0
    t0 = time.monotonic()
    for i in range(WRITES_PER_THREAD):
        try:
            with SessionLocal() as session:
                session.add(MetricORM(
                    timestamp=time.time(),
                    name=f"stress_{thread_id}",
                    value=float(i),
                    labels={},
                ))
                session.commit()
            ok += 1
        except Exception as exc:
            fail += 1
            print(f"  thread-{thread_id} write {i} failed: {exc}")
    elapsed = time.monotonic() - t0
    results[thread_id] = {"ok": ok, "fail": fail, "elapsed_s": round(elapsed, 3)}


def test_concurrent_writes():
    results: dict = {}
    threads = [
        threading.Thread(target=_writer, args=(i, results))
        for i in range(WRITERS)
    ]

    t0 = time.monotonic()
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=120)
    wall = time.monotonic() - t0

    total_ok = sum(r["ok"] for r in results.values())
    total_fail = sum(r["fail"] for r in results.values())
    expected = WRITERS * WRITES_PER_THREAD

    print(f"\n{'='*50}")
    print(f"Concurrency stress test results:")
    print(f"  threads={WRITERS}  writes_per_thread={WRITES_PER_THREAD}")
    print(f"  total_ok={total_ok}  total_fail={total_fail}  wall_time={wall:.2f}s")
    for tid, r in sorted(results.items()):
        print(f"  thread-{tid}: ok={r['ok']} fail={r['fail']} elapsed={r['elapsed_s']}s")
    print(f"{'='*50}")

    assert total_fail == 0, f"{total_fail}/{expected} writes failed"
    assert total_ok == expected

    with SessionLocal() as session:
        count = session.query(MetricORM).filter(
            MetricORM.name.like("stress_%")
        ).count()
    assert count == expected, f"expected {expected} rows, got {count}"


def test_concurrent_mixed_read_write():
    """Writers and readers running simultaneously."""
    errors: list = []

    def writer():
        for i in range(30):
            try:
                with SessionLocal() as session:
                    session.add(EventORM(
                        event_id=str(uuid.uuid4()),
                        metric="mixed_test",
                        source="stress",
                        severity="info",
                        status="open",
                        timestamp=time.time(),
                    ))
                    session.commit()
            except Exception as exc:
                errors.append(f"write: {exc}")

    def reader():
        for _ in range(30):
            try:
                with SessionLocal() as session:
                    session.query(EventORM).filter(
                        EventORM.metric == "mixed_test"
                    ).all()
            except Exception as exc:
                errors.append(f"read: {exc}")

    threads = (
        [threading.Thread(target=writer) for _ in range(4)]
        + [threading.Thread(target=reader) for _ in range(4)]
    )

    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=120)

    assert len(errors) == 0, f"{len(errors)} errors: {errors[:5]}"
