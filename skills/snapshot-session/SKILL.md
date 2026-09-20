---
name: snapshot-session
description: Saves session progress to the OmniState MCP server (archives done tasks, creates a session chunk). Use when the user asks to save the session, or says "snapshot", "save session", "close session".
---

# Snapshot Session (OmniState MCP)

1. Identify the current project (registered earlier via `project_register`; if not registered, register it now with the cwd absolute path).
2. Distill what was accomplished in this session into 2-5 essential lines.
3. If some completed work is not tracked as tasks, call `task_update` to set those tasks to `done` (create them with `task_add` if missing).
4. Call `session_snapshot` with the distilled summary.
5. Report to the user: number of archived tasks + snapshot created.

## Rules
- The summary must be real: only what actually happened in this session.
- Do not delete or rewrite previous memory, only add the new snapshot.
