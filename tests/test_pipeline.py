from pathlib import Path

from tracker import pipeline

CONFIG = Path(__file__).resolve().parents[1] / "config" / "tools.yaml"


def test_offline_run_writes_outputs(tmp_path):
    assert pipeline.run(CONFIG, tmp_path, offline=True) == 0
    for name in ["report.html", "adoption_metrics.csv", "data_quality.csv", "fact_weekly.csv"]:
        assert (tmp_path / name).exists(), name
    assert "synthetic sample data" in (tmp_path / "report.html").read_text()
