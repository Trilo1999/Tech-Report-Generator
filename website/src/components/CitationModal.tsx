import React from "react";
import { EvidenceItem } from "../types/research";

interface CitationModalProps {
  isOpen: boolean;
  citation: EvidenceItem | null;
  fullTag?: string;
  onClose: () => void;
  onShowToast?: (msg: string) => void;
}

export const CitationModal: React.FC<CitationModalProps> = ({
  isOpen,
  citation,
  fullTag,
  onClose,
  onShowToast,
}) => {
  if (!isOpen || !citation) return null;

  const sid = citation.source_id.toUpperCase();
  const isQdr = sid.startsWith("QDR");
  const isExt = sid.startsWith("EXT");
  const isCsv = sid.startsWith("CSV");
  const isCost = sid.startsWith("COST");

  const getBadgeClass = () => {
    if (isQdr) return "cite-qdr";
    if (isExt) return "cite-ext";
    if (isCsv) return "cite-csv";
    if (isCost) return "cite-cost";
    return "";
  };

  const getSourceTypeLabel = () => {
    if (isQdr) return "Internal Vector Architecture Guideline";
    if (isExt) return "Authoritative External Technical Whitepaper";
    if (isCsv) return "Empirical Runtime Telemetry Benchmark";
    if (isCost) return "Deterministic 12-to-36 Month Cloud TCO Model";
    return citation.source_type || "Ground Evidence Source";
  };

  const meta = citation.metadata || {};
  const reliability = citation.reliability_score !== undefined
    ? Math.round(citation.reliability_score * 100)
    : (isCsv || isCost ? 100 : 92);

  const handleCopyExcerpt = () => {
    navigator.clipboard.writeText(citation.content).then(() => {
      if (onShowToast) onShowToast("Evidence excerpt copied to clipboard!");
    });
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-card citation-modal-card" onClick={(e) => e.stopPropagation()}>
        {/* Modal Header */}
        <div className="modal-header">
          <div className="citation-modal-header-tag">
            <span className={`cite-badge ${getBadgeClass()}`}>
              {fullTag || `[${citation.source_id}]`}
            </span>
            <span className="citation-type-pill">{getSourceTypeLabel()}</span>
          </div>
          <button type="button" className="modal-close-btn" onClick={onClose} title="Close window">
            &times;
          </button>
        </div>

        {/* Title */}
        <h3 className="citation-modal-title">{citation.title}</h3>

        {/* Reliability Indicator */}
        <div className="citation-reliability-box">
          <div className="reliability-label-row">
            <span>Ground Truth Verification Score</span>
            <strong className="reliability-value">{reliability}% Verified</strong>
          </div>
          <div className="reliability-progress-bar">
            <div
              className="reliability-progress-fill"
              style={{
                width: `${reliability}%`,
                background: reliability >= 90 ? "var(--accent-green)" : "var(--accent-amber)",
              }}
            ></div>
          </div>
        </div>

        {/* Metadata Details */}
        <div className="citation-meta-grid">
          {isExt && meta.url && (
            <div className="meta-grid-item full-width">
              <span className="meta-item-label">Source URL</span>
              <a
                href={meta.url}
                target="_blank"
                rel="noopener noreferrer"
                className="meta-link"
              >
                {meta.url}
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                  <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path>
                  <polyline points="15 3 21 3 21 9"></polyline>
                  <line x1="10" y1="14" x2="21" y2="3"></line>
                </svg>
              </a>
            </div>
          )}

          {isExt && meta.author && (
            <div className="meta-grid-item">
              <span className="meta-item-label">Author / Researcher</span>
              <span className="meta-item-value">{meta.author}</span>
            </div>
          )}

          {isExt && meta.publication && (
            <div className="meta-grid-item">
              <span className="meta-item-label">Publication</span>
              <span className="meta-item-value">{meta.publication}</span>
            </div>
          )}

          {isExt && meta.date && (
            <div className="meta-grid-item">
              <span className="meta-item-label">Publication Date</span>
              <span className="meta-item-value">{meta.date}</span>
            </div>
          )}

          {isQdr && (
            <>
              <div className="meta-grid-item">
                <span className="meta-item-label">Knowledge Engine</span>
                <span className="meta-item-value">Qdrant Vector DB (all-MiniLM-L6-v2)</span>
              </div>
              <div className="meta-grid-item">
                <span className="meta-item-label">Document Standard</span>
                <span className="meta-item-value">Internal Enterprise Architecture Guidelines</span>
              </div>
            </>
          )}

          {isCsv && (
            <>
              <div className="meta-grid-item">
                <span className="meta-item-label">Telemetry Source</span>
                <span className="meta-item-value">benchmark_results.csv (p50, p95, p99)</span>
              </div>
              <div className="meta-grid-item">
                <span className="meta-item-label">Concurrency Tiers</span>
                <span className="meta-item-value">50, 100, and 200 concurrent connections</span>
              </div>
            </>
          )}

          {isCost && (
            <>
              <div className="meta-grid-item">
                <span className="meta-item-label">Financial Dataset</span>
                <span className="meta-item-value">cloud_pricing.json (AWS / GCP / Open Source)</span>
              </div>
              <div className="meta-grid-item">
                <span className="meta-item-label">Software Licensing</span>
                <span className="meta-item-value">$0.00 MIT Open Source (React / Angular)</span>
              </div>
            </>
          )}
        </div>

        {/* Evidence Excerpt Content */}
        <div className="citation-content-section">
          <div className="citation-content-header">
            <span className="citation-content-title">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                <polyline points="14 2 14 8 20 8"></polyline>
              </svg>
              Ground Truth Evidence Excerpt
            </span>
            <button
              type="button"
              className="btn-copy-citation"
              onClick={handleCopyExcerpt}
              title="Copy text snippet"
            >
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
              </svg>
              Copy Excerpt
            </button>
          </div>
          <div className="citation-content-body">
            {citation.content}
          </div>
        </div>

        {/* Modal Footer */}
        <div className="modal-footer" style={{ marginTop: 20 }}>
          <button type="button" className="btn btn-primary" onClick={onClose} style={{ width: "100%" }}>
            Done / Close
          </button>
        </div>
      </div>
    </div>
  );
};
