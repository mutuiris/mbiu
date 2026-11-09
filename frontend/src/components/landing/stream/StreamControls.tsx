import React from "react";

export interface StreamControlsProps {
  onStartOver: () => void;
  className?: string;
}

export function StreamControls({ onStartOver, className = "" }: StreamControlsProps) {
  return (
    <div className={`stream-controls ${className}`}>
      <button type="button" className="secondary-btn restart-btn" onClick={onStartOver}>
        Check another contract
      </button>
    </div>
  );
}
