import React from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";

export default function PaginationBar({ page, pageCount, total, pageSize, onPrev, onNext }) {
  if (total === 0) return null;
  const start = (page - 1) * pageSize + 1;
  const end = Math.min(page * pageSize, total);

  return (
    <div className="flex items-center justify-between px-1 pt-3 text-xs text-slate-500">
      <span>
        Showing {start}-{end} of {total}
      </span>
      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={onPrev}
          disabled={page <= 1}
          className="flex items-center gap-1 px-2 py-1 rounded border border-slate-200 disabled:opacity-40 disabled:cursor-not-allowed hover:bg-slate-50"
        >
          <ChevronLeft size={14} /> Prev
        </button>
        <span>
          Page {page} / {pageCount}
        </span>
        <button
          type="button"
          onClick={onNext}
          disabled={page >= pageCount}
          className="flex items-center gap-1 px-2 py-1 rounded border border-slate-200 disabled:opacity-40 disabled:cursor-not-allowed hover:bg-slate-50"
        >
          Next <ChevronRight size={14} />
        </button>
      </div>
    </div>
  );
}
