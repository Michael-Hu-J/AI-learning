"""
第 5 篇附录 — 像素级截图回归（教学 demo）

与「视觉语义定位」（keywords/OpenCV）不同：此处对比整页 PNG 基线。

首次生成基线:
  cd 配套代码 && pytest tests/test_snapshot_demo.py --update-snapshots -v

后续回归:
  pytest tests/test_snapshot_demo.py -v

完整 visual_regression spec 见专业版 Skill templates/visual_regression.md
"""
import os
import hashlib
from pathlib import Path
from playwright.sync_api import Page


def _snapshot_path(name: str) -> str:
    return str(Path(__file__).parent / "snapshots" / name)


def _file_hash(path: str) -> str:
    return hashlib.md5(Path(path).read_bytes()).hexdigest()


def test_login_page_snapshot(page: Page, demo_app):
    page.set_viewport_size({"width": 1280, "height": 720})
    page.goto("http://127.0.0.1:5000/login")
    page.wait_for_selector("#username")

    baseline = _snapshot_path("login_page.png")
    current = _snapshot_path("login_page_current.png")

    page.screenshot(path=current, full_page=True)

    if os.path.exists(baseline):
        # 回归对比：基线已存在，比较哈希
        assert _file_hash(baseline) == _file_hash(current), (
            f"截图与基线不一致（基线: {baseline}）\n"
            f"如需更新基线：删除 {baseline} 后重新运行"
        )
        # 对比通过后删除当前截图
        os.remove(current)
    else:
        # 首次运行：保存为基线
        os.rename(current, baseline)
        print(f"\n  基线已生成: {baseline}")
