# OmniState v2 — Design: MCP Server + Web Dashboard (Docker)

Status: **draft under review** — no code was written until approval.
Agreed decisions: **Docker** container, **MCP-only** (no more local skills: the MCP server is the single memory), **auto-registration** of projects when they use the MCP, **dashboard v2 only** (static generator removed), **English-only** project.

---

## 1. Context and goals

Today OmniState v1 was a **file-based** memory system, copied into every project:

| Per-project | Purpose |
|---|---|
| `tasks-history.json`, `tasks-archive.json` | Active / archived tasks |
| `chunks/*.md` | Session snapshots |
| `project-summary.md` | Architecture and state |
| `omni_cost.json` | API costs |
| `omnistate.config.json` | Config |
| `omnistate-dashboard.html` | Static dashboard (per-project) |

**v1 limitations:**
- No central index: every project was an island, no cross-project search.
- No shared memory (the only `.omnistate/shared-workflow.json` was a workflow list, not memory).
- Static dashboard, manually regenerated, single project, dead data.
- Skills (start/snapshot/cost-setup/dashboard) only touched local files.

**v2 goal:** an **OmniState server** running as a Docker container that is the **single** persistent memory (no local skills, no memory files in projects), offers **cross-project search + shared memory** via **MCP**, and exposes a **web dashboard** as the server UI itself.

---

## 2. Target architecture

One Python process (uvicorn) in the container, two interfaces:

```
┌─────────────────────────── CONTAINER (omnistate) ───────────────────────────┐
│                                                                              │
│   uvicorn :8347                                                              │
│   ├── /mcp            → MCP Streamable HTTP (official `mcp` SDK)             │
│   ├── /api/*          → REST for the dashboard                               │
│   ├── /               → web dashboard (HTML+JS, current design extended)     │
│   └── /health         → healthcheck                                          │
│                                                                              │
│   SQLite index   /data/index.db   (persistent volume)                        │
│   Shared memory  /data/shared/*.md (persistent volume)                       │
│   Config         /data/config.json (host↔container root mapping)             │
│                                                                              │
│   Scheduler: periodic scan of mounted roots + scheduled GitHub scans         │
└───────────────┬───────────────────────────────────────┬──────────────────────┘
                │ volumes                              │ port 8347
        ┌───────▼────────┐                     ┌────────▼─────────┐
        │ /workspaces     │                     │ AI client        │
        │ (projects root) │                     │ opencode/Claude  │
        │ read-only :ro   │                     │ (remote MCP)     │
        └─────────────────┘                     └──────────────────┘
                                 ┌──────────┐
                                 │ Browser  │  → http://localhost:8347
                                 └──────────┘
```

**Principles:**
- The MCP server is the **single source of truth**: memory lives in `/data/index.db` and `/data/shared/`. No local skills, no memory files written into projects.
- Old per-project files (`tasks-history.json`, `chunks/`, etc.) can be **imported once** (migration) but are no longer written nor managed.
- The server never runs shell commands with unsanitized input and never reads files outside the mounted roots.

---

## 3. Docker container

### Volume layout

| Volume | Container mount | Purpose |
|---|---|---|
| user's projects root (e.g. `~/projects`) | `/workspaces` | Projects to **read** (discovery + legacy import) |
| named volume `omnistate-data` | `/data` | `index.db` (single memory), `shared/`, `config.json`, `logs/` |

HTTP/MCP port is **8347** (configurable). Projects are mounted **read-only** (`:ro`): the server never writes into the user's projects.

### Host ↔ container mapping

The path the AI tool sees on the host (e.g. `/home/user/projects/ProjectX`) **is not** the same seen in the container (`/workspaces/ProjectX`). The server translates paths via `/data/config.json`:

```json
{
  "port": 8347,
  "roots": [
    { "host": "/home/user/projects", "container": "/workspaces" }
  ],
  "scan_interval_seconds": 300,
  "reindex_on_change": true
}
```

When an MCP tool receives a host path (e.g. `project_register("/home/user/projects/ProjectX")`), the server:
1. finds the matching host root → derives the container path,
2. verifies the path lives inside the root (no arbitrary reads),
3. indexes it.

### Container configuration via `.env`

`docker-compose.yml` reads a local **`.env`** file (git-ignored and docker-ignored; documented template: `.env.example`):

| Variable | Purpose |
|---|---|
| `PROJECTS_ROOT` | absolute host path of the projects root (volume mount + path translation) |
| `OMNISTATE_HOST_PORT` | host port (default 8347; container always listens on 8347) |
| `GITHUB_ACCOUNTS` | accounts/orgs to scan (empty = disabled) |
| `GITHUB_TOKEN` | optional PAT (GraphQL + private repos + extended metrics) |
| `GITHUB_SCAN_INTERVAL_HOURS` | hours between automatic scans (default 6) |
| `OMNISTATE_SCAN_INTERVAL_SECONDS` | seconds between discovery scans (default 300) |

### `docker-compose.yml` (draft)

```yaml
services:
  omnistate:
    build: .
    container_name: omnistate
    env_file: .env
    ports:
      - "${OMNISTATE_HOST_PORT:-8347}:8347"
    volumes:
      - ${PROJECTS_ROOT:-/home/youruser/projects}:/workspaces:ro
      - omnistate-data:/data
    environment:
      - OMNISTATE_PORT=8347
      - OMNISTATE_DATA=/data
      - OMNISTATE_ROOTS=${PROJECTS_ROOT:-/home/youruser/projects}:/workspaces
    restart: unless-stopped

volumes:
  omnistate-data:
```

---

## 4. Data model (SQLite `/data/index.db`)

### `projects` table

```sql
CREATE TABLE projects (
  id              INTEGER PRIMARY KEY,
  name            TEXT UNIQUE NOT NULL,        -- project name (dir basename)
  host_path       TEXT NOT NULL,
  container_path  TEXT NOT NULL,
  last_indexed_at TEXT,
  status          TEXT DEFAULT 'active',       -- active | removed
  created_at      TEXT
);
```

### `memory` table (single table for per-project + shared)

```sql
CREATE TABLE memory (
  id          INTEGER PRIMARY KEY,
  project_id  INTEGER REFERENCES projects(id),  -- NULL = shared
  scope       TEXT NOT NULL DEFAULT 'project',  -- 'project' | 'shared'
  kind        TEXT NOT NULL,                    -- summary|task|chunk|note|decision
  title       TEXT,
  content     TEXT NOT NULL,
  tags        TEXT DEFAULT '[]',                -- JSON array
  source_file TEXT,                             -- origin file in the project
  created_at  TEXT,
  updated_at  TEXT
);

CREATE VIRTUAL TABLE memory_fts USING fts5(content, title, tags, content='memory');
```

- `project_id = NULL` → **shared** memory (common to all projects).
- Entries are written **by the server** via MCP tools (`memory_remember`, session snapshot, etc.) — no longer from files.
- Optional migration: the indexer can import old per-project files (`tasks-history.json`, `chunks/`, `project-summary.md`, `omni_cost.json`) once as `memory` entries to preserve history.
- **FTS5** = SQLite native full-text search (parameterized queries, no SQL injection).

### Optional legacy import (one-shot)

| Source | Imported entries |
|---|---|
| `project-summary.md` | `summary` (title, architecture, state) |
| `tasks-history.json` | `task` (title, status, timestamp) |
| `tasks-archive.json` | `task` (status=archived) |
| `chunks/*.md` | `chunk` (label from first line, content, date) |
| `omni_cost.json` | `note` (cost totals, by_model) |

### GitHub PR Health tables (CheckGitHubRepo integration)

Same schema as the `github_pr_checker.html` tool (in-browser), but living in the server's central DB:

```sql
CREATE TABLE gh_scans (
  id          INTEGER PRIMARY KEY,
  timestamp   TEXT NOT NULL,               -- ISO
  accounts    TEXT,                        -- scanned accounts/orgs
  method      TEXT,                        -- 'rest' | 'graphql'
  total_repos INTEGER,
  total_prs   INTEGER
);

CREATE TABLE gh_repos (
  id            INTEGER PRIMARY KEY,
  scan_id       INTEGER REFERENCES gh_scans(id),
  owner         TEXT, name TEXT, full_name TEXT, url TEXT,
  stars         INTEGER, language TEXT,
  is_fork       INTEGER, is_archived INTEGER, is_private INTEGER,
  open_prs      INTEGER, draft_prs INTEGER, no_reviewer INTEGER,
  stale_prs     INTEGER, oldest_pr_days INTEGER, open_issues INTEGER,
  updated_at    TEXT
);

CREATE TABLE gh_authors (
  id INTEGER PRIMARY KEY, scan_id INTEGER, author TEXT, pr_count INTEGER
);

CREATE TABLE gh_labels (
  id INTEGER PRIMARY KEY, scan_id INTEGER, label TEXT, pr_count INTEGER
);

CREATE INDEX idx_gh_repos_scan ON gh_repos(scan_id);
CREATE INDEX idx_gh_scans_ts ON gh_scans(timestamp);
```

Every scan is stored as a `gh_scans` row with all its `gh_repos` + `gh_authors`/`gh_labels`, so **historical trends and delta** (vs previous scan) are direct SQL queries on the central DB.

---

## 5. MCP server

### Transport

**Streamable HTTP** on `/mcp` (the only transport that crosses the container cleanly). The AI client configures it as a remote MCP:

```json
// opencode.json
{
  "mcp": {
    "omnistate": { "type": "remote", "url": "http://localhost:8347/mcp" }
  }
}
```

### Tools

| Tool | Description |
|---|---|
| `project_list` | Lists registered projects with metrics |
| `project_register(path?)` | Registers the current project (or given path) — **auto-registration** |
| `project_summary(project)` | Distilled summary (architecture + state) of a project |
| `project_metrics(project)` | Active/archived/done tasks, snapshots, token savings (logic from `collect-dashboard-data`, now server-side) |
| `project_import_legacy(project)` | One-shot import of old per-project files (migration) |
| `session_start(project)` | **Replaces `/start-session`**: loads relevant memory, starts a session |
| `session_snapshot(project, summary?)` | **Replaces `/snapshot-session`**: archives done tasks, distills progress, creates a chunk |
| `task_add(project, title, status?)` | Adds a task |
| `task_update(project, id, status?)` | Updates a task (→ done ⇒ ready for snapshot) |
| `task_list(project, status?)` | Lists tasks |
| `memory_search(query, project?, scope=all\|project\|shared, limit=10)` | Cross-project + shared full-text search |
| `memory_remember(text, project?, scope=shared\|project, tags?)` | Saves a note (shared or per-project) |
| `memory_recall(project)` | Returns relevant memory for session start (reduced context) |
| `memory_forget(id)` | Deletes an entry |
| `github_scan(accounts?, extended?, include_forks?, include_archived?)` | Runs a GitHub scan (REST or GraphQL) and stores metrics in the DB |
| `github_metrics()` | Latest scan totals (repos, PRs, drafts, no-reviewer, stale, issues) |
| `github_delta()` | Delta vs previous scan |
| `github_history(metric?, top_n?)` | Historical open-PR trend (total and per-repo) |
| `github_top_authors()` / `github_top_labels()` | Aggregations |
| `github_config(accounts?, token?, extended?)` | Stores accounts/token/config for automatic scans |

> The old skills `start-session`, `snapshot-session`, `cost-setup`, `dashboard-omnistate` are no longer distributed as code: their flows are MCP tools. Thin wrapper skills (markdown-only) remain available in `skills/` for familiar UX. Existing skills in projects can stay until migration, but are no longer part of the product.

### Resources

| URI | Content |
|---|---|
| `omnistate://projects` | Projects list |
| `omnistate://projects/{name}/summary` | Per-project summary |
| `omnistate://projects/{name}/tasks` | Indexed tasks |
| `omnistate://shared` | Shared memory |
| `omnistate://search?q=...` | Search results |
| `omnistate://github/metrics` | Latest GitHub scan |
| `omnistate://github/history` | Historical open-PR trend |

### Tool schema (Zod/Pydantic example)

- `memory_search`: `query: str` (required), `project: str?`, `scope: enum[all,project,shared]` (default `all`), `limit: int` (default 10, max 50).
- `memory_remember`: `text: str` (required), `scope` (default `shared`), `project?` (required if `scope=project`), `tags: list[str]?`.
- `session_snapshot`: `project: str` (required), `summary: str?` (model-distilled).
- `task_add`: `project: str`, `title: str`, `status: enum[todo,in_progress,done]` (default `todo`).

---

## 6. Index and project discovery (auto-registration)

The requirement: *"when a project uses the MCP server, it should automatically have memory or be added to memory"*.

Two complementary mechanisms:

1. **On demand (auto-registration):** the AI, when starting work in a project, calls `project_register(<path>)`. It is the first step of the session flow: the agent registers the project and then uses `session_start` / `session_snapshot` directly as tools.
2. **Background scan:** the server scheduler walks the mounted roots, detects projects (looks for `opencode.json`, `.git/`, `tasks-history.json` and other markers) and registers them by itself. Rescan every `scan_interval_seconds` (default 300).

In both cases the server translates host→container paths, validates the path inside the root, and populates `projects` + `memory`.

> No skills involved: registration is an MCP tool called by the agent, or an automatic watcher discovery.

---

## 7. Web dashboard (MCP server UI)

The dashboard is no longer a static per-project file: it is the **server UI**, served at `/` and fed by the APIs.

### REST endpoints

| Endpoint | Description |
|---|---|
| `GET /` | HTML dashboard (vanilla JS + Chart.js, reuses current aesthetic) |
| `GET /health` | Server status |
| `GET /api/projects` | Aggregate of all projects (cards: tasks, snapshots, token savings) |
| `POST /api/register` | Registers a project by host path |
| `POST /api/discover` | Runs discovery of mounted roots |
| `GET /api/projects/{name}` | Detail: timeline, architecture, costs, tasks |
| `GET /api/memory?q=&project=&scope=` | Cross-project search |
| `GET /api/shared` + `POST /api/shared` | Shared memory (list / add) |
| `GET /api/stats` | Server totals (projects, memories, token savings, last sync) |
| `POST /api/github/scan` | Runs a GitHub scan (accounts/token from config or body) |
| `GET /api/github/metrics` | Latest GitHub scan |
| `GET /api/github/delta` | Delta vs previous scan |
| `GET /api/github/history?metric=&top_n=` | Historical open-PR trend |
| `GET /api/github/repos?scan_id=` | Repos table of a scan |
| `GET /api/github/authors` / `GET /api/github/labels` | Aggregations |

### New dashboard layout

```
┌──────────────────────────────────────────────────────────────┐
│ Header: OMNISTATE v2 · <server status> · last sync            │
├──────────────────────────────────────────────────────────────┤
│ Aggregate view: card per project (tasks/snapshots/tokens)     │
│ + "Shared Memory" section (tag cloud + entries)               │
├──────────────────────────────────────────────────────────────┤
│ [Project A]  [Project B]  [Project C]  (selector)             │
│ → drill-down: session timeline, architecture, tasks, costs    │
├──────────────────────────────────────────────────────────────┤
│ ── GITHUB PR HEALTH (new tab/section) ──                      │
│ Stats: repos, total PRs, drafts, no-reviewer, stale, issues   │
│ Delta vs last scan · charts (top repos, distribution,         │
│ historical trend, per-repo trend) · repos table ·             │
│ top authors + labels · "Scan now" button                      │
├──────────────────────────────────────────────────────────────┤
│ Global search bar → cross-project + shared results            │
└──────────────────────────────────────────────────────────────┘
```

- Reuses the existing design (`omnistate-dashboard.html` / `dist/templates/dashboard.html`): dark palette, glassmorphism, stat cards, timeline.
- APIs expose the same data `collect-dashboard-data.py` used to produce, so the UI can reuse current rendering.
- **v2 only**: the static generator (`collect-dashboard-data.py`/`.sh`, `dashboard.html`, `omnistate-dashboard.html`) has been **removed**. The v2 dashboard is the only UI. English-only UI.

---

## 8. GitHub PR Health (CheckGitHubRepo integration)

The functionality of [CheckGitHubRepo](https://github.com/spupuz/CheckGitHubRepo) (`github_pr_checker.html`) is moved **server-side** and integrated into the v2 dashboard.

### What the tool does today (replicated)

- **Account/org scan** (multi, comma-separated) via **GitHub API**:
  - **REST** (no token): PR count per repo via `Link` header (~60 req/h).
  - **GraphQL** (with PAT): up to 50 repos/request, includes private repos, extended metrics (draft, age, issues, reviewers, labels), ~5000 req/h.
- **Per-repo metrics**: open PRs, drafts, no-reviewer, stale (>30d), oldest PR, open issues, stars, last update, language.
- **Aggregations**: top PR authors, most frequent labels.
- **Delta**: change vs previous scan.
- **History**: every scan saved to SQLite → trend over time.

### Differences in v2 (server-side)

| Aspect | v1 (browser) | v2 (server) |
|---|---|---|
| Persistence | sql.js/WASM in-browser + IndexedDB | **Central SQLite `/data/index.db`** (`gh_*` tables) |
| Token | browser localStorage | **server config** `/data/config.json` or env `GITHUB_TOKEN` (via `.env`), never exposed by API/dashboard |
| Scan | manual from browser | manual (dashboard/MCP) + **automatic on schedule** (e.g. every 6h) |
| API calls | from the browser | from the server (rate-limit handled in one place) |

### Token security

- The token is **written only by the admin** (`GITHUB_TOKEN` in `.env` at boot, or `github_config` MCP → `/data/config.json`).
- REST APIs and the dashboard **never return the token**; they return only metadata (`token_set: true/false`, login, scopes).
- No token → scans run in REST mode (public, no extended metrics).

### Schedule

- An automatic scan runs every `GITHUB_SCAN_INTERVAL_HOURS` (default 6), plus manual scans.
- Delta is computed between the latest and previous rows in `gh_scans` (no `localStorage`).

---

## 9. Shared memory vs per-project

- **Per-project** (`project_id` set, `scope='project'`): session/task/note memory of the single project, written via MCP tools (`session_snapshot`, `task_add`, `memory_remember(scope=project)`). Isolated: a search can filter it with `project=<name>`.
- **Shared** (`project_id NULL`, `scope='shared'`): decisions, reusable patterns, preferences — visible in every project. Entries written via `memory_remember(scope=shared)`, stored in `/data/shared/` (human-readable) and indexed in `memory`.
- `scope=all` search combines both; `scope=shared` returns shared only. Shared entries can carry tags to organize them (e.g. `workflow`, `preference`, `architecture`).

---

## 10. Replacing local skills (MCP-only)

Local skills (`start-session`, `snapshot-session`, `cost-setup`, `dashboard-omnistate`) are **replaced by MCP tools** and remain only as **thin markdown wrappers** (repo `skills/` directory, installable to `~/.config/opencode/skills/`): instruction files telling the agent which MCP tools to call — no code executed on the host. 1:1 map:

| Local skill (v1, removed) | MCP tool (v2) |
|---|---|
| `start-session` | `session_start` + `memory_recall` + `project_register` |
| `snapshot-session` | `session_snapshot` + `task_update` |
| `cost-setup` | `project_register` + `project_import_legacy` |
| `dashboard-omnistate` | web dashboard v2 (single URL) |

Consequences for the repo:
- `dist/skills/*`, `.opencode/skills/*` (v1), `dist/workflows/*`, `update.sh`, `update.ps1`, `migrate.sh`, `migrate.ps1`, `dist/sync/*` are **removed**.
- The only client configuration is the remote MCP in `opencode.json` (or equivalent per tool), plus the session protocol in the client's global instructions (`~/.config/opencode/AGENTS.md`, `~/.gemini/GEMINI.md`).
- `plugin.json` describes the MCP server instead of skills.
- Repo language is **English-only**.

---

## 11. Security (host safety)

- The server runs in an **isolated container**: no skill scripts run on the host anymore (one less host risk).
- The server **never executes** shell commands from user input (no `subprocess` with unsanitized paths).
- File reads **only inside mounted roots** (resolve + prefix check), never outside.
- SQLite with **parameterized queries** (no SQL injection), FTS5.
- Dashboard: JSON escape (`<`→`\u003c`) as already done; no `innerHTML` with user input.
- No tool writes outside `/data` or the registered project.
- Optional authenticated dashboard access (defaults to localhost listen).
- **GitHub token**: only in `.env` or `/data/config.json`; never exposed via API/MCP/dashboard (only `token_set` flag + login). GitHub API calls go to `api.github.com` only (whitelist, as per host-security review).

---

## 12. Privacy: the DB and metrics never end up on GitHub

**Absolute rule:** the SQLite database (`/data/index.db`), the shared memory (`/data/shared/`), the config holding the token (`/data/config.json`, `.env`), the tests and all metrics (per-project memory, GitHub PR health, costs) **live only in the container's `/data` volume and must NEVER be versioned, committed or pushed to GitHub**.

### Physical boundaries

- `/data` is a **Docker named volume** (`omnistate-data`), mounted **only in the container**, never in the user's repo.
- The container has no "export/upload to GitHub" logic for the DB or metrics: no `git` commands, no push, no dumps.

### Repo guarantees

- The OmniState repository contains **only code + design**: no personal data files, no sample DB with real data, no `dashboard-data.json`/`index.db` with metrics.
- `.gitignore` (repo root): `*.db`, `*.sqlite*`, `/data/`, `shared/`, `config.json`, `.env`, `tests/` (local-only), `.opencode/` (personal local skills).
- The v1 git protection for project memory files is obsolete: v2 writes **nothing into projects**, so that risk disappears entirely — memory lives in `/data`.
- Legacy data imported from projects stays in `/data` (never written back to projects, never committed).

### Operational guarantees

- **Dashboard/API/MCP**: read the DB but never export it as a downloadable file into a repo.
- **No automatic dumps** into the workspace: files from any backup command go to `/data/backups/`, outside the repo.
- **GitHub PR Health**: scan results (`gh_scans`, `gh_repos`, `gh_authors`, `gh_labels`) stay in `/data/index.db` only. The dashboard renders them at runtime; no export, no writes into repos.

### Protection against accidental commits

- The `/data` volume is NEVER mounted inside a user repo (and vice versa).
- When building/testing the server locally, use a temp DB in `tmp/` (git-ignored) with fake data — never real data.
- PR rule: **any PR adding/containing a `.db`/`.sqlite`/`config.json`/`.env`/metrics dump file is rejected** (release skill check: `git diff` scan for `*.db`, `*.sqlite`, `/data/`, `.env`).
- **Tests are local-only**: `tests/` is git-ignored and docker-ignored; CI does not run them; the release workflow verifies locally before push.

---

## 13. Implementation plan (phases)

| Phase | Content | Outcome |
|---|---|---|
| **0** | Design approval | — |
| **1** | Python scaffold: `server/` (uvicorn + MCPServer + SQLite), `Dockerfile`, `docker-compose.yml`, `/health` | Container runs, health OK |
| **2** | Store + core tools: `projects`/`memory`/FTS5, tools `project_*`, `task_*`, `memory_*`, `session_*` | MCP working from opencode |
| **3** | Project discovery + legacy import (scheduler, auto-registration, v1 file migration) | Real auto-registration |
| **4** | REST API + web dashboard v2 (aggregate + shared + search) | Live server dashboard |
| **5** | **GitHub PR Health**: server-side REST/GraphQL client, `gh_*` tables, `github_*` tools, schedule, dashboard section | CheckGitHubRepo in central DB |
| **6** | Skill replacement: legacy removal (skills/workflows/update/migrate/collect-dashboard) + `plugin.json` → MCP server + English-only docs | MCP-only |
| **7** | Local-only tests (pytest store/API/MCP/GitHub) + version bump + release via `release-merge-prs` skill | v2.0.0 |

Stack: **Python 3.12 + `mcp` (official SDK) + FastAPI/uvicorn + SQLite(FTS5)**, minimal dependencies.

---

## 14. Tests (local-only)

`tests/` is **git-ignored and docker-ignored**: it never goes to GitHub. It runs locally before every commit/release (see §12).

- `pytest` for: store (schema, FTS5 search), path-traversal rejection, MCP tools (test client), API endpoints, legacy import (fake projects in tmp).
- GitHub: tests with mocked API (fake REST/GraphQL responses) for `github_scan`, `gh_*` persistence, delta and history; token security tests (never exposed).
- **Anti-leak test**: verify that data (`index.db`, `gh_*`, token config, dumps, `.env`) **never appears in the repo tree** — automatic check at release time (grep for `*.db`, `*.sqlite`, `config.json`, `.env`, `/data/` in diffs).
- Manual test: `docker compose up`, connect opencode to the remote MCP, verify `project_register` + `session_snapshot` + `memory_search` + `github_scan` + dashboard on `:8347`.

---

*Design v1 — English-only. Approved for implementation.*