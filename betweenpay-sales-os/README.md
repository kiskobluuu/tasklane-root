# BetweenPay Sales OS

A standalone Windows marketing and sales operations program for BetweenPay.

## North-star goal
- 100 legitimate completed sales in a rolling 7-day window.
- Current product price assumption: $12.99.
- The program should diagnose the sales gap, choose actions, execute allowed actions, measure results, learn, and repeat.

## Architecture
- Windows desktop app: PySide6 dashboard.
- Background engine: APScheduler + Python decision loop.
- Credential vault: Windows Credential Manager via keyring.
- Local state: SQLite.
- Existing BetweenPay data: Supabase/API connector.
- Social publishing: Buffer API adapter for Facebook, X and Pinterest.
- AI strategy: optional OpenAI API adapter for unattended reasoning.
- ChatGPT connection: MCP bridge module, intended to be exposed through a secure remote endpoint later.
- GitHub: source/version control and update channel.

## Safety / operating boundaries
The autonomous engine may change organic content, scheduling, channels, CTAs, experiments, SEO/content priorities, directory outreach and nurture tactics.

It must NOT autonomously change:
- product price
- contest prizes
- Official Rules
- refund/payment configuration
- product functionality
- paid advertising/spend

## Credentials
Secrets are never stored in source code or SQLite. On Windows, the Settings screen stores them in Windows Credential Manager through `keyring`.

## Run
1. Install Python 3.12+.
2. Run `run_windows.bat`.
3. Open Settings and enter the required API credentials once.
4. Connect social accounts to Buffer once.
5. Turn on Autopilot when the channels show healthy.

## Build EXE
Run `build_windows.bat`.

This project is intentionally isolated from the public BetweenPay website code even though it currently lives in the same Git repository. It can be moved to its own repository later without architectural changes.
