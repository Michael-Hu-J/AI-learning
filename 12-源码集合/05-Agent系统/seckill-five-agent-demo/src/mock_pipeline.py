"""Mock 五 Agent 流水线：无需 API Key，演示完整测试流程"""

import time
from pathlib import Path
from typing import Dict, List


REPORT_FILES = [
    "01_test_plan.md",
    "02_test_cases.md",
    "03_test_results.md",
    "04_analysis_report.md",
    "05_final_report.md",
]


def _write(reports_dir: Path, name: str, content: str) -> None:
    path = reports_dir / name
    path.write_text(content.strip() + "\n", encoding="utf-8")


def run_mock_pipeline(reports_dir: Path, requirements_path: Path) -> Dict:
    """顺序模拟 Manager → Designer → Engineer → Analyst → Reporter"""
    reports_dir.mkdir(parents=True, exist_ok=True)
    req_excerpt = requirements_path.read_text(encoding="utf-8")[:200].replace("\n", " ")

    stages: List[Dict] = []

    print("\n[1/5] 测试经理 Agent — 制定测试计划")
    time.sleep(0.3)
    plan = f"""# 秒杀系统测试计划

> 输入摘要：{req_excerpt}...

## 测试范围

| 模块 | 优先级 | 说明 |
|------|--------|------|
| 库存扣减 | P0 | 防超卖 |
| 下单接口 | P0 | 幂等与重复提交 |
| 商品查询 | P1 | 数据一致性 |
| 限流降级 | P1 | 高并发保护 |

## 资源评估

- 人力：2 人 × 3 天
- 环境：测试环境 + Mock 并发
"""
    _write(reports_dir, REPORT_FILES[0], plan)
    stages.append({"agent": "Manager", "output": REPORT_FILES[0]})
    print("  ✅ 已生成 reports/01_test_plan.md")

    print("\n[2/5] 测试设计师 Agent — 设计测试用例")
    time.sleep(0.3)
    cases = """# 秒杀测试用例（节选）

| ID | 模块 | 优先级 | 场景 | 预期 |
|----|------|--------|------|------|
| TC-001 | 库存 | P0 | 100 并发抢 100 件 | 库存归零，无超卖 |
| TC-002 | 订单 | P0 | 同一用户重复下单 | 第二次拒绝 |
| TC-003 | 订单 | P0 | 库存为 0 时下单 | 返回售罄 |
| TC-004 | 接口 | P1 | 响应时间 | P99 < 500ms |
| TC-005 | 安全 | P2 | 未登录下单 | 401 |
"""
    _write(reports_dir, REPORT_FILES[1], cases)
    stages.append({"agent": "Designer", "output": REPORT_FILES[1]})
    print("  ✅ 已生成 reports/02_test_cases.md")

    print("\n[3/5] 测试工程师 Agent — 执行 API 测试")
    time.sleep(0.3)
    results = """# 测试执行结果

| 用例 ID | 结果 | 说明 |
|---------|------|------|
| TC-001 | PASS | 库存扣减正确 |
| TC-002 | PASS | 重复订单被拦截 |
| TC-003 | PASS | 售罄提示正确 |
| TC-004 | FAIL | P99=620ms，超出 500ms 阈值 |
| TC-005 | PASS | 未登录返回 401 |

**通过率：4/5（80%）**
"""
    _write(reports_dir, REPORT_FILES[2], results)
    stages.append({"agent": "Engineer", "output": REPORT_FILES[2]})
    print("  ✅ 已生成 reports/03_test_results.md")

    print("\n[4/5] 测试分析师 Agent — 根因分析")
    time.sleep(0.3)
    analysis = """# 缺陷分析报告

## 问题：TC-004 性能未达标

**5 Why 分析：**
1. 为什么 P99 超时？→ 下单链路慢
2. 为什么慢？→ 库存扣减串行锁竞争
3. 为什么锁竞争？→ 单 Redis 节点热点 key
4. 为什么热点？→ 未按商品分片
5. 根因？→ 架构未针对秒杀做分片设计

**建议：** 库存分片 + 本地缓存预热；压测回归 TC-004。
"""
    _write(reports_dir, REPORT_FILES[3], analysis)
    stages.append({"agent": "Analyst", "output": REPORT_FILES[3]})
    print("  ✅ 已生成 reports/04_analysis_report.md")

    print("\n[5/5] 测试报告专员 Agent — 输出发布建议")
    time.sleep(0.3)
    final = """# 秒杀系统测试总结报告

## 结论

| 指标 | 数值 |
|------|------|
| 用例总数 | 5 |
| 通过 | 4 |
| 失败 | 1 |
| 通过率 | 80% |

## 发布建议

**有条件发布** — 核心功能（库存/幂等/鉴权）已通过；需修复 TC-004 性能后全量上线。

## 产出物

- 01_test_plan.md
- 02_test_cases.md
- 03_test_results.md
- 04_analysis_report.md
- 05_final_report.md（本文件）
"""
    _write(reports_dir, REPORT_FILES[4], final)
    stages.append({"agent": "Reporter", "output": REPORT_FILES[4]})
    print("  ✅ 已生成 reports/05_final_report.md")

    return {"mode": "demo", "stages": stages, "reports_dir": str(reports_dir)}
