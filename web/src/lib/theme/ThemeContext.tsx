import { createContext, useContext, useEffect, useMemo, useState } from "react";
import type { PropsWithChildren } from "react";

export type ThemeMode = "light" | "dark";

type ThemeContextValue = {
  mode: ThemeMode;
  isDark: boolean;
  toggle: () => void;
  setMode: (mode: ThemeMode) => void;
};

const THEME_MODE_KEY = "divum_chat_theme_mode";

const ThemeContext = createContext<ThemeContextValue | null>(null);

function systemPrefersDark(): boolean {
  return window.matchMedia?.("(prefers-color-scheme: dark)").matches ?? false;
}

function readStoredMode(): ThemeMode {
  const stored = localStorage.getItem(THEME_MODE_KEY);
  if (stored === "light" || stored === "dark") return stored;
  return systemPrefersDark() ? "dark" : "light";
}

export function ThemeProvider({ children }: PropsWithChildren) {
  const [mode, setModeState] = useState<ThemeMode>(readStoredMode);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", mode);
  }, [mode]);

  function setMode(next: ThemeMode) {
    setModeState(next);
    localStorage.setItem(THEME_MODE_KEY, next);
  }

  function toggle() {
    setMode(mode === "dark" ? "light" : "dark");
  }

  const value = useMemo(
    () => ({ mode, isDark: mode === "dark", toggle, setMode }),
    [mode]
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme(): ThemeContextValue {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error("useTheme must be used within a ThemeProvider");
  return ctx;
}
