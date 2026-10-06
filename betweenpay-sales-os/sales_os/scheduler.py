from __future__ import annotations

import logging
from apscheduler.schedulers.background import BackgroundScheduler

logger = logging.getLogger(__name__)


class EngineScheduler:
    def __init__(self, store, engine):
        self.store = store
        self.engine = engine
        self.scheduler = BackgroundScheduler(daemon=True)

    def start(self) -> None:
        engine_minutes = max(10, self.store.get_int("engine_interval_minutes", 30))
        publish_minutes = max(5, self.store.get_int("publish_interval_minutes", 10))
        self.scheduler.add_job(
            self._safe_engine, "interval", minutes=engine_minutes,
            id="strategy_engine", max_instances=1, coalesce=True,
            replace_existing=True, next_run_time=None,
        )
        self.scheduler.add_job(
            self._safe_publish, "interval", minutes=publish_minutes,
            id="publisher", max_instances=1, coalesce=True,
            replace_existing=True, next_run_time=None,
        )
        self.scheduler.start()

    def run_startup_cycle(self) -> None:
        if self.store.get_bool("autopilot_enabled"):
            self._safe_engine()
            self._safe_publish()

    def reschedule(self) -> None:
        if not self.scheduler.running:
            return
        self.scheduler.reschedule_job(
            "strategy_engine", trigger="interval",
            minutes=max(10, self.store.get_int("engine_interval_minutes", 30)),
        )
        self.scheduler.reschedule_job(
            "publisher", trigger="interval",
            minutes=max(5, self.store.get_int("publish_interval_minutes", 10)),
        )

    def _safe_engine(self) -> None:
        try:
            self.engine.run_once()
        except Exception:
            logger.exception("Sales engine cycle failed")

    def _safe_publish(self) -> None:
        try:
            self.engine.reconcile_buffer_posts()
            self.engine.publish_due()
        except Exception:
            logger.exception("Publishing cycle failed")

    def stop(self) -> None:
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
