"""Local MCP bridge for BetweenPay Sales OS.

This exposes a controlled tool surface to an MCP-capable client. It uses the same
local SQLite store and Windows Credential Manager as the desktop app. It does not
expose credentials through tools.
"""
from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from .engine import SalesEngine
from .store import Store

mcp = FastMCP("BetweenPay Sales OS")
store = Store()
engine = SalesEngine(store)


@mcp.tool()
def get_sales_status() -> dict:
    snap = store.latest_snapshot()
    target = store.get_int("weekly_sales_target", 100)
    sales = int(snap["sales_7d"]) if snap else 0
    return {
        "weekly_target": target,
        "sales_7d": sales,
        "gap": max(0, target - sales),
        "autopilot_enabled": store.get_bool("autopilot_enabled"),
        "latest_snapshot": dict(snap) if snap else None,
    }


@mcp.tool()
def run_sales_engine_now() -> dict:
    result = engine.run_once()
    return {
        "diagnosis": result.diagnosis,
        "constraint": result.primary_constraint,
        "recommended_action": result.recommended_action,
        "sales_7d": result.sales_7d,
        "target": result.target,
        "gap": result.gap,
        "planned_actions": result.planned_actions,
    }


@mcp.tool()
def recent_actions(limit: int = 25) -> list[dict]:
    limit = max(1, min(limit, 100))
    return [dict(r) for r in store.recent_actions(limit)]


@mcp.tool()
def active_experiments(limit: int = 50) -> list[dict]:
    limit = max(1, min(limit, 100))
    return [dict(r) for r in store.experiments(limit=limit)]


@mcp.tool()
def social_content_queue(limit: int = 50) -> list[dict]:
    limit = max(1, min(limit, 100))
    rows = []
    for row in store.content_queue(limit):
        item = dict(row)
        item.pop("performance", None)
        rows.append(item)
    return rows


@mcp.tool()
def set_autopilot(enabled: bool) -> dict:
    store.set("autopilot_enabled", "1" if enabled else "0")
    return {"autopilot_enabled": enabled}


@mcp.tool()
def set_weekly_sales_target(target: int) -> dict:
    target = max(1, min(int(target), 100000))
    store.set("weekly_sales_target", target)
    return {"weekly_sales_target": target}


if __name__ == "__main__":
    mcp.run()
