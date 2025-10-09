import unicodedata
import difflib
import pandas as pd


def ascii_lower(s: str) -> str:
    s = str(s)
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    return s.lower().strip()


def list_known_cuisines(df: pd.DataFrame, min_count: int = 20) -> list[str]:
    vals = []
    for x in df["Cuisines"].dropna():
        vals += [c.strip() for c in str(x).split(",")]
    s = pd.Series(vals).value_counts()
    return [str(c) for c, n in s.items() if n >= min_count]


def fuzzy_choice(query: str, candidates: list[str], cutoff: float = 0.6) -> str | None:
    q = ascii_lower(query)
    cand_norm = {ascii_lower(c): c for c in candidates}
    match = difflib.get_close_matches(q, list(cand_norm.keys()), n=1, cutoff=cutoff)
    return cand_norm[match[0]] if match else None


def normalize_city(raw: str) -> str:
    t = (raw or "").strip().lower()
    # quick mappings
    nonlatin_map = {
        "برلين": "berlin",  # Arabic
        "берлин": "berlin",  # Russian
        "berlín": "berlin",  # accented
    }
    return nonlatin_map.get(t, t)
