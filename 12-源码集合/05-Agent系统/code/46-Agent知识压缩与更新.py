class HierarchicalCompressor:
    """分层压缩器：近期完整保留，远期分层压缩"""
    
    def __init__(self, llm, recent_rounds=5, mid_rounds=25):
        self.llm = llm
        self.recent_rounds = recent_rounds    # 近期：完整保留
        self.mid_rounds = mid_rounds           # 中期：200字摘要
        self.key_patterns = [                 # 关键信息正则
            r'订单号[:\s]*([A-Za-z0-9]+)',
            r'金额[:\s]*(\d+\.?\d*)',
            r'时间[:\s]*(\d{4}-\d{2}-\d{2})',
        ]
    
    def compress(self, conversation):
        if len(conversation) <= self.recent_rounds:
            return conversation
        
        recent = conversation[-self.recent_rounds:]
        mid = conversation[-self.mid_rounds:-self.recent_rounds]
        far = conversation[:-self.mid_rounds]
        
        # 中期压缩为200字摘要
        mid_summary = self._summarize(mid, max_length=200)
        
        # 远期压缩为50字概要
        far_summary = self._summarize(far, max_length=50)
        
        # 提取关键信息强制保留
        key_info = self._extract_key_info(conversation)
        
        return {
            "key_info": key_info,
            "far_summary": far_summary,
            "mid_summary": mid_summary,
            "recent": recent
        }

def evaluate_compression(original_text, compressed_text, key_items=None):
    """评估压缩质量"""
    # 1. 计算压缩率
    original_tokens = count_tokens(original_text)
    compressed_tokens = count_tokens(compressed_text)
    compression_ratio = 1 - compressed_tokens / original_tokens
    
    # 2. 信息保留率（如果有key_items）
    preservation_rate = None
    if key_items:
        preserved = sum(1 for item in key_items if item in compressed_text)
        preservation_rate = preserved / len(key_items)
    
    # 3. 语义一致性（用LLM评估）
    consistency_prompt = f"""
    请判断以下压缩结果是否改变了原文的核心含义。
    原文：{original_text[:2000]}
    压缩结果：{compressed_text}
    只回答"一致"或"不一致"，并说明原因。
    """
    consistency = llm.invoke(consistency_prompt).content
    
    return {
        "compression_ratio": compression_ratio,
        "preservation_rate": preservation_rate,
        "consistency": consistency,
        "passed": compression_ratio >= 0.5 and (
            preservation_rate is None or preservation_rate >= 0.8
        )
    }

class MemoryUpdater:
    """记忆更新管理器：支持冲突检测和覆盖更新"""
    
    def __init__(self, storage):
        self.storage = storage
        self.conflict_rules = {
            "user_city": "latest_wins",      # 城市：最新值获胜
            "user_name": "latest_wins",      # 姓名：最新值获胜
            "order_status": "state_machine", # 订单状态：状态机转换
        }
    
    def update(self, key, value, user_id):
        old_value = self.storage.get(key, user_id)
        
        # 冲突检测
        if old_value is not None and old_value != value:
            rule = self.conflict_rules.get(key, "latest_wins")
            if rule == "latest_wins":
                self.storage.set(key, value, user_id)
            elif rule == "state_machine":
                if not self._is_valid_transition(old_value, value):
                    raise ValueError(f"无效的状态转换: {old_value} -> {value}")
                self.storage.set(key, value, user_id)
        
        # 记录审计日志
        self._log_audit(key, old_value, value, user_id)
        
        return True

def test_memory_lifecycle(agent):
    """测试完整记忆生命周期"""
    # 阶段1：收集（100轮对话）
    for i in range(100):
        agent.process(f"用户输入{i}")
    
    # 阶段2：压缩
    compressed = agent.compress_memory()
    assert compressed.compression_ratio >= 0.5
    assert compressed.preservation_rate >= 0.8
    
    # 阶段3：存储
    agent.save_compressed_memory(compressed)
    
    # 阶段4：更新（用户纠正信息）
    agent.update_memory("user_city", "上海")
    
    # 阶段5：验证更新及时性
    response = agent.answer("我住在哪？")
    assert "上海" in response
    
    # 阶段6：再压缩（验证多轮压缩稳定性）
    compressed2 = agent.compress_memory()
    assert compressed2.preservation_rate >= 0.7
    
    return {"passed": True, "stages": 6}

"""
Agent 知识压缩测试
验证压缩后信息是否完整、质量是否下降
"""
import pytest
from dataclasses import dataclass
from typing import List, Dict

@dataclass
class CompressionResult:
    original_length: int
    compressed_length: int
    compression_ratio: float
    information_loss: float
    key_entities_preserved: List[str]
    key_events_preserved: List[str]


class TestKnowledgeCompression:
    def test_summary_compression(self):
        conversation = [
            {"role": "user", "content": "我想订明天去北京的机票"},
            {"role": "agent", "content": "好的，请问什么时间？"},
            {"role": "user", "content": "上午的航班"},
            {"role": "agent", "content": "查到了，CA1201 08:00 起飞，¥1200"},
            {"role": "user", "content": "订这个"},
            {"role": "agent", "content": "已订好，订单号 BJ20260608001"},
        ]
        compressor = SummaryCompressor()
        result = compressor.compress(conversation)
        assert result.compression_ratio >= 0.5, "压缩率应 >= 50%"
        assert "北京" in result.key_entities_preserved, "应保留目的地"
        assert "CA1201" in result.key_events_preserved or \
               "已订好" in result.key_events_preserved, "应保留订票结果"

    def test_information_loss_measurement(self):
        conversation = self.prepare_test_conversation()
        key_info = self.extract_key_info(conversation)
        result = self.compressor.compress(conversation)
        preserved = set(result.key_entities_preserved) & set(key_info)
        loss_rate = 1 - len(preserved) / len(key_info)
        assert loss_rate <= 0.2, f"信息损失率应 <= 20%，实际 {loss_rate:.1%}"

    def test_compression_quality_after_multiple_rounds(self):
        conversation = self.prepare_long_conversation()
        prev_result = None
        for round_num in range(5):
            result = self.compressor.compress(conversation)
            if round_num > 0:
                assert len(result.key_entities_preserved) >= \
                       len(prev_result.key_entities_preserved) * 0.9, \
                    f"第{round_num}轮压缩导致信息进一步丢失"
            prev_result = result
            conversation = result.compressed_text

    def test_sliding_window_compression(self):
        window_size = 5
        conversation = [f"第{i}轮对话" for i in range(20)]
        compressed = self.sliding_window.compress(conversation, window_size)
        assert len(compressed) == window_size
        assert compressed[0] == "第15轮对话"
        assert compressed[-1] == "第19轮对话"

    def test_hierarchical_compression(self):
        conversation = self.prepare_30_round_conversation()
        result = self.hierarchical_compressor.compress(
            conversation, recent_rounds=5, far_summary=True
        )
        assert len(result.recent_content) == 5
        assert result.far_summary is not None
        assert len(result.far_summary) > 0

    def test_token_savings(self):
        conversation = self.prepare_long_conversation()
        original_tokens = count_tokens(conversation)
        result = self.compressor.compress(conversation)
        compressed_tokens = count_tokens(result.compressed_text)
        savings = (original_tokens - compressed_tokens) / original_tokens
        assert savings >= 0.5, f"Token 节省应 >= 50%，实际 {savings:.1%}"


class CompressionQualityEvaluator:
    """压缩质量评估器"""
    def evaluate_entity_preservation(self, original, compressed):
        original_entities = self.extract_entities(original)
        compressed_entities = self.extract_entities(compressed)
        preserved = original_entities & compressed_entities
        preservation_rate = len(preserved) / len(original_entities)
        return {
            "preservation_rate": preservation_rate,
            "lost_entities": list(original_entities - compressed_entities),
        }

    def evaluate_compression_quality(self, original, compressed):
        entity = self.evaluate_entity_preservation(original, compressed)
        savings = self.calculate_token_savings(original, compressed)
        score = entity["preservation_rate"] * 0.4 + min(savings / 0.7, 1.0) * 0.1
        return {"overall_score": score, **entity}


class TestKnowledgeUpdate:
    def test_outdated_info_cleanup(self):
        memory = {"user_address": "北京市朝阳区XX路1号", "last_updated": "2025-01-01"}
        updater = KnowledgeUpdater(memory)
        updated = updater.update("我搬家了，现在住上海市浦东新区YY路2号")
        assert updated["user_address"] == "上海市浦东新区YY路2号"
        response = agent.answer("我的地址是什么？")
        assert "朝阳区" not in response, "不应再提到旧地址"

    def test_conflict_resolution(self):
        memory = {"user_preference": "喜欢红色"}
        updater = KnowledgeUpdater(memory)
        result = updater.detect_and_resolve_conflict("我现在喜欢蓝色了")
        assert result.has_conflict is True
        assert result.resolved_preference == "喜欢蓝色"

    def test_memory_capacity_trigger(self):
        memory_manager = MemoryManager(max_tokens=1000)
        for i in range(50):
            memory_manager.add(f"第{i}条记忆信息" * 10)
        assert memory_manager.current_tokens <= memory_manager.max_tokens

    def test_update_consistency(self):
        memory = KnowledgeBase()
        for value in ["北京", "上海", "广州"]:
            memory.update("user_city", value)
        assert memory.get("user_city") == "广州"
        assert len(memory.get_all("user_city")) == 1

    def test_feedback_based_update(self):
        memory = KnowledgeBase()
        memory.add("user_hobby", "游泳")
        memory.apply_feedback({"type": "correction", "key": "user_hobby", "value": "跑步"})
        assert memory.get("user_hobby") == "跑步"


class UpdateQualityEvaluator:
    def evaluate_update_accuracy(self, memory, updates, expected):
        errors = []
        for key, value in updates:
            memory.update(key, value)
        for key, expected_value in expected.items():
            if memory.get(key) != expected_value:
                errors.append({"key": key, "expected": expected_value})
        return {"accuracy": 1 - len(errors) / len(updates), "errors": errors}

    def evaluate_update_latency(self, memory, updates):
        import time
        latencies = []
        for key, value in updates:
            start = time.time()
            memory.update(key, value)
            latencies.append((time.time() - start) * 1000)
        latencies.sort()
        return {
            "p50_latency_ms": latencies[len(latencies) // 2],
            "p95_latency_ms": latencies[int(len(latencies) * 0.95)],
        }


class TestCompressionAndUpdate:
    def test_compress_then_update(self):
        conversation = self.prepare_long_conversation()
        compressed = self.compressor.compress(conversation)
        memory = KnowledgeUpdater().update_from_summary(compressed.compressed_text)
        assert len(memory) > 0 and memory.contains_key_facts()

    def test_end_to_end_memory_lifecycle(self):
        agent = AgentWithMemory()
        for i in range(100):
            agent.process(f"用户输入{i}")
        compressed = agent.compress_memory()
        assert compressed.compression_ratio >= 0.5
        agent.save_compressed_memory(compressed)
        agent.update_memory("user_city", "上海")
        final = agent.compress_memory()
        assert "上海" in final.content
        assert final.compression_ratio >= 0.5
