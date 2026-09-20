"""Project discovery + one-time legacy import.

The server walks the mounted roots (read-only), finds projects by markers
(opencode.json, .git/, tasks-history.json, omnistate.config.json) and indexes
them into the store. Legacy v1 files can be imported once via project_import_legacy.
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from .config import Config
from .store import Store

MARKERS = ("opencode.json", ".git", "tasks-history.json", "omnistate.config.json", "project-summary.md")
LEGACY_FILES = (
    "project-summary.md",
    "tasks-history.json",
    "tasks-archive.json",
    "omni_cost.json",
)
MAX_DEPTH = 8


def _mtime(path: Path) -> str:
    try:
        return datetime.fromtimestamp(path.stat().st_mtime).isoformat()
    except Exception:
        return ""


def _is_project_dir(path: Path) -> bool:
    return any((path / m).exists() for m in MARKERS)


def discover_projects(cfg: Config) -> list[Path]:
    found: list[Path] = []
    for root in cfg.roots:
        container_root = Path(root.container)
        if not container_root.exists():
            continue

        def walk(directory: Path, depth: int) -> None:
            if depth > MAX_DEPTH:
                return
            try:
                entries = sorted(
                    directory.iterdir(),
                    key=lambda p: (p.is_file(), p.name.lower()),
                )
            except (PermissionError, OSError):
                return
            for entry in entries:
                if entry.name.startswith(".") and entry.name not in (".git",):
                    continue
                if entry.is_dir() and entry.name not in ("node_modules", ".git", "dist", "build"):
                    if _is_project_dir(entry):
                        found.append(entry)
                    else:
                        walk(entry, depth + 1)

        walk(container_root, 0)
    return found


_GH_PATH_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
_REMOTE_URL_RE = re.compile(r"^(?:[A-Za-z][A-Za-z0-9+.-]*://)?(?:[^/@]*@)?([^/:]+)(?::\d+)?[:/](.+)$")


def parse_remote_url(url: str) -> str | None:
    """Extract 'owner/repo' from a git remote URL. Only github.com remotes qualify.

    Handles https://, ssh:// and scp-like git@github.com:owner/repo forms.
    Credentials/userinfo in the URL are never kept: the host must be exactly
    github.com (not a path trick like evil.com/github.com) and the path must be
    a plain owner/repo slug.
    """
    url = (url or "").strip().strip('"')
    m = _REMOTE_URL_RE.match(url)
    if not m:
        return None
    host, path = m.group(1).lower(), (m.group(2) or "").strip()
    if host != "github.com":
        return None
    if path.endswith(".git"):
        path = path[:-4]
    if ".." in path or any(c in path for c in "@\\?# \t"):
        return None
    return path if _GH_PATH_RE.match(path) else None


def read_gh_repo(container_path: str) -> str | None:
    """Read the `origin` remote of a local git repo and map it to 'owner/repo'."""
    try:
        text = (Path(container_path) / ".git" / "config").read_text(encoding="utf-8", errors="ignore")[:20000]
    except (OSError, ValueError):
        return None
    in_origin = False
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("["):
            in_origin = s.replace(" ", "").lower().startswith('[remote"origin"]')
            continue
        if in_origin and s.lower().startswith("url"):
            _, _, val = s.partition("=")
            return parse_remote_url(val)
    return None


def register_project(cfg: Config, store: Store, container_path: str) -> dict[str, Any] | None:
    """Register a project given its container path. Returns project row or None."""
    root = None
    for r in cfg.roots:
        if container_path == r.container or container_path.startswith(r.container.rstrip("/") + "/"):
            root = r
            break
    if root is None:
        return None
    host_path = root.container_to_host(container_path) or container_path
    name = Path(container_path).name or "root"
    pid = store.upsert_project(name, host_path, container_path, gh_repo=read_gh_repo(container_path))
    return store.get_project(name)


def import_legacy(cfg: Config, store: Store, container_path: str) -> dict[str, Any]:
    """Import v1 per-project memory files once (migration). Read-only."""
    project_dir = Path(container_path)
    if not project_dir.exists():
        return {"imported": 0, "error": "path not found"}
    project = store.get_project(Path(container_path).name or "root")
    if project is None:
        register_project(cfg, store, container_path)
        project = store.get_project(Path(container_path).name or "root")
    if project is None:
        return {"imported": 0, "error": "project not registered"}

    pid = int(project["id"])
    imported = 0

    # project-summary.md -> summary
    summary = project_dir / "project-summary.md"
    if summary.exists():
        content = _read_safe(summary)
        if content:
            store.add_memory(
                project_id=pid, scope="project", kind="summary",
                title="Project Summary", content=content[:4000],
                source_file=str(summary),
            )
            imported += 1

    # tasks-history.json + tasks-archive.json -> task entries
    for tf in ("tasks-history.json", "tasks-archive.json"):
        path = project_dir / tf
        if not path.exists():
            continue
        try:
            data = json.loads(_read_safe(path) or "{}")
        except Exception:
            continue
        for task in data.get("tasks", []):
            title = task.get("title") or ""
            status = task.get("status") or "todo"
            if not title:
                continue
            store.add_memory(
                project_id=pid, scope="project", kind="task",
                title=title[:120], content=json.dumps({"title": title, "status": status}),
                source_file=tf, tags=["legacy"],
            )
            imported += 1

    # chunks/*.md -> chunk entries
    chunks_dir = project_dir / "chunks"
    if chunks_dir.exists():
        for chunk in sorted(chunks_dir.glob("*.md")):
            content = _read_safe(chunk)
            if not content:
                continue
            first = content.strip().splitlines()[0] if content.strip() else "Session"
            label = first.lstrip("# ").strip()[:40]
            store.add_memory(
                project_id=pid, scope="project", kind="chunk",
                title=label, content=content[:4000], source_file=str(chunk),
                tags=["legacy"],
            )
            imported += 1

    return {"imported": imported, "project": project.get("name")}


def _read_safe(path: Path) -> str | None:
    """Read a file, refusing symlinks and paths outside the project dir (SECURITY)."""
    try:
        if path.is_symlink():
            return None
        resolved = path.resolve()
        if resolved.is_symlink():
            return None
        # do not follow symlinked parents
        if os.path.realpath(path) != str(resolved):
            return None
        if resolved.stat().st_size > 2_000_000:
            return None
        return resolved.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return None