import React from "react";
import { NavLink } from "react-router-dom";
import {
  History,
  LayoutDashboard,
  LineChart,
  SlidersHorizontal,
  X,
  FlaskConical,
  FileText,
  Bot,
  Target,
  TrendingUp,
  ShieldCheck,
  Activity,
  Calculator,
  BarChart3,
} from "lucide-react";

const NAV_ITEMS = [
  { to: "/", label: "New Campaign", icon: SlidersHorizontal, end: true },
  { to: "/history", label: "Campaign History", icon: History },
];

/**
 * Left sidebar for the enterprise dashboard shell.
 * Active link uses the secondary brand color as a left accent bar.
 *
 * Renders two ways:
 *  - md and up: always-visible fixed column.
 *  - below md: hidden by default; becomes a slide-in drawer.
 */
export default function Sidebar({ activeRunId, mobileOpen = false, onClose }) {
  const content = (
    <>
      <div className="flex items-center justify-between gap-2 px-5 py-5 border-b border-white/10">
        <div className="flex items-center gap-2">
          <LineChart size={22} className="text-brand-secondary" />
          <div>
            <div className="font-semibold text-white leading-tight">EconoCausal</div>
            <div className="text-[11px] text-white/50 leading-tight">Causal Pricing Platform</div>
          </div>
        </div>
        {onClose && (
          <button
            type="button"
            onClick={onClose}
            className="md:hidden p-1 text-white/60 hover:text-white"
            aria-label="Close navigation menu"
          >
            <X size={18} />
          </button>
        )}
      </div>

      <nav className="flex-1 px-2 py-4 space-y-1 overflow-y-auto">
        {NAV_ITEMS.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            onClick={onClose}
            className={({ isActive }) =>
              `flex items-center gap-2.5 px-3 py-2 rounded-md text-sm transition-colors border-l-2 ${
                isActive
                  ? "bg-white/10 text-white border-brand-secondary font-medium"
                  : "border-transparent text-white/70 hover:bg-white/5 hover:text-white"
              }`
            }
          >
            <Icon size={16} />
            {label}
          </NavLink>
        ))}

        {activeRunId && (
          <>
            <NavLink
              to={`/dashboard/${activeRunId}`}
              onClick={onClose}
              className={({ isActive }) =>
                `flex items-center gap-2.5 px-3 py-2 rounded-md text-sm transition-colors border-l-2 ${
                  isActive
                    ? "bg-white/10 text-white border-brand-secondary font-medium"
                    : "border-transparent text-white/70 hover:bg-white/5 hover:text-white"
                }`
              }
            >
              <LayoutDashboard size={16} />
              Dashboard
            </NavLink>

            <div className="pt-3 pb-1 px-3 text-[10px] font-semibold uppercase tracking-wider text-white/30">
              Analysis
            </div>

            <NavLink
              to={`/dashboard/${activeRunId}/analytics`}
              onClick={onClose}
              className={({ isActive }) =>
                `flex items-center gap-2.5 px-3 py-1.5 rounded-md text-sm transition-colors border-l-2 ${
                  isActive
                    ? "bg-white/10 text-white border-brand-secondary font-medium"
                    : "border-transparent text-white/70 hover:bg-white/5 hover:text-white"
                }`
              }
            >
              <LineChart size={16} />
              Analytics
            </NavLink>

            <NavLink
              to={`/dashboard/${activeRunId}/propensity`}
              onClick={onClose}
              className={({ isActive }) =>
                `flex items-center gap-2.5 px-3 py-1.5 rounded-md text-sm transition-colors border-l-2 ${
                  isActive
                    ? "bg-white/10 text-white border-brand-secondary font-medium"
                    : "border-transparent text-white/70 hover:bg-white/5 hover:text-white"
                }`
              }
            >
              <Target size={16} />
              Propensity
            </NavLink>

            <NavLink
              to={`/dashboard/${activeRunId}/explainability`}
              onClick={onClose}
              className={({ isActive }) =>
                `flex items-center gap-2.5 px-3 py-1.5 rounded-md text-sm transition-colors border-l-2 ${
                  isActive
                    ? "bg-white/10 text-white border-brand-secondary font-medium"
                    : "border-transparent text-white/70 hover:bg-white/5 hover:text-white"
                }`
              }
            >
              <BarChart3 size={16} />
              Explainability
            </NavLink>

            <NavLink
              to={`/dashboard/${activeRunId}/refutation`}
              onClick={onClose}
              className={({ isActive }) =>
                `flex items-center gap-2.5 px-3 py-1.5 rounded-md text-sm transition-colors border-l-2 ${
                  isActive
                    ? "bg-white/10 text-white border-brand-secondary font-medium"
                    : "border-transparent text-white/70 hover:bg-white/5 hover:text-white"
                }`
              }
            >
              <ShieldCheck size={16} />
              Refutation
            </NavLink>

            <NavLink
              to={`/dashboard/${activeRunId}/drift`}
              onClick={onClose}
              className={({ isActive }) =>
                `flex items-center gap-2.5 px-3 py-1.5 rounded-md text-sm transition-colors border-l-2 ${
                  isActive
                    ? "bg-white/10 text-white border-brand-secondary font-medium"
                    : "border-transparent text-white/70 hover:bg-white/5 hover:text-white"
                }`
              }
            >
              <Activity size={16} />
              Drift
            </NavLink>

            <div className="pt-3 pb-1 px-3 text-[10px] font-semibold uppercase tracking-wider text-white/30">
              Decisions
            </div>

            <NavLink
              to={`/dashboard/${activeRunId}/recommendations`}
              onClick={onClose}
              className={({ isActive }) =>
                `flex items-center gap-2.5 px-3 py-1.5 rounded-md text-sm transition-colors border-l-2 ${
                  isActive
                    ? "bg-white/10 text-white border-brand-secondary font-medium"
                    : "border-transparent text-white/70 hover:bg-white/5 hover:text-white"
                }`
              }
            >
              <TrendingUp size={16} />
              Recommendations
            </NavLink>

            <NavLink
              to={`/dashboard/${activeRunId}/allocation`}
              onClick={onClose}
              className={({ isActive }) =>
                `flex items-center gap-2.5 px-3 py-1.5 rounded-md text-sm transition-colors border-l-2 ${
                  isActive
                    ? "bg-white/10 text-white border-brand-secondary font-medium"
                    : "border-transparent text-white/70 hover:bg-white/5 hover:text-white"
                }`
              }
            >
              <Calculator size={16} />
              Allocation
            </NavLink>

            <NavLink
              to={`/dashboard/${activeRunId}/ite`}
              onClick={onClose}
              className={({ isActive }) =>
                `flex items-center gap-2.5 px-3 py-1.5 rounded-md text-sm transition-colors border-l-2 ${
                  isActive
                    ? "bg-white/10 text-white border-brand-secondary font-medium"
                    : "border-transparent text-white/70 hover:bg-white/5 hover:text-white"
                }`
              }
            >
              <BarChart3 size={16} />
              ITE
            </NavLink>

            <NavLink
              to={`/dashboard/${activeRunId}/scenario`}
              onClick={onClose}
              className={({ isActive }) =>
                `flex items-center gap-2.5 px-3 py-1.5 rounded-md text-sm transition-colors border-l-2 ${
                  isActive
                    ? "bg-white/10 text-white border-brand-secondary font-medium"
                    : "border-transparent text-white/70 hover:bg-white/5 hover:text-white"
                }`
              }
            >
              <FlaskConical size={16} />
              Scenario Simulator
            </NavLink>

            <div className="pt-3 pb-1 px-3 text-[10px] font-semibold uppercase tracking-wider text-white/30">
              Tools
            </div>

            <NavLink
              to={`/dashboard/${activeRunId}/reports`}
              onClick={onClose}
              className={({ isActive }) =>
                `flex items-center gap-2.5 px-3 py-1.5 rounded-md text-sm transition-colors border-l-2 ${
                  isActive
                    ? "bg-white/10 text-white border-brand-secondary font-medium"
                    : "border-transparent text-white/70 hover:bg-white/5 hover:text-white"
                }`
              }
            >
              <FileText size={16} />
              Reports
            </NavLink>

            <NavLink
              to={`/dashboard/${activeRunId}/assistant`}
              onClick={onClose}
              className={({ isActive }) =>
                `flex items-center gap-2.5 px-3 py-1.5 rounded-md text-sm transition-colors border-l-2 ${
                  isActive
                    ? "bg-white/10 text-white border-brand-secondary font-medium"
                    : "border-transparent text-white/70 hover:bg-white/5 hover:text-white"
                }`
              }
            >
              <Bot size={16} />
              AI Assistant
            </NavLink>
          </>
        )}
      </nav>

      <div className="px-5 py-4 border-t border-white/10 text-[11px] text-white/40">
        Dynamic Pricing via Double Machine Learning
      </div>
    </>
  );

  return (
    <>
      {/* Desktop: unchanged always-visible column. */}
      <aside className="hidden md:flex md:w-60 md:flex-col bg-brand-primary text-white/90 shrink-0">{content}</aside>

      {/* Mobile: slide-in drawer. */}
      {mobileOpen && (
        <div className="fixed inset-0 z-40 md:hidden">
          <div className="absolute inset-0 bg-black/40" onClick={onClose} aria-hidden="true" />
          <aside className="absolute inset-y-0 left-0 w-64 flex flex-col bg-brand-primary text-white/90 shadow-xl">
            {content}
          </aside>
        </div>
      )}
    </>
  );
}
