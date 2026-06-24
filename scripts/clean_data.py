import pathlib
import pandas as pd
import numpy as np

RAW  = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
PROC = pathlib.Path(__file__).resolve().parent.parent / "data" / "processed"
PROC.mkdir(parents=True, exist_ok=True)


def clean_nav_history():
    df = pd.read_csv(RAW / "02_nav_history.csv")
    print("nav_history - raw shape:", df.shape)

    df["date"] = pd.to_datetime(df["date"])
    df.sort_values(["amfi_code", "date"], inplace=True)
    df.reset_index(drop=True, inplace=True)

    # remove duplicates
    before = len(df)
    df.drop_duplicates(subset=["amfi_code", "date"], inplace=True)
    print(f"  duplicates removed: {before - len(df)}")

    # forward fill missing dates (holidays/weekends)
    # reindex each scheme to full trading date range then ffill
    all_dates = pd.date_range(df["date"].min(), df["date"].max(), freq="B")
    filled = []
    for code, grp in df.groupby("amfi_code"):
        grp = grp.set_index("date").reindex(all_dates)
        grp["amfi_code"] = code
        grp["nav"] = grp["nav"].ffill()
        grp.index.name = "date"
        grp.reset_index(inplace=True)
        filled.append(grp)

    df = pd.concat(filled, ignore_index=True)

    # drop rows where nav still null (start of series before first data point)
    df.dropna(subset=["nav"], inplace=True)

    # validate nav > 0
    invalid = df[df["nav"] <= 0]
    if not invalid.empty:
        print(f"  WARNING: {len(invalid)} rows with nav <= 0, dropping")
        df = df[df["nav"] > 0]

    df.sort_values(["amfi_code", "date"], inplace=True)
    df.reset_index(drop=True, inplace=True)

    out = PROC / "clean_nav_history.csv"
    df.to_csv(out, index=False)
    print(f"  clean shape: {df.shape}  -> saved {out.name}")
    return df


def clean_investor_transactions():
    df = pd.read_csv(RAW / "08_investor_transactions.csv")
    print("investor_transactions - raw shape:", df.shape)

    df["transaction_date"] = pd.to_datetime(df["transaction_date"])

    # standardise transaction_type casing just in case
    df["transaction_type"] = df["transaction_type"].str.strip().str.title()
    valid_types = {"Sip", "Lumpsum", "Redemption"}
    bad_types = df[~df["transaction_type"].isin(valid_types)]
    if not bad_types.empty:
        print(f"  WARNING: unexpected transaction_type values: {bad_types['transaction_type'].unique()}")

    # rename SIP -> SIP (title case gives 'Sip', fix that)
    df["transaction_type"] = df["transaction_type"].replace("Sip", "SIP")

    # validate amount
    before = len(df)
    df = df[df["amount_inr"] > 0]
    print(f"  rows with amount <= 0 dropped: {before - len(df)}")

    # check kyc
    valid_kyc = {"Verified", "Pending"}
    bad_kyc = df[~df["kyc_status"].isin(valid_kyc)]
    if not bad_kyc.empty:
        print(f"  WARNING: unexpected kyc_status: {bad_kyc['kyc_status'].unique()}")
    else:
        print(f"  kyc_status values ok: {df['kyc_status'].unique().tolist()}")

    df.reset_index(drop=True, inplace=True)
    out = PROC / "clean_investor_transactions.csv"
    df.to_csv(out, index=False)
    print(f"  clean shape: {df.shape}  -> saved {out.name}")
    return df


def clean_scheme_performance():
    df = pd.read_csv(RAW / "07_scheme_performance.csv")
    print("scheme_performance - raw shape:", df.shape)

    numeric_cols = [
        "return_1yr_pct", "return_3yr_pct", "return_5yr_pct",
        "benchmark_3yr_pct", "alpha", "beta", "sharpe_ratio",
        "sortino_ratio", "std_dev_ann_pct", "max_drawdown_pct",
        "aum_crore", "expense_ratio_pct"
    ]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")
        nulls = df[col].isnull().sum()
        if nulls:
            print(f"  WARNING: {col} has {nulls} non-numeric values")

    # expense ratio should be between 0.1 and 2.5
    out_of_range = df[(df["expense_ratio_pct"] < 0.1) | (df["expense_ratio_pct"] > 2.5)]
    if not out_of_range.empty:
        print(f"  WARNING: {len(out_of_range)} funds with expense_ratio outside 0.1-2.5%")
        print(out_of_range[["scheme_name", "expense_ratio_pct"]])
    else:
        er_min = df["expense_ratio_pct"].min()
        er_max = df["expense_ratio_pct"].max()
        print(f"  expense_ratio range: {er_min} - {er_max}  (all within 0.1-2.5%)")

    # flag negative sharpe - not dropping, just noting
    neg_sharpe = df[df["sharpe_ratio"] < 0]
    if not neg_sharpe.empty:
        print(f"  funds with negative sharpe: {len(neg_sharpe)}")
        print(neg_sharpe[["scheme_name", "sharpe_ratio"]])
    else:
        print("  no negative sharpe ratios")

    out = PROC / "clean_scheme_performance.csv"
    df.to_csv(out, index=False)
    print(f"  clean shape: {df.shape}  -> saved {out.name}")
    return df


def clean_passthrough(fname, outname):
    # for datasets that are already clean, just copy to processed with date parsing
    df = pd.read_csv(RAW / fname)
    # try to parse any column that looks like a date
    for col in df.columns:
        if "date" in col or "month" in col:
            try:
                df[col] = pd.to_datetime(df[col])
            except Exception:
                pass
    out = PROC / outname
    df.to_csv(out, index=False)
    print(f"{fname} -> {outname}  shape: {df.shape}")
    return df


if __name__ == "__main__":
    print("=== cleaning nav_history ===")
    clean_nav_history()

    print("\n=== cleaning investor_transactions ===")
    clean_investor_transactions()

    print("\n=== cleaning scheme_performance ===")
    clean_scheme_performance()

    print("\n=== passthrough cleans ===")
    clean_passthrough("01_fund_master.csv",          "clean_fund_master.csv")
    clean_passthrough("03_aum_by_fund_house.csv",    "clean_aum_by_fund_house.csv")
    clean_passthrough("04_monthly_sip_inflows.csv",  "clean_monthly_sip_inflows.csv")
    clean_passthrough("05_category_inflows.csv",     "clean_category_inflows.csv")
    clean_passthrough("06_industry_folio_count.csv", "clean_industry_folio_count.csv")
    clean_passthrough("09_portfolio_holdings.csv",   "clean_portfolio_holdings.csv")
    clean_passthrough("10_benchmark_indices.csv",    "clean_benchmark_indices.csv")

    print("\ndone.")
