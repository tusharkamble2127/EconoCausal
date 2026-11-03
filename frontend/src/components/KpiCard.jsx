import React from "react";

const ACCENT = {
  primary: "border-l-brand-primary",
  secondary: "border-l-brand-secondary",
  success: "border-l-brand-success",
  warning: "border-l-brand-warning",
  danger: "border-l-brand-danger",
};

/**
 * Single KPI card (Enhancement #4). A colored left accent bar carries the
 * "good/neutral/watch" read of the metric at a glance, without needing a
 * legend -- e.g. green for ROI improvement, amber for budget utilization.
 */
export default function KpiCard({ label, value, sublabel, accent = "primary", icon: Icon }) {
  return (
    <div className={`bg-white rounded-lg border border-slate-200 border-l-4 ${ACCENT[accent]} p-4 shadow-sm`}>
      <div className="flex items-start justify-between">
        <span className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</span>
        {Icon && <Icon size={16} className="text-slate-300" />}
      </div>
      <div className="mt-2 text-2xl font-semibold text-slate-900 tabular-nums">{value}</div>
      {sublabel && <div className="mt-1 text-xs text-slate-500">{sublabel}</div>}
    </div>
  );
}
