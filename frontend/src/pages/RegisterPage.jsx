import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { LineChart, UserPlus } from "lucide-react";

import { useAuth } from "../hooks/useAuth.js";

export default function RegisterPage() {
  const navigate = useNavigate();
  const { register, submitting, error } = useAuth();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    const ok = await register(email, password, fullName);
    if (ok) navigate("/");
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
            <h2 className="text-base font-semibold text-slate-900">Create your account</h2>
            <p className="text-sm text-slate-500 mt-1">Save and revisit campaign runs across sessions.</p>
          </div>

          <div>
            <label htmlFor="fullName" className="block text-sm font-medium text-slate-700 mb-1">Full name</label>
            <input
              id="fullName"
              type="text"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-secondary"
              placeholder="Jordan Rivera"
              autoComplete="name"
            />
          </div>

          <div>
            <label htmlFor="regEmail" className="block text-sm font-medium text-slate-700 mb-1">Email</label>
            <input
              id="regEmail"
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
            <label htmlFor="regPassword" className="block text-sm font-medium text-slate-700 mb-1">Password</label>
            <input
              id="regPassword"
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
            <UserPlus size={15} />
            {submitting ? "Creating account..." : "Create account"}
          </button>

          <p className="text-sm text-slate-500 text-center">
            Already have an account?{" "}
            <Link to="/login" className="text-brand-secondary font-medium hover:underline">
              Sign in
            </Link>
          </p>
        </form>
      </div>
    </div>
  );
}
