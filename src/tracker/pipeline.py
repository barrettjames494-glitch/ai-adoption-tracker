"""Run the whole pipeline: extract -> transform -> validate -> metrics -> report.

    python -m tracker.pipeline            # live GitHub data
    python -m tracker.pipeline --offline  # synthetic sample data, no network needed
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from . import extract, metrics, report, sample, transform, validate

log = logging.getLogger("tracker")


def run(config: Path, out_dir: Path, offline: bool = False) -> int:
    out_dir.mkdir(parents=True, exist_ok=True)
    tools = extract.load_tools(config)

    raw = sample.make_raw(tools) if offline else extract.extract_all(tools)
    if not raw:
        log.error("No data extracted; stopping.")
        return 1
    (out_dir / "raw.json").write_text(json.dumps(raw, indent=1), encoding="utf-8")

    tables = transform.build_tables(raw)
    for name, df in tables.items():
        df.to_csv(out_dir / f"{name}.csv", index=False)

    results = validate.run_checks(tables)
    dq = validate.to_frame(results)
    dq.to_csv(out_dir / "data_quality.csv", index=False)
    if validate.has_errors(results):
        log.error("Data quality errors found; see %s. Report not built.", out_dir / "data_quality.csv")
        print(dq[~dq["passed"]].to_string(index=False))
        return 2

    m = metrics.compute(tables)
    m.to_csv(out_dir / "adoption_metrics.csv", index=False)
    insights = metrics.headline_insights(m)

    html = report.build(m, tables, insights, dq, offline=offline)
    report_path = out_dir / "report.html"
    report_path.write_text(html, encoding="utf-8")

    log.info("Done. %d tools, %d checks passed. Report: %s", len(m), int(dq["passed"].sum()), report_path)
    for line in insights:
        log.info("  - %s", line)
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="AI Tool Adoption Tracker")
    p.add_argument("--config", type=Path, default=Path("config/tools.yaml"))
    p.add_argument("--out", type=Path, default=Path("output"))
    p.add_argument("--offline", action="store_true", help="use synthetic sample data instead of the GitHub API")
    p.add_argument("-v", "--verbose", action="store_true")
    args = p.parse_args(argv)

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")
    return run(args.config, args.out, offline=args.offline)


if __name__ == "__main__":
    sys.exit(main())
