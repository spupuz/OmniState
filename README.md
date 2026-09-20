# OmniState v2.0.0

**Multi-project persistent memory MCP server**, with a built-in web dashboard.

OmniState v2 is a **Docker container** that runs as an **MCP server** (Model Context Protocol): it indexes the memory of all your projects into a **single central SQLite database**, offers **cross-project search** and **shared memory**, and integrates **GitHub PR Health** monitoring directly in the web dashboard.

No local skills, no memory files scattered across projects: everything lives in the server.

## Features

- **MCP server** (Streamable HTTP on `/mcp`): connects to opencode, Claude Code and other AI tools as a remote MCP.
- **Central memory**: all projects indexed in one SQLite (FTS5) in the `/data` volume.
- **Auto-registration**: when you use the MCP in a project, the server registers and indexes it automatically.
- **Per-project + shared**: isolated memory for each project + shared memory common to all.
- **Cross-project search**: full-text across all projects and the shared memory.
- **Sessions**: `session_start` / `session_snapshot` replace the old `/start-session` and `/snapshot-session` skills.
- **Web dashboard** on `:8347`: aggregate view, per-project drill-down, shared memory, global search.
- **GitHub PR Health**: scans open PRs of your accounts/orgs with metrics (drafts, no-reviewer, stale, issues), historical trends and delta — stored in the central DB.
- **Privacy-first**: the DB, the metrics and the token **never leave the container volume** and never end up on GitHub.

## Installation (Docker)

```bash
git clone https://github.com/spupuz/OmniState.git
cd OmniState

# 1. Configuration: create your .env (NEVER committed)
cp .env.example .env
nano .env    # set PROJECTS_ROOT to your projects path

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
| `OMNISTATE_SCAN_INTERVAL_SECONDS` | — | Seconds between project discovery scans (default `300`). |

The file also holds the GitHub token: **do not share it, do not commit it, do not paste it**. If you lose it, rotate it on GitHub.

Verify: `curl http://localhost:8347/health` → `OK`.

## Connecting an AI tool

### opencode

Add the remote MCP to your `opencode.json`:

```json
{
  "mcp": {
    "omnistate": { "type": "remote", "url": "http://localhost:8347/mcp" }
  }
}
```

### Antigravity

Global (all workspaces) via the GUI: agent panel `…` → **MCP Servers** → **Manage MCP Servers** → **View raw config** → edit `~/.gemini/config/mcp_config.json`:

```json
{
  "mcpServers": {
    "omnistate": { "serverUrl": "http://localhost:8347/mcp" }
  }
}
```

Note: for remote (HTTP) servers Antigravity requires the **`serverUrl`** field — legacy `url`/`httpUrl` are not supported. Workspace-level alternative: `<project>/.agents/mcp_config.json`.

### Other tools

Any MCP client with **Streamable HTTP** support: point it to `http://localhost:8347/mcp`.

## Usage

| MCP tool | What it does |
|---|---|
| `project_register` | Registers the current project (auto-registration) |
| `session_start` | Loads relevant memory, starts a session |
| `session_snapshot` | Archives done tasks, distills progress, creates a chunk |
| `task_add` / `task_update` / `task_list` | Task management |
| `memory_search` | Cross-project + shared memory full-text search |
| `memory_remember` | Saves a note (per-project or shared) |
| `memory_recall` / `memory_forget` | Recall and delete memory |
| `project_summary` / `project_metrics` | Project state and metrics |
| `github_scan` | Runs a GitHub scan (open PRs + metrics) |
| `github_metrics` / `github_delta` / `github_history` | GitHub scan results |
| `github_config` | Configures accounts/token for automatic scans |

## Web dashboard

Open **http://localhost:8347** in the browser:

- **Aggregate view**: card per project (tasks, snapshots, token savings) + shared memory.
- **Per-project drill-down**: session timeline, architecture, tasks, costs.
- **GitHub PR Health**: stats (repos, PRs, drafts, no-reviewer, stale, issues), delta vs previous scan, charts (top repos, distribution, historical trend, per-repo trend), repos table, top authors/labels, "Scan now" button.
- **Global search** across projects.

## GitHub PR Health

The server scans your GitHub accounts/organizations and stores the metrics in the central DB:

- **REST** (no token): open-PR count per repo (~60 req/h).
- **GraphQL** (with PAT via `GITHUB_TOKEN` or `github_config`): up to 50 repos/request, private repos included, extended metrics (drafts, PR age, no-reviewer, stale >30d, open issues, stars).
- **Automatic scan** every 6h (configurable) + manual scans.
- **Delta** and **historical trend** computed from scans stored in the DB.

## Architecture

```
CONTAINER omnistate (:8347)
├── /mcp        → MCP Streamable HTTP (tools & resources)
├── /api/*      → REST for the dashboard
├── /           → web dashboard
└── /data       → SQLite index.db (memory + GitHub metrics) + shared/ + config.json
    └── Docker named volume (omnistate-data) — never in the repo, never on GitHub
```

- The server is the **single source of truth**; old per-project files (v1) can be imported once via `project_import_legacy`.
- Shared memory lives in `/data/shared/`; shared entries are visible in every project.

## Automatic memory (session protocol)

The MCP connection makes the tools **available**; the session protocol makes them **automatic**. The protocol file is shipped in the repo (`skills/omnistate-protocol.md`) — copy it to your client's global instructions:

| Tool | Global file | Purpose |
|---|---|---|
| opencode | `~/.config/opencode/AGENTS.md` | Protocol: `project_register`+`session_start` at session start, `session_snapshot` at the end, `memory_remember` for notes |
| Antigravity | `~/.gemini/GEMINI.md` (Global Rules) | Same protocol, all workspaces |

## Privacy

The SQLite database, the shared memory, the config holding the token and all metrics **live only in the container's `/data` volume**:

- `/data` is never mounted inside a repo nor versioned.
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

### v2.0.0 (current)
- **New architecture**: from file-based system with local skills to a **Docker MCP server** with central SQLite memory.
- **Web dashboard v2**: served by the server, aggregate view, per-project drill-down, shared memory, global search.
- **GitHub PR Health**: server-side GitHub scans (REST/GraphQL), open-PR metrics, historical trends and delta, stored in the central DB.
- **Shared memory**: namespace common to all projects, searchable together with projects.
- **Auto-registration**: projects are registered/indexed when they use the MCP.
- **Automatic discovery + legacy import**: the scheduler finds new projects under `PROJECTS_ROOT` and optionally imports old v1 memory files (`OMNISTATE_AUTO_IMPORT_LEGACY`).
- **Per-project drill-down**: click a project in the dashboard to browse its saved memory entries with filtering.
- **Privacy**: DB, metrics and token isolated in the `/data` volume, never versioned nor exposed.

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