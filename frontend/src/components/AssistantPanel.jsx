import React, { useState } from "react";
import { Bot, Send, User } from "lucide-react";

import { useAssistant } from "../hooks/useAssistant.js";

const SUGGESTIONS_BY_CONTEXT = {
  default: [
    "Explain this campaign",
    "Who should we target?",
    "Why is this allocation recommended?",
    "Summarize the causal results",
    "Explain the refutation result",
  ],
};

export default function AssistantPanel({ runId }) {
  const { messages, ask, asking } = useAssistant(runId);
  const [draft, setDraft] = useState("");

  const suggestions = SUGGESTIONS_BY_CONTEXT.default;

  const send = (text) => {
    const question = (text ?? draft).trim();
    if (!question) return;
    ask(question);
    setDraft("");
  };

  return (
    <div className="flex flex-col h-[420px]">
      <div className="flex-1 overflow-y-auto space-y-3 pr-1" role="log" aria-live="polite">
        {messages.map((m, i) => (
          <div key={i} className={`flex gap-2 ${m.role === "user" ? "justify-end" : ""}`}>
            {m.role === "assistant" && (
              <div className="w-6 h-6 rounded-full bg-brand-primary/10 text-brand-primary flex items-center justify-center shrink-0" aria-hidden="true">
                <Bot size={13} />
              </div>
            )}
            <div
              className={`text-sm rounded-lg px-3 py-2 max-w-[85%] ${
                m.role === "user" ? "bg-brand-primary text-white" : "bg-slate-100 text-slate-700"
              }`}
            >
              {m.text}
            </div>
            {m.role === "user" && (
              <div className="w-6 h-6 rounded-full bg-slate-200 text-slate-500 flex items-center justify-center shrink-0" aria-hidden="true">
                <User size={13} />
              </div>
            )}
          </div>
        ))}
        {asking && (
          <div className="text-xs text-slate-400 pl-8 flex items-center gap-2">
            <span className="inline-block w-3 h-3 border-2 border-slate-300 border-t-brand-secondary rounded-full animate-spin" />
            Thinking...
          </div>
        )}
      </div>

      <div className="flex flex-wrap gap-1.5 mb-2 mt-3">
        {suggestions.map((s) => (
          <button
            key={s}
            onClick={() => send(s)}
            disabled={asking}
            className="text-xs px-2.5 py-1.5 rounded-full border border-slate-200 text-slate-600 hover:border-brand-secondary hover:text-brand-secondary disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {s}
          </button>
        ))}
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          send();
        }}
        className="flex gap-2"
      >
        <label htmlFor="assistant-input" className="sr-only">Ask a question about this campaign</label>
        <input
          id="assistant-input"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder="Ask about this campaign..."
          disabled={asking}
          className="flex-1 rounded-md border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-secondary disabled:bg-slate-50 disabled:text-slate-400"
        />
        <button
          type="submit"
          disabled={asking || !draft.trim()}
          className="bg-brand-primary text-white rounded-md px-3 py-2 disabled:opacity-50 hover:bg-brand-primary/90 transition-colors"
          aria-label="Send message"
        >
          <Send size={15} />
        </button>
      </form>
    </div>
  );
}
