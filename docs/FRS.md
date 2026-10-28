# Functional Requirements Specification (FRS)

**Project Name**: AI Research & Report Generation Agent
**Document Version**: 1.0
**Status**: Approved
**Author**: Engineering Team
**Date**: October 2026

---

## 1. Introduction

### 1.1 Purpose
This document specifies the complete functional and operational requirements for the **AI Research & Report Generation Agent**. It serves as the formal functional baseline for engineering, validation, and acceptance testing.

### 1.2 Scope
The system is an autonomous, human-steered research and analytical platform. It accepts high-level research topics, decomposes them into structured subquestions, retrieves data across heterogeneous sources (vector search over internal documents and mock external sources), performs deterministic data analysis and cost calculations, evaluates evidence sufficiency in feedback loops, drafts cited technical reports, and pauses for human-in-the-loop review before final document export.

### 1.3 Target Audience & User Personas
* **Primary Researcher / Decision Maker**: Submits strategic research queries (e.g., database evaluation, cloud architecture trade-offs), reviews draft findings, requests section-level revisions, and exports final PDF/DOCX reports.
* **System Integrator / API Consumer**: Interfaces with the agent programmatically via FastAPI REST endpoints and persists cross-session research states.

---

## 2. System Overview & Core Capabilities

The agent operates across six core functional domains:
1. **Research Planning & Topic Decomposition**: Breaking macro questions into focused research subquestions.
2. **Multi-Source Evidence Gathering**: Semantic search in Qdrant (internal PDFs and markdown) and external mock databases.
3. **Deterministic Numerical Computation**: Exact tabular analysis using Pandas and algorithmic infrastructure cost calculation.
4. **Sufficiency Evaluation & Adaptive Looping**: Self-evaluating evidence adequacy with bounded retry loops.
5. **Cited Technical Synthesis**: Drafting formal reports with source attribution and explicit limitation/unsupported claim flagging.
6. **Non-Destructive Human-in-the-Loop Review**: Checkpoint-based pause/resume enabling approval, section-targeted revision, or rejection without re-running prior research.

---

## 3. Functional Requirements

### 3.1 Topic Ingestion & Decomposition (FR-01)
* **FR-01.1**: The system shall accept a natural language research topic or query string from the user or API.
* **FR-01.2**: The agent shall decompose the primary topic into a minimum of **three (3) distinct research subquestions** covering separate architectural and analytical dimensions (e.g., technical architecture, performance benchmarks, total cost of ownership, compliance).
* **FR-01.3**: The generated subquestions shall be recorded in the persistent agent state schema.

### 3.2 Dual-Source Retrieval (FR-02)
* **FR-02.1**: **Internal Document Retrieval (`search_internal_documents`)**:
  * The system shall execute semantic vector searches against a local Qdrant collection containing chunked internal documents (`database_comparison.pdf` and `architecture_guidelines.md`).
  * The tool shall support metadata filtering by document type (`pdf` vs. `guideline`), domain, and section.
  * Search results shall return chunk content, source file metadata, similarity score, and unique source identifier (`[QDR-xx]`).
* **FR-02.2**: **External Information Retrieval (`search_external_sources`)**:
  * The system shall query an external registry (`research_sources.json`) simulating verified analyst reports and industry benchmark publications.
  * Search results shall include title, publication date, URL, content snippet, reliability rating, and unique source identifier (`[EXT-xx]`).

### 3.3 Deterministic Tabular & Cost Calculations (FR-03)
* **FR-03.1**: **Tabular Data Analysis (`analyze_csv`)**:
  * The system shall execute non-hallucinatory statistical calculations on tabular benchmark data (`benchmark_results.csv`) using Pandas.
  * Supported operations shall include:
    * `summary_stats`: Mean, standard deviation, and count by database and operation.
    * `latency_percentiles`: p50, p95, and p99 read and write latencies.
    * `throughput_comparison`: Peak and average ops/sec by concurrency level.
  * The results shall be registered in the state as `[CSV-xx]`.
* **FR-03.2**: **Cost Calculation Engine (`calculate_cost`)**:
  * The system shall calculate accurate monthly and annual Total Cost of Ownership (TCO) based on `cloud_pricing.json`.
  * The calculation model shall compute instance compute hourly rates, provisioned storage per GB/month, backup retention costs, and support tiers for specified databases over configurable projection horizons (e.g., 12 or 36 months).
  * The results shall be registered in the state as `[COST-xx]`.

### 3.4 Evidence Evaluation & Sufficiency Looping (FR-04)
* **FR-04.1**: Following retrieval and calculations, the system shall evaluate whether the accumulated evidence answers all planned subquestions.
* **FR-04.2**: If evidence gaps or missing metrics are detected:
  * The system shall formulate focused delta queries targeting only the missing information.
  * The workflow shall route back to the evidence-gathering stage.
* **FR-04.3**: **Loop Guardrail**: The re-search loop shall enforce a hard iteration cap (`MAX_RESEARCH_ITERATIONS = 2`). If the threshold is reached without resolving all gaps, the system shall terminate the loop and proceed to drafting, explicitly flagging unresolved areas.

### 3.5 Cited Technical Drafting & Gap Detection (FR-05)
* **FR-05.1**: The agent shall synthesize all collected evidence into a structured technical report containing standard sections:
  * Executive Summary
  * Architectural Comparison & Isolation Analysis
  * Performance Benchmark Evaluation
  * Total Cost of Ownership (TCO) Breakdown
  * Compliance & Data Sovereignty Assessment
  * Strategic Recommendation
* **FR-05.2**: **Factual Attribution**: Every factual assertion and numerical figure must cite its canonical source identifier (e.g., `[QDR-01]`, `[CSV-01]`, `[COST-01]`, `[EXT-02]`).
* **FR-05.3**: **Unsupported Claim Detection**: Any assertion made without supporting evidence in the active evidence registry must be identified, isolated, and listed under an explicit `unsupported_claims` section.

### 3.6 Human-in-the-Loop Review & Revision (FR-06)
* **FR-06.1**: **State Interruption**: Upon draft generation, the graph must pause execution using LangGraph's checkpointed `interrupt()` mechanism, transitioning the workflow to `review_pending`.
* **FR-06.2**: **Review Options**: The system shall expose three distinct decision pathways to the human reviewer:
  1. **Approve (`approved`)**: Accepts the report draft and triggers final document generation.
  2. **Revise (`revise`)**: Specifies human feedback notes and a list of target section names (e.g., `["Cost Analysis"]`).
  3. **Reject (`rejected`)**: Terminates the workflow with recorded feedback comments.
* **FR-06.3**: **Non-Destructive Revision**: When `revise` is invoked:
  * All previously accumulated evidence, CSV stats, and cost models must be preserved.
  * The agent shall rewrite **only** the designated target sections incorporating the reviewer's feedback.
  * The revised draft shall be presented back for human review.

### 3.7 Report Export (FR-07)
* **FR-07.1**: The system shall export approved reports to publication-ready **PDF** (via ReportLab) and/or **DOCX** (via python-docx).
* **FR-07.2**: Exported documents must include formatted headings, structured benchmark tables, callout blocks for recommendations/unsupported claims, and a complete bibliographic reference list.
* **FR-07.3**: The export tool shall return the deterministic file path in the `reports/` directory.

---

## 4. External Tool Specifications

| Tool Identifier | Function Signature | Description | Output Schema |
| :--- | :--- | :--- | :--- |
| `search_internal_documents` | `(query: str, filters: dict = None) -> list[dict]` | Queries Qdrant vector database using cosine similarity | List of chunks with `source_id`, `content`, `score`, `metadata` |
| `search_external_sources` | `(query: str) -> list[dict]` | Keyword/semantic search on external sources registry | List of items with `source_id`, `title`, `url`, `date`, `snippet`, `reliability_score` |
| `analyze_csv` | `(file_path: str, operation: str) -> dict` | Executes Pandas statistical calculations on CSV data | Dictionary containing structured numerical metrics |
| `calculate_cost` | `(config: dict) -> dict` | Computes deterministic TCO from pricing matrices | Dictionary with monthly/annual totals by database |
| `generate_report` | `(content: dict, format: str = "pdf") -> str` | Compiles structured report dictionary into document file | File system path string (`reports/<filename>.<ext>`) |

---

## 5. Non-Functional Requirements (NFR)

* **NFR-01 (Persistence)**: Research state and thread checkpoints must persist in SQLite (`data/checkpoints.db`) or PostgreSQL, surviving process restarts.
* **NFR-02 (Determinism & Anti-Hallucination)**: Numerical benchmarks and cost statistics must originate exclusively from tool outputs, never from LLM generative arithmetic.
* **NFR-03 (Fault Tolerance & Error Recovery)**: Missing files, malformed JSON, or tool timeouts must raise structured exceptions without crashing the LangGraph execution flow.
* **NFR-04 (Traceability & Observability)**: Every step, tool invocation, and decision branch must be traceable via LangSmith or local audit logging.
* **NFR-05 (Portability)**: The system must run in an embedded mode (embedded Qdrant, SQLite checkpointing) without mandatory external Docker or cloud daemon dependencies for local development.

---

## 6. Acceptance Criteria Matrix

| ID | Criterion | Verification Method |
| :--- | :--- | :--- |
| **AC-01** | Topic decomposition produces ≥ 3 subquestions | Automated unit/graph test |
| **AC-02** | Retrieval accesses Qdrant and external mock source | Tool execution log inspection |
| **AC-03** | Pipeline executes ≥ 4 distinct tools, including a calculation tool | Tool call audit trail |
| **AC-04** | Dynamic loop triggers when evidence is insufficient and halts at max limit | Test with simulated missing data |
| **AC-05** | Factual claims cite `[source_id]` tags; unsupported claims are flagged | Draft schema verification |
| **AC-06** | State and reviewer decisions persist across sessions | Checkpointer DB persistence test |
| **AC-07** | Pipeline supports approve, revise, and reject review branches | Human-in-the-loop branch test |
| **AC-08** | Revision updates only designated sections and preserves existing evidence | State diff check before/after revision |
| **AC-09** | Approved report exports valid, readable PDF and DOCX documents | File format & content validation |
| **AC-10** | System passes a suite of 10+ comprehensive automated tests | Pytest execution suite |
