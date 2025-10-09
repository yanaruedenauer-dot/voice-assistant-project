from __future__ import annotations

import os
import re
import sys
import subprocess
from typing import Any, Callable, Dict, Optional


import sounddevice as sd

import dialog_manager
from whisper_mic_transcribe import transcribe_once
from src.utils.normalize import fuzzy_choice
from src.data.loader import load_restaurants
from src.models.preferences import UserPreferences
from src.dialog.manager import handle_turn

analyze_sentiment: Optional[Callable[[str], Dict[str, Any]]]
try:
    from src.nlp.sentiment_en import analyze_sentiment as _analyze_sentiment

    analyze_sentiment = _analyze_sentiment
except Exception:
    analyze_sentiment = None


os.environ["TOKENIZERS_PARALLELISM"] = "false"


# Local imports


# --- Data & Preferences init -----------------------------------------------
DATA_PATH = "data/restaurants_test.csv"
df = load_restaurants(DATA_PATH)
print(f"✅ Loaded {len(df)} restaurants with accessibility info")
prefs = UserPreferences()  # persists across turns

# --- Feature toggles --------------------------------------------------------
USE_WHISPER = True  # mic + Whisper, else keyboard
USE_TTS = True  # assistant speaks
TTS_BACKEND = "say"  # "say" (macOS) or "pyttsx3"
TTS_VOICE = "Samantha"  # "Anna" for German
RESULT_LINES_TO_SPEAK = 3  # speak first N recommendation lines

# --- TTS engine cache -------------------------------------------------------
_engine = None  # used only if TTS_BACKEND == "pyttsx3"


# --- Helpers ----------------------------------------------------------------
def default_input_index() -> Optional[int]:
    """Return default input device index for sounddevice, or a safe fallback."""
    try:
        in_idx, _ = sd.default.device  # (input_idx, output_idx)
        idx = int(in_idx)
        if idx < 0:
            idx = 1  # common macOS internal mic
        print(f"[debug] input_device index = {idx}")
        return idx
    except Exception as e:
        print(f"[debug] could not read default input device: {e}")
        return 1


def _safe_transcribe(**kwargs) -> str:
    """Call transcribe_once and always return a string."""
    try:
        return (transcribe_once(**kwargs) or "").strip()
    except Exception as e:
        print(f"[WARN] Transcription failed: {e}")
        return ""


def speak(text: str) -> None:
    """Text-to-speech with either macOS 'say' or pyttsx3."""
    if not USE_TTS or not text:
        return
    if TTS_BACKEND == "say":
        try:
            subprocess.run(["say", "-v", TTS_VOICE, text], check=False)
        except Exception:
            pass
    elif TTS_BACKEND == "pyttsx3":
        global _engine
        try:
            if _engine is None:
                import pyttsx3

                _engine = pyttsx3.init()
                _engine.setProperty("rate", 180)
            _engine.say(text)
            _engine.runAndWait()
        except Exception:
            pass


def print_and_speak(msg: str) -> None:
    print(msg)
    speak(msg)


# --- Slot helpers -----------------------------------------------------------
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

# Accepts: "6", "6 am", "6 a.m.", "06:15", "6pm", "6 p m", "6 aem" (typo)
TIME_RE_RELAXED = re.compile(
    r"""
    \b
    (?P<h>\d{1,2})              # hour
    (?:[:.\s](?P<m>\d{2}))?     # optional minutes
    \s*
    (?P<ampm>                   # optional am/pm group
        a\.?m\.? | p\.?m\.? |
        am | pm |
        aem | pem              # common STT typos
    )?
    \b
    """,
    re.IGNORECASE | re.VERBOSE,
)


def _normalize_ampm(s: Optional[str]) -> str:
    if not s:
        return ""
    s = s.lower().replace(" ", "")
    s = s.replace("aem", "am").replace("pem", "pm")
    s = (
        s.replace("a.m.", "am")
        .replace("p.m.", "pm")
        .replace("a.m", "am")
        .replace("p.m", "pm")
    )
    return s


def _parse_time(text: str) -> Optional[str]:
    m = TIME_RE_RELAXED.search(text or "")
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
    # number words
    for w, n in EN_NUM.items():
        if re.search(rf"\b{re.escape(w)}\b", t, flags=re.I):
            return n
    for w, n in GERMAN_NUM.items():
        if re.search(rf"\b{re.escape(w)}\b", t, flags=re.I):
            return n
    # digits
    m = re.search(r"\b(\d{1,2})\b", t)
    if m:
        try:
            n = int(m.group(1))
            if 1 <= n <= 20:
                return n
        except ValueError:
            pass
    return None


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


def normalize_cuisine(text: str) -> str:
    raw = (text or "").strip().lower()
    raw = raw.split(",")[0]
    raw = re.sub(r"[/|]", " ", raw)
    raw = re.sub(r"[^\wÀ-ÿ ]+", "", raw).strip()
    if not raw:
        return ""
    cand = CUISINE_SYNONYMS.get(raw, raw)
    try:
        if getattr(dialog_manager, "_CUISINES", None):
            guess = fuzzy_choice(cand, dialog_manager._CUISINES, cutoff=0.55)
            if guess:
                return guess
    except Exception:
        pass
    return cand.split()[0]


def extract_basic_slots(
    text: str, slots: Dict[str, object] | None = None
) -> Dict[str, object]:
    if slots is None:
        slots = {}
    t = (text or "").lower()

    # guests
    if "guests" not in slots:
        g = _parse_guests(t)
        if g is not None:
            slots["guests"] = g

    # time
    if "time" not in slots:
        tm = _parse_time(t)
        if tm:
            slots["time"] = tm

    # city
    if "city" not in slots:
        m = re.search(r"\b(?:in|at)\s+([a-zA-ZÀ-ÿ\-.' ]{2,})$", t.strip(), flags=re.I)
        if m:
            slots["city"] = m.group(1).strip()

    # cuisine
    if "cuisine" not in slots:
        m = re.search(
            r"\b(?:italian|sushi|indian|mexican|chinese|greek|french|turkish|vietnamese|korean|japanese)\b",
            t,
        )
        if m:
            slots["cuisine"] = normalize_cuisine(m.group(0))

    return slots  # ← return at the end


def cuisine_picklist() -> str:
    options = (dialog_manager._CUISINES or [])[:10]
    if not options:
        print("(No predefined cuisines found — please type)")
        return input("> ").strip()
    print("Please choose a cuisine (number or name):")
    for i, c in enumerate(options, 1):
        print(f"{i}. {c}")
    ans = input("> ").strip().lower()
    if ans in {"quit", "exit", "stop", "beenden"}:
        print("OK, exiting. 👋")
        sys.exit(0)
    if ans in {"restart", "neustart"}:
        return "__RESTART__"
    if ans.isdigit():
        n = int(ans)
        if 1 <= n <= len(options):
            return options[n - 1]
    if ans in GERMAN_NUM:
        n = GERMAN_NUM[ans]
        if 1 <= n <= len(options):
            return options[n - 1]
    return ans


# --- User I/O ---------------------------------------------------------------
def ask_user(slot: Optional[str] = None) -> str:
    """
    Voice-first input with:
    - exit words (quit/exit/stop/beenden)
    - 1 retry on empty
    - cuisine hint + optional pick-list fallback
    - robust guests capture (digits)
    - sentiment probe (if available)
    """
    # Keyboard mode
    if not USE_WHISPER:
        ans = input("> ").strip()
        if ans.lower() in {"quit", "exit", "stop", "beenden"}:
            print("OK, exiting. 👋")
            sys.exit(0)
        return ans

    idx = default_input_index()

    # per-slot hints
    lang = None  # auto detect by default
    initial = None
    seconds = 3
    if slot == "cuisine":
        lang = "de"
        initial = (
            "Sprache Deutsch. Antworte nur mit einer Küche wie "
            "Italienisch, Sushi, Indisch, Chinesisch, Mexikanisch, Griechisch, "
            "Türkisch, Vietnamesisch, Koreanisch, Spanisch, Französisch."
        )
    elif slot == "guests":
        initial = "Answer with digits only like: 2, 3, 4."
        seconds = 2

    print("(Speak now for ~3s…)" if seconds == 3 else "(Speak a number…)")
    text = _safe_transcribe(
        seconds=seconds,
        model="base",
        language=lang,
        device="cpu",
        input_device=idx,
        temperature=0.0,
        initial_prompt=initial,
    )

    # Exit words
    if text.lower() in {"quit", "exit", "stop", "beenden"}:
        print("OK, exiting. 👋")
        sys.exit(0)

    # If asking for guests, force digits extraction (retry + fallback)
    if slot == "guests":
        m = re.search(r"\b(\d{1,2})\b", text)
        if not m:
            print("(I didn’t catch the number — one more try)")
            text = _safe_transcribe(
                seconds=2,
                model="base",
                language=lang,
                device="cpu",
                input_device=idx,
                temperature=0.0,
                initial_prompt=initial,
            )
            m = re.search(r"\b(\d{1,2})\b", text)
        if not m:
            typed = input("Please type the number of guests (e.g., 2): ").strip()
            m = re.search(r"\b(\d{1,2})\b", typed or "")
            if not m:
                return ""
            return m.group(1)
        return m.group(1)

    # Retry once on empty
    if not text:
        print("(I didn’t catch that — one more try)")
        text = _safe_transcribe(
            seconds=3,
            model="base",
            language=lang,
            device="cpu",
            input_device=idx,
            temperature=0.0,
            initial_prompt=(
                (
                    "Sprache Deutsch. Nur ein Wort für die Küche, z. B. Italienisch oder Sushi."
                )
                if slot == "cuisine"
                else None
            ),
        )
        if text.lower() in {"quit", "exit", "stop", "beenden"}:
            print("OK, exiting. 👋")
            sys.exit(0)
        if not text:
            print("(Still nothing — please type)")
            typed = input("> ").strip()
            if typed.lower() in {"quit", "exit", "stop", "beenden"}:
                print("OK, exiting. 👋")
                sys.exit(0)
            return typed

    # Sentiment
    if analyze_sentiment:
        try:
            sent = analyze_sentiment(text)
            print(f"[sentiment] {sent['label']} ({sent['score']:.2f})")
            if sent["label"] == "NEGATIVE" and sent["score"] > 0.8:
                print_and_speak("I sense some frustration. Let's try again calmly.")
        except Exception:
            pass

    print(f"[gehört] {text}")

    # Cuisine normalization / pick-list
    if slot == "cuisine" and getattr(dialog_manager, "_CUISINES", None):
        cand = normalize_cuisine(text)
        if cand:
            confirm = input(f"Meintest du '{cand}'? (j/n) ").strip().lower()
            if confirm in {"j", "ja", "y", "yes"}:
                return cand
        options = (dialog_manager._CUISINES or [])[:10]
        if options:
            print("Bitte wähle eine Küche (Nummer oder Name):")
            for i, c in enumerate(options, 1):
                print(f"{i}. {c}")
            pick = input("> ").strip()
            if pick.isdigit() and 1 <= int(pick) <= len(options):
                return options[int(pick) - 1]
            return normalize_cuisine(pick)

    return text


# --- Main loop --------------------------------------------------------------
def run():
    # greeting
    print_and_speak("Hi! How can I help?")

    while True:
        user_text = ask_user()  # MIC/keyboard preserved
        if user_text.lower() in {"quit", "exit", "stop", "beenden"}:
            print("Bye! 👋")
            break

        reply, results = handle_turn(prefs, user_text, df)

        # show & speak the reply
        print_and_speak(reply)

        # if there are results, list the top ones with badges
        if results is not None and hasattr(results, "iterrows"):
            for i, (_, row) in enumerate(
                results.head(RESULT_LINES_TO_SPEAK).iterrows(), 1
            ):
                badges = []
                if row.get("access_wheelchair"):
                    badges.append("♿ wheelchair")
                if row.get("access_step_free"):
                    badges.append("⬆ step-free")
                if row.get("access_restroom"):
                    badges.append("🚻 accessible restroom")
                badge_str = " | ".join(badges) if badges else "—"
                line = f"{i:>2}. {row['name']} ({row['cuisine']}, {row['price']}, ★{row['rating']}) [{badge_str}]"
                print(line)
                speak(line)


# --- Entrypoint -------------------------------------------------------------
if __name__ == "__main__":
    try:
        run()
    except (KeyboardInterrupt, EOFError):
        print("\nBye! 👋")
        sys.exit(0)
