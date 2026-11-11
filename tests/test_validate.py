from tracker import validate


def test_clean_data_passes(tables):
    results = validate.run_checks(tables)
    assert not validate.has_errors(results)


def test_negative_commits_fail(tables):
    tables["fact_weekly"].loc[0, "commits"] = -5
    results = validate.run_checks(tables)
    failed = [r.check for r in results if not r.passed]
    assert "non_negative" in failed
    assert validate.has_errors(results)


def test_orphan_fact_rows_fail(tables):
    tables["fact_releases"].loc[0, "tool_id"] = "org__unknown"
    failed = [r.check for r in validate.run_checks(tables) if not r.passed]
    assert "tool_id_in_dim" in failed


def test_duplicate_tool_fails(tables):
    import pandas as pd

    tables["dim_tool"] = pd.concat([tables["dim_tool"], tables["dim_tool"].iloc[[0]]])
    failed = [r.check for r in validate.run_checks(tables) if not r.passed]
    assert "unique_tool_id" in failed


def test_stale_repo_is_only_a_warning(tables):
    import pandas as pd

    tables["fact_snapshot"].loc[0, "last_push_at"] = pd.Timestamp("2025-01-01", tz="UTC")
    results = validate.run_checks(tables)
    stale = [r for r in results if r.check.startswith("pushed_within")][0]
    assert not stale.passed and stale.severity == "warning"
    assert not validate.has_errors(results)
