import React from "react";
import { ResearchWorkflowState } from "../types/research";

interface MetricsGridProps {
  state: ResearchWorkflowState;
}

export const MetricsGrid: React.FC<MetricsGridProps> = ({ state }) => {
  const evidenceCount = state.evidence_count ?? (state.evidence ? state.evidence.length : 0);
  const subquestionsCount = state.subquestions ? state.subquestions.length : 0;
  const gapsCount = state.unsupported_claims ? state.unsupported_claims.length : 0;
  const displayStatus = (state.status || "IDLE").toUpperCase();

  return (
    <div className="stats-grid">
      <div className="stat-box">
        <div className="stat-icon" style={{ background: "rgba(56, 189, 248, 0.12)", color: "var(--primary)" }}>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
            <polyline points="14 2 14 8 20 8"></polyline>
          </svg>
        </div>
        <div>
          <div className="stat-val">{evidenceCount}</div>
          <div className="stat-lbl">Evidence Collected</div>
        </div>
      </div>

      <div className="stat-box">
        <div className="stat-icon" style={{ background: "rgba(129, 140, 248, 0.12)", color: "var(--accent-purple)" }}>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10"></circle>
            <line x1="12" y1="16" x2="12" y2="12"></line>
            <line x1="12" y1="8" x2="12.01" y2="8"></line>
          </svg>
        </div>
        <div>
          <div className="stat-val">{subquestionsCount}</div>
          <div className="stat-lbl">Subquestions Formulated</div>
        </div>
      </div>

      <div className="stat-box">
        <div className="stat-icon" style={{ background: "rgba(244, 63, 94, 0.12)", color: "var(--accent-rose)" }}>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path>
            <line x1="12" y1="9" x2="12" y2="13"></line>
            <line x1="12" y1="17" x2="12.01" y2="17"></line>
          </svg>
        </div>
        <div>
          <div className="stat-val">{gapsCount}</div>
          <div className="stat-lbl">Limitations Audited</div>
        </div>
      </div>

      <div className="stat-box">
        <div className="stat-icon" style={{ background: "rgba(16, 185, 129, 0.12)", color: "var(--accent-emerald)" }}>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
            <polyline points="22 4 12 14.01 9 11.01"></polyline>
          </svg>
        </div>
        <div>
          <div className="stat-val" style={{ fontSize: "16px" }}>{displayStatus}</div>
          <div className="stat-lbl">Workflow Status</div>
        </div>
      </div>
    </div>
  );
};
