import React from "react";
import { AlertTriangle, CheckCircle2, HelpCircle } from "lucide-react";

export default function DriftPanel({ drift }) {
  if (!drift || !drift.has_reference) {
    return (
      <div className="flex items-center gap-2 text-sm text-slate-500 py-4">
        <HelpCircle size={16} />
        No prior campaign to compare against yet -- drift status will appear starting with your next run.
      </div>
    );
  }

  const driftedFeatures = drift.features?.filter((f) => f.drifted) || [];

  return (
    <div className="space-y-3">
      <div
        className={`flex items-center gap-2 text-sm font-medium rounded-md px-3 py-2 ${
          drift.any_drift ? "bg-brand-warning/10 text-brand-warning" : "bg-brand-success/10 text-brand-success"
        }`}
      >
        {drift.any_drift ? <AlertTriangle size={16} /> : <CheckCircle2 size={16} />}
        {drift.any_drift
          ? `Data drift detected in ${driftedFeatures.length} feature${driftedFeatures.length !== 1 ? "s" : ""} -- review before large-scale rollout.`
          : "No significant data drift detected relative to the previous campaign."}
      </div>

      <div className="grid grid-cols-2 gap-2">
        {drift.features.map((f) => (
          <div
            key={f.feature}
            className={`flex items-center justify-between text-xs px-3 py-2 rounded-md border ${
              f.drifted ? "border-brand-warning/40 bg-brand-warning/5" : "border-slate-200 bg-slate-50"
            }`}
          >
            <span className="font-medium text-slate-700">{f.feature}</span>
            <span className={f.drifted ? "text-brand-warning" : "text-slate-500"}>p={f.p_value.toFixed(3)}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
