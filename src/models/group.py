from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Dict
from .preferences import UserPreferences, AccessibilityNeeds


@dataclass
class GroupState:
    active: bool = False
    size: Optional[int] = None
    members: List[UserPreferences] = field(default_factory=list)

    def add_member(self, prefs: UserPreferences) -> None:
        self.members.append(prefs)


def merge_group_preferences(group: GroupState) -> UserPreferences:
    """
    Merge member preferences:
      - accessibility: OR rule (if any True -> True)
      - cuisine: majority vote; fallback to first non-empty
      - city/time: first non-empty
      - guests: group.size if set, else sum of members with guests or count of members
    """
    merged = UserPreferences()

    # --- Accessibility OR (safe even if member.accessibility is None) ---
    acc = AccessibilityNeeds()
    any_wheel = any(
        getattr(m.accessibility, "wheelchair", None) is True for m in group.members
    )
    any_step = any(
        getattr(m.accessibility, "step_free", None) is True for m in group.members
    )
    any_wc = any(
        getattr(m.accessibility, "restroom", None) is True for m in group.members
    )
    acc.wheelchair = True if any_wheel else None
    acc.step_free = True if any_step else None
    acc.restroom = True if any_wc else None
    merged.accessibility = acc

    # --- Cuisine majority vote (typed local dict to appease mypy) ---
    cuisine_counts: Dict[str, int] = {}
    for m in group.members:
        if m.cuisine:
            key = m.cuisine.strip().lower()
            cuisine_counts[key] = cuisine_counts.get(key, 0) + 1

    if cuisine_counts:
        merged.cuisine = max(cuisine_counts.items(), key=lambda kv: kv[1])[0]
    else:
        # fallback: first non-empty cuisine
        for m in group.members:
            if m.cuisine:
                merged.cuisine = m.cuisine
                break

    # --- City / time: first non-empty seen ---
    for m in group.members:
        if not merged.city and m.city:
            merged.city = m.city
        if not merged.time and m.time:
            merged.time = m.time
        if merged.city and merged.time:
            break

    # --- Guests ---
    if group.size is not None:
        merged.guests = group.size
    else:
        explicit_guest_counts: List[int] = [
            int(g) for g in (m.guests or 0 for m in group.members) if g
        ]
        merged.guests = (
            sum(explicit_guest_counts)
            if explicit_guest_counts
            else (len(group.members) or None)
        )

    return merged
