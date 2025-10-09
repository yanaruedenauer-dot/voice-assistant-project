from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class AccessibilityNeeds:
    wheelchair: Optional[bool] = None
    step_free: Optional[bool] = None
    restroom: Optional[bool] = None


@dataclass
class UserPreferences:
    city: Optional[str] = None
    cuisine: Optional[str] = None
    guests: Optional[int] = None
    time: Optional[str] = None
    accessibility: AccessibilityNeeds = field(default_factory=AccessibilityNeeds)

    # transient dialog state (NEW)
    pending_access_slot: Optional[str] = None
    pending_misses: int = 0
    pending_required_slot: Optional[str] = None
    pending_required_misses: int = 0
