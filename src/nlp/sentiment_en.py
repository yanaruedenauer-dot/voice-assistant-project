from __future__ import annotations
from typing import Dict
from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    TextClassificationPipeline,
)

_MODEL_NAME = "nlptown/bert-base-multilingual-uncased-sentiment"

_PIPE: TextClassificationPipeline | None = None


def _get_pipeline() -> TextClassificationPipeline:
    global _PIPE
    if _PIPE is None:
        tok = AutoTokenizer.from_pretrained(_MODEL_NAME)
        mdl = AutoModelForSequenceClassification.from_pretrained(_MODEL_NAME)
        _PIPE = TextClassificationPipeline(
            model=mdl, tokenizer=tok, framework="pt", return_all_scores=False
        )
    return _PIPE


def analyze_sentiment(text: str) -> Dict[str, object]:
    """
    Return {"label": "NEGATIVE|NEUTRAL|POSITIVE", "score": float}
    (Maps 1–5 star output into 3 sentiment categories.)
    """
    if not text or not text.strip():
        return {"label": "NEUTRAL", "score": 0.0}

    pipe = _get_pipeline()
    out = pipe(text)[0]  # {'label': '4 stars', 'score': 0.9}
    stars = int(out["label"].split()[0])

    if stars <= 2:
        label = "NEGATIVE"
        score = 1 - (stars - 1) / 4
    elif stars == 3:
        label = "NEUTRAL"
        score = 0.5
    else:
        label = "POSITIVE"
        score = (stars - 3) / 2

    return {"label": label, "score": float(score)}
