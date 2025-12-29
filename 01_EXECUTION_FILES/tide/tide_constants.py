#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TIDE Constants (SSOT)
=====================
Centralized constants for TIDE/UKC calculations.
"""

from pathlib import Path
from typing import Dict, Any, Optional
import json

# Default values (fallback only)
DEFAULT_TIDE_TOL_M = 0.10  # Tide margin tolerance (m)
DEFAULT_DEPTH_REF_M = 5.50  # AGI default depth reference
DEFAULT_UKC_MIN_M = 0.50  # Minimum UKC requirement
DEFAULT_SQUAT_M = 0.15  # Default squat allowance
DEFAULT_SAFETY_ALLOW_M = 0.20  # Default safety allowance

# Timeout settings
FORMULA_TIMEOUT_SEC = 120  # Excel formula finalization timeout

# Column names (SSOT)
COL_FORECAST_TIDE_M = "Forecast_Tide_m"
COL_TIDE_REQUIRED_M = "Tide_required_m"
COL_TIDE_MARGIN_M = "Tide_margin_m"
COL_UKC_MIN_M = "UKC_min_m"
COL_UKC_FWD_M = "UKC_fwd_m"
COL_UKC_AFT_M = "UKC_aft_m"


def load_tide_constants_from_profile(profile_path: Optional[Path] = None) -> Dict[str, Any]:
    """Load tide/UKC constants from profile JSON with fallbacks."""
    if profile_path and profile_path.exists():
        try:
            with open(profile_path, encoding="utf-8") as f:
                profile = json.load(f)
            tide_ukc = profile.get("tide_ukc", {})
            operational = profile.get("operational", {})
            return {
                "tide_tol_m": tide_ukc.get("tide_tol_m", DEFAULT_TIDE_TOL_M),
                "depth_ref_m": tide_ukc.get("depth_ref_m", DEFAULT_DEPTH_REF_M),
                "ukc_min_m": tide_ukc.get("ukc_min_m", DEFAULT_UKC_MIN_M),
                "squat_m": tide_ukc.get("squat_m", DEFAULT_SQUAT_M),
                "safety_allow_m": tide_ukc.get("safety_allow_m", DEFAULT_SAFETY_ALLOW_M),
                "formula_timeout_sec": operational.get("formula_timeout_sec", FORMULA_TIMEOUT_SEC),
            }
        except Exception as e:
            import logging
            logging.warning(f"Profile load failed: {e}, using defaults")

    return {
        "tide_tol_m": DEFAULT_TIDE_TOL_M,
        "depth_ref_m": DEFAULT_DEPTH_REF_M,
        "ukc_min_m": DEFAULT_UKC_MIN_M,
        "squat_m": DEFAULT_SQUAT_M,
        "safety_allow_m": DEFAULT_SAFETY_ALLOW_M,
        "formula_timeout_sec": FORMULA_TIMEOUT_SEC,
    }

