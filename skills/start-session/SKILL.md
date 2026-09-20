---
name: start-session
description: Loads persistent memory from the OmniState MCP server at session start. Use when the user starts a session, asks to recall memory/context, or says "start session" / "resume" / "load memory".
---

# Start Session (OmniState MCP)

1. Get the current working directory (absolute path) and call `project_register` with it.
2. Call `session_start` with the project name from the register response.
3. Read the returned recent memory and open tasks BEFORE acting. Summarize them in max 3 bullets, then proceed with the user's task.

## Rules
- Never fabricate memory: report only real tool results.
- If the MCP server is unreachable, say so and continue without memory (do not block the user's work).
- If the project is new (no memory), say "new project: empty memory" and continue.
