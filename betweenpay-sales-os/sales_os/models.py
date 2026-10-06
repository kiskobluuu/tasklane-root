from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class MetricsSnapshot:
    sales_7d: int = 0
    revenue_7d: float = 0.0
    sessions_7d: int = 0
    landing_views_7d: int = 0
    contest_views_7d: int = 0
    checkout_views_7d: int = 0
    checkout_starts_7d: int = 0
    leads_7d: int = 0
    participant_joins_7d: int = 0
    qualified_referrals_7d: int = 0
    sales_24h: int = 0
    revenue_24h: float = 0.0
    sessions_24h: int = 0
    checkout_starts_24h: int = 0
    source_performance: list[dict[str, Any]] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def checkout_start_rate(self) -> float:
        return self.checkout_starts_7d / self.sessions_7d if self.sessions_7d else 0.0

    @property
    def purchase_rate(self) -> float:
        return self.sales_7d / self.sessions_7d if self.sessions_7d else 0.0

    @property
    def checkout_to_purchase_rate(self) -> float:
        return self.sales_7d / self.checkout_starts_7d if self.checkout_starts_7d else 0.0


@dataclass
class EngineDecision:
    diagnosis: str
    primary_constraint: str
    recommended_action: str
    urgency: str
    target: int
    sales_7d: int
    gap: int
    pace_per_day: float
    required_per_day: float
    planned_actions: list[dict[str, Any]] = field(default_factory=list)
