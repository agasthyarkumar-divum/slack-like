import { useCallback, useEffect, useState } from "react";
import { ActivityIndicator, FlatList, Modal, Pressable, RefreshControl, StyleSheet, Text, View } from "react-native";
import { Check, ChevronRight, X } from "lucide-react-native";

import { Avatar } from "@/components/Avatar";
import { EmptyState } from "@/components/EmptyState";
import { Screen } from "@/components/Screen";
import { getStats, listAuditLogs, listUsers, updateUserRole } from "@/lib/api/admin";
import type { AdminStats, AdminUser, AuditLogEntry, Scope } from "@/lib/api/types";
import { useAuth } from "@/lib/auth/AuthContext";
import { useTheme } from "@/lib/theme/ThemeContext";
import type { ColorTokens } from "@/lib/theme/tokens";
import { fonts, radii, spacing } from "@/lib/theme/tokens";

type Tab = "overview" | "users" | "audit";

const SCOPE_LABEL: Record<Scope, string> = { users: "User", admin: "Admin", superAdmin: "Super Admin" };
const ALL_SCOPES: Scope[] = ["users", "admin", "superAdmin"];
const TAB_LABEL: Record<Tab, string> = { overview: "Overview", users: "Users", audit: "Audit Log" };

function timeLabel(iso: string): string {
  return new Date(iso).toLocaleString([], { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
}

function describeAuditEntry(entry: AuditLogEntry): string {
  if (entry.action === "user.scope_updated") {
    const extra = entry.extra_data as { old_scope?: string; new_scope?: string } | null;
    return `Changed a user's scope: ${extra?.old_scope ?? "?"} → ${extra?.new_scope ?? "?"}`;
  }
  return entry.action;
}

// Real Admin Dashboard (architecture.md §6): usage stats, user scope
// management (users/admin/superAdmin), and the audit trail those changes
// write to. Gated server-side by require_admin — the link to this screen is
// also hidden for non-admins in Profile, but a direct nav here degrades to
// an EmptyState rather than a broken screen if the API 403s.
export default function AdminDashboardScreen() {
  const { colors } = useTheme();
  const { user: currentUser, isAdmin, isSuperAdmin } = useAuth();
  const [tab, setTab] = useState<Tab>("overview");

  const [stats, setStats] = useState<AdminStats | null>(null);
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditLogEntry[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [forbidden, setForbidden] = useState(false);
  const [pickerUser, setPickerUser] = useState<AdminUser | null>(null);
  const [isUpdatingRole, setIsUpdatingRole] = useState(false);

  const load = useCallback(async () => {
    try {
      const [statsData, usersData, auditData] = await Promise.all([getStats(), listUsers(), listAuditLogs()]);
      setStats(statsData);
      setUsers(usersData);
      setAuditLogs(auditData);
      setForbidden(false);
    } catch (error: unknown) {
      const status = (error as { response?: { status?: number } })?.response?.status;
      if (status === 403) setForbidden(true);
      else throw error;
    }
  }, []);

  useEffect(() => {
    load().finally(() => setIsLoading(false));
  }, [load]);

  async function handleRefresh() {
    setIsRefreshing(true);
    await load();
    setIsRefreshing(false);
  }

  async function handlePickScope(scope: Scope) {
    if (!pickerUser) return;
    setIsUpdatingRole(true);
    try {
      const updated = await updateUserRole(pickerUser.id, scope);
      setUsers((prev) => prev.map((u) => (u.id === updated.id ? updated : u)));
      setPickerUser(null);
      await load(); // also refreshes the audit log + stats
    } catch {
      // best-effort — leave the picker open so the admin can see it didn't apply and retry
    } finally {
      setIsUpdatingRole(false);
    }
  }

  if (isLoading) {
    return (
      <Screen padded>
        <ActivityIndicator style={styles.loading} color={colors.accentMoss} />
      </Screen>
    );
  }

  if (forbidden || !isAdmin) {
    return (
      <Screen padded>
        <EmptyState title="You don't have access." subtitle="The admin dashboard requires 'admin' scope or higher." />
      </Screen>
    );
  }

  return (
    <Screen>
      <View style={[styles.tabs, { borderColor: colors.borderHairline }]}>
        {(Object.keys(TAB_LABEL) as Tab[]).map((t) => (
          <Pressable key={t} onPress={() => setTab(t)} style={styles.tabButton}>
            <Text style={[styles.tabLabel, { color: tab === t ? colors.accentMoss : colors.textSecondary }]}>
              {TAB_LABEL[t]}
            </Text>
            {tab === t ? <View style={[styles.tabUnderline, { backgroundColor: colors.accentMoss }]} /> : null}
          </Pressable>
        ))}
      </View>

      {tab === "overview" && stats ? (
        <View style={styles.statsGrid}>
          <StatCard label="Total users" value={stats.total_users} colors={colors} />
          <StatCard label="Active users" value={stats.active_users} colors={colors} />
          <StatCard label="Active today" value={stats.users_active_today} colors={colors} />
          <StatCard label="Channels" value={stats.total_channels} colors={colors} />
          <StatCard label="Messages" value={stats.total_messages} colors={colors} />
        </View>
      ) : null}

      {tab === "users" ? (
        <FlatList
          data={users}
          keyExtractor={(item) => item.id}
          refreshControl={<RefreshControl refreshing={isRefreshing} onRefresh={handleRefresh} tintColor={colors.accentMoss} />}
          contentContainerStyle={styles.listContent}
          ItemSeparatorComponent={() => <View style={[styles.separator, { backgroundColor: colors.borderHairline }]} />}
          renderItem={({ item }) => {
            const isSelf = item.id === currentUser?.id;
            const isLockedSuperAdmin = item.scope === "superAdmin" && !isSuperAdmin;
            const disabled = isSelf || isLockedSuperAdmin;
            return (
              <Pressable
                style={[styles.userRow, disabled && styles.userRowDisabled]}
                onPress={() => !disabled && setPickerUser(item)}
                disabled={disabled}
              >
                <Avatar name={item.display_name} size={36} />
                <View style={styles.userInfo}>
                  <Text style={[styles.userName, { color: colors.textPrimary }]}>
                    {item.display_name}
                    {isSelf ? " (you)" : ""}
                  </Text>
                  <Text style={[styles.userEmail, { color: colors.textSecondary }]}>{item.email}</Text>
                </View>
                <View style={[styles.scopeChip, { backgroundColor: colors.accentMossSoft }]}>
                  <Text style={[styles.scopeChipText, { color: colors.accentMoss }]}>{SCOPE_LABEL[item.scope]}</Text>
                </View>
                {!disabled ? <ChevronRight size={16} color={colors.textSecondary} strokeWidth={1.5} /> : null}
              </Pressable>
            );
          }}
        />
      ) : null}

      {tab === "audit" ? (
        <FlatList
          data={auditLogs}
          keyExtractor={(item) => item.id}
          refreshControl={<RefreshControl refreshing={isRefreshing} onRefresh={handleRefresh} tintColor={colors.accentMoss} />}
          contentContainerStyle={styles.listContent}
          ListEmptyComponent={<EmptyState title="No activity yet." subtitle="Scope changes and other admin actions will show up here." />}
          ItemSeparatorComponent={() => <View style={[styles.separator, { backgroundColor: colors.borderHairline }]} />}
          renderItem={({ item }) => (
            <View style={styles.auditRow}>
              <Text style={[styles.auditDescription, { color: colors.textPrimary }]}>{describeAuditEntry(item)}</Text>
              <Text style={[styles.auditTime, { color: colors.textSecondary }]}>{timeLabel(item.created_at)}</Text>
            </View>
          )}
        />
      ) : null}

      <Modal visible={!!pickerUser} transparent animationType="fade" onRequestClose={() => setPickerUser(null)}>
        <Pressable style={styles.modalBackdrop} onPress={() => !isUpdatingRole && setPickerUser(null)}>
          <Pressable
            style={[styles.modalSheet, { backgroundColor: colors.bgSurfaceRaised }]}
            onPress={(event) => event.stopPropagation()}
          >
            <View style={styles.modalHeader}>
              <Text style={[styles.modalTitle, { color: colors.textPrimary }]}>{pickerUser?.display_name}</Text>
              <Pressable onPress={() => setPickerUser(null)} disabled={isUpdatingRole}>
                <X size={20} color={colors.textSecondary} strokeWidth={1.5} />
              </Pressable>
            </View>
            {ALL_SCOPES.map((scope) => {
              const isDisabledOption = scope === "superAdmin" && !isSuperAdmin;
              return (
                <Pressable
                  key={scope}
                  style={styles.scopeOption}
                  onPress={() => !isDisabledOption && !isUpdatingRole && handlePickScope(scope)}
                  disabled={isDisabledOption || isUpdatingRole}
                >
                  <Text
                    style={[
                      styles.scopeOptionLabel,
                      { color: colors.textPrimary, opacity: isDisabledOption ? 0.4 : 1 },
                    ]}
                  >
                    {SCOPE_LABEL[scope]}
                  </Text>
                  {pickerUser?.scope === scope ? <Check size={18} color={colors.accentMoss} strokeWidth={2} /> : null}
                </Pressable>
              );
            })}
            {isUpdatingRole ? <ActivityIndicator style={styles.modalLoading} color={colors.accentMoss} /> : null}
          </Pressable>
        </Pressable>
      </Modal>
    </Screen>
  );
}

function StatCard({ label, value, colors }: { label: string; value: number; colors: ColorTokens }) {
  return (
    <View style={[styles.statCard, { backgroundColor: colors.bgSurface }]}>
      <Text style={[styles.statValue, { color: colors.textPrimary }]}>{value}</Text>
      <Text style={[styles.statLabel, { color: colors.textSecondary }]}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  loading: { marginTop: spacing.xxl },
  tabs: { flexDirection: "row", borderBottomWidth: 1, paddingHorizontal: spacing.lg },
  tabButton: { paddingVertical: spacing.md, marginRight: spacing.lg },
  tabLabel: { fontFamily: fonts.bodyMedium, fontSize: 14 },
  tabUnderline: { height: 2, borderRadius: 1, marginTop: spacing.xs },
  statsGrid: { flexDirection: "row", flexWrap: "wrap", gap: spacing.sm, padding: spacing.lg },
  statCard: { flexBasis: "47%", borderRadius: radii.md, padding: spacing.md, gap: spacing.xs },
  statValue: { fontFamily: fonts.display, fontSize: 26 },
  statLabel: { fontFamily: fonts.body, fontSize: 13 },
  listContent: { paddingBottom: spacing.xl },
  separator: { height: 1, marginLeft: spacing.lg + 36 + spacing.sm },
  userRow: { flexDirection: "row", alignItems: "center", gap: spacing.sm, paddingHorizontal: spacing.lg, paddingVertical: spacing.md },
  userRowDisabled: { opacity: 0.6 },
  userInfo: { flex: 1, gap: 2 },
  userName: { fontFamily: fonts.bodyMedium, fontSize: 15 },
  userEmail: { fontFamily: fonts.body, fontSize: 13 },
  scopeChip: { borderRadius: radii.pill, paddingHorizontal: spacing.sm, paddingVertical: 3 },
  scopeChipText: { fontFamily: fonts.bodyMedium, fontSize: 11 },
  auditRow: { paddingHorizontal: spacing.lg, paddingVertical: spacing.md, gap: 2 },
  auditDescription: { fontFamily: fonts.body, fontSize: 14, lineHeight: 20 },
  auditTime: { fontFamily: fonts.body, fontSize: 12 },
  modalBackdrop: { flex: 1, backgroundColor: "rgba(0,0,0,0.4)", justifyContent: "flex-end" },
  modalSheet: { borderTopLeftRadius: radii.lg, borderTopRightRadius: radii.lg, padding: spacing.lg, gap: spacing.xs },
  modalHeader: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: spacing.sm },
  modalTitle: { fontFamily: fonts.bodySemiBold, fontSize: 17 },
  scopeOption: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", paddingVertical: spacing.md },
  scopeOptionLabel: { fontFamily: fonts.body, fontSize: 15 },
  modalLoading: { marginTop: spacing.sm },
});
