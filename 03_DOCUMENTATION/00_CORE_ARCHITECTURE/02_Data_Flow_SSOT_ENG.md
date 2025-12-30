

**Latest Update (v3.7 - 2025-12-29):**

- Added pipeline execution file → output file → header structure mapping
- Specified relationship between Excel/CSV files created by each Step and headers
- Details: See section 8 of `00_System_Architecture_Complete.md`

**Latest Update (v3.6 - 2025-12-29):**

- Forecast_Tide_m priority change: CLI `--forecast_tide` value takes highest priority
  - Ensures complete alignment of `Forecast_Tide_m` between `stage_table_unified.csv` and `solver_ballast_summary.csv`
  - SSOT rule update: CLI value → stage_tide_csv → tide_table order
  - Details: See section 17.6.5 of `17_TIDE_UKC_Calculation_Logic.md`

**Latest Update (v3.5 - 2025-12-28):**

- Option 2 implementation: BALLAST_SEQUENCE option/execution separation
  - `BALLAST_OPTION.csv`: Planning level (Delta_t centered, includes all Stages)
  - `BALLAST_EXEC.csv`: Execution sequence (Start_t/Target_t carry-forward, Stage 6B excluded)
  - Start_t/Target_t chain: Previous step's Target_t → Next Start_t automatically passed
  - Stage 6B separation: Excluded from execution sequence via OPTIONAL_STAGES constant
- Option 1 patch proposal (not implemented)
  - Bryan Pack Forecast_tide_m injection (merge with pipeline_stage_QA.csv)
  - Stage 5_PreBallast GateB critical enforcement (AGI rule)
  - Current_* vs Draft_* unification (QA table)

**Latest Update (v3.4 - 2025-12-28):**

- I/O Optimization (PR-01~05): Parquet cache, Manifest logging, Fast CSV reading
  - Parquet sidecar cache: stage_results.parquet auto-generated (right after Step 1b)
  - read_table_any() unified API: Parquet priority load, CSV fallback
  - Manifest logging: All I/O operations automatically tracked (manifests/<run_id>/`<step>`_`<pid>`.jsonl)
  - Fast CSV: Polars lazy scan priority, pandas fallback (pyarrow → c → python)
- SSOT CSV reading: Use read_table_any() at all points (OPS, StageExcel, Orchestrator)

**Latest Update (v3.3 - 2025-12-27):**

- Tide Integration (AGI-only): stage_tide_AGI.csv, Forecast_tide_m, Tide_required_m, Tide_margin_m
- Stage Table expansion: Added DatumOffset_m, Forecast_Tide_m, Tide_Source, Tide_QC columns
- QA CSV expansion: Tide alias columns (Forecast_tide_m, Tide_required_m, UKC_min_m, UKC_fwd_m, UKC_aft_m)
- SPMT Integration: Added SPMT cargo data flow

**Latest Update (v3.2 - 2025-12-27):**

- AGENTS.md SSOT integration (coordinate system conversion formula, Tank Direction SSOT)
- Coordinate system conversion formula clarification (x = 30.151 - Fr, no reinterpretation)
- Tank Direction SSOT addition (FWD/AFT Zone classification, Golden Rule)

**Latest Update (v3.1 - 2025-12-27):**

- Current_t auto-discovery feature (automatic detection of current_t_*.csv pattern)
- diff_audit.csv generation (sensor injection history record)
- GM verification and FSM integration (CLAMP detection, FSM verification, GM_eff calculation)

**Latest Update (v2.2 - 2024-12-23):**

- Excel/CSV consistency patch (2024-12-23)
- Read `stage_results.csv` SSOT when generating Excel
- Detailed Draft clipping logic explanation

---

## 2.1 SSOT (Single Source of Truth) Concept

### 2.1.1 Need for SSOT

The Ballast Pipeline consists of **4 independent Python scripts**. Each script may require different data formats and structures, which can cause the following problems:

- **Data inconsistency**: Each script interprets the same tank information differently
- **Coordinate system confusion**: Differences in LCG representation (AP reference vs Midship reference)
- **Version management difficulty**: Multiple scripts modifying the same source data differently
- **Debugging complexity**: Difficult error tracking due to intermediate data format inconsistencies

The SSOT architecture solves these problems by **defining source data in JSON only once**, and the pipeline **converts to standardized CSV format** as needed.

### 2.1.2 SSOT Data Flow

**Input data sources (`bplus_inputs/` folder)**:

- `Hydro_Table_Engineering.json`: Hydrostatic table (Step 1, 2, 3)
- `profiles/AGI.json`: Site profile (Step 2, 3)
- `data/Frame_x_from_mid_m.json`: Frame ↔ x conversion (Step 1)
- `stage_schedule.csv`: Stage-wise timestamps (Tide Integration, optional)
- `water tide_202512.xlsx`: Tide data (Tide Integration, optional)
- `tide_windows_AGI.json`: Stage-wise tide window definitions (Tide Integration, optional)

**Search order**:

1. `inputs_dir/bplus_inputs/` (or `base_dir/bplus_inputs/`)
2. `02_RAW_DATA/` (fallback)

**Note**: Details: See section 2.12 of `파이프라인 전체 아키텍처, 실행 파일, 로직 상세 설명.MD`.

```
┌─────────────────────────────────────────────────────────┐
│          SOURCE DATA (JSON - Single Source)             │
├─────────────────────────────────────────────────────────┤
│  tank_catalog_from_tankmd.json                         │
│    └─> {"tanks": [{"id": "FWB2", "lcg_m": 25.0, ...}]} │
│                                                         │
│  Hydro_Table_Engineering.json                          │
│    └─> [{"Tmean_m": 2.0, "TPC_t_per_cm": 8.0, ...}]   │
│                                                         │
│  stage_results.csv (from Step 1)                        │
│    └─> Stage, Dfwd_m, Daft_m, ...                       │
└──────────────────────┬──────────────────────────────────┘
                       │
                       │ Pipeline Conversion Functions
                       ▼
┌─────────────────────────────────────────────────────────┐
│        SSOT CSV (Standardized - Multiple Consumers)     │
├─────────────────────────────────────────────────────────┤
│  ssot/tank_ssot_for_solver.csv                         │
│    └─> Tank, x_from_mid_m, Current_t, Min_t, Max_t... │
│                                                         │
│  ssot/hydro_table_for_solver.csv                       │
│    └─> Tmean_m, TPC_t_per_cm, MTC_t_m_per_cm, ...     │
│                                                         │
│  ssot/stage_table_unified.csv                          │
│    └─> Stage, Current_FWD_m, Current_AFT_m, Gates...  │
│         Forecast_Tide_m, DatumOffset_m (AGI-only)      │
│                                                         │
│  ssot/pipeline_stage_QA.csv                            │
│    └─> Definition-split validation & Gate status      │
│         Forecast_tide_m, Tide_required_m, Tide_margin_m│
│         UKC_min_m, UKC_fwd_m, UKC_aft_m, Tide_verdict  │
│         Draft_FWD_m, Draft_AFT_m (SSOT, Current_* removal recommended) │
│                                                         │
│  BALLAST_OPTION.csv (Option 2, planning level)        │
│    └─> Stage, Tank, Action, Delta_t, PumpRate_tph, Priority, Rationale │
│                                                         │
│  BALLAST_EXEC.csv (Option 2, execution sequence)      │
│    └─> Stage, Step, Tank, Start_t, Target_t, Delta_t, Time_h, Hold_Point │
│         (Start_t/Target_t carry-forward, Stage 6B excluded) │
│                                                         │
│  BALLAST_SEQUENCE.csv (Legacy, compatibility)          │
│    └─> Legacy format (parallel with Option 2)          │
│                                                         │
│  stage_tide_AGI.csv (AGI-only, Pre-Step)                │
│    └─> StageKey, Forecast_tide_m, tide_src, tide_qc    │
│                                                         │
│  stage_results.parquet (PR-04, Parquet cache)          │
│    └─> Parquet sidecar cache (mtime validation)        │
│                                                         │
│  manifests/<run_id>/<step>_<pid>.jsonl (PR-01)         │
│    └─> I/O operation logs (JSONL format)              │
└──────────────────────┬──────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
   Step 2: OPS    Step 3: LP    Step 4: OPT
   Report Gen     Solver        Optimizer
   (read_table_any) (read_table_any) (read_table_any)
```

---

## 2.2 Tank Catalog Conversion

### 2.2.1 Input Format: `tank_catalog_from_tankmd.json`

```json
{
  "source_file": "tank.md",
  "tanks": [
    {
      "id": "FWB2",
      "category": "fresh_water_ballast",
      "lcg_m": 25.0,
      "tcg_m": 0.0,
      "vcg_m": 1.5,
      "cap_t": 50.0,
      "loc": "AFT",
      "fr_start": 40,
      "fr_end": 45
    },
    ...
  ]
}
```

**Important fields:**

- `id`: Tank identifier
- `lcg_m`: LCG (Longitudinal Center of Gravity) from AP (After Perpendicular), unit: m
- `cap_t`: Tank capacity (tons)
- `category`: Tank category (used to check if ballast-related keywords are included)

### 2.2.2 Output Format: `tank_ssot_for_solver.csv`

| Column              | Type   | Description                                    | Example          |
| ------------------- | ------ | ---------------------------------------------- | ---------------- |
| `Tank`            | string | Tank identifier                                | "FWB2"           |
| `Capacity_t`      | float  | Tank capacity (tons)                           | 50.0             |
| `x_from_mid_m`    | float  | X coordinate relative to Midship (+AFT / -FWD) | -5.151           |
| `Current_t`       | float  | Current tank weight (tons)                     | 0.0              |
| `Min_t`           | float  | Minimum allowed weight (tons)                  | 0.0              |
| `Max_t`           | float  | Maximum allowed weight (tons)                  | 50.0             |
| `mode`            | string | Operating mode                                 | "FILL_DISCHARGE" |
| `use_flag`        | string | Usage flag (Y/N)                               | "Y"              |
| `pump_rate_tph`   | float  | Pump rate (tons/hour)                          | 100.0            |
| `priority_weight` | float  | Priority weight (lower = higher priority)      | 1.0              |

### 2.2.3 Coordinate System Conversion (SSOT - AGENTS.md standard, no reinterpretation)

**Frame coordinate system (BUSHRA TCP / tank.md standard)**:

- `Fr.0 = AP (AFT)`: After Perpendicular (stern perpendicular)
- `Frame increase direction = FWD`: Frame increases toward bow
- `Frame 30.151 = Midship → x = 0.0`: Midship reference point

**X coordinate system (for calculation, Midship reference)**:

- `LPP_M = 60.302`: Length between perpendiculars (m)
- `MIDSHIP_FROM_AP_M = 30.151`: Midship position (from AP, m)
- `_FRAME_SLOPE = -1.0`: Frame→x conversion slope
- `_FRAME_OFFSET = 30.151`: Frame→x conversion offset

**Coordinate conversion formula (standard, no reinterpretation)**:

```python
# Constants (from integrated_pipeline_defsplit_v2.py)
LPP_M = 60.302  # m (Length Between Perpendiculars)
MIDSHIP_FROM_AP_M = LPP_M / 2.0  # 30.151 m

# Coordinate transformation (LCG from AP → x from Midship)
lcg_from_ap = tank["lcg_m"]  # LCG from AP (stern)
x_from_mid_m = MIDSHIP_FROM_AP_M - lcg_from_ap

# Frame → x conversion (general)
x = _FRAME_SLOPE * (Fr - _FRAME_OFFSET)
x = 30.151 - Fr
```

**Coordinate system rules:**

- **Input (JSON)**: `lcg_m` is relative to AP (After Perpendicular, stern)
- **Output (CSV)**: `x_from_mid_m` is relative to Midship
  - Positive (+) = AFT (stern direction, `x > 0`)
  - Negative (-) = FWD (bow direction, `x < 0`)

**Examples:**

- Tank LCG at 25.0m from AP → `x_from_mid_m = 30.151 - 25.0 = +5.151m` (AFT)
- Tank LCG at 35.0m from AP → `x_from_mid_m = 30.151 - 35.0 = -4.849m` (FWD)
- Frame 25.0 → `x = 30.151 - 25.0 = +5.151m` (AFT)
- Frame 35.0 → `x = 30.151 - 35.0 = -4.849m` (FWD)

**Golden Rule**: Treating bow tanks (high Fr / high LCG(AP)) as "stern ballast" reverses physical laws and breaks all gates.

### 2.2.4 Tank Direction SSOT (FWD/AFT Classification - No Re-discussion)

**AFT Zone (stern)**:

- `FW2 P/S`: Fr.0-6 (stern fresh water)
- `VOIDDB4 P/S`, `SLUDGE.C`, `SEWAGE.P`: Fr.19-24 (mid-stern)
- Fuel tanks `DO`, `FODB1`, `FOW1`, `LRFO P/S/C`: Fr.22-33 (near Midship)

**MID Zone**:

- `VOID3 P/S`: Fr.33-38

**MID-FWD Zone**:

- `FWCARGO2 P/S`: Fr.38-43
- `FWCARGO1 P/S`: Fr.43-48

**FWD/BOW Zone (bow)**:

- `FWB2 P/S`: Fr.48-53 (bow ballast)
- `VOIDDB1.C`: Fr.48-56
- `FWB1 P/S`: Fr.56-FE (bow ballast)
- `CL P/S`: Fr.56-59 (Chain lockers)

**Practical result**: `FWB1.*` and `FWB2.*` are **bow/bow tanks**. They have `x < 0` in the X coordinate system and **cannot be used as "stern ballast"**. If AFT-up / stern-down moment is needed, **AFT zone tanks** and/or cargo LCG must be moved toward stern.

### 2.2.4 Conversion Function: `convert_tank_catalog_json_to_solver_csv`

**Location:** `integrated_pipeline_defsplit_v2.py` (lines 151-220)

**Key logic:**

1. **JSON parsing and validation**

   ```python
   obj = json.loads(tank_catalog_json.read_text(encoding="utf-8"))
   tanks = obj.get("tanks", [])
   if not isinstance(tanks, list):
       raise ValueError(f"Unexpected tank catalog structure")
   ```
2. **Tank filtering and classification**

   - Default keywords: `["BALLAST", "VOID", "FWB", "FW", "DB"]`
   - Marked with `use_flag = "Y"` for use in LP Solver
   - If no keywords, `use_flag = "N"` (not available)
3. **Priority assignment (Priority Weight)**

   ```python
   if "FWB2" in tid.upper():
       priority_weight = 1.0  # Highest priority (Primary discharge source)
   elif "VOIDDB2" in tid.upper():
       priority_weight = 2.0  # Second priority
   elif "VOIDDB1" in tid.upper():
       priority_weight = 3.0  # Third priority
   else:
       priority_weight = 5.0  # Default
   ```

   - Lower value = higher priority (used as weight in LP objective function)
4. **CSV output**

   - UTF-8 with BOM (`encoding="utf-8-sig"`) for Excel compatibility
   - All numeric values rounded to appropriate precision

---

## 2.3 Hydrostatic Table Conversion

### 2.3.1 Input Format: `Hydro_Table_Engineering.json`

JSON structure is handled flexibly:

- List format: `[{...}, {...}]`
- Dictionary with "rows": `{"rows": [{...}, {...}]}`
- Single dictionary: `{...}` (attempt direct DataFrame conversion)

**Required columns:**

- `Tmean_m`: Mean draft (m)
- `TPC_t_per_cm`: Tons Per Centimeter (weight change per 1cm draft)
- `MTC_t_m_per_cm`: Moment to Change Trim (moment per 1cm trim)
- `LCF_m` or `LCF_m_from_midship`: Longitudinal Center of Flotation (m)
- `LBP_m`: Length Between Perpendiculars (m) - use default if missing

### 2.3.2 Output Format: `hydro_table_for_solver.csv`

| Column             | Type  | Description                       | Example |
| ------------------ | ----- | --------------------------------- | ------- |
| `Tmean_m`        | float | Mean draft (m)                    | 2.50    |
| `TPC_t_per_cm`   | float | Tons Per Centimeter               | 8.00    |
| `MTC_t_m_per_cm` | float | Moment to Change Trim (t·m/cm)   | 34.00   |
| `LCF_m`          | float | LCF from Midship (m, +AFT/-FWD)   | 0.76    |
| `LBP_m`          | float | Length Between Perpendiculars (m) | 60.302  |

**Sorting:** Ascending by `Tmean_m` (required for interpolation)

### 2.3.3 Conversion Function: `convert_hydro_engineering_json_to_solver_csv`

**Location:** `integrated_pipeline_defsplit_v2.py` (lines 223-263)

**Key logic:**

1. **Flexible JSON parsing**

   ```python
   raw = json.loads(hydro_json.read_text(encoding="utf-8"))
   if isinstance(raw, list):
       df = pd.DataFrame(raw)
   elif isinstance(raw, dict) and "rows" in raw:
       df = pd.DataFrame(raw.get("rows", []))
   else:
       df = pd.DataFrame(raw)
   ```
2. **Column name normalization**

   ```python
   colmap = {}
   if "MCTC_t_m_per_cm" in df.columns and "MTC_t_m_per_cm" not in df.columns:
       colmap["MCTC_t_m_per_cm"] = "MTC_t_m_per_cm"
   if "LCF_m_from_midship" in df.columns and "LCF_m" not in df.columns:
       colmap["LCF_m_from_midship"] = "LCF_m"
   df = df.rename(columns=colmap)
   ```

   - Supports various naming conventions (e.g., `MCTC` vs `MTC`)
3. **Required column validation**

   ```python
   required = ["Tmean_m", "TPC_t_per_cm", "MTC_t_m_per_cm", "LCF_m"]
   missing = [c for c in required if c not in df.columns]
   if missing:
       raise ValueError(f"Hydro table missing required columns: {missing}")
   ```
4. **LBP default handling**

   ```python
   if "LBP_m" not in df.columns:
       df["LBP_m"] = float(lbp_m)  # Default: LPP_M = 60.302
   ```
5. **Sorting and filtering**

   - Sort ascending by `Tmean_m`
   - Remove rows where `Tmean_m` is NaN

---

## 2.4 Stage Table Construction

### 2.4.1 Input: `stage_results.csv` (Step 1 output)

File generated when Step 1 (TR Excel Generator) runs in CSV mode.

**Expected columns (flexible recognition):**

- `Stage` or `stage_name` or `name`: Stage identifier
- `Dfwd_m` or `FWD_m`: Forward Draft (m)
- `Daft_m` or `AFT_m`: Aft Draft (m)
- Other metadata (optional)

### 2.4.2 Output: `stage_table_unified.csv`

**Solver columns:**

- `Stage`: Stage identifier
- `Current_FWD_m`: Current Forward Draft (m)
- `Current_AFT_m`: Current Aft Draft (m)
- `FWD_MAX_m`: FWD maximum gate (e.g., 2.70m)
- `AFT_MIN_m`: AFT minimum gate (e.g., 2.70m)
- `D_vessel_m`: Hull depth (m, for Freeboard calculation)
- `Forecast_Tide_m`: Forecast tide (m, optional, for UKC calculation)
- `DepthRef_m`: Reference depth (m, optional, for UKC calculation)
- `UKC_Min_m`: Minimum UKC requirement (m, optional)

**Optimizer columns:**

- `FWD_Limit_m`: FWD upper limit (m, = FWD_MAX_m)
- `AFT_Limit_m`: AFT upper limit (m, Optimizer only, e.g., 3.50m)
- `Trim_Abs_Limit_m`: Absolute trim limit (m, e.g., 0.50m)

### 2.4.3 Conversion Function: `build_stage_table_from_stage_results`

**Location:** `integrated_pipeline_defsplit_v2.py` (lines 266-344)

**Key logic:**

1. **Flexible column recognition**

   ```python
   stage_col = "Stage" if "Stage" in df.columns else None
   if stage_col is None:
       for c in df.columns:
           if str(c).strip().lower() in ("stage_name", "name"):
               stage_col = c
               break
   ```

   - Automatically recognizes various naming conventions
2. **Draft column mapping**

   ```python
   dfwd_col = ("Dfwd_m" if "Dfwd_m" in df.columns
               else ("FWD_m" if "FWD_m" in df.columns else None))
   daft_col = ("Daft_m" if "Daft_m" in df.columns
               else ("AFT_m" if "AFT_m" in df.columns else None))
   ```
3. **Gate value assignment**

   - For Solver: `FWD_MAX_m`, `AFT_MIN_m` (required)
   - For Optimizer: `FWD_Limit_m`, `AFT_Limit_m`, `Trim_Abs_Limit_m`
4. **Optional UKC parameters**

   - Add columns if `forecast_tide_m`, `depth_ref_m`, `ukc_min_m` are provided
   - Required inputs for UKC calculation (see Chapter 5)

---

## 2.5 Stage QA CSV Generation

### 2.5.1 Purpose

Generate QA CSV to verify Definition-Split concept and clearly check gate compliance for each stage.

**Location:** `integrated_pipeline_defsplit_v2.py` (lines 347-466)

### 2.5.2 Output: `pipeline_stage_QA.csv`

**Definition-Split columns:**

| Column                    | Description                                                    | Formula                                                 |
| ------------------------- | -------------------------------------------------------------- | ------------------------------------------------------- |
| `Forecast_Tide_m`       | Forecast tide (predicted value)                                | Input value (e.g., 0.30m)                               |
| `Required_WL_for_UKC_m` | Required water level for UKC satisfaction (reverse-calculated) | `(Draft_max + Squat + Safety + UKC_MIN) - DepthRef`   |
| `Freeboard_FWD_m`       | Freeboard at FWD (tide independent)                            | `D_vessel_m - Current_FWD_m`                          |
| `Freeboard_AFT_m`       | Freeboard at AFT (tide independent)                            | `D_vessel_m - Current_AFT_m`                          |
| `Freeboard_Min_m`       | Minimum Freeboard                                              | `min(Freeboard_FWD, Freeboard_AFT)`                   |
| `UKC_FWD_m`             | UKC at FWD (tide dependent)                                    | `(DepthRef + Forecast_Tide) - (FWD + Squat + Safety)` |
| `UKC_AFT_m`             | UKC at AFT (tide dependent)                                    | `(DepthRef + Forecast_Tide) - (AFT + Squat + Safety)` |
| `UKC_Min_m`             | Minimum UKC                                                    | `min(UKC_FWD, UKC_AFT)`                               |

**Gate verification columns:**

| Column             | Values              | Description                                           |
| ------------------ | ------------------- | ----------------------------------------------------- |
| `Gate_FWD_Max`   | "OK" / "NG"         | Whether FWD ≤ FWD_MAX_m                              |
| `Gate_AFT_Min`   | "OK" / "NG"         | Whether AFT ≥ AFT_MIN_m                              |
| `Gate_Freeboard` | "OK" / "NG"         | Whether Freeboard ≥ 0                                |
| `Gate_UKC`       | "OK" / "NG" / "N/A" | Whether UKC ≥ UKC_MIN_m (only if parameter provided) |

**Margin columns:**

| Column           | Description                                               |
| ---------------- | --------------------------------------------------------- |
| `FWD_Margin_m` | `FWD_MAX_m - Current_FWD_m` (positive if margin exists) |
| `AFT_Margin_m` | `Current_AFT_m - AFT_MIN_m` (positive if margin exists) |
| `UKC_Margin_m` | `UKC_Min_m - UKC_Min_Required_m` (if provided)          |

### 2.5.3 Key Calculation Logic

**Freeboard (tide independent):**

```python
freeboard_fwd = d_vessel_m - dfwd
freeboard_aft = d_vessel_m - daft
freeboard_min = min(freeboard_fwd, freeboard_aft)
```

**⚠️ SSOT Gap - Operational Minimum Freeboard:**

- **Current Implementation:** Geometric definition only (`Freeboard = D_vessel - Draft`) ✓
- **Gate Check:** Only prevents negative freeboard (`Freeboard_Min_m >= -tol_m`)
- **Missing:** Operational minimum freeboard requirement not defined in SSOT (AGENTS.md)
- **Default `freeboard_min_m = 0.0`:** No operational buffer (only prevents deck wet)
- **Recommendation:** Define operational minimum freeboard in SSOT (e.g., 0.20m, 0.50m for operations)
- **Documentation Requirement:** When `freeboard = 0.00m`, explicitly state whether this is acceptable or requires mitigation

**UKC (tide dependent):**

```python
if depth_ref_m is not None and forecast_tide_m is not None:
    available_depth = depth_ref_m + forecast_tide_m
    ukc_fwd = available_depth - (dfwd + squat_m + safety_allow_m)
    ukc_aft = available_depth - (daft + squat_m + safety_allow_m)
    ukc_min = min(ukc_fwd, ukc_aft)
```

**Required_WL_for_UKC_m (reverse calculation):**

```python
if ukc_min_m is not None:
    draft_ref_max = max(dfwd, daft)
    required_wl_for_ukc = (
        draft_ref_max + squat_m + safety_allow_m + ukc_min_m
    ) - depth_ref_m
    required_wl_for_ukc = max(required_wl_for_ukc, 0.0)  # Prevent negative
```

---

## 2.6 Data Validation and Error Handling

### 2.6.1 Input Validation

Each conversion function performs the following validation:

1. **File existence check**

   - `Path.exists()` check
   - `FileNotFoundError` with clear error message if file not found
2. **JSON structure validation**

   - Check for expected top-level keys (`tanks`, `rows`, etc.)
   - Validate data types (list, dict, etc.)
3. **Required column validation**

   - CSV: Check for required column existence
   - JSON: Check for required field existence
   - Provide list of missing columns with `ValueError` if missing
4. **Numeric data validation**

   - Safe conversion with `pd.to_numeric(..., errors="coerce")`
   - Handle NaN values (drop or assign default)

### 2.6.2 Coordinate System Consistency Validation

**Validation items:**

- `x_from_mid_m` range: Generally within `[-LPP_M/2, +LPP_M/2]` range
- `LCF_m` range: Generally within `[-2.0, +2.0]` m range (varies by vessel design)

**Consistency check:**

- Use same constants throughout pipeline (`LPP_M = 60.302`, `MIDSHIP_FROM_AP_M = 30.151`)
- Use same coordinate system conversion formula in all conversion functions

### 2.6.3 Error Recovery Strategy

1. **Allow partial failure**

   - Continue processing remaining tanks if some tank conversions fail
   - Raise `ValueError` if final result is empty
2. **Logging**

   - Output major steps of conversion process to console
   - Provide detailed context information on error
3. **Default value assignment**

   - Use reasonable defaults for optional parameters
   - Example: `pump_rate_tph = 100.0`, `priority_weight = 5.0`

---

## 2.7 CSV Schema Summary

### 2.7.1 Tank SSOT Schema

```python
{
    "Tank": str,                    # Required
    "Capacity_t": float,            # Required, > 0
    "x_from_mid_m": float,          # Required, +AFT/-FWD
    "Current_t": float,             # Required, ≥ 0, ≤ Capacity_t
    "Min_t": float,                 # Required, ≥ 0
    "Max_t": float,                 # Required, ≥ Min_t, ≤ Capacity_t
    "mode": str,                    # Required, "FILL_DISCHARGE"|"FILL_ONLY"|"DISCHARGE_ONLY"|"BLOCKED"|"FIXED"
    "use_flag": str,                # Required, "Y"|"N"
    "pump_rate_tph": float,         # Required, > 0
    "priority_weight": float        # Required, > 0 (lower = higher priority)
}
```

### 2.7.2 Hydro Table SSOT Schema

```python
{
    "Tmean_m": float,               # Required, sorted ascending, > 0
    "TPC_t_per_cm": float,          # Required, > 0
    "MTC_t_m_per_cm": float,        # Required, > 0
    "LCF_m": float,                 # Required, +AFT/-FWD
    "LBP_m": float                  # Required, > 0 (typically 60.302)
}
```

### 2.7.3 Stage Table SSOT Schema

```python
{
    "Stage": str,                   # Required
    "Current_FWD_m": float,         # Required
    "Current_AFT_m": float,         # Required
    "FWD_MAX_m": float,             # Required, > 0
    "AFT_MIN_m": float,             # Required, > 0
    "FWD_Limit_m": float,           # Optional (Optimizer)
    "AFT_Limit_m": float,           # Optional (Optimizer)
    "Trim_Abs_Limit_m": float,      # Optional (Optimizer)
    "D_vessel_m": float,            # Optional, > 0
    "Forecast_Tide_m": float,       # Optional (UKC)
    "DepthRef_m": float,            # Optional (UKC), > 0
    "UKC_Min_m": float              # Optional (UKC), ≥ 0
}
```

---

## 2.8 Tank SSOT Post-Processing (Sensor Data and Overrides)

After Tank SSOT CSV generation, the following post-processing steps are performed:

### 2.8.1 Current_t Sensor Data Injection (v3.1 update)

Read sensor CSV files provided by PLC/IoT systems and automatically inject `Current_t` values into Tank SSOT.

#### Auto-discovery Feature (v3.1)

**Function**: `resolve_current_t_sensor_csv()`

**Search order:**

1. Explicit `--current_t_csv` argument
2. Fixed path candidates:
   - `inputs_dir/current_t_sensor.csv`
   - `inputs_dir/current_t.csv`
   - `inputs_dir/sensors/current_t_sensor.csv`
   - `inputs_dir/sensors/current_t.csv`
   - `inputs_dir/plc/current_t.csv`
   - `inputs_dir/iot/current_t.csv`
3. **Fallback auto-discovery** (v3.1 new):
   - Search directories: `inputs_dir`, `inputs_dir/sensors`, `base_dir`, `base_dir/sensors`
   - Pattern: `current_t_*.csv`, `current_t-*.csv`
   - Selection criteria: Latest modification time (mtime) priority

#### Injection Function

**Function**: `inject_current_t_from_sensor_csv()`

**Input**: Sensor CSV (`sensors/current_t_final_verified.csv`, etc.)

**Strategy:**

- `override` (default): Overwrite all values
- `fill_missing`: Inject only if 0.0

**Matching:**

- Exact match: `LRFO.P` → `LRFO.P`
- Base name matching: `FWB1` → `FWB1.P`, `FWB1.S`

#### diff_audit.csv Generation (v3.1 new)

**Location**: `ssot/diff_audit.csv`

**Columns:**

- `Tank`, `TankKey`, `TankBase`
- `CurrentOld_t`, `ComputedNew_t`, `Delta_t`
- `ClampedFlag` (N/Y), `Updated` (Y/N)
- `SkipReason` (NO_MATCH, etc.)

**Usage:**

- Track sensor injection history
- Compare values before/after injection
- Check clamping status

**Note**: Details: See section 5 of `Ballast Pipeline 운영 가이드.MD`.

### 2.8.2 Tank Overrides Application

Apply settings for specific tanks defined in the `tank_overrides` section of the Site profile to Tank SSOT.

- **Function**: `apply_tank_overrides_from_profile()`
- **Input**: `tank_overrides` object from profile JSON
- **Supported overrides**: `mode`, `use_flag`, `pump_rate_tph`, `Min_t`, `Max_t`, `priority_weight`
- **Matching**: Exact match or base name matching (e.g., `VOID3` → `VOID3.P`, `VOID3.S`)

**Note**: Details: See sections 4.1 and 3.3 of `Ballast Pipeline 운영 가이드.MD`.

---

## 2.9 Excel Generation and SSOT (2024-12-23 update)

### 2.9.1 Why Excel Reads stage_results.csv

Previously, Excel generation (`create_roro_sheet()`) used hardcoded cfg, but **after 2024-12-23 patch**, it directly reads `stage_results.csv` to dynamically determine TR positions.

**Before change (duplicate cfg problem):**

```python
# agi_tr_patched_v6_6_defsplit_v1.py
# Line 4070: Old version cfg
cfg = {
    "FR_TR2_STOW": 40.00,  # Old value
}

# Line 7494: New version cfg
cfg = {
    "FR_TR2_STOW": 29.39,  # Latest value
}
```

- Problem: Excel and CSV could use different cfg
- Result: Stage 6C TR position mismatch (x=-9.50m vs x=0.76m)

**After change (SSOT unified):**

```python
# agi_tr_patched_v6_6_defsplit_v1.py - inside create_roro_sheet()
import csv
from pathlib import Path

stage_results_path = Path("stage_results.csv")
if stage_results_path.exists():
    print("[INFO] Reading TR positions from stage_results.csv (SSOT)")
    stage_data = {}
    with open(stage_results_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            stage_name = row.get('Stage', '')
            x_stage_m = float(row.get('x_stage_m', 0.0))
            stage_data[stage_name] = {'x': x_stage_m}

    # x (m from midship) → Frame number conversion
    def x_to_fr(x_m: float) -> float:
        return 30.151 - x_m

    cfg = {
        "W_TR": 271.20,
        "FR_TR2_STOW": x_to_fr(stage_data.get('Stage 6C', {}).get('x', 0.76)),
        # x=0.76m → Fr=29.391
    }
    print(f"[INFO] cfg from stage_results.csv: {cfg}")
```

**Effect:**

- Excel and CSV use **the same** `stage_results.csv` data
- TR position data unified (Single Source of Truth)
- Excel/CSV mismatch problem completely resolved

### 2.9.2 Draft Clipping Logic

Automatically clips stage data if it exceeds vessel physical limits (`D_vessel` = 3.65m, molded depth).

**Implementation location:** Inside `build_stage_table_from_stage_results()` function

```python
D_vessel_m = 3.65  # LCT BUSHRA molded depth (keel to main deck)

# Draft clipping
if dfwd > D_vessel_m:
    print(f"[WARNING] Draft clipped: FWD {dfwd:.2f} -> {D_vessel_m:.2f}m")
    dfwd = D_vessel_m

if daft > D_vessel_m:
    print(f"[WARNING] Draft clipped: AFT {daft:.2f} -> {D_vessel_m:.2f}m")
    daft = D_vessel_m

# Freeboard calculation
freeboard_fwd = D_vessel_m - dfwd
freeboard_aft = D_vessel_m - daft
freeboard_min = min(freeboard_fwd, freeboard_aft)
```

**Actual example (Stage 6C):**

| Item                | stage_results.csv (Input) | pipeline_stage_QA.csv (Output) | Note                                  |
| ------------------- | ------------------------- | ------------------------------ | ------------------------------------- |
| x_stage_m           | 0.76m                     | -                              | LCF (even keel)                       |
| Dfwd_m (calculated) | 3.80m                     | 3.65m                          | Clipped to D_vessel                   |
| Daft_m (calculated) | 3.80m                     | 3.65m                          | Clipped to D_vessel                   |
| Trim_cm             | 0.0                       | 0.0                            | Even keel maintained                  |
| Freeboard_Min_m     | -                         | 0.00m                          | **⚠️ Deck edge at waterline** |

**Pipeline log example:**

```
[WARNING] Draft values clipped to D_vessel (3.65m) for 1 stages:
  - Stage 6C: FWD 3.80 -> 3.65m, AFT 3.80 -> 3.65m
[CRITICAL] PHYSICAL LIMIT EXCEEDED: Freeboard = 0.00m (deck edge at waterline) for 1 stage(s):
  - Stage 6C: Draft = D_vessel (3.65m) -> Freeboard = 0.00m
[ACTION REQUIRED] Engineering verification required:
  1. Validate input: Check TR position, cargo weight, and stage calculations
  2. If input is valid: Requires class acceptance and load-line compliance documentation
  3. Risk mitigation: Green water risk, structural stress at deck edge
  4. Approval packages must explicitly state draft clipping and justify freeboard = 0.00m
```

### 2.9.3 Freeboard = 0.00m Risk and Mitigation

**⚠️ Critical Safety Warning:**

**Clipping vs. Physical Judgment:**

- **Clipping masks input validity issues:** Input draft exceeding D_vessel indicates potential input error or structural concern
- **Freeboard = 0.00m risk:** Deck edge at waterline → green water risk, structural stress
- **Recommendation:** Draft exceeding D_vessel should trigger:
  1. **FAIL**: If input is invalid (TR position error, calculation error)
  2. **VERIFY**: If input is valid but requires engineering approval (class acceptance, load-line verification)

**Risk:**

- Draft = D_vessel → **Deck edge at waterline**
- Possible **green water** (deck wet) due to waves/swell
- Cargo damage, safety risk
- **Structural stress** at deck edge

**Mitigation:**

**1. Tidal Assist (recommended)**

```
Mina Zayed Tidal Data (Jan 1-5, 2026):
- High Tide: 2.10-2.22m (Chart Datum)
- Effective Freeboard: Freeboard_calc + Tide_height
- Stage 6C example: 0.00m + 2.22m = +2.22m effective freeboard
```

**2. D_allow Reset (alternative)**

```python
# Current: D_allow = 3.65m (zero freeboard)
# Recommended: D_allow = 3.35m (safety margin +0.30m)

D_allow_revised = 3.35  # m
Required_deballast = (Current_Draft - D_allow_revised) * TPC
# Stage 6C example: (3.65 - 3.35) * 10.5 ≈ 3.15 t
```

**3. Operational constraints**

- Weather conditions: Sea state ≤ 2
- Real-time draft monitoring
- Emergency deballast plan ready

### 2.9.4 Data Flow Diagram (updated)

```
┌─────────────────────────────────────────────────────────┐
│          SOURCE DATA (JSON - Single Source)             │
├─────────────────────────────────────────────────────────┤
│  tank_catalog_from_tankmd.json                         │
│  Hydro_Table_Engineering.json                          │
│  stage_results.csv (from Step 1b) ⭐ NEW: Excel also uses │
└──────────────────────┬──────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        ↓              ↓              ↓
   [Step 1]       [Pipeline]     [Step 2-4]
   Excel Gen      SSOT Conv      OPS/Solver
        ↓              ↓              ↓
   ✅ Reads        Converts       Consumes
   stage_results   to SSOT CSV    SSOT CSV
        ↓              ↓              ↓
   Excel =        Stage QA       Ballast
   CSV data       (clipped)      Plans
```

---

## 2.10 GM Verification and FSM Integration (v3.1 new)

### 2.10.1 GM 2D Grid Integration

**File**: `LCT_BUSHRA_GM_2D_Grid.json`

**Structure:**

```json
{
  "description": "LCT BUSHRA GM 2D Grid",
  "grid_axis": "disp_x_trim",  // Standard axis: DISP×TRIM
  "disp": [3200, 3400, 3600, ...],  // Displacement (t)
  "trim": [-1.5, -1.0, -0.5, ...],  // Trim (m)
  "gm_grid": [
    [1.552, 1.598, ...],  // gm_grid[disp_idx][trim_idx]
    ...
  ]
}
```

**Axis alignment rules:**

- Pipeline engine standard: `DISP×TRIM` (`gm_grid[disp_idx][trim_idx]`)
- Auto-transpose if input Grid is `TRIM×DISP`

### 2.10.2 CLAMP Detection

**Status**: `VERIFY_CLAMP_RANGE`

**Conditions:**

- `Disp < disp_min` → `CLAMP_LOW`
- `Disp > disp_max` → `CLAMP_HIGH`
- `Trim < trim_min` → `CLAMP_LOW`
- `Trim > trim_max` → `CLAMP_HIGH`

**Impact:**

- GM value forced to Grid boundary value
- `VERIFY` status for submission (range expansion needed)

### 2.10.3 FSM (Free Surface Moment) Integration

**File**: `Tank_FSM_Coeff.json`

**Structure** (nested support):

```json
{
  "tanks": {
    "LRFO.P": {"fsm_tm_max": 45.2},
    "LRFO.S": {"fsm_tm_max": 45.2},
    ...
  }
}
```

**Calculation:**

- `FSM_total_tm = Σ fsm_from_coeff(tank, fill_pct)`
- `GM_eff = GM_raw - (FSM_total_tm / Displacement)`

**Status:**

- `FSM_status = OK`: Coefficient exists, calculation complete
- `FSM_status = MISSING_COEFF`: Partially filled tanks exist but no coefficient
- `FSM_status = NOT_REQUIRED`: No partially filled tanks

### 2.10.4 GM Verification Output

**File**: `gm_stability_verification_v2b.csv`

**Key columns:**

- `GM_raw_m`: GM interpolated from Grid
- `GM_grid_source`: Grid file path or "fallback_minimal_safe_1.50"
- `GM_is_fallback`: Whether fallback is used
- `FSM_status`: FSM status (OK/MISSING_COEFF/NOT_REQUIRED)
- `FSM_total_tm`: Total FSM (t·m)
- `GM_eff_m`: Effective GM (GM_raw - FSM/Δ)
- `Status`: GOOD/MINIMUM/FAIL/VERIFY_CLAMP_RANGE/VERIFY_FSM_MISSING

**Note**: Details: See `verify_gm_stability_v2b.py` script.

---

## 2.11 Tide Integration Data Flow (AGI-only, v3.3 new)

### 2.11.1 Tide Stage Mapping (Pre-Step)

**Input files:**

- `bplus_inputs/water tide_202512.xlsx` (time-series tide data)
  - `datetime_gst`: Timestamp (GST)
  - `tide_m (Chart Datum)`: Tide height (m, CD)
- `bplus_inputs/tide_windows_AGI.json` (stage time windows)
  - `windows`: Array of `{Stage, start, end, stat, note}`
  - `stat`: "min" or "mean" (tide statistic selection)

**Processing:**

- Execute `tide_stage_mapper.py` (Pre-Step)
- Extract min/mean tide for each Stage's time window
- Support Stage alias mapping (e.g., "Stage 6 50% TR2 loaded (HOLD)" → "Stage 6A_Critical (Opt C)")

**Output:**

- `stage_tide_AGI.csv`
  - `StageKey`: Stage name
  - `Forecast_tide_m`: Stage-wise tide (m, CD)
  - `tide_src`: "window_min" or "window_mean"
  - `tide_qc`: "OK", "VERIFY", or "MISSING_WINDOW"

### 2.11.2 Stage Table Merge (Step 1b)

**Merge logic:**

- Merge `stage_tide_AGI.csv` when creating `stage_table_unified.csv`
- Add `Forecast_Tide_m` column (overwrite from stage_tide)
- Add `DatumOffset_m` column (CLI `--datum_offset` parameter)
- Add `Tide_Source`, `Tide_QC` columns (data source tracking)

**SSOT rules (v3.6 update, 2025-12-29):**

- `Forecast_Tide_m` priority:
  0. CLI `--forecast_tide` (highest priority, directly applied to all Stages if explicitly provided)
  1. `stage_tide_AGI.csv` (used only if CLI not provided)
  2. `tide_table` + `stage_schedule` interpolation (option)
  3. CLI `--forecast_tide` (fillna, safety mechanism)
- `DatumOffset_m` is CLI parameter SSOT (default: 0.0 m)

**Changes (2025-12-29):**

- CLI `--forecast_tide` value takes highest priority, ensuring complete alignment of `Forecast_Tide_m` between `stage_table_unified.csv` and `solver_ballast_summary.csv`
- Details: See section 17.6.5 of `17_TIDE_UKC_Calculation_Logic.md`

### 2.11.3 UKC Calculation (Step 3)

**Calculation formula (fixed):**

- `AvailableDepth_m = DepthRef_m + DatumOffset_m + Forecast_tide_m`
- `UKC_fwd_m = AvailableDepth_m - (Dfwd_m + Squat_m + SafetyAllow_m)`
- `UKC_aft_m = AvailableDepth_m - (Daft_m + Squat_m + SafetyAllow_m)`
- `UKC_min_calc_m = min(UKC_fwd_m, UKC_aft_m)`
- `Tide_required_m = max(0.00, (Draft_ref_m + Squat_m + SafetyAllow_m + UKC_min_m) - (DepthRef_m + DatumOffset_m))`
- `Tide_margin_m = Forecast_tide_m - Tide_required_m`

**Tide Verdict:**

- `FAIL`: `Tide_margin_m < 0.00`
- `LIMIT`: `0.00 ≤ Tide_margin_m < 0.10`
- `OK`: `Tide_margin_m ≥ 0.10`
- `VERIFY`: `Tide_QC == "VERIFY"` (missing window or data quality issue)

### 2.11.4 QA CSV Alias Columns

**Alias columns added to pipeline_stage_QA.csv:**

- `Forecast_tide_m` ← `Forecast_Tide_m`
- `Tide_required_m` ← `Required_WL_for_UKC_m`
- `UKC_min_m` ← `UKC_Min_Required_m`
- `UKC_fwd_m` ← `UKC_FWD_m`
- `UKC_aft_m` ← `UKC_AFT_m`

**Purpose:** Provide user-friendly column names, maintain consistency

### 2.11.5 AUTO-HOLD Warnings

**Trigger conditions:**

- Holdpoint stages: Stage 2, Stage 6A_Critical (Opt C)
- `Tide_margin_m < 0.10` (10cm margin threshold)

**Output:**

- Automatically inserted into `gate_fail_report.md`
- Format: `**HOLD**: {stage_name} Tide_margin_m={value:.3f} (< 0.10m)`

### 2.11.6 Consolidated Excel TIDE_BY_STAGE Sheet

**Generation location:** `merge_excel_files_to_one()` function
**Data source:** `pipeline_stage_QA.csv`
**Columns:**

- `Stage`, `Forecast_tide_m`, `Tide_required_m`, `Tide_margin_m`
- `UKC_min_m`, `UKC_fwd_m`, `UKC_aft_m`, `Tide_verdict`

---

## 2.12 SPMT Integration Data Flow (v3.3 new)

### 2.12.1 SPMT Cargo Input Generation

**Input:**

- `spmt/cargo_spmt_inputs_config_example.json` (SPMT config)
- `stage_results.csv` (SSOT, optional for SSOT mapping)

**Processing:**

- Execute `spmt_unified.py integrate`
  - `cargo-autofill` → `Cargo_SPMT_Inputs.xlsx`
  - `shuttle-builder` → `stage_loads.csv`, `stage_summary.csv`
  - `stage-autocalc` → `Stage_Results` (with SSOT mapping)
  - `lct-shuttle` → `LCT_Stages_Summary` (optional)

**Output:**

- `SPMT_Integrated_Complete.xlsx`
  - `Stage_Config`: SSOT parameters
  - `Cargo_SPMT_Inputs`: Cargo data
  - `Stage_Results`: SSOT-mapped stage results
  - `Stage-wise Cargo on Deck`: Bryan format

### 2.12.2 Bryan Template Integration

**Input:**

- `SPMT_Integrated_Complete.xlsx` (from Step 5a)
- `stage_results.csv` (SSOT)

**Processing:**

- Execute `bryan_template_unified.py one-click`
  - `create` → `Bryan_Submission_Data_Pack_Template.xlsx`
  - `populate` → Uses `stage_results.csv`
  - `--spmt-xlsx` → Imports SPMT cargo into `04_Cargo_SPMT` sheet

**Output:**

- `Bryan_Submission_Data_Pack_Populated.xlsx`
  - `04_Cargo_SPMT`: SPMT cargo data
  - `07_Stage_Calc`: Stage calculations
  - `06_Stage_Plan`: Stage-wise cargo positions

### 2.12.3 Coordinate System Alignment

**SPMT ↔ Pipeline:**

- **SPMT uses:** `x_from_midship = midship_from_ap_m - Fr(m)`
- **Pipeline uses:** Same formula (AGENTS.md Method B)
- **Midship reference:** 30.151 m from AP (consistent)

**Stage Definition Alignment:**

- SPMT stages: Stage 1, 2, 3, 4, 5, 5_PreBallast, 6A_Critical, 6C, 7
- Pipeline stages: Same 9-stage set (from `stage_results.csv`)
- SSOT enforcement: Stage names must match exactly

---

## 2.14 Ballast Sequence Data Flow (Option 2, v3.5 new)

### 2.14.1 Option Planning vs Execution Sequence Separation

**Problems:**

- NaN issues with Delta_t/Target_t in existing `BALLAST_SEQUENCE.csv`
- Stage 6B mixed into execution sequence causing Start_t/Target_t accumulation errors
- Planning level and execution level mixed

**Solution (Option 2):**

- **BALLAST_OPTION.csv**: Planning/option level (Delta_t centered, includes all Stages)
- **BALLAST_EXEC.csv**: Execution sequence (Start_t/Target_t chain, Stage 6B excluded)

### 2.14.2 BALLAST_OPTION.csv Structure

**Purpose:** Express ballast changes for all Stages at planning level, Delta_t centered

**Columns:**

- `Stage`: Stage name (includes all Stages, including Stage 6B)
- `Tank`: Tank ID
- `Action`: FILL/DISCHARGE
- `Delta_t`: Mass change (t)
- `PumpRate_tph`: Pump rate (t/h)
- `Priority`: 1=highest (critical), 2=PreBallast, 3=Standard, 5=Optional (Stage 6B)
- `Rationale`: Why this action is needed

**Features:**

- No Start_t/Target_t (Delta_t only)
- Includes all Stages (including Stage 6B)
- Clarifies planning intent with Priority and Rationale

### 2.14.3 BALLAST_EXEC.csv Structure

**Purpose:** Clearly express step-by-step Start_t/Target_t chain at execution level

**Columns:**

- `Stage`: Stage name (Stage 6B excluded)
- `Step`: Sequential step number
- `Tank`: Tank ID
- `Action`: FILL/DISCHARGE
- `Start_t`: Start mass (t, carry-forward from previous step's Target_t)
- `Target_t`: Target mass (t, Start_t + Delta_t)
- `Delta_t`: Mass change (t)
- `Time_h`: Duration (h)
- `Pump_ID`: Pump identifier
- `PumpRate_tph`: Pump rate (t/h)
- `Valve_Lineup`: Valve IDs
- `Hold_Point`: Y/N
- `Draft_FWD`, `Draft_AFT`, `Trim_cm`, `UKC`: Predicted conditions
- `Notes`: Warnings/notes

**Core logic:**

```python
# Tank state tracking across steps (carry-forward)
tank_state: Dict[str, float] = initial_tank_current.copy()

for step in sequence:
    tank_id = step.tank
    # Start_t = current tank state (carry-forward from previous step)
    start_t = tank_state.get(tank_id, 0.0)
    target_t = start_t + step.delta_t

    # Update tank state for next step
    tank_state[tank_id] = target_t
```

**Features:**

- Start_t/Target_t chain: Maintains state for consecutive operations on same tank
- Stage 6B excluded: Filtered via OPTIONAL_STAGES constant
- Tank capacity validation: Clipping if Target_t > Capacity_t

### 2.14.4 Stage 6B Separation Logic

**OPTIONAL_STAGES constant:**

```python
OPTIONAL_STAGES = [
    "Stage 6B Tide Window",  # Option/analysis scenario - excluded from execution sequence
]
```

**Filtering:**

```python
stage_order = _stage_order_from_df(ballast_plan_df)
if exclude_optional_stages:
    stage_order = [s for s in stage_order if s not in OPTIONAL_STAGES]
```

**Result:**

- `BALLAST_OPTION.csv`: Includes Stage 6B (planning level)
- `BALLAST_EXEC.csv`: Excludes Stage 6B (execution level)

### 2.14.5 Data Flow Diagram

```
┌─────────────────────────────────────────────────────────┐
│          SOLVER/OPTIMIZER OUTPUT                        │
├─────────────────────────────────────────────────────────┤
│  solver_ballast_stage_plan.csv                         │
│    └─> Stage, Tank, Delta_t/Weight_t                    │
└──────────────────────┬──────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        ↓              ↓              ↓
   [Option Plan]  [Exec Sequence]  [Legacy]
        ↓              ↓              ↓
BALLAST_OPTION.csv  BALLAST_EXEC.csv  BALLAST_SEQUENCE.csv
(All Stages)       (Stage 6B excluded) (Compatibility)
        ↓              ↓              ↓
   Priority        Start_t/Target_t  Legacy format
   Rationale       Carry-forward
   Delta_t         Time_h
```

---

## 2.15 Option 1 Patch Proposal (AGI Submission Readiness Improvement, Not Implemented)

### Background

AGI submission readiness verification results indicate 3 patches needed:

1. **Bryan Pack Forecast_tide_m Injection**

   - Problem: `Forecast_tide_m` not injected into `07_Stage_Calc` of `Bryan_Submission_Data_Pack_Populated.xlsx`
   - Solution: Read `Forecast_tide_m` from `pipeline_stage_QA.csv`, merge with `stage_results.csv`, then populate
   - Implementation location: `integrated_pipeline` Step 5 (before Bryan Pack generation)
2. **Stage 5_PreBallast GateB Critical Enforcement**

   - Problem: `Stage 5_PreBallast` not caught as GateB critical application target
   - Solution: Add explicit check to `_is_critical_stage()` function
   - Implementation location: `integrated_pipeline` Gate calculation logic
3. **Current_* vs Draft_* Unification**

   - Problem: `Current_*` and `Draft_*` coexist in `pipeline_stage_QA.csv` causing confusion
   - Solution: Remove `Current_*` columns or unify to `Draft_*` when generating QA
   - Implementation location: `generate_stage_QA_csv()` function

**Details:** See `02_IMPLEMENTATION_REPORTS/20251228/OPTION1_OPTION2_AGI_SUBMISSION_PATCHES_20251228.md`

---

## 2.17 Execution File → Output File → Header Structure Mapping (v3.7 new)

### 2.17.1 Pipeline Execution Flow → Output File → Header Structure

#### Step 0: SPMT Cargo Generation (optional)

- **Execution file**: `spmt v1/agi_spmt_unified.py`
- **Output file**: `AGI_SPMT_Shuttle_Output.xlsx`
- **Generated headers**:
  - `Stage_Summary`: `Stage`, `Stage_Name`, `Total_onDeck_t`, `LCG_x_from_Midship_m`, `LCG_Fr_from_AP_m`, `Note`
  - `Stage_Loads`: `Stage`, `Stage_Name`, `Item`, `Weight_t`, `Fr_m_from_AP`, `x_m_from_Midship`
  - `Stage_Results`: `Stage`, `Cargo Total(t) [calc]`, `LCGx(m) [calc]`, `Cargo Total(t) [SSOT]`, `LCGx(m) [SSOT]`, `ΔCargo(t)`, `ΔLCGx(m)`, `Note`
  - `Stage-wise Cargo on Deck`: Same as Stage_Results (8 columns)

#### Step 1: TR Excel Generation (optional)

- **Execution file**: `agi_tr_patched_v6_6_defsplit_v1.py`
- **Output file**: `LCT_BUSHRA_AGI_TR_Final_v*.xlsx`
- **Generated headers**:
  - `Ballast_Tanks`: `TankName`, `x_from_mid_m`, `max_t`, `SG`, `use_flag`, `air_vent_mm`
  - `CONST_TANKS`: `Tank`, `Type`, `Weight_t`, `LCG_m`, `FSM_mt_m`, `Remarks`
  - `Hydro_Table`: `Disp_t`, `Tmean_m`, `Trim_m`, `GM_m`, `Draft_FWD`, `Draft_AFT`, `LCF_m_from_midship`, `MCTC_t_m_per_cm`, `TPC_t_per_cm`, `GM_min_m`, `LCF_m`, `KM_m`
  - `Hourly_FWD_AFT_Heights`: `DateTime (GST)`, `Tide_m`, `Dfwd_req_m (even)`, `Trim_m (optional)`, `Dfwd_adj_m`, `Daft_adj_m`, `Ramp_Angle_deg`, `Status`, `FWD_Height_m`, `AFT_Height_m`, `Notes`

#### Step 1b: stage_results.csv Generation (required)

- **Execution file**: `agi_tr_patched_v6_6_defsplit_v1.py csv`
- **Output file**: `stage_results.csv`
- **Generated headers**: `Stage`, `Dfwd_m`, `Daft_m`, `Disp_t`, `Tmean_m`, `Trim_cm`, etc.
- **SSOT role**: Stage definition SSOT for all subsequent reports/verification scripts

#### Step 2: OPS Integrated Report

- **Execution file**: `ops_final_r3_integrated_defs_split_v4_patched_TIDE_v1.py`
- **Output file**: `OPS_FINAL_R3_AGI_Ballast_Integrated.xlsx`
- **Generated headers**:
  - `Stage_Calculations`: 37 columns (Stage, Description, Mass_t, LCG_m, FWD_m, AFT_m, Trim_cm, Mean_m, Forecast_Tide_m, Water_Level_m, Max_Draft_m, Freeboard_Min_m, Gate_FWD_Max, Gate_AFT_Min, Gate_Freeboard, GM_m, GM_min_m, LCF_used_m, MCTC_used, TPC_used, FWD_Margin_m, AFT_Margin_m, Discharge_Needed_t, Status, Engineering_Grade, PreBallast_t, UKC_Min_m, Required_WL_m, Tide_required_m, Forecast_tide_m, Tide_margin_m, UKC_min_m, UKC_fwd_m, UKC_aft_m, UKC_min_actual_m, Gate_UKC, Gate_Overall)
  - `Tank_SSOT`: `Tank_ID`, `Category`, `Location`, `Fr_Start`, `Fr_End`, `Capacity_t`, `LCG_stern_m`, `LCG_midship_m`, `TCG_m`, `TCG_Side`, `VCG_m`
  - `Discharge_Matrix`: `Tank_ID`, `Capacity_t`, `LCG_m`, `Delta_FWD_per_10t_cm`, `Priority`, `Priority_Label`, `Effectiveness`, `Operational_Status`
  - `BWRB_Log`: `Date/Time`, `Operation`, `Tank_ID`, `Amount_t`, `Source`, `Destination`, `FWD_Before_m`, `FWD_After_m`, `Port_Approval`, `Master_Sign`, `BWMP_Status`

#### Step 3: Ballast Gate Solver (LP)

- **Execution file**: `tide/ballast_gate_solver_v4_TIDE_v1.py`
- **Output files**:
  - `solver_ballast_plan.csv`
  - `solver_ballast_summary.csv` (TIDE_v1: 8 Tide columns)
  - `solver_ballast_stage_plan.csv`
  - `solver_state_trace.csv`
- **Generated headers**:
  - `solver_ballast_summary.csv`: `Stage`, `Forecast_tide_m`, `DepthRef_m`, `UKC_min_m`, `Tide_required_m`, `Tide_margin_m`, `UKC_fwd_m`, `UKC_aft_m`, `Tide_verdict` (TIDE_v1 version)
  - `solver_ballast_stage_plan.csv`: `Stage`, `Tank`, `Action`, `Delta_t`, `Target_t`, `Current_t`, etc.

#### Step 4: Ballast Optimizer (optional)

- **Execution file**: `Untitled-2_patched_defsplit_v1_1.py`
- **Output file**: `optimizer_ballast_plan.xlsx`
- **Generated headers**:
  - `Plan`: `Stage`, `Tank`, `Action`, `Weight_t`, `Start_%`, `End_%`, `Time_h`
  - `Summary`: `Stage`, `Current_FWD_m`, `Current_AFT_m`, `New_FWD_m`, `New_AFT_m`, `ΔW_t`, `PumpTime_h`, `viol_fwd_m`
  - `Tank Log`: `Tank`, `UseFlag`, `Mode`, `Freeze`, `x_from_mid_m`, `Start_t`, `Δt_t`, `End_t`, `Min_t`, `Max_t`
  - `BWRB Log`: `Vessel`, `Location`, `Lat`, `Lon`, `Date`, `Start`, `End`, `Tank`, `Operation`, `Volume_m3`, `Weight_t`, `Officer`, `MasterVerified`, `Remarks`

#### Step 4b: Ballast Sequence Generator (optional)

- **Execution file**: `ballast_sequence_generator.py` (import module)
- **Output files**:
  - `BALLAST_EXEC.csv` (17 columns)
  - `BALLAST_OPTION.csv` (7 columns)
  - `BALLAST_SEQUENCE.csv` (19 columns)
  - `BALLAST_SEQUENCE.xlsx` (3 sheets: Ballast_Exec, Ballast_Option, Ballast_Sequence)
- **Generated headers**:
  - `BALLAST_EXEC.csv`: `Stage`, `Step`, `Tank`, `Action`, `Start_t`, `Target_t`, `Delta_t`, `Time_h`, `Pump_ID`, `PumpRate_tph`, `Valve_Lineup`, `Hold_Point`, `Draft_FWD`, `Draft_AFT`, `Trim_cm`, `UKC`, `Notes`
  - `BALLAST_OPTION.csv`: `Stage`, `Tank`, `Action`, `Delta_t`, `PumpRate_tph`, `Priority`, `Rationale`
  - `BALLAST_SEQUENCE.csv`: BALLAST_EXEC (17) + `Valve_Sequence`, `Valve_Notes` (2 additional)

#### Step 4c: Valve Lineup Generator (optional)

- **Execution file**: `valve_lineup_generator.py` (import module)
- **Output file**: `BALLAST_SEQUENCE_WITH_VALVES.md`
- **Role**: Add valve lineup information to Ballast Sequence

#### Step 5: Bryan Template Generation

- **Execution file**: `tide/bryan_template_unified_TIDE_v1.py`
- **Dependent scripts**:
  - `create_bryan_excel_template_NEW.py` (subprocess)
  - `populate_template.py` (import embedded)
- **Output file**: `Bryan_Submission_Data_Pack_Populated.xlsx`
- **Generated headers**:
  - `07_Stage_Calc`: Row 20 header (33-35 columns) - `Stage_ID`, `HoldPoint`, `GateB_Critical`, `Stage_Remark`, `Progress_%`, `x_stage_m`, `W_stage_t`, `Displacement_t`, `Tmean_m`, `Trim_cm`, `Draft_FWD_m`, `Draft_AFT_m`, `Freeboard_min_m`, `Tide_required_m`, `Forecast_tide_m`, `Tide_margin_m`, `UKC_min_m`, `UKC_fwd_m`, `UKC_aft_m`, `Ramp_angle_deg`, `GM_m`, `Gate_FWD`, `Gate_AFT`, `Gate_TRIM`, `Gate_UKC`, `Gate_RAMP`, `HoldPoint_Band`, `Go/No-Go`, `Ballast_Action`, `Ballast_Time_h`, `Ballast_Net_t`, `Ballast_Alloc`, `Notes`
  - `01_SSOT_Master`: `Control / Input`, `Value`, `Unit`, `Notes`, `Owner`, `Source/Ref`
  - `02_Vessel_Hydro`: `#`, `Disp_t`, `Tmean_m`, `TPC_t/cm`, `MTC_t·m/cm`, `LCF_m`, `GM_m`, `Source/Remark`
  - `03_Berth_Tide`: `Field`, `Value`, `Unit`, `Notes`, `Source`
  - `04_Cargo_SPMT`: `Item`, `Weight_t`, `CoG_x_m`, `CoG_y_m`, `CoG_z_m`, `Final_Frame`, `Ramp_Frame`, `L_m`, `W_m`, `Remarks/Source`
  - `05_Ballast_Tanks`: Multi-section structure
  - `06_Stage_Plan`: `Stage_ID`, `Progress_%`, `Planned_Start`, `Planned_End`, `HoldPoint`, `GateB_Critical(Y/N)`, `Stage_Status`, `Remarks`
  - `08_HoldPoint_Log`: Row 2 header (12 columns)
  - `09_Evidence_Log`: `Site`, `Category`, `Document / Evidence Item`, `Req`, `Status`, `Due/Submitted`, `Portal`, `Ref No.`, `File/Link`, `Remarks`
  - `10_RACI`: `Activity / Deliverable`, `SCT Logistics`, `DSV/3PL`, `Vessel Master`, `Chief Officer/Ballast`, `Port Authority`, `HSE`, `Notes`
  - `11_Assumptions_Issues`: `ID`, `Type`, `Description`, `Value`, `Unit`, `Impact`, `Owner`, `Due`, `Status`, `Evidence/Ref`
  - `12_DataDictionary`: `Sheet`, `Field`, `Unit`, `Type`, `Definition / Rule`

#### Post-processing: Excel Consolidation and Finalization

- **Execution files**:
  - `tide/excel_com_recalc_save.py` (optional, COM recalculation)
  - `tide/ballast_excel_finalize.py` (auto-execute)
- **Output file**: `PIPELINE_CONSOLIDATED_AGI_*.xlsx`
- **Generated headers**:
  - Base CSV headers + 28 extension columns (Draft/Freeboard/Gate related)
  - Version differences: 14 sheets (213110) vs 29 sheets (205824/213758)

### 2.17.2 Header Extension Pattern

**Consolidated Excel extension columns (28)**:

1. `Draft_FWD_m_solver`
2. `Draft_AFT_m_solver`
3. `Draft_Source`
4. `Forecast_tide_m`
5. `DepthRef_m`
6. `UKC_min_m`
7. `UKC_fwd_m`
8. `UKC_aft_m`
9. `Tide_required_m`
10. `Tide_margin_m`
11. `Tide_verdict`
12. `Freeboard_Min_m`
13. `Freeboard_Min_BowStern_m`
14. `Freeboard_FWD_m`
15. `Freeboard_AFT_m`
16. `Gate_AFT_MIN_2p70_PASS`
17. `AFT_Margin_2p70_m`
18. `Gate_B_Applies`
19. `Gate_FWD_MAX_2p70_critical_only`
20. `FWD_Margin_2p70_m`
21. `Gate_Freeboard_ND`
22. `Freeboard_Req_ND_m`
23. `Freeboard_ND_Margin_m`
24. `D_vessel_m`
25. `Draft_Max_raw_m`
26. `Draft_Max_solver_m`
27. `Draft_Clipped_raw`
28. `Draft_Clipped_solver`

**Extension pattern application targets**:

- `BALLAST_EXEC.csv` (17) → `Sequence_Ballast_Exec` (45)
- `BALLAST_OPTION.csv` (7) → `Sequence_Ballast_Option` (35)
- `BALLAST_SEQUENCE.csv` (19) → `Sequence_Ballast_Sequence` (47)
- `TIDE_BY_STAGE` base (9) → Extended (35)
- `OPS Stage_Calculations` (37) → Consolidated (56-58)
- `Optimizer Plan` (7) → Consolidated (27-35)
- `Optimizer Summary` (8) → Consolidated (28-36)

### 2.17.3 SSOT Data Flow (Execution File Perspective)

```
Step 1b (stage_results.csv)
  → Step 2 (OPS report)
  → Step 3 (Solver input: stage_table_unified.csv)
  → Step 4 (Optimizer input)
  → Step 4b (Sequence Generator input)
  → Step 5 (Bryan Template input)
  → Consolidated Excel (final integration)
```

**SSOT hierarchy:**

1. **Stage definition SSOT**: `stage_results.csv` (Step 1b)
2. **Tank SSOT**: `tank_ssot_for_solver.csv` (Pipeline generated)
3. **Hydro SSOT**: `hydro_ssot_for_solver.csv` (Pipeline generated)
4. **Stage Table SSOT**: `stage_table_unified.csv` (Pipeline generated, includes Tide/UKC)

**Note**: Details: See section 8 of `00_System_Architecture_Complete.md` for detailed execution file list.

---

## 2.18 Next Chapter Guide

- **Chapter 3**: Pipeline Execution Flow - Step-by-step execution order and subprocess management
- **Chapter 4**: LP Solver Logic - Linear programming mathematical model
- **Chapter 5**: Definition-Split and Gates - Concept and implementation details
- **GM Verification**: `verify_gm_stability_v2b.py` - CLAMP detection, FSM verification, GM_eff calculation
- **Pipeline execution file list**: Section 8 of `00_System_Architecture_Complete.md` - Complete execution file list and mapping

---

**References:**

- Chapter 1: Pipeline Architecture Overview
- `Ballast Pipeline 운영 가이드.MD`: Sensor data integration and profile system details
- `integrated_pipeline_defsplit_v2.py`: Conversion function implementation
- `verify_gm_stability_v2b.py`: GM verification script
- `tide_stage_mapper.py`: Tide stage mapping (AGI-only)
- `spmt_unified.py`: SPMT unified entrypoint
- `03_DOCUMENTATION/AGENTS.md`: Coordinate system, Gate definitions, Tank Direction SSOT
- `03_DOCUMENTATION/Pipeline Integration.md`: SPMT/Tide integration details
- `00_System_Architecture_Complete.md`: Complete pipeline execution file list (section 8)
- 2025-12-16 document: Definition-Split requirements

**Document Version:** v3.7 (Execution file → Output file → Header mapping added)
**Last Updated:** 2025-12-29

```

This translation maintains:
- Technical terms and code blocks unchanged
- Structure and formatting
- Mathematical formulas
- Code examples and implementations
- Version numbers and dates
- References and cross-references

The document is ready for use in English.
```

**Version:**

 v3.7 (Updated: 2025-12-29)
**Purpose:** Understanding the data conversion process from JSON to CSV and SSOT architecture
