#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
spmt2.py (AGI SSOT patched)

This file previously mixed "frame index * 0.60m + AP offset" logic.
For AGI SSOT, "Frame" inputs are treated as **Fr(m) station from AP** and used directly.

Recommendation
- Prefer using `agi_spmt_unified.py` as the integrated entrypoint.
- Keep this script only if you need a lightweight calculator.

"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

from agi_ssot import build_agi_default_ssot

SSOT = build_agi_default_ssot()


@dataclass
class Load:
    name: str
    weight_t: float
    fr_m_from_ap: float

    @property
    def x_m_from_midship(self) -> float:
        return SSOT.x_from_midship_m(self.fr_m_from_ap)


def summarize(loads: List[Load]) -> Tuple[float, float]:
    """Returns (total_t, lcg_x_from_midship_m)."""
    total = sum(l.weight_t for l in loads)
    if total <= 0:
        return 0.0, 0.0
    lcg_x = sum(l.weight_t * l.x_m_from_midship for l in loads) / total
    return round(total, 3), round(lcg_x, 3)


def demo():
    # Example (replace with your actual values)
    midship = SSOT.midship_from_ap_m
    tr1_final_fr = 42.0
    tr2_final_fr = 40.0

    loads = [
        Load("TR1 (fixed)", 217.0, tr1_final_fr),
        Load("TR2 (fixed)", 217.0, tr2_final_fr),
    ]
    total, lcg_x = summarize(loads)
    lcg_fr = SSOT.fr_from_x_from_midship_m(lcg_x)
    print(f"SSOT midship_from_ap_m = {midship}")
    print(f"Total = {total:.3f} t")
    print(f"LCGx (from midship) = {lcg_x:.3f} m")
    print(f"LCG Fr (from AP) = {lcg_fr:.3f} m")


if __name__ == "__main__":
    demo()
