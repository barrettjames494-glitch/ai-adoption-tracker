import pandas as pd

from tracker import metrics


def test_one_row_per_tool_ranked(tables):
    m = metrics.compute(tables)
    assert len(m) == 3
    assert m["rank"].tolist() == sorted(m["rank"].tolist())
    assert m["momentum_score"].between(0, 100).all()


def test_commit_growth_maths():
    # 25 complete weeks of 10 commits then 12 weeks of 20, plus a partial current week that must be ignored.
    weeks = pd.date_range("2026-01-04", periods=38, freq="W-SUN", tz="UTC")
    commits = [10] * 25 + [20] * 12 + [999]
    weekly = pd.DataFrame({"tool_id": "t", "week_start": weeks, "commits": commits})
    act = metrics._activity(weekly)
    assert act.loc[0, "commits_12w"] == 240
    assert act.loc[0, "commit_growth_pct"] == 100.0


def test_zero_prior_activity_gives_no_growth_figure():
    weeks = pd.date_range("2026-01-04", periods=25, freq="W-SUN", tz="UTC")
    weekly = pd.DataFrame({"tool_id": "t", "week_start": weeks, "commits": [0] * 12 + [5] * 13})
    assert pd.isna(metrics._activity(weekly).loc[0, "commit_growth_pct"])


def test_insights_mention_leader(tables):
    m = metrics.compute(tables)
    insights = metrics.headline_insights(m)
    assert m.iloc[0]["name"] in insights[0]
