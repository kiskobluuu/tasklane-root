from __future__ import annotations

import json
import random
from datetime import datetime, timedelta, timezone
from typing import Any

from .ai_planner import AIPlanner
from .config import APP_VERSION, BETWEENPAY_SITE, CHANNELS
from .connectors import BufferPublisher, SupabaseConnector
from .models import EngineDecision, MetricsSnapshot
from .templates import contest_variants, fallback_variants


class SalesEngine:
    def __init__(self, store):
        self.store = store
        self.supabase = SupabaseConnector(store)
        self.buffer = BufferPublisher(store)
        self.ai = AIPlanner(store)
        self.last_decision: EngineDecision | None = None

    def _diagnose(self, m: MetricsSnapshot) -> tuple[str, str, str]:
        target = self.store.get_int("weekly_sales_target", 100)
        gap = max(0, target - m.sales_7d)
        min_sessions = self.store.get_int("min_sessions_before_judgment", 20)
        min_checkouts = self.store.get_int("min_checkouts_before_judgment", 8)
        if gap == 0:
            return (
                "target_reached",
                f"The rolling 7-day target of {target} sales has been reached.",
                "Protect winners, increase durable reach, and keep a small exploration budget active.",
            )
        if m.sessions_7d < min_sessions:
            return (
                "traffic",
                f"Only {m.sessions_7d} measured sessions are available in the last 7 days, which is too little traffic to judge conversion reliably.",
                "Increase diverse qualified organic traffic across connected channels and free discovery surfaces.",
            )
        if m.checkout_starts_7d < min_checkouts or m.checkout_start_rate < 0.03:
            return (
                "click_to_checkout",
                f"Traffic exists, but checkout starts are weak ({m.checkout_starts_7d} starts from {m.sessions_7d} sessions).",
                "Test clearer problem/solution hooks, stronger CTAs, and lower-friction calculator-to-product bridges.",
            )
        if m.checkout_to_purchase_rate < 0.15:
            return (
                "checkout_conversion",
                f"Checkout intent exists, but checkout-to-purchase conversion is only {m.checkout_to_purchase_rate:.1%}.",
                "Prioritize credibility, purchase reassurance, recovery messaging, and detection of checkout friction.",
            )
        return (
            "scale_winners",
            f"The funnel is producing purchases, but {gap} more sales are needed to reach {target} in the rolling 7-day window.",
            "Scale the best-performing source/angle while reserving part of activity for new experiments.",
        )

    def _connected_channels(self) -> list[str]:
        status = self.buffer.test_connection()
        if not status.get("ok"):
            return []
        services = status.get("channels") or []
        out = []
        if "facebook" in services:
            out.append("facebook")
        if "twitter" in services:
            out.append("x")
        if "pinterest" in services:
            out.append("pinterest")
        return out

    def _sync_experiments_from_metrics(self, m: MetricsSnapshot) -> None:
        min_sessions = self.store.get_int("min_sessions_before_judgment", 20)
        for p in m.source_performance:
            source = str(p.get("source") or "direct")
            campaign = str(p.get("campaign") or "none")
            content = str(p.get("content") or "none")
            key = f"{source}:{campaign}:{content}"
            sessions = int(p.get("sessions") or 0)
            checkouts = int(p.get("checkout_starts") or 0)
            purchases = int(p.get("purchases") or 0)
            revenue = float(p.get("revenue") or 0)
            maturity = min(1.0, sessions / max(1, min_sessions))
            score = maturity * (purchases * 100 + revenue * 2 + checkouts * 5 + min(sessions, 100) * 0.1)
            status = "active"
            learning = {"sample_mature": sessions >= min_sessions}
            if sessions >= min_sessions and purchases > 0:
                status = "winner"
                learning["summary"] = "Produced at least one purchase with a mature traffic sample."
            elif sessions >= min_sessions and checkouts == 0:
                status = "loser"
                learning["summary"] = "Mature sample produced no checkout starts."
            self.store.upsert_experiment({
                "experiment_key": key,
                "channel": source,
                "angle": content,
                "source": source,
                "campaign": campaign,
                "content": content,
                "sessions": sessions,
                "checkout_starts": checkouts,
                "purchases": purchases,
                "revenue": revenue,
                "score": score,
                "status": status,
                "learnings": learning,
            })

    def _sync_acquisition_queue(self) -> int:
        if not self.supabase.configured():
            return 0
        rows = self.supabase.fetch_acquisition_queue(300)
        self.store.upsert_acquisition_items(rows)
        return len(rows)

    def _sync_remote_social_queue(self) -> int:
        if not self.supabase.configured():
            return 0
        imported = 0
        for row in self.supabase.fetch_remote_social_queue(100):
            remote_id = int(row["id"])
            already = [r for r in self.store.content_queue(500) if r["remote_queue_id"] == remote_id]
            if already:
                continue
            payload = row.get("provider_payload") or {}
            text = str(row.get("post_copy") or "")
            performance: dict[str, Any] = {}
            if row.get("platform") == "x" and isinstance(payload, dict) and payload.get("thread"):
                thread = []
                for i, part in enumerate(payload.get("thread") or []):
                    thread.append({
                        "text": str(part.get("text") or ""),
                        "assets": [{"image": {"url": row.get("asset_url")}}]
                        if i == 0 and row.get("asset_url") else [],
                    })
                performance["thread"] = thread
            if row.get("platform") == "pinterest" and isinstance(payload, dict):
                title = payload.get("title")
                destination = payload.get("destination") or row.get("destination")
                text = payload.get("description") or text
            else:
                title = None
                destination = row.get("destination")
            self.store.queue_content({
                "platform": row.get("platform"),
                "post_type": row.get("post_type") or "post",
                "theme": row.get("theme") or "imported",
                "growth_angle": row.get("growth_angle"),
                "text": text,
                "title": title,
                "destination": destination,
                "asset_url": row.get("asset_url"),
                "source": row.get("source"),
                "medium": row.get("medium") or "organic",
                "campaign": row.get("campaign"),
                "content": row.get("content"),
                "experiment_key": row.get("experiment_key"),
                "scheduled_for": row.get("scheduled_for") or datetime.now(timezone.utc).isoformat(),
                "status": "ready" if row.get("status") == "ready" else "scheduled",
                "provider": "buffer",
                "remote_queue_id": remote_id,
                "performance": performance,
            })
            imported += 1
        if imported:
            self.store.log_action(
                "sync_social_queue",
                f"Imported {imported} existing BetweenPay social queue item(s) into the desktop engine.",
                status="executed",
            )
        return imported

    def _daily_post_count(self) -> int:
        today = datetime.now(timezone.utc).date().isoformat()
        return sum(
            1
            for r in self.store.content_queue(500)
            if str(r["created_at"]).startswith(today) and r["status"] in {"ready", "scheduled", "published"}
        )

    def _next_slot(self, offset_index: int = 0) -> datetime:
        now = datetime.now(timezone.utc)
        return now + timedelta(minutes=20 + 90 * offset_index)

    def _queue_variants(self, variants: list[dict], max_new: int) -> int:
        queued = 0
        for variant in variants:
            if queued >= max_new:
                break
            platform = variant["platform"]
            scheduled = self._next_slot(queued)
            if self.store.content_exists(platform, variant.get("campaign"), variant.get("content"), scheduled.date().isoformat()):
                continue
            exp_key = f"{platform}:{variant.get('campaign')}:{variant.get('content')}"
            post_type = "thread" if platform == "x" and "---THREAD---" in variant.get("text", "") else ("pin" if platform == "pinterest" else "post")
            self.store.queue_content({
                **variant,
                "post_type": post_type,
                "growth_angle": variant.get("angle"),
                "experiment_key": exp_key,
                "scheduled_for": scheduled.isoformat(),
                "status": "ready",
                "provider": "buffer",
            })
            self.store.upsert_experiment({
                "experiment_key": exp_key,
                "channel": platform,
                "angle": variant.get("angle") or variant.get("content"),
                "destination": variant.get("destination"),
                "hypothesis": variant.get("hypothesis"),
                "source": variant.get("source"),
                "medium": variant.get("medium"),
                "campaign": variant.get("campaign"),
                "content": variant.get("content"),
                "status": "active",
            })
            self.store.log_action(
                "queue_campaign_variant",
                variant.get("hypothesis") or "Queued a measurable organic campaign variant.",
                channel=platform,
                experiment_key=exp_key,
                payload={"scheduled_for": scheduled.isoformat(), "content": variant.get("content")},
                status="executed",
            )
            queued += 1
        return queued

    def _plan_growth_actions(self, m: MetricsSnapshot, constraint: str, diagnosis: str) -> list[dict]:
        actions = []
        channels = self._connected_channels()
        if not channels:
            actions.append({"type": "blocker", "reason": "No Buffer publishing channels are available through the API yet."})
            return actions

        post_cap = self.store.get_int("daily_post_cap", 6)
        remaining = max(0, post_cap - self._daily_post_count())
        if remaining <= 0:
            actions.append({"type": "hold", "reason": "Daily organic post cap reached; wait for performance data."})
            return actions

        desired = min(remaining, max(1, len(channels)))
        variants: list[dict] = []
        if self.ai.configured() and self.ai.allowed_today():
            variants = self.ai.generate_campaign_variants(m, diagnosis, channels, count=desired)
        if not variants:
            variants = fallback_variants(channels)
            if constraint in {"traffic", "scale_winners"} and random.random() < 0.35:
                variants = contest_variants(channels) + variants
        queued = self._queue_variants(variants, desired)
        actions.append({"type": "queue_variants", "count": queued, "channels": channels})
        return actions

    def run_once(self) -> EngineDecision:
        target = self.store.get_int("weekly_sales_target", 100)
        if not self.supabase.configured():
            decision = EngineDecision(
                diagnosis="Live BetweenPay data is not connected yet.",
                primary_constraint="configuration",
                recommended_action="Enter the Supabase service-role key once in Connections, then test the connection.",
                urgency="blocked",
                target=target,
                sales_7d=0,
                gap=target,
                pace_per_day=0.0,
                required_per_day=target / 7.0,
                planned_actions=[],
            )
            self.last_decision = decision
            self.store.log_action("engine_blocked", decision.diagnosis, status="blocked")
            return decision

        metrics = self.supabase.collect_metrics()
        self.store.save_snapshot(metrics)
        self.supabase.sync_snapshot(metrics)
        self._sync_experiments_from_metrics(metrics)
        self.supabase.sync_experiments([dict(r) for r in self.store.experiments(limit=100)])
        self._sync_acquisition_queue()
        self._sync_remote_social_queue()
        constraint, diagnosis, recommended = self._diagnose(metrics)
        target = self.store.get_int("weekly_sales_target", 100)
        gap = max(0, target - metrics.sales_7d)
        planned = self._plan_growth_actions(metrics, constraint, diagnosis) if self.store.get_bool("autopilot_enabled") else []

        urgency = "on_target" if gap == 0 else ("high" if metrics.sales_24h < target / 7 else "normal")
        decision = EngineDecision(
            diagnosis=diagnosis,
            primary_constraint=constraint,
            recommended_action=recommended,
            urgency=urgency,
            target=target,
            sales_7d=metrics.sales_7d,
            gap=gap,
            pace_per_day=metrics.sales_7d / 7.0,
            required_per_day=target / 7.0,
            planned_actions=planned,
        )
        self.last_decision = decision
        self.store.log_action(
            "engine_decision",
            diagnosis,
            payload={
                "constraint": constraint,
                "recommended_action": recommended,
                "target": target,
                "sales_7d": metrics.sales_7d,
                "gap": gap,
                "sales_24h": metrics.sales_24h,
                "planned_actions": planned,
            },
            status="executed",
        )
        self.supabase.log_remote_growth_action({
            "action_type": "desktop_engine_decision",
            "rationale": diagnosis,
            "action_payload": {
                "constraint": constraint,
                "recommended_action": recommended,
                "sales_7d": metrics.sales_7d,
                "target": target,
                "gap": gap,
            },
            "status": "executed",
            "executed_at": datetime.now(timezone.utc).isoformat(),
        })
        try:
            buffer_state = self.buffer.test_connection()
            self.supabase.update_heartbeat(
                app_version=APP_VERSION,
                autopilot=self.store.get_bool("autopilot_enabled"),
                target=target,
                sales_7d=metrics.sales_7d,
                last_strategy_cycle_at=datetime.now(timezone.utc).isoformat(),
                connection_state={
                    "supabase": True,
                    "buffer": bool(buffer_state.get("ok")),
                    "buffer_channels": buffer_state.get("channels") or [],
                    "openai": bool(self.ai.configured()),
                },
                machine_state={
                    "primary_constraint": constraint,
                    "recommended_action": recommended,
                    "ai_calls_today": self.store.ai_calls_today(),
                    "queue_items": len(self.store.content_queue(500)),
                },
            )
        except Exception:
            pass
        return decision

    def process_remote_commands(self) -> dict[str, int]:
        summary = {"completed": 0, "failed": 0, "rejected": 0}
        if not self.supabase.configured():
            return summary
        allowed_settings = {
            "daily_post_cap", "engine_interval_minutes", "publish_interval_minutes",
            "openai_daily_call_limit", "openai_model", "pinterest_board_name",
            "min_sessions_before_judgment", "min_checkouts_before_judgment",
        }
        for command_row in self.supabase.pending_commands(20):
            command_id = int(command_row["id"])
            command = str(command_row.get("command") or "").strip()
            payload = command_row.get("payload") or {}
            self.supabase.update_command(command_id, "running")
            try:
                result: dict[str, Any]
                if command == "run_engine":
                    d = self.run_once()
                    result = {
                        "constraint": d.primary_constraint,
                        "diagnosis": d.diagnosis,
                        "sales_7d": d.sales_7d,
                        "target": d.target,
                        "gap": d.gap,
                    }
                elif command == "publish_due":
                    result = self.publish_due()
                elif command == "set_weekly_target":
                    target = max(1, min(int(payload.get("target", 100)), 100000))
                    self.store.set("weekly_sales_target", target)
                    result = {"weekly_sales_target": target}
                elif command == "set_autopilot":
                    enabled = bool(payload.get("enabled", False))
                    self.store.set("autopilot_enabled", "1" if enabled else "0")
                    result = {"autopilot_enabled": enabled}
                elif command == "set_setting":
                    key = str(payload.get("key") or "")
                    if key not in allowed_settings:
                        raise PermissionError(f"Setting '{key}' is not remotely changeable.")
                    value = payload.get("value")
                    self.store.set(key, value)
                    result = {"key": key, "value": str(value)}
                elif command == "queue_content":
                    platform = str(payload.get("platform") or "").lower()
                    text = str(payload.get("text") or "").strip()
                    destination = str(payload.get("destination") or "").strip()
                    if platform not in CHANNELS:
                        raise PermissionError("Unsupported publishing platform.")
                    if not text or len(text) > 5000:
                        raise ValueError("Content text must be between 1 and 5000 characters.")
                    if destination and not destination.startswith(BETWEENPAY_SITE):
                        raise PermissionError("Remote queue content may only link to BetweenPay.")
                    scheduled_for = str(payload.get("scheduled_for") or datetime.now(timezone.utc).isoformat())
                    item = {
                        "platform": platform,
                        "post_type": payload.get("post_type") or ("pin" if platform == "pinterest" else "post"),
                        "theme": payload.get("theme") or "chatgpt",
                        "growth_angle": payload.get("growth_angle") or "chatgpt",
                        "text": text,
                        "title": payload.get("title"),
                        "destination": destination or BETWEENPAY_SITE,
                        "asset_url": payload.get("asset_url"),
                        "source": payload.get("source") or platform,
                        "medium": "organic",
                        "campaign": payload.get("campaign") or "sales_os",
                        "content": payload.get("content") or f"chatgpt_{command_id}",
                        "experiment_key": payload.get("experiment_key") or f"{platform}:sales_os:chatgpt_{command_id}",
                        "scheduled_for": scheduled_for,
                        "status": "ready",
                        "provider": "buffer",
                    }
                    local_id = self.store.queue_content(item)
                    result = {"queued": True, "local_content_id": local_id, "platform": platform}
                else:
                    self.supabase.update_command(
                        command_id, "rejected", error=f"Unsupported command: {command}"
                    )
                    summary["rejected"] += 1
                    continue
                self.supabase.update_command(command_id, "completed", result=result)
                self.store.log_action(
                    "remote_command",
                    f"Completed cloud command: {command}",
                    payload={"command_id": command_id, "payload": payload},
                    status="executed",
                    result=result,
                )
                summary["completed"] += 1
            except PermissionError as exc:
                self.supabase.update_command(command_id, "rejected", error=str(exc))
                summary["rejected"] += 1
            except Exception as exc:
                self.supabase.update_command(command_id, "failed", error=str(exc))
                summary["failed"] += 1
        return summary

    def publish_due(self) -> dict[str, int]:
        summary = {"published": 0, "scheduled": 0, "failed": 0, "blocked": 0}
        if not self.store.get_bool("autopilot_enabled"):
            return summary
        if not self.buffer.configured():
            return summary
        now = datetime.now(timezone.utc).isoformat()
        for row in self.store.due_content(now, 12):
            item = dict(row)
            try:
                post = self.buffer.create_post(item)
                provider_status = str(post.get("status") or "pending")
                final_status = "published" if provider_status == "sent" else "scheduled"
                self.store.update_content(
                    row["id"],
                    status=final_status,
                    provider_post_id=post.get("id"),
                    provider_status=provider_status,
                    last_error=None,
                )
                if row["remote_queue_id"] and self.supabase.configured():
                    self.supabase.update_remote_social_queue(
                        int(row["remote_queue_id"]),
                        {
                            "status": final_status,
                            "provider": "buffer",
                            "external_post_id": post.get("id"),
                            "provider_status": provider_status,
                            "provider_updated_at": datetime.now(timezone.utc).isoformat(),
                            "last_error": None,
                        },
                    )
                self.store.log_action(
                    "publish_social",
                    f"Sent {row['platform']} content to Buffer.",
                    channel=row["platform"],
                    experiment_key=row["experiment_key"],
                    payload={"provider_post_id": post.get("id")},
                    status="executed",
                )
                summary[final_status] += 1
            except Exception as exc:
                msg = str(exc)[:1000]
                blocked = "not connected" in msg.lower() or "no board" in msg.lower()
                self.store.update_content(
                    row["id"],
                    status="ready" if blocked else "failed",
                    last_error=msg,
                    provider_status="blocked" if blocked else "error",
                )
                if row["remote_queue_id"] and self.supabase.configured():
                    self.supabase.update_remote_social_queue(
                        int(row["remote_queue_id"]),
                        {
                            "provider": "buffer",
                            "provider_status": "blocked" if blocked else "error",
                            "provider_updated_at": datetime.now(timezone.utc).isoformat(),
                            "last_error": msg,
                        },
                    )
                self.store.log_action(
                    "publish_social",
                    msg,
                    channel=row["platform"],
                    experiment_key=row["experiment_key"],
                    status="blocked" if blocked else "failed",
                )
                summary["blocked" if blocked else "failed"] += 1
        try:
            snap = self.store.latest_snapshot()
            sales = int(snap["sales_7d"]) if snap else 0
            self.supabase.update_heartbeat(
                app_version=APP_VERSION,
                autopilot=self.store.get_bool("autopilot_enabled"),
                target=self.store.get_int("weekly_sales_target", 100),
                sales_7d=sales,
                last_publish_cycle_at=datetime.now(timezone.utc).isoformat(),
                machine_state={"last_publish_summary": summary},
            )
        except Exception:
            pass
        return summary

    def reconcile_buffer_posts(self) -> int:
        if not self.buffer.configured():
            return 0
        changed = 0
        for row in self.store.content_queue(200):
            if row["status"] != "scheduled" or not row["provider_post_id"]:
                continue
            try:
                post = self.buffer.get_post(row["provider_post_id"])
                if not post:
                    continue
                status = str(post.get("status") or "")
                if status == "sent":
                    self.store.update_content(row["id"], status="published", provider_status="sent")
                    changed += 1
                elif status == "error":
                    self.store.update_content(row["id"], status="failed", provider_status="error")
                    changed += 1
            except Exception:
                continue
        return changed
