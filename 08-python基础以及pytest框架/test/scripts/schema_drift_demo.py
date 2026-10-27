#!/usr/bin/env python3
"""
第 22 节附录 A — OpenAPI 契约漂移检测（教学简化版）

对比两版 OpenAPI，输出路径/方法/必填字段层面的变更。
完整版（含响应体字段、报告导出）见「AI 测试专业版 Skill」中的 api_schema_drift_detector.py。

用法:
  cd test
  python scripts/schema_drift_demo.py examples/openapi_mini_v1.json examples/openapi_mini_v2.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

HTTP_METHODS = {"get", "post", "put", "delete", "patch"}


def load_spec(path: Path) -> Dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if path.suffix in {".yaml", ".yml"}:
        import yaml

        return yaml.safe_load(text)
    return json.loads(text)


def required_body_fields(operation: Dict[str, Any]) -> Set[str]:
    body = operation.get("requestBody") or {}
    content = body.get("content") or {}
    for media in content.values():
        schema = media.get("schema") or {}
        return set(schema.get("required") or [])
    return set()


def compare_specs(old: Dict[str, Any], new: Dict[str, Any]) -> List[str]:
    lines: List[str] = []
    old_paths = old.get("paths") or {}
    new_paths = new.get("paths") or {}

    for path in sorted(set(old_paths) - set(new_paths)):
        lines.append(f"[BREAKING] 删除路径: {path}")

    for path in sorted(set(new_paths) - set(old_paths)):
        lines.append(f"[COMPAT] 新增路径: {path}")

    for path in sorted(set(old_paths) & set(new_paths)):
        old_ops = old_paths[path]
        new_ops = new_paths[path]
        old_methods = {m.lower() for m in old_ops if m.lower() in HTTP_METHODS}
        new_methods = {m.lower() for m in new_ops if m.lower() in HTTP_METHODS}

        for method in sorted(old_methods - new_methods):
            lines.append(f"[BREAKING] {path} 删除方法: {method.upper()}")

        for method in sorted(new_methods - old_methods):
            lines.append(f"[COMPAT] {path} 新增方法: {method.upper()}")

        for method in sorted(old_methods & new_methods):
            old_req = required_body_fields(old_ops[method])
            new_req = required_body_fields(new_ops[method])
            added = new_req - old_req
            removed = old_req - new_req
            if added:
                lines.append(
                    f"[BREAKING] {path} {method.upper()} 新增必填字段: {sorted(added)}"
                )
            if removed:
                lines.append(
                    f"[COMPAT] {path} {method.upper()} 移除必填: {sorted(removed)}"
                )

    return lines


def main(argv: List[str]) -> int:
    if len(argv) != 3:
        print(__doc__)
        return 1

    old_path = Path(argv[1])
    new_path = Path(argv[2])
    changes = compare_specs(load_spec(old_path), load_spec(new_path))

    print(f"对比: {old_path.name} → {new_path.name}")
    print("-" * 50)
    if not changes:
        print("未检测到路径/方法/必填字段层面的差异。")
        return 0

    for line in changes:
        print(line)

    breaking = sum(1 for c in changes if c.startswith("[BREAKING]"))
    print("-" * 50)
    print(f"共 {len(changes)} 项变更，其中破坏性 {breaking} 项。")
    print("CI 建议: 存在 BREAKING 时触发接口测试回归或通知开发。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
