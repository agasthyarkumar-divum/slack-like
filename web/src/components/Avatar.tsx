import styles from "./Avatar.module.css";

type AvatarProps = {
  name: string;
  imageUri?: string | null;
  size?: number;
};

function initialsFor(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "?";
  if (parts.length === 1) return parts[0]!.slice(0, 2).toUpperCase();
  return (parts[0]![0]! + parts[parts.length - 1]![0]!).toUpperCase();
}

// Soft rounded squares, not circles — matches the mobile app's Avatar
// (a small deliberate departure from the typical circular-avatar convention).
export function Avatar({ name, imageUri, size = 40 }: AvatarProps) {
  const style = {
    width: size,
    height: size,
    borderRadius: Math.max(8, size * 0.28),
  };

  if (imageUri) {
    return <img src={imageUri} alt="" className={styles.image} style={style} />;
  }

  return (
    <div className={styles.fallback} style={style}>
      <span className={styles.initials} style={{ fontSize: size * 0.4 }}>
        {initialsFor(name)}
      </span>
    </div>
  );
}
