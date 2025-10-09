from typing import List
import pandas as pd
from ..models.preferences import UserPreferences


def filter_and_rank(
    df: pd.DataFrame,
    prefs: UserPreferences,
    top_k: int = 10,
) -> pd.DataFrame:
    q = df.copy()

    # --- Base score: rating normalized 0..1 ---
    rmin = float(q["rating"].min())
    rmax = float(q["rating"].max())
    q["score"] = (q["rating"] - rmin) / (rmax - rmin + 1e-9)

    # --- Popularity (if available) ---
    if "rating_count" in q.columns:
        pmin = float(q["rating_count"].min())
        pmax = float(q["rating_count"].max())
        pop = (q["rating_count"] - pmin) / (pmax - pmin + 1e-9)
    else:
        # scalar 0.0 keeps vectorized math valid below
        pop = 0.0
    q["score"] = 0.70 * q["score"] + 0.10 * pop

    # --- Soft boosts container (keeps alignment if we filter) ---
    boosts = pd.Series(0.0, index=q.index)

    # --- Accessibility: hard filter only if explizit True; sonst soft boost ---
    acc = getattr(prefs, "accessibility", None)

    # Wheelchair
    if acc and getattr(acc, "wheelchair", None) is True:
        q = q[q["access_wheelchair"].fillna(False)]
        boosts = boosts.loc[q.index]
    else:
        boosts.loc[q.index] += q["access_wheelchair"].fillna(False).astype(float) * 0.03

    # Step-free
    if acc and getattr(acc, "step_free", None) is True:
        q = q[q["access_step_free"].fillna(False)]
        boosts = boosts.loc[q.index]
    else:
        boosts.loc[q.index] += q["access_step_free"].fillna(False).astype(float) * 0.02

    # Accessible restroom
    if acc and getattr(acc, "restroom", None) is True:
        q = q[q["access_restroom"].fillna(False)]
        boosts = boosts.loc[q.index]
    else:
        boosts.loc[q.index] += q["access_restroom"].fillna(False).astype(float) * 0.02

    # --- Content/intent alignment (soft boosts) ---
    if getattr(prefs, "cuisine", None):
        mask_c = q["cuisine"].str.lower() == str(prefs.cuisine).strip().lower()
        boosts.loc[mask_c.index[mask_c]] += 0.08  # 8%

    if getattr(prefs, "city", None):
        mask_city = q["city"].str.lower() == str(prefs.city).strip().lower()
        boosts.loc[mask_city.index[mask_city]] += 0.05  # 5%

    # Apply boosts
    q["score"] = q["score"].loc[q.index] + boosts

    # --- Graceful fallback if hard filters wiped everything ---
    if q.empty:
        q = df.copy()
        rmin = float(q["rating"].min())
        rmax = float(q["rating"].max())
        rating_norm = (q["rating"] - rmin) / (rmax - rmin + 1e-9)
        q["score"] = 0.80 * rating_norm

        if "rating_count" in q.columns:
            pmin = float(q["rating_count"].min())
            pmax = float(q["rating_count"].max())
            pop = (q["rating_count"] - pmin) / (pmax - pmin + 1e-9)
            q["score"] += 0.10 * pop

        if getattr(prefs, "cuisine", None):
            q.loc[
                q["cuisine"].str.lower() == str(prefs.cuisine).strip().lower(),
                "score",
            ] += 0.06
        if getattr(prefs, "city", None):
            q.loc[
                q["city"].str.lower() == str(prefs.city).strip().lower(),
                "score",
            ] += 0.04

    q = q.sort_values("score", ascending=False)

    cols: List[str] = [
        "id",
        "name",
        "city",
        "cuisine",
        "price",
        "rating",
        "access_wheelchair",
        "access_step_free",
        "access_restroom",
        "score",
    ]
    cols = [c for c in cols if c in q.columns]
    return q[cols].head(top_k)
