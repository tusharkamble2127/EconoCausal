import React from "react";
import { HelpCircle } from "lucide-react";

import InfoTooltip from "./InfoTooltip.jsx";

export default function SectionHeader({ title, description, tooltip, actions }) {
  return (
    <div className="flex items-start justify-between gap-4 mb-3">
      <div>
        <div className="flex items-center gap-2">
          <h2 className="text-sm font-semibold text-slate-900">{title}</h2>
          {tooltip && (
            <InfoTooltip term={title} explanation={tooltip} />
          )}
        </div>
        {description && <p className="text-xs text-slate-500 mt-0.5">{description}</p>}
      </div>
      {actions && <div className="flex items-center gap-2 shrink-0">{actions}</div>}
    </div>
  );
}
