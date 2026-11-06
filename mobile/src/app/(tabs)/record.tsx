import { router } from "expo-router";
import { useCallback, type ReactNode } from "react";
import { ActivityIndicator, Share, View } from "react-native";

import { api, type DoctorRecord, type LogCategory } from "../../api";
import { Body, Button, Card, ErrorNote, Eyebrow, Heading, Screen, styles, Title, usePhaseTheme } from "../../components/ui";
import { CATEGORIES, PHASES, RECORD_DISCLAIMER } from "../../copy";
import { isCycleAware, useSession, useUser } from "../../session";
import { useRemote } from "../../useRemote";

const hoursMinutes = (minutes: number | null): string =>
  minutes === null ? "--" : `${Math.floor(minutes / 60)}h ${String(Math.round(minutes % 60)).padStart(2, "0")}m`;
const rounded = (value: number | null, unit = ""): string => (value === null ? "--" : `${Math.round(value).toLocaleString("en-US")}${unit}`);

export default function Record(): ReactNode {
  const user = useUser();
  const { signOut } = useSession();
  const theme = usePhaseTheme();
  const load = useCallback(() => api.record(user.id), [user.id]);
  const { data: record, error, loading, reload } = useRemote(load);

  const startOver = async (): Promise<void> => {
    await signOut();
    router.replace("/onboarding");
  };

  return (
    <Screen>
      <Heading
        eyebrow="Lifestyle record"
        title="The story your doctor never gets."
        sub={`How you sleep, move, eat, stress, and feel${isCycleAware(user) ? ", plus your cycle" : ""}. Ready to bring to your appointment.`}
      />
      {loading && !record ? <ActivityIndicator color={theme.accent} /> : null}
      <ErrorNote error={error} />
      {error ? <Button kind="ghost" label="Try again" onPress={reload} /> : null}
      {record ? <Summary record={record} /> : null}
      {record ? <Button label="Share with my doctor" onPress={() => Share.share({ message: asText(record) })} /> : null}
      <Button kind="ghost" label="Start over" onPress={startOver} />
    </Screen>
  );
}

function Summary({ record }: { record: DoctorRecord }): ReactNode {
  const theme = usePhaseTheme();
  const { lifestyle, self_reports: reports, cycle, patient } = record;
  const tiles: readonly [string, string][] = [
    [hoursMinutes(lifestyle.sleep_min), "average sleep"],
    [rounded(lifestyle.hrv_ms, " ms"), "average HRV"],
    [rounded(lifestyle.steps), "average daily steps"],
    [rounded(lifestyle.resting_hr_bpm, " bpm"), "resting heart rate"],
  ];
  const conditions = patient.conditions.filter((condition) => condition !== "None");

  return (
    <Card>
      <Eyebrow>Patient-provided summary</Eyebrow>
      <Title>{`${patient.name}, ${patient.age}`}</Title>
      <Body muted style={{ fontSize: 13 }}>
        {conditions.length ? `Managing: ${conditions.join(", ")}` : "No conditions reported"}
        {record.first_day && record.last_day ? ` · ${record.first_day} to ${record.last_day}` : ""}
      </Body>

      <Title level="h3">{`Last ${lifestyle.window_days} days`}</Title>
      <View style={styles.wrap}>
        {tiles.map(([value, label]) => (
          <View key={label} style={{ width: "48%", padding: 12, borderRadius: 14, backgroundColor: theme.surface2 }}>
            <Title level="h3">{value}</Title>
            <Body muted style={{ fontSize: 12 }}>
              {label}
            </Body>
          </View>
        ))}
      </View>

      <Title level="h3">Self-reported</Title>
      <Body>
        {(Object.entries(reports.counts) as [LogCategory, number][]).map(([category, count]) => `${CATEGORIES[category].label} ${count}`).join(" · ") ||
          "No entries yet."}
      </Body>

      {record.habits.length ? <Title level="h3">Habit consistency</Title> : null}
      {record.habits.map((habit) => {
        const latest = habit.weeks.at(-1);
        return <Body key={habit.habit_id}>{`${habit.title}: ${latest ? `${latest.days_checked} of ${latest.days_possible} days this week` : "new"}`}</Body>;
      })}

      {cycle ? (
        <>
          <Title level="h3">By cycle phase</Title>
          {cycle.by_phase.map((stats) => (
            <View key={stats.phase} style={[styles.row, { justifyContent: "space-between" }]}>
              <Body style={{ color: theme.phase[stats.phase], fontWeight: "700" }}>{PHASES[stats.phase].label}</Body>
              <Body muted>{`${hoursMinutes(stats.sleep_min)} sleep · HRV ${rounded(stats.hrv_ms)}`}</Body>
            </View>
          ))}
          {cycle.pre_period_sleep.is_notable && cycle.pre_period_sleep.drop_min !== null ? (
            <Body>{`You sleep about ${Math.round(cycle.pre_period_sleep.drop_min)} minutes less in the ${cycle.pre_period_sleep.window_days} days before your period.`}</Body>
          ) : null}
        </>
      ) : null}

      <Body muted style={{ fontSize: 13 }}>
        {record.note}
      </Body>
      <Body muted style={{ fontSize: 11 }}>
        {RECORD_DISCLAIMER}
      </Body>
    </Card>
  );
}

function asText(record: DoctorRecord): string {
  const { patient, lifestyle } = record;
  return [
    `HerLife lifestyle record for ${patient.name}, ${patient.age}`,
    `Last ${lifestyle.window_days} days: sleep ${hoursMinutes(lifestyle.sleep_min)}, HRV ${rounded(lifestyle.hrv_ms, " ms")}, steps ${rounded(lifestyle.steps)}, resting heart rate ${rounded(lifestyle.resting_hr_bpm, " bpm")}.`,
    ...record.habits.map((habit) => `Habit: ${habit.title}`),
    record.note,
    RECORD_DISCLAIMER,
  ].join("\n");
}
