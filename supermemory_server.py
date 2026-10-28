"""Minimal SuperMemory server running inside OmniState container.
Provides the API v5 endpoints that the OmniState client expects.
Runs on port 6767.
"""
import json
import os
import threading
import time
import uuid
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import Body, FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="SuperMemory Local Server", version="5.0.1")

# In-memory storage for demo purposes
memories_store: dict[str, dict[str, dict[str, Any]]] = {}
profiles_store: dict[str, dict[str, Any]] = {}

DATA_FILE = Path(os.environ.get("OMNISTATE_DATA", "/data")) / "supermemory_local.json"
_lock = threading.Lock()


def _load() -> None:
    global memories_store, profiles_store
    try:
        if DATA_FILE.exists():
            raw = json.loads(DATA_FILE.read_text(encoding="utf-8"))
            memories_store = raw.get("memories", {}) or {}
            profiles_store = raw.get("profiles", {}) or {}
    except Exception:
        memories_store = {}
        profiles_store = {}


def _save() -> None:
    try:
        DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
        tmp = DATA_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps({"memories": memories_store, "profiles": profiles_store}), encoding="utf-8")
        tmp.replace(DATA_FILE)
    except Exception:
        pass


def _ns(namespace: str | None) -> str:
    ns = (namespace or "").strip()
    return ns or "sm_project_default"


def _ensure_ns(ns: str) -> None:
    memories_store.setdefault(ns, {})
    profiles_store.setdefault(ns, {"static": [], "dynamic": [], "buckets": {}})


@app.on_event("startup")
async def startup() -> None:
    _load()
    _ensure_ns("sm_project_default")


# ---- API Endpoints ----

@app.post("/ns/{namespace}/search")
async def search(namespace: str, body: dict[str, Any] = Body(default={})):
    ns = _ns(namespace)
    _ensure_ns(ns)
    q = str(body.get("query") or "").strip()
    limit = int(body.get("limit") or 10)
    results = []
    items = list(memories_store.get(ns, {}).values())
    # newest first
    items = items[-limit:] if limit else items
    for mem in items:
        text = mem.get("content", "") or ""
        title = mem.get("title", "") or (text.strip().splitlines()[0][:60] if text.strip() else "Untitled")
        if q and q.lower() not in (title + " " + text).lower():
            continue
        results.append({
            "id": mem.get("id"),
            "memory": text,
            "chunk": text,
            "similarity": 0.5,
            "metadata": {"title": title, **(mem.get("metadata") or {})},
            "system": {},
            "isLatest": True,
            "isInference": False,
        })
    return {"query": q, "namespace": ns, "results": results, "total": len(results)}


@app.post("/ns/{namespace}/list/memories")
async def list_memories(namespace: str, limit: int = 10, body: dict[str, Any] = Body(default={})):
    ns = _ns(namespace)
    _ensure_ns(ns)
    lim = int(limit or body.get("limit") or 10)
    results = []
    items = list(memories_store.get(ns, {}).values())[-lim:]
    for mem in items:
        text = mem.get("content", "") or ""
        title = mem.get("title", "") or (text.strip().splitlines()[0][:60] if text.strip() else "Untitled")
        results.append({
            "id": mem.get("id"),
            "memory": text,
            "metadata": {"title": title, **(mem.get("metadata") or {})},
            "isStatic": mem.get("isStatic", False),
            "isInference": mem.get("isInference", False),
        })
    return {"memories": results, "results": results, "total": len(results)}


@app.post("/ns/{namespace}/profile")
async def profile(namespace: str, body: dict[str, Any] = Body(default={})):
    ns = _ns(namespace)
    _ensure_ns(ns)
    prof = profiles_store.get(ns, {"static": [], "dynamic": [], "buckets": {}})
    return {"namespace": ns, "profile": {
        "static": prof.get("static", []),
        "dynamic": prof.get("dynamic", []),
        "buckets": prof.get("buckets", {}),
    }}


@app.post("/ns/{namespace}/document")
async def add_document(namespace: str, body: dict[str, Any] = Body(default={})):
    ns = _ns(namespace)
    _ensure_ns(ns)
    content = body.get("content") or ""
    metadata = body.get("metadata") or {}
    title = metadata.get("title") or body.get("title") or ""
    mem_id = str(uuid.uuid4())
    mem_data = {
        "id": mem_id,
        "title": title or f"Memory {mem_id[:8]}",
        "content": content,
        "namespace": ns,
        "metadata": metadata,
        "isStatic": False,
        "isInference": False,
        "created_at": time.time(),
    }
    with _lock:
        memories_store[ns][mem_id] = mem_data
        _save()
    return {"id": mem_id, "content_id": mem_id, "namespace": ns, "status": "success"}


@app.get("/health")
async def health():
    return {"status": "ok", "service": "supermemory-local", "port": 6767}


if __name__ == "__main__":
    print("SuperMemory local server started on port 6767")
    uvicorn.run(app, host="0.0.0.0", port=6767)
