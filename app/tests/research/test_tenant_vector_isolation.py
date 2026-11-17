"""Unit tests for tenant-scoped vector isolation with row-level and collection-level security."""

from unittest.mock import MagicMock

from app.services.core_services.qdrant_ingestion import QdrantDocumentIngestor
from app.tools.internal_search_tool import InternalDocumentRetriever


def test_get_tenant_collection_name_sanitizes_identifiers():
    """Verify collection-level security produces safe, deterministic isolated collection names."""
    base_name = "research_documents"
    safe_name = QdrantDocumentIngestor.get_tenant_collection_name(
        base_name, "Tenant-Alpha.123!"
    )
    assert safe_name == "research_documents_t_tenant_alpha_123_"
    assert "." not in safe_name
    assert "!" not in safe_name


def test_search_injects_tenant_id_filter():
    """Verify search method injects row-level tenant security filter into Qdrant query_points."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.points = []
    mock_client.query_points.return_value = mock_response

    ingestor = QdrantDocumentIngestor()

    ingestor.search(
        query="database scaling",
        limit=5,
        client=mock_client,
        tenant_id="tenant_org_42",
    )

    mock_client.query_points.assert_called_once()
    call_kwargs = mock_client.query_points.call_args[1]
    effective_filter = call_kwargs["query_filter"]

    assert effective_filter is not None
    assert len(effective_filter.must) >= 1
    tenant_cond = effective_filter.must[0]
    assert tenant_cond.key == "tenant_id"
    assert tenant_cond.match.value == "tenant_org_42"


def test_internal_retriever_propagates_tenant_isolation():
    """Verify InternalDocumentRetriever passes tenant_id to underlying Qdrant query."""
    retriever = InternalDocumentRetriever()

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.points = []
    mock_client.query_points.return_value = mock_response

    from app.services.core_services.qdrant_ingestion import default_qdrant_ingestor

    original_client = default_qdrant_ingestor._qdrant_client
    default_qdrant_ingestor._qdrant_client = mock_client

    try:
        retriever.search(
            query="PostgreSQL vs MongoDB",
            limit=3,
            tenant_id="tenant_finance_99",
        )
        mock_client.query_points.assert_called_once()
        filter_arg = mock_client.query_points.call_args[1]["query_filter"]
        assert filter_arg is not None
        assert filter_arg.must[0].match.value == "tenant_finance_99"
    finally:
        default_qdrant_ingestor._qdrant_client = original_client
