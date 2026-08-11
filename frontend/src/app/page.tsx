import React from "react";

export default function HomePage() {
  return (
    <main className="min-h-screen bg-gradient-to-br from-sky-50 via-white to-emerald-50">
      <div className="mx-auto flex min-h-screen max-w-6xl flex-col items-center justify-center px-6 py-12">
        <div className="w-full rounded-[2rem] border border-slate-200 bg-white/90 p-10 shadow-2xl shadow-slate-200/50 backdrop-blur-sm">
          <div className="space-y-6 text-center">
            <p className="text-sm font-semibold uppercase tracking-[0.24em] text-sky-600">RentFlow</p>
            <h1 className="text-4xl font-semibold tracking-tight text-slate-900 sm:text-5xl">
              Modern property management built with Next.js
            </h1>
            <p className="mx-auto max-w-2xl text-base leading-7 text-slate-600">
              A lightweight App Router shell that proves the frontend is running with Tailwind styles.
            </p>
            <div className="mt-8 flex flex-wrap justify-center gap-3">
              <span className="rounded-3xl bg-sky-600 px-5 py-3 text-sm font-semibold text-white shadow-lg shadow-sky-200/50">
                App Router
              </span>
              <span className="rounded-3xl bg-slate-100 px-5 py-3 text-sm font-semibold text-slate-700">
                Tailwind CSS
              </span>
              <span className="rounded-3xl bg-emerald-100 px-5 py-3 text-sm font-semibold text-emerald-900">
                Type-safe
              </span>
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}
