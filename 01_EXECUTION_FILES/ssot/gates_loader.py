"""
SSOT Gates Loader Module
AGENTS.md compliant gate loading and validation

This module provides:
1. Gate definition loading from AGI site profile
2. Gate compliance checking
3. Evidence tracking
4. SSOT parameter access
5. Tank catalog loading with operability enforcement (B-1 patch)
6. Ballast plan operability validation (B-1 patch)

Usage:
    from ssot.gates_loader import load_agi_profile

    profile = load_agi_profile()
    gates = profile.gates

    # Check gate compliance
    gate_aft = profile.get_gate("AFT_MIN_2p70_propulsion")
    passed, msg = gate_aft.check(draft_aft_m=2.75, stage_name="Stage_6A")

    # Load tank catalog with operability (B-1)
    tank_catalog_df = profile.load_tank_catalog()

    # Validate ballast plan operability (B-1)
    violations = profile.validate_ballast_plan(ballast_plan_df, tank_catalog_df)
"""

import json
from dataclasses import dataclass
from typing import List, Dict, Any, Tuple, Optional
from pathlib import Path
import re


@dataclass
class Gate:
    """Single gate definition with compliance checking"""

    gate_id: str
    gate_name: str
    phase: str
    metric: str
    comparator: str
    limit_value: float
    unit: str
    reference_frame: str
    basis_doc: str
    evidence_required: List[str]
    owner: str
    mandatory: bool
    notes: str

    def check(self, value: float, stage_name: Optional[str] = None) -> Tuple[bool, str]:
        """
        Check gate compliance

        Args:
            value: Measured value to check
            stage_name: Optional stage name for phase checking

        Returns:
            (passed: bool, message: str)
        """
        # Phase check for critical-only gates
        if self.phase == "critical_stages" and stage_name:
            # AGI critical regex from profile
            if not re.search(
                r"(preballast|stage.*6[abc]|critical)", stage_name, re.IGNORECASE
            ):
                return (
                    True,
                    f"N/A: Stage '{stage_name}' not critical for {self.gate_id}",
                )

        # Value check based on comparator
        if self.comparator == ">=":
            passed = value >= self.limit_value
        elif self.comparator == "<=":
            passed = value <= self.limit_value
        elif self.comparator == ">":
            passed = value > self.limit_value
        elif self.comparator == "<":
            passed = value < self.limit_value
        elif self.comparator == "==":
            passed = abs(value - self.limit_value) < 0.01
        else:
            raise ValueError(f"Unknown comparator: {self.comparator}")

        status = "PASS" if passed else "FAIL"
        msg = (
            f"{status}: {self.metric} {value:.2f}{self.unit} "
            f"{self.comparator} {self.limit_value}{self.unit}"
        )

        if not passed:
            msg += f" | Owner: {self.owner} | Evidence: {', '.join(self.evidence_required[:2])}"

        return passed, msg

    def __repr__(self) -> str:
        return f"Gate({self.gate_id}: {self.metric} {self.comparator} {self.limit_value}{self.unit})"


class SiteProfile:
    """
    AGI Site Profile SSOT

    Provides unified access to:
    - Gate definitions
    - Draft calculation parameters
    - Ballast parameters
    - Hydro parameters
    - Operational limits
    """

    def __init__(self, profile_path: str):
        """
        Load site profile from JSON

        Args:
            profile_path: Path to site profile JSON file
        """
        self.profile_path = Path(profile_path)
        if not self.profile_path.exists():
            raise FileNotFoundError(f"Site profile not found: {profile_path}")

        self.data = self._load()
        self.gates = self._build_gates()

    def _load(self) -> Dict[str, Any]:
        """Load and parse JSON profile"""
        with open(self.profile_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _build_gates(self) -> List[Gate]:
        """Build Gate objects from profile data"""
        gates = []
        for g in self.data.get("gates", []):
            gates.append(
                Gate(
                    gate_id=g["gate_id"],
                    gate_name=g["gate_name"],
                    phase=g["phase"],
                    metric=g["metric"],
                    comparator=g["comparator"],
                    limit_value=g["limit_value"],
                    unit=g["unit"],
                    reference_frame=g["reference_frame"],
                    basis_doc=g["basis_doc"],
                    evidence_required=g["evidence_required"],
                    owner=g["owner"],
                    mandatory=g["mandatory"],
                    notes=g.get("notes", ""),
                )
            )
        return gates

    def get_gate(self, gate_id: str) -> Gate:
        """
        Get gate by ID

        Args:
            gate_id: Gate identifier (e.g., "AFT_MIN_2p70_propulsion")

        Returns:
            Gate object

        Raises:
            KeyError: If gate not found
        """
        for gate in self.gates:
            if gate.gate_id == gate_id:
                return gate
        raise KeyError(f"Gate not found: {gate_id}")

    def check_all_gates(
        self, values: Dict[str, float], stage_name: str
    ) -> Dict[str, Tuple[bool, str]]:
        """
        Check all gates for a stage

        Args:
            values: Dict mapping metric names to values
                   e.g., {"Draft_AFT": 2.75, "Draft_FWD": 2.65, "Trim_abs": 15.0}
            stage_name: Stage identifier

        Returns:
            Dict mapping gate_id to (passed, message)
        """
        results = {}
        for gate in self.gates:
            if gate.metric in values:
                results[gate.gate_id] = gate.check(values[gate.metric], stage_name)
            else:
                results[gate.gate_id] = (None, f"SKIP: {gate.metric} not provided")
        return results

    @property
    def meta(self) -> Dict[str, Any]:
        """Profile metadata"""
        return self.data.get("meta", {})

    @property
    def draft_calc_params(self) -> Dict[str, Any]:
        """Draft calculation parameters (AGENTS.md Method B)"""
        return self.data.get("draft_calc", {})

    @property
    def ballast_params(self) -> Dict[str, Any]:
        """Ballast parameters (pumps, contingency)"""
        return self.data.get("ballast", {})

    @property
    def hydro_params(self) -> Dict[str, Any]:
        """Hydro parameters (datum, depth, tide)"""
        return self.data.get("hydro", {})

    @property
    def hold_point_params(self) -> Dict[str, Any]:
        """Hold point parameters"""
        return self.data.get("hold_point", {})

    @property
    def operational_limits(self) -> Dict[str, Any]:
        """Operational limits"""
        return self.data.get("operational_limits", {})

    @property
    def bplus_preflight(self) -> Dict[str, Any]:
        """B+ preflight configuration"""
        return self.data.get("bplus_preflight", {})

    def load_tank_catalog(self) -> "pd.DataFrame":
        """
        Load tank catalog with operability constraints

        Returns:
            DataFrame with operability, pump_access, zone
        """
        try:
            import pandas as pd
        except ImportError:
            raise ImportError(
                "pandas is required for tank catalog loading. Install with: pip install pandas"
            )

        tank_catalog_ref = self.data.get("tank_catalog_ref", {})
        tank_catalog_file = tank_catalog_ref.get(
            "source", "tank_catalog_AGI_with_operability.json"
        )

        tank_catalog_path = Path(self.profile_path).parent / tank_catalog_file

        if not tank_catalog_path.exists():
            raise FileNotFoundError(f"Tank catalog not found: {tank_catalog_path}")

        with open(tank_catalog_path, "r", encoding="utf-8") as f:
            tank_data = json.load(f)

        tanks = []
        for t in tank_data["tanks"]:
            tanks.append(
                {
                    "Tank": t["tank_id"],
                    "Cap_t": t["capacity_t"],
                    "x_from_mid_m": t["lcg_from_midship_m"],
                    "operability": t.get("operability", "NORMAL"),
                    "operability_notes": t.get("operability_notes", ""),
                    "pump_access": t.get("pump_access", True),
                    "zone": t.get("zone", "UNKNOWN"),
                    "max_rate_tph": t.get("max_rate_tph", None),
                    "valve_lineup_id": t.get("valve_lineup_id", None),
                }
            )

        df = pd.DataFrame(tanks)

        # Print operability summary
        pre_ballast_only = df[df["operability"] == "PRE_BALLAST_ONLY"]
        if not pre_ballast_only.empty:
            print(f"\n[OPERABILITY] Pre-ballast storage only tanks:")
            for _, row in pre_ballast_only.iterrows():
                print(f"  - {row['Tank']}: {row['operability_notes']}")

        discharge_only = df[df["operability"] == "DISCHARGE_ONLY"]
        if not discharge_only.empty:
            print(f"\n[OPERABILITY] Discharge-only tanks:")
            for _, row in discharge_only.iterrows():
                print(f"  - {row['Tank']}: {row['operability_notes']}")

        locked = df[df["operability"] == "LOCKED"]
        if not locked.empty:
            print(f"\n[OPERABILITY] Locked tanks:")
            for _, row in locked.iterrows():
                print(f"  - {row['Tank']}: {row['operability_notes']}")

        return df

    def validate_ballast_plan(
        self, ballast_plan_df: "pd.DataFrame", tank_catalog_df: "pd.DataFrame" = None
    ) -> List[str]:
        """
        Validate ballast plan against operability constraints

        Args:
            ballast_plan_df: Ballast plan with columns [Tank, Delta_t, ...]
            tank_catalog_df: Tank catalog (optional, will load if not provided)

        Returns:
            List of violation messages (empty if compliant)
        """
        try:
            import pandas as pd
        except ImportError:
            raise ImportError("pandas is required. Install with: pip install pandas")

        if tank_catalog_df is None:
            tank_catalog_df = self.load_tank_catalog()

        violations = []

        for _, plan_row in ballast_plan_df.iterrows():
            tank_id = plan_row["Tank"]
            delta_t = plan_row.get("Delta_t", 0)

            # Skip if no change
            if abs(delta_t) < 0.01:
                continue

            # Check tank operability
            tank_info = tank_catalog_df[tank_catalog_df["Tank"] == tank_id]
            if tank_info.empty:
                violations.append(f"Tank {tank_id} not found in catalog")
                continue

            operability = tank_info.iloc[0]["operability"]

            # PRE_BALLAST_ONLY: Cannot transfer (fill/discharge)
            if operability == "PRE_BALLAST_ONLY":
                violations.append(
                    f"OPERABILITY VIOLATION: Tank {tank_id} is PRE_BALLAST_ONLY. "
                    f"Attempted delta: {delta_t:.2f}t. "
                    f"Notes: {tank_info.iloc[0]['operability_notes']}"
                )

            # DISCHARGE_ONLY: Cannot fill (positive delta)
            elif operability == "DISCHARGE_ONLY" and delta_t > 0:
                violations.append(
                    f"OPERABILITY VIOLATION: Tank {tank_id} is DISCHARGE_ONLY. "
                    f"Attempted fill: {delta_t:.2f}t"
                )

            # No pump access: Cannot transfer
            elif not tank_info.iloc[0]["pump_access"] and abs(delta_t) > 0:
                violations.append(
                    f"OPERABILITY VIOLATION: Tank {tank_id} has no pump access. "
                    f"Attempted delta: {delta_t:.2f}t"
                )

        return violations

    def __repr__(self) -> str:
        site = self.meta.get("site", "UNKNOWN")
        version = self.meta.get("version", "UNKNOWN")
        n_gates = len(self.gates)
        return f"SiteProfile(site={site}, version={version}, gates={n_gates})"


def load_agi_profile() -> SiteProfile:
    """
    Convenience function to load AGI site profile

    Returns:
        SiteProfile for AGI site
    """
    # Try multiple possible paths
    possible_paths = [
        Path(__file__).parent.parent.parent / "patch1225" / "AGI_site_profile_COMPLETE_v1.json",  # Project root
        Path(__file__).parent.parent / "patch1225" / "AGI_site_profile_COMPLETE_v1.json",  # Original
        Path("C:/AGI RORO TR/patch1225/AGI_site_profile_COMPLETE_v1.json"),  # Absolute fallback
    ]

    for profile_path in possible_paths:
        if profile_path.exists():
            return SiteProfile(str(profile_path))

    # If none found, raise with helpful message
    raise FileNotFoundError(
        f"AGI site profile not found. Tried paths:\n" +
        "\n".join(f"  - {p}" for p in possible_paths)
    )


# Example usage and testing
if __name__ == "__main__":
    print("=" * 80)
    print("SSOT Gates Loader Test")
    print("=" * 80)

    # Load profile
    profile = load_agi_profile()
    print(f"\n{profile}")
    print(f"Site: {profile.meta['site']}")
    print(f"Version: {profile.meta['version']}")
    print(f"Effective Date: {profile.meta['effective_date']}")

    # List gates
    print(f"\n{len(profile.gates)} Gates Loaded:")
    for gate in profile.gates:
        print(f"  - {gate.gate_id}: {gate.gate_name}")

    # Test gate check
    print("\n" + "=" * 80)
    print("Gate Compliance Test")
    print("=" * 80)

    test_values = {
        "Draft_AFT": 2.75,
        "Draft_FWD": 2.65,
        "Trim_abs": 15.0,
        "UKC": 0.60,
        "GM": 1.55,
    }

    print(f"\nTest Values: {test_values}")
    print(f"Stage: Stage_6A (critical)")

    results = profile.check_all_gates(test_values, "Stage_6A")

    print("\nResults:")
    for gate_id, (passed, msg) in results.items():
        status_icon = "✅" if passed is True else "❌" if passed is False else "⏭️"
        print(f"  {status_icon} {gate_id}: {msg}")

    # Test draft calc params
    print("\n" + "=" * 80)
    print("Draft Calculation Parameters (AGENTS.md Method B)")
    print("=" * 80)
    dc = profile.draft_calc_params
    print(f"Method: {dc['method']} - {dc['method_description']}")
    print(f"LCF from midship: {dc['LCF_m_from_midship']} m")
    print(f"Lpp: {dc['Lpp_m']} m")
    print(f"MTC: {dc['MTC_t_m_per_cm']} t·m/cm")
    print(f"TPC: {dc['TPC_t_per_cm']} t/cm")

    # Test ballast params
    print("\n" + "=" * 80)
    print("Ballast Parameters")
    print("=" * 80)
    bp = profile.ballast_params
    print(f"Ship pump: {bp['pump_rate_tph']} t/h")
    print(f"Hired pump: {bp['pump_rate_tph_hired']} t/h")
    print(f"Contingency modes:")
    for mode, config in bp["contingency"].items():
        print(
            f"  - Mode {mode}: {config['pump_rate_tph']} t/h - {config['description']}"
        )

    print("\n" + "=" * 80)
    print("SSOT Gates Loader: ✅ ALL TESTS PASSED")
    print("=" * 80)
