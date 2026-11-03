import React from "react";
import { useParams } from "react-router-dom";

import DashboardLayout from "../../components/DashboardLayout.jsx";
import Loader from "../../components/Loader.jsx";
import InfoTooltip from "../../components/InfoTooltip.jsx";
import AllocationTable from "../../components/AllocationTable.jsx";
import { useRun } from "../../hooks/useRun.js";

function breadcrumbs(runId) {
  return [
    { label: "Dashboard", to: `/dashboard/${runId}` },
    { label: "Decisions", to: `/dashboard/${runId}/recommendations` },
    { label: "Allocation" },
  ];
}

export default function AllocationPage() {
  const { runId } = useParams();
  const { allocation, error, loading, run } = useRun(runId);

  if (!runId) {
    return <div className="text-sm text-slate-500 p-6">No run selected.</div>;
  }

  if (error) {
    return (
      <DashboardLayout title="Allocation" subtitle={`Run #${runId}`} breadcrumbs={breadcrumbs(runId)}>
        <div className="text-sm text-brand-danger bg-red-50 border border-red-200 rounded-md px-3 py-2">{error}</div>
      </DashboardLayout>
    );
  }

  if (loading || !run) {
    return (
      <DashboardLayout title="Allocation" subtitle={`Run #${runId}`} breadcrumbs={breadcrumbs(runId)}>
        <Loader label={`Run status: ${run?.status || "starting"}...`} />
      </DashboardLayout>
    );
  }

  const allocs = allocation?.allocations || [];
  const totalBudget = allocation?.budget || run.budget || 0;
  const usedBudget = allocs.reduce((s, a) => s + (a.budget_used || 0), 0);
  const remaining = totalBudget - usedBudget;
  const utilizationPct = totalBudget > 0 ? ((usedBudget / totalBudget) * 100).toFixed(1) : "0.0";

  return (
    <DashboardLayout title="Allocation" subtitle={`Run #${runId} • ${run.campaign_name}`} breadcrumbs={breadcrumbs(runId)}>
      <div className="space-y-6">
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 flex items-start gap-3">
          <div className="text-sm text-blue-900 leading-relaxed">
            <span className="font-medium">What this page shows:</span> The optimized budget prescription for each
            customer — which discount level was chosen and how much budget was consumed. The optimizer allocated
            the budget to maximize expected incremental revenue.{" "}
            <InfoTooltip
              term="How allocation works"
              explanation="The optimizer solves a mixed-integer program that selects a discount level for each customer to maximize total expected uplift, subject to the total budget constraint. Customers with higher estimated treatment effects receive higher discounts."
            />
          </div>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-white border border-slate-200 rounded-lg p-4">
            <div className="text-xs font-medium uppercase tracking-wide text-slate-500">Total Budget</div>
            <div className="mt-1 text-xl font-semibold text-slate-900">${totalBudget.toFixed(0)}</div>
          </div>
          <div className="bg-white border border-slate-200 rounded-lg p-4">
            <div className="text-xs font-medium uppercase tracking-wide text-slate-500">Used Budget</div>
            <div className="mt-1 text-xl font-semibold text-slate-900">${usedBudget.toFixed(0)}</div>
            <div className="text-[10px] text-slate-400 mt-1">{utilizationPct}% utilized</div>
          </div>
          <div className="bg-white border border-slate-200 rounded-lg p-4">
            <div className="text-xs font-medium uppercase tracking-wide text-slate-500">Remaining</div>
            <div className="mt-1 text-xl font-semibold text-slate-900">${remaining.toFixed(0)}</div>
          </div>
          <div className="bg-white border border-slate-200 rounded-lg p-4">
            <div className="text-xs font-medium uppercase tracking-wide text-slate-500">Customers</div>
            <div className="mt-1 text-xl font-semibold text-slate-900">{allocs.length.toLocaleString()}</div>
          </div>
        </div>

        <div className="bg-white border border-slate-200 rounded-lg p-4">
          <AllocationTable allocations={allocs} budget={totalBudget} />
        </div>
      </div>
    </DashboardLayout>
  );
}
