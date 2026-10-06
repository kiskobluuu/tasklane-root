from __future__ import annotations

import json

from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QFormLayout, QGridLayout, QGroupBox, QHBoxLayout,
    QHeaderView, QLabel, QLineEdit, QMainWindow, QMessageBox, QProgressBar,
    QPushButton, QSpinBox, QSystemTrayIcon, QTabWidget, QTableWidget,
    QTableWidgetItem, QTextEdit, QVBoxLayout, QWidget, QMenu,
)

from .config import APP_NAME, APP_VERSION
from .connectors import BufferPublisher, SupabaseConnector
from .startup import set_run_on_startup
from .vault import get_secret, set_secret

CARD = "QGroupBox{border:1px solid #dce7ec;border-radius:12px;margin-top:8px;padding:14px;background:white;}"
PRIMARY = "QPushButton{background:#0b3248;color:white;padding:9px 14px;border-radius:8px;font-weight:700;} QPushButton:hover{background:#124a69;}"


class MainWindow(QMainWindow):
    def __init__(self, store, engine, scheduler, start_minimized: bool = False):
        super().__init__()
        self.store, self.engine, self.scheduler = store, engine, scheduler
        self.setWindowTitle(f"{APP_NAME} {APP_VERSION}")
        self.resize(1260, 820)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._dashboard(), "Command Center")
        self.tabs.addTab(self._queue_tab(), "Content Queue")
        self.tabs.addTab(self._acquisition_tab(), "Acquisition Channels")
        self.tabs.addTab(self._experiments_tab(), "Experiments")
        self.tabs.addTab(self._actions_tab(), "Activity & Learning")
        self.tabs.addTab(self._connections_tab(), "Connections")
        self.tabs.addTab(self._settings_tab(), "Settings")
        self.setCentralWidget(self.tabs)
        self._setup_tray()
        self.refresh()

        from PySide6.QtCore import QTimer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(15000)
        if start_minimized:
            QTimer.singleShot(200, self.hide)

    def _setup_tray(self) -> None:
        self.tray = QSystemTrayIcon(self)
        self.tray.setToolTip(APP_NAME)
        menu = QMenu()
        show_action = QAction("Open BetweenPay Sales OS", self)
        show_action.triggered.connect(self._show_from_tray)
        run_action = QAction("Run engine now", self)
        run_action.triggered.connect(self.run_engine)
        quit_action = QAction("Exit", self)
        quit_action.triggered.connect(QApplication.instance().quit)
        menu.addAction(show_action)
        menu.addAction(run_action)
        menu.addSeparator()
        menu.addAction(quit_action)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(
            lambda reason: self._show_from_tray() if reason == QSystemTrayIcon.Trigger else None
        )
        self.tray.show()

    def closeEvent(self, event):
        event.ignore()
        self.hide()
        self.tray.showMessage(APP_NAME, "Still running in the background.", QSystemTrayIcon.Information, 2500)

    def _show_from_tray(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def _metric_card(self, title: str, name: str) -> QGroupBox:
        box = QGroupBox()
        box.setStyleSheet(CARD)
        lay = QVBoxLayout(box)
        t = QLabel(title)
        t.setStyleSheet("color:#647b87;font-size:11px;font-weight:700")
        v = QLabel("—")
        v.setObjectName(name)
        v.setStyleSheet("font-size:27px;font-weight:900;color:#0b3248")
        lay.addWidget(t)
        lay.addWidget(v)
        return box

    def _dashboard(self):
        w = QWidget()
        root = QVBoxLayout(w)
        title = QLabel("BetweenPay Sales OS")
        title.setStyleSheet("font-size:30px;font-weight:900;color:#0b3248")
        self.goal_label = QLabel("Autonomous goal: 100 legitimate completed sales in a rolling 7-day window.")
        self.goal_label.setStyleSheet("color:#5c7280;font-size:13px")
        root.addWidget(title)
        root.addWidget(self.goal_label)

        grid = QGridLayout()
        cards = [
            ("7-DAY SALES", "sales7"),
            ("WEEKLY TARGET", "target"),
            ("GAP TO TARGET", "gap"),
            ("7-DAY REVENUE", "revenue7"),
            ("MEASURED SESSIONS", "sessions7"),
            ("CHECKOUT START RATE", "checkoutRate"),
            ("PURCHASE RATE", "purchaseRate"),
            ("QUALIFIED REFERRALS", "referrals7"),
        ]
        for idx, pair in enumerate(cards):
            grid.addWidget(self._metric_card(pair[0], pair[1]), idx // 4, idx % 4)
        root.addLayout(grid)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setFormat("%p% of weekly goal")
        self.progress.setMinimumHeight(26)
        root.addWidget(self.progress)

        decision_box = QGroupBox("Current diagnosis")
        decision_box.setStyleSheet(CARD)
        dl = QVBoxLayout(decision_box)
        self.constraint = QLabel("Waiting for a live data cycle.")
        self.constraint.setStyleSheet("font-weight:800;color:#0b3248")
        self.diagnosis = QLabel("")
        self.diagnosis.setWordWrap(True)
        self.recommended = QLabel("")
        self.recommended.setWordWrap(True)
        dl.addWidget(self.constraint)
        dl.addWidget(self.diagnosis)
        dl.addWidget(self.recommended)
        root.addWidget(decision_box)

        controls = QHBoxLayout()
        self.autopilot_badge = QLabel("AUTOPILOT OFF")
        self.autopilot_badge.setStyleSheet(
            "padding:7px 10px;border-radius:8px;background:#f0e4e4;color:#8b3232;font-weight:900"
        )
        run = QPushButton("Run Engine Now")
        run.setStyleSheet(PRIMARY)
        run.clicked.connect(self.run_engine)
        pub = QPushButton("Publish Due Queue Now")
        pub.clicked.connect(self.publish_now)
        controls.addWidget(self.autopilot_badge)
        controls.addStretch()
        controls.addWidget(pub)
        controls.addWidget(run)
        root.addLayout(controls)
        return w

    def _queue_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        self.queue_table = QTableWidget(0, 9)
        self.queue_table.setHorizontalHeaderLabels(
            ["Due", "Platform", "Theme", "Angle", "Campaign", "Content", "Status", "Provider", "Last error"]
        )
        self.queue_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.queue_table.horizontalHeader().setStretchLastSection(True)
        lay.addWidget(self.queue_table)
        return w

    def _acquisition_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        info = QLabel(
            "This is the full BetweenPay acquisition backlog, including SEO, directories, social, "
            "product/community placements and editorial outreach. Status is synchronized from Supabase."
        )
        info.setWordWrap(True)
        lay.addWidget(info)
        self.acq_table = QTableWidget(0, 8)
        self.acq_table.setHorizontalHeaderLabels(
            ["Priority", "Channel", "Placement", "Status", "Campaign", "Source", "Destination", "Notes"]
        )
        self.acq_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.acq_table.horizontalHeader().setStretchLastSection(True)
        lay.addWidget(self.acq_table)
        return w

    def _experiments_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        info = QLabel(
            "Experiments are ranked from measured sessions, checkout starts, purchases and revenue. "
            "Small samples are discounted."
        )
        info.setWordWrap(True)
        lay.addWidget(info)
        self.exp_table = QTableWidget(0, 9)
        self.exp_table.setHorizontalHeaderLabels(
            ["Channel", "Angle/content", "Status", "Sessions", "Checkout starts", "Purchases", "Revenue", "Score", "Experiment"]
        )
        self.exp_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.exp_table.horizontalHeader().setStretchLastSection(True)
        lay.addWidget(self.exp_table)
        return w

    def _actions_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        self.actions_table = QTableWidget(0, 6)
        self.actions_table.setHorizontalHeaderLabels(
            ["Time", "Type", "Channel", "Status", "Experiment", "Rationale"]
        )
        self.actions_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.actions_table.horizontalHeader().setStretchLastSection(True)
        lay.addWidget(self.actions_table)
        return w

    def _secret_line(self, name: str, placeholder: str) -> QLineEdit:
        field = QLineEdit()
        field.setEchoMode(QLineEdit.Password)
        field.setPlaceholderText(
            "Stored securely in Windows Credential Manager" if get_secret(name) else placeholder
        )
        return field

    def _connections_tab(self):
        w = QWidget()
        root = QVBoxLayout(w)
        form = QFormLayout()
        self.supabase_url = QLineEdit(self.store.get("supabase_url"))
        self.supabase_key = self._secret_line(
            "supabase_service_role_key", "Paste Supabase service-role key once"
        )
        self.buffer_token = self._secret_line(
            "buffer_api_token", "Paste Buffer API access token once"
        )
        self.openai_key = self._secret_line(
            "openai_api_key", "Paste OpenAI API key once"
        )
        self.github_token = self._secret_line(
            "github_token", "Optional GitHub fine-grained/PAT token"
        )
        form.addRow("Supabase project URL", self.supabase_url)
        form.addRow("Supabase service-role key", self.supabase_key)
        form.addRow("Buffer API token", self.buffer_token)
        form.addRow("OpenAI API key", self.openai_key)
        form.addRow("GitHub token (optional)", self.github_token)
        root.addLayout(form)

        buttons = QHBoxLayout()
        save = QPushButton("Save Credentials")
        save.setStyleSheet(PRIMARY)
        save.clicked.connect(self.save_connections)
        test = QPushButton("Test Connections")
        test.clicked.connect(self.test_connections)
        buttons.addWidget(save)
        buttons.addWidget(test)
        buttons.addStretch()
        root.addLayout(buttons)

        self.connection_status = QTextEdit()
        self.connection_status.setReadOnly(True)
        self.connection_status.setMaximumHeight(220)
        root.addWidget(self.connection_status)

        note = QLabel(
            "Credentials are stored by Windows Credential Manager, not in the GitHub repository or local SQLite database. "
            "The Supabase service-role key is powerful; use this app only on a Windows account you control."
        )
        note.setWordWrap(True)
        note.setStyleSheet("color:#6a7e89")
        root.addWidget(note)
        root.addStretch()
        return w

    def _settings_tab(self):
        w = QWidget()
        root = QVBoxLayout(w)
        form = QFormLayout()

        self.target_spin = QSpinBox()
        self.target_spin.setRange(1, 100000)
        self.target_spin.setValue(self.store.get_int("weekly_sales_target", 100))

        self.post_cap = QSpinBox()
        self.post_cap.setRange(1, 30)
        self.post_cap.setValue(self.store.get_int("daily_post_cap", 6))

        self.engine_interval = QSpinBox()
        self.engine_interval.setRange(10, 1440)
        self.engine_interval.setValue(self.store.get_int("engine_interval_minutes", 30))

        self.publish_interval = QSpinBox()
        self.publish_interval.setRange(5, 1440)
        self.publish_interval.setValue(self.store.get_int("publish_interval_minutes", 10))

        self.ai_limit = QSpinBox()
        self.ai_limit.setRange(0, 100)
        self.ai_limit.setValue(self.store.get_int("openai_daily_call_limit", 6))

        self.ai_model = QLineEdit(self.store.get("openai_model", "gpt-5.6-luna"))
        self.board_name = QLineEdit(self.store.get("pinterest_board_name", "BetweenPay"))

        self.autopilot = QCheckBox("Enable autonomous execution")
        self.autopilot.setChecked(self.store.get_bool("autopilot_enabled"))

        self.run_startup = QCheckBox(
            "Start BetweenPay Sales OS automatically when I sign into Windows"
        )
        self.run_startup.setChecked(self.store.get_bool("run_on_startup"))

        form.addRow("Rolling 7-day sales target", self.target_spin)
        form.addRow("Daily organic post cap", self.post_cap)
        form.addRow("Strategy cycle (minutes)", self.engine_interval)
        form.addRow("Publishing cycle (minutes)", self.publish_interval)
        form.addRow("OpenAI calls/day limit", self.ai_limit)
        form.addRow("OpenAI model", self.ai_model)
        form.addRow("Pinterest board contains", self.board_name)
        form.addRow("", self.autopilot)
        form.addRow("", self.run_startup)
        root.addLayout(form)

        save = QPushButton("Save Operating Settings")
        save.setStyleSheet(PRIMARY)
        save.clicked.connect(self.save_settings)
        root.addWidget(save)

        help_label = QLabel(
            "Autopilot can create, queue and publish organic content and learn from performance. "
            "It does not change product price, contest prizes/rules, payment settings, refunds, "
            "product functionality, or paid ad spend."
        )
        help_label.setWordWrap(True)
        root.addWidget(help_label)
        root.addStretch()
        return w

    def save_connections(self):
        self.store.set("supabase_url", self.supabase_url.text().strip())
        secrets = {
            "supabase_service_role_key": self.supabase_key,
            "buffer_api_token": self.buffer_token,
            "openai_api_key": self.openai_key,
            "github_token": self.github_token,
        }
        for name, field in secrets.items():
            if field.text().strip():
                set_secret(name, field.text().strip())
                field.clear()
                field.setPlaceholderText("Stored securely in Windows Credential Manager")
        QMessageBox.information(self, "Saved", "Connection credentials were saved securely.")

    def test_connections(self):
        lines = []
        supa = SupabaseConnector(self.store).test_connection()
        lines.append(("OK " if supa.get("ok") else "ERROR ") + "Supabase: " + supa.get("message", ""))

        buf = BufferPublisher(self.store).test_connection()
        lines.append(("OK " if buf.get("ok") else "ERROR ") + "Buffer: " + buf.get("message", ""))
        if buf.get("ok"):
            lines.append(
                "  Channels: "
                + ", ".join(buf.get("channels") or [])
                + " (Facebook/X/Pinterest should all appear when fully connected)"
            )

        lines.append(
            ("OK " if get_secret("openai_api_key") else "INFO ")
            + "OpenAI API key: "
            + ("stored" if get_secret("openai_api_key") else "not configured; built-in templates will be used")
        )
        lines.append(
            ("OK " if get_secret("github_token") else "INFO ")
            + "GitHub runtime token: "
            + ("stored" if get_secret("github_token") else "optional/not configured")
        )
        self.connection_status.setPlainText("\n".join(lines))

    def save_settings(self):
        self.store.set("weekly_sales_target", self.target_spin.value())
        self.store.set("daily_post_cap", self.post_cap.value())
        self.store.set("engine_interval_minutes", self.engine_interval.value())
        self.store.set("publish_interval_minutes", self.publish_interval.value())
        self.store.set("openai_daily_call_limit", self.ai_limit.value())
        self.store.set("openai_model", self.ai_model.text().strip() or "gpt-5.6-luna")
        self.store.set("pinterest_board_name", self.board_name.text().strip() or "BetweenPay")
        self.store.set("autopilot_enabled", "1" if self.autopilot.isChecked() else "0")
        self.store.set("run_on_startup", "1" if self.run_startup.isChecked() else "0")
        set_run_on_startup(self.run_startup.isChecked())
        self.scheduler.reschedule()
        QMessageBox.information(self, "Saved", "Operating settings updated.")
        self.refresh()

    def run_engine(self):
        try:
            result = self.engine.run_once()
            self.refresh()
            QMessageBox.information(
                self,
                "Sales engine completed",
                f"Constraint: {result.primary_constraint}\n\n{result.diagnosis}\n\nNext: {result.recommended_action}",
            )
        except Exception as exc:
            QMessageBox.critical(self, "Engine error", str(exc))

    def publish_now(self):
        try:
            result = self.engine.publish_due()
            self.refresh()
            QMessageBox.information(self, "Publishing cycle", json.dumps(result, indent=2))
        except Exception as exc:
            QMessageBox.critical(self, "Publishing error", str(exc))

    def _set(self, name: str, value: str):
        label = self.findChild(QLabel, name)
        if label:
            label.setText(value)

    def refresh(self):
        target = self.store.get_int("weekly_sales_target", 100)
        self.goal_label.setText(
            f"Autonomous goal: {target} legitimate completed sales in a rolling 7-day window."
        )
        self._set("target", str(target))
        snap = self.store.latest_snapshot()
        sales = int(snap["sales_7d"]) if snap else 0
        self._set("sales7", str(sales))
        self._set("gap", str(max(0, target - sales)))
        revenue_text = "$" + (f"{float(snap['revenue_7d']):,.2f}" if snap else "0.00")
        self._set("revenue7", revenue_text)
        self._set("sessions7", str(int(snap["sessions_7d"])) if snap else "0")

        if snap:
            sessions = int(snap["sessions_7d"])
            checkouts = int(snap["checkout_starts_7d"])
            self._set("checkoutRate", f"{(checkouts/sessions if sessions else 0):.1%}")
            self._set("purchaseRate", f"{(sales/sessions if sessions else 0):.1%}")
            self._set("referrals7", str(int(snap["qualified_referrals_7d"])))
        else:
            self._set("checkoutRate", "0.0%")
            self._set("purchaseRate", "0.0%")
            self._set("referrals7", "0")

        self.progress.setValue(min(100, int((sales / target) * 100)) if target else 0)

        if self.engine.last_decision:
            d = self.engine.last_decision
            self.constraint.setText(
                f"Primary constraint: {d.primary_constraint.replace('_',' ').title()} — {d.urgency.upper()}"
            )
            self.diagnosis.setText(d.diagnosis)
            self.recommended.setText("Next action: " + d.recommended_action)
        elif snap:
            self.constraint.setText("Live metrics loaded. Run the engine to refresh the diagnosis.")

        on = self.store.get_bool("autopilot_enabled")
        self.autopilot_badge.setText("AUTOPILOT ON" if on else "AUTOPILOT OFF")
        self.autopilot_badge.setStyleSheet(
            "padding:7px 10px;border-radius:8px;font-weight:900;"
            + ("background:#dff3eb;color:#146e58" if on else "background:#f0e4e4;color:#8b3232")
        )
        self.refresh_queue()
        self.refresh_acquisition()
        self.refresh_experiments()
        self.refresh_actions()

    def refresh_queue(self):
        rows = self.store.content_queue(250)
        self.queue_table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            vals = [
                str(row["scheduled_for"])[:16].replace("T", " "),
                row["platform"], row["theme"], row["growth_angle"] or "",
                row["campaign"] or "", row["content"] or "", row["status"],
                row["provider"] or "", row["last_error"] or "",
            ]
            for j, value in enumerate(vals):
                self.queue_table.setItem(i, j, QTableWidgetItem(str(value)))

    def refresh_acquisition(self):
        rows = self.store.acquisition_items(300)
        self.acq_table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            vals = [
                row["priority"], row["channel"], row["placement"] or "", row["status"],
                row["campaign"] or "", row["source"] or "", row["destination"] or "", row["notes"] or "",
            ]
            for j, value in enumerate(vals):
                self.acq_table.setItem(i, j, QTableWidgetItem(str(value)))

    def refresh_experiments(self):
        rows = self.store.experiments(limit=250)
        self.exp_table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            revenue = "$" + f"{float(row['revenue']):,.2f}"
            vals = [
                row["channel"], row["angle"], row["status"], row["sessions"],
                row["checkout_starts"], row["purchases"], revenue,
                f"{float(row['score'] or 0):.1f}", row["experiment_key"],
            ]
            for j, value in enumerate(vals):
                self.exp_table.setItem(i, j, QTableWidgetItem(str(value)))

    def refresh_actions(self):
        rows = self.store.recent_actions(250)
        self.actions_table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            vals = [
                str(row["created_at"])[:19].replace("T", " "),
                row["action_type"], row["channel"] or "", row["status"],
                row["experiment_key"] or "", row["rationale"],
            ]
            for j, value in enumerate(vals):
                self.actions_table.setItem(i, j, QTableWidgetItem(str(value)))
