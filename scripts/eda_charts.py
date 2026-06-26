import pathlib
import warnings
warnings.filterwarnings("ignore")

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

PROC   = pathlib.Path(__file__).resolve().parent.parent / "data" / "processed"
CHARTS = pathlib.Path(__file__).resolve().parent.parent / "reports" / "charts"
CHARTS.mkdir(parents=True, exist_ok=True)

# common style
sns.set_theme(style="whitegrid", palette="muted")
plt.rcParams.update({"font.size": 11, "figure.dpi": 120})


# ── load data ──────────────────────────────────────────────────────────────

df_nav   = pd.read_csv(PROC / "clean_nav_history.csv",        parse_dates=["date"])
df_fund  = pd.read_csv(PROC / "clean_fund_master.csv")
df_aum   = pd.read_csv(PROC / "clean_aum_by_fund_house.csv",  parse_dates=["date"])
df_sip   = pd.read_csv(PROC / "clean_monthly_sip_inflows.csv",parse_dates=["month"])
df_cat   = pd.read_csv(PROC / "clean_category_inflows.csv",   parse_dates=["month"])
df_tx    = pd.read_csv(PROC / "clean_investor_transactions.csv", parse_dates=["transaction_date"])
df_folio = pd.read_csv(PROC / "clean_industry_folio_count.csv", parse_dates=["month"])
df_port  = pd.read_csv(PROC / "clean_portfolio_holdings.csv")

nav = df_nav.merge(df_fund[["amfi_code","scheme_name","sub_category","fund_house"]], on="amfi_code")


# ── chart 1: NAV trend for large cap funds ─────────────────────────────────

def chart_nav_trend():
    lc_codes = df_fund[df_fund["sub_category"] == "Large Cap"]["amfi_code"].unique()
    # pick direct plans only to avoid clutter
    lc_direct = df_fund[(df_fund["sub_category"]=="Large Cap") & (df_fund["plan"]=="Direct")]["amfi_code"].unique()
    subset = nav[nav["amfi_code"].isin(lc_direct)].copy()

    # normalise to 100 at start so all lines start together
    base = subset.groupby("amfi_code")["nav"].transform("first")
    subset["nav_idx"] = subset["nav"] / base * 100

    fig = go.Figure()
    for code, grp in subset.groupby("amfi_code"):
        name = grp["scheme_name"].iloc[0].split(" - ")[0]
        fig.add_trace(go.Scatter(
            x=grp["date"], y=grp["nav_idx"],
            mode="lines", name=name, line=dict(width=1.5)
        ))

    # mark 2023 bull run and 2024 correction
    fig.add_vrect(x0="2023-01-01", x1="2023-12-31",
                  fillcolor="green", opacity=0.07, line_width=0,
                  annotation_text="2023 Bull Run", annotation_position="top left")
    fig.add_vrect(x0="2024-06-01", x1="2024-10-31",
                  fillcolor="red", opacity=0.07, line_width=0,
                  annotation_text="2024 Correction", annotation_position="top left")

    fig.update_layout(
        title="Large Cap Fund NAV — Indexed to 100 (Jan 2022)",
        xaxis_title="Date", yaxis_title="NAV Index (Base = 100)",
        height=500, legend=dict(font=dict(size=9)),
        template="plotly_white"
    )
    fig.write_html(str(CHARTS / "01_nav_trend.html"))
    print("chart 1 saved")
    return fig


# ── chart 2: AUM growth grouped bar ────────────────────────────────────────

def chart_aum_growth():
    df_aum["year"] = df_aum["date"].dt.year
    yearly = df_aum.groupby(["year","fund_house"])["aum_lakh_crore"].max().reset_index()
    yearly = yearly[yearly["year"].between(2022, 2025)]

    # sort fund houses by latest AUM
    order = (yearly[yearly["year"]==2025]
             .sort_values("aum_lakh_crore", ascending=False)["fund_house"].tolist())

    fig, ax = plt.subplots(figsize=(13, 6))
    yearly_pivot = yearly.pivot(index="fund_house", columns="year", values="aum_lakh_crore")
    yearly_pivot = yearly_pivot.reindex(order)
    yearly_pivot.plot(kind="bar", ax=ax, width=0.7)

    ax.set_title("AUM by Fund House — 2022 to 2025 (Rs. lakh crore)", fontsize=13)
    ax.set_xlabel("")
    ax.set_ylabel("AUM (Rs. lakh crore)")
    ax.set_xticklabels(ax.get_xticklabels(), rotation=30, ha="right")
    ax.legend(title="Year")

    # annotate SBI 2025 bar
    sbi_idx = order.index("SBI Mutual Fund")
    sbi_val = yearly_pivot.loc["SBI Mutual Fund", 2025]
    ax.annotate(f"Rs.{sbi_val}L Cr",
                xy=(sbi_idx + 0.22, sbi_val),
                fontsize=9, color="darkred", fontweight="bold")

    plt.tight_layout()
    plt.savefig(CHARTS / "02_aum_growth.png")
    plt.close()
    print("chart 2 saved")


# ── chart 3: SIP inflow time-series ────────────────────────────────────────

def chart_sip_trend():
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df_sip["month"], y=df_sip["sip_inflow_crore"],
        mode="lines+markers", name="SIP Inflow",
        line=dict(color="steelblue", width=2),
        marker=dict(size=4)
    ))

    # annotate all-time high
    ath = df_sip.loc[df_sip["sip_inflow_crore"].idxmax()]
    fig.add_annotation(
        x=ath["month"], y=ath["sip_inflow_crore"],
        text=f"ATH: Rs.{int(ath['sip_inflow_crore']):,} Cr<br>Dec 2025",
        showarrow=True, arrowhead=2, ax=40, ay=-40,
        font=dict(color="darkred", size=11)
    )

    fig.update_layout(
        title="Monthly SIP Inflows — Jan 2022 to Dec 2025",
        xaxis_title="Month", yaxis_title="SIP Inflow (Rs. crore)",
        template="plotly_white", height=420
    )
    fig.write_html(str(CHARTS / "03_sip_trend.html"))
    print("chart 3 saved")
    return fig


# ── chart 4: category inflow heatmap ───────────────────────────────────────

def chart_category_heatmap():
    df_cat["month_str"] = df_cat["month"].dt.strftime("%b %Y")
    pivot = df_cat.pivot(index="category", columns="month_str", values="net_inflow_crore")

    # keep month order
    months_ordered = df_cat.sort_values("month")["month"].dt.strftime("%b %Y").unique()
    pivot = pivot[months_ordered]

    fig, ax = plt.subplots(figsize=(16, 6))
    sns.heatmap(pivot, ax=ax, cmap="RdYlGn", center=0,
                linewidths=0.3, fmt=".0f", annot=False,
                cbar_kws={"label": "Net Inflow (Rs. crore)"})
    ax.set_title("Category-wise Net Inflows — Monthly Heatmap", fontsize=13)
    ax.set_xlabel("")
    ax.set_ylabel("")
    ax.set_xticklabels(ax.get_xticklabels(), rotation=45, ha="right", fontsize=8)
    plt.tight_layout()
    plt.savefig(CHARTS / "04_category_heatmap.png")
    plt.close()
    print("chart 4 saved")


# ── chart 5: investor demographics ─────────────────────────────────────────

def chart_demographics():
    sip_only = df_tx[df_tx["transaction_type"] == "SIP"]

    fig, axes = plt.subplots(1, 3, figsize=(15, 5))

    # age group distribution
    age_counts = df_tx["age_group"].value_counts().sort_index()
    axes[0].pie(age_counts, labels=age_counts.index, autopct="%1.1f%%",
                startangle=140, colors=sns.color_palette("pastel"))
    axes[0].set_title("Investor Age Distribution")

    # SIP amount box plot by age group
    order = ["18-25","26-35","36-45","46-55","56+"]
    sip_only.boxplot(column="amount_inr", by="age_group",
                     ax=axes[1], positions=range(len(order)),
                     showfliers=False)
    axes[1].set_xticklabels(order)
    axes[1].set_title("SIP Amount by Age Group")
    axes[1].set_xlabel("Age Group")
    axes[1].set_ylabel("SIP Amount (Rs.)")
    plt.sca(axes[1])
    plt.title("SIP Amount by Age Group")
    plt.suptitle("")

    # gender split
    gender_counts = df_tx["gender"].value_counts()
    axes[2].pie(gender_counts, labels=gender_counts.index, autopct="%1.1f%%",
                colors=["#5B9BD5","#ED7D31"], startangle=90)
    axes[2].set_title("Gender Split")

    plt.suptitle("Investor Demographics", fontsize=14, y=1.02)
    plt.tight_layout()
    plt.savefig(CHARTS / "05_demographics.png", bbox_inches="tight")
    plt.close()
    print("chart 5 saved")


# ── chart 6: geographic distribution ───────────────────────────────────────

def chart_geo():
    sip_only = df_tx[df_tx["transaction_type"] == "SIP"]
    state_sip = (sip_only.groupby("state")["amount_inr"]
                 .sum().sort_values() / 1e6)  # in millions

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # horizontal bar
    state_sip.plot(kind="barh", ax=axes[0], color="steelblue")
    axes[0].set_title("Total SIP Amount by State")
    axes[0].set_xlabel("SIP Amount (Rs. millions)")
    axes[0].set_ylabel("")

    # T30 vs B30
    tier_counts = df_tx["city_tier"].value_counts()
    axes[1].pie(tier_counts, labels=tier_counts.index, autopct="%1.1f%%",
                colors=["#2196F3","#FF9800"], startangle=90)
    axes[1].set_title("T30 vs B30 City Tier")

    plt.tight_layout()
    plt.savefig(CHARTS / "06_geo_distribution.png")
    plt.close()
    print("chart 6 saved")


# ── chart 7: folio count growth ─────────────────────────────────────────────

def chart_folio_growth():
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(df_folio["month"], df_folio["total_folios_crore"],
            color="steelblue", linewidth=2, marker="o", markersize=4)
    ax.fill_between(df_folio["month"], df_folio["total_folios_crore"],
                    alpha=0.15, color="steelblue")

    # milestones
    milestones = {
        "20 Cr": 20.0,
        "25 Cr": 25.0,
    }
    for label, val in milestones.items():
        row = df_folio[df_folio["total_folios_crore"] >= val].iloc[0]
        ax.annotate(label, xy=(row["month"], val),
                    xytext=(10, 10), textcoords="offset points",
                    fontsize=9, color="darkgreen",
                    arrowprops=dict(arrowstyle="->", color="darkgreen"))

    ax.set_title("Industry Folio Count Growth — Jan 2022 to Dec 2025", fontsize=13)
    ax.set_ylabel("Total Folios (crore)")
    ax.set_xlabel("")
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.1f Cr"))
    plt.tight_layout()
    plt.savefig(CHARTS / "07_folio_growth.png")
    plt.close()
    print("chart 7 saved")


# ── chart 8: NAV return correlation matrix ─────────────────────────────────

def chart_correlation():
    # 10 large cap direct plan codes
    lc_direct = df_fund[
        (df_fund["sub_category"] == "Large Cap") & (df_fund["plan"] == "Direct")
    ]["amfi_code"].unique()[:10]

    subset = df_nav[df_nav["amfi_code"].isin(lc_direct)].copy()
    pivot  = subset.pivot(index="date", columns="amfi_code", values="nav")
    returns = pivot.pct_change().dropna()

    # shorten column names for display
    code_to_name = df_fund.set_index("amfi_code")["scheme_name"].to_dict()
    short_names  = {c: code_to_name[c].split(" - ")[0].replace(" Fund","").strip()
                    for c in lc_direct if c in code_to_name}
    returns.rename(columns=short_names, inplace=True)

    corr = returns.corr()

    fig, ax = plt.subplots(figsize=(10, 8))
    mask = np.triu(np.ones_like(corr, dtype=bool))
    sns.heatmap(corr, ax=ax, mask=mask, annot=True, fmt=".2f",
                cmap="coolwarm", vmin=0.5, vmax=1.0,
                linewidths=0.5, cbar_kws={"shrink": 0.8})
    ax.set_title("Daily Return Correlation — Large Cap Funds", fontsize=13)
    ax.set_xticklabels(ax.get_xticklabels(), rotation=35, ha="right", fontsize=9)
    ax.set_yticklabels(ax.get_yticklabels(), fontsize=9)
    plt.tight_layout()
    plt.savefig(CHARTS / "08_correlation_matrix.png")
    plt.close()
    print("chart 8 saved")


# ── chart 9: sector allocation donut ────────────────────────────────────────

def chart_sector_donut():
    sector_wt = (df_port.groupby("sector")["weight_pct"]
                 .sum().sort_values(ascending=False))

    # group small sectors into Other
    threshold = sector_wt.sum() * 0.03
    main   = sector_wt[sector_wt >= threshold]
    other  = sector_wt[sector_wt < threshold].sum()
    if other > 0:
        main["Other"] = other

    fig, ax = plt.subplots(figsize=(9, 7))
    wedges, texts, autotexts = ax.pie(
        main, labels=main.index, autopct="%1.1f%%",
        pctdistance=0.82, startangle=140,
        colors=sns.color_palette("tab10", len(main)),
        wedgeprops=dict(width=0.5)   # donut
    )
    for t in autotexts:
        t.set_fontsize(8)
    ax.set_title("Sector Allocation — Aggregate Across All Equity Funds", fontsize=12)
    plt.tight_layout()
    plt.savefig(CHARTS / "09_sector_donut.png")
    plt.close()
    print("chart 9 saved")


# ── chart 10: SIP accounts growth ──────────────────────────────────────────

def chart_sip_accounts():
    fig, ax1 = plt.subplots(figsize=(12, 5))
    ax2 = ax1.twinx()

    ax1.bar(df_sip["month"], df_sip["sip_inflow_crore"],
            color="steelblue", alpha=0.6, width=20, label="SIP Inflow (crore)")
    ax2.plot(df_sip["month"], df_sip["active_sip_accounts_crore"],
             color="darkorange", linewidth=2, marker="o", markersize=3,
             label="Active SIP Accounts (crore)")

    ax1.set_title("SIP Inflow vs Active Accounts — 2022 to 2025", fontsize=13)
    ax1.set_ylabel("SIP Inflow (Rs. crore)", color="steelblue")
    ax2.set_ylabel("Active Accounts (crore)", color="darkorange")
    ax1.tick_params(axis="y", labelcolor="steelblue")
    ax2.tick_params(axis="y", labelcolor="darkorange")

    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper left", fontsize=9)

    plt.tight_layout()
    plt.savefig(CHARTS / "10_sip_accounts.png")
    plt.close()
    print("chart 10 saved")


if __name__ == "__main__":
    print("generating EDA charts...")
    chart_nav_trend()
    chart_aum_growth()
    chart_sip_trend()
    chart_category_heatmap()
    chart_demographics()
    chart_geo()
    chart_folio_growth()
    chart_correlation()
    chart_sector_donut()
    chart_sip_accounts()
    print(f"\nall charts saved to {CHARTS}")
