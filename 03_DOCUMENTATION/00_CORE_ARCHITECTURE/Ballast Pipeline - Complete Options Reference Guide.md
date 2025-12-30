# Ballast Pipeline - Complete Options Reference Guide

**Version**: v1.1
**Last Updated**: 2025-12-30
**Purpose**: Comprehensive reference for all pipeline command-line options
**Target Audience**: Advanced users, operators, developers

---

## Table of Contents

1. [Overview](#1-overview)
2. [Option Categories](#2-option-categories)
3. [Site and Profile Options](#3-site-and-profile-options)
4. [Step Control Options](#4-step-control-options)
5. [Gate Configuration Options](#5-gate-configuration-options)
6. [Tide and UKC Options](#6-tide-and-ukc-options)
7. [Sensor Data Options](#7-sensor-data-options)
8. [File Path Options](#8-file-path-options)
9. [Advanced Features Options](#9-advanced-features-options)
   - [9.5 Wave and Freeboard Options](#95-wave-and-freeboard-options)
   - [9.6 Tank Operability Options](#96-tank-operability-options)
   - [9.7 Data Conversion Options](#97-data-conversion-options)
10. [Debug and Reporting Options](#10-debug-and-reporting-options)
11. [Script Path Override Options](#11-script-path-override-options)
12. [Option Combinations and Examples](#12-option-combinations-and-examples)

---

## 1. Overview

### 1.1 Command Structure

```bash
python integrated_pipeline_defsplit_v2_gate270_split_v3_auditpatched_autodetect_TIDE_v1.py [OPTIONS]
```

### 1.2 Option Priority

1. **CLI Arguments** (Highest Priority): Explicitly provided command-line options
2. **Profile Values**: Values from site profile JSON (if CLI not provided)
3. **Default Values**: Built-in defaults

### 1.3 Option Format

- **Flags**: `--flag-name` (boolean, presence = True)
- **Values**: `--option-name VALUE` or `--option-name=VALUE`
- **Choices**: Limited to specific values (shown in brackets)

---

## 2. Option Categories

| Category | Options Count | Purpose |
|----------|--------------|---------|
| **Site & Profile** | 2 | Site selection and profile configuration |
| **Step Control** | 4 | Control which steps to execute |
| **Gate Configuration** | 7 | Set operational limits |
| **Tide & UKC** | 6 | Configure tide and UKC calculations |
| **Wave & Freeboard** | 2 | GL Noble Denton freeboard requirements |
| **Sensor Data** | 2 | Inject current tank levels |
| **File Paths** | 3 | Customize input/output locations |
| **Advanced Features** | 3 | Enable optional features |
| **Tank Operability** | 5 | Stage-specific tank constraints |
| **Data Conversion** | 2 | Tank/pump rate configuration |
| **Debug & Reporting** | 3 | Control reporting and debugging |
| **Script Paths** | 7 | Override default script locations |
| **Total** | **47+** | Complete pipeline control |

---

## 3. Site and Profile Options

### 3.1 `--site`

**Type**: Choice (AGI | DAS)
**Default**: `AGI`
**Required**: No

**Description**:
Specifies the site label for logging and default profile selection. This does not automatically change calculations; it primarily affects:
- Default profile path resolution
- Logging labels
- Output file naming

**Usage**:
```bash
--site AGI
--site DAS
```

**Profile Resolution Order** (when `--site` is used):
1. `inputs_dir/profiles/{SITE}.json`
2. `inputs_dir/profiles/site_{SITE}.json`
3. `inputs_dir/site_profile_{SITE}.json`

**Example**:
```bash
python integrated_pipeline_defsplit_v2_gate270_split_v3_auditpatched_autodetect_TIDE_v1.py --site AGI
```

**Notes**:
- Site label is used for logging and file naming only
- Actual calculations use profile values or CLI overrides
- Case-sensitive: Must be exactly "AGI" or "DAS"

---

### 3.2 `--profile_json`

**Type**: String (file path)
**Default**: `""` (empty, auto-detected)
**Required**: No

**Description**:
Explicit path to site profile JSON file. When provided, this overrides automatic profile detection.

**⚠️ Important: Profile Adjustment Before Pipeline Execution**
The site profile JSON file (e.g., `01_EXECUTION_FILES/bplus_inputs/profiles/AGI.json`) can be edited **before pipeline execution** to adjust:
- Gate limits (`fwd_max_m`, `aft_min_m`, `aft_max_m`, `trim_abs_limit_m`)
- Pump rates (`pump_rate_tph`)
- Tide/UKC parameters (`forecast_tide_m`, `depth_ref_m`, `ukc_min_m`)
- Tank operability settings (`tank_operability`, `tank_overrides`)
- Critical stage definitions (`critical_stage_list`)

**Profile values are loaded at pipeline startup**, so any changes to the profile file must be made **before running the pipeline**. CLI arguments will override profile values if both are provided.

**Usage**:
```bash
--profile_json "01_EXECUTION_FILES/bplus_inputs/profiles/AGI.json"
--profile_json "custom_profile.json"
```

**Profile Structure**:
```json
{
  "site": "AGI",
  "gates": {
    "fwd_max_m": 2.70,
    "aft_min_m": 2.70,
    "aft_max_m": 3.50
  },
  "tank_overrides": {
    "FWB2.P": {
      "use_flag": "Y",
      "mode": "FILL_DISCHARGE"
    }
  },
  "tide_ukc": {
    "forecast_tide_m": 1.5,
    "depth_ref_m": 10.0,
    "ukc_min_m": 2.0
  }
}
```

**Priority**:
1. CLI arguments (e.g., `--fwd_max 2.70`)
2. Profile JSON values
3. Built-in defaults

**Example**:
```bash
python integrated_pipeline_defsplit_v2_gate270_split_v3_auditpatched_autodetect_TIDE_v1.py \
  --profile_json "profiles/custom_AGI.json"
```

**Notes**:
- Use absolute or relative path
- Profile values are overridden by CLI arguments
- If file not found, pipeline will attempt auto-detection

---

## 4. Step Control Options

### 4.1 `--from_step`

**Type**: Integer (0-5)
**Default**: `1`
**Required**: No

**Description**:
Specifies the starting step for pipeline execution. Steps are:
- **Step 0**: SPMT cargo input generation (optional)
- **Step 1**: TR Excel generation (optional)
- **Step 1b**: `stage_results.csv` generation (required for subsequent steps)
- **Step 2**: OPS Integrated Report
- **Step 3**: Ballast Gate Solver (LP optimization)
- **Step 4**: Ballast Optimizer (heuristic optimization, optional)
- **Step 5**: Bryan Template generation

**Usage**:
```bash
--from_step 1    # Start from Step 1
--from_step 3    # Start from Step 3 (requires stage_results.csv exists)
```

**Example**:
```bash
# Run only solver (Step 3)
python integrated_pipeline_defsplit_v2_gate270_split_v3_auditpatched_autodetect_TIDE_v1.py \
  --site AGI \
  --from_step 3 \
  --to_step 3
```

**Dependencies**:
- Step 2+ requires `stage_results.csv` (from Step 1b)
- Step 3+ requires SSOT CSV files (from PREP)
- Step 4 requires Step 3 output

**Notes**:
- Step 1b is automatically executed if `stage_results.csv` is missing
- Cannot skip required steps (e.g., cannot run Step 3 without Step 1b)

---

### 4.2 `--to_step`

**Type**: Integer (0-5)
**Default**: `5`
**Required**: No

**Description**:
Specifies the ending step for pipeline execution. Pipeline will execute from `--from_step` to `--to_step` (inclusive).

**Usage**:
```bash
--to_step 3      # End at Step 3
--to_step 5      # Run all steps (default)
```

**Example**:
```bash
# Run steps 1-3 only (skip optimizer and template)
python integrated_pipeline_defsplit_v2_gate270_split_v3_auditpatched_autodetect_TIDE_v1.py \
  --site AGI \
  --from_step 1 \
  --to_step 3
```

**Common Combinations**:
- `--from_step 1 --to_step 1`: Generate `stage_results.csv` only
- `--from_step 1 --to_step 2`: Generate reports (no optimization)
- `--from_step 1 --to_step 3`: Include solver (recommended minimum)
- `--from_step 1 --to_step 4`: Include optimizer
- `--from_step 1 --to_step 5`: Full pipeline (default)

**Notes**:
- Steps execute sequentially
- Each step may have dependencies on previous steps
- Step 4 and 5 are optional

---

### 4.3 `--enable-sequence`

**Type**: Flag (boolean)
**Default**: `False`
**Required**: No

**Description**:
Enables Step 4b: Ballast Sequence Generator. This generates operational sequence files from the ballast plan.

**Usage**:
```bash
--enable-sequence
```

**Additional Outputs Generated**:
- `BALLAST_OPTION.csv`: Planning level (Delta_t centered, all stages)
- `BALLAST_EXEC.csv`: Execution sequence (Start_t/Target_t chain, Stage 6B excluded)
- `BALLAST_SEQUENCE.csv`: Legacy format (compatibility)
- `BALLAST_SEQUENCE.xlsx`: Excel with 3 sheets (Option, Exec, Legacy)
- `BALLAST_OPERATIONS_CHECKLIST.md`: Operational checklist
- `HOLD_POINT_SUMMARY.csv`: Hold point summary

**Requirements**:
- Step 3 or Step 4 must be executed (ballast plan required)
- `ballast_sequence_generator.py` must be available

**Example**:
```bash
python integrated_pipeline_defsplit_v2_gate270_split_v3_auditpatched_autodetect_TIDE_v1.py \
  --site AGI \
  --enable-sequence
```

**Features**:
- **Option/Execution Separation**: Planning vs. execution sequence
- **Start_t/Target_t Carry-forward**: Accurate tank state tracking
- **Stage 6B Separation**: Optional stages excluded from execution sequence
- **Tank Capacity Validation**: Automatic clipping when capacity exceeded

**Notes**:
- Requires ballast plan from Step 3 or Step 4
- Sequence files are generated in the output directory
- Excel file contains 3 sheets for different use cases

---

### 4.4 `--enable-valve-lineup`

**Type**: Flag (boolean)
**Default**: `False`
**Required**: No

**Description**:
Enables Step 4c: Valve Lineup Generator. Adds valve lineup information to ballast sequence.

**Usage**:
```bash
--enable-valve-lineup
```

**Additional Outputs Generated**:
- `BALLAST_SEQUENCE_WITH_VALVES.md`: Operational procedures with valve lineup

**Requirements**:
- `--enable-sequence` must be enabled
- `valve_lineup_generator.py` must be available
- `valve_map.json` must exist

**Example**:
```bash
python integrated_pipeline_defsplit_v2_gate270_split_v3_auditpatched_autodetect_TIDE_v1.py \
  --site AGI \
  --enable-sequence \
  --enable-valve-lineup
```

**Features**:
- Automatic valve sequence generation per tank
- Fill/Discharge valve sequences
- Safety procedures (vent, emergency valves)

**Notes**:
- Requires `--enable-sequence` to be set
- Valve map must be configured in `valve_map.json`

---

## 5. Gate Configuration Options

### 5.1 `--fwd_max`

**Type**: Float (meters)
**Default**: `2.70` (from profile or built-in)
**Required**: No

**Description**:
Maximum forward draft limit (Gate-B). This is the maximum allowed forward draft, typically 2.70m for critical RoRo stages.

**Usage**:
```bash
--fwd_max 2.70
--fwd_max 2.80
```

**Gate Label**: `FWD_MAX_2p70_critical_only` (Gate-B, Mammoet)

**Application**:
- Applied to critical stages only (Stage 5_PreBallast, Stage 6A_Critical)
- Non-critical stages: `N/A` (prevents false failures)
- Chart Datum reference

**Gate-B Margin Calculation (SSOT)**:
```
GateB_FWD_MAX_2p70_CD_Margin_m = 2.70 - Draft_FWD_m_CD
```

**Where:**
- `Draft_FWD_m_CD` = `Draft_FWD_m - Forecast_Tide_m` (Chart Datum reference)
- Positive margin: FWD draft within limit
- Negative margin: FWD draft exceeds 2.70m (Gate-B violation)

**⚠️ Important:** Always check `Draft_FWD_m_CD` (not `Draft_FWD_m`) when interpreting Gate-B margins.

**Example**:
```bash
python integrated_pipeline_defsplit_v2_gate270_split_v3_auditpatched_autodetect_TIDE_v1.py \
  --site AGI \
  --fwd_max 2.70
```

**Example Interpretation**:
- `Draft_FWD_m` = 2.19m, `Forecast_Tide_m` = 2.0m
- `Draft_FWD_m_CD` = 2.19 - 2.0 = 0.19m (Chart Datum)
- `GateB_Margin` = 2.70 - 0.19 = 2.51m ✅ (safe margin)

**Notes**:
- Critical stage determination: `DEFAULT_CRITICAL_STAGE_REGEX` or profile `critical_stage_list`
- Always use with `--aft_min` for complete gate configuration
- Value in meters
- **Chart Datum reference**: Gate-B uses Chart Datum (tide-adjusted) draft, not absolute draft

---

### 5.2 `--aft_min`

**Type**: Float (meters)
**Default**: `2.70` (from profile or built-in)
**Required**: No

**Description**:
Minimum aft draft limit (Gate-A). This is the minimum required aft draft to ensure propeller efficiency and propulsion capability.

**Usage**:
```bash
--aft_min 2.70
--aft_min 2.80
```

**Gate Label**: `AFT_MIN_2p70` (Gate-A, Captain)

**Application**:
- Applied to all stages
- Critical for propeller operation
- ITTC reference: Shaft centreline immersion (minimum 1.5D, recommended 2.0D)

**Example**:
```bash
python integrated_pipeline_defsplit_v2_gate270_split_v3_auditpatched_autodetect_TIDE_v1.py \
  --site AGI \
  --aft_min 2.70
```

**Notes**:
- Most critical gate (propeller operation)
- Always enforced (not stage-specific)
- Value in meters

---

### 5.3 `--aft_max`

**Type**: Float (meters)
**Default**: `3.50` (from profile or built-in)
**Required**: No

**Description**:
Maximum aft draft limit for optimizer. Used as upper bound in Step 4 (Optimizer).

**Usage**:
```bash
--aft_max 3.50
--aft_max 3.60
```

**Application**:
- Used by Optimizer (Step 4) as upper limit
- Not enforced by Solver (Step 3)
- AFT_MIN is enforced by Solver

**Example**:
```bash
python integrated_pipeline_defsplit_v2_gate270_split_v3_auditpatched_autodetect_TIDE_v1.py \
  --site AGI \
  --aft_max 3.50
```

**Notes**:
- Different from `--aft_min` (which is enforced)
- Used for optimization bounds only
- Value in meters

---

### 5.4 `--trim_abs_limit`

**Type**: Float (meters)
**Default**: `0.50` (from profile or built-in)
**Required**: No

**Description**:
Absolute trim limit. Maximum allowed absolute trim value (by stern or by head).

**Usage**:
```bash
--trim_abs_limit 0.50
--trim_abs_limit 0.60
```

**Enforcement**:
- Can be enforced as hard constraint (see `--trim_limit_enforced`)
- Applied in Solver (Step 3)

**Example**:
```bash
python integrated_pipeline_defsplit_v2_gate270_split_v3_auditpatched_autodetect_TIDE_v1.py \
  --site AGI \
  --trim_abs_limit 0.50
```

**Notes**:
- Absolute value (both positive and negative trim)
- Value in meters
- Use with `--trim_limit_enforced` to enable/disable enforcement

---

### 5.5 `--trim_limit_enforced` / `--no-trim-limit-enforced`

**Type**: Flag (boolean)
**Default**: `True` (enforced)
**Required**: No

**Description**:
Enable or disable hard enforcement of trim limit.

**Usage**:
```bash
--trim_limit_enforced        # Enable (default)
--no-trim-limit-enforced     # Disable
```

**Example**:
```bash
# Disable trim limit enforcement
python integrated_pipeline_defsplit_v2_gate270_split_v3_auditpatched_autodetect_TIDE_v1.py \
  --site AGI \
  --no-trim-limit-enforced
```

**Notes**:
- Default is enforced (hard constraint)
- Use `--no-trim-limit-enforced` to make it soft constraint

---

### 5.6 `--freeboard_min_m`

**Type**: Float (meters)
**Default**: `0.0` (from profile or built-in)
**Required**: No

**Description**:
Minimum freeboard requirement. Prevents deck wetting and downflooding.

**Usage**:
```bash
--freeboard_min_m 0.0
--freeboard_min_m 0.5
```

**Calculation (SSOT)**:
```
Freeboard = D_vessel_m - Draft
Freeboard_Min = min(Freeboard_FWD, Freeboard_AFT)
Gate: Freeboard_Min >= freeboard_min_m
```

**⚠️ SSOT Gap - Operational Minimum Freeboard**:
- **Current Implementation**: Default `freeboard_min_m = 0.0` (no operational buffer)
- **Current Gate**: Only prevents negative freeboard (deck wet)
- **Missing**: Operational minimum freeboard requirement (e.g., 0.20m, 0.50m for operations)
- **Recommendation**: Define operational minimum freeboard in SSOT (AGENTS.md) based on operational requirements
- **When Freeboard = 0.00m**: Deck edge at waterline → requires engineering verification (class acceptance, load-line compliance)

**Enforcement**:
- Can be enforced as hard constraint (see `--freeboard_min_enforced`)
- Applied in Solver (Step 3)

**Example**:
```bash
python integrated_pipeline_defsplit_v2_gate270_split_v3_auditpatched_autodetect_TIDE_v1.py \
  --site AGI \
  --freeboard_min_m 0.0
```

**Example (Freeboard = 0.00m - Critical)**:
- When draft is clipped to `D_vessel` (3.65m), `Freeboard_Min_m = 0.00m`
- **Risk**: Deck edge at waterline → green water, structural stress
- **Required**: Engineering verification (class acceptance, load-line compliance)

**Notes**:
- Value in meters
- Freeboard is independent of tide (vessel rises with tide)
- Use with `--freeboard_min_enforced` to enable/disable enforcement
- **Operational minimum**: Consider setting `--freeboard_min_m` to operational requirement (e.g., 0.20m, 0.50m)

---

### 5.7 `--freeboard_min_enforced` / `--no-freeboard-min-enforced`

**Type**: Flag (boolean)
**Default**: `True` (enforced)
**Required**: No

**Description**:
Enable or disable hard enforcement of minimum freeboard.

**Usage**:
```bash
--freeboard_min_enforced        # Enable (default)
--no-freeboard-min-enforced     # Disable
```

**Example**:
```bash
# Disable freeboard enforcement
python integrated_pipeline_defsplit_v2_gate270_split_v3_auditpatched_autodetect_TIDE_v1.py \
  --site AGI \
  --no-freeboard-min-enforced
```

---

### 5.8 `--gate_guard_band_cm`

**Type**: Float (centimeters)
**Default**: `2.0`
**Required**: No

**Description**:
Gate guard-band tolerance in centimeters. Provides operational margin for sensor error and fluid dynamics.

**Usage**:
```bash
--gate_guard_band_cm 2.0   # Production (default)
--gate_guard_band_cm 1.0   # Development (minimal margin)
--gate_guard_band_cm 0.0   # Strict (exact validation)
```

**Application**:
- Applied to Gate-A (AFT_MIN_2p70): `AFT >= (2.70 - guard_band/100)` → PASS
- Applied to Gate-B (FWD_MAX_2p70_critical_only): `FWD <= (2.70 + guard_band/100)` → PASS
- Production: 2.0cm (operational tolerance)
- Development: 1.0cm (minimal margin)
- Strict: 0.0cm (exact validation, no tolerance)

**Example**:
```bash
python integrated_pipeline_defsplit_v2_gate270_split_v3_auditpatched_autodetect_TIDE_v1.py \
  --site AGI \
  --gate_guard_band_cm 2.0
```

**Notes**:
- Default: 2.0cm (recommended for production)
- Use 0.0cm only for strict validation
- Value in centimeters (converted to meters internally)

---

## 6. Tide and UKC Options

### 6.1 `--forecast_tide`

**Type**: Float (meters)
**Default**: `None` (from profile or auto-detected)
**Required**: No

**Description**:
Forecast tide level. Used for UKC calculations. This has the **highest priority** in the 5-tier tide integration system.

**Usage**:
```bash
--forecast_tide 1.5
--forecast_tide 2.0
```

**Priority (5-tier system)**:
1. **Priority 0**: CLI `--forecast_tide` (highest, this option)
2. Priority 1: `--stage_tide_csv`
3. Priority 2: `tide_windows` (from profile)
4. Priority 3: `stage_schedule` (tide table interpolation)
5. Priority 4: CLI `--forecast_tide` (fillna, safety mechanism)

**Application**:
- Applied to all stages uniformly
- Used in UKC calculation: `UKC = (DepthRef + Forecast_Tide) - (Draft + Squat + Safety)`
- Ensures consistency between `stage_table_unified.csv` and `solver_ballast_summary.csv`

**Example**:
```bash
python integrated_pipeline_defsplit_v2_gate270_split_v3_auditpatched_autodetect_TIDE_v1.py \
  --site AGI \
  --forecast_tide 1.5
```

**Notes**:
- Highest priority in tide integration
- Value in meters (Chart Datum reference)
- Always use with `--depth_ref` and `--ukc_min` for UKC calculations

---

### 6.2 `--depth_ref`

**Type**: Float (meters)
**Default**: `None` (from profile)
**Required**: No

**Description**:
Reference depth (Chart Datum). Used for UKC calculations.

**Usage**:
```bash
--depth_ref 10.0
--depth_ref 12.5
```

**UKC Calculation**:
```
Available_Depth = depth_ref + forecast_tide
UKC = Available_Depth - (Draft + Squat + Safety_Allow)
```

**Example**:
```bash
python integrated_pipeline_defsplit_v2_gate270_split_v3_auditpatched_autodetect_TIDE_v1.py \
  --site AGI \
  --forecast_tide 1.5 \
  --depth_ref 10.0 \
  --ukc_min 2.0
```

**Notes**:
- Value in meters (Chart Datum)
- Required for UKC calculations
- Typically site-specific (port/channel depth)

---

### 6.3 `--ukc_min`

**Type**: Float (meters)
**Default**: `None` (from profile)
**Required**: No

**Description**:
Minimum Under Keel Clearance (UKC) requirement. Prevents grounding.

**Usage**:
```bash
--ukc_min 2.0
--ukc_min 1.5
```

**Gate Verification**:
```
Gate_UKC: UKC_Min >= ukc_min → "OK" | "NG" | "N/A"
```

**Example**:
```bash
python integrated_pipeline_defsplit_v2_gate270_split_v3_auditpatched_autodetect_TIDE_v1.py \
  --site AGI \
  --forecast_tide 1.5 \
  --depth_ref 10.0 \
  --ukc_min 2.0
```

**Notes**:
- Value in meters
- Required for UKC gate verification
- Typical values: 1.5m - 2.5m depending on conditions

---

### 6.4 `--squat`

**Type**: Float (meters)
**Default**: `0.0`
**Required**: No

**Description**:
Squat effect (vessel sinkage due to forward motion). Added to draft in UKC calculations.

**Usage**:
```bash
--squat 0.1
--squat 0.2
```

**UKC Calculation**:
```
UKC = (DepthRef + Forecast_Tide) - (Draft + Squat + Safety_Allow)
```

**Example**:
```bash
python integrated_pipeline_defsplit_v2_gate270_split_v3_auditpatched_autodetect_TIDE_v1.py \
  --site AGI \
  --forecast_tide 1.5 \
  --depth_ref 10.0 \
  --ukc_min 2.0 \
  --squat 0.1
```

**Notes**:
- Value in meters
- Typically 0.0 for static conditions
- May be significant at higher speeds

---

### 6.5 `--safety_allow`

**Type**: Float (meters)
**Default**: `0.0`
**Required**: No

**Description**:
Safety allowance. Additional margin added to draft in UKC calculations.

**Usage**:
```bash
--safety_allow 0.2
--safety_allow 0.5
```

**UKC Calculation**:
```
UKC = (DepthRef + Forecast_Tide) - (Draft + Squat + Safety_Allow)
```

**Example**:
```bash
python integrated_pipeline_defsplit_v2_gate270_split_v3_auditpatched_autodetect_TIDE_v1.py \
  --site AGI \
  --forecast_tide 1.5 \
  --depth_ref 10.0 \
  --ukc_min 2.0 \
  --safety_allow 0.2
```

**Notes**:
- Value in meters
- Additional safety margin
- Recommended: 0.2m - 0.5m

---

### 6.6 `--tide_tol`

**Type**: Float (meters)
**Default**: `0.10`
**Required**: No

**Description**:
Tide margin tolerance (m) for LIMIT vs OK determination. Used in tide verification logic.

**Usage**:
```bash
--tide_tol 0.10
--tide_tol 0.20
```

**Application**:
- Used in tide verification: `abs(forecast_tide - required_tide) <= tide_tol` → OK
- Default: 0.10m (10cm tolerance)
- Adjust based on operational requirements

**Example**:
```bash
python integrated_pipeline_defsplit_v2_gate270_split_v3_auditpatched_autodetect_TIDE_v1.py \
  --site AGI \
  --forecast_tide 1.5 \
  --tide_tol 0.10
```

**Notes**:
- Value in meters
- Used for tide verification consistency checks
- Default: 0.10m from `tide_constants.py`

---

## 7. Sensor Data Options

### 7.1 `--current_t_csv`

**Type**: String (file path)
**Default**: `""` (empty, auto-detected)
**Required**: No

**Description**:
Path to sensor/PLC/IoT CSV file containing current tank levels. Used to inject real-time tank levels into the pipeline.

**Usage**:
```bash
--current_t_csv "02_RAW_DATA/sensors/current_t_sensor.csv"
--current_t_csv "plc/current_t.csv"
```

**Auto-Detection Order** (if not specified):
1. `inputs_dir/current_t_sensor.csv`
2. `inputs_dir/current_t.csv`
3. `inputs_dir/sensors/current_t_sensor.csv`
4. `inputs_dir/sensors/current_t.csv`
5. `inputs_dir/plc/current_t.csv`
6. `inputs_dir/iot/current_t.csv`
7. Pattern search: `current_t_*.csv` (latest file)

**CSV Format**:
```csv
Tank,Current_t
FWB2.P,28.50
FWB2.S,28.50
VOIDDB2.P,0.0
```

**Supported Column Names**:
- **Tank identifier**: `Tank`, `tank_id`, `id`, `tag`, `name`
- **Value** (priority):
  1. `Current_t`, `current_ton`, `current_tons`, `tons`, `ton`, `amount_t`, `value_t`
  2. `level_pct`, `level_percent` (converted using Capacity_t)
  3. `volume_m3`, `vol_m3`, `m3` (with optional `spgr`)

**Example**:
```bash
python integrated_pipeline_defsplit_v2_gate270_split_v3_auditpatched_autodetect_TIDE_v1.py \
  --site AGI \
  --current_t_csv "02_RAW_DATA/sensors/current_t_sensor.csv" \
  --current_t_strategy override
```

**Notes**:
- Auto-detection available if file not specified
- Matching: Exact match or Group match (base name)
- Use with `--current_t_strategy` to control injection behavior

---

### 7.2 `--current_t_strategy`

**Type**: Choice (`override` | `fill_missing`)
**Default**: `override`
**Required**: No

**Description**:
Strategy for applying sensor values to Current_t in tank SSOT.

**Choices**:
- **`override`**: Always overwrite with sensor values (default)
- **`fill_missing`**: Only inject when Current_t is 0.0

**Usage**:
```bash
--current_t_strategy override
--current_t_strategy fill_missing
```

**Behavior**:

**`override` (default)**:
- Replaces all Current_t values with sensor values
- Use when sensor data is authoritative
- Recommended for real-time operations

**`fill_missing`**:
- Only updates tanks where Current_t = 0.0
- Preserves existing non-zero values
- Use when sensor data is incomplete

**Example**:
```bash
# Override all tank levels
python integrated_pipeline_defsplit_v2_gate270_split_v3_auditpatched_autodetect_TIDE_v1.py \
  --site AGI \
  --current_t_csv "sensors/current_t.csv" \
  --current_t_strategy override

# Fill only missing values
python integrated_pipeline_defsplit_v2_gate270_split_v3_auditpatched_autodetect_TIDE_v1.py \
  --site AGI \
  --current_t_csv "sensors/current_t.csv" \
  --current_t_strategy fill_missing
```

**Output**:
- `diff_audit.csv`: Injection history (before/after values, clamping status)

**Notes**:
- `override` is recommended for most cases
- `fill_missing` useful when sensor data is partial
- Values are clamped to Min_t/Max_t range

---

## 8. File Path Options

### 8.1 `--base_dir`

**Type**: String (directory path)
**Default**: `""` (script directory)
**Required**: No

**Description**:
Base directory containing pipeline scripts. Used for script path resolution.

**Usage**:
```bash
--base_dir "C:\AGI RORO TR"
--base_dir "/path/to/project"
```

**Default Behavior**:
- If not specified, uses directory containing the pipeline script
- Scripts are auto-detected relative to base_dir

**Example**:
```bash
python integrated_pipeline_defsplit_v2_gate270_split_v3_auditpatched_autodetect_TIDE_v1.py \
  --base_dir "C:\AGI RORO TR\01_EXECUTION_FILES"
```

**Notes**:
- Use when running from different directory
- Scripts are resolved relative to base_dir

---

### 8.2 `--inputs_dir`

**Type**: String (directory path)
**Default**: `""` (same as base_dir)
**Required**: No

**Description**:
Directory containing input files (JSON, CSV, profiles). Overrides default input location.

**Usage**:
```bash
--inputs_dir "02_RAW_DATA"
--inputs_dir "C:\AGI RORO TR\01_EXECUTION_FILES\bplus_inputs"
```

**Search Order** (for input files):
1. `inputs_dir/bplus_inputs/`
2. `base_dir/bplus_inputs/`
3. `02_RAW_DATA/` (fallback)

**Example**:
```bash
python integrated_pipeline_defsplit_v2_gate270_split_v3_auditpatched_autodetect_TIDE_v1.py \
  --site AGI \
  --inputs_dir "02_RAW_DATA"
```

**Notes**:
- Defaults to base_dir if not specified
- Used for profile, hydro table, and other input file resolution

---

### 8.3 `--out_dir`

**Type**: String (directory path)
**Default**: `""` (base_dir/pipeline_out_<timestamp>)
**Required**: No

**Description**:
Output directory for pipeline results. If not specified, creates timestamped directory.

**Usage**:
```bash
--out_dir "outputs/my_run"
--out_dir "C:\Results\Pipeline_20251230"
```

**Default Behavior**:
- Creates `pipeline_out_<timestamp>/` in base_dir
- Format: `pipeline_out_YYYYMMDD_HHMMSS/`

**Example**:
```bash
python integrated_pipeline_defsplit_v2_gate270_split_v3_auditpatched_autodetect_TIDE_v1.py \
  --site AGI \
  --out_dir "outputs/custom_run"
```

**Output Structure**:
```
out_dir/
├── ssot/
├── logs/
├── gate_fail_report.md
├── OPS_FINAL_R3_AGI_Ballast_Integrated.xlsx
└── ...
```

**Notes**:
- Directory is created if it doesn't exist
- Use for organizing multiple runs
- Timestamp format: `YYYYMMDD_HHMMSS`

---

## 9. Advanced Features Options

### 9.1 `--enable-headers-ssot`

**Type**: Flag (boolean)
**Default**: `False`
**Required**: No

**Description**:
Enables headers SSOT (Single Source of Truth) for all outputs. Ensures consistent column headers across all CSV/Excel files.

**Usage**:
```bash
--enable-headers-ssot
```

**Requirements**:
- `--headers-registry` must be provided
- `HEADERS_MASTER.xlsx` or `headers_registry.json` must exist

**Example**:
```bash
python integrated_pipeline_defsplit_v2_gate270_split_v3_auditpatched_autodetect_TIDE_v1.py \
  --site AGI \
  --headers-registry "headers_registry.json" \
  --enable-headers-ssot
```

**Benefits**:
- Consistent headers across all outputs
- Automatic header validation
- Reduced errors from header mismatches

**Notes**:
- Requires headers registry file
- Auto-compiles from `HEADERS_MASTER.xlsx` if needed

---

### 9.2 `--headers-registry`

**Type**: String (file path)
**Default**: `""` (auto-detected)
**Required**: No (required if `--enable-headers-ssot` is used)

**Description**:
Path to headers registry JSON file. Contains SSOT header definitions.

**Usage**:
```bash
--headers-registry "headers_registry.json"
--headers-registry "01_EXECUTION_FILES/ssot/headers_registry.json"
```

**Auto-Compilation**:
- If `HEADERS_MASTER.xlsx` exists, automatically compiles to JSON
- Uses `compile_headers_registry.py` internally

**Example**:
```bash
python integrated_pipeline_defsplit_v2_gate270_split_v3_auditpatched_autodetect_TIDE_v1.py \
  --site AGI \
  --headers-registry "headers_registry.json" \
  --enable-headers-ssot
```

**Notes**:
- Required when using `--enable-headers-ssot`
- Auto-compilation available from Excel master

---

### 9.3 `--head-registry`

**Type**: String (file path)
**Default**: `""`
**Required**: No

**Description**:
Path to HEAD_REGISTRY YAML file for header validation (optional).

**Usage**:
```bash
--head-registry "HEAD_REGISTRY_AGI_v3.0.yaml"
```

**Example**:
```bash
python integrated_pipeline_defsplit_v2_gate270_split_v3_auditpatched_autodetect_TIDE_v1.py \
  --site AGI \
  --head-registry "01_EXECUTION_FILES/HEAD_REGISTRY_AGI_v3.0.yaml"
```

**Notes**:
- Optional header validation
- Different from `--headers-registry` (JSON format)

---

### 9.4 `--auto-head-guard`

**Type**: Flag (boolean)
**Default**: `False`
**Required**: No

**Description**:
Enables automatic Head Guard validation. Validates output file headers against registry.

**Usage**:
```bash
--auto-head-guard
```

**Example**:
```bash
python integrated_pipeline_defsplit_v2_gate270_split_v3_auditpatched_autodetect_TIDE_v1.py \
  --site AGI \
  --auto-head-guard
```

**Notes**:
- Automatic header validation
- Requires head registry configuration

---

## 9.5 Wave and Freeboard Options

### 9.5.1 `--hmax_wave_m`

**Type**: Float (meters)
**Default**: `None`
**Required**: No

**Description**:
Maximum wave height (m) for GL Noble Denton 0013/ND effective freeboard check.

**Usage**:
```bash
--hmax_wave_m 2.0
--hmax_wave_m 0.30
```

**Calculation**:
- With 4-corner monitoring: `Freeboard_Req = 0.50 + 0.50*Hmax`
- Without monitoring: `Freeboard_Req = 0.80 + 0.50*Hmax`

**Application**:
- Required for GL Noble Denton 0013/ND freeboard gate
- Used with `--four_corner_monitoring` to determine freeboard requirement
- Gate-FB: MWS load-out effective freeboard verification

**Example**:
```bash
python integrated_pipeline_defsplit_v2_gate270_split_v3_auditpatched_autodetect_TIDE_v1.py \
  --site AGI \
  --hmax_wave_m 2.0 \
  --four_corner_monitoring
```

**Notes**:
- Value in meters
- Required for ND freeboard gate (Gate-FB)
- Use with `--four_corner_monitoring` to reduce requirement

---

### 9.5.2 `--four_corner_monitoring`

**Type**: Flag (boolean)
**Default**: `False`
**Required**: No

**Description**:
Enable 4-corner freeboard monitoring. Reduces GL Noble Denton freeboard requirement.

**Usage**:
```bash
--four_corner_monitoring
```

**Effect**:
- With monitoring: `Freeboard_Req = 0.50 + 0.50*Hmax`
- Without monitoring: `Freeboard_Req = 0.80 + 0.50*Hmax`
- Reduces requirement by 0.30m

**Example**:
```bash
python integrated_pipeline_defsplit_v2_gate270_split_v3_auditpatched_autodetect_TIDE_v1.py \
  --site AGI \
  --hmax_wave_m 2.0 \
  --four_corner_monitoring
```

**Notes**:
- Requires `--hmax_wave_m` to be set
- Reduces ND freeboard requirement by 0.30m
- Operational requirement: Must implement 4-corner monitoring if flag is set

---

## 9.6 Tank Operability Options

### 9.6.1 `--tank_operability_json`

**Type**: String (file path)
**Default**: `""`
**Required**: No

**Description**:
Tank operability/profile JSON file for PRE_BALLAST_ONLY enforcement. Contains tank operability metadata.

**Usage**:
```bash
--tank_operability_json "bplus_inputs/profiles/AGI.json"
```

**Application**:
- Used for PRE_BALLAST_ONLY tank mode enforcement
- Applies stage-specific tank constraints
- Works with `--operational_stage_regex` to determine operational stages

**Example**:
```bash
python integrated_pipeline_defsplit_v2_gate270_split_v3_auditpatched_autodetect_TIDE_v1.py \
  --site AGI \
  --tank_operability_json "bplus_inputs/profiles/AGI.json" \
  --operational_stage_regex "(6a|critical|ramp|roll|loadout)"
```

**Notes**:
- Can use same file as `--profile_json`
- Contains `tank_operability` section in profile JSON
- Used for stage-specific tank mode enforcement

---

### 9.6.2 `--operational_stage_regex`

**Type**: String (regex pattern)
**Default**: `"(6a|critical|ramp|roll|loadout)"`
**Required**: No

**Description**:
Regex pattern to identify operational stages for PRE_BALLAST_ONLY enforcement.

**Usage**:
```bash
--operational_stage_regex "(6a|critical|ramp|roll|loadout)"
--operational_stage_regex "(stage.*6a|critical)"
```

**Application**:
- Used to determine which stages are "operational"
- PRE_BALLAST_ONLY tanks are disabled on operational stages (unless `--disable_preballast_only_on_operational_stages` is set)
- Default matches: Stage 6A_Critical, ramp, roll, loadout stages

**Example**:
```bash
python integrated_pipeline_defsplit_v2_gate270_split_v3_auditpatched_autodetect_TIDE_v1.py \
  --site AGI \
  --tank_operability_json "bplus_inputs/profiles/AGI.json" \
  --operational_stage_regex "(6a|critical|ramp|roll|loadout)"
```

**Notes**:
- Case-insensitive matching
- Default pattern covers most operational stages
- Customize based on stage naming convention

---

### 9.6.3 `--disable_preballast_only_on_operational_stages`

**Type**: Flag (boolean)
**Default**: `False`
**Required**: No

**Description**:
Disable PRE_BALLAST_ONLY enforcement on operational stages. Allows PRE_BALLAST_ONLY tanks to be used during operational stages.

**Usage**:
```bash
--disable_preballast_only_on_operational_stages
```

**Behavior**:
- Default: PRE_BALLAST_ONLY tanks are disabled on operational stages
- With flag: PRE_BALLAST_ONLY tanks can be used on operational stages
- Use when operational stages need access to PRE_BALLAST_ONLY tanks

**Example**:
```bash
python integrated_pipeline_defsplit_v2_gate270_split_v3_auditpatched_autodetect_TIDE_v1.py \
  --site AGI \
  --tank_operability_json "bplus_inputs/profiles/AGI.json" \
  --operational_stage_regex "(6a|critical)" \
  --disable_preballast_only_on_operational_stages
```

**Notes**:
- Requires `--tank_operability_json`
- Overrides default PRE_BALLAST_ONLY behavior
- Use with caution (verify operational safety)

---

### 9.6.4 `--exclude_fwd_tanks`

**Type**: Flag (boolean)
**Default**: `False`
**Required**: No

**Description**:
Exclude FWD tanks (x_from_mid_m < 0) from solver by setting use_flag=N after profile overrides.

**Usage**:
```bash
--exclude_fwd_tanks
```

**Application**:
- Global exclusion: Sets `use_flag=N` for all FWD tanks (x_from_mid_m < 0)
- Applied after profile overrides
- Use when FWD tanks should not be used in any stage

**Example**:
```bash
python integrated_pipeline_defsplit_v2_gate270_split_v3_auditpatched_autodetect_TIDE_v1.py \
  --site AGI \
  --exclude_fwd_tanks
```

**Notes**:
- Global exclusion (all stages)
- Applied after profile overrides
- Use `--exclude_fwd_tanks_aftmin_only` for stage-specific exclusion

---

### 9.6.5 `--exclude_fwd_tanks_aftmin_only`

**Type**: Flag (boolean)
**Default**: `False`
**Required**: No

**Description**:
For AFT-min violating stages, set FWD tanks to DISCHARGE_ONLY (fill prohibited, discharge allowed).

**Usage**:
```bash
--exclude_fwd_tanks_aftmin_only
```

**Application**:
- Stage-specific: Only applies to stages violating AFT_MIN
- Sets FWD tanks to DISCHARGE_ONLY mode (fill prohibited, discharge allowed)
- Uses stage flag `Ban_FWD_Tanks=True` for per-stage handling
- Prevents using FWD tanks to raise AFT draft (physical constraint)

**Example**:
```bash
python integrated_pipeline_defsplit_v2_gate270_split_v3_auditpatched_autodetect_TIDE_v1.py \
  --site AGI \
  --exclude_fwd_tanks_aftmin_only
```

**Notes**:
- Stage-specific (AFT-min violating stages only)
- Sets FWD tanks to DISCHARGE_ONLY (not BLOCKED)
- Prevents incorrect use of FWD tanks for AFT draft correction
- Recommended for AFT ballast optimization scenarios

---

## 9.7 Data Conversion Options

### 9.7.1 `--pump_rate`

**Type**: Float (tonnes per hour)
**Default**: `100.0`
**Required**: No

**Description**:
Default pump rate (t/h) used when generating solver tank CSV. Used for pump time calculations.

**Usage**:
```bash
--pump_rate 100.0   # Hired/shore pump (default)
--pump_rate 10.0    # Ship pump
```

**Application**:
- Used in `tank_ssot_for_solver.csv` generation
- Default pump rate for tanks (unless overridden by profile)
- Used for PumpTime_h calculations in ballast sequence

**Example**:
```bash
python integrated_pipeline_defsplit_v2_gate270_split_v3_auditpatched_autodetect_TIDE_v1.py \
  --site AGI \
  --pump_rate 100.0
```

**Notes**:
- Value in tonnes per hour (t/h)
- Default: 100.0 t/h (hired/shore pump nominal)
- Ship pump: 10.0 t/h (from AGENTS.md SSOT)
- Can be overridden per-tank in profile JSON

---

### 9.7.2 `--tank_keywords`

**Type**: String (comma-separated keywords)
**Default**: `"BALLAST,VOID,FWB,FW,DB"`
**Required**: No

**Description**:
Comma-separated keywords to mark `use_flag=Y` in tank conversion. Tanks matching these keywords are marked as usable.

**Usage**:
```bash
--tank_keywords "BALLAST,VOID,FWB,FW,DB"
--tank_keywords "BALLAST,VOID"
```

**Application**:
- Used in `convert_tank_catalog_json_to_solver_csv()`
- Tanks with names containing keywords are set to `use_flag=Y`
- Default keywords cover standard ballast/void tanks

**Example**:
```bash
python integrated_pipeline_defsplit_v2_gate270_split_v3_auditpatched_autodetect_TIDE_v1.py \
  --site AGI \
  --tank_keywords "BALLAST,VOID,FWB,FW,DB"
```

**Notes**:
- Comma-separated keywords (no spaces after commas)
- Case-insensitive matching
- Default: "BALLAST,VOID,FWB,FW,DB" (covers standard ballast tanks)
- Customize based on tank naming convention

---

## 10. Debug and Reporting Options

### 10.1 `--no_gate_report`

**Type**: Flag (boolean)
**Default**: `False` (report generated)
**Required**: No

**Description**:
Disables automatic Gate FAIL report generation. By default, pipeline generates `gate_fail_report.md`.

**Usage**:
```bash
--no_gate_report
```

**Default Behavior**:
- Gate FAIL report is generated automatically
- Contains gate violation summary, heuristics, recommendations

**Example**:
```bash
# Disable gate report generation
python integrated_pipeline_defsplit_v2_gate270_split_v3_auditpatched_autodetect_TIDE_v1.py \
  --site AGI \
  --no_gate_report
```

**Notes**:
- Use when gate report is not needed
- Report generation is fast, so usually not necessary to disable

---

### 10.2 `--debug_report`

**Type**: Flag (boolean)
**Default**: `False`
**Required**: No

**Description**:
Generates debug feasibility report after QA CSV generation. Provides detailed diagnostics.

**Usage**:
```bash
--debug_report
```

**Additional Outputs**:
- `debug_feasibility_pipeline.md`: Debug report
- `debug_stage_flags.csv`: Stage-wise flags
- Enhanced logging

**Example**:
```bash
python integrated_pipeline_defsplit_v2_gate270_split_v3_auditpatched_autodetect_TIDE_v1.py \
  --site AGI \
  --debug_report
```

**Use Cases**:
- Troubleshooting gate failures
- Understanding solver behavior
- Detailed stage analysis

**Notes**:
- Generates additional diagnostic files
- Useful for troubleshooting

---

### 10.3 `--auto_debug_report`

**Type**: Flag (boolean)
**Default**: `False`
**Required**: No

**Description**:
Automatically generates debug report (alternative to `--debug_report`).

**Usage**:
```bash
--auto_debug_report
```

**Example**:
```bash
python integrated_pipeline_defsplit_v2_gate270_split_v3_auditpatched_autodetect_TIDE_v1.py \
  --site AGI \
  --auto_debug_report
```

**Notes**:
- Similar to `--debug_report`
- May have different trigger conditions

---

## 11. Script Path Override Options

These options allow you to override default script paths if scripts are located in non-standard locations.

### 11.1 `--tr_script`

**Type**: String (file path)
**Default**: `"agi_tr_patched_v6_6_defsplit_v1.py"`
**Required**: No

**Description**:
Path to TR Excel generation script (Step 1, Step 1b).

**Usage**:
```bash
--tr_script "custom_path/tr_script.py"
```

---

### 11.2 `--ops_script`

**Type**: String (file path)
**Default**: `"ops_final_r3_integrated_defs_split_v4_patched_TIDE_v1.py"`
**Required**: No

**Description**:
Path to OPS Integrated Report script (Step 2).

**Usage**:
```bash
--ops_script "custom_path/ops_script.py"
```

---

### 11.3 `--solver_script`

**Type**: String (file path)
**Default**: `"ballast_gate_solver_v4_TIDE_v1.py"`
**Required**: No

**Description**:
Path to Ballast Gate Solver script (Step 3).

**Usage**:
```bash
--solver_script "tide/ballast_gate_solver_v4_TIDE_v1.py"
```

---

### 11.4 `--optimizer_script`

**Type**: String (file path)
**Default**: `"Untitled-2_patched_defsplit_v1_1.py"`
**Required**: No

**Description**:
Path to Ballast Optimizer script (Step 4).

**Usage**:
```bash
--optimizer_script "custom_path/optimizer.py"
```

---

### 11.5 `--spmt_script`

**Type**: String (file path)
**Default**: `"spmt v1/agi_spmt_unified.py"`
**Required**: No

**Description**:
Path to SPMT unified script (Step 0, optional).

**Usage**:
```bash
--spmt_script "spmt/agi_spmt_unified.py"
```

---

### 11.6 `--bryan_template_script`

**Type**: String (file path)
**Default**: `"tide/bryan_template_unified_TIDE_v1.py"`
**Required**: No

**Description**:
Path to Bryan Template unified script (Step 5).

**Usage**:
```bash
--bryan_template_script "tide/bryan_template.py"
```

---

### 11.7 `--spmt_config`

**Type**: String (file path)
**Default**: `"spmt v1/spmt_shuttle_example_config_AGI_FR_M.json"` (auto-detected)
**Required**: No

**Description**:
Path to SPMT configuration JSON file. Required for Step 0 (SPMT cargo input generation).

**Usage**:
```bash
--spmt_config "spmt v1/spmt_shuttle_example_config_AGI_FR_M.json"
--spmt_config "custom_spmt_config.json"
```

**Requirements**:
- SPMT script (`agi_spmt_unified.py`) must be available
- `agi_ssot.py` module must be in the same directory as `agi_spmt_unified.py`

**Example**:
```bash
python integrated_pipeline_defsplit_v2_gate270_split_v3_auditpatched_autodetect_TIDE_v1.py \
  --site AGI \
  --from_step 0 \
  --spmt_config "spmt v1/spmt_shuttle_example_config_AGI_FR_M.json"
```

**Notes**:
- If `agi_ssot.py` is missing, copy it from `01_EXECUTION_FILES/spmt v1/agi_ssot.py` to `spmt v1/agi_ssot.py`
- Auto-detected if file exists in default location

---

## 12. Option Combinations and Examples

### 12.1 Basic Run (Minimum Options)

```bash
python integrated_pipeline_defsplit_v2_gate270_split_v3_auditpatched_autodetect_TIDE_v1.py --site AGI
```

**What it does**:
- Uses default AGI profile
- Auto-detects all input files
- Runs all steps (1b → 2 → 3)
- Generates standard outputs

---

### 12.2 Complete Run with All Features

```bash
python integrated_pipeline_defsplit_v2_gate270_split_v3_auditpatched_autodetect_TIDE_v1.py \
  --site AGI \
  --from_step 0 \
  --to_step 5 \
  --fwd_max 2.70 \
  --aft_min 2.70 \
  --forecast_tide 1.5 \
  --depth_ref 10.0 \
  --ukc_min 2.0 \
  --squat 0.15 \
  --safety_allow 0.20 \
  --tide_tol 0.10 \
  --hmax_wave_m 2.0 \
  --four_corner_monitoring \
  --gate_guard_band_cm 2.0 \
  --current_t_csv "sensors/current_t.csv" \
  --current_t_strategy override \
  --spmt_config "spmt v1/spmt_shuttle_example_config_AGI_FR_M.json" \
  --enable-sequence \
  --enable-valve-lineup \
  --stateful_solver \
  --state_trace_csv "solver_state_trace.csv" \
  --tank_operability_json "bplus_inputs/profiles/AGI.json" \
  --operational_stage_regex "(6a|critical|ramp|roll|loadout)" \
  --exclude_fwd_tanks_aftmin_only \
  --pump_rate 100.0 \
  --tank_keywords "BALLAST,VOID,FWB,FW,DB" \
  --debug_report
```

**Outputs**:
- All standard outputs
- SPMT cargo input files (`AGI_SPMT_Shuttle_Output.xlsx`, `spmt_output/`)
- Ballast sequence files
- Valve lineup
- Debug reports
- Stateful solver trace (`solver_state_trace.csv`)

---

### 12.3 Quick Gate Check (No Optimization)

```bash
python integrated_pipeline_defsplit_v2_gate270_split_v3_auditpatched_autodetect_TIDE_v1.py \
  --site AGI \
  --from_step 1 \
  --to_step 2
```

**Outputs**:
- `gate_fail_report.md` only
- No solver/optimizer runs

---

### 12.4 Solver Only (Re-run with Updated Data)

```bash
python integrated_pipeline_defsplit_v2_gate270_split_v3_auditpatched_autodetect_TIDE_v1.py \
  --site AGI \
  --from_step 3 \
  --to_step 3 \
  --current_t_csv "sensors/updated_current_t.csv" \
  --current_t_strategy override
```

**Prerequisites**:
- `stage_results.csv` must exist
- SSOT CSV files from previous run

---

### 12.5 Custom Profile and Paths

```bash
python integrated_pipeline_defsplit_v2_gate270_split_v3_auditpatched_autodetect_TIDE_v1.py \
  --site AGI \
  --profile_json "custom_profiles/my_profile.json" \
  --base_dir "C:\AGI RORO TR\01_EXECUTION_FILES" \
  --inputs_dir "C:\AGI RORO TR\02_RAW_DATA" \
  --out_dir "outputs/custom_run_20251230"
```

---

### 12.6 UKC Analysis with Custom Values

```bash
python integrated_pipeline_defsplit_v2_gate270_split_v3_auditpatched_autodetect_TIDE_v1.py \
  --site AGI \
  --forecast_tide 2.0 \
  --depth_ref 12.5 \
  --ukc_min 2.5 \
  --squat 0.2 \
  --safety_allow 0.3
```

---

## Appendix A: Option Quick Reference

### Site & Profile
- `--site AGI|DAS`
- `--profile_json <path>`

### Step Control
- `--from_step <0-5>`
- `--to_step <0-5>`
- `--enable-sequence`
- `--enable-valve-lineup`

### Gates
- `--fwd_max <m>`
- `--aft_min <m>`
- `--aft_max <m>`
- `--trim_abs_limit <m>`
- `--trim_limit_enforced` / `--no-trim-limit-enforced`
- `--freeboard_min_m <m>`
- `--freeboard_min_enforced` / `--no-freeboard-min-enforced`
- `--gate_guard_band_cm <cm>`

### Tide & UKC
- `--forecast_tide <m>`
- `--depth_ref <m>`
- `--ukc_min <m>`
- `--squat <m>`
- `--safety_allow <m>`
- `--tide_tol <m>`
- `--tide_table <path>`
- `--stage_schedule <path>`
- `--stage_tide_csv <path>`
- `--tide_strategy keep_csv|override_from_table`

### Wave and Freeboard
- `--hmax_wave_m <m>`
- `--four_corner_monitoring`

### Sensor Data
- `--current_t_csv <path>`
- `--current_t_strategy override|fill_missing`

### File Paths
- `--base_dir <path>`
- `--inputs_dir <path>`
- `--out_dir <path>`

### Debug & Reporting
- `--no_gate_report`
- `--debug_report`
- `--auto_debug_report`

### Advanced
- `--enable-headers-ssot`
- `--headers-registry <path>`
- `--head-registry <path>`
- `--auto-head-guard`

### Tank Operability
- `--tank_operability_json <path>`
- `--operational_stage_regex <regex>`
- `--disable_preballast_only_on_operational_stages`
- `--exclude_fwd_tanks`
- `--exclude_fwd_tanks_aftmin_only`

### Data Conversion
- `--pump_rate <t/h>`
- `--tank_keywords <keywords>`

### Stateful Solver
- `--stateful_solver` / `--stateful`
- `--reset_tank_state <list|regex>`
- `--state_trace_csv <path>`

---

## Appendix B: Draft Clipping Safety Warning

### ⚠️ Critical Safety Warning - Draft Clipping

**When Draft Exceeds D_vessel (3.65m)**:

The pipeline automatically clips draft values that exceed `D_vessel` (3.65m, molded depth) to prevent impossible values. However, this masking requires careful interpretation.

**Example (Stage 6C)**:
- **Input**: `Draft_FWD_m = 3.80m`, `Draft_AFT_m = 3.80m` (exceeds D_vessel = 3.65m)
- **Clipped**: `Draft_FWD_m = 3.65m`, `Draft_AFT_m = 3.65m`
- **Result**: `Freeboard_Min_m = 0.00m` (deck edge at waterline)

**⚠️ Critical Safety Warning**:

1. **Clipping Masks Input Validity Issues**:
   - Input draft 3.80m exceeding D_vessel indicates potential:
     - TR position error
     - Calculation error
     - Structural concern

2. **Freeboard = 0.00m Risk**:
   - Deck edge at waterline → green water risk
   - Structural stress at deck edge
   - Requires engineering verification

3. **Required Actions**:
   - **If Input Invalid**: FAIL - Correct TR position or calculation
   - **If Input Valid**: VERIFY - Requires engineering approval:
     - Class acceptance documentation
     - Load-line compliance verification
     - Structural analysis approval

**Pipeline Log Warning**:
```
[WARNING] Draft values clipped to D_vessel (3.65m) for 1 stages:
  - Stage 6C: FWD 3.80 -> 3.65m, AFT 3.80 -> 3.65m
  ⚠️ PHYSICAL LIMIT EXCEEDED: Freeboard = 0.00m
  → Requires engineering verification (class acceptance, load-line compliance)
```

**Documentation Requirement**:
- Approval packages must explicitly state when draft clipping occurred
- Engineering justification required for freeboard = 0.00m conditions
- Load-line class acceptance documentation required if clipping applied

---

**End of Options Reference Guide**

For additional information, refer to:
- `Ballast Pipeline - Complete User Guide for First-Time Users.md`
- `Pipeline Complete Architecture and Execution Files Logic Detailed.md`
```
