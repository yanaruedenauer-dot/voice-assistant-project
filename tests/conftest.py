import types
import pytest
import dialog_manager


@pytest.fixture(autouse=True)
def reset_dm():
    # Ensure the module-level cache is reset between tests
    if hasattr(dialog_manager, "_DF"):
        dialog_manager._DF = None
    yield
    if hasattr(dialog_manager, "_DF"):
        dialog_manager._DF = None


@pytest.fixture
def fake_places():
    """
    Returns a namespace with fake load_df() and search_restaurants_local().
    You can tweak 'RESULTS' per test via attribute assignment.
    """
    ns = types.SimpleNamespace()
    ns.RESULTS = [
        {"name": "Luigi Trattoria", "rating": 4.5, "address": "Altstadt 1, Munich"},
        {"name": "Roma Cucina", "rating": 4.3, "address": "Maxvorstadt 22, Munich"},
    ]

    def load_df(filename="zomato.csv", encoding="ISO-8859-1"):
        return object()  # sentinel

    def search_restaurants_local(
        df, cuisine: str, city: str, limit: int = 5
    ):  # Return a sliced copy to respect 'limit'

        return ns.RESULTS[:limit]

    ns.load_df = load_df
    ns.search_restaurants_local = search_restaurants_local
    return ns


@pytest.fixture
def patch_places(
    monkeypatch, fake_places
):  # Patch the imports used inside dialog_manager
    monkeypatch.setenv("PYTHONHASHSEED", "0")
    monkeypatch.setattr("dialog_manager.load_df", fake_places.load_df, raising=True)
    monkeypatch.setattr(
        "dialog_manager.search_restaurants_local",
        fake_places.search_restaurants_local,
        raising=True,
    )
    return fake_places
