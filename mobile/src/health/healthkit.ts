/**
 * HealthKit seam. Apple Health is the reason Bloom goes native: the web app can only
 * read Oura through OAuth, while on iPhone most women already have sleep, steps, heart
 * rate, and often cycle data sitting in HealthKit.
 *
 * Contract: read here, map to the canonical shapes, and post them to the API. A HealthKit
 * field never reaches a screen directly, the same rule CLAUDE.md sets for Oura.
 */

export type HealthMetric =
  | "sleepAnalysis"
  | "stepCount"
  | "heartRateVariabilitySDNN"
  | "restingHeartRate"
  | "menstrualFlow"
  | "basalBodyTemperature";

export interface SleepSample {
  start: Date;
  end: Date;
  stage: "inBed" | "asleep" | "core" | "deep" | "rem" | "awake";
}

export interface DailyQuantity {
  day: string;
  value: number;
}

export interface HealthSource {
  isAvailable(): Promise<boolean>;
  requestRead(metrics: readonly HealthMetric[]): Promise<boolean>;
  sleep(since: Date): Promise<SleepSample[]>;
  dailySteps(since: Date): Promise<DailyQuantity[]>;
  dailyHrv(since: Date): Promise<DailyQuantity[]>;
}

/**
 * TODO(healthkit): implement with react-native-health behind a development build.
 * 1. `npx expo install react-native-health`, add its config plugin to app.json with
 *    NSHealthShareUsageDescription copy, then `npx expo run:ios` (Expo Go cannot load it).
 * 2. Map samples with a new backend adapter (backend/canonical/apple_health_adapter.py,
 *    see the add-wearable skill) and a `POST /users/{id}/health` endpoint, rather than
 *    reshaping data on the phone.
 * 3. Read `menstrualFlow` only to prefill the period log; Bloom's own log stays the source
 *    of cycle day and phase.
 */
export const healthKit: HealthSource = {
  isAvailable: async () => false,
  requestRead: async () => false,
  sleep: async () => [],
  dailySteps: async () => [],
  dailyHrv: async () => [],
};
