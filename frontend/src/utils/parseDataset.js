import { read, utils } from "xlsx";

const FIELD_PATTERNS = {
  customer: /\bcustomer_id\b|\bid\b|\bcust_id\b|\buser_id\b|\bclient_id\b/i,
  treatment: /\btreatment\b|\bdiscount\b|\bdiscount_given\b|\boffer\b|\bpromo\b|\bcoupon\b|\bdiscount_amount\b/i,
  outcome: /\boutcome\b|\bpurchase\b|\bbought\b|\bconverted\b|\bresponse\b|\btarget\b|\bsale\b|\bpurchased\b/i,
};

function detectFieldType(columnName) {
  const trimmed = columnName.trim();
  if (FIELD_PATTERNS.customer.test(trimmed)) return "customer";
  if (FIELD_PATTERNS.treatment.test(trimmed)) return "treatment";
  if (FIELD_PATTERNS.outcome.test(trimmed)) return "outcome";
  return "feature";
}

function isNumeric(value) {
  if (value === null || value === undefined || value === "") return false;
  const num = Number(value);
  return !Number.isNaN(num) && Number.isFinite(num);
}

function parseCsvText(text) {
  const lines = text
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter((line) => line.length > 0);

  if (lines.length === 0) return { headers: [], rows: [] };

  const parseCsvLine = (line) => {
    const result = [];
    let current = "";
    let inQuotes = false;
    for (let i = 0; i < line.length; i++) {
      const char = line[i];
      if (char === '"') {
        if (inQuotes && line[i + 1] === '"') {
          current += '"';
          i++;
        } else {
          inQuotes = !inQuotes;
        }
      } else if (char === "," && !inQuotes) {
        result.push(current);
        current = "";
      } else {
        current += char;
      }
    }
    result.push(current);
    return result;
  };

  const headers = parseCsvLine(lines[0]);
  const rawRows = lines.slice(1);

  const rows = rawRows.map((line) => {
    const values = parseCsvLine(line);
    const record = {};
    headers.forEach((h, i) => {
      record[h] = values[i] ?? "";
    });
    return record;
  });

  return { headers, rows };
}

function parseJsonText(text) {
  const parsed = JSON.parse(text);
  if (!Array.isArray(parsed) || parsed.length === 0) {
    return { headers: [], rows: [] };
  }
  const headers = Object.keys(parsed[0]);
  const rows = parsed.map((record) => {
    const normalized = {};
    headers.forEach((h) => {
      normalized[h] = record[h] ?? "";
    });
    return normalized;
  });
  return { headers, rows };
}

function parseExcelBuffer(buffer) {
  const workbook = read(buffer, { type: "array" });
  const sheetName = workbook.SheetNames[0];
  const worksheet = workbook.Sheets[sheetName];
  const jsonData = utils.sheet_to_json(worksheet, { defval: "" });

  if (jsonData.length === 0) return { headers: [], rows: [] };

  const headers = Object.keys(jsonData[0]);
  const rows = jsonData.map((record) => {
    const normalized = {};
    headers.forEach((h) => {
      normalized[h] = record[h] ?? "";
    });
    return normalized;
  });

  return { headers, rows };
}

export async function parseDatasetFile(file) {
  const fileName = file.name.toLowerCase();
  const errors = [];

  if (fileName.endsWith(".csv")) {
    const text = await file.text();
    return parseCsvText(text);
  }

  if (fileName.endsWith(".json")) {
    const text = await file.text();
    try {
      return parseJsonText(text);
    } catch {
      errors.push("Unable to read this file. Please upload a valid CSV, Excel, or JSON dataset.");
      return { headers: [], rows: [], errors };
    }
  }

  if (fileName.endsWith(".xlsx") || fileName.endsWith(".xls")) {
    const buffer = await file.arrayBuffer();
    try {
      return parseExcelBuffer(buffer);
    } catch {
      errors.push("Unable to read this file. Please upload a valid CSV, Excel, or JSON dataset.");
      return { headers: [], rows: [], errors };
    }
  }

  errors.push("Unsupported file format. Please upload a valid CSV, Excel, or JSON dataset.");
  return { headers: [], rows: [], errors };
}

export function buildPreview(headers, rows, maxPreviewRows = 5) {
  const previewRows = rows.slice(0, maxPreviewRows);
  const columnTypes = {};
  headers.forEach((header) => {
    const sample = rows.slice(0, 20).map((r) => r[header]);
    const numericCount = sample.filter((v) => isNumeric(v)).length;
    columnTypes[header] = numericCount > sample.length * 0.8 ? "numeric" : "categorical";
  });

  return {
    totalRows: rows.length,
    totalColumns: headers.length,
    previewRows,
    columnTypes,
    fieldTypes: Object.fromEntries(headers.map((h) => [h, detectFieldType(h)])),
  };
}

export function autoMapColumns(headers) {
  const candidates = {
    customer: [],
    treatment: [],
    outcome: [],
  };

  headers.forEach((header) => {
    const type = detectFieldType(header);
    if (type === "customer") candidates.customer.push(header);
    if (type === "treatment") candidates.treatment.push(header);
    if (type === "outcome") candidates.outcome.push(header);
  });

  const mapping = {};
  const ambiguous = {};

  if (candidates.customer.length === 1) {
    mapping.customer = candidates.customer[0];
  } else if (candidates.customer.length > 1) {
    ambiguous.customer = candidates.customer;
  }

  if (candidates.treatment.length === 1) {
    mapping.treatment = candidates.treatment[0];
  } else if (candidates.treatment.length === 0) {
    ambiguous.treatment = ["none"];
  } else {
    ambiguous.treatment = candidates.treatment;
  }

  if (candidates.outcome.length === 1) {
    mapping.outcome = candidates.outcome[0];
  } else if (candidates.outcome.length === 0) {
    ambiguous.outcome = ["none"];
  } else {
    ambiguous.outcome = candidates.outcome;
  }

  return { mapping, ambiguous, candidates };
}

export function normalizeRows(rows, treatmentColumn, outcomeColumn) {
  return rows.map((record) => {
    const { [treatmentColumn]: treatment, [outcomeColumn]: outcome, ...rest } = record;
    const features = {};
    Object.entries(rest).forEach(([key, value]) => {
      const num = Number(value);
      features[key] = Number.isNaN(num) ? 0 : num;
    });
    return {
      features,
      treatment: Number(treatment),
      outcome: Number(outcome),
    };
  });
}

export function formatFileSize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function translateBackendError(error) {
  if (!error) return null;

  const detail = error?.response?.data?.detail;
  if (!detail) return error.message || "An unexpected error occurred.";

  if (typeof detail === "string") {
    if (detail.includes("outcome") && detail.includes("0 or 1")) {
      return "Outcome must contain only 0 or 1 values.";
    }
    if (detail.includes("Treatment must be a finite number")) {
      return "Treatment values must be finite numbers.";
    }
    if (detail.includes("Feature") && detail.includes("finite number")) {
      return "Feature values must be finite numbers.";
    }
    if (detail.includes("Dataset must contain at least one row")) {
      return "Dataset is empty. Please upload a file with at least one row of data.";
    }
    if (detail.includes("Dataset name must not be empty")) {
      return "Dataset name is missing.";
    }
    return detail;
  }

  if (Array.isArray(detail)) {
    const outcomeErrors = detail.filter((err) => {
      const loc = err.loc || [];
      return loc.some((part) => String(part) === "outcome");
    });
    if (outcomeErrors.length > 0) {
      const msgs = outcomeErrors.map((e) => e.msg || "").join(" ");
      if (msgs.includes("less than or equal to 1") || msgs.includes("greater than or equal to 0") || msgs.includes("0 or 1")) {
        return "Outcome must contain only 0 or 1 values.";
      }
      return `Outcome column error: ${msgs}`;
    }

    const treatmentErrors = detail.filter((err) => {
      const loc = err.loc || [];
      return loc.some((part) => String(part) === "treatment");
    });
    if (treatmentErrors.length > 0) {
      return `Treatment column error: ${treatmentErrors.map((e) => e.msg || "").join(" ")}`;
    }

    const featureErrors = detail.filter((err) => {
      const loc = err.loc || [];
      return loc.some((part) => String(part) === "features");
    });
    if (featureErrors.length > 0) {
      return `Feature values error: ${featureErrors.map((e) => e.msg || "").join(" ")}`;
    }

    const messages = detail.map((err) => err.msg || "Invalid value");
    return messages.join(" ");
  }

  return "Dataset validation failed. Please check your file and try again.";
}
