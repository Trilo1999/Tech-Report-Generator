"""
Tabular benchmark analysis tool powered by Pandas.

Executes deterministic aggregations, latency percentiles, and concurrency scaling
statistics from benchmark_results.csv. Ensures non-hallucinatory numerical facts.
"""

from pathlib import Path
from typing import Any, Dict, Optional
from langchain_core.tools import tool
import numpy as np
import pandas as pd
from pydantic import BaseModel, Field

from src.config import BENCHMARK_CSV


def analyze_csv(
    file_path: Optional[str] = None,
    operation: str = "summary_stats",
    filter_database: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Execute deterministic statistical calculations on tabular benchmark CSV data.

    Supported operations:
        - "summary_stats": Grouped mean, std, min, max for latency and throughput.
        - "latency_percentiles": p50, p90, p95, p99 latency by database and operation.
        - "concurrency_scaling": Performance metrics grouped across concurrency levels (50, 100, 200).
        - "headroom_comparison": Summary comparison between PostgreSQL and MongoDB.

    Args:
        file_path: Optional custom path to benchmark CSV (default: BENCHMARK_CSV).
        operation: Calculation operation to perform.
        filter_database: Optional database filter (e.g., "PostgreSQL" or "MongoDB").

    Returns:
        Structured dictionary tagged with [CSV-01] containing exact numeric metrics.
    """
    csv_file = Path(file_path) if file_path else BENCHMARK_CSV
    if not csv_file.is_file():
        raise FileNotFoundError(f"Benchmark CSV file not found: {csv_file}")

    df = pd.read_csv(csv_file)
    if df.empty:
        raise ValueError("Benchmark CSV file is empty")

    required_columns = {"database", "operation", "latency_ms", "throughput_ops_sec", "concurrency_level"}
    if not required_columns.issubset(set(df.columns)):
        raise ValueError(f"CSV missing required benchmark columns: {required_columns - set(df.columns)}")

    if filter_database:
        df = df[df["database"].str.lower() == filter_database.lower()]
        if df.empty:
            raise ValueError(f"No records found matching database filter: {filter_database}")

    result_data: Dict[str, Any] = {}

    if operation == "summary_stats":
        # Group by database and operation, compute mean, std, min, max
        grouped = df.groupby(["database", "operation"])
        stats_dict: Dict[str, Dict[str, Any]] = {}

        for (db, op), group in grouped:
            if db not in stats_dict:
                stats_dict[db] = {}
            stats_dict[db][op] = {
                "mean_latency_ms": round(float(group["latency_ms"].mean()), 2),
                "std_latency_ms": round(float(group["latency_ms"].std()), 2) if len(group) > 1 else 0.0,
                "min_latency_ms": round(float(group["latency_ms"].min()), 2),
                "max_latency_ms": round(float(group["latency_ms"].max()), 2),
                "mean_throughput_ops_sec": round(float(group["throughput_ops_sec"].mean()), 2),
                "max_throughput_ops_sec": int(group["throughput_ops_sec"].max()),
                "sample_count": int(len(group)),
            }
        result_data = stats_dict

    elif operation == "latency_percentiles":
        # Compute p50, p90, p95, p99
        grouped = df.groupby(["database", "operation"])
        p_dict: Dict[str, Dict[str, Any]] = {}

        for (db, op), group in grouped:
            if db not in p_dict:
                p_dict[db] = {}
            latencies = group["latency_ms"].values
            p_dict[db][op] = {
                "p50_latency_ms": round(float(np.percentile(latencies, 50)), 2),
                "p90_latency_ms": round(float(np.percentile(latencies, 90)), 2),
                "p95_latency_ms": round(float(np.percentile(latencies, 95)), 2),
                "p99_latency_ms": round(float(np.percentile(latencies, 99)), 2),
                "sample_count": int(len(group)),
            }
        result_data = p_dict

    elif operation == "concurrency_scaling":
        # Analyze latency/throughput degradation across concurrency levels (50, 100, 200)
        scaling_dict: Dict[str, Any] = {}
        grouped = df.groupby(["database", "concurrency_level"])

        for (db, conc), group in grouped:
            if db not in scaling_dict:
                scaling_dict[db] = {}
            scaling_dict[db][int(conc)] = {
                "mean_read_latency_ms": round(float(group[group["operation"] == "read"]["latency_ms"].mean()), 2)
                if any(group["operation"] == "read")
                else None,
                "mean_write_latency_ms": round(float(group[group["operation"] == "write"]["latency_ms"].mean()), 2)
                if any(group["operation"] == "write")
                else None,
                "total_throughput_ops_sec": int(group["throughput_ops_sec"].sum()),
            }
        result_data = scaling_dict

    elif operation == "headroom_comparison":
        # High-level direct comparison summary
        dbs = df["database"].unique()
        comparison: Dict[str, Any] = {}
        for db in dbs:
            read_df = df[(df["database"] == db) & (df["operation"] == "read")]
            write_df = df[(df["database"] == db) & (df["operation"] == "write")]
            comparison[db] = {
                "avg_read_latency_ms": round(float(read_df["latency_ms"].mean()), 2),
                "p95_read_latency_ms": round(float(np.percentile(read_df["latency_ms"].values, 95)), 2),
                "avg_write_latency_ms": round(float(write_df["latency_ms"].mean()), 2),
                "p95_write_latency_ms": round(float(np.percentile(write_df["latency_ms"].values, 95)), 2),
                "peak_throughput_ops_sec": int(df[df["database"] == db]["throughput_ops_sec"].max()),
            }
        result_data = comparison

    else:
        raise ValueError(
            f"Unsupported operation: '{operation}'. "
            f"Supported: 'summary_stats', 'latency_percentiles', 'concurrency_scaling', 'headroom_comparison'"
        )

    return {
        "source_id": "CSV-01",
        "source_type": "tabular_csv",
        "title": f"Benchmark Performance Statistics ({operation})",
        "file_name": csv_file.name,
        "operation": operation,
        "data": result_data,
        "reliability_score": 1.0,
    }


class TabularAnalysisInput(BaseModel):
    operation: str = Field(
        "summary_stats",
        description="Calculation operation: 'summary_stats' (mean/min/max/std), 'latency_percentiles' (p50/p90/p95/p99), 'concurrency_scaling' (50/100/200 load tiers), or 'headroom_comparison'.",
    )
    filter_database: Optional[str] = Field(
        None,
        description="Optional entity or database name filter, e.g. 'PostgreSQL', 'MongoDB', 'AWS', 'Azure', 'Python', 'React'.",
    )
    file_path: Optional[str] = Field(
        None,
        description="Optional custom file path to benchmark CSV (defaults to benchmark_results.csv).",
    )


@tool("analyze_csv", args_schema=TabularAnalysisInput)
def analyze_csv_tool(
    operation: str = "summary_stats",
    filter_database: Optional[str] = None,
    file_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Execute deterministic Pandas analytical calculations on tabular benchmark telemetry data.
    Computes exact throughput ops/sec, latency percentiles, and concurrency scaling.
    """
    return analyze_csv(file_path=file_path, operation=operation, filter_database=filter_database)
