"""Build a single self-contained HTML report: headline insights, charts, data quality summary."""

from __future__ import annotations

import html
from datetime import datetime

import pandas as pd
import plotly.express as px
import plotly.io as pio

TEMPLATE = "plotly_white"
ACCENT = "#1f4e79"


def _fig_html(fig, include_js: bool) -> str:
    fig.update_layout(template=TEMPLATE, margin=dict(l=10, r=10, t=50, b=10), font=dict(size=13))
    return pio.to_html(fig, full_html=False, include_plotlyjs="cdn" if include_js else False)


def build(metrics: pd.DataFrame, tables: dict[str, pd.DataFrame], insights: list[str],
          dq: pd.DataFrame, offline: bool) -> str:
    figs = []

    ranked = metrics.sort_values("momentum_score")
    fig = px.bar(ranked, x="momentum_score", y="name", orientation="h", color="category",
                 title="Momentum score (0-100)", labels={"momentum_score": "Score", "name": ""})
    fig.update_yaxes(categoryorder="total ascending")
    figs.append(fig)

    weekly = tables["fact_weekly"].merge(tables["dim_tool"][["tool_id", "name"]], on="tool_id")
    weekly = weekly.sort_values(["tool_id", "week_start"])
    is_last = weekly.groupby("tool_id").cumcount(ascending=False) == 0
    weekly = weekly[~is_last].copy()  # drop each tool's partial current week
    weekly["commits_4w_avg"] = weekly.groupby("tool_id")["commits"].transform(lambda s: s.rolling(4).mean())
    fig = px.line(weekly, x="week_start", y="commits_4w_avg", color="name",
                  title="Weekly commits (4-week rolling average)",
                  labels={"week_start": "", "commits_4w_avg": "Commits / week", "name": ""})
    figs.append(fig)

    fig = px.scatter(metrics, x="stars", y="commit_growth_pct", size="commits_12w", color="category",
                     hover_name="name", log_x=True, title="Adoption vs momentum",
                     labels={"stars": "GitHub stars (log scale)", "commit_growth_pct": "Commit growth %"})
    fig.add_hline(y=0, line_dash="dot", line_color="grey")
    figs.append(fig)

    charts = "\n".join(f'<div class="card">{_fig_html(f, i == 0)}</div>' for i, f in enumerate(figs))

    table_cols = ["rank", "name", "category", "momentum_score", "stars", "commits_12w",
                  "commit_growth_pct", "releases_90d", "median_release_gap", "fork_ratio"]
    labels = {"rank": "Rank", "name": "Tool", "category": "Category", "momentum_score": "Score",
              "stars": "Stars", "commits_12w": "Commits (12w)", "commit_growth_pct": "Growth %",
              "releases_90d": "Releases (90d)", "median_release_gap": "Days between releases",
              "fork_ratio": "Forks per 100 stars"}
    shown = metrics[table_cols].rename(columns=labels)
    for col in ["Stars", "Commits (12w)"]:
        shown[col] = shown[col].map("{:,}".format)
    table = shown.to_html(index=False, classes="tbl", na_rep="–", float_format="{:,.1f}".format)

    failed = dq[~dq["passed"]]
    dq_line = (f"All {len(dq)} data quality checks passed." if failed.empty else
               f"{len(dq) - len(failed)}/{len(dq)} checks passed. Issues: " +
               "; ".join(f"{r.table}.{r.check} ({r.severity}): {r.detail}" for r in failed.itertuples()))

    banner = ('<p class="banner">Offline demo: built from synthetic sample data, not live GitHub figures.</p>'
              if offline else "")
    bullets = "".join(f"<li>{html.escape(s)}</li>" for s in insights)
    stamp = datetime.now().strftime("%d %b %Y %H:%M")

    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>AI Tool Adoption Report</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
 body {{ font-family: -apple-system, Segoe UI, Roboto, sans-serif; margin: 0; background: #f5f7fa; color: #1a1a1a; }}
 header {{ background: {ACCENT}; color: white; padding: 24px 32px; }}
 header h1 {{ margin: 0 0 4px; font-size: 24px; }}
 main {{ max-width: 1100px; margin: 0 auto; padding: 24px; }}
 .card {{ background: white; border-radius: 8px; padding: 16px 20px; margin-bottom: 20px; box-shadow: 0 1px 3px rgba(0,0,0,.08); }}
 .banner {{ background: #fff4e5; border-left: 4px solid #e69500; padding: 10px 14px; margin: 0 0 20px; }}
 .tbl {{ border-collapse: collapse; width: 100%; font-size: 14px; }}
 .tbl th, .tbl td {{ padding: 6px 8px; border-bottom: 1px solid #e5e7eb; text-align: right; }}
 .tbl th:nth-child(2), .tbl td:nth-child(2), .tbl th:nth-child(3), .tbl td:nth-child(3) {{ text-align: left; }}
 .small {{ color: #555; font-size: 13px; }}
</style></head><body>
<header><h1>AI Tool Adoption Report</h1><div>Generated {stamp} · {len(metrics)} tools tracked</div></header>
<main>
{banner}
<div class="card"><h2>Key insights</h2><ul>{bullets}</ul></div>
{charts}
<div class="card"><h2>Scorecard</h2>{table}
<p class="small">Momentum score blends commit growth, recent commit volume, release frequency and fork ratio,
ranked across the tools tracked. See README for the method.</p></div>
<div class="card"><h2>Data quality</h2><p>{html.escape(dq_line)}</p></div>
</main></body></html>"""
