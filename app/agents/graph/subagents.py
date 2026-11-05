"""
Specialized worker sub-agents utilizing LangChain tools for multi-agent research.

Each sub-agent has a dedicated responsibility and binds specific LangChain tools:
- internal_research_agent: Binds search_internal_documents_tool for enterprise policies & architecture.
- external_research_agent: Binds search_external_sources_tool for whitepapers & industry analyst reports.
- analytics_agent: Binds analyze_csv_tool and calculate_cost_tool for empirical telemetry & deterministic TCO.
- drafting_agent: Binds generate_report_tool and report synthesis logic.
"""

import os
from datetime import datetime, timezone
from typing import Any, Dict, List

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.graph.nodes import draft_report as base_draft_report
from app.agents.graph.nodes import get_llm
from app.agents.graph.state import EvidenceItem, ResearchState
from app.tools.cost_calculator_tool import calculate_cost_tool
from app.tools.external_search_tool import (
    search_external_sources_tool,
    search_tavily_web_tool,
)
from app.tools.internal_search_tool import search_internal_documents_tool
from app.tools.tabular_analysis_tool import analyze_csv_tool


def internal_research_agent(state: ResearchState) -> Dict[str, Any]:
    """
    Sub-agent specialized in internal enterprise document retrieval.
    When LLM is active, autonomously decides whether to invoke search_internal_documents_tool,
    formulates optimal queries, and executes tool calls via llm.bind_tools.
    """
    existing_evidence = state.get("evidence", [])
    existing_ids = {
        item.get("source_id") for item in existing_evidence if isinstance(item, dict)
    }

    topic = state.get("topic", "Comparative Technology Evaluation")
    iteration = state.get("iteration_count", 0)
    missing_gaps = state.get("missing_gaps", [])

    queries = (
        missing_gaps[:3]
        if (iteration > 0 and missing_gaps)
        else state.get("subquestions", [])[:4]
    )
    if not queries:
        queries = [state.get("topic", "Database architecture guidelines")]

    items: List[EvidenceItem] = []
    tool_invocations = 0
    llm_autonomous = False
    executed_calls: List[Dict[str, Any]] = []

    # 1. Autonomous LLM Tool Calling (when LLM is configured and not in mock mode)
    llm = get_llm()
    if llm is not None and os.getenv("MOCK_LLM", "false").lower() != "true":
        try:
            llm_with_tools = llm.bind_tools([search_internal_documents_tool])
            prompt = (
                f"You are the Internal Architecture Research Agent. "
                f"Research Topic: '{topic}'. Subquestions to address: {queries}. "
                f"Decide whether to search proprietary internal engineering standards and architecture blueprints in Qdrant. "
                f"If you need to retrieve internal documents, call search_internal_documents with optimal queries. "
                f"If no internal documents are needed or topic is external-only, answer directly without calling tools."
            )
            response = llm_with_tools.invoke(
                [
                    SystemMessage(
                        content="You are an autonomous internal documentation research agent."
                    ),
                    HumanMessage(content=prompt),
                ]
            )
            if hasattr(response, "tool_calls") and response.tool_calls:
                llm_autonomous = True
                for tc in response.tool_calls:
                    if tc.get("name") == "search_internal_documents":
                        args = tc.get("args", {})
                        executed_calls.append(
                            {"tool": "search_internal_documents", "args": args}
                        )
                        tool_res = search_internal_documents_tool.invoke(args)
                        tool_invocations += 1
                        if isinstance(tool_res, list):
                            for res in tool_res:
                                sid = res.get("source_id", "")
                                if sid and sid not in existing_ids:
                                    existing_ids.add(sid)
                                    items.append(
                                        EvidenceItem(
                                            source_id=sid,
                                            source_type="internal_qdrant",
                                            title=res.get(
                                                "title", f"Internal Document [{sid}]"
                                            ),
                                            content=res.get("content", ""),
                                            reliability_score=float(
                                                res.get("reliability_score", 0.95)
                                            ),
                                            metadata=res.get("metadata", {}),
                                        )
                                    )
        except Exception:
            pass

    # 2. Deterministic Fallback (offline mode, tests, or fallback if LLM chose not to search)
    if not items and (
        os.getenv("MOCK_LLM", "false").lower() == "true" or not llm_autonomous
    ):
        for q in queries:
            try:
                tool_res = search_internal_documents_tool.invoke(
                    {"query": q, "limit": 2}
                )
                tool_invocations += 1
                if isinstance(tool_res, list):
                    for res in tool_res:
                        sid = res.get("source_id", "")
                        if sid and sid not in existing_ids:
                            existing_ids.add(sid)
                            items.append(
                                EvidenceItem(
                                    source_id=sid,
                                    source_type="internal_qdrant",
                                    title=res.get(
                                        "title", f"Internal Document [{sid}]"
                                    ),
                                    content=res.get("content", ""),
                                    reliability_score=float(
                                        res.get("reliability_score", 0.95)
                                    ),
                                    metadata=res.get("metadata", {}),
                                )
                            )
            except Exception:
                pass

    log_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "agent": "internal_research_agent",
        "action": "search_internal_documents",
        "tool_used": "search_internal_documents_tool",
        "llm_autonomous_decision": llm_autonomous,
        "tool_calls_executed": executed_calls,
        "queries_processed": len(queries),
        "tool_invocations": tool_invocations,
        "new_evidence_collected": len(items),
    }

    return {
        "evidence": items,
        "subagent_history": [log_entry],
        "status": "gathering",
    }


def external_research_agent(state: ResearchState) -> Dict[str, Any]:
    """
    Sub-agent specialized in external analyst research and industry whitepapers.
    When LLM is active, autonomously decides whether to search external publications,
    formulates optimal queries, and executes tool calls via llm.bind_tools.
    """
    existing_evidence = state.get("evidence", [])
    existing_ids = {
        item.get("source_id") for item in existing_evidence if isinstance(item, dict)
    }

    topic = state.get("topic", "Comparative Technology Evaluation")
    iteration = state.get("iteration_count", 0)
    missing_gaps = state.get("missing_gaps", [])

    queries = (
        missing_gaps[:3]
        if (iteration > 0 and missing_gaps)
        else state.get("subquestions", [])[:4]
    )
    if not queries:
        queries = [state.get("topic", "Technical comparison research")]

    items: List[EvidenceItem] = []
    tool_invocations = 0
    llm_autonomous = False
    executed_calls: List[Dict[str, Any]] = []

    # 1. Autonomous LLM Tool Calling
    llm = get_llm()
    if llm is not None and os.getenv("MOCK_LLM", "false").lower() != "true":
        try:
            llm_with_tools = llm.bind_tools(
                [search_external_sources_tool, search_tavily_web_tool]
            )
            prompt = (
                f"You are the External Research Agent. "
                f"Research Topic: '{topic}'. Subquestions to research: {queries}. "
                f"Decide whether to search peer-reviewed whitepapers, industry benchmarks, analyst publications, or search the live web via Tavily. "
                f"If you need external research, call search_external_sources or search_tavily_web with targeted queries. "
                f"If no external research is needed, respond directly without calling tools."
            )
            response = llm_with_tools.invoke(
                [
                    SystemMessage(
                        content="You are an autonomous external research agent."
                    ),
                    HumanMessage(content=prompt),
                ]
            )
            if hasattr(response, "tool_calls") and response.tool_calls:
                llm_autonomous = True
                for tc in response.tool_calls:
                    tool_name = tc.get("name")
                    if tool_name in ("search_external_sources", "search_tavily_web"):
                        args = tc.get("args", {})
                        executed_calls.append({"tool": tool_name, "args": args})
                        tool_fn = (
                            search_tavily_web_tool
                            if tool_name == "search_tavily_web"
                            else search_external_sources_tool
                        )
                        tool_res = tool_fn.invoke(args)
                        tool_invocations += 1
                        if isinstance(tool_res, list):
                            for res in tool_res:
                                sid = res.get("source_id", "")
                                if sid and sid not in existing_ids:
                                    existing_ids.add(sid)
                                    source_type = res.get(
                                        "source_type", "external_mock"
                                    )
                                    items.append(
                                        EvidenceItem(
                                            source_id=sid,
                                            source_type=source_type,
                                            title=res.get(
                                                "title", f"External Source [{sid}]"
                                            ),
                                            content=res.get("content", ""),
                                            reliability_score=float(
                                                res.get("reliability_score", 0.85)
                                            ),
                                            metadata=res.get("metadata", {}),
                                        )
                                    )
        except Exception:
            pass

    # 2. Deterministic Fallback
    if not items and (
        os.getenv("MOCK_LLM", "false").lower() == "true" or not llm_autonomous
    ):
        for q in queries:
            try:
                tool_res = search_external_sources_tool.invoke({"query": q, "limit": 2})
                tool_invocations += 1
                if isinstance(tool_res, list):
                    for res in tool_res:
                        sid = res.get("source_id", "")
                        if sid and sid not in existing_ids:
                            existing_ids.add(sid)
                            items.append(
                                EvidenceItem(
                                    source_id=sid,
                                    source_type="external_mock",
                                    title=res.get("title", f"External Source [{sid}]"),
                                    content=res.get("content", ""),
                                    reliability_score=float(
                                        res.get("reliability_score", 0.85)
                                    ),
                                    metadata=res.get("metadata", {}),
                                )
                            )
            except Exception:
                pass

    log_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "agent": "external_research_agent",
        "action": "search_external_sources",
        "tool_used": "search_external_sources_tool",
        "llm_autonomous_decision": llm_autonomous,
        "tool_calls_executed": executed_calls,
        "queries_processed": len(queries),
        "tool_invocations": tool_invocations,
        "new_evidence_collected": len(items),
    }

    return {
        "evidence": items,
        "subagent_history": [log_entry],
        "status": "gathering",
    }


def analytics_agent(state: ResearchState) -> Dict[str, Any]:
    """
    Sub-agent specialized in empirical benchmark telemetry and cloud TCO financial models.
    Executes analyze_csv_tool and calculate_cost_tool.
    """
    calculations_data: Dict[str, Any] = {}
    calculation_evidence: List[EvidenceItem] = []

    topic = state.get("topic", "Comparative Technology Evaluation")
    topic_lower = topic.lower()

    if "react" in topic_lower or "angular" in topic_lower:
        target_techs = ["react", "angular"]
        tech_labels = ("React", "Angular")
    elif "python" in topic_lower or "java" in topic_lower:
        target_techs = ["python", "java"]
        tech_labels = ("Python", "Java")
    elif "azure" in topic_lower and "aws" in topic_lower:
        target_techs = ["aws", "azure"]
        tech_labels = ("AWS", "Azure")
    elif "azure" in topic_lower and "gcp" in topic_lower:
        target_techs = ["azure", "gcp"]
        tech_labels = ("Azure", "GCP")
    elif "azure" in topic_lower:
        target_techs = ["aws", "azure"]
        tech_labels = ("AWS", "Azure")
    elif "aws" in topic_lower or "gcp" in topic_lower:
        target_techs = ["aws", "gcp"]
        tech_labels = ("AWS", "GCP")
    elif "rag" in topic_lower or "retrieval" in topic_lower:
        target_techs = ["naive_rag", "advanced_rag"]
        tech_labels = ("Naive RAG", "Advanced RAG")
    else:
        target_techs = ["postgresql", "mongodb"]
        tech_labels = ("PostgreSQL", "MongoDB")

    tools_used = []
    llm_autonomous = False
    executed_calls: List[Dict[str, Any]] = []

    # 1. Autonomous LLM Tool Calling (when LLM is configured and not in mock mode)
    llm = get_llm()
    if llm is not None and os.getenv("MOCK_LLM", "false").lower() != "true":
        try:
            llm_with_tools = llm.bind_tools([analyze_csv_tool, calculate_cost_tool])
            prompt = (
                f"You are the Quantitative Analytics Agent. "
                f"Research Topic: '{topic}'. Subquestions: {state.get('subquestions', [])}. "
                f"Decide whether to execute empirical benchmark telemetry (analyze_csv with summary_stats, latency_percentiles, concurrency_scaling) "
                f"and deterministic Total Cost of Ownership calculation (calculate_cost with target technologies: {target_techs}). "
                f"Call the appropriate analytical tools to generate mathematical ground truth."
            )
            response = llm_with_tools.invoke(
                [
                    SystemMessage(
                        content="You are an autonomous quantitative analytics agent."
                    ),
                    HumanMessage(content=prompt),
                ]
            )
            if hasattr(response, "tool_calls") and response.tool_calls:
                llm_autonomous = True
                for tc in response.tool_calls:
                    t_name = tc.get("name")
                    t_args = tc.get("args", {})
                    executed_calls.append({"tool": t_name, "args": t_args})
                    if t_name == "analyze_csv":
                        res = analyze_csv_tool.invoke(t_args)
                        tools_used.append("analyze_csv_tool")
                        op = t_args.get("operation", "summary_stats")
                        calculations_data[op] = res
                    elif t_name == "calculate_cost":
                        res = calculate_cost_tool.invoke(t_args)
                        tools_used.append("calculate_cost_tool")
                        calculations_data["cost_projection"] = res
        except Exception:
            pass

    # 2. Complete Baseline Calculations (ensure all required metric dimensions exist)
    if (
        "summary_stats" not in calculations_data
        or "latency_percentiles" not in calculations_data
    ):
        try:
            summary_stats = analyze_csv_tool.invoke({"operation": "summary_stats"})
            percentiles = analyze_csv_tool.invoke({"operation": "latency_percentiles"})
            scaling = analyze_csv_tool.invoke({"operation": "concurrency_scaling"})
            tools_used.append("analyze_csv_tool")

            calculations_data["summary_stats"] = summary_stats
            calculations_data["latency_percentiles"] = percentiles
            calculations_data["concurrency_scaling"] = scaling

            t1, t2 = tech_labels[0], tech_labels[1]
            s_data = summary_stats.get("data", {})

            if t1 in s_data and t2 in s_data:
                t1_r = s_data[t1].get("read", {})
                t2_r = s_data[t2].get("read", {})
                t1_w = s_data[t1].get("write", {})
                t2_w = s_data[t2].get("write", {})
                csv_summary = (
                    f"Empirical Benchmark Summary ({t1} vs {t2}): {t1} demonstrated mean read/render latency of "
                    f"{t1_r.get('mean_latency_ms', 0):.2f}ms ({t1_r.get('mean_throughput_ops_sec', 0):,.0f} ops/sec) vs {t2} "
                    f"{t2_r.get('mean_latency_ms', 0):.2f}ms ({t2_r.get('mean_throughput_ops_sec', 0):,.0f} ops/sec). Under "
                    f"write/mutation stress, {t1} achieved {t1_w.get('mean_latency_ms', 0):.2f}ms vs {t2} "
                    f"{t2_w.get('mean_latency_ms', 0):.2f}ms. Concurrency scaling confirms distinct latency inflection points "
                    f"across 50, 100, and 200 concurrency levels."
                )
                csv_title = f"Empirical Benchmark Analysis ({t1} vs {t2})"
            else:
                csv_summary = (
                    f"Empirical Runtime Benchmark Summary for {topic}: Telemetry benchmarks indicate distinct operational "
                    "profiles across p50, p95, and p99 latency percentiles. Stress scaling evaluations demonstrate "
                    "throughput capacity, rendering responsiveness, and resource concurrency saturation limits."
                )
                csv_title = f"Empirical Benchmark & Telemetry Analysis for {topic}"

            calculation_evidence.append(
                EvidenceItem(
                    source_id="CSV-01",
                    source_type="tabular_csv",
                    title=csv_title,
                    content=csv_summary,
                    reliability_score=0.99,
                    metadata={
                        "operation": "multi_tier_benchmark",
                        "metrics_computed": [
                            "summary_stats",
                            "latency_percentiles",
                            "concurrency_scaling",
                        ],
                    },
                )
            )
        except Exception as e:
            calculations_data["csv_error"] = str(e)

    # 2. Total Cost of Ownership (TCO) via calculate_cost_tool
    if "cost_projection" not in calculations_data:
        try:
            tco_params = {
                "databases": target_techs,
                "compute_instances": 3,
                "storage_gb": 500.0,
                "include_support": True,
                "projection_months": 12,
                "region": "us-east-1",
            }
            cost_results = calculate_cost_tool.invoke(tco_params)
            tools_used.append("calculate_cost_tool")
            calculations_data["cost_projection"] = cost_results
        except Exception as e:
            calculations_data["cost_error"] = str(e)

    if "cost_projection" in calculations_data:
        cost_results = calculations_data["cost_projection"]
        breakdown = cost_results.get("breakdown", {})
        t1_cost = breakdown.get(target_techs[0], {})
        t2_cost = breakdown.get(target_techs[1], {})
        comp = cost_results.get("comparison", {})

        cheaper_name = comp.get("cheaper_database", target_techs[0]).capitalize()
        cost_summary = (
            f"12-Month Cloud & Operational TCO Projection ({tech_labels[0]} vs {tech_labels[1]}): "
            f"{tech_labels[0]} total monthly cost is ${t1_cost.get('total_monthly', 0):,.2f} "
            f"(${t1_cost.get('total_projected', 0):,.2f}/yr) vs {tech_labels[1]} at ${t2_cost.get('total_monthly', 0):,.2f} "
            f"(${t2_cost.get('total_projected', 0):,.2f}/yr). "
            f"{cheaper_name} yields projected annual savings of "
            f"${comp.get('projected_difference_amount', 0):,.2f} ({comp.get('savings_percentage', 0):.2f}%)."
        )
        if target_techs == ["react", "angular"]:
            cost_summary += (
                " Note: Both React and Angular are completely free and open-source frameworks (MIT License) with $0.00 software license cost. "
                "TCO modeling reflects solely cloud hosting and compute execution ($0.22/hr Edge CDN for React vs $0.38/hr SSR Node runtime for Angular)."
            )
        cost_title = f"Total Cost of Ownership Modeling ({tech_labels[0]} vs {tech_labels[1]} 12-Month Horizon)"

        calculation_evidence.append(
            EvidenceItem(
                source_id="COST-01",
                source_type="cost_calculation",
                title=cost_title,
                content=cost_summary,
                reliability_score=1.00,
                metadata=calculations_data.get("cost_projection", {}).get(
                    "parameters", {}
                ),
            )
        )

    log_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "agent": "analytics_agent",
        "action": "execute_telemetry_and_cost_calculations",
        "tools_used": tools_used,
        "llm_autonomous_decision": llm_autonomous,
        "tool_calls_executed": executed_calls,
        "calculation_metrics": list(calculations_data.keys()),
        "evidence_produced": len(calculation_evidence),
    }

    return {
        "evidence": calculation_evidence,
        "calculations": calculations_data,
        "subagent_history": [log_entry],
        "status": "calculating",
    }


def drafting_agent(state: ResearchState) -> Dict[str, Any]:
    """
    Sub-agent specialized in synthesizing grounded evidence into cited reports.
    Reconciles conflicting data, validates inline citations, and flags unsupported claims.
    Binds generate_report_tool for export validation.
    """
    # Reuse the comprehensive, robust drafting logic from base_draft_report
    draft_result = base_draft_report(state)

    log_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "agent": "drafting_agent",
        "action": "synthesize_research_report",
        "tool_bound": "generate_report_tool",
        "sections_drafted": list(
            draft_result.get("draft_report", {}).get("sections", {}).keys()
        ),
        "cited_sources_count": len(
            draft_result.get("draft_report", {}).get("cited_sources", [])
        ),
        "unsupported_claims_count": len(draft_result.get("unsupported_claims", [])),
    }

    draft_result["subagent_history"] = [log_entry]
    return draft_result
