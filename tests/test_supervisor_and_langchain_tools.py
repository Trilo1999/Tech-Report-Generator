"""
Comprehensive test suite for LangChain @tool conversions, specialized sub-agents,
and the Supervisor Agent multi-agent orchestration pattern.
"""

from pathlib import Path
from unittest.mock import patch

from langchain_core.tools import BaseTool

from src.graph.builder import (
    build_multi_agent_graph,
    create_multi_agent_graph,
)
from src.graph.subagents import (
    analytics_agent,
    external_research_agent,
    internal_research_agent,
)
from src.graph.supervisor import (
    determine_next_agent_deterministic,
    evaluate_evidence_manifest,
    route_supervisor,
    supervisor_agent,
)
from src.state import EvidenceItem, ResearchState
from src.tools import (
    analyze_csv_tool,
    calculate_cost_tool,
    generate_report_tool,
    search_external_sources_tool,
    search_internal_documents_tool,
)


# ──────────────────────────────────────────────
# 1. LangChain Tools Verification
# ──────────────────────────────────────────────
def test_langchain_tools_are_structured_tools():
    """Verify that all 5 tools are instances of LangChain BaseTool with defined schema and name."""
    tools = [
        search_internal_documents_tool,
        search_external_sources_tool,
        analyze_csv_tool,
        calculate_cost_tool,
        generate_report_tool,
    ]
    for t in tools:
        assert isinstance(t, BaseTool), f"{t} is not a LangChain BaseTool"
        assert t.name != "", f"{t} has an empty tool name"
        assert t.description != "", f"{t} has an empty tool description"
        assert t.args_schema is not None, f"{t} lacks an args_schema"


def test_search_internal_documents_tool_invocation():
    """Verify invoking search_internal_documents_tool via LangChain invoke."""
    results = search_internal_documents_tool.invoke({"query": "PostgreSQL ACID compliance", "limit": 2})
    assert isinstance(results, list)
    assert len(results) > 0
    first = results[0]
    assert "source_id" in first
    assert "content" in first
    assert first["source_id"].startswith("QDR-")


def test_search_external_sources_tool_invocation():
    """Verify invoking search_external_sources_tool via LangChain invoke."""
    results = search_external_sources_tool.invoke({"query": "MongoDB scaling and telemetry", "limit": 2})
    assert isinstance(results, list)
    assert len(results) > 0
    first = results[0]
    assert "source_id" in first
    assert first["source_id"].startswith("EXT-")


def test_analyze_csv_tool_invocation():
    """Verify invoking analyze_csv_tool via LangChain invoke."""
    stats = analyze_csv_tool.invoke({"operation": "summary_stats"})
    assert isinstance(stats, dict)
    assert stats["source_id"] == "CSV-01"
    assert "PostgreSQL" in stats["data"]

    percentiles = analyze_csv_tool.invoke({"operation": "latency_percentiles"})
    assert "p95_latency_ms" in percentiles["data"]["PostgreSQL"]["write"]


def test_calculate_cost_tool_invocation():
    """Verify invoking calculate_cost_tool via LangChain invoke."""
    cost = calculate_cost_tool.invoke(
        {
            "databases": ["postgresql", "mongodb"],
            "storage_gb": 500.0,
            "compute_instances": 3,
            "projection_months": 12,
            "include_support": True,
            "region": "us-east-1",
        }
    )
    assert isinstance(cost, dict)
    assert cost["source_id"] == "COST-01"
    assert "postgresql" in cost["breakdown"]
    assert "mongodb" in cost["breakdown"]
    assert "comparison" in cost


def test_generate_report_tool_invocation(tmp_path):
    """Verify invoking generate_report_tool via LangChain invoke produces a PDF."""
    sample_content = {
        "title": "LangChain Tool Export Verification",
        "sections": {
            "Executive Summary": "Verified tool export pipeline.",
        },
        "cited_sources": ["QDR-01"],
        "unsupported_claims": [],
    }
    output_file = generate_report_tool.invoke(
        {
            "content": sample_content,
            "format": "pdf",
            "output_filename": "test_langchain_tool_export.pdf",
        }
    )
    assert Path(output_file).is_file()
    assert output_file.endswith(".pdf")


# ──────────────────────────────────────────────
# 2. Worker Sub-Agents Verification
# ──────────────────────────────────────────────
def test_internal_research_subagent_execution():
    """Verify internal_research_agent queries Qdrant and records subagent history."""
    state: ResearchState = {
        "topic": "PostgreSQL Architecture",
        "subquestions": ["How does PostgreSQL handle schema migration and ACID transactions?"],
        "evidence": [],
        "calculations": {},
        "iteration_count": 0,
        "is_sufficient": False,
        "missing_gaps": [],
        "draft_report": None,
        "unsupported_claims": [],
        "status": "planning",
    }
    result = internal_research_agent(state)
    assert result["status"] == "gathering"
    assert len(result["evidence"]) > 0
    assert result["evidence"][0]["source_id"].startswith("QDR-")
    assert len(result["subagent_history"]) == 1
    assert result["subagent_history"][0]["agent"] == "internal_research_agent"


def test_external_research_subagent_execution():
    """Verify external_research_agent queries external sources and records history."""
    state: ResearchState = {
        "topic": "NoSQL vs Relational Ecosystem",
        "subquestions": ["What is the developer ecosystem maturity for MongoDB?"],
        "evidence": [],
        "calculations": {},
        "iteration_count": 0,
        "is_sufficient": False,
        "missing_gaps": [],
        "draft_report": None,
        "unsupported_claims": [],
        "status": "planning",
    }
    result = external_research_agent(state)
    assert result["status"] == "gathering"
    assert len(result["evidence"]) > 0
    assert result["evidence"][0]["source_id"].startswith("EXT-")
    assert len(result["subagent_history"]) == 1
    assert result["subagent_history"][0]["agent"] == "external_research_agent"


def test_analytics_subagent_execution():
    """Verify analytics_agent computes telemetry and TCO with LangChain tools."""
    state: ResearchState = {
        "topic": "PostgreSQL vs MongoDB",
        "subquestions": ["What are the empirical benchmarks and costs?"],
        "evidence": [],
        "calculations": {},
        "iteration_count": 0,
        "is_sufficient": False,
        "missing_gaps": [],
        "draft_report": None,
        "unsupported_claims": [],
        "status": "planning",
    }
    result = analytics_agent(state)
    assert result["status"] == "calculating"
    assert len(result["evidence"]) == 2  # CSV-01 and COST-01
    source_ids = {e["source_id"] for e in result["evidence"]}
    assert "CSV-01" in source_ids
    assert "COST-01" in source_ids
    assert "summary_stats" in result["calculations"]
    assert "cost_projection" in result["calculations"]
    assert len(result["subagent_history"]) == 1
    assert result["subagent_history"][0]["agent"] == "analytics_agent"


# ──────────────────────────────────────────────
# 3. Supervisor Agent & Manifest Verification
# ──────────────────────────────────────────────
def test_evaluate_evidence_manifest():
    """Verify supervisor accurately categorizes evidence types."""
    manifest = evaluate_evidence_manifest(
        [
            {"source_id": "QDR-01", "source_type": "internal_qdrant"},
            {"source_id": "EXT-01", "source_type": "external_mock"},
            {"source_id": "CSV-01", "source_type": "tabular_csv"},
            {"source_id": "COST-01", "source_type": "cost_calculation"},
        ]
    )
    assert manifest["internal"] == 1
    assert manifest["external"] == 1
    assert manifest["csv"] == 1
    assert manifest["cost"] == 1


def test_supervisor_deterministic_routing_sequence():
    """Verify supervisor sequences subagents logically through the full research lifecycle."""
    base_state: ResearchState = {
        "topic": "PostgreSQL vs MongoDB Multi-Tenant Evaluation",
        "subquestions": ["Subquestion 1", "Subquestion 2", "Subquestion 3"],
        "evidence": [],
        "calculations": {},
        "iteration_count": 0,
        "is_sufficient": False,
        "missing_gaps": [],
        "draft_report": None,
        "unsupported_claims": [],
        "status": "planning",
    }

    # Step 1: No internal evidence -> internal_research_agent
    dec1 = determine_next_agent_deterministic(base_state)
    assert dec1["next_agent"] == "internal_research_agent"

    # Step 2: Add internal evidence -> external_research_agent
    state_with_internal = dict(base_state)
    state_with_internal["evidence"] = [
        EvidenceItem(
            source_id="QDR-01",
            source_type="internal_qdrant",
            title="Guidelines",
            content="ACID rules",
            reliability_score=0.95,
            metadata={},
        )
    ]
    dec2 = determine_next_agent_deterministic(state_with_internal)
    assert dec2["next_agent"] == "external_research_agent"

    # Step 3: Add external evidence -> analytics_agent
    state_with_external = dict(state_with_internal)
    state_with_external["evidence"] = state_with_internal["evidence"] + [
        EvidenceItem(
            source_id="EXT-01",
            source_type="external_mock",
            title="Whitepaper",
            content="Scaling rules",
            reliability_score=0.90,
            metadata={},
        )
    ]
    dec3 = determine_next_agent_deterministic(state_with_external)
    assert dec3["next_agent"] == "analytics_agent"

    # Step 4: Add calculations -> drafting_agent
    state_with_calc = dict(state_with_external)
    state_with_calc["evidence"] = state_with_external["evidence"] + [
        EvidenceItem(
            source_id="CSV-01",
            source_type="tabular_csv",
            title="Benchmarks",
            content="Ops/sec data",
            reliability_score=0.99,
            metadata={},
        ),
        EvidenceItem(
            source_id="COST-01",
            source_type="cost_calculation",
            title="TCO",
            content="Cost projection",
            reliability_score=1.00,
            metadata={},
        ),
    ]
    dec4 = determine_next_agent_deterministic(state_with_calc)
    assert dec4["next_agent"] == "drafting_agent"

    # Step 5: Add draft report -> human_review
    state_with_draft = dict(state_with_calc)
    state_with_draft["draft_report"] = {
        "title": "Evaluated Report",
        "sections": {"Executive Summary": "Summary"},
        "cited_sources": ["QDR-01", "EXT-01", "CSV-01", "COST-01"],
        "unsupported_claims": [],
    }
    dec5 = determine_next_agent_deterministic(state_with_draft)
    assert dec5["next_agent"] == "human_review"


def test_supervisor_agent_node_execution():
    """Verify supervisor_agent node returns correct keys, notes, and log history."""
    state: ResearchState = {
        "topic": "PostgreSQL vs MongoDB Architecture Evaluation",
        "subquestions": ["Subquestion 1", "Subquestion 2", "Subquestion 3"],
        "evidence": [],
        "calculations": {},
        "iteration_count": 0,
        "is_sufficient": False,
        "missing_gaps": [],
        "draft_report": None,
        "unsupported_claims": [],
        "status": "planning",
    }
    result = supervisor_agent(state)
    assert result["status"] == "supervising"
    assert result["next_agent"] == "internal_research_agent"
    assert "supervisor_notes" in result
    assert len(result["subagent_history"]) == 1
    assert result["subagent_history"][0]["agent"] == "supervisor_agent"
    assert route_supervisor(result) == "internal_research_agent"


# ──────────────────────────────────────────────
# 4. Multi-Agent Graph Compilation & Full End-to-End Execution
# ──────────────────────────────────────────────
def test_build_multi_agent_graph_compilation():
    """Verify multi-agent graph compiles and contains all subagents and supervisor."""
    workflow = build_multi_agent_graph()
    expected = {
        "plan_research",
        "supervisor",
        "internal_research_agent",
        "external_research_agent",
        "analytics_agent",
        "drafting_agent",
        "human_review",
        "revise_sections",
        "export_report",
    }
    actual = set(workflow.nodes.keys())
    assert expected.issubset(actual), f"Missing multi-agent nodes: {expected - actual}"

    compiled = create_multi_agent_graph()
    assert compiled is not None


def test_multi_agent_graph_full_execution_approved():
    """Verify multi-agent graph with supervisor runs all sub-agents and completes report export."""
    compiled = create_multi_agent_graph()

    mock_review_feedback = {
        "decision": "approved",
        "feedback_notes": "Supervisor coordinated all agents accurately.",
        "target_sections": [],
    }

    initial_input = {
        "topic": "AWS vs Azure Multi-Cloud TCO & Performance Architecture",
    }

    with patch("src.graph.nodes.interrupt", return_value=mock_review_feedback):
        final_state = compiled.invoke(initial_input)

        assert final_state is not None
        assert final_state["status"] == "completed"
        assert len(final_state["subquestions"]) >= 3
        assert len(final_state["evidence"]) >= 4
        assert final_state["draft_report"] is not None
        assert final_state["final_report_path"] is not None
        assert final_state["final_report_path"].endswith(".pdf")
        # Ensure subagent audit history exists and tracked executions
        history = final_state.get("subagent_history", [])
        assert len(history) >= 4
        agents_run = {h["agent"] for h in history}
        assert "supervisor_agent" in agents_run
        assert "internal_research_agent" in agents_run
        assert "external_research_agent" in agents_run
        assert "analytics_agent" in agents_run
        assert "drafting_agent" in agents_run


def test_rag_pipeline_external_search_and_analytics():
    """Verify that querying a novel topic like RAG pipelines retrieves external sources and executes RAG analytics."""
    # 1. External Search
    rag_sources = search_external_sources_tool.invoke(
        {
            "query": "RAG pipeline architecture chunking strategies and vector retrieval latency",
            "limit": 3,
        }
    )
    assert len(rag_sources) > 0
    assert any("RAG" in s["title"] or "Vector" in s["title"] for s in rag_sources)

    # 2. Analytics Agent for RAG
    state: ResearchState = {
        "topic": "Naive RAG vs Advanced RAG Architecture & TCO",
        "subquestions": ["How do Naive and Advanced RAG compare in retrieval latency and cost?"],
        "evidence": [],
        "calculations": {},
        "iteration_count": 0,
        "is_sufficient": False,
        "missing_gaps": [],
        "draft_report": None,
        "unsupported_claims": [],
        "status": "planning",
    }
    analytics_result = analytics_agent(state)
    assert analytics_result["status"] == "calculating"
    assert "cost_projection" in analytics_result["calculations"]
    breakdown = analytics_result["calculations"]["cost_projection"]["breakdown"]
    assert "naive_rag" in breakdown
    assert "advanced_rag" in breakdown


def test_llm_autonomous_tool_calling_decision():
    """Verify that sub-agents execute LLM-decided tool calls when emitted, and log autonomous decision."""
    from unittest.mock import MagicMock
    from langchain_core.messages import AIMessage

    mock_llm = MagicMock()
    mock_llm.bind_tools.return_value.invoke.return_value = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "search_internal_documents",
                "args": {"query": "PostgreSQL ACID compliance", "limit": 2},
                "id": "call-test-123",
                "type": "tool_call",
            }
        ],
    )

    with (
        patch("src.graph.subagents.get_llm", return_value=mock_llm),
        patch.dict("os.environ", {"MOCK_LLM": "false"}),
    ):
        state: ResearchState = {
            "topic": "PostgreSQL Architecture",
            "subquestions": ["How does PostgreSQL handle ACID?"],
            "evidence": [],
            "calculations": {},
            "iteration_count": 0,
            "is_sufficient": False,
            "missing_gaps": [],
            "draft_report": None,
            "unsupported_claims": [],
            "status": "planning",
        }
        res = internal_research_agent(state)
        history = res.get("subagent_history", [])
        assert len(history) > 0
        assert history[0]["llm_autonomous_decision"] is True
        assert len(history[0]["tool_calls_executed"]) == 1
        assert history[0]["tool_calls_executed"][0]["tool"] == "search_internal_documents"
        assert len(res["evidence"]) > 0


# ──────────────────────────────────────────────
# 5. Orchestrator-Worker Pattern Verification
# ──────────────────────────────────────────────
def test_orchestrator_planner_and_task_dispatch():
    """Verify orchestrator decomposes research into worker tasks and dispatches via Send."""
    from langgraph.types import Send
    from src.graph.orchestrator import assign_worker_tasks, orchestrator_planner

    state: ResearchState = {
        "topic": "PostgreSQL vs MongoDB Architecture Evaluation",
        "subquestions": ["How do schemas compare?", "What are latency numbers?", "What is TCO?"],
        "evidence": [],
        "calculations": {},
        "iteration_count": 0,
        "is_sufficient": False,
        "missing_gaps": [],
        "draft_report": None,
        "unsupported_claims": [],
        "status": "planning",
    }
    plan_res = orchestrator_planner(state)
    assert plan_res["status"] == "orchestrating"
    assert "worker_tasks" in plan_res
    tasks = plan_res["worker_tasks"]
    assert len(tasks) >= 3

    # Verify dynamic fan-out sends
    state_with_plan = {**state, **plan_res}
    sends = assign_worker_tasks(state_with_plan)
    assert len(sends) == len(tasks)
    for s in sends:
        assert isinstance(s, Send)
        assert s.node in {"internal_research_worker", "external_research_worker", "analytics_worker"}


def test_orchestrator_worker_graph_compilation_and_execution():
    """Verify full end-to-end execution of the Orchestrator-Worker pattern with Map-Reduce."""
    from src.graph.builder import build_orchestrator_worker_graph, create_orchestrator_worker_graph

    workflow = build_orchestrator_worker_graph()
    expected = {
        "plan_research",
        "orchestrator_planner",
        "internal_research_worker",
        "external_research_worker",
        "analytics_worker",
        "orchestrator_synthesizer",
        "human_review",
        "revise_sections",
        "export_report",
    }
    assert expected.issubset(set(workflow.nodes.keys()))

    compiled = create_orchestrator_worker_graph()
    assert compiled is not None

    mock_review_feedback = {
        "decision": "approved",
        "feedback_notes": "Orchestrator parallel workers gathered all dimensions accurately.",
        "target_sections": [],
    }

    initial_input = {
        "topic": "PostgreSQL vs MongoDB Enterprise Architecture & TCO",
    }

    with patch("src.graph.nodes.interrupt", return_value=mock_review_feedback):
        final_state = compiled.invoke(initial_input)

        assert final_state is not None
        assert final_state["status"] == "completed"
        assert len(final_state["evidence"]) >= 3
        assert final_state["draft_report"] is not None
        assert final_state["final_report_path"] is not None
        assert final_state["final_report_path"].endswith(".pdf")
        # Ensure subagent history captured both planner and workers
        history = final_state.get("subagent_history", [])
        agent_names = {h.get("agent") for h in history if isinstance(h, dict)}
        assert "orchestrator_planner" in agent_names
        assert "orchestrator_synthesizer" in agent_names
