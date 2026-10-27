#!/usr/bin/env bash
# 校验 demo-skills 全部示例产出（无 LLM，可进 CI）
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

python3 "$ROOT/my-first-testcase-skill/scripts/validate_testcase_output.py" \
  "$ROOT/my-first-testcase-skill/output/smoke_testcases.md"

python3 "$ROOT/my-api-spec-skill/scripts/validate_spec.py" \
  "$ROOT/my-api-spec-skill/output/login_api_smoke.md"

echo "[validate_all_skills.sh] ALL OK"
