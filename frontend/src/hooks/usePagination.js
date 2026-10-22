import { useMemo, useState } from "react";

/**
 * Simple client-side pagination for large per-customer tables
 * (Enhancement #6 recommendation panel, allocation detail table).
 *
 * BUGFIX (forensic pass): both AllocationTable.jsx and
 * RecommendationPanel.jsx rendered every row with no pagination --
 * confirmed via a real 1500-row campaign run to inflate the page to
 * ~115,000px tall (one <tr> per customer, no limit). This hook resets
 * to page 1 whenever the underlying row count changes (e.g. a new run
 * loads), so a stale page index can never point past the end of a
 * smaller dataset.
 */
export function usePagination(rows, pageSize = 25) {
  const [page, setPage] = useState(1);
  const total = rows.length;
  const pageCount = Math.max(1, Math.ceil(total / pageSize));
  const safePage = Math.min(page, pageCount);

  const pageRows = useMemo(() => {
    const start = (safePage - 1) * pageSize;
    return rows.slice(start, start + pageSize);
  }, [rows, safePage, pageSize]);

  return {
    pageRows,
    page: safePage,
    pageCount,
    total,
    goToPage: (p) => setPage(Math.min(Math.max(1, p), pageCount)),
    nextPage: () => setPage((p) => Math.min(p + 1, pageCount)),
    prevPage: () => setPage((p) => Math.max(p - 1, 1)),
  };
}
