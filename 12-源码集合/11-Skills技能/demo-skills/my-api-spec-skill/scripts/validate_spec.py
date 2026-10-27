#!/usr/bin/env python3
"""校验 api_pytest spec 的 YAML frontmatter（demo 版，无第三方依赖）。"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REQUIRED_CASE_KEYS = {"id", "method", "path", "expect_status"}


def extract_frontmatter(text: str) -> str:
    if not text.startswith("---"):
        raise ValueError("文件必须以 --- 开头的 YAML frontmatter 开始")
    parts = text.split("---", 2)
    if len(parts) < 3:
        raise ValueError("frontmatter 未正确闭合")
    return parts[1]


def parse_simple_yaml(block: str) -> dict:
    """极简 YAML 解析：仅支持 demo spec 用到的键值结构。"""
    data: dict = {}
    lines = block.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].rstrip()
        if not line.strip() or line.strip().startswith("#"):
            i += 1
            continue
        if line.startswith("kind:"):
            data["kind"] = line.split(":", 1)[1].strip()
        elif line.startswith("base_url:"):
            data["base_url"] = line.split(":", 1)[1].strip()
        elif line.strip() == "cases:":
            cases, i = _parse_cases(lines, i + 1)
            data["cases"] = cases
        i += 1
    return data


def _parse_cases(lines: list[str], start: int) -> tuple[list[dict], int]:
    cases: list[dict] = []
    i = start
    current: dict | None = None
    nested_key: str | None = None
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if stripped.startswith("- id:"):
            if current:
                cases.append(current)
            current = {"id": stripped.split(":", 1)[1].strip()}
            nested_key = None
        elif current is not None and stripped.startswith("method:"):
            current["method"] = stripped.split(":", 1)[1].strip()
        elif current is not None and stripped.startswith("path:"):
            current["path"] = stripped.split(":", 1)[1].strip()
        elif current is not None and stripped.startswith("expect_status:"):
            current["expect_status"] = int(stripped.split(":", 1)[1].strip())
        elif current is not None and stripped == "json_body:":
            nested_key = "json_body"
            current["json_body"] = {}
        elif nested_key and re.match(r"^\s+\w+:", line):
            k, v = line.strip().split(":", 1)
            current.setdefault("json_body", {})[k] = v.strip().strip('"')
        elif stripped and not line.startswith(" ") and not stripped.startswith("-"):
            break
        i += 1
    if current:
        cases.append(current)
    return cases, i


def validate(path: Path) -> list[str]:
    errors: list[str] = []
    text = path.read_text(encoding="utf-8")
    if "def test_" in text:
        errors.append("禁止包含 Python test 函数")
    try:
        fm = parse_simple_yaml(extract_frontmatter(text))
    except ValueError as e:
        return [str(e)]
    if fm.get("kind") != "api_pytest":
        errors.append("kind 必须为 api_pytest")
    if not fm.get("base_url"):
        errors.append("缺少 base_url")
    cases = fm.get("cases") or []
    if not cases:
        errors.append("cases 不能为空")
    for c in cases:
        missing = REQUIRED_CASE_KEYS - set(c.keys())
        if missing:
            errors.append(f"case {c.get('id', '?')} 缺少字段: {missing}")
    return errors


def main() -> int:
    if len(sys.argv) < 2:
        print("用法: validate_spec.py <spec.md>", file=sys.stderr)
        return 2
    path = Path(sys.argv[1])
    errs = validate(path)
    if errs:
        for e in errs:
            print(f"FAIL: {e}")
        return 1
    print(f"OK: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
