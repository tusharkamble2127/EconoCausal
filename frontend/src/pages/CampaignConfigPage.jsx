import React, { useState, useCallback, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { Rocket, UploadCloud, X, FileSpreadsheet, AlertCircle, CheckCircle2, HelpCircle } from "lucide-react";

import DashboardLayout from "../components/DashboardLayout.jsx";
import DiscountLevelPicker from "../components/DiscountLevelPicker.jsx";
import Loader from "../components/Loader.jsx";
import { createRun } from "../api/client.js";
import { useDatasets } from "../hooks/useDatasets.js";
import { useAppContext } from "../state/appContext.jsx";
import {
  parseDatasetFile,
  buildPreview,
  autoMapColumns,
  normalizeRows,
  formatFileSize,
  translateBackendError,
} from "../utils/parseDataset.js";


const SUPPORTED_FORMATS = ["CSV", "XLSX", "XLS", "JSON"];

export default function CampaignConfigPage() {
  const navigate = useNavigate();
  const { setActiveRunId } = useAppContext();
  const { upload, uploading, error: uploadError } = useDatasets();

  const [campaignName, setCampaignName] = useState("");
  const [budget, setBudget] = useState("5000");
  const [discountLevels, setDiscountLevels] = useState([0, 5, 10, 15, 20, 25, 30]);

  const [file, setFile] = useState(null);
  const [fileName, setFileName] = useState("");
  const [fileSize, setFileSize] = useState(0);
  const [headers, setHeaders] = useState([]);
  const [rawRows, setRawRows] = useState([]);
  const [parseError, setParseError] = useState("");
  const [preview, setPreview] = useState(null);
  const [columnMapping, setColumnMapping] = useState({ customer: "", treatment: "", outcome: "" });
  const [ambiguousColumns, setAmbiguousColumns] = useState({});
  const [fieldDetection, setFieldDetection] = useState({});

  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState("");
  const [dragOver, setDragOver] = useState(false);
  const [dragCounter, setDragCounter] = useState(0);

  const fileInputRef = useRef(null);

  const handleFileSelect = useCallback(async (selectedFile) => {
    if (!selectedFile) return;

    setParseError("");
    setFormError("");
    setPreview(null);
    setAmbiguousColumns({});
    setFieldDetection({});

    setFile(selectedFile);
    setFileName(selectedFile.name);
    setFileSize(selectedFile.size);

    if (!campaignName) {
      setCampaignName(selectedFile.name.replace(/\.(csv|xlsx|xls|json)$/i, ""));
    }

    try {
      const { headers: parsedHeaders, rows: parsedRows, errors } = await parseDatasetFile(selectedFile);

      if (errors && errors.length > 0) {
        setParseError(errors[0]);
        setHeaders([]);
        setRawRows([]);
        return;
      }

      if (parsedHeaders.length === 0 || parsedRows.length === 0) {
        setParseError("The uploaded file appears to be empty or has no readable data.");
        setHeaders([]);
        setRawRows([]);
        return;
      }

      setHeaders(parsedHeaders);
      setRawRows(parsedRows);

      const previewData = buildPreview(parsedHeaders, parsedRows);
      setPreview(previewData);

      const { mapping, ambiguous, candidates } = autoMapColumns(parsedHeaders);
      setColumnMapping(mapping);
      setAmbiguousColumns(ambiguous);
      setFieldDetection(candidates);
    } catch (err) {
      setParseError("Unable to read this file. Please upload a valid CSV, Excel, or JSON dataset.");
      setHeaders([]);
      setRawRows([]);
    }
  }, [campaignName]);

  const handleDragEnter = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragCounter((c) => c + 1);
    setDragOver(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragCounter((c) => {
      const next = c - 1;
      if (next === 0) setDragOver(false);
      return next;
    });
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragOver(false);
    setDragCounter(0);

    const droppedFile = e.dataTransfer.files?.[0];
    if (droppedFile) {
      handleFileSelect(droppedFile);
    }
  };

  const handleInputChange = (e) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      handleFileSelect(selectedFile);
    }
  };

  const removeFile = () => {
    setFile(null);
    setFileName("");
    setFileSize(0);
    setHeaders([]);
    setRawRows([]);
    setPreview(null);
    setColumnMapping({ customer: "", treatment: "", outcome: "" });
    setAmbiguousColumns({});
    setFieldDetection({});
    setParseError("");
    setFormError("");
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const resolveAmbiguity = (field, value) => {
    setColumnMapping((prev) => ({ ...prev, [field]: value }));
    setAmbiguousColumns((prev) => {
      const next = { ...prev };
      delete next[field];
      return next;
    });
  };

  const isValid =
    campaignName.trim().length > 0 &&
    headers.length > 0 &&
    rawRows.length > 0 &&
    columnMapping.treatment &&
    columnMapping.outcome &&
    columnMapping.treatment !== columnMapping.outcome &&
    budget &&
    Number(budget) >= 0 &&
    discountLevels.length >= 2 &&
    discountLevels.includes(0) &&
    new Set(discountLevels).size === discountLevels.length &&
    !submitting &&
    !uploading;

  const displayError = formError || uploadError || parseError;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setFormError("");

    const budgetNumber = Number(budget);
    if (!budget || Number.isNaN(budgetNumber) || budgetNumber < 0) {
      setFormError("Enter a valid, non-negative budget.");
      return;
    }
    if (headers.length === 0 || rawRows.length === 0) {
      setFormError("Choose a dataset before running.");
      return;
    }
    if (!columnMapping.treatment || !columnMapping.outcome) {
      setFormError("Map both treatment and outcome columns.");
      return;
    }
    if (columnMapping.treatment === columnMapping.outcome) {
      setFormError("Treatment and outcome must be different columns.");
      return;
    }

    setSubmitting(true);
    let rows;
    try {
      rows = normalizeRows(rawRows, columnMapping.treatment, columnMapping.outcome);
    } catch (err) {
      setFormError(err.message);
      setSubmitting(false);
      return;
    }

    const dataset = await upload(fileName.replace(/\.(csv|xlsx|xls|json)$/i, ""), rows);
    if (!dataset) {
      setSubmitting(false);
      return;
    }

    try {
      const run = await createRun({
        datasetId: dataset.dataset_id,
        budget: budgetNumber,
        campaignName: campaignName || "Untitled Campaign",
        discountLevels,
        treatmentColumn: columnMapping.treatment,
        outcomeColumn: columnMapping.outcome,
      });
      setActiveRunId(run.run_id);
      navigate(`/dashboard/${run.run_id}`);
    } catch (err) {
      const translated = translateBackendError(err);
      setFormError(translated);
    } finally {
      setSubmitting(false);
    }
  };

  const busy = submitting || uploading;

  return (
    <DashboardLayout title="New Campaign" subtitle="Configure a causally-optimized discount allocation run">
      <form onSubmit={handleSubmit} className="max-w-2xl space-y-6">
        <section className="bg-white border border-slate-200 rounded-lg p-5 space-y-4">
          <h2 className="text-sm font-semibold text-slate-900">1. Campaign details</h2>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Campaign name</label>
            <input
              type="text"
              value={campaignName}
              onChange={(e) => setCampaignName(e.target.value)}
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-secondary"
              placeholder="Spring loyalty promotion"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Historical campaign data</label>
            <p className="text-xs text-slate-500 mb-2">
              Supported formats: {SUPPORTED_FORMATS.join(" • ")}
            </p>

            {!file ? (
              <div
                onDragEnter={handleDragEnter}
                onDragLeave={handleDragLeave}
                onDragOver={handleDragOver}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
                className={`flex flex-col items-center justify-center gap-3 rounded-lg border-2 border-dashed px-4 py-8 cursor-pointer transition-colors ${
                  dragOver
                    ? "border-brand-secondary bg-brand-secondary/5 text-brand-secondary"
                    : "border-slate-300 text-slate-500 hover:border-brand-secondary hover:text-brand-secondary"
                }`}
              >
                <UploadCloud size={32} />
                <div className="text-center">
                  <p className="text-sm font-medium">Drag & drop dataset here</p>
                  <p className="text-xs text-slate-400 mt-1">or click to browse</p>
                </div>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".csv,.xlsx,.xls,.json"
                  onChange={handleInputChange}
                  className="hidden"
                />
              </div>
            ) : (
              <div className="flex items-center gap-3 rounded-md border border-slate-200 bg-slate-50 px-3 py-2">
                <FileSpreadsheet size={18} className="text-brand-secondary shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-slate-700 truncate">{fileName}</p>
                  <p className="text-xs text-slate-500">{formatFileSize(fileSize)}</p>
                </div>
                <button
                  type="button"
                  onClick={removeFile}
                  className="shrink-0 rounded-md p-1 text-slate-400 hover:text-brand-danger hover:bg-red-50"
                  aria-label="Remove file"
                >
                  <X size={16} />
                </button>
              </div>
            )}
          </div>
        </section>

        {parseError && (
          <div className="flex items-start gap-2 text-sm text-brand-danger bg-red-50 border border-red-200 rounded-md px-3 py-2">
            <AlertCircle size={16} className="shrink-0 mt-0.5" />
            <span>{parseError}</span>
          </div>
        )}

        {preview && !parseError && (
          <section className="bg-white border border-slate-200 rounded-lg p-5 space-y-4">
            <h2 className="text-sm font-semibold text-slate-900">2. Dataset preview</h2>
            <div className="flex flex-wrap gap-4 text-xs text-slate-600">
              <span className="flex items-center gap-1">
                <CheckCircle2 size={14} className="text-brand-success" />
                Rows: {preview.totalRows.toLocaleString()}
              </span>
              <span className="flex items-center gap-1">
                <CheckCircle2 size={14} className="text-brand-success" />
                Columns: {preview.totalColumns}
              </span>
            </div>

            <div className="overflow-x-auto border border-slate-200 rounded-md">
              <table className="min-w-full text-xs">
                <thead>
                  <tr className="bg-slate-50">
                    <th className="px-3 py-2 text-left font-medium text-slate-500 border-b border-slate-200">#</th>
                    {headers.map((header) => (
                      <th key={header} className="px-3 py-2 text-left font-medium text-slate-500 border-b border-slate-200 whitespace-nowrap">
                        {header}
                        <span className="ml-1 text-slate-400 normal-case">
                          ({preview.columnTypes[header] === "numeric" ? "numeric" : "categorical"})
                        </span>
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {preview.previewRows.map((row, idx) => (
                    <tr key={idx} className="border-b border-slate-100 last:border-b-0">
                      <td className="px-3 py-2 text-slate-400 border-r border-slate-100">{idx + 1}</td>
                      {headers.map((header) => (
                        <td key={header} className="px-3 py-2 text-slate-700 whitespace-nowrap">
                          {row[header] !== undefined && row[header] !== null ? String(row[header]) : ""}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {preview.totalRows > 5 && (
              <p className="text-xs text-slate-400">Showing first 5 of {preview.totalRows.toLocaleString()} rows</p>
            )}
          </section>
        )}

        {headers.length > 0 && !parseError && (
          <section className="bg-white border border-slate-200 rounded-lg p-5 space-y-4">
            <h2 className="text-sm font-semibold text-slate-900">3. Map your columns</h2>
            <p className="text-xs text-slate-500">
              Assign which uploaded column represents Customer ID, Treatment (discount), and Outcome (purchase).
              All other columns are treated as customer features (confounders).
            </p>

            {Object.keys(ambiguousColumns).length > 0 && (
              <div className="flex items-start gap-2 text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded-md px-3 py-2">
                <HelpCircle size={14} className="shrink-0 mt-0.5" />
                <span>
                  Multiple possible matches detected. Please confirm the correct column for each role.
                </span>
              </div>
            )}

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Customer ID column</label>
                <select
                  value={columnMapping.customer}
                  onChange={(e) => resolveAmbiguity("customer", e.target.value)}
                  className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                >
                  <option value="">-- select --</option>
                  {headers.map((h) => (
                    <option key={h} value={h}>
                      {h}
                    </option>
                  ))}
                </select>
                {fieldDetection.customer?.length > 0 && !ambiguousColumns.customer && (
                  <p className="text-xs text-brand-success mt-1">
                    Detected: {fieldDetection.customer[0]}
                  </p>
                )}
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Treatment column</label>
                <select
                  value={columnMapping.treatment}
                  onChange={(e) => resolveAmbiguity("treatment", e.target.value)}
                  className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                >
                  <option value="">-- select --</option>
                  {headers.map((h) => (
                    <option key={h} value={h}>
                      {h}
                    </option>
                  ))}
                </select>
                {fieldDetection.treatment?.length === 1 && !ambiguousColumns.treatment && (
                  <p className="text-xs text-brand-success mt-1">
                    Detected: {fieldDetection.treatment[0]}
                  </p>
                )}
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Outcome column</label>
                <select
                  value={columnMapping.outcome}
                  onChange={(e) => resolveAmbiguity("outcome", e.target.value)}
                  className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
                >
                  <option value="">-- select --</option>
                  {headers.map((h) => (
                    <option key={h} value={h}>
                      {h}
                    </option>
                  ))}
                </select>
                {fieldDetection.outcome?.length === 1 && !ambiguousColumns.outcome && (
                  <p className="text-xs text-brand-success mt-1">
                    Detected: {fieldDetection.outcome[0]}
                  </p>
                )}
              </div>
            </div>
          </section>
        )}

        <section className="bg-white border border-slate-200 rounded-lg p-5 space-y-4">
          <h2 className="text-sm font-semibold text-slate-900">4. Campaign budget</h2>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Budget ($)</label>
            <input
              type="number"
              min="0"
              step="1"
              value={budget}
              onChange={(e) => setBudget(e.target.value)}
              required
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-secondary"
              placeholder="e.g. 5000"
            />
            <p className="text-xs text-slate-400 mt-1">Total promotional budget available for this campaign.</p>
          </div>
        </section>

        <section className="bg-white border border-slate-200 rounded-lg p-5 space-y-3">
          <h2 className="text-sm font-semibold text-slate-900">5. Candidate discount levels</h2>
          <DiscountLevelPicker levels={discountLevels} onChange={setDiscountLevels} />
        </section>

        {displayError && (
          <div className="flex items-start gap-2 text-sm text-brand-danger bg-red-50 border border-red-200 rounded-md px-3 py-2">
            <AlertCircle size={16} className="shrink-0 mt-0.5" />
            <span>{displayError}</span>
          </div>
        )}

        {preview && !parseError && (
          <div className="text-xs text-slate-500 space-y-1">
            <p>Validation checklist:</p>
            <ul className="list-disc list-inside space-y-0.5 ml-1">
              <li className={headers.length > 0 ? "text-brand-success" : "text-slate-400"}>
                Dataset loaded ({rawRows.length.toLocaleString()} rows)
              </li>
              <li className={columnMapping.treatment && columnMapping.outcome ? "text-brand-success" : "text-slate-400"}>
                Required fields mapped {columnMapping.treatment && columnMapping.outcome ? "" : "(select treatment and outcome)"}
              </li>
              <li className={discountLevels.includes(0) ? "text-brand-success" : "text-brand-danger"}>
                0% control level included
              </li>
              <li className={new Set(discountLevels).size === discountLevels.length ? "text-brand-success" : "text-brand-danger"}>
                No duplicate discount levels
              </li>
            </ul>
          </div>
        )}

        <button
          type="submit"
          disabled={!isValid}
          className="flex items-center gap-2 bg-brand-primary text-white px-5 py-2.5 rounded-md text-sm font-medium disabled:opacity-50 hover:bg-brand-primary/90 transition-colors"
          title={!isValid ? "Complete all required fields to enable" : "Run campaign"}
        >
          <Rocket size={16} />
          {busy ? "Running causal analysis..." : "Run campaign"}
        </button>

        {busy && <Loader label="Training the causal model..." />}
      </form>
    </DashboardLayout>
  );
}
