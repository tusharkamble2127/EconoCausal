import { useState } from "react";

import { createDataset } from "../api/client.js";
import { useAppContext } from "../state/appContext.jsx";
import { formatApiError } from "../utils/apiError.js";

export function useDatasets() {
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);
  const { isAuthenticated } = useAppContext();

  const upload = async (name, rows) => {
    if (!isAuthenticated) {
      setError("Not authenticated");
      return null;
    }
    setUploading(true);
    setError(null);
    try {
      const dataset = await createDataset(name, rows);
      return dataset;
    } catch (err) {
      setError(formatApiError(err));
      return null;
    } finally {
      setUploading(false);
    }
  };

  return { upload, uploading, error };
}
