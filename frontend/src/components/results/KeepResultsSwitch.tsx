import React from "react";

interface KeepResultsSwitchProps {
  kept: boolean;
  onChange: (keep: boolean) => void;
}

export function KeepResultsSwitch({ kept, onChange }: KeepResultsSwitchProps) {
  return (
    <section className="keep-results" aria-label="Keep results on this device">
      <label className="consent-label" htmlFor="keep-results-switch">
        <input
          id="keep-results-switch"
          type="checkbox"
          role="switch"
          checked={kept}
          onChange={(e) => onChange(e.target.checked)}
          aria-describedby="keep-results-detail"
          className="consent-checkbox"
        />
        <span>Keep my results if this page reloads. Leave this off on a shared phone.</span>
      </label>
      <p id="keep-results-detail" className="keep-results-detail">
        Kept in this tab only, and cleared when you close it, after 60 minutes, or now.
      </p>
      {kept && (
        <button type="button" className="secondary-btn" onClick={() => onChange(false)}>
          Clear now
        </button>
      )}
    </section>
  );
}
