import React from "react";
import { useParams } from "react-router-dom";

import DashboardLayout from "../../components/DashboardLayout.jsx";
import Loader from "../../components/Loader.jsx";
import InfoTooltip from "../../components/InfoTooltip.jsx";
import RefutationPanel from "../../components/RefutationPanel.jsx";
import { useRun } from "../../hooks/useRun.js";

function breadcrumbs(runId) {
  return [
    { label: "Dashboard", to: `/dashboard/${runId}` },
    { label: "Analysis", to: `/dashboard/${runId}/analytics` },
    { label: "Refutation" },
  ];
}

export default function RefutationPage() {
  const { runId } = useParams();
  const { refutation, error, loading, run } = useRun(runId);

  if (!runId) {
    return <div className="text-sm text-slate-500 p-6">No run selected.</div>;
  }

  if (error) {
    return (
      <DashboardLayout title="Refutation" subtitle={`Run #${runId}`} breadcrumbs={breadcrumbs(runId)}>
        <div className="text-sm text-brand-danger bg-red-50 border border-red-200 rounded-md px-3 py-2">{error}</div>
      </DashboardLayout>
    );
  }

  if (loading || !run) {
    return (
      <DashboardLayout title="Refutation" subtitle={`Run #${runId}`} breadcrumbs={breadcrumbs(runId)}>
        <Loader label={`Run status: ${run?.status || "starting"}...`} />
      </DashboardLayout>
    );
  }

  const tests = refutation?.tests || [];
  const passedCount = tests.filter((t) => t.passed).length;
  const totalCount = tests.length;
  const overallStatus = totalCount === 0 ? "pending" : passedCount === totalCount ? "passed" : "warning";

  return (
    <DashboardLayout title="Refutation" subtitle={`Run #${runId} • ${run.campaign_name}`} breadcrumbs={breadcrumbs(runId)}>
      <div className="max-w-5xl space-y-6">
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 flex items-start gap-3">
          <div className="text-sm text-blue-900 leading-relaxed">
            <span className="font-medium">What this page shows:</span> Robustness checks that test whether the
            estimated causal relationship remains stable under alternative assumptions.{" "}
            <InfoTooltip
              term="Learn more about refutation"
              explanation="Refutation tests evaluate whether the causal estimate is sensitive to changes in assumptions. Passing tests increase confidence that the observed effect is truly causal and not an artifact of model assumptions or data quirks."
            />
          </div>
        </div>

        <div className="bg-white border border-slate-200 rounded-lg p-4">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-sm font-semibold text-slate-900">Causal Estimate Robustness</h2>
              <p className="text-xs text-slate-500 mt-0.5">
                {totalCount === 0
                  ? "No refutation tests have been run yet."
                  : `${passedCount} of ${totalCount} tests passed`}
              </p>
            </div>
            <span
              className={`text-xs font-medium px-2.5 py-1 rounded-full ${
                overallStatus === "passed"
                  ? "bg-brand-success/10 text-brand-success"
                  : overallStatus === "warning"
                    ? "bg-brand-warning/10 text-brand-warning"
                    : "bg-slate-100 text-slate-500"
              }`}
            >
              {overallStatus === "passed" ? "All tests passed" : overallStatus === "warning" ? "Mixed results" : "Pending"}
            </span>
          </div>
          <RefutationPanel refutation={refutation} />
        </div>
      </div>
    </DashboardLayout>
  );
}
