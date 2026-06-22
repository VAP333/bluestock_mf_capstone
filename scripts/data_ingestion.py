import pathlib
import pandas as pd

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"

files = {
    "fund_master":          "01_fund_master.csv",
    "nav_history":          "02_nav_history.csv",
    "aum_by_fund_house":    "03_aum_by_fund_house.csv",
    "monthly_sip_inflows":  "04_monthly_sip_inflows.csv",
    "category_inflows":     "05_category_inflows.csv",
    "industry_folio_count": "06_industry_folio_count.csv",
    "scheme_performance":   "07_scheme_performance.csv",
    "investor_transactions":"08_investor_transactions.csv",
    "portfolio_holdings":   "09_portfolio_holdings.csv",
    "benchmark_indices":    "10_benchmark_indices.csv",
}


def load_datasets():
    dfs = {}
    for name, fname in files.items():
        df = pd.read_csv(RAW / fname)
        dfs[name] = df
        print(f"\n--- {fname} ---")
        print("shape:", df.shape)
        print(df.dtypes)
        print(df.head())

        nulls = df.isnull().sum()
        if nulls.any():
            print("missing values found:")
            print(nulls[nulls > 0])
        else:
            print("no missing values")

    return dfs


def explore_fund_master(df):
    print("\n\n=== fund_master exploration ===")

    print("\nfund houses:", df["fund_house"].nunique())
    print(df["fund_house"].value_counts())

    print("\ncategories:")
    print(df["category"].value_counts())

    print("\nsub_categories:")
    print(df["sub_category"].value_counts())

    print("\nrisk grades:")
    print(df["risk_category"].value_counts())

    print("\nplans:", df["plan"].unique())
    print("amfi code range:", df["amfi_code"].min(), "to", df["amfi_code"].max())


def validate_codes(df_fund, df_nav):
    print("\n\n=== amfi code validation ===")

    master = set(df_fund["amfi_code"])
    nav    = set(df_nav["amfi_code"])

    print("codes in fund_master:", len(master))
    print("codes in nav_history:", len(nav))
    print("codes present in both:", len(master & nav))

    missing = master - nav
    if missing:
        print("codes in fund_master but NOT in nav_history:", sorted(missing))
    else:
        print("all fund_master codes found in nav_history")

    extra = nav - master
    if extra:
        print("extra codes in nav_history:", sorted(extra))
    else:
        print("no extra codes in nav_history")

    rows_per_scheme = df_nav.groupby("amfi_code").size()
    print("\nnav rows per scheme:")
    print(rows_per_scheme.describe())


if __name__ == "__main__":
    dfs = load_datasets()
    explore_fund_master(dfs["fund_master"])
    validate_codes(dfs["fund_master"], dfs["nav_history"])
    print("\ndone.")
