import { BarChart3, Cog, ShieldAlert } from "lucide-react";

import type { NavView } from "@/lib/types";
import { cn } from "@/lib/utils";

const navigation = [
  { id: "sales-overview", label: "Sales Overview", icon: BarChart3 },
  { id: "risk-detection", label: "Risk & Detection", icon: ShieldAlert },
  { id: "rule-configuration", label: "Rule Configuration", icon: Cog },
] satisfies Array<{ id: NavView; label: string; icon: typeof BarChart3 }>;

interface SidebarProps {
  activeView: NavView;
  onSelect: (view: NavView) => void;
}

export function Sidebar({ activeView, onSelect }: SidebarProps) {
  return (
    <aside className="flex h-screen w-72 flex-col border-r border-white/10 bg-slate-950 px-5 py-6 text-white">
      <div className="mb-10 flex items-center gap-3 px-2">
        <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-blue-500/15 text-blue-300">
          <BarChart3 className="h-5 w-5" />
        </div>
        <div>
          <div className="text-lg font-semibold tracking-tight">Sales Control</div>
          <div className="text-sm text-slate-400">Portfolio Dashboard</div>
        </div>
      </div>

      <div className="mb-3 px-2 text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-500">Main</div>
      <nav className="space-y-2">
        {navigation.map((item) => {
          const Icon = item.icon;
          const active = activeView === item.id;
          return (
            <button
              key={item.id}
              onClick={() => onSelect(item.id)}
              className={cn(
                "flex w-full items-center gap-3 rounded-2xl px-4 py-3.5 text-left transition",
                active ? "bg-slate-800 text-white shadow-soft" : "text-slate-300 hover:bg-slate-900 hover:text-white",
              )}
            >
              <Icon className="h-5 w-5" />
              <span className="text-sm font-medium leading-5 tracking-[-0.01em]">{item.label}</span>
            </button>
          );
        })}
      </nav>

      <div className="mt-auto rounded-2xl border border-white/10 bg-white/5 p-4">
        <div className="text-sm font-semibold">Business-first analytics</div>
        <p className="text-pretty mt-2 text-sm leading-6 text-slate-400">
          Reported sales, underlying baseline, target context, and risk signals in one polished view.
        </p>
      </div>
    </aside>
  );
}
