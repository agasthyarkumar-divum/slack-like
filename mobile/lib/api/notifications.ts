import { api } from "@/lib/api/client";
import type { NotificationListResponse, Notification } from "@/lib/api/types";

export async function listNotifications(): Promise<NotificationListResponse> {
  const { data } = await api.get<NotificationListResponse>("/notifications");
  return data;
}

export async function markRead(notificationId: string): Promise<Notification> {
  const { data } = await api.post<Notification>(`/notifications/${notificationId}/read`);
  return data;
}

export async function markAllRead(): Promise<void> {
  await api.post("/notifications/read-all");
}
