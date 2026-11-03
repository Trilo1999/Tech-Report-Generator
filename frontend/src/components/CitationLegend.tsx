import React, { useState } from "react";
import { EvidenceItem } from "../types/research";
import { CitationModal } from "./CitationModal";

interface CitationLegendProps {
  evidenceList?: EvidenceItem[];
  onShowToast?: (msg: string) => void;
}

export const CitationLegend: React.FC<CitationLegendProps> = ({
  evidenceList = [],
  onShowToast,
}) => {
  const [selectedCitation, setSelectedCitation] = useState<EvidenceItem | null>(null);

  return (
    <div className="legend-container">
      <div className="legend-box">
        <div className="legend-item">
          <span className="cite-badge cite-qdr">[QDR-xx]</span>
          <span><b>Internal Standards:</b> Architectural guidelines from Qdrant vector storage.</span>
        </div>
        <div className="legend-item">
          <span className="cite-badge cite-ext">[EXT-xx]</span>
          <span><b>External Research:</b> Peer-reviewed industry whitepapers and technical studies.</span>
        </div>
        <div className="legend-item">
          <span className="cite-badge cite-csv">[CSV-xx]</span>
          <span><b>Empirical Telemetry:</b> Stress-test benchmarks (latency percentiles & ops/sec).</span>
        </div>
        <div className="legend-item">
          <span className="cite-badge cite-cost">[COST-xx]</span>
          <span><b>Cloud TCO Models:</b> 12-to-36 month infrastructure and maintenance modeling.</span>
        </div>
      </div>

      {evidenceList.length > 0 && (
        <div className="legend-sources-quicklist">
          <div className="quicklist-header">
            <span>Verified Sources in Active Report (Click any citation to inspect):</span>
          </div>
          <div className="quicklist-badges">
            {evidenceList.map((item) => {
              const sid = item.source_id.toUpperCase();
              const badgeClass = sid.startsWith("QDR")
                ? "cite-qdr"
                : sid.startsWith("EXT")
                ? "cite-ext"
                : sid.startsWith("CSV")
                ? "cite-csv"
                : "cite-cost";
              return (
                <button
                  key={item.source_id}
                  type="button"
                  className={`cite-badge-btn cite-badge ${badgeClass}`}
                  onClick={() => setSelectedCitation(item)}
                  title={`Click to view ground truth evidence: ${item.title}`}
                >
                  <span>[{item.source_id}] {item.title.length > 32 ? `${item.title.slice(0, 32)}...` : item.title}</span>
                  <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" className="cite-badge-icon">
                    <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path>
                    <polyline points="15 3 21 3 21 9"></polyline>
                    <line x1="10" y1="14" x2="21" y2="3"></line>
                  </svg>
                </button>
              );
            })}
          </div>
        </div>
      )}

      <CitationModal
        isOpen={Boolean(selectedCitation)}
        citation={selectedCitation}
        fullTag={selectedCitation ? `[${selectedCitation.source_id}]` : ""}
        onClose={() => setSelectedCitation(null)}
        onShowToast={onShowToast}
      />
    </div>
  );
};
