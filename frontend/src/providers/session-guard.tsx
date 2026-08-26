"use client";

import { ReactNode, useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/hooks/use-auth";

export function SessionGuard({ children }: { children: ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth();
  const pathname = usePathname();
  const router = useRouter();

  useEffect(() => {
    if (isLoading || isAuthenticated) return;
    const returnPath = `${pathname}${window.location.search}`;
    router.replace(`/login?next=${encodeURIComponent(returnPath)}`);
  }, [isAuthenticated, isLoading, pathname, router]);

  if (isLoading || !isAuthenticated) return null;
  return children;
}
