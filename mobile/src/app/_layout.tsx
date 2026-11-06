import { Stack } from "expo-router";
import { StatusBar } from "expo-status-bar";
import type { ReactNode } from "react";
import { GestureHandlerRootView } from "react-native-gesture-handler";

import { SessionProvider } from "../session";

export default function RootLayout(): ReactNode {
  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <SessionProvider>
        <StatusBar style="auto" />
        <Stack screenOptions={{ headerShown: false }} />
      </SessionProvider>
    </GestureHandlerRootView>
  );
}
