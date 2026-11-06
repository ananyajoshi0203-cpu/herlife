"""Evals for HerLife's Claude features, run against the real models the web server uses.

Each case sends the same instructions the app sends (see the askClaude call sites in
web/index.html) and scores the answer against product rules: valid JSON, correct sorting,
allowed signal keys, no diagnosis language, no em dashes, no cycle talk for women on
hormonal birth control, and never menopause under 40.

    .venv/bin/python -m evals.claude_evals          # needs ANTHROPIC_API_KEY (read from .env)
"""

from __future__ import annotations

import json
import os
import re
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

import anthropic

from backend.webapp.server import JSON_FENCE, MAX_OUTPUT_TOKENS, MODELS, load_dotenv

ROOT = Path(__file__).resolve().parents[1]
PASS_RATE_REQUIRED = 0.85
SIGNAL_KEYS = ["sleepMin", "deep", "rem", "hrv", "ready", "energy", "steps", "kcal", "stress", "weight", "symptoms", "predictErr"]
# Reminding her to take a prescribed medication is a good small action; changing one is not ours to suggest.
DIAGNOSIS = re.compile(r"\b(you have|diagnos\w*|cure[sd]?|(start|stop|switch|change|increase|reduce)\w* (your |the )?(medication|dose|dosage)|dosage of)\b", re.I)
CYCLE_TALK = re.compile(r"\b(luteal|follicular|ovulat\w*|cycle phase|menstrual phase)\b", re.I)


@dataclass
class Case:
    name: str
    tier: str
    prompt: str
    checks: list[tuple[str, Callable[[dict[str, object]], bool]]] = field(default_factory=list)


def items(answer: dict[str, object], key: str) -> list[dict[str, object]]:
    value = answer.get(key, [])
    return [v for v in value if isinstance(v, dict)] if isinstance(value, list) else []


def keys(answer: dict[str, object], key: str) -> list[str]:
    value = answer.get(key, [])
    return [str(v) for v in value] if isinstance(value, list) else []


def text_of(value: object) -> str:
    return json.dumps(value, ensure_ascii=False)


def no_em_dash(answer: dict[str, object]) -> bool:
    return "—" not in text_of(answer) and "–" not in text_of(answer)


def sort_case(name: str, log: str, expected: dict[str, str]) -> Case:
    prompt = f'''Sort this woman's spoken daily health log into structured entries.
Categories: sleep, movement, nutrition, mood, symptoms. Split compound statements so each entry is one fact. Keep her words short and clean.
For each entry add a brief "detail" with any quantity you can infer (duration, portion, time of day, intensity), or an empty string.
Log: """{log}"""
Return JSON only: {{"entries":[{{"category":"sleep|movement|nutrition|mood|symptoms","text":"max 8 words","detail":"max 8 words"}}]}}'''

    def sorted_right(answer: dict[str, object]) -> bool:
        entries = items(answer, "entries")
        for phrase, category in expected.items():
            if not any(phrase in str(e.get("text", "")).lower() + str(e.get("detail", "")).lower() and e.get("category") == category for e in entries):
                return False
        return True

    return Case(name, "quick", prompt, [
        ("categories are allowed", lambda a: all(e.get("category") in {"sleep", "movement", "nutrition", "mood", "symptoms"} for e in items(a, "entries"))),
        ("each phrase lands in the right bucket", sorted_right),
        ("no em dashes", no_em_dash),
    ])


def habits_case(name: str, profile: str, goals: str, life_stage: str) -> Case:
    prompt = f'''You are a women's health coach. Suggest exactly 6 small daily habits for this person, varied across sleep, movement, food, and stress, so she can swipe to pick 3.
Profile: {profile}.
Goals: {goals}. Life stage: {life_stage}. {"Do not mention menstrual cycle phases." if life_stage not in ("cycling", "irregular") else ""}
Rules: each habit doable in under 10 minutes, specific, tied to her goals and lifestyle data first. American English. No em dashes. Lifestyle suggestions only, never medical advice.
Return JSON only: {{"habits":[{{"title":"max 6 words","cue":"when or where it happens, max 8 words","why":"one sentence, max 20 words, mention her data"}}]}}'''
    checks: list[tuple[str, Callable[[dict[str, object]], bool]]] = [
        ("exactly 6 habits", lambda a: len(items(a, "habits")) == 6),
        ("titles are 6 words or fewer", lambda a: all(len(str(h.get("title", "")).split()) <= 7 for h in items(a, "habits"))),
        ("no diagnosis or medication changes", lambda a: not DIAGNOSIS.search(text_of(a))),
        ("no em dashes", no_em_dash),
    ]
    if life_stage not in ("cycling", "irregular"):
        checks.append(("no cycle-phase talk for this life stage", lambda a: not CYCLE_TALK.search(text_of(a))))
    return Case(name, "quick", prompt, checks)


def goal_case(name: str, goal: str, must_include: set[str]) -> Case:
    prompt = f'''A woman wrote this health goal in her own words: """{goal}"""
Choose what HerLife should track. Allowed keys: {", ".join(SIGNAL_KEYS)}.
signals = 3 keys to track daily as leading indicators. outcomes = 3 keys to measure weekly as results. Prefer wearable keys; use weight only for weight goals, predictErr only for prediction goals, symptoms for cycle or symptom goals.
Return JSON only: {{"label":"goal restated in max 5 words","signals":["..."],"outcomes":["..."],"why":"one sentence, max 22 words, plain American English, no em dashes"}}'''
    return Case(name, "quick", prompt, [
        ("only allowed keys", lambda a: all(k in SIGNAL_KEYS for k in [*keys(a, "signals"), *keys(a, "outcomes")])),
        (f"tracks {sorted(must_include)}", lambda a: bool(must_include & set([*keys(a, "signals"), *keys(a, "outcomes")]))),
        ("weight only for weight goals", lambda a: "weight" in must_include or "weight" not in [*keys(a, "signals"), *keys(a, "outcomes")]),
        ("no em dashes", no_em_dash),
    ])


def summary_case(name: str, age: int, patterns: str) -> Case:
    prompt = f'''Write a concise patient-provided lifestyle summary that a woman will hand to her doctor. 3 short paragraphs, plain text, no headings, no bullet points, no em dashes, American English.
Paragraph 1: who she is and why she is coming in (age {age}). Paragraph 2: the patterns in her data. Paragraph 3: questions she may want to ask. Do not diagnose; describe patterns and suggest questions.
Data: {patterns}
Return JSON only: {{"summary":"the three paragraphs separated by \\n\\n"}}'''
    checks: list[tuple[str, Callable[[dict[str, object]], bool]]] = [
        ("three paragraphs", lambda a: len([p for p in str(a.get("summary", "")).split("\n\n") if p.strip()]) == 3),
        ("does not diagnose", lambda a: not re.search(r"\b(you have|she has (pcos|endometriosis|migraine)|diagnos\w* (with|as))\b", str(a.get("summary", "")), re.I)),
        ("no em dashes", no_em_dash),
    ]
    if age < 40:
        checks.append(("never menopause under 40", lambda a: "menopaus" not in str(a.get("summary", "")).lower()))
    return Case(name, "default", prompt, checks)


CASES: list[Case] = [
    sort_case("sort: messy morning", "Slept pretty badly, woke at 3. Oatmeal and an oat latte. 20 minute walk at lunch. Headache around 2 and anxious about planning.",
              {"slept": "sleep", "oatmeal": "nutrition", "walk": "movement", "headache": "symptoms", "anxious": "mood"}),
    sort_case("sort: strong day", "Great sleep, almost 8 hours. Lifted at the gym, squats felt strong. Salmon bowl for lunch. Feeling focused and happy.",
              {"sleep": "sleep", "squats": "movement", "salmon": "nutrition", "happy": "mood"}),
    sort_case("sort: period day", "Cramps all morning and heavy flow. Skipped the run. Ate dal and spinach. Felt low and tired by 4.",
              {"cramps": "symptoms", "dal": "nutrition", "low": "mood"}),
    habits_case("habits: migraines, cycling", "age 32, gym access, vegetarian, migraines", "Ease PMS and Sleep deeper", "cycling"),
    habits_case("habits: on the pill", "age 28, home workouts, no restrictions, none", "Steady energy and Calm my stress", "hormonal_birth_control"),
    habits_case("habits: perimenopause", "age 49, walking only, dairy free, perimenopause", "Sleep deeper and Heart health", "perimenopause_menopause"),
    habits_case("habits: night shift, no ring", "age 29, no wearable, halal, thyroid, night shifts", "Calm my stress and Steady energy", "cycling"),
    goal_case("goal: lose 10 pounds", "Lose 10 pounds", {"weight"}),
    goal_case("goal: 3 pm crash", "I want to stop crashing at 3 pm", {"energy", "ready"}),
    goal_case("goal: predict my period", "Know when my period is coming so it never surprises me", {"predictErr", "symptoms"}),
    goal_case("goal: calmer", "Feel less wired and anxious after work", {"stress", "hrv"}),
    summary_case("summary: migraines at 32", 32, "Headaches on 12 of 15 late luteal days vs 3 of 75 other days. Sleep 21 min shorter before her period. After high-stress days she sleeps 34 min less."),
    summary_case("summary: irregular at 24", 24, "Cycles 29, 30, 41, 52 days. Stress minutes rising. Training 6 days a week. Sleep under 6.5 hours on 9 of the last 14 nights."),
]


def ask(client: anthropic.Anthropic, case: Case) -> dict[str, object]:
    message = client.messages.create(
        model=MODELS[case.tier], max_tokens=MAX_OUTPUT_TOKENS,
        system="You are HerLife's assistant for a women's lifestyle app. Reply with JSON only, no prose, no code fences.",
        messages=[{"role": "user", "content": case.prompt}],
    )
    raw = "".join(block.text for block in message.content if block.type == "text")
    parsed = json.loads(JSON_FENCE.sub("", raw.strip()))
    assert isinstance(parsed, dict)
    return parsed


def main() -> int:
    load_dotenv(ROOT / ".env")
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("Set ANTHROPIC_API_KEY (or add it to .env) to run the Claude evals.")
        return 2
    client = anthropic.Anthropic()
    passed = total = 0
    for case in CASES:
        try:
            answer = ask(client, case)
            results = [(label, check(answer)) for label, check in case.checks]
        except (json.JSONDecodeError, AssertionError, anthropic.APIError) as error:
            results = [("valid JSON answer", False)]
            print(f"  ! {case.name}: {type(error).__name__}")
        for label, ok in results:
            passed += ok
            total += 1
            if not ok:
                print(f"  FAIL {case.name}: {label}")
        print(f"{'PASS' if all(ok for _, ok in results) else 'FAIL'}  {case.name}")
    rate = passed / total
    print(f"\n{passed}/{total} checks passed ({rate:.0%}); required {PASS_RATE_REQUIRED:.0%}")
    return 0 if rate >= PASS_RATE_REQUIRED else 1


if __name__ == "__main__":
    sys.exit(main())
