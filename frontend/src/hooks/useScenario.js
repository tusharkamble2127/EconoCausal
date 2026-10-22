import { useState } from "react";

import { simulateScenario } from "../api/client.js";
import { formatApiError } from "../utils/apiError.js";

/**
 * Drives the scenario simulator (Enhancement #8): re-optimizes over the
 * run's already-estimated ITE scores under a hypothetical budget/discount
 * subset, without retraining.
 */
export function useScenario(runId) {
  const [result, setResult] = useState(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState(null);

  const simulate = async (budget, discountLevels) => {
    setRunning(true);
    setError(null);
    try {
      const data = await simulateScenario(runId, budget, discountLevels);
      setResult(data);
      return data;
    } catch (err) {
      setError(formatApiError(err));
      return null;
    } finally {
      setRunning(false);
    }
  };

  return { simulate, result, running, error };
}
