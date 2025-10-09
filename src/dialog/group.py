from __future__ import annotations
import re
from typing import Optional
from ..models.group import GroupState
from ..models.preferences import UserPreferences
from .basic_parse import _maybe_update_basic_prefs
from .slots import update_accessibility_from_text

# Commands:
#   "start group" / "start group of 3"
#   "add" (add member)
#   "end group" / "finish group"
_START_RE = re.compile(r"\b(start|create|new)\s+group(?:\s+of\s+(\d+))?\b", re.I)
_ADD_RE = re.compile(r"\b(add|member|person)\b", re.I)
_END_RE = re.compile(r"\b(end|finish)\s+group\b", re.I)


def _normalize_group_text(text: str) -> str:
    t = (text or "").strip().lower()
    # common whisper mishears
    t = t.replace("and group", "end group")
    t = t.replace("in group", "end group")
    t = t.replace("ant group", "end group")
    t = t.replace("en group", "end group")
    t = t.replace("finish the group", "finish group")
    return t


def maybe_handle_group_command(group: GroupState, text: str) -> Optional[str]:
    t = _normalize_group_text(text)

    m = _START_RE.search(t)
    if m:
        size = None
        if m.group(2):
            try:
                size = int(m.group(2))
            except (TypeError, ValueError):
                size = None
        group.active = True
        group.size = size
        group.members.clear()
        return f"Group mode started.{(' Expecting '+str(size)+' people.' if size else '')} Say 'add' to add a member."

    if _END_RE.search(t):
        group.active = False
        # NEW: produce immediate guidance
        return "Group mode ended. Say 'show results' to merge preferences."

    if group.active and _ADD_RE.search(t):
        group.members.append(UserPreferences())
        return "OK. Describe this member's preferences (city, cuisine, time, and any accessibility needs)."

    return None


def update_last_member(group: GroupState, text: str) -> None:
    """
    Updates the most recently added member (or creates one) from free text.
    """
    if not group.members:
        group.members.append(UserPreferences())
    member = group.members[-1]
    _maybe_update_basic_prefs(member, text)
    update_accessibility_from_text(member, text)
