from __future__ import annotations
import httpx
from .vault import get_secret

class ConnectorError(RuntimeError):
    pass

class BetweenPayMetrics:
    def __init__(self, endpoint: str):
        self.endpoint = endpoint.strip()

    def fetch(self) -> dict:
        if not self.endpoint:
            return {"configured": False, "sales_7d": 0, "revenue_7d": 0, "sessions_7d": 0, "checkout_starts_7d": 0}
        token = get_secret("betweenpay_api_token")
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        r = httpx.get(self.endpoint, headers=headers, timeout=20)
        r.raise_for_status()
        data = r.json()
        data["configured"] = True
        return data

class BufferPublisher:
    def __init__(self, api_url: str = "https://api.buffer.com"):
        self.api_url = api_url.rstrip("/")

    def configured(self) -> bool:
        return bool(get_secret("buffer_api_token"))

    def graphql(self, query: str, variables: dict | None = None) -> dict:
        token = get_secret("buffer_api_token")
        if not token:
            raise ConnectorError("Buffer API token is not configured.")
        r = httpx.post(
            self.api_url,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={"query": query, "variables": variables or {}},
            timeout=30,
        )
        r.raise_for_status()
        body = r.json()
        if body.get("errors"):
            raise ConnectorError(str(body["errors"]))
        return body.get("data") or {}

class AIPlanner:
    def configured(self) -> bool:
        return bool(get_secret("openai_api_key"))

    def status(self) -> str:
        return "configured" if self.configured() else "optional API key not configured"
