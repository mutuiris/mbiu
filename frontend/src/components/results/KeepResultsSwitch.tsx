import React from "react";

interface KeepResultsSwitchProps {
  kept: boolean;
  onChange: (keep: boolean) => void;
}

export function KeepResultsSwitch({ kept, onChange }: KeepResultsSwitchProps) {
  return (
    <section className="keep-results" aria-label="Keep results on this device">
      <div className="flex w-full flex-wrap items-center justify-between gap-2">
        <label className="consent-label flex min-h-11 items-center gap-3" htmlFor="keep-results-switch">
          <input
            id="keep-results-switch"
            type="checkbox"
            role="switch"
            checked={kept}
            onChange={(e) => onChange(e.target.checked)}
            aria-describedby="keep-results-detail"
            className="consent-checkbox"
          />
          <span>Keep results on this phone for 1 hour</span>
        </label>
        {kept && (
          <button
            type="button"
            className="report-press min-h-11 px-2 text-[0.88rem] font-semibold text-mbiu-indigo underline underline-offset-4 dark:text-[#a9b0ff]"
            onClick={() => onChange(false)}
          >
            Clear now
          </button>
        )}
      </div>
      <p id="keep-results-detail" className="keep-results-detail">
        Leave this off on a shared phone. Kept in this tab only.
      </p>
    </section>
  );
}
