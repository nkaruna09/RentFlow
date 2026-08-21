// Authenticated shell: sidebar + topbar + session guard.
import type { ReactNode } from "react";
import { SessionGuard } from "@/providers/session-guard";

export default function DashboardLayout({ children }: { children: ReactNode }) {
  return (
    <SessionGuard><div className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white/90 px-6 py-4 backdrop-blur-sm">
        <div className="mx-auto max-w-6xl text-sm font-semibold text-slate-700">RentFlow dashboard</div>
      </header>
      <main className="mx-auto max-w-6xl px-6 py-10">{children}</main>
    </div></SessionGuard>
  );
}
