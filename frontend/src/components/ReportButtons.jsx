import React from "react";
import { FileSpreadsheet, FileText, Loader2 } from "lucide-react";

import { downloadCsvReport, downloadPdfReport } from "../api/client.js";

export default function ReportButtons({ runId }) {
  const [csvLoading, setCsvLoading] = React.useState(false);
  const [pdfLoading, setPdfLoading] = React.useState(false);
  const [error, setError] = React.useState(null);

  const handleCsv = async () => {
    setCsvLoading(true);
    setError(null);
    try {
      const blob = await downloadCsvReport(runId);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `run_${runId}_report.csv`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err) {
      setError("Failed to download CSV. Please try again.");
    } finally {
      setCsvLoading(false);
    }
  };

  const handlePdf = async () => {
    setPdfLoading(true);
    setError(null);
    try {
      const blob = await downloadPdfReport(runId);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `run_${runId}_report.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err) {
      setError("Failed to download PDF. Please try again.");
    } finally {
      setPdfLoading(false);
    }
  };

  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex gap-2">
        <button
          onClick={handleCsv}
          disabled={csvLoading || pdfLoading}
          className="flex items-center gap-1.5 text-sm border border-slate-300 rounded-md px-3 py-1.5 text-slate-600 hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {csvLoading ? <Loader2 size={14} className="animate-spin" /> : <FileSpreadsheet size={14} />}
          CSV
        </button>
        <button
          onClick={handlePdf}
          disabled={csvLoading || pdfLoading}
          className="flex items-center gap-1.5 text-sm border border-slate-300 rounded-md px-3 py-1.5 text-slate-600 hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {pdfLoading ? <Loader2 size={14} className="animate-spin" /> : <FileText size={14} />}
          PDF
        </button>
      </div>
      {error && <span className="text-[10px] text-brand-danger">{error}</span>}
    </div>
  );
}
