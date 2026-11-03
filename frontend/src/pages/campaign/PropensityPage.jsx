import React from "react";
import { useParams } from "react-router-dom";

import DashboardLayout from "../../components/DashboardLayout.jsx";
import Loader from "../../components/Loader.jsx";
import InfoTooltip from "../../components/InfoTooltip.jsx";
import PropensityPanel from "../../components/PropensityPanel.jsx";
import { useRun } from "../../hooks/useRun.js";

function breadcrumbs(runId) {
  return [
    { label: "Dashboard", to: `/dashboard/${runId}` },
    { label: "Analysis", to: `/dashboard/${runId}/analytics` },
    { label: "Propensity & Matching" },
  ];
}

export default function PropensityPage() {
  const { runId } = useParams();
  const { propensity, error, loading, run } = useRun(runId);

  if (!runId) {
    return <div className="text-sm text-slate-500 p-6">No run selected.</div>;
  }

  if (error) {
    return (
      <DashboardLayout title="Propensity & Matching" subtitle={`Run #${runId}`} breadcrumbs={breadcrumbs(runId)}>
        <div className="text-sm text-brand-danger bg-red-50 border border-red-200 rounded-md px-3 py-2">{error}</div>
      </DashboardLayout>
    );
  }

  if (loading || !run) {
    return (
      <DashboardLayout title="Propensity & Matching" subtitle={`Run #${runId}`} breadcrumbs={breadcrumbs(runId)}>
        <Loader label={`Run status: ${run?.status || "starting"}...`} />
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout title="Propensity & Matching" subtitle={`Run #${runId} • ${run.campaign_name}`} breadcrumbs={breadcrumbs(runId)}>
      <div className="max-w-5xl space-y-6">
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 flex items-start gap-3">
          <div className="text-sm text-blue-900 leading-relaxed">
            <span className="font-medium">What this page shows:</span> Propensity scores estimate how likely
            a customer is to receive a discount based on their observed characteristics. This helps assess
            whether treatment and control groups are comparable before causal analysis.{" "}
            <InfoTooltip
              term="Learn more about propensity scores"
              explanation="A propensity score is the probability of receiving the treatment (discount) given a customer's features. It is NOT the same as causal impact — a customer with a high propensity score may simply have been more likely to get a discount regardless of outcome."
            />
          </div>
        </div>

        <div className="bg-white border border-slate-200 rounded-lg p-4">
          <PropensityPanel propensity={propensity} />
        </div>
      </div>
    </DashboardLayout>
  );
}
