import React from "react";

export interface ServiceUnavailableBannerProps {
  onRetryAll?: () => void;
  message?: string;
}

export const ServiceUnavailableBanner: React.FC<ServiceUnavailableBannerProps> = ({
  onRetryAll,
  message = "Mbiu can't check contracts right now. Your clauses are listed below; try again in a few minutes.",
}) => {
  return (
    <div className="service-unavailable-banner" role="alert">
      <div className="banner-icon" aria-hidden="true">
        ⚠️
      </div>
      <div className="banner-text-content">
        <h3 className="banner-title">Service Temporarily Unavailable</h3>
        <p className="banner-message">{message}</p>
      </div>
      {onRetryAll && (
        <button
          type="button"
          className="banner-retry-btn"
          onClick={onRetryAll}
        >
          Try Again
        </button>
      )}
    </div>
  );
};
