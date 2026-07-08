from pathlib import Path
import pandas as pd

RAW_DIR = Path("data/raw")

files = [
    "companies.xlsx",
    "profitandloss.xlsx",
    "balancesheet.xlsx",
    "cashflow.xlsx",
    "financial_ratios.xlsx",
    "stock_prices.xlsx",
    "sectors.xlsx",
    "peer_groups.xlsx",
]

for file in files:
    path = RAW_DIR / file

    print("\n" + "=" * 80)
    print(file)
    print("=" * 80)

    if not path.exists():
        print("File not found")
        continue

    df = pd.read_excel(path)

    print("Shape:", df.shape)
    print("\nColumns:")
    for col in df.columns:
        print("-", col)

    print("\nFirst 3 rows:")
    print(df.head(3))