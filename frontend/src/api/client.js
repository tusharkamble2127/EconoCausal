import axios from "axios";

// Volume II Chapter 1.10: local deployment -- backend runs on :8000.
const BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

const TOKEN_STORAGE_KEY = "econocausal_token";

export const apiClient = axios.create({
  baseURL: BASE_URL,
  headers: { "Content-Type": "application/json" },
  timeout: 600000,
});

// Attach the bearer token (if the user is logged in) to every request.
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_STORAGE_KEY);
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Clear invalid/expired auth state and redirect to login on 401.
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error?.response?.status === 401) {
      localStorage.removeItem(TOKEN_STORAGE_KEY);
      localStorage.removeItem("econocausal_user");
      if (window.location.pathname !== "/login" && window.location.pathname !== "/register") {
        window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  }
);

export function setStoredToken(token) {
  if (token) localStorage.setItem(TOKEN_STORAGE_KEY, token);
  else localStorage.removeItem(TOKEN_STORAGE_KEY);
}

export function getStoredToken() {
  return localStorage.getItem(TOKEN_STORAGE_KEY);
}

// ---- Auth (Phase 3) --------------------------------------------------
export async function register(email, password, fullName) {
  const { data } = await apiClient.post("/auth/register", { email, password, full_name: fullName });
  return data;
}

export async function login(email, password) {
  const { data } = await apiClient.post("/auth/login", { email, password });
  return data;
}

export async function forgotPassword(email) {
  const { data } = await apiClient.post("/auth/forgot-password", { email });
  return data;
}

export async function resetPassword(token, newPassword) {
  const { data } = await apiClient.post("/auth/reset-password", { token, new_password: newPassword });
  return data;
}

// ---- Datasets & runs ---------------------------------------------------
export async function createDataset(name, rows) {
  const { data } = await apiClient.post("/datasets", { name, rows });
  return data;
}

export async function createRun({
  datasetId,
  budget,
  baseEstimator = "RandomForest",
  campaignName = "Untitled Campaign",
  discountLevels,
  treatmentColumn = "treatment",
  outcomeColumn = "outcome",
}) {
  const { data } = await apiClient.post("/runs", {
    dataset_id: datasetId,
    budget,
    base_estimator: baseEstimator,
    campaign_name: campaignName,
    discount_levels: discountLevels,
    treatment_column: treatmentColumn,
    outcome_column: outcomeColumn,
  });
  return data;
}

export async function getRun(runId) {
  const { data } = await apiClient.get(`/runs/${runId}`);
  return data;
}

export async function getIteScores(runId) {
  const { data } = await apiClient.get(`/runs/${runId}/ite`);
  return data;
}

export async function getAllocation(runId) {
  const { data } = await apiClient.get(`/runs/${runId}/allocation`);
  return data;
}

export async function getRefutation(runId) {
  const { data } = await apiClient.get(`/runs/${runId}/refutation`);
  return data;
}

// ---- Enhancement #4: KPI summary ---------------------------------------
export async function getSummary(runId) {
  const { data } = await apiClient.get(`/runs/${runId}/summary`);
  return data;
}

// ---- Enhancement #5: enhanced analytics --------------------------------
export async function getAnalytics(runId) {
  const { data } = await apiClient.get(`/runs/${runId}/analytics`);
  return data;
}

// ---- Enhancement #6: recommendation panel ------------------------------
export async function getRecommendations(runId) {
  const { data } = await apiClient.get(`/runs/${runId}/recommendations`);
  return data;
}

// ---- Enhancement #7: explainability -------------------------------------
export async function getExplainability(runId) {
  const { data } = await apiClient.get(`/runs/${runId}/explainability`);
  return data;
}

export async function getCustomerExplanation(runId, customerId) {
  const { data } = await apiClient.get(`/runs/${runId}/customers/${customerId}/explanation`);
  return data;
}

// ---- Enhancement #8: scenario simulator ---------------------------------
export async function simulateScenario(runId, budget, discountLevels) {
  const { data } = await apiClient.post(`/runs/${runId}/simulate`, {
    budget,
    discount_levels: discountLevels,
  });
  return data;
}

// ---- Enhancement #9: data drift -----------------------------------------
export async function getDrift(runId) {
  const { data } = await apiClient.get(`/runs/${runId}/drift`);
  return data;
}

// ---- Phase 3: campaign history -------------------------------------------
export async function getHistory() {
  const { data } = await apiClient.get("/campaigns");
  return data;
}

// ---- Phase 3: downloadable reports ---------------------------------------
export async function downloadCsvReport(runId) {
  const { data } = await apiClient.get(`/runs/${runId}/report.csv`, { responseType: "blob" });
  return data;
}

export async function downloadPdfReport(runId) {
  const { data } = await apiClient.get(`/runs/${runId}/report.pdf`, { responseType: "blob" });
  return data;
}

// ---- Propensity score / matching diagnostics ------------------------------
export async function getPropensity(runId) {
  const { data } = await apiClient.get(`/runs/${runId}/propensity`);
  return data;
}

// ---- Phase 3: AI assistant -----------------------------------------------
export async function askAssistant(runId, question) {
  const { data } = await apiClient.post(`/runs/${runId}/assistant`, { question });
  return data;
}
