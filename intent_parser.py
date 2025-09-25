# intent_parser.py
from __future__ import annotations

import re
from datetime import datetime, timedelta, date
from typing import TypedDict, Optional, Tuple


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

    # Guests (int)
    m: Optional[re.Match[str]] = re.search(r"(\d+)\s*(personen|gäste|leute)", t)
    if m:
        slots["guests"] = int(m.group(1))

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
