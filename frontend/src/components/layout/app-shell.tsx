import type { ReactNode } from "react";

import { Sidebar } from "@/components/layout/sidebar";
import type { NavView } from "@/lib/types";

interface AppShellProps {
  activeView: NavView;
  onSelect: (view: NavView) => void;
  children: ReactNode;
}

export function AppShell({ activeView, onSelect, children }: AppShellProps) {
  return (
    <div className="flex min-h-screen bg-background">
      <Sidebar activeView={activeView} onSelect={onSelect} />
      <main className="min-w-0 flex-1 overflow-x-hidden">
        <div className="mx-auto flex max-w-[1600px] flex-col gap-8 px-8 py-8">{children}</div>
      </main>
    </div>
  );
}
