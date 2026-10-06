from sales_os.scheduler import EngineScheduler
from sales_os.store import Store


class StubEngine:
    def run_once(self):
        return None
    def reconcile_buffer_posts(self):
        return 0
    def publish_due(self):
        return {}
    def process_remote_commands(self):
        return {}


def test_scheduler_jobs_are_not_paused(tmp_path):
    store = Store(tmp_path / "test.db")
    scheduler = EngineScheduler(store, StubEngine())
    scheduler.start()
    try:
        for job_id in ("strategy_engine", "publisher", "command_bridge"):
            job = scheduler.scheduler.get_job(job_id)
            assert job is not None
            assert job.next_run_time is not None
    finally:
        scheduler.stop()
