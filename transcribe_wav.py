import argparse
import torch
import whisper
from pathlib import Path


def main():
    p = argparse.ArgumentParser()
    p.add_argument("audio", help="Path to WAV/MP3/M4A file")
    p.add_argument(
        "--lang",
        default=None,
        help="Language code (e.g. de, en). Auto-detect if omitted.",
    )
    p.add_argument(
        "--model",
        default="small",
        help="tiny | base | small | medium | large (default: small)",
    )
    p.add_argument(
        "--out", default=None, help="Optional path to save the transcript (txt)"
    )
    p.add_argument("--device", default="cpu", help="cpu | mps | cuda (default: cpu)")
    args = p.parse_args()

    audio_path = Path(args.audio)
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    # pick device
    device = args.device
    if device == "mps" and not torch.backends.mps.is_available():
        print("MPS not available, falling back to CPU")
        device = "cpu"
    if device == "cuda" and not torch.cuda.is_available():
        print("CUDA not available, falling back to CPU")
        device = "cpu"

    print(
        f"Loading Whisper model '{args.model}' on {device} ... (first run may download the model)"
    )
    model = whisper.load_model(args.model, device=device)

    # fp16 only useful on GPU
    fp16 = device != "cpu"

    print(f"Transcribing: {audio_path.name}")
    result = model.transcribe(str(audio_path), language=args.lang, fp16=fp16)

    text = (result.get("text") or "").strip()
    print("\n=== TRANSCRIPT ===")
    print(text if text else "[No speech detected]")

    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
        print(f"\nSaved transcript to: {args.out}")


if __name__ == "__main__":
    main()
