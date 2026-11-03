import React, { useMemo, useState } from "react";
import { ChevronDown, ChevronUp, Search } from "lucide-react";

import { usePagination } from "../hooks/usePagination.js";
import PaginationBar from "./PaginationBar.jsx";

const PAGE_SIZE = 25;

export default function RecommendationPanel({ recommendations }) {
  const [sortKey, setSortKey] = useState("expected_uplift");
  const [sortDesc, setSortDesc] = useState(true);
  const [expanded, setExpanded] = useState(null);
  const [search, setSearch] = useState("");

  const rows = recommendations?.recommendations || [];

  const filtered = useMemo(() => {
    let result = [...rows];
    if (search.trim()) {
      const term = search.trim().toLowerCase();
      result = result.filter((r) => String(r.customer_id).includes(term));
    }
    return result.sort((a, b) => (sortDesc ? b[sortKey] - a[sortKey] : a[sortKey] - b[sortKey]));
  }, [rows, sortKey, sortDesc, search]);

  const { pageRows, page, pageCount, total, nextPage, prevPage } = usePagination(filtered, PAGE_SIZE);

  if (rows.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-10 text-center">
        <div className="text-sm text-slate-500">No recommendations yet.</div>
        <p className="text-xs text-slate-400 mt-1">Run the causal analysis to generate customer recommendations.</p>
      </div>
    );
  }

  const toggleSort = (key) => {
    if (sortKey === key) setSortDesc((v) => !v);
    else {
      setSortKey(key);
      setSortDesc(true);
    }
  };

  const columns = [
    { key: "recommended_discount", label: "Discount" },
    { key: "expected_uplift", label: "Expected Uplift" },
    { key: "purchase_probability", label: "Purchase Prob." },
    { key: "confidence_score", label: "Reliability" },
  ];

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <div className="relative">
          <Search size={14} className="absolute left-2.5 top-2 text-slate-400" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search customer ID..."
            className="rounded-md border border-slate-300 pl-8 pr-3 py-1.5 text-xs focus:outline-none focus:ring-2 focus:ring-brand-secondary w-48"
          />
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="min-w-full text-sm border border-slate-200 rounded">
          <thead className="bg-slate-50">
            <tr>
              <th className="text-left px-3 py-2">Customer ID</th>
              {columns.map((c) => (
                <th
                  key={c.key}
                  className="text-left px-3 py-2 cursor-pointer select-none whitespace-nowrap"
                  onClick={() => toggleSort(c.key)}
                >
                  {c.label} {sortKey === c.key ? (sortDesc ? "↓" : "↑") : ""}
                </th>
              ))}
              <th className="px-3 py-2" />
            </tr>
          </thead>
          <tbody>
            {pageRows.map((r) => (
              <React.Fragment key={r.customer_id}>
                <tr className="border-t border-slate-100 hover:bg-slate-50">
                  <td className="px-3 py-2 font-mono">{r.customer_id}</td>
                  <td className="px-3 py-2">{r.recommended_discount.toFixed(2)}%</td>
                  <td className="px-3 py-2 tabular-nums">{r.expected_uplift.toFixed(3)}</td>
                  <td className="px-3 py-2 tabular-nums">{(r.purchase_probability * 100).toFixed(1)}%</td>
                  <td className="px-3 py-2">
                    <ConfidenceBadge level={r.confidence_level} score={r.confidence_score} />
                  </td>
                  <td className="px-3 py-2 text-right">
                    <button
                      onClick={() => setExpanded(expanded === r.customer_id ? null : r.customer_id)}
                      className="text-slate-400 hover:text-brand-secondary"
                      aria-label={expanded === r.customer_id ? "Collapse details" : "Expand details"}
                    >
                      {expanded === r.customer_id ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                    </button>
                  </td>
                </tr>
                {expanded === r.customer_id && (
                  <tr className="bg-slate-50/70 border-t border-slate-100">
                    <td colSpan={6} className="px-4 py-3">
                      <div className="text-xs font-medium text-slate-500 mb-1.5">Top contributing factors</div>
                      <div className="flex flex-wrap gap-2 mb-2">
                        {r.contributing_factors.length === 0 && (
                          <span className="text-xs text-slate-400">No factor breakdown available.</span>
                        )}
                        {r.contributing_factors.map((f) => (
                          <span
                            key={f.feature}
                            className={`text-xs px-2 py-1 rounded-md border ${
                              f.impact >= 0
                                ? "border-brand-success/30 bg-brand-success/5 text-brand-success"
                                : "border-brand-danger/30 bg-brand-danger/5 text-brand-danger"
                            }`}
                          >
                            {f.feature}: {f.value.toFixed(2)} ({f.impact >= 0 ? "+" : ""}
                            {f.impact.toFixed(3)})
                          </span>
                        ))}
                      </div>
                      <div className="text-xs font-medium text-slate-500 mb-1">Confidence details</div>
                      <ConfidenceDetails
                        level={r.confidence_level}
                        score={r.confidence_score}
                        interval={r.confidence_interval}
                        evidence={r.evidence}
                      />
                    </td>
                  </tr>
                )}
              </React.Fragment>
            ))}
          </tbody>
        </table>
      </div>
      <PaginationBar page={page} pageCount={pageCount} total={total} pageSize={PAGE_SIZE} onPrev={prevPage} onNext={nextPage} />
    </div>
  );
}

function ConfidenceBadge({ level, score }) {
  const tone =
    level === "High"
      ? "text-brand-success bg-brand-success/10"
      : level === "Moderate"
        ? "text-brand-warning bg-brand-warning/10"
        : level === "Low"
          ? "text-brand-warning bg-brand-warning/10"
          : "text-slate-500 bg-slate-100";
  const label = level === "Insufficient Evidence" ? "N/A" : `${Math.round(score * 100)}`;
  return <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${tone}`}>{label}</span>;
}

function ConfidenceDetails({ level, score, interval, evidence }) {
  if (!evidence && !interval) {
    return <span className="text-xs text-slate-400">Confidence details not available.</span>;
  }
  return (
    <div className="text-xs text-slate-600 space-y-1">
      <div>
        <span className="font-medium">Reliability: </span>
        {level}
      </div>
      <div className="text-[10px] text-slate-400">
        Reliability score reflects evidence strength, not probability of correctness.
      </div>
      {interval ? (
        <div>
          <span className="font-medium">CI: </span>
          [{interval.lower.toFixed(4)}, {interval.upper.toFixed(4)}] ({Math.round(interval.level * 100)}%)
        </div>
      ) : (
        <div>
          <span className="font-medium">CI: </span>
          Not available
        </div>
      )}
      {evidence && (
        <div className="flex flex-wrap gap-x-3 gap-y-0.5">
          {evidence.ci_excludes_zero && <span>CI excludes zero</span>}
          {evidence.sufficient_sample && <span>Adequate sample</span>}
          {evidence.adequate_treatment_variation && <span>Adequate treatment variation</span>}
          {evidence.refutation_passed && <span>Refutation passed</span>}
          {evidence.adequate_data_support && <span>Adequate data support</span>}
          {!evidence.ci_excludes_zero && <span className="text-slate-400">CI includes zero</span>}
          {!evidence.refutation_passed && <span className="text-slate-400">Refutation mixed</span>}
          {!evidence.adequate_data_support && <span className="text-slate-400">Weak data support</span>}
        </div>
      )}
    </div>
  );
}
