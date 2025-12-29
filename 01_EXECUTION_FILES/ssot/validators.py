#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SSOT Validators (P1-1)
Input/physics/gate preflight validation before pipeline execution.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import json
import pandas as pd

from .gates_loader import SiteProfile, load_agi_profile


@dataclass
class ValidationIssue:
    """Single validation issue."""

    severity: str  # CRITICAL, WARNING, INFO
    category: str  # INPUT, PHYSICS, GATE, SSOT
    message: str
    details: str
    suggestion: str


@dataclass
class ValidationReport:
    """Complete validation report."""

    passed: bool
    issues: List[ValidationIssue]
    timestamp: str

    def get_critical_issues(self) -> List[ValidationIssue]:
        return [i for i in self.issues if i.severity == "CRITICAL"]

    def get_warnings(self) -> List[ValidationIssue]:
        return [i for i in self.issues if i.severity == "WARNING"]

    def summary(self) -> str:
        critical = len(self.get_critical_issues())
        warnings = len(self.get_warnings())
        status = "PASS" if self.passed else "FAIL"
        return f"[{status}] {critical} Critical, {warnings} Warnings"


def _first_existing_column(df: pd.DataFrame, candidates: List[str]) -> Optional[str]:
    for name in candidates:
        if name in df.columns:
            return name
    return None


def _safe_float(value: object, default: Optional[float] = None) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def load_hydro_table_df(hydro_path: Path) -> pd.DataFrame:
    """Load hydro table from JSON or CSV to a DataFrame."""
    if not hydro_path.exists():
        raise FileNotFoundError(f"Hydro table not found: {hydro_path}")

    if hydro_path.suffix.lower() == ".json":
        data = json.loads(hydro_path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            rows = None
            for key in ("rows", "table", "data", "hydro_table", "hydro"):
                if key in data:
                    rows = data[key]
                    break
            if rows is None:
                raise ValueError(
                    f"Hydro JSON missing rows/table list: {hydro_path.name}"
                )
            return pd.DataFrame(rows)
        if isinstance(data, list):
            return pd.DataFrame(data)
        raise ValueError(f"Unexpected hydro JSON format: {type(data).__name__}")

    return pd.read_csv(hydro_path, encoding="utf-8-sig")


class InputValidator:
    """Validate input data consistency and completeness."""

    def __init__(self, profile: SiteProfile):
        self.profile = profile

    def validate_tank_current_t(
        self,
        tank_catalog: pd.DataFrame,
        current_t_sensor: pd.DataFrame,
    ) -> List[ValidationIssue]:
        """
        Validate current_t consistency.
        - Sensor data vs catalog capacity
        - Physical constraints (0 <= current_t <= Cap_t)
        """
        issues: List[ValidationIssue] = []

        if tank_catalog.empty or "Tank" not in tank_catalog.columns:
            issues.append(
                ValidationIssue(
                    severity="CRITICAL",
                    category="INPUT",
                    message="Tank catalog missing or invalid",
                    details="Tank catalog must include a Tank column",
                    suggestion="Regenerate tank_ssot_for_solver.csv",
                )
            )
            return issues

        cap_col = _first_existing_column(tank_catalog, ["Cap_t", "Capacity_t"])
        if cap_col is None:
            issues.append(
                ValidationIssue(
                    severity="CRITICAL",
                    category="INPUT",
                    message="Tank capacity column missing",
                    details="Expected Cap_t or Capacity_t in tank catalog",
                    suggestion="Regenerate tank_ssot_for_solver.csv from tank catalog",
                )
            )
            return issues

        if current_t_sensor.empty or "Tank" not in current_t_sensor.columns:
            issues.append(
                ValidationIssue(
                    severity="WARNING",
                    category="INPUT",
                    message="Current_t sensor data missing or empty",
                    details="No sensor rows available for validation",
                    suggestion="Provide sensors/current_t_sensor.csv if available",
                )
            )
            return issues

        if "Current_t" not in current_t_sensor.columns:
            issues.append(
                ValidationIssue(
                    severity="CRITICAL",
                    category="INPUT",
                    message="Current_t column missing in sensor CSV",
                    details="Expected columns: Tank, Current_t",
                    suggestion="Fix sensors/current_t_sensor.csv export",
                )
            )
            return issues

        catalog_tanks = set(tank_catalog["Tank"].astype(str).str.strip().values)
        sensor_tanks = set(current_t_sensor["Tank"].astype(str).str.strip().values)

        missing_in_sensor = catalog_tanks - sensor_tanks
        if missing_in_sensor:
            issues.append(
                ValidationIssue(
                    severity="CRITICAL",
                    category="INPUT",
                    message=f"{len(missing_in_sensor)} tanks missing in current_t_sensor.csv",
                    details=f"Missing: {', '.join(sorted(missing_in_sensor))}",
                    suggestion="Add all tanks to current_t_sensor.csv or verify catalog",
                )
            )

        extra_in_sensor = sensor_tanks - catalog_tanks
        if extra_in_sensor:
            issues.append(
                ValidationIssue(
                    severity="WARNING",
                    category="INPUT",
                    message=f"{len(extra_in_sensor)} unknown tanks in sensor data",
                    details=f"Extra: {', '.join(sorted(extra_in_sensor))}",
                    suggestion="Remove unknown tanks or update tank catalog",
                )
            )

        # Check current_t vs capacity
        sensor_map = (
            current_t_sensor.set_index("Tank")["Current_t"]
            .apply(pd.to_numeric, errors="coerce")
            .to_dict()
        )
        for _, row in tank_catalog.iterrows():
            tank_id = str(row.get("Tank", "")).strip()
            if not tank_id or tank_id not in sensor_map:
                continue
            cap_t = _safe_float(row.get(cap_col), None)
            current_t = _safe_float(sensor_map.get(tank_id), None)
            if cap_t is None or current_t is None:
                continue

            if current_t < 0:
                issues.append(
                    ValidationIssue(
                        severity="CRITICAL",
                        category="INPUT",
                        message=f"Negative current_t for {tank_id}",
                        details=f"Current_t={current_t:.2f}t (must be >= 0)",
                        suggestion="Check sensor calibration or data entry",
                    )
                )

            if current_t > cap_t * 1.05:
                issues.append(
                    ValidationIssue(
                        severity="CRITICAL",
                        category="INPUT",
                        message=f"Overfilled tank {tank_id}",
                        details=f"Current_t={current_t:.2f}t > Cap_t={cap_t:.2f}t",
                        suggestion="Verify tank sounding or capacity data",
                    )
                )
            elif current_t > cap_t:
                issues.append(
                    ValidationIssue(
                        severity="WARNING",
                        category="INPUT",
                        message=f"Tank {tank_id} near capacity",
                        details=f"Current_t={current_t:.2f}t, Cap_t={cap_t:.2f}t",
                        suggestion="Tank may be at maximum fill",
                    )
                )

        return issues

    def validate_stage_results(self, stage_results: pd.DataFrame) -> List[ValidationIssue]:
        """
        Validate stage_results.csv completeness.
        - Required columns present
        - No NaN in critical fields
        - Stage naming consistency
        """
        issues: List[ValidationIssue] = []

        if stage_results.empty:
            issues.append(
                ValidationIssue(
                    severity="CRITICAL",
                    category="INPUT",
                    message="stage_results.csv is empty",
                    details="No rows found",
                    suggestion="Regenerate stage_results.csv from TR Excel",
                )
            )
            return issues

        stage_col = _first_existing_column(stage_results, ["Stage", "StageName"])
        tmean_col = _first_existing_column(stage_results, ["Tmean_m"])
        trim_col = _first_existing_column(stage_results, ["Trim_cm", "Trim"])

        missing_cols = []
        for label, col in (
            ("Stage", stage_col),
            ("Tmean_m", tmean_col),
            ("Trim_cm", trim_col),
        ):
            if col is None:
                missing_cols.append(label)

        if missing_cols:
            issues.append(
                ValidationIssue(
                    severity="CRITICAL",
                    category="INPUT",
                    message="Missing required columns in stage_results.csv",
                    details=f"Missing: {', '.join(missing_cols)}",
                    suggestion="Regenerate stage_results.csv from TR Excel",
                )
            )
            return issues

        for col in (stage_col, tmean_col, trim_col):
            nan_count = stage_results[col].isna().sum()
            if nan_count > 0:
                issues.append(
                    ValidationIssue(
                        severity="CRITICAL",
                        category="INPUT",
                        message=f"NaN values in {col}",
                        details=f"{nan_count} rows with missing {col} data",
                        suggestion="Check TR Excel calculation or export logic",
                    )
                )

        stage_names = stage_results[stage_col].astype(str).values
        critical_stages = [
            s
            for s in stage_names
            if "critical" in s.lower() or "6a" in s.lower()
        ]
        if not critical_stages:
            issues.append(
                ValidationIssue(
                    severity="WARNING",
                    category="INPUT",
                    message="No critical stages identified",
                    details="Stage names do not contain 'critical' or '6A' markers",
                    suggestion="Verify stage naming or Gate-B applicability rules",
                )
            )

        return issues


class PhysicsValidator:
    """Validate physical consistency of calculations."""

    def __init__(self, profile: SiteProfile):
        self.profile = profile
        self.MTC = 34.00
        self.LCF_from_mid = 0.76
        self.TPC = 8.00
        self.Lpp = 60.302
        self.D_vessel = 3.65

    def validate_draft_calculation(
        self,
        displ_t: float,
        tmean_m: float,
        trim_cm: float,
        hydro_table: pd.DataFrame,
    ) -> List[ValidationIssue]:
        """
        Verify drafts are physically consistent.
        - Displacement matches hydrostatic table
        - Trim calculation matches Method B
        """
        issues: List[ValidationIssue] = []

        draft_col = _first_existing_column(hydro_table, ["Draft_m", "Tmean_m"])
        disp_col = _first_existing_column(hydro_table, ["Displ_t", "Disp_t"])
        tpc_col = _first_existing_column(hydro_table, ["TPC_t_per_cm"])

        if draft_col is None or disp_col is None:
            issues.append(
                ValidationIssue(
                    severity="WARNING",
                    category="PHYSICS",
                    message="Hydro table missing Draft/Displacement columns",
                    details="Expected Draft_m or Tmean_m, and Displ_t or Disp_t",
                    suggestion="Verify Hydro_Table_Engineering.json structure",
                )
            )
            return issues

        hydro_table_sorted = hydro_table.sort_values(draft_col)
        closest_idx = (hydro_table_sorted[draft_col] - tmean_m).abs().idxmin()
        hydro_row = hydro_table_sorted.loc[closest_idx]

        hydro_displ = _safe_float(hydro_row.get(disp_col), None)
        if hydro_displ is None:
            return issues

        tpc_val = _safe_float(hydro_row.get(tpc_col), None) if tpc_col else None
        tpc_use = tpc_val if tpc_val is not None else self.TPC

        displ_error_t = abs(displ_t - hydro_displ)
        if displ_error_t > tpc_use * 5:
            issues.append(
                ValidationIssue(
                    severity="WARNING",
                    category="PHYSICS",
                    message="Displacement mismatch with hydro table",
                    details=(
                        f"Calc: {displ_t:.1f}t, Hydro: {hydro_displ:.1f}t "
                        f"(delta={displ_error_t:.1f}t)"
                    ),
                    suggestion="Check weight calculation for missing components",
                )
            )

        if tmean_m > self.D_vessel:
            issues.append(
                ValidationIssue(
                    severity="CRITICAL",
                    category="PHYSICS",
                    message="Tmean exceeds vessel molded depth",
                    details=f"Tmean={tmean_m:.3f}m > D_vessel={self.D_vessel:.3f}m",
                    suggestion="Check displacement or hydro table data",
                )
            )

        trim_m = trim_cm / 100.0
        slope = trim_m / self.Lpp
        x_fp = -self.Lpp / 2.0
        x_ap = self.Lpp / 2.0

        dfwd_calc = tmean_m + slope * (x_fp - self.LCF_from_mid)
        daft_calc = tmean_m + slope * (x_ap - self.LCF_from_mid)

        if dfwd_calc > self.D_vessel or daft_calc > self.D_vessel:
            issues.append(
                ValidationIssue(
                    severity="CRITICAL",
                    category="PHYSICS",
                    message="Draft exceeds D_vessel after Method B calculation",
                    details=(
                        f"FWD={dfwd_calc:.3f}m, AFT={daft_calc:.3f}m "
                        f"(D_vessel={self.D_vessel:.3f}m)"
                    ),
                    suggestion="Check trim calculation or apply clipping",
                )
            )

        return issues

    def validate_trim_moment(self, weights: pd.DataFrame) -> List[ValidationIssue]:
        """
        Validate trimming moment calculation.
        - LCG from midship convention (AFT positive)
        - Trim = TM / MTC consistency
        """
        issues: List[ValidationIssue] = []

        if "w_t" not in weights.columns or "x_from_mid_m" not in weights.columns:
            issues.append(
                ValidationIssue(
                    severity="CRITICAL",
                    category="PHYSICS",
                    message="Missing weight/LCG columns for trim validation",
                    details="Expected w_t and x_from_mid_m columns",
                    suggestion="Ensure weights DataFrame is provided",
                )
            )
            return issues

        tm_lcf = float((weights["w_t"] * (weights["x_from_mid_m"] - self.LCF_from_mid)).sum())
        trim_calc_cm = tm_lcf / self.MTC

        issues.append(
            ValidationIssue(
                severity="INFO",
                category="PHYSICS",
                message="Calculated trim from weights",
                details=f"TM_LCF={tm_lcf:.1f} t*m, Trim={trim_calc_cm:.1f} cm",
                suggestion="Compare with stage_results.csv Trim_cm for consistency",
            )
        )

        return issues


class GatePreflightValidator:
    """Preflight gate feasibility check."""

    def __init__(self, profile: SiteProfile):
        self.profile = profile
        self.gates = profile.data.get("gates", [])

    def preflight_gate_check(self, stage_results: pd.DataFrame) -> List[ValidationIssue]:
        """
        Check if stages can possibly satisfy gates (before solver).
        """
        issues: List[ValidationIssue] = []

        fwd_max = next(
            (
                g.get("limit_value")
                for g in self.gates
                if g.get("gate_id") == "FWD_MAX_2p70_critical_only"
            ),
            2.70,
        )
        aft_min = next(
            (
                g.get("limit_value")
                for g in self.gates
                if g.get("gate_id") == "AFT_MIN_2p70_propulsion"
            ),
            2.70,
        )

        stage_col = _first_existing_column(stage_results, ["Stage", "StageName"])
        fwd_col = _first_existing_column(
            stage_results, ["Draft_FWD_m", "Dfwd_m", "Fwd Draft(m)", "FWD_Height_m"]
        )
        aft_col = _first_existing_column(
            stage_results, ["Draft_AFT_m", "Daft_m", "Aft Draft(m)", "AFT_Height_m"]
        )

        if stage_col is None or fwd_col is None or aft_col is None:
            issues.append(
                ValidationIssue(
                    severity="WARNING",
                    category="GATE",
                    message="Stage draft columns missing for gate preflight",
                    details="Expected Draft_FWD_m/Dfwd_m and Draft_AFT_m/Daft_m",
                    suggestion="Regenerate stage_results.csv with draft columns",
                )
            )
            return issues

        for _, row in stage_results.iterrows():
            stage = str(row.get(stage_col, ""))
            dfwd_raw = _safe_float(row.get(fwd_col), 0.0) or 0.0
            daft_raw = _safe_float(row.get(aft_col), 0.0) or 0.0

            is_critical = "critical" in stage.lower() or "6a" in stage.lower()

            if is_critical and dfwd_raw > fwd_max:
                excess_cm = (dfwd_raw - fwd_max) * 100.0
                issues.append(
                    ValidationIssue(
                        severity="CRITICAL",
                        category="GATE",
                        message=f"Gate-B violation in {stage} (raw, before solver)",
                        details=(
                            f"FWD={dfwd_raw:.3f}m > {fwd_max:.2f}m "
                            f"(excess {excess_cm:.1f}cm)"
                        ),
                        suggestion="Solver must discharge FWD or fill AFT to meet Gate-B",
                    )
                )

            if daft_raw < aft_min:
                deficit_cm = (aft_min - daft_raw) * 100.0
                issues.append(
                    ValidationIssue(
                        severity="CRITICAL",
                        category="GATE",
                        message=f"Gate-A violation in {stage} (raw, before solver)",
                        details=(
                            f"AFT={daft_raw:.3f}m < {aft_min:.2f}m "
                            f"(deficit {deficit_cm:.1f}cm)"
                        ),
                        suggestion="Solver must fill AFT tanks or discharge FWD to meet Gate-A",
                    )
                )

        return issues


class SSOTVersionValidator:
    """Validate SSOT profile version and schema compliance."""

    @staticmethod
    def validate_ssot_version(
        profile_path: str, required_version: str = "v1.0"
    ) -> List[ValidationIssue]:
        issues: List[ValidationIssue] = []

        if not profile_path:
            return issues

        if not Path(profile_path).exists():
            issues.append(
                ValidationIssue(
                    severity="CRITICAL",
                    category="SSOT",
                    message="SSOT profile not found",
                    details=f"Path: {profile_path}",
                    suggestion="Verify profile path or create AGI profile",
                )
            )
            return issues

        profile_data = json.loads(Path(profile_path).read_text(encoding="utf-8"))

        profile_version = profile_data.get("version", "unknown")
        if profile_version != required_version:
            issues.append(
                ValidationIssue(
                    severity="WARNING",
                    category="SSOT",
                    message="SSOT profile version mismatch",
                    details=f"Profile: {profile_version}, Required: {required_version}",
                    suggestion="Update profile or verify compatibility",
                )
            )

        required_sections = ["gates", "draft_calc", "hydro", "ballast"]
        missing_sections = [s for s in required_sections if s not in profile_data]
        if missing_sections:
            issues.append(
                ValidationIssue(
                    severity="CRITICAL",
                    category="SSOT",
                    message="Missing required sections in SSOT profile",
                    details=f"Missing: {', '.join(missing_sections)}",
                    suggestion="Update profile to SSOT Phase 1 schema",
                )
            )

        return issues


def run_full_validation(
    profile_path: str,
    tank_catalog: pd.DataFrame,
    current_t_sensor: pd.DataFrame,
    stage_results: pd.DataFrame,
    hydro_table: pd.DataFrame,
) -> ValidationReport:
    """
    Run all validation checks.

    Returns:
        ValidationReport with pass/fail and all issues.
    """
    all_issues: List[ValidationIssue] = []

    try:
        if profile_path:
            profile = SiteProfile(profile_path)
        else:
            profile = load_agi_profile()
    except Exception as e:
        all_issues.append(
            ValidationIssue(
                severity="CRITICAL",
                category="SSOT",
                message="Failed to load SSOT profile",
                details=str(e),
                suggestion="Check profile JSON syntax and schema",
            )
        )
        return ValidationReport(
            passed=False,
            issues=all_issues,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )

    all_issues.extend(SSOTVersionValidator.validate_ssot_version(profile_path))

    input_validator = InputValidator(profile)
    all_issues.extend(input_validator.validate_tank_current_t(tank_catalog, current_t_sensor))
    all_issues.extend(input_validator.validate_stage_results(stage_results))

    physics_validator = PhysicsValidator(profile)
    tmean_col = _first_existing_column(stage_results, ["Tmean_m"])
    trim_col = _first_existing_column(stage_results, ["Trim_cm", "Trim"])
    displ_col = _first_existing_column(stage_results, ["W_stage_t", "W_Total_t", "Disp_t"])

    if tmean_col and trim_col and displ_col:
        for _, row in stage_results.iterrows():
            displ_t = _safe_float(row.get(displ_col), 0.0) or 0.0
            tmean_m = _safe_float(row.get(tmean_col), 0.0) or 0.0
            trim_cm = _safe_float(row.get(trim_col), 0.0) or 0.0
            all_issues.extend(
                physics_validator.validate_draft_calculation(
                    displ_t, tmean_m, trim_cm, hydro_table
                )
            )
    else:
        all_issues.append(
            ValidationIssue(
                severity="WARNING",
                category="PHYSICS",
                message="Skipping draft physics validation",
                details="Missing displacement/Tmean/Trim columns in stage_results.csv",
                suggestion="Ensure stage_results.csv includes W_stage_t, Tmean_m, Trim_cm",
            )
        )

    gate_validator = GatePreflightValidator(profile)
    all_issues.extend(gate_validator.preflight_gate_check(stage_results))

    critical_issues = [i for i in all_issues if i.severity == "CRITICAL"]
    passed = len(critical_issues) == 0

    return ValidationReport(
        passed=passed,
        issues=all_issues,
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )


def print_validation_report(report: ValidationReport) -> None:
    """Print validation report."""
    print("\n" + "=" * 80)
    print("BALLAST PIPELINE VALIDATION REPORT (B+ PREFLIGHT)")
    print("=" * 80)
    print(f"Timestamp: {report.timestamp}")
    print(f"Status: {report.summary()}")
    print("=" * 80)

    if report.passed:
        print("\nALL CHECKS PASSED - Pipeline ready for execution\n")
    else:
        print("\nVALIDATION FAILED - Critical issues must be resolved\n")

    critical = report.get_critical_issues()
    if critical:
        print(f"\nCRITICAL ISSUES ({len(critical)}):")
        print("-" * 80)
        for i, issue in enumerate(critical, 1):
            print(f"\n[{i}] {issue.category}: {issue.message}")
            print(f"    Details: {issue.details}")
            print(f"    Suggestion: {issue.suggestion}")

    warnings = report.get_warnings()
    if warnings:
        print(f"\nWARNINGS ({len(warnings)}):")
        print("-" * 80)
        for i, issue in enumerate(warnings, 1):
            print(f"\n[{i}] {issue.category}: {issue.message}")
            print(f"    Details: {issue.details}")
            print(f"    Suggestion: {issue.suggestion}")

    print("\n" + "=" * 80 + "\n")


if __name__ == "__main__":
    print("SSOT Validators (P1-1)")
    print("Use in integrated pipeline B+ preflight mode")
