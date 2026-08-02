import { useNavigate } from "react-router-dom";

import styles from "./WorkspaceSwitcher.module.css";

// Divum Chat is single-workspace by design — this screen exists purely to
// match the familiar "pick a workspace" entry flow, with exactly one card.
export default function WorkspaceSwitcher() {
  const navigate = useNavigate();

  return (
    <div className={styles.container}>
      <div className={styles.stack}>
        <h1 className={styles.title}>Welcome back</h1>
        <p className={styles.subtitle}>Choose a workspace to continue.</p>
        <button type="button" className={styles.card} onClick={() => navigate("/login")}>
          <div className={styles.mark}>DC</div>
          <div className={styles.cardText}>
            <span className={styles.workspaceName}>Divum Chat</span>
            <span className={styles.workspaceStatus}>All systems normal</span>
          </div>
        </button>
      </div>
    </div>
  );
}
