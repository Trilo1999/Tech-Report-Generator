"""
HyDE (Hypothetical Document Embeddings) and Multi-Query Expansion Engine.

Enhances vector retrieval precision and semantic recall by:
1. Decomposing research queries into multiple technical dimensions (Multi-Query Expansion).
2. Generating hypothetical ideal answers to capture semantic neighborhood vectors (HyDE).
3. Fusing multiple ranked retrieval candidate sets via Reciprocal Rank Fusion (RRF).
"""

from typing import Any, Callable, Dict, List

from app.config.log_config import logger


class HyDEEngine:
    """Hypothetical Document Embeddings and multi-angle query decomposition engine."""

    @classmethod
    def expand_queries(cls, query: str, num_queries: int = 3) -> List[str]:
        """Decompose a query into multiple diversified technical perspectives.

        Args:
            query: Base research query.
            num_queries: Number of target sub-query variations.

        Returns:
            List containing original query and expanded perspectives.
        """
        if not query or not query.strip():
            return []

        expanded = [query.strip()]
        lower_q = query.lower()

        # Domain heuristic expansion
        if any(
            k in lower_q
            for k in ("database", "postgres", "mongo", "sql", "nosql", "sharding")
        ):
            expanded.append(
                f"{query} architectural trade-offs, consistency models, and transaction isolation"
            )
            expanded.append(
                f"{query} empirical read write throughput, p95 latency benchmarks under concurrent load"
            )
            expanded.append(
                f"{query} horizontal clustering, automated failover, and total cost of ownership"
            )
        elif any(k in lower_q for k in ("aws", "azure", "gcp", "cloud")):
            expanded.append(
                f"{query} enterprise security governance, IAM permission boundaries, and compliance"
            )
            expanded.append(
                f"{query} multi-region high availability, network egress costs, and 3-year TCO"
            )
        else:
            expanded.append(
                f"{query} enterprise architecture standards and implementation guidelines"
            )
            expanded.append(
                f"{query} operational scalability limits and production failure modes"
            )

        return list(dict.fromkeys(expanded))[: num_queries + 1]

    @classmethod
    def generate_hypothetical_document(
        cls, query: str, domain: str = "enterprise_architecture"
    ) -> str:
        """Generate a hypothetical technical document passage answering the query (HyDE).

        Vectorizing this synthetic answer matches real documentation closer than the brief query alone.

        Args:
            query: Technical research question.
            domain: Technical domain context.

        Returns:
            Detailed hypothetical document passage.
        """
        import os

        fallback_hyde = (
            f"Technical Architecture Reference: For {query}, enterprise production standards "
            "recommend decoupling high-throughput analytical query workloads from primary transactional data stores. "
            "Under rigorous concurrency testing, sustained p95 latency boundaries remain within enterprise SLAs through "
            "connection pooling, distributed caching, partition pruning, and automated failover topologies."
        )

        if os.getenv("MOCK_LLM", "false").lower() == "true":
            return fallback_hyde

        from app.config.env_config import settings

        # In test environments with mock/test keys, use deterministic synthetic fallback
        test_keys = (settings.GEMINI_API_KEY or "", settings.OPENAI_API_KEY or "")
        if any("test" in k.lower() or "dummy" in k.lower() for k in test_keys):
            return fallback_hyde

        try:
            from app.llms.llm_factory import get_default_chat_client

            client = get_default_chat_client()
            prompt = (
                f"You are a Principal Software Architect drafting an internal enterprise engineering document. "
                f"Write a dense, 2-to-3 sentence technical passage that directly answers: '{query}'. "
                f"Include specific architectural mechanisms, concurrency controls, and failure isolation details."
            )
            response = client.invoke(prompt)
            content = (
                response.content if hasattr(response, "content") else str(response)
            )
            if content and len(content.strip()) > 30:
                return content.strip()
        except Exception as exc:
            logger.debug("HyDE generation LLM call skipped fallback used: %s", exc)

        return fallback_hyde

    @classmethod
    def retrieve_with_hyde_and_multi_query(
        cls,
        retriever_func: Callable[..., List[Dict[str, Any]]],
        query: str,
        limit: int = 4,
        use_hyde: bool = True,
        use_multi_query: bool = True,
        **retriever_kwargs: Any,
    ) -> List[Dict[str, Any]]:
        """Execute multi-angle retrieval fused with Reciprocal Rank Fusion (RRF).

        Args:
            retriever_func: Underlying retrieval callable (e.g. search_internal_documents).
            query: Original user/agent query.
            limit: Maximum number of merged results to return.
            use_hyde: Whether to generate and search with a hypothetical document.
            use_multi_query: Whether to expand the query into multiple perspectives.
            retriever_kwargs: Additional kwargs passed to retriever_func (e.g. tenant_id, filters).

        Returns:
            Ranked, deduplicated list of evidence dictionaries.
        """
        queries_to_run = [query]
        if use_multi_query:
            queries_to_run = cls.expand_queries(query, num_queries=2)

        if use_hyde:
            hypothetical_doc = cls.generate_hypothetical_document(query)
            queries_to_run.append(hypothetical_doc)

        # Collect candidate lists per query
        all_results_by_query: List[List[Dict[str, Any]]] = []
        for q in queries_to_run:
            try:
                res = retriever_func(query=q, limit=limit, **retriever_kwargs)
                if res:
                    all_results_by_query.append(res)
            except Exception as exc:
                logger.debug("Retrieval failed for query variant '%s': %s", q, exc)

        if not all_results_by_query:
            # Fall back to single direct query
            return retriever_func(query=query, limit=limit, **retriever_kwargs)

        # Reciprocal Rank Fusion (RRF) scoring: RRF(d) = sum(1 / (60 + rank))
        rrf_scores: Dict[str, float] = {}
        doc_map: Dict[str, Dict[str, Any]] = {}

        for candidate_list in all_results_by_query:
            for rank, doc in enumerate(candidate_list):
                doc_key = doc.get("content", "")[:120].strip() or doc.get(
                    "source_id", ""
                )
                if not doc_key:
                    continue
                rrf_scores[doc_key] = rrf_scores.get(doc_key, 0.0) + (
                    1.0 / (60.0 + rank)
                )
                if doc_key not in doc_map:
                    doc_map[doc_key] = doc

        # Sort by RRF score descending
        ranked_keys = sorted(
            rrf_scores.keys(), key=lambda k: rrf_scores[k], reverse=True
        )

        fused_results: List[Dict[str, Any]] = []
        for k in ranked_keys[:limit]:
            doc = doc_map[k]
            fused_doc = dict(doc)
            # Store RRF fusion score metadata
            fused_doc["rrf_score"] = round(rrf_scores[k], 5)
            fused_results.append(fused_doc)

        return fused_results
