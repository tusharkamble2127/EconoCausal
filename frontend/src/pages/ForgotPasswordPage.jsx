import React, { useState } from "react";
import { Link } from "react-router-dom";
import { LineChart, Mail } from "lucide-react";

import { forgotPassword } from "../api/client.js";
import { formatApiError } from "../utils/apiError.js";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    setSuccess(false);
    try {
      await forgotPassword(email);
      setSuccess(true);
    } catch (err) {
      setError(formatApiError(err));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50 px-4">
      <div className="w-full max-w-sm">
        <div className="flex items-center gap-2 justify-center mb-6">
          <LineChart size={26} className="text-brand-primary" />
          <span className="text-lg font-semibold text-slate-900">EconoCausal</span>
        </div>

        <form onSubmit={handleSubmit} className="bg-white border border-slate-200 rounded-lg shadow-sm p-6 space-y-4">
          <div>
            <h2 className="text-base font-semibold text-slate-900">Forgot your password?</h2>
            <p className="text-sm text-slate-500 mt-1">Enter your registered email address and we'll send you a password reset link.</p>
          </div>

          {success ? (
            <div className="text-sm text-green-700 bg-green-50 border border-green-200 rounded-md px-3 py-2" role="status">
              If an account exists for this email, a password reset link has been sent.
            </div>
          ) : (
            <>
              <div>
                <label htmlFor="email" className="block text-sm font-medium text-slate-700 mb-1">Email</label>
                <input
                  id="email"
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-secondary"
                  placeholder="you@company.com"
                  autoComplete="email"
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
                <Mail size={15} />
                {submitting ? "Sending..." : "Send Reset Link"}
              </button>
            </>
          )}

          <p className="text-sm text-slate-500 text-center">
            Remember your password?{" "}
            <Link to="/login" className="text-brand-secondary font-medium hover:underline">
              Sign in
            </Link>
          </p>
        </form>
      </div>
    </div>
  );
}
