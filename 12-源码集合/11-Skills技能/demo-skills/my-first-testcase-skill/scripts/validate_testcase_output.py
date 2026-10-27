#!/usr/bin/env python3
"""校验冒烟测试点输出结构（demo 版）。"""
import re
import sys
from pathlib import Path

REQUIRED_SECTIONS = ["## 文档信息", "## 测试点", "## 待澄清清单"]
SM_PATTERN = re.compile(r"^### SM-\d{3}\s", re.M)


def validate(path: Path) -> list[str]:
    errors: list[str] = []
    text = path.read_text(encoding="utf-8")
    for sec in REQUIRED_SECTIONS:
        if sec not in text:
            errors.append(f"缺少章节: {sec}")
    sm_heads = SM_PATTERN.findall(text)
    if len(sm_heads) < 3:
        errors.append(f"测试点过少: 找到 {len(sm_heads)} 条 SM-xxx")
    if "def test_" in text or "import pytest" in text:
        errors.append("不应包含 Python 测试代码")
    if "系统正常" in text or "体验良好" in text:
        errors.append("含不可判定描述（系统正常/体验良好）")
    return errors


def main() -> int:
    if len(sys.argv) < 2:
        print("用法: validate_testcase_output.py <smoke_testcases.md>", file=sys.stderr)
        return 2
    path = Path(sys.argv[1])
    errs = validate(path)
    if errs:
        for e in errs:
            print(f"FAIL: {e}")
        return 1
    print(f"OK: {path} ({len(SM_PATTERN.findall(path.read_text()))} test points)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
