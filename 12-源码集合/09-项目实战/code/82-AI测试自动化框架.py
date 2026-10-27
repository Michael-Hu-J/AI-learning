def run_test_case(test_case, model):
    # 1. 把 prompt 发给模型
    response = model.generate(test_case["input"]["prompt"])
    
    # 2. 根据验证规则判断结果
    validation_result = validate(response, test_case["validation"])
    
    # 3. 返回结果
    return {
        "name": test_case["name"],
        "passed": validation_result["passed"],
        "details": validation_result["details"],
        "response_time": validation_result["time"]
    }

class AITestFramework:
    """AI测试自动化框架核心类"""
    
    def __init__(self, config_path="config.yaml"):
        self.config = self._load_config(config_path)
        self.loader = TestLoader()
        self.runner = TestRunner(
            max_workers=self.config.get("max_workers", 5),
            timeout=self.config.get("timeout", 30)
        )
        self.validator = ResultValidator()
        self.reporter = ReportGenerator()
    
    def run(self, suite_path, model_endpoint, output_dir="./results"):
        """运行完整测试流程"""
        # 加载测试套件
        suite = self.loader.load(suite_path)
        print(f"加载了 {len(suite.cases)} 个测试用例")
        
        # 执行测试
        results = self.runner.execute(
            cases=suite.cases,
            endpoint=model_endpoint,
            config=self.config
        )
        
        # 验证结果
        validated = self.validator.validate_all(results, suite.cases)
        
        # 生成报告
        report = self.reporter.generate(validated, output_dir)
        return report

class ResultValidator:
    """结果验证器"""
    
    def __init__(self):
        self.strategies = {
            "keyword": self._check_keywords,
            "similarity": self._check_similarity,
            "rule": self._check_rules,
            "llm_judge": self._check_with_llm
        }
    
    def validate(self, result, test_case):
        """根据用例配置选择验证策略"""
        v_type = test_case["validation"]["type"]
        strategy = self.strategies.get(v_type)
        if not strategy:
            raise ValueError(f"未知验证类型: {v_type}")
        return strategy(result, test_case)
    
    def _check_similarity(self, result, test_case):
        """相似度验证"""
        from difflib import SequenceMatcher
        threshold = test_case["validation"].get("threshold", 0.7)
        # 这里用 embedding 相似度更准确
        score = compute_semantic_similarity(
            result.text, 
            test_case["expected"]["reference"]
        )
        return {"passed": score >= threshold, "score": score}

import asyncio
import aiohttp

async def batch_test(cases, endpoint, batch_size=10):
    """异步批量测试，控制并发量"""
    semaphore = asyncio.Semaphore(batch_size)
    
    async def single_test(case):
        async with semaphore:
            async with aiohttp.ClientSession() as session:
                start = time.time()
                async with session.post(endpoint, json={"prompt": case["input"]["prompt"]}) as resp:
                    result = await resp.json()
                    elapsed = time.time() - start
                    return {"case": case, "result": result, "time": elapsed}
    
    tasks = [single_test(c) for c in cases]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return [r for r in results if not isinstance(r, Exception)]
