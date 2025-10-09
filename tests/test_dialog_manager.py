import dialog_manager


def test_greeting_returns_prompt():
    action, payload = dialog_manager.next_action("greeting", {})
    assert action == "ask"
    assert "How can I help" in payload["message"]


def test_unknown_intent_prompts_help():
    action, payload = dialog_manager.next_action("smalltalk", {})
    assert action == "ask"
    assert "How can I help" in payload["message"]


def test_missing_slots_prompts_first_missing():  # REQUIRED = ["guests", "time", "cuisine", "city"]
    # Only cuisine is provided → should ask for 'guests' first
    action, payload = dialog_manager.next_action(
        "booking_request", {"cuisine": "italian"}
    )
    assert action == "ask"
    assert payload["slot"] == "guests"
    assert "For how many people" in payload["message"]


def test_recommend_with_all_slots_returns_results(patch_places):
    slots = {"guests": 2, "time": "19:00", "cuisine": "italian", "city": "Munich"}
    action, payload = dialog_manager.next_action("booking_request", slots)
    assert action == "recommend"
    assert "Here are some" in payload["message"]
    assert payload["results"]
    assert all("name" in r and "address" in r for r in payload["results"])


def test_no_results_prompts_retry(monkeypatch, patch_places):
    patch_places.RESULTS = []
    slots = {"guests": 2, "time": "19:00", "cuisine": "italian", "city": "Munich"}
    action, payload = dialog_manager.next_action("booking_request", slots)
    assert action == "ask"
    assert (
        "no italian places" in payload["message"].lower()
        or "found no italian" in payload["message"].lower()
    )
