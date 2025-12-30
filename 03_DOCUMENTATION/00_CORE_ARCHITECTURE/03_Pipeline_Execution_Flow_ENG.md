Chapter 3: Pipeline Execution Flow

*Date:*2025-12-20
**Version:** v3.5 (Updated: 2025-12-29)
**Purpose:** Understanding the Step-by-Step execution order, subprocess management, and error handling of the pipeline

**Latest Update (v3.5 - 2025-12-29):**

- Forecast_Tide_m priority change: CLI `--forecast_tide` value takes highest priority
  - Tide Integration priority redefined (Priority 0: CLI value)
  - Ensures consistency between `stage_table_unified.csv` and `solver_ballast_summary.csv`
  - For details, refer to `17_TIDE_UKC_Calculation_Logic.md` section 17.6.5

**Latest Update (v3.4 - 2025-12-27):**

- Added `tide/tide_ukc_engine.py` SSOT engine documentation
- Added mention of tide_ukc_engine.py to Step 5c
- Added stage_schedule and tide_ukc_engine.py to Tide Integration section

**Previous Update (v3.3 - 2025-12-27):**

- Added Pre-Step: Tide Stage Mapping (AGI-only)
- Step 1b: Added stage_tide_AGI.csv merge logic
- Step 3: Enhanced UKC calculation (Tide-dependent), Tide_required_m, Tide_margin_m, Tide_verdict calculation
- Step 5: Added Bryan Template Generation (includes SPMT cargo)
- Consolidated Excel: Automatic TIDE_BY_STAGE sheet generation
- AUTO-HOLD Warnings: Automatic warnings for holdpoint stages

**Latest Update (v3.2 - 2025-12-27):**

- AGENTS.md SSOT integration (coordinate system constants, Gate definitions)
- Clarified coordinate system constants (Frame↔x conversion, sign rules)
- Clarified Gate definitions (Gate-A: AFT_MIN_2p70, Gate-B: FWD_MAX_2p70_critical_only)

**Latest Update (v3.1 - 2025-12-27):**

- Current_t auto-detection feature (automatic detection of current_t_*.csv pattern)
- diff_audit.csv generation (sensor injection history recording)

**Latest Update (v2.2 - 2024-12-23):**

- Added `stage_results.csv` SSOT reading logic when generating Step 1 Excel
- Detailed explanation of Draft clipping mechanism
- Excel/CSV consistency guarantee process

---

## 3.1 Overall Execution Flow Overview

### 3.1.1 Execution Step Order

START
  │
  ▼
[Site Profile Loading] (AGI JSON profile)
  │
  ▼
[I/O Optimization Setup] (PR-01)
  │
  ├─→ Run ID generation (site_timestamp)
  ├─→ Manifest directory creation (manifests/<run_id>/)
  └─→ Environment variables injection (PIPELINE_RUN_ID, PIPELINE_MANIFEST_DIR)
  │
  ▼
[Pre-Step: Tide Stage Mapping] (AGI-only, optional)
  │
  ├─→ tide_table Excel (water tide_202512.xlsx)
  ├─→ tide_windows JSON (tide_windows_AGI.json)
  └─→ tide_stage_mapper.py → stage_tide_AGI.csv
  │
  ▼
[Step 1] TR Excel Generation (optional)
  │
  ▼
[Step 1b] stage_results.csv generation (TR script CSV mode)
  │
  ├─→ Merges stage_tide_AGI.csv (if available)
  ├─→ Adds Forecast_Tide_m, DatumOffset_m columns
  └─→ [PR-04] write_parquet_sidecar() → stage_results.parquet creation
  │
  ▼
[PREP] SSOT CSV conversion (Tank, Hydro, Stage)
  │
  ├─→ [PR-02] 1-pass encoding/delimiter detection
  ├─→ [PR-03] Fast CSV reading (Polars lazy → pandas fallback)
  ├─→ [PR-05] read_table_any() usage (Parquet priority, CSV fallback)
  └─→ [PR-01] Manifest logging (all I/O operations)
  │
  ├─→ [Current_t Sensor Injection] (auto-detection: current_t_*.csv)
  │   └─→ diff_audit.csv generation
  │
  ├─→ [Tank Overrides Application] (from profile)
  │
  └─→ [Stage Table with Tide data] (includes Forecast_tide_m)
  │
  ▼
[Gate FAIL Report Generation] (automatic)
  │
  ├─→ AUTO-HOLD warnings (holdpoint stages)
  └─→ Tide_margin_m < 0.10 warning
  │
  ▼
[Step 2] OPS Integrated Report (Excel + Markdown)
  │
  ├─→ [PR-05] read_table_any() usage (stage_results.parquet priority)
  └─→ [PR-01] Manifest logging
  │
  ▼
[Step 3] Ballast Gate Solver (LP optimization)
  │
  ├─→ UKC calculation (tide-dependent)
  ├─→ Tide_required_m (inverse UKC)
  ├─→ Tide_margin_m, Tide_verdict
  └─→ pipeline_stage_QA.csv (includes tide columns)
  │
  ▼
[Step 4] Ballast Optimizer (optional)
  │
  ▼
[Step 5] Bryan Template + SPMT Integration
  │
  ├─→ SPMT Integrated Excel (spmt_unified.py)
  ├─→ Bryan Template Generation
  └─→ Consolidated Excel (TIDE_BY_STAGE sheet)
  │
  ▼
END (Summary output)

```

### 3.1.2 Execution Control Options

The pipeline can control execution range using `--from_step` and `--to_step` arguments:

```bash
# Full execution (Step 1~5, default)
python integrated_pipeline_defsplit_v2_gate270_split_v3_auditpatched_autodetect.py --to_step 5

# Execute only Step 1~3 (exclude Optimizer)
python integrated_pipeline_defsplit_v2_gate270_split_v3_auditpatched_autodetect.py --to_step 3

# Execute from Step 2 (skip Step 1, stage_results.csv already exists)
python integrated_pipeline_defsplit_v2_gate270_split_v3_auditpatched_autodetect.py --from_step 2

# With Tide Integration (AGI-only)
python integrated_pipeline_defsplit_v2_gate270_split_v3_auditpatched_autodetect.py \
  --tide_table bplus_inputs/water\ tide_202512.xlsx \
  --tide_windows bplus_inputs/tide_windows_AGI.json \
  --datum_offset 0.0
```

---

## 3.2 Command-Line Argument Processing

### 3.2.1 Path-Related Arguments

| Argument         | Default                               | Description                           |
| ---------------- | ------------------------------------- | ------------------------------------- |
| `--base_dir`   | (script location)                     | Directory containing 4 scripts        |
| `--inputs_dir` | `base_dir`                          | Directory containing input JSON files |
| `--out_dir`    | `base_dir/pipeline_out_<timestamp>` | Output directory                      |

**Path Resolution Order:**

```python
base_dir = (
    Path(args.base_dir).resolve()
    if args.base_dir
    else Path(__file__).parent.resolve()
)
inputs_dir = Path(args.inputs_dir).resolve() if args.inputs_dir else base_dir
out_dir = (
    Path(args.out_dir).resolve()
    if args.out_dir
    else (base_dir / f"pipeline_out_{now_tag()}")
)
```

### 3.2.2 Script Path Arguments

| Argument               | Default                                      | Description   |
| ---------------------- | -------------------------------------------- | ------------- |
| `--tr_script`        | `agi_tr_patched_v6_6_defsplit_v1.py`       | Step 1 script |
| `--ops_script`       | `ops_final_r3_integrated_defs_split_v4.py` | Step 2 script |
| `--solver_script`    | `ballast_gate_solver_v4.py`                | Step 3 script |
| `--optimizer_script` | `Untitled-2_patched_defsplit_v1_1.py`      | Step 4 script |

**Script Path Resolution:**

```python
tr_script = (base_dir / args.tr_script).resolve()
ops_script = (base_dir / args.ops_script).resolve()
solver_script = (base_dir / args.solver_script).resolve()
optimizer_script = (base_dir / args.optimizer_script).resolve()
```

### 3.2.3 Input File Arguments

| Argument            | Default                                                  | Description                              |
| ------------------- | -------------------------------------------------------- | ---------------------------------------- |
| `--tank_catalog`  | `tank_catalog_from_tankmd.json`                        | Tank catalog JSON                        |
| `--hydro`         | `inputs_dir/bplus_inputs/Hydro_Table_Engineering.json` | Hydrostatic Table JSON                   |
| `--stage_results` | `base_dir/stage_results.csv`                           | Stage results CSV (generated in Step 1b) |

### 3.2.4 Gate/Limit Arguments (SSOT - Based on AGENTS.md)

| Argument             | Default | Description                                                     |
| -------------------- | ------- | --------------------------------------------------------------- |
| `--fwd_max`        | 2.70    | FWD maximum Draft gate (m, Gate-B: Mammoet, Critical RoRo only) |
| `--aft_min`        | 2.70    | AFT minimum Draft gate (m, Gate-A: Captain, all Stages)         |
| `--aft_max`        | 3.50    | AFT maximum Draft limit (m, for Optimizer)                      |
| `--trim_abs_limit` | 0.50    | Absolute trim limit (m, for Optimizer)                          |

**Gate Labels SSOT (Prevents Ambiguous "2.70m")**:

- **Never use "2.70m" alone**. Always include label:
  - **Gate-A**: `AFT_MIN_2p70` (Captain / Propulsion, all Stages)
  - **Gate-B**: `FWD_MAX_2p70_critical_only` (Mammoet / Critical RoRo only)

**Gate-B Application Scope**:

- Applied only to Critical stages (`Gate_B_Applies=True`)
- Non-critical stages are marked as `N/A` (prevents false failure)
- Critical stage determination: `DEFAULT_CRITICAL_STAGE_REGEX = r"(preballast.*critical|6a.*critical|stage\s*5.*preballast|stage\s*6a)"`

### 3.2.5 UKC-Related Arguments (Optional)

**Legacy Method (Single Point Tide):**

| Argument            | Default | Description                            |
| ------------------- | ------- | -------------------------------------- |
| `--forecast_tide` | None    | Tide forecast (m, Chart Datum basis)   |
| `--depth_ref`     | None    | Reference depth (m, Chart Datum basis) |
| `--ukc_min`       | None    | Minimum UKC requirement (m)            |
| `--squat`         | 0.0     | Squat allowance (m)                    |
| `--safety_allow`  | 0.0     | Additional safety allowance (m)        |

**Tide Integration Method (AGI-only, Stage-wise Tide):**

| Argument             | Default | Description                                                                              |
| -------------------- | ------- | ---------------------------------------------------------------------------------------- |
| `--tide_table`     | ""      | Tide table Excel path (time-series, e.g.,`bplus_inputs/water tide_202512.xlsx`)        |
| `--tide_windows`   | ""      | Tide windows JSON path (stage time windows, e.g.,`bplus_inputs/tide_windows_AGI.json`) |
| `--stage_tide_csv` | ""      | Precomputed `stage_tide_AGI.csv` path (optional, skips Pre-Step)                       |
| `--datum_offset`   | 0.0     | Datum offset (m) applied to DepthRef for UKC calculation                                 |

**UKC Calculation Activation:**

- **Legacy**: UKC gate activated when `--forecast_tide`, `--depth_ref`, `--ukc_min` are all provided
- **Tide Integration**: Pre-Step execution and Stage-wise tide mapping when `--tide_table` + `--tide_windows` are provided
- If only some are provided, only those parameters are added to Stage Table (gate inactive)

**Tide Integration Priority (v3.5 update, 2025-12-29):**
0. `--forecast_tide` (CLI value, highest priority) → Directly applied to all Stages, takes priority over stage_tide_csv

1. `--stage_tide_csv` (precomputed) → Used only when CLI is not provided, skips Pre-Step
2. `--tide_table` + `--tide_windows` → Used only when CLI is not provided, executes Pre-Step
3. `--forecast_tide` (fallback fillna) → Applied only to missing Stages

**Changes (2025-12-29):**

- CLI `--forecast_tide` value takes highest priority, ensuring consistency between `stage_table_unified.csv` and `solver_ballast_summary.csv`
- For details, refer to `17_TIDE_UKC_Calculation_Logic.md` section 17.6.5

### 3.2.6 Data Conversion Options

| Argument            | Default                  | Description                                           |
| ------------------- | ------------------------ | ----------------------------------------------------- |
| `--pump_rate`     | 100.0                    | Default pump rate (t/h)                               |
| `--tank_keywords` | "BALLAST,VOID,FWB,FW,DB" | Keywords for `use_flag=Y` marking (comma-separated) |

### 3.2.7 Site and Profile-Related Arguments

| Argument           | Default | Description                                                                                                      |
| ------------------ | ------- | ---------------------------------------------------------------------------------------------------------------- |
| `--site`         | "AGI"   | Site label (AGI-only)                                                                                            |
| `--profile_json` | ""      | Site profile JSON path (explicit specification, default: auto-detected from `inputs_dir/profiles/{site}.json`) |

**Profile Priority:**

1. Explicit CLI flag (e.g., `--fwd_max 2.8`)
2. Profile JSON value
3. argparse default value

### 3.2.8 Sensor Data-Related Arguments

| Argument                 | Default    | Description                                                                                         |
| ------------------------ | ---------- | --------------------------------------------------------------------------------------------------- |
| `--current_t_csv`      | ""         | Current_t sensor CSV path (default: auto-detected from `inputs_dir/sensors/current_t_sensor.csv`) |
| `--current_t_strategy` | "override" | Sensor value injection strategy ("override"\|"fill_missing")                                        |

**Sensor CSV Search Order (v3.1 update):**

1. Explicit `--current_t_csv` argument
2. Fixed path candidates:
   - `inputs_dir/current_t_sensor.csv`
   - `inputs_dir/current_t.csv`
   - `inputs_dir/sensors/current_t_sensor.csv`
   - `inputs_dir/sensors/current_t.csv`
   - `inputs_dir/plc/current_t.csv`
   - `inputs_dir/iot/current_t.csv`
3. **Fallback Auto-Detection** (v3.1 new):
   - Search directories: `inputs_dir`, `inputs_dir/sensors`, `base_dir`, `base_dir/sensors`
   - Pattern: `current_t_*.csv`, `current_t-*.csv`
   - Selection criteria: Latest modification time (mtime) priority

### 3.2.9 Execution Control Arguments

| Argument             | Default | Description                           |
| -------------------- | ------- | ------------------------------------- |
| `--from_step`      | 1       | Start step (1~5)                      |
| `--to_step`        | 5       | End step (1~5, default: 5)            |
| `--dry_run`        | False   | Only perform path resolution and exit |
| `--no_gate_report` | False   | Disable Gate FAIL report generation   |

### 3.2.10 P0 Features Arguments (Added 2025-12-25)

| Argument                 | Default | Description                                       |
| ------------------------ | ------- | ------------------------------------------------- |
| `--gate_guard_band_cm` | 2.0     | Gate tolerance (cm) - provides operational margin |

**P0-3: Guard-Band Support**

Guard-Band provides operational tolerance for gate checks:

```
Strict Limit: AFT >= 2.70m
Guard-Band (2.0cm): AFT >= 2.68m → PASS (with warning)
```

**Usage Example:**

```bash
# Production execution (2.0cm tolerance, recommended)
python integrated_pipeline_defsplit_v2_gate270_split_v3.py \
  --site AGI \
  --gate_guard_band_cm 2.0

# Strict mode (for development/verification, no tolerance)
python integrated_pipeline_defsplit_v2_gate270_split_v3.py \
  --site AGI \
  --gate_guard_band_cm 0.0
```

**Effects:**

- ✅ Accounts for sensor measurement errors (±1-2cm)
- ✅ Overcomes LP Solver numerical precision limits (±0.01m)
- ✅ Allows for fluid dynamic variations (sloshing, wave)
- ✅ Improves field execution feasibility

**P0-2: Step-wise Gate-B Handling**

Gate-B (FWD_MAX_2p70_critical_only) is applied **only to Critical RoRo stages**:

- **Critical stages:** Stage 5_PreBallast, Stage 6A_Critical (Opt C)
- **Non-critical stages:** Automatically excluded from Gate-B checks

**QA Output Columns:**

```csv
GateB_FWD_MAX_2p70_CD_applicable  # True=Critical, False=Non-critical
GateB_FWD_MAX_2p70_CD_PASS        # True/False
GateB_FWD_MAX_2p70_CD_Margin_m    # FWD margin (NaN for non-critical)
```

**Gate FAIL Report:**

- `GateB_..._CD` count includes **only Critical stages**
- Non-critical stages are not counted even if they FAIL

**Reference Documents:**

- `docs/16_P0_Guard_Band_and_Step_wise_Gate_B_Guide.md` - Complete guide

---

## 3.3 Dry-Run Mode

### 3.3.1 Purpose

A mode to verify path resolution and file existence before actual execution.

### 3.3.2 Execution Example

```bash
python integrated_pipeline_defsplit_v2.py --dry_run
```

### 3.3.3 Output Format

```
================================================================================
DRY RUN - PATH RESOLUTION
================================================================================
Site:        AGI
Base dir:    C:\...\ballast_pipeline_defsplit_v2_complete
Inputs dir:  C:\...\ballast_pipeline_defsplit_v2_complete
Out dir:     C:\...\ballast_pipeline_defsplit_v2_complete\pipeline_out_20251220_120000

[SCRIPTS]
TR:          C:\...\agi_tr_patched_v6_6_defsplit_v1.py  (OK)
OPS:         C:\...\ops_final_r3_integrated_defs_split_v4.py  (OK)
SOLVER:      C:\...\ballast_gate_solver_v4.py  (OK)
OPTIMIZER:   C:\...\Untitled-2_patched_defsplit_v1_1.py  (OK)

[INPUTS]
Tank catalog: C:\...\tank_catalog_from_tankmd.json  (OK)
Hydro:        C:\...\bplus_inputs\Hydro_Table_Engineering.json  (OK)
StageRes:     C:\...\stage_results.csv  (OK)

[OUTPUT SSOT]
Tank SSOT:   pipeline_out_20251220_120000\ssot\tank_ssot_for_solver.csv
Hydro SSOT:  pipeline_out_20251220_120000\ssot\hydro_table_for_solver.csv
Stage table: pipeline_out_20251220_120000\ssot\stage_table_unified.csv
```

---

## 3.4 Subprocess Execution Mechanism

### 3.4.1 `run_cmd` Function

**Location:** `integrated_pipeline_defsplit_v2.py` (lines 111-138)

**Features:**

- Subprocess execution
- Simultaneous output to log file and console (tee)
- UTF-8 encoding handling (Windows compatible)

**Implementation:**

```python
def run_cmd(
    cmd: List[str], cwd: Path, log_path: Path, env: Optional[Dict[str, str]] = None
) -> int:
    log_path.parent.mkdir(parents=True, exist_ok=True)

    with log_path.open("w", encoding="utf-8", errors="replace") as f:
        f.write(f"[CMD] {' '.join(cmd)}\n")
        f.write(f"[CWD] {cwd}\n\n")
        f.flush()

        p = subprocess.Popen(
            cmd,
            cwd=str(cwd),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,  # Redirect stderr to stdout
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env or os.environ.copy(),
        )
        assert p.stdout is not None
        for line in p.stdout:
            sys.stdout.write(line)  # Console output
            f.write(line)           # Log file recording
        return p.wait()  # Return exit code
```

**Characteristics:**

- **Real-time Output**: Subprocess output is immediately recorded to console and log
- **Error Recovery**: `errors="replace"` replaces characters on encoding errors
- **Environment Variables**: Optional `env` parameter allows environment variable override

### 3.4.2 `step_run_script` Function

**Location:** `integrated_pipeline_defsplit_v2.py` (lines 479-496)

**Features:**

- Wrapper function for script execution
- Script existence validation
- Log file path generation
- Returns `StepResult`

**Implementation:**

```python
@dataclass
class StepResult:
    ok: bool           # Execution success status
    returncode: int    # Process return code (0=success)
    log: Path          # Log file path

def step_run_script(
    step_id: int,
    name: str,
    script: Path,
    args: List[str],
    cwd: Path,
    out_dir: Path,
    env: Optional[Dict[str, str]] = None,
) -> StepResult:
    if not script.exists():
        log = out_dir / "logs" / f"{step_id:02d}_{name}_MISSING.log"
        log.write_text(f"Missing script: {script}\n", encoding="utf-8")
        return StepResult(False, 127, log)

    log = out_dir / "logs" / f"{step_id:02d}_{name}.log"
    cmd = [which_python(), str(script)] + args
    rc = run_cmd(cmd, cwd=cwd, log_path=log, env=env)
    return StepResult(rc == 0, rc, log)
```

**Log File Naming Convention:**

- Success: `{step_id:02d}_{name}.log` (e.g., `01_TR_EXCEL.log`)
- Script missing: `{step_id:02d}_{name}_MISSING.log`

---

## 3.5 Step-by-Step Execution Details

### 3.5.1 Step 1: TR Excel Generation

**Condition:** `args.from_step <= 1 <= args.to_step`

**Execution:**

```python
r1 = step_run_script(
    1,
    "TR_EXCEL",
    tr_script,
    args=[],  # No arguments (default execution mode)
    cwd=base_dir,
    out_dir=out_dir,
)
```

**⭐ SSOT Usage When Generating Excel (2024-12-23 update):**

When Step 1 (Excel generation) executes, the `create_roro_sheet()` function first checks `stage_results.csv` and dynamically loads TR positions.

**Execution Flow:**

1. Check if `stage_results.csv` exists
2. If exists → Read each Stage's `x_stage_m` from CSV
3. Convert `x_stage_m` → Frame number: `Fr = 30.151 - x`
4. Create cfg dictionary (dynamic)
5. Generate Excel RORO_Stage_Scenarios sheet

**Code Example (inside create_roro_sheet):**

```python
import csv
from pathlib import Path

stage_results_path = Path("stage_results.csv")
if not stage_results_path.exists():
    # Fallback to default cfg values
    cfg = {"W_TR": 271.20, "FR_TR2_STOW": 29.39, ...}
else:
    print("[INFO] Reading TR positions from stage_results.csv (SSOT)")
    stage_data = {}
    with open(stage_results_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            stage_name = row.get('Stage', '')
            x_m = float(row.get('x_stage_m', 0.0))
            stage_data[stage_name] = {'x': x_m}

    def x_to_fr(x_m: float) -> float:
        return 30.151 - x_m

    cfg = {
        "W_TR": 271.20,
        "FR_TR1_RAMP_START": x_to_fr(stage_data.get('Stage 2', {}).get('x', 4.0)),
        "FR_TR1_STOW": x_to_fr(stage_data.get('Stage 4', {}).get('x', 4.5)),
        "FR_TR2_RAMP": x_to_fr(stage_data.get('Stage 6A_Critical (Opt C)', {}).get('x', 5.11)),
        "FR_TR2_STOW": x_to_fr(stage_data.get('Stage 6C', {}).get('x', 0.76)),
        "FR_PREBALLAST": x_to_fr(stage_data.get('Stage 5_PreBallast', {}).get('x', 4.57)),
    }
    print(f"[INFO] cfg from stage_results.csv: {cfg}")
```

**Log Example:**

```
[INFO] Reading TR positions from stage_results.csv (SSOT)
[INFO] cfg from stage_results.csv: {
    'W_TR': 271.2,
    'FR_TR1_RAMP_START': 26.151,
    'FR_TR1_STOW': 25.651,
    'FR_TR2_RAMP': 25.041,
    'FR_TR2_STOW': 29.391,  # Stage 6C: x=0.76m → Fr=29.391
    'FR_PREBALLAST': 25.581
}
```

**Effects:**

- Excel and CSV use **the same TR position data**
- Stage 6C example: Both Excel/CSV use `x=0.76m` (LCF, even keel)
- Ensures Excel/CSV consistency

**Error Handling:**

- On failure, outputs `[WARN]` message
- Pipeline continues (Excel file is not mandatory)
- Informs user that they can proceed if `stage_results.csv` already exists or Excel is not needed

### 3.5.2 Step 1b: stage_results.csv Generation

**Condition:** `args.from_step <= 1 <= args.to_step` AND `stage_results_path.exists() == False`

**Execution:**

```python
if not stage_results_path.exists():
    r1b = step_run_script(
        2,
        "TR_STAGE_CSV",
        tr_script,
        args=["csv"],  # CSV mode execution
        cwd=base_dir,
        out_dir=out_dir,
    )
```

**Error Handling:**

- On failure, outputs `[ERROR]` message
- **Pipeline stops** (`return 1`) - `stage_results.csv` is a required input

**Validation:**

- If file still doesn't exist after execution, stops with additional error message

### 3.5.3 PREP: SSOT CSV Conversion

**Location:** `integrated_pipeline_defsplit_v2.py` (lines 748-814)

**Order:**

1. **Tank SSOT Conversion**

   ```python
   convert_tank_catalog_json_to_solver_csv(
       tank_catalog_json=tank_catalog,
       out_csv=tank_ssot_csv,
       pump_rate_tph=float(args.pump_rate),
       include_keywords=tank_keywords,
   )
   ```
2. **Current_t Sensor Injection (PLC/IoT) - v3.1 update**

   ```python
   # Resolve sensor CSV path (includes auto-detection)
   resolved_sensor_csv = resolve_current_t_sensor_csv(
       args.current_t_csv, base_dir=base_dir, inputs_dir=inputs_dir
   )
   if resolved_sensor_csv is not None:
       sensor_stats = inject_current_t_from_sensor_csv(
           tank_ssot_csv=tank_ssot_csv,
           sensor_csv=resolved_sensor_csv,
           strategy=str(args.current_t_strategy),  # "override" or "fill_missing"
           out_csv=tank_ssot_csv,
           out_audit_csv=out_dir / "ssot" / "diff_audit.csv",  # v3.1 new
       )
   ```

   - If sensor CSV is provided, automatically injects `Current_t` values into Tank SSOT
   - Strategy: `override` (overwrite all values) or `fill_missing` (inject only if 0.0)
   - **diff_audit.csv generation** (v3.1 new):
     - Pre/post injection value comparison (`CurrentOld_t`, `ComputedNew_t`, `Delta_t`)
     - Clamping status (`ClampedFlag`)
     - Update status (`Updated`)
     - Skip reason (`SkipReason`)
3. **Tank Overrides Application (from profile)**

   ```python
   # Apply profile's tank_overrides to Tank SSOT
   if profile_obj:
       apply_tank_overrides_from_profile(
           tank_ssot_csv=tank_ssot_csv,
           profile=profile_obj,
           out_csv=tank_ssot_csv,
       )
   ```

   - Overrides specific tank's `mode`, `use_flag`, `pump_rate_tph`, etc. from profile's `tank_overrides` section
   - Example: Fix `VOID3` as `FIXED/Y`, block `FWCARGO*` as `FIXED/N`
4. **Hydro SSOT Conversion**

   ```python
   convert_hydro_engineering_json_to_solver_csv(
       hydro_json=hydro_path,
       out_csv=hydro_ssot_csv,
       lbp_m=LPP_M,
   )
   ```
5. **Stage Table Construction**

   ```python
   build_stage_table_from_stage_results(
       stage_results_csv=stage_results_path,
       out_csv=stage_table_csv,
       fwd_max_m=float(args.fwd_max),
       aft_min_m=float(args.aft_min),
       ...
   )
   ```
6. **Stage QA CSV Generation**

   ```python
   generate_stage_QA_csv(
       stage_table_csv=stage_table_csv,
       out_qa_csv=stage_qa_csv,
       ...
   )
   ```
7. **Gate FAIL Report Generation (automatic)**

   ```python
   if not args.no_gate_report:
       generate_gate_fail_report_md(
           out_md=gate_report_md,
           site=str(args.site),
           profile_path=resolved_profile_path,
           stage_qa_csv=stage_qa_csv,
           tank_ssot_csv=tank_ssot_csv,
           sensor_stats=sensor_stats,
           ukc_inputs=ukc_inputs,
       )
   ```

   - Automatically generates Gate violation cause analysis report based on `pipeline_stage_QA.csv`
   - Includes Current_t status, sensor synchronization results, UKC input status, etc.
   - **v2.1+**: Includes 2.70m Split Gates (Gate-A: Captain, Gate-B: Mammoet)
     - `GateA_AFT_MIN_2p70_PASS`: Applied to all Stages
     - `GateB_FWD_MAX_2p70_CD_PASS`: Applied only to Critical stages

**Error Handling:**

- Missing input files: Stops with `[ERROR]` message
- Sensor injection failure: Outputs `[WARN]` message and continues
- Tank Overrides failure: Outputs `[WARN]` message and continues
- Conversion function internal errors propagate as exceptions and stop pipeline

### 3.5.4 Step 2: OPS Integrated Report

**Condition:** `args.from_step <= 2 <= args.to_step`

**Execution:**

```python
r2 = step_run_script(
    3,
    "OPS_INTEGRATED",
    ops_script,
    args=[],  # No arguments
    cwd=base_dir,
    out_dir=out_dir,
)
```

**Output File Collection:**

```python
expected_ops = [
    base_dir / "OPS_FINAL_R3_AGI_Ballast_Integrated.xlsx",
    base_dir / "OPS_FINAL_R3_Report_Integrated.md",
]
for p in expected_ops:
    if p.exists():
        shutil.copy2(p, out_dir / p.name)
        print(f"[OK] Collected output -> {out_dir / p.name}")
```

**Error Handling:**

- On failure, stops pipeline with `[ERROR]` message (`return 1`)

### 3.5.5 Step 3: Ballast Gate Solver (LP)

**Condition:** `args.from_step <= 3 <= args.to_step`

**Command-Line Argument Construction:**

```python
solver_args = [
    "--tank", str(tank_ssot_csv),
    "--hydro", str(hydro_ssot_csv),
    "--mode", "limit",
    "--stage", str(stage_table_csv),
    "--iterate_hydro", "2",
    "--out_plan", str(solver_out_plan),
    "--out_summary", str(solver_out_sum),
    "--out_stage_plan", str(solver_out_stage_plan),
    "--fwd_max", str(args.fwd_max),
    "--aft_min", str(args.aft_min),
    "--d_vessel", str(D_VESSEL_M),
    "--fb_min", "0.0",
    "--squat", str(args.squat),
    "--safety_allow", str(args.safety_allow),
]
# Add optional UKC parameters
if args.forecast_tide is not None:
    solver_args += ["--forecast_tide", str(args.forecast_tide)]
if args.depth_ref is not None:
    solver_args += ["--depth_ref", str(args.depth_ref)]
if args.ukc_min is not None:
    solver_args += ["--ukc_min", str(args.ukc_min)]
```

**Execution:**

```python
r3 = step_run_script(
    4,
    "SOLVER_LP",
    solver_script,
    args=solver_args,
    cwd=base_dir,
    out_dir=out_dir,
)
```

**Error Handling:**

- On failure, stops pipeline with `[ERROR]` message

### 3.5.6 Step 4: Ballast Optimizer

**Condition:** `args.from_step <= 4 <= args.to_step`

**Command-Line Argument Construction:**

```python
opt_args = [
    "--batch",
    "--tank", str(tank_ssot_csv),
    "--hydro", str(hydro_ssot_csv),
    "--stage", str(stage_table_csv),
    "--prefer_time",
    "--iterate_hydro", "2",
    "--out_plan", str(opt_out_plan),
    "--out_summary", str(opt_out_sum),
    "--bwrb_out", str(opt_out_bwrb),
    "--tanklog_out", str(opt_out_tanklog),
    "--excel_out", str(opt_excel),
]
```

**Execution:**

```python
r4 = step_run_script(
    5,
    "OPTIMIZER",
    optimizer_script,
    args=opt_args,
    cwd=base_dir,
    out_dir=out_dir,
)
```

**Note:**

- Optimizer uses `AFT_Limit_m` as **upper limit (MAX)** (not lower limit)
- Captain gate (AFT ≥ 2.70m) is enforced in Step 3 Solver

**Error Handling:**

- On failure, stops pipeline with `[ERROR]` message

### 3.5.7 Step 5: SPMT Integration & Bryan Template Generation

**Condition:** `args.from_step <= 5 <= args.to_step` (default: `--to_step 5`)

#### 3.5.7.1 Step 5a: SPMT Integrated Excel

**Purpose:** Generate and integrate SPMT cargo input workbook

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
  - `00_Cover`: Workbook overview
  - `Stage_Config`: SSOT parameters
  - `Cargo_SPMT_Inputs`: Cargo data
  - `Submission_Stagewise`: Stage-wise submission
  - `Stage_Results`: SSOT-mapped stage results
  - `Stage-wise Cargo on Deck`: Bryan format

**Execution Condition:**

- Automatically executes when `spmt_config` file exists
- Executes without `--ssot` if `stage_results.csv` is missing

**Error Handling:**

- If `spmt_config` is missing, outputs `[WARN]` message and skips Step 5a
- If `stage_results.csv` is missing, outputs `[WARN]` message and executes without `--ssot`

#### 3.5.7.2 Step 5b: Bryan Template Generation

**Purpose:** Generate Bryan submission data pack (includes SPMT cargo)

**Input:**

- `SPMT_Integrated_Complete.xlsx` (from Step 5a)
- `stage_results.csv` (SSOT)

**Processing:**

- Execute `bryan_template_unified.py one-click`
  - `create` → `Bryan_Submission_Data_Pack_Template.xlsx`
  - `populate` → Uses `stage_results.csv`
  - `--spmt-xlsx` → Imports SPMT cargo into `04_Cargo_SPMT` sheet

**Output:**

- `Bryan_Submission_Data_Pack_Template.xlsx`
- `Bryan_Submission_Data_Pack_Populated.xlsx`
  - `04_Cargo_SPMT`: SPMT cargo data
  - `07_Stage_Calc`: Stage calculations
  - `06_Stage_Plan`: Stage-wise cargo positions

**Error Handling:**

- If `SPMT_Integrated_Complete.xlsx` is missing, automatically executes Step 5a then retries
- On failure, outputs `[WARN]` message and skips Step 5b

#### 3.5.7.3 Step 5c: Consolidated Excel

**Purpose:** Consolidate all pipeline outputs into a single Excel file

**Input:**

- Step 2~4 output files
- `pipeline_stage_QA.csv` (includes tide columns, uses `tide_ukc_engine.py`)
- `SPMT_Integrated_Complete.xlsx` (optional)
- `Bryan_Submission_Data_Pack_Populated.xlsx` (optional)

**Processing:**

- Execute `ballast_excel_consolidator.py`
  - Merge all Excel files
  - Generate `TIDE_BY_STAGE` sheet (from `pipeline_stage_QA.csv`)
  - UKC calculations from `tide_ukc_engine.py` (SSOT)

**Output:**

- `PIPELINE_CONSOLIDATED_AGI_<timestamp>.xlsx`
  - `TIDE_BY_STAGE`: Stage-wise tide & UKC summary (based on `tide_ukc_engine.py`)
  - `Stage_QA`: Pipeline stage QA (includes tide columns)
  - `Solver_Plan`: Step 3 solver output
  - `Optimizer_Plan`: Step 4 optimizer output (if available)
  - `SPMT_Integrated`: SPMT data (if available)
  - `Bryan_Submission`: Bryan template (if available)

**TIDE_BY_STAGE Sheet Columns:**

- `Stage`, `Forecast_tide_m`, `Tide_required_m`, `Tide_margin_m`
- `UKC_min_m`, `UKC_fwd_m`, `UKC_aft_m`, `Tide_verdict`
- (All calculated using `tide/tide_ukc_engine.py` SSOT engine)

**Error Handling:**

- If some Excel files are missing, outputs `[WARN]` message and continues
- If `TIDE_BY_STAGE` sheet generation fails, outputs `[WARN]` message and continues

---

## 3.6 Error Handling Strategy

### 3.6.1 Error Level Classification

1. **WARNING (Warning)**

   - Step 1 failure: Excel generation failure is treated as warning, pipeline continues
   - Reason: Excel file is optional output, `stage_results.csv` is more important
2. **ERROR (Error, Pipeline Stops)**

   - Required input file missing
   - Step 1b failure (`stage_results.csv` generation failure)
   - SSOT conversion failure
   - Step 2, 3, 4 failure
   - Step 5b failure (Bryan template generation failure, WARNING if SPMT is missing)

### 3.6.2 Error Message Format

```
[WARN] Step-1 failed (rc=1). Log: pipeline_out_.../logs/01_TR_EXCEL.log
       You can still proceed if you already have stage_results.csv or do not need the Excel.

[ERROR] Step-1b failed and stage_results.csv not found. rc=1
        Log: pipeline_out_.../logs/02_TR_STAGE_CSV.log
```

### 3.6.3 Log File Usage

Each Step's log file includes:

- Execution command (`[CMD]`)
- Working directory (`[CWD]`)
- Complete stdout/stderr output from subprocess

**Log File Location:**

```
pipeline_out_<timestamp>/
└── logs/
    ├── 01_TR_EXCEL.log
    ├── 02_TR_STAGE_CSV.log
    ├── 03_OPS_INTEGRATED.log
    ├── 04_SOLVER_LP.log
    └── 05_OPTIMIZER.log
```

---

## 3.7 Output File Management

### 3.7.1 Output Directory Structure

```
pipeline_out_<timestamp>/
├── ssot/                              # SSOT CSV files
│   ├── tank_ssot_for_solver.csv
│   ├── hydro_table_for_solver.csv
│   ├── stage_table_unified.csv
│   ├── pipeline_stage_QA.csv
│   └── diff_audit.csv                 # Current_t injection history (v3.1)
│
├── logs/                              # Execution logs
│   ├── 01_TR_EXCEL.log
│   ├── 02_TR_STAGE_CSV.log
│   ├── 03_OPS_INTEGRATED.log
│   ├── 04_SOLVER_LP.log
│   ├── 05_OPTIMIZER.log
│   ├── 05a_SPMT_INTEGRATE.log
│   ├── 05b_BRYAN_TEMPLATE.log
│   └── 05c_EXCEL_CONSOLIDATE.log
│
├── gate_fail_report.md               # Gate FAIL automatic report (generated after PREP)
│
├── solver_ballast_plan.csv           # Step 3 output
├── solver_ballast_summary.csv
├── solver_ballast_stage_plan.csv
│
├── OPS_FINAL_R3_AGI_Ballast_Integrated.xlsx  # Step 2 output
├── OPS_FINAL_R3_Report_Integrated.md
│
├── optimizer_plan.csv                # Step 4 output
├── optimizer_summary.csv
├── optimizer_bwrb_log.csv
├── optimizer_tank_log.csv
├── optimizer_ballast_plan.xlsx
│
├── SPMT_Integrated_Complete.xlsx     # Step 5a output
├── Bryan_Submission_Data_Pack_Template.xlsx  # Step 5b output
├── Bryan_Submission_Data_Pack_Populated.xlsx
│
├── stage_tide_AGI.csv                 # Pre-Step output (AGI-only)
└── PIPELINE_CONSOLIDATED_AGI_*.xlsx  # Step 5c output (includes TIDE_BY_STAGE)
```

### 3.7.2 File Collection Mechanism

**Step 2 Output Collection:**

- Step 2 script creates files in working directory (`base_dir`)
- Pipeline copies to output directory (`out_dir`)

**Step 3, 4 Output:**

- Output paths specified via command-line arguments (`--out_plan`, `--out_summary`, etc.)
- Created directly in `out_dir`

### 3.7.3 Completion Summary

On pipeline completion, outputs the following information:

```
================================================================================
PIPELINE COMPLETE
================================================================================
Out dir: pipeline_out_20251220_120000
Key SSOT outputs:
 - tank_ssot_for_solver.csv
 - hydro_table_for_solver.csv
 - stage_table_unified.csv
 - pipeline_stage_QA.csv (definition-split QA)
Key reports:
 - gate_fail_report.md (Gate FAIL cause analysis report)
```

---

## 3.8 Step 6: Excel Formula Preservation (COM Post-Processing)

### 3.8.1 Purpose

Ensures **formula dependency integrity** of Excel files modified by openpyxl. Since openpyxl is not a calculation engine, the file is reopened via Excel COM and CalculateFullRebuild is executed to reconstruct the dependency graph.

### 3.8.2 Execution Condition

**Automatic Execution:**

- When merged_excel is successfully created in Step 5
- When `ballast_excel_finalize.py` script exists
- Windows environment + Excel installed + pywin32 installed

**Execution Location:**

```python
# integrated_pipeline_defsplit_v2_gate270_split_v3.py
# Line 4511-4549 (just before return 0)
```

### 3.8.3 Processing Steps

```
1. Excel COM initialization
   ↓
2. File reopen (merged_excel)
   ↓
3. Calculation = Automatic setting
   ↓
4. RefreshAll() execution (external data)
   ↓
5. CalculateFullRebuild() execution (dependency reconstruction)
   ↓
6. QueryTables & PivotCaches update
   ↓
7. Calc_Log sheet recording (audit trail)
   ↓
8. Save and close
```

### 3.8.4 Calc_Log Sheet (Auto-Generated)

**Location:** Last sheet in Excel file

**Content:**

| Parameter             | Value      | Timestamp           |
| --------------------- | ---------- | ------------------- |
| FullRebuild_Completed | SUCCESS    | 2025-12-25 00:24:11 |
| Engine                | Python+COM | 2025-12-25 00:24:11 |
| ProcessingTime_sec    | 11.15      | 2025-12-25 00:24:11 |
| QueryTables_Count     | 0          | 2025-12-25 00:24:11 |
| PivotCaches_Count     | 0          | 2025-12-25 00:24:11 |

### 3.8.5 Console Output

```
================================================================================
[FORMULA FINALIZE] Running COM post-processing...
================================================================================
[STEP 1/7] Initializing Excel COM...
[STEP 2/7] Opening workbook...
[STEP 3/7] Setting Calculation=Automatic...
[STEP 4/7] RefreshAll()...
[STEP 5/7] CalculateFullRebuild()...
[STEP 6/7] Checking QueryTables & PivotCaches...
[STEP 7/7] Recording build log (Calc_Log sheet)...

================================================================================
✅ SUCCESS - Formula finalization completed!
================================================================================
[OK] Formula finalization completed successfully
  [RESULT] Processing time: 11.15 sec
  [RESULT] File: PIPELINE_CONSOLIDATED_AGI_20251225_002354.xlsx
  [RESULT] Timestamp: 2025-12-25 00:24:11
```

### 3.8.6 Error Handling

**Non-Critical Processing:**

- Even if COM post-processing fails, pipeline completes normally (Exit code: 0)
- Outputs warning message and continues

**Timeout Setting:**

- Default: 120 seconds
- On timeout: Outputs warning and skips

**Fallback:**

```bash
# Manual execution
python ballast_excel_finalize.py --auto
```

### 3.8.7 Verification Method

**Pre-Deployment Check:**

1. **Calc_Log Sheet Verification**

   - Open Excel file
   - Verify Calc_Log sheet exists
   - Verify FullRebuild_Completed = SUCCESS
   - Check recent timestamp
2. **Formula Integrity Verification**

   - RORO_Stage_Scenarios sheet
   - BC18:BR28 range data exists
   - Verify Stage 6A AFT = 2.70m
   - Ctrl+F → Search for `#N/A`, `#REF!`, `#VALUE!` (0 occurrences)
3. **Console Log Verification**

   - `[FORMULA FINALIZE]` section output
   - `SUCCESS` message
   - `[RESULT]` line output

### 3.8.8 Performance

| File Size | Formula Count | Processing Time | Status          |
| --------- | ------------- | --------------- | --------------- |
| < 5 MB    | < 1,000       | < 5 sec         | ✅ Excellent    |
| 5-10 MB   | 1,000-5,000   | 5-15 sec        | ✅ Good         |
| 10-50 MB  | 5,000-10,000  | 15-60 sec       | ⚠️ Acceptable |
| > 50 MB   | > 10,000      | > 60 sec        | ❌ Review       |

**Current Project:** 121 KB, 7,887 formulas → **~11 sec** ✅

### 3.8.9 Requirements

**Required:**

- Windows OS
- Microsoft Excel installed
- Python 3.8+
- `pip install pywin32`

**Optional:**

- pywin32 post-install: `python -m pywin32_postinstall -install`

### 3.8.10 Reference Documents

- Script: `ballast_excel_finalize.py`
- Guide: `docs/EXCEL_FORMULA_PRESERVATION.md`
- Patch Information: `docs/10_System_Improvements_and_Patches.md` (Patch v3.7)

---

## 3.9 Execution Environment Requirements

### 3.9.1 Python Environment

- Python 3.7 or higher
- Uses currently running Python interpreter (`sys.executable`)
- Supports Windows/Linux/macOS

### 3.9.2 Required Input Files

| File                              | Location                     | Description                                 |
| --------------------------------- | ---------------------------- | ------------------------------------------- |
| `tank_catalog_from_tankmd.json` | `inputs_dir`               | Tank catalog                                |
| `Hydro_Table_Engineering.json`  | `inputs_dir/bplus_inputs/` | Hydrostatic Table                           |
| `stage_results.csv`             | `base_dir`                 | Stage results (can be generated in Step 1b) |

### 3.9.3 Optional Input Files

**Profile and Sensor Data:**

- `profiles/AGI.json`: Site profile (gate values, pump rates, UKC parameters, etc.)
- `sensors/current_t_sensor.csv`: Current_t sensor data (PLC/IoT)

**Tide Integration (AGI-only, optional):**

- `bplus_inputs/water tide_202512.xlsx`: Time-series tide data (Excel)
- `bplus_inputs/tide_windows_AGI.json`: Stage time windows (JSON)
- `bplus_inputs/stage_schedule.csv`: Stage schedule with tide (fallback, Option B Hybrid)
- `tide/tide_ukc_engine.py`: SSOT engine for Tide/UKC calculations (3-tier fallback)

**SPMT Integration (optional):**

- `spmt/cargo_spmt_inputs_config_example.json`: SPMT config (JSON)

**Step 1, 2 Related:**
Additional JSON files used in Step 1, 2 (GM_Min_Curve.json, Acceptance_Criteria.json, etc.) may be required depending on each script's requirements.

---

## 3.10 Next Chapter Guide

- **Chapter 4**: LP Solver Logic - Linear Programming mathematical model and optimization algorithm
- **Chapter 5**: Definition-Split and Gates - Concepts and implementation details
- **Chapter 6**: Script Interfaces and API - Command-line arguments and interfaces for each script

---

**References:**

- Chapter 1: Pipeline Architecture Overview
- Chapter 2: Data Flow and SSOT
- `Ballast Pipeline 운영 가이드.MD`: Detailed latest features including profile system, sensor data integration, Gate FAIL report, etc.
- `integrated_pipeline_defsplit_v2.py`: Main pipeline implementation
- `03_DOCUMENTATION/AGENTS.md`: Coordinate system, Gate definitions, Tank Direction SSOT

**Document Version:** v3.5 (Forecast_Tide_m priority change)
**Last Update:** 2025-12-29
