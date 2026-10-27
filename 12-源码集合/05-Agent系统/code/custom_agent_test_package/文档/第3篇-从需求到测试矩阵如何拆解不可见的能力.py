from pydantic import BaseModel, Field
from typing import List, Dict, Optional

class TestPoint(BaseModel):
    """能力点（可测试的原子单位）"""
    id: str
    description: str
    input_example: str
    verify_method: str
    success_criteria: str
    dimensions: List[str] = Field(default_factory=list)
    performance_indicator: Optional[str] = None  # 非功能性指标

class CapabilityItem(BaseModel):
    """能力项"""
    name: str
    description: str
    test_points: List[TestPoint] = Field(default_factory=list)

class CapabilityDomain(BaseModel):
    """能力域"""
    name: str
    description: str
    items: List[CapabilityItem] = Field(default_factory=list)
