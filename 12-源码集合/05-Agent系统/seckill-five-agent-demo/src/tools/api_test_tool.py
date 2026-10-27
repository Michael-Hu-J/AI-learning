"""秒杀 API 测试 Tool（Crew 模式使用）"""

from crewai.tools import BaseTool


class SeckillAPITestTool(BaseTool):
    name: str = "seckill_api_test"
    description: str = (
        "模拟秒杀 API 测试。参数 action: check_stock|place_order|query_product，"
        "返回结构化测试结果（通过/失败/耗时）。"
    )

    def _run(self, action: str = "check_stock") -> str:
        cases = {
            "check_stock": ("GET /api/seckill/stock/SK001", "PASS", "库存=100，无超卖"),
            "place_order": ("POST /api/seckill/order", "PASS", "订单创建成功 ORD-001"),
            "query_product": ("GET /api/seckill/products/SK001", "PASS", "商品信息完整"),
        }
        key = action if action in cases else "check_stock"
        method, status, detail = cases[key]
        return f"[{status}] {method} | {detail} | latency=42ms"
