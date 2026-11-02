import React from "react";

export const CitationLegend: React.FC = () => {
  return (
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
  );
};
