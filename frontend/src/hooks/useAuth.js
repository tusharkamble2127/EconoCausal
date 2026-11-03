import { useState } from "react";

import { login as loginRequest, register as registerRequest } from "../api/client.js";
import { useAppContext } from "../state/appContext.jsx";
import { formatApiError } from "../utils/apiError.js";

/**
 * Thin wrapper around the auth endpoints + AppContext session state
 * (Phase 3 -- authentication).
 */
export function useAuth() {
  const { login: setSession } = useAppContext();
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  const login = async (email, password) => {
    setSubmitting(true);
    setError(null);
    try {
      const data = await loginRequest(email, password);
      setSession(data.access_token, data.user);
      return true;
    } catch (err) {
      setError(formatApiError(err));
      return false;
    } finally {
      setSubmitting(false);
    }
  };

  const register = async (email, password, fullName) => {
    setSubmitting(true);
    setError(null);
    try {
      const data = await registerRequest(email, password, fullName);
      setSession(data.access_token, data.user);
      return true;
    } catch (err) {
      setError(formatApiError(err));
      return false;
    } finally {
      setSubmitting(false);
    }
  };

  return { login, register, submitting, error };
}
