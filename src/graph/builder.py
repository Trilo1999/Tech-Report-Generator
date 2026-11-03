"""LangGraph workflow assembly and compilation."""

from typing import Any, Optional

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from src.graph.edges import route_review, route_sufficiency
from src.graph.nodes import (
    draft_report,
    evaluate_evidence,
    execute_calculations,
    export_report,
    gather_evidence,
    human_review,
    plan_research,
    revise_sections,
)
from src.graph.subagents import (
    analytics_agent,
    drafting_agent,
    external_research_agent,
    internal_research_agent,
)
from src.graph.supervisor import route_supervisor, supervisor_agent
from src.state import ResearchState


def build_research_graph() -> StateGraph:
    """
    Construct the StateGraph with all core nodes, supervisor, sub-agents,
    sequential transitions, and conditional routing logic.
    """
    workflow = StateGraph(ResearchState)

    # 1. Register 8 workflow nodes + supervisor and sub-agent workers
    workflow.add_node("plan_research", plan_research)
    workflow.add_node("gather_evidence", gather_evidence)
    workflow.add_node("execute_calculations", execute_calculations)
    workflow.add_node("evaluate_evidence", evaluate_evidence)
    workflow.add_node("draft_report", draft_report)
    workflow.add_node("human_review", human_review)
    workflow.add_node("revise_sections", revise_sections)
    workflow.add_node("export_report", export_report)

    # Supervisor & sub-agent worker nodes
    workflow.add_node("supervisor", supervisor_agent)
    workflow.add_node("internal_research_agent", internal_research_agent)
    workflow.add_node("external_research_agent", external_research_agent)
    workflow.add_node("analytics_agent", analytics_agent)
    workflow.add_node("drafting_agent", drafting_agent)

    # 2. Linear transitions: Entry & Initial Research Pipeline
    workflow.add_edge(START, "plan_research")
    workflow.add_edge("plan_research", "gather_evidence")
    workflow.add_edge("gather_evidence", "execute_calculations")
    workflow.add_edge("execute_calculations", "evaluate_evidence")

    # 3. Conditional routing: Evidence sufficiency loop
    workflow.add_conditional_edges(
        "evaluate_evidence",
        route_sufficiency,
        {
            "gather_evidence": "gather_evidence",
            "draft_report": "draft_report",
        },
    )

    # 4. Draft to Human-in-the-Loop review
    workflow.add_edge("draft_report", "human_review")

    # 5. Conditional routing: Human Review outcome
    workflow.add_conditional_edges(
        "human_review",
        route_review,
        {
            "export_report": "export_report",
            "revise_sections": "revise_sections",
            END: END,
        },
    )

    # 6. Revision loop: Returns to human review
    workflow.add_edge("revise_sections", "human_review")

    # 7. Final export transition to workflow termination
    workflow.add_edge("export_report", END)

    return workflow


def build_multi_agent_graph() -> StateGraph:
    """
    Construct the Multi-Agent StateGraph with a Supervisor Agent orchestrating
    and monitoring specialized worker sub-agents.

    Supervisor coordinates:
    - internal_research_agent (search_internal_documents_tool)
    - external_research_agent (search_external_sources_tool)
    - analytics_agent (analyze_csv_tool, calculate_cost_tool)
    - drafting_agent (generate_report_tool)
    - human_review (Human-in-the-Loop interrupt)
    """
    workflow = StateGraph(ResearchState)

    # Register workflow nodes
    workflow.add_node("plan_research", plan_research)
    workflow.add_node("supervisor", supervisor_agent)
    workflow.add_node("internal_research_agent", internal_research_agent)
    workflow.add_node("external_research_agent", external_research_agent)
    workflow.add_node("analytics_agent", analytics_agent)
    workflow.add_node("drafting_agent", drafting_agent)
    workflow.add_node("human_review", human_review)
    workflow.add_node("revise_sections", revise_sections)
    workflow.add_node("export_report", export_report)

    # Entry point
    workflow.add_edge(START, "plan_research")
    workflow.add_edge("plan_research", "supervisor")

    # Supervisor conditional routing
    workflow.add_conditional_edges(
        "supervisor",
        route_supervisor,
        {
            "internal_research_agent": "internal_research_agent",
            "external_research_agent": "external_research_agent",
            "analytics_agent": "analytics_agent",
            "drafting_agent": "drafting_agent",
            "human_review": "human_review",
        },
    )

    # Sub-agents report back to supervisor for continuous monitoring
    workflow.add_edge("internal_research_agent", "supervisor")
    workflow.add_edge("external_research_agent", "supervisor")
    workflow.add_edge("analytics_agent", "supervisor")
    workflow.add_edge("drafting_agent", "supervisor")

    # Human review routing
    workflow.add_conditional_edges(
        "human_review",
        route_review,
        {
            "export_report": "export_report",
            "revise_sections": "revise_sections",
            END: END,
        },
    )

    # Revision returns to supervisor so supervisor can re-evaluate and dispatch
    workflow.add_edge("revise_sections", "supervisor")
    workflow.add_edge("export_report", END)

    return workflow


def create_research_graph(checkpointer: Optional[Any] = None) -> CompiledStateGraph:
    """
    Build and compile the research workflow graph with optional persistence checkpointer.
    """
    workflow = build_research_graph()
    return workflow.compile(checkpointer=checkpointer)


def create_multi_agent_graph(checkpointer: Optional[Any] = None) -> CompiledStateGraph:
    """
    Build and compile the multi-agent supervisor research workflow graph.
    """
    workflow = build_multi_agent_graph()
    return workflow.compile(checkpointer=checkpointer)
