import { useEffect, useState } from "react";

import { getHistory } from "../api/client.js";
import { useAppContext } from "../state/appContext.jsx";
import { formatApiError } from "../utils/apiError.js";

/** Loads the campaign history list (Phase 3). */
export function useHistory() {
  const [campaigns, setCampaigns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const { isAuthenticated } = useAppContext();

  useEffect(() => {
    let cancelled = false;
    (async () => {
      if (!isAuthenticated) {
        if (!cancelled) {
          setCampaigns([]);
          setLoading(false);
          setError("Not authenticated");
        }
        return;
      }
      try {
        const data = await getHistory();
        if (!cancelled) setCampaigns(data.campaigns);
      } catch (err) {
        if (!cancelled) setError(formatApiError(err));
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [isAuthenticated]);

  return { campaigns, loading, error };
}
