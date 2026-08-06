export default function Loading() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 px-6">
      <div className="flex items-center gap-3 rounded-3xl bg-white/90 px-6 py-4 text-slate-700 shadow-xl shadow-slate-200/70">
        <div className="h-3 w-3 animate-pulse rounded-full bg-sky-600" />
        <span className="text-sm font-medium">Loading RentFlow…</span>
      </div>
    </div>
  );
}
