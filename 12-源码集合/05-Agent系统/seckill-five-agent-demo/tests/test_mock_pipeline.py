"""Mock 流水线测试"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.mock_pipeline import run_mock_pipeline, REPORT_FILES


def test_mock_pipeline_generates_five_reports(tmp_path):
    req = Path(__file__).parent.parent / "samples" / "seckill_requirements.md"
    result = run_mock_pipeline(tmp_path / "reports", req)
    assert result["mode"] == "demo"
    assert len(result["stages"]) == 5
    for name in REPORT_FILES:
        assert (tmp_path / "reports" / name).is_file()
        assert (tmp_path / "reports" / name).stat().st_size > 50
