import React, { useMemo, useState } from "react";

import { usePagination } from "../hooks/usePagination.js";
import PaginationBar from "./PaginationBar.jsx";

const PAGE_SIZE = 25;

export default function AllocationTable({ allocations, budget }) {
  const [sortDesc, setSortDesc] = useState(true);
  const [search, setSearch] = useState("");

  const filtered = useMemo(() => {
    if (!allocations) return [];
    let rows = [...allocations];
    if (search.trim()) {
      const term = search.trim().toLowerCase();
      rows = rows.filter((a) => String(a.customer_id).includes(term));
    }
    return rows.sort((a, b) => (sortDesc ? b.chosen_discount - a.chosen_discount : a.chosen_discount - b.chosen_discount));
  }, [allocations, sortDesc, search]);

  const totalUsed = useMemo(() => (allocations || []).reduce((s, a) => s + a.budget_used, 0), [allocations]);
  const { pageRows, page, pageCount, total, nextPage, prevPage } = usePagination(filtered, PAGE_SIZE);

  if (!allocations || allocations.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-10 text-center">
        <div className="text-sm text-slate-500">No allocation data available.</div>
        <p className="text-xs text-slate-400 mt-1">Run the causal analysis to generate customer-level allocations.</p>
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <div className="relative">
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search customer ID..."
            className="rounded-md border border-slate-300 px-3 py-1.5 text-xs focus:outline-none focus:ring-2 focus:ring-brand-secondary w-48"
          />
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="min-w-full text-sm border border-neutral-200 rounded">
          <thead className="bg-slate-100">
            <tr>
              <th className="text-left px-3 py-2">Customer ID</th>
              <th
                className="text-left px-3 py-2 cursor-pointer select-none"
                onClick={() => setSortDesc((v) => !v)}
                title="Click to sort"
              >
                Chosen Discount {sortDesc ? "↓" : "↑"}
              </th>
              <th className="text-left px-3 py-2">Budget Used</th>
            </tr>
          </thead>
          <tbody>
            {pageRows.map((a) => (
              <tr key={a.customer_id} className="border-t border-neutral-100 font-mono">
                <td className="px-3 py-2">{a.customer_id}</td>
                <td className="px-3 py-2">{a.chosen_discount.toFixed(2)}%</td>
                <td className="px-3 py-2">${a.budget_used.toFixed(2)}</td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr className="border-t border-neutral-300 font-semibold bg-slate-50">
              <td className="px-3 py-2">Total (all {total} customers)</td>
              <td className="px-3 py-2"></td>
              <td className="px-3 py-2">
                ${totalUsed.toFixed(2)} / ${budget?.toFixed(2)}
              </td>
            </tr>
          </tfoot>
        </table>
      </div>
      <PaginationBar page={page} pageCount={pageCount} total={total} pageSize={PAGE_SIZE} onPrev={prevPage} onNext={nextPage} />
    </div>
  );
}
