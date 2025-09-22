from typing import List, Dict, Any


def rank(
    candidates: List[Dict[str, Any]], weights: Dict[str, float]
) -> List[Dict[str, Any]]:
    # Toy scoring for demo
    scored = []
    for c in candidates:
        score = (
            weights.get("distance", 0.2) * (1.0 - c.get("distance_norm", 0.5))
            + weights.get("rating", 0.2) * c.get("rating_norm", 0.5)
            + weights.get("price", 0.1) * (1.0 - c.get("price_norm", 0.5))
            + weights.get("accessibility", 0.3) * c.get("accessibility_norm", 0.5)
            + weights.get("preference_fit", 0.2) * c.get("preference_fit_norm", 0.5)
        )
        c["score"] = score
        c["rationale"] = {
            "distance": c.get("distance_km", "?"),
            "rating": c.get("rating", "?"),
            "accessibility": c.get("accessibility", {}),
            "preference_fit": c.get("preference_fit_norm", 0.0),
        }
        scored.append(c)
    return sorted(scored, key=lambda x: x["score"], reverse=True)
