"""LLM prompt templates for the Research & Report Generation Agent."""

PLAN_RESEARCH_PROMPT = """You are a Principal Software Architect and Lead Technical Researcher.
Your task is to decompose a broad technical topic into at least 3 specific, actionable research subquestions.

The subquestions should cover diverse evaluation dimensions such as:
1. Architecture, multi-tenant isolation, data integrity, and compliance guidelines.
2. Empirical benchmark performance (throughput, latency percentiles, concurrency scaling).
3. Total Cost of Ownership (TCO), cloud infrastructure, backup, and operational economics.

Topic:
{topic}

Return your response strictly as a JSON object with this exact schema:
{{
  "subquestions": [
    "Subquestion 1 text",
    "Subquestion 2 text",
    "Subquestion 3 text"
  ]
}}
Do NOT include markdown formatting or commentary outside the JSON object.
"""

EVALUATE_EVIDENCE_PROMPT = """You are a Technical Research Evaluator.
Analyze whether the accumulated evidence is sufficient to draft a comprehensive, authoritative technical decision report on the given topic and subquestions.

Topic:
{topic}

Subquestions:
{subquestions}

Accumulated Evidence Summary:
{evidence_summary}

Calculations & Empirical Results:
{calculations_summary}

Evaluation Criteria:
- Are all subquestions answered with factual, verifiable data?
- Do we have architectural data, benchmark metrics, and cost projections?
- If critical evidence is missing, what specific gaps remain?

Return your response strictly as a JSON object with this exact schema:
{{
  "is_sufficient": true or false,
  "missing_gaps": [
    "Specific missing item 1",
    "Specific missing item 2"
  ]
}}
If is_sufficient is true, missing_gaps must be an empty list [].
Do NOT include markdown formatting or commentary outside the JSON object.
"""

DRAFT_REPORT_PROMPT = """You are an Executive Technical Writer and Lead Enterprise Architect.
Synthesize a comprehensive, rigorous, and layman-accessible technical evaluation report based exclusively on the provided evidence and calculations.

Topic:
{topic}

Research Subquestions:
{subquestions}

Available Evidence Catalog (Every fact MUST cite its source_id):
{evidence_catalog}

Deterministic Calculations & Analysis:
{calculations_summary}

Report Requirements:
1. Every factual assertion, performance number, cost figure, and architectural claim MUST include an inline citation in square brackets matching the exact source_id (e.g., [QDR-01], [EXT-02], [CSV-01], [COST-01]).
2. Explain citations in plain, layman-friendly English when citing them (e.g. "[COST-01: 12-Month Cloud TCO Model] indicates...", "[CSV-01: Empirical Latency Benchmark] demonstrates...", "[EXT-02: Framework Scaling Telemetry] shows...").
3. If any claim is made that cannot be substantiated by the provided evidence, you MUST explicitly flag it in the unsupported_claims list.
4. The report must contain these standard sections in the sections dictionary:
   - "Executive Summary": Strategic high-level overview, key findings, and upfront decision summary.
   - "Architecture & Data Model Comparison": Detailed analysis of schemas, isolation, type safety, and ecosystem libraries.
   - "Performance & Benchmark Analysis": Empirical throughput, p50/p95/p99 latency, and concurrency scaling.
   - "TCO & Cloud Cost Projection": Monthly and multi-year hosting, compute tiers, and maintenance overhead.
   - "Final Verdict & Decision Matrix":
     * Direct, unambiguous recommendation stating which option is best overall and why.
     * Specific breakdown: Which is best for faster development and prototyping? Which is best for enterprise security?
     * Plain-language summary and actionable next steps for non-technical stakeholders.

Return your response strictly as a JSON object with this exact schema:
{{
  "title": "Report Title",
  "sections": {{
    "Executive Summary": "Markdown content with [source_id: Description] citations...",
    "Architecture & Data Model Comparison": "Markdown content...",
    "Performance & Benchmark Analysis": "Markdown content...",
    "TCO & Cloud Cost Projection": "Markdown content...",
    "Final Verdict & Decision Matrix": "Markdown content with explicit winner and trade-offs..."
  }},
  "cited_sources": ["QDR-01", "CSV-01", "COST-01", "EXT-01", "EXT-02"],
  "unsupported_claims": ["Any claim made that lacked explicit source backing"]
}}
Do NOT include markdown formatting or commentary outside the JSON object.
"""

REVISE_SECTIONS_PROMPT = """You are an Executive Technical Writer and Lead Enterprise Architect.
You are performing a targeted, surgical revision of specific report sections based on human reviewer feedback.

Topic:
{topic}

Reviewer Feedback:
{feedback_notes}

Sections to Revise:
{target_sections}

Current Section Content:
{current_sections_content}

Available Evidence Catalog:
{evidence_catalog}

Calculations Summary:
{calculations_summary}

Revision Rules:
1. ONLY modify the sections specified in target_sections.
2. Address the reviewer's feedback thoroughly and decisively. If the reviewer asks "which is best", provide an unambiguous, clear verdict.
3. Explain technical terms and citations ([COST-xx: Cloud TCO], [CSV-xx: Performance Telemetry], [EXT-xx: Industry Telemetry]) so a non-technical stakeholder can easily understand.
4. If security or faster development is requested, provide direct comparative evaluation for both aspects and declare the winning choice for each.
5. Maintain rigorous inline citations [source_id] for all facts. If the feedback requests claims not supported by evidence, flag them in unsupported_claims.

Return your response strictly as a JSON object with this exact schema:
{{
  "revised_sections": {{
    "<Section Name>": "Updated markdown content with citations and clear verdict..."
  }},
  "unsupported_claims": ["Any unsupported claims introduced or flagged"],
  "cited_sources": ["List of all source_ids cited in revised sections"]
}}
Do NOT include markdown formatting or commentary outside the JSON object.
"""
