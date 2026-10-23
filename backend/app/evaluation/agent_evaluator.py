"""
Agent Evaluator measuring multi-agent performance:
- Task Success Rate: Proportion of runs reaching successful completion.
- Planning Accuracy: Precision & recall of the Planner Agent's subtask breakdown.
- Tool Selection Accuracy: Correct tool selection rate matching intent requirements.
- Execution Success: Success rate across attempted tool calls and action proposals.
- Failure Rate: 1.0 - Task Success Rate.
"""

from typing import Dict, Any, List, Optional

class AgentEvaluator:
    """Evaluates Multi-Agent Orchestrator performance against operational benchmarks."""

    @staticmethod
    def evaluate_planning_accuracy(
        actual_steps: List[str],
        expected_steps: List[str]
    ) -> float:
        """
        Planning Accuracy: Evaluates whether the generated plan decomposed the user request
        into all required operational stages (intent understanding, retrieval, analysis, planning, actions).
        """
        if not expected_steps:
            return 1.0

        if not actual_steps:
            return 0.0

        actual_text = " ".join(actual_steps).lower()
        matched = 0

        for step in expected_steps:
            # Check for direct or partial match
            step_clean = step.replace("_", " ").lower()
            tokens = [t for t in step_clean.split() if len(t) > 3]
            if step_clean in actual_text or (tokens and any(t in actual_text for t in tokens)):
                matched += 1

        accuracy = matched / len(expected_steps)
        return round(min(1.0, accuracy), 3)

    @staticmethod
    def evaluate_tool_selection_accuracy(
        actual_tools_used: List[str],
        expected_tools: List[str]
    ) -> float:
        """
        Tool Selection Accuracy: Measures precision and recall of tool invocation.
        Checks if the agent invoked the necessary tools (calendar, documents, tasks, memory)
        without gratuitous or incorrect tool selection.
        """
        if not expected_tools:
            return 1.0 if not actual_tools_used else 0.8

        if not actual_tools_used:
            return 0.0

        actual_set = {t.lower() for t in actual_tools_used}
        expected_set = {t.lower() for t in expected_tools}

        # Intersect expected tools with actual tools
        intersection = actual_set.intersection(expected_set)
        recall = len(intersection) / len(expected_set)

        # Precision penalizes irrelevant tool calls
        precision = len(intersection) / len(actual_set)

        # F1 harmonic mean for balanced tool evaluation
        if precision + recall == 0:
            return 0.0

        f1 = (2 * precision * recall) / (precision + recall)
        return round(f1, 3)

    @staticmethod
    def evaluate_execution_success(
        tool_results: List[Dict[str, Any]]
    ) -> float:
        """
        Execution Success Rate: Proportion of attempted tool executions or action proposals
        that succeeded without unhandled runtime exceptions.
        """
        if not tool_results:
            return 1.0

        successes = 0
        for tr in tool_results:
            status = tr.get("status", "success")
            has_error = bool(tr.get("error") or tr.get("is_error"))
            if status in ["success", "pending_confirmation"] and not has_error:
                successes += 1

        return round(successes / len(tool_results), 3)

    @staticmethod
    def evaluate_run(
        actual_output: Dict[str, Any],
        benchmark_case: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Evaluates a complete single agent execution against a benchmark case.
        """
        actual_steps = actual_output.get("planning_steps", [])
        actual_tools = actual_output.get("tools_used", [])
        tool_results = actual_output.get("tool_results", [])
        is_success = bool(actual_output.get("success", False))

        planning_acc = AgentEvaluator.evaluate_planning_accuracy(
            actual_steps=actual_steps,
            expected_steps=benchmark_case.get("expected_planning_steps", [])
        )
        tool_acc = AgentEvaluator.evaluate_tool_selection_accuracy(
            actual_tools_used=actual_tools,
            expected_tools=benchmark_case.get("expected_tools", [])
        )
        exec_success = AgentEvaluator.evaluate_execution_success(
            tool_results=tool_results
        )

        expected_success = benchmark_case.get("expected_success", True)
        task_success = 1.0 if is_success == expected_success else 0.0

        return {
            "case_id": benchmark_case.get("id"),
            "task_name": benchmark_case.get("task_name"),
            "task_success": task_success,
            "planning_accuracy": planning_acc,
            "tool_selection_accuracy": tool_acc,
            "execution_success": exec_success,
            "failure_rate": round(1.0 - task_success, 3),
            "tools_used": actual_tools,
            "step_count": len(actual_steps)
        }

agent_evaluator = AgentEvaluator()
