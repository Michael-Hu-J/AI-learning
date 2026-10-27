from src.multimodal_app import MultimodalApp

# 模拟 LLM 调用函数
def mock_llm(messages):
    return "发票号码为 12345678，金额为 15800 元。"

# 初始化应用
app = MultimodalApp("config.yaml", mock_llm)

# 处理图片（OCR 任务）
result = app.process_file("data/invoice.jpg", task="ocr")
print(result["data"]["text"])        # 识别文本
print(result["data"]["confidence"])  # 置信度
print(result["quality_check"])       # 质量校验结果

# 处理音频
result = app.process_file("data/meeting.mp3", task="audio")
print(result["data"]["transcription"])

from difflib import SequenceMatcher
import re

def test_ocr_accuracy(test_images: list) -> dict:
    """OCR准确性测试"""
    results = []
    
    for img in test_images:
        ocr_text = ocr_engine.recognize(img.path)
        
        # 计算编辑距离相似度
        similarity = SequenceMatcher(None, img.ground_truth, ocr_text).ratio()
        
        # 检查关键字段
        amount_match = re.search(r'(\d+\.?\d*)\s*元', ocr_text)
        expected_amount = re.search(r'(\d+\.?\d*)\s*元', img.ground_truth)
        amount_ok = amount_match and expected_amount and amount_match.group(1) == expected_amount.group(1)
        
        # 检查税号
        tax_match = re.search(r'(\d{15,20})', ocr_text)
        expected_tax = re.search(r'(\d{15,20})', img.ground_truth)
        tax_ok = tax_match and expected_tax and tax_match.group(1) == expected_tax.group(1)
        
        results.append({
            'image': img.path,
            'ground_truth': img.ground_truth,
            'ocr_result': ocr_text,
            'similarity': similarity,
            'amount_ok': amount_ok,
            'tax_ok': tax_ok,
            'passed': similarity >= 0.95 and amount_ok and tax_ok
        })
    
    pass_rate = sum(1 for r in results if r['passed']) / len(results)
    
    return {
        'total': len(results),
        'passed': sum(1 for r in results if r['passed']),
        'pass_rate': pass_rate,
        'avg_similarity': sum(r['similarity'] for r in results) / len(results),
        'details': results
    }

def test_image_understanding(test_images: list) -> dict:
    """图片理解测试"""
    results = []
    for img in test_images:
        description = image_engine.describe(img.path)
        found = sum(1 for info in img.key_info if info in description)
        completeness = found / len(img.key_info) if img.key_info else 1.0
        results.append({'image': img.path, 'completeness': completeness, 'passed': completeness >= 0.80})
    
    return {'total': len(results), 'pass_rate': sum(1 for r in results if r['passed']) / len(results)}

def test_chart_analysis(test_charts: list) -> dict:
    """图表分析测试"""
    results = []
    for chart in test_charts:
        analysis = chart_engine.analyze(chart.path)
        value_ok = True
        for key, expected in chart.expected_analysis.items():
            actual = analysis.get(key)
            if isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
                if abs(actual - expected) / expected > 0.05:
                    value_ok = False
        results.append({'chart': chart.path, 'passed': value_ok})
    
    return {'total': len(results), 'pass_rate': sum(1 for r in results if r['passed']) / len(results)}

def test_audio_processing(test_audios: list) -> dict:
    """音频处理测试"""
    results = []
    for audio in test_audios:
        transcript = audio_engine.transcribe(audio.path)
        similarity = SequenceMatcher(None, audio.ground_truth, transcript).ratio()
        results.append({
            'audio': audio.path,
            'similarity': similarity,
            'passed': similarity >= 0.90
        })
    
    return {
        'total': len(results),
        'passed': sum(1 for r in results if r['passed']) / len(results),
        'pass_rate': sum(1 for r in results if r['passed']) / len(results),
        'avg_similarity': sum(r['similarity'] for r in results) / len(results)
    }

def test_multimodal_pipeline(test_cases: list) -> dict:
    """多模态端到端测试"""
    results = []
    
    for case in test_cases:
        # Step 1: 模态A处理（如OCR）
        step1_result = step1_engine.process(case.input)
        
        # Step 2: 模态B处理（如NLP理解）
        step2_result = step2_engine.process(step1_result)
        
        # Step 3: 结果验证
        final_ok = validate_final_result(step2_result, case.expected_output)
        
        # 逐层分析误差
        step1_ok = validate_step1(step1_result, case.expected_step1)
        step2_ok = validate_step2(step2_result, case.expected_step2)
        
        results.append({
            'case': case.id,
            'step1_passed': step1_ok,
            'step2_passed': step2_ok,
            'final_passed': final_ok,
            'error_source': determine_error_source(step1_ok, step2_ok, final_ok)
        })
    
    return {
        'total': len(results),
        'step1_pass_rate': sum(1 for r in results if r['step1_passed']) / len(results),
        'step2_pass_rate': sum(1 for r in results if r['step2_passed']) / len(results),
        'end_to_end_pass_rate': sum(1 for r in results if r['final_passed']) / len(results),
        'error_distribution': analyze_error_distribution(results)
    }
