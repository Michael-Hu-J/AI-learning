import re
import hashlib
from dataclasses import dataclass, field
from typing import List, Tuple, Optional
from enum import Enum

class PIICategory(Enum):
    """PII 类别"""
    PHONE = "phone"
    ID_CARD = "id_card"
    EMAIL = "email"
    NAME = "name"
    ADDRESS = "address"
    BANK_CARD = "bank_card"
    PLATE_NUMBER = "plate_number"

@dataclass
class PIIMatch:
    """PII 匹配结果"""
    category: PIICategory
    original: str
    start: int
    end: int
    replacement: str = ""

class PIIDetector:
    """PII 检测器"""

    PATTERNS = {
        PIICategory.PHONE: r'1[3-9]\d{9}',
        PIICategory.ID_CARD: r'\d{17}[\dXx]',
        PIICategory.EMAIL: r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
        PIICategory.BANK_CARD: r'\b\d{16,19}\b',
        PIICategory.PLATE_NUMBER: r'[京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏川宁琼][A-Z][A-Z0-9]{5,6}',
    }

    NAME_PATTERN = r'[\u4e00-\u9fa5]{2,4}'

    # 常见非人名词汇排除表
    NON_NAME_WORDS = {
        "这个", "那个", "什么", "怎么", "为什么", "可以", "如果", "但是",
        "因为", "所以", "虽然", "但是", "已经", "现在", "今天", "明天",
        "昨天", "这里", "那里", "哪里", "多少", "几个", "一些", "所有",
    }

    def __init__(self):
        self.compiled_patterns = {}
        for category, pattern in self.PATTERNS.items():
            self.compiled_patterns[category] = re.compile(pattern)

    def detect(self, text: str) -> List[PIIMatch]:
        """检测文本中的所有 PII"""
        matches = []

        # 先清理非数字字符（空格、横杠等），再检测
        cleaned_text = re.sub(r'[\s\-]', '', text)

        for category, compiled in self.compiled_patterns.items():
            for match in compiled.finditer(cleaned_text):
                # 映射回原始文本的位置
                original_start = self._map_position(text, cleaned_text, match.start())
                original_end = self._map_position(text, cleaned_text, match.end())
                matches.append(PIIMatch(
                    category=category,
                    original=match.group(),
                    start=original_start,
                    end=original_end,
                ))

        # 检测姓名
        for match in re.finditer(self.NAME_PATTERN, text):
            word = match.group()
            if word not in self.NON_NAME_WORDS and len(word) <= 4:
                matches.append(PIIMatch(
                    category=PIICategory.NAME,
                    original=word,
                    start=match.start(),
                    end=match.end(),
                ))

        matches.sort(key=lambda m: m.start)
        return self._remove_overlaps(matches)

    def _map_position(self, original: str, cleaned: str, cleaned_pos: int) -> int:
        """将清理后文本的位置映射回原始文本的位置"""
        orig_idx = 0
        clean_idx = 0
        while clean_idx < cleaned_pos and orig_idx < len(original):
            if original[orig_idx] not in ' \-':
                clean_idx += 1
            orig_idx += 1
        return orig_idx

    def _remove_overlaps(self, matches: List[PIIMatch]) -> List[PIIMatch]:
        """去除重叠的匹配"""
        if not matches:
            return []
        result = [matches[0]]
        for match in matches[1:]:
            if match.start >= result[-1].end:
                result.append(match)
        return result

class DataDesensitizer:
    """数据脱敏器"""

    def __init__(self, strategy: str = "mask", salt: str = ""):
        self.strategy = strategy
        self.salt = salt

    def desensitize(self, text: str, detector: PIIDetector) -> Tuple[str, List[PIIMatch]]:
        """对文本进行脱敏处理"""
        matches = detector.detect(text)
        if not matches:
            return text, []

        result = text
        for match in reversed(matches):
            if self.strategy == "mask":
                replacement = self._mask(match)
            elif self.strategy == "hash":
                replacement = self._hash(match)
            elif self.strategy == "remove":
                replacement = ""
            else:
                replacement = "[REDACTED]"

            match.replacement = replacement
            result = result[:match.start] + replacement + result[match.end:]

        return result, matches

    def _mask(self, match: PIIMatch) -> str:
        original = match.original
        if match.category == PIICategory.PHONE:
            return original[:3] + "****" + original[7:]
        elif match.category == PIICategory.ID_CARD:
            return original[:4] + "********" + original[-2:]
        elif match.category == PIICategory.EMAIL:
            parts = original.split("@")
            return parts[0][:2] + "***@" + parts[1]
        elif match.category == PIICategory.NAME:
            return original[0] + "**" if len(original) > 1 else "**"
        elif match.category == PIICategory.BANK_CARD:
            return original[:4] + " **** **** " + original[-4:]
        else:
            return "[脱敏]"

    def _hash(self, match: PIIMatch) -> str:
        hash_value = hashlib.sha256(
            f"{self.salt}:{match.original}".encode()
        ).hexdigest()[:8]
        return f"<{match.category.value}_hash_{hash_value}>"


if __name__ == "__main__":
    detector = PIIDetector()
    desensitizer = DataDesensitizer(strategy="mask")

    test_texts = [
        "我的手机号是13812345678，邮箱是zhangsan@example.com",
        "患者张三，身份证号320106199001011234，电话13987654321",
        "请联系李四处理，他车牌号是京A12345",
        "正常对话，不涉及任何个人信息",
    ]

    for text in test_texts:
        desensitized, matches = desensitizer.desensitize(text, detector)
        print(f"\n原文: {text}")
        print(f"脱敏: {desensitized}")
        if matches:
            print(f"检测到 {len(matches)} 条 PII:")
            for m in matches:
                print(f"  - [{m.category.value}] {m.original} → {m.replacement}")

import os
import json
import base64
import hashlib
from dataclasses import dataclass
from typing import Optional
from datetime import datetime

# 生产环境请使用 cryptography 库
# pip install cryptography
# from cryptography.fernet import Fernet

class EncryptionManager:
    """加密管理器 - 演示核心逻辑"""

    def __init__(self, master_key: str):
        self.master_key = master_key
        self.key = hashlib.sha256(master_key.encode()).digest()

    def encrypt(self, plaintext: str) -> str:
        """加密数据（简化版XOR演示，生产环境用AES-GCM）"""
        key_bytes = self.key
        text_bytes = plaintext.encode('utf-8')
        encrypted = bytes(
            b ^ key_bytes[i % len(key_bytes)]
            for i, b in enumerate(text_bytes)
        )
        return base64.b64encode(encrypted).decode('utf-8')

    def decrypt(self, ciphertext: str) -> str:
        """解密数据"""
        encrypted = base64.b64decode(ciphertext.encode('utf-8'))
        key_bytes = self.key
        decrypted = bytes(
            b ^ key_bytes[i % len(key_bytes)]
            for i, b in enumerate(encrypted)
        )
        return decrypted.decode('utf-8')

    def hash_for_lookup(self, value: str) -> str:
        """加盐哈希，用于查找索引"""
        salt = os.urandom(16).hex()
        hash_value = hashlib.sha256(
            f"{salt}:{value}:{self.master_key}".encode()
        ).hexdigest()
        return f"{salt}:{hash_value}"

@dataclass
class EncryptedRecord:
    record_id: str
    encrypted_data: str
    data_hash: str
    encrypted_at: str
    key_version: str = "v1"

class SecureDataStore:
    """安全数据存储"""

    def __init__(self, master_key: str):
        self.encryption = EncryptionManager(master_key)
        self.store = {}

    def save(self, record_id: str, data: dict) -> EncryptedRecord:
        json_data = json.dumps(data, ensure_ascii=False)
        encrypted = self.encryption.encrypt(json_data)
        data_hash = self.encryption.hash_for_lookup(json_data)

        record = EncryptedRecord(
            record_id=record_id,
            encrypted_data=encrypted,
            data_hash=data_hash,
            encrypted_at=datetime.now().isoformat(),
        )
        self.store[record_id] = record
        return record

    def load(self, record_id: str) -> Optional[dict]:
        record = self.store.get(record_id)
        if not record:
            return None
        json_data = self.encryption.decrypt(record.encrypted_data)
        return json.loads(json_data)


if __name__ == "__main__":
    store = SecureDataStore(master_key="my-super-secret-key-2024")

    user_data = {
        "name": "张三",
        "phone": "13812345678",
        "email": "zhangsan@example.com",
        "diagnosis": "高血压",
    }

    record = store.save("user_001", user_data)
    print(f"存储成功: {record.record_id}")
    print(f"加密数据: {record.encrypted_data[:50]}...")

    loaded = store.load("user_001")
    print(f"\n解密后: {loaded}")
    print(f"与原始数据一致: {loaded == user_data}")

import hashlib
from dataclasses import dataclass
from typing import List, Set

@dataclass
class PrivacyViolation:
    training_sample_id: str
    leaked_field: str
    original_value: str
    detection_method: str
    severity: str  # low / medium / high / critical

class TrainingDataPrivacyChecker:
    """训练数据隐私检查器"""

    def __init__(self):
        self.known_pii_hashes: Set[str] = set()
        self.violations: List[PrivacyViolation] = []

    def scan_training_data(self, sample_id: str, text: str, pii_detector) -> List[PrivacyViolation]:
        """扫描训练数据中的 PII"""
        violations = []
        matches = pii_detector.detect(text)

        for match in matches:
            pii_hash = hashlib.sha256(
                f"{match.category.value}:{match.original}".encode()
            ).hexdigest()

            violation = PrivacyViolation(
                training_sample_id=sample_id,
                leaked_field=match.category.value,
                original_value=match.original,
                detection_method="regex_detection",
                severity="high" if match.category in [
                    PIICategory.ID_CARD, PIICategory.BANK_CARD
                ] else "medium",
            )
            violations.append(violation)
            self.known_pii_hashes.add(pii_hash)

        self.violations.extend(violations)
        return violations

    def check_model_output(self, output: str, pii_detector) -> List[PrivacyViolation]:
        """检查模型输出是否包含训练数据中的 PII"""
        violations = []
        matches = pii_detector.detect(output)

        for match in matches:
            pii_hash = hashlib.sha256(
                f"{match.category.value}:{match.original}".encode()
            ).hexdigest()

            if pii_hash in self.known_pii_hashes:
                violation = PrivacyViolation(
                    training_sample_id="unknown",
                    leaked_field=match.category.value,
                    original_value=match.original,
                    detection_method="training_data_leakage",
                    severity="critical",
                )
                violations.append(violation)

        return violations

    def get_summary(self) -> dict:
        severity_counts = {"low": 0, "medium": 0, "high": 0, "critical": 0}
        for v in self.violations:
            severity_counts[v.severity] += 1

        return {
            "total_violations": len(self.violations),
            "severity_breakdown": severity_counts,
            "unique_pii_count": len(self.known_pii_hashes),
        }


if __name__ == "__main__":
    import json

    detector = PIIDetector()
    checker = TrainingDataPrivacyChecker()

    training_samples = [
        ("train_001", "患者张三，电话13812345678，诊断为高血压"),
        ("train_002", "用户李四，邮箱lisi@test.com，地址北京市朝阳区"),
        ("train_003", "正常医疗知识：高血压是一种常见的慢性病"),
    ]

    print("=== 训练数据隐私扫描 ===")
    for sample_id, text in training_samples:
        violations = checker.scan_training_data(sample_id, text, detector)
        print(f"\n样本 {sample_id}: {len(violations)} 条违规")
        for v in violations:
            print(f"  - [{v.severity}] 字段: {v.leaked_field}")

    print("\n=== 模型输出隐私检查 ===")
    model_outputs = [
        "高血压是一种常见的慢性病，需要长期服药控制。",
        "根据记录，患者张三的电话是13812345678。",  # 泄露了训练数据
    ]

    for output in model_outputs:
        violations = checker.check_model_output(output, detector)
        status = "⚠️ 检测到泄露!" if violations else "✅ 安全"
        print(f"[{status}] {output}")
        if violations:
            for v in violations:
                print(f"  - [{v.severity}] 泄露字段: {v.leaked_field}")

    print(f"\n=== 统计摘要 ===")
    summary = checker.get_summary()
    print(json.dumps(summary, indent=2, ensure_ascii=False))

import numpy as np
from typing import List

class DifferentialPrivacy:
    """差分隐私实现（拉普拉斯机制）"""

    def __init__(self, epsilon: float = 1.0):
        """
        :param epsilon: 隐私预算，越小隐私保护越强，数据可用性越低
        """
        self.epsilon = epsilon
        self.remaining_budget = epsilon

    def add_laplace_noise(self, value: float, sensitivity: float = 1.0) -> float:
        """添加拉普拉斯噪声"""
        scale = sensitivity / self.epsilon
        noise = np.random.laplace(0, scale)
        return value + noise

    def privatize_count(self, count: int) -> int:
        """隐私保护的计数查询"""
        noisy_count = self.add_laplace_noise(float(count), sensitivity=1.0)
        return max(0, int(round(noisy_count)))

    def privatize_mean(self, values: List[float]) -> float:
        """隐私保护的均值查询"""
        if not values:
            return 0.0
        n = len(values)
        sensitivity = (max(values) - min(values)) / n
        noisy_sum = sum(self.add_laplace_noise(v, sensitivity) for v in values)
        return noisy_sum / n

    def consume_budget(self, epsilon_cost: float) -> bool:
        """消耗隐私预算，返回是否还有足够预算"""
        if self.remaining_budget < epsilon_cost:
            return False
        self.remaining_budget -= epsilon_cost
        return True
