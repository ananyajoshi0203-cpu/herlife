import { useCallback, useState, type ReactNode } from "react";
import { View } from "react-native";

import { api, type Habit, type HabitConsistency } from "../../api";
import { SwipeDeck, type SwipeDirection } from "../../components/SwipeDeck";
import { Body, Button, Card, ErrorNote, friendlyError, Heading, Screen, styles, Title, usePhaseTheme } from "../../components/ui";
import { useSession, useUser } from "../../session";
import { useRemote } from "../../useRemote";

export default function Habits(): ReactNode {
  const user = useUser();
  const { habits, setHabits } = useSession();
  const loadConsistency = useCallback(() => api.habitConsistency(user.id), [user.id]);
  const consistency = useRemote(loadConsistency);
  // Resolved this session only: the API records "done" but has no notion of "not today".
  const [resolved, setResolved] = useState<Record<string, SwipeDirection>>({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const pending = habits.filter((habit) => !resolved[habit.id]);
  const doneToday = Object.values(resolved).filter((direction) => direction === "right").length;

  const resolve = async (habit: Habit, direction: SwipeDirection): Promise<void> => {
    setResolved((current) => ({ ...current, [habit.id]: direction }));
    if (direction === "left") return;
    try {
      await api.checkHabit(user.id, habit.id);
      consistency.reload();
    } catch (cause) {
      setResolved(({ [habit.id]: _undone, ...rest }) => rest);
      setError(friendlyError(cause));
    }
  };

  const refreshHabits = async (): Promise<void> => {
    setBusy(true);
    setError(null);
    try {
      await setHabits((await api.suggestHabits(user.id)).habits);
      setResolved({});
      consistency.reload();
    } catch (cause) {
      setError(friendlyError(cause));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Screen>
      <Heading eyebrow="Habit tracker" title={`${doneToday} of ${habits.length} done today`} sub="Consistency beats intensity. Here is every week, at a glance." />
      {habits.length ? <SwipeDeck habits={pending} onResolve={resolve} /> : <Body muted>No habits yet. Ask Claude for three that fit your goals.</Body>}
      <ErrorNote error={error ?? consistency.error} />
      {consistency.data?.length ? <WeeklyConsistency rows={consistency.data} /> : null}
      <Button kind="ghost" label="Ask Claude for fresh habits" busy={busy} onPress={refreshHabits} />
    </Screen>
  );
}

function WeeklyConsistency({ rows }: { rows: HabitConsistency[] }): ReactNode {
  const theme = usePhaseTheme();
  return (
    <Card>
      <Title>Weekly consistency</Title>
      {rows.map((row) => (
        <View key={row.habit_id} style={{ gap: 6 }}>
          <Body>{row.title}</Body>
          <View style={[styles.row, { gap: 6 }]}>
            {row.weeks.slice(-4).map((week) => (
              <View key={week.iso_week} style={{ flex: 1, height: 8, borderRadius: 4, backgroundColor: theme.line, overflow: "hidden" }}>
                <View style={{ width: `${Math.round(100 * (week.rate ?? 0))}%`, height: "100%", backgroundColor: theme.accent }} />
              </View>
            ))}
          </View>
        </View>
      ))}
      <Body muted style={{ fontSize: 13 }}>
        Last four weeks, oldest on the left.
      </Body>
    </Card>
  );
}
