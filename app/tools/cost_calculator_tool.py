"""
Cloud infrastructure Total Cost of Ownership (TCO) calculator implementing OOP patterns.

Queries cloud_pricing.json to perform exact deterministic mathematical calculations
for multi-database compute, storage, backup, and support over arbitrary projection periods.
Eliminates financial hallucinations from report generation.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from app.config.env_config import CLOUD_PRICING_JSON

# Standard monthly operational hours (365.25 / 12 * 24 ≈ 730)
HOURS_PER_MONTH = 730


class CloudCostCalculator:
    """Object-oriented engine for deterministic cloud infrastructure TCO calculations."""

    def __init__(self, default_pricing_file: Optional[Path] = None, hours_per_month: int = HOURS_PER_MONTH):
        self.default_pricing_file = default_pricing_file or CLOUD_PRICING_JSON
        self.hours_per_month = hours_per_month

    def load_pricing(self, pricing_file: Optional[Path] = None) -> Dict[str, Any]:
        """Load and parse cloud pricing matrix JSON."""
        path = pricing_file or self.default_pricing_file
        if not Path(path).is_file():
            raise FileNotFoundError(f"Cloud pricing matrix not found: {path}")

        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def calculate_tco(
        self,
        config: Optional[Dict[str, Any]] = None,
        pricing_file: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """Compute deterministic Total Cost of Ownership (TCO) for database deployments."""
        pricing_data = self.load_pricing(pricing_file)

        cfg = config or {}
        databases: List[str] = [db.lower() for db in cfg.get("databases", ["postgresql", "mongodb"])]
        storage_gb: float = float(cfg.get("storage_gb", 500))
        compute_instances: int = int(cfg.get("compute_instances", 3))
        projection_months: int = int(cfg.get("projection_months", 12))
        include_support: bool = bool(cfg.get("include_support", True))
        region: str = cfg.get("region", pricing_data.get("region", "us-east-1"))

        compute_matrix = pricing_data.get("compute", {})
        storage_matrix = pricing_data.get("storage", {})
        backup_matrix = pricing_data.get("backup", {})
        support_matrix = pricing_data.get("support", {})

        breakdown: Dict[str, Dict[str, Any]] = {}

        for db in databases:
            if db not in compute_matrix or db not in storage_matrix:
                raise KeyError(f"Pricing data not available for requested database: '{db}'")

            # 1. Compute Cost
            comp_info = compute_matrix[db]
            hourly_rate = float(comp_info["price_per_hour"])
            monthly_compute = round(hourly_rate * self.hours_per_month * compute_instances, 2)

            # 2. Storage Cost
            stor_info = storage_matrix[db]
            gb_rate = float(stor_info["price_per_gb_month"])
            monthly_storage = round(storage_gb * gb_rate, 2)

            # 3. Backup Cost
            backup_info = backup_matrix.get(db, {})
            backup_rate = float(backup_info.get("price_per_gb_month", 0.02))
            monthly_backup = round(storage_gb * backup_rate, 2)

            # 4. Support Cost
            monthly_support = 0.0
            if include_support and db in support_matrix:
                monthly_support = float(support_matrix[db].get("monthly_base", 0.0))

            # Totals
            total_monthly = round(monthly_compute + monthly_storage + monthly_backup + monthly_support, 2)
            total_projected = round(total_monthly * projection_months, 2)

            breakdown[db] = {
                "instance_type": comp_info.get("instance_type", "Standard"),
                "hourly_rate_per_instance": hourly_rate,
                "instances_count": compute_instances,
                "monthly_compute": monthly_compute,
                "storage_type": stor_info.get("type", "SSD"),
                "storage_gb": storage_gb,
                "price_per_gb": gb_rate,
                "monthly_storage": monthly_storage,
                "monthly_backup": monthly_backup,
                "monthly_support": monthly_support,
                "total_monthly": total_monthly,
                "total_projected": total_projected,
            }

        # Comparative analysis between first two databases
        comparison: Dict[str, Any] = {}
        if len(databases) >= 2:
            db1, db2 = databases[0], databases[1]
            cost1 = breakdown[db1]["total_projected"]
            cost2 = breakdown[db2]["total_projected"]

            cheaper = db1 if cost1 < cost2 else db2
            expensive = db2 if cheaper == db1 else db1
            diff_amount = round(abs(cost1 - cost2), 2)
            pct_savings = round((diff_amount / max(cost1, cost2)) * 100, 2) if max(cost1, cost2) > 0 else 0.0

            comparison = {
                "cheaper_database": cheaper,
                "more_expensive_database": expensive,
                "projected_difference_amount": diff_amount,
                "savings_percentage": pct_savings,
                "monthly_difference": round(abs(breakdown[db1]["total_monthly"] - breakdown[db2]["total_monthly"]), 2),
            }

        return {
            "source_id": "COST-01",
            "source_type": "cost_calculation",
            "title": f"Infrastructure Total Cost of Ownership ({projection_months}-Month Projection)",
            "parameters": {
                "databases": databases,
                "storage_gb": storage_gb,
                "compute_instances": compute_instances,
                "projection_months": projection_months,
                "include_support": include_support,
                "region": region,
                "hours_per_month": self.hours_per_month,
            },
            "breakdown": breakdown,
            "comparison": comparison,
            "reliability_score": 1.0,
        }


# Default singleton instance
default_cost_calculator = CloudCostCalculator()

# Backwards compatibility function
calculate_cost = default_cost_calculator.calculate_tco


class CostCalculatorInput(BaseModel):
    """Input schema for deterministic cloud infrastructure cost calculator."""

    databases: List[str] = Field(
        default=["postgresql", "mongodb"],
        description="List of database/cloud platform keys to compare (e.g., ['postgresql', 'mongodb'], ['aws', 'azure'], ['aws', 'gcp']).",
    )
    storage_gb: float = Field(
        default=500.0,
        description="Provisioned storage capacity in gigabytes per month.",
    )
    compute_instances: int = Field(
        default=3,
        description="Number of compute instances in HA topology (e.g. 1 primary + 2 replicas).",
    )
    projection_months: int = Field(
        default=12,
        description="Projection duration in months (e.g. 12 or 36).",
    )
    include_support: bool = Field(
        default=True,
        description="Whether to include enterprise cloud support plan tier.",
    )
    region: str = Field(
        default="us-east-1",
        description="Cloud region identifier (e.g., 'us-east-1').",
    )


@tool("calculate_cost", args_schema=CostCalculatorInput)
def calculate_cost_tool(
    databases: Optional[List[str]] = None,
    storage_gb: float = 500.0,
    compute_instances: int = 3,
    projection_months: int = 12,
    include_support: bool = True,
    region: str = "us-east-1",
) -> Dict[str, Any]:
    """Compute deterministic Total Cost of Ownership (TCO) for databases and cloud infrastructure platforms without financial hallucinations."""
    cfg = {
        "databases": databases or ["postgresql", "mongodb"],
        "storage_gb": storage_gb,
        "compute_instances": compute_instances,
        "projection_months": projection_months,
        "include_support": include_support,
        "region": region,
    }
    return default_cost_calculator.calculate_tco(config=cfg)
