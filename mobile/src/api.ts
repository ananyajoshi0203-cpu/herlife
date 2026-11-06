/**
 * Typed client for the HerLife FastAPI service (backend/api/app.py).
 * Types mirror backend/api/schemas.py, backend/canonical/models.py, and backend/insights.py.
 * Keep them in step by hand until we generate them from the OpenAPI schema at /openapi.json.
 */

type Uuid = string;
/** `YYYY-MM-DD`, as pydantic serializes `date`. */
type IsoDate = string;
/** ISO 8601 with time, as pydantic serializes `datetime`. */
type IsoDateTime = string;

export type GymAccess = "gym" | "home" | "none";
export type LifeStage =
  | "cycling"
  | "irregular"
  | "hormonal_birth_control"
  | "pregnant_postpartum"
  | "perimenopause_menopause"
  | "prefer_not";
export type LogCategory = "sleep" | "movement" | "nutrition" | "mood" | "symptoms";
export type Flow = "light" | "medium" | "heavy";
export type CyclePhase = "menstrual" | "follicular" | "ovulatory" | "luteal";
export type Source = "oura" | "self_report";

export const CYCLE_AWARE_STAGES: ReadonlySet<LifeStage> = new Set(["cycling", "irregular"]);

export interface UserCreate {
  name: string;
  age: number;
  gym_access: GymAccess;
  diet: string[];
  conditions: string[];
  life_stage: LifeStage;
  goals: [string, string];
}

export interface User extends UserCreate {
  id: Uuid;
  created_at: IsoDateTime;
}

export interface SyncResult {
  user_id: Uuid;
  live: boolean;
  start: IsoDate;
  end: IsoDate;
  sleep: number;
  readiness: number;
  activity: number;
  stress: number;
}

export interface PeriodCreate {
  start_day: IsoDate;
  end_day?: IsoDate | null;
  flow: Flow;
}

export interface PeriodLog extends PeriodCreate {
  end_day: IsoDate | null;
  source: Source;
}

export interface CycleDay {
  day: IsoDate;
  source: Source;
  cycle_day: number;
  phase: CyclePhase;
  is_period: boolean;
  ovulation_confirmed: boolean;
}

export interface CycleView {
  periods: PeriodLog[];
  today: CycleDay | null;
  days: CycleDay[];
}

export interface LogEntry {
  id: Uuid;
  day: IsoDate;
  category: LogCategory;
  text: string;
  detail: string;
}

export interface VoiceLogResult {
  used_ai: boolean;
  entries: LogEntry[];
}

export interface Habit {
  id: Uuid;
  title: string;
  why: string;
  goal: string;
  created_on: IsoDate;
}

export interface HabitSuggestions {
  used_ai: boolean;
  habits: Habit[];
}

export interface HabitCheck {
  habit_id: Uuid;
  day: IsoDate;
}

export interface WeekConsistency {
  iso_week: string;
  week_start: IsoDate;
  days_checked: number;
  days_possible: number;
  rate: number | null;
}

export interface HabitConsistency {
  habit_id: Uuid;
  title: string;
  weeks: WeekConsistency[];
}

export interface CycleContext {
  cycle_day: number;
  phase: CyclePhase;
  ovulation_confirmed: boolean;
  note: string;
}

export interface TodayPlan {
  day: IsoDate;
  sleep: string;
  move: string;
  eat: string;
  mind: string;
  ease_off: boolean;
  reasons: string[];
  cycle: CycleContext | null;
}

export interface LifestyleAverages {
  window_days: number;
  sleep_min: number | null;
  sleep_efficiency_pct: number | null;
  hrv_ms: number | null;
  resting_hr_bpm: number | null;
  readiness_score: number | null;
  steps: number | null;
  active_min: number | null;
  stress_high_min: number | null;
}

export interface SelfReportSummary {
  counts: Partial<Record<LogCategory, number>>;
  recent: LogEntry[];
}

export interface PhaseStats {
  phase: CyclePhase;
  nights: number;
  sleep_min: number | null;
  hrv_ms: number | null;
  readiness_score: number | null;
  stress_high_min: number | null;
}

export interface PrePeriodSleep {
  window_days: number;
  periods_counted: number;
  pre_period_sleep_min: number | null;
  other_nights_sleep_min: number | null;
  /** Positive means she sleeps less in the days before her period. */
  drop_min: number | null;
  is_notable: boolean;
}

export interface CycleRegularity {
  logged_period_starts: IsoDate[];
  cycle_lengths_days: number[];
  mean_length_days: number | null;
  length_spread_days: number | null;
  is_regular: boolean | null;
}

export interface OvulationConfirmation {
  completed_cycles: number;
  confirmed_cycles: number;
  confirmed_rate: number | null;
}

/**
 * The cycle half of `backend.insights.RecordInsights`. Its `lifestyle` block (weekly
 * slopes, weekday sleep, heavy-day effect) is left untyped until a screen reads it.
 */
export interface RecordInsights {
  generated_at: IsoDateTime;
  first_day: IsoDate | null;
  last_day: IsoDate | null;
  lifestyle: unknown;
  by_phase: PhaseStats[];
  pre_period_sleep: PrePeriodSleep;
  regularity: CycleRegularity;
  ovulation: OvulationConfirmation;
}

export interface DoctorRecord {
  generated_at: IsoDateTime;
  patient: User;
  first_day: IsoDate | null;
  last_day: IsoDate | null;
  lifestyle: LifestyleAverages;
  self_reports: SelfReportSummary;
  habits: HabitConsistency[];
  cycle: RecordInsights | null;
  note: string;
}

export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly detail: string,
  ) {
    super(`HerLife API ${status}: ${detail}`);
  }
}

const BASE_URL = (process.env.EXPO_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/+$/, "");

async function request<T>(method: "GET" | "POST", path: string, body?: unknown): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    method,
    headers: body === undefined ? undefined : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!response.ok) throw new ApiError(response.status, await response.text());
  return (await response.json()) as T;
}

const userPath = (userId: Uuid): string => `/users/${encodeURIComponent(userId)}`;

export const api = {
  createUser: (profile: UserCreate) => request<User>("POST", "/users", profile),
  sync: (userId: Uuid) => request<SyncResult>("POST", `${userPath(userId)}/sync`),
  logPeriod: (userId: Uuid, period: PeriodCreate) => request<PeriodLog>("POST", `${userPath(userId)}/periods`, period),
  cycle: (userId: Uuid) => request<CycleView>("GET", `${userPath(userId)}/cycle`),
  planToday: (userId: Uuid) => request<TodayPlan>("GET", `${userPath(userId)}/plan/today`),
  suggestHabits: (userId: Uuid) => request<HabitSuggestions>("POST", `${userPath(userId)}/habits/suggest`),
  checkHabit: (userId: Uuid, habitId: Uuid, day?: IsoDate) =>
    request<HabitCheck>("POST", `${userPath(userId)}/habits/${encodeURIComponent(habitId)}/checks`, { day: day ?? null }),
  habitConsistency: (userId: Uuid) => request<HabitConsistency[]>("GET", `${userPath(userId)}/habits/consistency`),
  logVoice: (userId: Uuid, text: string) => request<VoiceLogResult>("POST", `${userPath(userId)}/logs/voice`, { text }),
  record: (userId: Uuid) => request<DoctorRecord>("GET", `${userPath(userId)}/record`),
};
