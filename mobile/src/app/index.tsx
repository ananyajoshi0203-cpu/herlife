import { Redirect } from "expo-router";
import type { ReactNode } from "react";
import { ActivityIndicator, View } from "react-native";

import { useSession } from "../session";

export default function Entry(): ReactNode {
  const { user } = useSession();
  if (user === undefined) {
    return (
      <View style={{ flex: 1, alignItems: "center", justifyContent: "center" }}>
        <ActivityIndicator />
      </View>
    );
  }
  return <Redirect href={user ? "/today" : "/onboarding"} />;
}
