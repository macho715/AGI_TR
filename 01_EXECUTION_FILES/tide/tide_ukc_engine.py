#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tide + UKC SSOT Engine
=====================

AGI/DAS 공통으로 사용할 수 있는 Tide/UKC 계산 SSOT 모듈.

본 모듈은 "Forecast Tide(예보 조위)"와 "Required WL(UKC 만족을 위해 필요한 수위)"
를 혼동하지 않도록, 아래 정의를 **엄격히 분리**한다.

Definitions (CD 기준)
- Forecast_tide_m / Forecast_Tide_m:
    예보 조위(Chart Datum 기준). "필요 수위"가 아니라 예보값.
- Tide_required_m:
    UKC 요구조건을 만족하기 위해 필요한 최소 수위(조위).
    Tide_required_m = max(0, (Draft_ref + Squat + Safety + UKC_min) - DepthRef)
- Tide_margin_m:
    Tide_margin_m = Forecast_tide_m - Tide_required_m
- UKC_fwd_m / UKC_aft_m:
    UKC_end = DepthRef + Forecast_tide - Draft_end - Squat - Safety
- UKC_min_actual_m:
    min(UKC_fwd_m, UKC_aft_m)
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple, Dict

import numpy as np
import pandas as pd

try:
    from .tide_constants import (
        DEFAULT_TIDE_TOL_M,
        DEFAULT_DEPTH_REF_M,
        DEFAULT_UKC_MIN_M,
        DEFAULT_SQUAT_M,
        DEFAULT_SAFETY_ALLOW_M,
    )
except ImportError:
    # Fallback for direct execution
    from tide_constants import (
        DEFAULT_TIDE_TOL_M,
        DEFAULT_DEPTH_REF_M,
        DEFAULT_UKC_MIN_M,
        DEFAULT_SQUAT_M,
        DEFAULT_SAFETY_ALLOW_M,
    )


def _to_float(x, fallback: Optional[float] = None, warn: bool = False) -> Optional[float]:
    """
    Convert to float with optional fallback.

    Args:
        x: Value to convert
        fallback: Default value if conversion fails (None = return None)
        warn: Log warning on failure

    Returns:
        float or fallback value
    """
    try:
        if x is None:
            return fallback
        if isinstance(x, str) and x.strip() == "":
            return fallback
        if pd.isna(x):
            return fallback
        return float(x)
    except Exception as e:
        if warn:
            import logging
            logging.debug(f"_to_float conversion failed: {e}, using fallback={fallback}")
        return fallback


def required_tide_m(
    depth_ref_m: Optional[float],
    draft_ref_m: Optional[float],
    ukc_min_m: Optional[float],
    squat_m: float = 0.0,
    safety_allow_m: float = 0.0,
    clamp_zero: bool = True,
    fallback_depth: Optional[float] = None,
    fallback_draft: Optional[float] = None,
    fallback_ukc: Optional[float] = None,
) -> float:
    """Return required tide (m, CD) with fallbacks."""
    # Apply fallbacks
    depth = depth_ref_m if depth_ref_m is not None else (fallback_depth or DEFAULT_DEPTH_REF_M)
    draft = draft_ref_m if draft_ref_m is not None else (fallback_draft or 2.00)
    ukc = ukc_min_m if ukc_min_m is not None else (fallback_ukc or DEFAULT_UKC_MIN_M)

    req = float(draft + float(squat_m) + float(safety_allow_m) + float(ukc) - float(depth))
    if clamp_zero:
        return float(max(0.0, req))
    return float(req)


def ukc_end_m(
    depth_ref_m: Optional[float],
    forecast_tide_m: Optional[float],
    draft_end_m: Optional[float],
    squat_m: float = 0.0,
    safety_allow_m: float = 0.0,
) -> float:
    """Return UKC at one end (m)."""
    if depth_ref_m is None or forecast_tide_m is None or draft_end_m is None:
        return float("nan")
    return float(float(depth_ref_m) + float(forecast_tide_m) - float(draft_end_m) - float(squat_m) - float(safety_allow_m))


def ukc_fwd_aft_min(
    depth_ref_m: Optional[float],
    forecast_tide_m: Optional[float],
    draft_fwd_m: Optional[float],
    draft_aft_m: Optional[float],
    squat_m: float = 0.0,
    safety_allow_m: float = 0.0,
) -> Tuple[float, float, float]:
    """Return (UKC_fwd, UKC_aft, UKC_min_actual)."""
    uf = ukc_end_m(depth_ref_m, forecast_tide_m, draft_fwd_m, squat_m, safety_allow_m)
    ua = ukc_end_m(depth_ref_m, forecast_tide_m, draft_aft_m, squat_m, safety_allow_m)
    try:
        umin = float(min(uf, ua))
    except Exception:
        umin = float("nan")
    return uf, ua, umin


def verify_tide(
    tide_required_m_val: float,
    forecast_tide_m_val: Optional[float],
    tolerance_m: float = DEFAULT_TIDE_TOL_M,
) -> Tuple[str, str]:
    """
    Return (status, note)
    - VERIFY: forecast missing (no official tide table / forecast not provided)
    - FAIL  : margin < 0
    - LIMIT : 0 <= margin < tolerance
    - OK    : margin >= tolerance
    """
    ft = _to_float(forecast_tide_m_val, fallback=None, warn=False)
    if ft is None or (isinstance(ft, float) and np.isnan(ft)):
        return "VERIFY", "Forecast tide not provided"
    try:
        req = float(tide_required_m_val)
    except Exception:
        return "VERIFY", "Tide_required_m invalid"

    margin = float(ft - req)
    if margin < 0.0:
        return "FAIL", f"Forecast {ft:.2f}m < required {req:.2f}m"
    if margin < float(tolerance_m):
        return "LIMIT", f"Margin {margin:.2f}m < tol {float(tolerance_m):.2f}m"
    return "OK", f"Margin {margin:.2f}m"


def _detect_datetime_col(df: pd.DataFrame) -> Optional[str]:
    candidates = []
    for c in df.columns:
        s = df[c]
        # Skip if looks numeric
        if pd.api.types.is_numeric_dtype(s):
            continue
        try:
            parsed = pd.to_datetime(s, errors="coerce", utc=False)
            ratio = float(parsed.notna().mean())
            if ratio >= 0.6:
                candidates.append((ratio, c))
        except Exception:
            continue
    if not candidates:
        # fallback: try all columns
        for c in df.columns:
            try:
                parsed = pd.to_datetime(df[c], errors="coerce", utc=False)
                ratio = float(parsed.notna().mean())
                if ratio >= 0.6:
                    candidates.append((ratio, c))
            except Exception:
                continue
    if not candidates:
        return None
    candidates.sort(key=lambda x: x[0], reverse=True)
    return str(candidates[0][1])


def _detect_tide_col(df: pd.DataFrame, datetime_col: str) -> Optional[str]:
    # name-based priority
    priority = (
        "tide_m",
        "tide",
        "tide_height_m",
        "height_m",
        "wl_m",
        "water_level_m",
        "waterlevel_m",
        "wl",
    )
    cols_lower = {str(c).strip().lower(): c for c in df.columns}
    for p in priority:
        if p in cols_lower:
            if cols_lower[p] == datetime_col:
                continue
            return str(cols_lower[p])

    # fallback: first numeric column excluding datetime_col
    for c in df.columns:
        if str(c) == datetime_col:
            continue
        if pd.api.types.is_numeric_dtype(df[c]):
            return str(c)

    # last resort: try coercing others
    best = None
    for c in df.columns:
        if str(c) == datetime_col:
            continue
        s = pd.to_numeric(df[c], errors="coerce")
        ratio = float(s.notna().mean())
        if ratio > 0.6:
            if best is None or ratio > best[0]:
                best = (ratio, c)
    return str(best[1]) if best else None


def load_tide_table_any(path: Path) -> pd.DataFrame:
    """
    Load official tide table.
    Output df columns: ts (datetime64[ns]), tide_m (float).
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(str(path))

    ext = path.suffix.lower()
    if ext in (".csv", ".txt"):
        df = pd.read_csv(path, sep=None, engine="python")
    elif ext in (".xlsx", ".xls"):
        df = pd.read_excel(path)
    elif ext in (".json",):
        # Support list-of-dict or dict-with-records
        raw = path.read_text(encoding="utf-8", errors="replace")
        try:
            obj = pd.read_json(raw)
            df = obj
        except Exception:
            # try json.loads then DataFrame
            import json
            j = json.loads(raw)
            if isinstance(j, dict):
                if "records" in j:
                    df = pd.DataFrame(j["records"])
                elif "data" in j:
                    df = pd.DataFrame(j["data"])
                else:
                    df = pd.DataFrame([j])
            else:
                df = pd.DataFrame(j)
    else:
        # try csv fallback
        df = pd.read_csv(path, sep=None, engine="python")

    if df.empty:
        raise ValueError(f"Tide table is empty: {path}")

    dt_col = _detect_datetime_col(df)
    if not dt_col:
        raise ValueError(f"Cannot detect datetime column in tide table: cols={list(df.columns)}")

    tide_col = _detect_tide_col(df, dt_col)
    if not tide_col:
        raise ValueError(f"Cannot detect tide column in tide table: cols={list(df.columns)}")

    out = pd.DataFrame(
        {
            "ts": pd.to_datetime(df[dt_col], errors="coerce", utc=False),
            "tide_m": pd.to_numeric(df[tide_col], errors="coerce"),
        }
    ).dropna(subset=["ts", "tide_m"])

    if out.empty:
        raise ValueError("Parsed tide table has no valid (ts,tide_m) rows.")

    out = out.sort_values("ts").reset_index(drop=True)
    return out


def tide_at_timestamp(tide_df: pd.DataFrame, ts: pd.Timestamp) -> float:
    """
    Linear interpolation of tide at timestamp.
    Returns NaN if outside table range.
    """
    if tide_df is None or tide_df.empty:
        return float("nan")
    if ts is None or pd.isna(ts):
        return float("nan")
    ts = pd.to_datetime(ts, errors="coerce", utc=False)
    if pd.isna(ts):
        return float("nan")

    x = tide_df["ts"].astype("datetime64[ns]").view("int64").to_numpy()
    y = pd.to_numeric(tide_df["tide_m"], errors="coerce").to_numpy()
    xi = np.int64(ts.to_datetime64().astype("datetime64[ns]").astype("int64"))

    if xi < x.min() or xi > x.max():
        return float("nan")
    try:
        return float(np.interp(xi, x, y))
    except Exception:
        return float("nan")


def _norm_stage_key(x: str) -> str:
    s = str(x or "").strip().lower()
    s = " ".join(s.split())
    # normalize separators
    s = s.replace("_", " ").replace("-", " ")
    s = " ".join(s.split())
    return s


def load_stage_schedule_any(path: Path) -> pd.DataFrame:
    """
    Load stage schedule CSV/XLSX with at least (Stage, Timestamp).
    Output df columns: StageKey, ts.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(str(path))

    ext = path.suffix.lower()
    if ext in (".csv", ".txt"):
        df = pd.read_csv(path, sep=None, engine="python")
    elif ext in (".xlsx", ".xls"):
        df = pd.read_excel(path)
    else:
        df = pd.read_csv(path, sep=None, engine="python")

    if df.empty:
        raise ValueError(f"Stage schedule is empty: {path}")

    # detect stage col
    stage_candidates = ("stage", "stage_id", "stage name", "stagename", "stage_name")
    cols_lower = {str(c).strip().lower(): c for c in df.columns}
    stage_col = None
    for k in stage_candidates:
        if k in cols_lower:
            stage_col = cols_lower[k]
            break
    if stage_col is None:
        # fallback: first col
        stage_col = df.columns[0]

    # detect datetime col
    dt_col = None
    for k in ("timestamp", "datetime", "time", "ts", "start", "start_time", "eta"):
        if k in cols_lower and cols_lower[k] != stage_col:
            dt_col = cols_lower[k]
            break
    if dt_col is None:
        dt_col = _detect_datetime_col(df)
    if dt_col is None:
        raise ValueError(f"Cannot detect timestamp column in stage schedule: cols={list(df.columns)}")

    out = pd.DataFrame(
        {
            "StageKey": df[stage_col].astype(str).map(_norm_stage_key),
            "ts": pd.to_datetime(df[dt_col], errors="coerce", utc=False),
        }
    ).dropna(subset=["StageKey", "ts"])

    if out.empty:
        raise ValueError("Parsed stage schedule has no valid (Stage, ts) rows.")
    # If duplicates exist, keep earliest
    out = out.sort_values("ts").groupby("StageKey", as_index=False).first()
    return out


def apply_forecast_tide_from_table(
    stage_df: pd.DataFrame,
    tide_df: pd.DataFrame,
    schedule_df: pd.DataFrame,
    *,
    stage_col: str = "Stage",
    out_col: str = "Forecast_Tide_m",
    strategy: str = "fillna",
) -> pd.DataFrame:
    """
    Assign per-stage forecast tide from official tide table using stage schedule.
    strategy:
      - fillna : only fill when Forecast_Tide_m is missing/NaN
      - override : override existing values
    """
    if stage_df is None or stage_df.empty:
        return stage_df
    if tide_df is None or tide_df.empty or schedule_df is None or schedule_df.empty:
        return stage_df

    df = stage_df.copy()
    if out_col not in df.columns:
        df[out_col] = np.nan

    # map stage -> ts
    sched_map = {r["StageKey"]: r["ts"] for _, r in schedule_df.iterrows()}

    assigned = 0
    for i, r in df.iterrows():
        sk = _norm_stage_key(r.get(stage_col, ""))
        ts = sched_map.get(sk)
        if ts is None:
            continue
        tide_val = tide_at_timestamp(tide_df, ts)
        if np.isnan(tide_val):
            continue
        cur = _to_float(r.get(out_col), fallback=None, warn=False)
        if strategy == "override" or cur is None or (isinstance(cur, float) and np.isnan(cur)):
            df.at[i, out_col] = float(tide_val)
            assigned += 1

    # Convenience metadata
    df["Forecast_Tide_Source"] = np.where(
        pd.to_numeric(df[out_col], errors="coerce").notna(),
        "tide_table",
        df.get("Forecast_Tide_Source", "N/A") if "Forecast_Tide_Source" in df.columns else "N/A",
    )
    df.attrs["tide_assigned_count"] = assigned
    return df
