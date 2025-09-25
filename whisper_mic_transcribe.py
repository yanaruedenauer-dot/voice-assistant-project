#!/usr/bin/env python3
"""
Whisper Mic Transcribe
----------------------
Record audio from your microphone and transcribe it locally with OpenAI Whisper.

Usage (examples):
  # record 5s and transcribe (German forced), save WAV + TXT
  python whisper_mic_transcribe.py --seconds 5 --model small --language de \
      --outfile out.wav --transcript out.txt

  # record 10s, auto language detect, CPU
  python whisper_mic_transcribe.py --seconds 10 --model base --device cpu

Dependencies (install inside your conda env 'voice'):
  pip install openai-whisper sounddevice numpy scipy
  # if ffmpeg missing:
  # conda install -c conda-forge ffmpeg
"""
import argparse
import sys
import time
import queue
from pathlib import Path

import numpy as np
import sounddevice as sd
from scipy.io.wavfile import write as wav_write

try:
    import torch
    import whisper
except Exception:
    print(
        "ERROR: Missing packages. Install inside your env:\n"
        "  pip install openai-whisper sounddevice numpy scipy\n"
        "  conda install -c conda-forge ffmpeg  # if needed",
        file=sys.stderr,
    )
    raise

# ----------------------------- Recording ---------------------------------- #


def record(seconds: int, samplerate: int = 16000, channels: int = 1) -> np.ndarray:
    """
    Record audio from default microphone.
    Returns mono float32 array in range [-1, 1].
    """
    q: queue.Queue[np.ndarray] = queue.Queue()

    def callback(indata, frames, time_info, status):
        if status:
            # over/underruns etc. are non-fatal; print to stderr
            print(f"SoundDevice status: {status}", file=sys.stderr)
        q.put(indata.copy())

    stream = sd.InputStream(
        samplerate=samplerate,
        channels=channels,
        dtype="float32",
        callback=callback,
        blocksize=0,
    )

    chunks = []
    with stream:
        print(f"Recording {seconds} seconds... Speak now 🎤")
        start = time.time()
        while (time.time() - start) < seconds:
            try:
                data = q.get(timeout=1.0)
                chunks.append(data)
            except queue.Empty:
                pass

    if not chunks:
        raise RuntimeError(
            "No audio captured. Check mic permissions and default input device."
        )
    audio = np.concatenate(chunks, axis=0)
    # to mono
    if audio.ndim == 2 and audio.shape[1] > 1:
        audio = np.mean(audio, axis=1)
    else:
        audio = audio.reshape(-1)
    return audio


def save_wav(path: Path, audio: np.ndarray, samplerate: int = 16000) -> None:
    """Save float32 mono audio to 16-bit PCM WAV."""
    audio_int16 = np.clip(audio * 32767, -32768, 32767).astype(np.int16)
    wav_write(str(path), samplerate, audio_int16)


# ----------------------------- Transcription ------------------------------- #


def pick_device(user_device: str | None) -> str:
    """Choose best available device unless user fixed one."""
    if user_device:
        return user_device
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return "mps"  # Apple Silicon GPU
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"


def transcribe(model_name: str, wav_path: Path, language: str | None, device: str):
    print(
        f"Loading Whisper model '{model_name}' on {device} (first run will download the model)..."
    )
    model = whisper.load_model(model_name, device=device)
    fp16 = device != "cpu"  # half precision only on GPU
    print(f"Transcribing: {wav_path.name}")
    result = model.transcribe(str(wav_path), language=language, fp16=fp16)
    return (result.get("text") or "").strip()


# ----------------------------- CLI ---------------------------------------- #


def main():
    ap = argparse.ArgumentParser(
        description="Record audio from mic and transcribe with OpenAI Whisper."
    )
    ap.add_argument(
        "--seconds",
        type=int,
        default=10,
        help="Recording duration (seconds). Default: 10",
    )
    ap.add_argument(
        "--model",
        default="small",
        help="Whisper model: tiny|base|small|medium|large (default: small)",
    )
    ap.add_argument(
        "--outfile",
        default="recording.wav",
        help="Where to save the WAV (default: recording.wav)",
    )
    ap.add_argument(
        "--transcript", default=None, help="Optional path to save transcript .txt"
    )
    ap.add_argument(
        "--language",
        default=None,
        help="Force language code, e.g. 'de' or 'en' (auto-detect if omitted)",
    )
    ap.add_argument(
        "--device",
        default=None,
        help="Force device: cpu | mps | cuda (auto if omitted)",
    )
    args = ap.parse_args()

    wav_path = Path(args.outfile)

    # 1) Record
    try:
        audio = record(seconds=args.seconds, samplerate=16000, channels=1)
    except Exception as e:
        print(f"ERROR during recording: {e}", file=sys.stderr)
        print(
            "On macOS, grant mic access: System Settings → Privacy & Security → Microphone.",
            file=sys.stderr,
        )
        sys.exit(2)

    # 2) Save WAV
    try:
        save_wav(wav_path, audio, samplerate=16000)
        print(f"Saved recording to: {wav_path}")
    except Exception as e:
        print(f"ERROR saving WAV: {e}", file=sys.stderr)
        sys.exit(3)

    # 3) Transcribe
    try:
        device = pick_device(args.device)
        text = transcribe(args.model, wav_path, args.language, device)
        print("\n=== TRANSCRIPT ===")
        print(text if text else "[No speech detected]")
        if args.transcript:
            Path(args.transcript).write_text((text or "") + "\n", encoding="utf-8")
            print(f"\nTranscript saved to: {args.transcript}")
    except Exception as e:
        print(f"ERROR during transcription: {e}", file=sys.stderr)
        print(
            "Check that ffmpeg is installed and on PATH. In conda:\n"
            "  conda install -c conda-forge ffmpeg",
            file=sys.stderr,
        )
        sys.exit(4)


if __name__ == "__main__":
    main()
