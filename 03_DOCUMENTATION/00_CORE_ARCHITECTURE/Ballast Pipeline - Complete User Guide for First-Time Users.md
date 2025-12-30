# Ballast Pipeline - Complete User Guide for First-Time Users

**Version**: v1.1
**Last Updated**: 2025-12-30
**Target Audience**: First-time users, operators, engineers
**Purpose**: Complete step-by-step guide for using the Ballast Pipeline system

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [System Requirements](#2-system-requirements)
3. [Installation Guide](#3-installation-guide)
4. [First-Time Setup](#4-first-time-setup)
5. [Quick Start Guide](#5-quick-start-guide)
6. [Step-by-Step Tutorial](#6-step-by-step-tutorial)
7. [Understanding Output Files](#7-understanding-output-files)
8. [Common Use Cases](#8-common-use-cases)
9. [Troubleshooting Guide](#9-troubleshooting-guide)
10. [Advanced Features](#10-advanced-features)
11. [FAQ](#11-faq)

---

## 1. Introduction

### 1.1 What is the Ballast Pipeline?

The Ballast Pipeline is an integrated automation system for **Ballast Management** operations on the LCT BUSHRA vessel. It automates and optimizes:

- **Stage-wise Draft/Trim/GM calculations** (Engineering-grade accuracy)
- **Gate compliance verification** (AFT_MIN, FWD_MAX, Freeboard, UKC)
- **Ballast Plan optimization** (Linear Programming + Heuristic algorithms)
- **Operational document generation** (Sequence, Checklist, Valve Lineup)

### 1.2 Key Features

- ✅ **Automated Workflow**: Single command runs entire pipeline
- ✅ **Engineering-Grade Calculations**: Hydrostatic table interpolation, GM 2D interpolation
- ✅ **Gate Compliance**: Automatic verification of all operational limits
- ✅ **Site-Agnostic**: Works for AGI/DAS sites (profile-based configuration)
- ✅ **SSOT (Single Source of Truth)**: Consistent data across all steps
- ✅ **Comprehensive Reports**: Excel + Markdown outputs

### 1.3 What You Will Learn

By the end of this guide, you will be able to:
- Install and configure the pipeline
- Run a complete ballast analysis
- Understand and interpret output files
- Troubleshoot common issues
- Use advanced features

---

## 2. System Requirements

### 2.1 Software Requirements

| Component | Version | Notes |
|-----------|---------|-------|
| **Python** | 3.8 or higher | Required |
| **Operating System** | Windows 10/11, Linux, macOS | Tested on Windows 10/11 |
| **Excel** | Microsoft Excel 2016+ | For Excel output files (optional) |

### 2.2 Python Packages

The following packages are required (will be installed automatically):

```
pandas >= 1.3.0
numpy >= 1.20.0
openpyxl >= 3.0.0
scipy >= 1.7.0
```

### 2.3 Hardware Requirements

- **RAM**: Minimum 4GB (8GB recommended)
- **Storage**: 500MB free space for installation
- **CPU**: Any modern processor (multi-core recommended for faster processing)

### 2.4 Required Input Files

Before running the pipeline, ensure you have:

1. **Tank Catalog**: `tank_catalog_from_tankmd.json`
2. **Hydrostatic Table**: `Hydro_Table_Engineering.json`
3. **Site Profile**: `profiles/AGI.json` (or site-specific profile)
4. **Stage Results** (optional): `stage_results.csv` (can be generated)

---

## 3. Installation Guide

### 3.1 Step 1: Verify Python Installation

Open a terminal/command prompt and check Python version:

```bash
python --version
```

**Expected output**: `Python 3.8.x` or higher

If Python is not installed:
- **Windows**: Download from [python.org](https://www.python.org/downloads/)
- **Linux**: `sudo apt-get install python3 python3-pip` (Ubuntu/Debian)
- **macOS**: `brew install python3` (with Homebrew)

### 3.2 Step 2: Navigate to Project Directory

```bash
cd "C:\AGI RORO TR"
```

Or on Linux/macOS:
```bash
cd /path/to/AGI\ RORO\ TR
```

### 3.3 Step 3: Install Required Packages

```bash
pip install pandas numpy openpyxl scipy
```

Or install from requirements file (if available):
```bash
pip install -r requirements.txt
```

### 3.4 Step 4: Verify Installation

Test that all packages are installed correctly:

```bash
python -c "import pandas, numpy, openpyxl, scipy; print('All packages installed successfully!')"
```

**Expected output**: `All packages installed successfully!`

### 3.5 Step 5: Verify Pipeline Script Exists

Check that the main pipeline script exists:

```bash
# Windows
dir "01_EXECUTION_FILES\tide\integrated_pipeline_defsplit_v2_gate270_split_v3_auditpatched_autodetect_TIDE_v1.py"

# Linux/macOS
ls "01_EXECUTION_FILES/tide/integrated_pipeline_defsplit_v2_gate270_split_v3_auditpatched_autodetect_TIDE_v1.py"
```

---

## 4. First-Time Setup

### 4.1 Understanding the Project Structure

```
AGI RORO TR/
├── 01_EXECUTION_FILES/          # All Python scripts
│   ├── tide/                    # Main pipeline script location
│   └── bplus_inputs/            # Input data directory (PRIMARY)
│       ├── profiles/            # Site profiles (AGI.json, etc.)
│       ├── data/                # Frame conversion data
│       └── *.json               # Hydro tables, GM grids, etc.
├── 02_RAW_DATA/                 # Original data repository (FALLBACK)
│   ├── tank_catalog_from_tankmd.json
│   ├── profiles/                # Alternative profile location
│   ├── bplus_inputs/            # Alternative bplus_inputs location
│   └── sensors/
└── 03_DOCUMENTATION/            # Documentation files
```

**Input File Search Priority**:
1. **Primary**: `01_EXECUTION_FILES/bplus_inputs/` (or `inputs_dir/bplus_inputs/`)
2. **Fallback**: `02_RAW_DATA/bplus_inputs/` (or `02_RAW_DATA/`)

**Note**: Pipeline automatically searches both locations. Use `--inputs_dir` to specify custom location.

### 4.2 Locate Required Input Files

Before your first run, verify these files exist:

#### 4.2.1 Tank Catalog
**Location**: `02_RAW_DATA/tank_catalog_from_tankmd.json`
**Purpose**: Contains all tank definitions, capacities, and locations

**Check**:
```bash
# Windows
dir "02_RAW_DATA\tank_catalog_from_tankmd.json"

# Linux/macOS
ls "02_RAW_DATA/tank_catalog_from_tankmd.json"
```

#### 4.2.2 Hydrostatic Table
**Location**: `01_EXECUTION_FILES/bplus_inputs/Hydro_Table_Engineering.json`
**Purpose**: Vessel hydrostatic data for draft calculations

**Check**:
```bash
# Windows
dir "01_EXECUTION_FILES\bplus_inputs\Hydro_Table_Engineering.json"

# Linux/macOS
ls "01_EXECUTION_FILES/bplus_inputs/Hydro_Table_Engineering.json"
```

**Note**: For detailed schema, coordinate system, and usage information, see Section 4.4.1.

#### 4.2.3 Site Profile
**Location**: `01_EXECUTION_FILES/bplus_inputs/profiles/AGI.json` (or `02_RAW_DATA/profiles/AGI.json`)
**Purpose**: Site-specific configuration (gates, tank operability, etc.)

**⚠️ Profile Adjustment Before Pipeline Execution**
The `AGI.json` profile file can be **edited before pipeline execution** to customize:
- **Gate Parameters**: `fwd_max_m`, `aft_min_m`, `aft_max_m`, `trim_abs_limit_m`
- **Pump Rates**: `pump_rate_tph` (ship pump: 10.0 t/h, hired pump: 100.0 t/h)
- **Tide/UKC Settings**: `forecast_tide_m`, `depth_ref_m`, `ukc_min_m`, `squat_m`, `safety_allow_m`
- **Tank Operability**: `tank_operability` section for stage-specific tank constraints
- **Critical Stages**: `critical_stage_list` for Gate-B application

**Note**: Profile values are loaded at pipeline startup. Make all adjustments **before executing the pipeline**. CLI arguments (e.g., `--fwd_max 2.70`) will override profile values.

**Available Profiles**:

| Profile File | Purpose | When to Use |
|--------------|---------|-------------|
| `AGI.json` | Standard AGI profile | Default for standard operations |
| `AGI_site_profile_COMPLETE_v1.json` | Complete configuration | When full gate/tank configuration needed |
| `site_profile_AGI_aft_ballast_CORRECTED.json` | AFT ballast correction (testing) | Testing AFT draft corrections |
| `site_profile_AGI_aft_ballast_OPERATIONAL.json` | AFT ballast correction (operational) | Operational use with VOID3 constraints |
| `site_profile_AGI_aft_ballast_EXACT_ONLY.json` | Exact tank matching | When exact tank ID matching required |

**Check**:
```bash
# Windows
dir "01_EXECUTION_FILES\bplus_inputs\profiles\AGI.json"

# Linux/macOS
ls "01_EXECUTION_FILES/bplus_inputs/profiles/AGI.json"
```

**Custom Profile**:
```bash
--profile_json "02_RAW_DATA/profiles/custom_profile.json"
```

**Profile Search Order**:
1. CLI `--profile_json` argument (highest priority)
2. `inputs_dir/profiles/{site}.json` (e.g., `AGI.json`)
3. `inputs_dir/profiles/site_{site}.json`
4. `inputs_dir/site_profile_{site}.json`
5. Default profile (if available)

**Other Profile Files**:

##### 4.2.3.1 `AGI.json`

**Purpose**: Simplified AGI profile for standard operations

**⚠️ Pre-Execution Configuration**
This profile file can be edited **before pipeline execution** to adjust operational parameters. The pipeline loads profile values at startup, so changes must be made **prior to running** the pipeline command.

**Key Adjustable Parameters**:
- `operational.trim_abs_limit_m`: Trim limit (default: 2.40m, SSOT from AGENTS.md)
- `operational.pump_rate_tph`: Pump rate (default: 10.0 t/h, ship pump)
- `operational.gate_guard_band_cm`: Gate guard band (default: 2.0cm)
- `gates.AFT_MIN_m`, `gates.FWD_MAX_m`: Gate limits
- `tide_ukc.*`: Tide and UKC parameters

**Key Features**:
- Basic gate definitions (`fwd_max_m`, `aft_min_m`, `aft_max_m`)
- Tank operability keywords (`FWB,VOIDDB,FW2`)
- Critical stage definitions
- UKC parameters (optional)

**Schema**:
```json
{
  "profile_version": "1.3",
  "site": "AGI",
  "fwd_max_m": 2.7,
  "aft_min_m": 2.7,
  "aft_max_m": 3.5,
  "trim_abs_limit_m": 2.4,
  "pump_rate_tph": 10.0,
  "tank_keywords": "FWB,VOIDDB,FW2",
  "critical_stages": [
    "Stage 6A_Critical (Opt C)",
    "Stage 5_PreBallast"
  ],
  "tank_overrides": {...}
}
```

**Usage**: Default profile for standard AGI operations

---

##### 4.2.3.2 AFT Ballast-Specific Profiles

These profiles are specialized configurations for AFT ballast optimization scenarios.

**`site_profile_AGI_aft_ballast_CORRECTED.json`**

**Purpose**: Corrected AFT ballast profile using verified AFT tanks only

**Version**: `2.0_CORRECTED_AFT_BALLAST`

**Key Corrections**:
- **FWB1/2 Removed**: FWB1/2 are FORWARD tanks (x=-27.368m) - excluded from ballast plan
- **Primary AFT Ballast**: FW2.P/S (x=+30.032m, Fr0-6) as primary stern ballast
- **Secondary AFT Ballast**: VOID3.P can add up to +52t (current 100t, max 152.08t)
- **Propeller Safety**: Immersion safe @ AFT 2.70m (confirmed from vessel docs)

**Tank Overrides**:
- `FW2.P/S`: FILL_DISCHARGE, Max_t=13.92t (primary AFT ballast)
- `VOID3`: FILL_DISCHARGE, Min_t=100.0, Max_t=152.08t (secondary AFT ballast)
- `FWB1/2`: use_flag="N" (excluded - forward tanks)
- `FWCARGO1/2`: use_flag="N" (excluded - forward tanks)

**Target Stages**: Stage 5_PreBallast, Stage 6A_Critical

**Usage**: Use when correcting AFT draft violations using verified AFT zone tanks only

---

**`site_profile_AGI_aft_ballast_OPERATIONAL.json`**

**Purpose**: Operational version with VOID3 constraints and FWD discharge-only for AFT-min stages

**Version**: `3.0_OPERATIONAL`

**Key Operational Constraints**:
- **VOID3 Fixed**: Pre-ballast Storage ONLY - Transfer NOT AUTHORIZED
  - Current_t=100t fixed (no transfer authorized)
  - Solver cannot modify VOID3 levels
- **FWD Tanks**: DISCHARGE_ONLY for AFT-min stages (Option 1)
- **Propeller Immersion**: ITTC shaft CL immersion (not AFT draft) must be recorded

**Tank Overrides**:
- `FW2.P/S`: FILL_DISCHARGE, Max_t=13.92t (primary AFT ballast)
- `VOID3.P/S`: mode="FIXED", Min_t=100.0, Max_t=100.0 (operational constraint)
- `FWB1/2`, `FWCARGO1/2`: use_flag="N" (will be DISCHARGE_ONLY for AFT-min stages)

**Operational Constraints**:
```json
{
  "VOID3": {
    "role": "Pre-ballast Storage ONLY",
    "transfer_authorized": false,
    "current_t_fixed": 100.0,
    "note": "Shore-fill before RORO, maintain as static ballast throughout operation"
  }
}
```

**Usage**: Use for operational ballast planning with VOID3 transfer restrictions

---

**`site_profile_AGI_aft_ballast_EXACT_ONLY.json`**

**Purpose**: Exact-only tank overrides with stage-level SSOT for FWD tank handling

**Version**: `3.1_EXACT_ONLY`

**Key Features**:
- **Exact Tank Overrides Only**: No base name matching
- **Stage-Level SSOT**: AFT-min stages use stage-level SSOT for FWD tank handling
- **VOID3 Fixed**: Same operational constraint as OPERATIONAL version

**Tank Overrides**:
- `FW2.P/S`: FILL_DISCHARGE, Max_t=13.92t (AFT FW tank)
- `VOID3.P/S`: mode="FIXED", Min_t=100.0, Max_t=100.0 (operational constraint)
- `FWB1/2.P/S`, `FWCARGO1/2.P/S`: use_flag="N" (exact match only, DISCHARGE_ONLY via stage-level SSOT)

**MWS Notes**:
- DNV incomplete prop immersion handling
- ITTC shaft centreline immersion requirements
- ND 0013 freeboard requirements

**Usage**: Use when exact tank ID matching is required (no base name matching)

---

##### 4.2.3.3 Profile Selection Guide

| Scenario | Recommended Profile |
|----------|---------------------|
| **Standard Operations** | `AGI.json` |
| **Complete Configuration** | `AGI_site_profile_COMPLETE_v1.json` |
| **AFT Ballast Correction (Testing)** | `site_profile_AGI_aft_ballast_CORRECTED.json` |
| **AFT Ballast Correction (Operational)** | `site_profile_AGI_aft_ballast_OPERATIONAL.json` |
| **Exact Tank Matching Required** | `site_profile_AGI_aft_ballast_EXACT_ONLY.json` |

**Profile Priority** (when using `--profile_json`):
1. Explicit CLI path (`--profile_json`)
2. Auto-detection: `inputs_dir/profiles/{site}.json`
3. Default: `AGI.json` or `AGI_site_profile_COMPLETE_v1.json`

### 4.3 Optional: Sensor Data

If you have current tank level sensor data:

**Location**: `02_RAW_DATA/sensors/current_t_sensor.csv`
**Format**: CSV with columns: `Tank`, `Current_t` (or similar)

**Example**:
```csv
Tank,Current_t
FWB2.P,28.50
FWB2.S,28.50
VOIDDB2.P,0.0
```

---

### 4.4 `bplus_inputs/` - B+ System Inputs

#### 4.4.1 `Hydro_Table_Engineering.json`

**Purpose**: Hydrostatic table (engineering version) - SSOT for hydrostatic data

**File Size**: 4.6KB, 161 lines

**Schema**:
```json
{
  "_meta": {
    "ship_name": "BUSHRA",
    "source": "STABILITY CALCULATION INITIAL CONDITION_20251026.pdf",
    "verified_by": "Aries / BV",
    "generated_by": "hydro_table_calculator.py",
    "lcf_reference": "midship",
    "lcf_ref": "MIDSHIP_AFT_POS",
    "x_convention": "AFT+",
    "fallbacks": {
      "LCF_m_from_midship": 0.76,
      "MCTC_t_m_per_cm": 34.0,
      "TPC_t_per_cm": 8.0
    }
  },
  "rows": [
    {
      "Tmean_m": 3.0,
      "Disp_t": 2524.4,
      "Trim_m": 0.0,
      "Draft_FWD": 3.0,
      "Draft_AFT": 3.0,
      "LCF_m": 0.76,
      "TPC_t_per_cm": 10.2,
      "MCTC_t_m_per_cm": 38.3,
      "KM_m": 12.341,
      "GM_m": 8.45,
      "GM_min_m": 1.5,
      "LCF_m_from_midship": 0.76
    }
  ]
}
```

**Key Fields**:
- `Tmean_m`: Mean draft (meters) - primary key for interpolation
- `Disp_t`: Displacement (tonnes)
- `Trim_m`: Trim (meters, positive = trim by stern)
- `Draft_FWD`, `Draft_AFT`: Forward and aft drafts (meters)
- `LCF_m`: Longitudinal center of flotation (meters from AP)
- `LCF_m_from_midship`: LCF from midship (meters, AFT positive)
- `TPC_t_per_cm`: Tons per centimeter immersion
- `MCTC_t_m_per_cm`: Moment to change trim one centimeter
- `KM_m`: Metacentric height above keel
- `GM_m`: Metacentric height above center of gravity
- `GM_min_m`: Minimum GM requirement

**Coordinate System**:
- `lcf_reference`: "midship"
- `x_convention`: "AFT+" (AFT direction is positive)
- `LCF_m_from_midship`: Positive values = AFT of midship

**Interpolation Method**: Linear interpolation for intermediate Tmean values

**Fallback Values** (when interpolation fails):
- `LCF_m_from_midship`: 0.76 m
- `MCTC_t_m_per_cm`: 34.0 t·m/cm
- `TPC_t_per_cm`: 8.0 t/cm

**Usage**:
- Converted to `hydro_table_for_solver.csv` by `convert_hydro_engineering_json_to_solver_csv()`
- Used by Step 1 (TR Excel generation) for draft/trim calculations
- Used by Step 3 (Solver) for hydrostatic interpolation (iterative refinement)
- Used by Step 4 (Optimizer) for draft predictions

**Location Priority**:
1. `inputs_dir/bplus_inputs/Hydro_Table_Engineering.json`
2. `base_dir/bplus_inputs/Hydro_Table_Engineering.json`
3. `02_RAW_DATA/bplus_inputs/Hydro_Table_Engineering.json` (fallback)
4. Can be explicitly specified with `--hydro` argument

**Important**:
- This is the **SSOT for hydrostatic data**. All hydrostatic calculations must use this table.
- Verified by Aries / BV (Bureau Veritas)
- Source document: `STABILITY CALCULATION INITIAL CONDITION_20251026.pdf`

---

## 5. Quick Start Guide

### 5.1 Your First Pipeline Run

This is the simplest command to run the complete pipeline:

```bash
python "01_EXECUTION_FILES\tide\integrated_pipeline_defsplit_v2_gate270_split_v3_auditpatched_autodetect_TIDE_v1.py" --site AGI
```

**What this does**:
- Runs all steps (1b → 2 → 3)
- Uses default AGI profile
- Auto-detects input files
- Generates all output files

### 5.2 Understanding the Output

After running, you'll find output in:
```
pipeline_out_<timestamp>/
├── ssot/                        # SSOT CSV files
├── logs/                        # Execution logs
├── gate_fail_report.md          # Gate compliance report
├── OPS_FINAL_R3_AGI_Ballast_Integrated.xlsx
├── solver_ballast_plan.csv
└── PIPELINE_CONSOLIDATED_AGI_<timestamp>.xlsx
```

### 5.3 Basic Command Structure

```bash
python <pipeline_script> [OPTIONS]
```

**Common Options**:
- `--site AGI` : Specify site (AGI or DAS)
- `--from_step 1` : Start from step 1
- `--to_step 3` : End at step 3
- `--profile <path>` : Custom profile path
- `--enable-sequence` : Generate ballast sequence

---

## 6. Step-by-Step Tutorial

### 6.1 Tutorial: Complete Pipeline Run

Let's run through a complete example step by step.

#### Step 1: Prepare Your Environment

```bash
# Navigate to project directory
cd "C:\AGI RORO TR"

# Verify Python
python --version
```

#### Step 2: Run Basic Pipeline

```bash
python "01_EXECUTION_FILES\tide\integrated_pipeline_defsplit_v2_gate270_split_v3_auditpatched_autodetect_TIDE_v1.py" --site AGI
```

**What happens**:
1. Pipeline loads AGI profile
2. **Executes Step 0 (optional)**: SPMT cargo input generation (if `--from_step 0`)
3. Executes Step 1b: Generates `stage_results.csv`
4. Executes PREP: Converts JSON to SSOT CSV
5. Executes Step 2: Generates OPS report
6. Executes Step 3: Runs LP Solver
7. Executes Step 4 (optional): Runs Optimizer (if `--to_step 4` or `5`)
8. Executes Step 5 (optional): Generates Bryan Template (if `--to_step 5`)
9. Collects all outputs

**Expected output**:
```
[INFO] Loading site profile: AGI
[INFO] Executing Step 1b: stage_results.csv generation
[INFO] Executing PREP: SSOT CSV conversion
[INFO] Executing Step 2: OPS Integrated Report
[INFO] Executing Step 3: Ballast Gate Solver
[INFO] Pipeline completed successfully!
Output directory: pipeline_out_20251230_120000/
```

#### Step 3: Check Output Files

```bash
# Windows
dir pipeline_out_*\gate_fail_report.md
dir pipeline_out_*\solver_ballast_summary.csv

# Linux/macOS
ls pipeline_out_*/gate_fail_report.md
ls pipeline_out_*/solver_ballast_summary.csv
```

### 6.2 Tutorial: Running Specific Steps

Sometimes you only need to run certain steps:

#### Example 0: Run with SPMT (Step 0)

Generate SPMT cargo input before running pipeline:

```bash
python "01_EXECUTION_FILES\tide\integrated_pipeline_defsplit_v2_gate270_split_v3_auditpatched_autodetect_TIDE_v1.py" \
  --site AGI \
  --from_step 0 \
  --to_step 3 \
  --spmt_config "spmt v1/spmt_shuttle_example_config_AGI_FR_M.json"
```

**Output**:
- `AGI_SPMT_Shuttle_Output.xlsx`: SPMT cargo input
- Then proceeds to Steps 1b → 2 → 3

**When to use**: When you need to generate SPMT cargo input from configuration

#### Example 1: Only Generate Stage Results

```bash
python "01_EXECUTION_FILES\tide\integrated_pipeline_defsplit_v2_gate270_split_v3_auditpatched_autodetect_TIDE_v1.py" \
  --site AGI \
  --from_step 1 \
  --to_step 1
```

**Output**: `stage_results.csv` only

#### Example 2: Run Solver Only (if stage_results.csv exists)

```bash
python "01_EXECUTION_FILES\tide\integrated_pipeline_defsplit_v2_gate270_split_v3_auditpatched_autodetect_TIDE_v1.py" \
  --site AGI \
  --from_step 3 \
  --to_step 3
```

**Output**: Solver results only

### 6.3 Tutorial: Using Sensor Data

If you have current tank levels from sensors:

```bash
python "01_EXECUTION_FILES\tide\integrated_pipeline_defsplit_v2_gate270_split_v3_auditpatched_autodetect_TIDE_v1.py" \
  --site AGI \
  --current_t_csv "02_RAW_DATA\sensors\current_t_sensor.csv" \
  --current_t_strategy override
```

**What this does**:
- Loads sensor CSV
- Injects current tank levels into pipeline
- Uses sensor values instead of defaults

### 6.4 Tutorial: Custom Gate Values

Override default gate values:

```bash
python "01_EXECUTION_FILES\tide\integrated_pipeline_defsplit_v2_gate270_split_v3_auditpatched_autodetect_TIDE_v1.py" \
  --site AGI \
  --fwd_max 2.70 \
  --aft_min 2.70
```

### 6.5 Tutorial: Generate Ballast Sequence

To generate operational sequence files:

```bash
python "01_EXECUTION_FILES\tide\integrated_pipeline_defsplit_v2_gate270_split_v3_auditpatched_autodetect_TIDE_v1.py" \
  --site AGI \
  --enable-sequence
```

**Additional Outputs**:
- `BALLAST_OPTION.csv`: Planning level
- `BALLAST_EXEC.csv`: Execution sequence
- `BALLAST_SEQUENCE.xlsx`: Excel with 3 sheets
- `BALLAST_OPERATIONS_CHECKLIST.md`: Operational checklist

---

## 7. Understanding Output Files

### 7.1 Key Output Files

#### 7.1.1 `gate_fail_report.md`

**Purpose**: Gate compliance summary

**What to look for**:
- ✅ **PASS**: All gates satisfied
- ⚠️ **WARN**: Some gates have warnings
- ❌ **FAIL**: Gate violations detected

**Example**:
```markdown
## Gate Compliance Summary

| Stage | Gate-A (AFT_MIN_2p70) | Gate-B (FWD_MAX_2p70) | Status |
|-------|----------------------|----------------------|--------|
| Stage 5_PreBallast | PASS | PASS | ✅ |
| Stage 6A_Critical | PASS | PASS | ✅ |
```

#### 7.1.2 `solver_ballast_summary.csv`

**Purpose**: Stage-wise ballast plan summary

**Key Columns**:
- `Stage`: Stage name
- `New_FWD_m`: Forward draft after ballast
- `New_AFT_m`: Aft draft after ballast
- `Delta_W_t`: Total ballast change
- `Gate_FWD_Max`: Gate compliance status
- `Gate_AFT_Min`: Gate compliance status

**How to read**:
- Positive `Delta_W_t`: Ballast added
- Negative `Delta_W_t`: Ballast discharged
- `PASS` in Gate columns: Gate satisfied

#### 7.1.3 `pipeline_stage_QA.csv`

**Purpose**: Complete stage quality assurance data

**Key Columns**:
- `Draft_FWD_m`, `Draft_AFT_m`: Draft values
- `Freeboard_Min_m`: Minimum freeboard
- `Gate_*`: All gate statuses
- `HardStop_Any`: Critical issues flag

#### 7.1.4 `PIPELINE_CONSOLIDATED_AGI_<timestamp>.xlsx`

**Purpose**: Consolidated Excel with all data

**Sheets**:
- Stage-wise calculations
- Solver results
- Optimizer results (if Step 4 run)
- Ballast sequences (if enabled)

### 7.2 Output Directory Structure

```
pipeline_out_20251230_120000/
├── ssot/                              # SSOT CSV files
│   ├── tank_ssot_for_solver.csv      # Tank data for solver
│   ├── hydro_table_for_solver.csv    # Hydro data for solver
│   ├── stage_table_unified.csv       # Stage data
│   └── pipeline_stage_QA.csv         # QA data
├── logs/                              # Execution logs
│   ├── 01_TR_EXCEL.log
│   ├── 02_TR_STAGE_CSV.log
│   ├── 03_OPS_INTEGRATED.log
│   └── 04_SOLVER_LP.log
├── gate_fail_report.md                # Gate compliance report
├── TUG_Operational_SOP_DNV_ST_N001.md # TUG SOP
├── OPS_FINAL_R3_AGI_Ballast_Integrated.xlsx
├── solver_ballast_plan.csv
├── solver_ballast_summary.csv
└── PIPELINE_CONSOLIDATED_AGI_20251230_120000.xlsx
```

---

## 8. Common Use Cases

### 8.1 Use Case 1: Standard Ballast Analysis

**Scenario**: Run complete analysis for AGI site

**Command**:
```bash
python "01_EXECUTION_FILES\tide\integrated_pipeline_defsplit_v2_gate270_split_v3_auditpatched_autodetect_TIDE_v1.py" --site AGI
```

**Output**: Complete analysis with all reports

### 8.2 Use Case 2: Quick Gate Check

**Scenario**: Only check if gates are satisfied (no optimization)

**Command**:
```bash
python "01_EXECUTION_FILES\tide\integrated_pipeline_defsplit_v2_gate270_split_v3_auditpatched_autodetect_TIDE_v1.py" \
  --site AGI \
  --from_step 1 \
  --to_step 2
```

**Output**: Gate fail report only

### 8.3 Use Case 3: Optimized Ballast Plan

**Scenario**: Get optimized ballast plan with sequence

**Command**:
```bash
python "01_EXECUTION_FILES\tide\integrated_pipeline_defsplit_v2_gate270_split_v3_auditpatched_autodetect_TIDE_v1.py" \
  --site AGI \
  --enable-sequence
```

**Output**: Solver plan + Optimizer plan + Sequence files

### 8.4 Use Case 4: Custom Tide Values

**Scenario**: Use specific tide forecast values

**Command**:
```bash
python "01_EXECUTION_FILES\tide\integrated_pipeline_defsplit_v2_gate270_split_v3_auditpatched_autodetect_TIDE_v1.py" \
  --site AGI \
  --forecast_tide 1.5 \
  --depth_ref 10.0 \
  --ukc_min 2.0
```

### 8.5 Use Case 5: Re-run with Updated Sensor Data

**Scenario**: Update tank levels from sensors and re-optimize

**Command**:
```bash
python "01_EXECUTION_FILES\tide\integrated_pipeline_defsplit_v2_gate270_split_v3_auditpatched_autodetect_TIDE_v1.py" \
  --site AGI \
  --current_t_csv "02_RAW_DATA\sensors\current_t_sensor.csv" \
  --current_t_strategy override \
  --from_step 3 \
  --to_step 3
```

### 8.6 Use Case 6: Run with SPMT Input Generation

**Scenario**: Generate SPMT cargo input and run complete pipeline

**Prerequisites**:
- `agi_ssot.py` must be in `spmt v1/` directory (copy from `01_EXECUTION_FILES/spmt v1/` if missing)

**Command**:
```bash
python "01_EXECUTION_FILES\tide\integrated_pipeline_defsplit_v2_gate270_split_v3_auditpatched_autodetect_TIDE_v1.py" \
  --site AGI \
  --from_step 0 \
  --to_step 5 \
  --spmt_config "spmt v1/spmt_shuttle_example_config_AGI_FR_M.json" \
  --fwd_max 2.70 \
  --aft_min 2.70 \
  --enable-sequence \
  --enable-valve-lineup
```

**Output**:
- `AGI_SPMT_Shuttle_Output.xlsx`: SPMT cargo input Excel
- `spmt_output/`: SPMT output CSV files (`stage_loads.csv`, `stage_summary.csv`)
- Complete pipeline outputs (Steps 1b → 2 → 3 → 4 → 5)

---

## 9. Troubleshooting Guide

### 9.1 Common Errors and Solutions

#### Error 1: "File not found: tank_catalog_from_tankmd.json"

**Cause**: Tank catalog file missing or wrong path

**Solution**:
1. Check file exists: `dir "02_RAW_DATA\tank_catalog_from_tankmd.json"`
2. Verify you're in correct directory
3. Use `--tank_catalog` to specify custom path

#### Error 2: "ModuleNotFoundError: No module named 'pandas'"

**Cause**: Python packages not installed

**Solution**:
```bash
pip install pandas numpy openpyxl scipy
```

#### Error 3: "Gate FAIL: AFT_MIN_2p70 violation"

**Cause**: Aft draft below 2.70m requirement

**Solution**:
1. Check `gate_fail_report.md` for details
2. Review `solver_ballast_summary.csv` for ballast recommendations
3. May need to adjust ballast or cargo distribution

#### Error 4: "Stage results not found"

**Cause**: `stage_results.csv` missing

**Solution**:
```bash
# Run Step 1b to generate it
python "01_EXECUTION_FILES\tide\integrated_pipeline_defsplit_v2_gate270_split_v3_auditpatched_autodetect_TIDE_v1.py" \
  --site AGI \
  --from_step 1 \
  --to_step 1
```

#### Error 5: "Profile not found: AGI.json"

**Cause**: Site profile missing

**Solution**:
1. Check `01_EXECUTION_FILES\bplus_inputs\profiles\AGI.json` exists
2. Use `--profile` to specify custom path:
   ```bash
   --profile "path\to\your\profile.json"
   ```

#### Error 6: "ModuleNotFoundError: No module named 'agi_ssot'" (SPMT Step 0)

**Cause**: `agi_ssot.py` module missing from SPMT script directory

**Solution**:
1. Check if `agi_ssot.py` exists in `spmt v1/` directory:
   ```bash
   dir "spmt v1\agi_ssot.py"
   ```

2. If missing, copy from `01_EXECUTION_FILES/spmt v1/`:
   ```bash
   copy "01_EXECUTION_FILES\spmt v1\agi_ssot.py" "spmt v1\agi_ssot.py"
   ```

3. Verify import works:
   ```bash
   cd "spmt v1"
   python -c "from agi_ssot import VesselSSOT; print('OK')"
   ```

**Note**: `agi_ssot.py` must be in the same directory as `agi_spmt_unified.py` for Step 0 to work.

### 9.2 Debug Mode

Enable debug output for detailed information:

```bash
python "01_EXECUTION_FILES\tide\integrated_pipeline_defsplit_v2_gate270_split_v3_auditpatched_autodetect_TIDE_v1.py" \
  --site AGI \
  --debug_report
```

**Output**: Additional debug files in output directory

### 9.3 Checking Logs

Review execution logs for errors:

```bash
# Windows
type pipeline_out_*\logs\*.log

# Linux/macOS
cat pipeline_out_*/logs/*.log
```

**Look for**:
- `ERROR`: Critical errors
- `WARNING`: Warnings (may not stop execution)
- `INFO`: General information

---

## 10. Advanced Features

### 10.1 Custom Profile

**Profile Selection Guide**:

1. **Standard Operations**: Use `AGI.json`
   ```bash
   --site AGI  # Auto-loads AGI.json
   ```

2. **Complete Configuration**: Use `AGI_site_profile_COMPLETE_v1.json`
   ```bash
   --profile_json "02_RAW_DATA/profiles/AGI_site_profile_COMPLETE_v1.json"
   ```

3. **AFT Ballast Correction**: Use operational profile
   ```bash
   --profile_json "02_RAW_DATA/profiles/site_profile_AGI_aft_ballast_OPERATIONAL.json"
   ```

**Profile Search Order**:
1. CLI `--profile_json` argument (highest priority)
2. `inputs_dir/profiles/{site}.json` (e.g., `AGI.json`)
3. `inputs_dir/profiles/site_{site}.json`
4. `inputs_dir/site_profile_{site}.json`
5. Default profile (if available)

**Create Custom Site-Specific Profile**:

```json
{
  "site": "CUSTOM_SITE",
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
  }
}
```

**Usage**:
```bash
--profile_json "path\to\custom_profile.json"
```

### 10.2 Tide Integration

Multiple ways to provide tide data:

#### Option 1: CLI Argument (Highest Priority)
```bash
--forecast_tide 1.5
```

#### Option 2: Stage Tide CSV
```bash
--stage_tide_csv "stage_tide_AGI.csv"
```

#### Option 3: Tide Windows JSON
```bash
--tide_windows "tide_windows_AGI.json"
```

### 10.3 Step 4: Optimizer

Run heuristic optimizer after solver:

```bash
python "01_EXECUTION_FILES\tide\integrated_pipeline_defsplit_v2_gate270_split_v3_auditpatched_autodetect_TIDE_v1.py" \
  --site AGI \
  --from_step 1 \
  --to_step 4
```

**Output**: `optimizer_ballast_plan.xlsx` with optimized plan

### 10.4 Valve Lineup Generation

Generate valve lineup for operations:

```bash
python "01_EXECUTION_FILES\tide\integrated_pipeline_defsplit_v2_gate270_split_v3_auditpatched_autodetect_TIDE_v1.py" \
  --site AGI \
  --enable-sequence \
  --enable-valve-lineup
```

**Output**: `BALLAST_SEQUENCE_WITH_VALVES.md`

---

## 11. FAQ

### Q1: How long does a pipeline run take?

**A**: Typically 30 seconds to 2 minutes depending on:
- Number of stages
- Whether optimizer is run
- System performance

### Q2: Can I run only specific steps?

**A**: Yes, use `--from_step` and `--to_step`:
```bash
--from_step 2 --to_step 3
```

### Q3: What if I get gate failures?

**A**:
1. Check `gate_fail_report.md` for details
2. Review `solver_ballast_summary.csv` for recommendations
3. May need to adjust cargo distribution or ballast

### Q4: How do I update tank levels?

**A**: Use sensor CSV:
```bash
--current_t_csv "path\to\sensor.csv" --current_t_strategy override
```

### Q5: Can I use this for different sites?

**A**: Yes, create site-specific profile or use `--site DAS` for DAS site

### Q6: What's the difference between Solver and Optimizer?

**A**:
- **Solver (Step 3)**: LP-based, ensures gate compliance
- **Optimizer (Step 4)**: Heuristic-based, optimizes for time/capacity

### Q7: How do I interpret the output Excel file?

**A**:
- Each sheet represents different data
- Check sheet names for content
- `pipeline_stage_QA.csv` has complete QA data

### Q8: Can I customize gate values?

**A**: Yes, use CLI arguments:
```bash
--fwd_max 2.70 --aft_min 2.70
```

### Q9: What files do I need to provide?

**A**: Minimum:
- Tank catalog JSON
- Hydrostatic table JSON
- Site profile JSON

### Q10: How do I know if the run was successful?

**A**: Check:
1. No errors in terminal output
2. `gate_fail_report.md` shows PASS status
3. Output files exist in `pipeline_out_<timestamp>/`

### Q11: How do I interpret Gate-B margin values?

**A**: Gate-B margin uses **Chart Datum reference**:
```
GateB_FWD_MAX_2p70_CD_Margin_m = 2.70 - Draft_FWD_m_CD
```

**Where:**
- `Draft_FWD_m_CD` = `Draft_FWD_m - Forecast_Tide_m` (Chart Datum)
- **⚠️ Important:** Always check `Draft_FWD_m_CD` (not `Draft_FWD_m`) when interpreting Gate-B margins

**Example**:
- `Draft_FWD_m` = 2.19m, `Forecast_Tide_m` = 2.0m
- `Draft_FWD_m_CD` = 2.19 - 2.0 = 0.19m
- `GateB_Margin` = 2.70 - 0.19 = 2.51m ✅ (safe margin)

### Q12: What does Freeboard = 0.00m mean?

**A**:
- **Geometric Definition**: `Freeboard = D_vessel_m - Draft`
- **Freeboard = 0.00m**: Deck edge at waterline ⚠️
- **Risk**: Green water, structural stress
- **Required**: Engineering verification (class acceptance, load-line compliance)

**⚠️ SSOT Gap**: Current default `freeboard_min_m = 0.0` (no operational buffer). Consider setting operational minimum (e.g., 0.20m, 0.50m) based on requirements.

### Q13: What happens when draft exceeds D_vessel (3.65m)?

**A**:
- **Automatic Clipping**: Draft is clipped to `D_vessel` (3.65m)
- **Result**: `Freeboard_Min_m = 0.00m` (deck edge at waterline)
- **⚠️ Critical Warning**:
  - Clipping masks input validity issues (TR position error, calculation error)
  - Requires engineering verification (class acceptance, load-line compliance)
  - Approval packages must explicitly state when draft clipping occurred

**Pipeline Log Warning**:
```
[WARNING] Draft values clipped to D_vessel (3.65m) for 1 stages:
  - Stage 6C: FWD 3.80 -> 3.65m, AFT 3.80 -> 3.65m
  ⚠️ PHYSICAL LIMIT EXCEEDED: Freeboard = 0.00m
  → Requires engineering verification
```

---

## 12. Getting Help

### 12.1 Documentation

- **Architecture**: `03_DOCUMENTATION/00_CORE_ARCHITECTURE/`
- **Operating Guide**: `03_DOCUMENTATION/00_CORE_ARCHITECTURE/Ballast Pipeline Operating Guide.md`
- **Complete Architecture**: `03_DOCUMENTATION/00_CORE_ARCHITECTURE/Pipeline Complete Architecture and Execution Files Logic Detailed.md`

### 12.2 Log Files

Check logs in: `pipeline_out_<timestamp>/logs/`

### 12.3 Debug Mode

Run with `--debug_report` for detailed diagnostics

---

## Appendix A: Complete Command Reference

### A.1 Site and Profile Options

```bash
--site AGI|DAS                    # Site label (default: AGI)
--profile_json <path>            # Site profile JSON path
```

### A.2 Step Control Options

```bash
--from_step <0-5>                # Start step (default: 1)
--to_step <0-5>                  # End step (default: 5)
--enable-sequence                # Enable Step 4b: Ballast Sequence Generator
--enable-valve-lineup            # Enable Step 4c: Valve Lineup Generator
```

### A.3 Gate Configuration Options

```bash
--fwd_max <m>                    # FWD maximum draft gate (default: 2.70m)
--aft_min <m>                    # AFT minimum draft gate (default: 2.70m)
--aft_max <m>                    # AFT maximum draft limit for optimizer (default: 3.50m)
--trim_abs_limit <m>             # Absolute trim limit (default: 0.50m)
--trim-limit-enforced            # Enforce trim limit (default: enabled)
--no-trim-limit-enforced         # Disable trim limit enforcement
--freeboard-min-m <m>            # Minimum freeboard requirement (default: 0.0m)
--freeboard-min-enforced         # Enforce minimum freeboard (default: enabled)
--no-freeboard-min-enforced      # Disable minimum freeboard enforcement
--gate_guard_band_cm <cm>        # Gate guard-band tolerance (default: 2.0cm)
```

### A.4 Tide and UKC Options

```bash
--forecast_tide <m>              # Forecast tide level (m, Chart Datum, highest priority)
--depth_ref <m>                  # Reference depth (m, Chart Datum)
--ukc_min <m>                    # Minimum UKC requirement (m)
--squat <m>                      # Squat allowance (m, default: 0.0)
--safety_allow <m>               # Additional safety allowance (m, default: 0.0)
--tide_table <path>              # Official tide table file (CSV/XLSX/JSON)
--stage_schedule <path>          # Stage schedule file (Stage + Timestamp)
--stage_tide_csv <path>          # Pre-computed stage tide CSV (highest priority)
--tide_strategy keep_csv|override_from_table  # Tide assignment strategy (default: keep_csv)
--tide_tol <m>                   # Tide margin tolerance (default: 0.10m)
```

### A.5 Wave and Freeboard Options

```bash
--hmax_wave_m <m>                # Maximum wave height (m) for GL Noble Denton 0013/ND freeboard check
--four_corner_monitoring         # Enable 4-corner freeboard monitoring (reduces ND requirement)
```

### A.6 Sensor Data Options

```bash
--current_t_csv <path>           # Sensor/PLC/IoT CSV for Current_t injection
--current_t_strategy override|fill_missing  # Sensor injection strategy (default: override)
```

### A.7 Stateful Solver Options

```bash
--stateful_solver                # Enable stateful solver (carry-forward Current_t across stages)
--stateful                       # Alias for --stateful_solver
--reset_tank_state <list|regex>  # Reset Current_t from SSOT (comma list or regex with 're:' prefix)
--state_trace_csv <path>         # CSV path for stateful solver tank snapshots
```

### A.8 Tank Operability Options

```bash
--tank_operability_json <path>   # Tank operability/profile JSON (PRE_BALLAST_ONLY enforcement)
--operational_stage_regex <regex>  # Regex for operational stages (default: "(6a|critical|ramp|roll|loadout)")
--disable_preballast_only_on_operational_stages  # Disable PRE_BALLAST_ONLY on operational stages
```

### A.9 Input File Override Options

```bash
--tank_catalog <path>            # Tank catalog JSON path (default: tank_catalog_from_tankmd.json)
--hydro <path>                   # Hydro table JSON path
--stage_results <path>           # stage_results.csv path
--spmt_config <path>             # SPMT config JSON (default: spmt v1/spmt_shuttle_example_config_AGI_FR_M.json)
```

### A.10 Script Path Override Options

```bash
--tr_script <path>               # TR script path (default: agi_tr_patched_v6_6_defsplit_v1.py)
--ops_script <path>              # OPS script path (default: ops_final_r3_integrated_defs_split_v4_patched_TIDE_v1.py)
--solver_script <path>           # Solver script path (default: ballast_gate_solver_v4_TIDE_v1.py)
--optimizer_script <path>        # Optimizer script path (default: Untitled-2_patched_defsplit_v1_1.py)
--spmt_script <path>             # SPMT script path (default: spmt v1/agi_spmt_unified.py)
--bryan_template_script <path>   # Bryan template script path (default: tide/bryan_template_unified_TIDE_v1.py)
```

### A.11 Headers SSOT Options

```bash
--headers-registry <path>        # Path to headers_registry.json (auto-compiles from HEADERS_MASTER.xlsx if needed)
--enable-headers-ssot            # Enable headers SSOT for all outputs (requires --headers-registry)
--head-registry <path>           # Path to HEAD_REGISTRY YAML for header validation
--auto-head-guard                # Automatically run Head Guard validation (requires --head-registry)
```

### A.12 Data Conversion Options

```bash
--pump_rate <t/h>                # Default pump rate (default: 100.0 t/h)
--tank_keywords <keywords>       # Comma keywords for use_flag=Y (default: "BALLAST,VOID,FWB,FW,DB")
--exclude_fwd_tanks              # Exclude FWD tanks (x_from_mid_m < 0) from solver
--exclude_fwd_tanks_aftmin_only  # Set FWD tanks to DISCHARGE_ONLY for AFT-min stages
```

### A.13 File Path Options

```bash
--base_dir <path>                # Base directory containing scripts (default: script directory)
--inputs_dir <path>              # Input files directory (default: base_dir)
--out_dir <path>                 # Output directory (default: base_dir/pipeline_out_<timestamp>)
```

### A.14 Debug and Reporting Options

```bash
--no_gate_report                 # Disable Gate FAIL auto report generation
--debug_report                   # Generate debug feasibility report
--auto_debug_report              # Automatically generate debug report
--dry_run                        # Print resolved paths and planned actions, then exit
```

### A.15 Complete Example Commands

#### Basic Run
```bash
python integrated_pipeline_defsplit_v2_gate270_split_v3_auditpatched_autodetect_TIDE_v1.py --site AGI
```

#### With SPMT (Step 0)
```bash
python integrated_pipeline_defsplit_v2_gate270_split_v3_auditpatched_autodetect_TIDE_v1.py \
  --site AGI \
  --from_step 0 \
  --to_step 3 \
  --spmt_config "spmt v1/spmt_shuttle_example_config_AGI_FR_M.json"
```

#### With Stateful Solver
```bash
python integrated_pipeline_defsplit_v2_gate270_split_v3_auditpatched_autodetect_TIDE_v1.py \
  --site AGI \
  --stateful_solver \
  --state_trace_csv "state_trace.csv"
```

#### With Tide Integration
```bash
python integrated_pipeline_defsplit_v2_gate270_split_v3_auditpatched_autodetect_TIDE_v1.py \
  --site AGI \
  --tide_table "bplus_inputs/water tide_202512.xlsx" \
  --stage_schedule "bplus_inputs/stage_schedule.csv" \
  --tide_strategy override_from_table
```

#### Complete Run with All Features
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
  --current_t_csv "sensors/current_t_sensor.csv" \
  --current_t_strategy override \
  --enable-sequence \
  --enable-valve-lineup \
  --stateful_solver \
  --debug_report
```

---

**Note**: For detailed documentation on each option, refer to:
- `Ballast Pipeline - Complete Options Reference Guide.md` (comprehensive reference)
- `Pipeline Complete Architecture and Exe.md` (architecture and execution details)

---

## Appendix B: File Format Examples

### Sensor CSV Format

```csv
Tank,Current_t
FWB2.P,28.50
FWB2.S,28.50
VOIDDB2.P,0.0
VOIDDB2.S,0.0
```

### Stage Tide CSV Format

```csv
Stage,Forecast_Tide_m
Stage 1,1.2
Stage 5_PreBallast,1.5
Stage 6A_Critical,1.8
```

---

**End of Guide**

For additional support, refer to the technical documentation in `03_DOCUMENTATION/00_CORE_ARCHITECTURE/`
```
