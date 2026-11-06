import { useCallback, useEffect, type ReactNode } from "react";
import { ActivityIndicator, View } from "react-native";

import { api, type CyclePhase, type TodayPlan } from "../../api";
import { Body, Button, Card, ErrorNote, Eyebrow, Heading, Screen, styles, Title, usePhaseTheme } from "../../components/ui";
import { PHASES } from "../../copy";
import { useSession, useUser } from "../../session";
import { useRemote } from "../../useRemote";

/** Each pillar wears the phase color the web app gives it. */
const PILLARS: readonly { key: keyof Pick<TodayPlan, "sleep" | "move" | "eat" | "mind">; label: string; tone: CyclePhase }[] = [
  { key: "sleep", label: "Sleep", tone: "luteal" },
  { key: "move", label: "Move", tone: "follicular" },
  { key: "eat", label: "Nourish", tone: "ovulatory" },
  { key: "mind", label: "Mind", tone: "menstrual" },
];

export default function Today(): ReactNode {
  const user = useUser();
  const { setPhase } = useSession();
  const theme = usePhaseTheme();
  const load = useCallback(() => api.planToday(user.id), [user.id]);
  const { data: plan, error, loading, reload } = useRemote(load);

  useEffect(() => setPhase(plan?.cycle?.phase), [plan, setPhase]);

  const now = new Date();
  const dateLabel = now.toLocaleDateString("en-US", { weekday: "long", month: "long", day: "numeric" });
  const greeting = now.getHours() < 12 ? "Good morning" : now.getHours() < 17 ? "Good afternoon" : "Good evening";
  const cycle = plan?.cycle;

  return (
    <Screen>
      <Heading eyebrow={dateLabel} title={`${greeting}, ${user.name}.`} sub={cycle ? PHASES[cycle.phase].energy : undefined} />
      {loading && !plan ? <ActivityIndicator color={theme.accent} /> : null}
      <ErrorNote error={error} />
      {error ? <Button kind="ghost" label="Try again" onPress={reload} /> : null}

      {cycle ? (
        <Card flat>
          <Eyebrow color={theme.accent}>{`Day ${cycle.cycle_day} · ${PHASES[cycle.phase].label}`}</Eyebrow>
          <Body>{cycle.note}</Body>
        </Card>
      ) : null}

      {plan?.ease_off ? (
        <Card style={{ borderColor: theme.warn }}>
          <Eyebrow>Your body is asking</Eyebrow>
          <Title>Ease off today.</Title>
          {plan.reasons.map((reason) => (
            <Body key={reason}>{`• ${reason}`}</Body>
          ))}
          <Body muted>We swapped your workout for a walk and moved your bedtime earlier. Resting today is part of the plan, not a break from it.</Body>
        </Card>
      ) : null}

      {plan ? (
        <Card>
          <View style={[styles.row, { justifyContent: "space-between" }]}>
            <Title>Today's plan</Title>
            <Eyebrow>4 pillars</Eyebrow>
          </View>
          {PILLARS.map((pillar) => (
            <View key={pillar.key} style={{ flexDirection: "row", gap: 12 }}>
              <View style={{ width: 4, borderRadius: 2, backgroundColor: theme.phase[pillar.tone] }} />
              <View style={{ flex: 1, gap: 2 }}>
                <Eyebrow color={theme.phase[pillar.tone]}>{pillar.label}</Eyebrow>
                <Body>{plan[pillar.key]}</Body>
              </View>
            </View>
          ))}
        </Card>
      ) : null}
    </Screen>
  );
}
