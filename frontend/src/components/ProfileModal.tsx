import React, { useState } from "react";
import { useAuth } from "../context/AuthContext";
import { RoleType } from "../types/auth";

interface ProfileModalProps {
  isOpen: boolean;
  onClose: () => void;
  onOpenAuthModal: (mode: "login" | "register") => void;
  onShowToast: (msg: string) => void;
}

export const ProfileModal: React.FC<ProfileModalProps> = ({
  isOpen,
  onClose,
  onOpenAuthModal,
  onShowToast,
}) => {
  const { user, token, logout, loginAsDemo } = useAuth();
  const [copiedField, setCopiedField] = useState<string | null>(null);

  if (!isOpen || !user) return null;

  const copyToClipboard = (text: string, label: string) => {
    navigator.clipboard.writeText(text).then(() => {
      setCopiedField(label);
      onShowToast(`Copied ${label} to clipboard!`);
      setTimeout(() => setCopiedField(null), 2000);
    });
  };

  const getRoleBadgeClass = (role: RoleType) => {
    switch (role) {
      case "admin":
        return "badge-admin";
      case "researcher":
        return "badge-researcher";
      case "reviewer":
        return "badge-reviewer";
      case "viewer":
        return "badge-viewer";
      default:
        return "";
    }
  };

  const getRoleDescription = (role: RoleType) => {
    switch (role) {
      case "admin":
        return "System Administrator — Unrestricted access across all research, review, and export pipelines.";
      case "researcher":
        return "Lead Researcher — Permitted to trigger autonomous workflows, view real-time state, and request surgical revisions.";
      case "reviewer":
        return "Senior Reviewer — Authorized to conduct Human-in-the-Loop evaluations, issue final approvals, or reject proposals.";
      case "viewer":
        return "Stakeholder Viewer — Read-only observation mode with permission to monitor threads and download finalized reports.";
    }
  };

  // Format date
  const createdDate = user.created_at
    ? new Date(user.created_at * 1000).toLocaleString("en-US", {
        month: "short",
        day: "numeric",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      })
    : "Just now";

  // Permissions breakdown
  const permissions = [
    {
      name: "Launch Autonomous Research Workflows",
      allowed: ["admin", "researcher"].includes(user.role),
      requiredRole: "Admin or Researcher",
    },
    {
      name: "Human Review: Final Approval & PDF Publication",
      allowed: ["admin", "reviewer"].includes(user.role),
      requiredRole: "Admin or Reviewer",
    },
    {
      name: "Human Review: Request Surgical Section Revisions",
      allowed: ["admin", "reviewer", "researcher"].includes(user.role),
      requiredRole: "Admin, Reviewer, or Researcher",
    },
    {
      name: "Inspect Real-time Workflow State & Calculations",
      allowed: true,
      requiredRole: "All Roles",
    },
    {
      name: "Download Exported Publication PDF Reports",
      allowed: true,
      requiredRole: "All Roles",
    },
  ];

  const handleSwitchPersona = async (targetRole: RoleType) => {
    try {
      await loginAsDemo(targetRole);
      onShowToast(`Switched active profile to ${targetRole.toUpperCase()}`);
    } catch (err: any) {
      alert(`Role switch failed: ${err.message || err}`);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-card profile-modal-card" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="modal-header">
          <div className="modal-title">
            <div className="brand-icon" style={{ width: 32, height: 32, borderRadius: 10 }}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5">
                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
                <circle cx="12" cy="7" r="4"></circle>
              </svg>
            </div>
            <div>
              <h3>User Identity & Profile</h3>
              <p className="modal-subtitle">Security details, assigned roles, and permission gates</p>
            </div>
          </div>
          <button className="modal-close-btn" onClick={onClose} aria-label="Close modal">
            &times;
          </button>
        </div>

        {/* Profile Card Summary */}
        <div className="profile-hero">
          <div className="profile-avatar-large">
            {user.name.slice(0, 2).toUpperCase()}
          </div>
          <div className="profile-hero-info">
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <h4 className="profile-name">{user.name}</h4>
              <span className="profile-verified-badge" title="Verified session">
                ✓
              </span>
            </div>
            <p className="profile-email">{user.email}</p>
            <div style={{ display: "flex", alignItems: "center", gap: "8px", marginTop: "4px" }}>
              <span className={`user-role-tag ${getRoleBadgeClass(user.role)}`}>
                ROLE: {user.role.toUpperCase()}
              </span>
              <span className="profile-tag-session">JWT ACTIVE</span>
            </div>
          </div>
        </div>

        <p className="profile-role-description">{getRoleDescription(user.role)}</p>

        {/* Technical Details Grid */}
        <div className="profile-details-grid">
          <div className="detail-item">
            <span className="detail-label">Account ID</span>
            <div className="detail-value-row">
              <span className="detail-value mono">{user.id.slice(0, 18)}...</span>
              <button
                type="button"
                className="copy-btn-mini"
                onClick={() => copyToClipboard(user.id, "User ID")}
              >
                {copiedField === "User ID" ? "Copied!" : "Copy"}
              </button>
            </div>
          </div>

          <div className="detail-item">
            <span className="detail-label">Member Since</span>
            <span className="detail-value">{createdDate}</span>
          </div>

          <div className="detail-item detail-full-width">
            <span className="detail-label">Bearer Token Preview</span>
            <div className="detail-value-row">
              <span className="detail-value mono text-truncate">
                {token ? `${token.slice(0, 32)}...${token.slice(-12)}` : "No active token"}
              </span>
              {token && (
                <button
                  type="button"
                  className="copy-btn-mini"
                  onClick={() => copyToClipboard(token, "Access Token")}
                >
                  {copiedField === "Access Token" ? "Copied!" : "Copy Token"}
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Quick Persona Switcher in Profile */}
        <div className="profile-persona-box">
          <span className="persona-box-title">Switch Active Demo Persona:</span>
          <div className="persona-buttons">
            {(["admin", "researcher", "reviewer", "viewer"] as RoleType[]).map((r) => (
              <button
                key={r}
                type="button"
                className={`persona-btn ${user.role === r ? "active" : ""} ${getRoleBadgeClass(r)}`}
                onClick={() => handleSwitchPersona(r)}
              >
                {r.toUpperCase()}
              </button>
            ))}
          </div>
        </div>

        {/* Permissions Breakdown */}
        <div className="permissions-section">
          <h5>Access Control Matrix (RBAC)</h5>
          <div className="permissions-list">
            {permissions.map((p, idx) => (
              <div key={idx} className="permission-row">
                <span className={`perm-icon ${p.allowed ? "perm-allowed" : "perm-denied"}`}>
                  {p.allowed ? "✓" : "✕"}
                </span>
                <div className="perm-info">
                  <span className="perm-name">{p.name}</span>
                  <span className="perm-role">{p.allowed ? "Granted" : `Requires ${p.requiredRole}`}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Modal Actions */}
        <div className="profile-modal-actions">
          <div style={{ display: "flex", gap: "10px" }}>
            <button
              type="button"
              className="btn btn-outline"
              onClick={() => {
                onClose();
                onOpenAuthModal("login");
              }}
            >
              Switch Account
            </button>
            <button
              type="button"
              className="btn btn-outline-danger"
              onClick={() => {
                logout();
                onShowToast("Signed out successfully.");
                onClose();
              }}
            >
              Sign Out
            </button>
          </div>
          <button type="button" className="btn btn-primary" onClick={onClose}>
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
