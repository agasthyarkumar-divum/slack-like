import { api } from "@/lib/api/client";
import type { AdminStats, AdminUser, AuditLogEntry, Scope } from "@/lib/api/types";

export async function listUsers(): Promise<AdminUser[]> {
  const { data } = await api.get<AdminUser[]>("/admin/users");
  return data;
}

export async function updateUserRole(userId: string, scope: Scope): Promise<AdminUser> {
  const { data } = await api.patch<AdminUser>(`/admin/users/${userId}/role`, { scope });
  return data;
}

export async function listAuditLogs(limit = 50): Promise<AuditLogEntry[]> {
  const { data } = await api.get<AuditLogEntry[]>("/admin/audit-logs", { params: { limit } });
  return data;
}

export async function getStats(): Promise<AdminStats> {
  const { data } = await api.get<AdminStats>("/admin/stats");
  return data;
}
