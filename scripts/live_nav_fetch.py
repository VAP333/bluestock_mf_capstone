import pathlib
import time
import requests
import pandas as pd

RAW = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"

# schemes to fetch: name -> amfi code
schemes = {
    "HDFC_Top_100":     125497,
    "SBI_Bluechip":     119551,
    "ICICI_Bluechip":   120503,
    "Nippon_LargeCap":  118632,
    "Axis_Bluechip":    119092,
    "Kotak_Bluechip":   120841,
}


def fetch_from_api(code, name):
    url = f"https://api.mfapi.in/mf/{code}"
    print(f"fetching {name} ({code}) from {url}")

    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"  request failed: {e}")
        return None

    data = r.json()
    records = data.get("data", [])
    meta    = data.get("meta", {})

    print(f"  scheme: {meta.get('scheme_name', 'N/A')}")
    print(f"  records: {len(records)}")

    if not records:
        return None

    df = pd.DataFrame(records)
    df.rename(columns={"date": "nav_date"}, inplace=True)
    df["nav_date"] = pd.to_datetime(df["nav_date"], format="%d-%m-%Y", errors="coerce")
    df["nav"]      = pd.to_numeric(df["nav"], errors="coerce")
    df.dropna(inplace=True)
    df.sort_values("nav_date", inplace=True)
    df.reset_index(drop=True, inplace=True)
    df.insert(0, "amfi_code", code)
    df.insert(1, "scheme_name", meta.get("scheme_name", name))

    return df


def fallback_from_csv(code, name):
    # mfapi.in might be blocked in some environments
    # fall back to the provided nav_history csv in that case
    nav_csv = RAW / "02_nav_history.csv"
    if not nav_csv.exists():
        return None

    df_all = pd.read_csv(nav_csv)
    df = df_all[df_all["amfi_code"] == code].copy()
    if df.empty:
        return None

    df.rename(columns={"date": "nav_date"}, inplace=True)
    df["nav_date"] = pd.to_datetime(df["nav_date"])
    df.insert(1, "scheme_name", name)
    df.sort_values("nav_date", inplace=True)
    df.reset_index(drop=True, inplace=True)

    print(f"  using fallback data from nav_history.csv for {name}")
    return df


def save_csv(df, code, name):
    out = RAW / f"live_nav_{code}_{name}.csv"
    df.to_csv(out, index=False)
    print(f"  saved: {out.name}  ({len(df)} rows)")
    print(f"  date range: {df['nav_date'].min().date()} to {df['nav_date'].max().date()}")
    print(f"  latest nav: {df['nav'].iloc[-1]:.4f}")


if __name__ == "__main__":
    all_dfs = []

    for name, code in schemes.items():
        print(f"\n{name}")
        df = fetch_from_api(code, name)

        if df is None:
            df = fallback_from_csv(code, name)

        if df is not None:
            save_csv(df, code, name)
            all_dfs.append(df)
        else:
            print(f"  could not get data for {name}, skipping")

        time.sleep(0.5)

    if all_dfs:
        combined = pd.concat(all_dfs, ignore_index=True)
        out = RAW / "live_nav_all_schemes.csv"
        combined.to_csv(out, index=False)
        print(f"\ncombined file: {out.name}  ({len(combined)} rows)")

    print("\ndone.")
