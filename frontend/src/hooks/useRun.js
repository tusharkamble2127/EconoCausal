import { useCallback, useEffect, useRef, useState } from "react";

import {
  getAllocation,
  getAnalytics,
  getDrift,
  getExplainability,
  getIteScores,
  getPropensity,
  getRecommendations,
  getRefutation,
  getRun,
  getSummary,
} from "../api/client.js";
import { useAppContext } from "../state/appContext.jsx";
import { formatApiError } from "../utils/apiError.js";

const RUN_CACHE_TTL_MS = 30_000;
const runCache = new Map();

export function useRun(runId) {
  const [run, setRun] = useState(null);
  const [ite, setIte] = useState(null);
  const [allocation, setAllocation] = useState(null);
  const [refutation, setRefutation] = useState(null);
  const [summary, setSummary] = useState(null);
  const [analytics, setAnalytics] = useState(null);
  const [recommendations, setRecommendations] = useState(null);
  const [explainability, setExplainability] = useState(null);
  const [drift, setDrift] = useState(null);
  const [propensity, setPropensity] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  const statusRef = useRef(null);
  const cancelledRef = useRef(false);
  const latestRunIdRef = useRef(runId);
  const { isAuthenticated } = useAppContext();

  const fetchAll = useCallback(async () => {
    if (!runId) return;
    latestRunIdRef.current = runId;

    const cached = runCache.get(runId);
    if (cached && Date.now() - cached.ts < RUN_CACHE_TTL_MS) {
      const { run: runData, ite, allocation, refutation, summary, analytics, recommendations, explainability, drift, propensity } = cached;
      setRun(runData);
      setIte(ite);
      setAllocation(allocation);
      setRefutation(refutation);
      setSummary(summary);
      setAnalytics(analytics);
      setRecommendations(recommendations);
      setExplainability(explainability);
      setDrift(drift);
      setPropensity(propensity);
      setLoading(false);
      return;
    }

    try {
      const runData = await getRun(runId);
      if (cancelledRef.current || latestRunIdRef.current !== runId) return;
      setRun(runData);
      statusRef.current = runData.status;

      if (runData.status === "complete") {
        const results = await Promise.allSettled([
          getIteScores(runId),
          getAllocation(runId),
          getRefutation(runId),
          getSummary(runId),
          getAnalytics(runId),
          getRecommendations(runId),
          getExplainability(runId),
          getDrift(runId),
          getPropensity(runId),
        ]);
        if (cancelledRef.current || latestRunIdRef.current !== runId) return;

        const [
          iteData,
          allocData,
          refData,
          summaryData,
          analyticsData,
          recData,
          explainData,
          driftData,
          propensityData,
        ] = results.map((r) => (r.status === "fulfilled" ? r.value : null));

        setIte(iteData);
        setAllocation(allocData);
        setRefutation(refData);
        setSummary(summaryData);
        setAnalytics(analyticsData);
        setRecommendations(recData);
        setExplainability(explainData);
        setDrift(driftData);
        setPropensity(propensityData);
        setLoading(false);

        runCache.set(runId, {
          ts: Date.now(),
          run: runData,
          ite: iteData,
          allocation: allocData,
          refutation: refData,
          summary: summaryData,
          analytics: analyticsData,
          recommendations: recData,
          explainability: explainData,
          drift: driftData,
          propensity: propensityData,
        });
      } else if (runData.status === "failed") {
        setError("The training run failed. Check the backend logs.");
        setLoading(false);
      }
    } catch (err) {
      if (cancelledRef.current || latestRunIdRef.current !== runId) return;
      statusRef.current = "failed";
      setError(formatApiError(err));
      setLoading(false);
    }
  }, [runId]);

  useEffect(() => {
    if (!runId || !isAuthenticated) {
      if (!isAuthenticated) {
        setError("Not authenticated");
        setLoading(false);
      }
      return undefined;
    }

    cancelledRef.current = false;
    latestRunIdRef.current = runId;
    fetchAll();

    const interval = setInterval(() => {
      if (statusRef.current === "complete" || statusRef.current === "failed") {
        clearInterval(interval);
        return;
      }
      fetchAll();
    }, 1500);

    return () => {
      cancelledRef.current = true;
      clearInterval(interval);
    };
  }, [runId, fetchAll, isAuthenticated]);

  return { run, ite, allocation, refutation, summary, analytics, recommendations, explainability, drift, propensity, error, loading };
}
