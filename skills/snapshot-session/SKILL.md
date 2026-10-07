---
name: snapshot-session
description: MANDATORY at session end - saves session progress to the OmniState MCP server (archives done tasks, creates a session chunk). Use when work completes, the user asks to save the session, or says "snapshot" / "save session" / "close session" / "salva sessione".
---

# Snapshot Session (OmniState MCP)

1. Identify the current project (registered earlier via `project_register`; if not registered, register it now with the cwd absolute path).
2. Distill what was accomplished in this session into 2-5 essential lines.
3. Reconcile tasks: set completed work to `done` with `task_update`; create missing tasks first with `task_add`.
4. Call `tools.omnistate.session_snapshot({ project: "<name>", summary: "<2-5 lines>" })`.
5. Report to the user: number of archived tasks + snapshot created.

## Rules
- The summary must be real: only what actually happened in this session.
- Do not delete or rewrite previous memory, only add the new snapshot.
- Never fabricate results: report only the real tool output.
- If the MCP server is unreachable, say so ONCE and report that nothing was saved (do not block).
