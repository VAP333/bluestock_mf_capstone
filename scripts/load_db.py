import pathlib
import sqlite3
import pandas as pd
from sqlalchemy import create_engine, text

BASE = pathlib.Path(__file__).resolve().parent.parent
PROC = BASE / "data" / "processed"
DB   = BASE / "data" / "db"
DB.mkdir(parents=True, exist_ok=True)

DB_PATH  = DB / "bluestock_mf.db"
SCHEMA   = BASE / "sql" / "schema.sql"

engine = create_engine(f"sqlite:///{DB_PATH}")


def run_schema():
    with open(SCHEMA) as f:
        sql = f.read()
    with engine.connect() as conn:
        for stmt in sql.split(";"):
            stmt = stmt.strip()
            if stmt:
                conn.execute(text(stmt))
        conn.commit()
    print("schema created")


def build_dim_date(start="2022-01-01", end="2026-12-31"):
    dates = pd.date_range(start, end)
    df = pd.DataFrame({"date_id": dates.strftime("%Y-%m-%d")})
    df["year"]       = dates.year
    df["month"]      = dates.month
    df["quarter"]    = dates.quarter
    df["month_name"] = dates.strftime("%B")
    df["is_weekday"] = (dates.dayofweek < 5).astype(int)
    return df


def load_table(df, table_name, if_exists="replace"):
    df.to_sql(table_name, engine, if_exists=if_exists, index=False)
    with engine.connect() as conn:
        count = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}")).fetchone()[0]
    print(f"  {table_name}: {count} rows loaded")


def verify_counts():
    tables = [
        "dim_fund", "dim_date", "fact_nav", "fact_transactions",
        "fact_performance", "fact_aum", "fact_sip_industry", "fact_portfolio"
    ]
    print("\nrow counts in db:")
    with engine.connect() as conn:
        for t in tables:
            try:
                n = conn.execute(text(f"SELECT COUNT(*) FROM {t}")).fetchone()[0]
                print(f"  {t}: {n}")
            except Exception as e:
                print(f"  {t}: error - {e}")


if __name__ == "__main__":
    print("=== building sqlite db ===")
    print(f"db path: {DB_PATH}")

    run_schema()

    print("\nloading dimension tables")

    df_fund = pd.read_csv(PROC / "clean_fund_master.csv")
    load_table(df_fund, "dim_fund")

    df_date = build_dim_date()
    load_table(df_date, "dim_date")

    print("\nloading fact tables")

    df_nav = pd.read_csv(PROC / "clean_nav_history.csv")
    df_nav.rename(columns={"date": "nav_date"}, inplace=True)
    load_table(df_nav, "fact_nav")

    df_tx = pd.read_csv(PROC / "clean_investor_transactions.csv")
    df_tx.rename(columns={"transaction_date": "transaction_date"}, inplace=True)
    load_table(df_tx, "fact_transactions")

    df_perf = pd.read_csv(PROC / "clean_scheme_performance.csv")
    load_table(df_perf, "fact_performance")

    df_aum = pd.read_csv(PROC / "clean_aum_by_fund_house.csv")
    load_table(df_aum, "fact_aum")

    df_sip = pd.read_csv(PROC / "clean_monthly_sip_inflows.csv")
    load_table(df_sip, "fact_sip_industry")

    df_port = pd.read_csv(PROC / "clean_portfolio_holdings.csv")
    load_table(df_port, "fact_portfolio")

    verify_counts()
    print("\ndone.")
