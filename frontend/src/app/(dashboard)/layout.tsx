// Authenticated shell: sidebar + topbar + session guard.
import type { ReactNode } from "react";
import { Sidebar } from "@/components/layout/sidebar";
import { Topbar } from "@/components/layout/topbar";
import { SessionGuard } from "@/providers/session-guard";

export default function DashboardLayout({ children }: { children: ReactNode }) {
  return (
    <SessionGuard>
      <div className="min-h-screen bg-slate-50 lg:pl-64">
        <Sidebar />
        <div className="min-w-0">
          <Topbar />
          <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">{children}</main>
        </div>
      </div>
    </SessionGuard>
  );
}
