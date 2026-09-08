"use client";

import { useRouter } from "next/navigation";

import { useAuth } from "@/hooks/use-auth";

export function Topbar() {
  const router = useRouter();
  const { signOut } = useAuth();

  function handleSignOut() {
    signOut();
    router.replace("/login");
  }

  return (
    <header className="sticky top-0 z-10 border-b border-slate-200 bg-white/90 px-4 py-3 backdrop-blur sm:px-6">
      <div className="flex items-center justify-between gap-4">
        <p className="text-sm font-semibold text-slate-700">Property management dashboard</p>
        <button
          className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 transition-colors hover:border-slate-400 hover:bg-slate-50"
          onClick={handleSignOut}
          type="button"
        >
          Log out
        </button>
      </div>
    </header>
  );
}
