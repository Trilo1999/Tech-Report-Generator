"""
Supervisor Agent for coordinating and monitoring specialized research sub-agents.

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

from datetime import datetime, timezone
import json
import os
from typing import Any, Dict, List

from langchain_core.messages import HumanMessage

from src.config import MAX_RESEARCH_ITERATIONS
from src.graph.nodes import _clean_json_response, get_llm
from src.graph.prompts import SUPERVISOR_PROMPT
from src.state import ResearchState


def evaluate_evidence_manifest(evidence_list: List[Dict[str, Any]]) -> Dict[str, int]:
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


def determine_next_agent_deterministic(state: ResearchState) -> Dict[str, Any]:
    """
    Deterministic rule-based supervisor routing logic.
    Provides reliable, zero-hallucination monitoring and fallback for offline/test modes.
    """
    evidence = state.get("evidence", [])
    manifest = evaluate_evidence_manifest(evidence)
    iteration = state.get("iteration_count", 0)
    draft = state.get("draft_report")
    feedback = state.get("human_feedback")

    # If in revision cycle
    if feedback and feedback.get("decision") == "revise":
        target_sections = feedback.get("target_sections", [])
        if any("TCO" in sec or "Cost" in sec or "Benchmark" in sec for sec in target_sections):
            return {
                "next_agent": "analytics_agent",
                "reasoning": "Human reviewer requested revision targeting financial TCO or empirical performance benchmarks. Routing to analytics_agent.",
                "is_sufficient": True,
                "missing_gaps": [],
            }
        return {
            "next_agent": "drafting_agent",
            "reasoning": "Human reviewer requested text/architectural revisions. Routing directly to drafting_agent for surgical update.",
            "is_sufficient": True,
            "missing_gaps": [],
        }

    # Pipeline progression: 1. Internal Documents
    # If internal search was already attempted and yielded 0 matches (e.g. novel topic not in Qdrant KB),
    # gracefully proceed to external web research rather than looping.
    history = state.get("subagent_history", [])
    internal_attempted = any(h.get("agent") == "internal_research_agent" for h in history if isinstance(h, dict))

    if manifest["internal"] == 0 and not internal_attempted:
        return {
            "next_agent": "internal_research_agent",
            "reasoning": f"Evidence manifest lacks internal engineering guidelines (found {manifest['internal']}). Dispatching internal_research_agent.",
            "is_sufficient": False,
            "missing_gaps": ["Internal enterprise architecture & compliance standards"],
        }

    # 2. External Research
    if manifest["external"] == 0:
        return {
            "next_agent": "external_research_agent",
            "reasoning": f"Evidence manifest lacks external industry research (found {manifest['external']}). Dispatching external_research_agent.",
            "is_sufficient": False,
            "missing_gaps": ["External analyst research and industry whitepapers"],
        }

    # 3. Analytics & Calculations
    if manifest["csv"] == 0 or manifest["cost"] == 0:
        return {
            "next_agent": "analytics_agent",
            "reasoning": f"Evidence manifest lacks quantitative analysis (CSV: {manifest['csv']}, COST: {manifest['cost']}). Dispatching analytics_agent.",
            "is_sufficient": False,
            "missing_gaps": ["Empirical latency percentiles and cloud infrastructure TCO projections"],
        }

    # 4. Drafting Report
    if draft is None:
        return {
            "next_agent": "drafting_agent",
            "reasoning": "All evidence dimensions (internal guidelines, external whitepapers, CSV telemetry, TCO model) satisfied. Dispatching drafting_agent.",
            "is_sufficient": True,
            "missing_gaps": [],
        }

    # 5. Check for iterative gaps if evaluated and under iteration limit
    missing_gaps = state.get("missing_gaps", [])
    if missing_gaps and iteration < MAX_RESEARCH_ITERATIONS:
        # Check if gap is internal or external
        gap_text = " ".join(missing_gaps).lower()
        if "guideline" in gap_text or "internal" in gap_text or "policy" in gap_text:
            return {
                "next_agent": "internal_research_agent",
                "reasoning": f"Iteration {iteration + 1}: Resolving identified internal gaps: {missing_gaps[:2]}.",
                "is_sufficient": False,
                "missing_gaps": missing_gaps,
            }
        return {
            "next_agent": "external_research_agent",
            "reasoning": f"Iteration {iteration + 1}: Resolving identified external gaps: {missing_gaps[:2]}.",
            "is_sufficient": False,
            "missing_gaps": missing_gaps,
        }

    # 6. All requirements met -> Proceed to Human Review
    return {
        "next_agent": "human_review",
        "reasoning": "Draft report synthesized with comprehensive citations and validated unsupported claims. Ready for human inspection.",
        "is_sufficient": True,
        "missing_gaps": [],
    }


def supervisor_agent(state: ResearchState) -> Dict[str, Any]:
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

    manifest = evaluate_evidence_manifest(evidence)
    total_evidence = len(evidence)

    # 1. Base deterministic evaluation as foundational baseline
    decision = determine_next_agent_deterministic(state)

    # 2. If an LLM is enabled, optionally enhance with supervisory reasoning
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
            text = str(response.content) if hasattr(response, "content") else str(response)
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
                decision["reasoning"] = parsed.get("reasoning", decision["reasoning"])
                if "is_sufficient" in parsed:
                    decision["is_sufficient"] = bool(parsed["is_sufficient"])
                if "identified_gaps" in parsed and isinstance(parsed["identified_gaps"], list):
                    decision["missing_gaps"] = parsed["identified_gaps"]
        except Exception:
            pass  # Fall back gracefully to deterministic decision

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


def route_supervisor(state: ResearchState) -> str:
    """
    Conditional edge router for Supervisor Agent.
    Routes to the next agent designated by the supervisor.
    """
    return state.get("next_agent", "human_review")
