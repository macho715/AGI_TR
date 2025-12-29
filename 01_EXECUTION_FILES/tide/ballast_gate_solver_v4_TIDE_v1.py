#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ballast_gate_solver_v4.py
Definition-split + Gate-unified ballast solver.

Key points (per your “원인” 정리)
- Forecast_Tide_m (forecast) is NOT Required_WL_for_UKC_m (required WL).
- Draft is independent of tide.
- Draft vs Freeboard vs UKC are computed separately.
- Unified gate set:
    FWD <= FWD_MAX
    AFT >= AFT_MIN
    Freeboard >= FB_MIN (requires D_vessel_m)
    UKC >= UKC_MIN (requires DepthRef_m + Forecast_Tide_m)

Modes:
- limit  : soft violations (always returns best plan + violation meters)
- target : targets (Target_FWD_m, Target_AFT_m) via ΔW/ΔM equalities (with slack)

Dependencies:
- numpy, pandas, scipy
"""

from __future__ import annotations

import argparse
import re
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

try:
    from scipy.optimize import linprog
except Exception as e:
    raise SystemExit("scipy is required (pip install scipy).") from e


# -----------------------------
# Data models
# -----------------------------
@dataclass(frozen=True)
class HydroPoint:
    tmean_m: float
    tpc_t_per_cm: float
    mtc_t_m_per_cm: float
    lcf_m: float
    lbp_m: float


@dataclass
class Tank:
    name: str
    x_from_mid_m: float
    current_t: float
    min_t: float
    max_t: float
    mode: str
    use_flag: str
    pump_rate_tph: float
    priority_weight: float

    def bounds_pos_neg(self) -> Tuple[float, float, float, float]:
        """
        LP variables: p_i (fill), n_i (discharge)
        Δw_i = p_i - n_i
        """
        mode = (self.mode or "FILL_DISCHARGE").strip().upper()
        use = (self.use_flag or "N").strip().upper()

        if use != "Y" or mode in ("BLOCKED", "FIXED"):
            return 0.0, 0.0, 0.0, 0.0

        cur = float(self.current_t)
        mn = float(self.min_t)
        mx = float(self.max_t)

        max_fill = max(0.0, mx - cur)
        max_dis = max(0.0, cur - mn)

        # ENFORCE MODE AT BOUND LEVEL (non-negotiable)
        if mode == "DISCHARGE_ONLY":
            # prohibit fill (delta > 0)
            max_fill = 0.0
            # discharge allowed: max_dis = cur - mn (already calculated above)
            # No need to recalculate, but ensure it's correct
        elif mode == "FILL_ONLY":
            # prohibit discharge (delta < 0)
            max_dis = 0.0

        return 0.0, max_fill, 0.0, max_dis


# -----------------------------
# IO
# -----------------------------
def _read_df_any(path: Path) -> pd.DataFrame:
    """Read CSV/Excel/JSON with fast-path and parquet cache."""
    try:
        from io_parquet_cache import read_table_any
        has_fast_path = True
    except ImportError:
        has_fast_path = False

    suf = path.suffix.lower()
    if suf == ".csv":
        if has_fast_path:
            return read_table_any(path)  # ✅ fast-path + cache
        return pd.read_csv(path)  # Fallback
    if suf in (".xlsx", ".xls"):
        return pd.read_excel(path)
    if suf == ".parquet":
        if has_fast_path:
            return read_table_any(path)  # ✅ parquet cache
        return pd.read_parquet(path)  # Fallback
    if suf == ".json":
        return pd.DataFrame(json.loads(path.read_text(encoding="utf-8-sig")))
    raise ValueError(f"Unsupported file: {path}")


def load_hydro_table(path: Path) -> pd.DataFrame:
    df = _read_df_any(path).copy()
    need = {"Tmean_m", "TPC_t_per_cm", "MTC_t_m_per_cm", "LCF_m", "LBP_m"}
    miss = need - set(df.columns)
    if miss:
        raise ValueError(f"Hydro table missing columns: {sorted(miss)}")
    for c in need:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=["Tmean_m"]).sort_values("Tmean_m").reset_index(drop=True)
    return df


def interp_hydro(hdf: pd.DataFrame, tmean_m: float) -> HydroPoint:
    x = hdf["Tmean_m"].to_numpy(dtype=float)

    def _interp(col: str) -> float:
        return float(np.interp(float(tmean_m), x, hdf[col].to_numpy(dtype=float)))

    hp = HydroPoint(
        tmean_m=float(tmean_m),
        tpc_t_per_cm=_interp("TPC_t_per_cm"),
        mtc_t_m_per_cm=_interp("MTC_t_m_per_cm"),
        lcf_m=_interp("LCF_m"),
        lbp_m=_interp("LBP_m"),
    )
    if hp.tpc_t_per_cm <= 0 or hp.mtc_t_m_per_cm <= 0:
        raise ValueError("Invalid hydro: TPC/MTC must be > 0")
    return hp


def load_tanks(
    path: Path, default_min_t: float = 0.0, default_rate_tph: float = 50.0
) -> List[Tank]:
    df = _read_df_any(path).copy()
    req = {"Tank", "Current_t", "Capacity_t", "x_from_mid_m", "use_flag"}
    miss = req - set(df.columns)
    if miss:
        raise ValueError(f"tank SSOT missing columns: {sorted(miss)}")

    # defaults
    if "Min_t" not in df.columns:
        df["Min_t"] = default_min_t
    if "Max_t" not in df.columns:
        df["Max_t"] = df["Capacity_t"]
    if "mode" not in df.columns:
        df["mode"] = "FILL_DISCHARGE"
    if "pump_rate_tph" not in df.columns:
        df["pump_rate_tph"] = default_rate_tph
    if "priority_weight" not in df.columns:
        df["priority_weight"] = 1.0

    for c in [
        "Current_t",
        "Capacity_t",
        "x_from_mid_m",
        "Min_t",
        "Max_t",
        "pump_rate_tph",
        "priority_weight",
    ]:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0)

    tanks: List[Tank] = []
    for _, r in df.iterrows():
        cap = float(r["Capacity_t"])
        mx = float(r["Max_t"]) if float(r["Max_t"]) > 0 else cap
        mn = float(r["Min_t"])
        mx = min(mx, cap) if cap > 0 else mx
        cur = min(max(float(r["Current_t"]), mn), mx)

        tanks.append(
            Tank(
                name=str(r["Tank"]).strip(),
                x_from_mid_m=float(r["x_from_mid_m"]),
                current_t=cur,
                min_t=mn,
                max_t=mx,
                mode=str(r["mode"]).strip(),
                use_flag=str(r["use_flag"]).strip(),
                pump_rate_tph=max(float(r["pump_rate_tph"]), 0.01),
                priority_weight=max(float(r["priority_weight"]), 0.01),
            )
        )
    return tanks


def load_stage_table(path: Path) -> pd.DataFrame:
    df = _read_df_any(path).copy()

    # tolerant rename
    ren = {}
    for c in df.columns:
        cl = str(c).strip().lower()
        if cl in ("stage", "stage_name"):
            ren[c] = "Stage"
        elif cl in ("current_fwd_m", "dfwd_m", "fwd"):
            ren[c] = "Current_FWD_m"
        elif cl in ("current_aft_m", "daft_m", "aft"):
            ren[c] = "Current_AFT_m"
        elif cl in ("forecast_tide_m", "tide_m"):
            ren[c] = "Forecast_Tide_m"
        elif cl in ("depthref_m", "depth_ref_m"):
            ren[c] = "DepthRef_m"
        elif cl in ("squat_m",):
            ren[c] = "Squat_m"
        elif cl in ("safetyallow_m", "safety_allow_m"):
            ren[c] = "SafetyAllow_m"
        elif cl in ("fwd_max_m", "fwd_limit_m"):
            ren[c] = "FWD_MAX_m"
        elif cl in ("aft_min_m",):
            ren[c] = "AFT_MIN_m"
        elif cl in ("fb_min_m", "freeboard_min_m"):
            ren[c] = "FB_MIN_m"
        elif cl in ("ukc_min_m",):
            ren[c] = "UKC_MIN_m"
        elif cl in ("target_fwd_m",):
            ren[c] = "Target_FWD_m"
        elif cl in ("target_aft_m",):
            ren[c] = "Target_AFT_m"
        elif cl in ("ukc_ref",):
            ren[c] = "UKC_Ref"

    df = df.rename(columns=ren)
    need = {"Stage", "Current_FWD_m", "Current_AFT_m"}
    miss = need - set(df.columns)
    if miss:
        raise ValueError(f"stage table missing columns: {sorted(miss)}")

    for c in [
        "Current_FWD_m",
        "Current_AFT_m",
        "Forecast_Tide_m",
        "DepthRef_m",
        "Squat_m",
        "SafetyAllow_m",
        "FWD_MAX_m",
        "AFT_MIN_m",
        "FB_MIN_m",
        "UKC_MIN_m",
        "Target_FWD_m",
        "Target_AFT_m",
    ]:
        if c in df.columns:
            # Convert column to numeric - use apply for compatibility
            df[c] = df[c].apply(lambda x: pd.to_numeric(x, errors="coerce"))

    if "UKC_Ref" not in df.columns:
        df["UKC_Ref"] = "MAX"
    df["UKC_Ref"] = (
        df["UKC_Ref"].astype(str).str.upper().replace({"": "MAX"}).fillna("MAX")
    )

    return df


# -----------------------------
# Definition-split helpers
# -----------------------------
def pick_draft_ref_for_ukc(ref: str, dfwd: float, daft: float) -> float:
    r = (ref or "MAX").upper().strip()
    if r == "FWD":
        return float(dfwd)
    if r == "AFT":
        return float(daft)
    if r == "MEAN":
        return float(0.5 * (dfwd + daft))
    return float(max(dfwd, daft))


def ukc_value(
    depth_ref_m: Optional[float],
    wl_forecast_m: Optional[float],
    draft_ref_m: Optional[float],
    squat_m: float,
    safety_allow_m: float,
) -> float:
    if depth_ref_m is None or wl_forecast_m is None or draft_ref_m is None:
        return float("nan")
    return float(depth_ref_m + wl_forecast_m - draft_ref_m - squat_m - safety_allow_m)


def required_wl_for_ukc(
    depth_ref_m: Optional[float],
    ukc_min_m: Optional[float],
    draft_ref_m: Optional[float],
    squat_m: float,
    safety_allow_m: float,
) -> float:
    if depth_ref_m is None or ukc_min_m is None or draft_ref_m is None:
        return float("nan")
    return float(ukc_min_m + draft_ref_m + squat_m + safety_allow_m - depth_ref_m)


def freeboard_min(d_vessel_m: Optional[float], dfwd: float, daft: float) -> float:
    if d_vessel_m is None:
        return float("nan")
    return float(min(d_vessel_m - dfwd, d_vessel_m - daft))


# -----------------------------
# Draft model & LP coefficients
# -----------------------------
def predict_drafts(
    dfwd0: float,
    daft0: float,
    hydro: HydroPoint,
    tanks: List[Tank],
    delta: Dict[str, float],
) -> Dict[str, float]:
    """
    Draft prediction WITHOUT tide mixing.
    ΔTmean = ΣΔw / (TPC*100)
    ΔTrim  = ΣΔw*(x-LCF) / (MTC*100)
    Lpp/LCF-based trim distribution:
      slope = ΔTrim / LBP
      Dfwd = Dfwd0 + ΔTmean + slope*(x_fp - LCF)
      Daft = Daft0 + ΔTmean + slope*(x_ap - LCF)
    Fallback to 0.5*ΔTrim if LBP is missing.
    """
    total_w = 0.0
    total_m = 0.0
    for t in tanks:
        dw = float(delta.get(t.name, 0.0))
        total_w += dw
        total_m += dw * (t.x_from_mid_m - hydro.lcf_m)

    d_tmean = total_w / (hydro.tpc_t_per_cm * 100.0)
    d_trim = total_m / (hydro.mtc_t_m_per_cm * 100.0)

    lbp = float(hydro.lbp_m) if hydro.lbp_m is not None else None
    lcf = float(hydro.lcf_m) if hydro.lcf_m is not None else 0.0
    if lbp is not None and lbp != 0.0 and not np.isnan(lbp):
        x_fp = -lbp / 2.0
        x_ap = lbp / 2.0
        slope = d_trim / lbp
        dfwd = dfwd0 + d_tmean + slope * (x_fp - lcf)
        daft = daft0 + d_tmean + slope * (x_ap - lcf)
    else:
        dfwd = dfwd0 + d_tmean - 0.5 * d_trim
        daft = daft0 + d_tmean + 0.5 * d_trim

    return {
        "ΔW_t": float(total_w),
        "ΔM_t_m": float(total_m),
        "FWD_new_m": float(dfwd),
        "AFT_new_m": float(daft),
        "Trim_new_m": float(daft - dfwd),
        "Tmean_new_m": float(0.5 * (dfwd + daft)),
    }


def build_rows(hydro: HydroPoint, tanks: List[Tank]) -> Tuple[np.ndarray, np.ndarray]:
    """
    Build ΣΔw and ΣΔw*(x-LCF) rows for variables [p1,n1,p2,n2,...]
    """
    n = len(tanks)
    rowW = np.zeros(2 * n, dtype=float)
    rowM = np.zeros(2 * n, dtype=float)
    for i, t in enumerate(tanks):
        arm = t.x_from_mid_m - hydro.lcf_m
        rowW[2 * i] = 1.0
        rowW[2 * i + 1] = -1.0
        rowM[2 * i] = arm
        rowM[2 * i + 1] = -arm
    return rowW, rowM


# -----------------------------
# Solver
# -----------------------------
def solve_lp(
    *,
    dfwd0: float,
    daft0: float,
    hdf: pd.DataFrame,
    tanks: List[Tank],
    mode: str,
    iterate_hydro: int,
    # targets
    target_fwd: Optional[float],
    target_aft: Optional[float],
    # gates
    fwd_max: Optional[float],
    aft_min: Optional[float],
    d_vessel: Optional[float],
    fb_min: Optional[float],
    ukc_min: Optional[float],
    depth_ref: Optional[float],
    forecast_tide: Optional[float],
    squat: float,
    safety_allow: float,
    ukc_ref: str,
    trim_abs_limit_m: Optional[float] = None,
    trim_limit_enforced: bool = True,
    freeboard_min_enforced: bool = True,
    # objective + penalties
    prefer_time: bool,
    violation_penalty: float,
    slack_weight_penalty: float,
    slack_moment_penalty: float,
) -> Tuple[pd.DataFrame, Dict[str, float], Dict[str, float], HydroPoint]:
    mode = (mode or "").strip().lower()
    if mode not in ("limit", "target"):
        raise ValueError("mode must be limit|target")

    tmean = 0.5 * (dfwd0 + daft0)
    hydro_used = interp_hydro(hdf, tmean)

    last_plan = pd.DataFrame()
    last_pred: Dict[str, float] = {}
    last_delta: Dict[str, float] = {}

    for _ in range(max(1, int(iterate_hydro))):
        hydro_used = interp_hydro(hdf, tmean)

        n = len(tanks)
        var_names: List[str] = []
        bounds: List[Tuple[float, Optional[float]]] = []
        c: List[float] = []

        # tank vars
        for t in tanks:
            p_lo, p_hi, n_lo, n_hi = t.bounds_pos_neg()
            var_names += [f"{t.name}__p", f"{t.name}__n"]
            bounds += [(p_lo, p_hi), (n_lo, n_hi)]
            w = t.priority_weight
            if prefer_time:
                c += [w / t.pump_rate_tph, w / t.pump_rate_tph]
            else:
                c += [w, w]

        # slacks
        if mode == "limit":
            slack_names = ["viol_fwd", "viol_aft", "viol_fb", "viol_ukc"]
            var_names += slack_names
            bounds += [(0.0, None)] * 4
            c += [violation_penalty] * 4
            if freeboard_min_enforced:
                try:
                    viol_fb_idx = var_names.index("viol_fb")
                    bounds[viol_fb_idx] = (0.0, 0.0)
                except Exception:
                    pass
        else:
            slack_names = ["slackW_pos", "slackW_neg", "slackM_pos", "slackM_neg"]
            var_names += slack_names
            bounds += [(0.0, None)] * 4
            c += [
                slack_weight_penalty,
                slack_weight_penalty,
                slack_moment_penalty,
                slack_moment_penalty,
            ]

        c = np.array(c, dtype=float)

        # coefficients
        rowW, rowM = build_rows(hydro_used, tanks)
        coef_tmean = rowW / (hydro_used.tpc_t_per_cm * 100.0)
        coef_trim = rowM / (hydro_used.mtc_t_m_per_cm * 100.0)
        # Lpp/LCF-based distribution; fallback to legacy if LBP missing
        lbp = float(hydro_used.lbp_m) if hydro_used.lbp_m is not None else None
        lcf = float(hydro_used.lcf_m) if hydro_used.lcf_m is not None else 0.0
        if lbp is not None and lbp != 0.0 and not np.isnan(lbp):
            x_fp = -lbp / 2.0
            x_ap = lbp / 2.0
            coef_dfwd = coef_tmean + coef_trim * ((x_fp - lcf) / lbp)
            coef_daft = coef_tmean + coef_trim * ((x_ap - lcf) / lbp)
        else:
            coef_dfwd = coef_tmean - 0.5 * coef_trim
            coef_daft = coef_tmean + 0.5 * coef_trim

        A_eq, b_eq = [], []
        if mode == "target":
            if target_fwd is None or target_aft is None:
                raise ValueError("target mode requires Target_FWD_m and Target_AFT_m")

            mean0 = 0.5 * (dfwd0 + daft0)
            meanT = 0.5 * (target_fwd + target_aft)
            dTmean = meanT - mean0

            trim0 = daft0 - dfwd0
            trimT = target_aft - target_fwd
            dTrim = trimT - trim0

            reqW = dTmean * hydro_used.tpc_t_per_cm * 100.0
            reqM = dTrim * hydro_used.mtc_t_m_per_cm * 100.0

            eqW = np.zeros(len(var_names), dtype=float)
            eqW[: 2 * n] = rowW
            eqW[var_names.index("slackW_pos")] = 1.0
            eqW[var_names.index("slackW_neg")] = -1.0

            eqM = np.zeros(len(var_names), dtype=float)
            eqM[: 2 * n] = rowM
            eqM[var_names.index("slackM_pos")] = 1.0
            eqM[var_names.index("slackM_neg")] = -1.0

            A_eq = [eqW, eqM]
            b_eq = [reqW, reqM]

        A_ub, b_ub = [], []

        if mode == "limit":
            fwd_max_eff = fwd_max
            if fwd_max is not None and forecast_tide is not None and not np.isnan(forecast_tide):
                # Gate-B is CD-referenced; convert to MSL for comparison
                fwd_max_eff = float(fwd_max + forecast_tide)
            # FWD <= FWD_MAX + viol_fwd
            if fwd_max_eff is not None and not np.isnan(fwd_max_eff):
                row = np.zeros(len(var_names), dtype=float)
                row[: 2 * n] = coef_dfwd
                row[var_names.index("viol_fwd")] = -1.0
                A_ub.append(row)
                b_ub.append(float(fwd_max_eff - dfwd0))

            # AFT >= AFT_MIN  => -AFT - viol_aft <= -AFT_MIN
            if aft_min is not None and not np.isnan(aft_min):
                row = np.zeros(len(var_names), dtype=float)
                row[: 2 * n] = -coef_daft
                row[var_names.index("viol_aft")] = -1.0
                A_ub.append(row)
                b_ub.append(float(-(aft_min - daft0)))

            # Freeboard >= FB_MIN -> Draft_end <= D_vessel - FB_MIN
            if (d_vessel is not None and fb_min is not None) and (
                not np.isnan(d_vessel) and not np.isnan(fb_min)
            ):
                draft_max = float(d_vessel - fb_min)

                row = np.zeros(len(var_names), dtype=float)
                row[: 2 * n] = coef_dfwd
                row[var_names.index("viol_fb")] = -1.0
                A_ub.append(row)
                b_ub.append(float(draft_max - dfwd0))

                row = np.zeros(len(var_names), dtype=float)
                row[: 2 * n] = coef_daft
                row[var_names.index("viol_fb")] = -1.0
                A_ub.append(row)
                b_ub.append(float(draft_max - daft0))

            # UKC >= UKC_MIN -> Draft_ref <= DepthRef + WL - squat - safety - UKC_MIN
            if (
                ukc_min is not None
                and depth_ref is not None
                and forecast_tide is not None
            ) and (
                not np.isnan(ukc_min)
                and not np.isnan(depth_ref)
                and not np.isnan(forecast_tide)
            ):
                draft_max = float(
                    depth_ref + forecast_tide - squat - safety_allow - ukc_min
                )

                ref = (ukc_ref or "MAX").upper().strip()

                def add_ukc_row(coef_end, base_draft):
                    row = np.zeros(len(var_names), dtype=float)
                    row[: 2 * n] = coef_end
                    row[var_names.index("viol_ukc")] = -1.0
                    A_ub.append(row)
                    b_ub.append(float(draft_max - base_draft))

                if ref == "FWD":
                    add_ukc_row(coef_dfwd, dfwd0)
                elif ref == "AFT":
                    add_ukc_row(coef_daft, daft0)
                elif ref == "MEAN":
                    coef_mean = 0.5 * (coef_dfwd + coef_daft)
                    add_ukc_row(coef_mean, 0.5 * (dfwd0 + daft0))
                else:  # MAX
                    add_ukc_row(coef_dfwd, dfwd0)
                    add_ukc_row(coef_daft, daft0)

            # Trim constraint (hard if enforced): |Trim| <= trim_abs_limit_m
            if trim_limit_enforced and trim_abs_limit_m is not None:
                try:
                    trim_limit = float(trim_abs_limit_m)
                    trim0 = daft0 - dfwd0
                    coef_trim_m = coef_daft - coef_dfwd

                    row = np.zeros(len(var_names), dtype=float)
                    row[: 2 * n] = coef_trim_m
                    A_ub.append(row)
                    b_ub.append(float(trim_limit - trim0))

                    row = np.zeros(len(var_names), dtype=float)
                    row[: 2 * n] = -coef_trim_m
                    A_ub.append(row)
                    b_ub.append(float(trim_limit + trim0))
                except Exception:
                    pass

        res = linprog(
            c=c,
            A_ub=(np.vstack(A_ub) if A_ub else None),
            b_ub=(np.array(b_ub, dtype=float) if b_ub else None),
            A_eq=(np.vstack(A_eq) if A_eq else None),
            b_eq=(np.array(b_eq, dtype=float) if b_eq else None),
            bounds=bounds,
            method="highs",
        )
        if not res.success:
            raise RuntimeError(f"LP failed: {res.message}")

        x = res.x
        delta: Dict[str, float] = {}
        plan_rows = []
        for i, t in enumerate(tanks):
            p = float(x[2 * i])
            nvar = float(x[2 * i + 1])
            dw = p - nvar
            pumped = p + nvar
            if abs(dw) < 1e-10 and pumped < 1e-10:
                continue
            delta[t.name] = dw
            plan_rows.append(
                {
                    "Tank": t.name,
                    "Action": "FILL" if dw > 0 else "DISCHARGE",
                    "Delta_t": round(dw, 2),
                    "PumpTime_h": round(pumped / t.pump_rate_tph, 2),
                }
            )

        plan = (
            pd.DataFrame(plan_rows)
            .sort_values(["PumpTime_h", "Tank"], ascending=[False, True])
            .reset_index(drop=True)
            if plan_rows
            else pd.DataFrame()
        )
        pred = predict_drafts(dfwd0, daft0, hydro_used, tanks, delta)

        if mode == "limit":
            pred["viol_fwd_max_m"] = float(x[var_names.index("viol_fwd")])
            pred["viol_aft_min_m"] = float(x[var_names.index("viol_aft")])
            pred["viol_fb_min_m"] = float(x[var_names.index("viol_fb")])
            pred["viol_ukc_min_m"] = float(x[var_names.index("viol_ukc")])

        # update for next iteration
        tmean = float(pred["Tmean_new_m"])
        last_plan, last_pred, last_delta = plan, pred, delta

    return last_plan, last_pred, last_delta, hydro_used


def apply_delta(tanks: List[Tank], delta: Dict[str, float]) -> List[Tank]:
    out = []
    for t in tanks:
        dw = float(delta.get(t.name, 0.0))
        out.append(
            Tank(
                name=t.name,
                x_from_mid_m=t.x_from_mid_m,
                current_t=min(max(t.current_t + dw, t.min_t), t.max_t),
                min_t=t.min_t,
                max_t=t.max_t,
                mode=t.mode,
                use_flag=t.use_flag,
                pump_rate_tph=t.pump_rate_tph,
                priority_weight=t.priority_weight,
            )
        )
    return out


def diagnose_solver_plan_absence(
    stage_name: str,
    dfwd0: float,
    daft0: float,
    aft_min_m: float,
    fwd_max_m: float,
    fb_min_m: Optional[float],
    d_vessel_m: Optional[float],
) -> Dict[str, object]:
    diagnosis = {
        "stage": stage_name,
        "aft_draft": daft0,
        "fwd_draft": dfwd0,
        "aft_min_required": aft_min_m,
        "fwd_max_required": fwd_max_m,
        "aft_margin": daft0 - aft_min_m,
        "fwd_margin": fwd_max_m - dfwd0,
        "possible_reasons": [],
    }

    if diagnosis["aft_margin"] < -0.50:
        diagnosis["possible_reasons"].append(
            "AFT draft below limit by >0.50m; may need significant ballast"
        )
    elif diagnosis["aft_margin"] < -0.30:
        diagnosis["possible_reasons"].append(
            "AFT draft below limit by >0.30m; tank capacity constraints likely"
        )

    if diagnosis["fwd_margin"] < -0.30:
        diagnosis["possible_reasons"].append(
            "FWD draft exceeds limit by >0.30m; constraints may conflict"
        )

    if fb_min_m is not None and d_vessel_m is not None:
        fb_fwd = d_vessel_m - dfwd0
        fb_aft = d_vessel_m - daft0
        fb_min = min(fb_fwd, fb_aft)
        if fb_min < fb_min_m:
            diagnosis["possible_reasons"].append(
                "Freeboard below minimum; limited ballast options may block plan"
            )

    if not diagnosis["possible_reasons"]:
        diagnosis["possible_reasons"].append(
            "Solver returned empty plan; check tank operability and constraints"
        )

    return diagnosis


# -----------------------------
# Main
# -----------------------------
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tank", required=True)
    ap.add_argument("--hydro", required=True)
    ap.add_argument("--mode", choices=["limit", "target"], required=True)
    ap.add_argument("--iterate_hydro", type=int, default=2)
    ap.add_argument("--prefer_tons", action="store_true")

    # single-case inputs
    ap.add_argument("--current_fwd", type=float, default=None)
    ap.add_argument("--current_aft", type=float, default=None)

    # targets (target mode)
    ap.add_argument("--target_fwd", type=float, default=None)
    ap.add_argument("--target_aft", type=float, default=None)

    # unified gates (limit mode)
    ap.add_argument("--fwd_max", type=float, default=None)
    ap.add_argument("--aft_min", type=float, default=None)
    ap.add_argument("--d_vessel", type=float, default=None)
    ap.add_argument("--fb_min", type=float, default=None)
    ap.add_argument(
        "--trim_abs_limit",
        type=float,
        default=0.50,
        help="Absolute trim limit (m) for hard constraint.",
    )
    ap.add_argument(
        "--trim_limit_enforced",
        dest="trim_limit_enforced",
        action="store_true",
        default=True,
        help="Enforce trim limit as hard constraint (default: enabled).",
    )
    ap.add_argument(
        "--no-trim-limit-enforced",
        dest="trim_limit_enforced",
        action="store_false",
        help="Disable hard enforcement of trim limit.",
    )
    ap.add_argument(
        "--freeboard_min_m",
        type=float,
        default=0.0,
        help="Minimum freeboard requirement (m) for hard constraint.",
    )
    ap.add_argument(
        "--freeboard_min_enforced",
        dest="freeboard_min_enforced",
        action="store_true",
        default=True,
        help="Enforce minimum freeboard as hard constraint (default: enabled).",
    )
    ap.add_argument(
        "--no-freeboard-min-enforced",
        dest="freeboard_min_enforced",
        action="store_false",
        help="Disable hard enforcement of minimum freeboard.",
    )

    # tide/WL/UKC split
    ap.add_argument("--forecast_tide", type=float, default=None)
    ap.add_argument("--depth_ref", type=float, default=None)
    ap.add_argument("--ukc_min", type=float, default=None)
    ap.add_argument("--ukc_ref", type=str, default="MAX")
    ap.add_argument("--squat", type=float, default=0.0)
    ap.add_argument("--safety_allow", type=float, default=0.0)

    # penalties
    ap.add_argument("--violation_penalty", type=float, default=1e7)
    ap.add_argument("--slack_weight_penalty", type=float, default=1e6)
    ap.add_argument("--slack_moment_penalty", type=float, default=1e3)

    # stage mode
    ap.add_argument("--stage", type=str, default="")
    ap.add_argument("--out_plan", type=str, default="ballast_plan_out.csv")
    ap.add_argument("--out_summary", type=str, default="ballast_summary_out.csv")
    ap.add_argument("--out_stage_plan", type=str, default="ballast_stage_plan_out.csv")
    ap.add_argument(
        "--stateful_solver",
        "--stateful",
        action="store_true",
        help="Carry-forward tank Current_t across stages (stateful stage loop).",
    )
    ap.add_argument(
        "--reset_tank_state",
        default="",
        help="Comma list or regex (prefix 're:') to reset Current_t from SSOT.",
    )
    ap.add_argument(
        "--state_trace_csv",
        default="",
        help="Optional CSV path for stateful tank snapshot tracing.",
    )
    ap.add_argument(
        "--tank_operability_json",
        default="",
        help="Optional JSON with tank operability metadata (e.g., PRE_BALLAST_ONLY).",
    )
    ap.add_argument(
        "--disable_preballast_only_on_operational_stages",
        action="store_true",
        default=False,
        help="Disable enforcing PRE_BALLAST_ONLY tanks as FIXED on operational stages.",
    )
    ap.add_argument(
        "--operational_stage_regex",
        default=r"(6a|6b|critical|ramp|roll|loadout)",
        help="Regex to decide operational stages for PRE_BALLAST_ONLY enforcement.",
    )

    args = ap.parse_args()
    if args.fb_min is None:
        args.fb_min = args.freeboard_min_m

    print(
        "[INFO] Applying gates: Gate-A=AFT_MIN_2p70, "
        "Gate-B=FWD_MAX_2p70_critical_only (critical only)"
    )

    tanks = load_tanks(Path(args.tank))
    hdf = load_hydro_table(Path(args.hydro))

    prefer_time = not args.prefer_tons

    # Stage mode
    if args.stage:
        st = load_stage_table(Path(args.stage))
        tank_ssot_cache: Dict[str, List[Tank]] = {}
        default_ssot_path = Path(args.tank).resolve()
        stage_table_dir = Path(args.stage).resolve().parent

        def _load_tanks_cached(ssot_path: Path) -> List[Tank]:
            key = str(ssot_path.resolve())
            if key not in tank_ssot_cache:
                tank_ssot_cache[key] = load_tanks(ssot_path)
            return [
                Tank(
                    name=t.name,
                    x_from_mid_m=t.x_from_mid_m,
                    current_t=t.current_t,
                    min_t=t.min_t,
                    max_t=t.max_t,
                    mode=t.mode,
                    use_flag=t.use_flag,
                    pump_rate_tph=t.pump_rate_tph,
                    priority_weight=t.priority_weight,
                )
                for t in tank_ssot_cache[key]
            ]

        def _tank_state_from_list(tanks: List[Tank]) -> Dict[str, float]:
            return {t.name: float(t.current_t) for t in tanks}

        def _merge_policy_with_state(
            policy_tanks: List[Tank],
            cur_state: Dict[str, float],
        ) -> List[Tank]:
            stage_tanks = []
            for p in policy_tanks:
                current = float(cur_state.get(p.name, p.current_t))
                current = min(max(current, float(p.min_t)), float(p.max_t))
                stage_tanks.append(
                    Tank(
                        name=p.name,
                        x_from_mid_m=p.x_from_mid_m,
                        current_t=current,
                        min_t=p.min_t,
                        max_t=p.max_t,
                        mode=p.mode,
                        use_flag=p.use_flag,
                        pump_rate_tph=p.pump_rate_tph,
                        priority_weight=p.priority_weight,
                    )
                )
            return stage_tanks

        def _load_operability_map(path: str) -> Dict[str, str]:
            if not path:
                return {}
            p = Path(str(path))
            if not p.exists():
                print(f"[WARN] tank_operability_json not found: {p}")
                return {}
            try:
                obj = json.loads(p.read_text(encoding="utf-8"))
            except Exception as e:
                print(
                    f"[WARN] tank_operability_json read failed: {type(e).__name__}: {e}"
                )
                return {}

            def _set_oper(m: Dict[str, str], key: str, oper: str) -> None:
                key = str(key or "").strip().upper()
                oper = str(oper or "").strip().upper()
                if key and oper:
                    m[key] = oper

            oper_map: Dict[str, str] = {}

            if isinstance(obj, dict) and isinstance(obj.get("tanks"), list):
                for row in obj["tanks"]:
                    if not isinstance(row, dict):
                        continue
                    _set_oper(
                        oper_map,
                        row.get("id") or row.get("Tank") or row.get("tank"),
                        row.get("operability"),
                    )

            if isinstance(obj, dict) and isinstance(
                obj.get("operational_constraints"), dict
            ):
                for key, meta in obj["operational_constraints"].items():
                    if not isinstance(meta, dict):
                        continue
                    oper = meta.get("operability")
                    if not oper:
                        transfer = meta.get("transfer_authorized")
                        pump_access = meta.get("pump_access")
                        role = str(meta.get("role", "")).lower()
                        if transfer is False or pump_access is False or "pre-ballast" in role:
                            oper = "PRE_BALLAST_ONLY"
                    _set_oper(oper_map, key, oper)

            if isinstance(obj, dict) and isinstance(obj.get("tank_operability"), dict):
                for key, meta in obj["tank_operability"].items():
                    if not isinstance(meta, dict):
                        continue
                    oper = meta.get("operability")
                    if not oper:
                        transfer = meta.get("transfer_authorized")
                        pump_access = meta.get("pump_access")
                        role = str(meta.get("role", "")).lower()
                        if transfer is False or pump_access is False or "pre-ballast" in role:
                            oper = "PRE_BALLAST_ONLY"
                    _set_oper(oper_map, key, oper)

            if isinstance(obj, dict):
                for key, meta in obj.items():
                    if not isinstance(meta, dict) or key in (
                        "tanks",
                        "operational_constraints",
                        "tank_operability",
                    ):
                        continue
                    _set_oper(oper_map, key, meta.get("operability"))

            return oper_map

        def _is_operational_stage(stage_name: str, regex: str) -> bool:
            try:
                return re.search(regex, stage_name or "", re.IGNORECASE) is not None
            except re.error:
                print(
                    f"[WARN] operational_stage_regex invalid: {regex!r}; defaulting to False."
                )
                return False

        def _force_fixed_for_preballast_only(
            stage_tanks: List[Tank],
            oper_map: Dict[str, str],
            op_stage: bool,
        ) -> List[Tank]:
            if not op_stage or not oper_map:
                return stage_tanks
            for t in stage_tanks:
                key = str(t.name).strip().upper()
                base = key.split(".", 1)[0]
                oper = oper_map.get(key) or oper_map.get(base) or ""
                if oper == "PRE_BALLAST_ONLY":
                    t.mode = "FIXED"
                    if (t.use_flag or "").strip().upper() != "Y":
                        t.use_flag = "Y"
            return stage_tanks

        def _should_reset_stage(stage_name: str, spec: str) -> bool:
            if not spec:
                return False
            spec = str(spec).strip()
            if not spec:
                return False
            if spec.lower().startswith("re:"):
                pattern = spec[3:].strip()
                if not pattern:
                    return False
                try:
                    return re.search(pattern, stage_name, re.IGNORECASE) is not None
                except re.error:
                    print(
                        f"[WARN] reset_tank_state regex invalid: {pattern!r}; ignoring."
                    )
                    return False
            choices = [s.strip().lower() for s in spec.split(",") if s.strip()]
            return stage_name.strip().lower() in choices

        trace_keys = ("VOID3.P", "VOID3.S", "FWB2.P", "FWB2.S")

        def _log_state(stage_name: str, cur_state: Dict[str, float]) -> None:
            snap = {k: round(float(cur_state.get(k, 0.0)), 3) for k in trace_keys}
            print(f"[STATE][{stage_name}] {snap}")

        def _trace_row(
            stage_name: str,
            phase: str,
            cur_state_map: Dict[str, float],
        ) -> Dict[str, object]:
            row: Dict[str, object] = {"Stage": stage_name, "Phase": phase}
            for key in trace_keys:
                row[key] = round(float(cur_state_map.get(key, 0.0)), 3)
            return row

        default_policy_tanks = _load_tanks_cached(default_ssot_path)
        oper_map = _load_operability_map(args.tank_operability_json)
        cur_state = _tank_state_from_list(default_policy_tanks)
        cur_tanks = list(default_policy_tanks)
        state_trace_rows = []
        all_plan = []
        all_sum = []

        def _is_true(val) -> bool:
            if isinstance(val, str):
                return val.strip().lower() in ("1", "true", "y", "yes")
            return bool(val) if pd.notna(val) else False

        for _, r in st.iterrows():
            stage_name = str(r.get("Stage", "Unknown"))
            ssot_name = r.get("Tank_SSOT_CSV", None)
            ssot_was_custom = False
            policy_tanks = default_policy_tanks
            policy_source = default_ssot_path.name
            if ssot_name and str(ssot_name).strip():
                ssot_path = (stage_table_dir / str(ssot_name).strip()).resolve()
                if ssot_path.exists():
                    policy_tanks = _load_tanks_cached(ssot_path)
                    policy_source = ssot_path.name
                    print(
                        f"[INFO] Stage {stage_name}: Using tank SSOT {ssot_path.name}"
                    )
                    ssot_was_custom = True
                else:
                    print(
                        f"[WARN] Stage {stage_name}: Tank_SSOT_CSV={ssot_name} not found, using default"
                    )
                    policy_tanks = default_policy_tanks
                    policy_source = default_ssot_path.name

            if args.stateful_solver and _should_reset_stage(
                stage_name, args.reset_tank_state
            ):
                cur_state = _tank_state_from_list(policy_tanks)
                print(
                    f"[INFO] Stage {stage_name}: reset tank state from {policy_source}"
                )

            dfwd0 = float(r["Current_FWD_m"])
            daft0 = float(r["Current_AFT_m"])

            # Helper function to safely get float value from Series
            def safe_get_float(row, key, default):
                if key in row.index:
                    val = row[key]
                    if (
                        pd.notna(val)
                        if not isinstance(val, pd.Series)
                        else not pd.isna(val).any()
                    ):
                        try:
                            return float(val)
                        except (ValueError, TypeError):
                            pass
                return default

            fwd_max = safe_get_float(r, "FWD_MAX_m", args.fwd_max)
            aft_min = safe_get_float(r, "AFT_MIN_m", args.aft_min)
            fb_min = safe_get_float(r, "FB_MIN_m", args.fb_min)
            ukc_min = safe_get_float(r, "UKC_MIN_m", args.ukc_min)
            wl = safe_get_float(r, "Forecast_Tide_m", args.forecast_tide)
            depth_ref = safe_get_float(r, "DepthRef_m", args.depth_ref)
            squat = safe_get_float(r, "Squat_m", args.squat)
            safety = safe_get_float(r, "SafetyAllow_m", args.safety_allow)
            target_fwd = safe_get_float(r, "Target_FWD_m", args.target_fwd)
            target_aft = safe_get_float(r, "Target_AFT_m", args.target_aft)
            ukc_ref = str(r.get("UKC_Ref", args.ukc_ref)).upper().strip() or "MAX"

            op_stage = _is_operational_stage(
                stage_name, args.operational_stage_regex
            )

            if args.stateful_solver:
                stage_tanks = _merge_policy_with_state(policy_tanks, cur_state)
            else:
                cur_tanks = policy_tanks
                stage_tanks = cur_tanks

            if not args.disable_preballast_only_on_operational_stages:
                stage_tanks = _force_fixed_for_preballast_only(
                    stage_tanks, oper_map, op_stage
                )

            if args.stateful_solver and args.state_trace_csv:
                stage_state = _tank_state_from_list(stage_tanks)
                state_trace_rows.append(_trace_row(stage_name, "before", stage_state))

            # Stage-level SSOT already handles DISCHARGE_ONLY for FWD tanks (via tank_ssot_for_solver__aftmin.csv)
            # Only apply Ban_FWD_Tanks logic if stage-level SSOT was NOT used (fallback)
            if not ssot_was_custom:
                # Fallback: apply Ban_FWD_Tanks logic only when stage-level SSOT was not used
                try:
                    ban_fwd = r.get("Ban_FWD_Tanks", False)
                    if isinstance(ban_fwd, str):
                        ban_fwd = ban_fwd.strip().lower() in ("1", "true", "y", "yes")
                    if bool(ban_fwd):
                        base_tanks = stage_tanks
                        stage_tanks = []
                        fwd_tanks_modified = 0
                        for t in base_tanks:
                            t2 = Tank(
                                name=t.name,
                                x_from_mid_m=t.x_from_mid_m,
                                current_t=t.current_t,
                                min_t=t.min_t,
                                max_t=t.max_t,
                                mode=t.mode,
                                use_flag=t.use_flag,
                                pump_rate_tph=t.pump_rate_tph,
                                priority_weight=t.priority_weight,
                            )
                            if t2.x_from_mid_m < 0:
                                t2.mode = "DISCHARGE_ONLY"
                                t2.min_t = 0.0
                                if t2.max_t > t2.current_t:
                                    t2.max_t = t2.current_t
                                if t2.use_flag != "Y":
                                    t2.use_flag = "Y"
                                fwd_tanks_modified += 1
                            stage_tanks.append(t2)
                        if fwd_tanks_modified > 0:
                            print(
                                f"[INFO] AFT-min stage (fallback): {fwd_tanks_modified} FWD tank(s) set to DISCHARGE_ONLY (fill prohibited, discharge allowed)"
                            )
                except Exception as e:
                    print(
                        f"[WARN] FWD tank discharge-only setup failed: {type(e).__name__}: {e}"
                    )

            plan, pred, delta, _ = solve_lp(
                dfwd0=dfwd0,
                daft0=daft0,
                hdf=hdf,
                tanks=stage_tanks,
                mode=args.mode,
                iterate_hydro=args.iterate_hydro,
                target_fwd=target_fwd,
                target_aft=target_aft,
                fwd_max=fwd_max,
                aft_min=aft_min,
                d_vessel=args.d_vessel,
                fb_min=fb_min,
                ukc_min=ukc_min,
                depth_ref=depth_ref,
                forecast_tide=wl,
                squat=squat,
                safety_allow=safety,
                ukc_ref=ukc_ref,
                trim_abs_limit_m=args.trim_abs_limit,
                trim_limit_enforced=args.trim_limit_enforced,
                freeboard_min_enforced=args.freeboard_min_enforced,
                prefer_time=prefer_time,
                violation_penalty=args.violation_penalty,
                slack_weight_penalty=args.slack_weight_penalty,
                slack_moment_penalty=args.slack_moment_penalty,
            )

            dfwd_new = float(pred["FWD_new_m"])
            daft_new = float(pred["AFT_new_m"])
            draft_ref = pick_draft_ref_for_ukc(ukc_ref, dfwd_new, daft_new)
            plan_row_count = 0 if plan.empty else len(plan)

            stage_name = str(r.get("Stage", "Unknown"))
            stage_is_critical = False
            if "Gate_B_Applies" in r.index:
                stage_is_critical = _is_true(r.get("Gate_B_Applies"))
            elif "FWD_MAX_applicable" in r.index:
                stage_is_critical = _is_true(r.get("FWD_MAX_applicable"))
            else:
                stage_l = stage_name.lower()
                stage_is_critical = any(
                    key in stage_l for key in ("preballast", "critical", "6a", "ramp")
                )

            plan_diag = ""
            if plan.empty and stage_is_critical:
                diag = diagnose_solver_plan_absence(
                    stage_name=stage_name,
                    dfwd0=dfwd0,
                    daft0=daft0,
                    aft_min_m=aft_min,
                    fwd_max_m=fwd_max,
                    fb_min_m=fb_min,
                    d_vessel_m=args.d_vessel,
                )
                plan_diag = "; ".join(diag.get("possible_reasons", []))
                print(f"[WARN] Stage {stage_name}: solver plan empty. {plan_diag}")

            # Tide/UKC derived fields (definition-split aware)
            try:
                req_raw = required_wl_for_ukc(depth_ref, ukc_min, draft_ref, squat, safety)
                req_clamped = (
                    max(0.0, float(req_raw))
                    if (req_raw is not None and not np.isnan(req_raw))
                    else np.nan
                )
                ukc_fwd = (
                    ukc_value(depth_ref, wl, dfwd_new, squat, safety)
                    if depth_ref is not None and wl is not None
                    else np.nan
                )
                ukc_aft = (
                    ukc_value(depth_ref, wl, daft_new, squat, safety)
                    if depth_ref is not None and wl is not None
                    else np.nan
                )
                ukc_min_actual = (
                    min(float(ukc_fwd), float(ukc_aft))
                    if (not np.isnan(ukc_fwd) and not np.isnan(ukc_aft))
                    else np.nan
                )
                tide_margin = (
                    float(wl) - float(req_clamped)
                    if (wl is not None and not np.isnan(req_clamped))
                    else np.nan
                )
                if wl is None or (isinstance(wl, float) and np.isnan(wl)) or np.isnan(req_clamped):
                    tide_status = "VERIFY"
                elif tide_margin < 0.0:
                    tide_status = "FAIL"
                elif tide_margin < 0.10:
                    tide_status = "LIMIT"
                else:
                    tide_status = "OK"
            except Exception:
                req_raw = np.nan
                req_clamped = np.nan
                ukc_fwd = np.nan
                ukc_aft = np.nan
                ukc_min_actual = np.nan
                tide_margin = np.nan
                tide_status = "VERIFY"

            all_sum.append(
                {
                    "Stage": stage_name,
                    "New_FWD_m": round(dfwd_new, 2),
                    "New_AFT_m": round(daft_new, 2),
                    "Forecast_Tide_m": (
                        round(float(wl), 2) if wl is not None else np.nan
                    ),
                    "UKC_m": (
                        round(ukc_value(depth_ref, wl, draft_ref, squat, safety), 2)
                        if depth_ref is not None and wl is not None
                        else np.nan
                    ),
                    "Required_WL_for_UKC_m": (
                        round(float(req_raw), 2)
                        if req_raw is not None and not np.isnan(req_raw)
                        else np.nan
                    ),
                    "Tide_required_m": (
                        round(float(req_clamped), 2)
                        if req_clamped is not None and not np.isnan(req_clamped)
                        else np.nan
                    ),
                    "Forecast_tide_m": (round(float(wl), 2) if wl is not None else np.nan),
                    "Tide_margin_m": (
                        round(float(tide_margin), 2)
                        if tide_margin is not None and not np.isnan(tide_margin)
                        else np.nan
                    ),
                    "UKC_min_m": (
                        round(float(ukc_min), 2)
                        if ukc_min is not None and not np.isnan(ukc_min)
                        else np.nan
                    ),
                    "UKC_fwd_m": (
                        round(float(ukc_fwd), 2)
                        if ukc_fwd is not None and not np.isnan(ukc_fwd)
                        else np.nan
                    ),
                    "UKC_aft_m": (
                        round(float(ukc_aft), 2)
                        if ukc_aft is not None and not np.isnan(ukc_aft)
                        else np.nan
                    ),
                    "UKC_min_actual_m": (
                        round(float(ukc_min_actual), 2)
                        if ukc_min_actual is not None and not np.isnan(ukc_min_actual)
                        else np.nan
                    ),
                    "Tide_verification": tide_status,
                    "Freeboard_MIN_m": (
                        round(freeboard_min(args.d_vessel, dfwd_new, daft_new), 2)
                        if args.d_vessel is not None
                        else np.nan
                    ),
                    "viol_fwd_max_m": round(float(pred.get("viol_fwd_max_m", 0.0)), 3),
                    "viol_aft_min_m": round(float(pred.get("viol_aft_min_m", 0.0)), 3),
                    "viol_fb_min_m": round(float(pred.get("viol_fb_min_m", 0.0)), 3),
                    "viol_ukc_min_m": round(float(pred.get("viol_ukc_min_m", 0.0)), 3),
                    "Plan_Rows": plan_row_count,
                    "Plan_Diagnosis": plan_diag,
                }
            )

            if not plan.empty:
                p2 = plan.copy()
                p2.insert(0, "Stage", str(r["Stage"]))
                all_plan.append(p2)

            if args.stateful_solver:
                for t in stage_tanks:
                    dw = float(delta.get(t.name, 0.0))
                    new_current = t.current_t + dw
                    new_current = min(max(new_current, float(t.min_t)), float(t.max_t))
                    cur_state[t.name] = new_current
                _log_state(stage_name, cur_state)
                if args.state_trace_csv:
                    state_trace_rows.append(
                        _trace_row(stage_name, "after", cur_state)
                    )
            else:
                cur_tanks = apply_delta(cur_tanks, delta)

        df_stage = (
            pd.concat(all_plan, ignore_index=True) if all_plan else pd.DataFrame()
        )
        df_stage.to_csv(args.out_stage_plan, index=False, encoding="utf-8-sig")
        # Compatibility: also write out_plan in stage mode
        if args.out_plan:
            df_stage.to_csv(args.out_plan, index=False, encoding="utf-8-sig")
        pd.DataFrame(all_sum).to_csv(
            args.out_summary, index=False, encoding="utf-8-sig"
        )
        if args.state_trace_csv and state_trace_rows:
            trace_path = Path(args.state_trace_csv)
            trace_path.parent.mkdir(parents=True, exist_ok=True)
            pd.DataFrame(state_trace_rows).to_csv(
                trace_path, index=False, encoding="utf-8-sig"
            )
            print(f"[OK] Stateful trace CSV: {trace_path}")
        return

    # Single-case mode
    if args.current_fwd is None or args.current_aft is None:
        raise SystemExit("Provide --stage OR (--current_fwd and --current_aft).")

    dfwd0 = float(args.current_fwd)
    daft0 = float(args.current_aft)

    plan, pred, _, _ = solve_lp(
        dfwd0=dfwd0,
        daft0=daft0,
        hdf=hdf,
        tanks=tanks,
        mode=args.mode,
        iterate_hydro=args.iterate_hydro,
        target_fwd=args.target_fwd,
        target_aft=args.target_aft,
        fwd_max=args.fwd_max,
        aft_min=args.aft_min,
        d_vessel=args.d_vessel,
        fb_min=args.fb_min,
        ukc_min=args.ukc_min,
        depth_ref=args.depth_ref,
        forecast_tide=args.forecast_tide,
        squat=args.squat,
        safety_allow=args.safety_allow,
        ukc_ref=args.ukc_ref,
        trim_abs_limit_m=args.trim_abs_limit,
        trim_limit_enforced=args.trim_limit_enforced,
        freeboard_min_enforced=args.freeboard_min_enforced,
        prefer_time=prefer_time,
        violation_penalty=args.violation_penalty,
        slack_weight_penalty=args.slack_weight_penalty,
        slack_moment_penalty=args.slack_moment_penalty,
    )

    dfwd_new = float(pred["FWD_new_m"])
    daft_new = float(pred["AFT_new_m"])
    draft_ref = pick_draft_ref_for_ukc(args.ukc_ref, dfwd_new, daft_new)

    summary = {
        "New_FWD_m": round(dfwd_new, 2),
        "New_AFT_m": round(daft_new, 2),
        "Forecast_Tide_m": (
            round(float(args.forecast_tide), 2)
            if args.forecast_tide is not None
            else np.nan
        ),
        "UKC_m": round(
            ukc_value(
                args.depth_ref,
                args.forecast_tide,
                draft_ref,
                args.squat,
                args.safety_allow,
            ),
            2,
        ),
        "Required_WL_for_UKC_m": round(
            required_wl_for_ukc(
                args.depth_ref, args.ukc_min, draft_ref, args.squat, args.safety_allow
            ),
            2,
        ),
        "Freeboard_MIN_m": (
            round(freeboard_min(args.d_vessel, dfwd_new, daft_new), 2)
            if args.d_vessel is not None
            else np.nan
        ),
        "viol_fwd_max_m": round(float(pred.get("viol_fwd_max_m", 0.0)), 3),
        "viol_aft_min_m": round(float(pred.get("viol_aft_min_m", 0.0)), 3),
        "viol_fb_min_m": round(float(pred.get("viol_fb_min_m", 0.0)), 3),
        "viol_ukc_min_m": round(float(pred.get("viol_ukc_min_m", 0.0)), 3),
    }

    plan.to_csv(args.out_plan, index=False, encoding="utf-8-sig")
    pd.DataFrame([summary]).to_csv(args.out_summary, index=False, encoding="utf-8-sig")


if __name__ == "__main__":
    main()
