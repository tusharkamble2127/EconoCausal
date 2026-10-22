import React from "react";
import { LogOut, Menu, User } from "lucide-react";

import { useAppContext } from "../state/appContext.jsx";

/**
 * Top bar: page title/subtitle on the left, session controls on the right.
 * Kept separate from Sidebar so pages can pass a contextual title without
 * threading props through the router.
 */
export default function TopNav({ title, subtitle, actions, onOpenMobileNav, breadcrumbs }) {
  const { user, logout, isAuthenticated } = useAppContext();

  return (
    <header className="flex items-center justify-between border-b border-slate-200 bg-white px-4 md:px-6 py-4">
      <div className="flex items-center gap-3 min-w-0">
        {onOpenMobileNav && (
          <button
            type="button"
            onClick={onOpenMobileNav}
            className="md:hidden -ml-1 p-1.5 rounded text-slate-500 hover:bg-slate-100"
            aria-label="Open navigation menu"
          >
            <Menu size={20} />
          </button>
        )}
        <div className="min-w-0">
          <h1 className="text-lg font-semibold text-slate-900 truncate">{title}</h1>
          {subtitle && <p className="text-sm text-slate-500 mt-0.5 truncate">{subtitle}</p>}
        </div>
      </div>

      <div className="flex items-center gap-4">
        {actions}
        <div className="h-6 w-px bg-slate-200 hidden sm:block" />
        {isAuthenticated ? (
          <div className="flex items-center gap-2 text-sm text-slate-600">
            <User size={16} className="text-slate-400 hidden sm:block" />
            <span className="hidden sm:inline">{user.full_name || user.email}</span>
            <button
              onClick={logout}
              className="ml-1 flex items-center gap-1 text-slate-400 hover:text-brand-danger transition-colors"
              title="Sign out"
              aria-label="Sign out"
            >
              <LogOut size={15} />
            </button>
          </div>
        ) : (
          <span className="text-sm text-slate-400 hidden sm:inline">Guest session</span>
        )}
      </div>
    </header>
  );
}
