#!/usr/bin/env python3
"""
Task Planning Quality Scoring

Scoring dimensions:
1. Task count reasonableness (20 points)
2. Dependency accuracy (30 points)
3. Tool selection correctness (25 points)
4. Execution completion rate (25 points)

Additional features:
- Dependency graph validation (cycle detection, isolated task detection)
- Duplicate task detection
- Failure mode identification
"""

from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import difflib


@dataclass
class PlanningScore:
    """Planning scoring result"""
    total: float
    task_count_score: float
    dependency_score: float
    tool_selection_score: float
    completion_score: float
    details: Dict
    failure_modes: List[str]


VALID_TOOLS = {
    "calculator", "code_executor", "memory_store",
    "web_fetch", "safety_checker", "none", "search",
}


def calculate_similarity(str1: str, str2: str) -> float:
    """
    Calculate similarity between two strings
    
    Args:
        str1: String 1
        str2: String 2
        
    Returns:
        Similarity (0-1)
    """
    return difflib.SequenceMatcher(None, str1, str2).ratio()


def detect_duplicate_tasks(subtasks: List[Dict]) -> List[Tuple[int, int]]:
    """
    Detect duplicate subtasks
    
    Args:
        subtasks: List of subtasks
        
    Returns:
        List of index pairs for duplicate tasks
    """
    duplicates = []
    for i in range(len(subtasks)):
        for j in range(i + 1, len(subtasks)):
            desc1 = subtasks[i].get("description", "")
            desc2 = subtasks[j].get("description", "")
            similarity = calculate_similarity(desc1, desc2)
            
            # If description similarity is greater than threshold, consider it duplicate
            if similarity > 0.8:
                # Also check if tools and parameters are the same
                tool1 = subtasks[i].get("tool", "")
                tool2 = subtasks[j].get("tool", "")
                
                # For the same tool, compare parameters to avoid semantic duplication
                if tool1 == tool2:
                    # Additional check: compare parameters if available
                    params1 = subtasks[i].get("params", {})
                    params2 = subtasks[j].get("params", {})
                    
                    # If parameters are also the same, it's likely a true duplicate
                    if params1 == params2:
                        duplicates.append((i, j))
    
    return duplicates


def score_task_planning(result: Dict, expected: Dict = None) -> PlanningScore:
    """
    Score task planning

    Args:
        result: Agent execution result (with _meta)
        expected: Expected planning (optional, for comparison)

    Returns:
        PlanningScore
    """
    meta = result.get("_meta", {})
    subtasks = meta.get("subtasks", [])
    details = {}
    failure_modes = []

    # ========== Dimension 1: Task count reasonableness (20 points) ==========
    n = len(subtasks)
    
    # Determine reasonable range based on task complexity
    # Here we assume we can determine complexity through certain features, adjust according to specific scenarios in practice
    if n == 0:
        task_count_score = 0.0
        details["task_count"] = "0 (no planning)"
        failure_modes.append("Too few subtasks")
    elif n == 1:
        task_count_score = 15.0
        details["task_count"] = f"{n} (reasonable for simple task)"
    elif n == 2:
        task_count_score = 17.0
        details["task_count"] = f"{n} (reasonable for simple task)"
    elif 3 <= n <= 6:
        task_count_score = 20.0
        details["task_count"] = f"{n} (reasonable for medium task)"
    elif 7 <= n <= 10:
        task_count_score = 20.0
        details["task_count"] = f"{n} (reasonable for complex task)"
    elif n <= 15:
        task_count_score = max(0, 20 - (n - 10) * 2)
        details["task_count"] = f"{n} (too fine)"
    else:
        task_count_score = max(0, 20 - (n - 10) * 3)
        details["task_count"] = f"{n} (too fine)"
        failure_modes.append("Excessive subtask count")

    # ========== Dimension 2: Dependency accuracy (30 points) ==========
    task_ids = {s["id"] for s in subtasks}
    deps_correct = 0
    deps_total = 0
    redundant_deps = 0  # Count of redundant dependencies
    dep_errors = []

    for s in subtasks:
        for dep in s.get("depends_on", []):
            deps_total += 1
            if dep in task_ids:
                deps_correct += 1
            else:
                dep_errors.append(f"{s['id']} depends on non-existent {dep}")

    # Cycle detection
    has_cycle = detect_cycle(subtasks)
    if has_cycle:
        failure_modes.append("Dependency cycle")
        dep_errors.append("Cycle detected")

    # Isolated task detection
    isolated = detect_isolated_tasks(subtasks)
    if isolated:
        failure_modes.append(f"Isolated tasks: {', '.join(isolated)}")

    # Redundant dependency detection (over-dependence)
    for s in subtasks:
        if len(s.get("depends_on", [])) > 0 and len(task_ids) > 3:
            # If most tasks depend on the same task, it might be over-dependence
            all_deps = []
            for t in subtasks:
                all_deps.extend(t.get("depends_on", []))
            from collections import Counter
            dep_counts = Counter(all_deps)
            if dep_counts and max(dep_counts.values()) > len(subtasks) * 0.7:
                redundant_deps += 1
                failure_modes.append("Over-dependence")

    if deps_total > 0:
        dependency_score = (deps_correct / deps_total) * 30.0
        # Deduct penalty for redundant dependencies
        dependency_score = max(0, dependency_score - (redundant_deps * 2))
        details["dependency"] = f"{deps_correct}/{deps_total} correct, {redundant_deps} redundant"
    else:
        dependency_score = 30.0
        details["dependency"] = "No dependencies"

    if dep_errors:
        details["dep_errors"] = dep_errors

    # ========== Dimension 3: Tool selection correctness (25 points) ==========
    tools_correct = 0
    tools_total = 0
    tool_errors = []

    for s in subtasks:
        tool = s.get("tool", "")
        if tool and tool != "none":  # "none" is not counted in statistics
            tools_total += 1
            if tool in VALID_TOOLS:
                tools_correct += 1
            else:
                tool_errors.append(f"{s['id']} uses unknown tool '{tool}'")
                failure_modes.append("Wrong tool selection")

    if tools_total > 0:
        tool_selection_score = (tools_correct / tools_total) * 25.0
        details["tool_selection"] = f"{tools_correct}/{tools_total} correct"
    else:
        tool_selection_score = 25.0
        details["tool_selection"] = "No tool calls"

    if tool_errors:
        details["tool_errors"] = tool_errors

    # ========== Dimension 4: Execution completion and failure attribution (25 points) ==========
    success_count = meta.get("subtasks_success", 0)
    total_count = meta.get("subtasks_total", len(subtasks))
    
    # Detect duplicate tasks and calculate penalty
    duplicate_pairs = detect_duplicate_tasks(subtasks)
    duplicate_penalty = len(duplicate_pairs) * 3  # Deduct 3 points per duplicate pair

    if total_count > 0:
        completion_rate = success_count / total_count
        completion_score = completion_rate * 25.0
        # Deduct duplicate task penalty
        completion_score = max(0, completion_score - duplicate_penalty)
        
        details["completion"] = f"{success_count}/{total_count} ({completion_rate:.0%})"
        details["duplicate_penalty"] = f"Duplicate task penalty: {duplicate_penalty} points"
    else:
        completion_score = 0.0
        details["completion"] = "No subtasks"

    # ========== Total score ==========
    total = task_count_score + dependency_score + tool_selection_score + completion_score
    total = min(total, 100.0)

    # Detect duplicate tasks
    if duplicate_pairs:
        failure_modes.append(f"Duplicate tasks: {len(duplicate_pairs)} pairs")
        
    # Detect pseudo planning (too many retry/fallback steps)
    retry_tasks = [s for s in subtasks if "retry" in s.get("description", "").lower() or 
                   "fallback" in s.get("description", "").lower() or 
                   "rephrase" in s.get("description", "").lower()]
    
    # Calculate core task advancement ratio
    core_tasks = [s for s in subtasks if not ("retry" in s.get("description", "").lower() or 
                                             "fallback" in s.get("description", "").lower() or 
                                             "rephrase" in s.get("description", "").lower())]
    
    if len(subtasks) > 0:
        core_ratio = len(core_tasks) / len(subtasks)
        if core_ratio < 0.3:  # Less than 30% are core tasks
            failure_modes.append("Pseudo planning")
        elif len(retry_tasks) > len(subtasks) * 0.5:  # More than 50% are retry steps (conservative planning)
            failure_modes.append("Conservative planning")

    # Deduplicate failure modes
    failure_modes = list(set(failure_modes))

    return PlanningScore(
        total=total,
        task_count_score=task_count_score,
        dependency_score=dependency_score,
        tool_selection_score=tool_selection_score,
        completion_score=completion_score,
        details=details,
        failure_modes=failure_modes,
    )


def detect_cycle(subtasks: List[Dict]) -> bool:
    """
    Detect dependency cycles

    Args:
        subtasks: List of subtasks

    Returns:
        Whether there is a cycle
    """
    task_map = {s["id"]: s for s in subtasks}
    visited = set()
    rec_stack = set()

    def dfs(task_id):
        visited.add(task_id)
        rec_stack.add(task_id)

        task = task_map.get(task_id)
        if task:
            for dep in task.get("depends_on", []):
                if dep not in visited:
                    if dfs(dep):
                        return True
                elif dep in rec_stack:
                    return True

        rec_stack.discard(task_id)
        return False

    for s in subtasks:
        if s["id"] not in visited:
            if dfs(s["id"]):
                return True

    return False


def detect_isolated_tasks(subtasks: List[Dict]) -> List[str]:
    """
    Detect isolated tasks (no dependencies and no dependents)

    Args:
        subtasks: List of subtasks

    Returns:
        List of isolated task IDs
    """
    task_ids = {s["id"] for s in subtasks}
    depended_on = set()

    for s in subtasks:
        for dep in s.get("depends_on", []):
            depended_on.add(dep)

    isolated = []
    for s in subtasks:
        if not s.get("depends_on") and s["id"] not in depended_on:
            isolated.append(s["id"])

    return isolated


def print_score_report(score: PlanningScore):
    """Print scoring report"""
    print(f'''
{'='*60}
Planning Quality Scoring Report
{'='*60}
''')

    # Score bar
    def bar(value, max_value=100):
        filled = int(value / max_value * 20)
        return "█" * filled + "░" * (20 - filled)

    print(f'''
  Task count: {score.task_count_score:5.1f}/20  {bar(score.task_count_score, 20)}
  Dependency: {score.dependency_score:5.1f}/30  {bar(score.dependency_score, 30)}
  Tool selection:   {score.tool_selection_score:5.1f}/25  {bar(score.tool_selection_score, 25)}
  Execution:   {score.completion_score:5.1f}/25  {bar(score.completion_score, 25)}
  {'─'*40}
  Total:       {score.total:5.1f}/100  {bar(score.total)}

''')

    # Rating
    if score.total >= 80:
        grade = "Excellent"
    elif score.total >= 60:
        grade = "Qualified"
    else:
        grade = "Unqualified"
    print(f"  Rating: {grade}")

    # Details
    print(f'''
  Details:
''')
    for key, value in score.details.items():
        print(f"    {key}: {value}")

    # Failure modes
    if score.failure_modes:
        print(f'''
  ⚠  Failure modes: {', '.join(score.failure_modes)}
''')

    print(f"{'='*60}")


def run_demo():
    """Demo"""
    print("=" * 60)
    print("Task Planning Quality Scoring Demo")
    print("=" * 60)

    # Test case 1: Excellent planning
    result_good = {
        "success": True,
        "output": "Result is 120, stored",
        "_meta": {
            "subtasks_total": 3,
            "subtasks_success": 3,
            "subtasks_failed": 0,
            "subtasks": [
                {"id": "task_1", "description": "Calculate", "tool": "calculator", "status": "success", "depends_on": [], "retry_count": 0},
                {"id": "task_2", "description": "Store", "tool": "memory_store", "status": "success", "depends_on": ["task_1"], "retry_count": 0},
                {"id": "task_3", "description": "Confirm", "tool": "none", "status": "success", "depends_on": ["task_2"], "retry_count": 0},
            ],
        },
    }

    # Test case 2: Problematic planning
    result_bad = {
        "success": True,
        "output": "Execution completed",
        "_meta": {
            "subtasks_total": 12,
            "subtasks_success": 8,
            "subtasks_failed": 4,
            "subtasks": [
                {"id": "task_1", "description": "Calculate", "tool": "calculator", "status": "success", "depends_on": [], "retry_count": 0},
                {"id": "task_2", "description": "Calculate (duplicate)", "tool": "calculator", "status": "success", "depends_on": [], "retry_count": 0},
                {"id": "task_3", "description": "Store", "tool": "memory_store", "status": "success", "depends_on": ["task_1"], "retry_count": 0},
                {"id": "task_4", "description": "Unknown tool", "tool": "web_search", "status": "failed", "depends_on": ["task_99"], "retry_count": 3},
                {"id": "task_5", "description": "Calculate (again duplicate)", "tool": "calculator", "status": "success", "depends_on": [], "retry_count": 0},
                {"id": "task_6", "description": "Store (duplicate)", "tool": "memory_store", "status": "success", "depends_on": ["task_3"], "retry_count": 0},
                {"id": "task_7", "description": "Calculate (another duplicate)", "tool": "calculator", "status": "success", "depends_on": [], "retry_count": 0},
                {"id": "task_8", "description": "Confirm", "tool": "none", "status": "success", "depends_on": ["task_3"], "retry_count": 0},
                {"id": "task_9", "description": "Isolated task", "tool": "none", "status": "pending", "depends_on": [], "retry_count": 0},
                {"id": "task_10", "description": "Calculate (5th time)", "tool": "calculator", "status": "success", "depends_on": [], "retry_count": 0},
                {"id": "task_11", "description": "Store (3rd time)", "tool": "memory_store", "status": "success", "depends_on": ["task_3"], "retry_count": 0},
                {"id": "task_12", "description": "Confirm (duplicate)", "tool": "none", "status": "success", "depends_on": ["task_8"], "retry_count": 0},
            ],
        },
    }

    # Test case 3: Pseudo planning
    result_pseudo = {
        "success": True,
        "output": "Execution completed",
        "_meta": {
            "subtasks_total": 8,
            "subtasks_success": 5,
            "subtasks_failed": 3,
            "subtasks": [
                {"id": "task_1", "description": "Main task", "tool": "calculator", "status": "failed", "depends_on": [], "retry_count": 0},
                {"id": "task_2", "description": "Retry main task", "tool": "calculator", "status": "failed", "depends_on": ["task_1"], "retry_count": 0},
                {"id": "task_3", "description": "Retry again", "tool": "calculator", "status": "failed", "depends_on": ["task_2"], "retry_count": 0},
                {"id": "task_4", "description": "Fallback solution", "tool": "code_executor", "status": "success", "depends_on": ["task_3"], "retry_count": 0},
                {"id": "task_5", "description": "Verify result", "tool": "none", "status": "success", "depends_on": ["task_4"], "retry_count": 0},
                {"id": "task_6", "description": "Retry previously failed", "tool": "calculator", "status": "success", "depends_on": ["task_5"], "retry_count": 0},
                {"id": "task_7", "description": "Rephrase and retry", "tool": "none", "status": "failed", "depends_on": ["task_6"], "retry_count": 0},
                {"id": "task_8", "description": "Final confirmation", "tool": "none", "status": "success", "depends_on": ["task_7"], "retry_count": 0},
            ],
        },
    }

    # Test case 4: Planning parse failure (edge case)
    result_failure = {
        "success": False,
        "output": "Failed to parse planning",
        "_meta": {
            "subtasks_total": 0,
            "subtasks_success": 0,
            "subtasks_failed": 0,
            "subtasks": [],
        },
    }

    print("\n--- Test case 1: Excellent planning ---")
    score1 = score_task_planning(result_good)
    print_score_report(score1)

    print("\n--- Test case 2: Problematic planning ---")
    score2 = score_task_planning(result_bad)
    print_score_report(score2)

    print("\n--- Test case 3: Pseudo planning ---")
    score3 = score_task_planning(result_pseudo)
    print_score_report(score3)

    print("\n--- Test case 4: Planning parse failure ---")
    score4 = score_task_planning(result_failure)
    print_score_report(score4)

    # Comparison
    print("=" * 60)
    print("Comparison Summary")
    print("=" * 60)
    print(f'{"Metric":20s} {"Excellent":>10s} {"Problematic":>10s} {"Pseudo":>10s} {"Parse Fail":>10s}')
    print("-" * 60)
    print(f'{"Total score":20s} {score1.total:10.1f} {score2.total:10.1f} {score3.total:10.1f} {score4.total:10.1f}')
    print(f'{"Task count":20s} {score1.details["task_count"]:>10s} {score2.details["task_count"]:>10s} {score3.details["task_count"]:>10s} {score4.details["task_count"]:>10s}')
    print(f'{"Dependency":20s} {score1.details["dependency"]:>10s} {score2.details["dependency"]:>10s} {score3.details["dependency"]:>10s} {score4.details["dependency"]:>10s}')
    print(f'{"Tool selection":20s} {score1.details["tool_selection"]:>10s} {score2.details["tool_selection"]:>10s} {score3.details["tool_selection"]:>10s} {score4.details["tool_selection"]:>10s}')
    print(f'{"Execution":20s} {score1.details["completion"]:>10s} {score2.details["completion"]:>10s} {score3.details["completion"]:>10s} {score4.details["completion"]:>10s}')
    print(f'{"Failure modes":20s} {len(score1.failure_modes):10d} {len(score2.failure_modes):10d} {len(score3.failure_modes):10d} {len(score4.failure_modes):10d}')
    print("=" * 60)


if __name__ == "__main__":
    run_demo()
