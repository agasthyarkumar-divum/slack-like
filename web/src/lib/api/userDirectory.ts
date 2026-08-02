import { useEffect, useState } from "react";

import { getUser } from "@/lib/api/users";
import type { User } from "@/lib/api/types";

// Module-level cache, not per-component state — the same user (a channel's
// other DM member, a message sender, someone typing) gets looked up from
// several different components, and there's no batch "get users by id"
// endpoint to fetch them all in one call.
const cache = new Map<string, User>();
const pending = new Map<string, Promise<User>>();

export function getCachedUser(userId: string): User | undefined {
  return cache.get(userId);
}

export async function resolveUser(userId: string): Promise<User | null> {
  const cached = cache.get(userId);
  if (cached) return cached;
  const inFlight = pending.get(userId);
  if (inFlight) return inFlight;

  const promise = getUser(userId)
    .then((user) => {
      cache.set(userId, user);
      return user;
    })
    .catch(() => null)
    .finally(() => {
      pending.delete(userId);
    });
  pending.set(userId, promise as Promise<User>);
  return promise;
}

/** Resolves to a display name once loaded; "…" while pending, "" for no id. */
export function useUserName(userId: string | null | undefined): string {
  const [, setTick] = useState(0);

  useEffect(() => {
    if (!userId || cache.has(userId)) return;
    let cancelled = false;
    resolveUser(userId).then(() => {
      if (!cancelled) setTick((n) => n + 1);
    });
    return () => {
      cancelled = true;
    };
  }, [userId]);

  if (!userId) return "";
  return cache.get(userId)?.display_name ?? "…";
}
