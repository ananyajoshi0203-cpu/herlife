"""Claude calls for the API, each with a deterministic fallback.

Every call asks for JSON matching a pydantic model through structured outputs
(`messages.parse` with `output_format`). When ANTHROPIC_API_KEY is missing, the
call fails, Claude declines, or the output does not validate, the caller gets
the rule-based answer instead, so no endpoint dead-ends on the model.
"""

from __future__ import annotations

import logging
import os
import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import timedelta

import anthropic
from pydantic import BaseModel, ValidationError

from backend.api.schemas import GymAccess, LifestyleAverages, LogCategory, UserCreate

MODEL = "claude-sonnet-5-5"
FALLBACK_BETA = "server-side-fallback-2026-07-01"
TIMEOUT = timedelta(seconds=30)
MAX_TOKENS = 4000
HABIT_COUNT = 3
SHORT_SLEEP_MIN = 420

logger = logging.getLogger(__name__)


class VoiceEntry(BaseModel):
    category: LogCategory
    text: str
    detail: str


class VoiceSort(BaseModel):
    entries: list[VoiceEntry]


class HabitIdea(BaseModel):
    title: str
    why: str
    goal: str


class HabitIdeas(BaseModel):
    habits: list[HabitIdea]


@dataclass(frozen=True)
class Answer[T]:
    value: T
    used_ai: bool


def ask_structured[T: BaseModel](system: str, prompt: str, schema: type[T]) -> T | None:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return None
    client = anthropic.Anthropic(timeout=TIMEOUT.total_seconds(), max_retries=1)
    try:
        response = client.beta.messages.parse(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=system,
            messages=[{"role": "user", "content": prompt}],
            output_format=schema,
            output_config={"effort": "low"},
            betas=[FALLBACK_BETA],
            fallbacks="default",
        )
    except anthropic.APIStatusError as error:
        logger.warning("Claude returned %s; using the fallback", error.status_code)
        return None
    except anthropic.APIConnectionError:
        logger.warning("Claude unreachable; using the fallback")
        return None
    except ValidationError:
        logger.warning("Claude output did not match %s; using the fallback", schema.__name__)
        return None
    if response.stop_reason == "refusal":
        return None
    return response.parsed_output


VOICE_SYSTEM = """You sort a woman's spoken daily log for Bloom, a lifestyle record she shares with her doctor.
Split the transcript into separate facts. Give each one a category: sleep, movement, nutrition, mood, or symptoms.
`text` is the fact in her own words, lightly cleaned up. `detail` is the concrete specifics (amounts, times,
durations, intensity) or an empty string. Never add facts she did not say, never diagnose, and never use em dashes."""

CATEGORY_KEYWORDS: dict[LogCategory, tuple[str, ...]] = {
    LogCategory.SYMPTOMS: (
        "cramp",
        "headache",
        "migraine",
        "bloat",
        "nause",
        "pain",
        "ache",
        "sore",
        "acne",
        "spotting",
        "dizzy",
        "hot flash",
        "night sweat",
        "tender",
    ),
    LogCategory.SLEEP: ("slept", "sleep", "nap", "insomnia", "woke", "bed", "tired", "rested"),
    LogCategory.MOVEMENT: (
        "walk",
        "run",
        "ran",
        "gym",
        "yoga",
        "workout",
        "lift",
        "swim",
        "bike",
        "pilates",
        "steps",
        "stretch",
    ),
    LogCategory.NUTRITION: (
        "ate",
        "eat",
        "breakfast",
        "lunch",
        "dinner",
        "snack",
        "coffee",
        "water",
        "drank",
        "sugar",
        "protein",
        "meal",
        "craving",
        "alcohol",
        "wine",
    ),
    LogCategory.MOOD: ("happy", "sad", "anxious", "stress", "irritable", "calm", "angry", "mood", "low", "great"),
}
SENTENCE_BREAK = re.compile(r"[.!?;\n]+|,\s*(?:and\s+)?(?=i\s)|\s+and\s+(?=i\s)", re.IGNORECASE)
AMOUNT = re.compile(
    r"\b\d+(?:\.\d+)?\s*(?:hours?|hrs?|h|minutes?|mins?|k|steps|cups?|glasses?|miles?|km)\b", re.IGNORECASE
)


def categorize(sentence: str) -> LogCategory:
    lowered = sentence.lower()
    return next(
        (
            category
            for category, keywords in CATEGORY_KEYWORDS.items()
            if any(re.search(rf"\b{keyword}", lowered) for keyword in keywords)
        ),
        LogCategory.MOOD,
    )


def sort_voice_log_by_rules(text: str) -> VoiceSort:
    entries: list[VoiceEntry] = []
    for sentence in (part.strip(" ,") for part in SENTENCE_BREAK.split(text)):
        if not sentence:
            continue
        entries.append(
            VoiceEntry(category=categorize(sentence), text=sentence, detail=", ".join(AMOUNT.findall(sentence)))
        )
    return VoiceSort(entries=entries)


def sort_voice_log(text: str) -> Answer[VoiceSort]:
    sorted_log = ask_structured(VOICE_SYSTEM, f"Transcript:\n{text}", VoiceSort)
    if sorted_log and sorted_log.entries:
        return Answer(sorted_log, used_ai=True)
    return Answer(sort_voice_log_by_rules(text), used_ai=False)


HABITS_SYSTEM = f"""You suggest exactly {HABIT_COUNT} small daily habits for a woman using Bloom, a lifestyle app.
Tie every habit to one of her two goals and put that goal, verbatim, in `goal`. Fit them to her gym access, diet,
conditions, and recent wearable numbers. `title` is a short action she can check off today. `why` is one warm
sentence on why it helps her, citing her own data when it is relevant. These are lifestyle suggestions, not
medical advice. American English, no em dashes."""


@dataclass(frozen=True)
class HabitTemplate:
    title: str
    why: str


MOVE_BY_GYM_ACCESS = {
    GymAccess.GYM: HabitTemplate(
        "Two strength sessions at the gym this week", "Strength work protects bone and steadies energy."
    ),
    GymAccess.HOME: HabitTemplate(
        "15 minutes of bodyweight strength at home", "Short strength sessions add up and need no commute."
    ),
    GymAccess.NONE: HabitTemplate(
        "A brisk 20 minute walk", "Walking is the easiest movement to keep, and it lifts mood."
    ),
}

GOAL_HABITS: dict[str, tuple[HabitTemplate, ...]] = {
    "sleep": (
        HabitTemplate("Screens off 30 minutes before bed", "A calmer wind down makes falling asleep easier."),
        HabitTemplate("Same wake time every day, weekends too", "A steady wake time anchors your body clock."),
    ),
    "stress": (
        HabitTemplate(
            "Five slow breaths before lunch", "A short pause midday helps your body shift out of stress mode."
        ),
        HabitTemplate("A 10 minute walk without your phone", "Time outside with no input gives your mind a reset."),
    ),
    "energy": (
        HabitTemplate("Protein with breakfast", "A steadier breakfast helps avoid the midmorning crash."),
        HabitTemplate("Daylight within an hour of waking", "Morning light helps set energy for the whole day."),
    ),
    "nutrition": (
        HabitTemplate("A vegetable at lunch and dinner", "More plants means more fiber and steadier meals."),
        HabitTemplate("A full glass of water with every meal", "Hydration is easy to forget and shows up as fatigue."),
    ),
    "mood": (
        HabitTemplate("Write one line about your day", "Noticing patterns in mood starts with a quick note."),
        HabitTemplate("Message one friend", "Small moments of connection lift mood more than we expect."),
    ),
}
GOAL_ALIASES: dict[str, str] = {
    "sleep": "sleep",
    "rest": "sleep",
    "insomnia": "sleep",
    "stress": "stress",
    "anxiety": "stress",
    "calm": "stress",
    "burnout": "stress",
    "energy": "energy",
    "tired": "energy",
    "fatigue": "energy",
    "eat": "nutrition",
    "nutrition": "nutrition",
    "diet": "nutrition",
    "weight": "nutrition",
    "food": "nutrition",
    "mood": "mood",
    "happy": "mood",
    "mental": "mood",
}
MOVE_WORDS = ("fit", "strong", "strength", "move", "exercise", "active", "muscle", "run")


def templates_for_goal(goal: str, gym_access: GymAccess) -> list[HabitTemplate]:
    lowered = goal.lower()
    if any(word in lowered for word in MOVE_WORDS):
        return [
            MOVE_BY_GYM_ACCESS[gym_access],
            HabitTemplate("Stretch for 5 minutes after waking", "Gentle mobility makes harder movement feel easier."),
        ]
    family = next((family for alias, family in GOAL_ALIASES.items() if alias in lowered), "energy")
    return list(GOAL_HABITS[family])


def interleave[T](first: Sequence[T], second: Sequence[T]) -> list[T]:
    return (
        [item for pair in zip(first, second) for item in pair] + list(first[len(second) :]) + list(second[len(first) :])
    )


def suggest_habits_by_rules(profile: UserCreate, recent: LifestyleAverages) -> HabitIdeas:
    first_goal, second_goal = profile.goals
    pool = interleave(
        [(first_goal, template) for template in templates_for_goal(first_goal, profile.gym_access)],
        [(second_goal, template) for template in templates_for_goal(second_goal, profile.gym_access)],
    )
    if recent.sleep_min is not None and recent.sleep_min < SHORT_SLEEP_MIN:
        hours = round(recent.sleep_min / 60, 1)
        pool.insert(
            0,
            (
                first_goal,
                HabitTemplate(
                    "Lights out 20 minutes earlier",
                    f"You have averaged {hours} hours of sleep lately, and more rest helps everything else.",
                ),
            ),
        )
    ideas: list[HabitIdea] = []
    for goal, template in pool:
        if template.title not in {idea.title for idea in ideas}:
            ideas.append(HabitIdea(title=template.title, why=template.why, goal=goal))
    return HabitIdeas(habits=ideas[:HABIT_COUNT])


def describe(profile: UserCreate, recent: LifestyleAverages) -> str:
    return f"Profile: {profile.model_dump_json(exclude={'name'})}\nRecent averages: {recent.model_dump_json()}"


def suggest_habits(profile: UserCreate, recent: LifestyleAverages) -> Answer[HabitIdeas]:
    ideas = ask_structured(HABITS_SYSTEM, describe(profile, recent), HabitIdeas)
    if ideas and len(ideas.habits) >= HABIT_COUNT and all(idea.goal in profile.goals for idea in ideas.habits):
        return Answer(HabitIdeas(habits=ideas.habits[:HABIT_COUNT]), used_ai=True)
    return Answer(suggest_habits_by_rules(profile, recent), used_ai=False)
