"""
Export convenient imports for all 5 research and calculation tools, both as standard callables and LangChain StructuredTool instances.
"""

from src.tools.cost_calculator import calculate_cost, calculate_cost_tool
from src.tools.external_search import search_external_sources, search_external_sources_tool
from src.tools.internal_search import search_internal_documents, search_internal_documents_tool
from src.tools.report_exporter import generate_report, generate_report_tool
from src.tools.tabular_analysis import analyze_csv, analyze_csv_tool

__all__ = [
    # Callables
    "search_internal_documents",
    "search_external_sources",
    "analyze_csv",
    "calculate_cost",
    "generate_report",
    # LangChain StructuredTool instances
    "search_internal_documents_tool",
    "search_external_sources_tool",
    "analyze_csv_tool",
    "calculate_cost_tool",
    "generate_report_tool",
]
