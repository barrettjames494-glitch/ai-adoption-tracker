"""Adoption metrics, one row per tool.

    commits_12w          commits in the latest 12 complete weeks
    commit_growth_pct    change vs the 12 weeks before that (momentum)
    releases_90d         releases published in the last 90 days
    median_release_gap   median days between releases (delivery cadence)
    fork_ratio           forks per 100 stars (how often people build on it, not just bookmark it)
    issues_per_1k_stars  open issues per 1,000 stars (support load relative to adoption)
    momentum_score       0-100 composite, ranked across the tools tracked
"""

from __future__ import annotations

import pandas as pd

WINDOW_WEEKS = 12

# Weights for the composite score. They are a judgement call: tune them and say so in the README.
SCORE_WEIGHTS = {
    "commit_growth_pct": 0.35,
    "commits_12w": 0.25,
    "releases_90d": 0.20,
    "fork_ratio": 0.20,
}


def _activity(weekly: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for tid, grp in weekly.groupby("tool_id"):
        # GitHub includes the current, partial week as the last row; drop it.
        commits = grp.sort_values("week_start")["commits"].iloc[:-1]
        recent = commits.iloc[-WINDOW_WEEKS:].sum()
        prior = commits.iloc[-2 * WINDOW_WEEKS:-WINDOW_WEEKS].sum()
        growth = (recent - prior) / prior * 100 if prior else None
        rows.append({"tool_id": tid, "commits_12w": int(recent), "commit_growth_pct": growth})
    return pd.DataFrame(rows, columns=["tool_id", "commits_12w", "commit_growth_pct"])


def _releases(releases: pd.DataFrame, as_of: pd.Timestamp) -> pd.DataFrame:
    rows = []
    for tid, grp in releases.groupby("tool_id"):
        dates = grp["published_at"].sort_values()
        gaps = dates.diff().dt.days.dropna()
        rows.append({
            "tool_id": tid,
            "releases_90d": int((dates >= as_of - pd.Timedelta(days=90)).sum()),
            "median_release_gap": float(gaps.median()) if len(gaps) else None,
            "last_release_at": dates.iloc[-1],
        })
    return pd.DataFrame(rows, columns=["tool_id", "releases_90d", "median_release_gap", "last_release_at"])


def _percentile_rank(s: pd.Series) -> pd.Series:
    return s.rank(pct=True, method="average").fillna(0)


def compute(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    dim, snap = tables["dim_tool"], tables["fact_snapshot"]
    as_of = snap["snapshot_at"].max()

    df = (
        dim[["tool_id", "name", "category"]]
        .merge(snap[["tool_id", "stars", "forks", "open_issues"]], on="tool_id", how="left")
        .merge(_activity(tables["fact_weekly"]), on="tool_id", how="left")
        .merge(_releases(tables["fact_releases"], as_of), on="tool_id", how="left")
    )
    df["releases_90d"] = df["releases_90d"].fillna(0).astype(int)
    df["fork_ratio"] = (df["forks"] / df["stars"] * 100).round(1)
    df["issues_per_1k_stars"] = (df["open_issues"] / df["stars"] * 1000).round(1)

    score = sum(_percentile_rank(df[col]) * w for col, w in SCORE_WEIGHTS.items())
    df["momentum_score"] = (score / sum(SCORE_WEIGHTS.values()) * 100).round(0).astype(int)
    df["rank"] = df["momentum_score"].rank(ascending=False, method="min").astype(int)
    df["commit_growth_pct"] = df["commit_growth_pct"].round(1)

    return df.sort_values("rank").reset_index(drop=True)


def headline_insights(m: pd.DataFrame, top_n: int = 3) -> list[str]:
    """Plain-English findings for the top of the report."""
    out = []
    leaders = m.head(top_n)["name"].tolist()
    out.append(f"Highest momentum: {', '.join(leaders)}.")

    growth = m.dropna(subset=["commit_growth_pct"]).sort_values("commit_growth_pct")
    if not growth.empty:
        fast, slow = growth.iloc[-1], growth.iloc[0]
        out.append(
            f"Fastest-growing development activity: {fast['name']} "
            f"({fast['commit_growth_pct']:+.0f}% commits, last 12 weeks vs prior 12)."
        )
        if slow["commit_growth_pct"] < 0:
            out.append(f"Slowing: {slow['name']} ({slow['commit_growth_pct']:+.0f}%), worth watching before committing to it.")

    cat = m.groupby("category")["momentum_score"].mean().sort_values(ascending=False)
    out.append(f"Strongest category on average: {cat.index[0]} (score {cat.iloc[0]:.0f}).")

    load = m.sort_values("issues_per_1k_stars", ascending=False).iloc[0]
    out.append(f"Heaviest open-issue load relative to adoption: {load['name']} ({load['issues_per_1k_stars']:.0f} per 1k stars).")
    return out
