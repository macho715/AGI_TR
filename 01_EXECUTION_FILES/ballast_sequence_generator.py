#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ballast Sequence Generator (P0-2)
Generates step-by-step ballast operations sequence with hold points.
"""

from dataclasses import dataclass
import re
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

OPTIONAL_STAGES = [
    "Stage 6B Tide Window",
]


@dataclass
class BallastStep:
    """Single ballast sequence step."""

    stage: str
    step: int
    tank: str
    action: str  # FILL, DISCHARGE, HOLD, VERIFY
    start_t: float
    delta_t: float
    target_t: float
    pump_id: str
    pump_rate_tph: float
    time_h: float
    valve_lineup: str
    draft_fwd: float
    draft_aft: float
    trim: float
    ukc: float
    hold_point: bool
    notes: str = ""


@dataclass
class BallastOption:
    """Ballast option/plan level entry (Delta_t based)."""

    stage: str
    tank: str
    action: str
    delta_t: float
    pump_rate_tph: float
    priority: int
    rationale: str


def _stage_order_from_df(ballast_plan_df: pd.DataFrame) -> List[str]:
    if "Stage" not in ballast_plan_df.columns:
        return []
    stage_values = ballast_plan_df["Stage"].astype(str).tolist()
    # Filter out empty/nan values
    unique = list(
        dict.fromkeys(
            [
                s
                for s in stage_values
                if s and s.strip() and s.lower() not in ["nan", "none", ""]
            ]
        )
    )
    stage_priority = {
        "Stage 1": 1,
        "Stage 2": 2,
        "Stage 3": 3,
        "Stage 4": 4,
        "Stage 5": 5,
        "Stage 5_PreBallast": 6,
        "Stage 6A_Critical (Opt C)": 7,
        "Stage 6C": 8,
        "Stage 7": 9,
        "Stage 6B Tide Window": 99,
    }
    return sorted(unique, key=lambda s: stage_priority.get(s, 50))


def _tank_current_map(tank_catalog_df: Optional[pd.DataFrame]) -> Dict[str, float]:
    if tank_catalog_df is None:
        return {}

    # "Tank" 또는 "id" 컬럼 지원 (tank_catalog JSON은 "id" 사용)
    tank_col = None
    if "Tank" in tank_catalog_df.columns:
        tank_col = "Tank"
    elif "id" in tank_catalog_df.columns:
        tank_col = "id"
    else:
        return {}

    if "Current_t" not in tank_catalog_df.columns:
        return {}

    tank_map = {}
    for _, row in tank_catalog_df.iterrows():
        tank_name = str(row.get(tank_col, "")).strip()
        if not tank_name:
            continue
        try:
            tank_map[tank_name] = float(row.get("Current_t", 0.0))
        except (TypeError, ValueError):
            tank_map[tank_name] = 0.0
    return tank_map


def _delta_from_row(row: pd.Series) -> float:
    if "Delta_t" in row:
        try:
            val = row.get("Delta_t", 0.0)
            if pd.isna(val):
                return 0.0
            return float(val)
        except (TypeError, ValueError):
            return 0.0
    if "Weight_t" in row:
        try:
            weight_val = row.get("Weight_t", 0.0)
            if pd.isna(weight_val):
                weight = 0.0
            else:
                weight = float(weight_val)
        except (TypeError, ValueError):
            weight = 0.0
        action = str(row.get("Action", "")).strip().lower()
        if "discharge" in action:
            return -abs(weight)
        return abs(weight)
    return 0.0


def _canonical_stage_name(name: str) -> str:
    if not name:
        return ""
    raw = str(name).strip()
    if not raw:
        return ""
    norm = re.sub(r"\s+", " ", raw).strip()
    lower = norm.lower()
    if "6b" in lower and "tide" in lower:
        return "Stage 6B Tide Window"
    if "6a" in lower and "critical" in lower:
        return "Stage 6A_Critical (Opt C)"
    if "6c" in lower:
        return "Stage 6C"
    if "preballast" in lower or "pre ballast" in lower:
        return "Stage 5_PreBallast"
    match = re.match(r"stage\s*(\d+)", lower)
    if match:
        return f"Stage {int(match.group(1))}"
    return norm


def _canonicalize_stage_column(df: pd.DataFrame) -> pd.DataFrame:
    if "Stage" not in df.columns:
        return df
    out = df.copy()

    # Map stage names, but preserve non-empty values
    def _safe_canonical(name):
        if pd.isna(name) or not str(name).strip():
            return ""
        canonical = _canonical_stage_name(str(name))
        # Return canonical if valid, otherwise preserve original if non-empty
        return canonical if canonical and canonical.strip() else str(name).strip()

    out["Stage"] = out["Stage"].map(_safe_canonical)
    return out


def _merge_missing_optional_stages(
    plan_df: pd.DataFrame,
    fallback_df: Optional[pd.DataFrame],
    optional_stages: Optional[List[str]] = None,
) -> pd.DataFrame:
    optional_stages = optional_stages or OPTIONAL_STAGES
    optional_stages = [_canonical_stage_name(s) for s in optional_stages]
    if "Stage" not in plan_df.columns:
        return plan_df

    plan_stages = set(plan_df["Stage"].dropna().astype(str))
    missing = [s for s in optional_stages if s and s not in plan_stages]
    if not missing:
        return plan_df

    if fallback_df is None or fallback_df.empty or "Stage" not in fallback_df.columns:
        print(
            "[WARN] Optional stages missing from plan and no fallback provided: "
            + ", ".join(missing)
        )
        return plan_df

    fallback_rows = fallback_df[fallback_df["Stage"].isin(missing)].copy()
    if fallback_rows.empty:
        print(
            "[WARN] Optional stages missing from plan and fallback: "
            + ", ".join(missing)
        )
        return plan_df

    print(
        "[INFO] Filled optional stages from fallback plan: "
        + ", ".join(sorted(set(fallback_rows["Stage"].astype(str))))
    )
    return pd.concat([plan_df, fallback_rows], ignore_index=True, sort=False)


def _get_stage_pump_rate(stage_name: str, default_pump_rate: float = 10.0) -> float:
    """
    Stage별 pump rate 결정

    - Stage 5_PreBallast: 10 tph (급수차, 운영 시간에 포함되지 않음)
    - Stage 6A (Critical): 150 tph (외부 펌프 임대 100-200 tph, 중간값 사용)
    - 기타: default_pump_rate
    """
    stage_lower = stage_name.lower()

    # Stage 5_PreBallast: 급수차 (10 tph)
    if "preballast" in stage_lower or "5_preballast" in stage_lower:
        return 10.0

    # Stage 6A (Critical): 외부 펌프 임대 (100-200 tph, 중간값 150 tph 사용)
    if "6a" in stage_lower or "critical" in stage_lower:
        return 150.0  # 100-200 tph의 중간값

    # 기타 Stage: 기본값
    return default_pump_rate


def generate_sequence(
    ballast_plan_df: pd.DataFrame,
    profile,
    stage_drafts: Dict[str, Dict[str, float]],
    tank_catalog_df: Optional[pd.DataFrame] = None,
    exclude_optional_stages: bool = True,
    fallback_plan_df: Optional[pd.DataFrame] = None,
) -> List[BallastStep]:
    """
    Generate step-by-step ballast sequence.

    Args:
        ballast_plan_df: Solver/optimizer output (Stage, Tank, Delta_t/Weight_t)
        profile: SiteProfile with pump rates
        stage_drafts: {stage_name: {fwd, aft, trim, ukc}}
        tank_catalog_df: Tank catalog with Current_t (optional)
        fallback_plan_df: Optional fallback plan for missing optional stages

    Returns:
        List of BallastStep objects
    """
    sequence: List[BallastStep] = []
    step_counter = 1

    # Get pump scenario from SSOT (기본값만)
    ballast_params = profile.ballast_params if profile else {}
    default_scenario = ballast_params.get("default_scenario", "A")
    contingency = ballast_params.get("contingency", {})
    scenario_config = contingency.get(default_scenario, {"pump_rate_tph": 10.0})
    default_pump_rate = float(scenario_config.get("pump_rate_tph", 10.0)) or 10.0

    # Get daylight constraint
    daylight_only = bool(ballast_params.get("daylight_only", True))
    daylight_end = str(ballast_params.get("daylight_end", "18:00"))
    daylight_start = str(ballast_params.get("daylight_start", "06:00"))
    try:
        end_hour = int(daylight_end[:2])
        start_hour = int(daylight_start[:2])
    except ValueError:
        end_hour = 18
        start_hour = 6
    max_hours = end_hour - start_hour if daylight_only else 24

    ballast_plan_df = _canonicalize_stage_column(ballast_plan_df)
    fallback_plan_df = (
        _canonicalize_stage_column(fallback_plan_df)
        if fallback_plan_df is not None
        else None
    )
    ballast_plan_df = _merge_missing_optional_stages(
        ballast_plan_df, fallback_plan_df, OPTIONAL_STAGES
    )
    stage_drafts_norm = {_canonical_stage_name(k): v for k, v in stage_drafts.items()}

    cumulative_time = 0.0
    initial_tank_current = _tank_current_map(tank_catalog_df)
    tank_current = dict(initial_tank_current)
    stage_order = _stage_order_from_df(ballast_plan_df)
    if exclude_optional_stages:
        stage_order = [s for s in stage_order if s not in OPTIONAL_STAGES]

    for stage_name in stage_order:
        if not stage_name or not stage_name.strip():
            continue  # Skip empty stage names
        stage_df = ballast_plan_df[ballast_plan_df["Stage"] == stage_name].copy()
        stage_info = stage_drafts_norm.get(stage_name, {})
        stage_tank_current = tank_current

        # Stage별 pump rate 결정
        stage_pump_rate = _get_stage_pump_rate(stage_name, default_pump_rate)
        stage_current_map: Dict[str, float] = {}
        if "Current_t" in stage_df.columns:
            for _, row in stage_df.iterrows():
                tank_id = str(row.get("Tank", "")).strip()
                if not tank_id:
                    continue
                current_t = row.get("Current_t")
                if pd.notna(current_t):
                    try:
                        stage_current_map[tank_id] = float(current_t)
                    except (TypeError, ValueError):
                        continue
        # 수정: stage_current_map이 있는 탱크만 업데이트, 나머지는 이전 stage 상태 유지
        # 이렇게 하면 Stage 6A가 Stage 5_PreBallast의 종료 상태를 사용할 수 있음
        for tank_id, current_t in stage_current_map.items():
            tank_current[tank_id] = current_t
        stage_tank_current = tank_current
        # stage_current_map이 없으면 tank_current는 이전 stage의 상태를 그대로 사용 (carry-forward 유지)

        # Sort by delta magnitude (large changes first for stability)
        if "Delta_t" in stage_df.columns:
            stage_df = stage_df.sort_values(
                "Delta_t", key=lambda s: s.abs(), ascending=False
            )
        elif "Weight_t" in stage_df.columns:
            stage_df = stage_df.sort_values(
                "Weight_t", key=lambda s: s.abs(), ascending=False
            )

        for _, row in stage_df.iterrows():
            tank_id = str(row.get("Tank", "")).strip()
            if not tank_id:
                continue

            delta_t = _delta_from_row(row)
            if abs(delta_t) < 0.01:
                continue  # Skip negligible changes

            # Check tank operability
            if tank_catalog_df is not None and "Tank" in tank_catalog_df.columns:
                tank_info = tank_catalog_df[tank_catalog_df["Tank"] == tank_id]
                if not tank_info.empty:
                    operability = (
                        str(tank_info.iloc[0].get("operability", "NORMAL"))
                        .strip()
                        .upper()
                    )
                    mode = str(tank_info.iloc[0].get("mode", "")).strip().upper()
                    if operability == "PRE_BALLAST_ONLY" or mode in (
                        "BLOCKED",
                        "FIXED",
                    ):
                        # Skip - already filled at mobilization
                        continue

            # Determine action
            action = "FILL" if delta_t > 0 else "DISCHARGE"

            # Determine start_t
            start_t = stage_tank_current.get(tank_id, 0.0)
            if "Current_t" in row and pd.notna(row.get("Current_t")):
                try:
                    start_t = float(row.get("Current_t", 0.0))
                except (TypeError, ValueError):
                    start_t = stage_tank_current.get(tank_id, 0.0)

            target_t = start_t + delta_t
            if tank_catalog_df is not None and "Tank" in tank_catalog_df.columns:
                tank_info = tank_catalog_df[tank_catalog_df["Tank"] == tank_id]
                if not tank_info.empty:
                    capacity_t = float(tank_info.iloc[0].get("Capacity_t", 0.0))
                    min_t = float(tank_info.iloc[0].get("Min_t", 0.0))
                    if target_t > capacity_t:
                        print(
                            f"[WARN] Stage {stage_name}, Tank {tank_id}: "
                            f"Target_t ({target_t:.2f}t) exceeds Capacity_t ({capacity_t:.2f}t). "
                            "Clamping to capacity."
                        )
                        target_t = capacity_t
                        delta_t = target_t - start_t
                    if target_t < min_t:
                        print(
                            f"[WARN] Stage {stage_name}, Tank {tank_id}: "
                            f"Target_t ({target_t:.2f}t) below Min_t ({min_t:.2f}t). "
                            "Clamping to minimum."
                        )
                        target_t = min_t
                        delta_t = target_t - start_t
            stage_tank_current[tank_id] = target_t
            tank_current[tank_id] = target_t

            # Calculate time
            time_h = abs(delta_t) / stage_pump_rate if stage_pump_rate > 0 else 0.0
            cumulative_time += time_h

            # Check daylight constraint
            if daylight_only and cumulative_time > max_hours:
                notes = (
                    f"WARNING: cumulative time {cumulative_time:.1f}h exceeds "
                    f"daylight window {max_hours}h"
                )
            else:
                # Stage별 pump rate에 따른 notes 설정
                if "preballast" in stage_name.lower():
                    notes = f"D-1 급수차 작업 (운영 시간 제외) - Pump scenario: {default_scenario} ({stage_pump_rate} t/h)"
                elif stage_pump_rate != default_pump_rate:
                    notes = f"Pump scenario: Stage-specific ({stage_pump_rate} t/h - {'Hired pump' if stage_pump_rate >= 100 else 'Ship pump'})"
                else:
                    notes = f"Pump scenario: {default_scenario} ({stage_pump_rate} t/h)"

            # Pump ID
            if stage_pump_rate <= 10.0:
                pump_id = "SHIP_PUMP_01"
            elif stage_pump_rate <= 100.0:
                pump_id = "HIRED_PUMP_01"
            else:
                pump_id = "SHORE_PUMP"

            # Valve lineup (simplified - needs valve map)
            tank_clean = tank_id.replace(".", "").replace(" ", "_")
            if delta_t > 0:
                valve_lineup = f"V-{tank_clean}-FILL,V-{tank_clean}-INLET"
            else:
                valve_lineup = f"V-{tank_clean}-DISCHARGE,V-{tank_clean}-OUTLET"

            # Hold point criteria
            # 1. Large volume change (>10t)
            # 2. Critical stage (contains "critical" or "6a")
            # 3. After significant cumulative time (>2h)
            is_critical = "critical" in stage_name.lower() or "6a" in stage_name.lower()
            hold_point = (
                abs(delta_t) > 10.0
                or is_critical
                or (cumulative_time > 0 and cumulative_time % 2.0 < time_h)
            )

            step = BallastStep(
                stage=stage_name,
                step=step_counter,
                tank=tank_id,
                action=action,
                start_t=start_t,
                delta_t=delta_t,
                target_t=target_t,
                pump_id=pump_id,
                pump_rate_tph=stage_pump_rate,
                time_h=round(time_h, 2),
                valve_lineup=valve_lineup,
                draft_fwd=float(stage_info.get("fwd", 0.0)),
                draft_aft=float(stage_info.get("aft", 0.0)),
                trim=float(stage_info.get("trim", 0.0)),
                ukc=float(stage_info.get("ukc", 0.0)),
                hold_point=hold_point,
                notes=notes,
            )

            sequence.append(step)
            step_counter += 1

    return sequence


def generate_sequence_with_carryforward(
    ballast_plan_df: pd.DataFrame,
    profile,
    stage_drafts: Dict[str, Dict[str, float]],
    tank_catalog_df: Optional[pd.DataFrame] = None,
    exclude_optional_stages: bool = True,
    fallback_plan_df: Optional[pd.DataFrame] = None,
) -> List[BallastStep]:
    """
    Generate execution sequence with Start_t/Target_t carry-forward.
    Each step Start_t = previous Target_t for same tank (or initial Current_t).
    """
    sequence: List[BallastStep] = []
    step_counter = 1

    ballast_params = profile.ballast_params if profile else {}
    default_scenario = ballast_params.get("default_scenario", "A")
    contingency = ballast_params.get("contingency", {})
    scenario_config = contingency.get(default_scenario, {"pump_rate_tph": 10.0})
    default_pump_rate = float(scenario_config.get("pump_rate_tph", 10.0)) or 10.0

    daylight_only = bool(ballast_params.get("daylight_only", True))
    daylight_end = str(ballast_params.get("daylight_end", "18:00"))
    daylight_start = str(ballast_params.get("daylight_start", "06:00"))
    try:
        end_hour = int(daylight_end[:2])
        start_hour = int(daylight_start[:2])
    except ValueError:
        end_hour = 18
        start_hour = 6
    max_hours = end_hour - start_hour if daylight_only else 24

    ballast_plan_df = _canonicalize_stage_column(ballast_plan_df)
    fallback_plan_df = (
        _canonicalize_stage_column(fallback_plan_df)
        if fallback_plan_df is not None
        else None
    )
    ballast_plan_df = _merge_missing_optional_stages(
        ballast_plan_df, fallback_plan_df, OPTIONAL_STAGES
    )
    stage_drafts_norm = {_canonical_stage_name(k): v for k, v in stage_drafts.items()}

    cumulative_time = 0.0
    initial_tank_state = _tank_current_map(tank_catalog_df)
    tank_state = dict(initial_tank_state)

    stage_order = _stage_order_from_df(ballast_plan_df)
    if exclude_optional_stages:
        stage_order = [s for s in stage_order if s not in OPTIONAL_STAGES]

    for stage_name in stage_order:
        if not stage_name or not stage_name.strip():
            continue  # Skip empty stage names
        stage_df = ballast_plan_df[ballast_plan_df["Stage"] == stage_name].copy()
        stage_info = stage_drafts_norm.get(stage_name, {})

        # Stage별 pump rate 결정
        stage_pump_rate = _get_stage_pump_rate(stage_name, default_pump_rate)

        stage_current_map: Dict[str, float] = {}
        if "Current_t" in stage_df.columns:
            for _, row in stage_df.iterrows():
                tank_id = str(row.get("Tank", "")).strip()
                if not tank_id:
                    continue
                current_t = row.get("Current_t")
                if pd.notna(current_t):
                    try:
                        stage_current_map[tank_id] = float(current_t)
                    except (TypeError, ValueError):
                        continue
        # 수정: stage_current_map이 있는 탱크만 업데이트, 나머지는 이전 stage 상태 유지
        # 이렇게 하면 Stage 6A가 Stage 5_PreBallast의 종료 상태를 사용할 수 있음
        for tank_id, current_t in stage_current_map.items():
            tank_state[tank_id] = current_t
        # stage_current_map이 없으면 tank_state는 이전 stage의 상태를 그대로 사용 (carry-forward 유지)

        if "Delta_t" in stage_df.columns:
            stage_df = stage_df.sort_values(
                "Delta_t", key=lambda s: s.abs(), ascending=False
            )
        elif "Weight_t" in stage_df.columns:
            stage_df = stage_df.sort_values(
                "Weight_t", key=lambda s: s.abs(), ascending=False
            )

        for _, row in stage_df.iterrows():
            tank_id = str(row.get("Tank", "")).strip()
            if not tank_id:
                continue

            delta_t = _delta_from_row(row)
            if abs(delta_t) < 0.01:
                continue

            if tank_catalog_df is not None and "Tank" in tank_catalog_df.columns:
                tank_info = tank_catalog_df[tank_catalog_df["Tank"] == tank_id]
                if not tank_info.empty:
                    operability = (
                        str(tank_info.iloc[0].get("operability", "NORMAL"))
                        .strip()
                        .upper()
                    )
                    mode = str(tank_info.iloc[0].get("mode", "")).strip().upper()
                    if operability == "PRE_BALLAST_ONLY" or mode in (
                        "BLOCKED",
                        "FIXED",
                    ):
                        continue

            action = "FILL" if delta_t > 0 else "DISCHARGE"

            start_t = tank_state.get(tank_id, 0.0)
            if "Current_t" in row and pd.notna(row.get("Current_t")):
                try:
                    start_t = float(row.get("Current_t", 0.0))
                except (TypeError, ValueError):
                    start_t = tank_state.get(tank_id, 0.0)

            target_t = start_t + delta_t

            # DISCHARGE 시 target_t가 0 이하로 내려가지 않도록 클리핑 (물리적 제약)
            if action == "DISCHARGE" and target_t < 0.0:
                print(
                    f"[WARN] Stage {stage_name}, Tank {tank_id}: "
                    f"Target_t ({target_t:.2f}t) would be negative for DISCHARGE. "
                    f"Clamping to 0.0t (Start_t={start_t:.2f}t, Delta_t={delta_t:.2f}t)."
                )
                target_t = 0.0
                delta_t = target_t - start_t  # delta_t 재조정

            if tank_catalog_df is not None and "Tank" in tank_catalog_df.columns:
                tank_info = tank_catalog_df[tank_catalog_df["Tank"] == tank_id]
                if not tank_info.empty:
                    capacity_t = float(tank_info.iloc[0].get("Capacity_t", 0.0))
                    min_t = float(tank_info.iloc[0].get("Min_t", 0.0))
                    if target_t > capacity_t:
                        print(
                            f"[WARN] Stage {stage_name}, Tank {tank_id}: "
                            f"Target_t ({target_t:.2f}t) exceeds Capacity_t ({capacity_t:.2f}t). "
                            "Clamping to capacity."
                        )
                        target_t = capacity_t
                        delta_t = target_t - start_t
                    if target_t < min_t:
                        print(
                            f"[WARN] Stage {stage_name}, Tank {tank_id}: "
                            f"Target_t ({target_t:.2f}t) below Min_t ({min_t:.2f}t). "
                            "Clamping to minimum."
                        )
                        target_t = min_t
                        delta_t = target_t - start_t

            tank_state[tank_id] = target_t

            time_h = abs(delta_t) / stage_pump_rate if stage_pump_rate > 0 else 0.0
            cumulative_time += time_h

            if daylight_only and cumulative_time > max_hours:
                notes = (
                    f"WARNING: cumulative time {cumulative_time:.1f}h exceeds "
                    f"daylight window {max_hours}h"
                )
            else:
                # Stage별 pump rate에 따른 notes 설정
                if "preballast" in stage_name.lower():
                    notes = f"D-1 급수차 작업 (운영 시간 제외) - Pump scenario: {default_scenario} ({stage_pump_rate} t/h)"
                elif stage_pump_rate != default_pump_rate:
                    notes = f"Pump scenario: Stage-specific ({stage_pump_rate} t/h - {'Hired pump' if stage_pump_rate >= 100 else 'Ship pump'})"
                else:
                    notes = f"Pump scenario: {default_scenario} ({stage_pump_rate} t/h)"

            if stage_pump_rate <= 10.0:
                pump_id = "SHIP_PUMP_01"
            elif stage_pump_rate <= 100.0:
                pump_id = "HIRED_PUMP_01"
            else:
                pump_id = "SHORE_PUMP"

            tank_clean = tank_id.replace(".", "").replace(" ", "_")
            if delta_t > 0:
                valve_lineup = f"V-{tank_clean}-FILL,V-{tank_clean}-INLET"
            else:
                valve_lineup = f"V-{tank_clean}-DISCHARGE,V-{tank_clean}-OUTLET"

            is_critical = "critical" in stage_name.lower() or "6a" in stage_name.lower()
            hold_point = (
                abs(delta_t) > 10.0
                or is_critical
                or (cumulative_time > 0 and cumulative_time % 2.0 < time_h)
            )

            step = BallastStep(
                stage=stage_name,
                step=step_counter,
                tank=tank_id,
                action=action,
                start_t=start_t,
                delta_t=delta_t,
                target_t=target_t,
                pump_id=pump_id,
                pump_rate_tph=stage_pump_rate,
                time_h=round(time_h, 2),
                valve_lineup=valve_lineup,
                draft_fwd=float(stage_info.get("fwd", 0.0)),
                draft_aft=float(stage_info.get("aft", 0.0)),
                trim=float(stage_info.get("trim", 0.0)),
                ukc=float(stage_info.get("ukc", 0.0)),
                hold_point=hold_point,
                notes=notes,
            )

            sequence.append(step)
            step_counter += 1

    return sequence


def generate_option_plan(
    ballast_plan_df: pd.DataFrame,
    profile,
    stage_drafts: Dict[str, Dict[str, float]],
    tank_catalog_df: Optional[pd.DataFrame] = None,
    fallback_plan_df: Optional[pd.DataFrame] = None,
) -> List[BallastOption]:
    """Generate option/plan level ballast plan (Delta_t based)."""
    options: List[BallastOption] = []

    ballast_plan_df = _canonicalize_stage_column(ballast_plan_df)
    fallback_plan_df = (
        _canonicalize_stage_column(fallback_plan_df)
        if fallback_plan_df is not None
        else None
    )
    ballast_plan_df = _merge_missing_optional_stages(
        ballast_plan_df, fallback_plan_df, OPTIONAL_STAGES
    )

    ballast_params = profile.ballast_params if profile else {}
    default_scenario = ballast_params.get("default_scenario", "A")
    contingency = ballast_params.get("contingency", {})
    scenario_config = contingency.get(default_scenario, {"pump_rate_tph": 10.0})
    default_pump_rate = float(scenario_config.get("pump_rate_tph", 10.0)) or 10.0

    def get_priority(stage_name: str) -> int:
        if "critical" in stage_name.lower() or "6a" in stage_name.lower():
            return 1
        if "preballast" in stage_name.lower():
            return 2
        if "6b" in stage_name.lower() or "tide" in stage_name.lower():
            return 5
        return 3

    def get_rationale(stage_name: str, action: str) -> str:
        if "preballast" in stage_name.lower():
            return "Pre-ballast for critical RoRo stage (Gate-A/B compliance)"
        if "critical" in stage_name.lower() or "6a" in stage_name.lower():
            return f"Critical RoRo stage: {action} for draft control"
        if "6b" in stage_name.lower() or "tide" in stage_name.lower():
            return "Tide window optimization (optional scenario)"
        return f"Standard ballast operation: {action} for stage requirements"

    stage_order = _stage_order_from_df(ballast_plan_df)
    for stage_name in stage_order:
        if not stage_name or not stage_name.strip():
            continue  # Skip empty stage names
        stage_df = ballast_plan_df[ballast_plan_df["Stage"] == stage_name].copy()

        # Stage별 pump rate 결정
        stage_pump_rate = _get_stage_pump_rate(stage_name, default_pump_rate)

        for _, row in stage_df.iterrows():
            tank_id = str(row.get("Tank", "")).strip()
            if not tank_id:
                continue
            delta_t = _delta_from_row(row)
            if abs(delta_t) < 0.01:
                continue
            if tank_catalog_df is not None and "Tank" in tank_catalog_df.columns:
                tank_info = tank_catalog_df[tank_catalog_df["Tank"] == tank_id]
                if not tank_info.empty:
                    operability = (
                        str(tank_info.iloc[0].get("operability", "NORMAL"))
                        .strip()
                        .upper()
                    )
                    mode = str(tank_info.iloc[0].get("mode", "")).strip().upper()
                    if operability == "PRE_BALLAST_ONLY" or mode in (
                        "BLOCKED",
                        "FIXED",
                    ):
                        continue

            action = "FILL" if delta_t > 0 else "DISCHARGE"
            option = BallastOption(
                stage=stage_name,
                tank=tank_id,
                action=action,
                delta_t=delta_t,
                pump_rate_tph=stage_pump_rate,
                priority=get_priority(stage_name),
                rationale=get_rationale(stage_name, action),
            )
            options.append(option)

    return options


def generate_optional_sequence(
    ballast_plan_df: pd.DataFrame,
    profile,
    stage_drafts: Dict[str, Dict[str, float]],
    tank_catalog_df: Optional[pd.DataFrame] = None,
    fallback_plan_df: Optional[pd.DataFrame] = None,
    optional_stages: Optional[List[str]] = None,
) -> List[BallastStep]:
    """Generate sequence for optional stages only."""
    optional_stages = optional_stages or OPTIONAL_STAGES
    ballast_plan_df = _canonicalize_stage_column(ballast_plan_df)
    fallback_plan_df = (
        _canonicalize_stage_column(fallback_plan_df)
        if fallback_plan_df is not None
        else None
    )
    ballast_plan_df = _merge_missing_optional_stages(
        ballast_plan_df, fallback_plan_df, optional_stages
    )
    optional_stages = [_canonical_stage_name(s) for s in optional_stages]
    if "Stage" not in ballast_plan_df.columns:
        return []
    optional_df = ballast_plan_df[
        ballast_plan_df["Stage"].astype(str).isin(optional_stages)
    ].copy()
    if optional_df.empty:
        return []
    return generate_sequence(
        ballast_plan_df=optional_df,
        profile=profile,
        stage_drafts=stage_drafts,
        tank_catalog_df=tank_catalog_df,
        exclude_optional_stages=False,
    )


def export_to_dataframe(sequence: List[BallastStep]) -> pd.DataFrame:
    """Convert sequence to pandas DataFrame."""
    data = [
        {
            "Stage": s.stage,
            "Step": s.step,
            "Tank": s.tank,
            "Action": s.action,
            "Start_t": round(s.start_t, 2),
            "Delta_t": round(s.delta_t, 2),
            "Target_t": round(s.target_t, 2),
            "Pump_ID": s.pump_id,
            "PumpRate_tph": s.pump_rate_tph,
            "Time_h": s.time_h,
            "Valve_Lineup": s.valve_lineup,
            "Draft_FWD": round(s.draft_fwd, 3),
            "Draft_AFT": round(s.draft_aft, 3),
            "Trim_cm": round(s.trim * 100.0, 1),
            "UKC": round(s.ukc, 2),
            "Hold_Point": "Y" if s.hold_point else "N",
            "Notes": s.notes,
        }
        for s in sequence
    ]

    return pd.DataFrame(data)


def export_to_option_dataframe(options: List[BallastOption]) -> pd.DataFrame:
    """Convert option plan to pandas DataFrame."""
    data = [
        {
            "Stage": opt.stage if opt.stage and opt.stage.strip() else "",
            "Tank": opt.tank,
            "Action": opt.action,
            "Delta_t": round(opt.delta_t, 2),
            "PumpRate_tph": opt.pump_rate_tph,
            "Priority": opt.priority,
            "Rationale": opt.rationale,
        }
        for opt in options
    ]
    return pd.DataFrame(data)


def export_to_exec_dataframe(
    sequence: List[BallastStep],
    optimizer_excel_path: Optional[Path] = None,
) -> pd.DataFrame:
    """
    Convert execution sequence to pandas DataFrame.

    Args:
        sequence: List of BallastStep objects
        optimizer_excel_path: Optional path to optimizer_ballast_plan.xlsx
                             to supplement missing Delta_t values
    """
    data = [
        {
            "Stage": s.stage if s.stage and s.stage.strip() else "",
            "Step": s.step,
            "Tank": s.tank,
            "Action": s.action,
            "Start_t": round(s.start_t, 2),
            "Target_t": round(s.target_t, 2),
            "Delta_t": round(s.delta_t, 2),  # Always include delta_t (even if 0.0)
            "Time_h": s.time_h,
            "Pump_ID": s.pump_id,
            "PumpRate_tph": s.pump_rate_tph,
            "Valve_Lineup": s.valve_lineup,
            "Hold_Point": "Y" if s.hold_point else "N",
            "Draft_FWD": round(s.draft_fwd, 3),
            "Draft_AFT": round(s.draft_aft, 3),
            "Trim_cm": round(s.trim * 100.0, 1),
            "UKC": round(s.ukc, 2),
            "Notes": s.notes,
        }
        for s in sequence
    ]

    df = pd.DataFrame(data)

    # Supplement missing Delta_t from optimizer Excel if provided
    if optimizer_excel_path and optimizer_excel_path.exists():
        try:
            # Try to read optimizer Excel (Plan sheet)
            optimizer_df = pd.read_excel(
                optimizer_excel_path, sheet_name="Plan", engine="openpyxl"
            )

            # Normalize stage names for matching
            def _normalize_stage(s: str) -> str:
                return re.sub(r"\s+", " ", str(s).strip()).lower()

            optimizer_df["_stage_norm"] = optimizer_df["Stage"].apply(_normalize_stage)
            optimizer_df["_tank_norm"] = optimizer_df["Tank"].astype(str).str.strip()

            df["_stage_norm"] = df["Stage"].apply(_normalize_stage)
            df["_tank_norm"] = df["Tank"].astype(str).str.strip()

            # Fill missing Delta_t values
            missing_delta_mask = df["Delta_t"].isna() | (df["Delta_t"] == 0.0)
            if missing_delta_mask.any():
                filled_count = 0
                for idx in df[missing_delta_mask].index:
                    row = df.loc[idx]
                    stage_norm = row["_stage_norm"]
                    tank_norm = row["_tank_norm"]

                    # Find matching row in optimizer
                    match = optimizer_df[
                        (optimizer_df["_stage_norm"] == stage_norm)
                        & (optimizer_df["_tank_norm"] == tank_norm)
                    ]

                    if not match.empty and "Delta_t" in match.columns:
                        delta_val = match.iloc[0]["Delta_t"]
                        if pd.notna(delta_val) and abs(float(delta_val)) > 0.01:
                            df.loc[idx, "Delta_t"] = round(float(delta_val), 2)
                            filled_count += 1

                            # Recalculate Time_h if Delta_t was filled
                            if df.loc[idx, "PumpRate_tph"] > 0:
                                df.loc[idx, "Time_h"] = round(
                                    abs(df.loc[idx, "Delta_t"])
                                    / df.loc[idx, "PumpRate_tph"],
                                    2,
                                )

                if filled_count > 0:
                    print(
                        f"[INFO] Supplemented {filled_count} Delta_t values from optimizer Excel"
                    )

            # Clean up temporary columns
            df = df.drop(columns=["_stage_norm", "_tank_norm"], errors="ignore")

        except Exception as e:
            print(
                f"[WARN] Failed to supplement Delta_t from optimizer Excel: {type(e).__name__}: {e}"
            )

    return df


def export_to_csv(sequence: List[BallastStep], output_path: str) -> None:
    """Export sequence to CSV."""
    df = export_to_dataframe(sequence)
    df.to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f"[OK] Ballast sequence exported: {output_path}")


def export_option_to_csv(
    options: List[BallastOption],
    output_path: str,
    registry_path: Optional[Path] = None,
) -> None:
    """Export option plan to CSV with optional headers SSOT."""
    df = export_to_option_dataframe(options)

    # Apply headers SSOT if available
    if registry_path and registry_path.exists():
        try:
            from ssot.headers_writer import HeadersWriter

            writer = HeadersWriter(registry_path)
            writer.write_csv_with_schema(
                df,
                Path(output_path),
                "BALLAST_OPTION_CSV",
                keep_extra=False,
            )
            print(f"[OK] Ballast option plan exported (with SSOT): {output_path}")
            return
        except Exception as e:
            print(f"[WARN] Headers SSOT failed: {e}, using fallback")

    # Fallback to original
    df.to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f"[OK] Ballast option plan exported: {output_path}")


def export_exec_to_csv(
    sequence: List[BallastStep],
    output_path: str,
    optimizer_excel_path: Optional[Path] = None,
    registry_path: Optional[Path] = None,
) -> None:
    """Export execution sequence to CSV with optional headers SSOT."""
    df = export_to_exec_dataframe(sequence, optimizer_excel_path=optimizer_excel_path)

    # Apply headers SSOT if available
    if registry_path and registry_path.exists():
        try:
            from ssot.headers_writer import HeadersWriter

            writer = HeadersWriter(registry_path)
            writer.write_csv_with_schema(
                df,
                Path(output_path),
                "BALLAST_EXEC_CSV",
                keep_extra=False,
            )
            print(
                f"[OK] Ballast execution sequence exported (with SSOT): {output_path}"
            )
            return
        except Exception as e:
            print(f"[WARN] Headers SSOT failed: {e}, using fallback")

    # Fallback to original
    df.to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f"[OK] Ballast execution sequence exported: {output_path}")


def export_summary(sequence: List[BallastStep]) -> Dict[str, float]:
    """Generate sequence summary statistics."""
    total_time = sum(s.time_h for s in sequence)
    hold_points = [s for s in sequence if s.hold_point]
    fill_steps = [s for s in sequence if s.action == "FILL"]
    discharge_steps = [s for s in sequence if s.action == "DISCHARGE"]

    return {
        "total_steps": len(sequence),
        "total_time_h": round(total_time, 2),
        "hold_points": len(hold_points),
        "fill_steps": len(fill_steps),
        "discharge_steps": len(discharge_steps),
        "total_fill_t": sum(s.delta_t for s in fill_steps),
        "total_discharge_t": sum(abs(s.delta_t) for s in discharge_steps),
    }


if __name__ == "__main__":
    print("Ballast Sequence Generator - P0-2")
    print("Use in integrated pipeline or standalone mode")
