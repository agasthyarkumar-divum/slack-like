import { api } from "@/lib/api/client";
import type { NotificationPreference, User } from "@/lib/api/types";

export async function getUser(userId: string): Promise<User> {
  const { data } = await api.get<User>(`/users/${userId}`);
  return data;
}

export async function updateSettings(notification_preference: NotificationPreference): Promise<User> {
  const { data } = await api.patch<User>("/users/me", { notification_preference });
  return data;
}
