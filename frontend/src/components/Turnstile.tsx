"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";

import { TURNSTILE_SITE_KEY } from "@/lib/env";

declare global {
  interface Window {
    turnstile?: {
      render: (
        container: HTMLElement,
        options: {
          sitekey: string;
          callback?: (token: string) => void;
          "error-callback"?: (errorCode?: string) => void;
          "expired-callback"?: () => void;
          theme?: "light" | "dark" | "auto";
          retry?: "auto" | "never";
          "retry-interval"?: number;
        }
      ) => string;
      reset: (widgetId: string) => void;
      remove: (widgetId: string) => void;
    };
  }
}

interface TurnstileProps {
  siteKey?: string;
  onSuccess: (token: string) => void;
  onError?: (err?: string) => void;
  onExpire?: () => void;
}

const SCRIPT_ID = "cf-turnstile-script";
const MAX_AUTO_RETRIES = 2;

export function Turnstile({
  siteKey = TURNSTILE_SITE_KEY,
  onSuccess,
  onError,
  onExpire,
}: TurnstileProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const widgetIdRef = useRef<string | null>(null);
  const autoRetryCountRef = useRef(0);
  const [attempt, setAttempt] = useState(0);
  const [hasFailed, setHasFailed] = useState(false);

  // Callbacks live in a ref so a parent re-render doesn't reset the widget
  const callbacks = useRef({ onSuccess, onError, onExpire });
  useEffect(() => {
    callbacks.current = { onSuccess, onError, onExpire };
  });

  const handleManualRetry = useCallback(() => {
    autoRetryCountRef.current = 0;
    setHasFailed(false);
    const existingScript = document.getElementById(SCRIPT_ID);
    if (existingScript && !window.turnstile) {
      existingScript.remove();
    }
    setAttempt((n) => n + 1);
  }, []);

  useEffect(() => {
    if (!siteKey) {
      callbacks.current.onError?.("Turnstile site key is not set");
      return;
    }

    let cancelled = false;
    let pollTimer: ReturnType<typeof setInterval> | null = null;
    let retryTimer: ReturnType<typeof setTimeout> | null = null;

    const clearTimers = () => {
      if (pollTimer) {
        clearInterval(pollTimer);
        pollTimer = null;
      }
      if (retryTimer) {
        clearTimeout(retryTimer);
        retryTimer = null;
      }
    };

    const handleFailure = (reason?: string) => {
      if (cancelled) return;
      clearTimers();
      if (widgetIdRef.current && window.turnstile) {
        try {
          window.turnstile.remove(widgetIdRef.current);
        } catch {
          // Ignore widget cleanup errors
        }
        widgetIdRef.current = null;
      }

      if (autoRetryCountRef.current < MAX_AUTO_RETRIES) {
        autoRetryCountRef.current += 1;
        retryTimer = setTimeout(() => {
          if (!cancelled) {
            const brokenScript = document.getElementById(SCRIPT_ID);
            if (brokenScript && !window.turnstile) {
              brokenScript.remove();
            }
            setAttempt((n) => n + 1);
          }
        }, 900 * autoRetryCountRef.current);
        return;
      }

      setHasFailed(true);
      callbacks.current.onError?.(reason);
    };

    const renderWidget = () => {
      if (cancelled || !window.turnstile || !containerRef.current || widgetIdRef.current) return;
      clearTimers();
      try {
        containerRef.current.innerHTML = "";
        widgetIdRef.current = window.turnstile.render(containerRef.current, {
          sitekey: siteKey,
          callback: (token) => {
            if (cancelled) return;
            autoRetryCountRef.current = 0;
            setHasFailed(false);
            callbacks.current.onSuccess(token);
          },
          "error-callback": (err) => handleFailure(err),
          "expired-callback": () => {
            if (cancelled) return;
            callbacks.current.onExpire?.();
            if (widgetIdRef.current && window.turnstile) {
              try {
                window.turnstile.reset(widgetIdRef.current);
              } catch {
                // Ignore reset error
              }
            }
          },
          retry: "auto",
          "retry-interval": 1500,
          theme: "auto",
        });
      } catch {
        handleFailure("Failed to render security check");
      }
    };

    const failToLoad = () => {
      const s = document.getElementById(SCRIPT_ID);
      if (s) s.setAttribute("data-failed", "true");
      handleFailure("Failed to load Turnstile bot check");
    };

    let script = document.getElementById(SCRIPT_ID) as HTMLScriptElement | null;
    if (script && script.getAttribute("data-failed") === "true") {
      script.remove();
      script = null;
    }

    if (window.turnstile) {
      renderWidget();
    } else {
      if (!script) {
        script = document.createElement("script");
        script.id = SCRIPT_ID;
        script.src = "https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit";
        script.async = true;
        script.defer = true;
        script.addEventListener("load", renderWidget);
        script.addEventListener("error", failToLoad);
        document.head.appendChild(script);
      } else {
        script.addEventListener("load", renderWidget);
        script.addEventListener("error", failToLoad);
      }

      // Poll for window.turnstile in case the script finished loading before our listener attached
      let elapsed = 0;
      pollTimer = setInterval(() => {
        elapsed += 150;
        if (window.turnstile) {
          renderWidget();
        } else if (elapsed >= 10000) {
          failToLoad();
        }
      }, 150);
    }

    return () => {
      cancelled = true;
      clearTimers();
      script?.removeEventListener("load", renderWidget);
      script?.removeEventListener("error", failToLoad);
      if (widgetIdRef.current && window.turnstile) {
        try {
          window.turnstile.remove(widgetIdRef.current);
        } catch {
          // Ignore cleanup errors
        }
        widgetIdRef.current = null;
      }
    };
  }, [siteKey, attempt]);

  return (
    <div className="turnstile-container">
      <div ref={containerRef} aria-label="Security check" />
      {hasFailed && (
        <div className="mt-2 flex items-center gap-3">
          <button
            type="button"
            onClick={handleManualRetry}
            className="secondary-btn text-[0.82rem] font-semibold underline"
          >
            ↻ Retry security check
          </button>
        </div>
      )}
    </div>
  );
}
