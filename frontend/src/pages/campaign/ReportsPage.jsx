import React from "react";
import { useParams } from "react-router-dom";

import DashboardLayout from "../../components/DashboardLayout.jsx";
import Loader from "../../components/Loader.jsx";
import InfoTooltip from "../../components/InfoTooltip.jsx";
import ReportButtons from "../../components/ReportButtons.jsx";
import { useRun } from "../../hooks/useRun.js";

function breadcrumbs(runId) {
  return [
    { label: "Dashboard", to: `/dashboard/${runId}` },
    { label: "Reports" },
  ];
}

export default function ReportsPage() {
  const { runId } = useParams();
  const { run, error, loading } = useRun(runId);

  if (!runId) {
    return <div className="text-sm text-slate-500 p-6">No run selected.</div>;
  }

  if (error) {
    return (
      <DashboardLayout title="Reports" subtitle={`Run #${runId}`} breadcrumbs={breadcrumbs(runId)}>
        <div className="text-sm text-brand-danger bg-red-50 border border-red-200 rounded-md px-3 py-2">{error}</div>
      </DashboardLayout>
    );
  }

  if (loading || !run) {
    return (
      <DashboardLayout title="Reports" subtitle={`Run #${runId}`} breadcrumbs={breadcrumbs(runId)}>
        <Loader label={`Run status: ${run?.status || "starting"}...`} />
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout title="Reports" subtitle={`Run #${runId} • ${run.campaign_name}`} breadcrumbs={breadcrumbs(runId)}>
      <div className="max-w-3xl space-y-6">
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 flex items-start gap-3">
          <div className="text-sm text-blue-900 leading-relaxed">
            <span className="font-medium">Export campaign results:</span> Download detailed reports for offline
            analysis, sharing with stakeholders, or archival.{" "}
            <InfoTooltip
              term="Report contents"
              explanation="The CSV contains customer-level allocation data with confidence scores. The PDF contains a formatted KPI summary and allocation details for the first 200 customers."
            />
          </div>
        </div>

        <div className="bg-white border border-slate-200 rounded-lg p-6">
          <div className="flex items-start justify-between">
            <div>
              <h2 className="text-sm font-semibold text-slate-900">Campaign Report</h2>
              <p className="text-xs text-slate-500 mt-1">
                Run #${run.run_id} • {run.campaign_name} • {new Date(run.started_at).toLocaleDateString()}
              </p>
            </div>
            <ReportButtons runId={run.run_id} />
          </div>

          <div className="mt-6 grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-slate-50 rounded p-3">
              <div className="text-[10px] text-slate-500 uppercase">Budget</div>
              <div className="text-sm font-medium text-slate-800">${run.budget.toFixed(0)}</div>
            </div>
            <div className="bg-slate-50 rounded p-3">
              <div className="text-[10px] text-slate-500 uppercase">Estimator</div>
              <div className="text-sm font-medium text-slate-800">{run.base_estimator}</div>
            </div>
            <div className="bg-slate-50 rounded p-3">
              <div className="text-[10px] text-slate-500 uppercase">Status</div>
              <div className="text-sm font-medium text-slate-800 capitalize">{run.status}</div>
            </div>
            <div className="bg-slate-50 rounded p-3">
              <div className="text-[10px] text-slate-500 uppercase">Discount Levels</div>
              <div className="text-sm font-medium text-slate-800">{run.discount_levels?.join(", ")}%</div>
            </div>
          </div>

          <div className="mt-6 pt-4 border-t border-slate-100">
            <h3 className="text-xs font-medium text-slate-700 mb-3">Available exports</h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div className="flex items-start gap-3 p-3 rounded-md border border-slate-200">
                <div className="w-8 h-8 rounded bg-green-50 flex items-center justify-center shrink-0">
                  <span className="text-green-700 text-xs font-bold">CSV</span>
                </div>
                <div>
                  <div className="text-sm font-medium text-slate-800">Customer Allocation Export</div>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Per-customer recommended discounts, uplift, purchase probability, and reliability scores.
                  </p>
                </div>
              </div>
              <div className="flex items-start gap-3 p-3 rounded-md border border-slate-200">
                <div className="w-8 h-8 rounded bg-red-50 flex items-center justify-center shrink-0">
                  <span className="text-red-700 text-xs font-bold">PDF</span>
                </div>
                <div>
                  <div className="text-sm font-medium text-slate-800">Executive Summary Report</div>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Formatted KPI summary and allocation details for stakeholders.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
}
