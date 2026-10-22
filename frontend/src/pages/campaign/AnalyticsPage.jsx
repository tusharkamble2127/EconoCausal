import React from "react";
import { useParams } from "react-router-dom";

import DashboardLayout from "../../components/DashboardLayout.jsx";
import Loader from "../../components/Loader.jsx";
import SectionHeader from "../../components/SectionHeader.jsx";
import UpliftChart from "../../components/UpliftChart.jsx";
import QiniChart from "../../components/QiniChart.jsx";
import BucketChart from "../../components/BucketChart.jsx";
import { useRun } from "../../hooks/useRun.js";

function breadcrumbs(runId) {
  return [
    { label: "Dashboard", to: `/dashboard/${runId}` },
    { label: "Analytics" },
  ];
}

export default function AnalyticsPage() {
  const { runId } = useParams();
  const { run, ite, analytics, error, loading } = useRun(runId);

  if (!runId) {
    return <div className="text-sm text-slate-500 p-6">No run selected.</div>;
  }

  if (error) {
    return (
      <DashboardLayout title="Analytics" subtitle={`Run #${runId}`} breadcrumbs={breadcrumbs(runId)}>
        <div className="text-sm text-brand-danger bg-red-50 border border-red-200 rounded-md px-3 py-2">{error}</div>
      </DashboardLayout>
    );
  }

  if (loading || !run) {
    return (
      <DashboardLayout title="Analytics" subtitle={`Run #${runId}`} breadcrumbs={breadcrumbs(runId)}>
        <Loader label={`Run status: ${run?.status || "starting"}...`} />
      </DashboardLayout>
    );
  }

  const maxLevel = run.discount_levels?.length
    ? Math.max(...run.discount_levels.filter((l) => l > 0))
    : 0;

  return (
    <DashboardLayout title="Analytics" subtitle={`Run #${runId} • ${run.campaign_name}`} breadcrumbs={breadcrumbs(runId)}>
      <div className="space-y-6">
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 flex items-start gap-3">
          <div className="text-sm text-blue-900 leading-relaxed">
            <span className="font-medium">What this page shows:</span> The causal model's performance
            across different targeting strategies, how the budget is distributed across discount levels,
            and the projected revenue trajectory as the campaign spends.
          </div>
        </div>

        <section className="grid md:grid-cols-2 gap-4">
          <div className="bg-white border border-slate-200 rounded-lg p-4">
            <SectionHeader
              title="Causal Impact Curve"
              description="How incremental revenue accumulates as we target more customers"
              tooltip="This curve shows the cumulative predicted uplift when customers are targeted in order of their estimated individual treatment effect (ITE). A steeper curve means the model is good at identifying high-impact customers."
            />
            <UpliftChart data={ite?.scores?.filter((s) => s.discount_level === maxLevel)} />
          </div>
          <div className="bg-white border border-slate-200 rounded-lg p-4">
            <SectionHeader
              title="Qini Curve"
              description="Incremental gain over random targeting"
              tooltip="The Qini curve measures how much better the causal model performs compared to randomly selecting customers. Higher area under the curve indicates stronger targeting ability."
            />
            <QiniChart data={ite?.scores?.filter((s) => s.discount_level === maxLevel)} />
          </div>
        </section>

        {analytics && (
          <section className="grid md:grid-cols-2 gap-4">
            <div className="bg-white border border-slate-200 rounded-lg p-4">
              <SectionHeader
                title="Budget Allocation by Discount"
                description="How the optimized budget is distributed across discount levels"
                tooltip="Shows how the total promotional budget is split among the different discount levels evaluated by the optimizer."
              />
              <BucketChart buckets={analytics.budget_allocation_by_discount} valuePrefix="$" color="#1F4E79" />
            </div>
            <div className="bg-white border border-slate-200 rounded-lg p-4">
              <SectionHeader
                title="Customer Segmentation by Uplift"
                description="Distribution of customers across uplift categories"
                tooltip="Groups customers into segments based on their estimated treatment effect. Helps identify how many customers are persuadable vs. indifferent."
              />
              <BucketChart buckets={analytics.customer_segmentation} color="#7C3AED" />
            </div>
            <div className="bg-white border border-slate-200 rounded-lg p-4">
              <SectionHeader
                title="Historical Treatment Distribution"
                description="How discounts were distributed in the original dataset"
                tooltip="Shows the frequency of each discount level in the uploaded dataset before optimization. Useful for understanding the baseline treatment mix."
              />
              <BucketChart buckets={analytics.treatment_distribution} color="#2E86AB" />
            </div>
            <div className="bg-white border border-slate-200 rounded-lg p-4">
              <SectionHeader
                title="Optimized Discount Distribution"
                description="Recommended discount levels after causal optimization"
                tooltip="Shows the final recommended discount for each customer after the budget optimizer has allocated the budget across discount levels."
              />
              <BucketChart buckets={analytics.discount_distribution} color="#ED6C02" />
            </div>
            <div className="bg-white border border-slate-200 rounded-lg p-4">
              <SectionHeader
                title="Cumulative Revenue Projection"
                description="Expected revenue as the campaign spends its budget"
                tooltip="Projects how total revenue grows as more of the budget is deployed. Shows the diminishing returns effect as lower-ITE customers are targeted."
              />
              <BucketChart buckets={analytics.revenue_projection} kind="line" valuePrefix="$" color="#2E7D32" />
            </div>
            <div className="bg-white border border-slate-200 rounded-lg p-4">
              <SectionHeader
                title="ROI Trend"
                description="Return on investment as budget is spent"
                tooltip="Shows how ROI changes as the campaign exhausts its budget. A declining trend is expected because the model targets the highest-ROI customers first."
              />
              <BucketChart buckets={analytics.roi_trend} kind="line" color="#C62828" />
            </div>
          </section>
        )}
      </div>
    </DashboardLayout>
  );
}
