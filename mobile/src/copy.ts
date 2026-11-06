/** User-facing copy reused verbatim from web/index.html. American English, no em dashes. */
import type { CyclePhase, GymAccess, LifeStage, LogCategory } from "./api";

export interface Goal {
  title: string;
  sub: string;
}

export const GOALS: readonly Goal[] = [
  { title: "Sleep deeper", sub: "Fall asleep easier, wake rested" },
  { title: "Steady energy", sub: "No 3 pm crash" },
  { title: "Ease PMS", sub: "Fewer cramps, headaches, mood dips" },
  { title: "Balance hormones", sub: "PCOS, irregular cycles" },
  { title: "Get stronger", sub: "Build muscle with my cycle" },
  { title: "Eat for my cycle", sub: "Meals that match my phase" },
  { title: "Calm my stress", sub: "Recover from busy weeks" },
  { title: "Plan a pregnancy", sub: "Understand my fertile window" },
  { title: "Happier gut", sub: "Less bloating, more regular" },
  { title: "Heart health", sub: "Blood pressure, cholesterol, cardio" },
  { title: "Recover from burnout", sub: "Rebuild energy and boundaries" },
  { title: "Move every day", sub: "Even on busy days" },
];

export const LIFE_STAGES: readonly (readonly [LifeStage, string])[] = [
  ["cycling", "Regular periods"],
  ["irregular", "Irregular periods"],
  ["hormonal_birth_control", "On hormonal birth control"],
  ["pregnant_postpartum", "Pregnant or postpartum"],
  ["perimenopause_menopause", "Perimenopause or menopause"],
  ["prefer_not", "Prefer not to say"],
];

export const GYM_ACCESS: readonly (readonly [GymAccess, string])[] = [
  ["gym", "Gym access"],
  ["home", "At home"],
  ["none", "Just walking"],
];

export const PHASES: Record<CyclePhase, { label: string; energy: string }> = {
  menstrual: { label: "Menstrual", energy: "Lowest energy of the month. Iron and warmth help." },
  follicular: { label: "Follicular", energy: "Energy and mood climb as estrogen rises." },
  ovulatory: { label: "Ovulatory", energy: "Peak energy, confidence, and social drive." },
  luteal: { label: "Luteal", energy: "Energy tapers. Cravings and sleep disruption can show up late." },
};

/** Each log category borrows a phase color, as in the web app's CATEGORIES table. */
export const CATEGORIES: Record<LogCategory, { label: string; tone: CyclePhase | "warn" }> = {
  sleep: { label: "Sleep", tone: "luteal" },
  movement: { label: "Movement", tone: "follicular" },
  nutrition: { label: "Nutrition", tone: "ovulatory" },
  mood: { label: "Mood", tone: "menstrual" },
  symptoms: { label: "Symptoms", tone: "warn" },
};

export const RECORD_DISCLAIMER =
  "Self-reported and wearable data. A lifestyle record to support a conversation with a clinician, not a diagnosis.";
