"""OmniState MCP server (MCPServer 2.x).

Exposes project/session/task/memory and GitHub PR Health tools. All paths are
resolved host->container and validated inside the mounted roots (read-only).
The GitHub token is never returned; only token_set/login/scopes metadata.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import traceback
from functools import wraps
from typing import Any

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from .config import Config, save_config
from .github_client import GithubClient
from .indexer import discover_projects, import_legacy, register_project
from .store import Store
from .version import get_version

log = logging.getLogger("omnistate.mcp")


def _logged(fn: Any) -> Any:
    """Log tool failures and surface them as clean ToolError messages.

    Async/sync aware; preserves the original signature/docstring so the MCP
    SDK keeps building the right tool schema (functools.wraps sets __wrapped__).
    """

    def _make_wrap(fn_err: Any) -> Any:
        """Return a callable that catches non-ToolError failures and turns them
        into clean, pre-`name`-safe ToolError messages.

        The returned closure takes its own args so `*a, **k` are unambiguous
        (a bare factory that referenced the outer wrapper's args would raise
        `name 'a' is not defined`).
        """

        def _run(*a: Any, **k: Any) -> Any:
            try:
                return fn_err(*a, **k)
            except ToolError:
                raise
            except Exception as e:  # noqa: BLE001
                if os.environ.get("OMNISTATE_DEBUG"):
                    traceback.print_exc()
                log.warning("mcp tool %s failed: %s", fn_err.__name__, e)
                raise ToolError(f"{fn_err.__name__}: {e}") from e

        return _run

    if asyncio.iscoroutinefunction(fn):

        @wraps(fn)
        async def async_wrapper(*a: Any, **k: Any) -> Any:
            return await _make_wrap(fn)(*a, **k)

        return async_wrapper

    @wraps(fn)
    def wrapper(*a: Any, **k: Any) -> Any:
        return _make_wrap(fn)(*a, **k)

    return wrapper


def create_server(cfg: Config, store: Store) -> MCPServer:
    server = MCPServer(name="OmniState", version=get_version())

    def _resolve_project(project: str) -> dict[str, Any]:
        row = store.get_project(project)
        if row is None:
            raise ToolError(f"Project '{project}' not found. Register it with project_register first.")
        return row

    # ---------- projects ----------

    @server.tool()
    @_logged
    def project_list() -> str:
        """List registered projects with metrics."""
        out = []
        for p in store.list_projects():
            metrics = store.project_metrics(int(p["id"]))
            out.append({
                "name": p["name"],
                "host_path": p["host_path"],
                "status": p["status"],
                "last_indexed_at": p["last_indexed_at"],
                **metrics,
            })
        return json.dumps(out, indent=2)

    @server.tool()
    @_logged
    def project_register(path: str = "") -> str:
        """Register the current project (or a host path) so the server indexes it. Auto-registration."""
        host_path = path
        if not host_path:
            raise ToolError("Provide a project host path (e.g. the working directory).")
        root = cfg.resolve_host_root(host_path)
        if root is None:
            raise ToolError(
                f"Path '{host_path}' is outside the configured roots. Add it to /data/config.json (roots)."
            )
        container_path = root.host_to_container(host_path)
        if container_path is None:
            raise ToolError("Cannot map host path to container path.")
        project = register_project(cfg, store, container_path)
        if project is None:
            raise ToolError("Project could not be registered (path not under any root).")
        return json.dumps({
            "registered": True,
            "project": project["name"],
            "host_path": project["host_path"],
            "container_path": project["container_path"],
        }, indent=2)

    @server.tool()
    @_logged
    def project_summary(project: str) -> str:
        """Distilled summary (architecture + state) of a project."""
        row = _resolve_project(project)
        entries = store.q(
            "SELECT * FROM memory WHERE project_id = ? AND kind = 'summary' ORDER BY updated_at DESC LIMIT 1",
            (row["id"],),
        )
        summary = entries[0]["content"] if entries else "No summary yet. Run session_snapshot to create one."
        metrics = store.project_metrics(int(row["id"]))
        return json.dumps({"project": project, "summary": summary, "metrics": metrics}, indent=2)

    @server.tool()
    @_logged
    def project_metrics(project: str) -> str:
        """Active/archived/done tasks, snapshots and token savings of a project."""
        row = _resolve_project(project)
        return json.dumps(store.project_metrics(int(row["id"])), indent=2)

    @server.tool()
    @_logged
    def project_import_legacy(project: str) -> str:
        """Import v1 per-project memory files once (migration). Read-only import."""
        row = _resolve_project(project)
        result = import_legacy(cfg, store, row["container_path"])
        return json.dumps(result, indent=2)

    @server.tool()
    @_logged
    def project_discover() -> str:
        """Scan mounted roots for new projects and register them (auto-registration)."""
        found = discover_projects(cfg)
        registered = []
        for p in found:
            project = register_project(cfg, store, str(p))
            if project:
                registered.append(project["name"])
        return json.dumps({"found": len(found), "registered": registered}, indent=2)

    # ---------- sessions ----------

    @server.tool()
    @_logged
    def session_start(project: str) -> str:
        """Start a session: load relevant memory (project + shared) and open tasks."""
        row = _resolve_project(project)
        ctx = store.session_context(int(row["id"]))
        return json.dumps({
            "project": project,
            "session_started": True,
            **ctx,
            "token_measure": store.context_token_measure(int(row["id"]), ctx=ctx),
        }, indent=2)

    @server.tool()
    @_logged
    def session_snapshot(project: str, summary: str = "") -> str:
        """Archive done tasks, distill progress and create a session chunk."""
        row = _resolve_project(project)
        pid = int(row["id"])
        done = []
        for t in store.list_tasks(pid, status="done"):
            done.append(t["title"])
            store.delete_memory(int(t["id"]))
        content = summary or f"Session snapshot for {project}."
        chunk_count = store.one(
            "SELECT COUNT(*) AS c FROM memory WHERE kind = 'chunk' AND project_id = ?",
            (pid,),
        )["c"]
        chunk_id = store.add_memory(
            project_id=pid, scope="project", kind="chunk",
            title=f"Session {chunk_count + 1}",
            content=content[:4000],
        )
        return json.dumps({
            "snapshot_created": chunk_id,
            "archived_tasks": done,
            "archived_count": len(done),
        }, indent=2)

    # ---------- tasks ----------

    @server.tool()
    @_logged
    def task_add(project: str, title: str, status: str = "todo") -> str:
        """Add a task to a project."""
        row = _resolve_project(project)
        if status not in ("todo", "in_progress", "done"):
            raise ToolError("status must be one of: todo, in_progress, done")
        mem_id = store.add_memory(
            project_id=int(row["id"]), scope="project", kind="task",
            title=title[:120], content=json.dumps({"title": title, "status": status}),
        )
        return json.dumps({"task_id": mem_id, "status": status}, indent=2)

    @server.tool()
    @_logged
    def task_update(project: str, task_id: int, status: str) -> str:
        """Update a task status (-> done makes it ready for snapshot)."""
        row = _resolve_project(project)
        if status not in ("todo", "in_progress", "done"):
            raise ToolError("status must be one of: todo, in_progress, done")
        mem = store.get_memory(task_id)
        if mem is None or mem.get("project_id") != row["id"]:
            raise ToolError("Task not found in this project.")
        try:
            meta = json.loads(mem["content"])
        except Exception:
            meta = {"title": mem.get("title", "")}
        meta["status"] = status
        store.update_memory(task_id, json.dumps(meta), title=meta.get("title"))
        return json.dumps({"task_id": task_id, "status": status}, indent=2)

    @server.tool()
    @_logged
    def task_list(project: str, status: str = "") -> str:
        """List tasks of a project (optionally by status)."""
        row = _resolve_project(project)
        tasks = store.list_tasks(int(row["id"]), status or None)
        out = []
        for t in tasks:
            try:
                meta = json.loads(t["content"])
            except Exception:
                meta = {"title": t.get("title"), "status": "todo"}
            out.append({"id": t["id"], "title": meta.get("title"), "status": meta.get("status")})
        return json.dumps(out, indent=2)

    # ---------- memory ----------

    @server.tool()
    @_logged
    def memory_search(query: str, project: str = "", scope: str = "all", limit: int = 10,
                      startDate: str = "", endDate: str = "", include_outdated: bool = False,
                      debug: bool = False) -> str:
        """Hybrid search: FTS5 + coverage + tags + decayed importance + familiarity.
        Temporal filters (startDate/endDate, ISO or YYYY-MM-DD) apply to created_at."""
        results = store.search_memory(
            query, project=project or None, scope=scope, limit=min(limit, 50),
            start_date=startDate or None, end_date=endDate or None,
            include_outdated=include_outdated, debug=debug,
        )
        return json.dumps(results, indent=2)

    @server.tool()
    @_logged
    def memory_remember(text: str, project: str = "", scope: str = "shared", tags: str = "",
                          source: str = "") -> str:
        """Save a note (shared by default, or per-project)."""
        if scope not in ("shared", "project"):
            raise ToolError("scope must be 'shared' or 'project'.")
        tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
        project_id = None
        if scope == "project":
            row = _resolve_project(project)
            project_id = int(row["id"])
        mem_id = store.add_memory(
            project_id=project_id, scope=scope, kind="note", title=text[:120],
            content=text, tags=tag_list, source=source,
        )
        return json.dumps({"memory_id": mem_id, "scope": scope}, indent=2)

    @server.tool()
    @_logged
    def memory_recall(project: str) -> str:
        """Return relevant memory for a session start (reduced context)."""
        row = _resolve_project(project)
        pid = int(row["id"])
        recent = store.memory_for_project(pid, limit=10)
        shared = store.q(
            "SELECT title, content, tags FROM memory WHERE scope = 'shared' AND lifecycle_state = 'active' "
            "ORDER BY created_at DESC LIMIT 5"
        )
        return json.dumps({"project": project, "recent": recent, "shared": shared}, indent=2)

    @server.tool()
    @_logged
    def memory_reinforce(memory_id: int, signal: str, reason: str = "") -> str:
        """Apply a feedback signal (used/important/irrelevant/incorrect/outdated/restore).
        outdated/incorrect suppress the memory without deleting; restore re-activates.
        Importance is adjusted (bounded 0..1) and the event is audited."""
        return json.dumps(store.reinforce_memory(memory_id, signal, reason), indent=2)

    @server.tool()
    @_logged
    def memory_recent(limit: int = 10, project: str = "", include_outdated: bool = False) -> str:
        """Latest active memories (optionally per project, or including suppressed ones)."""
        return json.dumps(
            store.list_recent_memories(limit=min(limit, 200), project=project or None,
                                       include_outdated=include_outdated),
            indent=2,
        )

    @server.tool()
    @_logged
    def memory_export(path: str = "") -> str:
        """Dump all memories + reinforcement feedback to a JSON backup file."""
        return json.dumps(store.export_memories(path or "memory-export.json"), indent=2)

    @server.tool()
    @_logged
    def memory_export_markdown(path: str = "") -> str:
        """Export memories as Markdown files (decisions as ADR-XXXX.md)."""
        return json.dumps(store.export_memories_markdown(path or "memory-export"), indent=2)

    @server.tool()
    @_logged
    def memory_handoff(project: str, current_state: str,
                       next_steps: str, completed: str = "",
                       risks: str = "", validation: str = "") -> str:
        """Create a handoff for another agent or future session."""
        row = _resolve_project(project)
        def _parse_list(s: str) -> list[str]:
            return [x.strip() for x in (s or "").splitlines() if x.strip()]
        mem_id = store.memory_handoff(
            project_id=int(row["id"]),
            current_state=current_state,
            completed=_parse_list(completed),
            next_steps=_parse_list(next_steps),
            risks=_parse_list(risks),
            validation=_parse_list(validation),
        )
        return json.dumps({"handoff_id": mem_id, "project": project}, indent=2)

    @server.tool()
    @_logged
    def memory_forget(memory_id: int, reason: str = "") -> str:
        """Delete a memory entry by id with optional audit reason."""
        ok = store.delete_memory(memory_id, reason=reason)
        return json.dumps({"deleted": ok, "memory_id": memory_id}, indent=2)

    # ---------- memory resources (read-only, JSON) ----------

    @server.resource("omnistate://memory/recent", name="Recent memories",
                     description="Latest active memories across projects and shared scope.",
                     mime_type="application/json")
    @_logged
    def memory_recent_resource() -> str:
        return json.dumps(store.list_recent_memories(limit=25), indent=2)

    @server.resource("omnistate://memory/{id}", name="Memory entry",
                     description="A single memory entry by id (or JSON error object).",
                     mime_type="application/json")
    @_logged
    def memory_entry_resource(id: str) -> str:
        try:
            mid = int(id)
        except ValueError:
            return json.dumps({"error": f"invalid id: {id}"})
        row = store.get_memory(mid)
        if row is None:
            return json.dumps({"error": f"memory {mid} not found"})
        return json.dumps(row, indent=2)

    @server.resource("omnistate://projects/{project}/recent", name="Recent project memory",
                     description="Most recent memory entries of a registered project.",
                     mime_type="application/json")
    @_logged
    def project_recent_resource(project: str) -> str:
        row = _resolve_project(project)
        return json.dumps(store.memory_for_project(int(row["id"]), limit=15), indent=2)

    # ---------- GitHub PR Health ----------

    def _github_client() -> GithubClient:
        return GithubClient(cfg.github.token, stale_days=cfg.github.stale_days)

    @server.tool()
    @_logged
    async def github_scan(accounts: str = "", extended: bool = True, include_forks: bool = False,
                          include_archived: bool = False) -> str:
        """Scan GitHub accounts/orgs for open PRs and save metrics to the DB."""
        account_list = [a.strip() for a in (accounts or ",".join(cfg.github.accounts)).split(",") if a.strip()]
        if not account_list:
            raise ToolError("No accounts configured. Pass accounts or set them via github_config.")
        # Network + persistence is blocking: keep it off the event loop.
        result = await asyncio.to_thread(
            lambda: _github_client().scan(
                account_list, extended=extended, include_forks=include_forks,
                include_archived=include_archived,
            )
        )
        scan_id = await asyncio.to_thread(store.persist_gh_scan, result, account_list)
        log.info("github_scan: method=%s repos=%s prs=%s", result["method"], result["totalRepos"], result["totalPRs"])
        return json.dumps({
            "scan_id": scan_id,
            "method": result["method"],
            "total_repos": result["totalRepos"],
            "total_prs": result["totalPRs"],
            "timestamp": store.one("SELECT timestamp FROM gh_scans WHERE id = ?", (scan_id,))["timestamp"],
        }, indent=2)

    @server.tool()
    @_logged
    def github_metrics() -> str:
        """Latest GitHub scan totals."""
        scan = store.latest_gh_scan()
        if scan is None:
            return json.dumps({"error": "No scans yet. Run github_scan."}, indent=2)
        prev = store.one("SELECT * FROM gh_scans ORDER BY id DESC LIMIT 1 OFFSET 1")
        delta = (scan["total_prs"] - prev["total_prs"]) if prev else None
        return json.dumps({**scan, "delta_vs_previous": delta}, indent=2)

    @server.tool()
    @_logged
    def github_delta() -> str:
        """Delta between the last two GitHub scans."""
        scans = store.gh_history(limit=2)
        if len(scans) < 2:
            return json.dumps({"error": "Need at least two scans to compute delta."}, indent=2)
        latest, prev = scans[-1], scans[-2]
        d = latest["total_prs"] - prev["total_prs"]
        return json.dumps({
            "latest": latest["timestamp"],
            "previous": prev["timestamp"],
            "delta_prs": d,
            "delta_repos": latest["total_repos"] - prev["total_repos"],
        }, indent=2)

    @server.tool()
    @_logged
    def github_history(top_n: int = 5, limit: int = 30) -> str:
        """Historical open PR trend (total + per-repo)."""
        scans = store.gh_history(limit=limit)
        trend = [{"timestamp": s["timestamp"], "total_prs": s["total_prs"]} for s in scans]
        per_repo = store.gh_per_repo_trend(top_n=top_n, limit=limit)
        return json.dumps({"trend": trend, "per_repo": per_repo}, indent=2)

    @server.tool()
    @_logged
    def github_top_authors(limit: int = 10) -> str:
        """Top authors of open PRs across scans."""
        return json.dumps(store.gh_top_authors(limit=limit), indent=2)

    @server.tool()
    @_logged
    def github_top_labels(limit: int = 10) -> str:
        """Most frequent PR labels across scans."""
        return json.dumps(store.gh_top_labels(limit=limit), indent=2)

    @server.tool()
    @_logged
    def github_config(accounts: str = "", token: str = "", extended: bool = True) -> str:
        """Save GitHub accounts/token/config for automatic scans. Token is stored in /data/config.json only."""
        if accounts:
            cfg.github.accounts = [a.strip() for a in accounts.split(",") if a.strip()]
        if token:
            cfg.github.token = token
        cfg.github.extended = extended
        save_config(cfg)
        info = GithubClient(cfg.github.token).token_info() if cfg.github.token else {"token_set": False}
        return json.dumps({
            "saved": True,
            "accounts": cfg.github.accounts,
            "extended": cfg.github.extended,
            "token": info,  # token metadata only, never the token itself
        }, indent=2)

    @server.tool()
    @_logged
    def github_token_info() -> str:
        """GitHub token metadata (valid/login/scopes). Never returns the token."""
        return json.dumps(GithubClient(cfg.github.token).token_info(), indent=2)

    return server