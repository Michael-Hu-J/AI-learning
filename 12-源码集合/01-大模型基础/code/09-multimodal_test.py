import base64
import json
from openai import OpenAI

def test_image_understanding(image_path: str, question: str, model: str = "qwen-vl-plus") -> str:
    """测试模型的图像理解能力
    
    Args:
        image_path: 图片文件路径
        question: 提问内容
        model: 模型名称
    
    Returns:
        模型的回答文本
    """
    # 将图片编码为 base64
    with open(image_path, "rb") as f:
        image_b64 = base64.b64encode(f.read()).decode()
    
    client = OpenAI(api_key="your-api-key")
    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{image_b64}"}
                    },
                    {"type": "text", "text": question}
                ]
            }
        ]
    )
    return response.choices[0].message.content

import pytest
from dataclasses import dataclass
from typing import List

@dataclass
class TestCase:
    """测试用例数据结构"""
    id: str
    image_path: str
    question: str
    expected_keywords: List[str]
    difficulty: str  # "easy" | "medium" | "hard"

def calculate_text_similarity(actual: str, expected: str) -> float:
    """用编辑距离估算 OCR 相似度（0~1）"""
    from difflib import SequenceMatcher
    return SequenceMatcher(None, actual, expected).ratio()

class TestMultimodalImage:
    """多模态图像理解自动化测试"""

    @pytest.fixture
    def test_cases(self):
        return [
            TestCase("MU-001", "test_images/cat_dog.jpg", "图片里有什么动物？", ["猫", "狗"], "easy"),
            TestCase("MU-002", "test_images/chart.png", "柱状图中最高的柱子是多少？", ["100", "一百"], "medium"),
            TestCase("MU-003", "test_images/sign.jpg", "路牌上写的什么？", ["前方", "施工"], "easy"),
            TestCase("MU-004", "test_images/spatial.png", "左边的球是什么颜色？", ["红", "红色"], "medium"),
            TestCase("MU-005", "test_images/handwritten.jpg", "请识别图片中的所有文字", ["测试", "文字"], "hard"),
        ]

    @pytest.mark.parametrize("image,question,expected_keyword", [
        ("cat_dog.jpg", "图片里有什么动物？", ["猫", "狗"]),
        ("chart.png", "柱状图中最高的柱子是多少？", ["100", "一百"]),
        ("sign.jpg", "路牌上写的什么？", ["前方", "施工"]),
    ])
    def test_image_understanding(self, image, question, expected_keyword):
        """测试图像理解基础能力"""
        result = test_image_understanding(
            image_path=f"test_images/{image}",
            question=question
        )
        assert any(kw in result for kw in expected_keyword), \
            f"期望包含 {expected_keyword}，实际: {result}"

    def test_spatial_reasoning(self):
        """测试空间关系理解"""
        result = test_image_understanding(
            image_path="test_images/left_right.png",
            question="左边的球是什么颜色？右边的球是什么颜色？"
        )
        assert "左" in result and "红" in result, f"左侧判断错误: {result}"
        assert "右" in result and "蓝" in result, f"右侧判断错误: {result}"

    def test_ocr_accuracy(self):
        """测试 OCR 文字识别准确率"""
        result = test_image_understanding(
            image_path="test_images/handwritten.jpg",
            question="请识别图片中的所有文字"
        )
        expected_text = "测试文字内容"
        similarity = calculate_text_similarity(result, expected_text)
        assert similarity > 0.8, f"OCR 准确率过低: {similarity:.2%}"

def llm_judge_evaluate(
    question: str,
    expected_answer: str,
    actual_answer: str,
    judge_model: str = "gpt-4"
) -> dict:
    """用 LLM 作为裁判来评估回答质量
    
    Returns:
        {"score": 0-10, "reason": "评分理由", "pass": True/False}
    """
    prompt = f"""
    你是一个多模态模型测试的裁判。请评估以下回答的质量。

    问题：{question}
    期望答案：{expected_answer}
    实际回答：{actual_answer}

    请从以下维度评分（1-10分）：
    1. 准确性：回答是否准确
    2. 完整性：回答是否完整
    3. 相关性：回答是否与问题相关

    请以 JSON 格式返回评分结果。
    """
    
    response = call_llm(model=judge_model, prompt=prompt)
    return json.loads(response)

import pandas as pd
from datetime import datetime

def run_batch_test(model_name: str, test_cases: List[dict]) -> pd.DataFrame:
    """批量运行多模态测试并返回结果 DataFrame"""
    results = []
    
    for case in test_cases:
        try:
            start_time = datetime.now()
            answer = test_image_understanding(
                image_path=case["image_path"],
                question=case["question"],
                model=model_name
            )
            latency = (datetime.now() - start_time).total_seconds() * 1000
            
            # 评分
            score = llm_judge_evaluate(
                question=case["question"],
                expected_answer=case["expected"],
                actual_answer=answer
            )
            
            results.append({
                "case_id": case["id"],
                "category": case["category"],
                "passed": score["score"] >= 7,
                "score": score["score"],
                "latency_ms": latency,
                "answer": answer,
                "reason": score["reason"]
            })
        except Exception as e:
            results.append({
                "case_id": case["id"],
                "category": case["category"],
                "passed": False,
                "score": 0,
                "latency_ms": None,
                "answer": None,
                "reason": f"Error: {str(e)}"
            })
    
    df = pd.DataFrame(results)
    return df

def generate_report(df: pd.DataFrame) -> dict:
    """生成测试报告"""
    report = {
        "total_cases": len(df),
        "pass_rate": df["passed"].mean(),
        "avg_score": df["score"].mean(),
        "avg_latency_ms": df["latency_ms"].mean(),
        "by_category": df.groupby("category").agg({
            "passed": "mean",
            "score": "mean",
            "latency_ms": "mean"
        }).to_dict()
    }
    return report

def run_multimodal_benchmark(model_name: str, test_set: list) -> dict:
    """运行多模态基准测试，返回通过率与延迟"""
    results = {
        "model": model_name,
        "total": len(test_set),
        "passed": 0,
        "failed": 0,
        "errors": [],
        "details": []
    }

    for case in test_set:
        try:
            result = call_model(
                model=model_name,
                image=case["image"],
                prompt=case["prompt"]
            )
            is_correct = evaluate_answer(result, case["expected"])

            if is_correct:
                results["passed"] += 1
            else:
                results["failed"] += 1
                results["errors"].append({
                    "case": case["id"],
                    "expected": case["expected"],
                    "actual": result
                })

            results["details"].append({
                "case": case["id"],
                "passed": is_correct,
                "latency_ms": result["latency"]
            })
        except Exception as e:
            results["failed"] += 1
            results["errors"].append({"case": case["id"], "error": str(e)})

    results["accuracy"] = results["passed"] / results["total"]
    results["avg_latency_ms"] = sum(
        d["latency_ms"] for d in results["details"]
    ) / len(results["details"])
    return results

# 替换为你的图片路径和问题
answer = test_image_understanding(
    image_path="my_photo.jpg",
    question="请描述图片中的主要物体，并说明它们的空间位置关系"
)
print(answer)

test_set = [
    {"id": "MU-001", "image": "cat_dog.jpg", "prompt": "图片里有什么动物？", "expected": "猫和狗"},
    {"id": "MU-003", "image": "chart.png", "prompt": "柱状图最高值是多少？", "expected": "100"},
    {"id": "MU-004", "image": "left_right.png", "prompt": "左边球什么颜色？", "expected": "红色"},
]

for model in ["qwen-vl-plus", "gpt-4o"]:
    report = run_multimodal_benchmark(model, test_set)
    print(f"{model}: 通过率 {report['accuracy']:.0%}, 平均延迟 {report['avg_latency_ms']:.0f}ms")

# 用一张空白或极简图片，看模型会不会"脑补"
answer = test_image_understanding(
    image_path="empty_room.jpg",
    question="请详细列出房间里所有物品"
)
print(answer)
