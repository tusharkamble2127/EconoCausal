import React from "react";
import { Loader2 } from "lucide-react";

export default function Loader({ label = "Loading..." }) {
  return (
    <div className="flex items-center gap-2 text-neutral-600 py-6 justify-center">
      <Loader2 className="animate-spin" size={18} />
      <span>{label}</span>
    </div>
  );
}
