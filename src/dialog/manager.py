from __future__ import annotations

import re
from typing import Optional, Tuple, List, Dict
import pandas as pd

from ..models.preferences import UserPreferences
from ..reco.recommender import filter_and_rank

from .slots import (
    next_missing_access_slot,
    update_accessibility_from_text,
    classify_yes_no,
    ACCESS_QUESTIONS,
)
from .group import maybe_handle_group_command, update_last_member
from ..models.group import GroupState, merge_group_preferences
from ..privacy.data_privacy import (
    save_prefs_encrypted,
    load_prefs_encrypted,
    delete_prefs,
)

# Order for required slot filling
REQUIRED_ORDER: Tuple[str, ...] = ("city", "cuisine", "guests", "time")
REQUIRED_PROMPTS: Dict[str, str] = {
    "city": "In which city?",
    "cuisine": "Which cuisine (e.g., Italian, Sushi)?",
    "guests": "For how many people? (say a number like 2, 4)",
    "time": "What time? (e.g., 7 p.m. or 18:30)",
}

# module-level group state (per process)
GROUP = GroupState()

# --- Slim helpers kept local to avoid import/name clashes ---

_TIME_RE = re.compile(
    r"""\b(?P<h>\d{1,2})(?:[:.\s](?P<m>\d{2}))?\s*(?P<ampm>a\.?m\.?|p\.?m\.?|am|pm|aem|pem)?\b""",
    re.IGNORECASE | re.VERBOSE,
)

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


def _parse_time(text: str) -> Optional[str]:
    m = _TIME_RE.search(text or "")
    if not m:
        return None
    h = int(m.group("h"))
    mnt = m.group("m") or "00"
    ap = (m.group("ampm") or "").lower().replace(" ", "")
    ap = (
        ap.replace("a.m.", "am")
        .replace("p.m.", "pm")
        .replace("aem", "am")
        .replace("pem", "pm")
    )
    if ap == "pm" and h < 12:
        h += 12
    if ap == "am" and h == 12:
        h = 0
    if 0 <= h <= 23 and mnt.isdigit() and len(mnt) == 2:
        return f"{h:02}:{mnt}"
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


def _normalize_cuisine(s: str) -> str:
    return (s or "").strip().lower().split(",")[0].split()[0]


def _maybe_update_basic_prefs(prefs: UserPreferences, text: str) -> None:
    t = (text or "").lower().strip()
    if not getattr(prefs, "time", None):
        tm = _parse_time(t)
        if tm:
            prefs.time = tm
    if not getattr(prefs, "guests", None):
        g = _parse_guests(t)
        if g is not None:
            prefs.guests = g
    if not getattr(prefs, "city", None):
        m = re.search(r"\b(?:in|at)\s+([a-zA-ZÀ-ÿ\-.' ]{2,})$", t, flags=re.I)
        if m:
            prefs.city = m.group(1).strip()
    if not getattr(prefs, "cuisine", None):
        m = re.search(
            r"\b(italian|sushi|indian|mexican|chinese|greek|french|turkish|vietnamese|korean|japanese)\b",
            t,
        )
        if m:
            prefs.cuisine = _normalize_cuisine(m.group(1))


def _has_value(v: object) -> bool:
    if v is None:
        return False
    if isinstance(v, str):
        return v.strip() != ""
    if isinstance(v, int):
        return v > 0
    return True


def _next_missing_required(prefs: UserPreferences) -> Optional[str]:
    for key in REQUIRED_ORDER:
        if not _has_value(getattr(prefs, key, None)):
            return key
    return None


# --- Main turn handler ------------------------------------------------------
def handle_turn(
    prefs: UserPreferences, user_text: str, df: pd.DataFrame
) -> Tuple[str, Optional[pd.DataFrame]]:
    # --- Backward-compat: ensure new attrs exist on older prefs instances ---
    for k, v in {
        "pending_access_slot": None,
        "pending_misses": 0,
        "pending_required_slot": None,
        "pending_required_misses": 0,
    }.items():
        if not hasattr(prefs, k):
            setattr(prefs, k, v)

    t = (user_text or "").strip()
    low = t.lower()

    # ------------------ GDPR user controls ---------------------------------
    if "what do you store" in low or "welche daten speicherst du" in low:
        return (
            "I only store preferences if you ask me to. Everything runs locally. "
            "You can say 'remember my preferences' to save, or 'delete my data' to remove them.",
            None,
        )

    if "remember my preferences" in low or "speichere meine daten" in low:
        save_prefs_encrypted(prefs)
        return (
            "Saved your preferences locally with encryption. Say 'delete my data' anytime.",
            None,
        )

    if "load my preferences" in low or "lade meine daten" in low:
        loaded = load_prefs_encrypted(type(prefs))
        if loaded:
            prefs.__dict__.update(loaded.__dict__)
            return "Loaded your preferences.", None
        return "I don’t have any stored data yet.", None

    if (
        "delete my data" in low
        or "lösche meine daten" in low
        or "loesche meine daten" in low
    ):
        ok = delete_prefs()
        return ("Deleted locally stored data." if ok else "No stored data found."), None

    # ------------------ GROUP COMMANDS -------------------------------------
    cmd_reply = maybe_handle_group_command(GROUP, t)
    if cmd_reply:
        return cmd_reply, None

    if GROUP.active:
        update_last_member(GROUP, t)
        if GROUP.size and len(GROUP.members) >= GROUP.size:
            return (
                f"I've captured {GROUP.size} members. Say 'end group' to finalize or 'add' to add more.",
                None,
            )
        return (
            "Captured. Say 'add' for another member, or 'end group' to finalize.",
            None,
        )

    if (
        t.lower() in {"show results", "zeige ergebnisse", "results", "recommend"}
        and GROUP.members
    ):
        merged = merge_group_preferences(GROUP)
        results = filter_and_rank(df, merged, top_k=5)
        if results.empty:
            GROUP.members.clear()
            return (
                "I couldn't find any matches for your group. Should I relax the constraints?",
                None,
            )
        lines: List[str] = []
        for _, r in results.head(3).iterrows():
            badges: List[str] = []
            if r.get("access_wheelchair"):
                badges.append("♿ wheelchair")
            if r.get("access_step_free"):
                badges.append("⬆ step-free")
            if r.get("access_restroom"):
                badges.append("🚻 accessible restroom")
            lines.append(
                f"{r['name']} ({r['cuisine']}, {r['price']}, ★{r['rating']})  "
                f"[{' | '.join(badges) if badges else '—'}]"
            )
        GROUP.members.clear()
        return "Group matches:\n• " + "\n• ".join(lines), results

    # --------------- HANDLE PENDING REQUIRED-SLOT ANSWER -------------------
    asked_req = getattr(prefs, "pending_required_slot", None)
    if asked_req:
        value_set = False

        if asked_req == "guests":
            n = _parse_guests(t)
            if n is not None:
                prefs.guests = n
                value_set = True

        elif asked_req == "time":
            tm = _parse_time(t)
            if tm:
                prefs.time = tm
                value_set = True

        elif asked_req == "cuisine":
            cand = _normalize_cuisine(t.split(",")[0])
            if cand:
                prefs.cuisine = cand
                value_set = True

        elif asked_req == "city":
            city = t.strip()
            if city:
                prefs.city = city
                value_set = True

        if not value_set:
            prefs.pending_required_misses = (
                getattr(prefs, "pending_required_misses", 0) + 1
            )
            if prefs.pending_required_misses < 2 and t.lower() not in {"skip", "egal"}:
                return REQUIRED_PROMPTS[asked_req] + " (you can also say 'skip')", None
            # else: skip after 2 misses by clearing below

        # clear pending state either way
        prefs.pending_required_slot = None
        prefs.pending_required_misses = 0

    # ------------------ FREE-TEXT UPDATE ---------------------------------
    _maybe_update_basic_prefs(prefs, t)

    # -------------------- ACCESSIBILITY YES/NO ------------------------------
    if prefs.pending_access_slot:
        yn = classify_yes_no(t)
        if yn is None:
            prefs.pending_misses = getattr(prefs, "pending_misses", 0) + 1
            if prefs.pending_misses < 2:
                return (
                    ACCESS_QUESTIONS[prefs.pending_access_slot]
                    + " (you can also type 'skip')",
                    None,
                )
            # default to False after 2 unclear tries
            setattr(prefs.accessibility, prefs.pending_access_slot, False)
        else:
            setattr(prefs.accessibility, prefs.pending_access_slot, yn)
        prefs.pending_access_slot = None
        prefs.pending_misses = 0

    # keyword-based accessibility update (e.g., "barrierefrei", "wheelchair")
    update_accessibility_from_text(prefs, t)

    # Ask one pending accessibility question if any field unknown
    missing_access = next_missing_access_slot(prefs)
    if missing_access:
        prefs.pending_access_slot = missing_access
        prefs.pending_misses = 0
        return ACCESS_QUESTIONS[missing_access], None

    # ----------------- ASK NEXT MISSING REQUIRED SLOT ----------------------
    missing_req = _next_missing_required(prefs)
    if missing_req:
        if t.lower() in {"skip", "egal", "doesn't matter", "dont care", "don't care"}:
            # Skip - mark neutral/empty and continue
            if missing_req in ("city", "cuisine"):
                setattr(prefs, missing_req, "")
            elif missing_req == "guests":
                setattr(prefs, missing_req, 2)
            elif missing_req == "time":
                setattr(prefs, missing_req, "19:00")
        else:
            prefs.pending_required_slot = missing_req
            prefs.pending_required_misses = 0
            return REQUIRED_PROMPTS[missing_req], None

    # -------------------------- RECOMMEND ----------------------------------
    results = filter_and_rank(df, prefs, top_k=5)
    if results.empty:
        return "I couldn't find any matches. Want me to broaden the search?", None

    for _, r in results.head(3).iterrows():

        if r.get("access_wheelchair"):
            badges.append("♿ wheelchair")
        if r.get("access_step_free"):
            badges.append("⬆ step-free")
        if r.get("access_restroom"):
            badges.append("🚻 accessible restroom")
        lines.append(
            f"{r['name']} ({r['cuisine']}, {r['price']}, ★{r['rating']})  "
            f"[{' | '.join(badges) if badges else '—'}]"
        )

    reply = "Here are good matches:\n• " + "\n• ".join(lines)
    return reply, results
