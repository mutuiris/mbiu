"use client";

import React, { useEffect, useRef } from "react";

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

export function Turnstile({ siteKey = TURNSTILE_SITE_KEY, onSuccess, onError, onExpire }: TurnstileProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const widgetIdRef = useRef<string | null>(null);
  // Callbacks live in a ref so a parent re-render doesn't reset the widget
  const callbacks = useRef({ onSuccess, onError, onExpire });
  useEffect(() => {
    callbacks.current = { onSuccess, onError, onExpire };
  });

  useEffect(() => {
    // Fail closed: no key or no script means no token, so the form stays disabled
    if (!siteKey) {
      callbacks.current.onError?.("Turnstile site key is not set");
      return;
    }

    const renderWidget = () => {
      if (!window.turnstile || !containerRef.current || widgetIdRef.current) return;
      widgetIdRef.current = window.turnstile.render(containerRef.current, {
        sitekey: siteKey,
        callback: (token) => callbacks.current.onSuccess(token),
        "error-callback": (err) => callbacks.current.onError?.(err),
        "expired-callback": () => callbacks.current.onExpire?.(),
        theme: "auto",
      });
    };
    const failToLoad = () => callbacks.current.onError?.("Failed to load Turnstile bot check");

    let script = document.getElementById(SCRIPT_ID) as HTMLScriptElement | null;
    if (window.turnstile) {
      renderWidget();
    } else if (script) {
      script.addEventListener("load", renderWidget);
      script.addEventListener("error", failToLoad);
    } else {
      script = document.createElement("script");
      script.id = SCRIPT_ID;
      script.src = "https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit";
      script.async = true;
      script.addEventListener("load", renderWidget);
      script.addEventListener("error", failToLoad);
      document.head.appendChild(script);
    }

    return () => {
      script?.removeEventListener("load", renderWidget);
      script?.removeEventListener("error", failToLoad);
      if (widgetIdRef.current && window.turnstile) {
        window.turnstile.remove(widgetIdRef.current);
        widgetIdRef.current = null;
      }
    };
  }, [siteKey]);

  return (
    <div className="turnstile-container">
      <div ref={containerRef} aria-label="Security check" />
    </div>
  );
}
