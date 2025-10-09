from __future__ import annotations
import re
from typing import Optional
from ..models.preferences import UserPreferences

# Friendly questions (ask one at a time)
ACCESS_QUESTIONS = {
    "wheelchair": "Do you need wheelchair access?",
    "step_free": "Should I only show step-free entrances?",
    "restroom": "Do you need an accessible restroom?",
}


def next_missing_access_slot(prefs: UserPreferences) -> Optional[str]:
    acc = prefs.accessibility
    if acc.wheelchair is None:
        return "wheelchair"
    if acc.step_free is None:
        return "step_free"
    if acc.restroom is None:
        return "restroom"
    return None


def maybe_ask_accessibility(prefs: UserPreferences) -> Optional[str]:
    acc = prefs.accessibility
    if acc.wheelchair is None:
        return ACCESS_QUESTIONS["wheelchair"]
    if acc.step_free is None:
        return ACCESS_QUESTIONS["step_free"]
    if acc.restroom is None:
        return ACCESS_QUESTIONS["restroom"]
    return None


# --- Robust keyword detection for DE/EN, incl. Whisper quirks ---------------
_PAT_WHEELCHAIR = re.compile(
    r"(rollstuhl(?:\s*|-)?zugang|rollstuhl|barriere\s*frei|barrierefrei|barrierefreiheit|wheelchair)",
    re.IGNORECASE,
)
_PAT_STEPFREE = re.compile(
    r"(stufenlos|ohne\s*stufen|rampe|ebenerdig|step\s*free)", re.IGNORECASE
)
_PAT_RESTROOM = re.compile(
    r"(barrierefrei(?:es|er)?\s*wc|rollstuhl\s*wc|behinderten(?:\s*|-)?wc|behinderten(?:\s*|-)?toilette|accessible\s*restroom)",
    re.IGNORECASE,
)
_NEG = re.compile(r"\b(kein|keine|nicht|no|without)\b", re.IGNORECASE)


def update_accessibility_from_text(prefs: UserPreferences, user_text: str) -> None:
    """
    Update accessibility flags from a free-text utterance.
    Only sets a flag if it is currently None (unknown).
    """
    t = (user_text or "").lower().strip()

    # fix common Whisper split "zu gang" - "zugang"
    t_norm = t.replace("zu gang", "zugang")

    def set_true_if_unknown(attr: str, pattern: re.Pattern, text: str):
        if getattr(prefs.accessibility, attr) is None:
            if pattern.search(text) and not _NEG.search(text):
                setattr(prefs.accessibility, attr, True)

    set_true_if_unknown("wheelchair", _PAT_WHEELCHAIR, t_norm)
    set_true_if_unknown("step_free", _PAT_STEPFREE, t_norm)
    set_true_if_unknown("restroom", _PAT_RESTROOM, t_norm)


_YES = {"yes", "y", "yeah", "sure", "correct", "ja", "j", "genau", "stimmt"}
_NO = {"no", "n", "nein", "nope", "nicht", "kein"}
_NEUTRAL = {
    "egal",
    "doesnt matter",
    "doesn't matter",
    "dont care",
    "don't care",
    "egal ist",
    "egal danke",
}


def classify_yes_no(text: str) -> Optional[bool]:
    t = (text or "").strip().lower()
    if t in _YES:
        return True
    if t in _NO:
        return False
    if t in _NEUTRAL:
        return False  # treat "egal" as no strict filter
    # also handle leading words like "yes, please" / "ja bitte"
    if t.startswith(("yes", "ja")):
        return True
    if t.startswith(("no", "nein")):
        return False
    return None
