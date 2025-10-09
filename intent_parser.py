# intent_parser.py
from __future__ import annotations

import re
from datetime import datetime, timedelta, date
from typing import TypedDict, Tuple

NUMBER_WORDS = {
    "eins": 1,
    "eine": 1,
    "einem": 1,
    "einen": 1,
    "einer": 1,
    "ein": 1,
    "zwei": 2,
    "drei": 3,
    "vier": 4,
    "fünf": 5,
    "sechs": 6,
    "sieben": 7,
    "acht": 8,
    "neun": 9,
    "zehn": 10,
    "elf": 11,
    "zwölf": 12,
}

GREETING_WORDS = [
    "hallo",
    "hey",
    "hi",
    "guten tag",
    "guten morgen",
    "guten abend",
    "servus",
    "moin",
]


def _word_to_int(token: str) -> int | None:
    return NUMBER_WORDS.get(token.strip().lower())


class Slots(TypedDict, total=False):
    guests: int  # Anzahl Personen
    time: str  # "HH:MM"
    date: str  # ISO-Date (YYYY-MM-DD)
    cuisine: str  # italienisch, ...
    accessibility: bool  # True = barrierefrei


CUISINES = [
    "italienisch",
    "chinesisch",
    "japanisch",
    "indisch",
    "vegan",
    "mexikanisch",
    "griechisch",
]


def parse_intent(text: str) -> Tuple[str, Slots]:
    t = text.lower()
    intent = "unknown"
    slots: Slots = {}

    # Intent
    if any(k in t for k in ["buch", "reservier", "tisch"]):
        intent = "booking_request"
    elif any(k in t for k in ["empfehl", "vorschlag", "wo kann ich"]):
        intent = "recommendation_request"

    # greeting
    if any(w in t for w in GREETING_WORDS):
        intent = "greeting"

    # booking / recommendation (nur setzen, wenn nicht bereits greeting)
    if intent == "unknown" and any(k in t for k in ["buch", "reservier", "tisch"]):
        intent = "booking_request"
    elif intent == "unknown" and any(
        k in t for k in ["empfehl", "vorschlag", "wo kann ich"]
    ):
        intent = "recommendation_request"

    # Guests (int)
    m = re.search(r"(?:für\s*)?(\d{1,2})\s*(?:personen|gäste|leute)?", t)
    if m:
        slots["guests"] = int(m.group(1))
    else:
        # word form: "für vier personen", "vier gäste"
        m2 = re.search(r"(?:für\s*)?([a-zäöüß]+)\s*(?:personen|gäste|leute)\b", t)
        if m2:
            n = _word_to_int(m2.group(1))
            if n:
                slots["guests"] = n

    # Time "19 Uhr" / "19:30 Uhr"
    m = re.search(r"\b(\d{1,2})(?::|\.?(\d{2}))?\s*uhr\b", t)
    if m:
        hour = int(m.group(1))
        mins = int(m.group(2)) if m.group(2) else 0
        slots["time"] = f"{hour:02d}:{mins:02d}"

    # Date (heute/morgen)
    today: date = datetime.now().date()
    if "heute" in t:
        slots["date"] = today.isoformat()
    elif "morgen" in t:
        slots["date"] = (today + timedelta(days=1)).isoformat()

    # Cuisine
    for c in CUISINES:
        if c in t:
            slots["cuisine"] = c
            break

    # Accessibility
    if any(k in t for k in ["rollstuhl", "barrierefrei", "stufenfrei", "rampe"]):
        slots["accessibility"] = True

    return intent, slots


if __name__ == "__main__":
    s = "Buche einen Tisch für 4 Personen um 19:30 Uhr in einem italienischen Restaurant, barrierefrei."
    i, sl = parse_intent(s)
    print("Intent:", i)
    print("Slots:", sl)
