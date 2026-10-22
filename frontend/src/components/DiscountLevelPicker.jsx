import React, { useState } from "react";
import { Plus, X } from "lucide-react";

/**
 * Lets the campaign owner customize which discount levels EconML should
 * evaluate (Enhancement #3). 0% is always included as the "no discount"
 * control arm and cannot be removed.
 */
export default function DiscountLevelPicker({ levels, onChange }) {
  const [draft, setDraft] = useState("");

  const addLevel = () => {
    const value = parseFloat(draft);
    if (Number.isNaN(value) || !Number.isFinite(value) || value < 0 || value > 100) return;
    const rounded = Math.round(value * 100) / 100;
    if (levels.includes(rounded)) {
      setDraft("");
      return;
    }
    onChange([...levels, rounded].sort((a, b) => a - b));
    setDraft("");
  };

  const removeLevel = (value) => {
    if (value === 0) return;
    onChange(levels.filter((l) => l !== value));
  };

  return (
    <div>
      <div className="flex flex-wrap gap-2 mb-2">
        {levels.map((level) => (
          <span
            key={level}
            className="inline-flex items-center gap-1 rounded-full bg-brand-secondary/10 text-brand-secondary text-sm font-medium px-3 py-1"
          >
            {level}%
            {level !== 0 && (
              <button
                type="button"
                onClick={() => removeLevel(level)}
                className="hover:text-brand-danger"
                aria-label={`Remove ${level}% discount level`}
              >
                <X size={13} />
              </button>
            )}
          </span>
        ))}
      </div>
      <div className="flex gap-2">
        <input
          type="number"
          min="0"
          max="100"
          step="any"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), addLevel())}
          placeholder="Add a discount level, e.g. 12.5"
          className="flex-1 rounded-md border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-secondary"
        />
        <button
          type="button"
          onClick={addLevel}
          className="flex items-center gap-1 rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-600 hover:bg-slate-50"
        >
          <Plus size={14} /> Add
        </button>
      </div>
      <p className="mt-1 text-xs text-slate-400">0% is always included as the control (no-discount) arm.</p>
    </div>
  );
}
