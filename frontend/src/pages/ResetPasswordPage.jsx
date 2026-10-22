import React, { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { LineChart, LockOpen } from "lucide-react";

import { resetPassword } from "../api/client.js";
import { formatApiError } from "../utils/apiError.js";

export default function ResetPasswordPage() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token") || "";

  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    if (!token) {
      setError("This password reset link is invalid or has expired.");
    }
  }, [token]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setSuccess(false);

    if (!token) {
      setError("This password reset link is invalid or has expired.");
      return;
    }

    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    if (password.length < 6) {
      setError("Password must be at least 6 characters.");
      return;
    }

    setSubmitting(true);
    try {
      await resetPassword(token, password);
      setSuccess(true);
    } catch (err) {
      setError(formatApiError(err));
    } finally {
      setSubmitting(false);
    }
  };

  if (!token && !error) {
    return null;
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50 px-4">
      <div className="w-full max-w-sm">
        <div className="flex items-center gap-2 justify-center mb-6">
          <LineChart size={26} className="text-brand-primary" />
          <span className="text-lg font-semibold text-slate-900">EconoCausal</span>
        </div>

        <form onSubmit={handleSubmit} className="bg-white border border-slate-200 rounded-lg shadow-sm p-6 space-y-4">
          <div>
            <h2 className="text-base font-semibold text-slate-900">Reset your password</h2>
            <p className="text-sm text-slate-500 mt-1">Enter a new password for your account.</p>
          </div>

          {success ? (
            <>
              <div className="text-sm text-green-700 bg-green-50 border border-green-200 rounded-md px-3 py-2" role="status">
                Your password has been reset successfully.
              </div>
              <Link
                to="/login"
                className="block w-full text-center bg-brand-primary text-white rounded-md px-4 py-2 text-sm font-medium hover:bg-brand-primary/90 transition-colors focus:outline-none focus:ring-2 focus:ring-brand-secondary focus:ring-offset-2"
              >
                Go to Login
              </Link>
            </>
          ) : (
            <>
              <div>
                <label htmlFor="newPassword" className="block text-sm font-medium text-slate-700 mb-1">New Password</label>
                <input
                  id="newPassword"
                  type="password"
                  required
                  minLength={6}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-secondary"
                  placeholder="At least 6 characters"
                  autoComplete="new-password"
                />
                <p className="text-[10px] text-slate-400 mt-1">Minimum 6 characters</p>
              </div>

              <div>
                <label htmlFor="confirmPassword" className="block text-sm font-medium text-slate-700 mb-1">Confirm New Password</label>
                <input
                  id="confirmPassword"
                  type="password"
                  required
                  minLength={6}
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-secondary"
                  placeholder="Repeat your new password"
                  autoComplete="new-password"
                />
              </div>

              {error && (
                <div className="text-sm text-brand-danger bg-red-50 border border-red-200 rounded-md px-3 py-2" role="alert">
                  {error}
                </div>
              )}

              <button
                type="submit"
                disabled={submitting}
                className="w-full flex items-center justify-center gap-2 bg-brand-primary text-white rounded-md px-4 py-2 text-sm font-medium disabled:opacity-50 hover:bg-brand-primary/90 transition-colors focus:outline-none focus:ring-2 focus:ring-brand-secondary focus:ring-offset-2"
              >
                <LockOpen size={15} />
                {submitting ? "Resetting..." : "Reset Password"}
              </button>

              <p className="text-sm text-slate-500 text-center">
                <Link to="/forgot-password" className="text-brand-secondary font-medium hover:underline">
                  Request a new reset link
                </Link>
              </p>
            </>
          )}
        </form>
      </div>
    </div>
  );
}
