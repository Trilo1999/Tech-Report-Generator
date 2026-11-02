import React from "react";

export const Hero: React.FC = () => {
  return (
    <div className="hero">
      <div className="hero-tagline">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
          <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>
        </svg>
        Grounded Decision Intelligence
      </div>
      <h1>AI Technical Research & Decision Report Agent</h1>
      <p>
        Automated topic decomposition, Qdrant vector retrieval, empirical pandas benchmarks, deterministic cloud TCO modeling, and human review checkpointing.
      </p>
    </div>
  );
};
