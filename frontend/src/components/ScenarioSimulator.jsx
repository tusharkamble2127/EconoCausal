import React, { useState } from "react";
import { Play } from "lucide-react";

import { useScenario } from "../hooks/useScenario.js";
import DiscountLevelPicker from "./DiscountLevelPicker.jsx";

export default function ScenarioSimulator({ runId, defaultBudget, availableLevels }) {
  const { simulate, result, running, error } = useScenario(runId);
  const [budget, setBudget] = useState(defaultBudget ?? 0);
  const [levels, setLevels] = useState(availableLevels || [0]);

  const handleRun = (e) => {
    e.preventDefault();
    simulate(Number(budget), levels);
  };

  return (
    <form onSubmit={handleRun} className="space-y-4">
      <div>
        <label className="block text-sm font-medium text-slate-700 mb-1">Hypothetical budget ($)</label>
        <input
          type="number"
          min="0"
          value={budget}
          onChange={(e) => setBudget(e.target.value)}
          className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-secondary"
        />
        <p className="text-xs text-slate-400 mt-1">Current campaign budget: ${defaultBudget?.toFixed(0) || "0"}</p>
      </div>

      <div>
        <label className="block text-sm font-medium text-slate-700 mb-1">Allowed discount levels</label>
        <div className="flex flex-wrap gap-2">
          {(availableLevels || []).map((level) => (
            <label key={level} className="flex items-center gap-1.5 text-sm">
              <input
                type="checkbox"
                checked={levels.includes(level)}
                disabled={level === 0}
                onChange={(e) =>
                  setLevels((prev) => (e.target.checked ? [...prev, level] : prev.filter((l) => l !== level)))
                }
              />
              {level}%
            </label>
          ))}
        </div>
      </div>

      <button
        type="submit"
        disabled={running}
        className="flex items-center gap-2 bg-brand-secondary text-white px-4 py-2 rounded-md text-sm font-medium disabled:opacity-50 hover:bg-brand-secondary/90 transition-colors"
      >
        <Play size={14} />
        {running ? "Simulating..." : "Run simulation"}
      </button>

      {error && <div className="text-sm text-brand-danger">{error}</div>}

      {result && (
        <div className="grid grid-cols-2 gap-3 pt-3 border-t border-slate-100">
          <Stat label="Budget used" value={`$${result.total_budget_used.toFixed(2)}`} />
          <Stat label="Customers targeted" value={result.customers_targeted} />
          <Stat label="Estimated uplift" value={result.estimated_uplift.toFixed(3)} />
          <Stat label="Average discount" value={`${result.average_discount.toFixed(2)}%`} />
        </div>
      )}
    </form>
  );
}

function Stat({ label, value }) {
  return (
    <div>
      <div className="text-xs text-slate-500">{label}</div>
      <div className="text-base font-semibold text-slate-900 tabular-nums">{value}</div>
    </div>
  );
}
