import pandas as pd

BOOL_TRUE = {"true", "1", "yes", "y", "t"}
BOOL_FALSE = {"false", "0", "no", "n", "f", ""}


def _to_bool(x):
    if pd.isna(x):
        return None
    s = str(x).strip().lower()
    if s in BOOL_TRUE:
        return True
    if s in BOOL_FALSE:
        return False
    return None  # unknown / not provided


def load_restaurants(csv_path: str) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    # Ensure columns exist
    for col in ["access_wheelchair", "access_step_free", "access_restroom"]:
        if col not in df.columns:
            df[col] = None
    # Normalize booleans
    for col in ["access_wheelchair", "access_step_free", "access_restroom"]:
        df[col] = df[col].apply(_to_bool)
    return df
