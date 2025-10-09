import pandas as pd
from src.models.preferences import UserPreferences, AccessibilityNeeds
from src.models.group import GroupState, merge_group_preferences
from src.reco.recommender import filter_and_rank


def test_merge_access_any_true():
    g = GroupState(active=False, size=2)
    a = UserPreferences(
        city="Berlin",
        cuisine="italian",
        accessibility=AccessibilityNeeds(wheelchair=True),
    )
    b = UserPreferences(
        city="Berlin",
        cuisine="italian",
        accessibility=AccessibilityNeeds(step_free=True),
    )
    g.members = [a, b]
    merged = merge_group_preferences(g)
    assert merged.accessibility.wheelchair is True
    assert merged.accessibility.step_free is True


def test_merge_cuisine_majority():
    g = GroupState(active=False, size=3)
    g.members = [
        UserPreferences(cuisine="italian"),
        UserPreferences(cuisine="italian"),
        UserPreferences(cuisine="japanese"),
    ]
    merged = merge_group_preferences(g)
    assert merged.cuisine == "italian"


def test_group_reco_runs():
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
                "access_step_free": False,
                "access_restroom": True,
            },
            {
                "id": 2,
                "name": "B",
                "city": "Berlin",
                "cuisine": "japanese",
                "price": "$$$",
                "rating": 4.3,
                "access_wheelchair": False,
                "access_step_free": True,
                "access_restroom": False,
            },
        ]
    )
    g = GroupState(active=False, size=2)
    g.members = [
        UserPreferences(
            city="Berlin",
            cuisine="italian",
            accessibility=AccessibilityNeeds(wheelchair=True),
        ),
        UserPreferences(
            city="Berlin", accessibility=AccessibilityNeeds(step_free=True)
        ),
    ]
    merged = merge_group_preferences(g)
    out = filter_and_rank(df, merged, top_k=5)
    assert not out.empty
