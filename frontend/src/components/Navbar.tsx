import React from "react";

interface NavbarProps {
  threadId?: string;
}

export const Navbar: React.FC<NavbarProps> = ({ threadId }) => {
  return (
    <nav>
      <div className="brand">
        <div className="brand-icon">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
          </svg>
        </div>
        <span>Antigravity AI</span>
        <span className="brand-badge">2.0 Engine</span>
      </div>

      <div className="nav-status">
        <span style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <span className="live-dot"></span> Qdrant & Checkpoints Online
        </span>
        <span style={{ opacity: 0.5 }}>|</span>
        <span style={{ fontFamily: "var(--font-mono)", fontSize: "12px" }}>
          {threadId ? `Thread: ${threadId}` : "No active session"}
        </span>
      </div>
    </nav>
  );
};
