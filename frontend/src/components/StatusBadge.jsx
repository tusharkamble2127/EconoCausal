import React from "react";

export default function StatusBadge({ status }) {
  const tone =
    status === "complete"
      ? "bg-brand-success/10 text-brand-success"
      : status === "running"
        ? "bg-brand-secondary/10 text-brand-secondary"
        : status === "pending"
          ? "bg-slate-100 text-slate-500"
          : status === "failed"
            ? "bg-brand-danger/10 text-brand-danger"
            : "bg-slate-100 text-slate-500";

  return (
    <span className={`inline-flex items-center text-xs font-medium px-2 py-0.5 rounded-full capitalize ${tone}`}>
      {status}
    </span>
  );
}
