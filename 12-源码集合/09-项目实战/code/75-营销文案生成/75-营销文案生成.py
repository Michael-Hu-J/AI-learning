import re
import json
import random
import time
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field


@dataclass
class ProductInfo:
    """产品信息"""
    name: str
    category: str
    selling_points: List[str]
    price: str
    target_audience: str
    platform: str  # 发布平台：朋友圈/微博/抖音/电商


@dataclass
class CopyVersion:
    """文案版本"""
    content: str
    style: str
    version_id: str
    compliance_passed: bool = True
    quality_score: float = 0.0
    compliance_issues: List[str] = field(default_factory=list)
    metrics: Optional[Dict] = None


class CopyGenerator:
    """文案生成引擎"""

    STYLE_TEMPLATES = {
        "正式": "请以正式、专业的口吻撰写，适合企业官方渠道发布。",
        "幽默": "请以轻松幽默的口吻撰写，使用网络流行语和俏皮话。",
        "情感": "请以情感共鸣的方式撰写，触动用户内心需求。",
        "促销": "请以紧迫感推动的方式撰写，强调限时优惠和稀缺性。",
        "科普": "请以知识科普的方式撰写，先讲道理再推产品。",
    }

    PLATFORM_FORMATS = {
        "朋友圈": "字数控制在 100 字以内，适合配图发布。",
        "微博": "字数控制在 200 字以内，可以带话题标签。",
        "抖音": "口语化表达，适合口播，控制在 150 字以内。",
        "电商": "详细的产品描述，突出卖点，控制在 300 字以内。",
    }

    def __init__(self, llm_call_func):
        self.llm = llm_call_func

    def generate(self, product: ProductInfo, style: str, count: int = 3) -> List[CopyVersion]:
        """生成多个版本的文案"""
        if style not in self.STYLE_TEMPLATES:
            raise ValueError(f"不支持的风格：{style}，可选：{list(self.STYLE_TEMPLATES.keys())}")

        style_instruction = self.STYLE_TEMPLATES[style]
        platform_instruction = self.PLATFORM_FORMATS.get(product.platform, "")

        selling_points_text = "\n".join([f"- {sp}" for sp in product.selling_points])

        prompt = (
            f"你是一名资深营销文案撰稿人，擅长为不同平台撰写高转化率的营销文案。\n\n"
            f"产品信息：\n"
            f"- 产品名称：{product.name}\n"
            f"- 产品类别：{product.category}\n"
            f"- 核心卖点：\n{selling_points_text}\n"
            f"- 价格：{product.price}\n"
            f"- 目标受众：{product.target_audience}\n"
            f"- 发布平台：{product.platform}\n\n"
            f"风格要求：{style_instruction}\n"
            f"平台要求：{platform_instruction}\n\n"
            f"请生成 {count} 个不同版本的文案，每个版本包含：\n"
            f"1. 标题（吸引眼球）\n"
            f"2. 正文（突出卖点）\n"
            f"3. 行动号召（引导购买）\n\n"
            f"每个版本之间要有明显差异，不要重复。\n"
            f"输出格式：每个版本用 --- 分隔。\n"
        )

        response = self.llm(prompt)
        versions = self._parse_response(response, style, count)
        return versions

    def _parse_response(self, response: str, style: str, expected_count: int) -> List[CopyVersion]:
        """解析模型返回的多个文案版本"""
        parts = response.split("---")
        versions = []

        for i, part in enumerate(parts[:expected_count]):
            content = part.strip()
            if content:
                versions.append(CopyVersion(
                    content=content,
                    style=style,
                    version_id=f"{style}_{i + 1}",
                ))

        return versions if versions else [CopyVersion(
            content=response.strip(),
            style=style,
            version_id=f"{style}_1",
        )]

class ComplianceChecker:
    """合规检查器"""

    # 广告法禁用词库（部分示例）
    ABSOLUTE_BANNED_WORDS = [
        "最", "第一", "唯一", "绝对", "国家级", "全球领先",
        "顶级", "极致", "史无前例", "空前绝后",
    ]

    # 行业特定禁用词
    CATEGORY_BANNED_WORDS = {
        "保健品": [
            "有效率", "治愈率", "三天见效", "无效退款",
            "根治", "永不复发", "纯天然无副作用", "包治百病",
        ],
        "金融": [
            "稳赚不赔", "保本保息", "零风险", "guaranteed",
            "年化收益固定", "绝对安全",
        ],
        "教育": [
            "保过", "包过", "内部渠道", "命题专家",
            "百分百通过", "不过退款",
        ],
    }

    # 需要资质声明的表述
    CLAIM_PATTERNS = [
        (r'(\d+)%', "数据需要标注来源"),
        (r'临床验证|实验证明|科学研究', "需要标注研究机构和结论"),
        (r'专家推荐|权威认证', "需要标注专家姓名和认证机构"),
        (r'用户评价|用户反馈', "需要保证评价真实可查"),
    ]

    def __init__(self, category: str = ""):
        self.category = category

    def check(self, content: str) -> Tuple[bool, List[str]]:
        """执行合规检查，返回 (是否通过, 问题列表)"""
        issues = []

        # 检查绝对化用语
        for word in self.ABSOLUTE_BANNED_WORDS:
            if word in content:
                issues.append(f"包含绝对化用语：{word}")

        # 检查行业特定禁用词
        if self.category in self.CATEGORY_BANNED_WORDS:
            for word in self.CATEGORY_BANNED_WORDS[self.category]:
                if word in content:
                    issues.append(f"包含行业禁用词：{word}")

        # 检查需要资质声明的表述
        for pattern, message in self.CLAIM_PATTERNS:
            if re.search(pattern, content):
                issues.append(message)

        # 检查夸大表述
        exaggeration_patterns = [
            (r'(\d+)\s*天\s*见\s*效', "承诺见效时间，涉嫌虚假宣传"),
            (r'无效\s*退款', "承诺退款，可能涉嫌误导"),
            (r'包\w+过|包\w+会', "承诺效果，涉嫌虚假宣传"),
        ]
        for pattern, message in exaggeration_patterns:
            if re.search(pattern, content):
                issues.append(message)

        passed = len(issues) == 0
        return passed, issues

class QualityEvaluator:
    """文案质量评估器"""

    def evaluate(self, content: str, product: ProductInfo, llm_call_func=None) -> Dict:
        """综合质量评估"""
        score = 100.0
        details = {}

        # 长度评估
        length = len(content)
        if product.platform == "朋友圈" and length > 150:
            score -= 10
            details["length"] = f"过长（{length}字），朋友圈建议100字以内"
        elif length < 20:
            score -= 15
            details["length"] = f"过短（{length}字），信息量不足"
        else:
            details["length"] = f"适中（{length}字）"

        # 卖点覆盖评估
        covered_points = 0
        for point in product.selling_points:
            if point in content:
                covered_points += 1
        coverage = covered_points / len(product.selling_points) if product.selling_points else 0
        if coverage < 0.5:
            score -= 15
        details["selling_point_coverage"] = f"{covered_points}/{len(product.selling_points)}"

        # 行动号召评估
        has_cta = bool(re.search(r'立即|点击|购买|扫码|了解|咨询|限时|抢购', content))
        if not has_cta:
            score -= 10
        details["has_call_to_action"] = has_cta

        # 重复度评估（用于多版本对比）
        details["quality_score"] = round(max(0, score), 1)
        return details

    def calculate_diversity(self, versions: List[CopyVersion]) -> float:
        """计算多个版本之间的多样性分数"""
        if len(versions) < 2:
            return 1.0

        total_similarity = 0
        pair_count = 0

        for i in range(len(versions)):
            for j in range(i + 1, len(versions)):
                similarity = self._text_similarity(versions[i].content, versions[j].content)
                total_similarity += similarity
                pair_count += 1

        avg_similarity = total_similarity / pair_count if pair_count > 0 else 0
        return round(1.0 - avg_similarity, 2)

    def _text_similarity(self, text1: str, text2: str) -> float:
        """简单的文本相似度计算（基于字符级 n-gram）"""
        n = 3
        set1 = set(text1[i:i + n] for i in range(len(text1) - n + 1))
        set2 = set(text2[i:i + n] for i in range(len(text2) - n + 1))

        if not set1 or not set2:
            return 0.0

        intersection = len(set1 & set2)
        union = len(set1 | set2)
        return intersection / union if union > 0 else 0.0


class ABTestManager:
    """A/B 测试管理器"""

    def __init__(self):
        self.experiments: Dict[str, Dict] = {}

    def create_experiment(self, experiment_id: str, versions: List[CopyVersion],
                          total_impressions: int = 1000) -> Dict:
        """创建 A/B 测试实验"""
        self.experiments[experiment_id] = {
            "versions": versions,
            "total_impressions": total_impressions,
            "impressions": {v.version_id: 0 for v in versions},
            "clicks": {v.version_id: 0 for v in versions},
            "conversions": {v.version_id: 0 for v in versions},
            "start_time": time.time(),
        }
        return self.experiments[experiment_id]

    def record_impression(self, experiment_id: str, version_id: str):
        """记录一次展示"""
        if experiment_id in self.experiments:
            self.experiments[experiment_id]["impressions"][version_id] += 1

    def record_click(self, experiment_id: str, version_id: str):
        """记录一次点击"""
        if experiment_id in self.experiments:
            self.experiments[experiment_id]["clicks"][version_id] += 1

    def record_conversion(self, experiment_id: str, version_id: str):
        """记录一次转化"""
        if experiment_id in self.experiments:
            self.experiments[experiment_id]["conversions"][version_id] += 1

    def get_results(self, experiment_id: str) -> List[Dict]:
        """获取测试结果"""
        if experiment_id not in self.experiments:
            return []

        exp = self.experiments[experiment_id]
        results = []

        for version_id in exp["impressions"]:
            impressions = exp["impressions"][version_id]
            clicks = exp["clicks"][version_id]
            conversions = exp["conversions"][version_id]

            ctr = clicks / impressions if impressions > 0 else 0
            cvr = conversions / impressions if impressions > 0 else 0

            results.append({
                "version_id": version_id,
                "impressions": impressions,
                "clicks": clicks,
                "conversions": conversions,
                "ctr": round(ctr, 4),
                "cvr": round(cvr, 4),
            })

        results.sort(key=lambda x: x["cvr"], reverse=True)
        return results

class CopywritingPipeline:
    """营销文案生成完整流程"""

    def __init__(self, llm_call_func):
        self.generator = CopyGenerator(llm_call_func)
        self.compliance_checker = ComplianceChecker()
        self.quality_evaluator = QualityEvaluator()
        self.ab_manager = ABTestManager()

    def set_category(self, category: str):
        """设置产品类别以启用对应合规规则"""
        self.compliance_checker = ComplianceChecker(category)

    def process(self, product: ProductInfo, styles: List[str],
                versions_per_style: int = 2) -> List[CopyVersion]:
        """执行完整的文案生成流程"""
        all_versions = []

        for style in styles:
            # 第一步：生成文案
            versions = self.generator.generate(product, style, versions_per_style)

            for version in versions:
                # 第二步：合规检查
                passed, issues = self.compliance_checker.check(version.content)
                version.compliance_passed = passed
                version.compliance_issues = issues

                if not passed:
                    continue

                # 第三步：质量评估
                quality = self.quality_evaluator.evaluate(version.content, product)
                version.quality_score = quality.get("quality_score", 0)

                all_versions.append(version)

        # 第四步：多样性检查
        if len(all_versions) >= 2:
            diversity = self.quality_evaluator.calculate_diversity(all_versions)
            if diversity < 0.3:
                print(f"警告：版本间多样性不足（{diversity}），建议调整 temperature")

        return all_versions
