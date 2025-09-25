# scripts/whisper_nlu_cli.py
from __future__ import annotations

import argparse
import torch
import whisper

from intent_parser import parse_intent, Slots


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
    if dev == "mps":  # Stabilität auf macOS
        dev = "cpu"
    model = whisper.load_model(model_name, device=dev)
    fp16 = dev != "cpu"
    res = model.transcribe(path, language=lang, fp16=fp16)
    return (res.get("text") or "").strip()


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

    intent: str
    slots: Slots
    intent, slots = parse_intent(text)

    print("\n=== TRANSCRIPT ===")
    print(text or "[No speech detected]")
    print("\n=== NLU ===")
    print("intent:", intent)
    print("slots:", slots)


if __name__ == "__main__":
    main()
