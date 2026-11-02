# AI Research & Report Generation Agent

[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/release/python-3120/)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2+-orange.svg)](https://github.com/langchain-ai/langgraph)
[![Qdrant](https://img.shields.io/badge/Qdrant-1.12+-red.svg)](https://qdrant.tech/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

An enterprise-grade, autonomous AI research and decision report generation agent built with **LangChain**, **LangGraph**, **Qdrant**, **FastAPI**, **Pandas**, **ReportLab**, and **python-docx**.

The agent systematically decomposes technical decision topics, queries internal vector knowledge bases and external sources, executes deterministic statistical calculations and cloud TCO cost models, evaluates evidence completeness in an iterative loop, synthesizes fully cited technical reports with explicit unsupported claim tracking, and pauses at persistence checkpoints for Human-in-the-Loop review before exporting publication-grade PDF and Word documents.

---

## 🏛 System Architecture

The workflow is modeled as a stateful, cyclical graph in LangGraph with state persistence and human interrupt gates:

```mermaid
flowchart TD
    START([Start Workflow]) --> N1[1. plan_research<br/>Decompose into &ge;3 subquestions]
    N1 --> N2[2. gather_evidence<br/>Qdrant vector search + External sources]
    N2 --> N3[3. execute_calculations<br/>Pandas benchmark statistics + TCO cost engine]
    N3 --> N4[4. evaluate_evidence<br/>Assess coverage & identify gaps]

    N4 --> CondSuff{Evidence<br/>Sufficient?}
    CondSuff -- "No (iterations &lt; 2)" --> N2
    CondSuff -- "Yes (or max iterations)" --> N5[5. draft_report<br/>Cite sources & flag unsupported claims]

    subgraph HITL [Human-in-the-Loop Checkpoint]
        N5 --> N6[6. human_review<br/>interrupt() checkpoint boundary]
        N6 -.-> UserDecision{Reviewer Decision}
    end

    UserDecision -- "revise" --> N7[7. revise_sections<br/>Preserve evidence & patch named sections]
    N7 --> N6

    UserDecision -- "reject" --> N8([Workflow Terminated])

    UserDecision -- "approve" --> N9[8. export_report<br/>Generate Publication PDF / DOCX]
    N9 --> END([Final Report Exported])
```

---

## 🚀 Key Features

- **Strict Factual Grounding**: Every assertion is backed by canonical citations (`[QDR-xx]`, `[EXT-xx]`, `[CSV-01]`, `[COST-01]`).
- **Hallucination-Free Math**: Analytical benchmarks (p50/p95/p99 latencies, ops/sec throughput) and cloud TCO economics are computed deterministically via Pandas and Python math engines rather than LLM token generation.
- **Unsupported Claim Detection**: Claims that lack ground backing in the evidence catalog are isolated and surfaced in a dedicated limitations section.
- **Evidence Sufficiency Re-search Loop**: Automatically evaluates evidence completeness and re-searches up to `MAX_RESEARCH_ITERATIONS` to fill identified gaps.
- **Human-in-the-Loop (HITL) Checkpoints**: Utilizes LangGraph's native `interrupt()` and `Command(resume=...)` to pause execution, allowing reviewers to **approve**, **reject**, or request **surgical section revisions** without re-running previous research.
- **Publication-Ready Export**: Produces high-resolution corporate PDFs using ReportLab flowables and Microsoft Word `.docx` documents.
- **Dual-Mode Deployment**: Runs seamlessly with containerized Docker services (Qdrant & PostgreSQL) or fully local embedded fallbacks (`data/qdrant_storage` and SQLite).

---

## 📂 Project Structure

```text
├── data/
│   ├── sample_data/
│   │   ├── database_comparison.pdf        # Ingested PDF document
│   │   ├── benchmark_results.csv          # 28 rows of latency/throughput metrics
│   │   ├── cloud_pricing.json             # Compute, storage, backup & support rates
│   │   ├── research_sources.json          # Mock external analyst sources
│   │   └── architecture_guidelines.md     # Engineering compliance mandates
│   ├── qdrant_storage/                    # Embedded Qdrant storage directory
│   ├── cache/                             # Local FastEmbed model cache
│   └── checkpoints.db                     # SQLite persistence checkpoints
├── docs/
│   ├── FRS.md                             # Functional Requirements Specification
│   └── SDS.md                             # Software Design Specification
├── reports/                               # Output directory for generated PDF/DOCX
├── src/
│   ├── config.py                          # Centralized settings & dual-mode paths
│   ├── state.py                           # ResearchState & EvidenceItem TypedDicts
│   ├── ingestion/
│   │   └── ingest_qdrant.py               # Document chunking & FastEmbed vectorizer
│   ├── tools/
│   │   ├── internal_search.py             # Qdrant semantic search [QDR-xx]
│   │   ├── external_search.py             # External source retrieval [EXT-xx]
│   │   ├── tabular_analysis.py            # Pandas benchmark analysis [CSV-01]
│   │   ├── cost_calculator.py             # Cloud TCO pricing engine [COST-01]
│   │   └── report_exporter.py             # Publication PDF & Word builder
│   ├── graph/
│   │   ├── prompts.py                     # Structured LLM prompt templates
│   │   ├── nodes.py                       # 8 workflow node functions
│   │   ├── edges.py                       # Conditional sufficiency & review routers
│   │   ├── builder.py                     # StateGraph assembly & compilation
│   │   └── checkpoints.py                 # SQLite/PostgreSQL checkpoint management
│   └── server/
│       ├── app.py                         # FastAPI REST application
│       └── static/
│           └── index.html                 # Single-page HITL review dashboard
├── tests/
│   ├── test_config.py                     # Config & directory tests
│   ├── test_sample_data.py                # Sample dataset integrity tests
│   ├── test_ingestion.py                  # Qdrant ingestion & filtering tests
│   ├── test_tools.py                      # 5 tools verification tests
│   ├── test_nodes.py                      # 8 node functions tests
│   ├── test_graph.py                      # Graph wiring & conditional routing tests
│   ├── test_checkpoints.py                # HITL pause, resume, and persistence tests
│   └── test_server.py                     # FastAPI REST endpoint tests
├── docker-compose.yml                     # Qdrant & PostgreSQL services
├── Dockerfile                             # Containerized API server
├── main.py                                # CLI execution entrypoint
└── requirements.txt                       # Project dependencies
```

---

## 🛠 Quickstart Guide

### 1. Prerequisites
- Python 3.12+
- Docker Desktop (Optional; agent automatically falls back to embedded storage if Docker is offline)

### 2. Environment Setup
```bash
# Clone the repository
git clone https://github.com/Trilo1999/Tech-Report-Generator.git
cd Tech-Report-Generator

# Create and activate virtual environment
python3.12 -m venv venv
source venv/bin/activate

# Install all dependencies
pip install -r requirements.txt

# Configure environment variables (optional; defaults work out of the box)
cp .env.example .env
```

### 3. Start Optional Infrastructure (Docker)
```bash
# Start Qdrant and PostgreSQL
docker-compose up -d
```
*Note: If Docker is not running, the application automatically uses local embedded Qdrant (`data/qdrant_storage`) and SQLite checkpoints (`data/checkpoints.db`).*

---

## 💻 Usage

### Option 1: Interactive Terminal CLI
Run the full workflow directly from your terminal:
```bash
# Interactive mode (prompts for human review)
python main.py --topic "PostgreSQL vs MongoDB Architecture Evaluation"

# Headless mode (auto-approves and exports PDF)
python main.py --topic "PostgreSQL vs MongoDB Architecture Evaluation" --auto-approve
```

### Option 2: FastAPI Server & Web Review Dashboard
Start the web server:
```bash
uvicorn src.server.app:app --host 0.0.0.0 --port 8000 --reload
```
- **Web Dashboard**: Navigate to `http://localhost:8000` to access the interactive review station.
- **Interactive Swagger Docs**: Navigate to `http://localhost:8000/docs`.

---

## 📡 REST API Reference

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/` | Serves the single-page HTML review dashboard |
| `POST` | `/api/research/start` | Initializes research; returns `thread_id` and pauses at review checkpoint |
| `GET` | `/api/research/status/{thread_id}` | Retrieves full state snapshot, draft report, evidence items, and pending next nodes |
| `POST` | `/api/research/review/{thread_id}` | Delivers review verdict (`approved`, `revise`, `rejected`) and resumes thread |
| `GET` | `/api/research/download/{thread_id}`| Downloads the approved publication PDF report |

---

## 🧪 Testing & Verification

The project includes an exhaustive automated test suite with **51 tests** covering all layers:

```bash
# Run the entire test suite
pytest -v

# Run with test coverage
pytest --cov=src -v

# Verify code formatting and linting
pre-commit run --all-files
```

### Test Suite Breakdown:
- `tests/test_config.py` (4 tests): Path constants and environment settings.
- `tests/test_sample_data.py` (5 tests): PDF, CSV, JSON pricing, and Markdown guidelines validity.
- `tests/test_ingestion.py` (8 tests): Chunking, cosine similarity retrieval, metadata filtering, idempotency.
- `tests/test_tools.py` (15 tests): Qdrant search, mock search, Pandas operations, exact TCO math, and ReportLab export.
- `tests/test_nodes.py` (10 tests): Planning $\ge 3$ subquestions, evidence gathering, sufficiency evaluation, draft generation, and surgical revision.
- `tests/test_graph.py` (6 tests): Graph compilation, conditional routers (`route_sufficiency`, `route_review`), and end-to-end branch execution.
- `tests/test_checkpoints.py` (5 tests): SQLite persistence, interrupt verification, and resume cycles.
- `tests/test_server.py` (3 tests): FastAPI REST lifecycle, status polling, and PDF download.

---

## 📄 License
This project is licensed under the MIT License - see the LICENSE file for details.
