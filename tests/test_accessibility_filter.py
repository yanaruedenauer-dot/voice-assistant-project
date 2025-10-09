import pandas as pd
from src.models.preferences import UserPreferences, AccessibilityNeeds
from src.reco.recommender import filter_and_rank


def test_accessibility_filter():
    df = pd.DataFrame(
        [
            {
                "id": 1,
                "name": "A",
                "city": "Berlin",
                "cuisine": "italian",
                "price": "$$",
                "rating": 4.5,
                "access_wheelchair": True,
                "access_step_free": True,
                "access_restroom": True,
            },
            {
                "id": 2,
                "name": "B",
                "city": "Berlin",
                "cuisine": "italian",
                "price": "$$$",
                "rating": 4.6,
                "access_wheelchair": False,
                "access_step_free": True,
                "access_restroom": False,
            },
        ]
    )
    prefs = UserPreferences(
        city="Berlin",
        cuisine="italian",
        accessibility=AccessibilityNeeds(wheelchair=True),
    )
    out = filter_and_rank(df, prefs, top_k=5)
    assert (out["name"] == "A").any()
    assert not (out["name"] == "B").any()
