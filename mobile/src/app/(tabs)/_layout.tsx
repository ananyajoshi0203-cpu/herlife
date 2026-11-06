import { Redirect } from "expo-router";
import { Tabs } from "expo-router/js-tabs";
import type { ReactNode } from "react";

import { usePhaseTheme } from "../../components/ui";
import { useSession } from "../../session";

export default function TabLayout(): ReactNode {
  const { user } = useSession();
  const theme = usePhaseTheme();
  if (!user) return <Redirect href="/onboarding" />;
  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarActiveTintColor: theme.accent,
        tabBarInactiveTintColor: theme.muted,
        tabBarStyle: { backgroundColor: theme.surface, borderTopColor: theme.line },
      }}
    >
      <Tabs.Screen name="today" options={{ title: "Today" }} />
      <Tabs.Screen name="habits" options={{ title: "Habits" }} />
      <Tabs.Screen name="log" options={{ title: "Log" }} />
      <Tabs.Screen name="record" options={{ title: "Record" }} />
    </Tabs>
  );
}
