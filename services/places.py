import requests
import os


PLACES_BASE = "https://maps.googleapis.com/maps/api/place/textsearch/json"
DETAILS_BASE = "https://maps.googleapis.com/maps/api/place/details/json"


def _api_key() -> str:
    key = os.getenv("GOOGLE_PLACES_API_KEY")
    if not key:
        raise RuntimeError("GOOGLE_PLACES_API_KEY is not set")
    return key


def search_restaurants(query: str, city: str, max_results: int = 5):
    """
    Text search for restaurants. Query can include cuisine, constraints, etc.
    """
    params = {"query": f"{query} in {city}", "type": "restaurant", "key": _api_key()}
    r = requests.get(PLACES_BASE, params=params, timeout=10)
    r.raise_for_status()
    data = r.json()

    results = []
    for item in data.get("results", [])[:max_results]:
        results.append(
            {
                "name": item.get("name"),
                "rating": item.get("rating"),
                "address": item.get("formatted_address"),
                "place_id": item.get("place_id"),
                "price_level": item.get("price_level"),
                "open_now": (
                    item.get("opening_hours", {}).get("open_now")
                    if item.get("opening_hours")
                    else None
                ),
            }
        )
    return results


def enrich_details(place_id: str):
    params = {
        "place_id": place_id,
        "fields": "name,formatted_address,formatted_phone_number,website,opening_hours,price_level,rating,geometry",
        "key": _api_key(),
    }
    r = requests.get(DETAILS_BASE, params=params, timeout=10)
    r.raise_for_status()
    return r.json().get("result", {})
