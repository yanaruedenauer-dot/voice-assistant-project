# recommender_stub.py
from datetime import datetime


def recommend(slots: dict) -> list[dict]:
    cuisine = slots.get("cuisine", "gemischt")
    guests = slots.get("guests", 2)
    time = slots.get("time", "19:00")
    acc = " (barrierefrei)" if slots.get("accessibility") else ""

    base = [
        {
            "name": f"{cuisine.title()} Bistro A",
            "rating": 4.5,
            "distance_km": 1.2,
            "time": time,
            "guests": guests,
        },
        {
            "name": f"{cuisine.title()} Trattoria B",
            "rating": 4.3,
            "distance_km": 2.0,
            "time": time,
            "guests": guests,
        },
        {
            "name": f"{cuisine.title()} Restaurant C",
            "rating": 4.1,
            "distance_km": 0.8,
            "time": time,
            "guests": guests,
        },
    ]
    for r in base:
        r["note"] = f"Eignung: {guests} Pers um {time}{acc}"
        r["eta"] = datetime.now().strftime("%H:%M")
    return base


def format_cards(items: list[dict]) -> str:
    lines = []
    for r in items:
        lines.append(
            f"- {r['name']}  ⭐ {r['rating']}  · {r['distance_km']} km\n"
            f"  {r['note']}  · Vorschlag erstellt {r['eta']}"
        )
    return "\n".join(lines)
