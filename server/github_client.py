"""GitHub PR Health client (server-side).

Port of CheckGitHubRepo's github_pr_checker.html logic:
- REST mode (no token): exact open-PR count per repo via Link header.
- GraphQL mode (with PAT): extended metrics (draft, no-reviewer, stale, age,
  issues, labels, authors) and private repos.

All requests go to api.github.com only. The token is never exposed by callers.
"""
from __future__ import annotations

import re
import time
from datetime import datetime, timezone
from typing import Any

import httpx

GITHUB_API = "https://api.github.com"
GITHUB_GRAPHQL = "https://api.github.com/graphql"
STALE_DAYS = 30
MAX_PAGES = 10
CONCURRENCY = 8
RETRIES = 3


def _should_retry(resp: Any) -> bool:
    """Rate ceilings (403/429) and transient 5xx deserve a short backoff."""
    return resp.status_code in (403, 429) or resp.status_code >= 500


def _backoff(attempt: int) -> float:
    return min(1.0 * (1.5 ** attempt), 4.0)


def _get(*, url: str, headers: dict[str, str], timeout: float,
         follow_redirects: bool = False, retries: int = RETRIES) -> Any:
    for attempt in range(retries):
        res = httpx.get(url, headers=headers, timeout=timeout, follow_redirects=follow_redirects)
        if not _should_retry(res) or attempt >= retries - 1:
            return res
        time.sleep(_backoff(attempt))
    return res


def _post(*, url: str, headers: dict[str, str], json: dict[str, Any],
          timeout: float, retries: int = RETRIES) -> Any:
    for attempt in range(retries):
        res = httpx.post(url, headers=headers, json=json, timeout=timeout)
        if not _should_retry(res) or attempt >= retries - 1:
            return res
        time.sleep(_backoff(attempt))
    return res


def _days_between(iso: str | None) -> int | None:
    if not iso:
        return None
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except Exception:
        return None
    return max(0, (datetime.now(timezone.utc) - dt).days)


class GithubClient:
    def __init__(self, token: str = "", *, stale_days: int = 30):
        self.token = token
        self.stale_days = stale_days
        self._headers = {"Accept": "application/vnd.github+json"}
        if token:
            self._headers["Authorization"] = f"Bearer {token}"

    # ---- auth diagnostics (never returns the token) ----

    def token_info(self) -> dict[str, Any]:
        if not self.token:
            return {"token_set": False}
        try:
            res = _get(url=f"{GITHUB_API}/user", headers=self._headers, timeout=15)
            if res.status_code != 200:
                return {"token_set": True, "valid": False, "status": res.status_code}
            scopes = res.headers.get("x-oauth-scopes", "")
            data = res.json()
            return {
                "token_set": True,
                "valid": True,
                "login": data.get("login"),
                "scopes": [s.strip() for s in scopes.split(",") if s.strip()],
            }
        except Exception as e:
            return {"token_set": True, "valid": False, "error": str(e)}

    # ---- GraphQL mode ----

    def scan_graphql(self, login: str, *, extended: bool, include_collab: bool) -> dict[str, Any]:
        author_counts: dict[str, int] = {}
        label_counts: dict[str, int] = {}
        pr_part = (
            "pullRequests(states:OPEN,first:100,orderBy:{field:CREATED_AT,direction:ASC}){"
            "totalCount nodes{isDraft createdAt updatedAt reviews{totalCount} author{login} "
            "reviewRequests{totalCount} labels(first:3){nodes{name}}}}"
            if extended
            else "pullRequests(states:OPEN){totalCount}"
        )
        issue_part = "issues(states:OPEN){totalCount}" if extended else ""
        per_page = 100 if extended else 100
        query = (
            "query($login:String!,$cursor:String){repositoryOwner(login:$login){__typename "
            "repositories(first:%d,after:$cursor,orderBy:{field:NAME,direction:ASC}){pageInfo{hasNextPage endCursor} "
            "totalCount nodes{name nameWithOwner url stargazerCount isFork isArchived isPrivate "
            "primaryLanguage{name} owner{login} updatedAt %s %s}}}}"
            % (per_page, pr_part, issue_part)
        )
        cursor: str | None = None
        out: list[dict[str, Any]] = []
        while True:
            res = _post(
                url=GITHUB_GRAPHQL,
                headers={**self._headers, "Content-Type": "application/json"},
                json={"query": query, "variables": {"login": login, "cursor": cursor}},
                timeout=30,
            )
            if res.status_code == 401:
                raise RuntimeError("Invalid token (401). Check your GitHub token.")
            if res.status_code == 403:
                raise RuntimeError("GitHub rate limit reached (GraphQL).")
            json_data = res.json()
            if json_data.get("errors"):
                raise RuntimeError("GraphQL: " + json_data["errors"][0].get("message", "unknown error"))
            owner = json_data.get("data", {}).get("repositoryOwner")
            if not owner:
                raise RuntimeError(f'Account "{login}" not found.')
            conn = owner["repositories"]
            for node in conn.get("nodes", []):
                repo_owner = (node.get("owner") or {}).get("login", login)
                if not include_collab and owner.get("__typename") == "User" and repo_owner != login:
                    continue
                prs = node.get("pullRequests") or {}
                r: dict[str, Any] = {
                    "owner": repo_owner,
                    "name": node.get("name"),
                    "fullName": node.get("nameWithOwner"),
                    "url": node.get("url"),
                    "stars": node.get("stargazerCount") or 0,
                    "language": (node.get("primaryLanguage") or {}).get("name"),
                    "fork": bool(node.get("isFork")),
                    "archived": bool(node.get("isArchived")),
                    "private": bool(node.get("isPrivate")),
                    "updatedRaw": node.get("updatedAt"),
                    "openPRs": prs.get("totalCount"),
                    "draftPRs": None,
                    "noReviewer": None,
                    "stalePRs": None,
                    "oldestPRDate": None,
                    "oldestPRDays": None,
                    "openIssues": (node.get("issues") or {}).get("totalCount") if extended else None,
                }
                nodes = prs.get("nodes") or []
                if extended and nodes:
                    r["draftPRs"] = sum(1 for p in nodes if p.get("isDraft"))
                    r["noReviewer"] = sum(
                        1
                        for p in nodes
                        if not p.get("isDraft")
                        and (p.get("reviewRequests") or {}).get("totalCount", 0) == 0
                        and (p.get("reviews") or {}).get("totalCount", 0) == 0
                    )
                    # Stale = no push on the PR branch (updatedAt), not age since
                    # creation: an old-but-active PR is never "stale".
                    r["stalePRs"] = sum(
                        1 for p in nodes if (_days_between(p.get("updatedAt")) or 0) >= self.stale_days
                    )
                    r["oldestPRDate"] = nodes[0].get("createdAt")
                    r["oldestPRDays"] = _days_between(nodes[0].get("createdAt"))
                    for p in nodes:
                        author = (p.get("author") or {}).get("login")
                        if author:
                            author_counts[author] = author_counts.get(author, 0) + 1
                        for lbl in (p.get("labels") or {}).get("nodes") or []:
                            name = lbl.get("name")
                            if name:
                                label_counts[name] = label_counts.get(name, 0) + 1
                out.append(r)
            if not conn.get("pageInfo", {}).get("hasNextPage"):
                break
            cursor = conn["pageInfo"].get("endCursor")
        return {"repos": out, "authors": author_counts, "labels": label_counts}

    # ---- REST mode ----

    def list_repos_rest(self, login: str) -> list[dict[str, Any]]:
        def page(kind: str, p: int):
            url = f"{GITHUB_API}/{kind}/{login}/repos?per_page=100&page={p}&sort=full_name&type=owner"
            return _get(url=url, headers=self._headers, timeout=30)

        kind = "users"
        first = page("users", 1)
        if first.status_code == 404:
            kind = "orgs"
            first = page("orgs", 1)
        if first.status_code == 404:
            raise RuntimeError(f'Account "{login}" not found.')
        if first.status_code != 200:
            raise RuntimeError(f"GitHub error ({first.status_code}) fetching repositories for {login}.")
        all_repos = first.json()
        p = 2
        while len(all_repos) % 100 == 0 and len(all_repos) > 0 and p <= MAX_PAGES:
            res = page(kind, p)
            if res.status_code != 200 or not res.json():
                break
            all_repos.extend(res.json())
            p += 1
        return [
            {
                "owner": login,
                "name": r.get("name"),
                "fullName": r.get("full_name"),
                "url": r.get("html_url"),
                "stars": r.get("stargazers_count") or 0,
                "language": r.get("language"),
                "fork": bool(r.get("fork")),
                "archived": bool(r.get("archived")),
                "private": bool(r.get("private")),
                "updatedRaw": r.get("updated_at"),
                "openPRs": None,
                "draftPRs": None,
                "noReviewer": None,
                "stalePRs": None,
                "oldestPRDate": None,
                "oldestPRDays": None,
                "openIssues": None,
            }
            for r in all_repos
        ]

    def count_open_prs_rest(self, full_name: str) -> int | None:
        url = f"{GITHUB_API}/repos/{full_name}/pulls?state=open&per_page=1"
        try:
            res = _get(url=url, headers=self._headers, timeout=30)
        except Exception:
            return None
        if res.status_code != 200:
            return None
        link = res.headers.get("Link", "")
        m = re.search(r"[?&]page=(\d+)[^>]*>;\s*rel=\"last\"", link)
        if m:
            return int(m.group(1))
        data = res.json()
        return len(data) if isinstance(data, list) else 0

    def count_rest(self, repos: list[dict[str, Any]]) -> None:
        from concurrent.futures import ThreadPoolExecutor

        def worker(r: dict[str, Any]) -> None:
            r["openPRs"] = self.count_open_prs_rest(r["fullName"])

        with ThreadPoolExecutor(max_workers=CONCURRENCY) as pool:
            list(pool.map(worker, repos))

    # ---- single repo state ----

    def repo_state(self, full_name: str) -> str:
        """Return 'ok' | 'archived' | 'deleted' | 'unknown' for owner/repo.

        Never raises. 'unknown' (network error, rate limit, or an untrusted 404)
        must not change the previous state: only a 404 with a token that can see
        the repo proves deletion (unauthenticated 404 == private repo too).
        """
        try:
            res = _get(
                url=f"{GITHUB_API}/repos/{full_name}",
                headers=self._headers, timeout=15, follow_redirects=True,
            )
        except Exception:
            return "unknown"
        if res.status_code == 404:
            return "deleted" if self.token else "unknown"
        if res.status_code != 200:
            return "unknown"
        try:
            data = res.json()
        except Exception:
            return "unknown"
        return "archived" if bool(data.get("archived")) else "ok"

    # ---- orchestration ----

    def scan(self, accounts: list[str], *, extended: bool = True, include_forks: bool = False,
             include_archived: bool = False, include_collab: bool = True) -> dict[str, Any]:
        method = "graphql" if self.token and extended else "rest"
        all_repos: list[dict[str, Any]] = []
        author_counts: dict[str, int] = {}
        label_counts: dict[str, int] = {}
        for login in accounts:
            if method == "graphql":
                result = self.scan_graphql(login, extended=extended, include_collab=include_collab)
                repos = result["repos"]
                for author, count in result["authors"].items():
                    author_counts[author] = author_counts.get(author, 0) + count
                for label, count in result["labels"].items():
                    label_counts[label] = label_counts.get(label, 0) + count
            else:
                repos = self.list_repos_rest(login)
                self.count_rest(repos)
            if not include_forks:
                repos = [r for r in repos if not r.get("fork")]
            if not include_archived:
                repos = [r for r in repos if not r.get("archived")]
            all_repos.extend(repos)
        return {
            "method": method,
            "repos": all_repos,
            "authors": author_counts,
            "labels": label_counts,
            "totalRepos": len(all_repos),
            "totalPRs": sum((r.get("openPRs") or 0) for r in all_repos),
        }