from __future__ import annotations
import json, sqlite3
from pathlib import Path
from datetime import datetime, timezone

APP_DIR = Path.home() / "BetweenPaySalesOS"
DB_PATH = APP_DIR / "sales_os.db"

class Store:
    def __init__(self):
        APP_DIR.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init()

    def _init(self):
        self.conn.executescript("""
        create table if not exists settings(
          key text primary key,
          value text not null
        );
        create table if not exists actions(
          id integer primary key autoincrement,
          created_at text not null,
          action_type text not null,
          channel text,
          rationale text not null,
          payload text not null default '{}',
          status text not null default 'planned',
          result text not null default '{}'
        );
        create table if not exists snapshots(
          id integer primary key autoincrement,
          captured_at text not null,
          sales_7d integer not null default 0,
          revenue_7d real not null default 0,
          sessions_7d integer not null default 0,
          checkout_starts_7d integer not null default 0,
          data text not null default '{}'
        );
        """)
        self.conn.commit()
        self.set_default("weekly_sales_target", "100")
        self.set_default("product_price", "12.99")
        self.set_default("autopilot_enabled", "0")
        self.set_default("engine_interval_minutes", "30")
        self.set_default("supabase_metrics_url", "")
        self.set_default("buffer_api_url", "https://api.buffer.com")

    def set_default(self, key, value):
        self.conn.execute("insert or ignore into settings(key,value) values(?,?)", (key, value))
        self.conn.commit()

    def get(self, key, default=""):
        row = self.conn.execute("select value from settings where key=?", (key,)).fetchone()
        return row["value"] if row else default

    def set(self, key, value):
        self.conn.execute(
            "insert into settings(key,value) values(?,?) on conflict(key) do update set value=excluded.value",
            (key, str(value)),
        )
        self.conn.commit()

    def log_action(self, action_type, rationale, channel=None, payload=None, status="planned"):
        self.conn.execute(
            "insert into actions(created_at,action_type,channel,rationale,payload,status) values(?,?,?,?,?,?)",
            (datetime.now(timezone.utc).isoformat(), action_type, channel, rationale, json.dumps(payload or {}), status),
        )
        self.conn.commit()

    def recent_actions(self, limit=100):
        return self.conn.execute("select * from actions order by id desc limit ?", (limit,)).fetchall()

    def save_snapshot(self, sales_7d, revenue_7d, sessions_7d, checkout_starts_7d, data):
        self.conn.execute(
            "insert into snapshots(captured_at,sales_7d,revenue_7d,sessions_7d,checkout_starts_7d,data) values(?,?,?,?,?,?)",
            (datetime.now(timezone.utc).isoformat(), sales_7d, revenue_7d, sessions_7d, checkout_starts_7d, json.dumps(data)),
        )
        self.conn.commit()

    def latest_snapshot(self):
        return self.conn.execute("select * from snapshots order by id desc limit 1").fetchone()
