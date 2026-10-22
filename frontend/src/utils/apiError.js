/**
 * Safe API error formatter for React rendering.
 *
 * Backend validation errors can be arrays of objects (Pydantic style)
 * which React cannot render directly. This helper turns them into
 * a human-readable string.
 */
export function formatApiError(error) {
  if (!error) return null;

  const detail = error?.response?.data?.detail;
  if (!detail) return error.message || "An unexpected error occurred.";

  if (typeof detail === "string") {
    return detail;
  }

  if (Array.isArray(detail)) {
    const messages = detail
      .map((err) => {
        if (typeof err === "string") return err;
        if (err && typeof err === "object") {
          const loc = err.loc || [];
          const field = loc.filter((part) => typeof part === "string").join(".");
          const msg = err.msg || "Invalid value";
          return field ? `${field}: ${msg}` : msg;
        }
        return String(err);
      })
      .filter(Boolean);
    return messages.join("; ") || "Invalid request.";
  }

  if (typeof detail === "object" && detail !== null) {
    const msg = detail.msg || detail.detail || "Invalid request.";
    return typeof msg === "string" ? msg : JSON.stringify(msg);
  }

  return String(detail);
}
