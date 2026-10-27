class SummaryEvaluator:
    def __init__(self, config=None):
        self.config = config or {}
        self.info_loss_threshold = 0.15
        self.compression_range = (0.10, 0.40)
    
    def evaluate(self, summary, original, reference=None):
        results = {}
        results['info_loss'] = self._detect_info_loss(summary, original)
        results['fact_consistency'] = self._check_fact_consistency(summary, original)
        results['compression'] = self._check_compression(summary, original)
        results['readability'] = self._check_readability(summary)
        results['overall'] = self._make_decision(results)
        return results
    
    def _make_decision(self, results):
        if not results['info_loss']['passed']:
            return {'passed': False, 'reason': '信息丢失率过高'}
        if not results['fact_consistency']['passed']:
            return {'passed': False, 'reason': '事实不一致'}
        return {'passed': True, 'reason': '所有指标合格'}

class TestSummaryEvaluator:
    def test_information_loss_detection(self):
        """信息丢失应该被检测到"""
        original = "销售额增长5%，净利润下降3%，建议缩减B产品线。"
        summary = "销售额增长5%。"
        result = self.evaluator.evaluate(summary, original)
        assert result['info_loss']['loss_rate'] > 0.3
    
    def test_fact_inconsistency(self):
        """事实不一致应该被检测到"""
        original = "订单量增长15%，销售额增长5%。"
        summary = "销售额增长15%。"
        result = self.evaluator.evaluate(summary, original)
        assert result['overall']['passed'] is False

def batch_test(documents_dir, output_dir):
    evaluator = SummaryEvaluator()
    summarizer = GenerativeSummarizer()
    results = []
    for doc_path in Path(documents_dir).glob('*.txt'):
        original = doc_path.read_text(encoding='utf-8')
        summary = summarizer.summarize(original)
        result = evaluator.evaluate(summary, original)
        results.append(result)
    
    passed = sum(1 for r in results if r['overall']['passed'])
    print(f"通过率: {passed}/{len(results)}")
