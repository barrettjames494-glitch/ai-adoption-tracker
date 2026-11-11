"""Turn raw API records into tidy tables (a small star schema).

    dim_tool         one row per tool              (tool_id, name, category, repo, language, licence, created_at)
    fact_snapshot    one row per tool per run      (stars, forks, watchers, open issues, last push)
    fact_weekly      one row per tool per week     (commits)
    fact_releases    one row per release           (tag, published_at, prerelease)

The same tables load straight into Power BI or Tableau.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd


def _tool_id(repo: str) -> str:
    return repo.lower().replace("/", "__")


def build_tables(raw: list[dict], snapshot_at: datetime | None = None) -> dict[str, pd.DataFrame]:
    snapshot_at = snapshot_at or datetime.now(timezone.utc)
    dims, snaps, weekly, releases = [], [], [], []

    for rec in raw:
        tool, repo = rec["tool"], rec["repo"]
        tid = _tool_id(tool["repo"])

        dims.append({
            "tool_id": tid,
            "name": tool["name"],
            "category": tool["category"],
            "repo": tool["repo"],
            "language": repo.get("language"),
            "licence": (repo.get("license") or {}).get("spdx_id"),
            "created_at": repo.get("created_at"),
        })
        snaps.append({
            "tool_id": tid,
            "snapshot_at": snapshot_at,
            "stars": repo.get("stargazers_count"),
            "forks": repo.get("forks_count"),
            "watchers": repo.get("subscribers_count"),
            "open_issues": repo.get("open_issues_count"),
            "last_push_at": repo.get("pushed_at"),
            "archived": repo.get("archived", False),
        })
        for wk in rec.get("commit_activity") or []:
            weekly.append({"tool_id": tid, "week_start": wk["week"], "commits": wk["total"]})
        for rel in rec.get("releases") or []:
            if rel.get("draft"):
                continue
            releases.append({
                "tool_id": tid,
                "tag": rel.get("tag_name"),
                "published_at": rel.get("published_at"),
                "prerelease": bool(rel.get("prerelease")),
            })

    dim_tool = pd.DataFrame(dims)
    dim_tool["created_at"] = pd.to_datetime(dim_tool["created_at"], utc=True)

    fact_snapshot = pd.DataFrame(snaps)
    fact_snapshot["snapshot_at"] = pd.to_datetime(fact_snapshot["snapshot_at"], utc=True)
    fact_snapshot["last_push_at"] = pd.to_datetime(fact_snapshot["last_push_at"], utc=True)

    fact_weekly = pd.DataFrame(weekly, columns=["tool_id", "week_start", "commits"])
    fact_weekly["week_start"] = pd.to_datetime(fact_weekly["week_start"], unit="s", utc=True)
    fact_weekly = fact_weekly.sort_values(["tool_id", "week_start"]).reset_index(drop=True)

    fact_releases = pd.DataFrame(releases, columns=["tool_id", "tag", "published_at", "prerelease"])
    fact_releases["published_at"] = pd.to_datetime(fact_releases["published_at"], utc=True)
    fact_releases = fact_releases.sort_values(["tool_id", "published_at"]).reset_index(drop=True)

    return {
        "dim_tool": dim_tool,
        "fact_snapshot": fact_snapshot,
        "fact_weekly": fact_weekly,
        "fact_releases": fact_releases,
    }
