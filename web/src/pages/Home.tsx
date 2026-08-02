import {
  Bell,
  CheckCheck,
  GitBranch,
  Hash,
  MessageSquare,
  Moon,
  Paperclip,
  Search,
  ShieldCheck,
  Smartphone,
  Sun,
} from "lucide-react";
import { useNavigate } from "react-router-dom";

import { useTheme } from "@/lib/theme/ThemeContext";
import styles from "./Home.module.css";

const FEATURES = [
  {
    icon: MessageSquare,
    title: "Real-time messaging",
    description: "Instant delivery over WebSockets, live typing indicators, and presence — conversations feel like they're in the room.",
  },
  {
    icon: Hash,
    title: "Channels & DMs",
    description: "Public channels, private groups, and one-on-one DMs, all with unread tracking that stays out of your way.",
  },
  {
    icon: GitBranch,
    title: "Threaded replies",
    description: "Keep side conversations contained without losing context in the main channel.",
  },
  {
    icon: CheckCheck,
    title: "Reactions & receipts",
    description: "Emoji reactions plus delivered and read receipts, so you always know a message landed.",
  },
  {
    icon: Paperclip,
    title: "Encrypted file sharing",
    description: "Upload files with encryption at rest and automatic thumbnails, ready to preview instantly.",
  },
  {
    icon: Search,
    title: "Full-text search",
    description: "Find any message, file, channel, or person across the whole workspace in a keystroke.",
  },
  {
    icon: Bell,
    title: "Smart notifications",
    description: "Push and in-app alerts you control, per conversation — nothing you didn't ask for.",
  },
  {
    icon: ShieldCheck,
    title: "Admin dashboard & RBAC",
    description: "Role-based access control, audit logs, and a full admin console for the people who own the workspace.",
  },
];

export default function Home() {
  const navigate = useNavigate();
  const { isDark, toggle } = useTheme();

  return (
    <div className={styles.page}>
      <header className={styles.nav}>
        <div className={styles.brand}>
          <div className={styles.mark}>DC</div>
          <span className={styles.brandName}>Divum Chat</span>
        </div>
        <div className={styles.navActions}>
          <button type="button" className={styles.themeToggle} onClick={toggle} aria-label="Toggle theme">
            {isDark ? <Sun size={18} /> : <Moon size={18} />}
          </button>
          <button type="button" className={styles.navGhost} onClick={() => navigate("/login")}>
            Log in
          </button>
          <button type="button" className={styles.navPrimary} onClick={() => navigate("/signup")}>
            Sign up
          </button>
        </div>
      </header>

      <main>
        <section className={styles.hero}>
          <h1 className={styles.headline}>Team chat that gets out of your way.</h1>
          <p className={styles.subheadline}>
            Real-time messaging, threads, and file sharing for teams — with the security
            and admin controls IT actually wants.
          </p>
          <div className={styles.heroActions}>
            <button type="button" className={styles.ctaPrimary} onClick={() => navigate("/signup")}>
              Get started free
            </button>
            <button type="button" className={styles.ctaGhost} onClick={() => navigate("/login")}>
              Log in
            </button>
          </div>
        </section>

        <section className={styles.features}>
          <div className={styles.featureGrid}>
            {FEATURES.map(({ icon: Icon, title, description }) => (
              <div className={styles.featureCard} key={title}>
                <div className={styles.featureIcon}>
                  <Icon size={20} />
                </div>
                <h3 className={styles.featureTitle}>{title}</h3>
                <p className={styles.featureDescription}>{description}</p>
              </div>
            ))}
          </div>
        </section>

        <section className={styles.platforms}>
          <Smartphone size={18} />
          <span>Desktop web and mobile, from one account.</span>
        </section>

        <section className={styles.finalCta}>
          <h2 className={styles.finalCtaTitle}>Ready to bring your team together?</h2>
          <button type="button" className={styles.ctaPrimary} onClick={() => navigate("/signup")}>
            Create your account
          </button>
        </section>
      </main>

      <footer className={styles.footer}>
        <span>Divum Chat</span>
      </footer>
    </div>
  );
}
