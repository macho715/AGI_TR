# Pipeline Complete Architecture and Execution Files Detailed Documentation

**Created**: 2025-12-27
**Version**: v4.5 (Complete Architecture Documentation)
**Version Policy**: This document uses a separate versioning scheme from other documents (v3.1) as a complete architecture integration document
**Purpose**: Complete pipeline architecture, execution files, and detailed logic explanation

**Latest Update (v4.5 - 2025-12-29):**

- Added bplus_inputs folder structure and input data mapping
- Detailed pipeline step-by-step input file mapping
- Specified search order and Tide Integration priority

**Latest Update (v4.4 - 2025-12-29):**

- Added complete pipeline execution file list (21 files, categorized)
- Classification by execution method (subprocess, import module, dynamic import)
- Specified activation conditions and dependency relationships

**Latest Update (v4.3 - 2025-12-29):**

- Forecast_Tide_m priority change: CLI `--forecast_tide` value takes highest priority
  - Priority redefined in `build_stage_table_from_stage_results()` and `enrich_stage_table_with_tide_ukc()` functions
  - Ensures complete alignment of `Forecast_Tide_m` between `stage_table_unified.csv` and `solver_ballast_summary.csv`
  - Details: Refer to `17_TIDE_UKC_Calculation_Logic.md` section 17.6.5

**Latest Update (v4.2 - 2025-12-28):**

- Option 2 implementation complete: Step 4b Ballast Sequence Generator extension
  - Separate output of `BALLAST_OPTION.csv` / `BALLAST_EXEC.csv`
  - `generate_sequence_with_carryforward()`: Start_t/Target_t carry-forward implementation
  - `generate_option_plan()`: Delta_t plan generation (includes Stage 6B)
  - `BALLAST_SEQUENCE.xlsx` with 3 sheets (Ballast_Option, Ballast_Exec, Ballast_Sequence)
- Option 1 patch proposal (not implemented): Bryan Pack Forecast_tide_m injection, Stage 5_PreBallast critical application

**Latest Update (v4.1 - 2025-12-27):**

- Added GM verification v2b detailed explanation, enhanced GM Grid axis alignment information

---

## Table of Contents

1. [Complete Architecture Overview](#1-complete-architecture-overview)
2. [Execution File List and Roles](#2-execution-file-list-and-roles)
3. [Step-by-Step Detailed Logic](#3-step-by-step-detailed-logic)
4. [Data Flow and SSOT Integration](#4-data-flow-and-ssot-integration)
5. [Key Functions and Module Descriptions](#5-key-functions-and-module-descriptions)
6. [Input/Output File Structure](#6-inputoutput-file-structure)
7. [Error Handling and Logging](#7-error-handling-and-logging)

---

## 1. Complete Architecture Overview

### 1.1 Pipeline Purpose

The Ballast Pipeline is an integrated pipeline for automating and optimizing **Ballast Management** operations for the LCT BUSHRA vessel.

**Core Objectives:**

- Stage-wise Draft/Trim/GM calculation and verification
- Gate compliance (AFT_MIN, FWD_MAX, Freeboard, UKC)
- Ballast Plan optimization (LP Solver + Heuristic Optimizer)
- Automatic generation of operational preparation documents (Sequence, Checklist, Valve Lineup)

### 1.2 Architecture Layers

**Visual Architecture Diagram**: Refer to `03_DOCUMENTATION/Pipeline Integration.md` section 1 (Mermaid diagram)

```
┌─────────────────────────────────────────────────────────────┐
│ INPUT LAYER (JSON SSOT + Sensors)                           │
│ - tank_catalog_from_tankmd.json                             │
│ - Hydro_Table_Engineering.json                              │
│ - AGI_site_profile_COMPLETE_v1.json                         │
│ - current_t_*.csv (sensor data, auto-detected)               │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ ORCHESTRATOR LAYER (Single Entry Point)                     │
│ - integrated_pipeline_defsplit_v2_gate270_split_v3_         │
│   auditpatched_autodetect.py                                │
│   • Path resolution, profile loading, SSOT conversion       │
│   • Step execution control, output collection, Excel merge │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ SSOT CSV LAYER (Solver/Optimizer input)                     │
│ - tank_ssot_for_solver.csv                                   │
│ - hydro_table_for_solver.csv                                │
│ - stage_table_unified.csv                                    │
│ - pipeline_stage_QA.csv                                     │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ EXECUTION STEPS LAYER                                        │
│ - Step 1: TR Excel Generation                                │
│ - Step 1b: stage_results.csv generation                     │
│ - Step 2: OPS Integrated Report                             │
│ - Step 3: LP Solver (Gate Compliance)                       │
│ - Step 4: Optimizer (Heuristic Optimization)                │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ OUTPUT LAYER (Reports, Plans, Excel)                        │
│ - OPS_FINAL_R3_Report_Integrated.md                         │
│ - solver_ballast_plan.csv                                    │
│ - optimizer_ballast_plan.xlsx                                │
│ - PIPELINE_CONSOLIDATED_AGI_*.xlsx                          │
└─────────────────────────────────────────────────────────────┘
```

**Pipeline Execution Flow Diagram**: Refer to `03_DOCUMENTATION/Pipeline Integration.md` section 1.1 (Visual Pipeline Flow)

### 1.3 Core Design Principles

1. **SSOT (Single Source of Truth)**: All data loaded from a single source
2. **Definition Split**: Clear separation of Forecast Tide vs Required WL, Draft vs Freeboard/UKC
3. **Gate Unified System**: Simultaneous enforcement of FWD/AFT/Freeboard/UKC gates
4. **Site-Agnostic**: Same logic for AGI/DAS (only profile changes)
5. **Iterative Refinement**: Improved accuracy through Hydrostatic Table re-interpolation

---

## 2. Execution File List and Roles

### 2.1 Main Orchestrator

**File**: `integrated_pipeline_defsplit_v2_gate270_split_v3_auditpatched_autodetect.py`

**Role**:

- Overall pipeline execution control
- Path resolution and profile loading
- SSOT CSV conversion (Tank, Hydro, Stage)
- Current_t sensor data auto-detection and injection
- Step 1~4 execution control
- Output file collection and Excel merging

**Key Functions**:

- `main()`: Main execution function
- `convert_tank_catalog_json_to_solver_csv()`: Tank catalog → CSV conversion
- `convert_hydro_engineering_json_to_solver_csv()`: Hydro Table → CSV conversion
- `build_stage_table_from_stage_results()`: stage_results.csv → stage_table_unified.csv
- `generate_stage_QA_csv()`: Stage QA CSV generation (includes Gate verification)
- `resolve_current_t_sensor_csv()`: Current_t sensor CSV auto-detection
- `inject_current_t_from_sensor_csv()`: Current_t injection and diff_audit.csv generation
- `apply_tank_overrides_from_profile()`: Apply tank overrides from profile
- `generate_gate_fail_report_md()`: Gate FAIL report generation
- `step_run_script()`: Step script execution (subprocess management)

**Input Arguments**:

- `--site`: Site label (AGI/DAS)
- `--profile_json`: Site profile JSON path
- `--current_t_csv`: Current_t sensor CSV path (auto-detection available)
- `--current_t_strategy`: Sensor value injection strategy (override/fill_missing)
- `--from_step`, `--to_step`: Execution range control
- `--fwd_max`, `--aft_min`: Gate values
- `--forecast_tide`, `--depth_ref`, `--ukc_min`: UKC calculation parameters

**Output**:

- `pipeline_out_<timestamp>/`: Output directory
  - `ssot/`: SSOT CSV files
  - `logs/`: Step-wise execution logs
  - `gate_fail_report.md`: Gate FAIL report
  - `TUG_Operational_SOP_DNV_ST_N001.md`: TUG operational SOP
  - `PIPELINE_CONSOLIDATED_AGI_*.xlsx`: Consolidated Excel file

나머지 부분을 계속 번역해 제공합니다. 붙여넣기 편의를 위해 섹션별로 나눕니다.

## Section 2: Execution File List and Roles (계속)

```markdown
### 2.2 Step 1: TR Excel Generation

**File**: `agi_tr_patched_v6_6_defsplit_v1.py`

**Role**:
- Stage-wise Draft/Trim/GM calculation (Engineering-grade)
- TR Excel file generation (`LCT_BUSHRA_AGI_TR_Final_v*.xlsx`)
- CSV mode: `stage_results.csv` generation (SSOT)

**Key Functions**:
- `solve_stage()`: Stage-wise Draft/Trim/GM calculation
- `_load_hydro_table()`: Hydrostatic Table loading
- `_load_gm2d_grid()`: GM 2D Grid loading
- `gm_2d_bilinear()`: GM 2D interpolation (DISP×TRIM)
- `create_workbook_from_scratch()`: Excel workbook creation

**Input**:
- `Hydro_Table_Engineering.json`: Hydrostatic Table
- `LCT_BUSHRA_GM_2D_Grid.json`: GM 2D Grid (optional)
- `tank_catalog_from_tankmd.json`: Tank catalog

**Output**:
- `LCT_BUSHRA_AGI_TR_Final_v*.xlsx`: TR Excel file
- `stage_results.csv`: Stage results CSV (CSV mode)

**Features**:
- Engineering-grade calculation: Hydro table interpolation, GM 2D interpolation
- Frame-based coordinate system: Frame 0 = AP (AFT), Frame increase = FWD, Midship = Frame 30.151 → x = 0.0
- Coordinate conversion: `x = 30.151 - Fr` (x > 0 = AFT, x < 0 = FWD)
- SSOT enforcement: Hydro table required (fallback removed)

### 2.3 Step 1b: stage_results.csv Generation

**Execution**: `agi_tr_patched_v6_6_defsplit_v1.py csv`

**Role**:
- Execute TR script in CSV mode to generate `stage_results.csv`
- SSOT Stage definition (9 stages: Stage 1, 2, 3, 4, 5, 5_PreBallast, 6A_Critical, 6C, 7)

**Output**:
- `stage_results.csv`: Stage-wise Draft/Trim/Disp_t data

**Importance**:
- SSOT for all subsequent reports/verification scripts
- `ops_final_r3_integrated_defs_split_v4_patched.py` loads Stage definitions from this file
- `stage_wise_load_transfer_excel_patched.py` loads Stage Summary from this file

### 2.4 Step 2: OPS Integrated Report

**File**: `ops_final_r3_integrated_defs_split_v4_patched.py`

**Role**:
- OPS integrated report generation (Excel + Markdown)
- Engineering-grade calculation integration (uses agi_tr_patched engine)
- SSOT Stage definition loading (`stage_results.csv`)

**Key Functions**:
- `generate_ops_report()`: OPS report generation
- `load_stage_data_from_ssot()`: Load Stage data from stage_results.csv

**Input**:
- `stage_results.csv`: SSOT Stage definition
- `Hydro_Table_Engineering.json`: Hydrostatic Table
- `LCT_BUSHRA_GM_2D_Grid.json`: GM 2D Grid (optional)

**Output**:
- `OPS_FINAL_R3_AGI_Ballast_Integrated.xlsx`: OPS Excel report
- `OPS_FINAL_R3_Report_Integrated.md`: OPS Markdown report

**Features**:
- SSOT integration: Load Stage definitions from `stage_results.csv` (hardcoding removed)
- Engineering-grade: Hydro table interpolation, GM 2D interpolation
- Includes VOID3 analysis

### 2.5 Step 3: LP Solver (Gate Compliance)

**File**: `ballast_gate_solver_v4.py`

**Role**:
- Linear Programming-based Ballast Plan generation
- Gate compliance enforcement (FWD_MAX, AFT_MIN, Freeboard, UKC)
- Operability enforcement (DISCHARGE_ONLY, FILL_ONLY, BLOCKED)

**Key Functions**:
- `solve_ballast_plan()`: LP Solver execution
- `_build_lp_problem()`: LP problem construction
- `_apply_hydro_iteration()`: Hydrostatic Table re-interpolation

**Input**:
- `tank_ssot_for_solver.csv`: Tank SSOT
- `hydro_table_for_solver.csv`: Hydro Table SSOT
- `stage_table_unified.csv`: Stage Table SSOT

**Output**:
- `solver_ballast_plan.csv`: Tank-wise Ballast Plan
- `solver_ballast_summary.csv`: Stage-wise summary
- `solver_ballast_stage_plan.csv`: Stage-wise Ballast Plan

**Features**:
- Definition-split: Forecast Tide vs Required WL separation
- Unified gates: Simultaneous enforcement of FWD/AFT/Freeboard/UKC
- Iterative refinement: Hydrostatic Table re-interpolation (2 iterations)

### 2.6 Step 4: Optimizer (Heuristic Optimization)

**File**: `Untitled-2_patched_defsplit_v1_1.py`

**Role**:
- Heuristic-based Ballast Plan optimization
- Time/capacity priority selection available
- BWRB (Ballast Water Record Book) logging

**Key Functions**:
- `optimize_ballast_plan()`: Optimization execution
- `_heuristic_selection()`: Heuristic tank selection

**Input**:
- `tank_ssot_for_solver.csv`: Tank SSOT
- `hydro_table_for_solver.csv`: Hydro Table SSOT
- `stage_table_unified.csv`: Stage Table SSOT

**Output**:
- `optimizer_ballast_plan.xlsx`: Optimized Ballast Plan Excel
- `optimizer_plan.csv`: Optimized Ballast Plan CSV
- `optimizer_summary.csv`: Optimization summary

**Features**:
- AFT_Limit_m used as upper limit (MAX) (AFT_MIN already enforced in Step 3)
- Time priority or capacity priority selection available

### 2.8 Step 4b: Ballast Sequence Generator (Option 2 Implementation Complete)

**File**: `ballast_sequence_generator.py`, `checklist_generator.py`

**Role**:
- Convert Ballast plan to execution sequence
- Option 2 implementation: Option/execution separation, Start_t/Target_t carry-forward

**Key Functions**:
- `generate_sequence_with_carryforward()`: Execution sequence generation (Start_t/Target_t chain, Stage 6B excluded)
- `generate_option_plan()`: Option plan generation (Delta_t centered, Stage 6B included)
- `export_to_option_dataframe()`: Option plan DataFrame generation
- `export_to_exec_dataframe()`: Execution sequence DataFrame generation
- `export_option_to_csv()`, `export_exec_to_csv()`: Separate CSV generation

**Input**:
- `ballast_plan_df`: Ballast plan (Optimizer or Solver output)
- `profile`: Site Profile (Gate definitions, etc.)
- `stage_drafts`: Stage-wise Draft information
- `tank_catalog_df`: Tank catalog (capacity, Current_t, etc.)

**Output**:
- `BALLAST_OPTION.csv`: Planning level (Delta_t centered, all stages included)
- `BALLAST_EXEC.csv`: Execution sequence (Start_t/Target_t chain, Stage 6B excluded)
- `BALLAST_SEQUENCE.csv`: Legacy (compatibility)
- `BALLAST_SEQUENCE.xlsx`: Excel (Ballast_Option, Ballast_Exec, Ballast_Sequence sheets)
- `BALLAST_OPERATIONS_CHECKLIST.md`: Operational checklist
- `HOLD_POINT_SUMMARY.csv`: Hold Point summary

**Core Logic (Option 2):**
1. **Start_t/Target_t carry-forward**:
   ```python
   tank_state: Dict[str, float] = initial_tank_current.copy()
   for step in sequence:
       start_t = tank_state.get(tank_id, 0.0)  # Previous step's target_t
       target_t = start_t + delta_t
       # Tank capacity verification
       if target_t > capacity_t:
           target_t = capacity_t
           delta_t = target_t - start_t
       tank_state[tank_id] = target_t  # Update for next step
```

2. **Stage 6B Separation**:
   - `OPTIONAL_STAGES = ["Stage 6B Tide Window"]` constant definition
   - `exclude_optional_stages=True` parameter to exclude from execution sequence
   - `generate_option_plan()`: Option plan includes Stage 6B
3. **Tank Capacity Verification**:
   - Automatic clipping when `target_t > Capacity_t`

**Features**:

- Clear separation of option/execution distinguishes planning and execution sequence
- Start_t/Target_t carry-forward accurately tracks tank state
- Stage 6B separation ensures execution sequence integrity
- Excel output includes 3 sheets (Option, Exec, Legacy)

### 2.9 Step 4c: Valve Lineup Generator

**File**: `valve_lineup_generator.py`

**Role**:

- Add valve lineup information to Ballast Sequence
- Generate operational procedures

**Input**:

- `BALLAST_SEQUENCE.csv`: Ballast Sequence
- `valve_map.json`: Valve mapping information

**Output**:

- `BALLAST_SEQUENCE_WITH_VALVES.md`: Operational procedures with valve lineup

**Features**:

- Automatic generation of Fill/Discharge valve sequence per tank
- Includes safety procedures (vent, emergency valves)

### 2.10 Auxiliary Scripts

#### 2.10.1 GM Verification

**File**: `verify_gm_stability_v2b.py`

**Role**:

- Stage-wise GM verification
- CLAMP range detection (VERIFY_CLAMP_RANGE)
- FSM coefficient verification (VERIFY_FSM_MISSING)
- GM_eff calculation (GM - FSM/Displacement)

**Key Features**:

- **GM 2D Grid bilinear interpolation**: 2D interpolation based on DISP×TRIM axes
- **Automatic CLAMP range detection**: Sets VERIFY_CLAMP_RANGE status for values outside GM Grid boundaries
- **FSM integration**: GM_eff calculation using FSM coefficients (`GM_eff = GM_raw - FSM/Displacement`)
- **CLAMP summary report**: Automatically generated by `summarize_clamp_report.py`

**Input**:

- `pipeline_stage_QA.csv`: Stage QA data (includes Disp_t, Trim_cm)
- `LCT_BUSHRA_GM_2D_Grid.json`: GM 2D Grid (DISP×TRIM axes, includes `grid_axis` metadata)
- `Tank_FSM_Coeff.json`: FSM coefficients (optional, t·m units)

**Output**:

- `gm_stability_verification_v2b.csv`: GM verification results
  - Columns: Stage, Disp_t, Trim_cm, GM_raw, GM_eff, FSM_tm, CLAMP_Status, VERIFY_CLAMP_RANGE, VERIFY_FSM_MISSING
  - CLAMP_Status: "IN_RANGE" | "CLAMPED" | "OUT_OF_RANGE"
  - VERIFY_CLAMP_RANGE: "PASS" | "WARN" | "FAIL"
  - VERIFY_FSM_MISSING: "PASS" | "WARN" (when FSM coefficients missing)

**Features**:

- Engineering-grade: Uses actual GM Grid interpolation (fallback values removed)
- FSM impact reflected: Actual stability evaluation with GM_eff
- CLAMP detection: Automatic detection and warning for values outside Grid range

#### 2.7.2 GM Grid Generation

**File**: `build_gm_grid_json_v2.py`

**Role**:

- GM Table CSV → GM Grid JSON conversion
- DISP×TRIM axis standardization
- `grid_axis` metadata addition

**Key Improvements (v2)**:

- **Axis alignment standardization**: TRIM × DISP → DISP × TRIM (standardized)
- **Metadata addition**: Explicit axis information with `grid_axis` field (`{"x": "DISP", "y": "TRIM"}`)
- **Compatibility**: Fully compatible with `verify_gm_stability_v2b.py`
- **Interpolation efficiency**: Improved interpolation performance with DISP×TRIM axes

**Input**:

- `GM_table.csv`: GM Table (long format or matrix format)
  - Long format: `DISP, TRIM, GM` columns
  - Matrix format: rows=TRIM, columns=DISP

**Output**:

- `LCT_BUSHRA_GM_2D_Grid.json`: GM 2D Grid JSON
  - Structure: `{"grid_axis": {"x": "DISP", "y": "TRIM"}, "data": {...}, "x_axis": [...], "y_axis": [...]}`
  - `x_axis`: DISP value array (sorted)
  - `y_axis`: TRIM value array (sorted)
  - `data`: 2D Grid data (DISP×TRIM matrix)

**Features**:

- Ensures consistency with standardized axis alignment
- Clarifies Grid structure with metadata
- Fully compatible with `verify_gm_stability_v2b.py`

#### 2.7.3 FSM Conversion

**File**: `convert_fsm_knm_to_tm.py`

**Role**:

- FSM coefficient unit conversion (kN·m → t·m)
- Conversion formula: `t·m = (kN·m) / 9.80665`

**Input**:

- `Tank_FSM_Coeff_kNm.json`: FSM coefficients (kN·m)

**Output**:

- `Tank_FSM_Coeff.json`: FSM coefficients (t·m)

#### 2.7.4 Hold Point Management

**File**: `hold_point_manager.py`, `hold_point_cli.py`, `hold_point_recalculator.py`

**Role**:

- Hold Point measurement processing
- GO/RECALC/STOP determination (±2cm/±4cm criteria)
- Recalculation logic

#### 2.7.5 Excel Finalization

**File**: `ballast_excel_finalize.py`

**Role**:

- Excel file formula finalization (COM post-processing)
- RefreshAll + CalculateFullRebuild
- Calc_Log sheet generation

### 2.11 Complete Pipeline Execution File List (v4.4 Update)

**Latest Verification Date**: 2025-12-29
**Total Execution Files**: 21 (excluding duplicates, including modules)

#### 2.11.1 Required Execution Files (Main Pipeline Steps)

| Step              | Script Filename                                              | Default Path                                                 | Execution Method | Description                                           |
| ----------------- | ------------------------------------------------------------ | ------------------------------------------------------------ | ---------------- | ----------------------------------------------------- |
| **Step 0**  | `agi_spmt_unified.py`                                      | `spmt v1/agi_spmt_unified.py`                              | `subprocess`   | SPMT cargo input generation (optional)                |
| **Step 1**  | `agi_tr_patched_v6_6_defsplit_v1.py`                       | `agi_tr_patched_v6_6_defsplit_v1.py`                       | `subprocess`   | TR Excel generation (optional)                        |
| **Step 1b** | `agi_tr_patched_v6_6_defsplit_v1.py`                       | Same                                                         | `subprocess`   | `stage_results.csv` generation (required, csv mode) |
| **Step 2**  | `ops_final_r3_integrated_defs_split_v4_patched_TIDE_v1.py` | `ops_final_r3_integrated_defs_split_v4_patched_TIDE_v1.py` | `subprocess`   | OPS Integrated report (Excel + MD)                    |
| **Step 3**  | `ballast_gate_solver_v4_TIDE_v1.py`                        | `tide/ballast_gate_solver_v4_TIDE_v1.py`                   | `subprocess`   | Ballast Gate Solver (LP)                              |
| **Step 4**  | `Untitled-2_patched_defsplit_v1_1.py`                      | `Untitled-2_patched_defsplit_v1_1.py`                      | `subprocess`   | Ballast Optimizer (optional)                          |
| **Step 5**  | `bryan_template_unified_TIDE_v1.py`                        | `tide/bryan_template_unified_TIDE_v1.py`                   | `subprocess`   | Bryan Template generation and population              |

#### 2.11.2 Optional Execution Files (Optional Steps)

| Step              | Script Filename                   | Default Path                      | Execution Method    | Activation Condition      |
| ----------------- | --------------------------------- | --------------------------------- | ------------------- | ------------------------- |
| **Step 4b** | `ballast_sequence_generator.py` | `ballast_sequence_generator.py` | `import` (module) | `--enable-sequence`     |
| **Step 4b** | `checklist_generator.py`        | `checklist_generator.py`        | `import` (module) | `--enable-sequence`     |
| **Step 4c** | `valve_lineup_generator.py`     | `valve_lineup_generator.py`     | `import` (module) | `--enable-valve-lineup` |

#### 2.11.3 Dependent Execution Files (Dependencies)

| Parent Script                         | Dependent Script                       | Default Path                           | Execution Method      | Description                                    |
| ------------------------------------- | -------------------------------------- | -------------------------------------- | --------------------- | ---------------------------------------------- |
| `bryan_template_unified_TIDE_v1.py` | `create_bryan_excel_template_NEW.py` | `create_bryan_excel_template_NEW.py` | `subprocess`        | Bryan Template generation (internal to Step 5) |
| `bryan_template_unified_TIDE_v1.py` | `populate_template.py`               | `populate_template.py`               | `import` (embedded) | Template population logic (internal to Step 5) |

#### 2.11.4 Post-Processing Execution Files (Post-Processing)

| Script Filename               | Default Path                       | Execution Method | Activation Condition                                      | Description                       |
| ----------------------------- | ---------------------------------- | ---------------- | --------------------------------------------------------- | --------------------------------- |
| `excel_com_recalc_save.py`  | `tide/excel_com_recalc_save.py`  | `subprocess`   | When `EXCEL_COM_RECALC_OUT` environment variable is set | Excel formula recalculation (COM) |
| `ballast_excel_finalize.py` | `tide/ballast_excel_finalize.py` | `subprocess`   | Auto-executes when file exists                            | Excel formula finalization        |

#### 2.11.5 Utility Execution Files (Utilities)

| Script Filename                 | Default Path                    | Execution Method     | Activation Condition                              | Description                                          |
| ------------------------------- | ------------------------------- | -------------------- | ------------------------------------------------- | ---------------------------------------------------- |
| `compile_headers_registry.py` | `compile_headers_registry.py` | `import` (dynamic) | Auto-executes when `HEADERS_MASTER.xlsx` exists | Compile HEADERS_MASTER.xlsx → headers_registry.json |
| `debug_report.py`             | `debug_report.py`             | `import` (dynamic) | `--debug_report` or `--auto_debug_report`     | Debug report generation (optional)                   |

#### 2.11.6 Module Dependencies (Module Dependencies)

| Module Path                     | Usage Location  | Execution Method | Description                                             |
| ------------------------------- | --------------- | ---------------- | ------------------------------------------------------- |
| `ssot.gates_loader`           | Step 4b         | `import`       | `SiteProfile`, `load_agi_profile` (profile loading) |
| `ssot.data_quality_validator` | Step 3, Step 4b | `import`       | `DataQualityValidator` (Tidying First Implementation) |
| `tide.tide_ukc_engine`        | Multiple Steps  | `import`       | Tide/UKC calculation SSOT engine                        |
| `tide.tide_constants`         | Multiple Steps  | `import`       | Tide/UKC constants                                      |

#### 2.11.7 Pre-Step Execution Files (Optional)

| Script Filename          | Default Path             | Execution Method            | Activation Condition             | Description                        |
| ------------------------ | ------------------------ | --------------------------- | -------------------------------- | ---------------------------------- |
| `tide_stage_mapper.py` | `tide_stage_mapper.py` | Manual execution (Pre-Step) | When `--tide_windows` provided | Stage-wise tide mapping (AGI-only) |

#### 2.11.8 Execution File Statistics

| Category                                           | Count        | Notes                                      |
| -------------------------------------------------- | ------------ | ------------------------------------------ |
| **Required Execution Files (subprocess)**    | 4            | Step 1b, Step 2, Step 3 (always executed)  |
| **Optional Execution Files (subprocess)**    | 3            | Step 0, Step 1, Step 4, Step 5             |
| **Optional Execution Files (import module)** | 3            | Step 4b, Step 4c                           |
| **Dependent Execution Files**                | 2            | Internal Bryan Template calls              |
| **Post-Processing Execution Files**          | 2            | Excel finalization                         |
| **Utility Execution Files**                  | 2            | Headers registry compilation, Debug report |
| **Module Dependencies**                      | 4            | SSOT modules (import)                      |
| **Pre-Step Execution Files**                 | 1            | Tide mapping (manual execution)            |
| **Total**                                    | **21** | (excluding duplicates, including modules)  |

**Note**:

- All execution files are called from `integrated_pipeline_defsplit_v2_gate270_split_v3_auditpatched_autodetect_TIDE_v1.py` via `step_run_script()`, `subprocess.run()`, or dynamic `import`.
- Script paths are auto-detected by `resolve_script_path()` function (automatically recognizes parent folder scripts even when executed from `tide/` directory).

---

### 2.12 bplus_inputs Folder Structure and Input Data Mapping (v4.5 New)

**Latest Update**: 2025-12-29
**Purpose**: Clarify pipeline input data sources and search order

#### 2.12.1 Folder Structure

```
01_EXECUTION_FILES/bplus_inputs/
├── data/                                    # Frame ↔ x conversion data
│   └── Frame_x_from_mid_m.json            # Frame coordinate system conversion table
│
├── profiles/                                # Site profile
│   └── AGI.json                            # AGI site profile (default)
│
├── stage_schedule.csv                      # Stage-wise timestamps (for tide interpolation)
├── stage_schedule.sample.csv               # Sample file
├── tide_windows_AGI.json                  # Stage-wise tide window definitions
├── water tide_202512.xlsx                  # Tide data (Excel, 2025-12)
│
├── Hydro_Table_Engineering.json           # Hydrostatic table (engineering version)
├── LCT_BUSHRA_GM_2D_Grid.json            # GM 2D Grid (for GM verification)
├── Tank_FSM_Coeff.json                    # FSM coefficients (for GM verification)
│
├── Acceptance_Criteria.json               # Acceptance criteria
├── GM_Min_Curve.json                      # GM minimum curve
├── ISCODE_Criteria.json                   # ISCODE criteria
├── Securing_Input.json                    # Securing input
└── Structural_Limits.json                 # Structural limits
```

#### 2.12.2 Pipeline Step-by-Step Input File Mapping

| Step                                | Input File                       | Path                       | Usage Purpose                                  | Required |
| ----------------------------------- | -------------------------------- | -------------------------- | ---------------------------------------------- | -------- |
| **Step 1** (TR Excel)         | `Hydro_Table_Engineering.json` | `bplus_inputs/`          | Hydrostatic data                               | Required |
|                                     | `data/Frame_x_from_mid_m.json` | `bplus_inputs/data/`     | Frame ↔ x conversion                          | Required |
| **Step 2** (OPS)              | `profiles/AGI.json`            | `bplus_inputs/profiles/` | Site profile (auto-detected)                   | Required |
|                                     | `Hydro_Table_Engineering.json` | `bplus_inputs/`          | Hydrostatic data                               | Required |
| **Step 2** (Tide Integration) | `stage_schedule.csv`           | `bplus_inputs/`          | Stage-wise timestamps (for tide interpolation) | Optional |
|                                     | `water tide_202512.xlsx`       | `bplus_inputs/`          | Tide data (Excel)                              | Optional |
|                                     | `tide_windows_AGI.json`        | `bplus_inputs/`          | Stage-wise tide window definitions             | Optional |
| **Step 3** (Solver)           | `Hydro_Table_Engineering.json` | `bplus_inputs/`          | Hydrostatic data (indirect)                    | Required |
| **Step 5** (Post-processing)  | `LCT_BUSHRA_GM_2D_Grid.json`   | `bplus_inputs/`          | GM 2D Grid (GM verification)                   | Optional |
|                                     | `Tank_FSM_Coeff.json`          | `bplus_inputs/`          | FSM coefficients (GM verification)             | Optional |
|                                     | `Acceptance_Criteria.json`     | `bplus_inputs/`          | Acceptance criteria                            | Optional |
|                                     | `GM_Min_Curve.json`            | `bplus_inputs/`          | GM minimum curve                               | Optional |
|                                     | `ISCODE_Criteria.json`         | `bplus_inputs/`          | ISCODE criteria                                | Optional |
|                                     | `Securing_Input.json`          | `bplus_inputs/`          | Securing input                                 | Optional |
|                                     | `Structural_Limits.json`       | `bplus_inputs/`          | Structural limits                              | Optional |

#### 2.12.3 Key Input File Details

##### 1. `Hydro_Table_Engineering.json`

- **Purpose**: Hydrostatic table (engineering version)
- **Format**: JSON (Disp_t, Draft_m, MTC, TPC, LCF, etc.)
- **Usage Location**: Step-1, Step-2, Step-3
- **Required**: Required
- **Search Path**:
  - `inputs_dir/bplus_inputs/Hydro_Table_Engineering.json`
  - `base_dir/bplus_inputs/Hydro_Table_Engineering.json`
  - Can be explicitly specified with `--hydro` argument

##### 2. `stage_schedule.csv`

- **Purpose**: Stage-wise timestamps (for tide table interpolation)
- **Format**: CSV (`Stage,Timestamp`)
- **Usage Location**: Step-2 (Tide Integration)
- **Required**: Optional (used with `--tide_table`)
- **Example**:
  ```csv
  Stage,Timestamp
  Stage 1,2025-12-01 08:00:00
  Stage 6A_Critical (Opt C),2025-12-01 20:00:00
  ```

##### 3. `tide_windows_AGI.json`

- **Purpose**: Stage-wise tide window definitions (start/end time, statistics)
- **Format**: JSON (`{"tide_windows": {"Stage 1": {"start": "...", "end": "...", "stat": "mean"}}}`)
- **Usage Location**: Step-2 (Tide Integration, optional)
- **Required**: Optional

##### 4. `water tide_202512.xlsx`

- **Purpose**: Tide data (Excel format, 2025-12)
- **Format**: Excel (576 lines)
- **Usage Location**: Step-2 (Tide Integration, specified with `--tide_table` argument)
- **Required**: Optional

##### 5. `profiles/AGI.json`

- **Purpose**: Site profile (tank operability, gates, tide/UKC settings, etc.)
- **Format**: JSON
- **Usage Location**: Step-2, Step-3
- **Required**: Required (auto-detection supported)
- **⚠️ Pre-Execution Configuration**: This profile file can be **edited before pipeline execution** to adjust gate limits, pump rates, tide/UKC parameters, and tank operability settings. Profile values are loaded at pipeline startup, so all adjustments must be made **before running the pipeline**.
- **Search Path**:
  - `inputs_dir/bplus_inputs/profiles/AGI.json`
  - `inputs_dir/bplus_inputs/profiles/site_AGI.json`
  - `inputs_dir/bplus_inputs/site_profile_AGI.json`

##### 6. `data/Frame_x_from_mid_m.json`

- **Purpose**: Frame ↔ x conversion table
- **Format**: JSON
- **Usage Location**: Step-1
- **Required**: Required
- **Search Path**:
  - `base_dir/bplus_inputs/data/Frame_x_from_mid_m.json`
  - `base_dir/bplus_inputs/Frame_x_from_mid_m.json`
  - `02_RAW_DATA/Frame_x_from_mid_m.json` (fallback)

#### 2.12.4 `02_RAW_DATA` vs `01_EXECUTION_FILES/bplus_inputs` Comparison

| Item             | `02_RAW_DATA`              | `01_EXECUTION_FILES/bplus_inputs` |
| ---------------- | ---------------------------- | ----------------------------------- |
| Location         | Project root                 | Execution file directory            |
| Purpose          | Original data repository     | Input data at execution time        |
| File Duplication | Some files may be duplicated | Some files may be duplicated        |
| Priority         | Fallback                     | Primary (near execution files)      |
| Search Order     | 2nd priority                 | 1st priority                        |

**Pipeline Search Order**:

1. `inputs_dir/bplus_inputs/` (or `base_dir/bplus_inputs/`)
2. `02_RAW_DATA/` (fallback)

#### 2.12.5 Tide Integration Priority (5-tier, Detailed)

**Reference**: For detailed Tide Integration logic and priority, refer to:

- `03_DOCUMENTATION/Pipeline Integration.md` section 4 (Tide Integration details)
- `03_DOCUMENTATION/00_CORE_ARCHITECTURE/17_TIDE_UKC_Calculation_Logic.md` (mathematical model and Fallback mechanism)

**5-tier Priority Summary**:

1. **Priority 0**: CLI `--forecast_tide` (highest priority, v2.11 update)
2. **Priority 1**: `--stage_tide_csv` (only when CLI not available)
3. **Priority 2**: `tide_windows` method (AGI project standard)
4. **Priority 3**: `stage_schedule` method (fallback, simulation support)
5. **Priority 4**: CLI `--forecast_tide` (fillna, safety mechanism)

**Details**: Refer to `03_DOCUMENTATION/Pipeline Integration.md` section 4.1

## Section 3: Step-by-Step Detailed Logic

```markdown
## 3. Step-by-Step Detailed Logic

### 3.1 Step 1: TR Excel Generation

**Execution Condition**: `args.from_step <= 1 <= args.to_step`

**Execution Command**:
```python
python agi_tr_patched_v6_6_defsplit_v1.py
```

**Logic**:

1. Load Hydrostatic Table (`Hydro_Table_Engineering.json`)
2. Load GM 2D Grid (`LCT_BUSHRA_GM_2D_Grid.json`, optional)
3. Stage-wise calculation:
   - Define load items (TR1, TR2, Preballast, etc.)
   - Call `solve_stage()`:
     - Displacement calculation
     - Hydro table interpolation (LCF, MCTC, TPC)
     - Draft/Trim calculation
     - GM 2D interpolation (DISP×TRIM)
4. Excel workbook creation:
   - Stage-wise sheets
   - Hydro table sheet
   - GM Grid sheet
   - Frame table sheet

**Output**:

- `LCT_BUSHRA_AGI_TR_Final_v*.xlsx`: TR Excel file
- `RORO_Summary.png`: RORO summary graph (optional)

**Error Handling**:

- Step 1 failure: Only warning output (optional step)
- If `stage_results.csv` already exists, Step 1b can be skipped

### 3.2 Step 1b: stage_results.csv Generation

**Execution Condition**: `args.from_step <= 1 <= args.to_step` AND `stage_results.csv` does not exist

**Execution Command**:

```python
python agi_tr_patched_v6_6_defsplit_v1.py csv
```

**Logic**:

1. Execute TR script in CSV mode
2. Output stage-wise results to CSV:
   - Stage, Dfwd_m, Daft_m, Disp_t, Tmean_m, Trim_cm, etc.
3. Generate `stage_results.csv` (SSOT)

**Error Handling**:

- Step 1b failure: Pipeline stops (`return 1`)
- If `stage_results.csv` is missing, subsequent steps cannot execute

### 3.3 PREP: SSOT CSV Conversion

**Execution Order**: After Step 1b, before Step 2

#### 3.3.1 Tank SSOT Conversion

**Function**: `convert_tank_catalog_json_to_solver_csv()`

**Logic**:

1. Load `tank_catalog_from_tankmd.json`
2. For each tank:
   - Coordinate conversion: `x_from_mid_m = MIDSHIP_FROM_AP_M - lcg_from_ap_m`
     - `lcg_from_ap_m`: Tank LCG (AP reference, m)
     - `x_from_mid_m > 0`: AFT zone, `x_from_mid_m < 0`: FWD zone
   - Keyword filtering: `include_keywords` (default: BALLAST, VOID, FWB, FW, DB)
   - Set `use_flag`: "Y" when keyword matches
   - Set Priority weight: FWB2=1.0, VOIDDB2=2.0, VOIDDB1=3.0, others=5.0
3. CSV output: `tank_ssot_for_solver.csv`

**Caution**: FWD zone tanks (`FWB1.*`, `FWB2.*`) are bow tanks, so using them as "stern ballast" violates physical laws and breaks gates. For AFT-up, use AFT zone tanks.

**Output Columns**:

- Tank, Capacity_t, x_from_mid_m, Current_t, Min_t, Max_t, mode, use_flag, pump_rate_tph, priority_weight

#### 3.3.2 Current_t Sensor Injection

**Function**: `inject_current_t_from_sensor_csv()`

**Auto-Detection Logic** (`resolve_current_t_sensor_csv()`):

1. Check explicit `--current_t_csv` argument
2. Search fixed path candidates:
   - `inputs_dir/current_t_sensor.csv`
   - `inputs_dir/current_t.csv`
   - `inputs_dir/sensors/current_t_sensor.csv`
   - `inputs_dir/sensors/current_t.csv`
   - `inputs_dir/plc/current_t.csv`
   - `inputs_dir/iot/current_t.csv`
3. Fallback auto-detection:
   - Search directories: `inputs_dir`, `inputs_dir/sensors`, `base_dir`, `base_dir/sensors`
   - Pattern: `current_t_*.csv`, `current_t-*.csv`
   - Selection criteria: Latest modification time (mtime) priority

**Injection Logic**:

1. Load sensor CSV and normalize columns:
   - Tank identifier: Tank | tank_id | id | tag | name
   - Value (priority):
     1) Current_t | tons | ton | amount_t | value_t
     2) level_pct | level_percent (uses Capacity_t)
     3) volume_m3 | m3 + optional spgr (default 1.0)
2. Matching strategy:
   - Exact match: Tank ID exactly matches
   - Group match: Base name matches (e.g., FWB2 → FWB2.P, FWB2.S equal distribution)
3. Apply strategy:
   - `override`: Always overwrite with sensor value
   - `fill_missing`: Inject only when existing value is 0.0
4. Clamping: Limit within Min_t/Max_t range
5. Generate diff_audit.csv:
   - Compare before/after injection values
   - Record clamping status
   - Record skip reason

**Output**:

- `tank_ssot_for_solver.csv`: Updated tank SSOT
- `diff_audit.csv`: Injection history (TS, Tank, CurrentOld_t, ComputedNew_t, Delta_t, ClampedFlag, Updated, SkipReason)

#### 3.3.3 Tank Overrides Application

**Function**: `apply_tank_overrides_from_profile()`

**Logic**:

1. Load `tank_overrides` section from Site profile
2. For each override:
   - Exact match: Tank ID exactly matches
   - Base match: Base name matches (e.g., FW2 → FW2.P, FW2.S)
     - Base match requires explicit permission (`allow_base_match: true`)
3. Apply override:
   - `use_flag`: Y/N
   - `mode`: FILL_DISCHARGE, DISCHARGE_ONLY, FILL_ONLY, BLOCKED
   - `pump_rate_tph`: Pump rate
   - `operability`: NORMAL, PRE_BALLAST_ONLY, DISCHARGE_ONLY, etc.

**Output**:

- `tank_ssot_for_solver.csv`: Tank SSOT with overrides applied

#### 3.3.4 Hydro SSOT Conversion

**Function**: `convert_hydro_engineering_json_to_solver_csv()`

**Logic**:

1. Load `Hydro_Table_Engineering.json`
2. Column normalization:
   - `MCTC_t_m_per_cm` → `MTC_t_m_per_cm`
   - `LCF_m_from_midship` → `LCF_m`
3. Verify required columns: Tmean_m, TPC_t_per_cm, MTC_t_m_per_cm, LCF_m
4. Add LBP_m (use default if missing)
5. CSV output: `hydro_table_for_solver.csv`

**Output Columns**:

- Tmean_m, TPC_t_per_cm, MTC_t_m_per_cm, LCF_m, LBP_m

#### 3.3.5 Stage Table Build

**Function**: `build_stage_table_from_stage_results()`

**Logic**:

1. Load `stage_results.csv`
2. Column inference:
   - Stage: Stage | stage_name | name
   - FWD Draft: Dfwd_m | FWD_m | Fwd Draft(m)
   - AFT Draft: Daft_m | AFT_m | Aft Draft(m)
   - Displacement: Disp_t | disp | displacement_t
   - Tmean: Tmean_m | tmean | mean_draft_m
   - Trim: Trim_cm | trim
3. Draft clipping: Prevent exceeding Molded Depth (D_vessel_m)
4. Add Gate values:
   - FWD_MAX_m: `fwd_max_m` (default 2.70m)
   - AFT_MIN_m: `aft_min_m` (default 2.70m)
   - AFT_MAX_m: `aft_max_m_for_optimizer` (default 3.50m)
5. Critical stage marking:
   - Match with `critical_regex` or `critical_stage_list`
   - Determine Gate-B application
6. Add UKC parameters (if provided):
   - Forecast_Tide_m, Depth_Ref_m, UKC_MIN_m
7. Hydro range verification:
   - Check if Displacement is within Hydro table range
   - Set HardStop flag
8. CSV output: `stage_table_unified.csv`

**Output Columns**:

- Stage, Current_FWD_m, Current_AFT_m, FWD_MAX_m, AFT_MIN_m, AFT_MAX_m, D_vessel_m, Forecast_Tide_m, Depth_Ref_m, UKC_MIN_m, Gate_B_Applies, HardStop, HardStop_Reason

#### 3.3.6 Stage QA CSV Generation

**Function**: `generate_stage_QA_csv()`

**Logic**:

1. Load `stage_table_unified.csv`
2. Set Draft source:
   - `Draft_FWD_m_raw`, `Draft_AFT_m_raw`: Original values
   - `Draft_FWD_m`, `Draft_AFT_m`: Updated when Solver results applied
   - `Draft_Source`: "raw" or "solver"
3. Freeboard calculation:
   - `Freeboard_FWD_m = D_vessel_m - Draft_FWD_m`
   - `Freeboard_AFT_m = D_vessel_m - Draft_AFT_m`
   - `Freeboard_Min_m = min(Freeboard_FWD_m, Freeboard_AFT_m)`
   - `Freeboard_Min_BowStern_m`: Explicit label (distinguished from linkspan freeboard)
4. Gate verification:
   - `Gate_FWD_Max`: FWD <= FWD_MAX_m (Chart Datum reference, only when applicable)
   - `Gate_AFT_Min`: AFT >= AFT_MIN_m
   - `Gate_Freeboard`: Freeboard_Min_m >= 0 (prevent deck wet/downflooding)
   - `Gate_UKC`: UKC >= UKC_MIN_m (when provided, prevent grounding)
   - `Gate_Hydro_Range`: Displacement within Hydro table range
   - `Gate_AFT_MIN_2p70`: AFT >= 2.70m (Gate-A, Captain, ensure propeller efficiency/propulsion)
   - `Gate_FWD_MAX_2p70_critical_only`: FWD <= 2.70m (Gate-B, Mammoet, Critical RoRo stages only)
     - Critical stage determination: `DEFAULT_CRITICAL_STAGE_REGEX` or profile `critical_stage_list`
     - Non-critical stages: `Gate_FWD_MAX_2p70_critical_only = "N/A"` (prevent false failure)
5. Margin calculation:
   - `FWD_Margin_m = FWD_MAX_m - Draft_FWD_m`
   - `AFT_Margin_m = Draft_AFT_m - AFT_MIN_m`
   - `AFT_Margin_2p70_m = Draft_AFT_m - 2.70`
   - `FWD_Margin_2p70_m = 2.70 - Draft_FWD_m`
6. HardStop synthesis:
   - `HardStop_Any`: Y/N
   - `HardStop_Reason`: Cause (OverDepth/DeckWet, HydroOutOfRange, etc.)
7. CSV output: `pipeline_stage_QA.csv`

**Output Columns**:

- Stage, Draft_FWD_m_raw, Draft_AFT_m_raw, Draft_FWD_m, Draft_AFT_m, Draft_Source, Freeboard_Min_m, Freeboard_Min_BowStern_m, Gate_FWD_Max, Gate_AFT_Min, Gate_Freeboard, Gate_UKC, Gate_Hydro_Range, Gate_AFT_MIN_2p70, Gate_FWD_MAX_2p70_critical_only, FWD_Margin_m, AFT_Margin_m, AFT_Margin_2p70_m, FWD_Margin_2p70_m, HardStop_Any, HardStop_Reason

### 3.4 Gate FAIL Report Generation

**Function**: `generate_gate_fail_report_md()`

**Execution Condition**: `--no_gate_report` flag not set

**Logic**:

1. Load `pipeline_stage_QA.csv`
2. Aggregate Gate violation stages:
   - Gate_FWD_Max, Gate_AFT_Min, Gate_Freeboard, Gate_UKC
   - GateA_AFT_MIN_2p70_PASS, GateB_FWD_MAX_2p70_CD_PASS
   - Gate_Hydro_Range, HardStop
3. Generate heuristics:
   - Warning when Current_t is mostly 0.0
   - Warning when Freeboard_Min_m < 0
   - Warning for unassessed UKC Gate
   - Warning for Hydro Range violation
   - Warning for HardStop detection
4. Generate Markdown report:
   - Executive Summary
   - Gate violation summary
   - Stage-wise Gate status table
   - Automatic cause estimation
   - Recommended actions

**Output**:

- `gate_fail_report.md`: Gate FAIL report

**Additional Sections**:

- DNV Mitigation Section (`append_dnv_mitigation_section_to_gate_report()`)
- TUG Operational SOP (`generate_tug_operational_sop_md()`)
- Solver Section (`append_solver_section_to_gate_report()`, after Step 3)

### 3.5 Step 2: OPS Integrated Report

**Execution Condition**: `args.from_step <= 2 <= args.to_step`

**Execution Command**:

```python
python ops_final_r3_integrated_defs_split_v4_patched.py
```

**Logic**:

1. Load SSOT Stage data:
   - Load Stage definitions from `stage_results.csv`
   - Remove hardcoded Stage definitions (SSOT integration)
2. Engineering-grade calculation:
   - Use `agi_tr_patched_v6_6_defsplit_v1` engine
   - Hydro table interpolation
   - GM 2D interpolation
3. Excel report generation:
   - Stage-wise sheets
   - VOID3 analysis sheet
   - Discharge strategy sheet
4. Markdown report generation:
   - Executive Summary
   - Stage Analysis
   - Calculation Methodology

**Output**:

- `OPS_FINAL_R3_AGI_Ballast_Integrated.xlsx`: OPS Excel report
- `OPS_FINAL_R3_Report_Integrated.md`: OPS Markdown report

**Features**:

- SSOT integration: Load Stage definitions from `stage_results.csv`
- Engineering-grade: Hydro table interpolation, GM 2D interpolation
- Includes VOID3 analysis

### 3.6 Step 3: LP Solver

**Execution Condition**: `args.from_step <= 3 <= args.to_step`

**Execution Command**:

```python
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
  --squat 0.0 \
  --safety_allow 0.0 \
  --forecast_tide <value> \
  --depth_ref <value> \
  --ukc_min <value> \
  --out_plan solver_ballast_plan.csv \
  --out_summary solver_ballast_summary.csv \
  --out_stage_plan solver_ballast_stage_plan.csv
```

**Logic**:

1. Load SSOT CSV:
   - `tank_ssot_for_solver.csv`: Tank data
   - `hydro_table_for_solver.csv`: Hydro Table
   - `stage_table_unified.csv`: Stage data
2. Construct LP problem:
   - Variables: Fill/Discharge amount for each tank (p_i, n_i)
   - Objective function: Minimize (or achieve target)
   - Constraints:
     - Gate compliance: FWD <= FWD_MAX, AFT >= AFT_MIN, Freeboard >= FB_MIN, UKC >= UKC_MIN
     - Tank capacity: Min_t <= Current_t + Δw <= Max_t
     - Operability: Enforce DISCHARGE_ONLY, FILL_ONLY, BLOCKED
3. Hydrostatic Table re-interpolation:
   - Calculate initial solution
   - Update Displacement
   - Re-interpolate Hydro table (LCF, MCTC, TPC)
   - Recalculate Draft/Trim
   - Iterate (default 2 times)
4. Execute LP Solver:
   - Use `scipy.optimize.linprog`
   - Return optimal solution or optimal approximate solution
5. Output results:
   - `solver_ballast_plan.csv`: Tank-wise Ballast Plan
   - `solver_ballast_summary.csv`: Stage-wise summary
   - `solver_ballast_stage_plan.csv`: Stage-wise Ballast Plan

**Output Columns** (solver_ballast_summary.csv):

- Stage, New_FWD_m, New_AFT_m, New_Trim_m, Delta_W_t, Gate_FWD_Max, Gate_AFT_Min, Gate_Freeboard, Gate_UKC

**Features**:

- Definition-split: Forecast Tide vs Required WL separation
- Unified gates: Simultaneous enforcement of FWD/AFT/Freeboard/UKC
- Iterative refinement: Hydrostatic Table re-interpolation

### 3.7 After Step 3: QA CSV Update

**Logic**:

1. Load `solver_ballast_summary.csv`
2. Update `pipeline_stage_QA.csv`:
   - `Draft_FWD_m`, `Draft_AFT_m`: Update with Solver results
   - `Draft_Source`: Change to "solver"
3. Re-verify Gates:
   - Re-verify Gates with Draft after Solver application
   - Recalculate Margins

**Output**:

- `pipeline_stage_QA.csv`: QA CSV with Solver results reflected

### 3.8 Step 4: Optimizer

**Execution Condition**: `args.from_step <= 4 <= args.to_step`

**Execution Command**:

```python
python Untitled-2_patched_defsplit_v1_1.py \
  --batch \
  --tank tank_ssot_for_solver.csv \
  --hydro hydro_table_for_solver.csv \
  --stage stage_table_unified.csv \
  --prefer_time \
  --iterate_hydro 2 \
  --out_plan optimizer_plan.csv \
  --out_summary optimizer_summary.csv \
  --out_stage_plan ballast_stage_plan.csv \
  --bwrb_out optimizer_bwrb_log.csv \
  --tanklog_out optimizer_tank_log.csv \
  --excel_out optimizer_ballast_plan.xlsx
```

**Logic**:

1. Load SSOT CSV
2. Heuristic optimization:
   - Select time priority or capacity priority
   - Determine tank selection and Fill/Discharge amounts
3. Verify Gate compliance:
   - AFT_Limit_m used as upper limit (MAX)
   - AFT_MIN already enforced in Step 3
4. Excel output:
   - Ballast Plan sheet
   - BWRB log sheet
   - Tank log sheet

**Output**:

- `optimizer_ballast_plan.xlsx`: Optimized Ballast Plan Excel
- `optimizer_plan.csv`: Optimized Ballast Plan CSV
- `optimizer_summary.csv`: Optimization summary
- `optimizer_bwrb_log.csv`: BWRB log
- `optimizer_tank_log.csv`: Tank log

### 3.11 Step 4b: Ballast Sequence Generator (Option 2 Implementation Complete)

**Execution Condition**: `args.from_step <= 4 <= args.to_step` AND `args.enable_sequence`

**Execution Command**:

```python
from ballast_sequence_generator import (
    generate_sequence_with_carryforward,
    generate_option_plan,
    export_to_option_dataframe,
    export_to_exec_dataframe,
    export_option_to_csv,
    export_exec_to_csv,
)

# Generate option plan (all stages included, Stage 6B included)
option_plan = generate_option_plan(
    ballast_plan_df,
    profile,
    stage_drafts,
    tank_catalog_df
)
option_df = export_to_option_dataframe(option_plan)
export_option_to_csv(option_df, "BALLAST_OPTION.csv")

# Generate execution sequence (Stage 6B excluded, Start_t/Target_t carry-forward)
exec_sequence = generate_sequence_with_carryforward(
    ballast_plan_df,
    profile,
    stage_drafts,
    tank_catalog_df,
    exclude_optional_stages=True
)
exec_df = export_to_exec_dataframe(exec_sequence)
export_exec_to_csv(exec_df, "BALLAST_EXEC.csv")
```

**Logic**:

1. Load Ballast Plan (Optimizer or Solver output)
2. Generate option plan (`generate_option_plan()`):
   - Include all stages (Stage 6B included)
   - Delta_t centered plan
3. Generate execution sequence (`generate_sequence_with_carryforward()`):
   - Determine stage order (priority-based sorting)
   - Filter optional stages (exclude Stage 6B)
   - Generate sequence for each stage:
     - Initialize tank state (Current_t)
     - Start_t/Target_t carry-forward
     - Verify and clip tank capacity
4. Excel output:
   - Generate 3 sheets in `BALLAST_SEQUENCE.xlsx`:
     - `Ballast_Option`: Option plan
     - `Ballast_Exec`: Execution sequence
     - `Ballast_Sequence`: Legacy format

**Output**:

- `BALLAST_OPTION.csv`: Planning level (Stage, Tank, Action, Delta_t, PumpRate, Priority, Rationale)
- `BALLAST_EXEC.csv`: Execution sequence (Stage, Step, Tank, Action, Start_t, Target_t, Time_h, Valve_Lineup, Hold_Point)
- `BALLAST_SEQUENCE.csv`: Legacy (compatibility)
- `BALLAST_SEQUENCE.xlsx`: Excel (3 sheets)
- `BALLAST_OPERATIONS_CHECKLIST.md`: Operational checklist

**Verification Points:**

- ✅ Stage 6B included in BALLAST_OPTION.csv
- ✅ Stage 6B excluded from BALLAST_EXEC.csv
- ✅ Start_t/Target_t chain continuity (same tank)
- ✅ Clipping when tank capacity exceeded

### 3.12 Step 4c: Valve Lineup Generator

**Execution Condition**: `args.from_step <= 4 <= args.to_step` AND `args.enable_valve_lineup`

**Logic**:

1. Load `BALLAST_SEQUENCE.csv`
2. Load `valve_map.json`
3. Add valve lineup information to each Step
4. Generate Markdown operational procedures

**Output**:

- `BALLAST_SEQUENCE_WITH_VALVES.md`: Operational procedures with valve lineup

### 3.13 Output File Collection

**Function**: `collect_all_output_files()`

**Logic**:

1. Collect Step 1 outputs:
   - `LCT_BUSHRA_AGI_TR_Final_v*.xlsx`
   - `RORO_Summary.png`
2. Collect Step 2 outputs:
   - `OPS_FINAL_R3_AGI_Ballast_Integrated.xlsx`
   - `OPS_FINAL_R3_Report_Integrated.md`
3. Collect Step 4b outputs (Option 2):
   - `BALLAST_OPTION.csv`
   - `BALLAST_EXEC.csv`
   - `BALLAST_SEQUENCE.csv`
   - `BALLAST_SEQUENCE.xlsx`
   - `BALLAST_OPERATIONS_CHECKLIST.md`
   - `HOLD_POINT_SUMMARY.csv`
4. Copy input files:
   - `tank_catalog_from_tankmd.json`
   - `Hydro_Table_Engineering.json`
   - Other dependency files
5. Copy to `inputs/` subdirectory

### 3.10 Excel File Merging

**Function**: `merge_excel_files_to_one()`

**Logic**:

1. Search Excel files:
   - `LCT_BUSHRA_AGI_TR_Final_v*.xlsx`
   - `OPS_FINAL_R3_AGI_Ballast_Integrated.xlsx`
   - `optimizer_ballast_plan.xlsx`
2. Merge workbooks:
   - Copy all sheets from each Excel file into one workbook
   - Add filename prefix when sheet name conflicts
3. Save:
   - `PIPELINE_CONSOLIDATED_AGI_<timestamp>.xlsx`

**Output**:

- `PIPELINE_CONSOLIDATED_AGI_<timestamp>.xlsx`: Consolidated Excel file

### 3.11 Excel Formula Finalization

**Script**: `ballast_excel_finalize.py`

**Logic**:

1. Connect Excel COM
2. Execute RefreshAll
3. Execute CalculateFullRebuild
4. Generate Calc_Log sheet (calculation history)

**Output**:

- Updated Excel file (formulas calculated)

---



## Section 4: Data Flow and SSOT Integration

```markdown
## 4. Data Flow and SSOT Integration

### 4.1 SSOT Principles

**Single Source of Truth (SSOT)**:
- All data loaded from a single source
- Eliminate duplicate definitions
- Ensure consistency

### 4.2 SSOT File Hierarchy

```

Level 1: Original JSON (Input)
├── tank_catalog_from_tankmd.json
├── Hydro_Table_Engineering.json
├── AGI_site_profile_COMPLETE_v1.json
└── current_t_*.csv (sensor data)

Level 2: SSOT CSV (Solver/Optimizer input)
├── tank_ssot_for_solver.csv
│   ├── convert_tank_catalog_json_to_solver_csv()
│   ├── inject_current_t_from_sensor_csv()
│   └── apply_tank_overrides_from_profile()
├── hydro_table_for_solver.csv
│   └── convert_hydro_engineering_json_to_solver_csv()
└── stage_table_unified.csv
    └── build_stage_table_from_stage_results()

Level 3: Stage QA (verification results)
└── pipeline_stage_QA.csv
    └── generate_stage_QA_csv()
        ├── Gate verification
        ├── Solver results reflection (after Step 3)
        └── HardStop synthesis

Level 4: Reports (final output)
├── OPS_FINAL_R3_Report_Integrated.md
├── gate_fail_report.md
├── solver_ballast_plan.csv
└── optimizer_ballast_plan.xlsx

```

### 4.3 Stage Definition SSOT

**SSOT**: `stage_results.csv` (generated in Step 1b)

**Stage Definitions** (9 stages):
1. Stage 1
2. Stage 2
3. Stage 3
4. Stage 4
5. Stage 5
6. Stage 5_PreBallast
7. Stage 6A_Critical (Opt C)
8. Stage 6C
9. Stage 7

**SSOT Consumers**:
- `ops_final_r3_integrated_defs_split_v4_patched.py`: Loads Stage definitions
- `stage_wise_load_transfer_excel_patched.py`: Loads Stage Summary
- `build_stage_table_from_stage_results()`: Builds Stage Table

**Important**: Remove hardcoded Stage definitions, load only from SSOT

### 4.4 Current_t Injection Flow

```

Sensor CSV (current_t_*.csv)
    ↓
resolve_current_t_sensor_csv() (auto-detection)
    ↓
inject_current_t_from_sensor_csv()
    ├── Exact match: Tank ID exactly matches
    ├── Group match: Base name matches (equal distribution)
    └── Strategy application (override/fill_missing)
    ↓
tank_ssot_for_solver.csv (updated)
    ↓
diff_audit.csv (injection history)

```

### 4.5 Tank Overrides Flow

```

Site Profile JSON (AGI_site_profile_COMPLETE_v1.json)
    ├── tank_overrides section
    │   ├── exact match: Tank ID exactly matches
    │   └── base match: Base name matches (explicit permission required)
    └── apply_tank_overrides_from_profile()
        ↓
tank_ssot_for_solver.csv (overrides applied)

```

---

## 5. Key Functions and Module Descriptions

### 5.1 Path Resolution Functions

#### `resolve_site_profile_path()`
- Resolve Site profile JSON path
- Priority: Explicit argument > default path (`inputs_dir/profiles/{site}.json`)

#### `resolve_current_t_sensor_csv()`
- Resolve Current_t sensor CSV path
- Auto-detection: `current_t_*.csv` pattern, latest file priority

### 5.2 SSOT Conversion Functions

#### `convert_tank_catalog_json_to_solver_csv()`
- Tank catalog JSON → CSV conversion
- Coordinate conversion: `x_from_mid_m = MIDSHIP_FROM_AP_M - lcg_from_ap_m`
- Keyword filtering: Set `use_flag` with `include_keywords`

#### `convert_hydro_engineering_json_to_solver_csv()`
- Hydro Table JSON → CSV conversion
- Column normalization: MCTC → MTC, LCF_m_from_midship → LCF_m

#### `build_stage_table_from_stage_results()`
- `stage_results.csv` → `stage_table_unified.csv`
- Draft clipping: Prevent exceeding Molded Depth
- Add Gate values, mark Critical stages, add UKC parameters

#### `generate_stage_QA_csv()`
- `stage_table_unified.csv` → `pipeline_stage_QA.csv`
- Gate verification, Margin calculation, HardStop synthesis
- Reflect Solver results (after Step 3)

### 5.3 Sensor Injection Functions

#### `inject_current_t_from_sensor_csv()`
- Current_t sensor data injection
- Matching strategy: Exact match, Group match
- Strategy: override, fill_missing
- Generate diff_audit.csv

### 5.4 Report Generation Functions

#### `generate_gate_fail_report_md()`
- Generate Gate FAIL report
- Aggregate Gate violations, generate Heuristics, Markdown output

#### `generate_tug_operational_sop_md()`
- Generate TUG operational SOP
- Includes DNV-ST-N001 compliance checklist

#### `append_solver_section_to_gate_report()`
- Add Solver results to Gate FAIL report
- Execute after Step 3

### 5.5 Step Execution Functions

#### `step_run_script()`
- Execute Step script (subprocess)
- Generate log file (`logs/<step_id>_<name>.log`)
- Return value: `StepResult(ok, returncode, log)`

---

## 6. Input/Output File Structure

### 6.1 Input Files

#### Required Inputs
- `tank_catalog_from_tankmd.json`: Tank catalog
- `Hydro_Table_Engineering.json`: Hydrostatic Table
- `stage_results.csv`: Stage results (can be generated in Step 1b)

#### Optional Inputs
- `AGI_site_profile_COMPLETE_v1.json`: Site profile
- `current_t_*.csv`: Current_t sensor data (auto-detected)
- `LCT_BUSHRA_GM_2D_Grid.json`: GM 2D Grid
- `Tank_FSM_Coeff.json`: FSM coefficients

### 6.2 Output File Structure

**Reference**: For detailed output file list and header structure, refer to:
- `03_DOCUMENTATION/00_CORE_ARCHITECTURE/최종 출력 보고서 헤더명 종합 리포트 (실제 데이터 기반).md` (44 files, 725+ sheet headers detailed)
- `03_DOCUMENTATION/Pipeline Integration.md` section 8 (21-40 files detailed list)

**Basic Output Structure**:
```

pipeline_out_`<timestamp>`/
├── ssot/
│   ├── tank_ssot_for_solver.csv
│   ├── tank_ssot_for_solver__aftmin.csv (for AFT-min stage)
│   ├── hydro_table_for_solver.csv
│   ├── stage_table_unified.csv
│   ├── pipeline_stage_QA.csv
│   └── diff_audit.csv (Current_t injection history)
├── logs/
│   ├── 01_TR_EXCEL.log
│   ├── 02_TR_STAGE_CSV.log
│   ├── 03_OPS_INTEGRATED.log
│   ├── 04_SOLVER_LP.log
│   └── 05_OPTIMIZER.log
├── gate_fail_report.md
├── TUG_Operational_SOP_DNV_ST_N001.md
├── OPS_FINAL_R3_AGI_Ballast_Integrated.xlsx
├── OPS_FINAL_R3_Report_Integrated.md
├── solver_ballast_plan.csv
├── solver_ballast_summary.csv
├── solver_ballast_stage_plan.csv
├── optimizer_ballast_plan.xlsx
├── optimizer_plan.csv
├── optimizer_summary.csv
├── BALLAST_OPTION.csv              # Step 4b output (Option 2, planning level)
├── BALLAST_EXEC.csv                # Step 4b output (Option 2, execution sequence)
├── BALLAST_SEQUENCE.csv            # Step 4b output (Legacy, compatibility)
├── BALLAST_SEQUENCE.xlsx           # Step 4b output (Excel, 3 sheets)
├── BALLAST_OPERATIONS_CHECKLIST.md # Step 4b output
├── BALLAST_SEQUENCE_WITH_VALVES.md # Step 4c output
├── HOLD_POINT_SUMMARY.csv          # Step 4b output
├── PIPELINE_CONSOLIDATED_AGI_`<timestamp>`.xlsx
└── inputs/
    ├── tank_catalog_from_tankmd.json
    ├── Hydro_Table_Engineering.json
    └── ...

```

**Complete Output File List (Full Options Execution)**:
- SSOT CSV: 6-7 files
- Log Files: 2-5 files
- Excel Files: 4-10 files
- CSV Files: 6-12 files
- Markdown Reports: 2-6 files
- **Total 21-40 files** (depending on options)

**Detailed List**: Refer to `03_DOCUMENTATION/Pipeline Integration.md` section 8

### 6.3 Final Output Folder

**Function**: `create_final_output_folder()`

**Structure**:
```

final_output_`<timestamp>`/
├── manifest.json (file list and SHA256)
├── PIPELINE_CONSOLIDATED_AGI_`<timestamp>`.xlsx
├── pipeline_stage_QA.csv
├── stage_table_unified.csv
├── tank_ssot_for_solver.csv
├── hydro_table_for_solver.csv
├── gate_fail_report.md
├── TUG_Operational_SOP_DNV_ST_N001.md
└── ...

```

---

## 7. Error Handling and Logging

### 7.1 Error Handling Strategy

1. **HardStop**: Input data/domain problems (e.g., Draft > Molded Depth, Hydro out-of-range)
   - `strict_hardstop=True`: Immediately stop with ValueError
   - `strict_hardstop=False`: Only set HardStop flag, continue

2. **Step Failure**:
   - Step 1: Only warning output (optional step)
   - Step 1b: Pipeline stops (`return 1`)
   - Step 2~4: Pipeline stops (`return 1`)

3. **Missing Files**:
   - Required files: Pipeline stops
   - Optional files: Only warning output

### 7.2 Logging

**Log File Location**: `pipeline_out_<timestamp>/logs/`

**Log File Naming**:
- `<step_id>_<name>.log`: Normal execution
- `<step_id>_<name>_MISSING.log`: Script missing

**Debug Log**: `.cursor/debug.log` (NDJSON format)

### 7.3 Debug Report

**Function**: `debug_report_step()`

**Generation Condition**: `--debug_report` or `--auto_debug_report`

**Output**:
- `debug_feasibility_pipeline.md`: Debug report
- `debug_stage_flags.csv`: Stage-wise flags
- `pipeline_stage_QA.csv`: Stage QA data

---

## 8. Key Constants and Settings

### 8.1 Coordinate System Constants (SSOT - AGENTS.md reference)

**Frame Coordinate System (BUSHRA TCP / tank.md reference)**:
- `Fr.0 = AP (AFT)`: After Perpendicular (stern perpendicular)
- `Frame increase direction = FWD`: Frame increases toward bow
- `Frame 30.151 = Midship → x = 0.0`: Midship reference point

**X Coordinate System (for calculation, Midship reference)**:
- `MIDSHIP_FROM_AP_M = 30.151`: Midship position (AP reference, m)
- `LPP_M = 60.302`: Length between perpendiculars (m)
- `_FRAME_SLOPE = -1.0`: Frame→x conversion slope
- `_FRAME_OFFSET = 30.151`: Frame→x conversion offset

**Coordinate Conversion Formula (standard, no reinterpretation)**:
```

x = _FRAME_SLOPE * (Fr - _FRAME_OFFSET)
x = 30.151 - Fr

```

**X Coordinate Sign Rules**:
- `x > 0`: AFT (stern direction)
- `x < 0`: FWD (bow direction)

**Golden Rule**: Treating bow tanks (high Fr / high LCG(AP)) as "stern ballast" violates physical laws and breaks all gates.

### 8.2 Tank Direction SSOT (FWD/AFT Classification - No Re-discussion)

**AFT Zone (Stern)**:
- `FW2 P/S`: Fr.0-6 (stern fresh water)
- `VOIDDB4 P/S`, `SLUDGE.C`, `SEWAGE.P`: Fr.19-24 (mid-stern)
- Fuel tanks `DO`, `FODB1`, `FOW1`, `LRFO P/S/C`: Fr.22-33 (near Midship)

**MID Zone**:
- `VOID3 P/S`: Fr.33-38

**MID-FWD Zone**:
- `FWCARGO2 P/S`: Fr.38-43
- `FWCARGO1 P/S`: Fr.43-48

**FWD/BOW Zone (Bow)**:
- `FWB2 P/S`: Fr.48-53 (bow ballast)
- `VOIDDB1.C`: Fr.48-56
- `FWB1 P/S`: Fr.56-FE (bow ballast)
- `CL P/S`: Fr.56-59 (Chain lockers)

**Practical Result**: `FWB1.*` and `FWB2.*` are **bow/bow tanks**. They have `x < 0` in the X coordinate system and **cannot be used as "stern ballast"**. For AFT-up / stern-down moment, use **AFT zone tanks** and/or move cargo LCG toward stern.

### 8.3 Gate Constants (SSOT - AGENTS.md reference)

**Gate-A (Captain / Propulsion)**:
- `CAPTAIN_AFT_MIN_DRAFT_M = 2.70`: Captain AFT minimum Draft (m)
- `GATE_A_LABEL = "AFT_MIN_2p70"`: Gate-A label (prevents ambiguous "2.70m")
- **Definition**: AFT draft ≥ 2.70m (ensure propeller efficiency/propulsion in emergency)
- **ITTC Reference**: Approval documents must report **shaft centreline immersion** (propeller diameter reference)
  - Minimum: 1.5D, Recommended: 2.0D (D = propeller diameter)
  - Calculation: `immersion_shaftCL = draft_at_prop - z_shaftCL`

**Gate-B (Mammoet / Critical RoRo only)**:
- `MAMMOET_FWD_MAX_DRAFT_M_CD = 2.70`: Mammoet FWD maximum Draft (Chart Datum reference, m)
- `GATE_B_LABEL = "FWD_MAX_2p70_critical_only"`: Gate-B label (prevents ambiguous "2.70m")
- **Definition**: FWD draft (Chart Datum) ≤ 2.70m, **Critical RoRo stages only** apply
- **Critical Stage Definition**: `DEFAULT_CRITICAL_STAGE_REGEX = r"(preballast.*critical|6a.*critical|stage\s*5.*preballast|stage\s*6a)"`
- **Application Scope**: Only stages with `Gate_B_Applies=True` are verified for Gate-B (Non-critical are N/A)

**Gate Labels SSOT (prevents ambiguous "2.70m")**:
- **Never use "2.70m" alone**. Always include label:
  - **Gate-A**: `AFT_MIN_2p70` (Captain / Propulsion)
  - **Gate-B**: `FWD_MAX_2p70_critical_only` (Mammoet / Critical RoRo only)

**Gate-FB (MWS Load-out Effective Freeboard)**:
- **GL Noble Denton 0013/ND effective freeboard gate**:
  - With 4-corner monitoring: `Freeboard_Req = 0.50 + 0.50*Hmax`
  - Without monitoring: `Freeboard_Req = 0.80 + 0.50*Hmax`
- Pipeline flags: `--hmax_wave_m` (ND gate required), `--four_corner_monitoring` (reduces requirements)

**Draft vs Freeboard vs UKC Distinction (No Confusion)**:
- **Draft**: keel → waterline (FWD/AFT/Mean)
- **Molded depth (D_vessel_m)**: keel → main deck (geometric)
- **Freeboard**: deck (or openings) → waterline (risk: deck wet/downflooding)
- **UKC**: seabed/chart depth + tide − draft (risk: grounding)
- **Tide**: **Only affects UKC**, no effect on freeboard (vessel rises with tide)

### 8.4 Default Values

- `D_VESSEL_M = 3.65`: Molded depth (m, for freeboard = D - Draft calculation)
- `DEFAULT_PUMP_RATE_TPH = 100.0`: Default pump rate (t/h, hired/shore pump nominal)
- `DEFAULT_BASE_DISP_T = 2800.0`: Default displacement (t, SSOT candidate value)
- `GM_MIN_M = 1.50`: Minimum GM requirement (m)

---

## 9. Scalability and Maintenance

### 9.1 Site-Agnostic Design

- Same logic for AGI/DAS
- Only change parameters with Site profile
- Respond by modifying JSON without code changes

### 9.2 SSOT Integration

- All data loaded from SSOT
- Remove hardcoding
- Ensure consistency

### 9.3 Modularization

- Each Step is an independent script
- Modularized by function
- Reusable utility functions

---

## 10. Core Design Principles and SSOT Policy

### 10.1 Coordinate System and Physical Law Compliance

**Absolute Rules**:
1. **Frame→x conversion formula: No reinterpretation**: `x = 30.151 - Fr`
2. **Tank Direction SSOT compliance**: Do not use FWD zone tanks as "stern ballast"
3. **Coordinate sign rules**: `x > 0` = AFT, `x < 0` = FWD

### 10.2 Gate Definition and Labeling

**Gate Label SSOT**:
- **Never use "2.70m" alone**. Always include label:
  - Gate-A: `AFT_MIN_2p70` (Captain)
  - Gate-B: `FWD_MAX_2p70_critical_only` (Mammoet)

**Gate-B Application Scope**:
- Only apply to Critical stages (`Gate_B_Applies=True`)
- Non-critical stages marked as `N/A` (prevent false failure)

### 10.3 Draft vs Freeboard vs UKC Distinction

**Clear Distinction**:
- **Draft**: keel → waterline
- **Freeboard**: deck → waterline (deck wet/downflooding risk)
- **UKC**: seabed + tide − draft (grounding risk)
- **Tide**: Only affects UKC, no effect on freeboard

### 10.4 Stage Artifacts (No Confusion)

**File-wise Meaning**:
- `stage_results.csv`: TR/script stage geometry result (TR position only, may not include solver ballast)
- `tank_ssot_for_solver.csv`: Solver's tank universe, constraints, `current_t`
- `solver_ballast_summary.csv` / ballast plan: **Delta** ballast moves selected by solver
- `pipeline_stage_QA.csv`: Explicitly states whether Draft is **raw** (stage_results) or **post-solve** (after solver application)

**Hard Rule**: Do not manually edit `stage_results.csv` to inject ballast effects. For ballast to affect draft, integrate in deterministic pipeline step and re-execute.

### 10.5 Override Rules (Prevent Base Matching Traps)

1. **Explicit tank ID priority**: `FWB1.P` > `FWB1` (base key)
2. **Base keys disabled by default**: Base match requires explicit flag (`"match": "base"`)
3. **Ensure symmetry**: Apply equally when overriding `.P` and `.S` (except when asymmetry is intended)
4. **Prevent unintended reset from base match**: Be careful that `.S` override does not reset `.P` via base match

---

## 11. Related Documents and References

### 11.1 Core Architecture Documents
- `03_DOCUMENTATION/00_CORE_ARCHITECTURE/00_System_Architecture_Complete.md`: Complete system architecture
- `03_DOCUMENTATION/00_CORE_ARCHITECTURE/02_Data_Flow_SSOT.md`: SSOT data flow
- `03_DOCUMENTATION/00_CORE_ARCHITECTURE/03_Pipeline_Execution_Flow.md`: Pipeline execution flow

### 11.2 Integration and Header Documents
- `03_DOCUMENTATION/Pipeline Integration.md`: SPMT integration, Tide Integration, output file list
- `03_DOCUMENTATION/00_CORE_ARCHITECTURE/최종 출력 보고서 헤더명 종합 리포트 (실제 데이터 기반).md`: Excel/CSV header structure details

### 11.3 Calculation Logic Documents
- `03_DOCUMENTATION/00_CORE_ARCHITECTURE/17_TIDE_UKC_Calculation_Logic.md`: TIDE/UKC calculation mathematical model
- `03_DOCUMENTATION/AGENTS.md`: SSOT coordinate system and Gate definitions

---

**Document Version**: v4.5 (bplus_inputs folder structure addition + enhanced cross-document references)
**Last Updated**: 2025-12-29
**Author**: AI Assistant (Auto-generated from codebase analysis + AGENTS.md SSOT)
**Reference Documents**:
- `03_DOCUMENTATION/AGENTS.md` (coordinate system, Gate definitions, Tank Direction SSOT)
- `01_EXECUTION_FILES/문서 업데이트.MD` (latest feature reflection history)
```

**Summary**:

- Complete architecture overview (layer structure)
- Execution file list and roles (7 main scripts + auxiliary scripts)
- Step-by-step detailed logic (Step 1~4 + PREP stage)
- Data flow and SSOT integration (4-level SSOT hierarchy)
- Key functions and module descriptions (20+ functions)
- Input/output file structure (detailed directory structure)
- Error handling and logging strategy
