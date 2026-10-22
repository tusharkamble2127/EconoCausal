import React from "react";
import { useParams } from "react-router-dom";

import DashboardLayout from "../../components/DashboardLayout.jsx";
import Loader from "../../components/Loader.jsx";
import InfoTooltip from "../../components/InfoTooltip.jsx";
import RecommendationPanel from "../../components/RecommendationPanel.jsx";
import { useRun } from "../../hooks/useRun.js";

function breadcrumbs(runId) {
  return [
    { label: "Dashboard", to: `/dashboard/${runId}` },
    { label: "Decisions", to: `/dashboard/${runId}/recommendations` },
    { label: "Recommendations" },
  ];
}

export default function RecommendationsPage() {
  const { runId } = useParams();
  const { recommendations, error, loading, run } = useRun(runId);

  if (!runId) {
    return <div className="text-sm text-slate-500 p-6">No run selected.</div>;
  }

  if (error) {
    return (
      <DashboardLayout title="Recommendations" subtitle={`Run #${runId}`} breadcrumbs={breadcrumbs(runId)}>
        <div className="text-sm text-brand-danger bg-red-50 border border-red-200 rounded-md px-3 py-2">{error}</div>
      </DashboardLayout>
    );
  }

  if (loading || !run) {
    return (
      <DashboardLayout title="Recommendations" subtitle={`Run #${runId}`} breadcrumbs={breadcrumbs(runId)}>
        <Loader label={`Run status: ${run?.status || "starting"}...`} />
      </DashboardLayout>
    );
  }

  const recs = recommendations?.recommendations || [];
  const targetedRecs = recs.filter((r) => (r.recommended_discount || 0) > 0);
  const totalUplift = recs.reduce((s, r) => s + (r.expected_uplift || 0), 0);
  const avgDiscount = recs.length ? (recs.reduce((s, r) => s + (r.recommended_discount || 0), 0) / recs.length).toFixed(2) : 0;
  const avgConfidence = targetedRecs.length
    ? (targetedRecs.reduce((s, r) => s + (r.confidence_score || 0), 0) / targetedRecs.length * 100).toFixed(0)
    : 0;

  return (
    <DashboardLayout title="Recommendations" subtitle={`Run #${runId} • ${run.campaign_name}`} breadcrumbs={breadcrumbs(runId)}>
      <div className="space-y-6">
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 flex items-start gap-3">
          <div className="text-sm text-blue-900 leading-relaxed">
            <span className="font-medium">Decision support:</span> These recommendations identify which customers
            should receive a discount and at what level, based on causal analysis. Customers with positive
            estimated treatment effects are predicted to respond to the discount; those with near-zero effects
            are unlikely to change behavior.{" "}
            <InfoTooltip
              term="How recommendations are made"
              explanation="The optimizer uses the estimated individual treatment effects (ITE) to allocate the fixed budget across customers and discount levels. It maximizes expected incremental revenue while respecting the budget constraint."
            />
          </div>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-white border border-slate-200 rounded-lg p-4">
            <div className="text-xs font-medium uppercase tracking-wide text-slate-500">Customers Targeted</div>
            <div className="mt-1 text-xl font-semibold text-slate-900">{recs.length.toLocaleString()}</div>
            <p className="text-[10px] text-slate-400 mt-1">Total customers in dataset</p>
          </div>
          <div className="bg-white border border-slate-200 rounded-lg p-4">
            <div className="text-xs font-medium uppercase tracking-wide text-slate-500">Expected Incremental Revenue</div>
            <div className="mt-1 text-xl font-semibold text-slate-900">${totalUplift.toFixed(0)}</div>
            <p className="text-[10px] text-slate-400 mt-1">Above blanket targeting</p>
          </div>
          <div className="bg-white border border-slate-200 rounded-lg p-4">
            <div className="text-xs font-medium uppercase tracking-wide text-slate-500">Average Discount</div>
            <div className="mt-1 text-xl font-semibold text-slate-900">{avgDiscount}%</div>
            <p className="text-[10px] text-slate-400 mt-1">Mean across all customers</p>
          </div>
          <div className="bg-white border border-slate-200 rounded-lg p-4">
            <div className="text-xs font-medium uppercase tracking-wide text-slate-500">Avg Reliability</div>
            <div className="mt-1 text-xl font-semibold text-slate-900">
              {avgConfidence}%
            </div>
            <p className="text-[10px] text-slate-400 mt-1">Targeted customers only</p>
          </div>
        </div>

        <div className="bg-white border border-slate-200 rounded-lg p-4">
          <RecommendationPanel recommendations={recommendations} />
        </div>
      </div>
    </DashboardLayout>
  );
}
