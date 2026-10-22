import React from "react";
import { CheckCircle2, XCircle, HelpCircle } from "lucide-react";

const TEST_DESCRIPTIONS = {
  PlaceboTreatment: "Replaces the real treatment with a random placebo to check if the effect disappears.",
  RandomCommonCause: "Adds a random noise variable to see if the model falsely attributes it to the treatment.",
  DataSubset: "Tests whether the estimate is stable when using only a subset of the data.",
};

export default function RefutationPanel({ refutation }) {
  const tests = refutation?.tests || [];
  if (tests.length === 0) {
    return (
      <div className="flex items-center gap-2 text-sm text-slate-500 py-6">
        <HelpCircle size={16} />
        No refutation results yet.
      </div>
    );
  }

  return (
    <ul className="space-y-2">
      {tests.map((t) => (
        <li key={t.test_name} className="flex items-center gap-2 text-sm">
          {t.passed ? (
            <CheckCircle2 size={16} className="text-brand-success shrink-0" />
          ) : (
            <XCircle size={16} className="text-brand-danger shrink-0" />
          )}
          <span className="font-medium text-slate-800">{t.test_name}</span>
          <span
            className="ml-auto text-xs font-medium"
            title={TEST_DESCRIPTIONS[t.test_name] || "Robustness check for the causal estimate"}
          >
            {t.passed ? (
              <span className="text-brand-success">Passed</span>
            ) : (
              <span className="text-brand-danger">Failed</span>
            )}
          </span>
        </li>
      ))}
    </ul>
  );
}
