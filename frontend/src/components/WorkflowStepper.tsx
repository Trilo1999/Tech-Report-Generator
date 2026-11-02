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
    if (isLoading && !state) {
      return stepId === "plan" ? "step-active" : "";
    }
    if (!state) return "";

    const status = state.status;
    if (status === "completed" || status === "approved") {
      return "step-done";
    }

    if (stepId === "plan") return "step-done";
    if (stepId === "gather") return "step-done";
    if (stepId === "bench") return "step-done";
    if (stepId === "eval") return "step-done";
    if (stepId === "draft") return state.draft_report ? "step-done" : "step-active";
    if (stepId === "review") return state.is_pending_review ? "step-active" : "";

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
