import React, { useEffect, useRef } from "react";
import Plotly from "plotly.js-dist-min";

export default function UpliftChart({ data }) {
  const ref = useRef(null);

  useEffect(() => {
    if (!ref.current || !data || data.length === 0) return;

    const sorted = [...data].sort((a, b) => b.ite_value - a.ite_value);
    const cumulative = [];
    let running = 0;
    sorted.forEach((d) => {
      running += d.ite_value;
      cumulative.push(running);
    });
    const xPct = sorted.map((_, i) => ((i + 1) / sorted.length) * 100);
    const randomLine = xPct.map((_, i) => (cumulative[cumulative.length - 1] * (i + 1)) / sorted.length);

    Plotly.newPlot(
      ref.current,
      [
        { x: xPct, y: cumulative, type: "scatter", mode: "lines", name: "Causal Model (ITE-ranked)" },
        { x: xPct, y: randomLine, type: "scatter", mode: "lines", name: "Random Targeting", line: { dash: "dot" } },
      ],
      {
        title: "Uplift Curve",
        xaxis: { title: "% of Customers Targeted" },
        yaxis: { title: "Cumulative Predicted Uplift" },
        margin: { t: 40 },
      },
      { responsive: true, displayModeBar: false }
    );
  }, [data]);

  if (!data || data.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-10 text-center">
        <div className="text-sm text-slate-500">No uplift data available for this run.</div>
        <p className="text-xs text-slate-400 mt-1">Complete the causal analysis to view the uplift curve.</p>
      </div>
    );
  }

  return <div ref={ref} className="w-full h-80" />;
}
