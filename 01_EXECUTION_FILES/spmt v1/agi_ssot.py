#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AGI SSOT (Single Source of Truth) coordinate utilities for LCT cargo / SPMT scripts.

Scope
- **AGI Site** coordinate convention as implemented in the existing pipeline scripts:
  - Station from AP is denoted as Fr (meters).
  - Midship from AP is 30.151 m (LPP/2 when LPP=60.302 m).
  - x_from_midship (m) = midship_from_ap_m - fr_m_from_ap

Important
- This is a *geometric reference* used for stability / stage tables in the pipeline.
- It is NOT the same thing as *structural frame spacing* on the vessel.

This module is intended to be imported by:
- stage_shuttle_autocalc*.py
- cargo_spmt_inputs_stagewise_autofill.py
- spmt_shuttle_stage_builder.py
- lct_stage_spmt_shuttle.py (patched)
- spmt2.py (patched)

"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Literal, Optional, Tuple


CoordMode = Literal["FR_M", "FRAME_INDEX"]  # FR_M = station from AP in meters (SSOT)


def _as_float(v: Any) -> Optional[float]:
    if v is None:
        return None
    if isinstance(v, str):
        if v.strip() == "":
            return None
    try:
        return float(v)
    except Exception:
        return None


@dataclass(frozen=True)
class VesselSSOT:
    """
    Vessel coordinate handler.

    coord_mode
      - FR_M: input values are already station from AP (meters). (AGI default)
      - FRAME_INDEX: input values are frame index; station(m) = index*frame_spacing_m + ap_offset_m
        (Keep only for legacy compatibility. For AGI, use FR_M unless you have a verified index map.)
    """
    lpp_m: float = 60.302
    midship_from_ap_m: float = 30.151
    coord_mode: CoordMode = "FR_M"

    # Only used when coord_mode == "FRAME_INDEX"
    frame_spacing_m: float = 1.0
    ap_offset_m: float = 0.0

    # Validation
    fr_range_m: Tuple[float, float] = (0.0, 60.302)

    def to_fr_m_from_ap(self, v: Any) -> Optional[float]:
        x = _as_float(v)
        if x is None:
            return None

        if self.coord_mode == "FR_M":
            return float(x)

        # FRAME_INDEX (legacy)
        return float(x) * float(self.frame_spacing_m) + float(self.ap_offset_m)

    def x_from_midship_m(self, fr_m_from_ap: float) -> float:
        return float(self.midship_from_ap_m) - float(fr_m_from_ap)

    def fr_from_x_from_midship_m(self, x_from_midship_m: float) -> float:
        return float(self.midship_from_ap_m) - float(x_from_midship_m)

    def validate_fr_m(self, fr_m_from_ap: Optional[float], *, name: str = "Fr", strict: bool = True) -> None:
        if fr_m_from_ap is None:
            if strict:
                raise ValueError(f"{name}: missing (None).")
            return
        lo, hi = self.fr_range_m
        if not (lo <= float(fr_m_from_ap) <= hi):
            msg = (
                f"{name}: {fr_m_from_ap} is out of expected range [{lo}, {hi}] m "
                f"(coord_mode={self.coord_mode})."
            )
            if strict:
                raise ValueError(msg)
            # Non-strict: do nothing (caller can log)

    def explain(self) -> Dict[str, Any]:
        return {
            "lpp_m": self.lpp_m,
            "midship_from_ap_m": self.midship_from_ap_m,
            "coord_mode": self.coord_mode,
            "frame_spacing_m": self.frame_spacing_m,
            "ap_offset_m": self.ap_offset_m,
            "fr_range_m": self.fr_range_m,
            "formula": "x_from_midship = midship_from_ap_m - fr_m_from_ap",
        }


def build_agi_default_ssot() -> VesselSSOT:
    """
    Returns the AGI default SSOT values (LPP=60.302m, Midship=30.151m, coord_mode=FR_M).
    """
    return VesselSSOT(
        lpp_m=60.302,
        midship_from_ap_m=30.151,
        coord_mode="FR_M",
        frame_spacing_m=1.0,
        ap_offset_m=0.0,
        fr_range_m=(0.0, 60.302),
    )
