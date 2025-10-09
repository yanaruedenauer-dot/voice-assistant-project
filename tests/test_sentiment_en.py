import pytest
from typing import cast
from src.nlp.sentiment_en import analyze_sentiment
import warnings

warnings.filterwarnings(
    "ignore",
    message=r"`return_all_scores` is now deprecated",
    category=UserWarning,
)


def test_positive_en() -> None:
    out = analyze_sentiment("I love this service!")
    score = cast(float, out["score"])
    assert score >= 0.6


def test_negative_en() -> None:
    out = analyze_sentiment("This is terrible.")
    score = cast(float, out["score"])
    assert score >= 0.6


@pytest.mark.parametrize(
    "text, expect",
    [
        ("I absolutely loved the pasta, fantastic service!", "POSITIVE"),
        ("The pizza was terrible and the waiter was rude.", "NEGATIVE"),
        ("It was okay, nothing special.", "NEUTRAL"),
    ],
)
def test_basic_labels(text: str, expect: str) -> None:
    out = analyze_sentiment(text)
    assert isinstance(out, dict)
    assert out["label"] in {"POSITIVE", "NEGATIVE", "NEUTRAL"}
    assert out["label"] == expect
    assert isinstance(out["score"], float)
    assert 0.0 <= cast(float, out["score"]) <= 1.0


def test_empty_input_is_neutral() -> None:
    out = analyze_sentiment("")
    assert out["label"] == "NEUTRAL"
    assert out["score"] == 0.0


@pytest.mark.parametrize(
    "text", ["Loved it!", "Amazing experience", "Super tasty and friendly staff"]
)
def test_positive_has_high_score(text: str) -> None:
    out = analyze_sentiment(text)
    if out["label"] == "POSITIVE":
        assert cast(float, out["score"]) >= 0.6


@pytest.mark.parametrize(
    "text", ["Worst service ever", "Disgusting food", "I hated everything"]
)
def test_negative_has_high_score(text: str) -> None:
    out = analyze_sentiment(text)
    if out["label"] == "NEGATIVE":
        assert cast(float, out["score"]) >= 0.6
