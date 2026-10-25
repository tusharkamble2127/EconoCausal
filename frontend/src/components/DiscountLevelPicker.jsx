
import React, { useState } from "react";
import { Plus, X } from "lucide-react";

export default function DiscountLevelPicker({ levels = [], onChange }) {
  const [draft, setDraft] = useState("");
  const [error, setError] = useState("");

  const addLevel = () => {
    const input = draft.trim();

    if (input === "") {
      setError("Please enter a discount percentage.");
      return;
    }

    const value = Number(input);

    if (!Number.isFinite(value) || value < 0 || value > 100) {
      setError("Discount must be between 0% and 100%.");
      return;
    }

    const rounded = Math.round(value * 100) / 100;

    if (levels.includes(rounded)) {
      setError(`${rounded}% already exists.`);
      return;
    }

    onChange([...levels, rounded].sort((a, b) => a - b));
    setDraft("");
    setError("");
  };

  const removeLevel = (value) => {
    if (value === 0) return;

    onChange(levels.filter((level) => level !== value));
    setError("");
  };

  return (
    <div>
      <div className="mb-2 flex flex-wrap gap-2">
        {levels.map((level) => (
          <span
            key={level}
            className="inline-flex items-center gap-1 rounded-full bg-brand-secondary/10 px-3 py-1 text-sm font-medium text-brand-secondary"
          >
            {level}%
            {level !== 0 && (
              <button
                type="button"
                onClick={() => removeLevel(level)}
                aria-label={`Remove ${level}% discount level`}
                className="hover:text-brand-danger"
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
          aria-label="Discount percentage"
          aria-invalid={Boolean(error)}
          aria-describedby={error ? "discount-error" : undefined}
          onChange={(event) => {
            setDraft(event.target.value);
            setError("");
          }}
          onKeyDown={(event) => {
            if (event.key === "Enter") {
              event.preventDefault();
              addLevel();
            }
          }}
          placeholder="Enter discount, e.g. 12.5"
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

      {error && (
        <p
          id="discount-error"
          role="alert"
          className="mt-2 text-sm text-red-600"
        >
          {error}
        </p>
      )}

      <p className="mt-1 text-xs text-slate-400">
        0% is the control (no-discount) arm and cannot be removed.
      </p>
    </div>
  );
}

