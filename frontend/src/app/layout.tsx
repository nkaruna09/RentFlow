import type { Metadata } from "next";
import type { ReactNode } from "react";
import "./globals.css";
import { SessionProvider } from "@/providers/session-provider";

export const metadata: Metadata = {
  title: "RentFlow",
  description: "Property management for modern landlords and tenants",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-slate-50 text-slate-900 antialiased">
        <SessionProvider>{children}</SessionProvider>
      </body>
    </html>
  );
}
