from __future__ import annotations
import re
from typing import Optional
from ..models.preferences import UserPreferences

GERMAN_NUM = {
    "eins": 1,
    "zwei": 2,
    "drei": 3,
    "vier": 4,
    "fuenf": 5,
    "fünf": 5,
    "sechs": 6,
    "sieben": 7,
    "acht": 8,
    "neun": 9,
    "zehn": 10,
}
EN_NUM = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
}

CUISINE_SYNONYMS = {
    "italienisch": "italian",
    "chinesisch": "chinese",
    "mexikanisch": "mexican",
    "griechisch": "greek",
    "türkisch": "turkish",
    "tuerkisch": "turkish",
    "französisch": "french",
    "franzoesisch": "french",
    "spanisch": "spanish",
    "indisch": "indian",
    "vietnamesisch": "vietnamese",
    "koreanisch": "korean",
    "japanisch": "japanese",
    "sushi": "sushi",
}
CUISINE_WORDS = set(list(CUISINE_SYNONYMS.values()) + list(CUISINE_SYNONYMS.keys()))

_TIME_RE = re.compile(
    r"""\b(?P<h>\d{1,2})(?:[:.\s](?P<m>\d{2}))?\s*(?P<ampm>a\.?m\.?|p\.?m\.?|am|pm|aem|pem)?\b""",
    re.IGNORECASE | re.VERBOSE,
)


def _normalize_ampm(s: Optional[str]) -> str:
    if not s:
        return ""
    s = s.lower().replace(" ", "")
    return (
        s.replace("aem", "am")
        .replace("pem", "pm")
        .replace("a.m.", "am")
        .replace("p.m.", "pm")
        .replace("a.m", "am")
        .replace("p.m", "pm")
    )


def _parse_time(text: str) -> Optional[str]:
    m = _TIME_RE.search(text or "")
    if not m:
        return None
    hour = int(m.group("h"))
    minute = m.group("m") or "00"
    ampm = _normalize_ampm(m.group("ampm"))
    if ampm == "pm" and hour < 12:
        hour += 12
    if ampm == "am" and hour == 12:
        hour = 0
    if 0 <= hour <= 23 and minute.isdigit() and len(minute) == 2:
        return f"{hour:02}:{minute}"
    return None


def _parse_guests(text: str) -> Optional[int]:
    t = (text or "").lower()
    for w, n in EN_NUM.items():
        if re.search(rf"\b{re.escape(w)}\b", t):
            return n
    for w, n in GERMAN_NUM.items():
        if re.search(rf"\b{re.escape(w)}\b", t):
            return n
    m = re.search(r"\b(\d{1,2})\b", t)
    if m:
        try:
            n = int(m.group(1))
            if 1 <= n <= 20:
                return n
        except ValueError:
            pass
    return None


def _normalize_cuisine(token: str) -> str:
    token = token.strip().lower()
    token = CUISINE_SYNONYMS.get(token, token)
    return token.split()[0]


def _maybe_update_basic_prefs(prefs: UserPreferences, text: str) -> None:
    t = (text or "").lower().strip()
    # time
    if not prefs.time:
        tm = _parse_time(t)
        if tm:
            prefs.time = tm
    # guests
    if not prefs.guests:
        g = _parse_guests(t)
        if g is not None:
            prefs.guests = g
    # city (simple heuristic)
    if not prefs.city:
        m = re.search(r"\b(?:in|at)\s+([a-zA-ZÀ-ÿ\-.' ]{2,})$", t, flags=re.I)
        if m:
            prefs.city = m.group(1).strip()
    # cuisine
    if not prefs.cuisine:
        m = re.search(r"\b(" + "|".join(map(re.escape, CUISINE_WORDS)) + r")\b", t)
        if m:
            prefs.cuisine = _normalize_cuisine(m.group(1))
