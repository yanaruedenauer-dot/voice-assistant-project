import pandas as pd

CSV = "data/restaurants.csv"
df = pd.read_csv(CSV)

for col in ["access_wheelchair", "access_step_free", "access_restroom"]:
    if col not in df.columns:
        df[col] = False  # default

df.to_csv(CSV, index=False)
print("✅ Added accessibility columns (default=False) to", CSV)
