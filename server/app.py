"""OmniState web app: FastAPI mounting MCP (Streamable HTTP) + REST API + dashboard."""
from __future__ import annotations

import json
import threading
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse, Response

from .config import Config, GithubConfig
from .github_client import GithubClient
from .indexer import discover_projects, import_legacy, register_project
from .mcp_server import create_server
from .store import Store
from .version import get_version

DASHBOARD_HTML = Path(__file__).parent / "dashboard.html"


class App:
    METRICS_TTL_SECONDS = 60.0

    def __init__(self, cfg: Config, store: Store):
        self.cfg = cfg
        self.store = store
        self.fastapi = FastAPI(title="OmniState", version=get_version())
        self._scan_lock = threading.Lock()
        self._stop_event = threading.Event()
        # Dashboard list cache: all_project_metrics() runs tiktoken on every
        # memory row, which is wasteful on every poll. TTL-bounded + explicitly
        # invalidated by writes/scans so a "Scan now" always shows fresh counts.
        # Only the *metrics* are cached; category/gh_state stay decision data and
        # are recomputed on every poll (cheap SQL, must never go stale silently).
        self._metrics_cache: dict[int, dict[str, Any]] | None = None
        self._metrics_cache_ts = 0.0
        self._metrics_lock = threading.Lock()
        self._setup_routes()

    def invalidate_metrics_cache(self) -> None:
        """Drop the cached dashboard project list (call after any data write)."""
        with self._metrics_lock:
            self._metrics_cache = None
            self._metrics_cache_ts = 0.0

    # ---------- MCP mount ----------

    def mount_mcp(self) -> None:
        """Mount the MCP Streamable HTTP app at / and compose its lifespan into
        the parent app, so the MCP session manager starts on uvicorn startup."""
        mcp_server = create_server(self.cfg, self.store)
        mcp_app = mcp_server.streamable_http_app(streamable_http_path="/mcp", host="0.0.0.0")
        self.fastapi.mount("/", mcp_app)

        parent_lifespan = self.fastapi.router.lifespan_context

        @asynccontextmanager
        async def lifespan(app):
            async with parent_lifespan(app):
                async with mcp_app.router.lifespan_context(mcp_app):
                    yield

        self.fastapi.router.lifespan_context = lifespan

    # ---------- helpers ----------

    def _archived_repo_names(self) -> set[str]:
        """Lower-cased repo names (and full names) flagged archived in the latest GitHub scan."""
        scan = self.store.latest_gh_scan()
        if scan is None:
            return set()
        names: set[str] = set()
        for r in self.store.gh_scan_repos(int(scan["id"])):
            if r.get("is_archived"):
                if r.get("name"):
                    names.add(str(r["name"]).lower())
                if r.get("full_name"):
                    names.add(str(r["full_name"]).lower())
        return names

    @staticmethod
    def _project_category(project: dict[str, Any], archived_names: set[str]) -> str:
        """Dashboard lifecycle — GitHub wins over the local disk:
        deleted (path gone OR repo deleted on GitHub) > archived (GitHub) > active."""
        if project.get("status") == "removed":
            return "deleted"
        if project.get("gh_state") == "deleted":
            return "deleted"
        if project.get("gh_state") == "archived":
            return "archived"
        if str(project.get("name", "")).lower() in archived_names:
            return "archived"
        return "active"

    def _gh_deleted_is_trusted(self, repo: str) -> bool:
        """A 404 proves deletion only with a token that can see the owner's repos
        (unauthenticated 404s are also private/unknown repos)."""
        if not self.cfg.github.token:
            return False
        owner = repo.split("/", 1)[0].lower()
        return any(owner == a.strip().lower() for a in self.cfg.github.accounts if a and a.strip())

    def check_projects_github_state(self, *, force: bool = False) -> dict[str, str]:
        """Refresh gh_state per project 'gh_repo' (parsed from .git/config at registration).

        Queries api.github.com at most once per scan_interval_hours per project.
        'deleted' is applied only when trusted; network/rate-limit errors leave
        the previous state untouched ('unknown').
        """
        ttl = max(1, self.cfg.github.scan_interval_hours) * 3600
        client = GithubClient(self.cfg.github.token, stale_days=self.cfg.github.stale_days)
        out: dict[str, str] = {}
        changed = False
        for p in self.store.list_projects():
            repo = p.get("gh_repo")
            if not repo:
                continue
            checked = p.get("gh_checked_at")
            if not force and checked:
                try:
                    ts = datetime.strptime(str(checked), "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
                    if (datetime.now(timezone.utc) - ts).total_seconds() < ttl:
                        continue
                except ValueError:
                    pass
            state = client.repo_state(repo)
            if state == "deleted" and not self._gh_deleted_is_trusted(repo):
                state = "unknown"
            if state != "unknown":
                self.store.set_project_gh_state(p["name"], state)
                changed = True
            elif not p.get("gh_state"):
                self.store.set_project_gh_state(p["name"], "unknown")
                changed = True
            out[p["name"]] = state if state != "unknown" else (p.get("gh_state") or "unknown")
        if changed:
            self.invalidate_metrics_cache()
        return out

    def _project_metrics_list(self) -> list[dict[str, Any]]:
        """Dashboard list. The expensive token-counting metrics are TTL-cached
        (see __init__); category/gh_state are recomputed per poll so a scan that
        changed a repo's archived/deleted state is visible immediately."""
        now = time.time()
        with self._metrics_lock:
            if (
                self._metrics_cache is not None
                and now - self._metrics_cache_ts < self.METRICS_TTL_SECONDS
            ):
                cached_metrics = dict(self._metrics_cache)
            else:
                cached_metrics = None
        if cached_metrics is None:
            cached_metrics = self.store.all_project_metrics()
            with self._metrics_lock:
                self._metrics_cache = dict(cached_metrics)
                self._metrics_cache_ts = now
        archived_names = self._archived_repo_names()
        out = []
        for p in self.store.list_projects():
            pid = int(p["id"])
            metrics = cached_metrics.get(pid)
            if metrics is None:
                metrics = self.store.project_metrics(pid)
            out.append({
                "name": p["name"],
                "host_path": p["host_path"],
                "status": p["status"],
                "gh_repo": p.get("gh_repo"),
                "gh_state": p.get("gh_state"),
                "category": self._project_category(p, archived_names),
                **metrics,
            })
        return out

    def _github_config_view(self) -> dict[str, Any]:
        info = GithubClient(self.cfg.github.token).token_info()
        return {
            "accounts": self.cfg.github.accounts,
            "extended": self.cfg.github.extended,
            "include_forks": self.cfg.github.include_forks,
            "include_archived": self.cfg.github.include_archived,
            "scan_interval_hours": self.cfg.github.scan_interval_hours,
            "token": info,
        }

    # ---------- routes ----------

    def _setup_routes(self) -> None:
        app = self.fastapi

        @app.middleware("http")
        async def _auth_required(request, call_next):
            """Optional network auth (OMNISTATE_AUTH_TOKEN): everything reachable
            from the LAN must present a Bearer token when one is configured.

            - GET / (static dashboard shell) and /health stay open so the
              healthcheck and the token prompt still work.
            - /api/* requires the header on every call.
            - /mcp is checked at session creation (POST without an
              Mcp-Session-Id); follow-ups on an already-authenticated session
              pass without resending the header.
            """
            token = self.cfg.auth_token
            if not token:
                return await call_next(request)
            path = request.url.path
            if path in ("/", "/health"):
                return await call_next(request)
            protected = path.startswith("/api/") or path.startswith("/mcp")
            if not protected:
                return await call_next(request)
            if path == "/mcp" and "mcp-session-id" in request.headers:
                return await call_next(request)
            if request.headers.get("authorization", "") != f"Bearer {token}":
                return JSONResponse(
                    {"error": "unauthorized"},
                    status_code=401,
                    headers={"WWW-Authenticate": "Bearer"},
                )
            return await call_next(request)

        @app.middleware("http")
        async def _no_store_api(request, call_next):
            """Never let a browser/proxy cache the dashboard API: a scan must be
            visible immediately after it finishes (stale PR counts otherwise)."""
            response = await call_next(request)
            if request.url.path.startswith("/api/") or request.url.path == "/health":
                response.headers["Cache-Control"] = "no-store, must-revalidate"
                response.headers["Pragma"] = "no-cache"
            return response

        @app.get("/", response_class=HTMLResponse)
        def index() -> str:
            return DASHBOARD_HTML.read_text(encoding="utf-8") if DASHBOARD_HTML.exists() else "<h1>OmniState v2</h1>"

        @app.get("/favicon.svg")
        def favicon_svg() -> Response:
            p = Path(__file__).parent / "favicon.svg"
            return Response(p.read_text(encoding="utf-8"), media_type="image/svg+xml") if p.exists() else Response(status_code=404)

        @app.get("/favicon.ico")
        def favicon_ico() -> Response:
            # Serve the SVG for the legacy path too (browsers accept it via the
            # <link rel=icon> in the dashboard head).
            p = Path(__file__).parent / "favicon.svg"
            return Response(p.read_text(encoding="utf-8"), media_type="image/svg+xml") if p.exists() else Response(status_code=404)

        @app.get("/health")
        def health() -> dict[str, Any]:
            return {"status": "ok", "version": get_version(), "data_dir": str(self.cfg.data_dir)}

        @app.get("/api/projects")
        def api_projects() -> list[dict[str, Any]]:
            return self._project_metrics_list()

        @app.post("/api/register")
        def api_register(body: dict[str, Any]) -> dict[str, Any]:
            host_path = (body.get("path") or "").strip()
            if not host_path:
                return JSONResponse({"error": "path required"}, status_code=400)
            root = self.cfg.resolve_host_root(host_path)
            if root is None:
                return JSONResponse(
                    {"error": f"path '{host_path}' is outside the configured roots"}, status_code=400
                )
            container_path = root.host_to_container(host_path)
            project = register_project(self.cfg, self.store, container_path)
            if project is None:
                return JSONResponse({"error": "cannot register project"}, status_code=400)
            self.invalidate_metrics_cache()
            return {"registered": True, "project": project}

        @app.post("/api/discover")
        def api_discover() -> dict[str, Any]:
            registered = self.run_discovery()
            return {"registered": registered}

        @app.get("/api/projects/{name}")
        def api_project(name: str) -> dict[str, Any]:
            row = self.store.get_project(name)
            if row is None:
                return JSONResponse({"error": "not found"}, status_code=404)
            entries = self.store.memory_for_project(int(row["id"]), limit=50)
            return {
                "project": row,
                "category": self._project_category(row, self._archived_repo_names()),
                "metrics": self.store.project_metrics(int(row["id"])),
                "memory": entries,
            }

        @app.get("/api/memory")
        def api_memory(q: str = "", project: str = "", scope: str = "all", limit: int = 20,
                       startDate: str = "", endDate: str = "", include_outdated: bool = False) -> list[dict[str, Any]]:
            return self.store.search_memory(
                q, project=project or None, scope=scope, limit=limit,
                start_date=startDate or None, end_date=endDate or None,
                include_outdated=include_outdated,
            )

        @app.get("/api/memory/recent")
        def api_memory_recent(project: str = "", limit: int = 10,
                              include_outdated: bool = False) -> list[dict[str, Any]]:
            return self.store.list_recent_memories(limit=limit, project=project or None,
                                                  include_outdated=include_outdated)

        @app.post("/api/memory/{mem_id}/reinforce")
        def api_memory_reinforce(mem_id: int, body: dict[str, Any]) -> dict[str, Any]:
            signal = (body.get("signal") or "").strip()
            reason = (body.get("reason") or "").strip()
            try:
                result = self.store.reinforce_memory(mem_id, signal, reason)
            except ValueError as e:
                return JSONResponse({"error": str(e)}, status_code=400)
            self.invalidate_metrics_cache()
            return result

        @app.get("/api/memory/export")
        def api_memory_export() -> dict[str, Any]:
            return self.store.export_memories("memory-export.json")

        @app.get("/api/memory/{mem_id}/feedback")
        def api_memory_feedback(mem_id: int) -> list[dict[str, Any]]:
            return self.store.memory_feedback_for(mem_id)

        @app.get("/api/shared")
        def api_shared() -> list[dict[str, Any]]:
            return self.store.shared_memory()

        @app.post("/api/shared")
        def api_shared_add(body: dict[str, Any]) -> dict[str, Any]:
            text = (body.get("text") or "").strip()
            if not text:
                return JSONResponse({"error": "text required"}, status_code=400)
            tags = [t.strip() for t in (body.get("tags") or "").split(",") if t.strip()]
            mem_id = self.store.add_memory(
                project_id=None, scope="shared", kind="note", title=text[:120], content=text, tags=tags
            )
            self.invalidate_metrics_cache()
            return {"memory_id": mem_id, "scope": "shared"}

        @app.delete("/api/shared/{mem_id}")
        def api_shared_delete(mem_id: int) -> dict[str, Any]:
            row = self.store.get_memory(mem_id)
            if row is None or row.get("scope") != "shared":
                return JSONResponse({"error": "shared entry not found"}, status_code=404)
            self.store.delete_memory(mem_id)
            self.invalidate_metrics_cache()
            return {"deleted": True, "memory_id": mem_id}

        @app.get("/api/stats")
        def api_stats() -> dict[str, Any]:
            stats = self.store.stats()
            # "Progetti" = only truly active ones: excludes removed paths and
            # projects matching a GitHub repo flagged archived in the latest scan.
            metrics_list = self._project_metrics_list()
            stats["projects"] = sum(
                1 for p in metrics_list if p["category"] == "active"
            )

            stored_tokens = sum(p["storedTokens"] for p in metrics_list if p["category"] == "active")
            loaded_tokens = sum(p["loadedTokens"] for p in metrics_list if p["category"] == "active")
            stats["tokenSavings"] = max(0, stored_tokens - loaded_tokens)

            return stats

        # ---- GitHub PR Health ----

        @app.post("/api/github/scan")
        def api_github_scan(body: dict[str, Any] | None = None) -> dict[str, Any]:
            body = body or {}
            try:
                scan_id, summary = self.run_github_scan(
                    accounts=body.get("accounts"),
                    extended=body.get("extended"),
                    include_forks=body.get("include_forks"),
                    include_archived=body.get("include_archived"),
                )
            except (ValueError, RuntimeError) as e:
                return JSONResponse({"error": str(e)}, status_code=400)
            except Exception as e:  # noqa: BLE001
                return JSONResponse({"error": str(e)}, status_code=502)
            return {"scan_id": scan_id, **summary}

        @app.get("/api/github/metrics")
        def api_github_metrics() -> dict[str, Any]:
            scan = self.store.latest_gh_scan()
            if scan is None:
                return {"error": "no scans yet"}
            prev = self.store.one("SELECT * FROM gh_scans ORDER BY id DESC LIMIT 1 OFFSET 1")
            return {**scan, "delta_vs_previous": (scan["total_prs"] - prev["total_prs"]) if prev else None}

        @app.get("/api/github/delta")
        def api_github_delta() -> dict[str, Any]:
            scans = self.store.gh_history(limit=2)
            if len(scans) < 2:
                return {"error": "need at least two scans"}
            latest, prev = scans[-1], scans[-2]
            return {
                "latest": latest["timestamp"],
                "previous": prev["timestamp"],
                "delta_prs": latest["total_prs"] - prev["total_prs"],
                "delta_repos": latest["total_repos"] - prev["total_repos"],
            }

        @app.get("/api/github/history")
        def api_github_history(top_n: int = 5, limit: int = 30) -> dict[str, Any]:
            scans = self.store.gh_history(limit=limit)
            trend = [{"timestamp": s["timestamp"], "total_prs": s["total_prs"]} for s in scans]
            per_repo = self.store.gh_per_repo_trend(top_n=top_n, limit=limit)
            return {"trend": trend, "per_repo": per_repo}

        @app.get("/api/github/repos")
        def api_github_repos(scan_id: int = 0) -> list[dict[str, Any]]:
            scan = self.store.latest_gh_scan()
            if scan is None:
                return []
            return self.store.gh_scan_repos(scan_id or int(scan["id"]))

        @app.get("/api/github/authors")
        def api_github_authors(limit: int = 10) -> list[dict[str, Any]]:
            return self.store.gh_top_authors(limit=limit)

        @app.get("/api/github/labels")
        def api_github_labels(limit: int = 10) -> list[dict[str, Any]]:
            return self.store.gh_top_labels(limit=limit)

        @app.get("/api/github/config")
        def api_github_config() -> dict[str, Any]:
            return self._github_config_view()

    # ---------- background work ----------

    def sweep_missing_projects(self) -> list[str]:
        """Mark active projects whose path no longer exists as 'removed' (dashboard 'Deleted').

        A project is only evaluated when its mounted root is available, so a
        temporary mount failure never mass-marks projects as deleted.
        """
        marked: list[str] = []
        for p in self.store.list_projects():
            if p["status"] != "active":
                continue
            cp = p.get("container_path") or ""
            if not cp:
                continue
            root = next(
                (r for r in self.cfg.roots
                 if cp == r.container or cp.startswith(r.container.rstrip("/") + "/")),
                None,
            )
            if root is None or not Path(root.container).exists():
                continue
            if not Path(cp).exists():
                self.store.set_project_status(p["name"], "removed")
                marked.append(p["name"])
        return marked

    def run_discovery(self) -> list[str]:
        found = discover_projects(self.cfg)
        registered = []
        for p in found:
            existing = self.store.get_project(p.name)
            project = register_project(self.cfg, self.store, str(p))
            if project:
                # Auto-import legacy v1 memory (DESIGN §6): for newly discovered
                # projects AND for registered projects that still have no memory.
                has_legacy = any((p / m).exists() for m in ("chunks", "tasks-history.json", "project-summary.md"))
                needs_import = (
                    self.cfg.auto_import_legacy
                    and has_legacy
                    and (existing is None or not self.store.memory_for_project(int(project["id"]), limit=1))
                )
                if needs_import:
                    try:
                        import_legacy(self.cfg, self.store, str(p))
                    except Exception:
                        pass
                registered.append(project["name"])
        self.sweep_missing_projects()
        try:
            self.check_projects_github_state()
        except Exception:
            pass  # network issues must never break discovery
        self.invalidate_metrics_cache()
        return registered

    def run_github_scan(
        self,
        accounts: list[str] | None = None,
        extended: bool | None = None,
        include_forks: bool | None = None,
        include_archived: bool | None = None,
    ) -> tuple[int, dict[str, Any]]:
        """Run a GitHub scan and persist it. Returns (scan_id, summary with snake_case keys)."""
        account_list = accounts if accounts else list(self.cfg.github.accounts)
        account_list = [a.strip() for a in account_list if a and a.strip()]
        if not account_list:
            raise ValueError("no accounts configured")
        with self._scan_lock:
            client = GithubClient(self.cfg.github.token, stale_days=self.cfg.github.stale_days)
            result = client.scan(
                account_list,
                extended=self.cfg.github.extended if extended is None else extended,
                include_forks=self.cfg.github.include_forks if include_forks is None else include_forks,
                include_archived=self.cfg.github.include_archived if include_archived is None else include_archived,
            )
            scan_id = self.store.persist_gh_scan(result, account_list)
        # Fresh PR counts must be visible immediately after "Scan now".
        self.invalidate_metrics_cache()
        summary = {
            "method": result["method"],
            "total_repos": result["totalRepos"],
            "total_prs": result["totalPRs"],
        }
        return scan_id, summary

    def start_scheduler(self) -> threading.Thread:
        """Background loop: periodic project discovery + scheduled GitHub scans (DESIGN §6, §7b)."""
        def loop() -> None:
            import time
            discovery_interval = max(30, self.cfg.scan_interval_seconds)
            scan_interval = max(1, self.cfg.github.scan_interval_hours) * 3600
            last_scan = 0.0
            while not self._stop_event.is_set():
                try:
                    self.run_discovery()
                except Exception:
                    pass
                now = time.time()
                if self.cfg.github.accounts and now - last_scan >= scan_interval:
                    try:
                        self.run_github_scan()
                        last_scan = now
                    except Exception:
                        pass
                self._stop_event.wait(discovery_interval)

        thread = threading.Thread(target=loop, daemon=True, name="omnistate-scheduler")
        thread.start()
        return thread

    def stop(self) -> None:
        self._stop_event.set()