"""Age band and seasonal guidance, ported from AGE_BANDS and SEASONS in web/index.html.

Both are lifestyle content keyed off facts we already have (her age, today's
date), so they live here as data rather than in the Claude prompts. Sources are
in docs/RESEARCH.md, section 3 and the seasonal addendum.
"""

from __future__ import annotations

from datetime import date
from enum import StrEnum

from pydantic import BaseModel


class AgeBand(BaseModel):
    label: str
    focus: list[str]
    tip: str


AGE_BANDS: tuple[tuple[int, AgeBand], ...] = (
    (
        25,
        AgeBand(
            label="18 to 25",
            focus=["Iron and B12", "Bone building years", "Sleep regularity"],
            tip="Your bones are still gaining density. Strength work and calcium now pay off for decades.",
        ),
    ),
    (
        34,
        AgeBand(
            label="26 to 34",
            focus=["Strength training", "Iron", "Stress and sleep"],
            tip="Muscle and bone peak around now. Two strength sessions a week protects both.",
        ),
    ),
    (
        44,
        AgeBand(
            label="35 to 44",
            focus=["Protein and muscle", "Sleep quality", "Cycle changes"],
            tip="Muscle loss starts quietly in your late 30s. Protein at each meal and lifting slow it.",
        ),
    ),
    (
        55,
        AgeBand(
            label="45 to 55",
            focus=["Sleep and night sweats", "Heart health", "Bone density"],
            tip="Many women enter the menopause transition here. Sleep, strength, and heart health matter most.",
        ),
    ),
)
OLDEST_BAND = AgeBand(
    label="56 and up",
    focus=["Bone density", "Heart health", "Balance and strength"],
    tip="After menopause, heart and bone risk rise. Daily walking and strength keep you independent.",
)


def age_band_for(age: int) -> AgeBand:
    return next((band for oldest, band in AGE_BANDS if age <= oldest), OLDEST_BAND)


class SeasonName(StrEnum):
    WINTER = "winter"
    SPRING = "spring"
    SUMMER = "summer"
    FALL = "fall"


class SeasonRec(BaseModel):
    title: str
    body: str
    source: str


class Season(BaseModel):
    name: SeasonName
    label: str
    recs: list[SeasonRec]


FLU_SLEEP = SeasonRec(
    title="Protect 7 hours of sleep",
    body="People sleeping under 6 hours were about 4 times more likely to catch a cold after exposure.",
    source="Prather et al., SLEEP, 2015",
)
SEASONS: dict[SeasonName, Season] = {
    SeasonName.WINTER: Season(
        name=SeasonName.WINTER,
        label="Winter and peak flu season",
        recs=[
            SeasonRec(
                title="Get your flu shot if you haven't",
                body="The CDC recommends a yearly flu vaccine for everyone 6 months and older.",
                source="CDC, Seasonal Flu Vaccines",
            ),
            FLU_SLEEP,
            SeasonRec(
                title="Morning daylight, even when it's gray",
                body="Shorter days can lower mood and energy. Bright morning light is a first-line approach "
                "for winter blues.",
                source="NIMH, Seasonal Affective Disorder",
            ),
        ],
    ),
    SeasonName.SPRING: Season(
        name=SeasonName.SPRING,
        label="Spring and allergy season",
        recs=[
            SeasonRec(
                title="Track allergy days in your log",
                body="Pollen peaks can disrupt sleep and look like low energy days.",
                source="AAAAI, Seasonal Allergies",
            ),
            SeasonRec(
                title="Use the longer evenings",
                body="Adults need 150 minutes of moderate activity a week. Light evenings make an after-dinner "
                "walk easy.",
                source="HHS Physical Activity Guidelines, 2nd ed.",
            ),
        ],
    ),
    SeasonName.SUMMER: Season(
        name=SeasonName.SUMMER,
        label="Summer heat",
        recs=[
            SeasonRec(
                title="Hydrate ahead of the heat",
                body="Drink water before you feel thirsty on hot days and plan workouts for the cooler part "
                "of the day.",
                source="CDC, Heat and Your Health",
            ),
            SeasonRec(
                title="Keep your bedroom cool",
                body="Heat at night cuts deep sleep. A cooler, darker room helps.",
                source="Okamoto-Mizuno and Mizuno, J Physiol Anthropol, 2012",
            ),
        ],
    ),
    SeasonName.FALL: Season(
        name=SeasonName.FALL,
        label="Fall and early flu season",
        recs=[
            SeasonRec(
                title="Book your flu shot now",
                body="The CDC suggests getting vaccinated by the end of October, before flu spreads widely.",
                source="CDC, Seasonal Flu Vaccines",
            ),
            FLU_SLEEP,
            SeasonRec(
                title="Ask about vitamin D as days shorten",
                body="Less sun means less vitamin D made in the skin. Food sources and a blood test are worth "
                "a conversation.",
                source="NIH Office of Dietary Supplements, Vitamin D",
            ),
        ],
    ),
}
SEASON_BY_MONTH: dict[int, SeasonName] = {
    12: SeasonName.WINTER,
    1: SeasonName.WINTER,
    2: SeasonName.WINTER,
    3: SeasonName.SPRING,
    4: SeasonName.SPRING,
    5: SeasonName.SPRING,
    6: SeasonName.SUMMER,
    7: SeasonName.SUMMER,
    8: SeasonName.SUMMER,
    9: SeasonName.FALL,
    10: SeasonName.FALL,
    11: SeasonName.FALL,
}


def season_for(day: date) -> Season:
    return SEASONS[SEASON_BY_MONTH[day.month]]
