
# Jeeves — Voice Assistant for Restaurant Booking (Phase 2 Starter)

This repository scaffolds the **technical environment and frameworks** for Phase 2 (Development/Reflection) based on the Phase 1 concept and tutor feedback.

## Core modules (aligned with diagram)
- **ASR (Speech-to-Text)**: Whisper (local) with optional cloud fallback.
- **NLU (Intent/Slots + Sentiment)**: PyTorch/Transformers baseline; intent & entity schema in `data/training/intents.yml`.
- **Recommender**: Transparent ranking; attributes include distance, rating, price, **accessibility** (step-free, restrooms, parking), and user prefs. 
- **Booking**: Abstraction for booking providers (OpenTable adapter placeholder) plus mock provider.
- **TTS (Text-to-Speech)**: Coqui TTS (local) with optional cloud fallback.
- **Security/Privacy**: GDPR-first design; data minimization, consent flags, secure secrets, logging with redaction.

## Quickstart
```bash
# 1) Create environment
python -m venv .venv && source .venv/bin/activate
python -m pip install --upgrade pip

# 2) Install dependencies
pip install -r requirements.txt

# 3) (Optional) Install faster-whisper wheels that fit your platform (see docs)
# pip install faster-whisper

# 4) Pre-commit hooks
pre-commit install

# 5) Run a local demo (mock pipeline)
./scripts/run_local.sh
```

## Configuration
- Copy `.env.example` to `.env` and fill in keys if you will use external APIs.
- See `configs/app.yaml` for feature flags (e.g., multilingual, sentiment_on, cloud_fallbacks).

## Evaluation (initial plan)
See `EVALUATION.md` for metrics: ASR WER, Intent F1, Slot F1, Rec @k, Booking success, and latency.

## Security & Privacy
See `SECURITY.md` and `PRIVACY.md` (consent, retention, deletion, encryption at-rest/in-transit, logging redaction).

## CI
GitHub Actions workflow in `.github/workflows/ci.yml` runs lint & tests.

---
**Note:** This is a starter. Replace mocks with real providers as you progress.
