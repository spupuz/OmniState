"""OmniState SQLite store.

Central persistence: projects, memory (per-project + shared), FTS5 full-text
search, and GitHub PR Health tables (gh_scans/gh_repos/gh_authors/gh_labels).

All queries are parameterized (no SQL injection). Data never leaves /data.
"""
from __future__ import annotations

import json
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


SCHEMA = """
CREATE TABLE IF NOT EXISTS projects (
  id              INTEGER PRIMARY KEY,
  name            TEXT UNIQUE NOT NULL,
  host_path       TEXT NOT NULL,
  container_path  TEXT NOT NULL,
  last_indexed_at TEXT,
  status          TEXT DEFAULT 'active',
  gh_repo         TEXT,
  gh_state        TEXT,
  gh_checked_at   TEXT,
  created_at      TEXT
);

CREATE TABLE IF NOT EXISTS memory (
  id          INTEGER PRIMARY KEY,
  project_id  INTEGER REFERENCES projects(id),
  scope       TEXT NOT NULL DEFAULT 'project',
  kind        TEXT NOT NULL,
  title       TEXT,
  content     TEXT NOT NULL,
  tags        TEXT DEFAULT '[]',
  source_file TEXT,
  created_at  TEXT,
  updated_at  TEXT
);

CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts USING fts5(
  content, title, tags, content='memory', content_rowid='id'
);

CREATE TABLE IF NOT EXISTS gh_scans (
  id          INTEGER PRIMARY KEY,
  timestamp   TEXT NOT NULL,
  accounts    TEXT,
  method      TEXT,
  total_repos INTEGER,
  total_prs   INTEGER
);

CREATE TABLE IF NOT EXISTS gh_repos (
  id             INTEGER PRIMARY KEY,
  scan_id        INTEGER REFERENCES gh_scans(id),
  owner          TEXT, name TEXT, full_name TEXT, url TEXT,
  stars          INTEGER, language TEXT,
  is_fork        INTEGER, is_archived INTEGER, is_private INTEGER,
  open_prs       INTEGER, draft_prs INTEGER, no_reviewer INTEGER,
  stale_prs      INTEGER, oldest_pr_days INTEGER, open_issues INTEGER,
  updated_at     TEXT
);

CREATE TABLE IF NOT EXISTS gh_authors (
  id        INTEGER PRIMARY KEY,
  scan_id   INTEGER, author TEXT, pr_count INTEGER
);

CREATE TABLE IF NOT EXISTS gh_labels (
  id        INTEGER PRIMARY KEY,
  scan_id   INTEGER, label TEXT, pr_count INTEGER
);

CREATE INDEX IF NOT EXISTS idx_projects_name ON projects(name);
CREATE INDEX IF NOT EXISTS idx_memory_project ON memory(project_id);
CREATE INDEX IF NOT EXISTS idx_memory_scope ON memory(scope);
CREATE INDEX IF NOT EXISTS idx_gh_repos_scan ON gh_repos(scan_id);
CREATE INDEX IF NOT EXISTS idx_gh_scans_ts ON gh_scans(timestamp);
CREATE INDEX IF NOT EXISTS idx_gh_authors_scan ON gh_authors(scan_id);
CREATE INDEX IF NOT EXISTS idx_gh_labels_scan ON gh_labels(scan_id);
"""

# FTS triggers keep the external-content table in sync
FTS_TRIGGERS = """
CREATE TRIGGER IF NOT EXISTS memory_ai AFTER INSERT ON memory BEGIN
  INSERT INTO memory_fts(rowid, content, title, tags)
  VALUES (new.id, new.content, new.title, new.tags);
END;
CREATE TRIGGER IF NOT EXISTS memory_ad AFTER DELETE ON memory BEGIN
  INSERT INTO memory_fts(memory_fts, rowid, content, title, tags)
  VALUES ('delete', old.id, old.content, old.title, old.tags);
END;
CREATE TRIGGER IF NOT EXISTS memory_au AFTER UPDATE ON memory BEGIN
  INSERT INTO memory_fts(memory_fts, rowid, content, title, tags)
  VALUES ('delete', old.id, old.content, old.title, old.tags);
  INSERT INTO memory_fts(rowid, content, title, tags)
  VALUES (new.id, new.content, new.title, new.tags);
END;
"""


class Store:
    def __init__(self, db_path: Path | str, shared_dir: Path | str | None = None):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        # Human-readable mirror of shared entries (DESIGN §9): /data/shared/mem-<id>.md
        self.shared_dir = Path(shared_dir) if shared_dir else None
        if self.shared_dir:
            self.shared_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        with self._conn:
            self._conn.executescript(SCHEMA)
            self._conn.executescript(FTS_TRIGGERS)
            # Migration for pre-2.1 DBs: GitHub repo mapping/state columns.
            for col in ("gh_repo TEXT", "gh_state TEXT", "gh_checked_at TEXT"):
                try:
                    self._conn.execute(f"ALTER TABLE projects ADD COLUMN {col}")
                except sqlite3.OperationalError:
                    pass  # duplicate column: already migrated

    # ---------- shared memory file mirror ----------

    def _shared_file(self, mem_id: int) -> Path | None:
        return self.shared_dir / f"mem-{int(mem_id):06d}.md" if self.shared_dir else None

    def _write_shared_file(self, row: dict[str, Any]) -> None:
        path = self._shared_file(int(row["id"]))
        if path is None:
            return
        tags = json.loads(row.get("tags") or "[]")
        body = "\n".join([
            "---",
            f"id: {row['id']}",
            f"title: {row.get('title') or ''}",
            f"tags: [{', '.join(tags)}]",
            f"created_at: {row.get('created_at') or ''}",
            "---",
            "",
            row.get("content") or "",
            "",
        ])
        tmp = path.with_suffix(".tmp")
        tmp.write_text(body, encoding="utf-8")
        tmp.replace(path)

    def _delete_shared_file(self, mem_id: int) -> None:
        path = self._shared_file(mem_id)
        if path and path.exists():
            path.unlink()

    @contextmanager
    def tx(self) -> Iterator[sqlite3.Connection]:
        with self._lock:
            with self._conn:
                yield self._conn

    def q(self, sql: str, params: tuple = ()) -> list[dict[str, Any]]:
        with self._lock:
            cur = self._conn.execute(sql, params)
            rows = cur.fetchall()
        return [dict(r) for r in rows]

    def one(self, sql: str, params: tuple = ()) -> dict[str, Any] | None:
        rows = self.q(sql, params)
        return rows[0] if rows else None

    def execute(self, sql: str, params: tuple = ()) -> int:
        with self.tx() as conn:
            cur = conn.execute(sql, params)
            return int(cur.lastrowid)

    # ---------- projects ----------

    def upsert_project(
        self, name: str, host_path: str, container_path: str, gh_repo: str | None = None
    ) -> int:
        now = _now()
        row = self.one("SELECT id FROM projects WHERE name = ?", (name,))
        if row:
            with self.tx() as conn:
                conn.execute(
                    "UPDATE projects SET host_path=?, container_path=?, status='active', "
                    "gh_repo=COALESCE(?, gh_repo), last_indexed_at=? WHERE id=?",
                    (host_path, container_path, gh_repo, now, row["id"]),
                )
            return int(row["id"])
        return self.execute(
            "INSERT INTO projects(name, host_path, container_path, gh_repo, created_at, last_indexed_at) "
            "VALUES(?,?,?,?,?,?)",
            (name, host_path, container_path, gh_repo, now, now),
        )

    def list_projects(self) -> list[dict[str, Any]]:
        return self.q("SELECT * FROM projects ORDER BY name")

    def get_project(self, name: str) -> dict[str, Any] | None:
        return self.one("SELECT * FROM projects WHERE name = ?", (name,))

    def set_project_status(self, name: str, status: str) -> None:
        self.execute("UPDATE projects SET status=? WHERE name = ?", (status, name))

    def set_project_gh_state(self, name: str, state: str, *, repo: str | None = None) -> None:
        if repo is None:
            self.execute(
                "UPDATE projects SET gh_state=?, gh_checked_at=? WHERE name = ?",
                (state, _now(), name),
            )
        else:
            self.execute(
                "UPDATE projects SET gh_repo=?, gh_state=?, gh_checked_at=? WHERE name = ?",
                (repo, state, _now(), name),
            )
        self.execute(
            "UPDATE projects SET gh_state=?, gh_repo=COALESCE(?, gh_repo), gh_checked_at=? WHERE name = ?",
            (state, repo, _now(), name),
        )

    def mark_project_removed(self, name: str) -> None:
        self.set_project_status(name, "removed")

    # ---------- memory ----------

    def add_memory(
        self,
        *,
        project_id: int | None,
        scope: str,
        kind: str,
        content: str,
        title: str | None = None,
        tags: list[str] | None = None,
        source_file: str | None = None,
    ) -> int:
        now = _now()
        mem_id = self.execute(
            "INSERT INTO memory(project_id, scope, kind, title, content, tags, source_file, created_at, updated_at) "
            "VALUES(?,?,?,?,?,?,?,?,?)",
            (project_id, scope, kind, title, content, json.dumps(tags or []), source_file, now, now),
        )
        if scope == "shared":
            row = self.get_memory(mem_id)
            if row:
                self._write_shared_file(row)
        return mem_id

    def update_memory(self, mem_id: int, content: str, title: str | None = None, tags: list[str] | None = None) -> bool:
        now = _now()
        with self.tx() as conn:
            cur = conn.execute(
                "UPDATE memory SET content=?, title=COALESCE(?, title), tags=?, updated_at=? WHERE id=?",
                (content, title, json.dumps(tags or []), now, mem_id),
            )
        ok = cur.rowcount > 0
        if ok:
            row = self.get_memory(mem_id)
            if row and row.get("scope") == "shared":
                self._write_shared_file(row)
        return ok

    def get_memory(self, mem_id: int) -> dict[str, Any] | None:
        return self.one("SELECT * FROM memory WHERE id = ?", (mem_id,))

    def delete_memory(self, mem_id: int) -> bool:
        row = self.get_memory(mem_id)
        with self.tx() as conn:
            cur = conn.execute("DELETE FROM memory WHERE id = ?", (mem_id,))
        ok = cur.rowcount > 0
        if ok and row and row.get("scope") == "shared":
            self._delete_shared_file(mem_id)
        return ok

    def search_memory(
        self,
        query: str,
        *,
        project: str | None = None,
        scope: str = "all",
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        if not query.strip():
            return []
        # Build a safe FTS5 query: every word becomes a quoted phrase, so
        # user input (quotes, semicolons, operators) can never break MATCH.
        fts_query = " AND ".join(
            '"{}"'.format(tok.replace('"', '""')) for tok in query.split() if tok
        )
        params: list = [fts_query]
        where: list[str] = []
        if scope == "shared":
            where.append("m.scope = 'shared'")
        elif scope == "project":
            where.append("m.scope = 'project'")
        if project:
            where.append("p.name = ?")
            params.append(project)
        where_sql = ("WHERE " + " AND ".join(where)) if where else ""
        sql = (
            "SELECT m.*, p.name AS project_name, f.rank FROM "
            "(SELECT rowid, bm25(memory_fts) AS rank FROM memory_fts "
            "WHERE memory_fts MATCH ?) f "
            "JOIN memory m ON m.id = f.rowid "
            "LEFT JOIN projects p ON m.project_id = p.id "
            f"{where_sql} "
            "ORDER BY f.rank LIMIT ?"
        )
        params.append(int(limit))
        return self.q(sql, tuple(params))

    def memory_for_project(self, project_id: int, limit: int = 20) -> list[dict[str, Any]]:
        return self.q(
            "SELECT * FROM memory WHERE project_id = ? ORDER BY created_at DESC LIMIT ?",
            (project_id, int(limit)),
        )

    def memory_recall_for(self, project_id: int, limit: int = 8) -> list[dict[str, Any]]:
        """Reduced-context recall for session start."""
        return self.q(
            "SELECT title, content, created_at FROM memory WHERE project_id = ? "
            "ORDER BY updated_at DESC LIMIT ?",
            (project_id, int(limit)),
        )

    def shared_memory(self, limit: int = 50) -> list[dict[str, Any]]:
        return self.q(
            "SELECT m.*, NULL AS project_name FROM memory m WHERE m.scope = 'shared' "
            "ORDER BY m.created_at DESC LIMIT ?",
            (int(limit),),
        )

    # ---------- sessions / tasks (memory kinds) ----------

    def list_tasks(self, project_id: int, status: str | None = None) -> list[dict[str, Any]]:
        if status:
            return self.q(
                "SELECT * FROM memory WHERE project_id = ? AND kind = 'task' "
                "AND json_extract(content, '$.status') = ? ORDER BY created_at DESC",
                (project_id, status),
            )
        return self.q(
            "SELECT * FROM memory WHERE project_id = ? AND kind = 'task' ORDER BY created_at DESC",
            (project_id,),
        )

    def project_metrics(self, project_id: int) -> dict[str, Any]:
        total = self.one(
            "SELECT COUNT(*) AS c FROM memory WHERE project_id = ?", (project_id,)
        )["c"]
        tasks = self.q("SELECT content FROM memory WHERE project_id = ? AND kind = 'task'", (project_id,))
        active = 0
        done = 0
        for t in tasks:
            try:
                meta = json.loads(t["content"])
                status = meta.get("status", "todo")
            except Exception:
                status = "todo"
            if status == "done":
                done += 1
            else:
                active += 1
        chunks = self.one(
            "SELECT COUNT(*) AS c FROM memory WHERE project_id = ? AND kind = 'chunk'", (project_id,)
        )["c"]
        words = 0
        for row in self.q(
            "SELECT content FROM memory WHERE project_id = ? AND kind IN ('chunk','task')", (project_id,)
        ):
            words += len(row["content"].split())
        token_saved = int(words * 1.3) + (chunks * 4000)
        return {
            "activeTasks": active,
            "doneTasks": done,
            "totalTasks": total,
            "snapshots": chunks,
            "tokenSavings": token_saved,
        }

    # ---------- GitHub PR Health ----------

    def persist_gh_scan(self, result: dict[str, Any], accounts: list[str]) -> int:
        """Persist a scan result (from GithubClient.scan) into the gh_* tables."""
        scan_id = self.add_gh_scan(
            accounts, result["method"], result["totalRepos"], result["totalPRs"]
        )
        self.add_gh_repos(scan_id, result["repos"])
        self.add_gh_authors(scan_id, result["authors"])
        self.add_gh_labels(scan_id, result["labels"])
        return scan_id

    def add_gh_scan(self, accounts: list[str], method: str, total_repos: int, total_prs: int) -> int:
        return self.execute(
            "INSERT INTO gh_scans(timestamp, accounts, method, total_repos, total_prs) VALUES(?,?,?,?,?)",
            (_now(), ",".join(accounts), method, total_repos, total_prs),
        )

    def add_gh_repos(self, scan_id: int, repos: list[dict[str, Any]]) -> None:
        with self.tx() as conn:
            for r in repos:
                conn.execute(
                    "INSERT INTO gh_repos(scan_id, owner, name, full_name, url, stars, language, is_fork, "
                    "is_archived, is_private, open_prs, draft_prs, no_reviewer, stale_prs, oldest_pr_days, "
                    "open_issues, updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        scan_id, r.get("owner"), r.get("name"), r.get("fullName"), r.get("url"),
                        r.get("stars"), r.get("language"), 1 if r.get("fork") else 0,
                        1 if r.get("archived") else 0, 1 if r.get("private") else 0,
                        r.get("openPRs"), r.get("draftPRs"), r.get("noReviewer"), r.get("stalePRs"),
                        r.get("oldestPRDays"), r.get("openIssues"), r.get("updatedRaw"),
                    ),
                )

    def add_gh_authors(self, scan_id: int, counts: dict[str, int]) -> None:
        with self.tx() as conn:
            for author, count in counts.items():
                conn.execute(
                    "INSERT INTO gh_authors(scan_id, author, pr_count) VALUES(?,?,?)",
                    (scan_id, author, count),
                )

    def add_gh_labels(self, scan_id: int, counts: dict[str, int]) -> None:
        with self.tx() as conn:
            for label, count in counts.items():
                conn.execute(
                    "INSERT INTO gh_labels(scan_id, label, pr_count) VALUES(?,?,?)",
                    (scan_id, label, count),
                )

    def latest_gh_scan(self) -> dict[str, Any] | None:
        return self.one("SELECT * FROM gh_scans ORDER BY id DESC LIMIT 1")

    def gh_scan_repos(self, scan_id: int) -> list[dict[str, Any]]:
        return self.q("SELECT * FROM gh_repos WHERE scan_id = ? ORDER BY open_prs DESC", (scan_id,))

    def gh_history(self, limit: int = 30) -> list[dict[str, Any]]:
        return self.q(
            "SELECT * FROM gh_scans ORDER BY id DESC LIMIT ?", (int(limit),)
        )[::-1]

    def gh_top_authors(self, limit: int = 10) -> list[dict[str, Any]]:
        return self.q(
            "SELECT author, SUM(pr_count) AS pr_count FROM gh_authors "
            "GROUP BY author ORDER BY pr_count DESC LIMIT ?",
            (int(limit),),
        )

    def gh_top_labels(self, limit: int = 10) -> list[dict[str, Any]]:
        return self.q(
            "SELECT label, SUM(pr_count) AS pr_count FROM gh_labels "
            "GROUP BY label ORDER BY pr_count DESC LIMIT ?",
            (int(limit),),
        )

    def gh_per_repo_trend(self, top_n: int = 5, limit: int = 30) -> list[dict[str, Any]]:
        rows = self.q(
            "SELECT full_name, open_prs, timestamp FROM gh_repos r "
            "JOIN gh_scans s ON r.scan_id = s.id ORDER BY s.id DESC LIMIT ?",
            (int(top_n * limit),),
        )
        return rows

    def stats(self) -> dict[str, Any]:
        projects = self.one("SELECT COUNT(*) AS c FROM projects WHERE status='active'")["c"]
        memory = self.one("SELECT COUNT(*) AS c FROM memory")["c"]
        scans = self.one("SELECT COUNT(*) AS c FROM gh_scans")["c"]
        token = 0
        for row in self.q("SELECT content FROM memory WHERE kind IN ('chunk','task')"):
            token += len(row["content"].split())
        chunks = self.one("SELECT COUNT(*) AS c FROM memory WHERE kind='chunk'")["c"]
        return {
            "projects": projects,
            "memoryEntries": memory,
            "ghScans": scans,
            "tokenSavings": int(token * 1.3) + chunks * 4000,
            "lastUpdate": _now(),
        }

    def close(self) -> None:
        with self._lock:
            self._conn.close()