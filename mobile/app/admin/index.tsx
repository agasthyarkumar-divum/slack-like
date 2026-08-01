import { EmptyState } from "@/components/EmptyState";
import { Screen } from "@/components/Screen";

// The Admin Dashboard's backend (GET /admin/users, /admin/audit-logs, /admin/stats
// — architecture.md §6) was never part of the 10-phase build order (auth through
// notifications) this app was built through, so there's no real data to wire this
// screen to yet. Styled per the design system rather than left as a bare
// placeholder, but honest about not being backed by anything real.
export default function AdminDashboardScreen() {
  return (
    <Screen padded>
      <EmptyState
        title="Not built yet."
        subtitle="User management, audit logs, and usage stats need an admin API that hasn't been built (architecture.md §6)."
      />
    </Screen>
  );
}
