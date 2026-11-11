"""Generate synthetic raw data shaped exactly like the GitHub API responses.

Used by `--offline` mode and the tests, so the pipeline can run without network access.
The numbers are made up (seeded, so they are repeatable) and must not be presented as real.
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone


def _weeks(now: datetime, n: int = 52) -> list[datetime]:
    # GitHub's commit_activity weeks start on Sunday, oldest first.
    last_sunday = (now - timedelta(days=(now.weekday() + 1) % 7)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    return [last_sunday - timedelta(weeks=n - 1 - i) for i in range(n)]


def make_raw(tools: list[dict], seed: int = 42, now: datetime | None = None) -> list[dict]:
    rng = random.Random(seed)
    now = now or datetime.now(timezone.utc)
    raw = []
    for tool in tools:
        base = rng.randint(40, 400)            # typical weekly commits
        trend = rng.uniform(-0.4, 0.6)         # growth over the year
        stars = rng.randint(8_000, 150_000)

        activity = []
        for i, wk in enumerate(_weeks(now)):
            level = base * (1 + trend * i / 51)
            total = max(0, int(rng.gauss(level, level * 0.15)))
            split = [rng.random() for _ in range(7)]
            days = [int(total * s / sum(split)) for s in split]
            activity.append({"week": int(wk.timestamp()), "total": sum(days), "days": days})

        releases, d = [], now - timedelta(days=rng.randint(1, 20))
        cadence = rng.randint(5, 45)
        for n in range(rng.randint(6, 25)):
            releases.append({
                "tag_name": f"v0.{25 - n}.0",
                "published_at": d.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "draft": False,
                "prerelease": rng.random() < 0.15,
            })
            d -= timedelta(days=max(1, int(rng.gauss(cadence, cadence * 0.3))))

        raw.append({
            "tool": tool,
            "repo": {
                "full_name": tool["repo"],
                "stargazers_count": stars,
                "forks_count": int(stars * rng.uniform(0.08, 0.25)),
                "subscribers_count": int(stars * rng.uniform(0.005, 0.02)),
                "open_issues_count": rng.randint(50, 2_500),
                "language": "Python" if "cpp" not in tool["repo"] else "C++",
                "license": {"spdx_id": rng.choice(["MIT", "Apache-2.0"])},
                "created_at": (now - timedelta(days=rng.randint(400, 2_500))).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "pushed_at": (now - timedelta(hours=rng.randint(1, 72))).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "archived": False,
            },
            "commit_activity": activity,
            "releases": releases,
        })
    return raw
