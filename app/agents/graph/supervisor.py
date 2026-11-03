"""
Supervisor Agent for coordinating and monitoring specialized research sub-agents implementing OOP patterns.

Implements the multi-agent supervisor pattern in LangGraph:
- Continuously inspects research state, evidence manifest, and gap analysis.
- Dynamically assigns tasks to specialized worker sub-agents:
  * internal_research_agent
  * external_research_agent
  * analytics_agent
  * drafting_agent
- Verifies comprehensive coverage across architecture, empirical benchmarks, and TCO.
- Routes to human_review when all evidence is validated and drafted.
"""

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List

from langchain_core.messages import HumanMessage

from app.agents.graph.nodes import _clean_json_response, get_llm
from app.agents.graph.prompts import SUPERVISOR_PROMPT
from app.agents.graph.state import ResearchState
from app.config.env_config import MAX_RESEARCH_ITERATIONS


class SupervisorCoordinator:
    """Object-oriented coordinator implementing multi-agent supervisor routing, monitoring, and guardrails."""

    def __init__(self, max_iterations: int = MAX_RESEARCH_ITERATIONS):
        self.max_iterations = max_iterations

    @staticmethod
    def evaluate_manifest(evidence_list: List[Dict[str, Any]]) -> Dict[str, int]:
        """Calculate counts of each evidence category in the manifest."""
        counts = {
            "internal": 0,
            "external": 0,
            "csv": 0,
            "cost": 0,
        }
        for item in evidence_list:
            if not isinstance(item, dict):
                continue
            stype = item.get("source_type", "")
            sid = item.get("source_id", "")
            if stype == "internal_qdrant" or sid.startswith("QDR"):
                counts["internal"] += 1
            elif stype == "external_mock" or sid.startswith("EXT"):
                counts["external"] += 1
            elif stype == "tabular_csv" or sid.startswith("CSV"):
                counts["csv"] += 1
            elif stype == "cost_calculation" or sid.startswith("COST"):
                counts["cost"] += 1
        return counts

    def determine_next_agent_deterministic(
        self, state: ResearchState
    ) -> Dict[str, Any]:
        """
        Deterministic rule-based supervisor routing logic.
        Provides reliable, zero-hallucination monitoring and fallback for offline/test modes.
        """
        evidence = state.get("evidence", [])
        manifest = self.evaluate_manifest(evidence)
        iteration = state.get("iteration_count", 0)
        draft = state.get("draft_report")
        feedback = state.get("human_feedback")

        # If in revision cycle
        if feedback and feedback.get("decision") == "revise":
            target_sections = feedback.get("target_sections", [])
            if any(
                "TCO" in sec or "Cost" in sec or "Benchmark" in sec
                for sec in target_sections
            ):
                return {
                    "next_agent": "analytics_agent",
                    "reasoning": "Human reviewer requested revision targeting financial TCO or empirical performance benchmarks. Routing to analytics_agent.",
                    "is_sufficient": True,
                }
            return {
                "next_agent": "drafting_agent",
                "reasoning": "Human reviewer requested text revisions. Routing directly to drafting_agent for surgical refinement.",
                "is_sufficient": True,
            }

        history = state.get("subagent_history", [])
        internal_attempted = any(
            h.get("agent") == "internal_research_agent"
            or h.get("action") == "search_internal_documents"
            for h in history
        )

        # Step 1: Internal standards retrieval
        if manifest["internal"] == 0 and not internal_attempted:
            return {
                "next_agent": "internal_research_agent",
                "reasoning": "Internal architecture guidelines and isolation standards missing. Assigning internal_research_agent.",
                "is_sufficient": False,
            }

        # Step 2: External whitepapers retrieval
        if manifest["external"] == 0:
            return {
                "next_agent": "external_research_agent",
                "reasoning": "Peer-reviewed external whitepapers missing. Assigning external_research_agent.",
                "is_sufficient": False,
            }

        # Step 3: Empirical telemetry & cloud cost analytics
        if manifest["csv"] == 0 or manifest["cost"] == 0:
            return {
                "next_agent": "analytics_agent",
                "reasoning": "Empirical runtime benchmark statistics or 12-month cloud TCO calculations missing. Assigning analytics_agent.",
                "is_sufficient": False,
            }

        # Step 4: Iterative sufficiency evaluation
        is_fully_covered = (
            manifest["external"] >= 1 and manifest["csv"] >= 1 and manifest["cost"] >= 1
        )
        if not is_fully_covered and iteration < self.max_iterations:
            return {
                "next_agent": "external_research_agent",
                "reasoning": f"Evidence manifest has gaps (iteration {iteration}/{self.max_iterations}). Routing for additional research.",
                "is_sufficient": False,
                "missing_gaps": [
                    "concurrency stress scaling",
                    "reserved instance economics",
                ],
            }

        # Step 5: Drafting final publication
        if not draft:
            return {
                "next_agent": "drafting_agent",
                "reasoning": "Multi-dimensional evidence verified. Routing to drafting_agent to synthesize cited technical proposal.",
                "is_sufficient": True,
            }

        # Step 6: Complete
        return {
            "next_agent": "human_review",
            "reasoning": "Draft proposal validated with full grounded citations and empirical calculations. Pausing for human review approval.",
            "is_sufficient": True,
        }

    def execute_supervisor(self, state: ResearchState) -> Dict[str, Any]:
        """
        Supervisor Agent node function.
        Inspects multi-agent research progress, evaluates grounded evidence sufficiency,
        and assigns next steps to worker sub-agents or final human review.
        """
        topic = state.get("topic", "Comparative Technology Evaluation")
        subquestions = state.get("subquestions", [])
        evidence = state.get("evidence", [])
        iteration = state.get("iteration_count", 0)
        missing_gaps = state.get("missing_gaps", [])
        draft = state.get("draft_report")

        manifest = self.evaluate_manifest(evidence)
        total_evidence = len(evidence)

        decision = self.determine_next_agent_deterministic(state)

        llm = get_llm()
        if llm is not None and os.getenv("MOCK_LLM", "false").lower() != "true":
            try:
                prompt = SUPERVISOR_PROMPT.format(
                    topic=topic,
                    subquestions="\n".join(f"- {sq}" for sq in subquestions),
                    total_evidence=total_evidence,
                    internal_count=manifest["internal"],
                    external_count=manifest["external"],
                    csv_count=manifest["csv"],
                    cost_count=manifest["cost"],
                    iteration_count=iteration,
                    missing_gaps=", ".join(missing_gaps) if missing_gaps else "None",
                    draft_status="Drafted" if draft else "Pending",
                )
                response = llm.invoke([HumanMessage(content=prompt)])
                text = (
                    str(response.content)
                    if hasattr(response, "content")
                    else str(response)
                )
                cleaned = _clean_json_response(text)
                parsed = json.loads(cleaned)

                valid_agents = {
                    "internal_research_agent",
                    "external_research_agent",
                    "analytics_agent",
                    "drafting_agent",
                    "human_review",
                }
                if parsed.get("next_agent") in valid_agents:
                    decision["next_agent"] = parsed["next_agent"]
                    decision["reasoning"] = parsed.get(
                        "reasoning", decision["reasoning"]
                    )
                    if "is_sufficient" in parsed:
                        decision["is_sufficient"] = bool(parsed["is_sufficient"])
                    if "identified_gaps" in parsed and isinstance(
                        parsed["identified_gaps"], list
                    ):
                        decision["missing_gaps"] = parsed["identified_gaps"]
            except Exception:
                pass

        next_agent = decision["next_agent"]
        reasoning = decision["reasoning"]
        is_sufficient = decision.get("is_sufficient", False)
        updated_gaps = decision.get("missing_gaps", [])

        supervisor_log = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent": "supervisor_agent",
            "action": "supervise_and_route",
            "decision": {
                "dispatched_subagent": next_agent,
                "reasoning": reasoning,
                "evidence_manifest": manifest,
                "is_sufficient": is_sufficient,
            },
        }

        return {
            "next_agent": next_agent,
            "supervisor_notes": reasoning,
            "is_sufficient": is_sufficient,
            "missing_gaps": updated_gaps,
            "subagent_history": [supervisor_log],
            "status": "supervising",
        }

    @staticmethod
    def route(state: ResearchState) -> str:
        """Conditional edge router for Supervisor Agent."""
        return state.get("next_agent", "human_review")


# Default singleton instance
default_supervisor_coordinator = SupervisorCoordinator()

# Backwards compatibility function aliases
evaluate_evidence_manifest = SupervisorCoordinator.evaluate_manifest
determine_next_agent_deterministic = (
    default_supervisor_coordinator.determine_next_agent_deterministic
)
supervisor_agent = default_supervisor_coordinator.execute_supervisor
route_supervisor = default_supervisor_coordinator.route
