"""OmniState server configuration.

Loads config from /data/config.json (or OMNISTATE_DATA dir) with env overrides.
Root mapping host<->container is defined here (see DESIGN.md §3).
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Root:
    host: str
    container: str

    def host_to_container(self, host_path: str) -> str | None:
        h = os.path.abspath(host_path)
        if h == self.host or h.startswith(self.host.rstrip("/") + "/"):
            rel = os.path.relpath(h, self.host)
            return str(Path(self.container) / rel)
        return None

    def container_to_host(self, container_path: str) -> str | None:
        c = os.path.abspath(container_path)
        if c == self.container or c.startswith(self.container.rstrip("/") + "/"):
            rel = os.path.relpath(c, self.container)
            return str(Path(self.host) / rel)
        return None


@dataclass
class GithubConfig:
    accounts: list[str] = field(default_factory=list)
    token: str = ""
    extended: bool = True
    include_forks: bool = False
    include_archived: bool = False
    scan_interval_hours: int = 6
    stale_days: int = 30


@dataclass
class SupermemoryConfig:
    api_key: str = ""
    base_url: str = "https://api.supermemory.ai"
    api_version: str = "v5"
    default_space: str = "sm_project_default"
    enabled: bool = False
    sync_interval_hours: int = 6
    sync_on_session_end: bool = True


@dataclass
class Config:
    data_dir: Path
    port: int = 8347
    roots: list[Root] = field(default_factory=list)
    github: GithubConfig = field(default_factory=GithubConfig)
    supermemory: SupermemoryConfig = field(default_factory=SupermemoryConfig)
    scan_interval_seconds: int = 300
    reindex_on_change: bool = True
    auto_import_legacy: bool = False
    # Bearer token protecting /api/* and MCP session creation (network access).
    # Empty = open (trusted localhost only). Never logged.
    auth_token: str = ""

    # ---- derived paths ----
    @property
    def db_path(self) -> Path:
        return self.data_dir / "index.db"

    @property
    def shared_dir(self) -> Path:
        return self.data_dir / "shared"

    @property
    def config_path(self) -> Path:
        return self.data_dir / "config.json"

    @property
    def logs_dir(self) -> Path:
        return self.data_dir / "logs"

    def resolve_host_root(self, host_path: str) -> Root | None:
        for root in self.roots:
            if root.host_to_container(host_path) is not None:
                return root
        return None

    def to_host_path(self, container_path: str) -> str | None:
        for root in self.roots:
            h = root.container_to_host(container_path)
            if h is not None:
                return h
        return container_path


def _default_data_dir() -> Path:
    env = os.environ.get("OMNISTATE_DATA")
    if env:
        return Path(env)
    return Path.home() / ".omnistate" / "server"


def _parse_roots(value: str | None) -> list[Root]:
    """Parse OMNISTATE_ROOTS env var like 'host1:container1,host2:container2'."""
    roots: list[Root] = []
    if not value:
        return roots
    for pair in value.split(","):
        pair = pair.strip()
        if not pair:
            continue
        if ":" in pair:
            host, container = pair.split(":", 1)
            roots.append(Root(host=host.strip(), container=container.strip()))
    return roots


_ENV_REF_RE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")
_ENV_NAME_RE = re.compile(r"[A-Z][A-Z0-9_]*")


def token_env_ref(value: str) -> str | None:
    """Return the environment-variable name when `value` is a placeholder
    reference rather than a real token.

    `config.json` is sometimes written with the *name* of the variable
    (e.g. "GITHUB_TOKEN" or "${GITHUB_TOKEN}") instead of its value. Real
    GitHub tokens are never bare all-caps names (they are `ghp_...`,
    `github_pat_...`, ...), so such a value is always a placeholder.
    """
    v = (value or "").strip()
    m = _ENV_REF_RE.fullmatch(v)
    if m:
        return m.group(1)
    if _ENV_NAME_RE.fullmatch(v):
        return v
    return None


def resolve_token_placeholder(value: str, env: dict | None = None) -> str:
    """Resolve a placeholder token from the environment, or clear it.

    A placeholder that cannot be resolved is returned as an empty string so
    the server falls back to unauthenticated REST mode instead of sending a
    bogus token to GitHub (which yields confusing 401/400 errors).
    """
    name = token_env_ref(value)
    if name is None:
        return value
    return str((env or {}).get(name, "") or "")


def load_config(data_dir: Path | None = None, env: dict | None = None) -> Config:
    env = env if env is not None else os.environ
    data_dir = data_dir or _default_data_dir()
    data_dir = Path(data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)

    cfg = Config(data_dir=data_dir)

    cfg_file = data_dir / "config.json"
    if cfg_file.exists():
        try:
            raw = json.loads(cfg_file.read_text(encoding="utf-8"))
        except Exception:
            raw = {}
        cfg.port = int(raw.get("port", cfg.port))
        cfg.scan_interval_seconds = int(raw.get("scan_interval_seconds", cfg.scan_interval_seconds))
        cfg.reindex_on_change = bool(raw.get("reindex_on_change", cfg.reindex_on_change))
        cfg.auto_import_legacy = bool(raw.get("auto_import_legacy", cfg.auto_import_legacy))
        cfg.auth_token = str(raw.get("auth_token", "") or "")
        for r in raw.get("roots", []):
            cfg.roots.append(Root(host=r.get("host", ""), container=r.get("container", "")))
        gh = raw.get("github", {})
        sm = raw.get("supermemory", {})
        cfg.supermemory = SupermemoryConfig(
            api_key=str(sm.get("api_key", "") or ""),
            base_url=str(sm.get("base_url", cfg.supermemory.base_url)),
            api_version=str(sm.get("api_version", cfg.supermemory.api_version)),
            default_space=str(sm.get("default_space", cfg.supermemory.default_space)),
            enabled=bool(sm.get("enabled", cfg.supermemory.enabled)),
            sync_interval_hours=int(sm.get("sync_interval_hours", 6)),
            sync_on_session_end=bool(sm.get("sync_on_session_end", True)),
        )
        cfg.github.accounts = list(gh.get("accounts", []))
        cfg.github.token = resolve_token_placeholder(str(gh.get("token", "") or ""), env)
        cfg.github.extended = bool(gh.get("extended", True))
        cfg.github.include_forks = bool(gh.get("include_forks", False))
        cfg.github.include_archived = bool(gh.get("include_archived", False))
        cfg.github.scan_interval_hours = int(gh.get("scan_interval_hours", 6))
        cfg.github.stale_days = int(gh.get("stale_days", 30))

    # Env overrides
    if env.get("OMNISTATE_PORT"):
        cfg.port = int(env["OMNISTATE_PORT"])
    env_roots = _parse_roots(env.get("OMNISTATE_ROOTS"))
    if env_roots:
        cfg.roots = env_roots
    if "GITHUB_TOKEN" in env:
        cfg.github.token = env["GITHUB_TOKEN"]
    if "GITHUB_ACCOUNTS" in env:
        cfg.github.accounts = [
            a.strip() for a in env["GITHUB_ACCOUNTS"].split(",") if a.strip()
        ]
    if env.get("GITHUB_SCAN_INTERVAL_HOURS"):
        cfg.github.scan_interval_hours = int(env["GITHUB_SCAN_INTERVAL_HOURS"])
    if env.get("OMNISTATE_SCAN_INTERVAL_SECONDS"):
        cfg.scan_interval_seconds = int(env["OMNISTATE_SCAN_INTERVAL_SECONDS"])
    if env.get("OMNISTATE_AUTO_IMPORT_LEGACY") is not None:
        cfg.auto_import_legacy = env["OMNISTATE_AUTO_IMPORT_LEGACY"].strip().lower() in ("1", "true", "yes", "on")
    if env.get("OMNISTATE_AUTH_TOKEN") is not None:
        cfg.auth_token = env["OMNISTATE_AUTH_TOKEN"].strip()
    if env.get("SUPERMEMORY_API_KEY"):
        cfg.supermemory.api_key = env["SUPERMEMORY_API_KEY"]
    if env.get("SUPERMEMORY_BASE_URL"):
        cfg.supermemory.base_url = env["SUPERMEMORY_BASE_URL"]
    if env.get("SUPERMEMORY_API_VERSION"):
        cfg.supermemory.api_version = env["SUPERMEMORY_API_VERSION"]
    if env.get("SUPERMEMORY_DEFAULT_SPACE"):
        cfg.supermemory.default_space = env["SUPERMEMORY_DEFAULT_SPACE"]
    if env.get("SUPERMEMORY_ENABLED") is not None:
        cfg.supermemory.enabled = env["SUPERMEMORY_ENABLED"].strip().lower() in ("1", "true", "yes", "on")

    for d in (cfg.shared_dir, cfg.logs_dir):
        d.mkdir(parents=True, exist_ok=True)
    return cfg


def save_config(cfg: Config) -> None:
    payload = {
        "port": cfg.port,
        "roots": [{"host": r.host, "container": r.container} for r in cfg.roots],
        "scan_interval_seconds": cfg.scan_interval_seconds,
        "reindex_on_change": cfg.reindex_on_change,
        "auto_import_legacy": cfg.auto_import_legacy,
        "auth_token": cfg.auth_token,
        "supermemory": {
            "api_key": cfg.supermemory.api_key,
            "base_url": cfg.supermemory.base_url,
            "api_version": cfg.supermemory.api_version,
            "default_space": cfg.supermemory.default_space,
            "enabled": cfg.supermemory.enabled,
        },
        "github": {
            "accounts": cfg.github.accounts,
            "token": cfg.github.token,
            "extended": cfg.github.extended,
            "include_forks": cfg.github.include_forks,
            "include_archived": cfg.github.include_archived,
            "scan_interval_hours": cfg.github.scan_interval_hours,
            "stale_days": cfg.github.stale_days,
        },
    }
    tmp = cfg.config_path.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    tmp.replace(cfg.config_path)