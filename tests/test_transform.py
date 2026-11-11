def test_one_dim_row_per_tool(tables):
    assert len(tables["dim_tool"]) == 3
    assert tables["dim_tool"]["tool_id"].tolist() == ["org__alpha", "org__beta", "org__gamma"]


def test_weekly_has_52_weeks_per_tool(tables):
    counts = tables["fact_weekly"].groupby("tool_id").size()
    assert (counts == 52).all()


def test_draft_releases_are_dropped(raw):
    from tracker import transform

    raw[0]["releases"].append({"tag_name": "draft", "published_at": None, "draft": True, "prerelease": False})
    tables = transform.build_tables(raw)
    assert "draft" not in tables["fact_releases"]["tag"].tolist()


def test_dates_are_timezone_aware(tables):
    assert str(tables["fact_weekly"]["week_start"].dt.tz) == "UTC"
    assert str(tables["fact_releases"]["published_at"].dt.tz) == "UTC"
