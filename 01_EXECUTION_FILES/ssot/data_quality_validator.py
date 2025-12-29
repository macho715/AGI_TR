#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Data Quality Validator - 검증 결과 데이터 적합성 확인
Registry 스키마 검증 후 실제 데이터 값의 적합성을 검증
"""

import sys
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
import pandas as pd
from openpyxl import load_workbook

from ssot.headers_registry import load_registry, HeaderRegistry


class DataQualityValidator:
    """데이터 적합성 검증 (타입, 범위, 일관성)"""

    def __init__(self, registry_path: Path):
        self.registry: HeaderRegistry = load_registry(registry_path)
        self.issues = {"errors": [], "warnings": [], "info": []}

    def validate_numeric_range(
        self,
        value: Any,
        field_key: str,
        min_val: Optional[float] = None,
        max_val: Optional[float] = None,
    ) -> Tuple[bool, Optional[str]]:
        """숫자 값의 범위 검증"""
        if pd.isna(value):
            return True, None  # NaN은 별도로 처리

        try:
            num_val = float(value)
            if min_val is not None and num_val < min_val:
                return False, f"Value {num_val} < minimum {min_val}"
            if max_val is not None and num_val > max_val:
                return False, f"Value {num_val} > maximum {max_val}"
            return True, None
        except (ValueError, TypeError):
            return False, f"Cannot convert to float: {value}"

    def validate_enum(
        self, value: Any, allowed_values: List[str], case_sensitive: bool = False
    ) -> Tuple[bool, Optional[str]]:
        """열거형 값 검증"""
        if pd.isna(value):
            return True, None

        val_str = str(value).strip()
        if not case_sensitive:
            val_str = val_str.upper()
            allowed_upper = [v.upper() for v in allowed_values]
            if val_str not in allowed_upper:
                return False, f"Value '{value}' not in allowed values: {allowed_values}"
        else:
            if val_str not in allowed_values:
                return False, f"Value '{value}' not in allowed values: {allowed_values}"

        return True, None

    def validate_required_field(
        self, value: Any, field_name: str
    ) -> Tuple[bool, Optional[str]]:
        """필수 필드 존재 여부 검증"""
        if pd.isna(value) or (isinstance(value, str) and value.strip() == ""):
            return False, f"Required field '{field_name}' is empty"
        return True, None

    def validate_ballast_exec_csv(self, file_path: Path) -> Dict[str, Any]:
        """BALLAST_EXEC.csv 데이터 적합성 검증"""
        results = {
            "file": str(file_path.name),
            "deliverable_id": "BALLAST_EXEC_CSV",
            "errors": [],
            "warnings": [],
            "info": [],
        }

        try:
            df = pd.read_csv(file_path, encoding="utf-8-sig")

            # 1. Stage 필수 필드 검증
            empty_stage = df["Stage"].isna() | (
                df["Stage"].astype(str).str.strip() == ""
            )
            if empty_stage.any():
                results["errors"].append(
                    f"Stage column has {empty_stage.sum()} empty values (required field)"
                )

            # 2. Step 타입 및 범위 검증
            if "Step" in df.columns:
                if not pd.api.types.is_integer_dtype(df["Step"]):
                    results["warnings"].append("Step column is not integer type")
                if (df["Step"] < 1).any():
                    results["errors"].append("Step values must be >= 1")

            # 3. Action 값 검증
            if "Action" in df.columns:
                valid_actions = ["FILL", "DISCHARGE", "DEBALLAST"]
                for idx, action in df["Action"].items():
                    ok, msg = self.validate_enum(
                        action, valid_actions, case_sensitive=False
                    )
                    if not ok:
                        results["warnings"].append(f"Row {idx+2}: {msg}")

            # 4. Delta_t 범위 검증
            if "Delta_t" in df.columns:
                negative_delta = df["Delta_t"] < 0
                if negative_delta.any():
                    results["warnings"].append(
                        f"Delta_t has {negative_delta.sum()} negative values"
                    )

            # 5. Time_h 범위 검증
            if "Time_h" in df.columns:
                negative_time = df["Time_h"] < 0
                if negative_time.any():
                    results["errors"].append(
                        f"Time_h has {negative_time.sum()} negative values"
                    )
                # Time_h = Delta_t / PumpRate 검증 (대략적)
                if "Delta_t" in df.columns:
                    # PumpRate가 없으면 기본값 10 t/h 가정
                    pump_rate = 10.0
                    expected_time = df["Delta_t"] / pump_rate
                    time_diff = abs(df["Time_h"] - expected_time)
                    large_diff = time_diff > 0.1  # 0.1시간 이상 차이
                    if large_diff.any():
                        results["warnings"].append(
                            f"Time_h calculation mismatch in {large_diff.sum()} rows "
                            f"(expected ≈ Delta_t / {pump_rate})"
                        )

            # 6. Start_t, Target_t 일관성 검증
            if (
                "Start_t" in df.columns
                and "Target_t" in df.columns
                and "Delta_t" in df.columns
            ):
                expected_target = df["Start_t"] + df["Delta_t"]
                target_diff = abs(df["Target_t"] - expected_target)
                large_diff = target_diff > 0.01  # 0.01t 이상 차이
                if large_diff.any():
                    results["errors"].append(
                        f"Target_t = Start_t + Delta_t mismatch in {large_diff.sum()} rows"
                    )

            # 7. 통계 정보
            results["info"].append(f"Total rows: {len(df)}")
            if "Delta_t" in df.columns:
                results["info"].append(
                    f"Delta_t range: {df['Delta_t'].min():.2f} ~ {df['Delta_t'].max():.2f} t"
                )
            if "Time_h" in df.columns:
                results["info"].append(
                    f"Time_h range: {df['Time_h'].min():.2f} ~ {df['Time_h'].max():.2f} h"
                )

        except Exception as e:
            results["errors"].append(f"Error reading file: {type(e).__name__}: {e}")

        return results

    def validate_ballast_option_csv(self, file_path: Path) -> Dict[str, Any]:
        """BALLAST_OPTION.csv 데이터 적합성 검증"""
        results = {
            "file": str(file_path.name),
            "deliverable_id": "BALLAST_OPTION_CSV",
            "errors": [],
            "warnings": [],
            "info": [],
        }

        try:
            df = pd.read_csv(file_path, encoding="utf-8-sig")

            # 1. Stage 필수 필드 검증
            empty_stage = df["Stage"].isna() | (
                df["Stage"].astype(str).str.strip() == ""
            )
            if empty_stage.any():
                results["errors"].append(
                    f"Stage column has {empty_stage.sum()} empty values (required field)"
                )

            # 2. Priority 값 검증
            if "Priority" in df.columns:
                valid_priorities = [1, 2, 3, 5]  # 문서 기준
                invalid_priority = ~df["Priority"].isin(valid_priorities)
                if invalid_priority.any():
                    results["warnings"].append(
                        f"Priority has {invalid_priority.sum()} invalid values "
                        f"(expected: {valid_priorities})"
                    )

            # 3. PumpRate_tph 범위 검증
            if "PumpRate_tph" in df.columns:
                negative_rate = df["PumpRate_tph"] <= 0
                if negative_rate.any():
                    results["errors"].append(
                        f"PumpRate_tph has {negative_rate.sum()} non-positive values"
                    )

            # 4. Delta_t 범위 검증
            if "Delta_t" in df.columns:
                negative_delta = df["Delta_t"] < 0
                if negative_delta.any():
                    results["warnings"].append(
                        f"Delta_t has {negative_delta.sum()} negative values"
                    )

            # 통계 정보
            results["info"].append(f"Total rows: {len(df)}")
            if "Priority" in df.columns:
                priority_counts = df["Priority"].value_counts().to_dict()
                results["info"].append(f"Priority distribution: {priority_counts}")

        except Exception as e:
            results["errors"].append(f"Error reading file: {type(e).__name__}: {e}")

        return results

    def tidy_and_validate_ballast_sequence(
        self,
        file_path: Path,
        tank_catalog_path: Optional[Path] = None,
        deliverable_id: str = "BALLAST_EXEC_CSV",
    ) -> Dict[str, Any]:
        """
        Tidying + Validation pipeline for BALLAST_EXEC.csv or BALLAST_OPTION.csv

        Steps:
        1. Load raw CSV
        2. Tidy (dates, decimals, action case, tank IDs)
        3. Validate with Pydantic schema
        4. Cross-validate with tank catalog (operability, Max_t)
        5. Generate LLM-ready context (only if validation passed)

        Returns:
            Dict with tidying/validation results and LLM context
        """
        try:
            from ssot.tidying_models import (
                LogiDataTider,
                BallastSequenceRow,
                TankCatalogRow,
                TankOperability,
                BallastAction,
            )
        except ImportError:
            return {
                "file": str(file_path.name),
                "deliverable_id": deliverable_id,
                "tidying": {
                    "errors": [
                        "Pydantic not installed. Install with: pip install pydantic>=2.0.0"
                    ],
                    "warnings": [],
                },
                "validation": {"errors": [], "warnings": []},
                "cross_validation": {"errors": [], "warnings": []},
                "llm_context": None,
                "validated_count": 0,
                "total_rows": 0,
            }

        results = {
            "file": str(file_path.name),
            "deliverable_id": deliverable_id,
            "tidying": {"errors": [], "warnings": []},
            "validation": {"errors": [], "warnings": []},
            "cross_validation": {"errors": [], "warnings": []},
            "llm_context": None,
            "validated_count": 0,
            "total_rows": 0,
        }

        try:
            # Step 1: Load raw CSV
            df_raw = pd.read_csv(file_path, encoding="utf-8-sig")
            results["total_rows"] = len(df_raw)

            # Step 2: Tidying
            tider = LogiDataTider(df_raw)
            tider.tidy_action_case("Action")
            tider.tidy_tank_ids("Tank")
            tider.tidy_decimal_columns(
                [
                    "Start_t",
                    "Delta_t",
                    "Target_t",
                    "PumpRate_tph",
                    "Time_h",
                    "Draft_FWD",
                    "Draft_AFT",
                    "Trim_cm",
                    "UKC",
                ],
                decimal_places=2,
            )
            results["tidying"]["warnings"] = tider.warnings

            # Step 3: Validate with Pydantic schema
            # Build column mapping dynamically based on available columns
            column_mapping = {}
            available_cols = set(tider.df.columns)

            # Map available columns only
            col_map_defs = {
                "Stage": "stage",
                "Step": "step",
                "Tank": "tank",
                "Action": "action",
                "Start_t": "start_t",
                "Delta_t": "delta_t",
                "Target_t": "target_t",
                "Pump_ID": "pump_id",
                "PumpRate_tph": "pump_rate_tph",
                "Time_h": "time_h",
                "Valve_Lineup": "valve_lineup",
                "Draft_FWD": "draft_fwd",
                "Draft_AFT": "draft_aft",
                "Trim_cm": "trim_cm",
                "UKC": "ukc",
                "Hold_Point": "hold_point",
                "Notes": "notes",
                "Priority": "priority",
                "Rationale": "rationale",
            }

            for csv_col, model_field in col_map_defs.items():
                if csv_col in available_cols:
                    column_mapping[csv_col] = model_field

            validated_rows, validation_errors = tider.validate_with_schema(
                BallastSequenceRow, column_mapping=column_mapping
            )
            results["validation"]["errors"] = validation_errors
            results["validated_count"] = len(validated_rows)

            # Step 4: Cross-validate with tank catalog (VOID3 operability check)
            if tank_catalog_path and tank_catalog_path.exists():
                try:
                    tank_catalog_df = pd.read_csv(
                        tank_catalog_path, encoding="utf-8-sig"
                    )
                    tank_catalog_tider = LogiDataTider(tank_catalog_df)
                    tank_catalog_rows, _ = tank_catalog_tider.validate_with_schema(
                        TankCatalogRow, column_mapping={"Tank": "tank_id"}
                    )

                    # Build tank lookup
                    tank_lookup = {t.tank_id: t for t in tank_catalog_rows}

                    # Check VOID3 operability violations
                    for row in validated_rows:
                        if row.tank.startswith("VOID3"):
                            tank_info = tank_lookup.get(row.tank)
                            if tank_info:
                                if (
                                    tank_info.operability
                                    == TankOperability.PRE_BALLAST_ONLY
                                ):
                                    if row.action != BallastAction.NONE:
                                        results["cross_validation"]["errors"].append(
                                            f"Row {row.step or 'N/A'}: {row.tank} has action={row.action.value} "
                                            f"but operability=PRE_BALLAST_ONLY (should be NONE)"
                                        )

                                # Check Target_t <= Max_t (if Target_t present)
                                if (
                                    row.target_t is not None
                                    and row.target_t > tank_info.max_t
                                ):
                                    results["cross_validation"]["errors"].append(
                                        f"Row {row.step or 'N/A'}: {row.tank} Target_t={row.target_t} > Max_t={tank_info.max_t}"
                                    )
                except Exception as e:
                    results["cross_validation"]["warnings"].append(
                        f"Tank catalog cross-validation failed: {type(e).__name__}: {e}"
                    )

            # Step 5: Generate LLM-ready context (only if validation passed)
            if (
                not results["validation"]["errors"]
                and not results["cross_validation"]["errors"]
                and len(validated_rows) > 0
            ):
                results["llm_context"] = tider.to_llm_markdown(max_rows=50)
            else:
                results["llm_context"] = (
                    None  # Fail-fast: no LLM input if validation failed
                )

            return results

        except Exception as e:
            results["tidying"]["errors"].append(
                f"Tidying pipeline failed: {type(e).__name__}: {e}"
            )
            return results

    def validate_solver_summary_csv(self, file_path: Path) -> Dict[str, Any]:
        """solver_ballast_summary.csv 데이터 적합성 검증"""
        results = {
            "file": str(file_path.name),
            "deliverable_id": "SOLVER_SUMMARY_CSV",
            "errors": [],
            "warnings": [],
            "info": [],
        }

        try:
            df = pd.read_csv(file_path, encoding="utf-8-sig")

            # 1. UKC_min_m 범위 검증 (일반적으로 > 0)
            if "UKC_min_m" in df.columns:
                negative_ukc = df["UKC_min_m"] < 0
                if negative_ukc.any():
                    results["errors"].append(
                        f"UKC_min_m has {negative_ukc.sum()} negative values (safety issue)"
                    )
                low_ukc = (df["UKC_min_m"] > 0) & (df["UKC_min_m"] < 0.5)
                if low_ukc.any():
                    results["warnings"].append(
                        f"UKC_min_m has {low_ukc.sum()} values < 0.5m (low UKC warning)"
                    )

            # 2. Forecast_tide_m 범위 검증
            if "Forecast_tide_m" in df.columns:
                extreme_tide = (df["Forecast_tide_m"] < -1) | (
                    df["Forecast_tide_m"] > 5
                )
                if extreme_tide.any():
                    results["warnings"].append(
                        f"Forecast_tide_m has {extreme_tide.sum()} extreme values "
                        f"(outside typical range -1 to 5m)"
                    )

            # 3. Plan_Rows 검증
            if "Plan_Rows" in df.columns:
                empty_plans = df["Plan_Rows"] == 0
                if empty_plans.any():
                    stages = df.loc[empty_plans, "Stage"].tolist()
                    results["warnings"].append(
                        f"Empty plans (Plan_Rows=0) for stages: {stages}"
                    )

            # 4. Tide_verification 값 검증
            if "Tide_verification" in df.columns:
                invalid_verification = ~df["Tide_verification"].isin(
                    ["OK", "FAIL", "WARNING"]
                )
                if invalid_verification.any():
                    results["warnings"].append(
                        f"Tide_verification has {invalid_verification.sum()} unexpected values"
                    )

            # 통계 정보
            results["info"].append(f"Total rows: {len(df)}")
            if "UKC_min_m" in df.columns:
                results["info"].append(
                    f"UKC_min_m range: {df['UKC_min_m'].min():.2f} ~ {df['UKC_min_m'].max():.2f} m"
                )

        except Exception as e:
            results["errors"].append(f"Error reading file: {type(e).__name__}: {e}")

        return results

    def validate_solver_plan_csv(self, file_path: Path) -> Dict[str, Any]:
        """solver_ballast_stage_plan.csv 데이터 적합성 검증"""
        results = {
            "file": str(file_path.name),
            "deliverable_id": "SOLVER_PLAN_CSV",
            "errors": [],
            "warnings": [],
            "info": [],
        }

        try:
            df = pd.read_csv(file_path, encoding="utf-8-sig")

            # 1. Action 값 검증 (대소문자 일관성)
            if "Action" in df.columns:
                valid_actions = ["FILL", "DISCHARGE", "DEBALLAST"]
                action_values = df["Action"].unique()
                for action in action_values:
                    ok, msg = self.validate_enum(
                        action, valid_actions, case_sensitive=False
                    )
                    if not ok:
                        results["warnings"].append(
                            f"Action value '{action}' should be uppercase (FILL/DISCHARGE)"
                        )
                    elif action != action.upper():
                        results["warnings"].append(
                            f"Action value '{action}' is not uppercase (should be '{action.upper()}')"
                        )

            # 2. Delta_t 범위 검증
            if "Delta_t" in df.columns:
                negative_delta = df["Delta_t"] < 0
                if negative_delta.any():
                    results["warnings"].append(
                        f"Delta_t has {negative_delta.sum()} negative values"
                    )

            # 3. PumpTime_h 범위 검증
            if "PumpTime_h" in df.columns:
                negative_time = df["PumpTime_h"] < 0
                if negative_time.any():
                    results["errors"].append(
                        f"PumpTime_h has {negative_time.sum()} negative values"
                    )

            # 통계 정보
            results["info"].append(f"Total rows: {len(df)}")
            if "PumpTime_h" in df.columns:
                results["info"].append(
                    f"PumpTime_h range: {df['PumpTime_h'].min():.2f} ~ {df['PumpTime_h'].max():.2f} h"
                )

        except Exception as e:
            results["errors"].append(f"Error reading file: {type(e).__name__}: {e}")

        return results

    def validate_directory(self, dir_path: Path) -> Dict[str, Any]:
        """디렉토리 내 모든 파일 검증"""
        all_results = {
            "timestamp": datetime.now().isoformat(),
            "registry_version": self.registry.version,
            "files_validated": [],
            "summary": {"total_files": 0, "total_errors": 0, "total_warnings": 0},
        }

        # 각 deliverable에 대해 검증
        validators = {
            "BALLAST_EXEC_CSV": self.validate_ballast_exec_csv,
            "BALLAST_OPTION_CSV": self.validate_ballast_option_csv,
            "SOLVER_SUMMARY_CSV": self.validate_solver_summary_csv,
            "SOLVER_PLAN_CSV": self.validate_solver_plan_csv,
        }

        for deliverable_id, validator_func in validators.items():
            d = self.registry.deliverables.get(deliverable_id)
            if not d:
                continue

            file_path = dir_path / d.file_pattern
            if not file_path.exists():
                continue

            all_results["summary"]["total_files"] += 1
            result = validator_func(file_path)
            all_results["files_validated"].append(result)

            all_results["summary"]["total_errors"] += len(result["errors"])
            all_results["summary"]["total_warnings"] += len(result["warnings"])

        return all_results

    def print_summary(self, results: Dict[str, Any]):
        """검증 결과 요약 출력"""
        print("=" * 80)
        print("Data Quality Validation Summary")
        print("=" * 80)
        print(f"Registry Version: {results['registry_version']}")
        print(f"Timestamp: {results['timestamp']}")
        print()
        print("Summary:")
        print(f"  Total files: {results['summary']['total_files']}")
        print(f"  Total errors: {results['summary']['total_errors']}")
        print(f"  Total warnings: {results['summary']['total_warnings']}")
        print()

        for file_result in results["files_validated"]:
            print(f"\n{file_result['file']} ({file_result['deliverable_id']}):")

            if file_result["errors"]:
                print("  ERRORS:")
                for err in file_result["errors"]:
                    print(f"    - {err}")

            if file_result["warnings"]:
                print("  WARNINGS:")
                for warn in file_result["warnings"][:10]:
                    print(f"    - {warn}")
                if len(file_result["warnings"]) > 10:
                    print(f"    ... and {len(file_result['warnings']) - 10} more")

            if file_result["info"]:
                print("  INFO:")
                for info in file_result["info"]:
                    print(f"    - {info}")


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Validate data quality for pipeline outputs"
    )
    parser.add_argument(
        "--registry",
        type=str,
        default="01_EXECUTION_FILES/headers_registry.json",
        help="Path to headers_registry.json",
    )
    parser.add_argument(
        "--final-dir",
        type=str,
        required=True,
        help="Path to output directory to validate",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="DATA_QUALITY_REPORT.json",
        help="Output report file name",
    )

    args = parser.parse_args()

    registry_path = Path(args.registry)
    final_dir = Path(args.final_dir)
    output_path = final_dir / args.output

    if not registry_path.exists():
        print(f"[ERROR] Registry not found: {registry_path}")
        return 1

    if not final_dir.exists():
        print(f"[ERROR] Directory not found: {final_dir}")
        return 1

    validator = DataQualityValidator(registry_path)
    results = validator.validate_directory(final_dir)
    validator.print_summary(results)

    # Save report
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\nReport saved to: {output_path}")

    return 0 if results["summary"]["total_errors"] == 0 else 1


# -----------------------------------------------------------------------------
# Common CSV Tidying Function (for pipeline-wide tidying)
# -----------------------------------------------------------------------------
def tidy_and_validate_csv(
    validator: "DataQualityValidator",
    file_path: Path,
    deliverable_id: Optional[str] = None,
    custom_validators: Optional[List] = None,
) -> Dict[str, Any]:
    """
    범용 CSV tidying 및 검증 함수 (DataQualityValidator 메서드로 사용)

    Args:
        validator: DataQualityValidator 인스턴스
        file_path: 검증할 CSV 파일 경로
        deliverable_id: Deliverable ID (headers registry용)
        custom_validators: 커스텀 검증 함수 리스트

    Returns:
        검증 결과 딕셔너리
    """
    try:
        from ssot.tidying_models import LogiDataTider
    except ImportError:
        return {
            "file": str(file_path.name),
            "deliverable_id": deliverable_id or "GENERIC_CSV",
            "tidying": {
                "errors": [
                    "Pydantic not installed. Install with: pip install pydantic>=2.0.0"
                ],
                "warnings": [],
            },
            "validation": {"errors": [], "warnings": []},
            "llm_context": None,
            "validated_count": 0,
            "total_rows": 0,
        }

    results = {
        "file": str(file_path.name),
        "deliverable_id": deliverable_id or "GENERIC_CSV",
        "tidying": {"errors": [], "warnings": []},
        "validation": {"errors": [], "warnings": []},
        "llm_context": None,
        "validated_count": 0,
        "total_rows": 0,
    }

    try:
        # Load CSV
        df_raw = pd.read_csv(file_path, encoding="utf-8-sig")
        results["total_rows"] = len(df_raw)

        # Basic tidying
        tider = LogiDataTider(df_raw)

        # Auto-detect and tidy common columns
        if "Action" in df_raw.columns:
            tider.tidy_action_case("Action")
        if "Tank" in df_raw.columns:
            tider.tidy_tank_ids("Tank")

        # Tidy decimal columns (auto-detect)
        decimal_cols = [
            col
            for col in df_raw.columns
            if any(
                keyword in col.lower()
                for keyword in [
                    "_t",
                    "_m",
                    "_cm",
                    "rate",
                    "time",
                    "delta",
                    "target",
                    "start",
                    "draft",
                    "trim",
                    "ukc",
                    "capacity",
                ]
            )
        ]
        if decimal_cols:
            tider.tidy_decimal_columns(decimal_cols, decimal_places=2)

        results["tidying"]["warnings"] = tider.warnings

        # Custom validators if provided
        if custom_validators:
            for validator_func in custom_validators:
                try:
                    validator_result = validator_func(tider.df)
                    if isinstance(validator_result, dict):
                        if "errors" in validator_result:
                            results["validation"]["errors"].extend(
                                validator_result["errors"]
                            )
                        if "warnings" in validator_result:
                            results["validation"]["warnings"].extend(
                                validator_result["warnings"]
                            )
                except Exception as e:
                    results["validation"]["warnings"].append(
                        f"Custom validator failed: {type(e).__name__}: {e}"
                    )

        # Generate LLM context if no errors
        if not results["validation"]["errors"]:
            results["llm_context"] = tider.to_llm_markdown(max_rows=50)
            results["validated_count"] = len(tider.df)

        return results

    except Exception as e:
        results["tidying"]["errors"].append(
            f"Tidying pipeline failed: {type(e).__name__}: {e}"
        )
        return results


if __name__ == "__main__":
    sys.exit(main())
