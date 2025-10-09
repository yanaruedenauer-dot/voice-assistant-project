from __future__ import annotations

import argparse
import os
import sys
from typing import Any, Dict, Protocol, runtime_checkable
from typing import Tuple, cast

# make project root importable (so intent_parser.py at repo root works)
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import torch
import whisper  # mypy is configured to ignore missing stubs for this

from intent_parser import parse_intent  # don't import Slots to keep this generic
from dialog_manager import next_action
from recommender_stub import recommend, format_cards


def pick_device(prefer: str | None) -> str:
    if prefer:
        return prefer
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return "mps"
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"


def transcribe(
    path: str,
    model_name: str = "small",
    lang: str | None = None,
    device: str | None = None,
) -> str:
    dev = pick_device(device)
    # mps can be flaky for Whisper; CPU is more deterministic in small scripts
    if dev == "mps":
        dev = "cpu"
    model = whisper.load_model(model_name, device=dev)
    fp16 = dev != "cpu"
    res = model.transcribe(path, language=lang, fp16=fp16)
    return (res.get("text") or "").strip()


@runtime_checkable
class HasToDict(Protocol):
    def to_dict(self) -> Dict[str, Any]: ...


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("audio")
    ap.add_argument("--lang", default="de")
    ap.add_argument("--model", default="small")
    ap.add_argument("--device", default="cpu")
    args = ap.parse_args()

    text: str = transcribe(
        args.audio, model_name=args.model, lang=args.lang, device=args.device
    )

    print("\n=== TRANSCRIPT ===")
    print(text or "[No speech detected]")

    # ---- NLU ----
    intent, slots = cast(Tuple[str, Any], parse_intent(text))
    print("\n=== NLU ===")
    print("intent:", intent)
    print("slots:", slots)

    # ---- Convert slots safely to a dictionary ----
    if isinstance(slots, dict):
        slot_dict: Dict[str, Any] = dict(slots)
    elif isinstance(slots, HasToDict):
        slot_dict = slots.to_dict()
    else:
        slot_dict = {}

    # ---- Dialog step ----
    action, payload = next_action(intent, slot_dict)
    print("\n=== DIALOG ===")
    print("action:", action)
    print("message:", payload.get("message"))

    # ---- Recommendation (if applicable) ----
    if action == "recommend":
        recs = recommend(slot_dict)  # keep signature consistent with your stub
        print("\n=== RECOMMENDATIONS ===")
        print(format_cards(recs))


if __name__ == "__main__":
    main()
