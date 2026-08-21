// Current-session hook.
"use client";

import { useContext } from "react";
import { SessionContext, type SessionContextValue } from "@/providers/session-provider";

export function useAuth(): SessionContextValue {
  const context = useContext(SessionContext);
  if (!context) throw new Error("useAuth must be used within a SessionProvider");
  return context;
}
