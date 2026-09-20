---
name: cost-setup
description: Initializes/connects a project to the OmniState MCP server (registration + optional import of legacy v1 memory files). Use when the user asks to connect, init or set up a project with OmniState.
---

# Setup Project (OmniState MCP)

1. Call `project_register` with the current working directory (absolute path).
2. Ask the user if legacy v1 memory files exist in the project (`tasks-history.json`, `chunks/`, `project-summary.md`). If yes, call `project_import_legacy` with the project name to import them once.
3. Call `project_metrics` and report the registered project with its metrics.

## Rules
- The legacy import is read-only and one-shot: it never modifies project files.
- If the MCP server is unreachable, report the error and stop (do not create local files as fallback).
