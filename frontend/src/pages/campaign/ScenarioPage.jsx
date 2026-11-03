import React from "react";
import { useParams } from "react-router-dom";

import DashboardLayout from "../../components/DashboardLayout.jsx";
import Loader from "../../components/Loader.jsx";
import InfoTooltip from "../../components/InfoTooltip.jsx";
import ScenarioSimulator from "../../components/ScenarioSimulator.jsx";
import { useRun } from "../../hooks/useRun.js";

function breadcrumbs(runId) {
  return [
    { label: "Dashboard", to: `/dashboard/${runId}` },
    { label: "Decisions", to: `/dashboard/${runId}/recommendations` },
    { label: "Scenario Simulator" },
  ];
}

export default function ScenarioPage() {
  const { runId } = useParams();
  const { run, error, loading } = useRun(runId);

  if (!runId) {
    return <div className="text-sm text-slate-500 p-6">No run selected.</div>;
  }

  if (error) {
    return (
      <DashboardLayout title="Scenario Simulator" subtitle={`Run #${runId}`} breadcrumbs={breadcrumbs(runId)}>
        <div className="text-sm text-brand-danger bg-red-50 border border-red-200 rounded-md px-3 py-2">{error}</div>
      </DashboardLayout>
    );
  }

  if (loading || !run) {
    return (
      <DashboardLayout title="Scenario Simulator" subtitle={`Run #${runId}`} breadcrumbs={breadcrumbs(runId)}>
        <Loader label={`Run status: ${run?.status || "starting"}...`} />
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout title="Scenario Simulator" subtitle={`Run #${runId} • ${run.campaign_name}`} breadcrumbs={breadcrumbs(runId)}>
      <div className="max-w-3xl space-y-6">
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 flex items-start gap-3">
          <div className="text-sm text-blue-900 leading-relaxed">
            <span className="font-medium">What-if analysis:</span> Test alternative budgets and discount levels
            without retraining the model. The simulator re-optimizes over the existing ITE estimates to show
            how outcomes would change under different constraints.{" "}
            <InfoTooltip
              term="How simulation works"
              explanation="The scenario simulator uses the already-estimated individual treatment effects and re-solves the budget optimization problem under your new constraints. No retraining is needed — results are available instantly."
            />
          </div>
        </div>

        <div className="bg-white border border-slate-200 rounded-lg p-5">
          <ScenarioSimulator
            runId={run.run_id}
            defaultBudget={run.budget}
            availableLevels={run.discount_levels}
          />
        </div>
      </div>
    </DashboardLayout>
  );
}
