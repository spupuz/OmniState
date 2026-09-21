# OmniState — Persistent Memory Protocol

An OmniState MCP server (name: `omnistate`) provides persistent, cross-project memory: tasks, session snapshots, searchable notes. Use its tools in EVERY session.

## At session start (as soon as you receive the first task)
1. Get the current working directory (absolute path) and call `project_register` with it.
2. Call `session_start` with the project name from the register response.
3. Read the returned recent memory and open tasks BEFORE acting. Summarize them in max 3 bullets, then proceed with the user's task.

## During the session
- **Every significant activity gets a task**: call `task_add` (status `in_progress`) *before* starting it, and `task_update` to `done` when it finishes. Do not batch task creation at the end of the session — register and close them as you go, so the MCP server is updated live.
- `task_list` at the start of non-trivial work to avoid duplicating an open task.
- `memory_remember` with `scope="shared"` for decisions, preferences and reusable patterns valid across ALL projects (e.g. "this user prefers conventional commits").
- `memory_remember` with `scope="project"` for notes specific to the current project only.
- `memory_search` across all projects before planning work that may already have been solved elsewhere.

## At session end (or when the user asks to save)
- Call `session_snapshot` with a distilled 2-5 line summary of what was accomplished.

## Rules
- Never fabricate memory: use only real tool results.
- If the MCP server is unreachable, say so once and continue the user's work without blocking.
- Register the project before using its memory.
- Prefer distillation: memory entries must be short summaries, not dumps.
