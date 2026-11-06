import { router } from "expo-router";
import { useState, type ReactNode } from "react";
import { Pressable, Text, TextInput, View } from "react-native";

import { api, type GymAccess, type LifeStage } from "../api";
import { Body, Button, Chip, ErrorNote, friendlyError, Heading, Screen, styles, usePhaseTheme } from "../components/ui";
import { GOALS, GYM_ACCESS, LIFE_STAGES } from "../copy";
import { useSession } from "../session";

type Step = "profile" | "goals";

export default function Onboarding(): ReactNode {
  const theme = usePhaseTheme();
  const { signIn, setHabits } = useSession();
  const [step, setStep] = useState<Step>("profile");
  const [name, setName] = useState("");
  const [age, setAge] = useState("");
  const [gym, setGym] = useState<GymAccess>("home");
  const [lifeStage, setLifeStage] = useState<LifeStage | null>(null);
  const [goals, setGoals] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const ageNumber = Number.parseInt(age, 10);
  const profileReady = name.trim().length > 0 && ageNumber >= 13 && ageNumber <= 120 && lifeStage !== null;

  const toggleGoal = (title: string): void =>
    setGoals((picked) => (picked.includes(title) ? picked.filter((g) => g !== title) : picked.length < 2 ? [...picked, title] : picked));

  const finish = async (): Promise<void> => {
    const [first, second] = goals;
    if (!lifeStage || !first || !second) return;
    setBusy(true);
    setError(null);
    try {
      const user = await api.createUser({ name: name.trim(), age: ageNumber, gym_access: gym, diet: [], conditions: [], life_stage: lifeStage, goals: [first, second] });
      // Mock mode until she connects Oura; it seeds 90 days so Today and Record have something to show.
      await api.sync(user.id);
      await setHabits((await api.suggestHabits(user.id)).habits);
      await signIn(user);
      router.replace("/today");
    } catch (cause) {
      setError(friendlyError(cause));
    } finally {
      setBusy(false);
    }
  };

  const input = [styles.input, { borderColor: theme.line, backgroundColor: theme.surface, color: theme.ink }];

  if (step === "profile") {
    return (
      <Screen>
        <Heading eyebrow="HerLife" title="Let's set you up" sub="Your record belongs to you. We'll ask only what changes your plan." />
        <Field label="First name">
          <TextInput style={input} value={name} onChangeText={setName} placeholder="Maya" placeholderTextColor={theme.muted} autoComplete="given-name" textContentType="givenName" />
        </Field>
        <Field label="Age">
          <TextInput style={input} value={age} onChangeText={setAge} placeholder="32" placeholderTextColor={theme.muted} keyboardType="number-pad" />
        </Field>
        <Field label="Where do you work out?">
          <View style={styles.wrap}>
            {GYM_ACCESS.map(([value, label]) => (
              <Chip key={value} label={label} on={gym === value} onPress={() => setGym(value)} />
            ))}
          </View>
        </Field>
        <Field label="Where are you in life right now?">
          <View style={styles.wrap}>
            {LIFE_STAGES.map(([value, label]) => (
              <Chip key={value} label={label} on={lifeStage === value} onPress={() => setLifeStage(value)} />
            ))}
          </View>
        </Field>
        <Button label="Continue" disabled={!profileReady} onPress={() => setStep("goals")} />
      </Screen>
    );
  }

  return (
    <Screen>
      <Heading title="Pick two goals" sub="Your whole life, not just your cycle. Claude will turn them into three small habits you can actually keep." />
      <View style={styles.wrap}>
        {GOALS.map((goal) => {
          const on = goals.includes(goal.title);
          return (
            <Pressable
              key={goal.title}
              accessibilityRole="button"
              accessibilityState={{ selected: on }}
              onPress={() => toggleGoal(goal.title)}
              style={{ width: "48%", borderWidth: 1.5, borderRadius: 14, padding: 14, gap: 4, borderColor: on ? theme.accent : theme.line, backgroundColor: on ? theme.surface2 : theme.surface }}
            >
              <Text style={[styles.h3, { color: theme.ink }]}>{goal.title}</Text>
              <Text style={{ color: theme.muted, fontSize: 12 }}>{goal.sub}</Text>
            </Pressable>
          );
        })}
      </View>
      <ErrorNote error={error} />
      <Button label={goals.length === 2 ? "Build my habits" : `Choose ${2 - goals.length} more`} disabled={goals.length !== 2} busy={busy} onPress={finish} />
      <Button kind="ghost" label="Back" onPress={() => setStep("profile")} />
    </Screen>
  );
}

function Field({ label, children }: { label: string; children: ReactNode }): ReactNode {
  return (
    <View style={{ gap: 6 }}>
      <Body muted style={{ fontSize: 13, fontWeight: "600" }}>
        {label}
      </Body>
      {children}
    </View>
  );
}
