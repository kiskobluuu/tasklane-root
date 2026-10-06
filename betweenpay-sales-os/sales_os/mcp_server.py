"""Optional MCP bridge for ChatGPT/custom integration.

The desktop app does not need this module to run. This bridge exposes a small
control surface over Sales OS state. For ChatGPT web use, host this bridge on a
secured reachable server rather than exposing a Windows PC directly.
"""
from mcp.server.fastmcp import FastMCP
from .store import Store

mcp = FastMCP("BetweenPay Sales OS")
store = Store()

@mcp.tool()
def get_sales_os_status() -> dict:
    target = int(store.get("weekly_sales_target", "100"))
    snap = store.latest_snapshot()
    sales = int(snap["sales_7d"]) if snap else 0
    return {
        "weekly_target": target,
        "sales_7d": sales,
        "gap": max(0, target - sales),
        "autopilot_enabled": store.get("autopilot_enabled","0") == "1",
    }

@mcp.tool()
def recent_sales_os_actions(limit: int = 20) -> list[dict]:
    limit = max(1, min(limit, 100))
    return [dict(r) for r in store.recent_actions(limit)]

if __name__ == "__main__":
    mcp.run()
