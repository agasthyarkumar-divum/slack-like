import { api } from "@/lib/api/client";
import type { User } from "@/lib/api/types";

export async function getUser(userId: string): Promise<User> {
  const { data } = await api.get<User>(`/users/${userId}`);
  return data;
}
