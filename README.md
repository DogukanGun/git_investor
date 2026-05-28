# GitInvest

Tracks GitHub repos that are **rising fast but not yet mainstream** — the "famous but not the most famous" band — so you can spot the companies behind them and invest early.

Repos are ranked by a composite **emerging score** built from four signals:

- **Star velocity** — stars gained per day
- **Recency** — younger repos score higher
- **Contributor growth** — rising number of contributors
- **Company-backed** — owned by an org with a website/homepage
- **Funding** — venture-backed signal from free **SEC EDGAR Form D** filings. Favors early-stage: the boost decays as total raised grows (a company that's already raised big is past the "invest early" window). US issuers only, matched by company name, so coverage is partial.

## How it works

- **Discovery** uses the live GitHub Search API. Because that API caps at 1,000 results per query, the collector subdivides searches by **created-date windows × star bands** to enumerate all of GitHub without hitting the cap.
- **Snapshots** of star/fork/contributor counts are stored on every run, so velocity is computed from real deltas over time. On the first run there's no history, so velocity is bootstrapped as `stars / age_in_days` and gets more accurate as snapshots accumulate.
- A **daily scheduler** (APScheduler) refreshes the data; you can also trigger a refresh from the UI or CLI.

## Setup

### 1. Backend (Python 3.11+)

```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env        # then paste your GitHub token into .env
```

Get a token at https://github.com/settings/tokens — a classic token with
`public_repo` scope (or a fine-grained token with public-repo read) is enough.
Without a token you're limited to 60 requests/hour; with one, 5,000/hour.

Also set `SEC_USER_AGENT` in `.env` to a string containing your contact email
(e.g. `gitinvest you@example.com`). SEC's EDGAR archive returns **403** without
one — that's how funding lookups get the actual offering amounts.

### 2. Populate data

```bash
cd backend
.venv/bin/python collect.py          # uses default 500–15,000 star band
# or narrow it: .venv/bin/python collect.py 1000 30000
```

The first run takes a while (it walks ~2 years of date windows). Data lands in
`backend/gitinvest.db` (SQLite).

### 3. Run the API

```bash
cd backend
.venv/bin/uvicorn app.main:app --reload --port 8000
```

### 4. Run the dashboard

```bash
cd frontend
npm install
npm run dev      # http://localhost:5173
```

The Vite dev server proxies `/api` to the backend on port 8000.

## API

| Endpoint | Purpose |
| --- | --- |
| `GET /api/repos` | Ranked list. Filters: `min_stars`, `max_stars`, `language`, `topic`, `company_only`, `funded_only`, `q`, `sort` (incl. `funding_total`), `order`, `page`, `page_size` |
| `GET /api/repos/{id}` | Repo detail incl. org info |
| `GET /api/repos/{id}/history` | Snapshot series for the chart |
| `GET /api/languages` | Distinct languages seen (for the filter dropdown) |
| `POST /api/refresh` | Trigger a collection run in the background |
| `GET/POST/DELETE /api/watchlist[/{id}]` | Manage the watchlist |

## Configuration

All defaults live in `backend/app/config.py` and can be overridden via `.env`
(star band, date-window size, score weights, refresh hour, enrichment cap).

## Notes / not in v1

- Funding is from SEC EDGAR Form D (free, real, but US-only and name-matched, so partial coverage). Non-US raises, SAFEs that weren't filed, or filings under a different legal name won't match.
- SQLite for now; point `DATABASE_URL` at Postgres if data volume grows.
