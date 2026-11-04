import React from "react";

interface ToastProps {
  message: string | null;
}

export const Toast: React.FC<ToastProps> = ({ message }) => {
  return (
    <div className={`toast ${message ? "show" : ""}`}>
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#34D399" strokeWidth="2.5">
        <polyline points="20 6 9 17 4 12"></polyline>
      </svg>
      <span>{message}</span>
    </div>
  );
};
