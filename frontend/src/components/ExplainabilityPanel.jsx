import React, { useEffect, useRef } from "react";
import Plotly from "plotly.js-dist-min";

/**
 * Global feature importance panel (Enhancement #7). Horizontal bar chart,
 * ranked descending, so the most influential confounders read top-to-bottom.
 */
export default function ExplainabilityPanel({ explainability }) {
  const ref = useRef(null);
  const items = explainability?.global_feature_importance || [];

  useEffect(() => {
    if (!ref.current || items.length === 0) return;
    const sorted = [...items].sort((a, b) => a.importance - b.importance);

    Plotly.newPlot(
      ref.current,
      [
        {
          x: sorted.map((i) => i.importance),
          y: sorted.map((i) => i.feature),
          type: "bar",
          orientation: "h",
          marker: { color: "#2E86AB" },
        },
      ],
      {
        margin: { t: 10, l: 120, r: 20, b: 40 },
        xaxis: { title: "Relative importance", tickformat: ".0%" },
        font: { family: "Inter, system-ui, sans-serif", size: 11 },
      },
      { responsive: true, displayModeBar: false }
    );
  }, [items]);

  if (items.length === 0) {
    return <div className="text-sm text-slate-400 py-8 text-center">No explainability data yet.</div>;
  }

  return <div ref={ref} className="w-full h-72" />;
}
