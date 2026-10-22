import React, { useState } from "react";
import { Link } from "react-router-dom";
import { LineChart, LogIn } from "lucide-react";

import { useAuth } from "../hooks/useAuth.js";

export default function LoginPage() {
  const { login, submitting, error } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    const ok = await login(email, password);
    if (ok) window.location.href = "/";
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
            <h2 className="text-base font-semibold text-slate-900">Sign in</h2>
            <p className="text-sm text-slate-500 mt-1">Access your campaign history and saved runs.</p>
          </div>

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

          <div>
            <label htmlFor="password" className="block text-sm font-medium text-slate-700 mb-1">Password</label>
            <input
              id="password"
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-secondary"
              placeholder="••••••••"
              autoComplete="current-password"
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
            <LogIn size={15} />
            {submitting ? "Signing in..." : "Sign in"}
          </button>

          <p className="text-sm text-slate-500 text-center">
            Forgot your password?{" "}
            <Link to="/forgot-password" className="text-brand-secondary font-medium hover:underline">
              Reset it
            </Link>
          </p>

          <p className="text-sm text-slate-500 text-center">
            No account?{" "}
            <Link to="/register" className="text-brand-secondary font-medium hover:underline">
              Create one
            </Link>
          </p>
        </form>
      </div>
    </div>
  );
}
