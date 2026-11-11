"""Data quality checks run on every table before metrics are calculated.

Each check returns a Result. "error" results stop the pipeline; "warning" results are reported
but let the run continue. The full list is written to output/data_quality.csv for lineage/audit.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

import pandas as pd

REQUIRED_COLUMNS = {
    "dim_tool": ["tool_id", "name", "category", "repo"],
    "fact_snapshot": ["tool_id", "snapshot_at", "stars", "forks", "open_issues", "last_push_at"],
    "fact_weekly": ["tool_id", "week_start", "commits"],
    "fact_releases": ["tool_id", "tag", "published_at"],
}
NON_NEGATIVE = {
    "fact_snapshot": ["stars", "forks", "open_issues"],
    "fact_weekly": ["commits"],
}
STALE_AFTER_DAYS = 30


@dataclass
class Result:
    table: str
    check: str
    severity: str  # "error" or "warning"
    passed: bool
    detail: str = ""


def run_checks(tables: dict[str, pd.DataFrame]) -> list[Result]:
    results: list[Result] = []

    for name, cols in REQUIRED_COLUMNS.items():
        df = tables.get(name)
        if df is None:
            results.append(Result(name, "table_present", "error", False, "table missing"))
            continue
        missing = [c for c in cols if c not in df.columns]
        results.append(Result(name, "required_columns", "error", not missing,
                              f"missing: {missing}" if missing else ""))
        if missing:
            continue
        nulls = {c: int(df[c].isna().sum()) for c in cols if df[c].isna().any()}
        results.append(Result(name, "no_nulls_in_required", "error", not nulls,
                              f"nulls: {nulls}" if nulls else ""))

    for name, cols in NON_NEGATIVE.items():
        df = tables.get(name)
        if df is None:
            continue
        bad = {c: int((df[c] < 0).sum()) for c in cols if c in df and (df[c] < 0).any()}
        results.append(Result(name, "non_negative", "error", not bad, f"negatives: {bad}" if bad else ""))

    dim = tables.get("dim_tool")
    if dim is not None and "tool_id" in dim:
        dupes = int(dim["tool_id"].duplicated().sum())
        results.append(Result("dim_tool", "unique_tool_id", "error", dupes == 0,
                              f"{dupes} duplicate(s)" if dupes else ""))

        # Referential integrity: every fact row must point at a known tool.
        known = set(dim["tool_id"])
        for fact in ("fact_snapshot", "fact_weekly", "fact_releases"):
            df = tables.get(fact)
            if df is None or "tool_id" not in df:
                continue
            orphans = sorted(set(df["tool_id"]) - known)
            results.append(Result(fact, "tool_id_in_dim", "error", not orphans,
                                  f"unknown: {orphans}" if orphans else ""))

    weekly = tables.get("fact_weekly")
    if weekly is not None and dim is not None and {"tool_id", "week_start"} <= set(weekly.columns):
        dupes = int(weekly.duplicated(["tool_id", "week_start"]).sum())
        results.append(Result("fact_weekly", "unique_tool_week", "error", dupes == 0,
                              f"{dupes} duplicate(s)" if dupes else ""))
        no_activity = sorted(set(dim["tool_id"]) - set(weekly["tool_id"]))
        results.append(Result("fact_weekly", "activity_for_every_tool", "warning", not no_activity,
                              f"no weekly data: {no_activity}" if no_activity else ""))

    snap = tables.get("fact_snapshot")
    if snap is not None and {"snapshot_at", "last_push_at"} <= set(snap.columns):
        age = (snap["snapshot_at"] - snap["last_push_at"]).dt.days
        stale = snap.loc[age > STALE_AFTER_DAYS, "tool_id"].tolist()
        results.append(Result("fact_snapshot", f"pushed_within_{STALE_AFTER_DAYS}_days", "warning",
                              not stale, f"stale: {stale}" if stale else ""))

    return results


def to_frame(results: list[Result]) -> pd.DataFrame:
    return pd.DataFrame([asdict(r) for r in results])


def has_errors(results: list[Result]) -> bool:
    return any(r.severity == "error" and not r.passed for r in results)
