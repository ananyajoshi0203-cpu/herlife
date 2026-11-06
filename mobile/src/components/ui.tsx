import type { ReactNode } from "react";
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, View, type TextStyle, type ViewStyle } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { useSession } from "../session";
import { radius, useTheme, type Theme } from "../theme";

export function usePhaseTheme(): Theme {
  return useTheme(useSession().phase);
}

export function Screen({ children }: { children: ReactNode }): ReactNode {
  const theme = usePhaseTheme();
  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: theme.bg }} edges={["top", "left", "right"]}>
      <ScrollView contentContainerStyle={styles.screen} keyboardShouldPersistTaps="handled">
        {children}
      </ScrollView>
    </SafeAreaView>
  );
}

export function Heading({ eyebrow, title, sub }: { eyebrow?: string; title: string; sub?: string }): ReactNode {
  const theme = usePhaseTheme();
  return (
    <View style={styles.stack}>
      {eyebrow ? <Eyebrow>{eyebrow}</Eyebrow> : null}
      <Text style={[styles.h1, { color: theme.ink }]}>{title}</Text>
      {sub ? <Text style={{ color: theme.muted, fontSize: 15 }}>{sub}</Text> : null}
    </View>
  );
}

export function Title({ children, level = "h2" }: { children: ReactNode; level?: "h2" | "h3" }): ReactNode {
  const theme = usePhaseTheme();
  return <Text style={[styles[level], { color: theme.ink }]}>{children}</Text>;
}

export function Eyebrow({ children, color }: { children: ReactNode; color?: string }): ReactNode {
  const theme = usePhaseTheme();
  return <Text style={[styles.eyebrow, { color: color ?? theme.muted }]}>{children}</Text>;
}

export function Body({ children, muted, style }: { children: ReactNode; muted?: boolean; style?: TextStyle }): ReactNode {
  const theme = usePhaseTheme();
  return <Text style={[{ color: muted ? theme.muted : theme.ink, fontSize: 15, lineHeight: 21 }, style]}>{children}</Text>;
}

export function Card({ children, flat, style }: { children: ReactNode; flat?: boolean; style?: ViewStyle }): ReactNode {
  const theme = usePhaseTheme();
  const surface = flat
    ? { backgroundColor: theme.surface2, borderColor: "transparent" }
    : { backgroundColor: theme.surface, borderColor: theme.line };
  return <View style={[styles.card, surface, style]}>{children}</View>;
}

type ButtonKind = "solid" | "ghost" | "soft";

export function Button({
  label,
  onPress,
  kind = "solid",
  disabled,
  busy,
}: {
  label: string;
  onPress: () => void;
  kind?: ButtonKind;
  disabled?: boolean;
  busy?: boolean;
}): ReactNode {
  const theme = usePhaseTheme();
  const look: Record<ButtonKind, { bg: string; fg: string; border: string }> = {
    solid: { bg: theme.accent, fg: theme.accentInk, border: theme.accent },
    ghost: { bg: "transparent", fg: theme.ink, border: theme.line },
    soft: { bg: theme.surface2, fg: theme.accent, border: theme.surface2 },
  };
  const { bg, fg, border } = look[kind];
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityState={{ disabled: disabled || busy }}
      disabled={disabled || busy}
      onPress={onPress}
      style={({ pressed }) => [
        styles.button,
        { backgroundColor: bg, borderColor: border, opacity: disabled ? 0.45 : 1, transform: [{ scale: pressed ? 0.97 : 1 }] },
      ]}
    >
      {busy ? <ActivityIndicator color={fg} /> : <Text style={[styles.buttonLabel, { color: fg }]}>{label}</Text>}
    </Pressable>
  );
}

export function Chip({ label, on, onPress }: { label: string; on: boolean; onPress: () => void }): ReactNode {
  const theme = usePhaseTheme();
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityState={{ selected: on }}
      onPress={onPress}
      style={[styles.chip, { borderColor: on ? theme.accent : theme.line, backgroundColor: on ? theme.surface2 : theme.surface }]}
    >
      <Text style={{ color: on ? theme.accent : theme.ink, fontWeight: on ? "700" : "500" }}>{label}</Text>
    </Pressable>
  );
}

export function ErrorNote({ error }: { error: string | null }): ReactNode {
  const theme = usePhaseTheme();
  return error ? <Text style={{ color: theme.warn, fontSize: 13 }}>{error}</Text> : null;
}

export const friendlyError = (cause: unknown): string =>
  `We couldn't reach HerLife just now. Check your connection and try again.${__DEV__ ? ` (${String(cause)})` : ""}`;

export const styles = StyleSheet.create({
  screen: { padding: 18, paddingBottom: 32, gap: 16 },
  stack: { gap: 8 },
  row: { flexDirection: "row", alignItems: "center", gap: 10 },
  wrap: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  h1: { fontSize: 30, lineHeight: 33, fontWeight: "800", letterSpacing: -0.3 },
  h2: { fontSize: 21, fontWeight: "700" },
  h3: { fontSize: 16, fontWeight: "700" },
  eyebrow: { fontSize: 11, letterSpacing: 1, textTransform: "uppercase", fontWeight: "600" },
  card: { borderRadius: radius.lg, padding: 16, borderWidth: 1, gap: 10 },
  button: { borderRadius: 99, paddingVertical: 13, paddingHorizontal: 20, borderWidth: 1.5, alignItems: "center", justifyContent: "center" },
  buttonLabel: { fontWeight: "700", fontSize: 15 },
  chip: { borderWidth: 1.5, borderRadius: 99, paddingVertical: 8, paddingHorizontal: 14 },
  input: { borderWidth: 1.5, borderRadius: radius.md, paddingVertical: 12, paddingHorizontal: 14, fontSize: 15 },
});
