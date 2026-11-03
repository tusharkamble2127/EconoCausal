import React, { useEffect, useRef } from "react";
import Plotly from "plotly.js-dist-min";

const PALETTE = ["#1F4E79", "#2E86AB", "#2E7D32", "#ED6C02", "#7C3AED", "#C62828"];

export default function BucketChart({ title, buckets, kind = "bar", color = PALETTE[0], valuePrefix = "" }) {
  const ref = useRef(null);

  useEffect(() => {
    if (!ref.current || !buckets || buckets.length === 0) return;

    const x = buckets.map((b) => b.label);
    const y = buckets.map((b) => b.value);

    const trace =
      kind === "line"
        ? { x, y, type: "scatter", mode: "lines+markers", line: { color }, marker: { color } }
        : { x, y, type: "bar", marker: { color } };

    Plotly.newPlot(
      ref.current,
      [trace],
      {
        title: { text: title, font: { size: 13 } },
        margin: { t: 36, l: 48, r: 16, b: 40 },
        yaxis: { tickprefix: valuePrefix },
        font: { family: "Inter, system-ui, sans-serif", size: 11 },
      },
      { responsive: true, displayModeBar: false }
    );
  }, [buckets, kind, color, title, valuePrefix]);

  if (!buckets || buckets.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-10 text-center">
        <div className="text-sm text-slate-500">No data available.</div>
      </div>
    );
  }

  return <div ref={ref} className="w-full h-64" />;
}
