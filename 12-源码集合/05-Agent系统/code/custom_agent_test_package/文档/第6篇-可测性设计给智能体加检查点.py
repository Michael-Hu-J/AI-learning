class CustomAgent:
    def get_state(self) -> Dict:
        """
        获取智能体当前状态

        Returns:
            {
                "current_phase": "executing",
                "completed_subtasks": ["task_1", "task_2"],
                "failed_subtasks": ["task_3"],
                "skipped_subtasks": ["task_4"],
                "pending_subtasks": ["task_5"],
                "memory": {"key": "value"},
                "token_count": 1234,
                "llm_calls": 5,
                "elapsed": 12.3,
                "replan_count": 1,
            }
        """
        if not hasattr(self, 'state') or not self.state:
            return {"current_phase": "idle"}

        plan = self.state.plan
        return {
            "current_phase": self.state.current_phase,
            "completed_subtasks": [s.id for s in plan.subtasks if s.status == "success"],
            "failed_subtasks": [s.id for s in plan.subtasks if s.status == "failed"],
            "skipped_subtasks": [s.id for s in plan.subtasks if s.status == "skipped"],
            "pending_subtasks": [s.id for s in plan.subtasks if s.status == "pending"],
            "memory": self.state.memory.copy(),
            "token_count": self.state.total_tokens,
            "llm_calls": self.state.total_llm_calls,
            "elapsed": time.time() - self.state.start_time,
            "replan_count": self.state.replan_count,
        }

class StructuredLogger:
    """结构化日志处理器"""

    def __init__(self, log_file: str = None, trace_id: str = None):
        self.trace_id = trace_id or f"trace_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.log_file = log_file
        self.entries = []
        # ... 文件 handler 初始化 ...

    def log(self, phase: str, level: str, message: str, data: Dict = None):
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "trace_id": self.trace_id,
            "phase": phase,
            "level": level,
            "message": message,
            "data": data or {},
        }
        self.entries.append(entry)
        if self.log_file:
            self.logger.info(json.dumps(entry, ensure_ascii=False))

    def get_entries(self, phase: str = None, level: str = None) -> List[Dict]:
        """获取日志条目（支持按阶段/级别过滤）"""
        result = self.entries
        if phase:
            result = [e for e in result if e["phase"] == phase]
        if level:
            result = [e for e in result if e["level"] == level]
        return result

class CheckpointManager:
  CHECKPOINTS = {
      "CP-01": "规划完成", "CP-02": "子任务开始", "CP-03": "子任务完成",
      "CP-04": "反思完成", "CP-05": "重规划",   "CP-06": "总结完成",
  }

  def record(self, checkpoint_id: str, data: Dict = None):
      """到达检查点时调用，记录 ID + 附加数据"""
      entry = {
          "timestamp": datetime.now(timezone.utc).isoformat(),
          "checkpoint_id": checkpoint_id,
          "checkpoint_name": self.CHECKPOINTS[checkpoint_id],
          "data": data or {},
      }
      self.checkpoints.append(entry)

  def verify(self, expected: List[str]) -> Dict:
      """验证实际经过的检查点是否包含期望列表"""
      actual_ids = [cp["checkpoint_id"] for cp in self.checkpoints]
      missing = set(expected) - set(actual_ids)
      return {"passed": len(missing) == 0, "missing": list(missing), "actual": actual_ids}

class EcommerceAssertionValidator:
    """电商数据分析断言验证器"""

    def assert_sales_positive(self, sales_data: Dict) -> AssertionResult:
        """断言：销售额 > 0"""
        sales = sales_data.get("销售额", 0)
        passed = isinstance(sales, (int, float)) and sales > 0
        return AssertionResult(name="销售额为正数", passed=passed,
                               actual_value=sales, expected_range="> 0", severity="ERROR")

    def assert_avg_order_reasonable(self, sales_data: Dict,
                                    min_val=10, max_val=10000) -> AssertionResult:
        """断言：客单价在合理范围"""
        avg_price = sales_data.get("客单价", 0)
        passed = min_val <= avg_price <= max_val
        return AssertionResult(name="客单价合理性", passed=passed,
                               actual_value=avg_price,
                               expected_range=f"{min_val} ~ {max_val}", severity="WARN")

    def assert_report_contains_gmv(self, report: str) -> AssertionResult:
        """断言：报告包含 GMV 指标"""
        passed = "GMV" in report or "商品交易总额" in report
        return AssertionResult(name="报告包含GMV指标", passed=passed, severity="ERROR")

    def assert_no_sensitive_info(self, report: str) -> AssertionResult:
        """断言：报告不包含手机号、身份证等敏感信息"""
        # 正则匹配手机号 / 身份证 ...
        passed = not has_phone and not has_id
        return AssertionResult(name="报告无敏感信息", passed=passed, severity="ERROR")

    def run_all(self, sales_data: Dict, report: str) -> Dict:
        """依次运行全部断言，汇总 ERROR / WARN"""
        # assert_field_exists / assert_sales_positive / ... 依次调用
        return {"passed": len(errors) == 0, "errors": len(errors), "details": [...]}

def enhance_agent_with_observability(agent):
    """给已有 Agent 挂上日志 + 检查点 + get_state，不改原有业务逻辑"""
    agent.structured_logger = StructuredLogger()
    agent.checkpoint_manager = CheckpointManager()
    agent.get_state = lambda: {
        "current_phase": agent.state.current_phase,
        "completed_subtasks": [...],
        "checkpoints": agent.checkpoint_manager.get_checkpoints(),
        # ... token_count / elapsed 等
    }
    return agent

# 使用方式
agent = enhance_agent_with_observability(CustomAgent(temperature=0.3))
result = agent.run("生成6月销售报告，查询销售额、订单量、客单价，计算GMV")
state = agent.get_state()                          # 查当前进度
logs = agent.structured_logger.get_entries()       # 查结构化日志
cp_ok = agent.checkpoint_manager.verify(["CP-01", "CP-03", "CP-06"])  # 验证检查点

def get_state() -> Dict:
    """
    返回智能体当前状态

    字段说明：
    - current_phase: 当前阶段
    - completed_subtasks: 已完成的子任务 ID 列表
    - failed_subtasks: 失败的子任务 ID 列表
    - skipped_subtasks: 跳过的子任务 ID 列表
    - pending_subtasks: 待执行的子任务 ID 列表
    - memory: 记忆字典
    - token_count: 累计 Token 消耗
    - llm_calls: 累计 LLM 调用次数
    - elapsed: 累计耗时（秒）
    - replan_count: 重新规划次数
    - checkpoints: 检查点记录列表
    """
