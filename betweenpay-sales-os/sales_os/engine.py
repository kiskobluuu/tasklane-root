from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from .connectors import BetweenPayMetrics, BufferPublisher, AIPlanner

@dataclass
class EngineResult:
    sales_7d: int
    target: int
    gap: int
    pace_per_day: float
    required_per_day: float
    diagnosis: str
    action: str

class SalesEngine:
    def __init__(self, store):
        self.store = store
        self.last_run: EngineResult | None = None

    def run_once(self) -> EngineResult:
        target = int(self.store.get("weekly_sales_target", "100"))
        metrics = BetweenPayMetrics(self.store.get("supabase_metrics_url", "")).fetch()
        sales = int(metrics.get("sales_7d", 0) or 0)
        revenue = float(metrics.get("revenue_7d", 0) or 0)
        sessions = int(metrics.get("sessions_7d", 0) or 0)
        checkouts = int(metrics.get("checkout_starts_7d", 0) or 0)

        gap = max(0, target - sales)
        pace = sales / 7.0
        required = gap / 7.0 if gap else 0.0

        if not metrics.get("configured"):
            diagnosis = "Metrics connector is not configured yet."
            action = "Configure the BetweenPay metrics endpoint in Settings."
        elif sessions < 20:
            diagnosis = "Primary constraint is traffic volume; there is not enough sample to judge conversion reliably."
            action = "Increase diverse organic acquisition tests while preserving UTM attribution."
        elif checkouts == 0:
            diagnosis = "Traffic is arriving without checkout starts."
            action = "Test stronger product/problem CTAs and lower-friction calculator-to-checkout bridges."
        elif sales == 0:
            diagnosis = "Checkout interest exists but completed purchases are not following."
            action = "Inspect checkout friction and strengthen recovery/credibility messaging."
        elif sales < target:
            diagnosis = f"Sales are below the {target}/7d target with a remaining gap of {gap}."
            action = "Exploit the best converting source while reserving 30% of activity for new experiments."
        else:
            diagnosis = "Weekly target reached."
            action = "Protect winning channels, expand cautiously, and keep testing for higher sustainable volume."

        self.store.save_snapshot(sales, revenue, sessions, checkouts, metrics)
        self.store.log_action("engine_decision", diagnosis, payload={
            "recommended_action": action,
            "sales_7d": sales,
            "target": target,
            "gap": gap,
            "sessions_7d": sessions,
            "checkout_starts_7d": checkouts,
        }, status="executed")

        self.last_run = EngineResult(sales, target, gap, pace, required, diagnosis, action)
        return self.last_run
