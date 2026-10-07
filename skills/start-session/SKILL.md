---
name: start-session
description: MANDATORY first step of every session - loads persistent memory from the OmniState MCP server (project_register -> session_start -> max-3-bullet summary). Use when the user starts a session, sends the first task, or says "start session" / "resume" / "load memory" / "riprendi" / "carica memoria".
---

# Start Session (OmniState MCP)

MANDATORY: run these steps BEFORE any other action. Do not start implementation until steps 1-4 are complete.

1. Get the absolute current working directory: `pwd` (resolve symlinks if needed).
2. Call `tools.omnistate.project_register({ path: "<absolute_cwd>" })`. Wait for the result. Extract the `project` name.
3. Call `tools.omnistate.session_start({ project: "<name>" })`. Wait for the result.
4. Read `recent_memory`, `open_tasks`, and `recall` (if present) from the result. Output a summary in MAX 3 bullets BEFORE taking any other action, then proceed with the user's task.

## Rules
- Never fabricate memory: report only real tool results.
- If the MCP server is unreachable, say so ONCE and continue without memory (do not block the user's work).
- If the project is new (no memory), say "new project: empty memory" and continue.
- The project must be registered before any project-scoped memory call.
- These steps are MANDATORY for every new session; treat them as a precondition, not optional.
