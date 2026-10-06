from __future__ import annotations

import json
from typing import Any

from .config import ASSET_URLS, CALCULATOR_URL, CONTEST_URL, PRODUCT_URL
from .vault import get_secret


class AIPlanner:
    def __init__(self, store):
        self.store = store

    def configured(self) -> bool:
        return bool(get_secret("openai_api_key"))

    def allowed_today(self) -> bool:
        return self.store.ai_calls_today() < self.store.get_int("openai_daily_call_limit", 6)

    def generate_campaign_variants(self, metrics, diagnosis: str, channels: list[str], count: int = 3) -> list[dict[str, Any]]:
        if not self.configured() or not self.allowed_today():
            return []
        from openai import OpenAI
        key = get_secret("openai_api_key")
        model = self.store.get("openai_model", "gpt-5.6-luna")
        client = OpenAI(api_key=key)
        experiment_memory = []
        for row in self.store.experiments(limit=15):
            experiment_memory.append({
                "experiment_key": row["experiment_key"],
                "channel": row["channel"],
                "angle": row["angle"],
                "status": row["status"],
                "sessions": row["sessions"],
                "checkout_starts": row["checkout_starts"],
                "purchases": row["purchases"],
                "revenue": row["revenue"],
                "score": row["score"],
            })
        prompt = {
            "goal": f"Increase legitimate BetweenPay purchases toward {self.store.get_int('weekly_sales_target', 100)} completed sales in a rolling 7-day window.",
            "product": {
                "name": "BetweenPay",
                "price": "$12.99 one-time",
                "core_value": "Protect upcoming bills, goals and a selected safety buffer, then calculate one Safe-to-Spend number between paydays.",
                "bank_connection": "No bank connection required.",
                "contest": "A live $10,000 first-place referral challenge exists. Total Top-10 prize pool is $12,050. Never promise a win.",
            },
            "diagnosis": diagnosis,
            "metrics": {
                "sales_7d": metrics.sales_7d,
                "sessions_7d": metrics.sessions_7d,
                "checkout_starts_7d": metrics.checkout_starts_7d,
                "sales_24h": metrics.sales_24h,
                "source_performance": metrics.source_performance[:12],
            },
            "experiment_memory": experiment_memory,
            "exploration_share": self.store.get_float("exploration_share", 0.30),
            "channels": channels,
            "rules": [
                "Organic only; no paid advertising.",
                "No WhatsApp.",
                "No deceptive urgency, fake social proof, fake personal experience, or winning guarantees.",
                "Use distinct UTM content labels so variants can be measured.",
                "Prefer product-first or free-calculator value unless contest-first is strategically justified.",
                "Exploit measured winners more often, but reserve the configured exploration share for genuinely new angles.",
                "Do not repeat the same content slug or wording from experiment_memory; create a measurable evolution of a winner or a distinct exploration test.",
                "Facebook may be longer; X concise; Pinterest requires a useful search-style title and description.",
            ],
            "output": f"Return exactly {count} campaign variants as JSON.",
        }
        instructions = (
            "You are the campaign strategist inside an autonomous sales system. "
            "Return a JSON object with key 'variants'. Each variant must include: platform, angle, theme, text, title, "
            "destination_type (contest|calculator|product), asset_type (contest|calculator|product), content_slug, hypothesis. "
            "Do not include markdown."
        )
        try:
            response = client.responses.create(
                model=model,
                instructions=instructions,
                input=json.dumps(prompt, default=str),
                max_output_tokens=1400,
                text={"format": {"type": "json_object"}},
            )
            data = json.loads(response.output_text)
            variants = data.get("variants") or []
            normalized = []
            for v in variants[:count]:
                platform = str(v.get("platform") or "").lower()
                if platform not in channels:
                    continue
                content_slug = str(v.get("content_slug") or "ai_variant").strip().lower().replace(" ", "_")[:64]
                dtype = str(v.get("destination_type") or "product")
                if dtype == "contest":
                    destination = CONTEST_URL.format(source=platform, content=content_slug)
                    campaign = "live_10k"
                elif dtype == "calculator":
                    destination = CALCULATOR_URL.format(source=platform, content=content_slug)
                    campaign = "visual_search" if platform == "pinterest" else "safe_to_spend"
                else:
                    destination = PRODUCT_URL.format(source=platform, content=content_slug)
                    campaign = "product_discovery"
                asset_type = str(v.get("asset_type") or dtype)
                normalized.append({
                    "platform": platform,
                    "angle": str(v.get("angle") or "product_value")[:80],
                    "theme": str(v.get("theme") or "ai_generated")[:80],
                    "text": str(v.get("text") or "").strip(),
                    "title": str(v.get("title") or "").strip() or None,
                    "destination": destination,
                    "asset_url": ASSET_URLS.get(asset_type, ASSET_URLS["product"]),
                    "source": platform,
                    "medium": "organic",
                    "campaign": campaign,
                    "content": content_slug,
                    "hypothesis": str(v.get("hypothesis") or "")[:500],
                })
            usage = getattr(response, "usage", None)
            self.store.log_ai_usage(
                model=model,
                purpose="campaign_variants",
                success=True,
                input_tokens=getattr(usage, "input_tokens", None) if usage else None,
                output_tokens=getattr(usage, "output_tokens", None) if usage else None,
                request_id=getattr(response, "_request_id", None),
            )
            return normalized
        except Exception as exc:
            self.store.log_ai_usage(model=model, purpose="campaign_variants", success=False, error=str(exc)[:1000])
            return []
