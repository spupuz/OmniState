"""OmniState server entrypoint.

Runs one uvicorn process exposing:
  /mcp    — MCP Streamable HTTP
  /api/*  — REST for the dashboard
  /       — dashboard web
  /health — healthcheck
"""
from __future__ import annotations

import asyncio
import logging
import os
import threading

import uvicorn
from fastapi import FastAPI

from .app import App
from .config import load_config
from .mcp_server import create_server
from .store import Store

logger = logging.getLogger("omnistate")


def build_app() -> FastAPI:
    cfg = load_config()
    store = Store(cfg.db_path)
    app_holder = App(cfg, store)

    # MCP Streamable HTTP at /mcp (lifespan composed into the FastAPI app)
    app_holder.mount_mcp()

    # Background scheduler: periodic project discovery + scheduled GitHub scans
    app_holder.start_scheduler()
    return app_holder.fastapi


app = build_app()


if __name__ == "__main__":
    port = int(os.environ.get("OMNISTATE_PORT", "8347"))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")