"""
Orchestrator-Worker multi-agent pattern for LangGraph.

Implements dynamic fan-out task dispatch (Map-Reduce) using the LangGraph Send API:
1. Orchestrator Planner: Analyzes research topic, formulates work plan, and dynamically spawns WorkerTasks.
2. Dynamic Fan-Out Dispatch: Dispatches parallel worker tasks via LangGraph Send.
3. Specialized Workers:
   - internal_research_worker (search_internal_documents_tool)
   - external_research_worker (search_external_sources_tool)
   - analytics_worker (analyze_csv_tool, calculate_cost_tool)
4. Orchestrator Synthesizer: Reduces and aggregates worker outputs into a grounded, cited technical report.
"""

from datetime import datetime, timezone
import json
import os
from typing import Any, Dict, List

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.types import Send

from src.graph.nodes import (
    _clean_json_response,
    draft_report as base_draft_report,
    get_llm,
)
from src.graph.subagents import (
    analytics_agent as base_analytics_agent,
    external_research_agent as base_external_research_agent,
    internal_research_agent as base_internal_research_agent,
)
from src.state import ResearchState, WorkerTask


ORCHESTRATOR_PLAN_PROMPT = """You are the Lead Technical Research Orchestrator.
Your role is to analyze a research topic and dynamically break it down into a coordinated multi-worker execution plan.

Research Topic:
"{topic}"

Available Worker Roles:
1. "internal_research_worker": Queries internal engineering standards, architecture ADRs, and compliance blueprints via Qdrant.
2. "external_research_worker": Searches peer-reviewed whitepapers, industry benchmarks, and live external analyst reports.
3. "analytics_worker": Computes empirical latency percentiles, throughput telemetry, and Total Cost of Ownership (TCO) models.

Generate a structured execution plan with distinct tasks assigned to each worker.
Return STRICTLY a JSON object with this schema:
{{
  "plan_summary": "High-level strategy describing how workers will collaborate.",
  "tasks": [
    {{
      "id": "TASK-INT-01",
      "worker": "internal_research_worker",
      "description": "Specific investigation task for internal guidelines",
      "target_dimension": "architecture",
      "query": "Precise search query for internal Qdrant documentation"
    }},
    {{
      "id": "TASK-EXT-01",
      "worker": "external_research_worker",
      "description": "Specific investigation task for external whitepapers",
      "target_dimension": "external_analyst",
      "query": "Precise search query for external research"
    }},
    {{
      "id": "TASK-ANL-01",
      "worker": "analytics_worker",
      "description": "Specific quantitative analysis task",
      "target_dimension": "empirical_telemetry_and_cost",
      "query": "Benchmark and TCO parameters"
    }}
  ]
}}
Do NOT include markdown fences or commentary outside the JSON object."""


def orchestrator_planner(state: ResearchState) -> Dict[str, Any]:
    """
    Orchestrator Node: Decomposes a research topic into structured worker assignments.
    When LLM is active, uses dynamic planning; otherwise falls back to deterministic tasks.
    """
    topic = state.get("topic", "Comparative Technology Evaluation")

    default_tasks: List[WorkerTask] = [
        {
            "id": "TASK-INT-01",
            "worker": "internal_research_worker",
            "description": f"Retrieve internal enterprise standards, multi-tenant isolation, and ACID guidelines for {topic}.",
            "target_dimension": "architecture",
            "query": f"{topic} architecture guidelines compliance",
        },
        {
            "id": "TASK-EXT-01",
            "worker": "external_research_worker",
            "description": f"Search peer-reviewed external whitepapers and analyst reports for {topic}.",
            "target_dimension": "external_analyst",
            "query": f"{topic} performance benchmark whitepapers",
        },
        {
            "id": "TASK-ANL-01",
            "worker": "analytics_worker",
            "description": f"Execute empirical benchmark telemetry and 12-month cloud TCO calculations for {topic}.",
            "target_dimension": "empirical_telemetry_and_cost",
            "query": f"{topic} telemetry and cloud pricing",
        },
    ]

    plan_summary = f"Orchestrator dispatched 3 parallel worker tasks across architecture, external analyst, and analytics dimensions for {topic}."
    tasks = default_tasks

    llm = get_llm()
    if llm is not None and os.getenv("MOCK_LLM", "false").lower() != "true":
        try:
            prompt = ORCHESTRATOR_PLAN_PROMPT.format(topic=topic)
            response = llm.invoke(
                [
                    SystemMessage(content="You are an autonomous research orchestrator."),
                    HumanMessage(content=prompt),
                ]
            )
            text = str(response.content) if hasattr(response, "content") else str(response)
            cleaned = _clean_json_response(text)
            parsed = json.loads(cleaned)

            if "tasks" in parsed and isinstance(parsed["tasks"], list) and len(parsed["tasks"]) > 0:
                valid_workers = {"internal_research_worker", "external_research_worker", "analytics_worker"}
                validated_tasks: List[WorkerTask] = []
                for idx, t in enumerate(parsed["tasks"], start=1):
                    worker_name = t.get("worker", "external_research_worker")
                    if worker_name not in valid_workers:
                        worker_name = "external_research_worker"
                    validated_tasks.append(
                        WorkerTask(
                            id=t.get("id", f"TASK-{idx:02d}"),
                            worker=worker_name,
                            description=t.get("description", f"Investigation for {topic}"),
                            target_dimension=t.get("target_dimension", "general"),
                            query=t.get("query", topic),
                        )
                    )
                if validated_tasks:
                    tasks = validated_tasks
            if "plan_summary" in parsed:
                plan_summary = parsed["plan_summary"]
        except Exception:
            pass

    log_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "agent": "orchestrator_planner",
        "action": "plan_and_dispatch_workers",
        "worker_tasks_count": len(tasks),
        "plan_summary": plan_summary,
    }

    return {
        "worker_tasks": tasks,
        "orchestrator_plan": plan_summary,
        "subagent_history": [log_entry],
        "status": "orchestrating",
    }


def assign_worker_tasks(state: ResearchState) -> List[Send]:
    """
    Dynamic Fan-Out conditional edge.
    Spawns parallel Send instances for each WorkerTask created by the orchestrator.
    """
    tasks = state.get("worker_tasks", [])
    if not tasks:
        # Fallback to standard 3 tasks
        tasks = [
            {"worker": "internal_research_worker", "query": state.get("topic", "")},
            {"worker": "external_research_worker", "query": state.get("topic", "")},
            {"worker": "analytics_worker", "query": state.get("topic", "")},
        ]

    sends = []
    for task in tasks:
        worker_node = task.get("worker", "external_research_worker")
        task_payload = {
            **state,
            "current_task": task,
        }
        sends.append(Send(worker_node, task_payload))
    return sends


def internal_research_worker(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Worker node for internal engineering guidelines.
    Executes search_internal_documents_tool with autonomous tool calling.
    """
    result = base_internal_research_agent(state)
    task = state.get("current_task", {})
    if result.get("subagent_history"):
        result["subagent_history"][0]["assigned_task"] = task.get("id", "TASK-INT")
    result.pop("status", None)
    return result


def external_research_worker(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Worker node for external analyst whitepapers and web search.
    Executes search_external_sources_tool with autonomous tool calling via Hive AI.
    """
    result = base_external_research_agent(state)
    task = state.get("current_task", {})
    if result.get("subagent_history"):
        result["subagent_history"][0]["assigned_task"] = task.get("id", "TASK-EXT")
    result.pop("status", None)
    return result


def analytics_worker(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Worker node for empirical telemetry and cloud TCO.
    Executes analyze_csv_tool and calculate_cost_tool with autonomous tool calling.
    """
    result = base_analytics_agent(state)
    task = state.get("current_task", {})
    if result.get("subagent_history"):
        result["subagent_history"][0]["assigned_task"] = task.get("id", "TASK-ANL")
    result.pop("status", None)
    return result


def orchestrator_synthesizer(state: ResearchState) -> Dict[str, Any]:
    """
    Reducer / Synthesizer Node:
    Aggregates parallel worker evidence, validates multidimensional coverage,
    and synthesizes the unified cited technical research report.
    """
    draft_result = base_draft_report(state)

    log_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "agent": "orchestrator_synthesizer",
        "action": "synthesize_worker_outputs",
        "total_evidence_aggregated": len(state.get("evidence", [])),
        "calculations_available": list(state.get("calculations", {}).keys()),
        "sections_synthesized": list(draft_result.get("draft_report", {}).get("sections", {}).keys()),
    }

    draft_result["subagent_history"] = [log_entry]
    draft_result["status"] = "drafted"
    return draft_result
