#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tide_stage_mapper.py

AGI Tide table -> stage-wise forecast tide mapper.

Inputs:
  - tide table Excel (ts_local, tide_m columns; tolerant mapping supported)
  - tide_windows_AGI.json (stage -> time window + stat)
  - optional stage_results.csv for stage list

Output:
  - stage_tide_AGI.csv
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd


def load_tide_table_excel(tide_xlsx_path: Path) -> pd.DataFrame:
    df = pd.read_excel(tide_xlsx_path)

    ren = {}
    for c in df.columns:
        cl = str(c).strip().lower()
        if cl in ("ts_local", "timestamp", "datetime", "date", "time", "ts", "datetime_gst"):
            ren[c] = "ts_local"
        elif cl in ("tide_m", "tide", "water_level", "wl_m", "height_m") or "tide" in cl or "chart datum" in cl:
            ren[c] = "tide_m"
        elif cl in ("datum", "chart_datum"):
            ren[c] = "datum"
        elif cl in ("tz", "timezone"):
            ren[c] = "tz"
        elif cl in ("source", "src"):
            ren[c] = "source"
        elif cl in ("quality_flag", "quality", "qc"):
            ren[c] = "quality_flag"

    df = df.rename(columns=ren)
    if "ts_local" not in df.columns:
        raise ValueError(
            f"[HARDSTOP] Tide table missing timestamp column. Found: {list(df.columns)}"
        )
    if "tide_m" not in df.columns:
        raise ValueError(
            f"[HARDSTOP] Tide table missing tide_m column. Found: {list(df.columns)}"
        )

    df["ts_local"] = pd.to_datetime(df["ts_local"], errors="coerce")
    df["tide_m"] = pd.to_numeric(df["tide_m"], errors="coerce")
    df = df.dropna(subset=["ts_local", "tide_m"])
    return df


def load_tide_windows_json(windows_json_path: Path) -> Dict[str, Dict[str, Any]]:
    with windows_json_path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if "tide_windows" in data:
        return data["tide_windows"]
    return data


def extract_tide_for_window(
    tide_df: pd.DataFrame,
    window_start: str,
    window_end: str,
    stat: str = "min",
) -> Optional[float]:
    try:
        start_dt = pd.to_datetime(window_start)
        end_dt = pd.to_datetime(window_end)
    except Exception:
        if tide_df.empty:
            return None
        base_date = tide_df["ts_local"].min().date()
        start_dt = pd.to_datetime(f"{base_date} {window_start}")
        end_dt = pd.to_datetime(f"{base_date} {window_end}")
        if end_dt < start_dt:
            end_dt += pd.Timedelta(days=1)

    mask = (tide_df["ts_local"] >= start_dt) & (tide_df["ts_local"] <= end_dt)
    window_data = tide_df.loc[mask, "tide_m"]
    if window_data.empty:
        return None

    stat = str(stat).lower().strip()
    if stat == "min":
        return float(window_data.min())
    if stat == "max":
        return float(window_data.max())
    if stat == "mean":
        return float(window_data.mean())
    raise ValueError(f"Invalid stat: {stat}")


def map_stages_to_tide(
    tide_df: pd.DataFrame,
    tide_windows: Dict[str, Dict[str, Any]],
    stage_list: List[str],
) -> pd.DataFrame:
    rows: List[Dict[str, object]] = []
    for stage_name in stage_list:
        if stage_name not in tide_windows:
            rows.append(
                {
                    "StageKey": stage_name,
                    "Forecast_tide_min_m": None,
                    "Forecast_tide_mean_m": None,
                    "Forecast_tide_m": None,
                    "tide_src": "MISSING_WINDOW",
                    "tide_qc": "VERIFY",
                }
            )
            continue

        window = tide_windows[stage_name]
        stat = window.get("stat", "min")
        tide_min = extract_tide_for_window(
            tide_df, window["start"], window["end"], "min"
        )
        tide_mean = extract_tide_for_window(
            tide_df, window["start"], window["end"], "mean"
        )
        tide_selected = extract_tide_for_window(
            tide_df, window["start"], window["end"], stat
        )

        rows.append(
            {
                "StageKey": stage_name,
                "Forecast_tide_min_m": tide_min,
                "Forecast_tide_mean_m": tide_mean,
                "Forecast_tide_m": tide_selected if tide_selected is not None else tide_min,
                "tide_src": f"window_{stat}",
                "tide_qc": "OK" if tide_selected is not None else "MISSING_DATA",
            }
        )

    return pd.DataFrame(rows)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tide_table", required=True, help="Tide table Excel path")
    ap.add_argument("--tide_windows", required=True, help="Tide windows JSON path")
    ap.add_argument("--stage_list", help="Comma-separated stage names")
    ap.add_argument("--stage_results", help="stage_results.csv (Stage column)")
    ap.add_argument("--out", required=True, help="Output CSV path")
    args = ap.parse_args()

    tide_df = load_tide_table_excel(Path(args.tide_table))
    tide_windows = load_tide_windows_json(Path(args.tide_windows))

    if args.stage_list:
        stage_list = [s.strip() for s in args.stage_list.split(",") if s.strip()]
    elif args.stage_results:
        df_stages = pd.read_csv(args.stage_results)
        if "Stage" not in df_stages.columns:
            raise ValueError(
                f"[HARDSTOP] stage_results.csv missing Stage column: {args.stage_results}"
            )
        stage_list = df_stages["Stage"].astype(str).tolist()
    else:
        stage_list = list(tide_windows.keys())

    result_df = map_stages_to_tide(tide_df, tide_windows, stage_list)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    result_df.to_csv(out_path, index=False, encoding="utf-8-sig")

    print(f"[OK] Stage tide mapping: {out_path}")
    print(f"     Stages: {len(result_df)}")
    print(
        f"     Missing windows: {len(result_df[result_df['tide_qc'] == 'VERIFY'])}"
    )
    print(
        f"     Missing data: {len(result_df[result_df['tide_qc'] == 'MISSING_DATA'])}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
