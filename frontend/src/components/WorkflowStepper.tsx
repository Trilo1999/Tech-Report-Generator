import React from "react";
import { ResearchWorkflowState } from "../types/research";

interface WorkflowStepperProps {
  state?: ResearchWorkflowState | null;
  isLoading: boolean;
}

const STEPS = [
  { id: "plan", num: 1, label: "Planning" },
  { id: "gather", num: 2, label: "Evidence" },
  { id: "bench", num: 3, label: "TCO & Telemetry" },
  { id: "eval", num: 4, label: "Sufficiency" },
  { id: "draft", num: 5, label: "Draft Report" },
  { id: "review", num: 6, label: "HITL Review" },
];

export const WorkflowStepper: React.FC<WorkflowStepperProps> = ({ state, isLoading }) => {
  const getStepStatus = (stepId: string): "step-active" | "step-done" | "" => {
    if (!state) {
      if (isLoading) return stepId === "plan" ? "step-active" : "";
      return "";
    }

    const { status, is_running, draft_report, is_pending_review } = state;

    if (status === "completed" || status === "approved") {
      return "step-done";
    }

    if (is_running || status === "running") {
      if (!draft_report) {
        if (stepId === "plan") return "step-done";
        if (stepId === "gather") return "step-active";
        return "";
      }
      if (status === "review_resuming" || status === "processing") {
        if (stepId === "review") return "step-active";
        return "step-done";
      }
    }

    if (draft_report) {
      if (stepId !== "review") return "step-done";
      if (is_pending_review) return "step-active";
    }

    if (stepId === "plan") return "step-done";
    return "";
  };

  return (
    <div className="stepper">
      {STEPS.map((s) => {
        const statusClass = getStepStatus(s.id);
        return (
          <div key={s.id} className={`step-item ${statusClass}`}>
            <span className="step-num">{s.num}</span>
            <span className="step-label">{s.label}</span>
          </div>
        );
      })}
    </div>
  );
};
