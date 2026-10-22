import React, { useState } from "react";

import { NavLink } from "react-router-dom";
import { useAppContext } from "../state/appContext.jsx";
import Sidebar from "./Sidebar.jsx";
import TopNav from "./TopNav.jsx";

/**
 * Shared shell for every authenticated-area page: fixed sidebar, top bar,
 * scrollable content area, optional breadcrumbs.
 */
export default function DashboardLayout({ title, subtitle, actions, children, breadcrumbs }) {
  const { activeRunId } = useAppContext();
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  return (
    <div className="flex min-h-screen bg-slate-50">
      <Sidebar activeRunId={activeRunId} mobileOpen={mobileNavOpen} onClose={() => setMobileNavOpen(false)} />
      <div className="flex-1 flex flex-col min-w-0">
        <TopNav title={title} subtitle={subtitle} actions={actions} onOpenMobileNav={() => setMobileNavOpen(true)} />
        {breadcrumbs && breadcrumbs.length > 0 && (
          <nav className="px-4 md:px-6 py-2 bg-white border-b border-slate-100 text-xs text-slate-500">
            {breadcrumbs.map((crumb, idx) => (
              <span key={idx} className="inline-flex items-center">
                {idx > 0 && <span className="mx-2 text-slate-300">/</span>}
                {crumb.to && idx < breadcrumbs.length - 1 ? (
                  <NavLink to={crumb.to} className="hover:text-brand-secondary transition-colors">{crumb.label}</NavLink>
                ) : (
                  <span className="font-medium text-slate-700">{crumb.label}</span>
                )}
              </span>
            ))}
          </nav>
        )}
        <main className="flex-1 overflow-y-auto p-6">{children}</main>
      </div>
    </div>
  );
}
