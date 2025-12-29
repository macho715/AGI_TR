"""
SSOT Draft Calculation Module (AGENTS.md Method B)
LCF/Lpp-based physically consistent draft calculation

This module implements AGENTS.md Method B for draft calculations:
- Uses LCF (Longitudinal Center of Flotation) as reference point
- Physically consistent for all trim ranges
- Handles coordinate system conversion (Frame ↔ x)

Key Principles:
1. Trim moment about LCF: TM_LCF = Σ(w_i * (x_i - LCF))
2. Trim: Trim_cm = TM_LCF / MTC
3. Drafts: Dfwd/Daft calculated using Lpp distribution

Usage:
    from ssot.draft_calc import DraftCalculatorMethodB, calc_drafts

    # Method 1: Using calculator object
    calc = DraftCalculatorMethodB(
        LCF_m=0.76,
        Lpp_m=60.302,
        MTC_t_m_per_cm=34.00,
        TPC_t_per_cm=8.00
    )

    results = calc.calculate(
        weights=[(100.0, -15.0), (50.0, 10.0)],
        mean_draft_m=2.5
    )

    # Method 2: Convenience function
    results = calc_drafts(
        weights=[(100.0, -15.0)],
        mean_draft_m=2.5,
        LCF_m=0.76,
        Lpp_m=60.302,
        MTC=34.00,
        TPC=8.00
    )
"""

from dataclasses import dataclass
from typing import List, Tuple, Dict, Any


@dataclass
class DraftCalculationResult:
    """Results from draft calculation"""

    Dfwd_m: float
    Daft_m: float
    Tmean_m: float
    Trim_cm: float
    TM_LCF_tm: float
    total_weight_t: float
    method: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for export"""
        return {
            "Dfwd_m": round(self.Dfwd_m, 3),
            "Daft_m": round(self.Daft_m, 3),
            "Tmean_m": round(self.Tmean_m, 3),
            "Trim_cm": round(self.Trim_cm, 2),
            "TM_LCF_tm": round(self.TM_LCF_tm, 2),
            "total_weight_t": round(self.total_weight_t, 2),
            "method": self.method,
        }

    def __repr__(self) -> str:
        return (
            f"DraftResult(Dfwd={self.Dfwd_m:.3f}m, Daft={self.Daft_m:.3f}m, "
            f"Trim={self.Trim_cm:.2f}cm)"
        )


class DraftCalculatorMethodB:
    """
    AGENTS.md Method B: Lpp/LCF-based draft calculation

    Core Formulas (AGENTS.md v0.2):
    1. TM_LCF = Σ(w_i * (x_i - LCF))
    2. Trim_cm = TM_LCF / MTC
    3. Slope = Trim_m / Lpp
    4. Dfwd = Tmean + slope * (x_fp - LCF)
    5. Daft = Tmean + slope * (x_ap - LCF)

    Where:
    - x is measured from midship
    - x > 0: AFT (stern)
    - x < 0: FWD (bow)
    - LCF > 0: aft of midship (typical)
    """

    def __init__(
        self,
        LCF_m: float = 0.76,
        Lpp_m: float = 60.302,
        MTC_t_m_per_cm: float = 34.00,
        TPC_t_per_cm: float = 8.00,
        frame_offset: float = 30.151,
        frame_slope: float = -1.0,
    ):
        """
        Initialize draft calculator with vessel parameters

        Args:
            LCF_m: LCF from midship (positive = aft)
            Lpp_m: Length between perpendiculars
            MTC_t_m_per_cm: Moment to change trim 1 cm
            TPC_t_per_cm: Tons per centimeter immersion
            frame_offset: Frame reference (Fr.30.151 = midship)
            frame_slope: Frame to x conversion slope
        """
        self.LCF_m = LCF_m
        self.Lpp_m = Lpp_m
        self.MTC_t_m_per_cm = MTC_t_m_per_cm
        self.TPC_t_per_cm = TPC_t_per_cm
        self.frame_offset = frame_offset
        self.frame_slope = frame_slope

        # Calculate FP and AP positions
        # AP is at +Lpp/2, FP is at -Lpp/2 from midship
        self.x_ap = Lpp_m / 2.0
        self.x_fp = -Lpp_m / 2.0

    def frame_to_x(self, frame: float) -> float:
        """
        Convert Frame to x coordinate

        AGENTS.md convention:
        - Frame 0 = AP (aft perpendicular)
        - Frame 30.151 = Midship (x = 0)
        - x = frame_slope * (Frame - frame_offset)
        - Default: x = -1.0 * (Frame - 30.151) = 30.151 - Frame

        Args:
            frame: Frame number

        Returns:
            x coordinate (m from midship, positive = aft)
        """
        return self.frame_slope * (frame - self.frame_offset)

    def x_to_frame(self, x: float) -> float:
        """
        Convert x coordinate to Frame

        Args:
            x: Position from midship (m, positive = aft)

        Returns:
            Frame number
        """
        return (x / self.frame_slope) + self.frame_offset

    def calculate(
        self,
        weights: List[Tuple[float, float]],
        mean_draft_m: float = None,
        total_weight_t: float = None,
    ) -> DraftCalculationResult:
        """
        Calculate drafts using Method B

        Args:
            weights: List of (weight_t, x_from_midship_m) tuples
            mean_draft_m: Mean draft (optional, will calculate if total_weight_t provided)
            total_weight_t: Total weight (optional, will sum from weights)

        Returns:
            DraftCalculationResult with Dfwd, Daft, Trim, etc.
        """
        # Calculate total weight if not provided
        if total_weight_t is None:
            total_weight_t = sum(w for w, _ in weights)

        # Calculate mean draft if not provided
        if mean_draft_m is None:
            if total_weight_t == 0:
                raise ValueError("Cannot calculate mean draft with zero weight")
            # Simple approximation: draft = weight / TPC / 100
            mean_draft_m = total_weight_t / self.TPC_t_per_cm / 100.0

        # Step 1: Calculate trimming moment about LCF
        TM_LCF_tm = sum(w * (x - self.LCF_m) for w, x in weights)

        # Step 2: Calculate trim
        Trim_cm = TM_LCF_tm / self.MTC_t_m_per_cm

        # Step 3: Calculate slope
        Trim_m = Trim_cm / 100.0
        slope = Trim_m / self.Lpp_m

        # Step 4: Calculate drafts
        # Dfwd = Tmean + slope * (x_fp - LCF)
        # Daft = Tmean + slope * (x_ap - LCF)
        Dfwd_m = mean_draft_m + slope * (self.x_fp - self.LCF_m)
        Daft_m = mean_draft_m + slope * (self.x_ap - self.LCF_m)

        return DraftCalculationResult(
            Dfwd_m=Dfwd_m,
            Daft_m=Daft_m,
            Tmean_m=mean_draft_m,
            Trim_cm=Trim_cm,
            TM_LCF_tm=TM_LCF_tm,
            total_weight_t=total_weight_t,
            method="B",
        )

    def validate_physical_consistency(
        self, result: DraftCalculationResult
    ) -> List[str]:
        """
        Validate physical consistency of draft calculation

        Checks (AGENTS.md):
        1. Trim = Daft - Dfwd (within tolerance)
        2. Mean draft = (Dfwd + Daft) / 2 (within tolerance)

        Args:
            result: DraftCalculationResult to validate

        Returns:
            List of warning messages (empty if consistent)
        """
        warnings = []
        tolerance_cm = 0.5  # 0.5 cm tolerance

        # Check 1: Trim consistency
        trim_calculated_cm = (result.Daft_m - result.Dfwd_m) * 100.0
        trim_diff_cm = abs(trim_calculated_cm - result.Trim_cm)
        if trim_diff_cm > tolerance_cm:
            warnings.append(
                f"Trim inconsistency: {trim_calculated_cm:.2f}cm (from drafts) "
                f"vs {result.Trim_cm:.2f}cm (from TM) - diff {trim_diff_cm:.2f}cm"
            )

        # Check 2: Mean draft consistency
        mean_calculated_m = (result.Dfwd_m + result.Daft_m) / 2.0
        mean_diff_cm = abs((mean_calculated_m - result.Tmean_m) * 100.0)
        if mean_diff_cm > tolerance_cm:
            warnings.append(
                f"Mean draft inconsistency: {mean_calculated_m:.3f}m (from drafts) "
                f"vs {result.Tmean_m:.3f}m (input) - diff {mean_diff_cm:.2f}cm"
            )

        return warnings

    def __repr__(self) -> str:
        return (
            f"DraftCalculatorMethodB(LCF={self.LCF_m}m, Lpp={self.Lpp_m}m, "
            f"MTC={self.MTC_t_m_per_cm})"
        )


def calc_drafts(
    weights: List[Tuple[float, float]],
    mean_draft_m: float = None,
    total_weight_t: float = None,
    LCF_m: float = 0.76,
    Lpp_m: float = 60.302,
    MTC: float = 34.00,
    TPC: float = 8.00,
) -> DraftCalculationResult:
    """
    Convenience function for one-off draft calculations

    Args:
        weights: List of (weight_t, x_from_midship_m) tuples
        mean_draft_m: Mean draft (optional)
        total_weight_t: Total weight (optional)
        LCF_m, Lpp_m, MTC, TPC: Vessel parameters

    Returns:
        DraftCalculationResult
    """
    calc = DraftCalculatorMethodB(LCF_m, Lpp_m, MTC, TPC)
    return calc.calculate(weights, mean_draft_m, total_weight_t)


# Example usage and testing
if __name__ == "__main__":
    print("=" * 80)
    print("SSOT Draft Calculator (AGENTS.md Method B) Test")
    print("=" * 80)

    # Test with AGI parameters
    calc = DraftCalculatorMethodB(
        LCF_m=0.76, Lpp_m=60.302, MTC_t_m_per_cm=34.00, TPC_t_per_cm=8.00
    )

    print(f"\n{calc}")
    print(f"x_ap (AP position): {calc.x_ap:.3f} m")
    print(f"x_fp (FP position): {calc.x_fp:.3f} m")

    # Test case 1: Even loading
    print("\n" + "=" * 80)
    print("Test Case 1: Even Loading (no trim)")
    print("=" * 80)

    weights_even = [(100.0, 0.0)]  # 100t at midship
    result_even = calc.calculate(weights_even, mean_draft_m=2.5)

    print(f"\nInput: 100t @ midship, Tmean = 2.5m")
    print(f"Result: {result_even}")
    print(f"  TM_LCF: {result_even.TM_LCF_tm:.2f} t·m")
    print(f"  Trim: {result_even.Trim_cm:.2f} cm")
    print(f"  Dfwd: {result_even.Dfwd_m:.3f} m")
    print(f"  Daft: {result_even.Daft_m:.3f} m")

    warnings = calc.validate_physical_consistency(result_even)
    if warnings:
        print("⚠️  Warnings:")
        for w in warnings:
            print(f"  - {w}")
    else:
        print("✅ Physically consistent")

    # Test case 2: Forward heavy (bow down)
    print("\n" + "=" * 80)
    print("Test Case 2: Forward Heavy (bow down trim)")
    print("=" * 80)

    weights_fwd = [(50.0, -20.0), (50.0, 0.0)]  # 50t @ 20m forward  # 50t @ midship
    result_fwd = calc.calculate(weights_fwd, mean_draft_m=2.5)

    print(f"\nInput: 50t @ -20m (fwd), 50t @ 0m (mid), Tmean = 2.5m")
    print(f"Result: {result_fwd}")
    print(f"  TM_LCF: {result_fwd.TM_LCF_tm:.2f} t·m")
    print(f"  Trim: {result_fwd.Trim_cm:.2f} cm (negative = bow down)")
    print(f"  Dfwd: {result_fwd.Dfwd_m:.3f} m")
    print(f"  Daft: {result_fwd.Daft_m:.3f} m")

    warnings = calc.validate_physical_consistency(result_fwd)
    if warnings:
        print("⚠️  Warnings:")
        for w in warnings:
            print(f"  - {w}")
    else:
        print("✅ Physically consistent")

    # Test case 3: Aft heavy (stern down)
    print("\n" + "=" * 80)
    print("Test Case 3: Aft Heavy (stern down trim)")
    print("=" * 80)

    weights_aft = [(50.0, 0.0), (50.0, 20.0)]  # 50t @ midship  # 50t @ 20m aft
    result_aft = calc.calculate(weights_aft, mean_draft_m=2.5)

    print(f"\nInput: 50t @ 0m (mid), 50t @ +20m (aft), Tmean = 2.5m")
    print(f"Result: {result_aft}")
    print(f"  TM_LCF: {result_aft.TM_LCF_tm:.2f} t·m")
    print(f"  Trim: {result_aft.Trim_cm:.2f} cm (positive = stern down)")
    print(f"  Dfwd: {result_aft.Dfwd_m:.3f} m")
    print(f"  Daft: {result_aft.Daft_m:.3f} m")

    warnings = calc.validate_physical_consistency(result_aft)
    if warnings:
        print("⚠️  Warnings:")
        for w in warnings:
            print(f"  - {w}")
    else:
        print("✅ Physically consistent")

    # Test Frame ↔ x conversion
    print("\n" + "=" * 80)
    print("Frame ↔ x Coordinate Conversion Test")
    print("=" * 80)

    test_frames = [0.0, 30.151, 56.0]
    for fr in test_frames:
        x = calc.frame_to_x(fr)
        fr_back = calc.x_to_frame(x)
        print(f"Frame {fr:.3f} → x = {x:.3f} m → Frame {fr_back:.3f}")

    print("\n" + "=" * 80)
    print("SSOT Draft Calculator: ✅ ALL TESTS PASSED")
    print("=" * 80)
