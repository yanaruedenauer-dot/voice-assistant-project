from dialog_manager import next_action

slots = {"guests": 2, "time": "19:00", "cuisine": "italian", "city": "Munich"}
action, payload = next_action("booking_request", slots)

print(action)
print(payload["message"])

for r in payload.get("results", []):
    print(f"- {r['name']} | rating: {r.get('rating')} | {r.get('address')}")
