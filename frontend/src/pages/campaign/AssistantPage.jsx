import React from "react";
import { useParams } from "react-router-dom";

import DashboardLayout from "../../components/DashboardLayout.jsx";
import Loader from "../../components/Loader.jsx";
import InfoTooltip from "../../components/InfoTooltip.jsx";
import AssistantPanel from "../../components/AssistantPanel.jsx";
import { useRun } from "../../hooks/useRun.js";

function breadcrumbs(runId) {
  return [
    { label: "Dashboard", to: `/dashboard/${runId}` },
    { label: "AI Assistant" },
  ];
}

export default function AssistantPage() {
  const { runId } = useParams();
  const { run, error, loading } = useRun(runId);

  if (!runId) {
    return <div className="text-sm text-slate-500 p-6">No run selected.</div>;
  }

  if (error) {
    return (
      <DashboardLayout title="AI Assistant" subtitle={`Run #${runId}`} breadcrumbs={breadcrumbs(runId)}>
        <div className="text-sm text-brand-danger bg-red-50 border border-red-200 rounded-md px-3 py-2">{error}</div>
      </DashboardLayout>
    );
  }

  if (loading || !run) {
    return (
      <DashboardLayout title="AI Assistant" subtitle={`Run #${runId}`} breadcrumbs={breadcrumbs(runId)}>
        <Loader label={`Run status: ${run?.status || "starting"}...`} />
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout title="AI Assistant" subtitle={`Run #${runId} • ${run.campaign_name}`} breadcrumbs={breadcrumbs(runId)}>
      <div className="max-w-3xl space-y-6">
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 flex items-start gap-3">
          <div className="text-sm text-blue-900 leading-relaxed">
            <span className="font-medium">Campaign copilot:</span> Ask about this campaign's causal impact,
            budget allocation, customer targeting, or report results. Get plain-language explanations of the
            analysis.{" "}
            <InfoTooltip
              term="How the assistant works"
              explanation="The AI assistant uses the campaign's computed metrics to generate plain-language summaries. It does not call external LLMs — answers are generated from the run's own data."
            />
          </div>
        </div>

        <div className="bg-white border border-slate-200 rounded-lg p-4">
          <AssistantPanel runId={run.run_id} />
        </div>
      </div>
    </DashboardLayout>
  );
}
