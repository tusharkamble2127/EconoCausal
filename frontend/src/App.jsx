import React, { Suspense, lazy } from "react";
import { Route, Routes, Navigate } from "react-router-dom";

import LoginPage from "./pages/LoginPage.jsx";
import RegisterPage from "./pages/RegisterPage.jsx";
import ForgotPasswordPage from "./pages/ForgotPasswordPage.jsx";
import ResetPasswordPage from "./pages/ResetPasswordPage.jsx";
import { useAppContext } from "./state/appContext.jsx";
import Loader from "./components/Loader.jsx";

const CampaignConfigPage = lazy(() => import("./pages/CampaignConfigPage.jsx"));
const DashboardPage = lazy(() => import("./pages/DashboardPage.jsx"));
const HistoryPage = lazy(() => import("./pages/HistoryPage.jsx"));

const AnalyticsPage = lazy(() => import("./pages/campaign/AnalyticsPage.jsx"));
const PropensityPage = lazy(() => import("./pages/campaign/PropensityPage.jsx"));
const ExplainabilityPage = lazy(() => import("./pages/campaign/ExplainabilityPage.jsx"));
const RefutationPage = lazy(() => import("./pages/campaign/RefutationPage.jsx"));
const DriftPage = lazy(() => import("./pages/campaign/DriftPage.jsx"));
const RecommendationsPage = lazy(() => import("./pages/campaign/RecommendationsPage.jsx"));
const AllocationPage = lazy(() => import("./pages/campaign/AllocationPage.jsx"));
const ITEPage = lazy(() => import("./pages/campaign/ITEPage.jsx"));
const ScenarioPage = lazy(() => import("./pages/campaign/ScenarioPage.jsx"));
const ReportsPage = lazy(() => import("./pages/campaign/ReportsPage.jsx"));
const AssistantPage = lazy(() => import("./pages/campaign/AssistantPage.jsx"));

function LoadingFallback() {
  return (
    <div className="min-h-screen flex items-center justify-center">
      <Loader label="Loading page..." />
    </div>
  );
}

function ProtectedRoute({ children }) {
  const { isAuthenticated } = useAppContext();
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }
  return children;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route path="/forgot-password" element={<ForgotPasswordPage />} />
      <Route path="/reset-password" element={<ResetPasswordPage />} />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <Suspense fallback={<LoadingFallback />}>
              <CampaignConfigPage />
            </Suspense>
          </ProtectedRoute>
        }
      />
      <Route
        path="/history"
        element={
          <ProtectedRoute>
            <Suspense fallback={<LoadingFallback />}>
              <HistoryPage />
            </Suspense>
          </ProtectedRoute>
        }
      />
      <Route
        path="/dashboard/:runId"
        element={
          <ProtectedRoute>
            <Suspense fallback={<LoadingFallback />}>
              <DashboardPage />
            </Suspense>
          </ProtectedRoute>
        }
      />
      <Route
        path="/dashboard/:runId/analytics"
        element={
          <ProtectedRoute>
            <Suspense fallback={<LoadingFallback />}>
              <AnalyticsPage />
            </Suspense>
          </ProtectedRoute>
        }
      />
      <Route
        path="/dashboard/:runId/propensity"
        element={
          <ProtectedRoute>
            <Suspense fallback={<LoadingFallback />}>
              <PropensityPage />
            </Suspense>
          </ProtectedRoute>
        }
      />
      <Route
        path="/dashboard/:runId/explainability"
        element={
          <ProtectedRoute>
            <Suspense fallback={<LoadingFallback />}>
              <ExplainabilityPage />
            </Suspense>
          </ProtectedRoute>
        }
      />
      <Route
        path="/dashboard/:runId/refutation"
        element={
          <ProtectedRoute>
            <Suspense fallback={<LoadingFallback />}>
              <RefutationPage />
            </Suspense>
          </ProtectedRoute>
        }
      />
      <Route
        path="/dashboard/:runId/drift"
        element={
          <ProtectedRoute>
            <Suspense fallback={<LoadingFallback />}>
              <DriftPage />
            </Suspense>
          </ProtectedRoute>
        }
      />
      <Route
        path="/dashboard/:runId/recommendations"
        element={
          <ProtectedRoute>
            <Suspense fallback={<LoadingFallback />}>
              <RecommendationsPage />
            </Suspense>
          </ProtectedRoute>
        }
      />
      <Route
        path="/dashboard/:runId/allocation"
        element={
          <ProtectedRoute>
            <Suspense fallback={<LoadingFallback />}>
              <AllocationPage />
            </Suspense>
          </ProtectedRoute>
        }
      />
      <Route
        path="/dashboard/:runId/ite"
        element={
          <ProtectedRoute>
            <Suspense fallback={<LoadingFallback />}>
              <ITEPage />
            </Suspense>
          </ProtectedRoute>
        }
      />
      <Route
        path="/dashboard/:runId/scenario"
        element={
          <ProtectedRoute>
            <Suspense fallback={<LoadingFallback />}>
              <ScenarioPage />
            </Suspense>
          </ProtectedRoute>
        }
      />
      <Route
        path="/dashboard/:runId/reports"
        element={
          <ProtectedRoute>
            <Suspense fallback={<LoadingFallback />}>
              <ReportsPage />
            </Suspense>
          </ProtectedRoute>
        }
      />
      <Route
        path="/dashboard/:runId/assistant"
        element={
          <ProtectedRoute>
            <Suspense fallback={<LoadingFallback />}>
              <AssistantPage />
            </Suspense>
          </ProtectedRoute>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
