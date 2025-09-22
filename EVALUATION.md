
# Evaluation Plan (Phase 2)

## ASR
- **WER** (word error rate) on a small test set (EN/DE).
- Latency from audio end to transcript.

## NLU
- **Intent F1** and **Slot F1** on a labeled set.
- Confusion analysis; threshold-based fallback.

## Dialogue / UX
- **Conversation success rate** (fills: cuisine, time, party size, dietary, accessibility).
- **Time-to-decision** (goal: < 2 min to booking confirmation).

## Recommender
- Offline: Precision@k / Recall@k on synthetic preference labels.
- Online (manual eval): Top-3 relevance judgments; transparency check.

## System
- End-to-end latency: voice-in → recommendation <= 2s (target).
- Error budgets and fallback coverage.
