import { useState } from "react";

import { askAssistant } from "../api/client.js";

/**
 * Drives the AI assistant chat panel (Phase 3). Keeps a simple local
 * transcript; each question is answered independently by the backend's
 * templated-NLG endpoint.
 */
export function useAssistant(runId) {
  const [messages, setMessages] = useState([
    { role: "assistant", text: "Ask me about this campaign's budget, ROI, confidence, or data drift." },
  ]);
  const [asking, setAsking] = useState(false);

  const ask = async (question) => {
    if (!question.trim()) return;
    setMessages((prev) => [...prev, { role: "user", text: question }]);
    setAsking(true);
    try {
      const data = await askAssistant(runId, question);
      setMessages((prev) => [...prev, { role: "assistant", text: data.answer }]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", text: "Sorry, I couldn't reach the analysis backend just now." },
      ]);
    } finally {
      setAsking(false);
    }
  };

  return { messages, ask, asking };
}
