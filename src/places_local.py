import pandas as pd
import unicodedata


def _ascii_lower(s: str) -> str:
    """Normalize text (lowercase, ASCII)."""
    if not isinstance(s, str):
        return ""
    return (
        unicodedata.normalize("NFKD", s)
        .encode("ascii", "ignore")
        .decode("ascii")
        .lower()
        .strip()
    )


def _select_columns(df: pd.DataFrame) -> pd.DataFrame:
    return df[
        [
            "Restaurant Name",
            "City",
            "Cuisines",
            "Average Cost for two",
            "Aggregate rating",
            "Address",
        ]
    ].rename(
        columns={
            "Restaurant Name": "name",
            "City": "city",
            "Cuisines": "cuisine",
            "Average Cost for two": "price",
            "Aggregate rating": "rating",
            "Address": "address",
        }
    )


# Load once globally
_DF_CACHE = None


def load_df(path: str = "data/zomato.csv") -> pd.DataFrame:
    global _DF_CACHE
    if _DF_CACHE is None:
        _DF_CACHE = pd.read_csv(path, encoding="ISO-8859-1")
        _DF_CACHE["cuis_norm"] = _DF_CACHE["Cuisines"].apply(_ascii_lower)
        _DF_CACHE["city_norm"] = _DF_CACHE["City"].apply(_ascii_lower)
    return _DF_CACHE


def search_restaurants_local(df: pd.DataFrame, cuisine: str, city: str, limit: int = 5):
    """Return restaurants matching cuisine and city."""
    c = _ascii_lower(cuisine)
    ci = _ascii_lower(city)
    mask = df["cuis_norm"].str.contains(c, na=False) & df["city_norm"].str.contains(
        ci, na=False
    )
    res = _select_columns(df.loc[mask]).head(limit)
    return res.to_dict(orient="records")


def search_with_fallback(df: pd.DataFrame, cuisine: str, city: str, limit: int = 5):
    """
    Try exact city+cuisine, then fallback to nearest available city with that cuisine,
    then show top restaurants of that cuisine anywhere.
    """
    cuisine = _ascii_lower(cuisine)
    city = _ascii_lower(city)

    # Clean very long/invalid strings from Whisper
    if len(cuisine.split()) > 4 or cuisine.count(" ") > 6:
        cuisine = cuisine.split()[0]
    if len(city.split()) > 3:
        city = city.split()[0]

    # 1) exact match
    primary = search_restaurants_local(df, cuisine, city, limit)
    if primary:
        return {"results": primary, "fallback": None}

    # 2) try cuisine anywhere
    any_cuisine = _select_columns(
        df[df["cuis_norm"].str.contains(cuisine, na=False)]
    ).head(limit)
    if any_cuisine.shape[0] > 0:
        return {
            "results": any_cuisine.to_dict(orient="records"),
            "fallback": {"type": "global_cuisine"},
        }

    # 3) no matches at all
    return {"results": [], "fallback": None}
