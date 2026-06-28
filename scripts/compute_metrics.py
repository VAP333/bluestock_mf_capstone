import pathlib
import warnings
warnings.filterwarnings("ignore")

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats

PROC   = pathlib.Path(__file__).resolve().parent.parent / "data" / "processed"
CHARTS = pathlib.Path(__file__).resolve().parent.parent / "reports" / "charts"
CHARTS.mkdir(parents=True, exist_ok=True)

sns.set_theme(style="whitegrid")
plt.rcParams.update({"font.size": 11, "figure.dpi": 120})

RF_ANNUAL = 0.065   # RBI repo rate proxy
RF_DAILY  = RF_ANNUAL / 252


# load data
df_nav   = pd.read_csv(PROC / "clean_nav_history.csv",    parse_dates=["date"])
df_fund  = pd.read_csv(PROC / "clean_fund_master.csv")
df_bench = pd.read_csv(PROC / "clean_benchmark_indices.csv", parse_dates=["date"])

nav = df_nav.merge(df_fund[["amfi_code","scheme_name","fund_house",
                              "sub_category","plan","expense_ratio_pct"]], on="amfi_code")


# ── task 1: daily returns ──────────────────────────────────────────────────

def compute_daily_returns(df):
    df = df.sort_values(["amfi_code","date"])
    df["daily_return"] = df.groupby("amfi_code")["nav"].pct_change()
    return df

nav = compute_daily_returns(nav)

# quick sanity check
r = nav["daily_return"].dropna()
print("daily return stats:")
print(f"  mean={r.mean():.5f}  std={r.std():.4f}  min={r.min():.4f}  max={r.max():.4f}")
print(f"  values outside +-10%: {((r < -0.10) | (r > 0.10)).sum()}")


# ── task 2: CAGR ──────────────────────────────────────────────────────────

def cagr(nav_start, nav_end, years):
    if nav_start <= 0 or years <= 0:
        return np.nan
    return (nav_end / nav_start) ** (1 / years) - 1

def compute_cagr_all(df):
    results = []
    end_date = df["date"].max()

    for code, grp in df.groupby("amfi_code"):
        grp = grp.sort_values("date")
        nav_end = grp.iloc[-1]["nav"]

        row = {"amfi_code": code}
        for label, years in [("1yr", 1), ("3yr", 3), ("5yr", 5)]:
            target = end_date - pd.DateOffset(years=years)
            before = grp[grp["date"] <= target]
            if before.empty:
                row[f"cagr_{label}"] = np.nan
            else:
                nav_start = before.iloc[-1]["nav"]
                actual_years = (end_date - before.iloc[-1]["date"]).days / 365.25
                row[f"cagr_{label}"] = cagr(nav_start, nav_end, actual_years)

        results.append(row)

    return pd.DataFrame(results)

cagr_df = compute_cagr_all(nav)
cagr_df = cagr_df.merge(df_fund[["amfi_code","scheme_name","fund_house",
                                   "sub_category","plan"]], on="amfi_code")
print("\nCAGR computed for", len(cagr_df), "schemes")
print(cagr_df[["scheme_name","cagr_1yr","cagr_3yr","cagr_5yr"]].head(5).to_string(index=False))


# ── task 3: Sharpe ratio ───────────────────────────────────────────────────

def compute_sharpe(df):
    results = []
    for code, grp in df.groupby("amfi_code"):
        r = grp["daily_return"].dropna()
        if len(r) < 50:
            continue
        excess  = r - RF_DAILY
        sharpe  = (excess.mean() / r.std()) * np.sqrt(252)
        results.append({"amfi_code": code, "sharpe": round(sharpe, 4)})
    return pd.DataFrame(results)

sharpe_df = compute_sharpe(nav)
print(f"\nSharpe computed: min={sharpe_df['sharpe'].min():.3f}  max={sharpe_df['sharpe'].max():.3f}")


# ── task 4: Sortino ratio ──────────────────────────────────────────────────

def compute_sortino(df):
    results = []
    for code, grp in df.groupby("amfi_code"):
        r = grp["daily_return"].dropna()
        if len(r) < 50:
            continue
        excess      = r - RF_DAILY
        downside    = r[r < 0]
        down_std    = downside.std() * np.sqrt(252)
        ann_excess  = excess.mean() * 252
        sortino     = ann_excess / down_std if down_std != 0 else np.nan
        results.append({"amfi_code": code, "sortino": round(sortino, 4)})
    return pd.DataFrame(results)

sortino_df = compute_sortino(nav)
print(f"Sortino computed: min={sortino_df['sortino'].min():.3f}  max={sortino_df['sortino'].max():.3f}")


# ── task 5: Alpha and Beta via OLS ────────────────────────────────────────

# use NIFTY100 as benchmark
nifty100 = (df_bench[df_bench["index_name"] == "NIFTY100"]
            .sort_values("date")
            .set_index("date")["close_value"])
bench_returns = nifty100.pct_change().dropna()

def compute_alpha_beta(df, bench_ret):
    results = []
    for code, grp in df.groupby("amfi_code"):
        r = grp.set_index("date")["daily_return"].dropna()
        common = r.index.intersection(bench_ret.index)
        if len(common) < 100:
            continue
        fund_r  = r.loc[common].values
        bench_r = bench_ret.loc[common].values

        slope, intercept, r_val, p_val, _ = stats.linregress(bench_r, fund_r)
        alpha = intercept * 252
        beta  = slope

        results.append({
            "amfi_code": code,
            "alpha":     round(alpha, 4),
            "beta":      round(beta, 4),
            "r_squared": round(r_val**2, 4),
        })
    return pd.DataFrame(results)

ab_df = compute_alpha_beta(nav, bench_returns)
ab_df = ab_df.merge(df_fund[["amfi_code","scheme_name","fund_house","sub_category"]], on="amfi_code")
ab_df.to_csv(PROC / "alpha_beta.csv", index=False)
print(f"\nalpha_beta.csv saved — {len(ab_df)} schemes")
print(ab_df[["scheme_name","alpha","beta","r_squared"]].sort_values("alpha", ascending=False).head(5).to_string(index=False))


# ── task 6: Maximum Drawdown ──────────────────────────────────────────────

def compute_max_drawdown(df):
    results = []
    for code, grp in df.groupby("amfi_code"):
        grp = grp.sort_values("date").reset_index(drop=True)
        nav_s       = grp["nav"]
        rolling_max = nav_s.cummax()
        drawdown    = (nav_s / rolling_max) - 1
        max_dd      = drawdown.min()
        trough_pos  = drawdown.idxmin()   # integer position after reset_index
        trough_date = grp.loc[trough_pos, "date"]

        # peak is the highest NAV before the trough
        peak_pos  = nav_s.iloc[:trough_pos + 1].idxmax()
        peak_date = grp.loc[peak_pos, "date"]

        results.append({
            "amfi_code":    code,
            "max_drawdown": round(max_dd, 4),
            "peak_date":    peak_date,
            "trough_date":  trough_date,
        })
    return pd.DataFrame(results)

dd_df = compute_max_drawdown(nav)
print(f"\nMax drawdown: worst={dd_df['max_drawdown'].min():.3f}  best={dd_df['max_drawdown'].max():.3f}")


# ── task 7: Fund Scorecard ────────────────────────────────────────────────

def build_scorecard(cagr_df, sharpe_df, sortino_df, ab_df, dd_df):
    sc = cagr_df[["amfi_code","scheme_name","fund_house","sub_category","plan"]].copy()
    sc = sc.merge(cagr_df[["amfi_code","cagr_3yr"]], on="amfi_code")
    sc = sc.merge(sharpe_df,  on="amfi_code", how="left")
    sc = sc.merge(sortino_df, on="amfi_code", how="left")
    sc = sc.merge(ab_df[["amfi_code","alpha","beta"]], on="amfi_code", how="left")
    sc = sc.merge(dd_df[["amfi_code","max_drawdown"]], on="amfi_code", how="left")
    sc = sc.merge(df_fund[["amfi_code","expense_ratio_pct"]], on="amfi_code", how="left")

    n = len(sc)

    # ranks (higher = better for return, sharpe, alpha; lower = better for expense, drawdown)
    sc["rank_3yr"]     = sc["cagr_3yr"].rank(ascending=True)           # higher return = higher rank
    sc["rank_sharpe"]  = sc["sharpe"].rank(ascending=True)
    sc["rank_alpha"]   = sc["alpha"].rank(ascending=True)
    sc["rank_expense"] = sc["expense_ratio_pct"].rank(ascending=False)  # lower expense = higher rank
    sc["rank_dd"]      = sc["max_drawdown"].rank(ascending=False)       # less negative dd = higher rank

    sc["score"] = (
        0.30 * sc["rank_3yr"] +
        0.25 * sc["rank_sharpe"] +
        0.20 * sc["rank_alpha"] +
        0.15 * sc["rank_expense"] +
        0.10 * sc["rank_dd"]
    )

    # normalise to 0-100
    sc["score"] = ((sc["score"] - sc["score"].min()) /
                   (sc["score"].max() - sc["score"].min()) * 100).round(1)

    sc = sc.sort_values("score", ascending=False).reset_index(drop=True)
    sc["rank"] = sc.index + 1
    return sc

scorecard = build_scorecard(cagr_df, sharpe_df, sortino_df, ab_df, dd_df)
scorecard.to_csv(PROC / "fund_scorecard.csv", index=False)
print(f"\nfund_scorecard.csv saved")
print("\ntop 10 funds by scorecard:")
cols = ["rank","scheme_name","score","cagr_3yr","sharpe","alpha","max_drawdown"]
print(scorecard[cols].head(10).to_string(index=False))


# ── task 8: Benchmark comparison chart ────────────────────────────────────

def benchmark_chart(scorecard, nav_df, bench_df):
    top5_codes = scorecard.head(5)["amfi_code"].tolist()

    end_date   = nav_df["date"].max()
    start_date = end_date - pd.DateOffset(years=3)

    fig, ax = plt.subplots(figsize=(13, 6))

    tracking_errors = {}

    for code in top5_codes:
        grp  = nav_df[(nav_df["amfi_code"] == code) & (nav_df["date"] >= start_date)].sort_values("date")
        name = df_fund[df_fund["amfi_code"] == code]["scheme_name"].iloc[0].split(" - ")[0]

        # index to 100
        base = grp["nav"].iloc[0]
        ax.plot(grp["date"], grp["nav"] / base * 100, linewidth=1.8, label=name)

        # tracking error vs NIFTY100
        r_fund  = grp.set_index("date")["daily_return"].dropna()
        r_bench = bench_returns.reindex(r_fund.index).dropna()
        common  = r_fund.index.intersection(r_bench.index)
        if len(common) > 20:
            te = (r_fund.loc[common] - r_bench.loc[common]).std() * np.sqrt(252)
            tracking_errors[name] = round(te, 4)

    # add benchmark lines
    for idx_name, color, style in [("NIFTY50","black","--"), ("NIFTY100","dimgray",":")]:
        b = bench_df[bench_df["index_name"] == idx_name].copy()
        b = b[(b["date"] >= start_date)].sort_values("date")
        base = b["close_value"].iloc[0]
        ax.plot(b["date"], b["close_value"] / base * 100,
                color=color, linestyle=style, linewidth=2, label=idx_name)

    ax.set_title("Top 5 Funds vs Nifty 50 & Nifty 100 — 3 Year (Indexed to 100)", fontsize=13)
    ax.set_ylabel("Index (Base = 100)")
    ax.set_xlabel("")
    ax.legend(fontsize=9, loc="upper left")
    plt.tight_layout()
    plt.savefig(CHARTS / "11_benchmark_comparison.png")
    plt.close()
    print(f"\nbenchmark chart saved")

    print("\ntracking errors (annualised) vs NIFTY100:")
    for name, te in tracking_errors.items():
        print(f"  {name[:40]:40s}  {te:.4f}")

benchmark_chart(scorecard, nav, df_bench)

print("\ndone.")
