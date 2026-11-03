import React from "react";
import { useParams } from "react-router-dom";

import DashboardLayout from "../../components/DashboardLayout.jsx";
import Loader from "../../components/Loader.jsx";
import SectionHeader from "../../components/SectionHeader.jsx";
import InfoTooltip from "../../components/InfoTooltip.jsx";
import UpliftChart from "../../components/UpliftChart.jsx";
import QiniChart from "../../components/QiniChart.jsx";
import BucketChart from "../../components/BucketChart.jsx";
import { useRun } from "../../hooks/useRun.js";

function breadcrumbs(runId) {
  return [
    { label: "Dashboard", to: `/dashboard/${runId}` },
    { label: "Decisions", to: `/dashboard/${runId}/recommendations` },
    { label: "ITE / Treatment Effects" },
  ];
}

export default function ITEPage() {
  const { runId } = useParams();
  const { run, ite, analytics, error, loading } = useRun(runId);

  if (!runId) {
    return <div className="text-sm text-slate-500 p-6">No run selected.</div>;
  }

  if (error) {
    return (
      <DashboardLayout title="ITE / Treatment Effects" subtitle={`Run #${runId}`} breadcrumbs={breadcrumbs(runId)}>
        <div className="text-sm text-brand-danger bg-red-50 border border-red-200 rounded-md px-3 py-2">{error}</div>
      </DashboardLayout>
    );
  }

  if (loading || !run) {
    return (
      <DashboardLayout title="ITE / Treatment Effects" subtitle={`Run #${runId}`} breadcrumbs={breadcrumbs(runId)}>
        <Loader label={`Run status: ${run?.status || "starting"}...`} />
      </DashboardLayout>
    );
  }

  const maxLevel = run.discount_levels?.length
    ? Math.max(...run.discount_levels.filter((l) => l > 0))
    : 0;

  return (
    <DashboardLayout title="ITE / Treatment Effects" subtitle={`Run #${runId} • ${run.campaign_name}`} breadcrumbs={breadcrumbs(runId)}>
      <div className="space-y-6">
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 flex items-start gap-3">
          <div className="text-sm text-blue-900 leading-relaxed">
            <span className="font-medium">What this page shows:</span> The Individual Treatment Effect (ITE) estimates
            how much the outcome (purchase probability) is expected to change for each customer because of the
            intervention (discount). Positive values indicate customers more likely to convert when targeted;
            negative values indicate customers unlikely to respond.{" "}
            <InfoTooltip
              term="What is ITE?"
              explanation="ITE = Estimated change in outcome for an individual caused by the intervention. Unlike correlation, ITE answers the causal question: 'What would happen to this customer if we gave them a discount vs. if we did not?'"
            />
          </div>
        </div>

        <section className="grid md:grid-cols-2 gap-4">
          <div className="bg-white border border-slate-200 rounded-lg p-4">
            <SectionHeader
              title="Causal Impact Curve"
              description="Cumulative incremental outcome by targeting order"
              tooltip="Shows how total predicted uplift accumulates as customers are targeted in order of their ITE score. A steep initial slope indicates strong early wins."
            />
            <UpliftChart data={ite?.scores?.filter((s) => s.discount_level === maxLevel)} />
          </div>
          <div className="bg-white border border-slate-200 rounded-lg p-4">
            <SectionHeader
              title="Qini Curve"
              description="Incremental gain over random baseline"
              tooltip="Measures how much better the causal model performs compared to randomly selecting customers. Higher area = stronger targeting ability."
            />
            <QiniChart data={ite?.scores?.filter((s) => s.discount_level === maxLevel)} />
          </div>
        </section>

        {analytics && (
          <section className="grid md:grid-cols-2 gap-4">
            <div className="bg-white border border-slate-200 rounded-lg p-4">
              <SectionHeader
                title="Treatment Effect Distribution"
                description="How customers are distributed across predicted impact categories"
                tooltip="Shows the distribution of estimated treatment effects across the customer base. Most customers typically cluster near zero, with a smaller group showing strong positive or negative responses."
              />
              <BucketChart buckets={analytics.customer_segmentation} color="#7C3AED" />
            </div>
            <div className="bg-white border border-slate-200 rounded-lg p-4">
              <SectionHeader
                title="Chosen Discount Distribution"
                description="Recommended discount levels after optimization"
                tooltip="Shows which discount levels the optimizer selected for the customer base after considering budget constraints."
              />
              <BucketChart buckets={analytics.discount_distribution} color="#ED6C02" />
            </div>
          </section>
        )}
      </div>
    </DashboardLayout>
  );
}
