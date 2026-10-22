import React from "react";
import { AlertCircle, RefreshCw } from "lucide-react";

export default function ErrorBanner({ message, onRetry }) {
  return (
    <div className="flex items-start gap-3 text-sm text-brand-danger bg-red-50 border border-red-200 rounded-lg px-4 py-3">
      <AlertCircle size={16} className="shrink-0 mt-0.5" />
      <div className="flex-1">
        <p className="font-medium">Unable to load</p>
        <p className="text-xs text-red-600 mt-0.5">{message}</p>
      </div>
      {onRetry && (
        <button
          onClick={onRetry}
          className="shrink-0 flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 bg-white border border-red-200 rounded-md hover:bg-red-50 transition-colors"
        >
          <RefreshCw size={12} />
          Retry
        </button>
      )}
    </div>
  );
}
