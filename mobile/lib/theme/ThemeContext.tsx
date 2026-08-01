import { createContext, useContext, useEffect, useMemo, useState } from "react";
import type { PropsWithChildren } from "react";
import { useColorScheme } from "react-native";

import { getItem, setItem } from "@/lib/storage/platformStorage";
import { type ColorTokens, darkColors, lightColors } from "@/lib/theme/tokens";

type ThemeMode = "system" | "light" | "dark";

type ThemeContextValue = {
  mode: ThemeMode;
  isDark: boolean;
  colors: ColorTokens;
  setMode: (mode: ThemeMode) => void;
};

const THEME_MODE_KEY = "divum_chat_theme_mode";

const ThemeContext = createContext<ThemeContextValue | null>(null);

export function ThemeProvider({ children }: PropsWithChildren) {
  const systemScheme = useColorScheme();
  const [mode, setModeState] = useState<ThemeMode>("system");

  useEffect(() => {
    (async () => {
      const stored = await getItem(THEME_MODE_KEY);
      if (stored === "light" || stored === "dark" || stored === "system") {
        setModeState(stored);
      }
    })();
  }, []);

  function setMode(next: ThemeMode) {
    setModeState(next);
    setItem(THEME_MODE_KEY, next);
  }

  const isDark = mode === "system" ? systemScheme === "dark" : mode === "dark";
  const colors = isDark ? darkColors : lightColors;

  const value = useMemo(() => ({ mode, isDark, colors, setMode }), [mode, isDark, colors]);

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme(): ThemeContextValue {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error("useTheme must be used within a ThemeProvider");
  return ctx;
}
