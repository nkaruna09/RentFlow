"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import { ApiError } from "@/lib/api/client";
import { login, register } from "@/lib/auth";

export default function RegisterPage() {
  const router = useRouter();
  const [error, setError] = useState("");
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError(""); setFieldErrors({}); setSubmitting(true);
    const data = new FormData(event.currentTarget);
    const credentials = { email: String(data.get("email")), password: String(data.get("password")) };
    try {
      await register({ ...credentials, full_name: String(data.get("full_name")) });
      await login(credentials);
      router.replace("/");
    } catch (caught) {
      if (caught instanceof ApiError) {
        setFieldErrors(caught.fieldErrors);
        setError(Object.keys(caught.fieldErrors).length ? "Please correct the fields below." : caught.message);
      } else setError(caught instanceof Error ? caught.message : "Unable to create your account.");
    } finally { setSubmitting(false); }
  }

  function field(name: string, label: string, type = "text", autoComplete?: string) {
    return <label className="block text-sm font-medium text-slate-700">{label}
      <input aria-describedby={fieldErrors[name] ? `${name}-error` : undefined} aria-invalid={Boolean(fieldErrors[name])} className="mt-1 w-full rounded-xl border border-slate-300 px-3 py-2 aria-[invalid=true]:border-red-500" name={name} type={type} autoComplete={autoComplete} required />
      {fieldErrors[name] && <span id={`${name}-error`} className="mt-1 block text-sm text-red-600">{fieldErrors[name]}</span>}
    </label>;
  }

  return (
    <main className="mx-auto max-w-md space-y-6">
      <p className="text-sm uppercase tracking-[0.24em] text-sky-600">Auth</p>
      <h1 className="text-3xl font-semibold text-slate-900">Register</h1>
      <form className="space-y-4" onSubmit={handleSubmit}>
        {field("full_name", "Full name", "text", "name")}
        {field("email", "Email", "email", "email")}
        {field("password", "Password", "password", "new-password")}
        {error && <p role="alert" className="text-sm text-red-600">{error}</p>}
        <button className="w-full rounded-xl bg-sky-600 px-4 py-2 font-semibold text-white disabled:opacity-60" disabled={submitting} type="submit">
          {submitting ? "Creating account…" : "Create account"}
        </button>
      </form>
      <p className="text-sm text-slate-600">Already registered? <Link className="text-sky-700 underline" href="/login">Log in</Link></p>
    </main>
  );
}
