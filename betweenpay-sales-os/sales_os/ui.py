from __future__ import annotations
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTabWidget, QFormLayout, QLineEdit, QCheckBox, QTableWidget,
    QTableWidgetItem, QMessageBox, QGroupBox, QGridLayout
)
from .vault import set_secret, get_secret

CARD = "QGroupBox{border:1px solid #dce7ec;border-radius:12px;margin-top:8px;padding:14px;background:white;}"

class MainWindow(QMainWindow):
    def __init__(self, store, engine):
        super().__init__()
        self.store, self.engine = store, engine
        self.setWindowTitle("BetweenPay Sales OS")
        tabs = QTabWidget()
        tabs.addTab(self._dashboard(), "Command Center")
        tabs.addTab(self._actions(), "Actions & Learning")
        tabs.addTab(self._settings(), "Connections & Settings")
        self.setCentralWidget(tabs)
        self.refresh()

    def _metric_card(self, title, name):
        box=QGroupBox(); box.setStyleSheet(CARD)
        lay=QVBoxLayout(box)
        t=QLabel(title); t.setStyleSheet("color:#647b87;font-size:12px;font-weight:700")
        v=QLabel("—"); v.setObjectName(name); v.setStyleSheet("font-size:28px;font-weight:900;color:#0b3248")
        lay.addWidget(t); lay.addWidget(v)
        return box

    def _dashboard(self):
        w=QWidget(); root=QVBoxLayout(w)
        title=QLabel("BetweenPay Sales OS"); title.setStyleSheet("font-size:30px;font-weight:900;color:#0b3248")
        sub=QLabel("North star: 100 legitimate completed sales in a rolling 7-day window.")
        root.addWidget(title); root.addWidget(sub)
        grid=QGridLayout()
        grid.addWidget(self._metric_card("7-DAY SALES","sales7"),0,0)
        grid.addWidget(self._metric_card("WEEKLY TARGET","target"),0,1)
        grid.addWidget(self._metric_card("GAP TO TARGET","gap"),0,2)
        grid.addWidget(self._metric_card("REQUIRED DAILY PACE","pace"),0,3)
        root.addLayout(grid)
        self.diagnosis=QLabel("Engine has not run yet."); self.diagnosis.setWordWrap(True)
        self.action=QLabel(""); self.action.setWordWrap(True)
        self.run_btn=QPushButton("Run Sales Engine Now"); self.run_btn.clicked.connect(self.run_engine)
        root.addWidget(self.diagnosis); root.addWidget(self.action); root.addWidget(self.run_btn)
        root.addStretch()
        return w

    def _actions(self):
        w=QWidget(); lay=QVBoxLayout(w)
        self.actions_table=QTableWidget(0,5)
        self.actions_table.setHorizontalHeaderLabels(["Time","Type","Channel","Status","Rationale"])
        self.actions_table.horizontalHeader().setStretchLastSection(True)
        lay.addWidget(self.actions_table)
        return w

    def _settings(self):
        w=QWidget(); lay=QVBoxLayout(w)
        form=QFormLayout()
        self.metrics_url=QLineEdit(self.store.get("supabase_metrics_url",""))
        self.buffer_token=QLineEdit(); self.buffer_token.setEchoMode(QLineEdit.Password)
        self.buffer_token.setPlaceholderText("Stored securely" if get_secret("buffer_api_token") else "Enter Buffer API token")
        self.bp_token=QLineEdit(); self.bp_token.setEchoMode(QLineEdit.Password)
        self.bp_token.setPlaceholderText("Stored securely" if get_secret("betweenpay_api_token") else "Enter BetweenPay API token")
        self.openai_key=QLineEdit(); self.openai_key.setEchoMode(QLineEdit.Password)
        self.openai_key.setPlaceholderText("Optional: enables unattended AI strategy")
        self.autopilot=QCheckBox("Enable autonomous execution when connectors are healthy")
        self.autopilot.setChecked(self.store.get("autopilot_enabled","0")=="1")
        form.addRow("BetweenPay metrics endpoint",self.metrics_url)
        form.addRow("Buffer API token",self.buffer_token)
        form.addRow("BetweenPay access token",self.bp_token)
        form.addRow("OpenAI API key",self.openai_key)
        form.addRow("",self.autopilot)
        save=QPushButton("Save Settings"); save.clicked.connect(self.save_settings)
        lay.addLayout(form); lay.addWidget(save); lay.addStretch()
        return w

    def save_settings(self):
        self.store.set("supabase_metrics_url", self.metrics_url.text().strip())
        self.store.set("autopilot_enabled","1" if self.autopilot.isChecked() else "0")
        if self.buffer_token.text().strip(): set_secret("buffer_api_token",self.buffer_token.text().strip())
        if self.bp_token.text().strip(): set_secret("betweenpay_api_token",self.bp_token.text().strip())
        if self.openai_key.text().strip(): set_secret("openai_api_key",self.openai_key.text().strip())
        self.buffer_token.clear(); self.bp_token.clear(); self.openai_key.clear()
        QMessageBox.information(self,"Saved","Settings saved. Secrets are stored in Windows Credential Manager.")

    def run_engine(self):
        try:
            r=self.engine.run_once()
            self._set("sales7",str(r.sales_7d)); self._set("target",str(r.target)); self._set("gap",str(r.gap))
            self._set("pace",f"{r.required_per_day:.1f}/day")
            self.diagnosis.setText("Diagnosis: "+r.diagnosis)
            self.action.setText("Next action: "+r.action)
            self.refresh_actions()
        except Exception as e:
            QMessageBox.critical(self,"Engine error",str(e))

    def _set(self,name,value):
        x=self.findChild(QLabel,name)
        if x: x.setText(value)

    def refresh_actions(self):
        rows=self.store.recent_actions(100); self.actions_table.setRowCount(len(rows))
        for i,r in enumerate(rows):
            vals=[r["created_at"],r["action_type"],r["channel"] or "",r["status"],r["rationale"]]
            for j,v in enumerate(vals): self.actions_table.setItem(i,j,QTableWidgetItem(str(v)))

    def refresh(self):
        target=int(self.store.get("weekly_sales_target","100"))
        self._set("target",str(target))
        s=self.store.latest_snapshot()
        if s:
            sales=int(s["sales_7d"]); gap=max(0,target-sales)
            self._set("sales7",str(sales)); self._set("gap",str(gap)); self._set("pace",f"{gap/7:.1f}/day")
        self.refresh_actions()
