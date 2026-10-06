from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from .config import COMPLETED_ORDER_STATUSES
from .models import MetricsSnapshot
from .vault import get_secret


class ConnectorError(RuntimeError):
    pass


class SupabaseConnector:
    """Direct PostgREST connector using the user's Supabase service-role key."""

    def __init__(self, store):
        self.store = store

    @property
    def base_url(self) -> str:
        return self.store.get("supabase_url", "").rstrip("/")

    @property
    def key(self) -> str | None:
        return get_secret("supabase_service_role_key")

    def configured(self) -> bool:
        return bool(self.base_url and self.key)

    def _headers(self, prefer: str | None = None) -> dict[str, str]:
        if not self.key:
            raise ConnectorError("Supabase service-role key is not configured.")
        h = {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
        }
        if prefer:
            h["Prefer"] = prefer
        return h

    def _url(self, table: str) -> str:
        if not self.base_url:
            raise ConnectorError("Supabase URL is not configured.")
        return f"{self.base_url}/rest/v1/{table}"

    def get(self, table: str, params: dict[str, Any], timeout: int = 30) -> list[dict]:
        r = httpx.get(self._url(table), headers=self._headers(), params=params, timeout=timeout)
        if r.status_code >= 400:
            raise ConnectorError(f"Supabase {table} read failed: {r.status_code} {r.text[:500]}")
        return r.json() or []

    def patch(self, table: str, filters: dict[str, str], body: dict[str, Any]) -> list[dict]:
        r = httpx.patch(
            self._url(table),
            headers=self._headers("return=representation"),
            params=filters,
            json=body,
            timeout=30,
        )
        if r.status_code >= 400:
            raise ConnectorError(f"Supabase {table} update failed: {r.status_code} {r.text[:500]}")
        return r.json() or []

    def insert(self, table: str, body: dict[str, Any]) -> list[dict]:
        r = httpx.post(
            self._url(table),
            headers=self._headers("return=representation"),
            json=body,
            timeout=30,
        )
        if r.status_code >= 400:
            raise ConnectorError(f"Supabase {table} insert failed: {r.status_code} {r.text[:500]}")
        return r.json() or []

    def test_connection(self) -> dict[str, Any]:
        if not self.configured():
            return {"ok": False, "message": "Supabase URL/service-role key missing."}
        try:
            rows = self.get("betweenpay_funnel_events", {"select": "id", "limit": "1"})
            return {"ok": True, "message": "Connected to BetweenPay Supabase.", "sample_rows": len(rows)}
        except Exception as exc:
            return {"ok": False, "message": str(exc)}

    def _events(self, since: datetime) -> list[dict]:
        return self.get(
            "betweenpay_funnel_events",
            {
                "select": "created_at,event_name,session_id,source,medium,campaign,content,path,metadata",
                "created_at": f"gte.{since.isoformat()}",
                "order": "created_at.desc",
                "limit": "10000",
            },
        )

    def _orders(self, since: datetime) -> list[dict]:
        return self.get(
            "betweenpay_purchase_orders",
            {
                "select": "completed_at,status,amount,source,medium,campaign,content,session_id",
                "completed_at": f"gte.{since.isoformat()}",
                "order": "completed_at.desc",
                "limit": "10000",
            },
        )

    def _count_rows(self, table: str, time_field: str, since: datetime, extra: dict[str, str] | None = None) -> int:
        params = {"select": "id", time_field: f"gte.{since.isoformat()}", "limit": "10000"}
        params.update(extra or {})
        return len(self.get(table, params))

    @staticmethod
    def _normalize_dim(value: Any, fallback: str) -> str:
        value = str(value or "").strip()
        return value or fallback

    @staticmethod
    def _dt(value: Any) -> datetime | None:
        if not value:
            return None
        try:
            return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except Exception:
            return None

    def collect_metrics(self) -> MetricsSnapshot:
        if not self.configured():
            raise ConnectorError("Supabase connection is not configured.")
        now = datetime.now(timezone.utc)
        since7 = now - timedelta(days=7)
        since24 = now - timedelta(hours=24)
        events7 = self._events(since7)
        orders7 = self._orders(since7)

        completed7 = [o for o in orders7 if str(o.get("status")) in COMPLETED_ORDER_STATUSES]
        completed24 = [o for o in completed7 if (self._dt(o.get("completed_at")) or datetime.min.replace(tzinfo=timezone.utc)) >= since24]

        sessions7 = {e.get("session_id") for e in events7 if e.get("session_id")}
        events24 = [e for e in events7 if (self._dt(e.get("created_at")) or datetime.min.replace(tzinfo=timezone.utc)) >= since24]
        sessions24 = {e.get("session_id") for e in events24 if e.get("session_id")}

        def event_count(rows: list[dict], name: str) -> int:
            return sum(1 for e in rows if e.get("event_name") == name)

        perf: dict[tuple[str, str, str, str], dict[str, Any]] = {}
        for e in events7:
            key = (
                self._normalize_dim(e.get("source"), "direct"),
                self._normalize_dim(e.get("medium"), "none"),
                self._normalize_dim(e.get("campaign"), "none"),
                self._normalize_dim(e.get("content"), "none"),
            )
            x = perf.setdefault(key, {
                "source": key[0], "medium": key[1], "campaign": key[2], "content": key[3],
                "sessions_set": set(), "checkout_starts": 0, "purchases": 0, "revenue": 0.0,
            })
            if e.get("session_id"):
                x["sessions_set"].add(e["session_id"])
            if e.get("event_name") == "checkout_start":
                x["checkout_starts"] += 1

        for o in completed7:
            key = (
                self._normalize_dim(o.get("source"), "direct"),
                self._normalize_dim(o.get("medium"), "none"),
                self._normalize_dim(o.get("campaign"), "none"),
                self._normalize_dim(o.get("content"), "none"),
            )
            x = perf.setdefault(key, {
                "source": key[0], "medium": key[1], "campaign": key[2], "content": key[3],
                "sessions_set": set(), "checkout_starts": 0, "purchases": 0, "revenue": 0.0,
            })
            x["purchases"] += 1
            x["revenue"] += float(o.get("amount") or 0)

        source_performance: list[dict[str, Any]] = []
        for x in perf.values():
            sessions = len(x.pop("sessions_set"))
            x["sessions"] = sessions
            x["purchase_rate"] = (x["purchases"] / sessions) if sessions else 0.0
            x["checkout_rate"] = (x["checkout_starts"] / sessions) if sessions else 0.0
            source_performance.append(x)
        source_performance.sort(key=lambda x: (x["purchases"], x["revenue"], x["sessions"]), reverse=True)

        leads7 = self._count_rows("betweenpay_marketing_leads", "created_at", since7)
        joins7 = self._count_rows(
            "betweenpay_referral_participants", "joined_at", since7, {"is_demo": "eq.false"}
        )
        qualified7 = self._count_rows(
            "betweenpay_referrals", "qualified_at", since7, {"status": "eq.qualified"}
        )

        raw = {"captured_at": now.isoformat(), "source_performance": source_performance[:100]}
        return MetricsSnapshot(
            sales_7d=len(completed7),
            revenue_7d=sum(float(o.get("amount") or 0) for o in completed7),
            sessions_7d=len(sessions7),
            landing_views_7d=event_count(events7, "landing_view"),
            contest_views_7d=event_count(events7, "contest_view"),
            checkout_views_7d=event_count(events7, "checkout_view"),
            checkout_starts_7d=event_count(events7, "checkout_start"),
            leads_7d=leads7,
            participant_joins_7d=joins7,
            qualified_referrals_7d=qualified7,
            sales_24h=len(completed24),
            revenue_24h=sum(float(o.get("amount") or 0) for o in completed24),
            sessions_24h=len(sessions24),
            checkout_starts_24h=event_count(events24, "checkout_start"),
            source_performance=source_performance,
            raw=raw,
        )

    def fetch_remote_social_queue(self, limit: int = 100) -> list[dict]:
        return self.get(
            "betweenpay_social_queue",
            {
                "select": "*",
                "status": "in.(ready,scheduled)",
                "order": "priority.desc,id.asc",
                "limit": str(limit),
            },
        )

    def update_remote_social_queue(self, remote_id: int, body: dict[str, Any]) -> None:
        self.patch("betweenpay_social_queue", {"id": f"eq.{remote_id}"}, body)

    def log_remote_growth_action(self, action: dict[str, Any]) -> None:
        if not self.configured():
            return
        try:
            self.insert("betweenpay_growth_actions", action)
        except Exception:
            pass


class BufferPublisher:
    def __init__(self, store):
        self.store = store

    @property
    def api_url(self) -> str:
        return self.store.get("buffer_api_url", "https://api.buffer.com").rstrip("/")

    @property
    def token(self) -> str | None:
        return get_secret("buffer_api_token")

    def configured(self) -> bool:
        return bool(self.token)

    def graphql(self, query: str, variables: dict | None = None) -> dict:
        if not self.token:
            raise ConnectorError("Buffer API token is not configured.")
        r = httpx.post(
            self.api_url,
            headers={"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"},
            json={"query": query, "variables": variables or {}},
            timeout=45,
        )
        if r.status_code >= 400:
            raise ConnectorError(f"Buffer HTTP {r.status_code}: {r.text[:500]}")
        body = r.json()
        if body.get("errors"):
            raise ConnectorError("Buffer GraphQL: " + "; ".join(str(x.get("message")) for x in body["errors"]))
        return body.get("data") or {}

    def organization_and_channels(self) -> tuple[dict, list[dict]]:
        org_data = self.graphql(
            """query GetOrganizations { account { organizations { id name } } }"""
        )
        orgs = (org_data.get("account") or {}).get("organizations") or []
        if not orgs:
            raise ConnectorError("No Buffer organization was found.")
        org = next((o for o in orgs if o.get("name") == "BetweenPay"), orgs[0])
        channel_data = self.graphql(
            """
            query GetChannels($orgId: OrganizationId!) {
              channels(input:{organizationId:$orgId,filter:{isLocked:false}}) {
                id name displayName service isQueuePaused
              }
            }
            """,
            {"orgId": org["id"]},
        )
        return org, channel_data.get("channels") or []

    def test_connection(self) -> dict[str, Any]:
        if not self.configured():
            return {"ok": False, "message": "Buffer API token missing.", "channels": []}
        try:
            org, channels = self.organization_and_channels()
            return {
                "ok": True,
                "message": f"Connected to Buffer workspace {org.get('name')}",
                "channels": [c.get("service") for c in channels],
                "channel_details": channels,
            }
        except Exception as exc:
            return {"ok": False, "message": str(exc), "channels": []}

    def _channel(self, platform: str) -> dict:
        _, channels = self.organization_and_channels()
        service = "twitter" if platform == "x" else platform
        channel = next((c for c in channels if c.get("service") == service), None)
        if not channel:
            raise ConnectorError(f"Buffer {platform} channel is not connected.")
        return channel

    def _pinterest_board(self, channel_id: str) -> dict:
        data = self.graphql(
            """
            query GetPinterestChannel($id: ChannelId!) {
              channel(input:{id:$id}) {
                metadata { ... on PinterestMetadata { boards { serviceId name url } } }
              }
            }
            """,
            {"id": channel_id},
        )
        boards = (((data.get("channel") or {}).get("metadata") or {}).get("boards")) or []
        preferred_name = self.store.get("pinterest_board_name", "BetweenPay").strip().lower()
        board = next((b for b in boards if preferred_name in str(b.get("name", "")).lower()), None)
        if not board:
            raise ConnectorError(
                f"Pinterest is connected but no board containing '{self.store.get('pinterest_board_name','BetweenPay')}' was found."
            )
        return board

    def create_post(self, item: dict[str, Any]) -> dict:
        platform = str(item["platform"])
        channel = self._channel(platform)
        input_obj: dict[str, Any] = {
            "channelId": channel["id"],
            "schedulingType": "automatic",
            "mode": "shareNow",
            "text": str(item.get("text") or ""),
            "assets": [{"image": {"url": item["asset_url"]}}] if item.get("asset_url") else [],
        }

        if platform == "x" and item.get("post_type") == "thread":
            try:
                thread = json.loads(item.get("performance") or "{}").get("thread")
            except Exception:
                thread = None
            if not thread:
                parts = [p.strip() for p in str(item.get("text") or "").split("\n---THREAD---\n") if p.strip()]
                thread = [
                    {
                        "text": p,
                        "assets": [{"image": {"url": item["asset_url"]}}] if i == 0 and item.get("asset_url") else [],
                    }
                    for i, p in enumerate(parts)
                ]
            if len(thread) > 1:
                input_obj["text"] = thread[0]["text"]
                input_obj["assets"] = []
                input_obj["metadata"] = {"twitter": {"thread": thread}}

        if platform == "pinterest":
            board = self._pinterest_board(channel["id"])
            input_obj["metadata"] = {
                "pinterest": {
                    "boardServiceId": board["serviceId"],
                    "title": str(item.get("title") or "BetweenPay"),
                    "url": str(item.get("destination") or "https://betweenpay.tasklaneco.com/"),
                }
            }

        data = self.graphql(
            """
            mutation CreatePost($input: CreatePostInput!) {
              createPost(input:$input) {
                ... on PostActionSuccess { post { id status dueAt channelId } }
                ... on MutationError { message }
              }
            }
            """,
            {"input": input_obj},
        )
        result = data.get("createPost") or {}
        if result.get("message"):
            raise ConnectorError(str(result["message"]))
        post = result.get("post") or {}
        if not post.get("id"):
            raise ConnectorError("Buffer did not return a post ID.")
        return post

    def get_post(self, post_id: str) -> dict | None:
        data = self.graphql(
            """query GetPost($id: PostId!) { post(input:{id:$id}) { id status dueAt } }""",
            {"id": post_id},
        )
        return data.get("post")
