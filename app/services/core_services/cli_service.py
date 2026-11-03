"""CLI service implementing OOP patterns for interactive research and server startup."""

import argparse
import sys
import uuid
from pathlib import Path
from typing import Any, Dict, List

import uvicorn

from app.agents.graph.builder import create_research_graph
from app.agents.graph.checkpoints import (
    get_checkpointer,
    get_thread_state,
    resume_workflow,
)
from app.config.env_config import SERVER_HOST, SERVER_PORT


class CLIService:
    """Service class encapsulating command-line arguments, terminal interaction, and research execution."""

    def __init__(self) -> None:
        self.parser = self._build_parser()

    def _build_parser(self) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(
            description="Autonomous AI Research & Report Generation Agent with Human-in-the-Loop Review"
        )
        parser.add_argument(
            "--topic",
            type=str,
            default="PostgreSQL vs MongoDB Multi-Tenant Architecture Evaluation",
            help="Broad technical research topic or architectural decision scope",
        )
        parser.add_argument(
            "--auto-approve",
            action="store_true",
            help="Automatically approve the drafted report without interactive terminal prompts",
        )
        parser.add_argument(
            "--format",
            choices=["pdf", "docx"],
            default="pdf",
            help="Report export format (default: pdf)",
        )
        parser.add_argument(
            "--server",
            action="store_true",
            help="Start the FastAPI backend server instead of running the CLI workflow",
        )
        return parser

    def run(self, args_list: List[str] | None = None) -> None:
        """Parse arguments and execute either server boot or interactive research workflow."""
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(line_buffering=True)

        args = self.parser.parse_args(args_list)

        if args.server:
            print(f"Starting API Server on http://{SERVER_HOST}:{SERVER_PORT}...")
            uvicorn.run("app.main:app", host=SERVER_HOST, port=SERVER_PORT, reload=True)
            return

        self.execute_workflow(
            topic=args.topic, auto_approve=args.auto_approve, export_format=args.format
        )

    def execute_workflow(
        self, topic: str, auto_approve: bool, export_format: str = "pdf"
    ) -> Dict[str, Any]:
        """Execute the end-to-end research workflow from the terminal."""
        thread_id = f"cli_{uuid.uuid4().hex[:8]}"
        print("=" * 70)
        print(" AI Research & Report Generation Agent")
        print(f" Session Thread ID: {thread_id}")
        print(f" Topic: {topic}")
        print("=" * 70)

        # 1. Initialize workflow with persistence
        checkpointer = get_checkpointer()
        graph = create_research_graph(checkpointer=checkpointer)
        config = {"configurable": {"thread_id": thread_id}}

        print("\n[Phase 1] Executing Planning, Evidence Retrieval & Calculations...")
        state = graph.invoke({"topic": topic}, config=config)

        subquestions = state.get("subquestions", [])
        print(f"\nDecomposed Subquestions ({len(subquestions)} generated):")
        for idx, sq in enumerate(subquestions, 1):
            print(f"  {idx}. {sq}")

        evidence = state.get("evidence", [])
        print(f"\nGrounding Evidence Items Collected: {len(evidence)}")
        for e in evidence:
            print(f"  - [{e.get('source_id')}] {e.get('title')}")

        calculations = state.get("calculations", {})
        if "cost_projection" in calculations:
            comp = calculations["cost_projection"].get("comparison", {})
            print("\nDeterministic TCO Analysis:")
            print(
                f"  - Cost Advantage: {comp.get('cheaper_database', '').capitalize()} is {comp.get('savings_percentage')}% cheaper"
            )
            print(
                f"  - Projected Savings: ${comp.get('projected_difference_amount'):,.2f}"
            )

        draft = state.get("draft_report") or {}
        print(f"\n[Phase 2] Draft Report Synthesized: '{draft.get('title')}'")
        sections = draft.get("sections", {})
        for sec_name in sections:
            print(f"  * Section: {sec_name}")

        unsupported = state.get("unsupported_claims", [])
        if unsupported:
            print("\n[WARNING] Flagged Unsupported Claims:")
            for u in unsupported:
                print(f"  ! {u}")

        # 2. Checkpoint boundary
        snapshot = get_thread_state(thread_id, checkpointer=checkpointer)
        if not snapshot or "human_review" not in snapshot.get("next", []):
            print("\nWorkflow completed or not paused.")
            return state

        print("\n" + "=" * 70)
        print(" [Phase 3] Checkpoint: Human Review Required")
        print("=" * 70)

        if auto_approve:
            print("Auto-approve flag detected. Approving proposal...")
            decision = "approved"
            feedback_notes = "Auto-approved via CLI flag."
            target_sections: list[str] = []
        else:
            print("Options: [a]pprove, [r]evise, [x]reject")
            choice = input("Enter decision (a/r/x) [default: a]: ").strip().lower()
            if choice == "r":
                decision = "revise"
                feedback_notes = input("Enter revision feedback: ").strip()
                print("Available sections:")
                sec_keys = list(sections.keys())
                for i, s in enumerate(sec_keys, 1):
                    print(f"  {i}. {s}")
                sec_idx = input("Enter section number to revise: ").strip()
                target_sections = (
                    [sec_keys[int(sec_idx) - 1]]
                    if sec_idx.isdigit() and 1 <= int(sec_idx) <= len(sec_keys)
                    else []
                )
            elif choice == "x":
                decision = "rejected"
                feedback_notes = "Rejected in CLI."
                target_sections = []
            else:
                decision = "approved"
                feedback_notes = "Approved via interactive CLI."
                target_sections = []

        # 3. Resume workflow
        print(f"\nResuming thread '{thread_id}' with decision: {decision.upper()}...")
        review_payload = {
            "decision": decision,
            "feedback_notes": feedback_notes,
            "target_sections": target_sections,
        }
        final_state = resume_workflow(
            thread_id, review_payload, checkpointer=checkpointer
        )

        print("\n" + "=" * 70)
        print(f" Final Workflow Status: {final_state.get('status').upper()}")
        if final_state.get("final_report_path"):
            report_file = Path(final_state["final_report_path"])
            print(f" Published Document: {report_file.resolve()}")
            print(f" Document Size: {report_file.stat().st_size:,} bytes")
        print("=" * 70)
        return final_state


default_cli_service = CLIService()
run_cli = default_cli_service.run
