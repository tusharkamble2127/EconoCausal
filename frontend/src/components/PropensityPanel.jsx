import React from "react";

export default function PropensityPanel({ propensity }) {
  if (!propensity) {
    return (
      <div className="bg-white border border-slate-200 rounded-lg p-4">
        <h2 className="text-sm font-semibold text-slate-900">Propensity Analysis</h2>
        <p className="text-xs text-slate-500 mt-1">No propensity data available for this run.</p>
      </div>
    );
  }

  const { binary, continuous, warnings } = propensity;

  return (
    <div className="bg-white border border-slate-200 rounded-lg p-4">
      <h2 className="text-sm font-semibold text-slate-900">Propensity Analysis</h2>
      <p className="text-xs text-slate-500 mt-1 mb-3">Treatment assignment analysis and covariate balance diagnostics</p>

      {warnings && warnings.length > 0 && (
        <div className="mb-3 space-y-1">
          {warnings.map((w, i) => (
            <div key={i} className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded px-2 py-1">
              {w}
            </div>
          ))}
        </div>
      )}

      {binary && (
        <div className="mb-4">
          <h3 className="text-xs font-medium text-slate-700 mb-2">Treated vs Control (Binary Diagnostic)</h3>

          {binary.overlap && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-2 mb-3">
              <div className="bg-slate-50 rounded p-2">
                <div className="text-[10px] text-slate-500 uppercase">Observations</div>
                <div className="text-sm font-medium">{binary.overlap.n_total}</div>
              </div>
              <div className="bg-slate-50 rounded p-2">
                <div className="text-[10px] text-slate-500 uppercase">Common Support</div>
                <div className="text-sm font-medium">
                  [{binary.overlap.common_support_min.toFixed(2)}, {binary.overlap.common_support_max.toFixed(2)}]
                </div>
              </div>
              <div className="bg-slate-50 rounded p-2">
                <div className="text-[10px] text-slate-500 uppercase">Outside Support</div>
                <div className="text-sm font-medium">
                  {binary.overlap.n_outside_support} ({binary.overlap.pct_outside_support.toFixed(1)}%)
                </div>
              </div>
              <div className="bg-slate-50 rounded p-2">
                <div className="text-[10px] text-slate-500 uppercase">Extreme Scores</div>
                <div className="text-sm font-medium">
                  {binary.overlap.n_extreme_low + binary.overlap.n_extreme_high} ({binary.overlap.pct_extreme.toFixed(1)}%)
                </div>
              </div>
            </div>
          )}

          {binary.matching && (
            <div className="bg-slate-50 rounded p-2 mb-3">
              <div className="text-xs font-medium text-slate-700">Matching Summary</div>
              <div className="grid grid-cols-3 gap-2 mt-1">
                <div>
                  <span className="text-[10px] text-slate-500">Method</span>
                  <div className="text-xs">{binary.matching.method}</div>
                </div>
                <div>
                  <span className="text-[10px] text-slate-500">Matched Pairs</span>
                  <div className="text-xs">{binary.matching.n_matched_pairs}</div>
                </div>
                <div>
                  <span className="text-[10px] text-slate-500">Unmatched</span>
                  <div className="text-xs">
                    {binary.matching.n_unmatched_treated} treated, {binary.matching.n_unmatched_control} control
                  </div>
                </div>
              </div>
              {binary.matching.caliper && (
                <div className="text-xs text-slate-500 mt-1">Caliper: {binary.matching.caliper.toFixed(2)}</div>
              )}
            </div>
          )}

          {binary.balance && binary.balance.length > 0 && (
            <div>
              <div className="text-xs font-medium text-slate-700 mb-1">Covariate Balance</div>
              <div className="overflow-x-auto">
                <table className="min-w-full text-xs">
                  <thead>
                    <tr className="bg-slate-50">
                      <th className="text-left px-2 py-1 font-medium text-slate-600">Feature</th>
                      <th className="text-right px-2 py-1 font-medium text-slate-600">Before SMD</th>
                      <th className="text-right px-2 py-1 font-medium text-slate-600">After SMD</th>
                      <th className="text-right px-2 py-1 font-medium text-slate-600">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {binary.balance.map((b, i) => (
                      <tr key={i} className="border-t border-slate-100">
                        <td className="px-2 py-1">{b.feature}</td>
                        <td className="text-right px-2 py-1">{b.smd_before.toFixed(3)}</td>
                        <td className="text-right px-2 py-1">
                          {b.smd_after !== null && b.smd_after !== undefined ? b.smd_after.toFixed(3) : "N/A"}
                        </td>
                        <td className="text-right px-2 py-1">
                          {b.balanced_after ? (
                            <span className="text-green-700 font-medium">Balanced</span>
                          ) : (
                            <span className="text-amber-700 font-medium">Unbalanced</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p className="text-[10px] text-slate-400 mt-1">Threshold: |SMD| &lt; 0.1 indicates balance.</p>
            </div>
          )}
        </div>
      )}

      {continuous && (
        <div>
          <h3 className="text-xs font-medium text-slate-700 mb-2">Continuous Treatment Balance</h3>
          <p className="text-xs text-slate-500 mb-2">
            Stratified by predicted treatment deciles (n_strata={continuous.n_strata})
          </p>

          {continuous.balance && continuous.balance.length > 0 && (
            <div className="overflow-x-auto">
              <table className="min-w-full text-xs">
                <thead>
                  <tr className="bg-slate-50">
                    <th className="text-left px-2 py-1 font-medium text-slate-600">Feature</th>
                    <th className="text-right px-2 py-1 font-medium text-slate-600">SMD (Low vs High Stratum)</th>
                    <th className="text-right px-2 py-1 font-medium text-slate-600">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {continuous.balance.map((b, i) => (
                    <tr key={i} className="border-t border-slate-100">
                      <td className="px-2 py-1">{b.feature}</td>
                      <td className="text-right px-2 py-1">{b.smd_before.toFixed(3)}</td>
                      <td className="text-right px-2 py-1">
                        {b.balanced_before ? (
                          <span className="text-green-700 font-medium">Balanced</span>
                        ) : (
                          <span className="text-amber-700 font-medium">Unbalanced</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {!binary && !continuous && (
        <p className="text-xs text-slate-500">Propensity analysis did not produce results for this run.</p>
      )}
    </div>
  );
}
