# Data Tidying First Implementation Guide — MACHO-GPT Pipeline Integration

**Created:** 2025-12-29
**Version:** v1.0
**Purpose:** Improve context quality and reduce errors/hallucinations by tidying and validating data before LLM/AI analysis

---

## 1. Executive Summary

### 1.1 Purpose

This guide implements a **"Tidying First"** approach for the MACHO-GPT Ballast Pipeline, ensuring data is cleaned, validated, and standardized before being used in LLM/AI workflows. This reduces context ambiguity, prevents hallucinations, and improves cost efficiency.

### 1.2 Current State

- **Existing Infrastructure:**
  - `ssot/headers_registry.py`: Header schema registry and validation
  - `ssot/data_quality_validator.py`: Data quality validation (type, range, consistency)
  - `ssot/head_guard_v2.py`: Header validation against JSON registry
  - `ssot/headers_writer.py`: Schema application for output files

- **Gaps:**
  - No Pydantic-based type safety for data validation
  - No integrated tidying pipeline (normalization, standardization)
  - No cross-validation with tank catalog (e.g., VOID3 operability)
  - No LLM-ready context generation from validated data

### 1.3 Proposed Solution

**4-Stage Integration:**
1. **Rule-Based Tidying**: Normalize dates, decimals, action codes, tank IDs
2. **Pydantic Schema Validation**: Type-safe validation with domain constraints
3. **Cross-Validation**: Tank catalog operability, capacity limits, physics constraints
4. **LLM Context Generation**: Fail-fast (no LLM input if validation fails)

### 1.4 Tools & Technologies

- **Code Quality**: Ruff, Black (formatting, linting)
- **Data Validation**: Pydantic v2 (type safety, schema validation)
- **Parallel Processing**: asyncio, LangChain (for future agent workflows)
- **CI/CD Integration**: Pre-commit hooks, pipeline validation gates
- **Integration Points**: Extends `ssot/data_quality_validator.py`, integrates with `ssot/headers_registry.py`

---

## 2. Architecture (Current vs Proposed)

| Component | Current Implementation | Proposed Enhancement | MACHO-GPT Integration Example |
|-----------|----------------------|---------------------|------------------------------|
| **Header Registry** | `ssot/headers_registry.py` (header matching) | ✅ Keep existing, add Pydantic models | Header validation + type-safe data models |
| **Data Validator** | `ssot/data_quality_validator.py` (type, range checks) | Add Pydantic models + tidying pipeline | Normalize Action (Fill → FILL), validate Delta_t precision |
| **Tidying Pipeline** | Manual normalization (inside pipeline) | Dedicated `LogiDataTider` class | Date YYYY-MM-DD, Decimal(2), Action uppercase |
| **Cross-Validation** | None | Tank catalog lookup + operability checks | VOID3 PRE_BALLAST_ONLY constraint enforcement |
| **LLM Context** | Raw DataFrame dump | Validated data → Markdown (sampled/aggregated) | Only validated rows sent to LLM, with error summary |

---

## 3. Implementation Strategy

### Option 1: Rule-Based Tidying (Pydantic Integration) ⭐ **RECOMMENDED**

**Pros:**
- Type safety and reproducibility
- Reduced LLM dependency (fail-fast on invalid data)
- Domain constraints enforced at schema level (VOID3 operability, capacity limits)

**Cons:**
- Schema design and exception handling required
- Rule changes may require reprocessing

**Risk:** Low (extends existing infrastructure)

**Integration Point:** Extend `ssot/data_quality_validator.py` with Pydantic models

### Option 2: Parallel Agent Processing (Task Decomposition)

**Pros:**
- Throughput and speed improvement
- Task-specific accuracy

**Cons:**
- Rate limit and error handling required
- Result synthesis consistency risk

**Risk:** Medium (requires async infrastructure)

**Integration Point:** Parallelize steps in `integrated_pipeline_*.py`

### Option 3: Data Quality Gate (CI/CD Integration)

**Pros:**
- Prevents "Garbage In" at pipeline entry
- Operational stability improvement

**Cons:**
- Initial resistance to strict rules
- Risk of workflow disruption if gates too strict

**Risk:** Low (Warn/Fail mode separation)

**Integration Point:** Pre-commit hooks + pipeline internal validation

---

## 4. RED → GREEN → REFACTOR Roadmap

### RED (Problem)

**Current Issues:**
- Raw data used directly → ambiguity → hallucinations/cost increase
- Example: `BALLAST_SEQUENCE.csv` shows VOID3 with `FILL` action (should be `PRE_BALLAST_ONLY` → `NONE`)
- Mixed case actions (`Fill`, `DISCHARGE`, `fill`) → inconsistent LLM interpretation
- Decimal precision inconsistency (152.08 vs 152.080000) → calculation errors

### GREEN (Pillar/Blob)

**Implementation Steps:**
1. **Define Rules**: Date format (YYYY-MM-DD), Decimal precision (2 places), Action codes (uppercase enum)
2. **Create Pydantic Models**: `BallastSequenceRow`, `TankCatalogRow` with domain constraints
3. **Implement Tidying Pipeline**: `LogiDataTider` class for normalization
4. **Integrate with Validator**: Extend `DataQualityValidator` with tidying + Pydantic validation
5. **Add Cross-Validation**: Tank catalog operability checks (VOID3, capacity limits)

**Deliverables:**
- `ssot/tidying_models.py`: Pydantic models
- `ssot/data_quality_validator.py`: Extended with tidying pipeline
- Tests: `tests/test_tidying_pipeline.py`

### REFACTOR (Owner/Status)

**Owner:** Python Dev Team
**Status:** Design → Pilot (small scale) → Rollout (gate enforcement)
**KPI:**
- Accuracy: Validation error rate < 1%
- Reproducibility: Same input → same output (deterministic)
- Missing Rate: Cross-validation coverage > 95%
- Approval Time: Human review < 5 min per batch

---

## 5. Code Implementation

### 5.1 Pydantic Models (New File: `ssot/tidying_models.py`)

```python
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
from pydantic import BaseModel, Field, field_validator, model_validator


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
    stage: str = Field(min_length=1, description="Stage name (required)")
    step: Optional[int] = Field(default=None, ge=1, description="Step number (1-based, optional for OPTION)")
    tank: str = Field(min_length=1, description="Tank ID (required)")
    action: BallastAction = Field(description="Ballast action (FILL/DISCHARGE/NONE)")
    start_t: Optional[Decimal] = Field(default=None, ge=0, decimal_places=2, description="Start tonnage")
    delta_t: Decimal = Field(decimal_places=2, description="Delta tonnage")
    target_t: Optional[Decimal] = Field(default=None, ge=0, decimal_places=2, description="Target tonnage")
    pump_id: Optional[str] = Field(default=None, description="Pump ID")
    pump_rate_tph: Decimal = Field(gt=0, decimal_places=2, description="Pump rate (tph)")
    time_h: Optional[Decimal] = Field(default=None, ge=0, decimal_places=2, description="Operating time (hours)")
    valve_lineup: Optional[str] = Field(default=None, description="Valve lineup")
    draft_fwd: Optional[Decimal] = Field(default=None, ge=0, le=3.65, decimal_places=2)
    draft_aft: Optional[Decimal] = Field(default=None, ge=0, le=3.65, decimal_places=2)
    trim_cm: Optional[Decimal] = Field(default=None, decimal_places=2)
    ukc: Optional[Decimal] = Field(default=None, ge=0, decimal_places=2)
    hold_point: Optional[Literal["Y", "N"]] = Field(default=None)
    notes: Optional[str] = Field(default=None)
    priority: Optional[int] = Field(default=None, ge=1, le=5, description="Priority (1=highest, 5=lowest)")
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
        s = str(v).strip()
        if not s:
            raise ValueError("Stage name cannot be empty")
        return s

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

        # Target_t <= Max_t (if available from tank catalog)
        # Note: This requires tank catalog lookup, handled in TidyingPipeline

        return self


class TankCatalogRow(BaseModel):
    """Validated row from tank catalog"""
    tank_id: str = Field(min_length=1, alias="Tank")
    capacity_t: Decimal = Field(gt=0, decimal_places=2)
    x_from_mid_m: Decimal = Field(decimal_places=3)
    current_t: Decimal = Field(ge=0, decimal_places=2)
    min_t: Decimal = Field(ge=0, decimal_places=2)
    max_t: Decimal = Field(ge=0, decimal_places=2)
    mode: str = Field(description="Tank mode (FILL_DISCHARGE/DISCHARGE_ONLY/FIXED)")
    use_flag: Literal["Y", "N"] = Field(description="Use flag")
    operability: Optional[TankOperability] = Field(default=None)
    pump_rate_tph: Optional[Decimal] = Field(default=None, gt=0, decimal_places=2)

    @field_validator("tank_id", mode="before")
    @classmethod
    def normalize_tank_id(cls, v):
        return str(v).strip().upper()

    @model_validator(mode="after")
    def validate_capacity(self):
        """Validate capacity constraints"""
        if self.min_t > self.max_t:
            raise ValueError(f"Min_t ({self.min_t}) > Max_t ({self.max_t})")
        if self.max_t > self.capacity_t:
            raise ValueError(f"Max_t ({self.max_t}) > Capacity_t ({self.capacity_t})")
        if self.current_t > self.capacity_t:
            raise ValueError(f"Current_t ({self.current_t}) > Capacity_t ({self.capacity_t})")
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
                    self.df[col] = pd.to_datetime(self.df[col], errors="coerce").dt.strftime("%Y-%m-%d")
                except Exception as e:
                    self.warnings.append(f"Date column '{col}' normalization failed: {e}")
        return self

    def tidy_decimal_columns(
        self,
        columns: List[str],
        decimal_places: int = 2
    ) -> "LogiDataTider":
        """Normalize decimal columns to specified precision"""
        for col in columns:
            if col in self.df.columns:
                try:
                    self.df[col] = self.df[col].apply(
                        lambda x: round(float(x), decimal_places) if pd.notna(x) else None
                    )
                except Exception as e:
                    self.warnings.append(f"Decimal column '{col}' normalization failed: {e}")
        return self

    def tidy_action_case(self, action_column: str = "Action") -> "LogiDataTider":
        """Normalize action column to uppercase"""
        if action_column in self.df.columns:
            self.df[action_column] = (
                self.df[action_column]
                .astype(str)
                .str.strip()
                .str.upper()
            )
        return self

    def tidy_tank_ids(self, tank_column: str = "Tank") -> "LogiDataTider":
        """Normalize tank ID column (strip, uppercase)"""
        if tank_column in self.df.columns:
            self.df[tank_column] = (
                self.df[tank_column]
                .astype(str)
                .str.strip()
                .str.upper()
            )
        return self

    def validate_with_schema(
        self,
        model_class: type[BaseModel],
        column_mapping: Optional[Dict[str, str]] = None
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

        for idx, row_dict in df_mapped.to_dict(orient="records").items():
            try:
                # Handle Pydantic aliases (e.g., "Tank" -> "tank_id")
                model = model_class(**row_dict)
                validated.append(model)
            except Exception as e:
                errors.append(f"Row {idx}: {type(e).__name__}: {e}")

        return validated, errors

    def to_llm_markdown(
        self,
        max_rows: int = 50,
        sample: bool = False
    ) -> str:
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

        return f"{note}{view.to_markdown(index=False)}"
```

### 5.2 Integration with Existing Validator

**File:** `ssot/data_quality_validator.py` (extend existing class)

```python
# Add to existing DataQualityValidator class

from ssot.tidying_models import LogiDataTider, BallastSequenceRow, TankCatalogRow, TankOperability, BallastAction

class DataQualityValidator:
    # ... existing code ...

    def tidy_and_validate_ballast_sequence(
        self,
        file_path: Path,
        tank_catalog_path: Optional[Path] = None,
        deliverable_id: str = "BALLAST_EXEC_CSV"
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
        results = {
            "file": str(file_path.name),
            "deliverable_id": deliverable_id,
            "tidying": {"errors": [], "warnings": []},
            "validation": {"errors": [], "warnings": []},
            "cross_validation": {"errors": [], "warnings": []},
            "llm_context": None,
            "validated_count": 0,
            "total_rows": 0
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
                ["Start_t", "Delta_t", "Target_t", "PumpRate_tph", "Time_h",
                 "Draft_FWD", "Draft_AFT", "Trim_cm", "UKC"],
                decimal_places=2
            )
            results["tidying"]["warnings"] = tider.warnings

            # Step 3: Validate with Pydantic schema
            column_mapping = {
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
                "Rationale": "rationale"
            }

            validated_rows, validation_errors = tider.validate_with_schema(
                BallastSequenceRow,
                column_mapping=column_mapping
            )
            results["validation"]["errors"] = validation_errors
            results["validated_count"] = len(validated_rows)

            # Step 4: Cross-validate with tank catalog (VOID3 operability check)
            if tank_catalog_path and tank_catalog_path.exists():
                try:
                    tank_catalog_df = pd.read_csv(tank_catalog_path, encoding="utf-8-sig")
                    tank_catalog_tider = LogiDataTider(tank_catalog_df)
                    tank_catalog_rows, _ = tank_catalog_tider.validate_with_schema(
                        TankCatalogRow,
                        column_mapping={"Tank": "tank_id"}
                    )

                    # Build tank lookup
                    tank_lookup = {t.tank_id: t for t in tank_catalog_rows}

                    # Check VOID3 operability violations
                    for row in validated_rows:
                        if row.tank.startswith("VOID3"):
                            tank_info = tank_lookup.get(row.tank)
                            if tank_info:
                                if tank_info.operability == TankOperability.PRE_BALLAST_ONLY:
                                    if row.action != BallastAction.NONE:
                                        results["cross_validation"]["errors"].append(
                                            f"Row {row.step or 'N/A'}: {row.tank} has action={row.action.value} "
                                            f"but operability=PRE_BALLAST_ONLY (should be NONE)"
                                        )

                                # Check Target_t <= Max_t (if Target_t present)
                                if row.target_t is not None and row.target_t > tank_info.max_t:
                                    results["cross_validation"]["errors"].append(
                                        f"Row {row.step or 'N/A'}: {row.tank} Target_t={row.target_t} > Max_t={tank_info.max_t}"
                                    )
                except Exception as e:
                    results["cross_validation"]["warnings"].append(
                        f"Tank catalog cross-validation failed: {type(e).__name__}: {e}"
                    )

            # Step 5: Generate LLM-ready context (only if validation passed)
            if (not results["validation"]["errors"] and
                not results["cross_validation"]["errors"] and
                len(validated_rows) > 0):
                results["llm_context"] = tider.to_llm_markdown(max_rows=50)
            else:
                results["llm_context"] = None  # Fail-fast: no LLM input if validation failed

            return results

        except Exception as e:
            results["tidying"]["errors"].append(
                f"Tidying pipeline failed: {type(e).__name__}: {e}"
            )
            return results
```

### 5.3 Pipeline Integration

**File:** `integrated_pipeline_*.py` (add tidying step before LLM/analysis)

```python
# Add to integrated_pipeline after Step 4b (Ballast Sequence Generation)

from ssot.data_quality_validator import DataQualityValidator
from pathlib import Path

# After generating BALLAST_EXEC.csv
if args.enable_sequence:
    ballast_exec_csv = out_dir / "BALLAST_EXEC.csv"
    tank_catalog_csv = out_dir / "ssot" / "tank_ssot_for_solver.csv"

    # Tidying + Validation
    validator = DataQualityValidator(registry_path=Path("headers_registry.json"))
    tidying_results = validator.tidy_and_validate_ballast_sequence(
        file_path=ballast_exec_csv,
        tank_catalog_path=tank_catalog_csv,
        deliverable_id="BALLAST_EXEC_CSV"
    )

    # Log results
    if tidying_results["tidying"]["errors"]:
        print(f"[ERROR] Tidying failed: {tidying_results['tidying']['errors']}")

    if tidying_results["validation"]["errors"]:
        print(f"[ERROR] Validation failed: {tidying_results['validation']['errors']}")

    if tidying_results["cross_validation"]["errors"]:
        print(f"[ERROR] Cross-validation failed: {tidying_results['cross_validation']['errors']}")

    # Only proceed with LLM/analysis if validation passed
    if tidying_results["llm_context"]:
        print(f"[OK] Tidying complete: {tidying_results['validated_count']}/{tidying_results['total_rows']} rows validated")
        # Use tidying_results["llm_context"] for LLM input
    else:
        print(f"[WARN] Validation failed, skipping LLM analysis")
```

### 5.4 Tests (pytest)

**File:** `tests/test_tidying_pipeline.py`

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for Tidying Pipeline
"""

import pytest
import pandas as pd
from decimal import Decimal
from pathlib import Path

from ssot.tidying_models import (
    LogiDataTider,
    BallastSequenceRow,
    BallastAction,
    TankCatalogRow,
    TankOperability
)


def test_tidy_action_case():
    """Test action case normalization"""
    df = pd.DataFrame({
        "Action": ["Fill", "DISCHARGE", "fill", "discharge"]
    })

    tider = LogiDataTider(df)
    tider.tidy_action_case("Action")

    assert all(df["Action"].str.isupper())
    assert df["Action"].tolist() == ["FILL", "DISCHARGE", "FILL", "DISCHARGE"]


def test_tidy_decimal_columns():
    """Test decimal precision normalization"""
    df = pd.DataFrame({
        "Delta_t": [152.080000, 30.123456, 0.0]
    })

    tider = LogiDataTider(df)
    tider.tidy_decimal_columns(["Delta_t"], decimal_places=2)

    assert df["Delta_t"].tolist() == [152.08, 30.12, 0.0]


def test_validate_ballast_sequence_row():
    """Test Pydantic validation"""
    row_dict = {
        "stage": "Stage 5_PreBallast",
        "step": 1,
        "tank": "VOID3.S",
        "action": "FILL",
        "start_t": 0.0,
        "delta_t": 152.08,
        "target_t": 152.08,
        "pump_rate_tph": 10.0,
        "time_h": 15.21,
    }

    row = BallastSequenceRow(**row_dict)
    assert row.action == BallastAction.FILL
    assert row.target_t == Decimal("152.08")


def test_void3_operability_violation():
    """Test VOID3 PRE_BALLAST_ONLY constraint (cross-validation)"""
    # This test would be in DataQualityValidator.tidy_and_validate_ballast_sequence
    # VOID3 with PRE_BALLAST_ONLY should not have FILL/DISCHARGE actions
    pass  # Integration test in test_data_quality_validator.py


def test_physics_validation():
    """Test Target_t = Start_t + Delta_t constraint"""
    row_dict = {
        "stage": "Stage 5_PreBallast",
        "step": 1,
        "tank": "FWB2.P",
        "action": "DISCHARGE",
        "start_t": 50.0,
        "delta_t": -30.0,
        "target_t": 20.0,  # Correct: 50.0 + (-30.0) = 20.0
        "pump_rate_tph": 10.0,
        "time_h": 3.0,
    }

    row = BallastSequenceRow(**row_dict)
    assert row.target_t == Decimal("20.0")

    # Test violation
    row_dict["target_t"] = 25.0  # Wrong: should be 20.0
    with pytest.raises(ValueError, match="Target_t.*Start_t.*Delta_t"):
        BallastSequenceRow(**row_dict)
```

---

## 6. QA Checklist (Gate Enforcement)

- [ ] **Schema Validation Failure → LLM Input Blocked** (Fail-fast)
- [ ] **Date/Decimal/Code Standardization Rules** (Single SSOT, documented + tested)
- [ ] **Parallel Processing** (Rate limit semaphore + exponential backoff retry)
- [ ] **Security**: Keys in `.env`/Secrets, no PII/Key exposure in logs
- [ ] **Context Generation**: Sampling/aggregation + evidence links (record IDs) instead of raw dump
- [ ] **VOID3 Operability**: PRE_BALLAST_ONLY constraint enforced at schema level
- [ ] **Capacity Limits**: Target_t <= Max_t validated with tank catalog
- [ ] **Physics Constraints**: Target_t = Start_t + Delta_t (within tolerance)

---

## 7. Integration Roadmap

### Phase 1: Pydantic Models (Week 1)
- [ ] Create `ssot/tidying_models.py`
- [ ] Define `BallastSequenceRow`, `TankCatalogRow` models
- [ ] Add domain constraints (VOID3 operability, capacity limits, physics)

### Phase 2: Tidying Pipeline Integration (Week 1)
- [ ] Implement `LogiDataTider` class
- [ ] Extend `DataQualityValidator.tidy_and_validate_ballast_sequence()`
- [ ] Add cross-validation with tank catalog

### Phase 3: Pipeline Integration (Week 2)
- [ ] Add tidying step to `integrated_pipeline_*.py` (after Step 4b)
- [ ] Fail-fast: Skip LLM/analysis if validation fails
- [ ] Generate validation report (JSON + Markdown)

### Phase 4: CI/CD Gate Integration (Week 2)
- [ ] Pre-commit hook (Ruff/Black)
- [ ] Pipeline internal validation gate (Warn/Fail mode)
- [ ] Audit log generation

---

## 8. Command Recommendations

```bash
# Code quality
ruff check . && ruff format .

# Tests
pytest tests/test_tidying_pipeline.py -v
pytest tests/test_data_quality_validator.py -v

# Pre-commit setup
pre-commit install

# Run tidying pipeline manually
python -m ssot.data_quality_validator \
  --registry headers_registry.json \
  --final-dir pipeline_out_*/ \
  --output DATA_QUALITY_REPORT.json

# Validate specific file
python -c "
from pathlib import Path
from ssot.data_quality_validator import DataQualityValidator
validator = DataQualityValidator(Path('headers_registry.json'))
results = validator.tidy_and_validate_ballast_sequence(
    Path('BALLAST_EXEC.csv'),
    tank_catalog_path=Path('ssot/tank_ssot_for_solver.csv')
)
print(results)
"
```

---

## 9. Benefits & Expected Outcomes

### 9.1 Context Quality Improvement
- **Before**: Raw CSV with mixed case, inconsistent precision → LLM confusion
- **After**: Normalized, validated data → Clear context, reduced hallucinations

### 9.2 Cost Reduction
- **Before**: LLM processes invalid data → wasted tokens, retries
- **After**: Fail-fast → Only valid data sent to LLM → Cost savings

### 9.3 Reproducibility
- **Before**: Same input → different outputs (due to data ambiguity)
- **After**: Same input → same output (deterministic tidying + validation)

### 9.4 Domain Constraint Enforcement
- **VOID3 Operability**: PRE_BALLAST_ONLY constraint caught at validation stage
- **Capacity Limits**: Target_t > Max_t detected before execution
- **Physics Constraints**: Target_t = Start_t + Delta_t validated

---

## 10. References

- **Existing Infrastructure:**
  - `ssot/headers_registry.py`: Header schema registry
  - `ssot/data_quality_validator.py`: Data quality validation
  - `ssot/head_guard_v2.py`: Header validation
  - `ssot/headers_writer.py`: Schema application

- **Related Documentation:**
  - `03_DOCUMENTATION/00_CORE_ARCHITECTURE/02_Data_Flow_SSOT.md`: SSOT architecture
  - `03_DOCUMENTATION/00_CORE_ARCHITECTURE/06_Script_Interfaces.md`: Script interfaces
  - `HEADERS_SSOT_INTEGRATION_SUMMARY.md`: Headers registry integration

- **External Resources:**
  - Pydantic v2 Documentation: https://docs.pydantic.dev/
  - Ruff Documentation: https://docs.astral.sh/ruff/
  - Black Documentation: https://black.readthedocs.io/

---

**Document Version:** v1.0
**Last Updated:** 2025-12-29
**Status:** Design Phase (Ready for Implementation)

