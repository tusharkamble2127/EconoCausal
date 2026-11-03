import React, { useEffect, useRef } from "react";
import Plotly from "plotly.js-dist-min";

export default function QiniChart({ data }) {
  const ref = useRef(null);

  useEffect(() => {
    if (!ref.current || !data || data.length === 0) return;

    const sorted = [...data].sort((a, b) => b.ite_value - a.ite_value);
    const n = sorted.length;
    const totalIte = sorted.reduce((s, d) => s + d.ite_value, 0);

    let running = 0;
    const qini = sorted.map((d, i) => {
      running += d.ite_value;
      const randomExpectation = (totalIte * (i + 1)) / n;
      return running - randomExpectation;
    });
    const xPct = sorted.map((_, i) => ((i + 1) / n) * 100);

    Plotly.newPlot(
      ref.current,
      [{ x: xPct, y: qini, type: "scatter", mode: "lines", name: "Qini Gain", fill: "tozeroy" }],
      {
        title: "Qini Curve",
        xaxis: { title: "% of Customers Targeted" },
        yaxis: { title: "Incremental Gain vs. Random" },
        margin: { t: 40 },
      },
      { responsive: true, displayModeBar: false }
    );
  }, [data]);

  if (!data || data.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-10 text-center">
        <div className="text-sm text-slate-500">No Qini data available for this run.</div>
        <p className="text-xs text-slate-400 mt-1">Complete the causal analysis to view the Qini curve.</p>
      </div>
    );
  }

  return <div ref={ref} className="w-full h-80" />;
}
