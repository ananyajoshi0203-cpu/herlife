/** Color tokens copied from the `:root` block of web/index.html so the two apps read as one product. */
import { useColorScheme } from "react-native";

import type { CyclePhase } from "./api";

export interface Palette {
  bg: string;
  surface: string;
  surface2: string;
  ink: string;
  muted: string;
  line: string;
  good: string;
  warn: string;
  accentInk: string;
  phase: Record<CyclePhase, string>;
}

const light: Palette = {
  bg: "#F6F2F6",
  surface: "#FFFFFF",
  surface2: "#F1EAF0",
  ink: "#2A1D2D",
  muted: "#75677A",
  line: "#E6DAE4",
  good: "#2E8A67",
  warn: "#C46A12",
  accentInk: "#FFFFFF",
  phase: { menstrual: "#B8395C", follicular: "#2E8A67", ovulatory: "#C98712", luteal: "#7655C2" },
};

const dark: Palette = {
  bg: "#141016",
  surface: "#1F1922",
  surface2: "#2A222E",
  ink: "#F3EAF3",
  muted: "#AE9FB2",
  line: "#372D3B",
  good: "#5CC79C",
  warn: "#F0A050",
  accentInk: "#160F18",
  phase: { menstrual: "#F0718F", follicular: "#5CC79C", ovulatory: "#F2B74B", luteal: "#A68BF0" },
};

/** Follicular green is the web app's accent whenever her phase is unknown or not tracked. */
export const DEFAULT_PHASE: CyclePhase = "follicular";

export interface Theme extends Palette {
  accent: string;
}

export function useTheme(phase: CyclePhase = DEFAULT_PHASE): Theme {
  const palette = useColorScheme() === "dark" ? dark : light;
  return { ...palette, accent: palette.phase[phase] };
}

export const radius = { lg: 22, md: 14, sm: 10 } as const;
