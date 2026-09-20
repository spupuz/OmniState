"""OmniState MCP server (MCPServer 2.x).

Exposes project/session/task/memory and GitHub PR Health tools. All paths are
resolved host->container and validated inside the mounted roots (read-only).
The GitHub token is never returned; only token_set/login/scopes metadata.
"""
from __future__ import annotations

import asyncio
import json
from typing import Any

from mcp.server.mcpserver import MCPServer

from .config import Config, save_config
from .github_client import GithubClient
from .indexer import discover_projects, import_legacy, register_project
from .store import Store


def create_server(cfg: Config, store: Store) -> MCPServer:
    server = MCPServer(name="OmniState", version="2.0.0")

    def _resolve_project(project: str) -> dict[str, Any]:
        row = store.get_project(project)
        if row is None:
            raise ValueError(f"Project '{project}' not found. Register it with project_register first.")
        return row

    # ---------- projects ----------

    @server.tool()
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
    def project_register(path: str = "") -> str:
        """Register the current project (or a host path) so the server indexes it. Auto-registration."""
        host_path = path
        if not host_path:
            raise ValueError("Provide a project host path (e.g. the working directory).")
        root = cfg.resolve_host_root(host_path)
        if root is None:
            raise ValueError(
                f"Path '{host_path}' is outside the configured roots. Add it to /data/config.json (roots)."
            )
        container_path = root.host_to_container(host_path)
        if container_path is None:
            raise ValueError("Cannot map host path to container path.")
        project = register_project(cfg, store, container_path)
        if project is None:
            raise ValueError("Project could not be registered (path not under any root).")
        return json.dumps({
            "registered": True,
            "project": project["name"],
            "host_path": project["host_path"],
            "container_path": project["container_path"],
        }, indent=2)

    @server.tool()
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
    def project_metrics(project: str) -> str:
        """Active/archived/done tasks, snapshots and token savings of a project."""
        row = _resolve_project(project)
        return json.dumps(store.project_metrics(int(row["id"])), indent=2)

    @server.tool()
    def project_import_legacy(project: str) -> str:
        """Import v1 per-project memory files once (migration). Read-only import."""
        row = _resolve_project(project)
        result = import_legacy(cfg, store, row["container_path"])
        return json.dumps(result, indent=2)

    @server.tool()
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
    def session_start(project: str) -> str:
        """Start a session: load relevant memory and open tasks for the project."""
        row = _resolve_project(project)
        tasks = store.list_tasks(int(row["id"]))
        open_tasks = [t for t in tasks if t["content"]]
        recent = store.q(
            "SELECT title, content, created_at FROM memory WHERE project_id = ? AND kind IN ('chunk','summary') "
            "ORDER BY created_at DESC LIMIT 3",
            (row["id"],),
        )
        return json.dumps({
            "project": project,
            "session_started": True,
            "open_tasks": len(open_tasks),
            "recent_memory": [{"title": m["title"], "created_at": m["created_at"]} for m in recent],
            "recall": store.memory_recall_for(int(row["id"])),
        }, indent=2)

    @server.tool()
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
    def task_add(project: str, title: str, status: str = "todo") -> str:
        """Add a task to a project."""
        row = _resolve_project(project)
        if status not in ("todo", "in_progress", "done"):
            raise ValueError("status must be one of: todo, in_progress, done")
        mem_id = store.add_memory(
            project_id=int(row["id"]), scope="project", kind="task",
            title=title[:120], content=json.dumps({"title": title, "status": status}),
        )
        return json.dumps({"task_id": mem_id, "status": status}, indent=2)

    @server.tool()
    def task_update(project: str, task_id: int, status: str) -> str:
        """Update a task status (-> done makes it ready for snapshot)."""
        row = _resolve_project(project)
        if status not in ("todo", "in_progress", "done"):
            raise ValueError("status must be one of: todo, in_progress, done")
        mem = store.get_memory(task_id)
        if mem is None or mem.get("project_id") != row["id"]:
            raise ValueError("Task not found in this project.")
        try:
            meta = json.loads(mem["content"])
        except Exception:
            meta = {"title": mem.get("title", "")}
        meta["status"] = status
        store.update_memory(task_id, json.dumps(meta), title=meta.get("title"))
        return json.dumps({"task_id": task_id, "status": status}, indent=2)

    @server.tool()
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
    def memory_search(query: str, project: str = "", scope: str = "all", limit: int = 10) -> str:
        """Full-text search across projects and shared memory."""
        results = store.search_memory(
            query, project=project or None, scope=scope, limit=min(limit, 50)
        )
        return json.dumps(results, indent=2)

    @server.tool()
    def memory_remember(text: str, project: str = "", scope: str = "shared", tags: str = "") -> str:
        """Save a note (shared by default, or per-project)."""
        if scope not in ("shared", "project"):
            raise ValueError("scope must be 'shared' or 'project'.")
        tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
        project_id = None
        if scope == "project":
            row = _resolve_project(project)
            project_id = int(row["id"])
        mem_id = store.add_memory(
            project_id=project_id, scope=scope, kind="note", title=text[:120],
            content=text, tags=tag_list,
        )
        return json.dumps({"memory_id": mem_id, "scope": scope}, indent=2)

    @server.tool()
    def memory_recall(project: str) -> str:
        """Return relevant memory for a session start (reduced context)."""
        row = _resolve_project(project)
        pid = int(row["id"])
        recent = store.memory_for_project(pid, limit=10)
        shared = store.shared_memory(limit=5)
        return json.dumps({"project": project, "recent": recent, "shared": shared}, indent=2)

    @server.tool()
    def memory_forget(memory_id: int) -> str:
        """Delete a memory entry by id."""
        ok = store.delete_memory(memory_id)
        return json.dumps({"deleted": ok, "memory_id": memory_id}, indent=2)

    # ---------- GitHub PR Health ----------

    def _github_client() -> GithubClient:
        return GithubClient(cfg.github.token, stale_days=cfg.github.stale_days)

    @server.tool()
    def github_scan(accounts: str = "", extended: bool = True, include_forks: bool = False,
                    include_archived: bool = False) -> str:
        """Scan GitHub accounts/orgs for open PRs and save metrics to the DB."""
        account_list = [a.strip() for a in (accounts or ",".join(cfg.github.accounts)).split(",") if a.strip()]
        if not account_list:
            raise ValueError("No accounts configured. Pass accounts or set them via github_config.")
        result = _github_client().scan(
            account_list, extended=extended, include_forks=include_forks, include_archived=include_archived
        )
        scan_id = store.persist_gh_scan(result, account_list)
        return json.dumps({
            "scan_id": scan_id,
            "method": result["method"],
            "total_repos": result["totalRepos"],
            "total_prs": result["totalPRs"],
            "timestamp": store.one("SELECT timestamp FROM gh_scans WHERE id = ?", (scan_id,))["timestamp"],
        }, indent=2)

    @server.tool()
    def github_metrics() -> str:
        """Latest GitHub scan totals."""
        scan = store.latest_gh_scan()
        if scan is None:
            return json.dumps({"error": "No scans yet. Run github_scan."}, indent=2)
        prev = store.one("SELECT * FROM gh_scans ORDER BY id DESC LIMIT 1 OFFSET 1")
        delta = (scan["total_prs"] - prev["total_prs"]) if prev else None
        return json.dumps({**scan, "delta_vs_previous": delta}, indent=2)

    @server.tool()
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
    def github_history(top_n: int = 5, limit: int = 30) -> str:
        """Historical open PR trend (total + per-repo)."""
        scans = store.gh_history(limit=limit)
        trend = [{"timestamp": s["timestamp"], "total_prs": s["total_prs"]} for s in scans]
        per_repo = store.gh_per_repo_trend(top_n=top_n, limit=limit)
        return json.dumps({"trend": trend, "per_repo": per_repo}, indent=2)

    @server.tool()
    def github_top_authors(limit: int = 10) -> str:
        """Top authors of open PRs across scans."""
        return json.dumps(store.gh_top_authors(limit=limit), indent=2)

    @server.tool()
    def github_top_labels(limit: int = 10) -> str:
        """Most frequent PR labels across scans."""
        return json.dumps(store.gh_top_labels(limit=limit), indent=2)

    @server.tool()
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
    def github_token_info() -> str:
        """GitHub token metadata (valid/login/scopes). Never returns the token."""
        return json.dumps(GithubClient(cfg.github.token).token_info(), indent=2)

    return server