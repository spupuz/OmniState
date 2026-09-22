# OmniState v2.4.0

<p align="center">
  <img src="server/favicon.svg" alt="OmniState logo" width="80" height="80">
</p>

**Multi-project persistent memory MCP server**, with a built-in web dashboard.

OmniState v2 is a **Docker container** that runs as an **MCP server** (Model Context Protocol): it indexes the memory of all your projects into a **single central SQLite database**, offers **cross-project search** and **shared memory**, and integrates **GitHub PR Health** monitoring directly in the web dashboard.

No local skills, no memory files scattered across projects: everything lives in the server.

## Features

- **MCP server** (Streamable HTTP on `/mcp`): connects to opencode, Claude Code and other AI tools as a remote MCP.
- **Central memory**: all projects indexed in one SQLite (FTS5) in a plain **folder on your host** (`DATA_HOST_DIR`).
- **Auto-registration**: when you use the MCP in a project, the server registers and indexes it automatically.
- **Per-project + shared**: isolated memory for each project + shared memory common to all.
- **Cross-project search**: full-text across all projects and the shared memory.
- **Sessions**: `session_start` / `session_snapshot` replace the old `/start-session` and `/snapshot-session` skills.
- **Web dashboard** on `:8347`: aggregate view, per-project drill-down, shared memory, global search.
- **Project lifecycle**: the Projects tab splits repositories into **Active / Archived / Deleted** — GitHub is authoritative: a project whose remote repo is archived or deleted on GitHub moves to those sections even if its local folder still exists (and only active projects show on the Overview).
- **GitHub PR Health**: scans open PRs of your accounts/orgs with metrics (drafts, no-reviewer, stale, issues), historical trends and delta — stored in the central DB. Every repo row in the dashboard links straight to its GitHub PRs and issues.
- **Optional auth**: set `OMNISTATE_AUTH_TOKEN` in `.env` to protect `/api/*` and MCP session creation with a Bearer token — dashboard prompts for it and stores it in `localStorage`; MCP clients send it via header (opencode) or `httpHeaders` (Antigravity).
- **Favicon + branding**: `server/favicon.svg` served at `/favicon.svg` and `/favicon.ico` (exempt from auth) and shown in the README and dashboard.
- **Privacy-first**: the DB, the metrics and the token **never leave your data folder** and never end up on GitHub.

## Installation (Docker)

```bash
git clone https://github.com/spupuz/OmniState.git
cd OmniState

# 1. Configuration: create your .env (NEVER committed)
cp .env.example .env
nano .env    # set PROJECTS_ROOT (projects) and DATA_HOST_DIR (where data lives)

# 2. Start
docker compose up -d --build
```

### The `.env` file

The container configuration lives in a local **`.env`** file, **never committed to GitHub** (it is in `.gitignore` and `.dockerignore`). The repo ships a documented template, **`.env.example`**:

```bash
cp .env.example .env
```

| Variable | Required | Description |
|---|---|---|
| `PROJECTS_ROOT` | ✅ | **Absolute** path on the host to your projects root (e.g. `/home/mario/projects`). Mounted at `/workspaces` **read-only** and used for MCP path translation. |
| `OMNISTATE_HOST_PORT` | — | Host port for dashboard+MCP (default `8347`; the container always listens on 8347). |
| `GITHUB_ACCOUNTS` | — | GitHub accounts/orgs to scan, comma-separated (empty = scans disabled). |
| `GITHUB_TOKEN` | — | GitHub PAT: enables GraphQL, private repos and extended metrics. **Never exposed** by API/dashboard/MCP. |
| `GITHUB_SCAN_INTERVAL_HOURS` | — | Hours between automatic scans (default `6`). |
| `OMNISTATE_SCAN_INTERVAL_SECONDS` | — | Seconds between discovery scans (default `300`). |
| `OMNISTATE_AUTH_TOKEN` | — | **Optional** access token for everything reachable over the network (`/api/*` + MCP sessions) — set it if the box is reachable by others on the LAN. Read below for how each client sends it. |
| `DATA_HOST_DIR` | — | Host folder where all server data lives, bind-mounted at `/data` (default `./data` inside the OmniState dir). A plain directory: browse it, back it up, move it. |
| `OMNISTATE_AUTO_IMPORT_LEGACY` | — | Import old v1 memory files (`chunks/`, `tasks-history.json`, …) automatically when a project with such files is discovered (default off: `false`). |

The file also holds the GitHub token: **do not share it, do not commit it, do not paste it**. If you lose it, rotate it on GitHub.

### Access token (optional auth)

When `OMNISTATE_AUTH_TOKEN` is set in `.env`, the server requires a **Bearer token** on `/api/*` and on **MCP session creation** (`POST /mcp` without an `Mcp-Session-Id`). Routes that stay open on purpose: `/` (dashboard shell, so the token prompt loads), `/health`, `/favicon.*`, and MCP follow-ups that already carry a server-issued `Mcp-Session-Id`. Without the variable the server is wide open, as before.

Verify: `curl http://localhost:8347/health` → `{"status":"ok","version":"X.Y.Z",...}` (the version always mirrors `VERSION.txt`). With a token set, `curl http://localhost:8347/api/projects` returns **401** unless you send `-H "Authorization: Bearer $TOKEN"`.

### Where the data lives (mount points)

Everything is stored in **one plain folder on your host** — `DATA_HOST_DIR` (default `./data` inside the OmniState clone) — bind-mounted into the container. There are exactly **two mounts**:

| Host path | Container path | Mode | What it is |
|---|---|---|---|
| `DATA_HOST_DIR` (e.g. `~/OmniState/data`) | `/data` | **read-write** | The server's whole brain: `index.db` (memory + GitHub metrics), `shared/` (shared memory files), `config.json` (accounts + token), `logs/` |
| `PROJECTS_ROOT` (e.g. `/home/mario/projects`) | `/workspaces` | **read-only** | Your projects: discovery + one-shot legacy import only — the server *never writes* into them |

Inside `DATA_HOST_DIR`:

```
data/
├── index.db      ← SQLite: projects, memory (FTS5), gh_* GitHub scan tables
├── shared/       ← shared memory entries as readable files
├── config.json   ← runtime config incl. GitHub token (local only, never committed)
└── logs/
```

Key points:

- **All paths in the DB are stored twice** — host path (what you see, e.g. `/home/mario/projects/myapp`) and container path (`/workspaces/myapp`) — because the agent talks to the server with host paths, and the server reads files through the `:ro` mount. That's what `OMNISTATE_ROOTS` translation is for.
- **Persistence**: `docker compose down`/`up`, rebuilds and host reboots lose nothing — the data is just files in that folder.
- **Backup**: `cp -r data /backups/omnistate-$(date +%F)` while the container is stopped (or use `sqlite3 data/index.db ".backup ..."` while running).
- **Move the data**: stop the container → copy the folder to the new path → set `DATA_HOST_DIR` in `.env` → `docker compose up -d`.
- **Privacy**: this folder is git-ignored (`/data/`, `*.db`, `config.json`, `.env` patterns) and docker-ignored — it can never end up on GitHub or inside the image.
- After an upgrade from the old setup: if you still have the Docker named volume `omnistate_omnistate-data`, copy it into your data folder and remove it:
  ```bash
  docker compose stop
  docker run --rm -v omnistate_omnistate-data:/v -v ./data:/out alpine cp -a /v/. /out/
  docker compose up -d
  docker volume rm omnistate_omnistate-data
  ```

## Connecting an AI tool

### opencode

Add the remote MCP to your `opencode.json`:

```json
{
  "mcp": {
    "omnistate": {
      "type": "remote",
      "url": "http://localhost:8347/mcp",
      "headers": { "Authorization": "Bearer {file:/root/.config/opencode/omnistate_token}" }
    }
  }
}
```

The `{file:...}` interpolation reads the token from a local, `chmod 600` file instead of hardcoding the secret in the config. Omit `headers` when `OMNISTATE_AUTH_TOKEN` is not set.

### Antigravity

Global (all workspaces) via the GUI: agent panel `…` → **MCP Servers** → **Manage MCP Servers** → **View raw config** → edit `~/.gemini/config/mcp_config.json`:

```json
{
  "mcpServers": {
    "omnistate": {
      "serverUrl": "http://localhost:8347/mcp",
      "httpHeaders": { "Authorization": "Bearer PASTE-OMNISTATE_AUTH_TOKEN-HERE" }
    }
  }
}
```

Note: for remote (HTTP) servers Antigravity requires the **`serverUrl`** field — legacy `url`/`httpUrl` are not supported. Workspace-level alternative: `<project>/.agents/mcp_config.json`.

### Other tools

Any MCP client with **Streamable HTTP** support: point it to `http://localhost:8347/mcp` and add the `Authorization: Bearer <token>` header on session creation if auth is enabled.

## Usage

| MCP tool | What it does |
|---|---|
| `project_register` | Registers the current project (auto-registration) |
| `session_start` | Loads relevant memory, starts a session |
| `session_snapshot` | Archives done tasks, distills progress, creates a chunk |
| `task_add` / `task_update` / `task_list` | Task management |
| `memory_search` | Scored hybrid recall across projects + shared (keyword coverage, tag boost, decayed importance, familiarity); accepts `startDate`/`endDate` and natural-language dates |
| `memory_remember` | Saves a note (per-project or shared) |
| `memory_recall` / `memory_forget` | Recall and delete memory |
| `memory_reinforce` | Applies feedback signals (`used`/`important`/`irrelevant`/`incorrect`/`outdated`) that tune recall without deleting |
| `memory_recent` | Lists the latest active memories (optionally per project) |
| `memory_export` | Dumps all memories + feedback to a JSON backup file |
| `project_summary` / `project_metrics` | Project state and metrics |
| `github_scan` | Runs a GitHub scan (open PRs + metrics) |
| `github_metrics` / `github_delta` / `github_history` | GitHub scan results |
| `github_config` | Configures accounts/token for automatic scans |

## Web dashboard

Open **http://localhost:8347** in the browser:

> **Auth**: if `OMNISTATE_AUTH_TOKEN` is set, the dashboard shows an *Access token* field in the header. Paste the token there and press **Token** — the browser stores it in `localStorage` (`omnistate_auth_token`) and sends it as `Authorization: Bearer` on every API call. Do it once per browser.

- **Aggregate view**: card per project (tasks, snapshots, token savings) + shared memory; clicking a card drills into the project.
- **Per-project drill-down**: session timeline, architecture, tasks, costs — reachable from both the Overview cards and the Projects table.
- **Projects sections**: one aligned table grouped into **Active / Archived / Deleted** (path missing on disk, or remote repo deleted/archived on GitHub); the Overview lists only active projects.
- **GitHub PR Health**: stats (repos, PRs, drafts, no-reviewer, stale, issues), delta vs previous scan, charts (top repos, distribution, historical trend, per-repo trend), repos table (each repo name and count links to its GitHub PRs/issues pages), top authors/labels, "Scan now" button (awaits the reload; API responses are `no-store` so the new counts always appear immediately), "Only with open PRs" filter (persisted via shared memory).
- **Global search** across projects.
- **Accessible + actionable**: the charts expose summary stats via `aria-label` (`role="img"`), and empty states show the exact next command to run (e.g. `omnistate index /path/to/project` or Auto-discover) instead of a dead end.

## GitHub PR Health

The server scans your GitHub accounts/organizations and stores the metrics in the central DB:

- **REST** (no token): open-PR count per repo (~60 req/h).
- **GraphQL** (with PAT via `GITHUB_TOKEN` or `github_config`): up to 50 repos/request, private repos included, extended metrics (drafts, PR age, no-reviewer, stale >30d, open issues, stars).
- **Automatic scan** every 6h (configurable) + manual scans; a manual "Scan now" waits for the reload and the API is served `Cache-Control: no-store`, so the dashboard never shows a stale count.
- **Delta** and **historical trend** computed from scans stored in the DB.
- **Repo state check**: each registered project is mapped to its GitHub repo via the local `origin` remote (`gh_repo`); the server verifies it exists (`GET /repos/...`, rate-limited by a TTL) and records `gh_state` = `ok | archived | deleted`. A deleted/archived repo **wins over the local folder** when classifying the project; ambiguous results (missing token, untrusted owner, network errors) never flip the previous state.

## Architecture

```
CONTAINER omnistate (:8347)
├── /mcp        → MCP Streamable HTTP (tools & resources) — auth on session creation
├── /api/*      → REST for the dashboard — Bearer auth when enabled
├── /           → web dashboard (open shell, loads even without a token)
├── /favicon.*  → icons (open)
├── /health     → healthcheck (open)
└── /data       → SQLite index.db (memory + GitHub metrics) + shared/ + config.json
    └── bind mount of DATA_HOST_DIR (host folder, default ./data) — git-ignored, never on GitHub

Mounts:  DATA_HOST_DIR → /data (rw)   |   PROJECTS_ROOT → /workspaces (read-only)
```

- The server is the **single source of truth**; old per-project files (v1) can be imported once via `project_import_legacy`.
- Projects track `gh_repo` (parsed from the local `.git/config` origin remote — only a literal `github.com` host qualifies, credentials in the URL are discarded) and `gh_state` for the Active/Archived/Deleted lifecycle; the discovery loop also marks projects whose path disappeared as `removed`.
- Shared memory lives in `/data/shared/` as human-readable files (mirrored from the DB on every write/delete) and is visible in every project.

### How shared memory gets populated

| Path | Triggered by |
|---|---|
| `memory_remember(scope="shared")` | The **agent**, following the [session protocol](#automatic-memory-session-protocol): cross-project decisions, preferences, reusable patterns it notices while working |
| Dashboard → **Shared Memory** tab | You: type a note (+ optional tags) and Save; each entry can be deleted with ✕ |
| `POST /api/shared` | Scripts/curl against the server API |

Shared entries are **never auto-invented**: nothing extracts them from sessions or scans — they only exist because the agent (instructed by the protocol) or you explicitly saved them. At `session_start` the server returns the latest shared entries to the agent, so every project starts with the common knowledge. Entries live in the DB **and** as `.md` files under `DATA_HOST_DIR/shared/` (backup-friendly, human-readable).

## Automatic memory (session protocol)

An MCP connection only makes the tools **available** — nothing gets saved or read until the agent actually **calls** them. The agent decides what to do based on its instruction files; the **session protocol** tells it to use OmniState automatically in every project, so memory populates itself while you work.

The protocol is shipped in the repo: [`skills/omnistate-protocol.md`](skills/omnistate-protocol.md). Copy it into your client's global instructions (one-time, per machine — these files are local, never committed):

| Client | Global file (all projects) | Project-level file (single project) |
|---|---|---|
| opencode | `~/.config/opencode/AGENTS.md` | `<project>/AGENTS.md` |
| Antigravity (IDE + CLI) | `~/.gemini/GEMINI.md` (Global Rules) | `<project>/.agents/rules/omnistate.md` |

### opencode

```bash
# global: applies to every project opencode opens
mkdir -p ~/.config/opencode
cp ~/OmniState/skills/omnistate-protocol.md ~/.config/opencode/AGENTS.md
```

To enable it only for a single project instead, put the same file at `<project>/AGENTS.md` (the closest `AGENTS.md` wins; explicit chat instructions override both).

### Antigravity

**Option A — file** (works for Antigravity 2.0, IDE and CLI):

```bash
cp ~/OmniState/skills/omnistate-protocol.md ~/.gemini/GEMINI.md
```

If you already have a `GEMINI.md`, append the protocol content at the end (global rules have a 12,000-character limit per file).

**Option B — GUI**: `…` menu at the top of the agent panel → **Customizations** → **Rules** → **+ Global** → paste the protocol content.

For one project only: `<project>/.agents/rules/omnistate.md` (or **+ Workspace** in the same panel). Set the rule activation mode to **Always On** so it applies to every session.

**Note:** the protocol only helps if the MCP server itself is also configured for the client (see [Connecting an AI tool](#connecting-an-ai-tool)) — Antigravity needs `serverUrl` in `mcp_config.json`, opencode needs the `mcp` entry in `opencode.json`.

### What the agent will do once configured

1. **Session start** — `project_register` (with the current working directory) + `session_start` (loads the project's recent memory and open tasks *before* acting)
2. **During work** — `task_add` / `task_update` to track activities; `memory_remember` with `scope="shared"` for cross-project decisions and `scope="project"` for project-specific notes; `memory_search` before redoing solved work
3. **Session end** — `session_snapshot` with a distilled 2–5 line summary

No action is required from you. Verify it works after a real session: the dashboard's **Projects** tab → click your project → memory entries appear; or `curl http://localhost:8347/api/stats` and watch `memoryEntries` grow.

### Manual control (optional)

Without the protocol files you can trigger the same flow on demand — either by asking the agent ("save this session to omnistate") or via the [wrapper skills](#optional-opencode-skills) (`/start-session`, `/snapshot-session`, …).

## Privacy

The SQLite database, the shared memory, the config holding the token and all metrics **live only in a plain folder on your host** (mounted at `/data` in the container):

- The data folder (default `./data`, git-ignored) is never versioned; pick any host path with `DATA_HOST_DIR` in `.env`.
- The container has no push/export logic for the DB or metrics.
- The OmniState repo contains **only code and design** — no `.db`, `.sqlite`, `config.json` or dumps.
- The local `.env` (token and paths) is **git-ignored and docker-ignored**: it never ends up on GitHub or in the image.
- The GitHub token lives only in the `.env` or `/data/config.json` and is **never exposed** by API/dashboard/MCP (`token_set` flag + login only).
- Tests are local-only (`tests/` is git-ignored): CI does not run them; the release workflow verifies locally.
- In development the server uses git-ignored temp DBs with fake data.

## Migration from v1

The local skills (`start-session`, `snapshot-session`, `cost-setup`, `dashboard-omnistate`) and per-project memory files are **no longer used**. The v1→v2 map:

| v1 (local skill) | v2 (MCP tool) |
|---|---|
| `/start-session` | `session_start` + `memory_recall` + `project_register` |
| `/snapshot-session` | `session_snapshot` + `task_update` |
| `/cost-setup` | `project_register` + `project_import_legacy` |
| `/dashboard-omnistate` | web dashboard (single URL) |

Old per-project files (`tasks-history.json`, `chunks/`, `project-summary.md`, etc.) can be **imported once** via `project_import_legacy` to keep the history; after migration they are no longer written.

## Optional opencode skills

The v1 skills still exist as **thin wrappers** that call the MCP tools — same familiar UX, memory lives in the server. Install globally:

```bash
cp -r skills/* ~/.config/opencode/skills/
```

Skills are `.md` instruction files: the agent follows them and calls the MCP tools — no code runs on the host.

## Requirements

- Docker (with docker compose).
- An MCP client with Streamable HTTP support (opencode, Claude Code, etc.).
- A modern browser for the dashboard.

## Development

- `server/` — Python server (MCP + FastAPI/uvicorn + SQLite FTS5).
- `DESIGN.md` — full design document (architecture, DB schema, API, security).
- `tests/` — local-only test suite (`pytest tests/ -q`), never published.

## Changelog

### v2.4.0 (current)
- **Security**: optional access token (`OMNISTATE_AUTH_TOKEN` in `.env` / `server/config.py:auth_token`) protecting everything reachable over the network — `BaseHTTPMiddleware` `/_auth_required` guards `/api/*` and MCP session creation (`POST /mcp` without `Mcp-Session-Id`), while `/`, `/health`, `/favicon.*` and already-authenticated `Mcp-Session-Id` follow-ups stay open. Dashboard shows a header token prompt stored in `localStorage` (`omnistate_auth_token`); `opencode.json` uses `{file:...}` header interpolation and Antigravity uses `~/.gemini/config/mcp_config.json:httpHeaders` — no secret hardcoded.
- **Features (branding)**: `server/favicon.svg` (indigo→cyan gradient "O") served at `GET /favicon.svg` and legacy `GET /favicon.ico` (`server/app.py:Response`), linked via `<link rel="icon">` in `dashboard.html` and as `<img src="server/favicon.svg">` in the README.
- **Bugfix (MCP)**: harden `server/mcp_server.py:_logged` — new `_make_wrap` closure owns its `*argv/**kwargs`, separate async/sync wrappers with `functools.wraps`, `OMNISTATE_DEBUG` traceback, all tools now wrapped with `@_logged` (fixes `NameError: name 'a' is not defined` + unreachable dead-code after `return wrapper`).
- **Bugfix (dashboard)**: `/_project_metrics_list` TTL cache now caches only `all_project_metrics()` and recomputes `category`/`gh_state` every poll (fixes stale `archived` after de-archiving, `test_project_category_archived_via_github_scan` — 63 passed); `server/dashboard.html:api()` header-merge bug fixed (`...rest, headers` instead of clobbering `opts.headers`, fixes 401 on `Scan now`); `api_github_scan` now returns `400` on `ValueError`/`RuntimeError` and `502` on unexpected errors instead of `500`; dashboard `fetch` uses `cache: 'no-store'` and server sends `no-store` on `/api/*`.
- **Bugfix (GitHub)**: `server/github_client.py` scans use `pullRequests(first:100, states:OPEN, orderBy:updatedAt)` + `reviews.totalCount`, `noReviewer` gated on `!isDraft`, stale on `updatedAt`, retry/backoff `_get`/`_post` (`RETRIES=3`, 1.5^n on `403/429/5xx`), `github_scan` runs via `asyncio.to_thread`.
- **Performance**: `server/store.py` adds indices (`idx_memory_*`, `idx_feedback_*`), `memory_recent` bounded (`limit=200`), decayed importance anchored to `COALESCE(last_reinforced_at, created_at)`, `context_token_measure` accepts precomputed `ctx`; `server/main.py` pre-warms `tiktoken` via `logging.basicConfig`.
- **CI**: new `ci.yml` smoke workflow (compile, temporary-DB roundtrip, auth probes, version consistency) on every PR/push to `main`; `release.yml` adds `concurrency` guard; `version-check.yml` tightened semver enforcement.

### v2.3.4
- **Bugfix**: the "Only with open PRs" filter is now restored reliably after a scan or a refresh — the dashboard read its shared-memory note with a case-mismatched comparison (`content.toLowerCase()` against a non-lowercased `GH_ONLY_PR_` prefix), so it always resolved to "off" and unchecked the box after every reload. The preference is read case-insensitively and survives scans, refreshes and page loads.

### v2.3.3
- **Security**: fixed a stored XSS in the dashboard — the `esc()` function emitted a literal `"` instead of `&quot;`, leaving attribute injections possible; it now emits proper entities.
- **Performance**: fixed N+1 queries in the project-metrics dashboard — metrics for every project are now fetched in a single pass (counts + measured token savings), falling back per project only if absent.
- **UX**: chart accessibility and actionable empty states — trend/top-repo charts expose summary stats via `aria-label` (`role="img"`), and empty states show the exact next command to run.
- **Bugfix**: `/health` and the MCP server reported a hardcoded `2.0.0` instead of the real release version. The version now has a single source of truth — `server/version.py` reads `VERSION.txt` (also baked into the image at `/app/VERSION.txt`) — used by `/health`, the FastAPI app and the MCP server; a test guards against drift.
- **Metrics**: token savings are now **real measured data, not an estimate**. `session_start` returns a single bounded, deduplicated context (`recent_memory` with the 3 latest chunks at ≤600 chars + `recall` of notes at ≤400 chars, chunks/tasks excluded) built by one shared source (`Store.session_context`), and both `project_metrics` and `/api/stats` compute `tokenSavings = stored raw tokens − loaded session payload tokens` with a real tokenizer (`tiktoken` cl100k_base, BPE cache pre-warmed in the image). The old `words × 1.3 + chunks × 4000` heuristic is gone.
- **Features (memory engine)**: recall is now a scored hybrid instead of raw FTS5. `memory_search` scores results by keyword coverage + tag boost (applied only in the headroom above the relevance score), decayed importance (half-life anchored to the last `used`/`important` signal) and a saturating familiarity boost (≤0.03) drawn from recalled-in-the-last-30-days exposures; a relevance gate (0.55, 0.75 for long queries) filters noise; near-duplicate memories (token Jaccard ≥0.9) collapse instead of filling the results.
- **Features (lifecycle, non-destructive)**: memories gain `importance`, `lifecycle_state` (`active`/`outdated`/`incorrect`), `reinforcement_count`, `last_reinforced_at`, `access_count`, `last_accessed`. `memory_reinforce` applies feedback signals (`used` +0.08, `important` +0.18, `irrelevant` −0.2, `incorrect` −0.5, `outdated`) with every event appended to an audit table (`memory_feedback`); `outdated`/`incorrect` suppress from recall **without deleting**, `restore` re-activates. Note/task/chunk tables and the dashboard show the state; suppressed entries stay hidden unless `include_outdated=True`.
- **Features (temporal + audit + backup)**: `memory_search`/`memory_recall` accept `startDate`/`endDate` (ISO) and parse natural-language dates in the query ("last week", "2025-03-01", "yesterday"); pure-date queries rank by recency. `memory_recent` lists latest entries, `memory_export` dumps memories + feedback to JSON (refuses to overwrite), and `memory_feedback` for a memory is exposed via the API.

### v2.3.2
- **Bugfix**: "Scan now" could leave the GitHub PR counts unchanged — the dashboard fired the reload without awaiting it and the browser could reuse a cached `/api/*` response. The scan button now awaits the reload (with a "Scanning…" state and an error message on failure), all API calls are made with `cache: 'no-store'`, and the server sends `Cache-Control: no-store` on `/api/*` and `/health`.
- **Docs**: the session protocol now requires registering an MCP task for every significant activity (`task_add` before, `task_update` → `done` after, no batch at the end); the `commit-push` and `release-merge-prs` skills register and close their task accordingly.

### v2.3.1
- **Bugfix**: "Only with open PRs" filter now actually persists — the dashboard had signed a note field the API doesn't accept (`content` instead of `text`), so every toggle failed with "Could not save preference". The preference is stored as a `GH_ONLY_PR_`-prefixed shared-memory note matching the API schema.

### v2.3.0
- **Features**: The GitHub PR Health repos table is now clickable — the repository name and every metric (open PRs, drafts, no-reviewer, stale, issues, stars) link straight to the matching GitHub page (`/pulls`, the filtered `?q=is:pr is:open draft:true` / `no:review` views, the oldest-sorted list, `/issues`, `/stargazers`), so you can drill from a count to the actual PRs/issues without leaving the dashboard. Only `github.com` repository URLs are linked; missing or foreign URLs render as plain text.

### v2.2.0
- **Features**: Added "Only with open PRs" filter in GitHub PR Health dashboard (persisted via shared memory).
- **Performance**: Optimized metrics queries in store for task/chunk counting and token savings calculation (single-pass SQL aggregation).

### v2.1.0
- **Features**: project lifecycle in the dashboard — Projects tab grouped into aligned Active / Archived / Deleted sections; Overview shows only active projects and its cards now drill down into the project detail.
- **Features**: GitHub-authoritative project state — each project is mapped to its repo via the local `origin` remote and verified on GitHub (`gh_state` ok/archived/deleted, TTL-cached); a deleted or archived repo classifies the project as Deleted/Archived even if the local folder exists; discovery now marks projects whose path is gone as deleted (never on mount failures).
- **Features**: data now lives in a plain host folder (`DATA_HOST_DIR`, bind-mounted at `/data`) instead of a Docker named volume; shared-memory files backfilled on startup; MCP tools raise clean `ToolError`s; `session_start` returns shared memory.
- **Security**: fix stored XSS in dashboard escaping — `esc()` now also escapes quotes so project/label values can no longer break out of HTML attributes (PR #106).
- **Accessibility**: `aria-label` on all dashboard inputs/selects and high-contrast `:focus-visible` outlines for keyboard navigation (PR #107).

### v2.0.0
- **New architecture**: from file-based system with local skills to a **Docker MCP server** with central SQLite memory.
- **Web dashboard v2**: served by the server, aggregate view, per-project drill-down, shared memory, global search.
- **GitHub PR Health**: server-side GitHub scans (REST/GraphQL), open-PR metrics, historical trends and delta, stored in the central DB.
- **Shared memory**: namespace common to all projects, searchable together with projects.
- **Auto-registration**: projects are registered/indexed when they use the MCP.
- **Automatic discovery + legacy import**: the scheduler finds new projects under `PROJECTS_ROOT` and optionally imports old v1 memory files (`OMNISTATE_AUTO_IMPORT_LEGACY`).
- **Per-project drill-down**: click a project in the dashboard to browse its saved memory entries with filtering.
- **Privacy**: DB, metrics and token isolated in the host data folder (`DATA_HOST_DIR`), never versioned nor exposed.

### v1.17.0
- **Security**: Fix [HIGH] arbitrary file read / permission manipulation via symlinks in `migrate.sh` and `update.sh` by skipping symlinked configs and `.gitignore`, and removing the `cp -a` symlink copy fallback
- **Performance**: Optimize chunk label parsing in `collect-dashboard-data.py` — parse labels only for the 5 most recent chunks; use fast word-count path for older chunks
- **Accessibility**: Add dynamic ARIA labels to saved-token stats and Chart.js canvas in the dashboard for screen reader users

### v1.16.0
- **Security**: Fix [HIGH] arbitrary file read / permission manipulation in `sync-workflows.sh` by skipping symlinks entirely in the sync loop
- **Performance**: Optimize task counting and session word/file-reading overhead in `collect-dashboard-data.py` (single-pass line reads, native list counting)
- **Accessibility**: Wrap global empty-state injections in `<main id="main-content">`, remove `tabindex="0"` from non-scrollable empty containers, and pair `aria-valuetext` with `aria-valuenow` on the progress bar

### v1.15.1
- **Security**: Fix [HIGH] JSON injection in `collect-dashboard-data.sh` bash fallback logic by escaping backslashes and double quotes with native `bash` parameter expansion when `jq` is unavailable
- **Accessibility**: Fix `<main>` landmark boundaries in dashboard so the stat grid and optimization/timeline sections are enclosed, preventing skip-links from bypassing critical metrics

### v1.15.0
- **Security**: Fix arbitrary file read via symlink backup in `migrate.sh` with `mktemp -d` + `cp -a` for atomic, symlink-preserving backups (TOCTOU-safe)
- **Security**: Fix [HIGH] arbitrary file read / symlink destruction in `migrate.sh` backup and fallback copy paths by preserving symlinks with `cp -a`
- **Performance**: Batch jq string escaping into a single call in `collect-dashboard-data.sh` to eliminate N+1 subprocess spawning
- **Accessibility**: Improve screen reader semantics in dashboard — replace `<h3>` with `<p>` for numerical stats, fix heading nesting (`h3` under `h2`), keep `tabindex="0"` on scrollable timeline, and remove redundant `title` attributes

### v1.14.0
- **Security**: Fix symlink traversal bypass in `migrate.sh` by replacing `cp -a` with `mktemp` + `cat` + `mv` for atomic, symlink-safe file writes and preserving file attributes
- **Performance**: Consolidate `collect-dashboard-data.py` file reads into a single pass with early exit to prevent redundant disk I/O
- **UX**: Enhance dashboard metrics with exact token tooltips and number formatting

### v1.13.0
- **Security**: Fix JSON injection in `sync-workflows.sh` by escaping backslashes and double quotes before injecting filenames into manually constructed JSON
- **Performance**: Cache multiple chunk metrics simultaneously in `collect-dashboard-data.py` to prevent redundant I/O
- **UX**: Fix contrast on dashboard stat cards by removing opacity modifier that caused WCAG contrast failures

### v1.12.2
- **Security**: Fix JSON injection in dashboard data — properly escape `costTotal` via `jq -n --arg` in `collect-dashboard-data.sh`
- **UX**: Improve empty state CLI command scannability in dashboard (monospace styling via `innerHTML` with static strings)

### v1.12.1
- **Bugfix**: Fix double-escaping of project name in `collect-dashboard-data.sh` that produced invalid JSON output (removed redundant manual escaping now that `jq -n --arg` handles it)

### v1.12.0
- **Security**: Fix JSON injection vulnerabilities in `collect-dashboard-data.sh` (awk backslash escaping bypass, quote/backslash escaping for dates, labels, project name)
- **Performance**: Avoid eager evaluation of `dict.get()` default argument in `collect-dashboard-data.py` (lazy dict lookup passes)
- **Accessibility**: Improve screen reader semantics for metrics and empty states in dashboard (`role="list"`/`role="listitem"`)

### v1.11.0
- **Security**: Fix symlink traversal mitigation bypass in `migrate.sh` (`cp -a` preserving symlinks)
- **Security**: Fix CRITICAL symlink traversal vulnerability in `mktemp` mitigation across `migrate.sh` and `sync-workflows.sh`
- **Accessibility**: Add skip-to-main-content link and `<main>` landmark to dashboard
- **Accessibility**: Add semantic `list`/`listitem` roles to dynamically generated dashboard lists
- **Performance**: Cache config JSON loads and per-chunk word counts in `collect-dashboard-data.py` to eliminate redundant disk I/O

### v1.10.0
- **Security**: Fix symlink traversal vulnerabilities in `update.sh` using `mktemp` + `mv` for atomic file operations
- **Performance**: Optimize skill directory copying to prevent N+1 process spawning overhead
- **UX**: Add chart empty state for better context in dashboard

### v1.9.4
- **Security**: Fix symlink traversal vulnerability in `sync-workflows.sh` using `mktemp` + `mv` for atomic file operations
- **UX**: Improve dark mode text contrast for secondary labels in dashboard
- **Performance**: Optimize JSON loading and task counting in Python dashboard script

### v1.9.3
- **Security**: Fix symlink traversal vulnerabilities in shell scripts (`migrate.sh`, `collect-dashboard-data.sh`) using `mktemp` + `mv` for atomic file operations
- **UX**: Improve dark mode contrast and screen reader accessibility in dashboard
- **Accessibility**: Add `aria-hidden`/`sr-only` labels to status indicator

### v1.9.2
- **Performance**: Optimize file reading in Python dashboard script
- Use line-by-line iteration instead of `read_text().split()`
- Add error handling for file read operations

### v1.9.1
- **UX**: Style inline CLI commands in empty states
- **Performance**: Optimize resource loading in dashboard (defer chart.js, preconnect fonts)

### v1.9.0
- **UX**: Improve empty states with helpful CTAs and actionable subtext
- **Security**: Fix gitignore substring matching vulnerability
- **Security**: Fix bash arithmetic injection risk
- **Performance**: Batch `wc -w` calls to remove N+1 overhead
- **Performance**: Replace external processes with native bash string matching

### v1.8.0
- **UX**: Add empty states to dashboard data views

### v1.7.1
- **Performance**: Replace `basename` with parameter expansion for performance
- **Security**: Fix XSS vulnerability in JSON escaping (`<` and `>`)

### v1.7.0
- **Security**: Escape `<` in dashboard JSON to prevent XSS
- **Security**: Replace `innerHTML` with DOM building to fix XSS
- **Accessibility**: Add ARIA progressbar roles to dashboard
- **Performance**: Batch file copy, subprocess, and jq query operations

### v1.6.1
- **Security**: Fix command injection in Python embedded scripts

### v1.6.0
- **Performance**: Optimize JSON parsing in dashboard collection script using `jq`
- **Accessibility**: Improve dashboard keyboard and screen reader accessibility

### v1.5.1
- **Support section**: Added Buy Me a Coffee link

### v1.5.0
- **Platform-specific installation**: Skills installed in correct format per platform
- **Smart detection**: Detects which platform your project uses
- **opencode/Claude Code**: Subdirectory + `SKILL.md` format
- **Antigravity/Kilocode/Roo**: Flat `.md` workflow format
- **Mixed projects**: Supports multiple platforms simultaneously

### v1.4.0
- **Migration scripts**: Auto-migrate `antigravity.config.json` → `omnistate.config.json`
- **Safe backups**: Old configs backed up to `.omnistate/backups/` before migration
- **Git safety**: Old config files added to `.gitignore` automatically
- **Idempotent migration**: Safe to run multiple times without side effects

### v1.3.0
- **Universal**: Works with any AI coding tool, not just specific platforms
- **Auto-detect**: Installer finds all installed AI tools and syncs to all of them
- **Auto-update**: Skills and scripts auto-update from GitHub daily
- **Renamed config**: `antigravity.config.json` → `omnistate.config.json`
- **Platform-agnostic**: No more hardcoded platform names in skills or templates
- **New config**: `omnistate.config.json` with empty model fields (user fills in their own)

### v1.2.0
- opencode native support with `.opencode/skills/` format
- Multi-platform installer

### v1.1.3
- DOM optimization for dashboard (~80% faster)
- XSS prevention with textContent

### v1.1.2
- Auto-generated documentation
- Cleaner dist/ structure

### v1.1.1
- Background sync and auto-update
- Task auto-archiving
- Dashboard auto-refresh

---

*OmniState v2 — Multi-project persistent memory MCP server.*