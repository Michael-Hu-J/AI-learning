"""数据分析器"""

import json
import logging
from typing import List, Dict, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class AnalysisResult:
    """分析结果"""
    question: str
    sql: str
    data: List[Dict]
    summary: str = ""
    chart_type: str = ""  # bar, line, pie, table
    chart_data: Optional[Dict] = None
    anomalies: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "question": self.question,
            "sql": self.sql,
            "data": self.data,
            "summary": self.summary,
            "chart_type": self.chart_type,
            "chart_data": self.chart_data,
            "anomalies": self.anomalies,
        }


class DataAnalyzer:
    """数据分析器"""

    def analyze(self, question: str, sql: str, data: List[Dict]) -> AnalysisResult:
        """分析查询结果"""
        result = AnalysisResult(question=question, sql=sql, data=data)

        # 1. 生成摘要
        result.summary = self._generate_summary(data)

        # 2. 推荐图表类型
        result.chart_type = self._recommend_chart_type(data)

        # 3. 提取图表数据
        if result.chart_type:
            result.chart_data = self._extract_chart_data(data, result.chart_type)

        # 4. 异常检测
        result.anomalies = self._detect_anomalies(data)

        return result

    @staticmethod
    def _generate_summary(data: List[Dict]) -> str:
        """生成数据摘要"""
        if not data:
            return "查询结果为空。"

        count = len(data)
        columns = list(data[0].keys()) if data else []

        parts = [f"共返回 {count} 条记录。"]

        for col in columns:
            values = [row.get(col) for row in data if isinstance(row.get(col), (int, float))]
            if values:
                parts.append(
                    f"{col}: 最小值={min(values)}, 最大值={max(values)}, 平均值={sum(values)/len(values):.1f}"
                )

        return " ".join(parts)

    @staticmethod
    def _recommend_chart_type(data: List[Dict]) -> str:
        """根据数据特征推荐图表类型"""
        if not data:
            return "table"

        columns = list(data[0].keys())
        numeric_cols = []
        text_cols = []

        for col in columns:
            if isinstance(data[0].get(col), (int, float)):
                numeric_cols.append(col)
            else:
                text_cols.append(col)

        # 有分类字段 + 数值字段 --> 柱状图
        if text_cols and numeric_cols:
            return "bar"

        # 只有数值 --> 表格
        return "table"

    @staticmethod
    def _extract_chart_data(data: List[Dict], chart_type: str) -> Dict:
        """提取图表数据"""
        if not data:
            return {}

        columns = list(data[0].keys())
        text_col = next((c for c in columns if not isinstance(data[0].get(c), (int, float))), columns[0])
        num_col = next((c for c in columns if isinstance(data[0].get(c), (int, float))), columns[-1])

        return {
            "type": chart_type,
            "labels": [str(row.get(text_col, "")) for row in data],
            "values": [row.get(num_col, 0) for row in data],
            "title": f"{num_col} 分析",
        }

    @staticmethod
    def _detect_anomalies(data: List[Dict]) -> List[str]:
        """检测数据异常"""
        anomalies = []

        if not data:
            anomalies.append("查询结果为空，请确认查询条件是否正确")
            return anomalies

        columns = list(data[0].keys())

        for col in columns:
            values = [row.get(col) for row in data if isinstance(row.get(col), (int, float))]
            if not values:
                continue

            avg = sum(values) / len(values)
            # 检测异常值（超过平均值 3 倍标准差）
            if len(values) > 1:
                std = (sum((v - avg) ** 2 for v in values) / len(values)) ** 0.5
                if std > 0:
                    for v in values:
                        if abs(v - avg) > 3 * std:
                            anomalies.append(f"{col} 中存在异常值: {v}")

        return anomalies


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    analyzer = DataAnalyzer()
    sample_data = [
        {"name": "商品A", "sales": 120000},
        {"name": "商品B", "sales": 95000},
        {"name": "商品C", "sales": 110000},
    ]
    result = analyzer.analyze("销售额最高的商品", "SELECT ...", sample_data)
    print(f"摘要: {result.summary}")
    print(f"图表类型: {result.chart_type}")
    print(f"图表数据: {result.chart_data}")
    print(f"异常: {result.anomalies}")
