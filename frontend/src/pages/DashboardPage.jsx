import React, { useMemo } from "react";
import { useParams, Link } from "react-router-dom";
import {
  DollarSign,
  PieChart as PieChartIcon,
  Target,
  TrendingUp,
  CheckCircle2,
  AlertTriangle,
  Lightbulb,
  ArrowUpRight,
} from "lucide-react";

import DashboardLayout from "../components/DashboardLayout.jsx";
import Loader from "../components/Loader.jsx";
import KpiCard from "../components/KpiCard.jsx";
import StatusBadge from "../components/StatusBadge.jsx";
import UpliftChart from "../components/UpliftChart.jsx";
import QiniChart from "../components/QiniChart.jsx";
import RecommendationPanel from "../components/RecommendationPanel.jsx";
import InfoTooltip from "../components/InfoTooltip.jsx";
import { useRun } from "../hooks/useRun.js";

export default function DashboardPage() {
  const { runId } = useParams();
  const { run, ite, summary, analytics, recommendations, explainability, drift, refutation, error, loading } =
    useRun(runId);

  const campaignInsight = useMemo(() => {
    if (!summary) return null;
    const parts = [];
    if (summary.roi_improvement_pct > 0) {
      parts.push(
        `causal targeting yields ${summary.roi_improvement_pct.toFixed(1)}% better ROI than blanket targeting`
      );
    }
    if (summary.customers_targeted > 0) {
      parts.push(
        `${summary.customers_targeted.toLocaleString()} of ${summary.customers_total.toLocaleString()} customers received a discount`
      );
    }
    if (summary.incremental_revenue > 0) {
      parts.push(`expected incremental revenue of $${summary.incremental_revenue.toFixed(0)}`);
    }
    if (parts.length === 0) return "Run analysis is still processing or produced no measurable results.";
    return parts.join(", ") + ".";
  }, [summary]);

  if (!runId) {
    return (
      <DashboardLayout title="Dashboard" subtitle="No run selected">
        <div className="text-sm text-slate-500 p-6">No run selected. Go back and start a new campaign.</div>
      </DashboardLayout>
    );
  }

  if (error) {
    return (
      <DashboardLayout title="Dashboard" subtitle={`Run #${runId}`}>
        <div className="text-sm text-brand-danger bg-red-50 border border-red-200 rounded-md px-3 py-2">{error}</div>
      </DashboardLayout>
    );
  }

  if (loading || !run) {
    return (
      <DashboardLayout title="Dashboard" subtitle={`Run #${runId}`}>
        <Loader label={`Run status: ${run?.status || "starting"}...`} />
      </DashboardLayout>
    );
  }

  const maxLevel = run.discount_levels?.length
    ? Math.max(...run.discount_levels.filter((l) => l > 0))
    : 0;

  const recs = recommendations?.recommendations || [];
  const targetedRecs = recs.filter((r) => (r.recommended_discount || 0) > 0);
  const allTestsPassed = refutation?.tests?.length ? refutation.tests.every((t) => t.passed) : null;
  const anyDrift = drift?.any_drift;

  const avgConfidence = targetedRecs.length
    ? (targetedRecs.reduce((s, r) => s + (r.confidence_score || 0), 0) / targetedRecs.length * 100).toFixed(0)
    : "N/A";
  const avgConfidenceRaw = targetedRecs.length
    ? targetedRecs.reduce((s, r) => s + (r.confidence_score || 0), 0) / targetedRecs.length
    : 0;

  return (
    <DashboardLayout title={run.campaign_name} subtitle={`Run #${run.run_id} • ${run.status}`}>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <StatusBadge status={run.status} />
          <span className="text-xs text-slate-400">
            Started {new Date(run.started_at).toLocaleString()}
          </span>
        </div>

        {summary && (
          <>
            <section className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
              <KpiCard
                label={
                  <span className="inline-flex items-center gap-1">
                    Budget Utilization
                    <InfoTooltip term="Budget Utilization" explanation="Percentage of the total budget allocated to discounts." />
                  </span>
                }
                value={`${summary.budget_utilization_pct.toFixed(1)}%`}
                sublabel={`$${summary.budget_used.toFixed(0)} / $${summary.budget.toFixed(0)}`}
                accent="secondary"
                icon={DollarSign}
              />
              <KpiCard
                label={
                  <span className="inline-flex items-center gap-1">
                    Customers Targeted
                    <InfoTooltip term="Customers Targeted" explanation="Customers who received a recommended discount vs. total customers in the dataset." />
                  </span>
                }
                value={`${summary.customers_targeted.toLocaleString()} / ${summary.customers_total.toLocaleString()}`}
                sublabel={`Avg discount ${summary.average_discount.toFixed(2)}%`}
                accent="primary"
                icon={Target}
              />
              <KpiCard
                label={
                  <span className="inline-flex items-center gap-1">
                    ROI Improvement
                    <InfoTooltip term="ROI Improvement" explanation="How much better causal targeting performs compared to giving everyone the same discount." />
                  </span>
                }
                value={`${summary.roi_improvement_pct >= 0 ? "+" : ""}${summary.roi_improvement_pct.toFixed(1)}%`}
                sublabel="vs. blanket targeting"
                accent={summary.roi_improvement_pct >= 0 ? "success" : "danger"}
                icon={TrendingUp}
              />
              <KpiCard
                label={
                  <span className="inline-flex items-center gap-1">
                    Incremental Revenue
                    <InfoTooltip term="Incremental Revenue" explanation="Additional revenue expected because of the causal optimization, above what blanket targeting would generate." />
                  </span>
                }
                value={`$${summary.incremental_revenue.toFixed(0)}`}
                sublabel={`Saves $${summary.savings_vs_blanket.toFixed(0)} vs. blanket`}
                accent="warning"
                icon={PieChartIcon}
              />
              <KpiCard
                label={
                  <span className="inline-flex items-center gap-1">
                    Avg Discount
                    <InfoTooltip term="Avg Discount" explanation="Mean discount percentage across all targeted customers." />
                  </span>
                }
                value={`${summary.average_discount.toFixed(2)}%`}
                sublabel="Mean targeted discount"
                accent="secondary"
              />
                  <KpiCard
                label={
                  <span className="inline-flex items-center gap-1">
                    Reliability
                    <InfoTooltip term="Reliability" explanation="Average reliability score across targeted customers based on statistical uncertainty, model stability, data support, and robustness checks. It is not a probability that the recommendation is correct." />
                  </span>
                }
                value={avgConfidence === "N/A" ? "N/A" : `${avgConfidence}%`}
                sublabel="Targeted customer reliability index"
                accent={avgConfidenceRaw > 0.7 ? "success" : "warning"}
              />
            </section>
          </>
        )}

        {campaignInsight && (
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 flex items-start gap-3">
            <Lightbulb size={18} className="text-brand-secondary shrink-0 mt-0.5" />
            <div>
              <div className="text-sm font-medium text-blue-900">Campaign Insight</div>
              <p className="text-xs text-blue-700 mt-1 leading-relaxed">{campaignInsight}</p>
            </div>
          </div>
        )}

        <section className="grid md:grid-cols-2 gap-4">
          <div className="bg-white border border-slate-200 rounded-lg p-4">
            <h2 className="text-sm font-semibold text-slate-900 mb-1">Causal Impact Curve</h2>
            <p className="text-xs text-slate-500 mb-3">
              How incremental revenue accumulates as we target more customers by descending ITE
            </p>
            <UpliftChart data={ite?.scores?.filter((s) => s.discount_level === maxLevel)} />
          </div>
          <div className="bg-white border border-slate-200 rounded-lg p-4">
            <h2 className="text-sm font-semibold text-slate-900 mb-1">Qini Curve</h2>
            <p className="text-xs text-slate-500 mb-3">Incremental gain over random targeting baseline</p>
            <QiniChart data={ite?.scores?.filter((s) => s.discount_level === maxLevel)} />
          </div>
        </section>

        <div className="grid lg:grid-cols-3 gap-6">
          <section className="lg:col-span-2">
            <div className="flex items-center justify-between mb-2">
              <div>
                <h2 className="text-sm font-semibold text-slate-900">Top Recommendations</h2>
                <p className="text-xs text-slate-500">Highest-reliability customer targeting</p>
              </div>
              <Link
                to={`/dashboard/${runId}/recommendations`}
                className="text-xs text-brand-secondary hover:underline font-medium inline-flex items-center gap-1"
              >
                View all <ArrowUpRight size={12} />
              </Link>
            </div>
            <div className="bg-white border border-slate-200 rounded-lg p-4">
              <RecommendationPanel recommendations={recommendations} />
            </div>
          </section>

          <section className="space-y-6">
            <div>
              <h2 className="text-sm font-semibold text-slate-900 mb-2">Data Quality & Robustness</h2>
              <div className="bg-white border border-slate-200 rounded-lg p-4 space-y-3">
                <div className="flex items-center gap-2 text-sm">
                  {allTestsPassed === true ? (
                    <CheckCircle2 size={16} className="text-brand-success" />
                  ) : allTestsPassed === false ? (
                    <AlertTriangle size={16} className="text-brand-warning" />
                  ) : (
                    <div className="w-4 h-4 rounded-full border-2 border-slate-200" />
                  )}
                  <span className="text-slate-700">Refutation tests</span>
                  <span className={`ml-auto text-xs font-medium ${allTestsPassed ? "text-brand-success" : allTestsPassed === false ? "text-brand-warning" : "text-slate-400"}`}>
                    {allTestsPassed === true ? "All passed" : allTestsPassed === false ? "Some failed" : "Pending"}
                  </span>
                </div>
                <div className="flex items-center gap-2 text-sm">
                  {anyDrift === false ? (
                    <CheckCircle2 size={16} className="text-brand-success" />
                  ) : anyDrift === true ? (
                    <AlertTriangle size={16} className="text-brand-warning" />
                  ) : (
                    <div className="w-4 h-4 rounded-full border-2 border-slate-200" />
                  )}
                  <span className="text-slate-700">Data drift</span>
                  <span className={`ml-auto text-xs font-medium ${anyDrift === false ? "text-brand-success" : anyDrift === true ? "text-brand-warning" : "text-slate-400"}`}>
                    {anyDrift === false ? "None detected" : anyDrift === true ? "Detected" : "Pending"}
                  </span>
                </div>
              </div>
            </div>

            <div>
              <h2 className="text-sm font-semibold text-slate-900 mb-2">Key Drivers</h2>
              <div className="bg-white border border-slate-200 rounded-lg p-4">
                {explainability?.global_feature_importance?.length > 0 ? (
                  <ul className="space-y-2">
                    {explainability.global_feature_importance.slice(0, 5).map((f) => (
                      <li key={f.feature} className="flex items-center justify-between text-sm">
                        <span className="text-slate-700 truncate mr-2">{f.feature}</span>
                        <span className="text-xs text-slate-500 shrink-0">{(f.importance * 100).toFixed(1)}%</span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-xs text-slate-400">Run explainability analysis for feature insights.</p>
                )}
              </div>
            </div>

            <div>
              <h2 className="text-sm font-semibold text-slate-900 mb-2">Quick Actions</h2>
              <div className="bg-white border border-slate-200 rounded-lg p-3 space-y-2">
                <Link to={`/dashboard/${runId}/scenario`} className="flex items-center gap-2 text-sm text-slate-700 hover:text-brand-secondary transition-colors">
                  <span className="w-1.5 h-1.5 rounded-full bg-brand-secondary" />
                  Run scenario simulation
                </Link>
                <Link to={`/dashboard/${runId}/reports`} className="flex items-center gap-2 text-sm text-slate-700 hover:text-brand-secondary transition-colors">
                  <span className="w-1.5 h-1.5 rounded-full bg-brand-secondary" />
                  Download campaign report
                </Link>
                <Link to={`/dashboard/${runId}/assistant`} className="flex items-center gap-2 text-sm text-slate-700 hover:text-brand-secondary transition-colors">
                  <span className="w-1.5 h-1.5 rounded-full bg-brand-secondary" />
                  Ask AI assistant
                </Link>
              </div>
            </div>
          </section>
        </div>
      </div>
    </DashboardLayout>
  );
}
