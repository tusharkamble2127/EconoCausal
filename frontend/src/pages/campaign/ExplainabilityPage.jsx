import React from "react";
import { useParams } from "react-router-dom";

import DashboardLayout from "../../components/DashboardLayout.jsx";
import Loader from "../../components/Loader.jsx";
import InfoTooltip from "../../components/InfoTooltip.jsx";
import ExplainabilityPanel from "../../components/ExplainabilityPanel.jsx";
import { useRun } from "../../hooks/useRun.js";

function breadcrumbs(runId) {
  return [
    { label: "Dashboard", to: `/dashboard/${runId}` },
    { label: "Analysis", to: `/dashboard/${runId}/analytics` },
    { label: "Explainability" },
  ];
}

export default function ExplainabilityPage() {
  const { runId } = useParams();
  const { explainability, error, loading, run } = useRun(runId);

  if (!runId) {
    return <div className="text-sm text-slate-500 p-6">No run selected.</div>;
  }

  if (error) {
    return (
      <DashboardLayout title="Explainability" subtitle={`Run #${runId}`} breadcrumbs={breadcrumbs(runId)}>
        <div className="text-sm text-brand-danger bg-red-50 border border-red-200 rounded-md px-3 py-2">{error}</div>
      </DashboardLayout>
    );
  }

  if (loading || !run) {
    return (
      <DashboardLayout title="Explainability" subtitle={`Run #${runId}`} breadcrumbs={breadcrumbs(runId)}>
        <Loader label={`Run status: ${run?.status || "starting"}...`} />
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout title="Explainability" subtitle={`Run #${runId} • ${run.campaign_name}`} breadcrumbs={breadcrumbs(runId)}>
      <div className="max-w-5xl space-y-6">
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 flex items-start gap-3">
          <div className="text-sm text-blue-900 leading-relaxed">
            <span className="font-medium">What this page shows:</span> Which customer characteristics most
            influenced the estimated causal effect. Higher values mean the feature had a stronger influence
            on the model's predictions.{" "}
            <InfoTooltip
              term="How to read feature importance"
              explanation="Feature importance is measured by how much each feature contributes to the model's predictions. A feature with 30% importance means it accounts for roughly 30% of the variation in predicted treatment effects across customers."
            />
          </div>
        </div>

        <div className="bg-white border border-slate-200 rounded-lg p-4">
          <ExplainabilityPanel explainability={explainability} />
        </div>
      </div>
    </DashboardLayout>
  );
}
