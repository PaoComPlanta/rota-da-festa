# Copilot Instructions — Rota da Festa

## Project Overview

Rota da Festa is a Portuguese-language platform that aggregates sports events and cultural festivals across Portugal onto an interactive map. It consists of two main parts: a **Python scraper backend** and a **Next.js frontend**, connected through **Supabase** (PostgreSQL).

## Architecture

- **`rota-da-festa/`** — Python scrapers that run daily via GitHub Actions (03:00 UTC). Three scrapers run in sequence:
  1. `scraper_mestre.py` — Football matches from ZeroZero.pt (Playwright + BeautifulSoup, async)
  2. `scraper_festas.py` — Cultural events from Eventbrite (Playwright, uses Groq LLM for classification)
  3. `scraper_camaras.py` — Municipal council events (requests + BeautifulSoup, no Playwright)
- **`rota-da-festa-web/`** — Next.js 16 frontend (React 19, TypeScript, Tailwind CSS 4) deployed on Vercel. Also configured as a Capacitor mobile app (`pt.rotadafesta.app`).
- **Supabase** — Shared PostgreSQL database with two main tables: `eventos` (unique constraint on `nome, data`) and `favoritos`. The scrapers use `SUPABASE_SERVICE_KEY` for write access; the frontend uses `NEXT_PUBLIC_SUPABASE_ANON_KEY` for read access.

## Build, Lint, and Run Commands

### Frontend (`rota-da-festa-web/`)

```bash
npm install
npm run dev          # Dev server at localhost:3000
npm run build        # Production build
npm run lint         # ESLint (eslint-config-next with core-web-vitals + typescript)
```

### Scrapers (`rota-da-festa/`)

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements_etl.txt && pip install supabase
playwright install --with-deps chromium

python src/scraper_mestre.py    # Football scraper
python src/scraper_festas.py    # Cultural events scraper
python src/scraper_camaras.py   # Municipal events scraper
```

There is no test suite in either project.

## Environment Variables

### Frontend (`.env.local` in `rota-da-festa-web/`)
- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`

### Scrapers (`.env` or `.env.local` in `rota-da-festa/`)
- `SUPABASE_URL`
- `SUPABASE_SERVICE_KEY`
- `GROQ_API_KEY` (used by `scraper_festas.py` for LLM classification)

Scrapers also try to load `../../rota-da-festa-web/.env.local` as a fallback for Supabase credentials.

## Key Conventions

- **Language**: All UI text, comments, variable names in scrapers, and commit messages are in **Portuguese**. Keep this consistent.
- **Leaflet is dynamically imported** (`next/dynamic` with `ssr: false`) because it requires the browser's `window` object. Always follow this pattern for map-related components.
- **`"use client"` directive**: The main page and all components use client-side rendering. Supabase queries happen client-side.
- **API routes** (`src/app/api/`) handle server-side concerns: alerts, chat, moderation, business listings, reviews, Stripe payments, and attendance ("vou").
- **Scraper geolocation** uses a 6-step fallback chain: stadium cache → multiple Nominatim queries → locality extraction from team name → district centroid. New stadiums should be added to `CACHE_ESTADIOS` in `scraper_mestre.py`.
- **Supabase upsert** on `(nome, data)` prevents duplicate events. All scrapers follow this pattern.
- **Dynamic routes** use bracket notation: `src/app/jogos/[distrito]/` for district-specific pages.

## GitHub Actions

The `scrape.yml` workflow runs all three scrapers daily and auto-commits any stadium cache updates. Secrets required: `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `GROQ_API_KEY`. Timeout is 90 minutes.
