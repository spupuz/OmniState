# OmniState — Agent Rules

## Data Protection (CRITICAL)
- **NEVER commit secrets**: No `.env` files, API keys, tokens, passwords, or credentials.
- **NEVER commit runtime data**: No `.db`, `.sqlite`, `.sqlite3`, WAL/SHM files, or contents of `/data/`, `shared/`, or `tmp/`.
- **NEVER commit local config**: No `config.json`, `dashboard-data.json`, or user-specific config.
- **NEVER commit test data**: `tests/` directory is gitignored for security.
- **Check before committing**: Always run `git status` to verify no sensitive files are staged.
- Follow `.gitignore` strictly — it exists to prevent accidental leaks (DESIGN.md §10b).

## Development Rules
- All changes must maintain backward compatibility unless explicitly breaking.
- Tests must pass before committing: `python -m pytest tests/ -q`
- Bump `VERSION.txt` and `plugin.json` together for releases.
- Follow the pr-push/commit-push skill workflows when releasing.

## OmniState Memory Protocol
When working in OmniState codebase, use the OmniState MCP:
1. `project_register` → `session_start` at session start
2. `task_add` before significant work, `task_update` to done when finished
3. `memory_remember` for decisions (project/shared scope appropriately)
4. `session_snapshot` at end if needed
