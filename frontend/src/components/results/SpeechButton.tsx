"use client";

import React, { useEffect, useState } from "react";

export interface SpeechButtonProps {
  text: string;
}

export type ReadAloudButtonProps = SpeechButtonProps;

export const SpeechButton: React.FC<SpeechButtonProps> = ({ text }) => {
  const [isSpeaking, setIsSpeaking] = useState<boolean>(false);

  useEffect(() => {
    return () => {
      if (typeof window !== "undefined" && "speechSynthesis" in window) {
        window.speechSynthesis.cancel();
      }
    };
  }, []);

  const handleToggleSpeech = () => {
    if (typeof window === "undefined" || !("speechSynthesis" in window)) {
      return;
    }

    if (isSpeaking) {
      window.speechSynthesis.cancel();
      setIsSpeaking(false);
      return;
    }

    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = "en-KE";
    utterance.onend = () => setIsSpeaking(false);
    utterance.onerror = () => setIsSpeaking(false);
    setIsSpeaking(true);
    window.speechSynthesis.speak(utterance);
  };

  return (
    <button
      type="button"
      onClick={handleToggleSpeech}
      className={`read-aloud-btn ${isSpeaking ? "speaking" : ""}`}
      aria-label={isSpeaking ? "Stop reading aloud" : "Read card summary aloud"}
      title={isSpeaking ? "Stop speech" : "Read aloud on this device"}
    >
      <span className="speaker-icon" aria-hidden="true">
        {isSpeaking ? "⏹" : "🔊"}
      </span>
      <span>{isSpeaking ? "Stop reading" : "Read aloud"}</span>
      {isSpeaking && <span className="speaking-pulse" aria-hidden="true" />}
    </button>
  );
};

export const ReadAloudButton = SpeechButton;
