from sales_os.engine import SalesEngine
from sales_os.models import MetricsSnapshot
from sales_os.store import Store


def make_engine(tmp_path):
    store = Store(tmp_path / "test.db")
    return store, SalesEngine(store)


def test_diagnoses_low_traffic(tmp_path):
    store, engine = make_engine(tmp_path)
    constraint, diagnosis, action = engine._diagnose(MetricsSnapshot(sessions_7d=10))
    assert constraint == "traffic"
    assert "traffic" in action.lower()


def test_diagnoses_checkout_conversion(tmp_path):
    store, engine = make_engine(tmp_path)
    metrics = MetricsSnapshot(sessions_7d=100, checkout_starts_7d=20, sales_7d=1)
    constraint, _, _ = engine._diagnose(metrics)
    assert constraint == "checkout_conversion"


def test_target_reached(tmp_path):
    store, engine = make_engine(tmp_path)
    metrics = MetricsSnapshot(sessions_7d=1000, checkout_starts_7d=200, sales_7d=100)
    constraint, _, _ = engine._diagnose(metrics)
    assert constraint == "target_reached"
