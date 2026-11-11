"""Extract raw data from the GitHub REST API.

Each tool produces one raw record:
    {"tool": {...config...}, "repo": {...}, "commit_activity": [...], "releases": [...]}

Set GITHUB_TOKEN in your environment to raise the rate limit from 60 to 5,000 requests/hour.
"""

from __future__ import annotations

import logging
import os
import time
from pathlib import Path

import requests
import yaml

log = logging.getLogger(__name__)

API = "https://api.github.com"
MAX_RETRIES = 5


def load_tools(path: str | Path) -> list[dict]:
    """Read the list of tools to track from a YAML config file."""
    with open(path, encoding="utf-8") as f:
        tools = yaml.safe_load(f)["tools"]
    for t in tools:
        missing = {"name", "repo", "category"} - t.keys()
        if missing:
            raise ValueError(f"Tool entry {t} is missing {sorted(missing)}")
    return tools


class GitHubClient:
    """Small wrapper around the GitHub API with auth, retries and rate-limit handling."""

    def __init__(self, token: str | None = None, session: requests.Session | None = None):
        self.session = session or requests.Session()
        self.session.headers.update({
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        })
        token = token or os.getenv("GITHUB_TOKEN")
        if token:
            self.session.headers["Authorization"] = f"Bearer {token}"

    def get(self, path: str, params: dict | None = None):
        url = f"{API}{path}"
        for attempt in range(1, MAX_RETRIES + 1):
            resp = self.session.get(url, params=params, timeout=30)

            # Statistics endpoints return 202 while GitHub computes the data in the background.
            if resp.status_code == 202:
                log.info("GitHub is computing stats for %s, retrying (%d)", path, attempt)
                time.sleep(2 * attempt)
                continue

            if resp.status_code == 403 and resp.headers.get("X-RateLimit-Remaining") == "0":
                reset = int(resp.headers.get("X-RateLimit-Reset", time.time() + 60))
                wait = max(reset - time.time(), 1)
                raise RuntimeError(
                    f"GitHub rate limit hit; resets in {wait:.0f}s. Set GITHUB_TOKEN to raise the limit."
                )

            if resp.status_code >= 500:
                time.sleep(2 * attempt)
                continue

            resp.raise_for_status()
            return resp.json()

        raise RuntimeError(f"Gave up on {url} after {MAX_RETRIES} attempts")

    def get_paginated(self, path: str, max_pages: int = 3, per_page: int = 100) -> list:
        items: list = []
        for page in range(1, max_pages + 1):
            batch = self.get(path, params={"per_page": per_page, "page": page})
            items.extend(batch)
            if len(batch) < per_page:
                break
        return items


def extract_tool(client: GitHubClient, tool: dict) -> dict:
    repo = tool["repo"]
    log.info("Extracting %s (%s)", tool["name"], repo)
    return {
        "tool": tool,
        "repo": client.get(f"/repos/{repo}"),
        "commit_activity": client.get(f"/repos/{repo}/stats/commit_activity") or [],
        "releases": client.get_paginated(f"/repos/{repo}/releases"),
    }


def extract_all(tools: list[dict], client: GitHubClient | None = None) -> list[dict]:
    """Extract every tool; one failing repo is logged and skipped rather than stopping the run."""
    client = client or GitHubClient()
    raw, failures = [], []
    for tool in tools:
        try:
            raw.append(extract_tool(client, tool))
        except Exception as exc:  # noqa: BLE001 - we want to keep going and report at the end
            log.error("Failed to extract %s: %s", tool["repo"], exc)
            failures.append(tool["repo"])
    if failures:
        log.warning("%d tool(s) failed: %s", len(failures), ", ".join(failures))
    return raw
