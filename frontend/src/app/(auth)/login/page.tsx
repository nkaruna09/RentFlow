"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import { ApiError } from "@/lib/api/client";
import { login } from "@/lib/auth";

export default function LoginPage() {
  const router = useRouter();
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError(""); setSubmitting(true);
    const data = new FormData(event.currentTarget);
    try {
      await login({ email: String(data.get("email")), password: String(data.get("password")) });
      router.replace("/");
    } catch (caught) {
      setError(caught instanceof ApiError && caught.status === 401 ? "Invalid email or password." : caught instanceof Error ? caught.message : "Unable to log in.");
    } finally { setSubmitting(false); }
  }

  return (
    <main className="mx-auto max-w-md space-y-6">
      <p className="text-sm uppercase tracking-[0.24em] text-sky-600">Auth</p>
      <h1 className="text-3xl font-semibold text-slate-900">Login</h1>
      <form className="space-y-4" onSubmit={handleSubmit}>
        <label className="block text-sm font-medium text-slate-700">Email
          <input className="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2" name="email" type="email" autoComplete="email" required />
        </label>
        <label className="block text-sm font-medium text-slate-700">Password
          <input className="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2" name="password" type="password" autoComplete="current-password" required />
        </label>
        {error && <p role="alert" className="text-sm text-red-600">{error}</p>}
        <button className="w-full rounded-xl bg-sky-600 px-4 py-2 font-semibold text-white disabled:opacity-60" disabled={submitting} type="submit">
          {submitting ? "Logging in…" : "Log in"}
        </button>
      </form>
      <p className="text-sm text-slate-600">New to RentFlow? <Link className="text-sky-700 underline" href="/register">Create an account</Link></p>
    </main>
  );
}
