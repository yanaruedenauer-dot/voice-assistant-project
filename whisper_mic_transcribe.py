"""
Whisper Mic Transcribe
----------------------
Record audio from your microphone and transcribe it locally with OpenAI Whisper.

Examples:
  python whisper_mic_transcribe.py --seconds 5 --model small --language de \
      --outfile out.wav --transcript out.txt

  python whisper_mic_transcribe.py --seconds 10 --model base --device cpu
"""

from __future__ import annotations

import argparse
import sys
import time
import queue
from pathlib import Path
from typing import Optional
from scipy.io import wavfile as _wavfile
import whisper
import numpy as np
import sounddevice as sd

import os

os.environ["TOKENIZERS_PARALLELISM"] = "false"

# Prefer 'soundfile' for writing WAV; fall back to scipy
try:
    import soundfile as sf

    _USE_SF = True
except Exception:
    from scipy.io import wavfile as _wavfile

    _USE_SF = False

# Core ML deps
try:
    import torch
    import whisper
except Exception:
    print(
        "ERROR: Missing packages.\n"
        "  pip install openai-whisper sounddevice numpy scipy\n"
        "If ffmpeg is missing:\n"
        "  conda install -c conda-forge ffmpeg",
        file=sys.stderr,
    )
    raise


# ----------------------------- Recording ---------------------------------- #


def record(
    seconds: int,
    samplerate: int = 16000,
    channels: int = 1,
    input_device: int | None = None,
) -> np.ndarray:
    """
    Record audio from default (or given) microphone and return mono float32 array in [-1, 1].
    """
    q: queue.Queue[np.ndarray] = queue.Queue()

    def callback(indata, frames, time_info, status):
        if status:
            print(f"SoundDevice status: {status}", file=sys.stderr)
        q.put(indata.copy())

    stream = sd.InputStream(
        samplerate=samplerate,
        channels=channels,
        dtype="float32",
        callback=callback,
        blocksize=0,
        device=input_device,  # use CLI/param
        latency="low",
    )

    chunks: list[np.ndarray] = []
    with stream:
        print(f" Recording {seconds}s … Speak now")
        start = time.time()
        while (time.time() - start) < seconds:
            try:
                data = q.get(timeout=1.0)
                chunks.append(data)
            except queue.Empty:
                pass

    if not chunks:
        raise RuntimeError(
            "No audio captured. Check mic permissions and default/input device."
        )

    audio = np.concatenate(chunks, axis=0)
    if audio.ndim == 2 and audio.shape[1] > 1:
        audio = np.mean(audio, axis=1)
    else:
        audio = audio.reshape(-1)
    return audio


def save_wav(path: Path, audio: np.ndarray, samplerate: int = 16000) -> None:
    """Save float32 mono audio to WAV. Uses soundfile if available, otherwise scipy."""
    if _USE_SF:
        sf.write(str(path), audio, samplerate)  # float32 OK
    else:
        # convert to int16 for scipy
        pcm16 = np.clip(audio, -1.0, 1.0)
        pcm16 = (pcm16 * 32767.0).astype(np.int16)
        _wavfile.write(str(path), samplerate, pcm16)


#  Transcription ------------------------------- #


def pick_device(user_device: Optional[str]) -> str:
    """Choose device; honor user choice if provided."""
    if user_device:
        return user_device
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return "mps"  # Apple Silicon GPU
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"


_MODEL = None  # cache


def get_model(model_name: str, device: str):
    global _MODEL
    if _MODEL is None:
        print(f" Loading Whisper model '{model_name}' on {device} (one-time)…")
        _MODEL = whisper.load_model(model_name, device=device)
    return _MODEL


def transcribe(
    model_name: str, wav_path: Path, language: Optional[str], device: str, **opts
) -> str:
    """
    Transcribe a WAV with Whisper. Extra options (temperature, initial_prompt, etc.)
    are accepted via **opts and forwarded to Whisper.
    """
    model = get_model(model_name, device)
    fp16 = device != "cpu"
    print(f"Transcribing: {wav_path.name}")
    result = model.transcribe(
        str(wav_path),
        language=language,
        fp16=fp16,
        condition_on_previous_text=False,
        **opts,  # forward temperature, initial_prompt, etc.
    )
    return (result.get("text") or "").strip()


# --------------------------------- CLI ------------------------------------- #


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Record audio from mic and transcribe with OpenAI Whisper."
    )
    ap.add_argument(
        "--seconds", type=int, default=10, help="Recording duration (seconds)"
    )
    ap.add_argument("--model", default="small", help="tiny|base|small|medium|large")
    ap.add_argument("--outfile", default="recording.wav", help="WAV output path")
    ap.add_argument("--transcript", default=None, help="Optional transcript .txt path")
    ap.add_argument("--language", default=None, help="Language code like 'de' or 'en'")
    ap.add_argument("--device", default=None, help="cpu | mps | cuda")
    ap.add_argument(
        "--input-device",
        type=int,
        default=None,
        help="Mic input device index (see sounddevice.query_devices())",
    )
    args = ap.parse_args()

    wav_path = Path(args.outfile)

    # 1) Record
    audio = record(
        seconds=args.seconds,
        samplerate=16000,
        channels=1,
        input_device=args.input_device,
    )

    # 2) Save WAV
    save_wav(wav_path, audio, samplerate=16000)
    print(f" WAV saved to: {wav_path}")

    # 3) Transcribe
    device = pick_device(args.device)
    text = transcribe(args.model, wav_path, args.language, device)

    # 4) Output
    print("\n=== TRANSCRIPT ===")
    print(text if text else "[No speech detected]")

    if args.transcript:
        Path(args.transcript).write_text((text or "") + "\n", encoding="utf-8")
        print(f"\n Transcript saved to: {args.transcript}")


# --------------- Helper used by run_local.py (voice I/O) ------------------- #


def transcribe_once(
    seconds: int = 5,
    model: str = "small",
    language: str | None = None,
    device: str | None = None,
    input_device: int | None = None,
    temperature: float = 0.0,
    initial_prompt: str | None = None,
) -> str:
    """
    Record from the microphone for `seconds` and return a Whisper transcript.
    - Never prints the transcript (so no duplicates).
    - Always returns a string ("" on failure).
    - Safely removes the temporary WAV.
    """
    from pathlib import Path

    tmp_wav = Path(".tmp_whisper_recording.wav")
    text: str = ""

    try:
        # 1) Record
        audio = record(
            seconds=seconds,
            samplerate=16000,
            channels=1,
            input_device=input_device,
        )

        # 2) Save temporary WAV
        save_wav(tmp_wav, audio, samplerate=16000)

        # 3) Transcribe (no printing here)
        dev = pick_device(device)
        result = transcribe(
            model,  # model name, e.g. "base"
            tmp_wav,  # Path to wav
            language,  # e.g. "de" or "en"
            dev,  # "cpu" | "mps" | "cuda"
            temperature=temperature,
            initial_prompt=initial_prompt,
        )

        # Ensure a string is returned
        text = result or ""
        return text

    except Exception as e:
        # Keep helper silent except for a short warning
        print(f"[WARN] Transcription failed: {e}")
        return ""

    finally:
        # 4) Cleanup
        try:
            if tmp_wav.exists():
                tmp_wav.unlink()
        except Exception:
            pass


if __name__ == "__main__":
    main()
