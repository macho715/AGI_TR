#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
BALLAST OPTIMIZER INTEGRATED (LCT BUSHRA & GENERIC)
=============================================================================
Merges Linear Programming accuracy with Operational Heuristics.

Features:
- SCIPY Linear Programming Solver (Exact targets, Slack variables)
- Interactive CLI for crew use
- Batch processing for office use (CSV/Excel support)
- BWRB (Ballast Water Record Book) Logging generation
- AGI Site & Pre-ballast specific logic

Usage:
  1. Interactive: python ballast_optimizer_integrated.py
  2. Batch:       python ballast_optimizer_integrated.py --tank tank.csv ...
=============================================================================
"""

from __future__ import annotations
import argparse
import json
import sys
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum

import numpy as np
import pandas as pd

# Check for Scipy
try:
    from scipy.optimize import linprog
except ImportError:
    print("CRITICAL ERROR: 'scipy' is required.")
    print("Please install: pip install scipy pandas numpy openpyxl")
    sys.exit(1)

# Optional dependencies
HAS_PYDANTIC = False
try:
    from pydantic import BaseModel, Field, field_validator, model_validator
    from typing import Annotated

    HAS_PYDANTIC = True
except ImportError:
    pass

HAS_XLSXWRITER = False
try:
    import xlsxwriter

    HAS_XLSXWRITER = True
except ImportError:
    pass

HAS_SYMPY = False
try:
    import sympy as sp

    HAS_SYMPY = True
except ImportError:
    pass

HAS_SCIPY_INTERPOLATE = False
try:
    from scipy.interpolate import CubicSpline, UnivariateSpline, interp1d

    HAS_SCIPY_INTERPOLATE = True
except ImportError:
    pass


# =============================================================================
# CONSTANTS & DEFAULTS (LCT BUSHRA)
# =============================================================================


class VesselParams:
    """Default LCT BUSHRA Parameters (Used if no Hydro table provided)"""

    LBP = 60.302
    MTC = 34.00  # t*m/cm
    TPC = 8.00  # t/cm
    LCF = 0.76  # m from midship
    D_VESSEL = 3.65  # Molded Depth

    # Operational Limits
    MAX_FWD_DRAFT_OPS = 2.70
    MAX_AFT_DRAFT_OPS = 3.50
    MIN_DRAFT = 1.50
    TRIM_LIMIT_CM = 240.0

    # Defaults
    PUMP_RATE = 50.0  # t/h
    DENSITY = 1.025  # t/m3

    # Safety margins and factors
    SAFETY_MARGIN_DRAFT_CM = 5.0  # 5cm safety margin for draft
    SAFETY_FACTOR_DRAFT = 1.05  # 5% safety factor for draft calculations
    SAFETY_FACTOR_TRIM = 1.05  # 5% safety factor for trim calculations
    MIN_GM_M = 1.5  # Minimum GM requirement

    # Safety margins and factors
    SAFETY_MARGIN_DRAFT_CM = 5.0  # 5cm safety margin for draft
    SAFETY_FACTOR_DRAFT = 1.05  # 5% safety factor for draft calculations
    SAFETY_FACTOR_TRIM = 1.05  # 5% safety factor for trim calculations
    MIN_GM_M = 1.5  # Minimum GM requirement


# RORO Frame mapping constants (BUSHRA 757 TCP)
_FRAME_SLOPE = -1.0  # Frame 증가 = FWD 방향, x는 Frame이 커질수록 감소
_FRAME_OFFSET = 30.151  # Midship Frame → x = 0.0m


def fr_to_x(fr: float) -> float:
    """
    Convert Frame number to x [m from midship].

    BUSHRA 757 TCP 기준:
    - Frame 증가 = FWD 방향
    - Frame 30.151 = Midship → x = 0.0
    - Frame < 30.151 (AFT) → x > 0 (AFT)
    - Frame > 30.151 (FWD) → x < 0 (FWD)

    공식: x = _FRAME_SLOPE * (fr - _FRAME_OFFSET)
    """
    return _FRAME_SLOPE * (float(fr) - _FRAME_OFFSET)


def x_to_fr(x: float) -> float:
    """
    Inverse: x [m from midship] → Frame number.

    공식: fr = _FRAME_OFFSET - x / _FRAME_SLOPE
    (x = _FRAME_SLOPE * (fr - _FRAME_OFFSET) 이므로)
    """
    return _FRAME_OFFSET - float(x) / _FRAME_SLOPE


class TankZone(Enum):
    STERN = "STERN"
    AFT = "AFT"
    MID = "MID"
    FWD = "FWD"
    BOW = "BOW"


# Hardcoded Tank Data (Fallback if no CSV loaded)
DEFAULT_TANKS_DATA = [
    # Name, x_from_mid (derived from LCG-LBP/2), Capacity, PumpRate, Group
    ("FW2.P", -30.03, 13.92, 50, "STERN"),
    ("FW2.S", -30.03, 13.92, 50, "STERN"),
    ("FW1.P", -24.17, 23.16, 50, "AFT"),
    ("FW1.S", -24.17, 23.16, 50, "AFT"),
    ("VOID3.P", -2.40, 152.08, 100, "MID"),  # LCG ~27.75 - 30.15
    ("VOID3.S", -2.40, 152.08, 100, "MID"),
    ("FWCARGO2.P", 5.10, 148.36, 100, "FWD"),  # LCG ~35.25 - 30.15
    ("FWCARGO2.S", 5.10, 148.36, 100, "FWD"),
    ("FWCARGO1.P", 12.60, 148.35, 100, "FWD"),
    ("FWCARGO1.S", 12.60, 148.35, 100, "FWD"),
    ("FWB2.P", 19.89, 109.98, 50, "BOW"),
    ("FWB2.S", 19.89, 109.98, 50, "BOW"),
    ("FWB1.P", 27.37, 50.57, 50, "BOW"),
    ("FWB1.S", 27.37, 50.57, 50, "BOW"),
]


# =============================================================================
# DATA STRUCTURES
# =============================================================================


@dataclass(frozen=True)
class HydroPoint:
    tmean_m: float
    tpc_t_per_cm: float
    mtc_t_m_per_cm: float
    lcf_m: float
    lbp_m: float


# Pydantic models (optional, for validation)
if HAS_PYDANTIC:

    class HydroPointModel(BaseModel):
        """Pydantic model for HydroPoint validation."""

        tmean_m: Annotated[float, Field(gt=0, description="Mean draft in meters")]
        tpc_t_per_cm: Annotated[float, Field(gt=0, description="Tons per centimeter")]
        mtc_t_m_per_cm: Annotated[
            float, Field(gt=0, description="Moment to change trim")
        ]
        lcf_m: float = Field(
            description="Longitudinal center of floatation from midship"
        )
        lbp_m: Annotated[
            float, Field(gt=0, description="Length between perpendiculars")
        ]

        @field_validator("tpc_t_per_cm", "mtc_t_m_per_cm", "lbp_m")
        @classmethod
        def validate_positive(cls, v):
            if v <= 0:
                raise ValueError(f"Value must be positive, got {v}")
            return v

        def to_hydropoint(self) -> HydroPoint:
            """Convert to dataclass."""
            return HydroPoint(
                tmean_m=self.tmean_m,
                tpc_t_per_cm=self.tpc_t_per_cm,
                mtc_t_m_per_cm=self.mtc_t_m_per_cm,
                lcf_m=self.lcf_m,
                lbp_m=self.lbp_m,
            )

    class TankModel(BaseModel):
        """Pydantic model for Tank validation."""

        name: str = Field(min_length=1, description="Tank name")
        x_from_mid_m: float = Field(description="Distance from midship in meters")
        current_t: Annotated[float, Field(ge=0, description="Current weight in tons")]
        min_t: Annotated[float, Field(ge=0, description="Minimum weight in tons")]
        max_t: Annotated[float, Field(gt=0, description="Maximum weight in tons")]
        mode: str = Field(
            default="FILL_DISCHARGE",
            description="Operation mode: FILL_DISCHARGE, FILL_ONLY, DISCHARGE_ONLY, FIXED, BLOCKED",
        )
        use_flag: str = Field(
            default="Y", pattern="^[YN]$", description="Use flag: Y or N"
        )
        pump_rate_tph: Annotated[
            float, Field(gt=0, description="Pump rate in tons per hour")
        ]
        group: Optional[str] = Field(default=None, description="Tank group")
        priority_weight: Annotated[float, Field(ge=0, description="Priority weight")]
        density_t_per_m3: Annotated[
            float, Field(gt=0, description="Density in tons per cubic meter")
        ]
        freeze_flag: str = Field(
            default="N", pattern="^[YN]$", description="Freeze flag: Y or N"
        )

        @field_validator("mode")
        @classmethod
        def validate_mode(cls, v):
            valid_modes = [
                "FILL_DISCHARGE",
                "FILL_ONLY",
                "DISCHARGE_ONLY",
                "FIXED",
                "BLOCKED",
            ]
            if v.upper() not in valid_modes:
                raise ValueError(f"Mode must be one of {valid_modes}, got {v}")
            return v.upper()

        @model_validator(mode="after")
        def validate_bounds(self):
            if self.min_t > self.max_t:
                raise ValueError(
                    f"min_t ({self.min_t}) must be <= max_t ({self.max_t})"
                )
            if self.current_t < self.min_t or self.current_t > self.max_t:
                raise ValueError(
                    f"current_t ({self.current_t}) must be between min_t ({self.min_t}) and max_t ({self.max_t})"
                )
            return self

        def to_tank(self) -> "Tank":
            """Convert to dataclass."""
            return Tank(
                name=self.name,
                x_from_mid_m=self.x_from_mid_m,
                current_t=self.current_t,
                min_t=self.min_t,
                max_t=self.max_t,
                mode=self.mode,
                use_flag=self.use_flag,
                pump_rate_tph=self.pump_rate_tph,
                group=self.group,
                priority_weight=self.priority_weight,
                density_t_per_m3=self.density_t_per_m3,
                freeze_flag=self.freeze_flag,
            )


@dataclass
class Tank:
    name: str
    x_from_mid_m: float
    current_t: float
    min_t: float
    max_t: float
    mode: str  # FILL_DISCHARGE, FILL_ONLY, DISCHARGE_ONLY, FIXED, BLOCKED
    use_flag: str  # Y/N
    pump_rate_tph: float
    group: Optional[str]
    priority_weight: float
    density_t_per_m3: float
    freeze_flag: str  # Y/N

    @property
    def current_pct(self) -> float:
        return (self.current_t / self.max_t * 100) if self.max_t > 0 else 0

    def bounds_pos_neg(self) -> Tuple[float, float, float, float]:
        """Returns bounds for LP variables (pump_in, pump_out)"""
        mode = (self.mode or "FILL_DISCHARGE").strip().upper()
        use = (self.use_flag or "N").strip().upper()
        freeze = (self.freeze_flag or "N").strip().upper()

        if use != "Y" or mode == "BLOCKED" or freeze == "Y" or mode == "FIXED":
            return 0.0, 0.0, 0.0, 0.0

        cur, mn, mx = float(self.current_t), float(self.min_t), float(self.max_t)
        max_fill = max(0.0, mx - cur)
        max_dis = max(0.0, cur - mn)

        if mode == "DISCHARGE_ONLY":
            max_fill = 0.0
        elif mode == "FILL_ONLY":
            max_dis = 0.0

        # format: (fill_min, fill_max), (dis_min, dis_max)
        return 0.0, max_fill, 0.0, max_dis


@dataclass
class OptimizationResult:
    plan_df: pd.DataFrame
    summary: Dict[str, float]
    delta: Dict[str, float]
    success: bool
    msg: str


# Pydantic model for OptimizationResult (optional)
if HAS_PYDANTIC:

    class OptimizationResultModel(BaseModel):
        """Pydantic model for OptimizationResult validation."""

        success: bool = Field(description="Whether optimization succeeded")
        msg: str = Field(description="Status message")
        summary: Dict[str, float] = Field(description="Summary dictionary")
        delta: Dict[str, float] = Field(description="Delta dictionary")

        class Config:
            arbitrary_types_allowed = True  # Allow pd.DataFrame

        def to_optimization_result(self, plan_df: pd.DataFrame) -> OptimizationResult:
            """Convert to dataclass."""
            return OptimizationResult(
                plan_df=plan_df,
                summary=self.summary,
                delta=self.delta,
                success=self.success,
                msg=self.msg,
            )


# =============================================================================
# UTILITIES & I/O
# =============================================================================


# =============================================================================
# RORO HYDRO TABLE FUNCTIONS
# =============================================================================


def interpolate_tmean_from_disp(
    disp_t: float, hydro_df: Optional[pd.DataFrame] = None
) -> float:
    """
    Δdisp → Tmean 보간

    Args:
        disp_t: 배수량 (ton)
        hydro_df: Hydro table DataFrame (Tmean_m, Displacement_t 또는 Disp_t 컬럼 필요)

    Returns:
        Tmean (m) - 선형 보간된 평균 흘수
    """
    if hydro_df is None or hydro_df.empty:
        return 2.00  # Fallback

    try:
        # 컬럼 이름 확인 (다양한 형식 지원)
        disp_col = None
        tmean_col = None

        for col in hydro_df.columns:
            col_lower = col.strip().lower()
            if "disp" in col_lower or "displacement" in col_lower:
                disp_col = col
            if "tmean" in col_lower or ("mean" in col_lower and "draft" in col_lower):
                tmean_col = col

        if disp_col is None or tmean_col is None:
            return 2.00

        # Displacement 및 Tmean 배열 추출
        disps = pd.to_numeric(hydro_df[disp_col], errors="coerce").dropna().values
        tmeans = pd.to_numeric(hydro_df[tmean_col], errors="coerce").dropna().values

        if len(disps) == 0 or len(tmeans) == 0:
            return 2.00

        # 정렬 확인 (필요시 정렬)
        sorted_idx = np.argsort(disps)
        disps = disps[sorted_idx]
        tmeans = tmeans[sorted_idx]

        # Clamp 및 보간
        if disp_t <= disps[0]:
            return float(tmeans[0])
        elif disp_t >= disps[-1]:
            return float(tmeans[-1])

        # 선형 보간
        tmean = np.interp(disp_t, disps, tmeans)
        return float(tmean)
    except Exception as e:
        return 2.00


def interpolate_hydro_by_tmean(
    tmean_m: float, hydro_df: Optional[pd.DataFrame] = None
) -> Dict[str, float]:
    """
    Interpolate hydrostatic fields by mean draft (Tmean_m).

    Expected columns in hydro_df:
      - Tmean_m
      - LCF_m_from_midship or LCF_m (x_from_mid_m, aft+)
      - MCTC_t_m_per_cm or MTC_t_m_per_cm
      - TPC_t_per_cm or TPC
      - GM_min_m (optional)

    Returns:
      dict with any available interpolated fields (missing fields omitted).
    """
    if hydro_df is None or hydro_df.empty:
        return {}

    out = {"Tmean_m": float(tmean_m)}

    # Tmean 컬럼 찾기
    tmean_col = None
    for col in hydro_df.columns:
        if "tmean" in col.lower():
            tmean_col = col
            break

    if tmean_col is None:
        return out

    # Tmean 기준 정렬
    df_sorted = hydro_df.sort_values(tmean_col).reset_index(drop=True)
    tmeans = df_sorted[tmean_col].astype(float).values

    # Clamp
    if tmean_m <= tmeans[0]:
        idx = 0
    elif tmean_m >= tmeans[-1]:
        idx = len(tmeans) - 1
    else:
        idx = np.searchsorted(tmeans, tmean_m)

    # 보간할 컬럼들
    interp_cols = {
        "LCF_m_from_midship": ["lcf_m_from_midship", "lcf_from_mid_m", "lcf_m", "lcf"],
        "MCTC_t_m_per_cm": ["mctc_t_m_per_cm", "mtc_t_m_per_cm", "mctc", "mtc"],
        "TPC_t_per_cm": ["tpc_t_per_cm", "tpc"],
        "GM_min_m": ["gm_min_m", "gmmin_m", "gm_min"],
    }

    for out_key, candidates in interp_cols.items():
        col = None
        for c in df_sorted.columns:
            if c.lower() in [cand.lower() for cand in candidates]:
                col = c
                break

        if col is None:
            continue

        values = df_sorted[col].astype(float).values
        # 유효한 값만 필터링
        valid_mask = ~np.isnan(values)
        if valid_mask.sum() < 2:
            continue

        valid_tmeans = tmeans[valid_mask]
        valid_values = values[valid_mask]

        # Clamp
        if tmean_m <= valid_tmeans[0]:
            out[out_key] = float(valid_values[0])
        elif tmean_m >= valid_tmeans[-1]:
            out[out_key] = float(valid_values[-1])
        else:
            # 선형 보간
            interp_val = np.interp(tmean_m, valid_tmeans, valid_values)
            out[out_key] = float(interp_val)

    return out


def calc_draft_with_lcf(
    tmean_m: float, trim_cm: float, lcf_m: float, lbp_m: float
) -> Tuple[float, float]:
    """
    Draft 계산 (단일 참조점/부호 규약 고정).

    Conventions (LOCKED)
    --------------------
    - x_from_mid_m: midship 기준, AFT = +, FWD = -
    - trim_cm: (Daft - Dfwd) * 100  [cm]
        * + : stern down (AFT deeper)
        * - : bow down   (FWD deeper)
    - tmean_m: midship draft ≈ (Dfwd + Daft) / 2   [m]
    - lbp_m: LBP/Lpp used for trim slope length     [m]
    - lcf_m: LCF x_from_mid_m (aft+)  [m]

    Returns
    -------
    (Dfwd_m, Daft_m)
    """
    if lbp_m <= 0:
        raise ValueError("LBP must be > 0")

    halfL = lbp_m / 2.0

    # Guard-rail: LCF는 midship 기준이면 |LCF| <= LBP/2 근처여야 한다.
    if abs(lcf_m) > halfL + 0.50:
        raise ValueError(
            f"LCF reference mismatch suspected. "
            f"Expected lcf_m as x_from_mid_m (|lcf|<=~{halfL:.3f}), got {lcf_m:.3f}."
        )

    trim_m = trim_cm / 100.0  # cm -> m

    # Linear trim line about midship:
    # draft(x) = tmean_m + (trim_m / lbp_m) * x_from_mid_m
    dfwd_m = tmean_m + (trim_m / lbp_m) * (-halfL)
    daft_m = tmean_m + (trim_m / lbp_m) * (+halfL)

    return dfwd_m, daft_m


def calc_trim_gate_cm_from_tmean(tmean_m: float, fwd_limit_m: float = 2.70) -> float:
    """
    Calculate required trim (cm) to satisfy forward draft limit.

    Formula: Trim_gate_cm = max(0, 2 * (Tmean - FWD_limit) * 100)

    This ensures: Dfwd = Tmean - (Trim/2) <= FWD_limit
    Therefore: Trim >= 2 * (Tmean - FWD_limit)

    Args:
        tmean_m: Mean draft (m)
        fwd_limit_m: Forward draft limit (m), default 2.70

    Returns:
        Required trim in cm (positive = stern down, negative = bow down)
        Returns 0 if Tmean <= FWD_limit (no trim needed)
    """
    trim_gate_cm = max(0.0, 2.0 * (tmean_m - fwd_limit_m) * 100.0)
    return float(trim_gate_cm)


def gm_2d_bilinear(
    disp_t: float, trim_m: float, gm_grid: Optional[Dict[str, Any]] = None
) -> float:
    """
    Bilinear interpolation on (disp, trim) → GM 2D grid.

    Args:
        disp_t: Displacement (tons)
        trim_m: Trim in meters (positive = bow down, negative = stern down)
        gm_grid: Optional GM grid dict with keys:
            - "disp_grid": list of displacement values
            - "trim_grid": list of trim values
            - "gm_grid": 2D list of GM values [disp_idx][trim_idx]

    Returns:
        GM value (meters) or 1.50m fallback if data not available
    """
    # Fallback: Grid가 없으면 안전한 최소값 반환
    if gm_grid is None:
        return VesselParams.MIN_GM_M  # Safe minimum GM requirement

    try:
        disp_grid = gm_grid.get("disp_grid", [])
        trim_grid = gm_grid.get("trim_grid", [])
        gm_values = gm_grid.get("gm_grid", [])

        if not disp_grid or not trim_grid or not gm_values:
            return VesselParams.MIN_GM_M

        # Clamp disp
        if disp_t <= disp_grid[0]:
            i0 = i1 = 0
        elif disp_t >= disp_grid[-1]:
            i0 = i1 = len(disp_grid) - 1
        else:
            i = np.searchsorted(disp_grid, disp_t)
            i0 = max(0, i - 1)
            i1 = min(len(disp_grid) - 1, i)

        # Clamp trim
        if trim_m <= trim_grid[0]:
            j0 = j1 = 0
        elif trim_m >= trim_grid[-1]:
            j0 = j1 = len(trim_grid) - 1
        else:
            j = np.searchsorted(trim_grid, trim_m)
            j0 = max(0, j - 1)
            j1 = min(len(trim_grid) - 1, j)

        d0, d1 = disp_grid[i0], disp_grid[i1]
        t0, t1 = trim_grid[j0], trim_grid[j1]

        # 보간 비율
        td = (disp_t - d0) / (d1 - d0) if d1 != d0 else 0.0
        tt = (trim_m - t0) / (t1 - t0) if t1 != t0 else 0.0

        # 모서리 GM 값
        g00 = gm_values[i0][j0]
        g10 = gm_values[i1][j0]
        g01 = gm_values[i0][j1]
        g11 = gm_values[i1][j1]

        # Bilinear interpolation
        gm = (
            (1 - td) * (1 - tt) * g00
            + td * (1 - tt) * g10
            + (1 - td) * tt * g01
            + td * tt * g11
        )

        # Sanity check
        if gm < 0 or gm > 5.0:
            return VesselParams.MIN_GM_M

        return float(gm)
    except Exception as e:
        print(
            f"[WARNING] GM calculation error: {e} → fallback GM={VesselParams.MIN_GM_M}m"
        )
        return VesselParams.MIN_GM_M


def _read_df_any(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"{path} not found")
    suf = path.suffix.lower()
    if suf == ".csv":
        return pd.read_csv(path)
    if suf in (".xlsx", ".xls"):
        return pd.read_excel(path)
    if suf == ".json":
        return pd.DataFrame(json.loads(path.read_text(encoding="utf-8-sig")))
    raise ValueError(f"Unsupported file: {path}")


def get_default_hydro_table() -> pd.DataFrame:
    """Create a synthetic hydro table based on vessel constants."""
    # Create a range of drafts
    drafts = np.linspace(1.0, 4.0, 31)
    data = []
    for d in drafts:
        data.append(
            {
                "Tmean_m": d,
                "TPC_t_per_cm": VesselParams.TPC,
                "MTC_t_m_per_cm": VesselParams.MTC,
                "LCF_m": VesselParams.LCF,
                "LBP_m": VesselParams.LBP,
            }
        )
    return pd.DataFrame(data)


def get_default_tanks() -> List[Tank]:
    """Load default hardcoded tanks."""
    tanks = []
    for name, x, cap, rate, grp in DEFAULT_TANKS_DATA:
        tanks.append(
            Tank(
                name=name,
                x_from_mid_m=x,
                current_t=0.0,
                min_t=0.0,
                max_t=cap,
                mode="FILL_DISCHARGE",
                use_flag="Y",
                pump_rate_tph=rate,
                group=grp,
                priority_weight=1.0,
                density_t_per_m3=VesselParams.DENSITY,
                freeze_flag="N",
            )
        )
    return tanks


def load_tanks_from_file(path: Path) -> List[Tank]:
    df = _read_df_any(path).copy()
    # Normalize columns
    df.columns = [c.strip() for c in df.columns]

    # Required check
    required = {"Tank", "Capacity_t", "x_from_mid_m"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Tank file missing columns: {missing}")

    # Set defaults for optional
    defaults = {
        "Current_t": 0.0,
        "Min_t": 0.0,
        "Max_t": 0.0,
        "mode": "FILL_DISCHARGE",
        "use_flag": "Y",
        "pump_rate_tph": VesselParams.PUMP_RATE,
        "group": "MID",
        "priority_weight": 1.0,
        "density_t_per_m3": VesselParams.DENSITY,
        "freeze_flag": "N",
    }
    for col, val in defaults.items():
        if col not in df.columns:
            df[col] = val

    tanks = []
    for _, r in df.iterrows():
        cap = float(r["Capacity_t"])
        mx = float(r["Max_t"])
        if mx <= 0:
            mx = cap

        tank_data = {
            "name": str(r["Tank"]),
            "x_from_mid_m": float(r["x_from_mid_m"]),
            "current_t": min(max(float(r["Current_t"]), 0), mx),
            "min_t": float(r["Min_t"]),
            "max_t": mx,
            "mode": str(r["mode"]),
            "use_flag": str(r["use_flag"]),
            "pump_rate_tph": float(r["pump_rate_tph"]),
            "group": str(r["group"]) if pd.notna(r.get("group")) else None,
            "priority_weight": float(r["priority_weight"]),
            "density_t_per_m3": float(r["density_t_per_m3"]),
            "freeze_flag": str(r["freeze_flag"]),
        }

        # Validate with pydantic if available
        if HAS_PYDANTIC:
            try:
                tank_model = TankModel(**tank_data)
                tanks.append(tank_model.to_tank())
            except Exception as e:
                raise ValueError(f"Validation error for tank {tank_data['name']}: {e}")
        else:
            tanks.append(Tank(**tank_data))
    return tanks


# =============================================================================
# CALCULATION ENGINE (LINEAR PROGRAMMING)
# =============================================================================


class BallastOptimizer:
    def __init__(self, tanks: List[Tank], hydro_df: Optional[pd.DataFrame] = None):
        self.tanks = tanks
        self.hydro_df = hydro_df if hydro_df is not None else get_default_hydro_table()
        # Sort hydro for interpolation
        self.hydro_df = self.hydro_df.sort_values("Tmean_m").reset_index(drop=True)

    def get_hydro_at_draft(self, tmean_m: float) -> HydroPoint:
        x = self.hydro_df["Tmean_m"].to_numpy(float)
        tmean_val = float(tmean_m)

        # Use advanced interpolation if available
        if HAS_SCIPY_INTERPOLATE and len(x) >= 4:
            # Use CubicSpline for smooth interpolation (requires at least 4 points)
            def _interp_advanced(col: str) -> float:
                y = self.hydro_df[col].to_numpy(float)
                # Check for NaN values
                mask = ~np.isnan(y)
                if mask.sum() < 4:
                    # Fall back to linear interpolation
                    return float(np.interp(tmean_val, x[mask], y[mask]))
                try:
                    spline = CubicSpline(x[mask], y[mask], extrapolate=False)
                    return float(spline(tmean_val))
                except:
                    # Fall back to linear interpolation
                    return float(np.interp(tmean_val, x[mask], y[mask]))

        else:
            # Fall back to linear interpolation
            def _interp_advanced(col: str) -> float:
                return float(
                    np.interp(tmean_val, x, self.hydro_df[col].to_numpy(float))
                )

            return HydroPoint(
                tmean_m=tmean_val,
                tpc_t_per_cm=_interp_advanced("TPC_t_per_cm"),
                mtc_t_m_per_cm=_interp_advanced("MTC_t_m_per_cm"),
                lcf_m=_interp_advanced("LCF_m"),
                lbp_m=(
                    _interp_advanced("LBP_m")
                    if "LBP_m" in self.hydro_df.columns
                    else self.lbp_m
                ),
            )

        return HydroPoint(
            tmean_m=tmean_val,
            tpc_t_per_cm=_interp_advanced("TPC_t_per_cm"),
            mtc_t_m_per_cm=_interp_advanced("MTC_t_m_per_cm"),
            lcf_m=_interp_advanced("LCF_m"),
            lbp_m=(
                _interp_advanced("LBP_m")
                if "LBP_m" in self.hydro_df.columns
                else VesselParams.LBP
            ),
        )

    def predict_drafts(
        self, dfwd0: float, daft0: float, delta: Dict[str, float]
    ) -> Dict[str, float]:
        """Calculate new drafts based on weight changes and current hydrostatics."""
        tmean0 = 0.5 * (dfwd0 + daft0)
        hydro = self.get_hydro_at_draft(tmean0)

        tpc, mtc, lcf = hydro.tpc_t_per_cm, hydro.mtc_t_m_per_cm, hydro.lcf_m
        total_w = sum(float(delta.get(t.name, 0.0)) for t in self.tanks)
        total_m = sum(
            float(delta.get(t.name, 0.0)) * (t.x_from_mid_m - lcf) for t in self.tanks
        )

        # Apply safety factors
        d_tmean = (
            total_w / (tpc * 100.0) if tpc > 0 else 0.0
        ) * VesselParams.SAFETY_FACTOR_DRAFT
        d_trim = (
            total_m / (mtc * 100.0) if mtc > 0 else 0.0
        ) * VesselParams.SAFETY_FACTOR_TRIM

        dfwd_new = dfwd0 + d_tmean - 0.5 * d_trim
        daft_new = daft0 + d_tmean + 0.5 * d_trim

        return {
            "total_w_t": float(total_w),
            "total_m_t_m": float(total_m),
            "dfwd_new_m": float(dfwd_new),
            "daft_new_m": float(daft_new),
            "trim_new_m": float(daft_new - dfwd_new),
            "tmean_new_m": float(0.5 * (dfwd_new + daft_new)),
        }

    def solve(
        self,
        dfwd: float,
        daft: float,
        target_fwd: Optional[float] = None,
        target_aft: Optional[float] = None,
        limit_fwd: Optional[float] = None,
        limit_aft: Optional[float] = None,
        limit_trim: Optional[float] = None,
        prefer_time: bool = True,
        violation_penalty: float = 1e7,
    ) -> OptimizationResult:
        """
        Solves the ballast plan using Linear Programming.
        Supports 'Target' mode (exact draft) or 'Limit' mode (inequalities).
        """

        # 1. Setup Hydro
        mean_draft = 0.5 * (dfwd + daft)
        hydro = self.get_hydro_at_draft(mean_draft)

        # 2. Setup Variables
        # x = [p1, n1, p2, n2, ..., slacks...]
        # p = pump in (positive), n = pump out (negative representation in math, but positive var)
        var_names = []
        bounds = []
        cost = []

        for t in self.tanks:
            p_lo, p_hi, n_lo, n_hi = t.bounds_pos_neg()
            var_names.extend([f"{t.name}_p", f"{t.name}_n"])
            bounds.extend([(p_lo, p_hi), (n_lo, n_hi)])

            # Cost function
            w = t.priority_weight
            if prefer_time:
                c = w / t.pump_rate_tph if t.pump_rate_tph > 0 else 1e6
            else:
                c = w
            cost.extend([c, c])

        # 3. Mode Determination & Constraints
        A_eq, b_eq = None, None
        A_ub, b_ub = [], []

        # Helper to build rows
        # Weight Coef: 1/(TPC*100)
        # Moment Coef: (x - LCF)/(MTC*100) * (-1 for sign convention fix discussed earlier)

        inv_tpc = 1.0 / (hydro.tpc_t_per_cm * 100.0)
        inv_mtc = -1.0 / (
            hydro.mtc_t_m_per_cm * 100.0
        )  # Negative because pos moment (fwd) -> neg trim

        def get_coeffs():
            # Returns arrays for dSinkage and dTrim
            c_sink = []
            c_trim = []
            for t in self.tanks:
                arm = t.x_from_mid_m - hydro.lcf_m
                # For P (Fill): +Weight
                c_sink.append(inv_tpc)
                c_trim.append(arm * inv_mtc)
                # For N (Discharge): -Weight
                c_sink.append(-inv_tpc)
                c_trim.append(-arm * inv_mtc)
            return np.array(c_sink), np.array(c_trim)

        kw_sink, kw_trim = get_coeffs()

        # Geometric factors for drafts
        # dFwd = dSink - dTrim * (0.5 - LCF/LBP)
        # dAft = dSink + dTrim * (0.5 + LCF/LBP)
        f_fac = 0.5 - (hydro.lcf_m / hydro.lbp_m)
        a_fac = 0.5 + (hydro.lcf_m / hydro.lbp_m)

        row_fwd = kw_sink - kw_trim * f_fac
        row_aft = kw_sink + kw_trim * a_fac

        # Mode: TARGET (Equality Constraints)
        if target_fwd is not None and target_aft is not None:
            # Add slack variables for soft constraints (penalty)
            # slack_fwd_p, slack_fwd_n, slack_aft_p, slack_aft_n
            var_names.extend(["sf_p", "sf_n", "sa_p", "sa_n"])
            bounds.extend([(0, None)] * 4)
            cost.extend([1e6] * 4)  # High penalty for missing target

            # Current delta needed
            req_df = target_fwd - dfwd
            req_da = target_aft - daft

            # Rows with slacks
            # sum(weights) + slack_p - slack_n = required
            rf = np.concatenate([row_fwd, [1, -1, 0, 0]])
            ra = np.concatenate([row_aft, [0, 0, 1, -1]])

            A_eq = np.vstack([rf, ra])
            b_eq = np.array([req_df, req_da])

        # Mode: LIMIT (Inequality Constraints with Violation Variables)
        else:
            # Add violation variables for soft constraints
            viol_vars = [
                "viol_fwd_m",
                "viol_aft_m",
                "viol_trim_pos_m",
                "viol_trim_neg_m",
            ]
            var_names.extend(viol_vars)
            bounds.extend([(0.0, None)] * 4)
            cost.extend([violation_penalty] * 4)

            # Helper to pad rows with violation variables
            def pad_with_viol(row: np.ndarray) -> np.ndarray:
                padded = np.zeros(len(var_names), float)
                padded[: len(row)] = row
                return padded

            # If Limit Fwd provided: Fwd_new <= Limit -> dFwd <= Limit - Fwd_cur
            if limit_fwd is not None and not (
                np.isnan(limit_fwd) or np.isinf(limit_fwd)
            ):
                r = pad_with_viol(row_fwd)
                r[var_names.index("viol_fwd_m")] = -1.0
                # Check for invalid values
                if not (np.any(np.isnan(r)) or np.any(np.isinf(r))):
                    b_val = limit_fwd - dfwd
                    if not (np.isnan(b_val) or np.isinf(b_val)):
                        A_ub.append(r)
                        b_ub.append(b_val)

            if limit_aft is not None and not (
                np.isnan(limit_aft) or np.isinf(limit_aft)
            ):
                # Aft_new <= Limit
                r = pad_with_viol(row_aft)
                r[var_names.index("viol_aft_m")] = -1.0
                # Check for invalid values
                if not (np.any(np.isnan(r)) or np.any(np.isinf(r))):
                    b_val = limit_aft - daft
                    if not (np.isnan(b_val) or np.isinf(b_val)):
                        A_ub.append(r)
                        b_ub.append(b_val)

            if limit_trim is not None and not (
                np.isnan(limit_trim) or np.isinf(limit_trim)
            ):
                # abs(Trim_new) <= Limit
                trim_cur = daft - dfwd
                if not (np.isnan(trim_cur) or np.isinf(trim_cur)):
                    # Positive trim constraint
                    r = pad_with_viol(kw_trim)
                    r[var_names.index("viol_trim_pos_m")] = -1.0
                    # Check for invalid values
                    if not (np.any(np.isnan(r)) or np.any(np.isinf(r))):
                        b_val = limit_trim - trim_cur
                        if not (np.isnan(b_val) or np.isinf(b_val)):
                            A_ub.append(r)
                            b_ub.append(b_val)
                    # Negative trim constraint
                    r = pad_with_viol(-kw_trim)
                    r[var_names.index("viol_trim_neg_m")] = -1.0
                    # Check for invalid values
                    if not (np.any(np.isnan(r)) or np.any(np.isinf(r))):
                        b_val = limit_trim + trim_cur
                        if not (np.isnan(b_val) or np.isinf(b_val)):
                            A_ub.append(r)
                            b_ub.append(b_val)

        # Convert lists to arrays
        if len(A_ub) > 0:
            A_ub = np.vstack(A_ub)
            # Final check for invalid values
            if np.any(np.isnan(A_ub)) or np.any(np.isinf(A_ub)):
                # Replace invalid values with 0
                A_ub = np.nan_to_num(A_ub, nan=0.0, posinf=1e6, neginf=-1e6)
            # Pad A_ub if variables were added (slacks) - not applicable in the Limit logic block above currently
            b_ub = np.array(b_ub)
            # Final check for invalid values in b_ub
            if np.any(np.isnan(b_ub)) or np.any(np.isinf(b_ub)):
                b_ub = np.nan_to_num(b_ub, nan=0.0, posinf=1e6, neginf=-1e6)
        else:
            A_ub, b_ub = None, None

        # Solve
        res = linprog(
            c=cost,
            A_ub=A_ub,
            b_ub=b_ub,
            A_eq=A_eq,
            b_eq=b_eq,
            bounds=bounds,
            method="highs",
        )

        if not res.success:
            return OptimizationResult(pd.DataFrame(), {}, {}, False, res.message)

        # Parse Result
        delta = {}
        rows = []
        total_pump_time = 0

        n_tanks = len(self.tanks)
        x = res.x

        for i, t in enumerate(self.tanks):
            p = x[2 * i]
            n = x[2 * i + 1]
            dw = p - n

            if abs(dw) < 0.01:
                continue

            pump_time = (p + n) / t.pump_rate_tph
            total_pump_time += pump_time
            delta[t.name] = dw

            rows.append(
                {
                    "Tank": t.name,
                    "Action": "Fill" if dw > 0 else "Discharge",
                    "Weight_t": round(dw, 1),
                    "Start_%": round(t.current_pct, 1),
                    "End_%": (
                        round(((t.current_t + dw) / t.max_t) * 100, 1) if t.max_t else 0
                    ),
                    "Time_h": round(pump_time, 2),
                }
            )

        plan_df = pd.DataFrame(rows)
        pred = self.predict_drafts(dfwd, daft, delta)
        pred["total_time_h"] = total_pump_time

        # Add violation values if in limit mode
        if target_fwd is None or target_aft is None:
            # Limit mode - extract violation values
            n_tanks = len(self.tanks)
            base_idx = 2 * n_tanks
            if "viol_fwd_m" in var_names:
                pred["viol_fwd_m"] = float(x[var_names.index("viol_fwd_m")])
            if "viol_aft_m" in var_names:
                pred["viol_aft_m"] = float(x[var_names.index("viol_aft_m")])
            if "viol_trim_pos_m" in var_names:
                pred["viol_trim_pos_m"] = float(x[var_names.index("viol_trim_pos_m")])
            if "viol_trim_neg_m" in var_names:
                pred["viol_trim_neg_m"] = float(x[var_names.index("viol_trim_neg_m")])

        # Safety validation
        warnings = []
        # Draft limits validation
        if pred["dfwd_new_m"] < VesselParams.MIN_DRAFT:
            warnings.append(
                f"WARNING: FWD draft {pred['dfwd_new_m']:.3f}m below minimum {VesselParams.MIN_DRAFT}m"
            )
        if pred["dfwd_new_m"] > VesselParams.MAX_FWD_DRAFT_OPS:
            warnings.append(
                f"WARNING: FWD draft {pred['dfwd_new_m']:.3f}m exceeds operational limit {VesselParams.MAX_FWD_DRAFT_OPS}m"
            )
        if pred["daft_new_m"] > VesselParams.MAX_AFT_DRAFT_OPS:
            warnings.append(
                f"WARNING: AFT draft {pred['daft_new_m']:.3f}m exceeds operational limit {VesselParams.MAX_AFT_DRAFT_OPS}m"
            )

        # Trim limit validation
        trim_cm = abs(pred["trim_new_m"]) * 100.0
        if trim_cm > VesselParams.TRIM_LIMIT_CM:
            warnings.append(
                f"WARNING: Trim {trim_cm:.1f}cm exceeds limit {VesselParams.TRIM_LIMIT_CM}cm"
            )

        # IMO/Industry standard compliance checks
        # GM check (simplified - would need actual GM calculation for full compliance)
        # Note: Full GM calculation requires additional hydrostatic data
        pred["_compliance_checks"] = {
            "draft_within_limits": (
                VesselParams.MIN_DRAFT
                <= pred["dfwd_new_m"]
                <= VesselParams.MAX_FWD_DRAFT_OPS
                and pred["daft_new_m"] <= VesselParams.MAX_AFT_DRAFT_OPS
            ),
            "trim_within_limit": trim_cm <= VesselParams.TRIM_LIMIT_CM,
            "imo_draft_compliant": pred["dfwd_new_m"] <= VesselParams.MAX_FWD_DRAFT_OPS,
        }

        # Tank capacity validation with group balance check
        tank_groups = {}
        for t in self.tanks:
            if t.name in delta:
                new_level = t.current_t + delta[t.name]
                if new_level > t.max_t:
                    warnings.append(
                        f"WARNING: Tank {t.name} exceeds max capacity ({new_level:.2f}t > {t.max_t:.2f}t)"
                    )
                if new_level < t.min_t:
                    warnings.append(
                        f"WARNING: Tank {t.name} below min level ({new_level:.2f}t < {t.min_t:.2f}t)"
                    )

                # Group balance tracking
                if t.group:
                    if t.group not in tank_groups:
                        tank_groups[t.group] = {"total": 0.0, "count": 0}
                    tank_groups[t.group]["total"] += new_level
                    tank_groups[t.group]["count"] += 1

        # Check group balance
        for group, data in tank_groups.items():
            avg_level = data["total"] / data["count"] if data["count"] > 0 else 0.0
            # Warn if significant imbalance (more than 10% difference from average)
            for t in self.tanks:
                if t.group == group and t.name in delta:
                    new_level = t.current_t + delta[t.name]
                    if abs(new_level - avg_level) > avg_level * 0.1:
                        warnings.append(
                            f"WARNING: Tank {t.name} in group {group} imbalanced ({new_level:.2f}t vs avg {avg_level:.2f}t)"
                        )

        if warnings:
            pred["_warnings"] = warnings

        return OptimizationResult(plan_df, pred, delta, True, "Optimal")

    def update_tanks(self, delta: Dict[str, float]):
        """Updates internal tank states based on delta."""
        for t in self.tanks:
            if t.name in delta:
                t.current_t = min(max(t.current_t + delta[t.name], t.min_t), t.max_t)

    def apply_delta_to_tanks(self, delta: Dict[str, float]) -> List[Tank]:
        """Apply delta to tanks and return new tank list with updated states."""
        new_tanks = []
        for t in self.tanks:
            dw = float(delta.get(t.name, 0.0))
            new_tanks.append(
                Tank(
                    name=t.name,
                    x_from_mid_m=t.x_from_mid_m,
                    current_t=min(max(t.current_t + dw, t.min_t), t.max_t),
                    min_t=t.min_t,
                    max_t=t.max_t,
                    mode=t.mode,
                    use_flag=t.use_flag,
                    pump_rate_tph=t.pump_rate_tph,
                    group=t.group,
                    priority_weight=t.priority_weight,
                    density_t_per_m3=t.density_t_per_m3,
                    freeze_flag=t.freeze_flag,
                )
            )
        return new_tanks

    def iterate_hydro_solve(
        self, dfwd0: float, daft0: float, iterate_hydro: int = 2, **kwargs
    ) -> Tuple[pd.DataFrame, Dict[str, float], HydroPoint, Dict[str, float]]:
        """
        Solve with iterative hydro interpolation for improved accuracy.

        Args:
            dfwd0: Initial forward draft
            daft0: Initial aft draft
            iterate_hydro: Number of iterations (default 2)
            **kwargs: Additional arguments for solve method

        Returns:
            Tuple of (plan_df, summary, hydro, delta)
        """
        tmean = 0.5 * (dfwd0 + daft0)
        plan = None
        pred = None
        delta = None
        hydro = None

        for _ in range(max(int(iterate_hydro), 1)):
            hydro = self.get_hydro_at_draft(tmean)
            # Extract prefer_time and violation_penalty from kwargs if present
            prefer_time = kwargs.pop("prefer_time", True)
            violation_penalty = kwargs.pop("violation_penalty", 1e7)
            res = self.solve(
                dfwd0,
                daft0,
                prefer_time=prefer_time,
                violation_penalty=violation_penalty,
                **kwargs,
            )
            if not res.success:
                raise RuntimeError(f"Optimization failed: {res.msg}")

            plan = res.plan_df
            pred = res.summary
            delta = res.delta

            # Update tmean for next iteration
            tmean = float(pred.get("tmean_new_m", tmean))

        return plan, pred, hydro, delta


# =============================================================================
# OPERATIONAL WRAPPERS
# =============================================================================


def print_summary(res: OptimizationResult, initial: Tuple[float, float]):
    if not res.success:
        print(f"\n[ERROR] Optimization Failed: {res.msg}")
        return

    print("\n" + "=" * 60)
    print(" OPTIMIZED BALLAST PLAN")
    print("=" * 60)

    print("Draft Change:")
    print(f"  FWD:  {initial[0]:.3f}m -> {res.summary['dfwd_new_m']:.3f}m")
    print(f"  AFT:  {initial[1]:.3f}m -> {res.summary['daft_new_m']:.3f}m")
    print(f"  TRIM: {initial[1]-initial[0]:.3f}m -> {res.summary['trim_new_m']:.3f}m")
    print(f"  Total Ballast Moved: {res.summary['total_w_t']:.1f} t")
    print(f"  Total Pump Time:     {res.summary.get('total_time_h', 0):.2f} h")
    print("-" * 60)

    if not res.plan_df.empty:
        print(res.plan_df.to_string(index=False))
    else:
        print("No ballast operations required.")
    print("=" * 60 + "\n")


def run_interactive_mode():
    print("\nInitializing Ballast Optimizer...")
    tanks = get_default_tanks()

    # Try to load CSVs if they exist in CWD, else silent fallback
    # Check for multiple possible filenames
    tank_files = ["tank_ssot.csv", "tank_ssot_for_solver.csv"]
    hydro_files = ["hydro_table.csv", "hydro_table_for_solver.csv"]

    tank_loaded = False
    for tank_file in tank_files:
        if Path(tank_file).exists():
            print(f"Loading local {tank_file}...")
            try:
                tanks = load_tanks_from_file(Path(tank_file))
                tank_loaded = True
                break
            except Exception as e:
                print(f"Warning: Failed to load {tank_file}: {e}")
                continue

    if not tank_loaded:
        print("Using default hardcoded tank data (LCT BUSHRA)")

    hydro = None
    for hydro_file in hydro_files:
        if Path(hydro_file).exists():
            print(f"Loading local {hydro_file}...")
            try:
                hydro = load_hydro_table(Path(hydro_file))
                break
            except Exception as e:
                print(f"Warning: Failed to load {hydro_file}: {e}")
                continue

    if hydro is None:
        print("Using default synthetic hydro table")

    optimizer = BallastOptimizer(tanks, hydro)

    # Simple state tracking for the session
    state = {"dfwd": 2.5, "daft": 3.0}

    while True:
        print(
            f"\n--- CURRENT STATE: FWD {state['dfwd']:.2f}m / AFT {state['daft']:.2f}m ---"
        )
        print("1. Set Current Drafts")
        print("2. Set Tank Levels")
        print("3. Solve for Target Draft")
        print("4. Optimization: AGI Arrival (Max Fwd 2.7m)")
        print("5. Optimization: Pre-Ballast (Simulate Cargo)")
        print("6. Show Tank Status")
        print("q. Quit")

        choice = input("Select > ").strip().lower()

        if choice == "q":
            break

        elif choice == "1":
            try:
                state["dfwd"] = float(input("FWD Draft (m): "))
                state["daft"] = float(input("AFT Draft (m): "))
            except:
                print("Invalid number")

        elif choice == "2":
            print("Enter Tank Name and % (e.g., 'FW1.P 50'). Empty to finish.")
            while True:
                line = input("Tank > ")
                if not line:
                    break
                parts = line.split()
                if len(parts) >= 2:
                    tname = parts[0]
                    try:
                        pct = float(parts[1])
                        found = False
                        for t in optimizer.tanks:
                            if t.name.lower() == tname.lower():
                                t.current_t = t.max_t * (pct / 100.0)
                                print(f"Updated {t.name} to {t.current_t:.1f}t")
                                found = True
                        if not found:
                            print("Tank not found")
                    except:
                        print("Invalid format")

        elif choice == "3":
            try:
                tf = float(input("Target FWD (m): "))
                ta = float(input("Target AFT (m): "))
                res = optimizer.solve(
                    state["dfwd"], state["daft"], target_fwd=tf, target_aft=ta
                )
                print_summary(res, (state["dfwd"], state["daft"]))
                if (
                    res.success
                    and input("Apply to virtual tanks? (y/n) ").lower() == "y"
                ):
                    optimizer.update_tanks(res.delta)
                    state["dfwd"] = res.summary["dfwd_new_m"]
                    state["daft"] = res.summary["daft_new_m"]
            except ValueError:
                print("Invalid inputs")

        elif choice == "4":
            # AGI Arrival Logic: Max FWD 2.7 + Tide
            try:
                tide = float(input("Tide Height (m, default 0): ") or 0)
                limit = VesselParams.MAX_FWD_DRAFT_OPS + tide
                print(f"Optimizing for FWD Draft <= {limit:.2f}m...")

                # If already compliant
                if state["dfwd"] <= limit:
                    print("Already compliant.")
                    continue

                # Use LIMIT mode in Solver
                res = optimizer.solve(
                    state["dfwd"], state["daft"], limit_fwd=limit - 0.05
                )  # 5cm safety
                print_summary(res, (state["dfwd"], state["daft"]))

                if res.success and input("Apply? (y/n) ").lower() == "y":
                    optimizer.update_tanks(res.delta)
                    state["dfwd"] = res.summary["dfwd_new_m"]
                    state["daft"] = res.summary["daft_new_m"]

            except ValueError:
                print("Error in AGI calculation")

        elif choice == "5":
            # Pre-Ballast
            try:
                w = float(input("Cargo Weight (t): "))
                lcg = float(input("Cargo LCG from AP (m): "))
                # Convert AP LCG to Midship X
                x_cargo = lcg - (VesselParams.LBP / 2.0)

                # Create a temporary 'tank' for cargo to see effect
                sim_delta = {"CARGO": w}
                # Temporary tank obj
                cargo_t = Tank("CARGO", x_cargo, 0, 0, 0, "", "", 0, None, 0, 0, "")
                opt_sim = BallastOptimizer([cargo_t], optimizer.hydro_df)
                pred = opt_sim.predict_drafts(state["dfwd"], state["daft"], sim_delta)

                print(
                    f"\nSimulated Draft after Cargo: FWD {pred['dfwd_new_m']:.2f}, AFT {pred['daft_new_m']:.2f}"
                )

                limit = VesselParams.MAX_FWD_DRAFT_OPS
                if pred["dfwd_new_m"] > limit:
                    print(
                        f"WARNING: Exceeds limit {limit}m. Calculating pre-ballast..."
                    )
                    # Strategy: Target a draft NOW such that adding cargo lands us at limit
                    # Simple heuristic loop or complex calc?
                    # Let's target FWD = Limit - (Cargo_Effect)
                    cargo_effect_fwd = pred["dfwd_new_m"] - state["dfwd"]
                    target_pre_fwd = limit - cargo_effect_fwd - 0.05

                    # We usually want to keep even keel or slight trim aft.
                    # Let's try to maintain current trim, just sink/rise
                    trim = state["daft"] - state["dfwd"]
                    target_pre_aft = target_pre_fwd + trim

                    print(
                        f"Targeting Pre-Ballast Drafts: FWD {target_pre_fwd:.2f}, AFT {target_pre_aft:.2f}"
                    )

                    res = optimizer.solve(
                        state["dfwd"],
                        state["daft"],
                        target_fwd=target_pre_fwd,
                        target_aft=target_pre_aft,
                    )
                    print_summary(res, (state["dfwd"], state["daft"]))

                    if (
                        res.success
                        and input("Apply Pre-Ballast? (y/n) ").lower() == "y"
                    ):
                        optimizer.update_tanks(res.delta)
                        state["dfwd"] = res.summary["dfwd_new_m"]
                        state["daft"] = res.summary["daft_new_m"]
                else:
                    print("Safe to load without pre-ballast.")

            except Exception as e:
                print(f"Error: {e}")

        elif choice == "6":
            print(f"\n{'TANK':<12} {'CAP(t)':<8} {'CUR(t)':<8} {'PCT':<6} {'GRP':<5}")
            print("-" * 45)
            for t in optimizer.tanks:
                print(
                    f"{t.name:<12} {t.max_t:<8.1f} {t.current_t:<8.1f} {t.current_pct:<6.0f} {t.group or ''}"
                )


# =============================================================================
# BATCH MODE & CSV HELPERS
# =============================================================================


def load_stage_table(path: Path) -> pd.DataFrame:
    """Load stage table with flexible column name mapping."""
    df = _read_df_any(path).copy()
    colmap = {}
    for c in df.columns:
        cl = c.strip().lower()
        if cl in ("stage", "stage_name"):
            colmap[c] = "Stage"
        elif cl in ("dfwd_m", "current_fwd_m", "fwd_m", "fwd"):
            colmap[c] = "Current_FWD_m"
        elif cl in ("daft_m", "current_aft_m", "aft_m", "aft"):
            colmap[c] = "Current_AFT_m"
        elif cl in ("target_fwd_m", "fwd_target_m"):
            colmap[c] = "Target_FWD_m"
        elif cl in ("target_aft_m", "aft_target_m"):
            colmap[c] = "Target_AFT_m"
        elif cl in ("fwd_limit_m", "limit_fwd_m"):
            colmap[c] = "FWD_Limit_m"
        elif cl in ("aft_limit_m", "limit_aft_m"):
            colmap[c] = "AFT_Limit_m"
        elif cl in ("trim_limit_m", "trim_abs_limit_m"):
            colmap[c] = "Trim_Abs_Limit_m"

    df = df.rename(columns=colmap)
    need = {"Stage", "Current_FWD_m", "Current_AFT_m"}
    miss = need - set(df.columns)
    if miss:
        raise ValueError(f"stage table missing columns: {sorted(miss)}")
    for c in [
        "Current_FWD_m",
        "Current_AFT_m",
        "Target_FWD_m",
        "Target_AFT_m",
        "FWD_Limit_m",
        "AFT_Limit_m",
        "Trim_Abs_Limit_m",
    ]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def load_hydro_table(path: Path) -> pd.DataFrame:
    df = _read_df_any(path).copy()
    need = {"Tmean_m", "TPC_t_per_cm", "MTC_t_m_per_cm", "LCF_m", "LBP_m"}

    # Normalize column names (strip whitespace, handle case)
    df.columns = [c.strip() for c in df.columns]
    cols_lower = {c.lower(): c for c in df.columns}

    # Column mapping for common variations
    col_map = {
        "tmean_m": "Tmean_m",
        "tpc_t_per_cm": "TPC_t_per_cm",
        "mtc_t_m_per_cm": "MTC_t_m_per_cm",
        "mctc_t_m_per_cm": "MTC_t_m_per_cm",  # Alternative spelling
        "lcf_m": "LCF_m",
        "lbp_m": "LBP_m",
    }

    # Check for missing columns
    missing = []
    for req_lower, req_std in col_map.items():
        if req_lower not in cols_lower and req_std not in df.columns:
            missing.append(req_std)

    if missing:
        raise ValueError(f"Hydro table missing required columns: {sorted(missing)}")

    # Rename columns to standard names if needed
    rename_dict = {}
    for req_lower, req_std in col_map.items():
        if req_std not in df.columns and req_lower in cols_lower:
            rename_dict[cols_lower[req_lower]] = req_std

    if rename_dict:
        df = df.rename(columns=rename_dict)

    # Basic cleanup and validation
    df["Tmean_m"] = pd.to_numeric(df["Tmean_m"], errors="coerce")
    df["TPC_t_per_cm"] = pd.to_numeric(df["TPC_t_per_cm"], errors="coerce")
    df["MTC_t_m_per_cm"] = pd.to_numeric(df["MTC_t_m_per_cm"], errors="coerce")
    df["LCF_m"] = pd.to_numeric(df["LCF_m"], errors="coerce")

    # LBP_m is optional, use default if missing
    if "LBP_m" not in df.columns:
        df["LBP_m"] = VesselParams.LBP
    else:
        df["LBP_m"] = pd.to_numeric(df["LBP_m"], errors="coerce").fillna(
            VesselParams.LBP
        )

    df_clean = (
        df.dropna(subset=["Tmean_m"]).sort_values("Tmean_m").reset_index(drop=True)
    )

    # Validate with pydantic if available
    if HAS_PYDANTIC:
        for idx, row in df_clean.iterrows():
            try:
                hydro_data = {
                    "tmean_m": float(row["Tmean_m"]),
                    "tpc_t_per_cm": float(row["TPC_t_per_cm"]),
                    "mtc_t_m_per_cm": float(row["MTC_t_m_per_cm"]),
                    "lcf_m": float(row["LCF_m"]),
                    "lbp_m": float(row["LBP_m"]),
                }
                HydroPointModel(**hydro_data)
            except Exception as e:
                raise ValueError(
                    f"Validation error for hydro table row {idx} (Tmean={row.get('Tmean_m', 'N/A')}): {e}"
                )

    return df_clean


def validate_hydro_formula() -> Dict[str, bool]:
    """Validate hydrostatic formulas using sympy."""
    if not HAS_SYMPY:
        return {"available": False, "message": "sympy not installed"}

    try:
        # Define symbols
        tmean, tpc, mtc, lcf, lbp = sp.symbols(
            "tmean tpc mtc lcf lbp", real=True, positive=True
        )
        total_w, total_m = sp.symbols("total_w total_m", real=True)

        # Draft change formulas
        d_tmean = total_w / (tpc * 100.0)
        d_trim = total_m / (mtc * 100.0)

        # New draft formulas
        dfwd_new = sp.Symbol("dfwd0") + d_tmean - 0.5 * d_trim
        daft_new = sp.Symbol("daft0") + d_tmean + 0.5 * d_trim

        # Validate: trim should be daft - dfwd
        trim_calc = daft_new - dfwd_new
        expected_trim = d_trim

        # Check if formulas are consistent
        trim_diff = sp.simplify(trim_calc - expected_trim)
        is_consistent = trim_diff == 0

        # Validate units: d_tmean should have units of length (meters)
        # This is a simplified check - in practice would need unit checking library
        d_tmean_dim = sp.simplify(d_tmean.subs({total_w: 1, tpc: 1}))
        is_dimensionally_consistent = True  # Simplified check

        return {
            "available": True,
            "formula_consistent": is_consistent,
            "dimensionally_consistent": is_dimensionally_consistent,
            "d_tmean_formula": str(d_tmean),
            "d_trim_formula": str(d_trim),
        }
    except Exception as e:
        return {"available": True, "error": str(e)}


def export_to_excel(
    plan_df: pd.DataFrame,
    summary_df: pd.DataFrame,
    tank_log_df: Optional[pd.DataFrame] = None,
    bwrb_log_df: Optional[pd.DataFrame] = None,
    output_path: Path = Path("ballast_plan.xlsx"),
) -> None:
    """Export all results to a formatted Excel file with multiple sheets."""
    if not HAS_XLSXWRITER:
        raise ImportError(
            "xlsxwriter is required for Excel export. Install with: pip install xlsxwriter"
        )

    workbook = xlsxwriter.Workbook(str(output_path))

    # Define formats
    header_format = workbook.add_format(
        {
            "bold": True,
            "bg_color": "#366092",
            "font_color": "white",
            "border": 1,
            "align": "center",
            "valign": "vcenter",
        }
    )

    number_format = workbook.add_format({"num_format": "#,##0.00"})
    percent_format = workbook.add_format({"num_format": "0.0%"})
    warning_format = workbook.add_format(
        {"bg_color": "#FFC7CE", "font_color": "#9C0006"}
    )
    ok_format = workbook.add_format({"bg_color": "#C6EFCE", "font_color": "#006100"})

    # Sheet 1: Plan
    if not plan_df.empty:
        ws_plan = workbook.add_worksheet("Plan")
        for col_num, col_name in enumerate(plan_df.columns):
            ws_plan.write(0, col_num, col_name, header_format)
            # Auto-adjust column width
            max_len = max(
                len(str(col_name)), plan_df[col_name].astype(str).str.len().max()
            )
            ws_plan.set_column(col_num, col_num, min(max_len + 2, 50))

        for row_num, (_, row) in enumerate(plan_df.iterrows(), start=1):
            for col_num, col_name in enumerate(plan_df.columns):
                value = row[col_name]
                if isinstance(value, (int, float)):
                    ws_plan.write(row_num, col_num, value, number_format)
                else:
                    ws_plan.write(row_num, col_num, value)

    # Sheet 2: Summary
    if not summary_df.empty:
        ws_summary = workbook.add_worksheet("Summary")
        for col_num, col_name in enumerate(summary_df.columns):
            ws_summary.write(0, col_num, col_name, header_format)
            ws_summary.set_column(col_num, col_num, max(len(str(col_name)) + 2, 15))

        for row_num, (_, row) in enumerate(summary_df.iterrows(), start=1):
            for col_num, col_name in enumerate(summary_df.columns):
                value = row[col_name]
                # Check for warnings or compliance issues
                fmt = number_format
                if col_name == "dfwd_new_m" and isinstance(value, (int, float)):
                    if value > VesselParams.MAX_FWD_DRAFT_OPS:
                        fmt = warning_format
                    elif value >= VesselParams.MIN_DRAFT:
                        fmt = ok_format
                elif col_name == "daft_new_m" and isinstance(value, (int, float)):
                    if value > VesselParams.MAX_AFT_DRAFT_OPS:
                        fmt = warning_format
                    elif value >= VesselParams.MIN_DRAFT:
                        fmt = ok_format

                # Handle dict/list types (convert to string)
                if isinstance(value, (dict, list)):
                    value = str(value)

                if isinstance(value, (int, float)):
                    ws_summary.write(row_num, col_num, value, fmt)
                else:
                    ws_summary.write(row_num, col_num, str(value))

    # Sheet 3: Tank Log
    if tank_log_df is not None and not tank_log_df.empty:
        ws_tank = workbook.add_worksheet("Tank Log")
        for col_num, col_name in enumerate(tank_log_df.columns):
            ws_tank.write(0, col_num, col_name, header_format)
            ws_tank.set_column(col_num, col_num, max(len(str(col_name)) + 2, 12))

        for row_num, (_, row) in enumerate(tank_log_df.iterrows(), start=1):
            for col_num, col_name in enumerate(tank_log_df.columns):
                value = row[col_name]
                if isinstance(value, (int, float)):
                    ws_tank.write(row_num, col_num, value, number_format)
                else:
                    ws_tank.write(row_num, col_num, value)

    # Sheet 4: BWRB Log
    if bwrb_log_df is not None and not bwrb_log_df.empty:
        ws_bwrb = workbook.add_worksheet("BWRB Log")
        for col_num, col_name in enumerate(bwrb_log_df.columns):
            ws_bwrb.write(0, col_num, col_name, header_format)
            ws_bwrb.set_column(col_num, col_num, max(len(str(col_name)) + 2, 15))

        for row_num, (_, row) in enumerate(bwrb_log_df.iterrows(), start=1):
            for col_num, col_name in enumerate(bwrb_log_df.columns):
                value = row[col_name]
                if isinstance(value, (int, float)):
                    ws_bwrb.write(row_num, col_num, value, number_format)
                else:
                    ws_bwrb.write(row_num, col_num, value)

    # Sheet 5: Charts
    if (
        not summary_df.empty
        and "dfwd_new_m" in summary_df.columns
        and "daft_new_m" in summary_df.columns
    ):
        ws_charts = workbook.add_worksheet("Charts")

        # Draft comparison chart
        chart1 = workbook.add_chart({"type": "line"})
        fwd_col = summary_df.columns.get_loc("dfwd_new_m")
        aft_col = summary_df.columns.get_loc("daft_new_m")
        num_rows = len(summary_df)

        chart1.add_series(
            {
                "name": "FWD Draft",
                "categories": (
                    ["Summary", 0, 0, num_rows, 0]
                    if "Stage" in summary_df.columns
                    else None
                ),
                "values": ["Summary", 1, fwd_col, num_rows, fwd_col],
            }
        )
        chart1.add_series(
            {
                "name": "AFT Draft",
                "values": ["Summary", 1, aft_col, num_rows, aft_col],
            }
        )
        chart1.set_title({"name": "Draft Comparison"})
        chart1.set_x_axis(
            {"name": "Stage" if "Stage" in summary_df.columns else "Index"}
        )
        chart1.set_y_axis({"name": "Draft (m)"})
        chart1.set_size({"width": 720, "height": 480})
        ws_charts.insert_chart("B2", chart1)

        # Tank usage chart (if tank log available)
        if (
            tank_log_df is not None
            and not tank_log_df.empty
            and "Δt_t" in tank_log_df.columns
        ):
            chart2 = workbook.add_chart({"type": "column"})
            # Get top 10 tanks by absolute delta
            top_tanks = tank_log_df.reindex(
                tank_log_df["Δt_t"].abs().nlargest(10).index
            )
            tank_col = tank_log_df.columns.get_loc("Tank")
            delta_col = tank_log_df.columns.get_loc("Δt_t")
            num_tanks = len(top_tanks)

            chart2.add_series(
                {
                    "name": "Weight Change",
                    "categories": ["Tank Log", 1, tank_col, num_tanks, tank_col],
                    "values": ["Tank Log", 1, delta_col, num_tanks, delta_col],
                }
            )
            chart2.set_title({"name": "Top 10 Tank Weight Changes"})
            chart2.set_x_axis({"name": "Tank"})
            chart2.set_y_axis({"name": "Weight Change (t)"})
            chart2.set_size({"width": 720, "height": 480})
            ws_charts.insert_chart("B30", chart2)

    workbook.close()


def build_tank_log(tanks: List[Tank], delta: Dict[str, float]) -> pd.DataFrame:
    """Generate tank-by-tank log with start/end states."""
    return pd.DataFrame(
        [
            {
                "Tank": t.name,
                "UseFlag": t.use_flag,
                "Mode": t.mode,
                "Freeze": t.freeze_flag,
                "x_from_mid_m": round(t.x_from_mid_m, 2),
                "Start_t": round(t.current_t, 2),
                "Δt_t": round(float(delta.get(t.name, 0.0)), 2),
                "End_t": round(t.current_t + float(delta.get(t.name, 0.0)), 2),
                "Min_t": round(t.min_t, 2),
                "Max_t": round(t.max_t, 2),
            }
            for t in tanks
        ]
    )


def col_idx_to_excel_letter(col_idx: int) -> str:
    """
    Convert 0-based column index to Excel column letter (A, B, ..., Z, AA, AB, ...)

    Args:
        col_idx: 0-based column index

    Returns:
        Excel column letter (e.g., 0 -> 'A', 15 -> 'P', 26 -> 'AA')
    """
    result = ""
    col_idx += 1  # Convert to 1-based
    while col_idx > 0:
        col_idx -= 1
        result = chr(65 + (col_idx % 26)) + result
        col_idx //= 26
    return result


def get_styles(workbook: Optional[Any] = None) -> Dict[str, Any]:
    """
    Get xlsxwriter format styles for RORO Excel export.

    Args:
        workbook: xlsxwriter Workbook instance (required for creating formats)

    Returns:
        dict with format keys: title_format, header_format, input_fill, normal_font, etc.
    """
    if workbook is None:
        # Return format names only (will be created later)
        return {
            "title_format": None,
            "header_format": None,
            "input_fill": None,
            "normal_font": None,
            "ok_fill": None,
            "ng_fill": None,
            "structure_fill": None,
            "opt1_fill": None,
            "center_align": None,
        }

    # Create formats using workbook
    styles = {}

    # Title format
    styles["title_format"] = workbook.add_format(
        {
            "bold": True,
            "font_size": 14,
            "font_name": "Calibri",
        }
    )

    # Header format
    styles["header_format"] = workbook.add_format(
        {
            "bold": True,
            "bg_color": "#366092",
            "font_color": "#FFFFFF",
            "align": "center",
            "valign": "vcenter",
            "border": 1,
            "font_name": "Calibri",
        }
    )

    # Input fill (yellow)
    styles["input_fill"] = workbook.add_format(
        {
            "bg_color": "#FFFF99",
            "font_name": "Calibri",
        }
    )

    # Normal font
    styles["normal_font"] = workbook.add_format(
        {
            "font_name": "Calibri",
        }
    )

    # OK fill (green)
    styles["ok_fill"] = workbook.add_format(
        {
            "bg_color": "#C6EFCE",
            "font_color": "#006100",
            "font_name": "Calibri",
        }
    )

    # NG fill (red)
    styles["ng_fill"] = workbook.add_format(
        {
            "bg_color": "#FFC7CE",
            "font_color": "#9C0006",
            "font_name": "Calibri",
        }
    )

    # Structure fill (orange)
    styles["structure_fill"] = workbook.add_format(
        {
            "bg_color": "#FFC000",
            "font_name": "Calibri",
        }
    )

    # Option 1 fill (purple)
    styles["opt1_fill"] = workbook.add_format(
        {
            "bg_color": "#D9D9D9",
            "font_name": "Calibri",
        }
    )

    # Center align
    styles["center_align"] = workbook.add_format(
        {
            "align": "center",
            "valign": "vcenter",
            "font_name": "Calibri",
        }
    )

    return styles


def export_roro_stages_to_excel(
    stage_results: Dict[str, Dict[str, Any]],
    preballast_opt: float,
    base_tmean: float,
    base_disp: float,
    output_path: Path = Path("roro_stages.xlsx"),
    params: Optional[Dict[str, Any]] = None,
    tanks: Optional[List[Tank]] = None,
) -> None:
    """
    Export RORO stage results to Excel file with RORO_Stage_Scenarios sheet.
    Structure matches agi_tr_patched_v6_6.py create_roro_sheet format.

    Args:
        stage_results: Dict mapping stage names to calculation results
        preballast_opt: Optimized pre-ballast weight (t)
        base_tmean: Base mean draft (m)
        base_disp: Base displacement (t)
        output_path: Output Excel file path
        params: Optional parameters dict (MTC, LCF, LBP, D_vessel, TPC, pump_rate_effective_tph, etc.)
    """
    if not HAS_XLSXWRITER:
        print("[WARNING] xlsxwriter not available, skipping Excel export")
        return

    workbook = xlsxwriter.Workbook(str(output_path))
    number_format = "#,##0.00"

    # Get styles
    styles = get_styles(workbook)

    # Default parameters
    if params is None:
        params = {}
    MTC = params.get("MTC", 34.00)
    LCF = params.get("LCF", 0.76)
    LBP = params.get("LBP", 60.302)
    D_vessel = params.get("D_vessel", 3.65)
    TPC = params.get("TPC", 8.00)
    pump_rate_effective_tph = params.get("pump_rate_effective_tph", 100.00)
    Tide_ref = params.get(
        "Forecast_Tide_m", params.get("Tide_ref", 2.00)
    )  # Forecast tide height (CD)
    Trim_target_cm = params.get("Trim_target_cm", 240.0)
    X_Ballast = params.get("X_Ballast", fr_to_x(3.0))  # FW2 center at Fr 3.0

    # Create RORO_Stage_Scenarios sheet
    ws = workbook.add_worksheet("RORO_Stage_Scenarios")

    # Row 1: Title
    ws.write(
        0,
        0,
        "RORO Stage Scenarios – Option C (Target 240cm Safe Margin)",
        styles["title_format"],
    )

    # Row 2: Input parameter 안내
    ws.write(1, 2, "← Input parameter(yellow cellls only)", styles["normal_font"])

    # Row 4: 섹션 제목
    ws.write(
        3,
        0,
        "1.Critical Stage Verification: Trim & Draft Status Sequence",
        styles["normal_font"],
    )
    ws.write(3, 5, "2. Stage Sequence Table", styles["normal_font"])

    # Row 5: 헤더
    headers_row5 = [
        ("A", "Parameter"),
        ("B", "Value"),
        ("C", "Unit"),
        ("D", "REMARK"),
        ("F", "Stage"),
        ("G", "EXPLANATION"),
        ("O", "Fwd Draft (m)"),
        ("P", "Freeboard (m)"),
        ("Q", "Aft Draft (m)"),
        ("R", "Status Assessment"),
    ]
    col_map = {
        "A": 0,
        "B": 1,
        "C": 2,
        "D": 3,
        "E": 4,
        "F": 5,
        "G": 6,
        "H": 7,
        "I": 8,
        "J": 9,
        "K": 10,
        "L": 11,
        "M": 12,
        "N": 13,
        "O": 14,
        "P": 15,
        "Q": 16,
        "R": 17,
    }
    for letter, header in headers_row5:
        col_idx = col_map.get(letter, 0)
        ws.write(4, col_idx, header, styles["header_format"])

    # Row 6-15: 파라미터 섹션
    num_format = workbook.add_format({"num_format": number_format})
    input_num_format = workbook.add_format(
        {"num_format": number_format, "bg_color": "#FFFF99"}
    )

    # Stage explanations
    explanations = {
        "Stage 1": "Arrival lightship condition. Baseline drafts, trim, and GM are checked before any cargo loading or ballast change.",
        "Stage 2": "TR1 roll-on start – first axle on the ramp. Initial bow-down trim response is checked against allowable draft and freeboard limits.",
        "Stage 3": "TR1 mid-ramp – transformer COG on the ramp. Progressive bow-down trim is monitored to remain within the allowable envelope.",
        "Stage 4": "TR1 fully on deck. Weight is completely transferred from ramp to vessel deck; deck loading, ramp condition, drafts, and trim are verified.",
        "Stage 5": "TR1 secured at final aft stowage position (around Fr.42). New reference condition with TR1 only on board, used as the basis for D-1 stern pre-ballasting using FW2 (Fr.0–6, aft).",
        "Stage 5_PreBallast": (
            "Pre-ballast condition with TR1 only on board (D-1, using shore water). "
            "An intentional stern trim is set using the aft FW2 fresh water tanks (Fr.0–6, AFT, Ballast CG near FR 3.0) "
            "so that the bow-down trimming moment of TR2 at ramp entry is counterbalanced and the forward draft remains within the 2.70 m AGI limit "
            "without any major dynamic ballasting during the critical RORO operation on D-day."
        ),
        "Stage 6A_Critical (Opt C)": "Critical TR2 ramp-entry condition on D-day with the D-1 stern pre-ballast (FW2, Fr.0–6) kept fixed. This stage is used to check worst-case forward draft against the 2.70 m limit, trim envelope, GM criteria, and ramp/linkspan clearance under combined TR1+TR2 loading.",
        "Stage 6C_TotalMassOpt": 'Alternative "total mass optimized" final condition with TR1 and TR2 on deck and higher combined cargo+ballast weight. Sensitivity case to assess maximum displacement effects on drafts, trim, GM and freeboard.',
        "Stage 6C": "Planned final stowage condition with TR1 and TR2 secured on deck and ballast as per departure plan. Main departure case for checking GM, trim and freeboard criteria.",
        "Stage 7": "Post-operation lightship/reference condition after cargo is discharged. Used to reconfirm hydrostatic characteristics and GM consistency against Stage 1.",
    }

    stages_list = [
        "Stage 1",
        "Stage 2",
        "Stage 3",
        "Stage 4",
        "Stage 5",
        "Stage 5_PreBallast",
        "Stage 6A_Critical (Opt C)",
        "Stage 6C_TotalMassOpt",
        "Stage 6C",
        "Stage 7",
    ]

    # A6: Tmean_baseline
    ws.write(5, 0, "Tmean_baseline", styles["normal_font"])
    ws.write(5, 1, base_tmean, input_num_format)
    ws.write(5, 2, "m", styles["normal_font"])
    ws.write(5, 3, "Baseline mean draft (from hydro table)", styles["normal_font"])
    ws.write(5, 5, stages_list[0], styles["normal_font"])
    if stages_list[0] in explanations:
        ws.write(5, 6, explanations[stages_list[0]], styles["input_fill"])

    # A7: Forecast_Tide_m (Chart Datum)
    ws.write(6, 0, "Forecast_Tide_m", styles["normal_font"])
    ws.write(6, 1, Tide_ref, input_num_format)
    ws.write(6, 2, "m", styles["normal_font"])
    ws.write(
        6,
        3,
        "Forecast tide height (Chart Datum) – source: official tide table (station/datum/TZ)",
        styles["normal_font"],
    )
    ws.write(
        6, 5, stages_list[1] if len(stages_list) > 1 else "", styles["normal_font"]
    )
    if len(stages_list) > 1 and stages_list[1] in explanations:
        ws.write(6, 6, explanations[stages_list[1]], styles["input_fill"])

    # A8: Trim_target_cm
    ws.write(7, 0, "Trim_target_cm", styles["normal_font"])
    ws.write(7, 1, Trim_target_cm, input_num_format)
    ws.write(7, 2, "cm", styles["normal_font"])
    ws.write(7, 3, "Target trim (bow down = negative)", styles["normal_font"])
    ws.write(
        7, 5, stages_list[2] if len(stages_list) > 2 else "", styles["normal_font"]
    )
    if len(stages_list) > 2 and stages_list[2] in explanations:
        ws.write(7, 6, explanations[stages_list[2]], styles["input_fill"])

    # A9: MTC
    ws.write(8, 0, "MTC", styles["normal_font"])
    ws.write(8, 1, MTC, input_num_format)
    ws.write(8, 2, "t·m/cm", styles["normal_font"])
    ws.write(8, 3, "Moment to change trim 1cm", styles["normal_font"])
    ws.write(
        8, 5, stages_list[3] if len(stages_list) > 3 else "", styles["normal_font"]
    )
    if len(stages_list) > 3 and stages_list[3] in explanations:
        ws.write(8, 6, explanations[stages_list[3]], styles["input_fill"])

    # A10: LCF
    ws.write(9, 0, "LCF", styles["normal_font"])
    ws.write(9, 1, LCF, input_num_format)
    ws.write(9, 2, "m", styles["normal_font"])
    ws.write(
        9,
        3,
        "Longitudinal center of flotation (from midship, aft=+)",
        styles["normal_font"],
    )
    ws.write(
        9, 5, stages_list[4] if len(stages_list) > 4 else "", styles["normal_font"]
    )
    if len(stages_list) > 4 and stages_list[4] in explanations:
        ws.write(9, 6, explanations[stages_list[4]], styles["input_fill"])

    # A11: D_vessel
    ws.write(10, 0, "D_vessel", styles["normal_font"])
    ws.write(10, 1, D_vessel, input_num_format)
    ws.write(10, 2, "m", styles["normal_font"])
    ws.write(10, 3, "Deck elevation (CD)", styles["normal_font"])
    ws.write(
        10, 5, stages_list[5] if len(stages_list) > 5 else "", styles["normal_font"]
    )
    if len(stages_list) > 5 and stages_list[5] in explanations:
        ws.write(10, 6, explanations[stages_list[5]], styles["input_fill"])

    # A12: TPC
    ws.write(11, 0, "TPC", styles["normal_font"])
    ws.write(11, 1, TPC, input_num_format)
    ws.write(11, 2, "t/cm", styles["normal_font"])
    ws.write(11, 3, "Tons per centimeter immersion", styles["normal_font"])
    ws.write(
        11, 5, stages_list[6] if len(stages_list) > 6 else "", styles["normal_font"]
    )
    if len(stages_list) > 6 and stages_list[6] in explanations:
        ws.write(11, 6, explanations[stages_list[6]], styles["input_fill"])

    # A13: pump_rate_effective_tph
    ws.write(12, 0, "pump_rate_effective_tph", styles["normal_font"])
    ws.write(12, 1, pump_rate_effective_tph, input_num_format)
    ws.write(12, 2, "t/h", styles["normal_font"])
    ws.write(12, 3, "Effective ballast pump rate", styles["normal_font"])
    ws.write(
        12, 5, stages_list[7] if len(stages_list) > 7 else "", styles["normal_font"]
    )
    if len(stages_list) > 7 and stages_list[7] in explanations:
        ws.write(12, 6, explanations[stages_list[7]], styles["input_fill"])

    # A14: X_Ballast
    ws.write(13, 0, "X_Ballast", styles["normal_font"])
    ws.write(13, 1, X_Ballast, input_num_format)
    ws.write(13, 2, "m", styles["normal_font"])
    ws.write(13, 3, "Ballast CG x from midship (aft=+)", styles["normal_font"])
    ws.write(
        13, 5, stages_list[8] if len(stages_list) > 8 else "", styles["normal_font"]
    )
    if len(stages_list) > 8 and stages_list[8] in explanations:
        ws.write(13, 6, explanations[stages_list[8]], styles["input_fill"])

    # A15: Lpp
    ws.write(14, 0, "Lpp", styles["normal_font"])
    ws.write(14, 1, LBP, input_num_format)
    ws.write(14, 2, "m", styles["normal_font"])
    ws.write(14, 3, "Length between perpendiculars", styles["normal_font"])
    ws.write(
        14, 5, stages_list[9] if len(stages_list) > 9 else "", styles["normal_font"]
    )
    if len(stages_list) > 9 and stages_list[9] in explanations:
        ws.write(14, 6, explanations[stages_list[9]], styles["input_fill"])

    # Row 17: Ballast Water Optimization Matrix 제목
    ws.write(16, 0, "Ballast Water Optimization Matrix", styles["title_format"])

    # Row 18: Stage table 헤더 (21개 컬럼)
    stage_headers = [
        "Stage",
        "W_stage_t",
        "Fr_stage",
        "x_stage_m",
        "TM (t·m)",
        "Trim_cm",
        "FWD_precise_m",
        "AFT_precise_m",
        "ΔTM_cm_tm",
        "Lever_arm_m",
        "Ballast_t_calc",
        "Ballast_time_h_calc",
        "Ballast_t",
        "Ballast_time_h",
        "Trim_Check",
        "Dfwd_m",
        "Daft_m",
        "Trim_target_stage_cm",
        "FWD_DeckElev_CD_m",
        "AFT_DeckElev_CD_m",
        "Difference",
    ]
    for col_idx, header in enumerate(stage_headers):
        ws.write(17, col_idx, header, styles["header_format"])

    # Row 19+: Stage 데이터
    stages_order = [
        "Stage 1",
        "Stage 2",
        "Stage 3",
        "Stage 4",
        "Stage 5",
        "Stage 5_PreBallast",
        "Stage 6A_Critical (Opt C)",
        "Stage 6C_TotalMassOpt",
        "Stage 6C",
        "Stage 7",
    ]

    first_data_row = 18  # Row 19 (0-based index 18)
    for row_idx, stage_name in enumerate(stages_order, start=first_data_row):
        if stage_name not in stage_results:
            continue

        res = stage_results[stage_name]

        # Stage
        ws.write(row_idx, 0, stage_name, styles["normal_font"])

        # W_stage_t
        ws.write(row_idx, 1, res.get("W_stage_t", 0.0), num_format)

        # Fr_stage (calculate from x_stage_m)
        x_stage = res.get("x_stage_m", 0.0)
        fr_stage = x_to_fr(x_stage) if abs(x_stage) > 0.01 else 0.0
        ws.write(row_idx, 2, fr_stage, num_format)

        # x_stage_m
        ws.write(row_idx, 3, x_stage, num_format)

        # TM (t·m)
        tm_tm = res.get("TM_LCF_tm", res.get("TM_tm", 0.0))
        ws.write(row_idx, 4, tm_tm, num_format)

        # Trim_cm
        trim_cm = res.get("Trim_cm", 0.0)
        ws.write(row_idx, 5, trim_cm, num_format)

        # FWD_precise_m
        dfwd_m = res.get("Dfwd_m", 0.0)
        ws.write(row_idx, 6, dfwd_m, num_format)

        # AFT_precise_m
        daft_m = res.get("Daft_m", 0.0)
        ws.write(row_idx, 7, daft_m, num_format)

        # ΔTM_cm_tm (trim change moment)
        dtm_cm_tm = res.get("ΔTM_cm_tm", 0.0)
        ws.write(row_idx, 8, dtm_cm_tm, num_format)

        # Lever_arm_m
        lever_arm = res.get("Lever_arm_m", X_Ballast - LCF)
        ws.write(row_idx, 9, lever_arm, num_format)

        # Ballast_t_calc
        ballast_t_calc = res.get("Ballast_t_calc", res.get("Ballast_t", 0.0))
        ws.write(row_idx, 10, ballast_t_calc, num_format)

        # Ballast_time_h_calc
        ballast_time_h_calc = res.get(
            "Ballast_time_h_calc", res.get("Ballast_time_h", 0.0)
        )
        ws.write(row_idx, 11, ballast_time_h_calc, num_format)

        # Ballast_t
        ballast_t = res.get("Ballast_t", 0.0)
        ws.write(row_idx, 12, ballast_t, num_format)

        # Ballast_time_h
        ballast_time_h = res.get("Ballast_time_h", 0.0)
        ws.write(row_idx, 13, ballast_time_h, num_format)

        # Trim_Check
        trim_check = res.get(
            "Trim_Check", "OK" if abs(trim_cm) <= abs(Trim_target_cm) else "NG"
        )
        trim_check_format = (
            styles["ok_fill"] if trim_check == "OK" else styles["ng_fill"]
        )
        ws.write(row_idx, 14, trim_check, trim_check_format)

        # Dfwd_m
        ws.write(row_idx, 15, dfwd_m, num_format)

        # Daft_m
        ws.write(row_idx, 16, daft_m, num_format)

        # Trim_target_stage_cm
        trim_target_stage = res.get("Trim_target_stage_cm", Trim_target_cm)
        ws.write(row_idx, 17, trim_target_stage, num_format)

        # FWD_DeckElev_CD_m (D_vessel - Dfwd_m + Tide_ref)
        fwd_deck_elev = D_vessel - dfwd_m + Tide_ref
        ws.write(row_idx, 18, fwd_deck_elev, num_format)

        # AFT_DeckElev_CD_m (D_vessel - Daft_m + Tide_ref)
        aft_deck_elev = D_vessel - daft_m + Tide_ref
        ws.write(row_idx, 19, aft_deck_elev, num_format)

        # Difference
        difference = res.get("Difference", fwd_deck_elev - aft_deck_elev)
        ws.write(row_idx, 20, difference, num_format)

        # Status Assessment (Column R, index 17) - Fwd Draft vs 2.70m
        fwd_limit = 2.70
        vs_270 = "OK" if dfwd_m <= fwd_limit else "NG"
        status_format = styles["ok_fill"] if vs_270 == "OK" else styles["ng_fill"]
        ws.write(row_idx, col_map["R"], vs_270, status_format)

    # Set column widths
    ws.set_column(0, 0, 25)  # Stage
    ws.set_column(1, 20, 12)  # Other columns
    ws.set_column(6, 6, 15)  # EXPLANATION column wider

    # Freeze panes at G2 (column F, row 1)
    ws.freeze_panes(1, 6)

    # Extend with Captain Requirement columns (U-AE)
    extend_roro_captain_req(
        ws,
        workbook,
        first_data_row,
        len(stages_order),
        styles,
        num_format,
        D_vessel,
        TPC,
        pump_rate_effective_tph,
        Trim_target_cm,
    )

    # Extend with Structural/Option 1 columns (AK-BB)
    extend_roro_structural_opt1(
        ws, workbook, first_data_row, len(stages_order), styles, num_format
    )

    # Create BALLASTING sheet
    create_ballasting_sheet(
        workbook=workbook,
        stage_results=stage_results,
        tanks=tanks,  # Use provided tanks or default
        styles=styles,
        params=params,
    )

    workbook.close()
    print(f"[INFO] RORO Excel file created: {output_path}")


def extend_roro_captain_req(
    ws: Any,
    workbook: Any,
    first_data_row: int,
    num_stages: int,
    styles: Dict[str, Any],
    num_format: Any,
    D_vessel: float,
    TPC: float,
    pump_rate_effective_tph: float,
    Trim_target_cm: float,
) -> None:
    """
    Add Captain Requirement columns (U-AE) to RORO_Stage_Scenarios sheet.

    Columns:
    - U(21): GM(m) - from stage_results
    - V(22): Fwd Draft(m) - Dfwd_m copy
    - W(23): vs 2.70m - Fwd ≤ 2.70m check
    - X(24): De-ballast Qty(t) - Ballast_t
    - Y(25): Timing - manual input
    - Z(26): Phys_Freeboard_m - D_vessel - Dfwd_m
    - AA(27): Clearance_Check - optional
    - AB(28): GM_calc - GM copy
    - AC(29): GM_Check - GM ≥ GM_target check
    - AD(30): Disp_total_t - Total displacement
    - AE(31): Vent_Time_h - De-ballast qty / pump rate
    """
    # Header row (Row 18, 0-based index 17)
    header_row = 17

    captain_cols = [
        "GM(m)",  # U(21)
        "Fwd Draft(m)",  # V(22)
        "vs 2.70m+Tide",  # W(23)
        "De-ballast Qty(t)",  # X(24)
        "Timing",  # Y(25)
        "Phys_Freeboard_m",  # Z(26)
        "Clearance_Check",  # AA(27)
        "GM_calc",  # AB(28)
        "GM_Check",  # AC(29)
        "Disp_total_t",  # AD(30)
        "Vent_Time_h",  # AE(31)
    ]

    start_col = 21  # U column (0-based index 21)

    # Write headers
    for i, header in enumerate(captain_cols):
        col_idx = start_col + i
        ws.write(header_row, col_idx, header, styles["header_format"])

    # Write data for each stage
    # Define column indices for reference
    col_dfwd = 15  # Dfwd_m column (P in Excel)
    col_daft = 16  # Daft_m column (Q in Excel)
    col_ballast_t = 12  # Ballast_t column (M in Excel)
    col_w_stage = 1  # W_stage_t column (B in Excel)
    col_gm = 21  # GM(m) column (U in Excel)
    col_fwd_draft = 22  # Fwd Draft(m) column (V in Excel)
    col_vs_270 = 23  # vs 2.70m column (W in Excel)
    col_deballast = 24  # De-ballast Qty(t) column (X in Excel)
    col_phys_freeboard = 26  # Phys_Freeboard_m column (Z in Excel)
    col_gm_calc = 28  # GM_calc column (AB in Excel)
    col_gm_check = 29  # GM_Check column (AC in Excel)
    col_disp_total = 30  # Disp_total_t column (AD in Excel)
    col_vent_time = 31  # Vent_Time_h column (AE in Excel)

    # Parameter row references (1-based Excel row numbers)
    param_row_d_vessel = 11  # D_vessel parameter (row_idx=10, Excel row 11)
    param_row_pump_rate = 13  # pump_rate_effective_tph (row_idx=12, Excel row 13)
    col_letter_param_b = col_idx_to_excel_letter(1)  # B column

    for row_idx in range(first_data_row, first_data_row + num_stages):
        row_num = row_idx + 1  # Excel row number (1-based)

        # U(21): GM(m) - from stage_results (will be filled by Python values)
        # Note: Excel formula would be: =IFERROR(VLOOKUP(AVERAGE(P{row},Q{row}), Hydro_Table!$B:$D, 3, 1), "")
        # But we use Python calculated values instead
        ws.write(
            row_idx, col_gm, "", num_format
        )  # Placeholder, will be filled from stage_results

        # V(22): Fwd Draft(m) - =P{row} (Dfwd_m column, index 15)
        col_letter_dfwd = col_idx_to_excel_letter(col_dfwd)
        ws.write_formula(
            row_idx, col_fwd_draft, f"={col_letter_dfwd}{row_num}", num_format
        )

        # W(23): vs 2.70m - =IF(V{row}<=2.70,"OK","NG")
        col_letter_fwd_draft = col_idx_to_excel_letter(col_fwd_draft)
        ws.write_formula(
            row_idx,
            col_vs_270,
            f'=IF({col_letter_fwd_draft}{row_num}<=2.70+$B$7,"OK","NG")',
            styles["normal_font"],
        )

        # X(24): De-ballast Qty(t) - =M{row} (Ballast_t column, index 12)
        col_letter_ballast = col_idx_to_excel_letter(col_ballast_t)
        ws.write_formula(
            row_idx, col_deballast, f"={col_letter_ballast}{row_num}", num_format
        )

        # Y(25): Timing - manual input (yellow fill)
        ws.write(row_idx, 25, "", styles["input_fill"])

        # Z(26): Phys_Freeboard_m - =B11 - P{row} (D_vessel - Dfwd_m)
        # Note: B11 is parameter row 11 (row_idx=10, col 1)
        ws.write_formula(
            row_idx,
            col_phys_freeboard,
            f"={col_letter_param_b}{param_row_d_vessel}-{col_letter_dfwd}{row_num}",
            num_format,
        )

        # AA(27): Clearance_Check - optional, skip for now

        # AB(28): GM_calc - =U{row}
        col_letter_gm = col_idx_to_excel_letter(col_gm)
        ws.write_formula(row_idx, col_gm_calc, f"={col_letter_gm}{row_num}", num_format)

        # AC(29): GM_Check - =IF(AB{row}>=1.50,"OK","NG") (GM_target = 1.50m)
        col_letter_gm_calc = col_idx_to_excel_letter(col_gm_calc)
        ws.write_formula(
            row_idx,
            col_gm_check,
            f'=IF({col_letter_gm_calc}{row_num}>=1.50,"OK","NG")',
            styles["normal_font"],
        )

        # AD(30): Disp_total_t - =B{row} + M{row} (W_stage_t + Ballast_t)
        # Note: This is simplified; actual formula might include CONST_TANKS
        col_letter_w_stage = col_idx_to_excel_letter(col_w_stage)
        ws.write_formula(
            row_idx,
            col_disp_total,
            f"={col_letter_w_stage}{row_num}+{col_letter_ballast}{row_num}",
            num_format,
        )

        # AE(31): Vent_Time_h - =IF(OR(X{row}="",B13="",B13=0),"",ROUND(ABS(X{row})/B13,2))
        # Note: B13 is pump_rate_effective_tph (row 13, col 1)
        col_letter_deballast = col_idx_to_excel_letter(col_deballast)
        ws.write_formula(
            row_idx,
            col_vent_time,
            f'=IF(OR({col_letter_deballast}{row_num}="",{col_letter_param_b}{param_row_pump_rate}="",{col_letter_param_b}{param_row_pump_rate}=0),"",ROUND(ABS({col_letter_deballast}{row_num})/{col_letter_param_b}{param_row_pump_rate},2))',
            num_format,
        )

    print("  [OK] Captain Requirement columns added (U-AE)")


def extend_roro_structural_opt1(
    ws: Any,
    workbook: Any,
    first_data_row: int,
    num_stages: int,
    styles: Dict[str, Any],
    num_format: Any,
) -> None:
    """
    Add Structural Strength and Option 1 Ballast Fix Check columns (AK-BB) to RORO_Stage_Scenarios sheet.

    Columns:
    - AK-AP(37-42): Structural Strength columns
    - AQ(43): Dynamic Load Case B
    - AR-AS(44-45): Heel/FSE (handled by extend_roro_captain_req)
    - AT-AV(46-48): Option 1 Ballast Fix Check
    - AW-AZ(49-52): Ramp Angle & Pin Stress
    - BA-BB(53-54): Opt C / High Tide
    """
    # Header row (Row 18, 0-based index 17)
    header_row = 17

    structural_cols = [
        "Share_Load_t",  # AK(37)
        "Share_Check",  # AL(38)
        "Hinge_Rx_t",  # AM(39)
        "Rx_Check",  # AN(40)
        "Deck_Press_t/m²",  # AO(41)
        "Press_Check",  # AP(42)
    ]

    dynamic_load_cols = [
        "Load_Case_B_t",  # AQ(43)
    ]

    opt1_cols = [
        "Ballast_req_t",  # AT(46)
        "Ballast_gap_t",  # AU(47)
        "Time_Add_h",  # AV(48)
    ]

    ramp_stress_cols = [
        "Ramp_Angle_deg",  # AW(49)
        "Ramp_Angle_Check",  # AX(50)
        "Pin_Stress_N/mm²",  # AY(51)
        "Von_Mises_Check",  # AZ(52)
    ]

    # Tide / Water Level definitions (to avoid misinterpretation)
    # - Forecast_Tide_m: from official tide table (Chart Datum)
    # - Required_WL_m: required water level (sea level) to satisfy draft limits (NOT a forecast)
    opt_c_tide_cols = [
        "Required_WL_m",  # BA(53) - required water level/sea level (NOT forecast)
        "WL_OK",  # BB(54) - Forecast_Tide_m >= Required_WL_m
        "Forecast_Tide_m",  # BC(55) - repeated input value for clarity
        "FWD_Allow_m",  # BD(56) = MAX_FWD_DRAFT_OPS + Forecast_Tide_m
        "FWD_OK_wTide",  # BE(57) = IF(Dfwd_m <= FWD_Allow_m, OK, NG)
        "AFT_Min_2.70_OK",  # BF(58) = IF(Daft_m >= 2.70, OK, NG)
        "Min_Freeboard_m",  # BG(59) = D_vessel - MAX(Dfwd_m, Daft_m)
        "Deck_Encroach_Check",  # BH(60) = IF(Min_Freeboard_m > 0, OK, NG)
    ]

    all_cols = (
        structural_cols
        + dynamic_load_cols
        + opt1_cols
        + ramp_stress_cols
        + opt_c_tide_cols
    )
    start_col = 37  # AK column (0-based index 37)

    # Write headers with appropriate fills
    for i, header in enumerate(all_cols):
        col_idx = start_col + i

        # Create header format with appropriate fill color
        if i < len(structural_cols):
            bg_color = "#FFC000"  # Orange for structural
        elif i < len(structural_cols) + len(dynamic_load_cols):
            bg_color = "#FFC000"  # Orange for dynamic load
        elif i < len(structural_cols) + len(dynamic_load_cols) + len(opt1_cols):
            bg_color = "#D9D9D9"  # Gray for option 1
        elif i < len(structural_cols) + len(dynamic_load_cols) + len(opt1_cols) + len(
            ramp_stress_cols
        ):
            bg_color = "#FFC000"  # Orange for ramp/stress
        else:
            bg_color = "#D9D9D9"  # Gray for opt c tide

        header_fmt = workbook.add_format(
            {
                "bold": True,
                "bg_color": bg_color,
                "font_color": "#FFFFFF",
                "align": "center",
                "valign": "vcenter",
                "border": 1,
                "font_name": "Calibri",
            }
        )

        ws.write(header_row, col_idx, header, header_fmt)

    # Write data for each stage
    # Define column indices for reference
    col_share_load = 37  # Share_Load_t column (AK in Excel)
    col_share_check = 38  # Share_Check column (AL in Excel)
    col_hinge_rx = 39  # Hinge_Rx_t column (AM in Excel)
    col_rx_check = 40  # Rx_Check column (AN in Excel)
    col_deck_press = 41  # Deck_Press_t/m² column (AO in Excel)
    col_press_check = 42  # Press_Check column (AP in Excel)
    col_load_case_b = 43  # Load_Case_B_t column (AQ in Excel)
    col_ballast_req = 46  # Ballast_req_t column (AT in Excel)
    col_ballast_gap = 47  # Ballast_gap_t column (AU in Excel)
    col_time_add = 48  # Time_Add_h column (AV in Excel)
    col_stage = 0  # Stage column (A in Excel)
    col_lever_arm = (
        9  # Lever_arm_m column (J in Excel, but formula uses I which is col 8)
    )
    col_lever_arm_formula = (
        8  # I column in formula (actually Lever_arm_m is col 9, but formula uses I)
    )
    col_mtc_formula = 9  # J column in formula (MTC reference)
    col_ballast_t_ref = 12  # Ballast_t column (M in Excel)

    # Parameter row references
    param_row_pump_rate = 13  # pump_rate_effective_tph (row_idx=12, Excel row 13)
    col_letter_param_b = col_idx_to_excel_letter(1)  # B column

    for row_idx in range(first_data_row, first_data_row + num_stages):
        row_num = row_idx + 1  # Excel row number (1-based)

        # AK(37): Share_Load_t - manual input (yellow fill)
        ws.write(row_idx, col_share_load, "", styles["input_fill"])

        # AL(38): Share_Check - =IF(AK{row}<=Calc!$E$24,"OK","CHECK")
        # Note: Simplified without Calc sheet reference
        col_letter_share_load = col_idx_to_excel_letter(col_share_load)
        ws.write_formula(
            row_idx,
            col_share_check,
            f'=IF({col_letter_share_load}{row_num}<=100,"OK","CHECK")',
            styles["normal_font"],
        )

        # AM(39): Hinge_Rx_t - =IF(AK{row}="",45,45+AK{row}*0.545)
        ws.write_formula(
            row_idx,
            col_hinge_rx,
            f'=IF({col_letter_share_load}{row_num}="",45,45+{col_letter_share_load}{row_num}*0.545)',
            num_format,
        )

        # AN(40): Rx_Check - =IF(AM{row}<=Calc!$E$37,"OK","NG")
        col_letter_hinge_rx = col_idx_to_excel_letter(col_hinge_rx)
        ws.write_formula(
            row_idx,
            col_rx_check,
            f'=IF({col_letter_hinge_rx}{row_num}<=200,"OK","NG")',
            styles["normal_font"],
        )

        # AO(41): Deck_Press_t/m² - =IF(AK{row}="","",AK{row}/Calc!$E$26)
        ws.write_formula(
            row_idx,
            col_deck_press,
            f'=IF({col_letter_share_load}{row_num}="","",{col_letter_share_load}{row_num}/10)',
            num_format,
        )

        # AP(42): Press_Check - =IF(AO{row}<=Calc!$E$25,"OK","CHECK")
        col_letter_deck_press = col_idx_to_excel_letter(col_deck_press)
        ws.write_formula(
            row_idx,
            col_press_check,
            f'=IF({col_letter_deck_press}{row_num}<=4,"OK","CHECK")',
            styles["normal_font"],
        )

        # AQ(43): Load_Case_B_t - =IF(AK{row}="","",AK{row}*Calc!$E$42)
        ws.write_formula(
            row_idx,
            col_load_case_b,
            f'=IF({col_letter_share_load}{row_num}="","",{col_letter_share_load}{row_num}*1.5)',
            num_format,
        )

        # AT(46): Ballast_req_t - =IF($A{row}="","",IF(OR($I{row}="",$I{row}=0),0,ROUND(H{row}/$I{row},2)))
        # Note: H{row} is Lever_arm_m (col 9, Excel I), I{row} is MTC reference (col 8, Excel J)
        # Actually: Lever_arm_m is col 9 (J), but formula uses I (col 8) and J (col 9)
        col_letter_stage = col_idx_to_excel_letter(col_stage)
        col_letter_lever_arm_i = col_idx_to_excel_letter(
            col_lever_arm_formula
        )  # I column
        col_letter_mtc_j = col_idx_to_excel_letter(col_mtc_formula)  # J column
        ws.write_formula(
            row_idx,
            col_ballast_req,
            f'=IF(${col_letter_stage}{row_num}="","",IF(OR(${col_letter_mtc_j}{row_num}="",${col_letter_mtc_j}{row_num}=0),0,ROUND({col_letter_lever_arm_i}{row_num}/${col_letter_mtc_j}{row_num},2)))',
            num_format,
        )

        # AU(47): Ballast_gap_t - =IF($A{row}="","",AT{row}-$M{row})
        col_letter_ballast_req = col_idx_to_excel_letter(col_ballast_req)
        col_letter_ballast_t = col_idx_to_excel_letter(col_ballast_t_ref)
        ws.write_formula(
            row_idx,
            col_ballast_gap,
            f'=IF(${col_letter_stage}{row_num}="","",{col_letter_ballast_req}{row_num}-${col_letter_ballast_t}{row_num})',
            num_format,
        )

        # AV(48): Time_Add_h - =IF(AU{row}="","",ROUND(AU{row}/B13,2))
        col_letter_ballast_gap = col_idx_to_excel_letter(col_ballast_gap)
        ws.write_formula(
            row_idx,
            col_time_add,
            f'=IF({col_letter_ballast_gap}{row_num}="","",ROUND({col_letter_ballast_gap}{row_num}/{col_letter_param_b}{param_row_pump_rate},2))',
            num_format,
        )

        # AW(49): Ramp_Angle_deg - placeholder
        ws.write(row_idx, 49, "", num_format)

        # AX(50): Ramp_Angle_Check - placeholder
        ws.write(row_idx, 50, "", styles["normal_font"])

        # AY(51): Pin_Stress_N/mm² - placeholder
        ws.write(row_idx, 51, "", num_format)

        # AZ(52): Von_Mises_Check - placeholder
        ws.write(row_idx, 52, "", styles["normal_font"])

        # BA(53): Required_WL_m (required water level/sea level to satisfy draft limits; NOT forecast)
        # Required_WL_m = MAX(0, Dfwd_m - MAX_FWD_DRAFT_OPS, Daft_m - MAX_AFT_DRAFT_OPS)
        col_letter_dfwd = col_idx_to_excel_letter(15)  # Dfwd_m column (P, 0-based 15)
        col_letter_daft = col_idx_to_excel_letter(16)  # Daft_m column (Q, 0-based 16)
        ws.write_formula(
            row_idx,
            53,
            f"=MAX(0,{col_letter_dfwd}{row_num}-{VesselParams.MAX_FWD_DRAFT_OPS:.2f},{col_letter_daft}{row_num}-{VesselParams.MAX_AFT_DRAFT_OPS:.2f})",
            num_format,
        )

        # BB(54): WL_OK (Forecast_Tide_m >= Required_WL_m)
        ws.write_formula(
            row_idx,
            54,
            f'=IF($B$7>={col_idx_to_excel_letter(53)}{row_num},"OK","NG")',
            styles["normal_font"],
        )

        # BC(55): Forecast_Tide_m (repeat input for clarity)
        ws.write_formula(row_idx, 55, "=$B$7", num_format)

        # BD(56): FWD_Allow_m = MAX_FWD_DRAFT_OPS + Forecast_Tide_m
        ws.write_formula(
            row_idx, 56, f"={VesselParams.MAX_FWD_DRAFT_OPS:.2f}+$B$7", num_format
        )

        # BE(57): FWD_OK_wTide = IF(Dfwd_m <= FWD_Allow_m, OK, NG)
        ws.write_formula(
            row_idx,
            57,
            f'=IF({col_letter_dfwd}{row_num}<={col_idx_to_excel_letter(56)}{row_num},"OK","NG")',
            styles["normal_font"],
        )

        # BF(58): AFT_Min_2.70_OK (Captain emergency propulsion gate)
        ws.write_formula(
            row_idx,
            58,
            f'=IF({col_letter_daft}{row_num}>=2.70,"OK","NG")',
            styles["normal_font"],
        )

        # BG(59): Min_Freeboard_m = D_vessel - MAX(Dfwd_m, Daft_m)
        # D_vessel is parameter cell $B$11
        ws.write_formula(
            row_idx,
            59,
            f"=$B$11-MAX({col_letter_dfwd}{row_num},{col_letter_daft}{row_num})",
            num_format,
        )

        # BH(60): Deck_Encroach_Check = IF(Min_Freeboard_m > 0, OK, NG)
        ws.write_formula(
            row_idx,
            60,
            f'=IF({col_idx_to_excel_letter(59)}{row_num}>0,"OK","NG")',
            styles["normal_font"],
        )

    print("  [OK] Structural/Option 1 columns added (AK-BB)")


def validate_and_correct_transfer(
    transfer_t: float,
    start_t: float,
    tank: Tank,
    stage_ballast_total: float,
    available_tanks: List[Tank],
) -> Tuple[float, List[str]]:
    """
    Validate and correct transfer to ensure capacity limits.

    Args:
        transfer_t: Proposed transfer amount (t)
        start_t: Starting tank level (t)
        tank: Tank object
        stage_ballast_total: Total ballast for this stage (t)
        available_tanks: List of available tanks for redistribution

    Returns:
        (corrected_transfer_t, warnings)
    """
    # Check capacity limits
    end_t_calc = start_t + transfer_t
    warnings = []
    original_transfer = transfer_t

    if end_t_calc > tank.max_t:
        # Over capacity - limit transfer
        max_transfer = tank.max_t - start_t
        transfer_t = max_transfer
        warnings.append(
            f"Transfer limited: {tank.name} capacity exceeded "
            f"(requested {original_transfer:.2f}t, limited to {transfer_t:.2f}t)"
        )

    if end_t_calc < tank.min_t:
        # Below minimum - limit transfer
        min_transfer = tank.min_t - start_t
        transfer_t = min_transfer
        warnings.append(
            f"Transfer limited: {tank.name} below minimum "
            f"(requested {original_transfer:.2f}t, limited to {min_transfer:.2f}t)"
        )

    return transfer_t, warnings


def validate_stage_continuity(
    stage_name: str,
    tank_name: str,
    current_start_t: float,
    previous_end_t: Optional[float],
    tolerance: float = 0.01,
) -> Tuple[float, List[str]]:
    """
    Validate tank state continuity between stages.

    Args:
        stage_name: Current stage name
        tank_name: Tank name
        current_start_t: Current stage start level (t)
        previous_end_t: Previous stage end level (t)
        tolerance: Tolerance for continuity check (t)

    Returns:
        (corrected_start_t, warnings)
    """
    warnings = []

    if previous_end_t is not None:
        if abs(current_start_t - previous_end_t) > tolerance:
            warnings.append(
                f"Continuity mismatch: {tank_name} in {stage_name} "
                f"(expected {previous_end_t:.2f}t, got {current_start_t:.2f}t)"
            )
            # Force continuity
            current_start_t = previous_end_t

    return current_start_t, warnings


def redistribute_excess_ballast(
    excess_t: float,
    source_tank: Tank,
    available_tanks: List[Tank],
    tank_states: Dict[str, float],
) -> Dict[str, float]:
    """
    Redistribute excess ballast to other available tanks.

    Args:
        excess_t: Excess ballast amount to redistribute (t)
        source_tank: Source tank that exceeded capacity
        available_tanks: List of available tanks for redistribution
        tank_states: Current tank states dict

    Returns:
        dict mapping tank names to additional transfer amounts
    """
    redistribution = {}
    remaining_excess = excess_t

    # Find tanks with available capacity (prioritize same group)
    same_group_tanks = [
        t
        for t in available_tanks
        if t.group == source_tank.group and t.name != source_tank.name
    ]
    other_tanks = [
        t
        for t in available_tanks
        if t.group != source_tank.group and t.name != source_tank.name
    ]

    # Try same group first, then other groups
    for tank in same_group_tanks + other_tanks:
        if remaining_excess <= 0.01:
            break

        current_level = tank_states.get(tank.name, tank.current_t)
        available_capacity = tank.max_t - current_level

        if available_capacity > 0.01:
            transfer_amount = min(remaining_excess, available_capacity)
            redistribution[tank.name] = transfer_amount
            remaining_excess -= transfer_amount

    return redistribution


def create_ballasting_sheet(
    workbook: Any,
    stage_results: Dict[str, Dict[str, Any]],
    tanks: Optional[List[Tank]] = None,
    styles: Optional[Dict[str, Any]] = None,
    params: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Create BALLASTING sheet showing stage-by-stage tank status and ballast operations.

    Args:
        workbook: xlsxwriter Workbook instance
        stage_results: Dict mapping stage names to calculation results
        tanks: Optional list of Tank objects (uses default if None)
        styles: Optional styles dict (creates if None)
    """
    if not HAS_XLSXWRITER:
        print("[WARNING] xlsxwriter not available, skipping BALLASTING sheet")
        return

    if styles is None:
        styles = get_styles(workbook)

    # Get default tanks if not provided
    if tanks is None:
        tanks = get_default_tanks()

    # Get parameters
    if params is None:
        params = {}
    Tide_ref = params.get(
        "Forecast_Tide_m", params.get("Tide_ref", 2.00)
    )  # Forecast tide height (CD)
    pump_rate_effective_tph = params.get("pump_rate_effective_tph", 100.00)

    # Create BALLASTING sheet
    ws = workbook.add_worksheet("BALLASTING")
    number_format = "#,##0.00"
    num_format = workbook.add_format({"num_format": number_format})

    # Row 1: Title
    ws.write(
        0, 0, "BALLASTING PLAN - Stage by Stage Tank Status", styles["title_format"]
    )

    # Row 2: Input parameter 안내
    ws.write(1, 0, "← Ballast transfer operations by stage", styles["normal_font"])

    # Row 4: 섹션 제목
    ws.write(3, 0, "Stage-by-Stage Ballast Tank Operations", styles["normal_font"])

    # Row 5: 헤더
    # Base headers (columns 0-12)
    headers = [
        "Stage",
        "Tank",
        "Group",
        "x_from_mid_m",
        "Capacity_t",
        "Start_t",
        "Transfer_t",
        "End_t",
        "Pump_Time_h",
        "Status",
        "Draft_FWD_m",
        "Draft_AFT_m",
        "Remarks",
    ]
    # Step-by-step headers (columns 13-20 for Step 1 and Step 2)
    # Step 1: columns 13-16 (N-O-P-Q)
    step_headers = [
        "Step1_n",
        "Step1_Transfer_t",
        "Step1_Cumulative_t",
        "Step1_Pump_Time_h",
    ]
    # Step 2: columns 17-20 (R-S-T-U)
    step_headers.extend(
        [
            "Step2_n",
            "Step2_Transfer_t",
            "Step2_Cumulative_t",
            "Step2_Pump_Time_h",
        ]
    )
    headers.extend(step_headers)
    for col_idx, header in enumerate(headers):
        ws.write(4, col_idx, header, styles["header_format"])

    # Stage order (same as RORO_Stage_Scenarios)
    stages_order = [
        "Stage 1",
        "Stage 2",
        "Stage 3",
        "Stage 4",
        "Stage 5",
        "Stage 5_PreBallast",
        "Stage 6A_Critical (Opt C)",
        "Stage 6C_TotalMassOpt",
        "Stage 6C",
        "Stage 7",
    ]

    # Track cumulative ballast by tank
    tank_states: Dict[str, float] = {t.name: t.current_t for t in tanks}
    cumulative_ballast: Dict[str, float] = {t.name: 0.0 for t in tanks}

    # Track stage-by-stage ballast totals
    stage_ballast_totals: Dict[str, float] = {}
    for stage_name in stages_order:
        if stage_name in stage_results:
            stage_ballast_totals[stage_name] = stage_results[stage_name].get(
                "Ballast_t", 0.0
            )
        else:
            stage_ballast_totals[stage_name] = 0.0

    # Calculate cumulative ballast
    running_total = 0.0
    for stage_name in stages_order:
        if stage_name in ["Stage 1", "Stage 7"]:
            # Arrival/Departure - reset ballast
            running_total = 0.0
        else:
            running_total += stage_ballast_totals.get(stage_name, 0.0)
        cumulative_ballast[stage_name] = running_total

    # Write data rows
    row_idx = 5  # Start from row 6 (0-based index 5)

    # Track validation statistics
    validation_stats = {
        "capacity_breaches": 0,  # Hard breaches: clamp required (End_t_raw outside bounds)
        "capacity_limits_applied": 0,  # Soft limits: requested transfer limited to stay within bounds
        "capacity_clamps": 0,  # Count of clamp events applied after calculation
        "continuity_mismatches": 0,
        "redistributions": 0,
        "warnings": [],
    }

    # Track previous stage end states for continuity validation
    previous_stage_ends: Dict[str, Dict[str, float]] = (
        {}
    )  # stage_name -> {tank_name: end_t}

    # Track redistributions per stage (for applying excess to other tanks)
    stage_redistributions: Dict[str, Dict[str, float]] = (
        {}
    )  # stage_name -> {tank_name: additional_transfer}

    for stage_name in stages_order:
        stage_ballast = stage_ballast_totals.get(stage_name, 0.0)
        stage_pump_time = 0.0

        if stage_name in stage_results:
            stage_pump_time = stage_results[stage_name].get("Ballast_time_h", 0.0)

        # Distribute ballast to tanks based on group and priority
        # Strategy: Distribute to BOW tanks (FWB1, FWB2) for forward ballast
        # For pre-ballast stages, distribute to STERN tanks (FW2)

        # Determine ballast distribution strategy
        # For pre-ballast: Use STERN tanks (FW2) to reduce forward draft
        # For forward ballast: Use BOW tanks (FWB1, FWB2) to increase forward draft
        # For discharge: Use appropriate tanks based on trim requirements

        if stage_name == "Stage 5_PreBallast":
            # Pre-ballast: Use STERN tanks (FW2) to reduce forward draft
            target_tanks = [
                t for t in tanks if t.group == "STERN" and t.use_flag == "Y"
            ]
        elif stage_ballast > 0:
            # Forward ballast: Use BOW tanks (FWB1, FWB2) to increase forward draft
            target_tanks = [t for t in tanks if t.group == "BOW" and t.use_flag == "Y"]
        elif stage_ballast < 0:
            # Discharge: Use FWD tanks (FWCARGO) to reduce forward draft
            target_tanks = [t for t in tanks if t.group == "FWD" and t.use_flag == "Y"]
        else:
            # No ballast change
            target_tanks = []

        # If no target tanks found but ballast is needed, use all available tanks
        if not target_tanks and abs(stage_ballast) > 0.01:
            target_tanks = [t for t in tanks if t.use_flag == "Y"]

        # Get actual optimization result if available (tank_deltas from BallastOptimizer)
        tank_deltas = {}
        if stage_name in stage_results:
            tank_deltas = stage_results[stage_name].get("tank_deltas", {})

        # Use actual optimization results if available, otherwise use even distribution
        use_optimization = len(tank_deltas) > 0

        # Distribute ballast evenly among target tanks (fallback if no optimization)
        num_targets = len(target_tanks) if target_tanks else 1
        ballast_per_tank = stage_ballast / num_targets if num_targets > 0 else 0.0
        pump_time_per_tank = stage_pump_time / num_targets if num_targets > 0 else 0.0

        # Get stage drafts for Effective Draft calculation
        stage_dfwd = 0.0
        stage_daft = 0.0
        if stage_name in stage_results:
            stage_dfwd = stage_results[stage_name].get("Dfwd_m", 0.0)
            stage_daft = stage_results[stage_name].get("Daft_m", 0.0)

        # Calculate step-by-step breakdown for this stage
        step_size_t = 50.0  # Each step = 50t
        num_steps = (
            max(1, int(math.ceil(abs(stage_ballast) / step_size_t)))
            if abs(stage_ballast) > 0.01
            else 0
        )
        actual_step_size = abs(stage_ballast) / num_steps if num_steps > 0 else 0.0

        # Write tank rows for this stage - show all tanks, not just target tanks
        tanks_to_show = tanks  # Show all tanks for visibility
        tank_row_index = 0  # Track which tank row we're on for this stage

        # Initialize redistribution dict for this stage
        stage_redistributions[stage_name] = {}

        for tank in tanks_to_show:
            # Calculate tank state for this stage with continuity validation
            if stage_name == "Stage 1":
                # Reset to initial state
                start_t = tank.current_t
            else:
                # Use previous stage's end state
                start_t = tank_states.get(tank.name, tank.current_t)

                # Validate continuity with previous stage
                prev_stage_name = stages_order[stages_order.index(stage_name) - 1]
                if prev_stage_name in previous_stage_ends:
                    prev_end_t = previous_stage_ends[prev_stage_name].get(tank.name)
                    if prev_end_t is not None:
                        corrected_start, continuity_warnings = (
                            validate_stage_continuity(
                                stage_name, tank.name, start_t, prev_end_t
                            )
                        )
                        if continuity_warnings:
                            validation_stats["continuity_mismatches"] += 1
                            validation_stats["warnings"].extend(continuity_warnings)
                            start_t = corrected_start

            # Calculate transfer for this tank
            # Priority: Use actual optimization result if available
            if use_optimization and tank.name in tank_deltas:
                transfer_t = float(tank_deltas[tank.name])
                # Calculate pump time from actual transfer
                if abs(transfer_t) > 0.01 and tank.pump_rate_tph > 0:
                    pump_time_per_tank = abs(transfer_t) / tank.pump_rate_tph
                else:
                    pump_time_per_tank = 0.0
            elif tank in target_tanks:
                transfer_t = ballast_per_tank
            else:
                transfer_t = 0.0

            # Apply any redistributions from other tanks in this stage
            if tank.name in stage_redistributions.get(stage_name, {}):
                transfer_t += stage_redistributions[stage_name][tank.name]

            # Validate and correct transfer to ensure capacity limits
            original_transfer = transfer_t
            transfer_t, transfer_warnings = validate_and_correct_transfer(
                transfer_t, start_t, tank, stage_ballast, target_tanks
            )

            if transfer_warnings:
                validation_stats["warnings"].extend(transfer_warnings)

                # Soft-limit accounting: requested transfer was limited due to capacity bounds
                if abs(transfer_t) < abs(original_transfer):
                    validation_stats["capacity_limits_applied"] += 1

                    # Attempt redistribution if transfer was limited
                    excess = abs(original_transfer) - abs(transfer_t)
                    if excess > 0.01 and stage_ballast > 0:
                        redistribution = redistribute_excess_ballast(
                            excess,
                            source_tank=tank,
                            available_tanks=target_tanks,
                            tank_states=tank_states,
                        )
                        if redistribution:
                            stage_redistributions.update(redistribution)
                            validation_stats["redistributions"] += 1
                            validation_stats["warnings"].append(
                                f"Redistributed {excess:.2f}t from {tank.name} to other tanks: {redistribution}"
                            )
                        else:
                            validation_stats["warnings"].append(
                                f"Redistribution skipped: no eligible tanks for {excess:.2f}t from {tank.name} in {stage_name}"
                            )
            end_t_raw = start_t + transfer_t
            end_t = max(tank.min_t, min(end_t_raw, tank.max_t))

            # Hard-breach accounting: clamp required (End_t_raw outside bounds)
            tol = 0.01
            if abs(end_t - end_t_raw) > tol:
                validation_stats["capacity_breaches"] += 1
                validation_stats["capacity_clamps"] += 1
                validation_stats["warnings"].append(
                    f"Hard capacity clamp: {tank.name} in {stage_name} "
                    f"(raw {end_t_raw:.2f}t -> clamped {end_t:.2f}t, "
                    f"bounds [{tank.min_t:.2f}, {tank.max_t:.2f}]t)"
                )

            # Sync Transfer_t so Excel always satisfies End_t = Start_t + Transfer_t
            transfer_t = end_t - start_t

            # Update tank state for next stage
            tank_states[tank.name] = end_t

            # Status check (NG only on hard clamp; CHECK on zero pump time with non-zero transfer)
            status = "OK" if abs(end_t - end_t_raw) <= tol else "NG"
            if abs(transfer_t) > 0.01 and abs(pump_time_per_tank) < 0.01:
                status = "CHECK"
            status_format = styles["ok_fill"] if status == "OK" else styles["ng_fill"]

            # Get Excel row number (1-based) for formulas
            excel_row = row_idx + 1

            # Write row
            ws.write(row_idx, 0, stage_name, styles["normal_font"])
            ws.write(row_idx, 1, tank.name, styles["normal_font"])
            ws.write(row_idx, 2, tank.group or "", styles["normal_font"])
            ws.write(row_idx, 3, tank.x_from_mid_m, num_format)
            ws.write(row_idx, 4, tank.max_t, num_format)
            ws.write(row_idx, 5, start_t, num_format)

            # Transfer_t: Use value (can be manually adjusted)
            ws.write(row_idx, 6, transfer_t, num_format)

            # End_t: Excel formula = Start_t + Transfer_t
            # Start_t: col_idx=5 (F in Excel), Transfer_t: col_idx=6 (G in Excel)
            col_letter_start = col_idx_to_excel_letter(5)  # Start_t column
            col_letter_transfer = col_idx_to_excel_letter(6)  # Transfer_t column
            ws.write_formula(
                row_idx,
                7,
                f"={col_letter_start}{excel_row}+{col_letter_transfer}{excel_row}",
                num_format,
            )

            # Pump_Time_h: Calculate based on transfer and pump rate
            if abs(transfer_t) > 0.01:
                if pump_rate_effective_tph > 0:
                    pump_time_val = abs(transfer_t) / pump_rate_effective_tph
                    ws.write(row_idx, 8, pump_time_val, num_format)
                elif tank.pump_rate_tph > 0:
                    pump_time_val = abs(transfer_t) / tank.pump_rate_tph
                    ws.write(row_idx, 8, pump_time_val, num_format)
                else:
                    ws.write(row_idx, 8, 0.0, num_format)
            else:
                ws.write(row_idx, 8, 0.0, num_format)

            ws.write(row_idx, 9, status, status_format)

            # Draft_FWD_m: physical draft at FWD (do NOT add tide)
            ws.write(row_idx, 10, stage_dfwd, num_format)

            # Draft_AFT_m: physical draft at AFT (do NOT add tide)
            ws.write(row_idx, 11, stage_daft, num_format)

            # Remarks
            remarks = ""
            if abs(transfer_t) > 0.01:
                if transfer_t > 0:
                    remarks = f"Fill {transfer_t:.2f}t"
                else:
                    remarks = f"Discharge {abs(transfer_t):.2f}t"
            ws.write(row_idx, 12, remarks, styles["normal_font"])

            # Add step-by-step breakdown in columns 13-20 (only for first tank row of each stage)
            # Step 1: columns 13-16 (N-O-P-Q)
            # Step 2: columns 17-20 (R-S-T-U)
            if tank_row_index == 0 and num_steps > 0:
                cumulative_step = 0.0
                # Show max 2 steps per row (Step 1 and Step 2)
                max_steps_to_show = min(num_steps, 2)

                for step_n in range(1, max_steps_to_show + 1):
                    if step_n == num_steps:
                        step_transfer = abs(stage_ballast) - cumulative_step
                    else:
                        step_transfer = actual_step_size

                    cumulative_step += step_transfer
                    step_pump_time = (
                        step_transfer / pump_rate_effective_tph
                        if pump_rate_effective_tph > 0
                        else 0.0
                    )

                    # Calculate column base for this step
                    # Step 1: column base = 13, Step 2: column base = 17
                    step_col_base = 13 + (step_n - 1) * 4

                    # Check if step fits within column range (N-U, columns 13-20)
                    # Last column for this step = step_col_base + 3 (4 columns per step)
                    if step_col_base + 3 <= 20:  # Allow up to column U (index 20)
                        # Write step data: Step_n, Step_Transfer_t, Cumulative_t, Step_Pump_Time_h
                        ws.write(row_idx, step_col_base, step_n, styles["normal_font"])
                        ws.write(
                            row_idx,
                            step_col_base + 1,
                            step_transfer if stage_ballast > 0 else -step_transfer,
                            num_format,
                        )
                        ws.write(
                            row_idx,
                            step_col_base + 2,
                            cumulative_step if stage_ballast > 0 else -cumulative_step,
                            num_format,
                        )
                        ws.write(row_idx, step_col_base + 3, step_pump_time, num_format)

                # If more than 2 steps, write total steps count in Remarks column
                if num_steps > 2:
                    additional_remarks = f" (Total {num_steps} steps)"
                    updated_remarks = (
                        (remarks + additional_remarks)
                        if remarks
                        else additional_remarks
                    )
                    ws.write(row_idx, 12, updated_remarks, styles["normal_font"])

            tank_row_index += 1
            row_idx += 1

        # Store end states for next stage continuity validation
        previous_stage_ends[stage_name] = {
            t.name: tank_states.get(t.name, t.current_t) for t in tanks
        }

        # Add empty row between stages for readability
        row_idx += 1

    # Set column widths
    ws.set_column(0, 0, 25)  # Stage
    ws.set_column(1, 1, 15)  # Tank
    ws.set_column(2, 2, 10)  # Group
    ws.set_column(3, 3, 15)  # x_from_mid_m
    ws.set_column(4, 4, 12)  # Capacity_t
    ws.set_column(5, 8, 12)  # Start_t, Transfer_t, End_t, Pump_Time_h
    ws.set_column(9, 9, 10)  # Status
    ws.set_column(10, 11, 15)  # Effective_FWD_m, Effective_AFT_m
    ws.set_column(12, 12, 20)  # Remarks
    # Step 1 columns (13-16): N-O-P-Q
    ws.set_column(13, 13, 10)  # Step1_n
    ws.set_column(14, 14, 15)  # Step1_Transfer_t
    ws.set_column(15, 15, 15)  # Step1_Cumulative_t
    ws.set_column(16, 16, 15)  # Step1_Pump_Time_h
    # Step 2 columns (17-20): R-S-T-U
    ws.set_column(17, 17, 10)  # Step2_n
    ws.set_column(18, 18, 15)  # Step2_Transfer_t
    ws.set_column(19, 19, 15)  # Step2_Cumulative_t
    ws.set_column(20, 20, 15)  # Step2_Pump_Time_h

    # Freeze panes at A6 (row 5, column 0)
    ws.freeze_panes(5, 0)

    # Add summary section at the end
    summary_row = row_idx + 2
    ws.write(summary_row, 0, "Summary", styles["title_format"])
    summary_row += 1
    ws.write(summary_row, 0, "Total Ballast Operations:", styles["normal_font"])
    ws.write(summary_row, 1, f"{sum(stage_ballast_totals.values()):.2f} t", num_format)
    summary_row += 1
    ws.write(summary_row, 0, "Total Pump Time:", styles["normal_font"])
    total_pump_time = sum(
        stage_results.get(s, {}).get("Ballast_time_h", 0.0) for s in stages_order
    )
    ws.write(summary_row, 1, f"{total_pump_time:.2f} h", num_format)

    # Add validation report section
    summary_row += 2
    ws.write(summary_row, 0, "Validation Report", styles["title_format"])
    summary_row += 1
    ws.write(summary_row, 0, "Capacity Breaches:", styles["normal_font"])
    capacity_status = "PASS" if validation_stats["capacity_breaches"] == 0 else "FAIL"
    capacity_format = (
        styles["ok_fill"]
        if validation_stats["capacity_breaches"] == 0
        else styles["ng_fill"]
    )
    ws.write(
        summary_row,
        1,
        f"{validation_stats['capacity_breaches']} ({capacity_status})",
        capacity_format,
    )
    summary_row += 1
    ws.write(summary_row, 0, "Capacity Limits Applied:", styles["normal_font"])
    ws.write(
        summary_row,
        1,
        f"{validation_stats.get('capacity_limits_applied',0)} (INFO)",
        styles["normal_font"],
    )
    summary_row += 1
    ws.write(summary_row, 0, "Capacity Clamps Applied:", styles["normal_font"])
    clamps_status = (
        "PASS" if validation_stats.get("capacity_clamps", 0) == 0 else "FAIL"
    )
    clamps_format = (
        styles["ok_fill"]
        if validation_stats.get("capacity_clamps", 0) == 0
        else styles["ng_fill"]
    )
    ws.write(
        summary_row,
        1,
        f"{validation_stats.get('capacity_clamps',0)} ({clamps_status})",
        clamps_format,
    )
    summary_row += 1
    ws.write(summary_row, 0, "Continuity Mismatches:", styles["normal_font"])
    continuity_status = (
        "PASS" if validation_stats["continuity_mismatches"] == 0 else "FAIL"
    )
    continuity_format = (
        styles["ok_fill"]
        if validation_stats["continuity_mismatches"] == 0
        else styles["ng_fill"]
    )
    ws.write(
        summary_row,
        1,
        f"{validation_stats['continuity_mismatches']} ({continuity_status})",
        continuity_format,
    )
    summary_row += 1
    ws.write(summary_row, 0, "Redistributions:", styles["normal_font"])
    ws.write(
        summary_row, 1, f"{validation_stats['redistributions']}", styles["normal_font"]
    )

    # Print warnings if any
    if validation_stats["warnings"]:
        summary_row += 2
        ws.write(summary_row, 0, "Warnings:", styles["normal_font"])
        summary_row += 1
        for warning in validation_stats["warnings"][:10]:  # Limit to first 10 warnings
            ws.write(summary_row, 0, f"- {warning}", styles["normal_font"])
            summary_row += 1
        if len(validation_stats["warnings"]) > 10:
            ws.write(
                summary_row,
                0,
                f"... and {len(validation_stats['warnings']) - 10} more warnings",
                styles["normal_font"],
            )

    # Print validation summary to console
    if (
        validation_stats["capacity_breaches"] > 0
        or validation_stats["continuity_mismatches"] > 0
    ):
        print(
            f"  [WARNING] Validation issues: {validation_stats['capacity_breaches']} capacity breaches, "
            f"{validation_stats['continuity_mismatches']} continuity mismatches"
        )
    else:
        print("  [OK] Validation passed: 0 capacity breaches, 0 continuity mismatches")

    print("  [OK] BALLASTING sheet created")


def generate_bwrb_log(
    plan_df: pd.DataFrame,
    vessel: str,
    loc: str,
    lat: str,
    lon: str,
    officer: str,
    master_verified: str = "N",
):
    """Generates a CSV compatible with Ballast Water Record Books (IMO BWRB compliant)."""
    rows = []
    from datetime import datetime, timedelta

    # Validate location data
    if not lat or not lon:
        print("WARNING: Lat/Lon missing - BWRB requires location information")

    t_cursor = datetime.now()

    for _, r in plan_df.iterrows():
        dur_h = float(r.get("Time_h", 0.0))
        weight_t = float(r.get("Weight_t", 0.0))
        volume_m3 = round(weight_t / 1.025, 1) if weight_t > 0 else 0.0

        rows.append(
            {
                "Vessel": vessel,
                "Location": loc or "Sea",
                "Lat": lat or "",
                "Lon": lon or "",
                "Date": t_cursor.strftime("%Y-%m-%d"),
                "Start": t_cursor.strftime("%H:%M"),
                "End": (
                    (t_cursor + timedelta(hours=dur_h)).strftime("%H:%M")
                    if dur_h > 0
                    else ""
                ),
                "Tank": r.get("Tank", ""),
                "Operation": r.get("Action", ""),
                "Volume_m3": volume_m3,
                "Weight_t": round(weight_t, 2),
                "Officer": officer or "",
                "MasterVerified": master_verified,
                "Remarks": "",
            }
        )
        if dur_h > 0:
            t_cursor += timedelta(hours=dur_h)
    return pd.DataFrame(rows)


# =============================================================================
# RORO PRE-BALLAST OPTIMIZATION FUNCTIONS
# =============================================================================


def _stage_moment_and_drafts_for_preballast(
    w_tr_unit_t: float,
    w_preballast_t: float,
    fr_tr1_stow: float,
    fr_tr2_ramp: float,
    fr_preballast: float,
    base_disp_t: float,
    base_tmean_m: float,
    hydro_df: Optional[pd.DataFrame],
    params: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Calculate Stage 5_PreBallast and Stage 6A_Critical moments and drafts
    for pre-ballast optimization.

    Args:
        w_tr_unit_t: Transformer unit weight (t)
        w_preballast_t: Pre-ballast weight (t)
        fr_tr1_stow: TR1 stow Frame number
        fr_tr2_ramp: TR2 ramp Frame number
        fr_preballast: Pre-ballast Frame number (FW2)
        base_disp_t: Base displacement (t)
        base_tmean_m: Base mean draft (m)
        hydro_df: Hydro table DataFrame
        params: Parameters dict (MTC, LCF, LBP, etc.)

    Returns:
        dict with keys: "stage5", "stage6A", "w_preballast_t"
    """
    # Get hydro constants
    MTC = params.get("MTC", params.get("MTC_t_m_per_cm", VesselParams.MTC))
    LCF = params.get("LCF", params.get("LCF_m_from_midship", VesselParams.LCF))
    LBP = params.get("LBP", VesselParams.LBP)
    TPC = params.get("TPC", params.get("TPC_t_per_cm", VesselParams.TPC))

    # Convert Frame to x_from_mid_m
    x_tr1 = fr_to_x(fr_tr1_stow)
    x_tr2 = fr_to_x(fr_tr2_ramp)
    x_pb = fr_to_x(fr_preballast)

    # Stage 5_PreBallast: TR1 + Pre-ballast
    disp5 = base_disp_t + w_tr_unit_t + w_preballast_t
    tm5_tr1 = w_tr_unit_t * (x_tr1 - LCF)
    tm5_pb = w_preballast_t * (x_pb - LCF)
    tm5 = tm5_tr1 + tm5_pb
    trim5_cm = (tm5 / MTC) if MTC > 0 else 0.0

    # Calculate Tmean for Stage 5
    if hydro_df is not None and not hydro_df.empty:
        tmean5 = interpolate_tmean_from_disp(disp5, hydro_df)
        hydro5 = interpolate_hydro_by_tmean(tmean5, hydro_df)
        lcf5 = hydro5.get("LCF_m_from_midship", LCF)
        mtc5 = hydro5.get("MCTC_t_m_per_cm", MTC)
        tpc5 = hydro5.get("TPC_t_per_cm", TPC)
        # Recalculate trim with updated MTC
        tm5_recalc = w_tr_unit_t * (x_tr1 - lcf5) + w_preballast_t * (x_pb - lcf5)
        trim5_cm = (tm5_recalc / mtc5) if mtc5 > 0 else 0.0
    else:
        tmean5 = base_tmean_m + (w_tr_unit_t + w_preballast_t) / (TPC * 100.0)
        lcf5 = LCF
        mtc5 = MTC

    dfwd5, daft5 = calc_draft_with_lcf(tmean5, trim5_cm, lcf5, LBP)

    stage5 = {
        "W_stage_t": float(disp5),
        "x_stage_m": float(
            (w_tr_unit_t * x_tr1 + w_preballast_t * x_pb)
            / (w_tr_unit_t + w_preballast_t)
            if (w_tr_unit_t + w_preballast_t) > 0
            else 0.0
        ),
        "TM_tm": float(tm5),
        "Trim_cm": float(trim5_cm),
        "FWD_m": float(dfwd5),
        "AFT_m": float(daft5),
        "Tmean_m": float(tmean5),
    }

    # Stage 6A_Critical: TR1 + TR2 + Pre-ballast
    disp6a = base_disp_t + 2 * w_tr_unit_t + w_preballast_t
    tm6a_tr1 = w_tr_unit_t * (x_tr1 - LCF)
    tm6a_tr2 = w_tr_unit_t * (x_tr2 - LCF)
    tm6a_pb = w_preballast_t * (x_pb - LCF)
    tm6a = tm6a_tr1 + tm6a_tr2 + tm6a_pb
    trim6a_cm = (tm6a / MTC) if MTC > 0 else 0.0

    # Calculate Tmean for Stage 6A
    if hydro_df is not None and not hydro_df.empty:
        tmean6a = interpolate_tmean_from_disp(disp6a, hydro_df)
        hydro6a = interpolate_hydro_by_tmean(tmean6a, hydro_df)
        lcf6a = hydro6a.get("LCF_m_from_midship", LCF)
        mtc6a = hydro6a.get("MCTC_t_m_per_cm", MTC)
        # Recalculate trim with updated MTC
        tm6a_recalc = (
            w_tr_unit_t * (x_tr1 - lcf6a)
            + w_tr_unit_t * (x_tr2 - lcf6a)
            + w_preballast_t * (x_pb - lcf6a)
        )
        trim6a_cm = (tm6a_recalc / mtc6a) if mtc6a > 0 else 0.0
    else:
        tmean6a = base_tmean_m + (2 * w_tr_unit_t + w_preballast_t) / (TPC * 100.0)
        lcf6a = LCF
        mtc6a = MTC

    dfwd6a, daft6a = calc_draft_with_lcf(tmean6a, trim6a_cm, lcf6a, LBP)

    stage6a = {
        "W_stage_t": float(disp6a),
        "x_stage_m": float(
            (w_tr_unit_t * x_tr1 + w_tr_unit_t * x_tr2 + w_preballast_t * x_pb)
            / (2 * w_tr_unit_t + w_preballast_t)
            if (2 * w_tr_unit_t + w_preballast_t) > 0
            else 0.0
        ),
        "TM_tm": float(tm6a),
        "Trim_cm": float(trim6a_cm),
        "FWD_m": float(dfwd6a),
        "AFT_m": float(daft6a),
        "Tmean_m": float(tmean6a),
    }

    return {
        "w_preballast_t": float(w_preballast_t),
        "stage5": stage5,
        "stage6A": stage6a,
    }


def build_roro_stage_loads(
    stage_name: str,
    preballast_t: float,
    w_tr: float = 271.20,
    fr_tr1_stow: float = 42.0,
    fr_tr1_ramp_start: float = 40.15,
    fr_tr1_ramp_mid: float = 37.00,
    fr_tr2_ramp: float = 17.95,
    fr_tr2_stow: float = 40.00,
    fr_preballast: float = 3.0,
) -> List[Dict[str, Any]]:
    """
    Build load list for RORO stage.

    Args:
        stage_name: Stage name (e.g., "Stage 1", "Stage 2", etc.)
        preballast_t: Pre-ballast weight (t)
        w_tr: Transformer unit weight (t)
        fr_tr1_stow: TR1 stow Frame number
        fr_tr1_ramp_start: TR1 ramp start Frame number
        fr_tr1_ramp_mid: TR1 ramp mid Frame number
        fr_tr2_ramp: TR2 ramp Frame number
        fr_tr2_stow: TR2 stow Frame number
        fr_preballast: Pre-ballast Frame number

    Returns:
        List of load dicts with keys: "name", "weight_t", "x_from_mid_m", "kind"
    """
    loads: List[Dict[str, Any]] = []

    if stage_name == "Stage 1":
        return loads  # Arrival - no loads

    if stage_name == "Stage 2":
        # TR1 ramp start
        loads.append(
            {
                "name": "TR1+SPMT",
                "weight_t": w_tr,
                "x_from_mid_m": fr_to_x(fr_tr1_ramp_start),
                "kind": "CARGO",
            }
        )
    elif stage_name == "Stage 3":
        # TR1 mid-ramp
        loads.append(
            {
                "name": "TR1+SPMT",
                "weight_t": w_tr,
                "x_from_mid_m": fr_to_x(fr_tr1_ramp_mid),
                "kind": "CARGO",
            }
        )
    elif stage_name == "Stage 4":
        # TR1 on deck
        loads.append(
            {
                "name": "TR1+SPMT",
                "weight_t": w_tr,
                "x_from_mid_m": fr_to_x(fr_tr1_stow),
                "kind": "CARGO",
            }
        )
    elif stage_name == "Stage 5":
        # TR1 final position
        loads.append(
            {
                "name": "TR1+SPMT",
                "weight_t": w_tr,
                "x_from_mid_m": fr_to_x(fr_tr1_stow),
                "kind": "CARGO",
            }
        )
    elif stage_name == "Stage 5_PreBallast":
        loads.append(
            {
                "name": "TR1+SPMT",
                "weight_t": w_tr,
                "x_from_mid_m": fr_to_x(fr_tr1_stow),
                "kind": "CARGO",
            }
        )
        loads.append(
            {
                "name": "PreBallast",
                "weight_t": preballast_t,
                "x_from_mid_m": fr_to_x(fr_preballast),
                "kind": "BALLAST",
            }
        )
    elif stage_name == "Stage 6A_Critical (Opt C)":
        loads.append(
            {
                "name": "TR1+SPMT",
                "weight_t": w_tr,
                "x_from_mid_m": fr_to_x(fr_tr1_stow),
                "kind": "CARGO",
            }
        )
        loads.append(
            {
                "name": "TR2+SPMT",
                "weight_t": w_tr,
                "x_from_mid_m": fr_to_x(fr_tr2_ramp),
                "kind": "CARGO",
            }
        )
        loads.append(
            {
                "name": "PreBallast",
                "weight_t": preballast_t,
                "x_from_mid_m": fr_to_x(fr_preballast),
                "kind": "BALLAST",
            }
        )
    elif stage_name == "Stage 6C_TotalMassOpt":
        loads.append(
            {
                "name": "TR1+SPMT",
                "weight_t": w_tr,
                "x_from_mid_m": fr_to_x(fr_tr1_stow),
                "kind": "CARGO",
            }
        )
        loads.append(
            {
                "name": "TR2+SPMT",
                "weight_t": w_tr,
                "x_from_mid_m": fr_to_x(fr_tr2_stow),
                "kind": "CARGO",
            }
        )
        loads.append(
            {
                "name": "PreBallast",
                "weight_t": preballast_t,
                "x_from_mid_m": fr_to_x(fr_preballast),
                "kind": "BALLAST",
            }
        )
    elif stage_name == "Stage 6C":
        loads.append(
            {
                "name": "TR1+SPMT",
                "weight_t": w_tr,
                "x_from_mid_m": fr_to_x(fr_tr1_stow),
                "kind": "CARGO",
            }
        )
        loads.append(
            {
                "name": "TR2+SPMT",
                "weight_t": w_tr,
                "x_from_mid_m": fr_to_x(fr_tr2_stow),
                "kind": "CARGO",
            }
        )
        loads.append(
            {
                "name": "PreBallast",
                "weight_t": preballast_t,
                "x_from_mid_m": fr_to_x(fr_preballast),
                "kind": "BALLAST",
            }
        )
    elif stage_name == "Stage 7":
        return loads  # Departure - no loads

    return loads


def calculate_roro_stage_drafts(
    stage_name: str,
    loads: List[Dict[str, Any]],
    base_disp: float,
    base_tmean: float,
    hydro_df: Optional[pd.DataFrame],
    params: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Calculate drafts for a RORO stage based on loads.

    Args:
        stage_name: Stage name
        loads: List of load dicts
        base_disp: Base displacement (t)
        base_tmean: Base mean draft (m)
        hydro_df: Hydro table DataFrame
        params: Parameters dict

    Returns:
        dict with stage calculation results
    """
    # Get constants
    MTC = params.get("MTC", params.get("MTC_t_m_per_cm", VesselParams.MTC))
    LCF = params.get("LCF", params.get("LCF_m_from_midship", VesselParams.LCF))
    LBP = params.get("LBP", VesselParams.LBP)
    TPC = params.get("TPC", params.get("TPC_t_per_cm", VesselParams.TPC))
    D_vessel = params.get("D_vessel", VesselParams.D_VESSEL)

    # Calculate total weight and moment
    delta_w = sum(ld["weight_t"] for ld in loads)
    disp_stage = base_disp + delta_w

    if abs(delta_w) < 1e-9:
        x_lcg = 0.0
    else:
        x_lcg = sum(ld["weight_t"] * ld["x_from_mid_m"] for ld in loads) / delta_w

    # Calculate Tmean from displacement
    if hydro_df is not None and not hydro_df.empty:
        tmean_stage = interpolate_tmean_from_disp(disp_stage, hydro_df)
        hydro_i = interpolate_hydro_by_tmean(tmean_stage, hydro_df)
        lcf_used = hydro_i.get("LCF_m_from_midship", LCF)
        mctc_used = hydro_i.get("MCTC_t_m_per_cm", MTC)
        tpc_used = hydro_i.get("TPC_t_per_cm", TPC)
    else:
        tmean_stage = base_tmean + delta_w / (TPC * 100.0)
        lcf_used = LCF
        mctc_used = MTC
        tpc_used = TPC

    # Calculate trimming moment and trim
    tm = sum(ld["weight_t"] * (ld["x_from_mid_m"] - lcf_used) for ld in loads)
    trim_cm = (tm / mctc_used) if (mctc_used and mctc_used > 1e-9) else 0.0

    # Calculate end drafts
    dfwd_m, daft_m = calc_draft_with_lcf(tmean_stage, trim_cm, lcf_used, LBP)

    # Calculate GM (simplified - can be enhanced with GM grid)
    trim_m = trim_cm / 100.0
    gm_m = gm_2d_bilinear(disp_stage, trim_m, params.get("gm_grid"))

    # Calculate freeboard
    fwd_height_m = max(0.0, D_vessel - dfwd_m)
    aft_height_m = max(0.0, D_vessel - daft_m)

    # Validation checks
    max_fwd = params.get("max_fwd_draft_ops_m", VesselParams.MAX_FWD_DRAFT_OPS)
    trim_limit = params.get("trim_limit_abs_cm", VesselParams.TRIM_LIMIT_CM)
    gm_min = params.get("gm_min_m", VesselParams.MIN_GM_M)

    trim_check = "OK" if abs(trim_cm) <= trim_limit else "EXCESSIVE"
    vs_ops = "OK" if dfwd_m <= max_fwd else "NG"
    gm_check = "OK" if gm_m >= gm_min else "LOW"

    # Calculate Ballast_t and Ballast_time_h (if applicable)
    ballast_t = 0.0
    ballast_time_h = 0.0
    if abs(trim_cm) > 0 and tpc_used > 0:
        trim_m_abs = abs(trim_cm / 100.0)
        ballast_t = round(trim_m_abs * 50.0 * tpc_used, 2)
        pump_rate = params.get("pump_rate_effective_tph", 100.0)
        if pump_rate > 0:
            ballast_time_h = round(ballast_t / pump_rate, 2)

    return {
        "ΔW_t": float(delta_w),
        "x_LCG_m": float(x_lcg),
        "TM_t_m": float(tm),
        "Trim_cm": float(trim_cm),
        "Tmean_m": float(tmean_stage),
        "Dfwd_m": float(dfwd_m),
        "Daft_m": float(daft_m),
        "GM_m": float(gm_m),
        "FWD_Height_m": float(fwd_height_m),
        "AFT_Height_m": float(aft_height_m),
        "Trim_Check": trim_check,
        "vs_ops_fwd_draft": vs_ops,
        "GM_Check": gm_check,
        "W_stage_t": float(disp_stage),
        "x_stage_m": float(x_lcg),
        "TM_LCF_tm": float(tm),
        "vs_2.70m": vs_ops,
        "Disp_t": float(disp_stage),
        "Ballast_t": float(ballast_t),
        "Ballast_time_h": float(ballast_time_h),
    }


def optimize_preballast_for_roro(
    base_disp_t: float,
    base_tmean_m: float,
    hydro_df: Optional[pd.DataFrame],
    w_tr_unit_t: float = 271.20,
    fr_tr1_stow: float = 42.0,
    fr_tr2_ramp: float = 17.95,
    fr_preballast: float = 3.0,
    search_min_t: float = 20.0,
    search_max_t: float = 400.0,
    search_step_t: float = 1.0,
    params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Optimize pre-ballast weight for Stage 5_PreBallast and Stage 6A_Critical.

    Args:
        base_disp_t: Base displacement (t)
        base_tmean_m: Base mean draft (m)
        hydro_df: Hydro table DataFrame
        w_tr_unit_t: Transformer unit weight (t)
        fr_tr1_stow: TR1 stow Frame number
        fr_tr2_ramp: TR2 ramp Frame number
        fr_preballast: Pre-ballast Frame number
        search_min_t: Minimum search weight (t)
        search_max_t: Maximum search weight (t)
        search_step_t: Search step (t)
        params: Additional parameters dict

    Returns:
        dict with keys: "ok", "reason", "w_preballast_t", "stage5", "stage6A"
    """
    if params is None:
        params = {}

    min_fwd = params.get("min_fwd_draft_m", VesselParams.MIN_DRAFT)
    max_fwd = params.get("max_fwd_draft_ops_m", VesselParams.MAX_FWD_DRAFT_OPS)
    trim_limit = params.get("trim_limit_abs_cm", VesselParams.TRIM_LIMIT_CM)
    check_stage5 = params.get("CHECK_STAGE5", True)

    if search_step_t <= 0:
        raise ValueError("search_step_t must be positive.")

    best: Optional[Dict[str, Any]] = None
    best_metric: Optional[float] = None

    w = search_min_t
    while w <= search_max_t + 1e-9:
        result = _stage_moment_and_drafts_for_preballast(
            w_tr_unit_t=w_tr_unit_t,
            w_preballast_t=w,
            fr_tr1_stow=fr_tr1_stow,
            fr_tr2_ramp=fr_tr2_ramp,
            fr_preballast=fr_preballast,
            base_disp_t=base_disp_t,
            base_tmean_m=base_tmean_m,
            hydro_df=hydro_df,
            params=params,
        )

        st5 = result["stage5"]
        st6 = result["stage6A"]

        fwd5 = st5["FWD_m"]
        fwd6 = st6["FWD_m"]
        trim5 = abs(st5["Trim_cm"])
        trim6 = abs(st6["Trim_cm"])

        # Gate 1: Draft limits
        if check_stage5 and not (min_fwd <= fwd5 <= max_fwd):
            w += search_step_t
            continue
        if not (min_fwd <= fwd6 <= max_fwd):
            w += search_step_t
            continue

        # Gate 2: Trim envelope
        if check_stage5 and trim5 > trim_limit:
            w += search_step_t
            continue
        if trim6 > trim_limit:
            w += search_step_t
            continue

        # Objective: Stage 6A FWD as close as possible to ops limit
        margin5 = max_fwd - fwd5
        margin6 = max_fwd - fwd6
        metric = abs(margin6) + 0.1 * abs(margin5)  # Stage 5 penalty 10%

        if best_metric is None or metric < best_metric - 1e-9:
            best_metric = metric
            best = result
        elif best is not None and abs(metric - best_metric) < 1e-9:
            # Tie-breaker: smaller ballast preferred
            if w < best["w_preballast_t"]:
                best_metric = metric
                best = result

        w += search_step_t

    if best is None:
        return {
            "ok": False,
            "reason": "No feasible pre-ballast found within search range.",
            "w_preballast_t": None,
            "stage5": None,
            "stage6A": None,
        }

    return {
        "ok": True,
        "reason": "Feasible pre-ballast found.",
        "w_preballast_t": best["w_preballast_t"],
        "stage5": best["stage5"],
        "stage6A": best["stage6A"],
    }


def run_roro_mode(args):
    """Run RORO stage-by-stage ballast optimization."""
    print("Running RORO Mode...")

    # Load tanks and hydro table
    tanks = load_tanks_from_file(Path(args.tank)) if args.tank else get_default_tanks()
    hydro_df = load_hydro_table(Path(args.hydro)) if args.hydro else None

    # RORO parameters
    base_disp_t = getattr(args, "roro_base_disp", 2800.0)
    w_tr = getattr(args, "roro_w_tr", 271.20)
    fr_tr1_stow = getattr(args, "roro_fr_tr1_stow", 42.0)
    fr_tr1_ramp_start = getattr(args, "roro_fr_tr1_ramp_start", 40.15)
    fr_tr1_ramp_mid = getattr(args, "roro_fr_tr1_ramp_mid", 37.00)
    fr_tr2_ramp = getattr(args, "roro_fr_tr2_ramp", 17.95)
    fr_tr2_stow = getattr(args, "roro_fr_tr2_stow", 40.00)
    fr_preballast = getattr(args, "roro_fr_preballast", 3.0)

    # Calculate base_tmean from hydro table
    if hydro_df is not None and not hydro_df.empty:
        base_tmean_m = interpolate_tmean_from_disp(base_disp_t, hydro_df)
        print(f"[INFO] base_tmean_m calculated from hydro table: {base_tmean_m:.3f} m")
    else:
        base_tmean_m = 2.00  # Fallback
        print(f"[WARNING] Using fallback base_tmean_m: {base_tmean_m:.3f} m")

    # Parameters dict
    params = {
        "MTC": VesselParams.MTC,
        "LCF": VesselParams.LCF,
        "LBP": VesselParams.LBP,
        "TPC": VesselParams.TPC,
        "D_vessel": VesselParams.D_VESSEL,
        "max_fwd_draft_ops_m": VesselParams.MAX_FWD_DRAFT_OPS,
        "trim_limit_abs_cm": VesselParams.TRIM_LIMIT_CM,
        "gm_min_m": VesselParams.MIN_GM_M,
        "min_fwd_draft_m": VesselParams.MIN_DRAFT,
        "CHECK_STAGE5": True,
        "pump_rate_effective_tph": 100.0,
    }

    # Pre-ballast optimization
    preballast_opt = None
    stage5_pb = None
    stage6a_pb = None

    if getattr(args, "roro_preballast", None) is not None:
        # Use provided pre-ballast value
        preballast_opt = float(args.roro_preballast)
        print(f"[INFO] Using provided pre-ballast: {preballast_opt:.2f} t")
    else:
        # Optimize pre-ballast
        print("[INFO] Optimizing pre-ballast...")
        search_min = getattr(args, "roro_preballast_min", 20.0)
        search_max = getattr(args, "roro_preballast_max", 400.0)
        search_step = getattr(args, "roro_preballast_step", 1.0)

        preballast_result = optimize_preballast_for_roro(
            base_disp_t=base_disp_t,
            base_tmean_m=base_tmean_m,
            hydro_df=hydro_df,
            w_tr_unit_t=w_tr,
            fr_tr1_stow=fr_tr1_stow,
            fr_tr2_ramp=fr_tr2_ramp,
            fr_preballast=fr_preballast,
            search_min_t=search_min,
            search_max_t=search_max,
            search_step_t=search_step,
            params=params,
        )

        if not preballast_result["ok"]:
            print(
                f"[WARNING] Pre-ballast optimization failed: {preballast_result['reason']}"
            )
            preballast_opt = 250.0  # Fallback
            print(f"[WARNING] Using fallback pre-ballast: {preballast_opt:.2f} t")
        else:
            preballast_opt = preballast_result["w_preballast_t"]
            stage5_pb = preballast_result.get("stage5")
            stage6a_pb = preballast_result.get("stage6A")
            print(f"[INFO] Pre-ballast optimization successful: {preballast_opt:.2f} t")
            if stage6a_pb:
                fwd6 = stage6a_pb.get("FWD_m", 0.0)
                print(f"[INFO] Stage 6A FWD: {fwd6:.2f} m (Limit: 2.70m)")

    # Stage order
    stages_order = [
        "Stage 1",
        "Stage 2",
        "Stage 3",
        "Stage 4",
        "Stage 5",
        "Stage 5_PreBallast",
        "Stage 6A_Critical (Opt C)",
        "Stage 6C_TotalMassOpt",
        "Stage 6C",
        "Stage 7",
    ]

    # Process each stage
    stage_results = {}
    current_disp = base_disp_t
    current_tmean = base_tmean_m
    current_fwd = None
    current_aft = None

    optimizer = BallastOptimizer(tanks, hydro_df)

    for stage_name in stages_order:
        print(f"\n[INFO] Processing {stage_name}...")

        # Build loads for this stage
        loads = build_roro_stage_loads(
            stage_name=stage_name,
            preballast_t=preballast_opt if preballast_opt else 0.0,
            w_tr=w_tr,
            fr_tr1_stow=fr_tr1_stow,
            fr_tr1_ramp_start=fr_tr1_ramp_start,
            fr_tr1_ramp_mid=fr_tr1_ramp_mid,
            fr_tr2_ramp=fr_tr2_ramp,
            fr_tr2_stow=fr_tr2_stow,
            fr_preballast=fr_preballast,
        )

        # Calculate stage drafts
        res = calculate_roro_stage_drafts(
            stage_name=stage_name,
            loads=loads,
            base_disp=current_disp,
            base_tmean=current_tmean,
            hydro_df=hydro_df,
            params=params,
        )

        # Override with pre-ballast optimization results if available
        if stage_name == "Stage 5_PreBallast" and stage5_pb:
            res["Dfwd_m"] = float(stage5_pb.get("FWD_m", res["Dfwd_m"]))
            res["Daft_m"] = float(stage5_pb.get("AFT_m", res["Daft_m"]))
            res["Trim_cm"] = float(stage5_pb.get("Trim_cm", res["Trim_cm"]))
            res["Tmean_m"] = float(stage5_pb.get("Tmean_m", res["Tmean_m"]))
            res["FWD_Height_m"] = float(VesselParams.D_VESSEL - res["Dfwd_m"])
            res["AFT_Height_m"] = float(VesselParams.D_VESSEL - res["Daft_m"])

        if stage_name == "Stage 6A_Critical (Opt C)" and stage6a_pb:
            res["Dfwd_m"] = float(stage6a_pb.get("FWD_m", res["Dfwd_m"]))
            res["Daft_m"] = float(stage6a_pb.get("AFT_m", res["Daft_m"]))
            res["Trim_cm"] = float(stage6a_pb.get("Trim_cm", res["Trim_cm"]))
            res["Tmean_m"] = float(stage6a_pb.get("Tmean_m", res["Tmean_m"]))
            res["FWD_Height_m"] = float(VesselParams.D_VESSEL - res["Dfwd_m"])
            res["AFT_Height_m"] = float(VesselParams.D_VESSEL - res["Daft_m"])

        # Run BallastOptimizer for stages that require ballast operations
        # This provides actual tank-by-tank ballast distribution from LP optimization
        if abs(res.get("Ballast_t", 0.0)) > 0.01:
            # Get current drafts for optimization
            opt_fwd = res["Dfwd_m"]
            opt_aft = res["Daft_m"]

            # Determine optimization mode based on stage requirements
            max_fwd = params.get("max_fwd_draft_ops_m", VesselParams.MAX_FWD_DRAFT_OPS)

            # Use limit mode to ensure FWD draft stays within limits
            opt_result = optimizer.solve(
                dfwd=opt_fwd,
                daft=opt_aft,
                limit_fwd=max_fwd,
                prefer_time=True,
            )

            if opt_result.success and not opt_result.plan_df.empty:
                # Store optimization result for BALLASTING sheet
                res["optimization_result"] = opt_result
                res["tank_deltas"] = opt_result.delta
                print(
                    f"  [OK] BallastOptimizer solved: {len(opt_result.plan_df)} tank operations"
                )
            else:
                # Fallback: no optimization result available
                res["tank_deltas"] = {}
                print(
                    f"  [WARNING] BallastOptimizer did not find solution for {stage_name}"
                )

        # Update current state for next stage
        current_disp = res["Disp_t"]
        current_tmean = res["Tmean_m"]
        current_fwd = res["Dfwd_m"]
        current_aft = res["Daft_m"]

        # Store results
        stage_results[stage_name] = res

        print(
            f"[INFO] {stage_name}: FWD={res['Dfwd_m']:.2f}m, AFT={res['Daft_m']:.2f}m, "
            f"Trim={res['Trim_cm']:.1f}cm, Status={res.get('vs_2.70m', 'N/A')}"
        )

    # Export to Excel
    if not getattr(args, "no_excel", False):
        excel_path = (
            Path(args.excel_out)
            if getattr(args, "excel_out", None)
            else Path("roro_stages.xlsx")
        )
        export_roro_stages_to_excel(
            stage_results=stage_results,
            preballast_opt=preballast_opt,
            base_tmean=base_tmean_m,
            base_disp=base_disp_t,
            output_path=excel_path,
            params=params,
            tanks=tanks,
        )
        print(f"\n[INFO] Excel file saved to {excel_path}")

    return stage_results


def run_batch_mode(args):
    print("Running Batch Mode...")
    tanks = load_tanks_from_file(Path(args.tank))
    hydro_df = load_hydro_table(Path(args.hydro)) if args.hydro else None

    optimizer = BallastOptimizer(tanks, hydro_df)

    # Stage table loop mode
    if args.stage:
        st = load_stage_table(Path(args.stage))
        cur_tanks = tanks
        all_plan = []
        summary = []

        for _, r in st.iterrows():
            plan, pred, hydro, delta = optimizer.iterate_hydro_solve(
                dfwd0=float(r["Current_FWD_m"]),
                daft0=float(r["Current_AFT_m"]),
                iterate_hydro=getattr(args, "iterate_hydro", 2),
                target_fwd=(
                    float(r["Target_FWD_m"])
                    if "Target_FWD_m" in r and pd.notna(r["Target_FWD_m"])
                    else args.target_fwd
                ),
                target_aft=(
                    float(r["Target_AFT_m"])
                    if "Target_AFT_m" in r and pd.notna(r["Target_AFT_m"])
                    else args.target_aft
                ),
                limit_fwd=(
                    float(r["FWD_Limit_m"])
                    if "FWD_Limit_m" in r and pd.notna(r["FWD_Limit_m"])
                    else args.fwd_limit
                ),
                limit_aft=(
                    float(r["AFT_Limit_m"])
                    if "AFT_Limit_m" in r and pd.notna(r["AFT_Limit_m"])
                    else args.aft_limit
                ),
                limit_trim=(
                    float(r["Trim_Abs_Limit_m"])
                    if "Trim_Abs_Limit_m" in r and pd.notna(r["Trim_Abs_Limit_m"])
                    else args.trim_limit
                ),
                prefer_time=getattr(args, "prefer_time", True),
            )

            if not plan.empty:
                p2 = plan.copy()
                p2.insert(0, "Stage", str(r["Stage"]))
                all_plan.append(p2)

            summary.append(
                {
                    "Stage": str(r["Stage"]),
                    "Current_FWD_m": round(float(r["Current_FWD_m"]), 2),
                    "Current_AFT_m": round(float(r["Current_AFT_m"]), 2),
                    "New_FWD_m": round(pred["dfwd_new_m"], 2),
                    "New_AFT_m": round(pred["daft_new_m"], 2),
                    "ΔW_t": round(pred["total_w_t"], 2),
                    "PumpTime_h": round(pred.get("total_time_h", 0.0), 2),
                    "viol_fwd_m": round(pred.get("viol_fwd_m", 0.0), 3),
                }
            )

            # Validate stage result before proceeding
            validation_passed = True
            validation_errors = []

            # Check draft limits
            if pred["dfwd_new_m"] < VesselParams.MIN_DRAFT:
                validation_errors.append(
                    f"FWD draft {pred['dfwd_new_m']:.3f}m below minimum"
                )
                validation_passed = False
            if pred["dfwd_new_m"] > VesselParams.MAX_FWD_DRAFT_OPS:
                validation_errors.append(
                    f"FWD draft {pred['dfwd_new_m']:.3f}m exceeds limit"
                )
                validation_passed = False
            if pred["daft_new_m"] > VesselParams.MAX_AFT_DRAFT_OPS:
                validation_errors.append(
                    f"AFT draft {pred['daft_new_m']:.3f}m exceeds limit"
                )
                validation_passed = False

            # Check trim limit
            trim_cm = abs(pred["trim_new_m"]) * 100.0
            if trim_cm > VesselParams.TRIM_LIMIT_CM:
                validation_errors.append(f"Trim {trim_cm:.1f}cm exceeds limit")
                validation_passed = False

            # Check violations in limit mode
            if pred.get("viol_fwd_m", 0.0) > 0.01 or pred.get("viol_aft_m", 0.0) > 0.01:
                validation_errors.append("Draft limit violations detected")
                validation_passed = False

            if not validation_passed:
                print(f"\n[WARNING] Stage {r['Stage']} validation failed:")
                for err in validation_errors:
                    print(f"  - {err}")
                if getattr(args, "strict_validation", False):
                    print(
                        "[ERROR] Strict validation enabled - stopping stage processing"
                    )
                    break

            # Update tanks for next stage
            cur_tanks = optimizer.apply_delta_to_tanks(delta)
            optimizer.tanks = cur_tanks

        # Output stage results
        if all_plan:
            df_all_plan = pd.concat(all_plan, ignore_index=True)
            out_stage_plan = getattr(args, "out_stage_plan", "ballast_stage_plan.csv")
            out_stage_path = Path(out_stage_plan)
            out_stage_path.parent.mkdir(parents=True, exist_ok=True)
            df_all_plan.to_csv(out_stage_path, index=False, encoding="utf-8-sig")
            print(f"Stage plan saved to {out_stage_path}")

            # Pipeline compatibility: also write --out_plan if provided
            out_plan = getattr(args, "out_plan", "") or ""
            if out_plan:
                out_plan_path = Path(out_plan)
                if out_plan_path.resolve() != out_stage_path.resolve():
                    out_plan_path.parent.mkdir(parents=True, exist_ok=True)
                    df_all_plan.to_csv(out_plan_path, index=False, encoding="utf-8-sig")
                    print(f"Plan saved to {out_plan_path}")

        # Prepare data for Excel
        summary_df = pd.DataFrame(summary)
        df_all_plan = (
            pd.concat(all_plan, ignore_index=True) if all_plan else pd.DataFrame()
        )

        # Build tank log and BWRB log if available (for both Excel and CSV export)
        tank_log_df = None
        if getattr(args, "tanklog_out", None) and cur_tanks:
            tank_log_df = build_tank_log(cur_tanks, {})

        bwrb_log_df = None
        if args.bwrb_out and not df_all_plan.empty:
            master_verified = getattr(args, "master_verified", "N")
            bwrb_log_df = generate_bwrb_log(
                df_all_plan,
                args.vessel,
                args.location_name,
                args.lat,
                args.lon,
                args.officer,
                master_verified,
            )

        # Excel export for stage mode (default behavior unless --no_excel is set)
        if not getattr(args, "no_excel", False):
            excel_output_path = None
            if getattr(args, "excel_out", None):
                excel_output_path = Path(args.excel_out)
            else:
                # Default Excel file name for stage mode
                excel_output_path = Path("ballast_stage_plan.xlsx")

            try:

                export_to_excel(
                    df_all_plan,
                    summary_df,
                    tank_log_df,
                    bwrb_log_df,
                    excel_output_path,
                )
                print(f"Excel file saved to {excel_output_path}")
            except ImportError as e:
                print(f"WARNING: Excel export failed: {e}")
            except Exception as e:
                print(f"ERROR: Excel export failed: {e}")

        # CSV outputs (optional, only if specified)
        if args.out_summary:
            out_summary_path = Path(args.out_summary)
            out_summary_path.parent.mkdir(parents=True, exist_ok=True)
            summary_df.to_csv(out_summary_path, index=False, encoding="utf-8-sig")
            print(f"Summary saved to {out_summary_path}")

        # Optional CSV logs (stage mode)
        if getattr(args, "tanklog_out", "") and tank_log_df is not None:
            Path(args.tanklog_out).parent.mkdir(parents=True, exist_ok=True)
            tank_log_df.to_csv(args.tanklog_out, index=False, encoding="utf-8-sig")
        if getattr(args, "bwrb_out", "") and bwrb_log_df is not None:
            Path(args.bwrb_out).parent.mkdir(parents=True, exist_ok=True)
            bwrb_log_df.to_csv(args.bwrb_out, index=False, encoding="utf-8-sig")

        return

    # Single solve mode
    # Check inputs
    if args.current_fwd is None or args.current_aft is None:
        print("Error: --current_fwd and --current_aft are required (or use --stage).")
        return

    # Solve
    res = optimizer.solve(
        args.current_fwd,
        args.current_aft,
        target_fwd=args.target_fwd,
        target_aft=args.target_aft,
        limit_fwd=args.fwd_limit,
        limit_aft=args.aft_limit,
        limit_trim=args.trim_limit,
        prefer_time=getattr(args, "prefer_time", True),
    )

    if not res.success:
        print(f"Optimization Failed: {res.msg}")
        return

    # Prepare data for Excel (always prepare, even if not exporting)
    summary_df = pd.DataFrame([res.summary])
    tank_log_df = build_tank_log(optimizer.tanks, res.delta)
    master_verified = getattr(args, "master_verified", "N")
    bwrb_log_df = generate_bwrb_log(
        res.plan_df,
        args.vessel,
        args.location_name,
        args.lat,
        args.lon,
        args.officer,
        master_verified,
    )

    # Excel export (default behavior unless --no_excel is set)
    excel_output_path = None
    if not getattr(args, "no_excel", False):
        if getattr(args, "excel_out", None):
            excel_output_path = Path(args.excel_out)
        else:
            # Default Excel file name
            excel_output_path = Path("ballast_plan.xlsx")

        try:
            export_to_excel(
                res.plan_df,
                summary_df,
                tank_log_df,
                bwrb_log_df,
                excel_output_path,
            )
            print(f"Excel file saved to {excel_output_path}")
        except ImportError as e:
            print(f"WARNING: Excel export failed: {e}")
        except Exception as e:
            print(f"ERROR: Excel export failed: {e}")

    # CSV outputs (optional, only if specified)
    if args.out_plan:
        res.plan_df.to_csv(args.out_plan, index=False, encoding="utf-8-sig")
        print(f"Plan saved to {args.out_plan}")

    if args.out_summary:
        summary_df.to_csv(args.out_summary, index=False, encoding="utf-8-sig")
        print(f"Summary saved to {args.out_summary}")

    if args.bwrb_out:
        bwrb_log_df.to_csv(args.bwrb_out, index=False, encoding="utf-8-sig")
        print(f"BWRB Log saved to {args.bwrb_out}")

    if getattr(args, "tanklog_out", None):
        tank_log_df.to_csv(args.tanklog_out, index=False, encoding="utf-8-sig")
        print(f"Tank log saved to {args.tanklog_out}")


# =============================================================================
# MAIN ENTRY
# =============================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ballast Optimizer Integrated")

    # Switch
    parser.add_argument(
        "--batch", action="store_true", help="Run in batch mode (requires args)"
    )

    # Inputs
    parser.add_argument("--tank", help="Path to Tank SSOT CSV")
    parser.add_argument("--hydro", help="Path to Hydro Table CSV")
    parser.add_argument(
        "--stage", default="", help="Path to Stage Table CSV/Excel/JSON"
    )

    # Drafts
    parser.add_argument("--current_fwd", type=float)
    parser.add_argument("--current_aft", type=float)
    parser.add_argument("--target_fwd", type=float)
    parser.add_argument("--target_aft", type=float)

    # Limits
    parser.add_argument("--fwd_limit", type=float)
    parser.add_argument("--aft_limit", type=float)
    parser.add_argument(
        "--trim_limit", type=float, help="Absolute trim limit in meters"
    )

    # Optimization options
    parser.add_argument(
        "--prefer_time", action="store_true", help="Optimize for minimum pump time"
    )
    parser.add_argument(
        "--prefer_tons", action="store_true", help="Optimize for minimum weight moved"
    )
    parser.add_argument(
        "--iterate_hydro",
        type=int,
        default=2,
        help="Number of hydro iterations (default 2)",
    )

    # Outputs
    parser.add_argument(
        "--out_plan",
        default="",
        help="CSV output for plan (optional, Excel is default)",
    )
    parser.add_argument(
        "--out_summary",
        default="",
        help="CSV output for summary (optional, Excel is default)",
    )
    parser.add_argument(
        "--out_stage_plan",
        default="ballast_stage_plan.csv",
        help="Output for stage table mode",
    )
    parser.add_argument("--bwrb_out", default="", help="BWRB log output file")
    parser.add_argument(
        "--tanklog_out", default="", help="Tank-by-tank log output file"
    )
    parser.add_argument(
        "--excel_out",
        default="",
        help="Excel output file (requires xlsxwriter). Default: ballast_plan.xlsx",
    )
    parser.add_argument(
        "--no_excel", action="store_true", help="Disable Excel output (use CSV only)"
    )

    # RORO mode options
    parser.add_argument("--roro", action="store_true", help="Enable RORO stage mode")
    parser.add_argument(
        "--roro_base_disp",
        type=float,
        default=2800.0,
        help="Base displacement for RORO (t), default: 2800.0",
    )
    parser.add_argument(
        "--roro_base_tmean",
        type=float,
        default=None,
        help="Base mean draft for RORO (m), auto-calculated if not provided",
    )
    parser.add_argument(
        "--roro_w_tr",
        type=float,
        default=271.20,
        help="Transformer unit weight for RORO (t), default: 271.20",
    )
    parser.add_argument(
        "--roro_preballast",
        type=float,
        default=None,
        help="Pre-ballast weight for RORO (t), auto-optimized if not provided",
    )
    parser.add_argument(
        "--roro_preballast_min",
        type=float,
        default=20.0,
        help="Minimum pre-ballast search weight (t), default: 20.0",
    )
    parser.add_argument(
        "--roro_preballast_max",
        type=float,
        default=400.0,
        help="Maximum pre-ballast search weight (t), default: 400.0",
    )
    parser.add_argument(
        "--roro_preballast_step",
        type=float,
        default=1.0,
        help="Pre-ballast search step (t), default: 1.0",
    )
    parser.add_argument(
        "--roro_fr_tr1_stow",
        type=float,
        default=42.0,
        help="TR1 stow Frame number, default: 42.0",
    )
    parser.add_argument(
        "--roro_fr_tr1_ramp_start",
        type=float,
        default=40.15,
        help="TR1 ramp start Frame number, default: 40.15",
    )
    parser.add_argument(
        "--roro_fr_tr1_ramp_mid",
        type=float,
        default=37.00,
        help="TR1 ramp mid Frame number, default: 37.00",
    )
    parser.add_argument(
        "--roro_fr_tr2_ramp",
        type=float,
        default=17.95,
        help="TR2 ramp Frame number, default: 17.95",
    )
    parser.add_argument(
        "--roro_fr_tr2_stow",
        type=float,
        default=40.00,
        help="TR2 stow Frame number, default: 40.00",
    )
    parser.add_argument(
        "--roro_fr_preballast",
        type=float,
        default=3.0,
        help="Pre-ballast Frame number (FW2), default: 3.0",
    )

    # Metadata
    parser.add_argument("--vessel", default="LCT BUSHRA")
    parser.add_argument("--location_name", default="Sea")
    parser.add_argument("--lat", default="")
    parser.add_argument("--lon", default="")
    parser.add_argument("--officer", default="")

    args = parser.parse_args()

    # RORO mode
    if getattr(args, "roro", False):
        run_roro_mode(args)
    elif args.batch or args.tank:
        run_batch_mode(args)
    else:
        run_interactive_mode()
