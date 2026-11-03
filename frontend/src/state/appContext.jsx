import React, { createContext, useContext, useEffect, useState } from "react";

import { getStoredToken, setStoredToken } from "../api/client.js";

/**
 * Lightweight cross-page state. Holds the currently selected dataset, the
 * active run id, and (Phase 3) the logged-in user + auth token.
 */
const AppContext = createContext(null);

export function AppProvider({ children }) {
  const [selectedDataset, setSelectedDataset] = useState(null);
  const [activeRunId, setActiveRunId] = useState(null);
  const [user, setUser] = useState(() => {
    const raw = localStorage.getItem("econocausal_user");
    if (raw) {
      try {
        return JSON.parse(raw);
      } catch {
        localStorage.removeItem("econocausal_user");
      }
    }
    return null;
  });
  const [authReady, setAuthReady] = useState(true);

  const login = (token, userData) => {
    setStoredToken(token);
    localStorage.setItem("econocausal_user", JSON.stringify(userData));
    setUser(userData);
  };

  const logout = () => {
    setStoredToken(null);
    localStorage.removeItem("econocausal_user");
    setUser(null);
  };

  const value = {
    selectedDataset,
    setSelectedDataset,
    activeRunId,
    setActiveRunId,
    user,
    authReady,
    isAuthenticated: Boolean(user && getStoredToken()),
    login,
    logout,
  };
  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

export function useAppContext() {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error("useAppContext must be used within an AppProvider");
  return ctx;
}
