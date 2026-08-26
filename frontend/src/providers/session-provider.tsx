"use client";

import { createContext, ReactNode, useCallback, useEffect, useMemo, useState } from "react";
import { clearSession, getSession, getValidAccessToken, refreshSession, sessionEventName } from "@/lib/auth";
import type { TokenPair } from "@/types/api";

export interface SessionContextValue {
  session: TokenPair | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  refresh: () => Promise<void>;
  signOut: () => void;
}

export const SessionContext = createContext<SessionContextValue | null>(null);

export function SessionProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<TokenPair | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const syncSession = useCallback(async () => {
    try {
      await getValidAccessToken();
      setSession(getSession());
    } catch {
      setSession(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void syncSession();
    const handleChange = () => setSession(getSession());
    window.addEventListener(sessionEventName, handleChange);
    window.addEventListener("storage", handleChange);
    const refreshTimer = window.setInterval(() => void syncSession(), 30_000);
    return () => {
      window.removeEventListener(sessionEventName, handleChange);
      window.removeEventListener("storage", handleChange);
      window.clearInterval(refreshTimer);
    };
  }, [syncSession]);

  const value = useMemo<SessionContextValue>(() => ({
    session,
    isAuthenticated: session !== null,
    isLoading,
    refresh: async () => { await refreshSession(); setSession(getSession()); },
    signOut: () => { clearSession(); setSession(null); },
  }), [isLoading, session]);

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}
