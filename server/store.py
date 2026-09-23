"""OmniState SQLite store.

Central persistence: projects, memory (per-project + shared), FTS5 full-text
search, and GitHub PR Health tables (gh_scans/gh_repos/gh_authors/gh_labels).

All queries are parameterized (no SQL injection). Data never leaves /data.
"""
from __future__ import annotations

import json
import math
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterator

_token_encoder = None


def count_tokens(text: str) -> int:
    """Real token count using tiktoken cl100k_base (single cached encoding)."""
    global _token_encoder
    if _token_encoder is None:
        import tiktoken

        _token_encoder = tiktoken.get_encoding("cl100k_base")
    return len(_token_encoder.encode(text or ""))


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _text_tokens(text: str) -> set[str]:
    """Lower-cased meaningful tokens from free text (compounds expanded)."""
    import re

    out: set[str] = set()
    for tok in re.findall(r"[a-zA-Z0-9_\-]+", text or ""):
        tok = tok.lower()
        if len(tok) <= 1:
            continue
        out.add(tok)
        for part in re.split(r"[_\-]", tok):
            if len(part) > 1 and part not in out:
                out.add(part)
    return out


def _query_hash(text: str) -> str:
    import hashlib

    return hashlib.sha256(" ".join(sorted(_text_tokens(text))).encode("utf-8")).hexdigest()[:16]


def _normalize_iso(value: str, *, end: bool = False) -> str:
    """Accept 'YYYY-MM-DD' or 'YYYY-MM-DDTHH:MM:SSZ' and normalize to the
    ISO format used everywhere in the DB (..T..Z)."""
    value = (value or "").strip()
    if not value:
        return value
    if len(value) == 10:
        return value + ("T23:59:59Z" if end else "T00:00:00Z")
    return value if value.endswith("Z") else value.replace(" ", "T") + "Z"


def _parse_temporal(query: str) -> tuple[str | None, str | None, str]:
    """Extract an optional time window from a natural-language or ISO query.

    Returns (start, end, remaining_query). Recognizes ISO ranges and simple
    phrases like "last week" / "in 2025". Falls back to dateparser.search.
    """
    import re

    iso = re.search(r"\b(\d{4})-(\d{2})-(\d{2})", query)
    if iso:
        day = f"{iso.group(1)}-{iso.group(2)}-{iso.group(3)}"
        start, end = f"{day}T00:00:00Z", f"{day}T23:59:59Z"
        rest = query[:iso.start()] + " " + query[iso.end():]
        return start, end, re.sub(r"\s+", " ", rest).strip()

    try:
        import dateparser
        from dateparser.search import search_dates

        found = search_dates(query, languages=["en", "it", "es"], settings={"PREFER_DATES_FROM": "past"})
        if found:
            phrase, dt = found[0]
            if dt is not None:
                day = dt.strftime("%Y-%m-%d")
                start, end = f"{day}T00:00:00Z", f"{day}T23:59:59Z"
                rest = query.replace(phrase, "", 1)
                return start, end, re.sub(r"\s+", " ", rest).strip()
    except Exception:
        pass
    return None, None, query


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
  id                  INTEGER PRIMARY KEY,
  project_id          INTEGER REFERENCES projects(id),
  scope               TEXT NOT NULL DEFAULT 'project',
  kind                TEXT NOT NULL,
  title               TEXT,
  content             TEXT NOT NULL,
  tags                TEXT DEFAULT '[]',
  source_file         TEXT,
  created_at          TEXT,
  updated_at          TEXT,
  importance          REAL NOT NULL DEFAULT 0.5,
  lifecycle_state     TEXT NOT NULL DEFAULT 'active',
  reinforcement_count INTEGER NOT NULL DEFAULT 0,
  last_reinforced_at  TEXT,
  access_count        INTEGER NOT NULL DEFAULT 0,
  last_accessed       TEXT
);

CREATE TABLE IF NOT EXISTS memory_feedback (
  id         INTEGER PRIMARY KEY,
  memory_id  INTEGER NOT NULL REFERENCES memory(id) ON DELETE CASCADE,
  signal     TEXT NOT NULL,
  delta      REAL NOT NULL,
  reason     TEXT,
  created_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_feedback_memory ON memory_feedback(memory_id);

CREATE TABLE IF NOT EXISTS memory_recall_exposures (
  memory_id   INTEGER NOT NULL REFERENCES memory(id) ON DELETE CASCADE,
  query_hash  TEXT NOT NULL,
  recalled_on TEXT NOT NULL,
  created_at  TEXT,
  PRIMARY KEY (memory_id, query_hash, recalled_on)
);
CREATE INDEX IF NOT EXISTS idx_exposures_memory ON memory_recall_exposures(memory_id);

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
CREATE INDEX IF NOT EXISTS idx_memory_created ON memory(created_at);
CREATE INDEX IF NOT EXISTS idx_memory_updated ON memory(updated_at, project_id);
CREATE INDEX IF NOT EXISTS idx_memory_scope_lifecycle ON memory(scope, lifecycle_state);
CREATE INDEX IF NOT EXISTS idx_feedback_memory ON memory_feedback(memory_id);
CREATE INDEX IF NOT EXISTS idx_feedback_memory_created ON memory_feedback(memory_id, created_at);
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
            # Migration for post-2.3 DBs: memory lifecycle + reinforcement + exposure.
            self._migrate_memory_columns()

    def _migrate_memory_columns(self) -> None:
        """Add lifecycle/reinforcement columns to pre-existing memory tables.

        SQLite ALTER TABLE accepts a literal DEFAULT, so unset values get the
        same defaults as fresh tables: importance 0.5, lifecycle 'active',
        counters 0, timestamps NULL.
        """
        python_defaults = {
            "importance": "0.5",
            "lifecycle_state": "'active'",
            "reinforcement_count": "0",
            "last_reinforced_at": "NULL",
            "access_count": "0",
            "last_accessed": "NULL",
        }
        existing = {r["name"] for r in self.q("PRAGMA table_info(memory)")}
        for col, default in python_defaults.items():
            if col in existing:
                continue
            with self.tx() as conn:
                conn.execute(f"ALTER TABLE memory ADD COLUMN {col} DEFAULT {default}")

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
        """Single UPDATE: gh_state now, gh_repo only when provided (COALESCE)."""
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
        start_date: str | None = None,
        end_date: str | None = None,
        include_outdated: bool = False,
        debug: bool = False,
    ) -> list[dict[str, Any]]:
        """Hybrid recall: FTS5 evidence + coverage + tag boost + decayed
        importance + bounded familiarity (feedback signals never rewritten here).

        Mirrors the mcp-local-memory scoring model with FTS-only evidence.
        """
        limit = max(1, int(limit))
        start, end, rest = _parse_temporal(query)
        tokens = _text_tokens(rest)
        start = _normalize_iso(start_date) if start_date else start
        end = _normalize_iso(end_date, end=True) if end_date else end

        # Pure temporal query (dates only, no remaining tokens)
        if not tokens and (start or end):
            rows = self._recall_by_time(project, scope, start, end, limit, include_outdated)
            return [self._score_row(r, debug) for r in rows]

        if not tokens:
            return []

        fts_phrase = " OR ".join(f'"{t.replace(chr(34), chr(34) + chr(34))}"' for t in sorted(tokens))
        params: list = [fts_phrase]
        where: list[str] = []
        if scope == "shared":
            where.append("m.scope = 'shared'")
        elif scope == "project":
            where.append("m.scope = 'project'")
        if project:
            where.append("p.name = ?")
            params.append(project)
        if not include_outdated:
            where.append("m.lifecycle_state = 'active'")
        if start:
            where.append("m.created_at >= ?")
            params.append(start)
        if end:
            where.append("m.created_at <= ?")
            params.append(end)
        where_sql = ("WHERE " + " AND ".join(where)) if where else ""
        pool = max(20, min(200, limit * 4))
        rows = self.q(
            "SELECT m.*, p.name AS project_name, f.rank FROM "
            "(SELECT rowid, bm25(memory_fts) AS rank FROM memory_fts WHERE memory_fts MATCH ?) f "
            "JOIN memory m ON m.id = f.rowid "
            "LEFT JOIN projects p ON m.project_id = p.id "
            f"{where_sql} "
            "ORDER BY f.rank LIMIT ?",
            tuple(params) + (pool,),
        )
        if not rows:
            return []

        q_tokens = tokens
        for r in rows:
            row_tokens = _text_tokens(f"{r.get('title','')} {r.get('content','')} {r.get('tags','')}")
            coverage = len(q_tokens & row_tokens) / len(q_tokens)
            tag_tokens = _text_tokens(r.get("tags") or "")
            tag_cov = len(q_tokens & tag_tokens) / len(q_tokens) if tag_tokens else 0.0
            r["coverage"] = coverage
            r["tag_coverage"] = tag_cov

        rows.sort(key=lambda r: (r["rank"],))  # better bm25 first = lower/negative rank
        rows = rows[:pool]
        for rank_i, r in enumerate(rows):
            r["keyword_rank"] = rank_i
        rows.sort(key=lambda r: r["coverage"], reverse=True)

        scored = [self._score_row(r, debug) for r in rows]
        keep = []
        for r in scored:
            if r.get("relevance") < self._relevance_gate(len(q_tokens), r.get("coverage", 0)):
                continue
            keep.append(r)
        # greedy near-duplicate collapse (token Jaccard >= 0.9)
        collapsed: list[dict[str, Any]] = []
        kept_sets: list[set[str]] = []
        for r in keep:
            if len(q_tokens) >= 5:
                ts = _text_tokens(r.get("content", ""))
                dup = any(
                    len(ts & ks) / max(1, len(ts | ks)) >= 0.9 for ks in kept_sets
                )
                if dup:
                    continue
                kept_sets.append(ts)
            collapsed.append(r)
        collapsed.sort(key=lambda r: (r.get("score", 0), r.get("relevance", 0), r.get("coverage", 0)), reverse=True)
        top = collapsed[:limit]
        self._record_exposures([int(r["id"]) for r in top], query)
        return top

    def _recall_by_time(self, project, scope, start, end, limit, include_outdated):
        where: list[str] = []
        params: list = []
        if scope == "shared":
            where.append("scope = 'shared'")
        elif scope == "project":
            where.append("scope = 'project'")
        if project:
            where.append("(SELECT name FROM projects p WHERE p.id = memory.project_id) = ?")
            params.append(project)
        if not include_outdated:
            where.append("lifecycle_state = 'active'")
        if start:
            where.append("created_at >= ?")
            params.append(start)
        if end:
            where.append("created_at <= ?")
            params.append(end)
        where_sql = ("WHERE " + " AND ".join(where)) if where else ""
        return self.q(
            f"SELECT *, NULL AS project_name, 0 AS rank FROM memory {where_sql} "
            "ORDER BY created_at DESC LIMIT ?",
            tuple(params) + (limit,),
        )

    def _relevance_gate(self, q_len: int, coverage: float) -> float:
        if q_len >= 4 and coverage < 0.4:
            return 0.75
        return 0.55

    def _score_row(self, r: dict[str, Any], debug: bool = False) -> dict[str, Any]:
        """Apply the retrieval scoring model to a candidate row."""
        q_tokens = []
        # coverage/tag scores were attached by the caller (or default for time rows)
        coverage = float(r.get("coverage", 1.0))
        tag_cov = float(r.get("tag_coverage", 0.0))
        kw_rank = int(r.get("keyword_rank", 0))
        source = coverage * 0.85 + (11 / (10 + kw_rank)) * 0.15
        relevance = min(1.0, source + (1 - source) * (coverage * 0.15 + tag_cov * 0.15))

        importance = float(r.get("importance") if r.get("importance") is not None else 0.5)
        importance = self._decayed_importance(r, importance)
        base = 0.9 * relevance + 0.1 * importance

        fam = self._familiarity_boost(int(r["id"]))
        score = base + (1 - base) * fam
        out = dict(r)
        out["score"] = round(score, 4)
        out["relevance"] = round(relevance, 4)
        out["coverage"] = round(coverage, 3)
        out["tag_coverage"] = round(tag_cov, 3)
        out["importance"] = round(importance, 3)
        out["beam"] = round(base, 4)
        if debug:
            out["debug"] = {
                "source_evidence": round(source, 3),
                "familiarity": round(fam, 4),
                "keyword_rank": kw_rank,
            }
        return out

    def _decayed_importance(self, r: dict[str, Any], importance: float) -> float:
        """Half-life decay anchored to last_reinforced_at, falling back to
        created_at so a never-reinforced memory still fades over time
        (non-destructive: importance drops, the entry is never deleted)."""
        anchor = r.get("last_reinforced_at") or r.get("created_at")
        if not anchor or importance <= 0:
            return importance
        try:
            ts = datetime.strptime(str(anchor), "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        except ValueError:
            return importance
        weeks = max(0.0, (datetime.now(timezone.utc) - ts).total_seconds() / (7 * 24 * 3600))
        reinforcement = int(r.get("reinforcement_count") or 0)
        stability = 4 * (1 + math.log2(min(reinforcement, 20) + 1))
        return round(importance * 0.5 ** (weeks / stability), 3)

    def _familiarity_boost(self, mem_id: int) -> float:
        days = 30
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        n = self.one(
            "SELECT COUNT(DISTINCT recalled_on) AS n FROM memory_recall_exposures "
            "WHERE memory_id = ? AND recalled_on >= ?",
            (mem_id, cutoff.strftime("%Y-%m-%d")),
        )["n"] or 0
        return 0.03 * (1 - math.exp(-n / 5))

    def _record_exposures(self, mem_ids: list[int], query: str) -> None:
        if not mem_ids or not query.strip():
            return
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        qhash = _query_hash(query)
        now = _now()
        for mid in mem_ids:
            self.execute(
                "INSERT OR IGNORE INTO memory_recall_exposures(memory_id, query_hash, recalled_on, created_at) "
                "VALUES(?,?,?,?)",
                (mid, qhash, today, now),
            )
        self.execute(
            f"UPDATE memory SET access_count = access_count + 1, last_accessed = ? "
            f"WHERE id IN ({','.join('?' * len(mem_ids))})",
            (now, *mem_ids),
        )

    # ---------- reinforcement lifecycle ----------

    SIGNAL_DELTAS = {
        "used": 0.08,
        "important": 0.18,
        "irrelevant": -0.2,
        "incorrect": -0.5,
    }

    def reinforce_memory(self, memory_id: int, signal: str, reason: str = "") -> dict[str, Any]:
        """Apply a feedback signal. outdated/incorrect suppress without deleting;
        restore re-activates. Every event is appended to memory_feedback."""
        mem = self.get_memory(memory_id)
        if mem is None:
            raise ValueError(f"memory {memory_id} not found")
        if signal not in ("used", "important", "irrelevant", "incorrect", "outdated", "restore"):
            raise ValueError("signal must be one of: used, important, irrelevant, incorrect, outdated, restore")

        importance = float(mem.get("importance") if mem.get("importance") is not None else 0.5)
        state = mem.get("lifecycle_state") or "active"
        now = _now()

        if signal in ("outdated", "restore"):
            state = "outdated" if signal == "outdated" else "active"
            delta = 0.0
        elif signal == "incorrect":
            delta = -0.5
            state = "incorrect"
        elif signal == "irrelevant":
            # negative is proportional to current importance, applied immediately
            delta = -0.2 * importance
        else:
            # positive events saturate toward 0.95, damped by recent positives
            recent = self.one(
                "SELECT COUNT(*) AS c FROM memory_feedback WHERE memory_id = ? "
                "AND signal IN ('used','important') AND created_at >= ?",
                (memory_id, (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")),
            )["c"] or 0
            delta = self.SIGNAL_DELTAS[signal] * (0.95 - importance) / (1 + recent)

        new_importance = max(0.0, min(1.0, importance + delta))
        with self.tx() as conn:
            conn.execute(
                "UPDATE memory SET importance=?, lifecycle_state=?, "
                "reinforcement_count=reinforcement_count+1, last_reinforced_at=? WHERE id=?",
                (round(new_importance, 3), state, now, memory_id),
            )
            conn.execute(
                "INSERT INTO memory_feedback(memory_id, signal, delta, reason, created_at) VALUES(?,?,?,?,?)",
                (memory_id, signal, round(delta, 4), reason or None, now),
            )
        if mem.get("scope") == "shared":
            self._write_shared_file(self.get_memory(memory_id))
        return {
            "memory_id": memory_id,
            "signal": signal,
            "delta": round(delta, 4),
            "importance": round(new_importance, 3),
            "lifecycle_state": state,
        }

    def list_recent_memories(self, limit: int = 10, project: str | None = None,
                             include_outdated: bool = False) -> list[dict[str, Any]]:
        where = [] if include_outdated else ["lifecycle_state = 'active'"]
        params: list = []
        if project:
            where.append("project_id = (SELECT id FROM projects WHERE name = ?)")
            params.append(project)
        where_sql = ("WHERE " + " AND ".join(where)) if where else ""
        return self.q(
            f"SELECT id, title, content, tags, kind, scope, created_at FROM memory {where_sql} "
            "ORDER BY created_at DESC LIMIT ?",
            tuple(params) + (int(limit),),
        )

    def memory_feedback_for(self, memory_id: int) -> list[dict[str, Any]]:
        return self.q(
            "SELECT * FROM memory_feedback WHERE memory_id = ? ORDER BY created_at",
            (memory_id,),
        )

    def export_memories(self, path: str) -> dict[str, Any]:
        """Dump all memories + feedback to a JSON backup file."""
        import os

        p = Path(path)
        if not p.is_absolute():
            p = self.db_path.parent / p
        p.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "exported_at": _now(),
            "memories": self.q("SELECT * FROM memory ORDER BY id"),
            "feedback": self.q("SELECT * FROM memory_feedback ORDER BY id"),
        }
        if p.exists():
            raise ValueError(f"export path already exists: {p}")
        tmp = p.with_suffix(p.suffix + ".tmp")
        tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
        os.replace(tmp, p)
        return {"path": str(p), "memories": len(data["memories"]), "feedback_events": len(data["feedback"])}

    def memory_for_project(self, project_id: int, limit: int = 20) -> list[dict[str, Any]]:
        return self.q(
            "SELECT * FROM memory WHERE project_id = ? ORDER BY created_at DESC LIMIT ?",
            (project_id, int(limit)),
        )

    def session_context(self, project_id: int) -> dict[str, Any]:
        """The exact, bounded, deduplicated context session_start returns.

        Single source of truth so token measurements always match what the
        assistant actually receives.
        """
        def _clip(text: str, limit: int) -> str:
            text = (text or "").strip()
            return text if len(text) <= limit else text[:limit].rstrip() + "…"

        active = []
        for t in self.list_tasks(project_id):
            try:
                meta = json.loads(t["content"])
            except Exception:
                meta = {"title": t.get("title"), "status": "todo"}
            if meta.get("status", "todo") != "done":
                active.append({"id": t["id"], "title": meta.get("title", t["title"]), "status": meta.get("status", "todo")})
        recent = self.q(
            "SELECT title, content, created_at FROM memory WHERE project_id = ? AND lifecycle_state = 'active' "
            "AND kind IN ('chunk','summary') ORDER BY created_at DESC LIMIT 3",
            (project_id,),
        )
        recall = self.memory_recall_for(project_id, limit=8)
        shared = self.q(
            "SELECT title, content, tags FROM memory WHERE scope = 'shared' AND lifecycle_state = 'active' "
            "ORDER BY created_at DESC LIMIT 5"
        )
        return {
            "open_tasks": active,
            "recent_memory": [
                {"title": m["title"], "content": _clip(m["content"], 600), "created_at": m["created_at"]}
                for m in recent
            ],
            "shared_memory": [
                {"title": m["title"], "content": _clip(m["content"], 200), "tags": m["tags"]} for m in shared
            ],
            "recall": [
                {"title": m["title"], "content": _clip(m["content"], 400), "created_at": m["created_at"]}
                for m in recall
            ],
        }

    def context_token_measure(self, project_id: int, ctx: dict[str, Any] | None = None) -> dict[str, Any]:
        """Measured token budget for a project.

        Real data, not an estimate: both sides are counted with a real
        tokenizer (tiktoken cl100k_base).
          - stored_tokens: all project memory content (chunks + tasks + notes)
          - loaded_tokens: the actual session_start payload that gets returned
          - token_savings: stored - loaded  (context you no longer re-read raw)

        Pass `ctx` (already-computed session_context) to avoid recomputing it.
        """
        stored = 0
        for r in self.q("SELECT content FROM memory WHERE project_id = ?", (project_id,)):
            stored += count_tokens(r["content"] or "")
        # Same serialization session_start emits, so the loaded side is exact.
        loaded = count_tokens(json.dumps(ctx if ctx is not None else self.session_context(project_id), indent=2))
        return {
            "storedTokens": stored,
            "loadedTokens": loaded,
            "tokenSavings": max(0, stored - loaded),
        }

    def memory_recall_for(self, project_id: int, limit: int = 8) -> list[dict[str, Any]]:
        """Reduced-context recall for session start (active notes only)."""
        kinds = ("chunk", "summary", "task")
        ph = ",".join("?" * len(kinds))
        return self.q(
            f"SELECT title, content, created_at FROM memory WHERE project_id = ? "
            f"AND lifecycle_state = 'active' AND kind NOT IN ({ph}) "
            "ORDER BY updated_at DESC LIMIT ?",
            (project_id, *kinds, int(limit)),
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

        row = self.one("""
            SELECT
                SUM(CASE WHEN kind = 'task' AND json_valid(content) AND COALESCE(json_extract(content, '$.status'), 'todo') = 'done' THEN 1 ELSE 0 END) as done_tasks,
                SUM(CASE WHEN kind = 'task' AND (NOT json_valid(content) OR COALESCE(json_extract(content, '$.status'), 'todo') != 'done') THEN 1 ELSE 0 END) as active_tasks,
                SUM(CASE WHEN kind = 'chunk' THEN 1 ELSE 0 END) as chunks
            FROM memory
            WHERE project_id = ? AND kind IN ('task', 'chunk')
        """, (project_id,))

        done = row["done_tasks"] or 0
        active = row["active_tasks"] or 0
        chunks = row["chunks"] or 0

        tokens = self.context_token_measure(project_id)
        return {
            "activeTasks": active,
            "doneTasks": done,
            "totalTasks": total,
            "snapshots": chunks,
            "tokenSavings": tokens["tokenSavings"],
            "storedTokens": tokens["storedTokens"],
            "loadedTokens": tokens["loadedTokens"],
        }

    def all_project_metrics(self) -> dict[int, dict[str, Any]]:
        """Bulk metrics for every project (dashboard list): single streaming pass
        so the N+1 bottleneck is gone, with the same measured token savings that
        context_token_measure() reports (tiktoken stored-minus-loaded)."""
        def _clip(text: str, limit: int) -> str:
            text = (text or "").strip()
            return text if len(text) <= limit else text[:limit].rstrip() + "…"

        res: dict[int, dict[str, Any]] = {
            r["id"]: {
                "activeTasks": 0, "doneTasks": 0, "totalTasks": 0, "snapshots": 0,
                "storedTokens": 0, "loadedTokens": 0, "tokenSavings": 0,
                "_tasks": [], "_recent": [], "_recall": [],
            }
            for r in self.q("SELECT id FROM projects")
        }

        for r in self.q(
            "SELECT project_id, id, kind, content, title, tags, created_at, updated_at, lifecycle_state "
            "FROM memory"
        ):
            if (pid := r["project_id"]) not in res:
                continue
            m = res[pid]
            m["totalTasks"] += 1
            m["storedTokens"] += count_tokens(r["content"] or "")
            kind = r["kind"]
            if kind == "task":
                m["_tasks"].append(r)
            elif kind == "chunk":
                m["snapshots"] += 1
            if r["lifecycle_state"] == "active":
                if kind in ("chunk", "summary"):
                    m["_recent"].append(r)
                elif kind not in ("chunk", "summary", "task"):
                    m["_recall"].append(r)

        shared_dump = [
            {"title": m["title"], "content": _clip(m["content"], 200), "tags": m["tags"]}
            for m in self.q(
                "SELECT title, content, tags FROM memory WHERE scope = 'shared' AND lifecycle_state = 'active' "
                "ORDER BY created_at DESC LIMIT 5"
            )
        ]

        for pid, m in res.items():
            open_tasks = []
            for t in sorted(m["_tasks"], key=lambda x: x["created_at"], reverse=True):
                try:
                    meta = json.loads(t["content"])
                except Exception:
                    meta = {"title": t.get("title"), "status": "todo"}
                if meta.get("status", "todo") == "done":
                    m["doneTasks"] += 1
                    continue
                m["activeTasks"] += 1
                open_tasks.append({
                    "id": t["id"],
                    "title": meta.get("title", t["title"]),
                    "status": meta.get("status", "todo"),
                })
            recent = sorted(m["_recent"], key=lambda x: x["created_at"], reverse=True)[:3]
            recall = sorted(m["_recall"], key=lambda x: x["updated_at"], reverse=True)[:8]
            ctx = {
                "open_tasks": open_tasks,
                "recent_memory": [
                    {"title": r["title"], "content": _clip(r["content"], 600), "created_at": r["created_at"]}
                    for r in recent
                ],
                "shared_memory": shared_dump,
                "recall": [
                    {"title": r["title"], "content": _clip(r["content"], 400), "created_at": r["created_at"]}
                    for r in recall
                ],
            }
            m["loadedTokens"] = count_tokens(json.dumps(ctx, indent=2))
            m["tokenSavings"] = max(0, m["storedTokens"] - m["loadedTokens"])
            m.pop("_tasks", None)
            m.pop("_recent", None)
            m.pop("_recall", None)

        return res

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

        return {
            "projects": projects,
            "memoryEntries": memory,
            "ghScans": scans,
            "lastUpdate": _now(),
        }

    def close(self) -> None:
        with self._lock:
            self._conn.close()