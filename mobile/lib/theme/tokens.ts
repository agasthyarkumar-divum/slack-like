/**
 * Design tokens — calm workspace tool, not a flashy consumer app. Warm
 * off-whites and a muted moss accent in light mode; a true (not just
 * inverted-gray) warm near-black palette in dark mode, same moss accent.
 */

export const radii = {
  sm: 8,
  md: 14,
  lg: 18,
  pill: 999,
};

export const spacing = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 24,
  xxl: 32,
};

export type ColorTokens = {
  bgBase: string;
  bgSurface: string;
  bgSurfaceRaised: string;
  textPrimary: string;
  textSecondary: string;
  accentMoss: string;
  accentMossSoft: string;
  borderHairline: string;
  stateError: string;
};

export const lightColors: ColorTokens = {
  bgBase: "#FAFAF8",
  bgSurface: "#F1EFEA",
  bgSurfaceRaised: "#FFFFFF",
  textPrimary: "#2B2A26",
  textSecondary: "#83816F",
  accentMoss: "#5F7052",
  accentMossSoft: "#E5E9DE",
  borderHairline: "#E6E3DA",
  stateError: "#A6503B",
};

export const darkColors: ColorTokens = {
  bgBase: "#1C1B18",
  bgSurface: "#26241F",
  bgSurfaceRaised: "#2F2C26",
  textPrimary: "#EDEBE6",
  textSecondary: "#96927F",
  accentMoss: "#7A8F6B",
  accentMossSoft: "#333A2B",
  borderHairline: "#38352E",
  stateError: "#C17057",
};

export const fonts = {
  display: "Fraunces_600SemiBold",
  displayRegular: "Fraunces_400Regular",
  body: "Inter_400Regular",
  bodyMedium: "Inter_500Medium",
  bodySemiBold: "Inter_600SemiBold",
  bodyBold: "Inter_700Bold",
};
