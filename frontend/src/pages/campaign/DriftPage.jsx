import React from "react";
import { useParams } from "react-router-dom";

import DashboardLayout from "../../components/DashboardLayout.jsx";
import Loader from "../../components/Loader.jsx";
import InfoTooltip from "../../components/InfoTooltip.jsx";
import DriftPanel from "../../components/DriftPanel.jsx";
import { useRun } from "../../hooks/useRun.js";

function breadcrumbs(runId) {
  return [
    { label: "Dashboard", to: `/dashboard/${runId}` },
    { label: "Analysis", to: `/dashboard/${runId}/analytics` },
    { label: "Drift" },
  ];
}

export default function DriftPage() {
  const { runId } = useParams();
  const { drift, error, loading, run } = useRun(runId);

  if (!runId) {
    return <div className="text-sm text-slate-500 p-6">No run selected.</div>;
  }

  if (error) {
    return (
      <DashboardLayout title="Drift" subtitle={`Run #${runId}`} breadcrumbs={breadcrumbs(runId)}>
        <div className="text-sm text-brand-danger bg-red-50 border border-red-200 rounded-md px-3 py-2">{error}</div>
      </DashboardLayout>
    );
  }

  if (loading || !run) {
    return (
      <DashboardLayout title="Drift" subtitle={`Run #${runId}`} breadcrumbs={breadcrumbs(runId)}>
        <Loader label={`Run status: ${run?.status || "starting"}...`} />
      </DashboardLayout>
    );
  }

  const driftedFeatures = drift?.features?.filter((f) => f.drifted) || [];
  const driftAction = drift?.any_drift
    ? "Customer behavior has shifted in several monitored features. Consider reviewing the campaign before applying historical recommendations unchanged."
    : "No significant data drift detected. The current campaign assumptions remain valid relative to the previous run.";

  return (
    <DashboardLayout title="Drift" subtitle={`Run #${runId} • ${run.campaign_name}`} breadcrumbs={breadcrumbs(runId)}>
      <div className="max-w-5xl space-y-6">
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 flex items-start gap-3">
          <div className="text-sm text-blue-900 leading-relaxed">
            <span className="font-medium">What this page shows:</span> Whether customer behavior in the current
            dataset has shifted compared to the previous campaign. Drift detection helps ensure that causal
            recommendations remain valid.{" "}
            <InfoTooltip
              term="What is data drift?"
              explanation="Data drift occurs when the statistical properties of customer features change over time. If drift is detected, historical causal estimates may no longer apply, and the campaign should be retrained on recent data."
            />
          </div>
        </div>

        <div className="bg-white border border-slate-200 rounded-lg p-4">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-sm font-semibold text-slate-900">Data Health</h2>
              <p className="text-xs text-slate-500 mt-0.5">
                {drift?.has_reference
                  ? `Compared against previous campaign • ${driftedFeatures.length} features with drift`
                  : "No prior campaign available for comparison"}
              </p>
            </div>
          </div>
          <DriftPanel drift={drift} />
        </div>

        {drift?.has_reference && (
          <div className={`rounded-lg p-4 flex items-start gap-3 ${drift.any_drift ? "bg-amber-50 border border-amber-200" : "bg-green-50 border border-green-200"}`}>
            <div className="text-sm leading-relaxed">
              <span className="font-medium">{drift.any_drift ? "Recommended action:" : "Status:"}</span>{" "}
              <span className={drift.any_drift ? "text-amber-800" : "text-green-800"}>
                {driftAction}
              </span>
            </div>
          </div>
        )}
      </div>
    </DashboardLayout>
  );
}
