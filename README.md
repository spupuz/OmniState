# OmniState v1.16.0

**Universal Persistent Memory** for any AI coding tool.
Works with opencode, Antigravity, Kilocode, Roo Code, Claude Code, and more.

Tracks tasks, archives progress, and minimizes context window usage — saving thousands of tokens per session.

## Features

- **Universal**: Works with any AI coding tool (opencode, Antigravity, Kilocode, Roo Code, Claude Code)
- **Auto-Update**: Self-updates from GitHub, syncs skills to all detected platforms
- **Visual Dashboard**: HTML dashboard with real-time metrics and token savings
- **Smart Archiving**: Auto-moves completed tasks to keep context lean
- **Context Purge**: Cleans AI context on startup to prevent distractions
- **Git Protection**: Automatically protects memory files from commits

## Install

```bash
# Clone and install globally
git clone https://github.com/spupuz/OmniState.git ~/OmniState
cd ~/OmniState

# Linux / macOS
bash update.sh

# Windows (PowerShell)
.\update.ps1
```

The installer auto-detects your AI coding tools and installs skills to all of them.

### Manual Setup (opencode)

If auto-detection doesn't work, add to your `opencode.json`:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "skills": {
    "paths": ["~/.agents/skills"]
  }
}
```

## Upgrade from v1.2.x or earlier

If you have an existing OmniState installation from v1.2.x or earlier, follow these steps to upgrade to v1.5.0 (universal version).

### What Changed in v1.5.0

- **Platform-specific installation**: Skills installed in correct format per platform
- **Smart detection**: Detects which platform your project uses
- **Config renamed**: `antigravity.config.json` → `omnistate.config.json`
- **Schema updated**: Removed `compression_level`, added `project_name`, model fields now empty
- **Universal**: Works with all AI coding tools, not just Antigravity

### Automatic Migration

The upgrade process automatically migrates your config:

```bash
# Linux / macOS
cd ~/OmniState
git pull origin main
bash update.sh --auto /path/to/your/project

# Windows
cd ~/OmniState
git pull origin main
.\update.ps1 -Auto C:\path\to\your\project
```

**What happens:**
1. `antigravity.config.json` is backed up to `.omnistate/backups/`
2. Config is migrated to `omnistate.config.json` with updated schema
3. Old config is added to `.gitignore` for safety

### Manual Migration

If automatic migration doesn't work:

```bash
# Linux / macOS
bash migrate.sh /path/to/your/project

# Windows
.\migrate.ps1 -Target C:\path\to\your\project
```

### Verify Migration

After upgrading, check that:
- `omnistate.config.json` exists in your project root
- `antigravity.config.json` no longer exists (or is in `.gitignore`)
- Your model settings are correct (old Gemini defaults are now empty)

### Troubleshooting

- **Both configs exist**: The migration script will prompt you before overwriting
- **Backup location**: Backups are stored in `.omnistate/backups/` (git-ignored)
- **Manual cleanup**: If needed, manually remove `antigravity.config.json` and add it to `.gitignore`

## Usage

| Command | When | What it does |
|---------|------|-------------|
| `/cost-setup` | First time | Creates memory files, git protection, cost routing |
| `/start-session` | Session start | Context purge, loads summaries, shows status |
| `/snapshot-session` | Session end | Archives tasks, distills progress, creates chunk |
| `/dashboard-omnistate` | Any time | Generates visual HTML dashboard |

### Quick Start

1. **Init**: Run `/cost-setup` in your project
2. **Start**: Run `/start-session` at the beginning of each session
3. **Save**: Run `/snapshot-session` at the end to persist state
4. **View**: Open `omnistate-dashboard.html` in a browser

## Platform-Specific Installation

OmniState automatically detects which AI coding tool your project uses and installs skills in the correct format:

### How It Works

```bash
# Sync to a project
bash update.sh --sync /path/to/your/project
```

The script will:
1. Detect which platform your project uses (from `opencode.json`, `.kilo/`, `.agents/`, etc.)
2. Install skills in the correct format for that platform
3. Also install globally to detected platforms

### Skill Formats by Platform

| Platform | Format | Example |
|----------|--------|---------|
| **opencode** | Subdirectory + `SKILL.md` | `.opencode/skills/start-session/SKILL.md` |
| **Claude Code** | Subdirectory + `SKILL.md` | `.agents/skills/start-session/SKILL.md` |
| **Antigravity** | Flat `.md` files | `.agents/workflows/start-session.md` |
| **Kilocode** | Flat `.md` files | `.kilo/commands/start-session.md` |
| **Roo Code** | Flat `.md` files | `.roo/commands/start-session.md` |

### Mixed Projects

If your project uses multiple platforms, skills are installed in all relevant formats:

```bash
# Example: opencode + kilocode project
mkdir my-project && cd my-project
echo '{}' > opencode.json
mkdir .kilo

bash update.sh --sync .

# Result:
# .opencode/skills/start-session/SKILL.md (opencode format)
# .kilo/commands/start-session.md (kilocode format)
```

## Platform Support

| Platform | Auto-detected | Skills path |
|----------|:------------:|-------------|
| opencode | ✅ | `~/.agents/skills/` |
| Antigravity | ✅ | `~/.gemini/antigravity/plugins/omnistate/` |
| Kilocode | ✅ | `~/.kilo/commands/` |
| Roo Code | ✅ | `~/.roo/commands/` |
| Claude Code | ✅ | `~/.claude/skills/` |
| Other | — | Copy `.opencode/skills/*` to your tool's skill directory |

## Project Sync

To sync skills to a specific project:

```bash
# Linux / macOS
bash update.sh /path/to/your/project

# Windows
.\update.ps1 C:\path\to\your\project
```

## Files Created in Your Project

| File | Purpose | Git-ignored |
|------|---------|:-----------:|
| `omnistate.config.json` | Configuration | ✅ |
| `project-summary.md` | Architecture index | ✅ |
| `tasks-history.json` | Active + completed tasks | ✅ |
| `tasks-archive.json` | Old archived tasks | ✅ |
| `AGENTS.md` | Agent definitions | ✅ |
| `AI_POLICY.md` | AI interaction rules | ✅ |
| `CONTEXT.md` | Project context | ✅ |
| `chunks/` | Session snapshots | ✅ |
| `omnistate-dashboard.html` | Visual dashboard | ✅ |

## SSH / Remote Host One-Liner

```bash
export REPO_DIR=~/OmniState; [ -d $REPO_DIR ] || git clone https://github.com/spupuz/OmniState.git $REPO_DIR; cd $REPO_DIR && git pull && bash update.sh
```

---

## Changelog

### v1.16.0 (current)
- **Security**: Fix [HIGH] arbitrary file read / permission manipulation in `sync-workflows.sh` by skipping symlinks entirely in the sync loop
- **Performance**: Optimize task counting and session word/file-reading overhead in `collect-dashboard-data.py` (single-pass line reads, native list counting)
- **Accessibility**: Wrap global empty-state injections in `<main id="main-content">`, remove `tabindex="0"` from non-scrollable empty containers, and pair `aria-valuetext` with `aria-valuenow` on the progress bar

### v1.15.1 (current)
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

## Support

If OmniState is saving you time, tokens, and context-window headaches every single day, consider fueling the next version with a coffee. Every cup helps keep development going, features shipping, and your AI sessions lean and fast:

<p align="center">
<a href="https://www.buymeacoffee.com/spupuz"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy me a coffee" width="160" /></a>
</p>

---

*OmniState — Persistent Memory for Any AI.*
