"""Thin Python client for the Supermemory REST API (v5).

Replaces the previous Node.js/node-fetch stubs with real HTTP calls using
httpx, which is already a project dependency. All methods are synchronous;
async callers (MCP tools) wrap them with ``asyncio.to_thread``.
"""
from __future__ import annotations

import logging
from typing import Any

import httpx

log = logging.getLogger("omnistate.supermemory")


class SupermemoryError(Exception):
    """Raised when a Supermemory API call fails or is mis-configured."""


class SupermemoryClient:
    def __init__(self, cfg: Any) -> None:
        self.cfg = cfg
        # Accept either a top-level Config (with .supermemory), a mapping, or a
        # SupermemoryConfig directly, so callers can pass either.
        if isinstance(cfg, dict):
            sm = cfg.get("supermemory", cfg)
        else:
            sm = getattr(cfg, "supermemory", cfg)
        self.sm = sm if sm is not None else cfg

        if isinstance(self.sm, dict):
            self.base_url = str(self.sm.get("base_url", "") or "").rstrip("/")
            self.api_key = str(self.sm.get("api_key", "") or "")
            self.default_space = str(self.sm.get("default_space", "") or "sm_project_default")
        else:
            self.base_url = str(getattr(self.sm, "base_url", "") or "").rstrip("/")
            self.api_key = str(getattr(self.sm, "api_key", "") or "")
            self.default_space = str(getattr(self.sm, "default_space", "") or "sm_project_default")

    # ---------- helpers ----------

    def _ensure_enabled(self) -> None:
        sm = self.sm
        if isinstance(sm, dict):
            enabled = sm.get("enabled", False)
            api_key = sm.get("api_key", self.api_key)
        else:
            enabled = getattr(sm, "enabled", False)
            api_key = getattr(sm, "api_key", self.api_key)
        if not enabled:
            raise SupermemoryError("Supermemory integration is disabled. Set SUPERMEMORY_ENABLED=1.")
        if not (api_key or self.api_key):
            raise SupermemoryError("Supermemory API key not configured. Set SUPERMEMORY_API_KEY.")

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    def _request(self, method: str, path: str, *, params: dict[str, Any] | None = None,
                 json: Any = None, timeout: float = 30.0) -> dict[str, Any]:
        self._ensure_enabled()
        url = self._url(path)
        try:
            with httpx.Client(timeout=timeout) as client:
                resp = client.request(method, url, params=params, json=json, headers=self._headers())
        except httpx.HTTPError as e:
            raise SupermemoryError(f"Supermemory request failed: {e}") from e
        if resp.status_code >= 400:
            try:
                detail = resp.json()
            except Exception:  # noqa: BLE001
                detail = resp.text
            raise SupermemoryError(f"Supermemory API error {resp.status_code}: {detail}")
        try:
            return resp.json()
        except Exception as e:  # noqa: BLE001
            raise SupermemoryError(f"Supermemory returned non-JSON response: {e}") from e

    def _namespace(self, namespace: str | None) -> str:
        ns = (namespace or "").strip() or self.default_space
        return ns

    # ---------- public API ----------

    def search(self, namespace: str = "", query: str = "", limit: int = 10,
               search_mode: str = "hybrid") -> dict[str, Any]:
        ns = self._namespace(namespace)
        q = (query or "").strip()
        if not q:
            # Fall back to listing recent memories for "empty query" callers.
            return self.list_memories(namespace=ns, limit=limit)
        body = {"query": q, "limit": max(1, min(int(limit or 10), 100)), "searchMode": search_mode}
        data = self._request("POST", f"/ns/{ns}/search", json=body)
        results = []
        for r in (data.get("results") or []):
            text = r.get("memory") or r.get("chunk") or ""
            meta = r.get("metadata") or {}
            title = meta.get("title")
            if not title and text:
                title = text.strip().splitlines()[0][:60]
            results.append({
                "id": r.get("id"),
                "title": title,
                "content": text,
                "namespace": ns,
                "score": r.get("similarity"),
                "metadata": r.get("metadata") or {},
                "system": r.get("system") or {},
                "isLatest": r.get("isLatest"),
                "isInference": r.get("isInference"),
                "raw": r,
            })
        return {"query": q, "namespace": ns, "results": results, "total": len(results)}

    def list_memories(self, namespace: str = "", limit: int = 10) -> dict[str, Any]:
        ns = self._namespace(namespace)
        params = {"limit": max(1, min(int(limit or 10), 100)), "sort": "createdAt", "order": "desc"}
        data = self._request("POST", f"/ns/{ns}/list/memories", params=params, json={})
        results = []
        for m in (data.get("memories") or []):
            meta = m.get("metadata") or {}
            text = m.get("memory") or ""
            title = meta.get("title")
            if not title and text:
                title = text.strip().splitlines()[0][:60]
            results.append({
                "id": m.get("id"),
                "title": title,
                "content": text,
                "namespace": ns,
                "score": None,
                "metadata": m.get("metadata") or {},
                "system": m.get("system") or {},
                "isStatic": m.get("isStatic"),
                "isInference": m.get("isInference"),
                "raw": m,
            })
        return {"query": "", "namespace": ns, "results": results, "total": len(results)}

    def profile(self, namespace: str = "") -> dict[str, Any]:
        ns = self._namespace(namespace)
        data = self._request("POST", f"/ns/{ns}/profile", json={})
        prof = data.get("profile") or {}
        # Normalize static/dynamic items to {id, memory}
        def _norm(items):
            out = []
            for it in (items or []):
                out.append({"id": it.get("id"), "memory": it.get("memory")})
            return out
        return {
            "namespace": ns,
            "profile": {
                "static": _norm(prof.get("static")),
                "dynamic": _norm(prof.get("dynamic")),
                "buckets": prof.get("buckets") or {},
            },
        }

    def add(self, namespace: str = "", content: str = "", title: str = "",
            tags: str = "", source: str = "", metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        ns = self._namespace(namespace)
        if not (content or "").strip():
            raise SupermemoryError("content is required")
        meta: dict[str, Any] = {}
        if metadata:
            meta.update(metadata)
        if tags:
            if isinstance(tags, (list, tuple)):
                meta["tags"] = [str(t).strip() for t in tags if str(t).strip()]
            else:
                meta["tags"] = [t.strip() for t in str(tags).split(",") if t.strip()]
        if source:
            meta["source"] = source
        if title:
            meta["title"] = title
        body: dict[str, Any] = {"content": content}
        if meta:
            body["metadata"] = meta
        # dreaming instant for immediate availability
        body["dreaming"] = "instant"
        data = self._request("POST", f"/ns/{ns}/document", json=body)
        return {
            "namespace": ns,
            "content_id": data.get("id"),
            "status": data.get("status"),
            "title": title or None,
        }

    def sync_from_store(self, store: Any, project: str = "", namespace: str = "",
                        limit: int = 50) -> dict[str, Any]:
        ns = self._namespace(namespace)
        limit = max(1, min(int(limit or 50), 500))
        # Collect OmniState memories.
        memories: list[dict[str, Any]] = []
        if project:
            row = store.get_project(project)
            if row is None:
                raise SupermemoryError(f"Project '{project}' not found.")
            memories = store.memory_for_project(int(row["id"]), limit=limit)
        else:
            memories = store.list_recent_memories(limit=limit)
        synced = 0
        errors: list[str] = []
        for m in memories:
            content = m.get("content") or m.get("title") or ""
            if not str(content).strip():
                continue
            title = (m.get("title") or "")[:120]
            tags = m.get("tags") or []
            if isinstance(tags, str):
                try:
                    import json as _json
                    parsed = _json.loads(tags)
                    if isinstance(parsed, list):
                        tags = parsed
                    else:
                        tags = [t.strip() for t in tags.split(",") if t.strip()]
                except Exception:  # noqa: BLE001
                    tags = [t.strip() for t in tags.split(",") if t.strip()]
            tags = [str(t).strip() for t in (tags or []) if str(t).strip()]
            try:
                self.add(namespace=ns, content=str(content), title=title,
                         tags=",".join(tags) if tags else "", source="omnistate-sync",
                         metadata={"omnistate_id": m.get("id"), "scope": m.get("scope")})
                synced += 1
            except Exception as e:  # noqa: BLE001
                errors.append(str(e))
        return {
            "project": project or "",
            "namespace": ns,
            "memories_found": len(memories),
            "memories_synced": synced,
            "errors": errors,
            "status": "sync_completed",
        }


def client_from_config(cfg: Any) -> SupermemoryClient:
    return SupermemoryClient(cfg)
