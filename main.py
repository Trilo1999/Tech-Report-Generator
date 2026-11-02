"""Interactive command-line entrypoint for the AI Research & Report Generation Agent."""

import argparse
from pathlib import Path
import sys
import uuid

# Ensure unbuffered realtime output
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True)

from src.graph.builder import create_research_graph
from src.graph.checkpoints import get_checkpointer, get_thread_state, resume_workflow


def run_cli():
    """Run an interactive or automated research workflow from the terminal."""
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
    args = parser.parse_args()

    thread_id = f"cli_{uuid.uuid4().hex[:8]}"
    print("=" * 70)
    print(" AI Research & Report Generation Agent")
    print(f" Session Thread ID: {thread_id}")
    print(f" Topic: {args.topic}")
    print("=" * 70)

    # 1. Initialize workflow with persistence
    checkpointer = get_checkpointer()
    graph = create_research_graph(checkpointer=checkpointer)
    config = {"configurable": {"thread_id": thread_id}}

    print("\n[Phase 1] Executing Planning, Evidence Retrieval & Calculations...")
    state = graph.invoke({"topic": args.topic}, config=config)

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
        print(f"  - Projected Savings: ${comp.get('projected_difference_amount'):,.2f}")

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
        return

    print("\n" + "=" * 70)
    print(" [Phase 3] Checkpoint: Human Review Required")
    print("=" * 70)

    if args.auto_approve:
        print("Auto-approve flag detected. Approving proposal...")
        decision = "approved"
        feedback_notes = "Auto-approved via CLI flag."
        target_sections = []
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
                [sec_keys[int(sec_idx) - 1]] if sec_idx.isdigit() and 1 <= int(sec_idx) <= len(sec_keys) else []
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
    final_state = resume_workflow(thread_id, review_payload, checkpointer=checkpointer)

    print("\n" + "=" * 70)
    print(f" Final Workflow Status: {final_state.get('status').upper()}")
    if final_state.get("final_report_path"):
        report_file = Path(final_state["final_report_path"])
        print(f" Published Document: {report_file.resolve()}")
        print(f" Document Size: {report_file.stat().st_size:,} bytes")
    print("=" * 70)


if __name__ == "__main__":
    run_cli()
