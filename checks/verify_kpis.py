"""Recompute the dashboard numbers from the raw CSVs with pandas.

A cross-check between the BI layer and the data: every figure on the
dashboard and in the README should match what this script prints.

Run from the repo root:
    python checks/verify_kpis.py
"""
from pathlib import Path

import pandas as pd

DATA = Path(__file__).resolve().parent.parent / "data"

sales = pd.read_csv(DATA / "fact_sales.csv")
dates = pd.read_csv(DATA / "dim_date.csv", usecols=["DateKey", "Year"])
products = pd.read_csv(DATA / "dim_product.csv", usecols=["ProductKey", "Category"])
customers = pd.read_csv(DATA / "dim_customer.csv", usecols=["CustomerKey"])
stores = pd.read_csv(DATA / "dim_store.csv", usecols=["StoreKey"])

# Referential integrity: every foreign key in the fact must exist in its dimension.
for key, dim in [("DateKey", dates), ("ProductKey", products),
                 ("CustomerKey", customers), ("StoreKey", stores)]:
    orphans = (~sales[key].isin(dim[key])).sum()
    print(f"orphan {key:<12} {orphans}")

df = sales.merge(dates, on="DateKey").merge(products, on="ProductKey")
df["Revenue"] = df.UnitPrice * (1 - df.Discount) * df.Quantity  # same as the SUMX measure
df["Cost"] = df.UnitCost * df.Quantity
df["GrossProfit"] = df.Revenue - df.Cost

rev, gp = df.Revenue.sum(), df.GrossProfit.sum()
by_year = df.groupby("Year").Revenue.sum()

print(f"\norder lines      {len(df):,}")
print(f"Revenue          € {rev:,.0f}")
print(f"Gross Profit     € {gp:,.0f}")
print(f"Margin %         {gp / rev:.2%}")
print(f"Revenue YoY %    {by_year[2025] / by_year[2024] - 1:.2%}   "
      f"(2024 € {by_year[2024]:,.0f} -> 2025 € {by_year[2025]:,.0f})")

cat = df.groupby("Category")[["Revenue", "GrossProfit"]].sum()
cat["rev_share"] = cat.Revenue / rev
cat["gp_share"] = cat.GrossProfit / gp
growth = df.pivot_table(index="Category", columns="Year", values="Revenue", aggfunc="sum")
cat["yoy"] = growth[2025] / growth[2024] - 1
cat["share_of_growth"] = (growth[2025] - growth[2024]) / (by_year[2025] - by_year[2024])
print("\nBy category\n", cat.round(3).to_string())

band = df.groupby("Discount").agg(
    lines=("Revenue", "size"),
    revenue=("Revenue", "sum"),
    gross_profit=("GrossProfit", "sum"),
    units_per_line=("Quantity", "mean"),
)
band["share_of_lines"] = band.lines / len(df)
band["margin"] = band.gross_profit / band.revenue
print("\nBy discount band\n",
      band[["share_of_lines", "margin", "units_per_line"]].round(3).to_string())
print(f"\nlines with any discount: {(df.Discount > 0).mean():.1%}")
