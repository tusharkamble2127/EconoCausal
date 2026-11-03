import React, { useState, useEffect, useCallback } from "react";
import { HelpCircle, X } from "lucide-react";

export default function InfoTooltip({ term, explanation }) {
  const [open, setOpen] = useState(false);

  const close = useCallback(() => setOpen(false), []);

  useEffect(() => {
    if (!open) return;
    const onKey = (e) => {
      if (e.key === "Escape") close();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, close]);

  return (
    <span className="inline-flex items-center relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        onBlur={(e) => {
          if (!e.currentTarget.contains(e.relatedTarget)) close();
        }}
        className="text-slate-400 hover:text-brand-secondary transition-colors"
        aria-label={`Learn more about ${term}`}
        aria-expanded={open}
      >
        <HelpCircle size={14} />
      </button>
      {open && (
        <span
          role="tooltip"
          className="absolute z-50 bottom-full left-0 mb-2 w-64 max-w-[calc(100vw-24px)] bg-slate-900 text-white text-xs rounded-lg px-3 py-2 shadow-lg leading-relaxed break-words"
        >
          {explanation}
          <button
            onClick={close}
            onBlur={(e) => {
              if (!e.currentTarget.contains(e.relatedTarget)) close();
            }}
            className="absolute top-1 right-1 text-white/60 hover:text-white"
            aria-label="Close tooltip"
          >
            <X size={12} />
          </button>
        </span>
      )}
    </span>
  );
}
