Chapter 6: Script Interfaces and API

**Date:** 2025-12-20
**Version:** v2.4 (Updated: 2025-12-28)
**Purpose:** Understanding command-line interfaces, input/output formats, and data flow of each script

**Latest Update (v2.4 - 2025-12-28):**
- Option 2 implementation: Step 4b Ballast Sequence Generator interface expansion
  - Separate output of `BALLAST_OPTION.csv` / `BALLAST_EXEC.csv`
  - `generate_sequence_with_carryforward()`: Start_t/Target_t carry-forward implementation
  - Added `exclude_optional_stages` parameter (Stage 6B separation)

**Latest Update (v2.3 - 2025-12-28):**
- Added I/O optimization module interfaces (section 6.6)
  - `perf_manifest.py`: Manifest logging API
  - `io_detect.py`: Encoding/delimiter detection API
  - `io_csv_fast.py`: Fast CSV reading API
  - `io_parquet_cache.py`: Parquet cache API (`read_table_any()`, `write_parquet_sidecar()`)
- Added MAMMOET Calculation Sheet Generator interface (section 6.7)

**Latest Update (v2.2 - 2024-12-23):**
- Step 1 script cfg structure change (2024-12-23 patch)
- SSOT-based operation of `create_roro_sheet()` function
- Excel/CSV consistency guarantee mechanism

---

## 6.1 Overview

This chapter details the interfaces of **4 core scripts** that make up the pipeline:

1. **Step 1**: TR Excel Generator (`agi_tr_patched_v6_6_defsplit_v1.py`)
2. **Step 2**: OPS Integrated Report (`ops_final_r3_integrated_defs_split_v4.py`)
3. **Step 3**: Ballast Gate Solver (`ballast_gate_solver_v4.py`)
4. **Step 4**: Ballast Optimizer (`Untitled-2_patched_defsplit_v1_1.py`)

---

## 6.2 Step 1: TR Excel Generator

### 6.2.1 Script Information

**Filename:** `agi_tr_patched_v6_6_defsplit_v1.py`

**Role:**
- Generate Technical Report (TR) Excel file
- Generate stage-wise calculation results
- Generate `stage_results.csv` in CSV mode

### 6.2.2 Execution Modes

#### Basic Execution (Excel Generation)

```bash
python agi_tr_patched_v6_6_defsplit_v1.py
```

**Operation:**
- Read all input JSON files and generate TR Excel file
- Output: `LCT_BUSHRA_AGI_TR_Final_v6_2.xlsx`

#### CSV Mode (Stage Results Generation)

```bash
python agi_tr_patched_v6_6_defsplit_v1.py csv
```

**Operation:**
- Output stage-wise Draft results as CSV
- Output: `stage_results.csv`

### 6.2.3 Input Files

The following files must be in the working directory:

| File | Description |
|------|-------------|
| `Hydro_Table_Engineering.json` | Hydrostatic Table (usually in `bplus_inputs/` directory) |
| `GM_Min_Curve.json` | GM minimum curve |
| `Acceptance_Criteria.json` | Acceptance criteria |
| `Structural_Limits.json` | Structural limits |
| `Securing_Input.json` | Securing input |
| `bplus_inputs/data/GZ_Curve_Stage_*.json` | Stage-wise GZ curves (10 files) |

### 6.2.4 Output Files

**Excel mode:**
- `LCT_BUSHRA_AGI_TR_Final_v6_2.xlsx`: Technical Report Excel file

**CSV mode:**
- `stage_results.csv`: Stage-wise Draft results
  - Columns: `Stage`, `Dfwd_m`, `Daft_m`, other metadata

### 6.2.5 cfg Structure Change (2024-12-23 Patch)

**Changes:**
- Removed duplicate cfg at Line 4070
- Updated cfg at Line 7494 based on latest `stage_results.csv`
- Modified `create_roro_sheet()` function to dynamically read `stage_results.csv`

**Before change (duplicate cfg problem):**
```python
# Line 4070: Old version cfg (inside create_roro_sheet)
cfg = {
    "W_TR": 271.20,
    "FR_TR1_RAMP_START": 40.15,  # ❌ Old version
    "FR_TR1_STOW": 42.0,          # ❌ Old version
    "FR_TR2_RAMP": 17.95,         # ❌ Old version (x=12.20m)
    "FR_TR2_STOW": 40.00,         # ❌ Old version
    "FR_PREBALLAST": 3.0,         # ❌ Old version
}

# Line 7494: New version cfg (inside export_stages_to_csv)
cfg = {
    "W_TR": 271.20,
    "FR_TR1_RAMP_START": 40.15,  # ❌ Still old version
    "FR_TR1_STOW": 42.0,
    "FR_TR2_RAMP": 17.95,
    "FR_TR2_STOW": 40.00,
    "FR_PREBALLAST": 3.0,
}
```
- **Problem:** Excel and CSV could use different cfg
- **Result:** Stage 6C TR position mismatch (x=-9.50m vs x=0.76m)

**After change (SSOT unified):**

**1. create_roro_sheet() - Dynamic reading of stage_results.csv:**
```python
# Line 4068-4112 (replaces old version cfg)
import csv
from pathlib import Path

stage_results_path = Path("stage_results.csv")
if not stage_results_path.exists():
    # Fallback to default values
    cfg = {
        "W_TR": 271.20,
        "FR_TR2_STOW": 29.39,  # Latest value
    }
else:
    print("[INFO] Reading TR positions from stage_results.csv (SSOT)")
    stage_data = {}
    with open(stage_results_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            stage_name = row.get('Stage', '')
            x_stage_m = float(row.get('x_stage_m', 0.0))
            stage_data[stage_name] = {'x': x_stage_m}

    def x_to_fr(x_m: float) -> float:
        """Convert x position (m from midship) to Frame number"""
        return 30.151 - x_m

    cfg = {
        "W_TR": 271.20,
        "FR_TR1_RAMP_START": x_to_fr(stage_data.get('Stage 2', {}).get('x', 4.0)),
        "FR_TR1_RAMP_MID": x_to_fr(stage_data.get('Stage 3', {}).get('x', 4.0)),
        "FR_TR1_STOW": x_to_fr(stage_data.get('Stage 4', {}).get('x', 4.5)),
        "FR_TR2_RAMP": x_to_fr(stage_data.get('Stage 6A_Critical (Opt C)', {}).get('x', 5.11)),
        "FR_TR2_STOW": x_to_fr(stage_data.get('Stage 6C', {}).get('x', 0.76)),
        "FR_PREBALLAST": x_to_fr(stage_data.get('Stage 5_PreBallast', {}).get('x', 4.57)),
    }
    print(f"[INFO] cfg from stage_results.csv: {cfg}")
```

**2. export_stages_to_csv() - cfg value update:**
```python
# Line 7494-7506 (based on stage_results.csv)
cfg = {
    "W_TR": 271.20,
    # TR1 positions (Frame) - ✅ Based on stage_results.csv
    "FR_TR1_RAMP_START": 26.15,  # Stage 2: x=+4.0m → Fr=30.151-4.0≈26.15
    "FR_TR1_RAMP_MID": 26.15,    # Stage 3: x=+4.0m (same)
    "FR_TR1_STOW": 25.65,         # Stage 4/5: x=+4.5m → Fr=30.151-4.5≈25.65
    # TR2 positions (Frame) - ✅ Based on stage_results.csv
    "FR_TR2_RAMP": 25.04,         # Stage 6A: x=+5.11m → Fr=30.151-5.11≈25.04
    "FR_TR2_STOW": 29.39,         # Stage 6C: x=+0.76m (LCF, even keel) → Fr=30.151-0.76≈29.39
    # Pre-ballast center (FW2, AFT side) - ✅ Based on stage_results.csv
    "FR_PREBALLAST": 25.58,       # Stage 5_PreBallast: x=+4.57m → Fr=30.151-4.57≈25.58
}
```

**Effect:**
- Excel and CSV use **the same** `stage_results.csv` data
- Stage 6C example: Both Excel/CSV use `FR_TR2_STOW=29.39` (x=0.76m)
- Excel/CSV consistency fully guaranteed

**Verification log:**
```
[INFO] Reading TR positions from stage_results.csv (SSOT)
[INFO] cfg from stage_results.csv: {
    'W_TR': 271.2,
    'FR_TR1_RAMP_START': 26.151,
    'FR_TR1_RAMP_MID': 26.151,
    'FR_TR1_STOW': 25.651,
    'FR_TR2_RAMP': 25.041,
    'FR_TR2_STOW': 29.391,  # ✅ Stage 6C: x=0.76m
    'FR_PREBALLAST': 25.581
}
```

### 6.2.6 Pipeline Integration

In the pipeline, it is executed as follows:

```python
# Step 1: Excel generation (optional)
step_run_script(1, "TR_EXCEL", tr_script, args=[], ...)

# Step 1b: CSV generation (when stage_results.csv doesn't exist)
step_run_script(2, "TR_STAGE_CSV", tr_script, args=["csv"], ...)
```

---

## 6.3 Step 2: OPS Integrated Report

### 6.3.1 Script Information

**Filename:** `ops_final_r3_integrated_defs_split_v4.py`

**Role:**
- Generate integrated report for operational stages (Excel + Markdown)
- Integrate and analyze Tank catalog and Stage results
- Engineering-grade calculations (Hydro table interpolation, GM 2D bilinear)

### 6.3.2 Execution Method

```bash
python ops_final_r3_integrated_defs_split_v4.py
```

**Command-line arguments:** None (all inputs read from working directory)

### 6.3.3 Input Files

| File | Description |
|------|-------------|
| `tank_catalog_from_tankmd.json` | Tank catalog |
| `stage_results.csv` | Stage results (generated from Step 1) |
| `Hydro_Table_Engineering.json` | Hydrostatic Table |

### 6.3.4 Output Files

| File | Description |
|------|-------------|
| `OPS_FINAL_R3_AGI_Ballast_Integrated.xlsx` | Operational report Excel |
| `OPS_FINAL_R3_Report_Integrated.md` | Operational report Markdown |

### 6.3.5 Key Features

- Engineering-grade stage calculations (hydro table interpolation)
- GM 2D bilinear interpolation
- Frame-based coordinate system
- VOID3 ballast analysis
- Discharge-only strategy

### 6.3.6 Pipeline Integration

```python
step_run_script(3, "OPS_INTEGRATED", ops_script, args=[], ...)

# Collect output files
expected_ops = [
    base_dir / "OPS_FINAL_R3_AGI_Ballast_Integrated.xlsx",
    base_dir / "OPS_FINAL_R3_Report_Integrated.md",
]
for p in expected_ops:
    if p.exists():
        shutil.copy2(p, out_dir / p.name)
```

---

## 6.4 Step 3: Ballast Gate Solver (LP)

### 6.4.1 Script Information

**Filename:** `ballast_gate_solver_v4.py`

**Role:**
- Linear Programming-based Ballast plan optimization
- Definition-Split + Gate Unified System implementation
- Supports two modes: `limit` (constraints) vs `target` (target values)

### 6.4.2 Execution Method

#### Basic Execution (Limit Mode)

```bash
python ballast_gate_solver_v4.py \
  --tank tank_ssot_for_solver.csv \
  --hydro hydro_table_for_solver.csv \
  --mode limit \
  --stage stage_table_unified.csv \
  --iterate_hydro 2 \
  --fwd_max 2.70 \
  --aft_min 2.70 \
  --d_vessel 3.65 \
  --fb_min 0.0 \
  --out_plan solver_ballast_plan.csv \
  --out_summary solver_ballast_summary.csv \
  --out_stage_plan solver_ballast_stage_plan.csv
```

#### Target Mode

```bash
python ballast_gate_solver_v4.py \
  --tank tank_ssot_for_solver.csv \
  --hydro hydro_table_for_solver.csv \
  --mode target \
  --target_fwd 2.70 \
  --target_aft 2.70 \
  --iterate_hydro 2 \
  --out_plan solver_ballast_plan.csv \
  --out_summary solver_ballast_summary.csv
```

### 6.4.3 Command-Line Arguments

#### Required Arguments

| Argument | Description | Example |
|----------|-------------|---------|
| `--tank` | Tank SSOT CSV path | `tank_ssot_for_solver.csv` |
| `--hydro` | Hydro Table CSV path | `hydro_table_for_solver.csv` |
| `--mode` | Execution mode | `limit` or `target` |

#### Single Case Input (when Stage mode not used)

| Argument | Type | Description |
|----------|------|-------------|
| `--current_fwd` | float | Current Forward Draft (m) |
| `--current_aft` | float | Current Aft Draft (m) |

#### Target Mode Arguments

| Argument | Type | Description |
|----------|------|-------------|
| `--target_fwd` | float | Target Forward Draft (m) |
| `--target_aft` | float | Target Aft Draft (m) |

#### Gate Arguments (Limit Mode)

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--fwd_max` | float | None | FWD maximum Draft gate (m) |
| `--aft_min` | float | None | AFT minimum Draft gate (m) |
| `--d_vessel` | float | None | Hull depth (m, for Freeboard calculation) |
| `--fb_min` | float | None | Minimum Freeboard (m) |

#### UKC-Related Arguments (Optional)

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--forecast_tide` | float | None | Forecast tide (m, Chart Datum) |
| `--depth_ref` | float | None | Reference depth (m, Chart Datum) |
| `--ukc_min` | float | None | Minimum UKC requirement (m) |
| `--ukc_ref` | string | "MAX" | UKC calculation reference ("FWD"\|"AFT"\|"MEAN"\|"MAX") |
| `--squat` | float | 0.0 | Squat allowance (m) |
| `--safety_allow` | float | 0.0 | Additional safety allowance (m) |

#### Optimization Options

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--iterate_hydro` | int | 2 | Hydrostatic Table iterative interpolation count |
| `--prefer_tons` | flag | False | Weight minimization priority (default: time minimization) |

#### Penalty Parameters

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--violation_penalty` | float | 1e7 | Gate violation Penalty (Limit Mode) |
| `--slack_weight_penalty` | float | 1e6 | Weight Slack Penalty (Target Mode) |
| `--slack_moment_penalty` | float | 1e3 | Moment Slack Penalty (Target Mode) |

#### Stage Mode Arguments

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--stage` | string | "" | Stage Table CSV path (stage-wise processing if provided) |
| `--out_plan` | string | "ballast_plan_out.csv" | Ballast Plan output path |
| `--out_summary` | string | "ballast_summary_out.csv" | Summary output path |
| `--out_stage_plan` | string | "ballast_stage_plan_out.csv" | Stage-wise Plan output path |

### 6.4.4 Input File Formats

#### Tank SSOT CSV

See Chapter 2. Key columns:
- `Tank`, `x_from_mid_m`, `Current_t`, `Min_t`, `Max_t`, `mode`, `use_flag`, `pump_rate_tph`, `priority_weight`

#### Hydro Table SSOT CSV

See Chapter 2. Key columns:
- `Tmean_m`, `TPC_t_per_cm`, `MTC_t_m_per_cm`, `LCF_m`, `LBP_m`

#### Stage Table CSV

See Chapter 2. Key columns:
- `Stage`, `Current_FWD_m`, `Current_AFT_m`, `FWD_MAX_m`, `AFT_MIN_m`, other gate parameters

### 6.4.5 Output File Formats

#### Ballast Plan CSV

| Column | Description | Example |
|--------|-------------|---------|
| `Tank` | Tank identifier | "FWB2" |
| `Action` | "Fill" or "Discharge" | "Discharge" |
| `Delta_t` | Net weight change (tons) | -25.50 |
| `PumpTime_h` | Pumping time (hours) | 0.26 |

#### Summary CSV

**Limit Mode:**
- `FWD_new_m`, `AFT_new_m`, `Trim_new_m`, `Tmean_new_m`, `ΔW_t`
- `viol_fwd_max_m`, `viol_aft_min_m`, `viol_fb_min_m`, `viol_ukc_min_m`

**Target Mode:**
- `FWD_new_m`, `AFT_new_m`, `Trim_new_m`, `Tmean_new_m`, `ΔW_t`

### 6.4.6 Pipeline Integration

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

step_run_script(4, "SOLVER_LP", solver_script, args=solver_args, ...)
```

---

## 6.5 Step 4: Ballast Optimizer

### 6.5.1 Script Information

**Filename:** `Untitled-2_patched_defsplit_v1_1.py`

**Role:**
- Optimization combining operational heuristics and LP
- Batch mode processing for multiple stages
- Excel output provided

### 6.5.2 Execution Method

```bash
python Untitled-2_patched_defsplit_v1_1.py \
  --batch \
  --tank tank_ssot_for_solver.csv \
  --hydro hydro_table_for_solver.csv \
  --stage stage_table_unified.csv \
  --prefer_time \
  --iterate_hydro 2 \
  --out_plan optimizer_plan.csv \
  --out_summary optimizer_summary.csv \
  --bwrb_out optimizer_bwrb_log.csv \
  --tanklog_out optimizer_tank_log.csv \
  --excel_out optimizer_ballast_plan.xlsx
```

### 6.5.3 Command-Line Arguments

#### Mode Switch

| Argument | Description |
|----------|-------------|
| `--batch` | Batch mode execution (required if arguments provided) |

#### Input Files

| Argument | Description |
|----------|-------------|
| `--tank` | Tank SSOT CSV path |
| `--hydro` | Hydro Table CSV path |
| `--stage` | Stage Table CSV path |

#### Draft Input (Single Case Mode)

| Argument | Type | Description |
|----------|------|-------------|
| `--current_fwd` | float | Current Forward Draft (m) |
| `--current_aft` | float | Current Aft Draft (m) |
| `--target_fwd` | float | Target Forward Draft (m) |
| `--target_aft` | float | Target Aft Draft (m) |

#### Limits

| Argument | Type | Description |
|----------|------|-------------|
| `--fwd_limit` | float | FWD upper limit (m) |
| `--aft_limit` | float | AFT upper limit (m) |
| `--trim_limit` | float | Absolute trim limit (m) |

**Note:** Optimizer uses `AFT_Limit` as **upper limit (MAX)**. If AFT minimum gate is needed, use Step 3 Solver.

#### Optimization Options

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--prefer_time` | flag | False | Pumping time minimization priority |
| `--prefer_tons` | flag | False | Weight change minimization priority |
| `--iterate_hydro` | int | 2 | Hydrostatic Table iterative interpolation count |

#### Output Files

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--out_plan` | string | "" | Ballast Plan CSV (optional) |
| `--out_summary` | string | "" | Summary CSV (optional) |
| `--out_stage_plan` | string | "" | Stage-wise Plan CSV (optional) |
| `--bwrb_out` | string | "" | BWRB log CSV (optional) |
| `--tanklog_out` | string | "" | Tank log CSV (optional) |
| `--excel_out` | string | "" | Excel output (default output format) |

### 6.5.4 Input/Output File Formats

Input file formats are the same as Step 3 (Tank SSOT, Hydro SSOT, Stage Table).

Output format is Excel-centered, with optional CSV also available.

### 6.5.5 Pipeline Integration

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

step_run_script(5, "OPTIMIZER", optimizer_script, args=opt_args, ...)
```

---

## 6.6 Data Flow Diagram

```
┌─────────────────────────────────────────────────────────┐
│  INPUT LAYER (JSON)                                      │
├─────────────────────────────────────────────────────────┤
│  tank_catalog_from_tankmd.json                         │
│  Hydro_Table_Engineering.json                          │
│  GM_Min_Curve.json, Acceptance_Criteria.json, etc.     │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│  Step 1: TR Excel Generator                             │
├─────────────────────────────────────────────────────────┤
│  Input: JSON files                                     │
│  Output: LCT_BUSHRA_AGI_TR_Final_v6_2.xlsx            │
│          stage_results.csv (CSV mode)                  │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│  Pipeline: SSOT Conversion                              │
├─────────────────────────────────────────────────────────┤
│  - convert_tank_catalog_json_to_solver_csv()           │
│  - convert_hydro_engineering_json_to_solver_csv()      │
│  - build_stage_table_from_stage_results()              │
│  - generate_stage_QA_csv()                             │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│  SSOT CSV Files                                         │
├─────────────────────────────────────────────────────────┤
│  tank_ssot_for_solver.csv                              │
│  hydro_table_for_solver.csv                            │
│  stage_table_unified.csv                               │
│  pipeline_stage_QA.csv                                 │
└──────────────────────┬──────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┬──────────────┐
        ▼              ▼              ▼              ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  Step 2:     │  │  Step 3:     │  │  Step 4:     │
│  OPS Report  │  │  LP Solver   │  │  Optimizer   │
├──────────────┤  ├──────────────┤  ├──────────────┤
│  Input:      │  │  Input:      │  │  Input:      │
│  - tank_*    │  │  - tank_ssot │  │  - tank_ssot │
│  - stage_*   │  │  - hydro_ssot│  │  - hydro_ssot│
│              │  │  - stage_*   │  │  - stage_*   │
│  Output:     │  │              │  │              │
│  - OPS_*.xlsx│  │  Output:     │  │  Output:     │
│  - OPS_*.md  │  │  - solver_*  │  │  - optimizer_│
│              │  │    .csv      │  │    .xlsx     │
└──────────────┘  └──────────────┘  └──────────────┘
```

---

## 6.7 Common Parameters and Constants

### 6.7.1 Vessel Constants

Constants used consistently throughout the pipeline:

| Constant | Value | Description |
|----------|-------|-------------|
| `LPP_M` | 60.302 m | Length Between Perpendiculars |
| `MIDSHIP_FROM_AP_M` | 30.151 m | Midship position (from AP) |
| `D_VESSEL_M` | 3.65 m | Molded Depth (for Freeboard calculation) |

### 6.7.2 Default Gate Values

| Parameter | Default | Description |
|-----------|---------|-------------|
| `FWD_MAX_m` | 2.70 m | FWD maximum Draft (Port/Ramp gate) |
| `AFT_MIN_m` | 2.70 m | AFT minimum Draft (Captain gate) |
| `AFT_MAX_m` | 3.50 m | AFT maximum Draft (Optimizer upper limit) |
| `Trim_Abs_Limit_m` | 0.50 m | Absolute trim limit (Optimizer) |
| `UKC_MIN_m` | 0.50 m | Minimum UKC (project default) |

### 6.7.3 Default Optimization Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `iterate_hydro` | 2 | Hydrostatic Table iterative interpolation count |
| `pump_rate_tph` | 100.0 | Default pump rate (t/h) |
| `prefer_time` | False | Time minimization priority (default: weight minimization) |

---

## 6.8 Standalone Script Execution Guide

### 6.8.1 Run Step 3 Solver Only

```bash
# Prepare SSOT CSV (generate from pipeline or create manually)
python integrated_pipeline_defsplit_v2.py --to_step 0  # Generate SSOT only

# Run Solver
python ballast_gate_solver_v4.py \
  --tank ssot/tank_ssot_for_solver.csv \
  --hydro ssot/hydro_table_for_solver.csv \
  --mode limit \
  --stage ssot/stage_table_unified.csv \
  --fwd_max 2.70 \
  --aft_min 2.70 \
  --d_vessel 3.65 \
  --out_plan my_plan.csv \
  --out_summary my_summary.csv
```

### 6.8.2 Run Step 4 Optimizer Only

```bash
python Untitled-2_patched_defsplit_v1_1.py \
  --batch \
  --tank ssot/tank_ssot_for_solver.csv \
  --hydro ssot/hydro_table_for_solver.csv \
  --stage ssot/stage_table_unified.csv \
  --prefer_time \
  --excel_out my_optimizer.xlsx
```

---

## 6.9 Error Handling and Validation

### 6.9.1 Input File Validation

Each script validates the following before execution:

1. **File existence check**
2. **Required column/field existence check**
3. **Data type and range validation**

### 6.9.2 Error Messages

- File missing: `FileNotFoundError` or clear error message
- Column missing: `ValueError` with missing columns list
- Data type error: `TypeError` or conversion error

### 6.9.3 Debugging Tips

1. **Use Dry-Run mode**: Check path resolution with pipeline's `--dry_run` option
2. **Check log files**: Review log files for each Step (`pipeline_out_.../logs/`)
3. **Validate SSOT CSV**: Directly check intermediate SSOT CSV files to verify data conversion accuracy

---

## 6.10 Next Steps

Through this document series, you should understand:

- Overall pipeline architecture (Chapter 1)
- Data conversion and SSOT concepts (Chapter 2)
- Execution flow and error handling (Chapter 3)
- LP Solver mathematical model (Chapter 4)
- Definition-Split and Gates (Chapter 5)
- Script interfaces (Chapter 6)

**Additional Learning Resources:**
- Source code comments for each script
- `README.md`: Quick start guide
- `requirements.txt`: Python package dependencies

---

## 6.11 I/O Optimization Modules (PR-01~05)

### 6.11.1 perf_manifest.py (PR-01)

**Role:** Subprocess-safe JSONL manifest logging

**API:**
```python
from perf_manifest import get_manifest_path, log_io

# Get manifest file path
manifest_path = get_manifest_path()
# Returns: Path("manifests/<run_id>/<step>_<pid>.jsonl")

# Log I/O operation
log_io(
    operation="read",  # "read" | "write"
    file_path="stage_results.csv",
    file_type="csv",  # "csv" | "parquet" | "json" | "xlsx"
    size_bytes=10752,
    engine="pyarrow",  # "polars_lazy" | "pyarrow" | "pandas_c" | "pandas_python"
    cache_key="hit",  # "hit" | "miss" | None
    duration_ms=15.2
)
```

**Environment variables:**
- `PIPELINE_RUN_ID`: Run ID (e.g., "AGI_20251228_004405")
- `PIPELINE_MANIFEST_DIR`: Manifest directory path
- `PIPELINE_STEP`: Current step name (e.g., "OPS_INTEGRATED")
- `PIPELINE_BASE_DIR`: Base directory path

**Output format (JSONL):**
```json
{"timestamp": "2025-12-28T00:44:11", "operation": "read", "file_path": "stage_results.csv", "file_type": "csv", "size_bytes": 10752, "engine": "pyarrow", "cache_key": "hit", "duration_ms": 15.2}
```

### 6.11.2 io_detect.py (PR-02)

**Role:** 1-pass encoding/delimiter detection

**API:**
```python
from io_detect import detect_encoding, guess_delimiter

# Encoding detection
encoding, confidence = detect_encoding("stage_results.csv")
# Returns: ("utf-8-sig", 0.99) or ("cp949", 0.95)

# Delimiter inference
delimiter = guess_delimiter("stage_results.csv", encoding="utf-8")
# Returns: "," | ";" | "\t" | "|"
```

### 6.11.3 io_csv_fast.py (PR-03)

**Role:** Fast CSV reading with Polars lazy evaluation

**API:**
```python
from io_csv_fast import read_csv_fast

# Fast CSV reading (Polars lazy → pandas fallback)
df = read_csv_fast(
    "stage_results.csv",
    columns=["Stage", "FWD_m", "AFT_m"],  # Optional: projection pushdown
    encoding="utf-8",
    sep=","
)
# Returns: pandas.DataFrame
```

**Fallback order:**
1. Polars lazy scan (projection pushdown)
2. pandas pyarrow engine
3. pandas c engine
4. pandas python engine

### 6.11.4 io_parquet_cache.py (PR-04, PR-05)

**Role:** Parquet sidecar cache and unified read API

**API:**
```python
from io_parquet_cache import write_parquet_sidecar, read_table_any

# Create Parquet sidecar cache
parquet_path = write_parquet_sidecar(Path("stage_results.csv"))
# Returns: Path("stage_results.parquet")
# Side effect: Manifest logging

# Unified read API (Parquet priority, CSV fallback)
df = read_table_any(
    Path("stage_results.csv"),  # or Path("stage_results.parquet")
    columns=["Stage", "FWD_m"],  # Optional: projection pushdown
    encoding="utf-8"
)
# Returns: pandas.DataFrame
# Side effect: Manifest logging (cache hit/miss)
```

**Cache validation:**
- Compare mtime of CSV and Parquet
- If Parquet is older, ignore and read CSV
- If Parquet is newer, load Parquet with priority

**Integration points:**
- Orchestrator: Call `write_parquet_sidecar()` right after Step 1b
- OPS: `df_stage_ssot = read_table_any(stage_results_path)`
- StageExcel: `df = read_table_any(stage_results_path)`

## 6.12 MAMMOET Calculation Sheet Generator

### 6.12.1 Script Information

**Filename:** `create_mammoet_calculation_sheet.py`

**Role:**
- Automatically generate MAMMOET-style technical calculation sheet
- Word document format (.docx)

### 6.12.2 API

```python
from create_mammoet_calculation_sheet import create_mammoet_calculation_sheet
from pathlib import Path
from datetime import datetime

# Project data
project_data = {
    "client": "SAMSUNG C&T",
    "project": "HVDC POWER TRANSFORMER (Al Ghallan)",
    "subject": "Stowage & Sea-Fastening Calcs",
    "project_number": "15111578",
    "document_number": "C15",
    "sap_number": "4000244577",
}

# Preparation information
prep_data = {
    "prepared": "Your Name",
    "checked": "Reviewer Name",
    "date": datetime.now().strftime("%d-%m-%Y"),
    "revision": "00",
}

# Motion criteria
motion_data = {
    "roll_angle": 5.00,
    "roll_period": 10.00,
    "pitch_angle": 2.50,
    "pitch_period": 10.00,
    "heave": 0.10,
}

# Forces data
forces_data = {
    "weight": 217,  # t
    "transverse_dist": 0,  # mm
    "vertical_dist": 5762,  # mm
    "longitudinal_dist": 14160,  # mm
}

# Signature information (optional)
signature_data = {
    "prepared_by": "_________________",
    "prepared_name": "Your Name",
    "prepared_date": "28-12-2025",
    "checked_by": "_________________",
    "checked_name": "Reviewer Name",
    "checked_date": "28-12-2025",
}

# Generate document
create_mammoet_calculation_sheet(
    output_path=Path("MAMMOET_Calculation_Sheet.docx"),
    project_data=project_data,
    prep_data=prep_data,
    introduction_text="The following sea going characteristics...",
    motion_data=motion_data,
    forces_data=forces_data,
    signature_data=signature_data,
    company_name="MAMMOET",  # Optional
    title="STOWAGE & SEA-FASTENING CALCULATION"  # Optional
)
```

### 6.12.3 Output Format

**Word document structure:**
1. Header: Company name (red, left) + "Calculation Sheet" (gray, right)
2. Title: Center-aligned, bold
3. Project information table (2 columns):
   - Left: CLIENT, PROJECT, SUBJECT, PROJECT NUMBER, DOCUMENT NUMBER, SAP NUMBER
   - Right: PREPARED, CHECKED, DATE, REVISION
4. Sections:
   - INTRODUCTION
   - MOTION CRITERIA (Roll/Pitch angles and periods, Heave)
   - FORCES EX-SHIPS MOTION (Weight, CoF to CoG distances)
   - ILLUSTRATION (PLAN VIEW, END ELEVATION placeholders)
5. Signature section (new page):
   - Prepared by / Checked by / Approved by

### 6.12.4 Dependencies

```bash
pip install python-docx
```

---

## 6.13 Step 4b: Ballast Sequence Generator (Option 2)

### 6.13.1 Script Information

**Filename:** `ballast_sequence_generator.py`

**Role:**
- Convert Ballast plan to execution sequence
- Option 2 implementation: option/execution separation, Start_t/Target_t carry-forward

### 6.13.2 Execution Method

```python
from ballast_sequence_generator import (
    generate_sequence,
    generate_optional_sequence,
    export_to_option_dataframe,
    export_to_exec_dataframe,
)

# Generate option plan (includes all Stages)
option_df = export_to_option_dataframe(
    ballast_plan_df,
    profile,
    stage_drafts,
    tank_catalog_df
)

# Generate execution sequence (Stage 6B excluded, Start_t/Target_t carry-forward)
exec_sequence = generate_sequence(
    ballast_plan_df,
    profile,
    stage_drafts,
    tank_catalog_df,
    exclude_optional_stages=True  # Exclude Stage 6B
)
exec_df = export_to_exec_dataframe(exec_sequence)
```

### 6.13.3 Key Functions

#### `generate_sequence()`

**Signature:**
```python
def generate_sequence(
    ballast_plan_df: pd.DataFrame,
    profile,
    stage_drafts: Dict[str, Dict[str, float]],
    tank_catalog_df: Optional[pd.DataFrame] = None,
    exclude_optional_stages: bool = True,  # Option 2: Exclude Stage 6B
) -> List[BallastStep]:
```

**Core logic (Option 2):**
- **Start_t/Target_t carry-forward**: Automatically pass previous step's `target_t` → next step's `start_t`
- **Stage 6B separation**: Excluded from execution sequence when `exclude_optional_stages=True`
- **Tank capacity validation**: Clipping if `target_t > Capacity_t`

#### `export_to_option_dataframe()`

**Output format:**
- `BALLAST_OPTION.csv`: Planning level (Delta_t centered, includes all Stages)
- Columns: `Stage`, `Tank`, `Action`, `Delta_t`, `PumpRate`, `Priority`, `Rationale`

#### `export_to_exec_dataframe()`

**Output format:**
- `BALLAST_EXEC.csv`: Execution sequence (Start_t/Target_t chain, Stage 6B excluded)
- Columns: `Stage`, `Step`, `Tank`, `Action`, `Start_t`, `Target_t`, `Time_h`, `Valve_Lineup`, `Hold_Point`

### 6.13.4 Pipeline Integration

```python
# Execute Step 4b (Option 2)
if args.enable_sequence:
    from ballast_sequence_generator import (
        generate_sequence,
        export_to_option_dataframe,
        export_to_exec_dataframe,
    )

    # Generate option plan
    option_df = export_to_option_dataframe(...)
    option_df.to_csv(out_dir / "BALLAST_OPTION.csv", index=False)

    # Generate execution sequence (Stage 6B excluded)
    exec_sequence = generate_sequence(
        ...,
        exclude_optional_stages=True
    )
    exec_df = export_to_exec_dataframe(exec_sequence)
    exec_df.to_csv(out_dir / "BALLAST_EXEC.csv", index=False)
```

### 6.13.5 Option 1 Patch Proposal (Not Implemented)

**Inject Forecast_tide_m into Bryan Pack:**
- Add `--qa-csv` option to `populate_template.py`
- Merge `Forecast_tide_m` from `pipeline_stage_QA.csv` into `Bryan_Submission_Data_Pack_Populated.xlsx`

---

**References:**
- Chapter 1: Pipeline Architecture Overview
- Chapter 2: Data Flow and SSOT
- Chapter 3: Pipeline Execution Flow
- Chapter 4: LP Solver Logic
- Chapter 5: Definition-Split and Gates
- Source code of each script
```

This translation maintains:
- Technical terms and code blocks unchanged
- Structure and formatting
- Code examples and implementations
- Version numbers and dates
- References and cross-references

The document is ready for use in English.
