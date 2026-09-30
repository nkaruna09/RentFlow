import { get } from "@/lib/api/client";
import type { User } from "@/types/api";

export function getCurrentUser(): Promise<User> {
  return get<User>("/auth/me");
}
