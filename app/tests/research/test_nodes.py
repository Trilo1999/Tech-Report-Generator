"""
Unit and integration tests for LangGraph State Schema and 8 Workflow Node Functions.
"""

from pathlib import Path
from unittest.mock import patch

from app.agents.graph.nodes import (
    draft_report,
    evaluate_evidence,
    execute_calculations,
    export_report,
    gather_evidence,
    human_review,
    plan_research,
    revise_sections,
)
from app.agents.graph.state import (
    DraftReport,
    EvidenceItem,
    HumanFeedback,
    ResearchState,
)


def test_state_schema_structure():
    """Verify state types and instantiation."""
    evidence_item: EvidenceItem = {
        "source_id": "QDR-01",
        "source_type": "internal_qdrant",
        "title": "Architecture Overview",
        "content": "PostgreSQL ensures strict ACID compliance.",
        "reliability_score": 0.95,
        "metadata": {"doc_type": "pdf"},
    }
    assert evidence_item["source_id"] == "QDR-01"
    assert evidence_item["reliability_score"] == 0.95

    feedback: HumanFeedback = {
        "decision": "approved",
        "feedback_notes": "Looks solid.",
        "target_sections": [],
    }
    assert feedback["decision"] == "approved"

    state: ResearchState = {
        "topic": "PostgreSQL vs MongoDB",
        "subquestions": ["Subquestion 1", "Subquestion 2", "Subquestion 3"],
        "evidence": [evidence_item],
        "calculations": {},
        "iteration_count": 0,
        "is_sufficient": False,
        "missing_gaps": [],
        "draft_report": None,
        "unsupported_claims": [],
        "human_feedback": None,
        "final_report_path": None,
        "status": "planning",
    }
    assert len(state["subquestions"]) == 3
    assert state["status"] == "planning"


def test_plan_research_node():
    """Verify plan_research generates >= 3 subquestions covering required dimensions."""
    initial_state: ResearchState = {
        "topic": "PostgreSQL vs MongoDB Multi-Tenant Evaluation",
        "subquestions": [],
        "evidence": [],
        "calculations": {},
        "iteration_count": 0,
        "is_sufficient": False,
        "missing_gaps": [],
        "draft_report": None,
        "unsupported_claims": [],
        "human_feedback": None,
        "final_report_path": None,
        "status": "planning",
    }

    result = plan_research(initial_state)

    assert "subquestions" in result
    subquestions = result["subquestions"]
    assert len(subquestions) >= 3, "Acceptance criteria requires >= 3 subquestions"
    assert result["status"] == "planning"
    assert result["iteration_count"] == 0


def test_gather_evidence_node():
    """Verify gather_evidence queries both Qdrant and external mock sources."""
    state: ResearchState = {
        "topic": "PostgreSQL vs MongoDB Architecture Evaluation",
        "subquestions": [
            "How does PostgreSQL handle multi-tenant isolation and row-level security?",
            "What are the latency benchmarks for concurrent write workloads?",
            "What is the 12-month cloud TCO comparison?",
        ],
        "evidence": [],
        "calculations": {},
        "iteration_count": 0,
        "is_sufficient": False,
        "missing_gaps": [],
        "draft_report": None,
        "unsupported_claims": [],
        "human_feedback": None,
        "final_report_path": None,
        "status": "gathering",
    }

    result = gather_evidence(state)

    assert "evidence" in result
    evidence = result["evidence"]
    assert len(evidence) > 0, "Should retrieve evidence items"

    source_ids = [e["source_id"] for e in evidence]
    assert any(
        sid.startswith("QDR-") for sid in source_ids
    ), "Should retrieve internal Qdrant evidence"
    assert any(
        sid.startswith("EXT-") for sid in source_ids
    ), "Should retrieve external mock evidence"
    assert result["status"] == "gathering"


def test_execute_calculations_node():
    """Verify execute_calculations runs Pandas analysis and TCO cost calculator."""
    state: ResearchState = {
        "topic": "PostgreSQL vs MongoDB Architecture Evaluation",
        "subquestions": [],
        "evidence": [],
        "calculations": {},
        "iteration_count": 0,
        "is_sufficient": False,
        "missing_gaps": [],
        "draft_report": None,
        "unsupported_claims": [],
        "human_feedback": None,
        "final_report_path": None,
        "status": "calculating",
    }

    result = execute_calculations(state)

    assert "calculations" in result
    calcs = result["calculations"]
    assert "summary_stats" in calcs
    assert "latency_percentiles" in calcs
    assert "cost_projection" in calcs

    # Verify evidence items created with canonical IDs
    evidence = result["evidence"]
    calc_source_ids = [e["source_id"] for e in evidence]
    assert "CSV-01" in calc_source_ids
    assert "COST-01" in calc_source_ids

    # Verify cost figures match expected deterministic formula
    cost_proj = calcs["cost_projection"]
    assert cost_proj["breakdown"]["postgresql"]["total_monthly"] == 1211.70
    assert cost_proj["breakdown"]["mongodb"]["total_monthly"] == 1426.30
    assert result["status"] == "calculating"


def test_evaluate_evidence_loop_and_max_iterations():
    """Verify evidence evaluation handles sufficiency and enforces max iterations loop break."""
    # Case 1: Incomplete evidence on iteration 0 -> is_sufficient=False
    state_iter_0: ResearchState = {
        "topic": "PostgreSQL vs MongoDB",
        "subquestions": ["Subquestion 1"],
        "evidence": [
            {
                "source_id": "QDR-01",
                "source_type": "internal_qdrant",
                "title": "Title",
                "content": "Content",
                "reliability_score": 0.9,
                "metadata": {},
            }
        ],  # Missing CSV, COST, EXT
        "calculations": {},
        "iteration_count": 0,
        "is_sufficient": False,
        "missing_gaps": [],
        "draft_report": None,
        "unsupported_claims": [],
        "human_feedback": None,
        "final_report_path": None,
        "status": "evaluating",
    }

    res_0 = evaluate_evidence(state_iter_0)
    assert res_0["iteration_count"] == 1
    assert res_0["is_sufficient"] is False
    assert len(res_0["missing_gaps"]) > 0

    # Case 2: Max iterations reached (iteration_count=1 -> increments to 2 >= MAX_RESEARCH_ITERATIONS)
    state_iter_1: ResearchState = {
        "topic": "PostgreSQL vs MongoDB",
        "subquestions": ["Subquestion 1"],
        "evidence": state_iter_0["evidence"],
        "calculations": {},
        "iteration_count": 1,
        "is_sufficient": False,
        "missing_gaps": ["Gap 1"],
        "draft_report": None,
        "unsupported_claims": [],
        "human_feedback": None,
        "final_report_path": None,
        "status": "evaluating",
    }

    res_max = evaluate_evidence(state_iter_1)
    assert res_max["iteration_count"] == 2
    assert (
        res_max["is_sufficient"] is True
    ), "Must force is_sufficient=True on max iterations"
    assert res_max["missing_gaps"] == []


def test_draft_report_node():
    """Verify draft_report produces sections with inline citations and flags unsupported claims."""
    state: ResearchState = {
        "topic": "PostgreSQL vs MongoDB Multi-Tenant Evaluation",
        "subquestions": ["Subquestion 1", "Subquestion 2", "Subquestion 3"],
        "evidence": [
            {
                "source_id": "QDR-01",
                "source_type": "internal_qdrant",
                "title": "Architecture",
                "content": "PostgreSQL supports RLS.",
                "reliability_score": 0.95,
                "metadata": {},
            },
            {
                "source_id": "CSV-01",
                "source_type": "tabular_csv",
                "title": "Benchmarks",
                "content": "PostgreSQL achieves 38,420 ops/sec.",
                "reliability_score": 0.99,
                "metadata": {},
            },
            {
                "source_id": "COST-01",
                "source_type": "cost_calculation",
                "title": "Cost Model",
                "content": "PostgreSQL monthly cost is $1,211.70.",
                "reliability_score": 1.0,
                "metadata": {},
            },
        ],
        "calculations": {"summary": "sample calculations"},
        "iteration_count": 1,
        "is_sufficient": True,
        "missing_gaps": [],
        "draft_report": None,
        "unsupported_claims": [],
        "human_feedback": None,
        "final_report_path": None,
        "status": "drafted",
    }

    result = draft_report(state)

    assert "draft_report" in result
    draft: DraftReport = result["draft_report"]
    assert "Executive Summary" in draft["sections"]
    assert "Architecture & Data Model Comparison" in draft["sections"]
    assert "Performance & Benchmark Analysis" in draft["sections"]
    assert "TCO & Cloud Cost Projection" in draft["sections"]
    assert "Strategic Recommendations & Trade-offs" in draft["sections"]

    # Check that sources are cited
    assert len(draft["cited_sources"]) > 0
    assert any(
        "QDR-" in c or "CSV-" in c or "COST-" in c for c in draft["cited_sources"]
    )

    # Check unsupported claims flagging
    assert (
        len(result["unsupported_claims"]) > 0
    ), "Must flag unsupported claims per acceptance criteria"
    assert result["status"] == "drafted"


def test_human_review_node_interrupt_approval():
    """Verify human_review triggers interrupt and handles approved verdict."""
    state: ResearchState = {
        "topic": "PostgreSQL vs MongoDB",
        "subquestions": [],
        "evidence": [],
        "calculations": {},
        "iteration_count": 1,
        "is_sufficient": True,
        "missing_gaps": [],
        "draft_report": {
            "title": "Report Title",
            "sections": {"Executive Summary": "Summary content with [QDR-01]"},
            "cited_sources": ["QDR-01"],
            "unsupported_claims": [],
        },
        "unsupported_claims": [],
        "human_feedback": None,
        "final_report_path": None,
        "status": "review_pending",
    }

    mock_review_payload = {
        "decision": "approved",
        "feedback_notes": "Architecture validated by enterprise committee.",
        "target_sections": [],
    }

    with patch(
        "app.agents.graph.nodes.interrupt", return_value=mock_review_payload
    ) as mock_interrupt:
        result = human_review(state)
        mock_interrupt.assert_called_once()
        assert result["status"] == "approved"
        assert result["human_feedback"]["decision"] == "approved"
        assert (
            result["human_feedback"]["feedback_notes"]
            == "Architecture validated by enterprise committee."
        )


def test_human_review_node_interrupt_revise():
    """Verify human_review triggers interrupt and handles revise verdict."""
    state: ResearchState = {
        "topic": "PostgreSQL vs MongoDB",
        "subquestions": [],
        "evidence": [],
        "calculations": {},
        "iteration_count": 1,
        "is_sufficient": True,
        "missing_gaps": [],
        "draft_report": None,
        "unsupported_claims": [],
        "human_feedback": None,
        "final_report_path": None,
        "status": "review_pending",
    }

    mock_review_payload = {
        "decision": "revise",
        "feedback_notes": "Update the TCO projection for 36 months scale.",
        "target_sections": ["TCO & Cloud Cost Projection"],
    }

    with patch("app.agents.graph.nodes.interrupt", return_value=mock_review_payload):
        result = human_review(state)
        assert result["status"] == "review_pending"
        assert result["human_feedback"]["decision"] == "revise"
        assert result["human_feedback"]["target_sections"] == [
            "TCO & Cloud Cost Projection"
        ]


def test_revise_sections_surgical_update():
    """Verify revise_sections surgically modifies ONLY target sections without altering others."""
    original_sections = {
        "Executive Summary": "Original intact summary text [QDR-01].",
        "Architecture & Data Model Comparison": "Original intact architecture text [QDR-02].",
        "Performance & Benchmark Analysis": "Original intact benchmark text [CSV-01].",
        "TCO & Cloud Cost Projection": "Original 12-month TCO text [COST-01].",
        "Strategic Recommendations & Trade-offs": "Original intact recommendations text [QDR-03].",
    }

    state: ResearchState = {
        "topic": "PostgreSQL vs MongoDB",
        "subquestions": [],
        "evidence": [
            {
                "source_id": "QDR-01",
                "source_type": "internal_qdrant",
                "title": "Title",
                "content": "Content",
                "reliability_score": 0.95,
                "metadata": {},
            }
        ],
        "calculations": {},
        "iteration_count": 1,
        "is_sufficient": True,
        "missing_gaps": [],
        "draft_report": {
            "title": "Database Report",
            "sections": dict(original_sections),
            "cited_sources": ["QDR-01", "QDR-02", "CSV-01", "COST-01", "QDR-03"],
            "unsupported_claims": [],
        },
        "unsupported_claims": [],
        "human_feedback": {
            "decision": "revise",
            "feedback_notes": "Emphasize 36-month reserved instance economics.",
            "target_sections": ["TCO & Cloud Cost Projection"],
        },
        "final_report_path": None,
        "status": "review_pending",
    }

    result = revise_sections(state)

    updated_draft = result["draft_report"]
    updated_sections = updated_draft["sections"]

    # Target section must be modified
    assert "36-month" in updated_sections["TCO & Cloud Cost Projection"]
    assert (
        updated_sections["TCO & Cloud Cost Projection"]
        != original_sections["TCO & Cloud Cost Projection"]
    )

    # Untargeted sections MUST remain exactly identical (no regression)
    assert (
        updated_sections["Executive Summary"] == original_sections["Executive Summary"]
    )
    assert (
        updated_sections["Architecture & Data Model Comparison"]
        == original_sections["Architecture & Data Model Comparison"]
    )
    assert (
        updated_sections["Performance & Benchmark Analysis"]
        == original_sections["Performance & Benchmark Analysis"]
    )
    assert (
        updated_sections["Strategic Recommendations & Trade-offs"]
        == original_sections["Strategic Recommendations & Trade-offs"]
    )

    assert result["status"] == "revised"


def test_export_report_node():
    """Verify export_report generates a publication-ready PDF document."""
    state: ResearchState = {
        "topic": "PostgreSQL vs MongoDB Evaluation",
        "subquestions": [],
        "evidence": [],
        "calculations": {},
        "iteration_count": 1,
        "is_sufficient": True,
        "missing_gaps": [],
        "draft_report": {
            "title": "PostgreSQL vs MongoDB Architecture Decision",
            "sections": {
                "Executive Summary": "Summary with [QDR-01].",
                "Architecture & Data Model Comparison": "Schema comparison.",
                "Performance & Benchmark Analysis": "Benchmark data [CSV-01].",
                "TCO & Cloud Cost Projection": "Cost projection [COST-01].",
                "Strategic Recommendations & Trade-offs": "Final recommendation.",
            },
            "cited_sources": ["QDR-01", "CSV-01", "COST-01"],
            "unsupported_claims": ["MongoDB cluster auto-shards without network hops."],
        },
        "unsupported_claims": ["MongoDB cluster auto-shards without network hops."],
        "human_feedback": {
            "decision": "approved",
            "feedback_notes": "Validated by CTO.",
            "target_sections": [],
        },
        "final_report_path": None,
        "status": "approved",
    }

    result = export_report(state)

    assert "final_report_path" in result
    pdf_path_str = result["final_report_path"]
    assert pdf_path_str is not None
    pdf_path = Path(pdf_path_str)
    assert pdf_path.exists(), f"Generated PDF file must exist at {pdf_path}"
    assert pdf_path.suffix == ".pdf"
    assert pdf_path.stat().st_size > 500, "PDF file must not be empty"
    assert result["status"] == "completed"


def test_evaluate_evidence_conflicting_and_missing_evidence():
    """Verify evaluation detects missing gaps when dimensions lack coverage and isolates conflicting evidence."""
    # 1. Test missing evidence detection
    state_missing: ResearchState = {
        "topic": "PostgreSQL vs MongoDB Multi-Tenant Scaling",
        "subquestions": [
            "How do PostgreSQL and MongoDB perform under 200 concurrent connections?"
        ],
        "evidence": [
            {
                "source_id": "QDR-01",
                "source_type": "internal_qdrant",
                "title": "Guidelines",
                "content": "Mandatory row-level security.",
                "reliability_score": 0.95,
                "metadata": {},
            }
        ],
        "calculations": {},
        "iteration_count": 0,
        "is_sufficient": False,
        "missing_gaps": [],
        "conflicting_evidence": [],
        "draft_report": None,
        "unsupported_claims": [],
        "human_feedback": None,
        "final_report_path": None,
        "status": "evaluating",
    }

    eval_missing = evaluate_evidence(state_missing)
    assert (
        eval_missing["is_sufficient"] is False
    ), "Must declare insufficient when external/csv/cost are missing"
    assert len(eval_missing["missing_gaps"]) > 0

    # 2. Test conflicting evidence detection between external source and empirical benchmark
    state_conflicting: ResearchState = {
        "topic": "PostgreSQL vs MongoDB Multi-Tenant Scaling",
        "subquestions": [
            "How do PostgreSQL and MongoDB perform under 200 concurrent connections?"
        ],
        "evidence": [
            {
                "source_id": "QDR-01",
                "source_type": "internal_qdrant",
                "title": "Guidelines",
                "content": "Mandatory row-level security.",
                "reliability_score": 0.95,
                "metadata": {},
            },
            {
                "source_id": "EXT-01",
                "source_type": "external_mock",
                "title": "Analyst Whitepaper",
                "content": "Throughput parity observed across document and relational paradigms.",
                "reliability_score": 0.85,
                "metadata": {},
            },
            {
                "source_id": "CSV-01",
                "source_type": "tabular_csv",
                "title": "Empirical Telemetry",
                "content": "MongoDB write p95 latency degrades to 7.91ms vs PostgreSQL 3.82ms under 200 concurrent connections.",
                "reliability_score": 0.99,
                "metadata": {},
            },
            {
                "source_id": "COST-01",
                "source_type": "cost_calculation",
                "title": "12-Month TCO Model",
                "content": "PostgreSQL total annual cost is 15.04% cheaper.",
                "reliability_score": 1.0,
                "metadata": {},
            },
        ],
        "calculations": {},
        "iteration_count": 0,
        "is_sufficient": False,
        "missing_gaps": [],
        "conflicting_evidence": [],
        "draft_report": None,
        "unsupported_claims": [],
        "human_feedback": None,
        "final_report_path": None,
        "status": "evaluating",
    }

    eval_conflicts = evaluate_evidence(state_conflicting)
    assert "conflicting_evidence" in eval_conflicts
    conflicts = eval_conflicts["conflicting_evidence"]
    assert (
        len(conflicts) > 0
    ), "Must detect contradiction between external whitepaper and empirical benchmark"
    assert any(
        c["source_a_id"] == "EXT-01" and c["source_b_id"] == "CSV-01" for c in conflicts
    )


def test_draft_report_reconciles_conflicting_evidence():
    """Verify draft_report explicitly surfaces conflicting evidence and cites empirical resolution."""
    state: ResearchState = {
        "topic": "PostgreSQL vs MongoDB Multi-Tenant Scaling",
        "subquestions": ["Subquestion 1", "Subquestion 2", "Subquestion 3"],
        "evidence": [
            {
                "source_id": "QDR-01",
                "source_type": "internal_qdrant",
                "title": "Architecture",
                "content": "PostgreSQL supports RLS.",
                "reliability_score": 0.95,
                "metadata": {},
            },
            {
                "source_id": "EXT-01",
                "source_type": "external_mock",
                "title": "Whitepaper",
                "content": "Claims throughput parity.",
                "reliability_score": 0.85,
                "metadata": {},
            },
            {
                "source_id": "CSV-01",
                "source_type": "tabular_csv",
                "title": "Benchmarks",
                "content": "MongoDB p95 write latency 7.91ms vs PostgreSQL 3.82ms.",
                "reliability_score": 0.99,
                "metadata": {},
            },
        ],
        "calculations": {},
        "iteration_count": 1,
        "is_sufficient": True,
        "missing_gaps": [],
        "conflicting_evidence": [
            {
                "source_a_id": "EXT-01",
                "source_b_id": "CSV-01",
                "claim_a": "Whitepaper claims throughput parity across models.",
                "claim_b": "Empirical stress test reveals 2x latency divergence on writes under 200 users.",
                "resolution_strategy": "Empirical benchmark telemetry [CSV-01] supersedes general whitepaper projections [EXT-01].",
            }
        ],
        "draft_report": None,
        "unsupported_claims": [],
        "human_feedback": None,
        "final_report_path": None,
        "status": "evaluating",
    }

    result = draft_report(state)
    draft = result["draft_report"]
    assert draft is not None
    # Verify conflict reconciliation block is embedded into sections
    all_text = " ".join(draft["sections"].values())
    assert "Conflicting Evidence & Reconciliation" in all_text
    assert "[EXT-01]" in all_text and "[CSV-01]" in all_text
    assert "supersedes" in all_text or "Resolution" in all_text


def test_all_ui_preset_topics_execute_and_have_data():
    """Verify that all default preset scopes shown in the UI have full data and execute successfully."""
    from app.tools.external_search_tool import search_external_sources
    from app.tools.internal_search_tool import search_internal_documents

    preset_topics = [
        "python vs java Architecture Evaluation on llm integration",
        "PostgreSQL vs MongoDB Architecture Evaluation",
        "React vs Angular Enterprise Performance Benchmark",
        "AWS vs Azure Cloud TCO & Infrastructure Evaluation",
        "AWS vs GCP Cloud TCO & Microservices",
    ]

    for topic in preset_topics:
        # 1. Calculations
        calc_res = execute_calculations({"topic": topic})
        calcs = calc_res.get("calculations", {})
        assert "cost_projection" in calcs
        assert "summary_stats" in calcs
        cost_comparison = calcs["cost_projection"].get("comparison", {})
        assert "cheaper_database" in cost_comparison
        assert cost_comparison["projected_difference_amount"] > 0

        # 2. Internal Search (Qdrant)
        internal_results = search_internal_documents(topic, limit=2)
        assert len(internal_results) > 0, f"No internal documents for topic: {topic}"

        # 3. External Search
        external_results = search_external_sources(topic, limit=2)
        assert len(external_results) > 0, f"No external sources for topic: {topic}"
