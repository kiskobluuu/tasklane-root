from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import (
    DEFAULT_DAILY_AI_CALL_LIMIT,
    DEFAULT_DAILY_POST_CAP,
    DEFAULT_ENGINE_INTERVAL_MINUTES,
    DEFAULT_EXPLORATION_SHARE,
    DEFAULT_OPENAI_MODEL,
    DEFAULT_PRODUCT_PRICE,
    DEFAULT_PUBLISH_INTERVAL_MINUTES,
    DEFAULT_WEEKLY_TARGET,
    SUPABASE_PROJECT_URL,
)

APP_DIR = Path.home() / "BetweenPaySalesOS"
DB_PATH = APP_DIR / "sales_os.db"
LOG_DIR = APP_DIR / "logs"


class Store:
    def __init__(self, db_path: str | Path | None = None):
        APP_DIR.mkdir(parents=True, exist_ok=True)
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        self.db_path = Path(db_path) if db_path else DB_PATH
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.lock = threading.RLock()
        self._init()

    def _init(self) -> None:
        with self.lock:
            self.conn.executescript(
                """
                PRAGMA journal_mode=WAL;
                PRAGMA foreign_keys=ON;

                CREATE TABLE IF NOT EXISTS settings(
                  key TEXT PRIMARY KEY,
                  value TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS actions(
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  created_at TEXT NOT NULL,
                  action_type TEXT NOT NULL,
                  channel TEXT,
                  experiment_key TEXT,
                  rationale TEXT NOT NULL,
                  payload TEXT NOT NULL DEFAULT '{}',
                  status TEXT NOT NULL DEFAULT 'planned',
                  executed_at TEXT,
                  result TEXT NOT NULL DEFAULT '{}'
                );

                CREATE TABLE IF NOT EXISTS snapshots(
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  captured_at TEXT NOT NULL,
                  sales_7d INTEGER NOT NULL DEFAULT 0,
                  revenue_7d REAL NOT NULL DEFAULT 0,
                  sessions_7d INTEGER NOT NULL DEFAULT 0,
                  landing_views_7d INTEGER NOT NULL DEFAULT 0,
                  contest_views_7d INTEGER NOT NULL DEFAULT 0,
                  checkout_views_7d INTEGER NOT NULL DEFAULT 0,
                  checkout_starts_7d INTEGER NOT NULL DEFAULT 0,
                  leads_7d INTEGER NOT NULL DEFAULT 0,
                  participant_joins_7d INTEGER NOT NULL DEFAULT 0,
                  qualified_referrals_7d INTEGER NOT NULL DEFAULT 0,
                  sales_24h INTEGER NOT NULL DEFAULT 0,
                  revenue_24h REAL NOT NULL DEFAULT 0,
                  sessions_24h INTEGER NOT NULL DEFAULT 0,
                  checkout_starts_24h INTEGER NOT NULL DEFAULT 0,
                  data TEXT NOT NULL DEFAULT '{}'
                );

                CREATE TABLE IF NOT EXISTS experiments(
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  experiment_key TEXT NOT NULL UNIQUE,
                  channel TEXT NOT NULL,
                  angle TEXT NOT NULL,
                  destination TEXT,
                  objective TEXT NOT NULL DEFAULT 'completed_purchases',
                  hypothesis TEXT,
                  status TEXT NOT NULL DEFAULT 'active',
                  source TEXT,
                  medium TEXT DEFAULT 'organic',
                  campaign TEXT,
                  content TEXT,
                  sessions INTEGER NOT NULL DEFAULT 0,
                  checkout_starts INTEGER NOT NULL DEFAULT 0,
                  purchases INTEGER NOT NULL DEFAULT 0,
                  revenue REAL NOT NULL DEFAULT 0,
                  score REAL,
                  started_at TEXT,
                  ended_at TEXT,
                  learnings TEXT NOT NULL DEFAULT '{}',
                  updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS content_queue(
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  created_at TEXT NOT NULL,
                  platform TEXT NOT NULL,
                  post_type TEXT NOT NULL DEFAULT 'post',
                  theme TEXT NOT NULL,
                  growth_angle TEXT,
                  text TEXT NOT NULL,
                  title TEXT,
                  destination TEXT,
                  asset_url TEXT,
                  source TEXT,
                  medium TEXT DEFAULT 'organic',
                  campaign TEXT,
                  content TEXT,
                  experiment_key TEXT,
                  scheduled_for TEXT NOT NULL,
                  status TEXT NOT NULL DEFAULT 'ready',
                  provider TEXT DEFAULT 'buffer',
                  provider_post_id TEXT,
                  provider_status TEXT,
                  external_url TEXT,
                  remote_queue_id INTEGER,
                  last_error TEXT,
                  performance TEXT NOT NULL DEFAULT '{}'
                );

                CREATE TABLE IF NOT EXISTS acquisition_queue(
                  remote_id INTEGER PRIMARY KEY,
                  channel TEXT NOT NULL,
                  placement TEXT,
                  priority INTEGER NOT NULL DEFAULT 50,
                  status TEXT NOT NULL DEFAULT 'ready',
                  destination TEXT,
                  source TEXT,
                  medium TEXT,
                  campaign TEXT,
                  content TEXT,
                  notes TEXT,
                  updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS ai_usage(
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  created_at TEXT NOT NULL,
                  model TEXT,
                  purpose TEXT,
                  success INTEGER NOT NULL DEFAULT 0,
                  input_tokens INTEGER,
                  output_tokens INTEGER,
                  estimated_cost REAL,
                  request_id TEXT,
                  error TEXT
                );

                CREATE TABLE IF NOT EXISTS sync_state(
                  key TEXT PRIMARY KEY,
                  value TEXT NOT NULL
                );
                """
            )
            self.conn.commit()

            # v1.0.3 repair: Buffer requires Facebook metadata.type.
            self.conn.execute(
                """UPDATE content_queue
                   SET status='ready', provider_status=NULL, last_error=NULL
                   WHERE provider='buffer'
                     AND platform='facebook'
                     AND status='failed'
                     AND last_error LIKE 'Invalid post: Facebook posts require a type%'"""
            )
            self.conn.commit()

        defaults = {
            "weekly_sales_target": str(DEFAULT_WEEKLY_TARGET),
            "product_price": str(DEFAULT_PRODUCT_PRICE),
            "autopilot_enabled": "0",
            "engine_interval_minutes": str(DEFAULT_ENGINE_INTERVAL_MINUTES),
            "publish_interval_minutes": str(DEFAULT_PUBLISH_INTERVAL_MINUTES),
            "daily_post_cap": str(DEFAULT_DAILY_POST_CAP),
            "exploration_share": str(DEFAULT_EXPLORATION_SHARE),
            "supabase_url": SUPABASE_PROJECT_URL,
            "buffer_api_url": "https://api.buffer.com",
            "openai_model": DEFAULT_OPENAI_MODEL,
            "openai_daily_call_limit": str(DEFAULT_DAILY_AI_CALL_LIMIT),
            "openai_web_search_enabled": "0",
            "pinterest_board_name": "BetweenPay",
            "github_repo": "kiskobluuu/tasklane-root",
            "github_betweenpay_path": "betweenpay",
            "run_on_startup": "0",
            "min_sessions_before_judgment": "20",
            "min_checkouts_before_judgment": "8",
        }
        for key, value in defaults.items():
            self.set_default(key, value)

    def set_default(self, key: str, value: Any) -> None:
        with self.lock:
            self.conn.execute("INSERT OR IGNORE INTO settings(key,value) VALUES(?,?)", (key, str(value)))
            self.conn.commit()

    def get(self, key: str, default: str = "") -> str:
        with self.lock:
            row = self.conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return row["value"] if row else default

    def get_int(self, key: str, default: int = 0) -> int:
        try:
            return int(float(self.get(key, str(default))))
        except Exception:
            return default

    def get_float(self, key: str, default: float = 0.0) -> float:
        try:
            return float(self.get(key, str(default)))
        except Exception:
            return default

    def get_bool(self, key: str, default: bool = False) -> bool:
        return self.get(key, "1" if default else "0") == "1"

    def set(self, key: str, value: Any) -> None:
        with self.lock:
            self.conn.execute(
                "INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (key, str(value)),
            )
            self.conn.commit()

    def log_action(
        self,
        action_type: str,
        rationale: str,
        channel: str | None = None,
        experiment_key: str | None = None,
        payload: dict | None = None,
        status: str = "planned",
        result: dict | None = None,
    ) -> int:
        now = datetime.now(timezone.utc).isoformat()
        executed_at = now if status == "executed" else None
        with self.lock:
            cur = self.conn.execute(
                """INSERT INTO actions(created_at,action_type,channel,experiment_key,rationale,payload,status,executed_at,result)
                VALUES(?,?,?,?,?,?,?,?,?)""",
                (
                    now,
                    action_type,
                    channel,
                    experiment_key,
                    rationale,
                    json.dumps(payload or {}),
                    status,
                    executed_at,
                    json.dumps(result or {}),
                ),
            )
            self.conn.commit()
            return int(cur.lastrowid)

    def update_action(self, action_id: int, status: str, result: dict | None = None) -> None:
        now = datetime.now(timezone.utc).isoformat() if status == "executed" else None
        with self.lock:
            self.conn.execute(
                "UPDATE actions SET status=?,executed_at=COALESCE(?,executed_at),result=? WHERE id=?",
                (status, now, json.dumps(result or {}), action_id),
            )
            self.conn.commit()

    def recent_actions(self, limit: int = 100):
        with self.lock:
            return self.conn.execute("SELECT * FROM actions ORDER BY id DESC LIMIT ?", (limit,)).fetchall()

    def save_snapshot(self, metrics) -> int:
        with self.lock:
            cur = self.conn.execute(
                """INSERT INTO snapshots(
                  captured_at,sales_7d,revenue_7d,sessions_7d,landing_views_7d,contest_views_7d,
                  checkout_views_7d,checkout_starts_7d,leads_7d,participant_joins_7d,qualified_referrals_7d,
                  sales_24h,revenue_24h,sessions_24h,checkout_starts_24h,data
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    datetime.now(timezone.utc).isoformat(),
                    metrics.sales_7d,
                    metrics.revenue_7d,
                    metrics.sessions_7d,
                    metrics.landing_views_7d,
                    metrics.contest_views_7d,
                    metrics.checkout_views_7d,
                    metrics.checkout_starts_7d,
                    metrics.leads_7d,
                    metrics.participant_joins_7d,
                    metrics.qualified_referrals_7d,
                    metrics.sales_24h,
                    metrics.revenue_24h,
                    metrics.sessions_24h,
                    metrics.checkout_starts_24h,
                    json.dumps(metrics.raw or {}),
                ),
            )
            self.conn.commit()
            return int(cur.lastrowid)

    def latest_snapshot(self):
        with self.lock:
            return self.conn.execute("SELECT * FROM snapshots ORDER BY id DESC LIMIT 1").fetchone()

    def snapshots(self, limit: int = 100):
        with self.lock:
            return self.conn.execute("SELECT * FROM snapshots ORDER BY id DESC LIMIT ?", (limit,)).fetchall()

    def upsert_experiment(self, data: dict[str, Any]) -> None:
        now = datetime.now(timezone.utc).isoformat()
        key = data["experiment_key"]
        with self.lock:
            self.conn.execute(
                """INSERT INTO experiments(
                   experiment_key,channel,angle,destination,objective,hypothesis,status,source,medium,campaign,content,
                   sessions,checkout_starts,purchases,revenue,score,started_at,learnings,updated_at
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(experiment_key) DO UPDATE SET
                   sessions=excluded.sessions,checkout_starts=excluded.checkout_starts,purchases=excluded.purchases,
                   revenue=excluded.revenue,score=excluded.score,status=excluded.status,learnings=excluded.learnings,
                   updated_at=excluded.updated_at""",
                (
                    key,
                    data.get("channel", "unknown"),
                    data.get("angle", "unknown"),
                    data.get("destination"),
                    data.get("objective", "completed_purchases"),
                    data.get("hypothesis"),
                    data.get("status", "active"),
                    data.get("source"),
                    data.get("medium", "organic"),
                    data.get("campaign"),
                    data.get("content"),
                    int(data.get("sessions", 0) or 0),
                    int(data.get("checkout_starts", 0) or 0),
                    int(data.get("purchases", 0) or 0),
                    float(data.get("revenue", 0) or 0),
                    data.get("score"),
                    data.get("started_at") or now,
                    json.dumps(data.get("learnings") or {}),
                    now,
                ),
            )
            self.conn.commit()

    def experiments(self, status: str | None = None, limit: int = 200):
        with self.lock:
            if status:
                return self.conn.execute(
                    "SELECT * FROM experiments WHERE status=? ORDER BY COALESCE(score,0) DESC,id DESC LIMIT ?",
                    (status, limit),
                ).fetchall()
            return self.conn.execute(
                "SELECT * FROM experiments ORDER BY COALESCE(score,0) DESC,id DESC LIMIT ?", (limit,)
            ).fetchall()

    def queue_content(self, item: dict[str, Any]) -> int:
        with self.lock:
            cur = self.conn.execute(
                """INSERT INTO content_queue(
                  created_at,platform,post_type,theme,growth_angle,text,title,destination,asset_url,source,medium,campaign,
                  content,experiment_key,scheduled_for,status,provider,remote_queue_id,performance
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    datetime.now(timezone.utc).isoformat(),
                    item["platform"],
                    item.get("post_type", "post"),
                    item.get("theme", "general"),
                    item.get("growth_angle"),
                    item["text"],
                    item.get("title"),
                    item.get("destination"),
                    item.get("asset_url"),
                    item.get("source", item["platform"]),
                    item.get("medium", "organic"),
                    item.get("campaign"),
                    item.get("content"),
                    item.get("experiment_key"),
                    item["scheduled_for"],
                    item.get("status", "ready"),
                    item.get("provider", "buffer"),
                    item.get("remote_queue_id"),
                    json.dumps(item.get("performance") or {}),
                ),
            )
            self.conn.commit()
            return int(cur.lastrowid)

    def content_exists(self, platform: str, campaign: str | None, content: str | None, scheduled_day: str) -> bool:
        with self.lock:
            row = self.conn.execute(
                """SELECT 1 FROM content_queue WHERE platform=? AND COALESCE(campaign,'')=COALESCE(?, '')
                   AND COALESCE(content,'')=COALESCE(?, '') AND substr(scheduled_for,1,10)=? LIMIT 1""",
                (platform, campaign, content, scheduled_day),
            ).fetchone()
        return bool(row)

    def due_content(self, now_iso: str, limit: int = 20):
        with self.lock:
            return self.conn.execute(
                "SELECT * FROM content_queue WHERE status='ready' AND scheduled_for<=? ORDER BY scheduled_for,id LIMIT ?",
                (now_iso, limit),
            ).fetchall()

    def content_queue(self, limit: int = 300):
        with self.lock:
            return self.conn.execute("SELECT * FROM content_queue ORDER BY id DESC LIMIT ?", (limit,)).fetchall()

    def update_content(self, content_id: int, **fields: Any) -> None:
        allowed = {
            "status", "provider_post_id", "provider_status", "external_url",
            "last_error", "scheduled_for", "performance",
        }
        pairs, values = [], []
        for key, value in fields.items():
            if key not in allowed:
                continue
            if key == "performance" and isinstance(value, dict):
                value = json.dumps(value)
            pairs.append(f"{key}=?")
            values.append(value)
        if not pairs:
            return
        values.append(content_id)
        with self.lock:
            self.conn.execute(f"UPDATE content_queue SET {','.join(pairs)} WHERE id=?", values)
            self.conn.commit()

    def upsert_acquisition_items(self, items: list[dict[str, Any]]) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self.lock:
            for item in items:
                self.conn.execute(
                    """INSERT INTO acquisition_queue(
                       remote_id,channel,placement,priority,status,destination,source,medium,campaign,content,notes,updated_at
                    ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
                    ON CONFLICT(remote_id) DO UPDATE SET
                       channel=excluded.channel,placement=excluded.placement,priority=excluded.priority,
                       status=excluded.status,destination=excluded.destination,source=excluded.source,
                       medium=excluded.medium,campaign=excluded.campaign,content=excluded.content,
                       notes=excluded.notes,updated_at=excluded.updated_at""",
                    (
                        int(item["id"]),
                        item.get("channel") or "Unknown",
                        item.get("placement"),
                        int(item.get("priority") or 50),
                        item.get("status") or "ready",
                        item.get("destination"),
                        item.get("source"),
                        item.get("medium"),
                        item.get("campaign"),
                        item.get("content"),
                        item.get("notes"),
                        now,
                    ),
                )
            self.conn.commit()

    def acquisition_items(self, limit: int = 300):
        with self.lock:
            return self.conn.execute(
                "SELECT * FROM acquisition_queue ORDER BY priority DESC, remote_id ASC LIMIT ?", (limit,)
            ).fetchall()

    def ai_calls_today(self) -> int:
        day = datetime.now(timezone.utc).date().isoformat()
        with self.lock:
            row = self.conn.execute(
                "SELECT COUNT(*) AS n FROM ai_usage WHERE substr(created_at,1,10)=? AND success=1", (day,)
            ).fetchone()
        return int(row["n"] if row else 0)

    def log_ai_usage(
        self,
        model: str,
        purpose: str,
        success: bool,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
        request_id: str | None = None,
        error: str | None = None,
    ) -> None:
        with self.lock:
            self.conn.execute(
                """INSERT INTO ai_usage(created_at,model,purpose,success,input_tokens,output_tokens,request_id,error)
                   VALUES(?,?,?,?,?,?,?,?)""",
                (
                    datetime.now(timezone.utc).isoformat(),
                    model,
                    purpose,
                    1 if success else 0,
                    input_tokens,
                    output_tokens,
                    request_id,
                    error,
                ),
            )
            self.conn.commit()

    def set_sync_state(self, key: str, value: str) -> None:
        with self.lock:
            self.conn.execute(
                "INSERT INTO sync_state(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (key, value),
            )
            self.conn.commit()

    def get_sync_state(self, key: str, default: str = "") -> str:
        with self.lock:
            row = self.conn.execute("SELECT value FROM sync_state WHERE key=?", (key,)).fetchone()
        return row["value"] if row else default
