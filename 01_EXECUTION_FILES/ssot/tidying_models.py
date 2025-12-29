#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tidying Models - Pydantic-based data validation for MACHO-GPT pipeline
Integrates with existing ssot/headers_registry.py and ssot/data_quality_validator.py
"""

from __future__ import annotations
from typing import Optional, List, Literal, Dict, Tuple
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum

import pandas as pd
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict


class BallastAction(str, Enum):
    """Ballast action enum (uppercase only)"""

    FILL = "FILL"
    DISCHARGE = "DISCHARGE"
    NONE = "NONE"


class TankOperability(str, Enum):
    """Tank operability enum"""

    NORMAL = "NORMAL"
    PRE_BALLAST_ONLY = "PRE_BALLAST_ONLY"
    DISCHARGE_ONLY = "DISCHARGE_ONLY"
    FIXED = "FIXED"
    LOCKED = "LOCKED"


class BallastSequenceRow(BaseModel):
    """Validated row from BALLAST_EXEC.csv or BALLAST_OPTION.csv"""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    stage: Optional[str] = Field(default=None, description="Stage name (optional)")
    step: Optional[int] = Field(
        default=None, ge=1, description="Step number (1-based, optional for OPTION)"
    )
    tank: str = Field(min_length=1, description="Tank ID (required)")
    action: BallastAction = Field(description="Ballast action (FILL/DISCHARGE/NONE)")
    start_t: Optional[Decimal] = Field(default=None, ge=0, description="Start tonnage")
    delta_t: Decimal = Field(description="Delta tonnage")
    target_t: Optional[Decimal] = Field(
        default=None, ge=0, description="Target tonnage"
    )
    pump_id: Optional[str] = Field(default=None, description="Pump ID")
    pump_rate_tph: Optional[Decimal] = Field(
        default=None, gt=0, description="Pump rate (tph)"
    )
    time_h: Optional[Decimal] = Field(
        default=None, ge=0, description="Operating time (hours)"
    )
    valve_lineup: Optional[str] = Field(default=None, description="Valve lineup")
    draft_fwd: Optional[Decimal] = Field(default=None, ge=0, le=3.65)
    draft_aft: Optional[Decimal] = Field(default=None, ge=0, le=3.65)
    trim_cm: Optional[Decimal] = Field(default=None)
    ukc: Optional[Decimal] = Field(default=None, ge=0)
    hold_point: Optional[Literal["Y", "N"]] = Field(default=None)
    notes: Optional[str] = Field(default=None)
    priority: Optional[int] = Field(
        default=None, ge=1, le=5, description="Priority (1=highest, 5=lowest)"
    )
    rationale: Optional[str] = Field(default=None, description="Rationale for action")

    @field_validator("action", mode="before")
    @classmethod
    def normalize_action(cls, v):
        """Normalize action to uppercase enum"""
        if v is None or v == "":
            return BallastAction.NONE
        v_str = str(v).strip().upper()
        if v_str in ["FILL", "DISCHARGE", "NONE"]:
            return BallastAction(v_str)
        # Legacy support
        if v_str in ["F", "D"]:
            return BallastAction.FILL if v_str == "F" else BallastAction.DISCHARGE
        raise ValueError(f"Invalid action: {v}")

    @field_validator("tank", mode="before")
    @classmethod
    def normalize_tank_id(cls, v):
        """Normalize tank ID (strip, uppercase)"""
        return str(v).strip().upper()

    @field_validator("stage", mode="before")
    @classmethod
    def normalize_stage(cls, v):
        """Normalize stage name (strip, preserve case)"""
        if v is None or pd.isna(v):
            return None
        s = str(v).strip()
        if not s:
            return None  # Allow empty stage
        return s

    @field_validator(
        "delta_t",
        "start_t",
        "target_t",
        "pump_rate_tph",
        "time_h",
        "draft_fwd",
        "draft_aft",
        "trim_cm",
        "ukc",
        mode="before",
    )
    @classmethod
    def normalize_decimal(cls, v):
        """Normalize decimal values to 2 decimal places"""
        if v is None or pd.isna(v):
            return None
        try:
            return Decimal(str(v)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        except (ValueError, TypeError):
            return None

    @model_validator(mode="after")
    def validate_physics(self):
        """Validate physical constraints"""
        # Target_t = Start_t + Delta_t (within tolerance, if both present)
        if self.start_t is not None and self.target_t is not None:
            expected_target = self.start_t + self.delta_t
            tolerance = Decimal("0.01")
            if abs(self.target_t - expected_target) > tolerance:
                raise ValueError(
                    f"Target_t ({self.target_t}) != Start_t ({self.start_t}) + Delta_t ({self.delta_t})"
                )
        return self


class TankCatalogRow(BaseModel):
    """Validated row from tank catalog"""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    tank_id: str = Field(min_length=1, alias="Tank")
    capacity_t: Decimal = Field(gt=0, description="Tank capacity (tons)")
    x_from_mid_m: Decimal = Field(description="X coordinate from midship (m)")
    current_t: Decimal = Field(ge=0, description="Current tonnage")
    min_t: Decimal = Field(ge=0, description="Minimum tonnage")
    max_t: Decimal = Field(ge=0, description="Maximum tonnage")
    mode: str = Field(description="Tank mode (FILL_DISCHARGE/DISCHARGE_ONLY/FIXED)")
    use_flag: Literal["Y", "N"] = Field(description="Use flag")
    operability: Optional[TankOperability] = Field(default=None)
    pump_rate_tph: Optional[Decimal] = Field(default=None, gt=0)

    @field_validator("tank_id", mode="before")
    @classmethod
    def normalize_tank_id(cls, v):
        return str(v).strip().upper()

    @field_validator(
        "capacity_t",
        "current_t",
        "min_t",
        "max_t",
        "x_from_mid_m",
        "pump_rate_tph",
        mode="before",
    )
    @classmethod
    def normalize_decimal(cls, v):
        """Normalize decimal values to 2 decimal places"""
        if v is None or pd.isna(v):
            return None
        try:
            return Decimal(str(v)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        except (ValueError, TypeError):
            return None

    @model_validator(mode="after")
    def validate_capacity(self):
        """Validate capacity constraints"""
        if self.min_t > self.max_t:
            raise ValueError(f"Min_t ({self.min_t}) > Max_t ({self.max_t})")
        if self.max_t > self.capacity_t:
            raise ValueError(f"Max_t ({self.max_t}) > Capacity_t ({self.capacity_t})")
        if self.current_t > self.capacity_t:
            raise ValueError(
                f"Current_t ({self.current_t}) > Capacity_t ({self.capacity_t})"
            )
        return self


class LogiDataTider:
    """Data tidying pipeline for MACHO-GPT logistics data"""

    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def tidy_dates(self, date_columns: Optional[List[str]] = None) -> "LogiDataTider":
        """Normalize date columns to YYYY-MM-DD format"""
        if date_columns is None:
            date_columns = [c for c in self.df.columns if "date" in c.lower()]

        for col in date_columns:
            if col in self.df.columns:
                try:
                    self.df[col] = pd.to_datetime(
                        self.df[col], errors="coerce"
                    ).dt.strftime("%Y-%m-%d")
                except Exception as e:
                    self.warnings.append(
                        f"Date column '{col}' normalization failed: {e}"
                    )
        return self

    def tidy_decimal_columns(
        self, columns: List[str], decimal_places: int = 2
    ) -> "LogiDataTider":
        """Normalize decimal columns to specified precision"""
        for col in columns:
            if col in self.df.columns:
                try:
                    self.df[col] = self.df[col].apply(
                        lambda x: (
                            round(float(x), decimal_places) if pd.notna(x) else None
                        )
                    )
                except Exception as e:
                    self.warnings.append(
                        f"Decimal column '{col}' normalization failed: {e}"
                    )
        return self

    def tidy_action_case(self, action_column: str = "Action") -> "LogiDataTider":
        """Normalize action column to uppercase"""
        if action_column in self.df.columns:
            self.df[action_column] = (
                self.df[action_column].astype(str).str.strip().str.upper()
            )
        return self

    def tidy_tank_ids(self, tank_column: str = "Tank") -> "LogiDataTider":
        """Normalize tank ID column (strip, uppercase)"""
        if tank_column in self.df.columns:
            self.df[tank_column] = (
                self.df[tank_column].astype(str).str.strip().str.upper()
            )
        return self

    def validate_with_schema(
        self,
        model_class: type[BaseModel],
        column_mapping: Optional[Dict[str, str]] = None,
    ) -> Tuple[List[BaseModel], List[str]]:
        """
        Validate DataFrame rows against Pydantic model

        Returns:
            Tuple of (validated_models, errors)
        """
        validated = []
        errors = []

        # Apply column mapping if provided
        df_mapped = self.df.copy()
        if column_mapping:
            df_mapped = df_mapped.rename(columns=column_mapping)

        for idx, row_dict in df_mapped.to_dict(orient="index").items():
            try:
                # Handle Pydantic aliases (e.g., "Tank" -> "tank_id")
                model = model_class(**row_dict)
                validated.append(model)
            except Exception as e:
                errors.append(f"Row {idx}: {type(e).__name__}: {e}")

        return validated, errors

    def to_llm_markdown(self, max_rows: int = 50, sample: bool = False) -> str:
        """Convert DataFrame to markdown for LLM context (with sampling if needed)"""
        if len(self.df) > max_rows:
            if sample:
                view = self.df.sample(n=max_rows, random_state=42)
            else:
                view = self.df.head(max_rows)
            note = f"\n*Note: Showing {max_rows} of {len(self.df)} rows*\n"
        else:
            view = self.df
            note = ""

        try:
            markdown_table = view.to_markdown(index=False)
            return f"{note}{markdown_table}"
        except Exception as e:
            # Fallback to simple string representation
            return f"{note}{view.to_string(index=False)}"
