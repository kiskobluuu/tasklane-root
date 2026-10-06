# BetweenPay Sales OS

BetweenPay Sales OS is the standalone Windows marketing-and-sales machine for BetweenPay. It runs continuously on the owner's PC, uses real funnel data, publishes through authorized APIs, scores experiments, learns from results, and keeps working toward a measurable sales target without requiring a ChatGPT conversation to stay open.

## North-star objective

**100 legitimate completed BetweenPay sales in a rolling 7-day window.** At the current $12.99 product price that is approximately $1,299 gross revenue per 100 sales. The target is an operating objective, not a guarantee.

The engine follows a closed loop:

**Observe → Diagnose → Decide → Act → Measure → Learn → Repeat**

## Version 1.0 capabilities

- Windows desktop command center built with PySide6.
- Runs continuously in the Windows system tray.
- Optional start-at-login support.
- Pulls live BetweenPay funnel, order, lead and referral data from Supabase.
- Calculates rolling 7-day and 24-hour sales/funnel performance. Checkout-start and purchase-rate dashboard percentages use unique measured sessions so repeated checkout events do not inflate conversion.
- Scores traffic sources and campaign/content experiments.
- Protects small samples from premature winner/loser decisions.
- Syncs the existing BetweenPay social queue into the desktop program.
- Publishes due Facebook, X and Pinterest content through Buffer's API.
- Reconciles Buffer post status back into the local queue.
- Updates the original Supabase social queue after provider confirmation.
- Uses permanent BetweenPay campaign image URLs, avoiding browser file-picker automation.
- Generates new campaign variants with the OpenAI Responses API when an API key and daily AI budget are available.
- Falls back to built-in campaign templates when AI is unavailable or the daily AI-call limit is reached.
- Stores API keys/tokens in Windows Credential Manager via keyring; secrets are not stored in source code or SQLite.
- Keeps a local action log, experiment history, content queue and performance snapshots.
- Includes an MCP bridge so an MCP-capable client can inspect status, run the engine, view experiments/actions, and change the weekly goal/autopilot setting without receiving platform credentials.
- Includes a GitHub Actions Windows build workflow that produces BetweenPaySalesOS.exe as an artifact.

## Autonomous boundaries

Autopilot may autonomously create and rotate organic campaign variants, queue and publish organic social content through connected channels, choose product-first/contest-first/free-calculator/education/credibility angles, learn from UTM-tagged results, and increase emphasis on measured winners while retaining exploration.

Autopilot does **not** autonomously change the product price, contest prizes or Official Rules, refund policy, payment configuration, core product functionality, paid advertising/spend, platform credentials, or create deceptive/fake engagement.

## One-time connection setup

Open **Connections** in the Windows app and enter each credential once:

1. **Supabase service-role key** for the existing BetweenPay project. The project URL is prefilled.
2. **Buffer API access token** for the Buffer workspace that holds the authorized Facebook/X/Pinterest channels.
3. **OpenAI API key** for autonomous campaign ideation. This is optional; the daily call cap defaults to 6 and can be changed in Settings. The default model is `gpt-6-luna`, selected to keep routine strategy generation inexpensive; you can change the model in Settings.
4. **GitHub token** is optional and reserved for future direct repository/site publishing from the desktop app. ChatGPT can already maintain this source through the connected GitHub app.

All entered secrets go to Windows Credential Manager.

After saving credentials, click **Test Connections**. Supabase and Buffer are tested live, and the OpenAI key is validated against the API without generating paid output. Buffer should report facebook, twitter and pinterest once all three channels are connected. Pinterest also needs a board containing the word BetweenPay by default; this can be changed in Settings.

## Run from source on Windows

Install Python 3.12+ and double-click:

run_windows.bat

The script creates .venv, installs dependencies and starts the app.

## Build the Windows EXE locally

Double-click:

build_windows.bat

The build runs tests first, then creates:

dist\BetweenPaySalesOS.exe

## Automatic GitHub build

The repository workflow .github/workflows/build-betweenpay-sales-os.yml runs tests and builds the Windows executable when Sales OS source changes. The finished executable is uploaded as the workflow artifact **BetweenPaySalesOS-Windows**.

## ChatGPT / MCP bridge

For a local MCP-capable client, run:

run_mcp_bridge.bat

or:

python -m sales_os.mcp_server

Exposed MCP tools intentionally do not return API keys or platform credentials. A remote ChatGPT connection should use a secured relay or approved plugin/connector rather than exposing the Windows machine directly to the public internet.

## Local data

App state:
%USERPROFILE%\BetweenPaySalesOS\sales_os.db

Logs:
%USERPROFILE%\BetweenPaySalesOS\logs\sales_os.log

Credentials:
Windows Credential Manager, service name BetweenPaySalesOS.
