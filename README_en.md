# Apple Supply Chain Graph · 苹果产品供应链上下游图谱

> **English documentation.** 中文文档请见 [README.md](README.md)。
>
> This project builds a **three-layer directed graph** — from a **specific product model** up to its key components and their suppliers / contract manufacturers — covering "Product → Component → Supplier", and exports structured data importable into **Neo4j**. It ships zero-dependency interactive visualizations plus supplier fundamentals / valuation / sentiment analysis.
>
> This is also a **demo / exploratory work** produced end-to-end with **AI-assisted coding (WorkBuddy Hy3)**, emphasizing reproducible engineering and interactive experience. It is **not a formal industry or investment analysis** (see "Methodological limitations" and "Disclaimer").

**An open, reproducible map of Apple's product supply chain** — from finished product models down to components and suppliers, exportable to Neo4j, with zero-dependency interactive visualizations.

> 📊 **Research use (illustrative)**: this graph can also serve as an **illustrative experimental dataset** for supply-chain graph analysis, vulnerability modeling, and **graph neural network (GNN) teaching** — *not a mature benchmark* (MIT license; see "As a research / analytical experimental dataset" below).

[![Nodes](https://img.shields.io/badge/nodes-115-blue)](data/neo4j)
[![Products](https://img.shields.io/badge/products-28-green)](data/neo4j)
[![Components](https://img.shields.io/badge/components-27-green)](data/neo4j)
[![Suppliers](https://img.shields.io/badge/suppliers-60-green)](data/neo4j)
[![Relationships](https://img.shields.io/badge/relationships-510-orange)](data/neo4j)
[![Python](https://img.shields.io/badge/python-3.9%2B-blue?logo=python)](scripts/generate.py)
[![Zero deps](https://img.shields.io/badge/dependencies-none-success)](scripts)
[![License](https://img.shields.io/badge/license-MIT-yellow)](LICENSE)

---

## Table of Contents

- [Why this project](#why-this-project)
- [Features](#features)
- [Screenshots](#screenshots)
- [Quick Start](#quick-start)
  - [0. Site overview: unified navigation as "fusion"](#0-site-overview-unified-navigation-as-fusion)
  - [0.1 Unified navigation across pages (multi-page jump, not silos)](#01-unified-navigation-across-pages-multi-page-jump-not-silos)
  - [0.2 One-click Docker launch (recommended for publishing / analytics)](#02-one-click-docker-launch-recommended-for-publishing--analytics)
  - [0.3 Enable HTTPS (domain + certificate)](#03-enable-https-domain--certificate)
  - [0.4 Deploy to GitHub Pages (static hosting)](#04-deploy-to-github-pages-static-hosting)
  - [1. Browse the graph (zero dependencies)](#1-browse-the-graph-zero-dependencies)
  - [2. Import into Neo4j (your existing instance)](#2-import-into-neo4j-your-existing-instance)
  - [3. Regenerate from source](#3-regenerate-from-source)
- [Data model](#data-model)
- [As a research / analytical experimental dataset](#as-a-research--analytical-experimental-dataset)
- [Supplier fundamentals & relative valuation analysis](#supplier-fundamentals--relative-valuation-analysis)
- [Supplier sentiment analysis](#supplier-sentiment-analysis)
- [Supplier analysis dashboard](#supplier-analysis-dashboard)
- [Supply chain vulnerability analysis (Component → Product → Product line)](#supply-chain-vulnerability-analysis-component--product--product-line)
- [Tech stack](#tech-stack)
- [Directory structure](#directory-structure)
- [Roadmap](#roadmap)
- [Methodological limitations](#methodological-limitations)
- [Optimization directions](#optimization-directions)
- [Documentation](#documentation)
- [Data sources & conventions](#data-sources--conventions)
- [Contributing](#contributing)
- [Disclaimer](#disclaimer)
- [License](#license)

---

## Why this project

Most public material on Apple's supply chain is either a "generic Tier-1 list" or "a single news article". There is a lack of a graph that strings **"a specific model → which components it uses → who supplies / contract-manufactures those components"** into something queryable, importable into a graph database, and interactively explorable.

This project drives a three-layer directed graph from a **single source of truth**, achieving:

- **Model-level precision**: not a vague "iPhone", but `iPhone 17` / `17 Air` / `17 Pro` / `17 Pro Max`, etc.
- **Reproducible & extensible**: all CSV / JSON / web pages are regenerated from source data by scripts under `scripts/` and `tools/`.
- **Graph-database ready**: directly produces Neo4j official bulk-import-format CSV, importable into your own instance with zero Cypher.
- **Out of the box**: the graph, report, and dashboard are static HTML with embedded data — just open the file, no backend needed.

## Features

- **Model-level precision**: covers six product lines — iPhone / Mac / iPad / Apple Watch / Vision Pro / AirPods·HomePod — down to specific models (e.g. `iPhone 17 Pro`, `MacBook Pro 14" (M4)`, `Apple Vision Pro (M5)`).
- **Attribute enrichment**: supplier nodes split into `full name / English name / short name`; product nodes carry `English name, alias, release date, status, launch price, main chip, display spec`.
- **Graph-database ready**: 6 Neo4j official bulk-import-format CSVs (`:ID` / `:LABEL` / `:START_ID` / `:END_ID` / `:TYPE` headers), with offline / online import options.
- **Zero-dependency visualization**: root `index.html` (home graph) and other pages embed data — just open, no network or database needed (the dashboard charts rely on Chart.js from CDN, requiring network on first open).
- **Multi-page navigation, not silos**: home graph / supplier list / report / map / dashboard share one top navigation bar (`topnav.py`, maintained in one place, applied globally); cross-page deep links jump straight to a specific entity. This unified nav bar *is* the "fusion" — pinned to the top of every page so users can move freely between sections, without building a separate aggregator page per section.
- **Supplier list (table view)**: `dist/supplier_table.html` presents all 60 suppliers as a table, with filtering by **region / country / category / tier**, keyword search, and click-to-sort columns **ascending / descending**; each row jumps back to the graph or map in one click.
- **Supplier research layer**: relative valuation + sentiment analysis for 15 key suppliers, presented as a dashboard and a report.
- **Reproducible**: pure Python standard library, no third-party dependencies; all artifacts regenerable from a single source.

## Screenshots

| Page | Preview |
|------|---------|
| **Supply chain graph** (force-directed interactive) | ![supply chain graph](docs/screenshots/graph.png) |
| **Upstream/downstream report** (model overview + cross-page deep links) | ![report](docs/screenshots/report.png) |
| **Supplier map** (markers + logistics lines) | ![map](docs/screenshots/map.png) |
| **Valuation dashboard** (sentiment–valuation divergence matrix) | ![dashboard](docs/screenshots/dashboard.png) |

---

## Quick Start

### 0. Site overview: unified navigation as "fusion"

The whole site consists of **5 sections**, linked by a top **unified navigation bar** (`topnav.py`, maintained in one place, applied globally) — this is exactly the intent of "fusion": a jump bar pinned to the top of every page, letting users travel freely between sections without building a separate aggregator page for each:

- **🕸️ Supply chain graph** (`index.html`, site home): force-directed interactive; filter by product line / type, search, locate.
- **📋 Supplier list** (`dist/supplier_table.html`): table view of all 60 suppliers, with filtering by region / country / category / tier, keyword search, and click-to-sort columns.
- **📄 Upstream/downstream report** (`dist/apple_supply_chain_report.html`): model overview + cross-page deep links.
- **🗺️ Supplier map** (`tools/visualizations/supplier_geo.html`): production-base markers + logistics lines.
- **📊 Valuation dashboard** (`tools/visualizations/supplier_dashboard.html`): valuation × sentiment visualization.

Each section can deep-link across pages to a specific entity (see next section).

### 0.1 Unified navigation across pages (multi-page jump, not silos)

Every page — **home graph** (`index.html`), **supplier list** (`dist/supplier_table.html`), **upstream/downstream report** (`dist/apple_supply_chain_report.html`), **supplier map** (`tools/visualizations/supplier_geo.html`), **valuation dashboard** (`tools/visualizations/supplier_dashboard.html`) — carries the **same navigation bar** (generated by `topnav.py`), enabling one-click jumps between pages; they are no longer isolated.

Deep links (cross-page jump to a specific entity):

| Source | Jump | Form |
|--------|------|------|
| Entity in report table | → locate node in graph | `index.html?focus=S:tsmc` |
| Supplier in report | → locate supplier on map | `supplier_geo.html?supplier=tsmc` |
| Graph node details | → report section / map location | links `apple_supply_chain_report.html#sec-suppliers` and `supplier_geo.html?supplier=…` |
| Home graph control bar "📋 Supplier table" button | → supplier list (table view) | `dist/supplier_table.html` |
| "Graph / Map" per row in supplier list | → locate in graph / drop pin on map | `index.html?focus=S:tsmc`, `supplier_geo.html?supplier=tsmc` |
| Map marker popup | → graph / report | "View in graph →" / "View in report →" inside popup |

> The map / dashboard are static pages or generated by `geo_build.py`; their nav bars are also injected by `topnav.py`.

### 0.2 One-click Docker launch (recommended for publishing / analytics)

Package the whole site into an **nginx container** and serve all pages (including the entry landing page) at `http://localhost:16161` with **one command**.

Only after accessing via **http** will Umami analytics actually report — when opened locally via `file://`, the analytics script is deliberately skipped (see the `location.protocol` gate in `topnav.py`). So if you want visit-frequency analytics, hosting via **Docker / any http server** is the better launch method. Analytics config (Website ID, etc.) is now injected via **environment variables** instead of being hard-coded in source: locally write values into a repo-root `.env` (already git-ignored), and in CI inject via the `env:` block in `pages.yml` (see `.env.example` and `topnav.py`).

Prerequisite: Docker installed (with Compose v2).

```bash
make up        # = docker compose up -d --build, build image and start in background
# open http://localhost:16161 in browser
make down      # stop and remove containers
make logs      # view container logs
make build     # build image only
make serve     # without Docker, start a local Python static server (same port)
```

> 🌐 **Network-restricted environments (e.g. mainland China)**: if `docker.io` pulls time out, copy a local config and fill in a mirror source:
> ```bash
> cp .env.example .env      # default already writes Huawei Cloud docker.io mirror (full image names PYTHON_IMG/NGINX_IMG)
> make up                   # compose auto-reads PYTHON_IMG / NGINX_IMG from .env as build args
> ```
> Overseas, directly pulling `docker.io` needs no such step (no `.env` → official sources `python:3.11-slim` / `nginx:1.27-alpine`). You can also add `"registry-mirrors": ["https://<mirror>"]` in Docker Desktop Settings → Docker Engine once and for all.
>
> Don't want Docker? `make serve` or `python3 -m http.server 16161` starts a local static server directly — same effect as Docker (also http hosting).
> ⚠️ The **supplier map page** relies on Tencent Location Service GL JS, which needs a **real domain + valid Key** (replace the `__WB_TMAP_SECRET__` placeholder in the page). Under `localhost` the map won't render — other pages are unaffected.
> The container build runs `build_all.py` to regenerate all pages; after changing data, `make up` rebuilds automatically.

### 0.3 Enable HTTPS (domain + certificate)

By default `make up` serves **HTTP** (port `16161`), suitable for local debugging, or HTTP deployment when you are not yet ready to configure a certificate. When you already have a domain and valid certificate (e.g. Let's Encrypt `fullchain.pem` + `privkey.pem`), use the "production override" to terminate TLS inside the container and auto-redirect HTTP → HTTPS, **without changing the default HTTP flow**:

```bash
mkdir -p certs
cp /path/to/fullchain.pem certs/fullchain.pem
cp /path/to/privkey.pem   certs/privkey.pem
make up-prod        # = docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
# visit https://your-domain (HTTP auto 301-redirects to HTTPS)
```

- Certificates live in `certs/`, **git-ignored, never committed**; `nginx.prod.conf` reads from there (change the file if paths differ).
- Production config `nginx.prod.conf` listens on 443 (SSL) + 80 (redirect), with TLS 1.2/1.3, strong cipher suites, and HSTS as a commented option.
- If you'd rather terminate TLS at a **reverse proxy / Cloudflare / cloud load balancer**, keep the container on default HTTP (just use `make up`).
- To keep HTTP directly (no redirect): replace the `return 301` on port 80 in `nginx.prod.conf` with a normal `location /` service.

### 0.4 Deploy to GitHub Pages (static hosting)

All pages of this project are **zero-dependency static files**, naturally fitting GitHub Pages. And navigation uses **relative paths** throughout (`topnav` builds `dist/...` / `tools/visualizations/...` with `../`, `../../`), so whether deployed to:

- User / org root domain: `https://<user>.github.io/`
- Project subpath: `https://<user>.github.io/apple-chain-graph/` (default, no custom domain needed)
- Custom domain: Settings → Pages → Custom domain

cross-page navigation never 404s. Umami analytics reports normally under **https** (the `file://` gate doesn't trigger); the analytics switch and Website ID are configured via the `ANALYTICS_WEBSITE_ID` environment variable — see `topnav.py` and `.env.example`.

**Automatic deployment (recommended)**: the repo includes `.github/workflows/pages.yml`; pushing to `main` auto-builds and publishes.

1. Before first deploy, in repo **Settings → Pages → Build and deployment → Source**, choose **GitHub Actions**.
2. Push a commit containing that workflow to `main`; GitHub runs CI and publishes automatically.
3. The access URL follows the three cases above; a custom domain also requires filling the domain in Settings → Pages → Custom domain and adding DNS per the prompt.

> **Multi-repo coexistence / naming-conflict note (important)**
> - **Project sites are isolated under a URL path by repo name**: this repo publishes to `https://Coolgiserz.github.io/apple-chain-graph/`, each repo owning its own independent `/<repo>/` path segment. Your other published GitHub Pages (e.g. `/other-repo/`) are **completely unaffected** — their URL paths are inherently different, so there is **no site-level naming conflict**.
> - **The only globally shared namespace is the "custom domain"**: a custom domain can be occupied by **only one** repo at a time. So please **do not** set a domain already used by another repo here. Keeping the default `*.github.io/apple-chain-graph/` form publishes with zero conflict.
> - **All CI resources are repo-scoped**: the `concurrency.group` in the workflow, the Pages artifact name, the `github-pages` environment, and the `GITHUB_TOKEN` used for deployment all act only on **this repo's** Actions and **will not** interfere with your other repos' deployments or lock each other.
> - **Future new repos**: each new repo only needs its own `.github/workflows/pages.yml`, getting its own `/<its-repo-name>/` with no cross-repo coordination needed (again, just obey the custom-domain-uniqueness rule above). If you create a **second** Pages workflow *within this repo*, give it a different `concurrency.group` (two workflows in the same repo both using `group: pages` would cancel each other); cross-repo there is no such issue.

**Published content**: CI picks only static artifacts — `index.html`, `dist/`, `tools/visualizations/`, `docs/`, plus `README.md` / `README_en.md` / `LICENSE` / `CONTRIBUTING.md`; it does **not** publish Python source, `data/`, `tools/*.py`, `.env`, `certs/`.

**Map page (Key-free by default, works on static hosting directly)**: the supplier map page (`supplier_geo.html`) auto-selects a render backend at runtime —

- **Default Leaflet + OpenStreetMap**: pure front-end, no Key, no proxy — renders directly on any static host like GitHub Pages, no config needed (markers colored by valuation, logistics lines, flow animation, category filter, deep link `?supplier=` all work).
- **Tencent Map GL (optional enhancement)**: when you stand up a public Tencent Map signing proxy and replace the page's `serviceHost` (`http://127.0.0.1:__WB_HTTP_PORT__/...`) with a real proxy domain + Key, the map auto-switches to Tencent's native style (can be auto-injected via Secrets in `.github/workflows/pages.yml`, see its comments). When unconfigured, Leaflet's default rendering is unaffected.

> Note: OSM tiles may be slow in mainland China; in the generated map page you can swap `tile.openstreetmap.org` for CartoDB / Amap tile sources. `.nojekyll` is added to the published artifacts to disable Jekyll and ensure `_`-prefixed directories publish as-is and speed up builds. If you only want manual publishing without CI, you can also choose "Deploy from a branch" in repo Settings → Pages and set `main`'s `/` or `/docs` as the source — but then you must commit build artifacts into the repo yourself.

### 1. Browse the graph (zero dependencies)

Just double-click to open the root **`index.html`** (or drag it into the browser). Data is embedded — no network or database needed:

- Scroll to zoom, drag to pan, drag nodes.
- Click a node to see details (release date, status, launch price, related suppliers, etc.).
- Filter at the top by Product / Component / Supplier, filter by product-line dropdown, search box to locate.

### 2. Import into Neo4j (your existing instance)

Data is ready; just follow **[docs/neo4j-import.md](docs/neo4j-import.md)**. Two official methods:

- **Method A — offline bulk import (neo4j-admin)**: for building a standalone new database. Point `NEO4J_HOME` at your instance and run:
  ```bash
  NEO4J_HOME="/path/to/your/neo4j/instance/root" bash data/neo4j/import_admin.sh
  ```
- **Method B — online import (LOAD CSV)**: for adding directly into a running existing database without stopping it. Put the 6 CSVs into Neo4j's `import/` directory, then run a Cypher snippet in Browser.

> ⚠️ The database name cannot contain underscores; this script defaults to `apple-supply-chain`. The target database must be **stopped** before import (neo4j-admin is offline import).

### 3. Regenerate from source

Requires Python 3.9+, no third-party dependencies (dependency list in `requirements.txt`, standard library + internal modules only):

```bash
# Regenerate all pages in one command (recommended)
python3 build_all.py
# Or syntax-check only: python3 build_all.py --check

# Or run individually (equivalent)
python3 scripts/generate.py     # generate data/neo4j/*.csv + data/apple_supply_chain.json
python3 scripts/report.py       # generate dist/apple_supply_chain_report.html (standalone report)
python3 scripts/build_viewer.py # generate root index.html (home graph) + dist/graph_engine.js (shared canvas engine)
python3 scripts/build_table.py  # generate dist/supplier_table.html (supplier list: filter + sort table view)
python3 tools/geo_build.py      # generate tools/visualizations/supplier_geo.html (supplier map)
# The valuation dashboard tools/visualizations/supplier_dashboard.html is a static page with the unified nav bar injected
```

> The graph's canvas physics engine has been extracted into a standalone file **`templates/graph_engine.js`** (copied to `dist/graph_engine.js` at build time; data is injected via the page-inlined `window.SUPPLY_DATA = …`), enabling Node unit tests and IDE syntax checks. This engine is the single source of truth, reused by the home graph; publish it together with the home page and `dist/` at deploy time.

> All pages share `topnav.py`'s unified nav bar — change once, apply globally; report content is rendered by `report.py`'s reusable builder (with `jump=True, mode="web"`, entities automatically carry cross-page `<a>` deep links). Adding a new section is just one line in `topnav.py`'s `NAV_ITEMS`, and it appears in every page's nav.

## Data model

Three layers of nodes + three types of relationships:

| Node | Key attributes |
|------|----------------|
| **Product** | `name` (model full name), `product_line`, `english_name`, `alias`, `release_date`, `release_year`, `status`, `soc`, `display`, `price_usd` |
| **Component** | `name` (Chinese full name), `english_name`, `category`, `subcategory` |
| **Supplier** | `name` (full name), `english_name`, `short_name`, `country`, `region`, `category`, `tier` |

Relationships: `Product -[USES_COMPONENT]-> Component`, `Component -[SUPPLIED_BY]-> Supplier`, `Product -[ASSEMBLED_BY]-> Supplier` (contract manufacturing). Full field meanings in **[docs/data-model.md](docs/data-model.md)**.

## As a research / analytical experimental dataset

> ⚠️ **Use with caution**: this graph is currently an **exploratory, illustrative experimental dataset** — **not yet a validated, standardized mature dataset / benchmark**. It is small (~115 nodes / 510 edges), a secondary aggregation of AI web-searched public materials, and a point-in-time snapshot, carrying risks of inconsistent conventions and model hallucination. The text below only explains *how to use it as experimental data*, and does not imply it already meets benchmark quality.

All artifacts in this repo (graph data, Neo4j import CSV, vulnerability analysis results, visualizations) can be used as a **reproducible, illustrative experimental dataset** for teaching and early exploration — not as an authoritative benchmark:

- **Graph-structure example data**: the three-layer directed graph (`Product → Component → Supplier`) is fixed-size and reproducible, suitable as a **teaching example or smoke-test** for **graph neural networks (GNN)** — node classification, link prediction, community detection. Edge direction semantics are clean and can be fed to `networkx` / `PyG` / `DGL` with no extra cleaning. But the sample is tiny — fit for teaching and prototyping only; **do not use it to claim a model "achieves SOTA on a supply-chain benchmark."**
- **Supply-chain risk-modeling sample**: the "single-point dependency / vulnerability" results from `tools/run_risk.py` (including single-point components like `audio_codec → Cirrus Logic`, and the most vulnerable line `iPhone ≈ 0.50`) can serve as a **draft input feature or label** for **supply-chain vulnerability modeling, risk propagation, and robustness analysis**, and still need verification against primary data before any formal research use.
- **End-to-end reproducible**: pure Python standard library, single source of truth (`data/apple_supply_chain.json`), one `python3 build_all.py` regenerates all artifacts, with **data and code fully separated** — edit the CSV / JSON to recompute, convenient for reproduction, controlled experiments, and extension.
- **License & attribution**: released under the **MIT license**, free to use for academic, teaching, and derivative work. Please **state the data conventions and limitations** (this is a secondary aggregation of AI web-searched public materials, a point-in-time snapshot — see "Methodological limitations" and "Data sources & conventions") and do not treat it as primary fact or formal investment / procurement basis.

> Want to turn the graph into GNN training data? Build an adjacency matrix directly from `data/apple_supply_chain.json`'s `nodes`/`edges`, or import the 6 Neo4j CSVs via LOAD CSV and export an edge list. When citing, please include the version (commit) and the data snapshot time, and clearly state it is "exploratory reference data, not a benchmark."

## Supplier fundamentals & relative valuation analysis

Beyond the graph (structure), we additionally study the fundamentals and valuation of **15 key suppliers among the 60**: revenue / net profit / gross margin / ROE, multiples like P/E · P/B · EV/EBITDA, and use **peer-relative valuation** to judge whether each is currently overvalued / undervalued / fairly valued, with **trends, recent status, and source links** per supplier.

The tool is entirely based on the Python standard library, with data and code separated (`tools/data/supplier_fundamentals.csv` can be manually reviewed/edited):

```bash
python3 tools/run_analysis.py                 # full analysis → tools/output/{supplier_analysis.md,json}
python3 tools/run_analysis.py --id tsmc       # view a single supplier only (print to stdout)
python3 tools/run_analysis.py --md out.md --json out.json
python3 tools/run_risk.py                    # supply chain vulnerability → tools/output/{supply_chain_risk.md,json}
python3 tools/run_risk.py --top 5            # print only Top5 most vulnerable lines/products/components
```

- Valuation method: current multiple ÷ **peer group (sector) median** → mean of the three ratios P/E, P/B, EV/EBITDA. `< 0.85` undervalued, `> 1.15` overvalued, otherwise fairly valued; when peers are insufficient, fall back to the full-sample median (marked in the report).
- Apple, as the terminal OEM / customer, is listed separately as an `OEM(Benchmark)` baseline and does not participate in supplier peer comparison.
- Full method, conventions, and limitations in **[docs/supplier-analysis.md](docs/supplier-analysis.md)**.
- Conclusions are based solely on a single point-in-time (Jul–Aug 2026) market snapshot and **do not constitute any investment advice**.

## Supplier sentiment analysis

Beyond fundamentals / valuation, we add a layer of **sentiment (market mood)** analysis for these **15 key suppliers**: crawl the tone of recent mainstream financial-media coverage (news sentiment: positive / neutral / negative), aggregate the rating distribution and consensus direction of sell-side research (analyst sentiment: bullish / neutral / bearish), and distill **key catalysts, key risks, and clickable source links**. The report auto-displays the previous section's **valuation conclusion** side by side, making it easy to spot "sentiment–valuation" divergences (e.g. negative news but already undervalued, or heated sentiment but already overvalued).

```bash
python3 tools/run_sentiment.py                 # generate tools/output/supplier_sentiment.md
python3 tools/run_sentiment.py --id qualcomm    # view a single supplier only
```

- Data and code separated: `tools/data/supplier_sentiment.csv` can be manually reviewed/edited (fields include news_summary / analyst_consensus / key_catalysts / key_risks / sources).
- Methodology, conventions, and limitations (including cross-market analyst coverage-density differences, snapshot time sensitivity, etc.) are in Section 3 of the report.
- Sentiment is a **qualitative + consensus** judgment, not a quantitative model, and **does not constitute any investment or procurement advice**.

## Supplier analysis dashboard

`tools/visualizations/supplier_dashboard.html` is a **backend-free, double-click-to-open** interactive dashboard that visualizes the valuation + sentiment conclusions. It contains 6 charts:

1. **Peer-relative valuation distribution** — horizontal bars sorted ascending by score, blue / green / red for undervalued / fairly / overvalued.
2. **Sentiment–valuation divergence matrix (core)** — bubble chart: x-axis = relative valuation score (right = more expensive), y-axis = sentiment index (news + sell-side consensus), bubble size = market cap. Four quadrants instantly reveal "quality at a discount / contrarian opportunity / priced for perfection / risk zone".
3. **Sentiment distribution** — news sentiment and sell-side consensus doughnuts.
4. **Profitability quality comparison** — ROE × net-margin bubble chart (bubble size = revenue).
5. **Sector market-cap distribution + detail table** — per-sector total market-cap bar chart + 15-supplier key-metrics table.

> Data sources: `tools/data/supplier_fundamentals.csv` + `supplier_sentiment.csv` + `tools/output/supplier_analysis.json`. Charts rely on Chart.js from CDN (network needed on first open).

## Supply chain vulnerability analysis (Component → Product → Product line)

Beyond valuation / sentiment, a new **graph-structure view of supply chain risk**: starting from "how many suppliers each component has", aggregate bottom-up to products, then roll up to product lines, to answer "which product line faces the greatest supply chain risk".

Model (naive / basic convention; full detail in **[docs/supply-chain-risk.md](docs/supply-chain-risk.md)**):

- **Component vulnerability** `V = 1 / n` (n = number of suppliers for that component): fewer suppliers → more vulnerable; `n = 1` is a single point of failure (stop-ship on disruption), `V = 1.0`; `n = 0` (missing data) also treated as most vulnerable.
- **Product vulnerability** = `0.5 × mean component vulnerability` (overall exposure) + `0.3 × weakest link` (max single-component vulnerability) + `0.2 × single-point share`, yielding a `[0,1]` score.
- **Product line vulnerability** = the mean of its products' vulnerability, with weakest link and total single-point count summarized.

```bash
python3 tools/run_risk.py                    # full analysis → tools/output/{supply_chain_risk.md,json}
python3 tools/run_risk.py --top 5            # print only Top5 most vulnerable lines/products/components
python3 tools/run_risk.py --md out.md --json out.json
```

- Driven entirely by the graph data (`data/apple_supply_chain.json`, single source of truth); pure standard library, zero third-party dependencies.
- The current convention uses "supplier count" as the primary signal; a component's **geographic dispersion** (number of distinct countries) is output as a reference field — multiple suppliers in one country is not true redundancy, helping spot "pseudo-redundancy" traps. **Not investment or procurement advice.**

## Tech stack

| Layer | Tech | Notes |
|-------|------|-------|
| Data processing | Python 3.9+ (standard library) | generation scripts under `scripts/` and `tools/`, **zero third-party deps** |
| Home graph viz | Native Canvas + custom force-directed layout | `index.html` (home), embedded data, double-click to open |
| Dashboard viz | Chart.js (CDN) | `supplier_dashboard.html`, network needed on first open |
| Map | Tencent Location Service GL JS | `supplier_geo.html` (run under your own domain) |
| Graph DB | Neo4j (official bulk-import-format CSV) | 6 CSVs, offline / online import |
| Graph data | JSON (`data/apple_supply_chain.json`) | full nodes + edges + field dictionary |

## Directory structure

```
apple_supply_chain/
├── README.md                 # Chinese version of this document
├── README_en.md              # this file (English)
├── LICENSE                   # MIT
├── CONTRIBUTING.md           # contribution guide
├── requirements.txt          # dependency list (standard library only, no third-party deps)
├── build_all.py              # unified build entry: regenerate all pages in one command
├── Dockerfile                # multi-stage build: python generates static pages → nginx hosts
├── docker-compose.yml        # one-click launch (make up)
├── Makefile                  # common shortcuts (up / down / logs / serve / build)
├── nginx.conf                # in-container nginx config (UTF-8 / gzip / long cache)
├── .dockerignore             # build-context exclusions
├── index.html                # home: supply chain graph (site entry, force-directed interactive, double-click to open)
├── .gitignore
├── data/                     # data artifacts
│   ├── apple_supply_chain.json   # full graph data (nodes + edges + field dictionary)
│   └── neo4j/                # Neo4j official bulk-import format
│       ├── products.csv
│       ├── components.csv
│       ├── suppliers.csv
│       ├── rel_product_component.csv
│       ├── rel_component_supplier.csv
│       ├── rel_product_assembly.csv
│       ├── import_admin.sh   # offline bulk-import script (neo4j-admin)
│       └── refresh_import.sh # sync CSVs to your import directory
├── scripts/                  # data-generation scripts (reproducible)
│   ├── generate.py           # generate CSV + JSON
│   ├── report.py             # generate HTML analysis report (reusable builder, supports jump deep links)
│   ├── build_viewer.py       # generate home interactive graph (root index.html, reuses templates/graph_engine.js)
│   └── build_table.py        # generate supplier list: dist/supplier_table.html (table filter + sort)
├── index.html                # home: supply chain graph (force-directed interactive, double-click to open)
├── templates/                # web front-end templates (HTML/JS/CSS maintained separately, scripts fill data to generate pages)
│   ├── graph_engine.js       # shared graph canvas physics engine (single source of truth for home graph)
│   ├── graph_page.html       # home graph HTML template
│   ├── graph_bootstrap.js    # home graph bootstrap script
│   └── table_page.html       # supplier list (table view) HTML template (inline filter/sort JS)
├── topnav.py                 # unified top nav bar shared by all pages (single source, change once apply globally)
├── tools/                    # supplier fundamentals & relative valuation analysis (reproducible, pure standard library)
│   ├── run_analysis.py        # CLI: merge three sources → run valuation → output md/json
│   ├── run_sentiment.py       # CLI: generate supplier sentiment analysis report
│   ├── run_risk.py            # CLI: supply chain vulnerability (component→product→line) → output md/json
│   ├── data/
│   │   ├── supplier_fundamentals.csv  # 15 key suppliers' fundamentals + multiples + sources
│   │   └── supplier_sentiment.csv     # 15 key suppliers' sentiment (news/analyst/catalysts/risks/sources)
│   ├── supplier_research/     # analysis engine (pure standard library)
│   │   ├── universe.py        # code/exchange/currency/sector peer grouping
│   │   ├── analysis.py        # three-source merge orchestration
│   │   ├── valuation.py       # peer-relative valuation engine (current multiple vs peer median)
│   │   ├── report.py          # render valuation markdown + json
│   │   ├── sentiment.py       # sentiment loading & rendering
│   │   └── risk.py            # supply chain vulnerability engine (component vuln + product/line aggregation)
│   └── output/                # generated supplier analysis artifacts
│       ├── supplier_analysis.md
│       ├── supplier_analysis.json
│       ├── supplier_sentiment.md
│       ├── supply_chain_risk.md
│       └── supply_chain_risk.json
├── docs/                     # documentation
│   ├── neo4j-import.md       # detailed Neo4j import tutorial (your own instance)
│   ├── data-model.md         # data model & field dictionary
│   ├── supplier-analysis.md  # supplier fundamentals & relative valuation: method / conventions / limitations
│   └── screenshots/          # README screenshots (see "Screenshots" section)
└── dist/                     # generated web artifacts
    ├── apple_supply_chain_report.html  # analysis report (standalone page)
    ├── supplier_table.html       # supplier list: filter + sort table view of all 60 suppliers
    ├── graph_engine.js           # shared graph canvas physics engine (reused by home index.html)
    └── graph_bootstrap.js        # home graph bootstrap script
```

## Roadmap

- [x] Three-layer directed graph + Neo4j official import format
- [x] Zero-dependency interactive graph (force-directed, filter, search, locate)
- [x] Upstream/downstream report + cross-page deep links
- [x] Unified navigation across pages (multi-page jump)
- [x] 15 key suppliers: peer-relative valuation + sentiment analysis + visualization dashboard
- [x] Supply chain vulnerability analysis (component → product → product line, graph single-point-dependency view)
- [x] Bilingual docs (English README) & multi-language UI (i18n for zh/en/fr/ja)
- [ ] Automated data-freshness updates (market snapshot refresh script)
- [ ] Broader coverage of more product lines / unreleased models
- [ ] Two-way graph–map linkage (click a supplier to highlight its upstream/downstream chain)
- [ ] Further language coverage / refinements

## Methodological limitations

This project is essentially **a demo / exploratory work rapidly built with AI-assisted coding**; its analytical conclusions carry the following systematic limitations and **should not be used as a basis for formal research or decisions**:

- **Data sources are secondary aggregations**: all data is integrated by AI via web search of public materials (supply-chain reports, news, research summaries) — not primary disclosures; different sources differ in convention, currency, and timing, and public materials themselves may be distorted by vendor narratives, media stance, or **astroturfing / fake engagement**; conclusions need manual verification.
- **Rough valuation method**: peer-relative valuation uses coarse `sector` grouping + median multiples (mean of P/E, P/B, EV/EBITDA) to judge over/under-valued, ignoring cross-market (A-share / HK / US) valuation-system differences, growth, capital structure, and accounting-standard differences; it is a single point-in-time snapshot with no historical percentiles or trends.
- **Sentiment is qualitative consensus, not a quantitative model**: news/analyst sentiment are manually/AI-summarized "positive / neutral / negative" labels, with no quantified sentiment intensity; analyst coverage density varies across markets, limiting representativeness.
- **Graph relationships are binary, unweighted**: edges only indicate "whether supplies / contract-manufactures", without share, amount, or output weight; supplier `tier` is a qualitative label, not modeling real dependency strength or substitution elasticity; some unreleased models are only forward-looking.
- **Inherent AI-generation risks**: data is retrieved and integrated by the model via web search and may contain **hallucinations, staleness, or misattribution**; code examples and copy also need review and cannot be assumed correct by default.

## Optimization directions

To address the above limitations, future work can improve along three dimensions — **technical / analytical / data**:

**Technical**
- Add a market-snapshot auto-refresh script (periodic fetch, generate new-version JSON) so valuation conclusions can update over time.
- Two-way graph–map linkage: clicking a supplier highlights its upstream/downstream chain in the graph and focuses its bases on the map.
- Introduce data validation & provenance: each value carries a `source` link, with consistency checks at generation; add automated tests / CI to prevent regressions.
- Multi-language (i18n) UI and English docs; further turn Umami visit analytics into a simple dashboard to inform content priorities.

**Analytical**
- Upgrade valuation from "cross-sectional median multiples" to **multi-year PE / PB historical percentiles** + **EV/EBITDA and DCF cross-validation**, distinguishing growth and capital structure.
- Switch sentiment to **quantitative sentiment analysis (NLP)**, outputting sentiment-intensity scores and time series to identify expectation turning points.
- Run **community detection** on the graph to identify core hub nodes, and build a **supply-chain risk-propagation** model (blast radius of a single-point supply cutoff).

**Data**
- Connect primary data sources (financial-report / announcement APIs, exchange disclosures), distinguishing valuation conventions across markets.
- Add **share / revenue weight** to relationship edges, moving "key supplier" from qualitative to quantitative.
- Broaden product-line coverage and establish a normalized data-update + manual-verification workflow, reducing reliance on a single point-in-time snapshot.

## Documentation

- [docs/neo4j-import.md](docs/neo4j-import.md) — detailed Neo4j import tutorial (focused on your existing instance)
- [docs/data-model.md](docs/data-model.md) — data model & field dictionary
- [docs/supplier-analysis.md](docs/supplier-analysis.md) — supplier fundamentals & relative valuation: method / conventions / limitations
- [docs/supply-chain-risk.md](docs/supply-chain-risk.md) — supply chain vulnerability (component→product→line): model / weights / limitations
- 中文文档：[README.md](README.md)

## Data sources & conventions

- **Data sources**: all data in this project is integrated by **WorkBuddy** via **web search of public materials** (supply-chain research reports, financial news, sell-side research summaries, Apple's public supplier lists, etc.) — a secondary aggregation and reorganization, **for reference and learning exchange only**.
- Sources include: public supply-chain reports (2024–2026) + Apple's 2024 supplier list (187 core suppliers, ~98% of direct spend), etc.; public materials themselves may be distorted by vendor narratives, media stance, or astroturfing / fake engagement, so conclusions should defer to official primary disclosures.
- Model coverage covers major models on sale / announced as of 2025–2026; some unreleased models are forward-looking only.
- Supplier share is quantified only for the few segments with clear public disclosure; the rest are described qualitatively as "key supplier".
- Data is used for supply-chain structure research and teaching and **does not constitute any investment or procurement advice**.
- Data conventions and limitations are detailed in Section 10 of `dist/apple_supply_chain_report.html`, and in the "Methodological limitations" section above.

## Contributing

Issues and PRs are welcome! Adding / correcting supplier relationships, supplementing models, and improving valuation conventions are all very valuable. Please read **[CONTRIBUTING.md](CONTRIBUTING.md)** before starting.

## Disclaimer

- **Project positioning**: this project is more about **demonstrating and exploring the effect of "using AI-assisted coding (WorkBuddy) to produce a visualization analysis project end-to-end"**, focusing on reproducible engineering and interactive experience, rather than a formal industry / investment analysis.
- The supplier fundamentals, valuation, and sentiment conclusions involved are all integrated by AI via web search of public materials, based solely on a point-in-time snapshot, and **should not be used as a basis for formal analysis, investment, procurement, or any decision**.
- Data may contain errors, staleness, or model hallucinations; defer to **official primary disclosures**; please verify before use.
- See "Methodological limitations" and "Data sources & conventions" above.

## License

[MIT](LICENSE) © 2026 Apple Supply Chain Graph contributors.
