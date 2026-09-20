---
name: dashboard-omnistate
description: Shows the OmniState web dashboard (live, server-rendered) or in-chat metrics. Use when the user asks to see the dashboard, metrics, project status, or GitHub PR health.
---

# Dashboard (OmniState MCP)

The dashboard is served by the MCP server itself — there is no static HTML anymore.

1. Tell the user to open the server URL in the browser (default `http://localhost:8347`; use the same host/IP as the MCP config, e.g. `http://192.168.1.28:8347`).
2. For quick numbers directly in chat, use the MCP tools instead:
   - `project_list` / `project_metrics` — tasks, snapshots, token savings
   - `memory_search` — cross-project search
   - `github_metrics` / `github_delta` / `github_history` — open PR health

## Rules
- Never generate a static dashboard file — the v2 dashboard is live at the server URL only.
