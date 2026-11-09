# OmniState v2.42.0

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
- **Agent handoffs**: `memory_handoff` creates structured context handoffs (current state, completed, next steps, risks, validation) between agents or sessions, browsable in the dashboard's **Handoffs** tab.
- **Memory provenance + validity**: every memory can carry a `source` (agent/session/commit/issue) and optional `valid_from`/`valid_until` temporal bounds; insert-time deduplication via `content_hash` (SHA-256, normalized content) collapses near-identical notes (token Jaccard ≥ 0.9). Audit retention purge (`memory_feedback` 90-day) included.
- **Tag filtering**: `memory_search` accepts a `tags` parameter (comma-separated, AND logic) to narrow results to memories carrying all specified tags.
- **Memory feedback audit**: `memory_feedback_for(memory_id)` returns the full feedback audit trail for any memory entry.
- **Async backup + scheduled purge**: `db_backup_async` runs SQLite backup in a thread (non-blocking); the scheduler auto-purges expired memories (`valid_until`), old feedback (90d) and exposure records (60d).
- **Prometheus `/metrics` endpoint**: `GET /metrics` exposes `omnistate_projects_active`, `omnistate_memory_entries`, `omnistate_gh_scans`, `omnistate_version`.
- **Security headers + rate limiting**: CSP (CDN-allowed sources), Referrer-Policy, per-IP rate limit (300 req/60s on `/api/*` and `/mcp`), oversized-payload rejection (>1MB).
- **Metrics endpoint + manifest**: `GET /api/metrics`, PWA manifest (`/manifest.json`), theme-color meta, skip-link and `aria-live` for accessibility.
- **Markdown export**: `memory_export_markdown` dumps active memories as human-readable `.md` files — decisions as `ADR-XXXX.md` under `decisions/` — for versioning stable knowledge in a repository.
- **Forget with audit**: `memory_forget` accepts an optional `reason` recorded in the `memory_feedback` audit table.
- **Web dashboard** on `:8347`: aggregate view, per-project drill-down, shared memory, global search, handoffs, with unified design tokens, pill tabs/buttons/inputs, glass cards with hover lift, health badges, saved-search dropdown, native form validation, in-button loading states, non-blocking toasts, accessible tab navigation, PWA manifest support, and graphic confirmation modals for project Remove and Merge (audit-trail reason field for removal, target selection dropdown for merge).
- **Project lifecycle**: the Projects tab splits repositories into **Active / Archived / Deleted** — GitHub is authoritative: a project whose remote repo is archived or deleted on GitHub moves to those sections even if its local folder still exists (and only active projects show on the Overview). **Remove project** (soft-delete) and **Merge projects** available from the project detail view, MCP tools (`project_remove`, `project_merge`) and REST API.
- **GitHub PR Health**: scans open PRs of your accounts/orgs with metrics (drafts, no-reviewer, stale, issues), historical trends and delta — stored in the central DB. Every repo row in the dashboard links straight to its GitHub PRs and issues.
- **Optional auth**: set `OMNISTATE_AUTH_TOKEN` in `.env` to protect `/api/*` and MCP session creation with a Bearer token — dashboard prompts for it and stores it in `localStorage`; MCP clients send it via header (opencode) or `httpHeaders` (Antigravity).
- **Favicon + branding**: `server/favicon.svg` served at `/favicon.svg` and `/favicon.ico` (exempt from auth) and shown in the README and dashboard.
- **Privacy-first**: the DB, the metrics and the token **never leave your data folder** and never end up on GitHub.

## Quick Start (Linux/macOS)

```bash
git clone https://github.com/spupuz/OmniState.git && cd OmniState
cp .env.example .env && nano .env   # set PROJECTS_ROOT to your projects folder
docker compose up -d --build
# open http://localhost:8347  (dashboard)
```

For a guided install (interactive `.env` generator), use:

```bash
bash install.sh       # Linux/macOS
./install.ps1         # Windows PowerShell
```

> **Windows users:** Docker Desktop (WSL2 backend) required. Use PowerShell in the repo root. Paths use backslashes: `C:\Users\you\projects`.

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
| `SUPERMEMORY_ENABLED` | — | Enable Supermemory integration (default `true` in the shipped `.env.example`). |
| `SUPERMEMORY_API_KEY` | — | Supermemory API key. Leave the placeholder (`sm_your_local_api_key_here`) to use the **built-in local Supermemory server** that runs inside the container on port 6767 (no external account needed). Set a real key + `SUPERMEMORY_BASE_URL=https://api.supermemory.ai` to use the cloud service. |
| `SUPERMEMORY_BASE_URL` | — | Supermemory base URL (default `http://localhost:6767` for the built-in local server). |
| `SUPERMEMORY_DEFAULT_SPACE` | — | Default Supermemory namespace (default `sm_project_default`). |

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
├── index.db      ← SQLite: projects, memory (FTS5, content_hash dedup), gh_* GitHub scan tables
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
| `project_remove` | Marks a project as removed (soft delete) |
| `project_merge` | Moves all memories from source to target, marks source removed |
| `project_discover` | Scans mounted roots for new projects |
| `session_start` | Loads relevant memory, starts a session |
| `session_snapshot` | Archives done tasks, distills progress, creates a chunk |
| `task_add` / `task_update` / `task_list` | Task management |
| `memory_search` | Scored hybrid recall across projects + shared (keyword coverage, tag boost, decayed importance, familiarity); accepts `startDate`/`endDate`, `tags` (comma-separated, AND logic), and natural-language dates |
| `memory_remember` | Saves a note (per-project or shared) |
| `memory_recall` / `memory_forget` | Recall and delete memory |
| `memory_reinforce` | Applies feedback signals (`used`/`important`/`irrelevant`/`incorrect`/`outdated`) that tune recall without deleting |
| `memory_feedback_for` | Returns the feedback audit trail for a memory entry |
| `memory_recent` | Lists the latest active memories (optionally per project) |
| `memory_export` | Dumps all memories + feedback to a JSON backup file |
| `project_summary` / `project_metrics` | Project state and metrics |
| `github_scan` | Runs a GitHub scan (open PRs + metrics) |
| `github_metrics` / `github_delta` / `github_history` | GitHub scan results |
| `github_config` | Configures accounts/token for automatic scans |

## OpenCode plugin — auto-population hooks

When OmniState is used with OpenCode, the bundled plugin (`.opencode/plugins/omnistate/`) hooks into the session lifecycle and **auto-populates memory** so you never have to remember `memory_remember` / `session_start` / `session_snapshot`:

| Hook | When | Action |
|---|---|---|
| `prompt` | Every user message (≥10 chars) | Saves the prompt text as a shared memory entry (tag `opencode-prompt`) |
| `context` | On agent-loop context build | Records which tools were used (tag `opencode-tools`) |
| `compaction` | Session compaction | Auto-snapshots the summary into the project's memory |
| `session.remove` | Session ends | Auto-snapshots any pending work |

### Configuration

In `opencode.json` (or `opencode.jsonc`):

```jsonc
{
  "plugins": [
    {
      "package": "./.opencode/plugins/omnistate",
      "options": {
        "url": "http://localhost:8347",
        "project": ""          // default project for snapshot (empty = shared-only)
      }
    }
  ]
}
```

- `url` — OmniState server URL (default `http://localhost:8347`).
- `project` — default project name for session snapshots. Leave empty for shared-scope-only memory.

The plugin is **fire-and-forget**: if the OmniState server is unreachable, prompts are silently skipped (non-blocking).

## Web dashboard

Open **http://localhost:8347** in the browser:

> **Auth**: if `OMNISTATE_AUTH_TOKEN` is set, the dashboard shows an *Access token* field in the header. Paste the token there and press **Token** — the browser stores it in `localStorage` (`omnistate_auth_token`) and sends it as `Authorization: Bearer` on every API call. Do it once per browser.

- **Aggregate view**: card per project (tasks, snapshots, token savings) + shared memory; clicking a card drills into the project.
- **Per-project drill-down**: session timeline, architecture, tasks, costs — reachable from both the Overview cards and the Projects table.
- **Projects sections**: one aligned table grouped into **Active / Archived / Deleted** (path missing on disk, or remote repo deleted/archived on GitHub); the Overview lists only active projects.
- **GitHub PR Health**: stats (repos, PRs, drafts, no-reviewer, stale, issues), delta vs previous scan, charts (top repos, distribution, historical trend, per-repo trend), repos table (each repo name and count links to its GitHub PRs/issues pages), top authors/labels, "Scan now" button (awaits the reload; API responses are `no-store` so the new counts always appear immediately; accounts and scan settings are persisted via `POST /api/github/config`), "Only with open PRs" filter (persisted via shared memory), "Save config" button and Advanced Settings panel (extended, include_forks, include_archived, scan_interval_hours, stale_days).
- **Global search** across projects: live debounced search as you type, filters for project scope/name, date range and result limit, result counter, skeleton loading, inline **Copy / 👍 useful / ⭐ important / 🗑 forget** actions, and a **⭐ Saved** dropdown (persisted in `localStorage`, max 15, Esc/outside to close) that auto-saves every query and lets you reload or remove past searches.
- **Theme toggle**: the dashboard persists a light/dark/system preference (sidebar cycle button, Settings dropdown, or the `T` key) — `system` follows the OS color scheme and updates live when it changes; the sidebar icon switches between sun, moon and a monitor for system. Refined light-theme overrides for glass, table and chip surfaces.
- **Command palette** (`Ctrl/⌘+K`): jump to any tab, reload all data, export Markdown, create a handoff, toggle theme or clear search from a keyboard-first palette (`/` focuses search, `Esc` closes).
- **Handoffs tab**: browse structured agent handoffs (current state, completed, next steps, risks, validation) with a one-click form to create new ones.
- **Accessible + actionable**: the charts expose summary stats via `aria-label` (`role="img"`); dynamic grids are exposed as ARIA lists (`role="list"` / `role="listitem"`); Overview project cards and command-palette items are keyboard-operable (`role="button"`, Enter/Space); Projects table rows are focusable with Enter/Space to open the project drill-down; Overview stat cards include tooltip descriptions with accessible interactive tooltip buttons for keyboard compatibility; actionable groups are wrapped in semantic `<form>` elements so **Enter** submits natively; scrollable regions are focusable only while they actually overflow; empty states show the exact next command to run. Every dashboard button is an explicit `<button type="button">`, hover-revealed actions (e.g. the saved-search delete control) also reveal on `:focus-within`, interactive elements (`.btn`, `.tab-btn`, `.copy-btn`) show a visible `:focus-visible` ring for keyboard navigation, and form controls that lack a visible label carry an `aria-label`, and every interactive utility button (copy, reinforce, forget) carries a descriptive `aria-label` for screen-reader context.
- **Inline copy feedback**: dashboard copy buttons now show temporary '✓ Copied' visual feedback for 2 seconds after clicking, confirming the action without requiring gaze shift. This was added via the inline feedback pattern where the button text changes and then restores automatically.
- **Inline reinforce feedback**: reinforce memory buttons (👍 useful / ⭐ important) now show temporary '✓ Saved' visual feedback during the async operation — the button disables and changes text, then restores after 2 seconds, preventing double-clicks and confirming the action without gaze shift.
- **Enhanced focus management**: improved keyboard navigation with explicit focus handling when transitioning between views (project details, handoffs, palette modals) and proper focus restoration when returning to previous screens. Added `tabindex="-1"` and `focus:outline-none` to interactive headings with explicit `.focus()` calls to ensure smooth keyboard navigation and screen reader flow.
- **Native form validation**: required inputs are validated by the browser through HTML5 constraints (`required`, `type="email"`, `minlength`), so empty submissions are blocked with a localized tooltip instead of a round-trip.
- **Async submit loading states**: while a form request is in flight its submit button is disabled and shows a pending label (`Saving…`, `Registering…`, `Deleting…`); the original label and enabled state are always restored in a `finally` block, so a failed request never leaves the button stuck.
- **Non-blocking notifications**: every result and failure is reported with a transient toast in the corner (success / error / info with left-border accent), so the page context is never interrupted by a modal dialog. Toasts may include optional undo actions for certain operations. For destructive actions like memory deletion, custom accessible HTML modals replace native `confirm()` and `prompt()` dialogs, preserving required audit trail data (like deletion reasons) while improving accessibility with keyboard navigation and proper ARIA labels.

The dashboard includes accessible modals for memory deletion that support keyboard dismissal (Escape key), proper focus management and maintain all required data collection functionality.
- **Responsive mobile layout**: tables collapse into stacked cards under 640px (`data-label` header attributes), tabs scroll horizontally, toast wraps full-width, inputs go full-width.
- **Responsive sidebar navigation**: persistent sidebar on desktop; on mobile (below 1024px) it is off-canvas and toggled by the hamburger button with an overlay, and its open state is reset on viewport resize so it never covers the main content.
- **Virtual scroll**: memory-entry lists over 50 items render via chunked scroll-based windowing (only visible rows are in the DOM), keeping large project drills smooth.
- **Deep-linking**: the active tab is mirrored into the URL hash (`#overview`, `#projects`, …) so tabs survive refresh, bookmarking and back/forward navigation.
- **Dynamic version badge + English-only copy**: the header badge is injected from `VERSION.txt` via `GET /health` and kept in sync live (was hardcoded `v2`); all dashboard copy is English.

## GitHub PR Health

The server scans your GitHub accounts/organizations and stores the metrics in the central DB:

- **REST** (no token): open-PR count per repo (~60 req/h).
- **GraphQL** (with PAT via `GITHUB_TOKEN` or `github_config`): up to 50 repos/request, private repos included, extended metrics (drafts, PR age, no-reviewer, stale >30d, open issues, stars).
- **Automatic scan** every 6h (configurable) + manual scans; a manual "Scan now" waits for the reload and the API is served `Cache-Control: no-store`, so the dashboard never shows a stale count.
- **Delta** and **historical trend** computed from scans stored in the DB.
- **Token validation**: `github_config` validates the PAT against the GitHub API before saving (opt-out with `validate=false`).
- **Config persistence**: `POST /api/github/config` saves accounts and scan settings (extended, include_forks, include_archived, scan_interval_hours, stale_days) to `config.json`; the dashboard now has a "Save config" button and an Advanced Settings panel for these options.
- **Repo state check**: each registered project is mapped to its GitHub repo via the local `origin` remote (`gh_repo`); the server verifies it exists (`GET /repos/...`, rate-limited by a TTL) and records `gh_state` = `ok | archived | deleted`. A deleted/archived repo **wins over the local folder** when classifying the project; ambiguous results (missing token, untrusted owner, network errors) never flip the previous state.

The GitHub metrics collection is optimized for performance — filtering logic is pushed down to the database level via SQL `WHERE` clauses to avoid materializing unused Python dictionaries during frequent dashboard polls. This significantly reduces memory allocation and improves dashboard responsiveness, especially when processing large repositories.

## Supermemory Integration

OmniState can bridge to [Supermemory](https://github.com/supermemoryai/supermemory) — an external memory API — through a set of MCP tools and a REST API surface. This enables bidirectional sync between OmniState's project/session/task memory and Supermemory's advanced memory store.

### How it is integrated

1. **Configuration** (`server/config.py`): a `SupermemoryConfig` dataclass is part of the main `Config`, loaded from `config.json` and overridable via env vars (`SUPERMEMORY_ENABLED`, `SUPERMEMORY_API_KEY`, `SUPERMEMORY_BASE_URL`, `SUPERMEMORY_API_VERSION`, `SUPERMEMORY_DEFAULT_SPACE`).

2. **REST client** (`server/supermemory_client.py`): a thin `httpx`-based client that calls the Supermemory REST API (v5) — `search`, `profile`, `add`, `sync`, `status`. All methods are synchronous and wrapped with `asyncio.to_thread` by the MCP tools.

3. **Built-in local server** (`supermemory_server.py`): a FastAPI server on port 6767 that ships inside the container and implements the Supermemory API v5 endpoints locally. It persists data to `/data/supermemory_local.json`. The container entrypoint (`entrypoint.sh`) starts it automatically and waits for `/health` before launching OmniState.

4. **MCP bridge tools** (`server/mcp_server.py`): five tools exposed to AI agents — `supermemory_search`, `supermemory_profile`, `supermemory_add`, `supermemory_sync`, `supermemory_status`.

5. **Dashboard tab**: a "Supermemory" tab in the web dashboard with status indicator, search modal, add-memory form, and manual sync.

### Usage modes

- **Local (default)**: leave `SUPERMEMORY_API_KEY` as the placeholder `sm_your_local_api_key_here` and `SUPERMEMORY_BASE_URL=http://localhost:6767`. The built-in local server handles everything with no external account.
- **Cloud**: set a real API key and `SUPERMEMORY_BASE_URL=https://api.supermemory.ai` to use the hosted Supermemory service.

### Auto-update

The Supermemory local server in the OmniState Docker image auto-updates:

- Every hour, the OmniState scheduler controlls the GitHub releases page of the OmniState repository (which tracks releases of `supermemory_server.py`).
- If a new version is found, you can apply it with a single POST to `/api/supermemory/update`.
- The update downloads the new server code from GitHub and replaces the file atomically, then restarts the process.
- If you prefer to keep the local server at its current version, disable this check by setting `SUPERMEMORY_AUTO_UPDATE=false` (env var not implemented yet – the check is optional and only logs)

You can watch for updates via the dashboard Supermemory tab, or poll `/api/supermemory/update-check` to see if an update is available.

### References

- Supermemory project: https://github.com/supermemoryai/supermemory
- Integration doc: `SUPERMEMORY_INTEGRATION.md`
- Demo: `integration_demo.py`
- Tests: `test_supermemory_integration.py`

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
- **Performance**: `Store.all_project_metrics()` uses SQLite window functions (`ROW_NUMBER() OVER(PARTITION BY ...)`) to push sorting and top-N filtering directly to the database, eliminating Python dictionary allocations and improving token counting efficiency.
- **Performance**: New `App.get_project_metrics(project_id)` provides O(1) single-project metric lookup from the TTL-cached dictionary instead of generating a full metrics list and filtering — used by `/api/projects/{name}`, `project_summary`, and `project_metrics` MCP tools.
- All SQLite access is serialized through a single re-entrant connection lock. Bulk reads (`Store.all_project_metrics()` behind the dashboard Projects/Overview lists, and `Store.context_token_measure()` when measuring stored tokens) stream natively via `cursor.execute()` + `fetchmany(1000)` over `sqlite3.Row`, avoiding generic `q_iter()` dictionary allocations (only rows that are actually kept are cast with `dict(r)`), so allocation overhead is minimal even on large indexes and the lock is released between chunks. `Store.q_iter()` itself uses `yield from map(dict, rows)` (C-level `map`) to cut Python interpreter overhead for any remaining callers. Task fields (`status`, `title`) are projected directly in the SQL via `json_extract()`/`json_valid()` rather than parsed with `json.loads()` in Python, so no per-row JSON decoding happens in the hot path.
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
2. **During work** — `task_add` / `task_update` to track activities; `memory_remember` with `scope="shared"` for cross-project decisions and `scope="project"` for project-specific notes; `memory_search` before redoing solved work; `memory_forget` with audit trail reasons (using accessible HTML modals instead of native `confirm()`/`prompt()` dialogs for improved UX and accessibility)
3. **Session end** — `session_snapshot` with a distilled 2–5 line summary

No action is required from you. Verify it works after a real session: the dashboard's **Projects** tab → click your project → memory entries appear; or `curl http://localhost:8347/api/stats` and watch `memoryEntries` grow.

**Memory deletion improvements**: The dashboard now uses custom accessible HTML modals for memory deletion operations, replacing blocking native dialogs while preserving all required audit trail data. These modals support keyboard navigation (Escape key for dismissal), proper focus management, and maintain the full audit trail functionality for compliance.

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

## CLI alternative (omnistate-pp-cli)

If you don't have an MCP client (or prefer a shell-native workflow), OmniState ships a **printed CLI** generated with [CLI Printing Press](https://printingpress.dev). It wraps the same REST API the dashboard uses, adds a local SQLite data layer (sync, offline FTS5 search, compound analytics), and is designed for AI agents first: `--json` auto-when-piped, `--compact` for 60–80% fewer tokens, typed exit codes, `--dry-run`, and an `--agent` flag that bundles all of the above in one.

### Install

**Prerequisites:** Go 1.26.3+ and Node/npm (for `npx`).

```bash
# 1. Install the Printing Press generator (one-time)
go install github.com/mvanhorn/cli-printing-press/v4/cmd/cli-printing-press@latest

# 2. Generate the CLI from the OpenAPI spec
cli-printing-press generate \
  --spec https://raw.githubusercontent.com/spupuz/OmniState/main/openapi.json \
  --name omnistate \
  --output ~/omnistate-pp-cli

# 3. Build and install
cd ~/omnistate-pp-cli
go build -o omnistate-pp-cli ./cmd/omnistate-pp-cli
sudo cp omnistate-pp-cli /usr/local/bin/
```

Or download a pre-built binary from the [releases page](https://github.com/spupuz/OmniState/releases) (when available).

### Configure

```bash
mkdir -p ~/.config/omnistate-pp-cli
cat > ~/.config/omnistate-pp-cli/config.toml << 'EOF'
base_url = "http://localhost:8347"
auth_header = "Bearer YOUR_OMNISTATE_AUTH_TOKEN"
EOF
chmod 600 ~/.config/omnistate-pp-cli/config.toml
```

Omit `auth_header` if `OMNISTATE_AUTH_TOKEN` is not set on the server.

Verify: `omnistate-pp-cli doctor` — checks config, auth, and API connectivity.

### Use

```bash
# Stats (JSON, compact — ready for an agent to consume)
omnistate-pp-cli stats --agent

# List all projects with metrics
omnistate-pp-cli projects api-projects --agent

# Sync data locally for offline search (SQLite + FTS5)
omnistate-pp-cli sync

# Search across all synced data — offline, no API call
omnistate-pp-cli search "release v2.26" --data-source local

# Recent memory entries
omnistate-pp-cli memory recent --agent

# GitHub PR health
omnistate-pp-cli github metrics --agent
```

Add `--agent` to any command for JSON + compact + non-interactive output. Run `omnistate-pp-cli --help` for the full command list.

### CLI vs MCP vs skills

| Interface | Best for | Token cost | Offline |
|---|---|---|---|
| **MCP server** (`/mcp`) | IDE agents (opencode, Antigravity, Claude Code) — tools auto-discovered | medium | no |
| **CLI** (`omnistate-pp-cli`) | Shell agents, scripts, CI — `--json --compact` pipes | **low** | **yes** (sync) |
| **Skills** (`.md` files) | Familiar slash-commands — thin wrappers that call MCP tools | medium | no |

All three talk to the same OmniState server. The CLI adds a local SQLite cache: `sync` pulls data down, `search` finds it in milliseconds without an API call, and compound commands (`stale`, `orphans`, `load`, `health`) join across resources in ways a stateless wrapper cannot. Use MCP inside your IDE, the CLI from the terminal or CI, and skills for the familiar `/start-session` / `/snapshot-session` UX.

### Skills + CLI together

The [optional opencode skills](#optional-opencode-skills) (and the per-project `.agents/skills/`) work with either the MCP server or the CLI — they are instruction files, not code. To use the CLI as the backend instead of MCP, point the skill's `tools.omnistate.*` calls at the CLI:

```bash
# Instead of calling MCP tools, the agent can run:
omnistate-pp-cli projects api-projects --agent
omnistate-pp-cli memory recent --agent
omnistate-pp-cli hooks session-snapshot --project MyProject --summary "..." --agent
```

The skills' slash-command UX (`/start-session`, `/snapshot-session`, `/cost-setup`, `/dashboard-omnistate`) stays the same — only the transport changes.

## Requirements

- Docker (with docker compose). On Windows: Docker Desktop + WSL2 backend. On Mac: Docker Desktop / OrbStack / colima.
- An MCP client with Streamable HTTP support (opencode, Claude Code, etc.).
- A modern browser for the dashboard.

## Development

- `server/` — Python server (MCP + FastAPI/uvicorn + SQLite FTS5).
- `DESIGN.md` — full design document (architecture, DB schema, API, security).
- `tests/` — local-only test suite (`pytest tests/ -q`), never published.
- **Releases**: `.github/workflows/release.yml` auto-creates the annotated tag `vX.Y.Z` and the GitHub Release when a push to `main` changes `VERSION.txt`/`plugin.json`. It can also be re-dispatched manually (`gh workflow run release.yml`) to regenerate them for the current `VERSION.txt`; a re-run is a no-op when the tag already exists.

## Changelog

### v2.42.0 (current)

- **Performance (Bolt)**: Combine project_metrics queries — eliminates N+1 database overhead by using subselects for aggregate metrics, dramatically faster dashboard loading and fewer database round-trips.
- **Performance (Bolt)**: Optimize session context to avoid Python JSON parsing — move JSON extraction and validation to SQLite native functions, eliminating massive dictionary allocations and speeding up session start times.
- **Security (Sentinel)**: Validate supermemory update tag name to prevent path traversal in the constructed URL — rejects malformed tags that could escape the repo path.
- **Security (Sentinel)**: Validate supermemory update download URL host to prevent SSRF — only allows `raw.githubusercontent.com` and `github.com` as trusted hosts.
- **UI (Palette)**: Fix broken merge modal layout and add missing `aria-labelledby` reference — restores visual consistency with the design system and screen reader accessibility.
- **UI (Palette)**: Add missing `aria-labelledby` target and `aria-label` in merge modal — improves accessibility for screen reader users.

- **Feature (Supermemory Auto-Update)**: Local Supermemory server now auto-checks for updates via GitHub releases API every hour; dashboard shows update badge and modal to apply update (downloads new `supermemory_server.py`, replaces atomically, restarts process).
- **Feature (Supermemory Update UI)**: Custom modal dialogs replace native `confirm()`/`alert()` for update check and result, matching dashboard glass style.
- **API**: New endpoints `GET /api/supermemory/update-check` and `POST /api/supermemory/update` for programmatic update control.
- **Scheduler**: Background job logs available updates; non-blocking, optional (only runs when Supermemory enabled).

- **Performance (Bolt)**: Optimized `project_metrics` query combines two separate SQLite queries into a single subselect for total count, reducing database round-trips by ~50% per call.

See the full changelog in the [GitHub Releases](https://github.com/spupuz/Omnistate/releases) section of the repository.

## About

**OmniState** is built and maintained by [**Alessandro "spupuz"**](https://github.com/spupuz) — a Vibe Coder, Artist, Father & Husband, Videogamer working for a multinational IT Vendor company, always looking for the next project.

- 🌍 Based in Italy
- 🎥 YouTube: [@spupuz](https://youtube.com/@spupuz)
- 🐦 X/Twitter: [@spupuz](https://x.com/@spupuz)
- 📸 Instagram: [spupuz](https://www.instagram.com/spupuz/)

### What OmniState is for

OmniState solves a common problem for developers working across multiple projects: **persistent, cross-project memory for AI assistants**. Instead of scattering memory files across projects or losing context between sessions, OmniState provides a single central MCP server that:

- Indexes memory for **all your projects** in one SQLite database
- Offers **cross-project search** and **shared memory** common to all projects
- Integrates **GitHub PR Health** monitoring in a built-in web dashboard
- Provides **session management** (start/snapshot) and **agent handoffs** between AI sessions
- Supports **Supermemory** integration for persistent memory across conversations (real REST API via httpx: search, profile, add, sync, status)

It's designed to work with **opencode**, **Claude Code**, and other AI tools that support the Model Context Protocol (MCP).

### Related Projects

- [VibeNVR](https://github.com/spupuz/VibeNVR) — Simple, privacy-respecting local NVR
- [proxmox-scripts](https://github.com/spupuz/proxmox-scripts) — Proxmox VE helper scripts

### License

This project is open source and available under the **MIT License**. See [LICENSE](LICENSE) for the full text.

DISCLAIMER: THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

---

*OmniState — Multi-project persistent memory MCP server. Made with ❤️ in Italy.*

## Security & Data Protection

**NEVER commit sensitive information.** The repository has strict safeguards:

- `.env` files, database files (`*.db`, `*.sqlite3`), and runtime data (`/data/`) are **gitignored** and never leave your machine.
- The `.gitignore` explicitly excludes secrets, local configs, and all runtime state (see DESIGN.md §10b).
- Tests are local-only and gitignored.
- GitHub CI runs in isolated environments and never accesses your local data.
