# Creator Revenue Toolkit

An open-source, single-file web app that helps content creators **earn more
revenue, decrease costs, and expand** their business. No accounts, no tracking,
no backend — all data lives in your browser's localStorage and can be exported
or imported as JSON.

## What it does

| Tab | Lever | What you get |
|---|---|---|
| **Dashboard** | overview | Stat tiles (revenue, costs, profit, diversification score), revenue-mix breakdown, and auto-generated recommendations computed from your data |
| **Sponsorship rates** | earn more | A rate card built from your reach + engagement against 2025–26 CPM benchmarks for YouTube, TikTok, Instagram, Podcast, Newsletter, and Twitch — with usage-rights / exclusivity / rush add-ons and a negotiation checklist |
| **Revenue streams** | earn more | Track every income source, get a diversification score (effective-streams / Herfindahl), and see which high-payoff streams you're missing |
| **Expenses** | decrease costs | Expense tracker with an automated audit: cost-to-revenue ratio flags, overlapping-subscription detection, non-essential spend annualized, annual-billing savings estimate |
| **Growth planner** | expand | 12-month compound revenue projection from your audience growth and revenue-per-1k, plus an expansion playbook |

The dashboard cross-references everything — e.g. it flags when your reported
sponsorship income is lower than what a *single* deal at your reach should pay.

## Run it

Open `index.html` in any browser. That's it — no build step, no dependencies.

To try it instantly, click **Load sample data** in the header.

```bash
# or serve it locally
python3 -m http.server 8000
# → http://localhost:8000
```

## Project layout

```
creator-revenue-toolkit/
├── index.html        # the entire app (HTML + CSS + vanilla JS)
├── docs/
│   └── playbook.md   # the written playbook behind the numbers
└── README.md
```

## Data & privacy

- State persists to `localStorage` under the key `crt-state-v1`.
- **Export JSON** downloads a backup; **Import JSON** restores it.
- Nothing ever leaves your machine.

## Benchmarks

Rate benchmarks are 2025–26 industry ranges for host-read / integrated sponsored
content and are documented (with sources of adjustment: engagement multiplier,
usage rights +25%, exclusivity +20%, rush +15%) in
[`docs/playbook.md`](docs/playbook.md). They are starting points for
negotiation, not guarantees — always price against your own niche and demand.

## Splitting this into its own repository

This project is self-contained. To extract it:

```bash
git subtree split --prefix=creator-revenue-toolkit -b creator-toolkit-only
# then push that branch to a fresh empty repo:
git push <new-repo-url> creator-toolkit-only:main
```

## License

MIT
