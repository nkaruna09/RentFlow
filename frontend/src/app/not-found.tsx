import Link from "next/link";

export default function NotFound() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-50 px-6 text-center">
      <div className="max-w-xl rounded-3xl border border-slate-200 bg-white p-10 shadow-xl">
        <p className="text-sm uppercase tracking-[0.24em] text-slate-500">Page not found</p>
        <h1 className="mt-4 text-3xl font-semibold text-slate-900">404</h1>
        <p className="mt-3 text-slate-600">We could not find the page you are looking for.</p>
        <Link
          href="/"
          className="mt-8 inline-flex rounded-full bg-slate-900 px-5 py-3 text-sm font-semibold text-white transition hover:bg-slate-700"
        >
          Return home
        </Link>
      </div>
    </main>
  );
}
