import React from "react";
import { useNavigate } from "react-router-dom";

import DashboardLayout from "../components/DashboardLayout.jsx";
import Loader from "../components/Loader.jsx";
import StatusBadge from "../components/StatusBadge.jsx";
import ReportButtons from "../components/ReportButtons.jsx";
import { useHistory } from "../hooks/useHistory.js";
import { useAppContext } from "../state/appContext.jsx";

export default function HistoryPage() {
  const { campaigns, loading, error } = useHistory();
  const { setActiveRunId } = useAppContext();
  const navigate = useNavigate();

  const openRun = (runId) => {
    setActiveRunId(runId);
    navigate(`/dashboard/${runId}`);
  };

  return (
    <DashboardLayout title="Campaign History" subtitle="Every campaign run, past and present">
      <div className="space-y-4">
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 flex items-start gap-3">
          <div className="text-sm text-blue-900 leading-relaxed">
            <span className="font-medium">Campaign archive:</span> Review past causal pricing runs, compare
            results, and reopen any campaign for deeper analysis or re-export.
          </div>
        </div>

        {loading && <Loader label="Loading campaign history..." />}
        {error && (
          <div className="text-sm text-brand-danger bg-red-50 border border-red-200 rounded-md px-3 py-2">{error}</div>
        )}

        {!loading && !error && campaigns.length === 0 && (
          <div className="bg-white border border-slate-200 rounded-lg">
            <div className="text-sm text-slate-500 py-10 text-center">No campaigns yet. Start a new one from the sidebar.</div>
          </div>
        )}

        {campaigns.length > 0 && (
          <div className="bg-white border border-slate-200 rounded-lg overflow-hidden">
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
                  <tr>
                    <th className="px-4 py-2.5">Campaign</th>
                    <th className="px-4 py-2.5">Dataset</th>
                    <th className="px-4 py-2.5">Estimator</th>
                    <th className="px-4 py-2.5">Budget</th>
                    <th className="px-4 py-2.5">Started</th>
                    <th className="px-4 py-2.5">Status</th>
                    <th className="px-4 py-2.5" />
                  </tr>
                </thead>
                <tbody>
                  {campaigns.map((c) => (
                    <tr key={c.run_id} className="border-t border-slate-100 hover:bg-slate-50">
                      <td className="px-4 py-2.5 font-medium text-slate-800">{c.campaign_name}</td>
                      <td className="px-4 py-2.5 text-slate-500">{c.dataset_name}</td>
                      <td className="px-4 py-2.5 text-slate-500">{c.base_estimator}</td>
                      <td className="px-4 py-2.5 tabular-nums text-slate-500">${c.budget.toFixed(0)}</td>
                      <td className="px-4 py-2.5 text-slate-500">{new Date(c.started_at).toLocaleString()}</td>
                      <td className="px-4 py-2.5">
                        <StatusBadge status={c.status} />
                      </td>
                      <td className="px-4 py-2.5 text-right space-x-2 whitespace-nowrap">
                        <button onClick={() => openRun(c.run_id)} className="text-brand-secondary text-xs font-medium hover:underline">
                          Open
                        </button>
                        {c.status === "complete" && <ReportButtons runId={c.run_id} />}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </DashboardLayout>
  );
}
