"""
Tabular benchmark analysis tool powered by Pandas implementing OOP patterns.

Executes deterministic aggregations, latency percentiles, and concurrency scaling
statistics from benchmark_results.csv. Ensures non-hallucinatory numerical facts.
"""

from pathlib import Path
from typing import Any, Dict, Optional, Type

import numpy as np
import pandas as pd
from langchain_core.tools import BaseTool, tool
from pydantic import BaseModel, Field

from app.config.env_config import BENCHMARK_CSV


class TabularAnalyzer:
    """Object-oriented engine for benchmark telemetry data loading, validation, and analytics."""

    def __init__(self, default_file_path: Optional[Path] = None):
        self.default_file_path = default_file_path or BENCHMARK_CSV

    def load_dataframe(
        self,
        file_path: Optional[str] = None,
        filter_database: Optional[str] = None,
    ) -> tuple[pd.DataFrame, Path]:
        """Load and validate benchmark CSV into a Pandas DataFrame."""
        csv_file = Path(file_path) if file_path else self.default_file_path
        if not csv_file.is_file():
            raise FileNotFoundError(f"Benchmark CSV file not found: {csv_file}")

        df = pd.read_csv(csv_file)
        if df.empty:
            raise ValueError("Benchmark CSV file is empty")

        required_columns = {
            "database",
            "operation",
            "latency_ms",
            "throughput_ops_sec",
            "concurrency_level",
        }
        if not required_columns.issubset(set(df.columns)):
            raise ValueError(
                f"CSV missing required benchmark columns: {required_columns - set(df.columns)}"
            )

        if filter_database:
            df = df[df["database"].str.lower() == filter_database.lower()]
            if df.empty:
                raise ValueError(
                    f"No records found matching database filter: {filter_database}"
                )

        return df, csv_file

    def compute_summary_stats(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Group by database and operation, compute mean, std, min, max, throughput."""
        grouped = df.groupby(["database", "operation"])
        stats_dict: Dict[str, Dict[str, Any]] = {}

        for (db, op), group in grouped:
            if db not in stats_dict:
                stats_dict[db] = {}
            stats_dict[db][op] = {
                "mean_latency_ms": round(float(group["latency_ms"].mean()), 2),
                "std_latency_ms": (
                    round(float(group["latency_ms"].std()), 2)
                    if len(group) > 1
                    else 0.0
                ),
                "min_latency_ms": round(float(group["latency_ms"].min()), 2),
                "max_latency_ms": round(float(group["latency_ms"].max()), 2),
                "mean_throughput_ops_sec": round(
                    float(group["throughput_ops_sec"].mean()), 2
                ),
                "max_throughput_ops_sec": int(group["throughput_ops_sec"].max()),
                "sample_count": int(len(group)),
            }
        return stats_dict

    def compute_latency_percentiles(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Compute p50, p90, p95, p99 latency percentiles across workloads."""
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
        return p_dict

    def compute_concurrency_scaling(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze latency and throughput degradation across concurrency levels (50, 100, 200)."""
        scaling_dict: Dict[str, Any] = {}
        grouped = df.groupby(["database", "concurrency_level"])

        for (db, conc), group in grouped:
            if db not in scaling_dict:
                scaling_dict[db] = {}
            scaling_dict[db][int(conc)] = {
                "mean_read_latency_ms": (
                    round(
                        float(group[group["operation"] == "read"]["latency_ms"].mean()),
                        2,
                    )
                    if any(group["operation"] == "read")
                    else None
                ),
                "mean_write_latency_ms": (
                    round(
                        float(
                            group[group["operation"] == "write"]["latency_ms"].mean()
                        ),
                        2,
                    )
                    if any(group["operation"] == "write")
                    else None
                ),
                "total_throughput_ops_sec": int(group["throughput_ops_sec"].sum()),
            }
        return scaling_dict

    def compute_headroom_comparison(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Compute high-level architectural headroom comparison."""
        dbs = df["database"].unique()
        comparison: Dict[str, Any] = {}
        for db in dbs:
            read_df = df[(df["database"] == db) & (df["operation"] == "read")]
            write_df = df[(df["database"] == db) & (df["operation"] == "write")]
            comparison[db] = {
                "avg_read_latency_ms": round(float(read_df["latency_ms"].mean()), 2),
                "p95_read_latency_ms": round(
                    float(np.percentile(read_df["latency_ms"].values, 95)), 2
                ),
                "avg_write_latency_ms": round(float(write_df["latency_ms"].mean()), 2),
                "p95_write_latency_ms": round(
                    float(np.percentile(write_df["latency_ms"].values, 95)), 2
                ),
                "peak_throughput_ops_sec": int(
                    df[df["database"] == db]["throughput_ops_sec"].max()
                ),
            }
        return comparison

    def analyze(
        self,
        file_path: Optional[str] = None,
        operation: str = "summary_stats",
        filter_database: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute deterministic statistical calculations on tabular benchmark CSV data."""
        df, csv_file = self.load_dataframe(
            file_path=file_path, filter_database=filter_database
        )

        if operation == "summary_stats":
            result_data = self.compute_summary_stats(df)
        elif operation == "latency_percentiles":
            result_data = self.compute_latency_percentiles(df)
        elif operation == "concurrency_scaling":
            result_data = self.compute_concurrency_scaling(df)
        elif operation == "headroom_comparison":
            result_data = self.compute_headroom_comparison(df)
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


# Default singleton instance
default_tabular_analyzer = TabularAnalyzer()

# Backwards compatibility function
analyze_csv = default_tabular_analyzer.analyze


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
    return default_tabular_analyzer.analyze(
        file_path=file_path, operation=operation, filter_database=filter_database
    )


class TabularAnalysisTool(BaseTool):
    """Tool that executes deterministic Pandas analysis on benchmark telemetry data."""

    name: str = "analyze_csv"
    description: str = (
        "Execute deterministic Pandas analytical calculations on tabular benchmark telemetry data. "
        "Computes exact throughput ops/sec, latency percentiles, and concurrency scaling."
    )
    args_schema: Type[BaseModel] = TabularAnalysisInput

    def _run(
        self,
        operation: str = "summary_stats",
        filter_database: Optional[str] = None,
        file_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute tabular benchmark telemetry analytics."""
        return default_tabular_analyzer.analyze(
            file_path=file_path, operation=operation, filter_database=filter_database
        )
