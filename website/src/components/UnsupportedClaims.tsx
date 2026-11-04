import React from "react";

interface UnsupportedClaimsProps {
  claims?: string[];
}

export const UnsupportedClaims: React.FC<UnsupportedClaimsProps> = ({ claims }) => {
  if (!claims || claims.length === 0) return null;

  return (
    <div className="claims-card">
      <div className="claims-header">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
          <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path>
          <line x1="12" y1="9" x2="12" y2="13"></line>
          <line x1="12" y1="17" x2="12.01" y2="17"></line>
        </svg>
        Audited Limitations & Unsupported Claims (Evidence Integrity Guardrail)
      </div>
      <ul className="claims-list">
        {claims.map((claim, idx) => (
          <li key={idx}>{claim}</li>
        ))}
      </ul>
    </div>
  );
};
