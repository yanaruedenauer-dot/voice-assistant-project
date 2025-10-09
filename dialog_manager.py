from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple, Callable, cast
import pandas as pd

from src.places_local import load_df, search_with_fallback

# Optional legacy/local search function (signature may vary across branches/tests)
try:
    from src.places_local import search_restaurants_local as _search_restaurants_local

    # accept any signature (3-arg or 4-arg with limit)
    search_restaurants_local: Optional[Callable[..., Any]] = _search_restaurants_local
except Exception:
    search_restaurants_local = None

# ----------------- globals -----------------
_DF: Optional[pd.DataFrame] = None  # dataset cache
_CUISINES: List[str] = []  # optional public-facing list
REQUIRED: List[str] = ["guests", "time", "cuisine", "city"]


# --- Dataset bootstrap ------------------------------------------------------
def _ensure_data_loaded() -> None:
    """Load the dataset once (idempotent)."""
    global _DF
    if _DF is None:
        _DF = load_df()


def _unpack_results(pack: Any) -> Tuple[List[Dict[str, Any]], Any]:
    """
    Tolerate different return shapes:
      - {"results": [...], "fallback": ...}
      - list[dict]
      - object with .RESULTS (and optional .fallback)
    Returns: (results_list, fallback_obj_or_None)
    """
    if isinstance(pack, dict):
        res = pack.get("results", []) or []
        return list(res), pack.get("fallback")

    if isinstance(pack, (list, tuple)):
        return list(pack), None

    results = getattr(pack, "RESULTS", None)
    if results is not None:
        try:
            return list(results), getattr(pack, "fallback", None)
        except Exception:
            return [], None

    return [], None


def next_action(intent: str, slots: Dict[str, object]) -> Tuple[str, Dict[str, Any]]:
    """
    Returns (action, payload)
      action ∈ {"ask", "recommend"}
      - ask payload:        {"message": str, "slot": Optional[str]}
      - recommend payload:  {"message": str, "results": list[dict], "slots": dict}
    """
    # greeting / generic
    if intent == "greeting":
        return "ask", {"message": "Hi! How can I help?", "slot": None}

    if intent not in {"booking_request", "recommendation_request"}:
        return "ask", {"message": "How can I help?", "slot": None}

    # ask for first missing slot
    missing = [k for k in REQUIRED if not slots.get(k)]
    if missing:
        prompts: Dict[str, str] = {
            "guests": "For how many people?",
            "time": "What time?",
            "cuisine": "Which cuisine (Italian, Sushi)?",
            "city": "In which city?",
        }
        k = missing[0]
        return "ask", {"message": prompts[k], "slot": k}

    # all slots present -> search
    _ensure_data_loaded()
    assert _DF is not None, "Internal dataset not loaded"
    df_local: pd.DataFrame = cast(pd.DataFrame, _DF)

    cuisine = str(slots["cuisine"])
    city = str(slots["city"])

    results: List[Dict[str, Any]] = []
    fb: Any = None

    # Prefer the new API; tolerate legacy shapes/signatures.
    try:
        pack = search_with_fallback(df_local, cuisine, city, limit=5)
        results, fb = _unpack_results(pack)
    except Exception:
        if callable(search_restaurants_local):
            try:
                # first try: 3-arg signature
                rows = list(search_restaurants_local(df_local, cuisine, city))
            except TypeError:
                # fallback: 4-arg signature (with limit)
                rows = list(search_restaurants_local(df_local, cuisine, city, 5))
            results = list(rows)
            fb = None
        else:
            results, fb = [], None

    if not results:
        return "ask", {
            "message": f"I found no {cuisine} places in {city}. Try another cuisine or city?",
            "slot": "cuisine",
        }

    # tailor message based on fallback info if available
    if not fb:
        msg = f"Here are some {cuisine} options in {city}. Shall I pick one?"
    elif isinstance(fb, dict) and fb.get("type") == "nearest_city":
        msg = (
            f"I couldn't find {cuisine} places in {city}. "
            f"Here are top {cuisine} options in the nearest available city: {fb.get('city')}."
        )
    elif isinstance(fb, dict) and fb.get("type") == "global_cuisine":
        msg = (
            f"I couldn't find {cuisine} places in {city}. "
            f"Here are top {cuisine} options across the dataset."
        )
    else:
        msg = f"Here are {cuisine} options."

    payload: Dict[str, Any] = {"message": msg, "results": results, "slots": slots}
    return "recommend", payload


# Optional helper so other modules don’t touch internals
def get_cuisines() -> List[str]:
    return list(_CUISINES)
