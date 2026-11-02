import React from "react";
import { DraftReport } from "../types/research";
import { getDownloadUrl } from "../services/api";

interface ReportViewerProps {
  draft: DraftReport;
  threadId: string;
  isCompleted?: boolean;
  onCopy: () => void;
}

export const ReportViewer: React.FC<ReportViewerProps> = ({ draft, threadId, isCompleted, onCopy }) => {
  const sections = draft.sections || {};

  const renderSectionText = (text: string) => {
    // Replace citations with color-coded badges
    const parts = text.split(/(\[(?:QDR|EXT|CSV|COST)-[\w\.\-]+(?::\s*[^\]]+)?\])/g);
    return parts.map((part, index) => {
      if (/^\[QDR-/.test(part)) {
        return <span key={index} className="cite-badge cite-qdr">{part}</span>;
      }
      if (/^\[EXT-/.test(part)) {
        return <span key={index} className="cite-badge cite-ext">{part}</span>;
      }
      if (/^\[CSV-/.test(part)) {
        return <span key={index} className="cite-badge cite-csv">{part}</span>;
      }
      if (/^\[COST-/.test(part)) {
        return <span key={index} className="cite-badge cite-cost">{part}</span>;
      }
      return part;
    });
  };

  return (
    <div className="card">
      <div className="card-header">
        <div className="card-title">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
            <polyline points="14 2 14 8 20 8"></polyline>
            <line x1="16" y1="13" x2="8" y2="13"></line>
            <line x1="16" y1="17" x2="8" y2="17"></line>
            <polyline points="10 9 9 9 8 9"></polyline>
          </svg>
          <span>{draft.title || "Synthesis & Evaluation Report"}</span>
        </div>
        <div style={{ display: "flex", gap: "8px" }}>
          <button className="btn btn-secondary" onClick={onCopy} style={{ padding: "8px 14px", fontSize: "13px" }}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
              <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
            </svg>
            Copy Text
          </button>
          {isCompleted && (
            <a
              href={getDownloadUrl(threadId)}
              className="btn btn-success"
              style={{ padding: "8px 16px", fontSize: "13px" }}
              download
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                <polyline points="7 10 12 15 17 10"></polyline>
                <line x1="12" y1="15" x2="12" y2="3"></line>
              </svg>
              Download PDF
            </a>
          )}
        </div>
      </div>

      <div>
        {Object.entries(sections).map(([secTitle, secBody]) => {
          const isVerdict = /verdict|recommendation|decision matrix|strategic/i.test(secTitle);
          if (isVerdict) {
            return (
              <div key={secTitle} className="verdict-card">
                <div className="verdict-header">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                    <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
                    <polyline points="22 4 12 14.01 9 11.01"></polyline>
                  </svg>
                  {secTitle}
                </div>
                <div className="section-body">{renderSectionText(secBody)}</div>
              </div>
            );
          }

          return (
            <div key={secTitle} className="section-card">
              <div className="section-header">{secTitle}</div>
              <div className="section-body">{renderSectionText(secBody)}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
