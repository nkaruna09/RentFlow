"use client";

import { useEffect } from "react";

interface ErrorProps {
  error: Error;
  reset?: () => void;
}

export default function ErrorPage({ error, reset }: ErrorProps) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-50 px-6 text-center">
      <div className="max-w-xl rounded-3xl border border-red-100 bg-white p-10 shadow-xl">
        <p className="text-sm uppercase tracking-[0.24em] text-red-600">Something went wrong</p>
        <h1 className="mt-4 text-3xl font-semibold text-slate-900">Application error</h1>
        <p className="mt-3 text-slate-600">{error?.message ?? "Please try again."}</p>
        <button
          type="button"
          onClick={() => reset?.()}
          className="mt-8 inline-flex rounded-full bg-red-600 px-5 py-3 text-sm font-semibold text-white transition hover:bg-red-700"
        >
          Try again
        </button>
      </div>
    </main>
  );
}
