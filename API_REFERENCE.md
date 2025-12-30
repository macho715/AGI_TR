# AGI_TR API Reference
## Module Overview

### Untitled-2_patched_defsplit_v1_1.py
=============================================================================
BALLAST OPTIMIZER INTEGRATED (LCT BUSHRA & GENERIC)
=============================================================================
Merges Linear Programming accuracy with Operational Heuristics.

Features:
- SCIPY Linear Programming Solver (Exact targets, Slack variables)
- Interactive CLI for crew use
- Batch processing for office use (CSV/Excel support)
- BWRB (Ballast Water Record Book) Logging generation
- AGI Site & Pre-ballast specific logic

Usage:
  1. Interactive: python ballast_optimizer_integrated.py
  2. Batch:       python ballast_optimizer_integrated.py --tank tank.csv ...
=============================================================================

**Classes:**
- `VesselParams`: Default LCT BUSHRA Parameters (Used if no Hydro table provided)
- `TankZone`: No description
- `HydroPoint`: No description
- `Tank`: No description
- `OptimizationResult`: No description

**Functions:**
- `fr_to_x()`: Convert Frame number to x [m from midship].
- `x_to_fr()`: Inverse: x [m from midship] → Frame number.
- `interpolate_tmean_from_disp()`: Δdisp → Tmean 보간
- `interpolate_hydro_by_tmean()`: Interpolate hydrostatic fields by mean draft (Tmean_m).
- `calc_draft_with_lcf()`: Draft 계산 (단일 참조점/부호 규약 고정).

### agi_tr_patched_v6_6_defsplit_v1.py
AGI TR RORO Integrated Calculation System

Version: 6.8.0-PATCH1111-ENFORCEMENT
Last Updated: 2025-12-16
Features:
  - B1-Enhanced: Hydro-based base_tmean_m calculation (SSOT enforcement, no fallback)
  - B2: Trim_gate auto + ΔTM direction correction (COMPLETE)
  - C-Enhanced: Iterative ballast correction + Operational columns
  - CONST_TANKS CSV integration (Option B-2)

VALIDATION STATUS:
✅ B1-Enhanced: RuntimeError if Hydro table missing (SSOT enforcement)
✅ B2: Trim_gate auto-calculation + correct ΔTM direction
✅ C-Enhanced: Operational columns (Ballast_alloc, Pump_time_h, Lineup_OK)
✅ CSV auto-loading 8/8 tanks (100% match rate)
✅ Stage 5_PreBallast: FWD ≤ 2.70m
✅ All regulatory constraints satisfied

PATCH1111 COMPLIANCE:
✅ B1: Fallback 2.00m removed (2 locations)
✅ B2: Already complete (Trim_gate + ΔTM)
✅ C: Operational columns added to iterative_ballast_correction()

REGULATORY BASIS:
- Max FWD Draft: 2.70m (AGI Site operational limit)
- Min GM: 1.50m (IMO stability requirement)
- Max Ramp Angle: 6° (SPMT climbing limit)
- Trim Envelope: ±2.40m (240cm)

**Classes:**
- `LoadItem`: Stage별 하중 구성 요소
- `LoadCase`: No description
- `BackupRecoveryError`: BACKUP PLAN: 백업 복구 가능한 에러

**Functions:**
- `_load_gm2d_grid()`: GM 2D Grid JSON 로드 및 전역 변수 설정
- `get_styles()`: 공통 스타일 정의
- `_get_search_roots()`: Return ordered search roots for input JSON files.
- `_find_existing_path()`: Find the first existing path for filename across search roots.
- `_load_json()`: JSON loader with ordered path priority (Option B+).

### ballast_excel_finalize.py
Ballast Pipeline - Excel Formula Preservation (COM Post-Processing)

Purpose:
    Preserve formula dependency integrity after openpyxl writes by using Excel COM.
    - CalculateFullRebuild (dependency graph rebuild)
    - RefreshAll (external queries/data)
    - Calc_Log sheet append

Requirements:
    - Windows OS + Excel installed
    - pip install pywin32

Usage:
    python ballast_excel_finalize.py --auto
    python ballast_excel_finalize.py "file.xlsx"
    python ballast_excel_finalize.py --batch "pattern/*.xlsx"

**Functions:**
- `finalize_excel_com()`: Excel COM post-processing for formula preservation.
- `find_latest_pipeline_output()`: Detect the most recent pipeline output Excel file.
- `main()`: CLI entry point.

### ballast_sequence_generator.py
Ballast Sequence Generator (P0-2)
Generates step-by-step ballast operations sequence with hold points.

**Classes:**
- `BallastStep`: Single ballast sequence step.
- `BallastOption`: Ballast option/plan level entry (Delta_t based).

**Functions:**
- `_stage_order_from_df()`: No description
- `_tank_current_map()`: No description
- `_delta_from_row()`: No description
- `_canonical_stage_name()`: No description
- `_canonicalize_stage_column()`: No description

### checklist_generator.py
Checklist Generator (P0-2)
Generates field operations checklist.

**Functions:**
- `generate_checklist()`: Generate field operations checklist (Markdown format).

### compile_headers_registry.py
Compile HEADERS_MASTER.xlsx to headers_registry.json

**Functions:**
- `compile_from_excel()`: Compile Excel master to JSON registry.
- `main()`: No description

### create_bryan_excel_template_NEW.py
create_bryan_excel_template.py

Goal
- Generate Bryan Submission Data Pack Template aligned to the analyzed report structure:
  16 sheets in fixed order (same sheet names).
- Provide enough rows/columns so all data can be entered.
- Use NamedRanges for cross-sheet DataValidation lists (Stage_List, Tanks_List).

Sheet order (per analysis doc)
- 00_README
- 01_SSOT_Master
- 02_Vessel_Hydro
- 03_Berth_Tide
- 04_Cargo_SPMT
- 05_Ballast_Tanks
- 06_Stage_Plan
- 07_Stage_Calc
- 08_HoldPoint_Log
- 09_Evidence_Log
- 10_RACI
- 11_Assumptions_Issues
- 12_DataDictionary
- Pack_A_Inputs_SSOT
- Pack_B_Calculation_Formulas
- Pack_D_Tide_Window_RACI

**Classes:**
- `Styles`: No description

**Functions:**
- `build_styles()`: No description
- `set_col_widths()`: No description
- `make_header_row()`: No description
- `apply_row_style()`: No description
- `add_named_range()`: refers_to example: "'06_Stage_Plan'!$A$2:$A$200"

### create_stage_excel_report.py
스테이지별 상세 결과 Excel 테이블 생성
Excel Table Style로 정리된 보고서 생성

**Functions:**
- `create_stage_summary_excel()`: 스테이지별 상세 결과를 Excel 테이블 형식으로 생성

### populate_template.py
populate_template.py

Fill 07_Stage_Calc input columns from engine stage CSV (e.g., stage_results.csv).

Default mapping (CSV -> 07_Stage_Calc)
- Stage / Stage_ID           -> A (Stage_ID)
- x_stage_m                  -> F (x_stage_m)
- W_stage_t                  -> G (W_stage_t)
- Disp_t                     -> H (Displacement_t)
- Tmean_m                    -> I (Tmean_m)
- Dfwd_m                     -> K (Draft_FWD_m)
- Daft_m                     -> L (Draft_AFT_m)
- GM(m)                      -> U (GM_m)

Notes
- Keeps existing formulas in calc columns.
- If the stage row exists (Stage_ID match), overwrites/FillBlank based on --mode.
- If not found, writes into the first empty row; if no empty rows, extends rows.
- Writes LOG sheet + text log.

**Functions:**
- `_norm_text()`: No description
- `_norm_col()`: No description
- `pick_column()`: Find best matching column from df given candidate names.
- `safe_float()`: No description
- `_norm_header()`: No description

### spmt v1/agi_spmt_unified.py
AGI SPMT Shuttle — Integrated Builder (SSOT-locked)

What this tool does (AGI scope)
1) Enforces a single coordinate convention (SSOT):
   - Input "Frame" values are **Fr(m) = station from AP in meters** (coord_mode=FR_M)
   - x_from_midship(m) = midship_from_ap_m - Fr(m)
2) Generates an Excel workbook with:
   - Stage_Config
   - Cargo_SPMT_Inputs (auto-filled, including CoG_x_m = x_from_midship)
   - Stage_Loads (itemized, per stage)
   - Stage_Summary (per stage)
   - Stage_Results + Stage-wise Cargo on Deck (Bryan-format summary)
   - LOG (warnings / assumptions / audit notes)
3) Exports CSVs (stage_loads.csv, stage_summary.csv, stage_results.csv)

Notes
- This script intentionally does NOT use "structural frame spacing" for coordinate conversion.
- If your input values are truly "frame indexes", DO NOT use this tool without a verified
  frame-index mapping; use a dedicated conversion table instead.

CLI Example
  python agi_spmt_unified.py --config spmt_shuttle_config_AGI.json --out_xlsx AGI_SPMT_Shuttle.xlsx --out_dir out/

**Classes:**
- `StageItem`: No description
- `StageSummary`: No description

**Functions:**
- `_as_float()`: No description
- `r()`: No description
- `ensure_sheet()`: No description
- `clear_sheet()`: No description
- `set_col_widths()`: No description

### spmt v1/agi_ssot.py
AGI SSOT (Single Source of Truth) coordinate utilities for LCT cargo / SPMT scripts.

Scope
- **AGI Site** coordinate convention as implemented in the existing pipeline scripts:
  - Station from AP is denoted as Fr (meters).
  - Midship from AP is 30.151 m (LPP/2 when LPP=60.302 m).
  - x_from_midship (m) = midship_from_ap_m - fr_m_from_ap

Important
- This is a *geometric reference* used for stability / stage tables in the pipeline.
- It is NOT the same thing as *structural frame spacing* on the vessel.

This module is intended to be imported by:
- stage_shuttle_autocalc*.py
- cargo_spmt_inputs_stagewise_autofill.py
- spmt_shuttle_stage_builder.py
- lct_stage_spmt_shuttle.py (patched)
- spmt2.py (patched)

**Classes:**
- `VesselSSOT`: Vessel coordinate handler.

**Functions:**
- `_as_float()`: No description
- `build_agi_default_ssot()`: Returns the AGI default SSOT values (LPP=60.302m, Midship=30.151m, coord_mode=FR_M).
- `to_fr_m_from_ap()`: No description
- `x_from_midship_m()`: No description
- `fr_from_x_from_midship_m()`: No description

### spmt v1/lct_stage_spmt_shuttle_AGI_SSOT_patched.py
lct_stage_spmt_shuttle.py (AGI SSOT patched)

Key change
- Default coordinate mode is FR_M (station from AP in meters).
- The legacy "frame index * 0.60 m + AP offset" conversion is preserved only if you
  explicitly set coord_mode="FRAME_INDEX" in your config.

Recommendation
- For AGI pipeline consistency, keep coord_mode="FR_M" and provide all frames as meters from AP.

**Classes:**
- `VesselCoord`: Wrapper around the shared AGI SSOT coordinate converter.
- `StageConfig`: No description

**Functions:**
- `load_config()`: No description
- `build_vessel_coord()`: No description
- `build_stages()`: Returns list of (stage_name, [(item_name, weight_t, fr_m_from_ap), ...]).
- `main()`: No description
- `frame_to_station_m()`: No description

### spmt v1/spmt2_AGI_SSOT_patched.py
spmt2.py (AGI SSOT patched)

This file previously mixed "frame index * 0.60m + AP offset" logic.
For AGI SSOT, "Frame" inputs are treated as **Fr(m) station from AP** and used directly.

Recommendation
- Prefer using `agi_spmt_unified.py` as the integrated entrypoint.
- Keep this script only if you need a lightweight calculator.

**Classes:**
- `Load`: No description

**Functions:**
- `summarize()`: Returns (total_t, lcg_x_from_midship_m).
- `demo()`: No description
- `x_m_from_midship()`: No description

### ssot/__init__.py
SSOT Module for Ballast Pipeline

### ssot/data_quality_validator.py
Data Quality Validator - 검증 결과 데이터 적합성 확인
Registry 스키마 검증 후 실제 데이터 값의 적합성을 검증

**Classes:**
- `DataQualityValidator`: 데이터 적합성 검증 (타입, 범위, 일관성)

**Functions:**
- `main()`: No description
- `tidy_and_validate_csv()`: 범용 CSV tidying 및 검증 함수 (DataQualityValidator 메서드로 사용)
- `__init__()`: No description
- `validate_numeric_range()`: 숫자 값의 범위 검증
- `validate_enum()`: 열거형 값 검증

### ssot/draft_calc.py
SSOT Draft Calculation Module (AGENTS.md Method B)
LCF/Lpp-based physically consistent draft calculation

This module implements AGENTS.md Method B for draft calculations:
- Uses LCF (Longitudinal Center of Flotation) as reference point
- Physically consistent for all trim ranges
- Handles coordinate system conversion (Frame ↔ x)

Key Principles:
1. Trim moment about LCF: TM_LCF = Σ(w_i * (x_i - LCF))
2. Trim: Trim_cm = TM_LCF / MTC
3. Drafts: Dfwd/Daft calculated using Lpp distribution

Usage:
    from ssot.draft_calc import DraftCalculatorMethodB, calc_drafts

    # Method 1: Using calculator object
    calc = DraftCalculatorMethodB(
        LCF_m=0.76,
        Lpp_m=60.302,
        MTC_t_m_per_cm=34.00,
        TPC_t_per_cm=8.00
    )

    results = calc.calculate(
        weights=[(100.0, -15.0), (50.0, 10.0)],
        mean_draft_m=2.5
    )

    # Method 2: Convenience function
    results = calc_drafts(
        weights=[(100.0, -15.0)],
        mean_draft_m=2.5,
        LCF_m=0.76,
        Lpp_m=60.302,
        MTC=34.00,
        TPC=8.00
    )

**Classes:**
- `DraftCalculationResult`: Results from draft calculation
- `DraftCalculatorMethodB`: AGENTS.md Method B: Lpp/LCF-based draft calculation

**Functions:**
- `calc_drafts()`: Convenience function for one-off draft calculations
- `to_dict()`: Convert to dictionary for export
- `__repr__()`: No description
- `__init__()`: Initialize draft calculator with vessel parameters
- `frame_to_x()`: Convert Frame to x coordinate

### ssot/gates_loader.py
SSOT Gates Loader Module
AGENTS.md compliant gate loading and validation

This module provides:
1. Gate definition loading from AGI site profile
2. Gate compliance checking
3. Evidence tracking
4. SSOT parameter access
5. Tank catalog loading with operability enforcement (B-1 patch)
6. Ballast plan operability validation (B-1 patch)

Usage:
    from ssot.gates_loader import load_agi_profile

    profile = load_agi_profile()
    gates = profile.gates

    # Check gate compliance
    gate_aft = profile.get_gate("AFT_MIN_2p70_propulsion")
    passed, msg = gate_aft.check(draft_aft_m=2.75, stage_name="Stage_6A")

    # Load tank catalog with operability (B-1)
    tank_catalog_df = profile.load_tank_catalog()

    # Validate ballast plan operability (B-1)
    violations = profile.validate_ballast_plan(ballast_plan_df, tank_catalog_df)

**Classes:**
- `Gate`: Single gate definition with compliance checking
- `SiteProfile`: AGI Site Profile SSOT

**Functions:**
- `load_agi_profile()`: Convenience function to load AGI site profile
- `check()`: Check gate compliance
- `__repr__()`: No description
- `__init__()`: Load site profile from JSON
- `_load()`: Load and parse JSON profile

### ssot/head_guard_v2.py
Head Guard v2 - JSON Registry Validator
Validates pipeline outputs against headers_registry.json

**Classes:**
- `HeadGuardV2`: Header validation against JSON registry.

**Functions:**
- `main()`: No description
- `__init__()`: Load JSON registry.
- `validate_csv_file()`: Validate CSV file against deliverable schema.
- `validate_excel_file()`: Validate Excel file against deliverable schema.
- `validate_directory()`: Validate all files in directory against registry.

### ssot/headers_registry.py
Headers Registry - SSOT for all pipeline output headers
Supports both validation (read) and schema application (write)

**Classes:**
- `FieldDef`: No description
- `Deliverable`: No description
- `HeaderRegistry`: No description

**Functions:**
- `_norm()`: Normalize header strings for matching.
- `load_registry()`: Load registry from JSON file.
- `_find_field_key_for_col()`: Find canonical field key for a column name.
- `apply_schema()`: Apply header schema to DataFrame.
- `validate_df()`: Validate DataFrame against deliverable schema.

### ssot/headers_writer.py
Unified header writer for all pipeline steps
Provides backward-compatible wrapper functions

**Classes:**
- `HeadersWriter`: Unified writer with header registry support.

**Functions:**
- `__init__()`: No description
- `write_csv_with_schema()`: Write CSV with schema application.
- `write_excel_sheet_with_schema()`: Write Excel sheet with schema application.
- `get_headers_for_deliverable()`: Get header list for deliverable (for legacy writerow compatibility).

### ssot/tidying_models.py
Tidying Models - Pydantic-based data validation for MACHO-GPT pipeline
Integrates with existing ssot/headers_registry.py and ssot/data_quality_validator.py

**Classes:**
- `BallastAction`: Ballast action enum (uppercase only)
- `TankOperability`: Tank operability enum
- `BallastSequenceRow`: Validated row from BALLAST_EXEC.csv or BALLAST_OPTION.csv
- `TankCatalogRow`: Validated row from tank catalog
- `LogiDataTider`: Data tidying pipeline for MACHO-GPT logistics data

**Functions:**
- `normalize_action()`: Normalize action to uppercase enum
- `normalize_tank_id()`: Normalize tank ID (strip, uppercase)
- `normalize_stage()`: Normalize stage name (strip, preserve case)
- `normalize_decimal()`: Normalize decimal values to 2 decimal places
- `validate_physics()`: Validate physical constraints

### ssot/validators.py
SSOT Validators (P1-1)
Input/physics/gate preflight validation before pipeline execution.

**Classes:**
- `ValidationIssue`: Single validation issue.
- `ValidationReport`: Complete validation report.
- `InputValidator`: Validate input data consistency and completeness.
- `PhysicsValidator`: Validate physical consistency of calculations.
- `GatePreflightValidator`: Preflight gate feasibility check.

**Functions:**
- `_first_existing_column()`: No description
- `_safe_float()`: No description
- `load_hydro_table_df()`: Load hydro table from JSON or CSV to a DataFrame.
- `run_full_validation()`: Run all validation checks.
- `print_validation_report()`: Print validation report.

### tide/__init__.py

### tide/ballast_gate_solver_v4_TIDE_v1.py
ballast_gate_solver_v4.py
Definition-split + Gate-unified ballast solver.

Key points (per your “원인” 정리)
- Forecast_Tide_m (forecast) is NOT Required_WL_for_UKC_m (required WL).
- Draft is independent of tide.
- Draft vs Freeboard vs UKC are computed separately.
- Unified gate set:
    FWD <= FWD_MAX
    AFT >= AFT_MIN
    Freeboard >= FB_MIN (requires D_vessel_m)
    UKC >= UKC_MIN (requires DepthRef_m + Forecast_Tide_m)

Modes:
- limit  : soft violations (always returns best plan + violation meters)
- target : targets (Target_FWD_m, Target_AFT_m) via ΔW/ΔM equalities (with slack)

Dependencies:
- numpy, pandas, scipy

**Classes:**
- `HydroPoint`: No description
- `Tank`: No description

**Functions:**
- `_read_df_any()`: Read CSV/Excel/JSON with fast-path and parquet cache.
- `load_hydro_table()`: No description
- `interp_hydro()`: No description
- `load_tanks()`: No description
- `load_stage_table()`: No description

### tide/bryan_template_unified_TIDE_v1.py
bryan_template_unified.py

Unified entrypoint for Bryan template workflows:
- create (generate template)
- populate (fill 07_Stage_Calc from stage_results.csv)
- validate (basic checks on populated file)
- one-click (create -> optional SPMT import -> populate -> optional validate)

This script uses create_bryan_excel_template_NEW.py for template generation
and embeds populate/validate logic for a single-file workflow.

**Functions:**
- `_load_module()`: No description
- `_resolve_script_path()`: Resolve dependent script path with fallback to parent dir and first filename match.
- `_norm_header()`: No description
- `_find_header_row()`: No description
- `_read_spmt_rows()`: No description

### tide/integrated_pipeline_defsplit_v2_gate270_split_v3_auditpatched_autodetect_TIDE_v1.py
==============================================================================
INTEGRATED PIPELINE (Definition-split aware)
==============================================================================
Purpose
- Orchestrate 4 scripts as one repeatable pipeline.
- Prevent the exact confusion you described: Forecast Tide vs Required WL, Draft vs
  Freeboard/UKC, and mixed gate-sets.

Why the previous "download" failed (root cause)
- The prior response pasted code in-chat but did not create a physical file.
- Also, the earlier pipeline logic had a sequencing bug: it attempted to extract a
  stage table BEFORE running Step-1 (so stage CSV could be missing and Step-3 fails).

This version fixes:
- Produces a real file (this script).
- Correct step order:
    Step-1 (TR Excel) -> Step-1b (stage_results.csv) -> build stage_table.csv
    -> Step-2 (OPS integrated) -> Step-3 (Gate solver) -> Step-4 (Optimizer)
- Corrects x_from_midship sign convention when converting tank_catalog JSON:
    x_from_midship = MIDSHIP_FROM_AP - LCG_from_AP
  (Aligns with ops_final_r3_integrated_defs_split_v4.py logic)

Inputs expected in your working folder (or provide --inputs_dir):
- tank_catalog_from_tankmd.json           (object with {"tanks":[...]} format)
- bplus_inputs/Hydro_Table_Engineering.json   (or specify --hydro)
- (optional) stage_results.csv (will be generated by Step-1b if possible)

Scripts required (defaults assume same folder as this pipeline):
- agi_tr_patched_v6_6_defsplit_v1.py
- ops_final_r3_integrated_defs_split_v4.py
- ballast_gate_solver_v4.py
- Untitled-2_patched_defsplit_v1_1.py

Usage examples
------------------------------------------------------------------------------
# Run all (AGI defaults)
python integrated_pipeline_defsplit_v2.py

# Run only steps 1..3 (skip optimizer step)
python integrated_pipeline_defsplit_v2.py --to_step 3

# Use custom inputs folder
python integrated_pipeline_defsplit_v2.py --inputs_dir ./LCF

# Override gates (important: Captain AFT minimum)
python integrated_pipeline_defsplit_v2.py --fwd_max 2.70 --aft_min 2.70

# Provide tide/depth for UKC checks in solver
python integrated_pipeline_defsplit_v2.py --forecast_tide 2.00 --depth_ref 5.50 --ukc_min 0.50
------------------------------------------------------------------------------
Notes
- This pipeline is site-agnostic. For AGI vs DAS, keep the same definition split,
  but you may set different gates, depth_ref, etc.
==============================================================================

**Classes:**
- `StepResult`: No description

**Functions:**
- `debug_log()`: Write debug log entry in NDJSON format
- `now_tag()`: No description
- `ensure_dir()`: No description
- `which_python()`: No description
- `run_cmd()`: Run a subprocess, tee stdout/stderr into a log file.

### tide/ops_final_r3_integrated_defs_split_v4_patched_TIDE_v1.py
OPS-FINAL-R3: AGI BALLAST MANAGEMENT SYSTEM (INTEGRATED)
Integrated with agi_tr_patched_v6_6.py engineering-grade calculations

Version: R3-INTEGRATED
Features:
- Engineering-grade stage calculations (hydro table interpolation)
- GM 2D bilinear interpolation
- Frame-based coordinate system
- VOID3 ballast analysis (preserved)
- Discharge-only strategy (preserved)
- Excel + Markdown outputs

**Functions:**
- `classify_tank_role()`: No description
- `_gate_icon()`: Return iconized gate result: ✅PASS / ⚠️FAIL / ❓VERIFY.
- `_freeboard_min_m()`: Freeboard = D - Draft (independent of tide).
- `_gate_freeboard_ok()`: If fb_limit is None → unknown (VERIFY).
- `_first_existing_path()`: No description

### tide/tide_constants.py
TIDE Constants (SSOT)
=====================
Centralized constants for TIDE/UKC calculations.

**Functions:**
- `load_tide_constants_from_profile()`: Load tide/UKC constants from profile JSON with fallbacks.

### tide/tide_ukc_engine.py
Tide + UKC SSOT Engine
=====================

AGI/DAS 공통으로 사용할 수 있는 Tide/UKC 계산 SSOT 모듈.

본 모듈은 "Forecast Tide(예보 조위)"와 "Required WL(UKC 만족을 위해 필요한 수위)"
를 혼동하지 않도록, 아래 정의를 **엄격히 분리**한다.

Definitions (CD 기준)
- Forecast_tide_m / Forecast_Tide_m:
    예보 조위(Chart Datum 기준). "필요 수위"가 아니라 예보값.
- Tide_required_m:
    UKC 요구조건을 만족하기 위해 필요한 최소 수위(조위).
    Tide_required_m = max(0, (Draft_ref + Squat + Safety + UKC_min) - DepthRef)
- Tide_margin_m:
    Tide_margin_m = Forecast_tide_m - Tide_required_m
- UKC_fwd_m / UKC_aft_m:
    UKC_end = DepthRef + Forecast_tide - Draft_end - Squat - Safety
- UKC_min_actual_m:
    min(UKC_fwd_m, UKC_aft_m)

**Functions:**
- `_to_float()`: Convert to float with optional fallback.
- `required_tide_m()`: Return required tide (m, CD) with fallbacks.
- `ukc_end_m()`: Return UKC at one end (m).
- `ukc_fwd_aft_min()`: Return (UKC_fwd, UKC_aft, UKC_min_actual).
- `verify_tide()`: Return (status, note)

### tide_stage_mapper.py
tide_stage_mapper.py

AGI Tide table -> stage-wise forecast tide mapper.

Inputs:
  - tide table Excel (ts_local, tide_m columns; tolerant mapping supported)
  - tide_windows_AGI.json (stage -> time window + stat)
  - optional stage_results.csv for stage list

Output:
  - stage_tide_AGI.csv

**Functions:**
- `load_tide_table_excel()`: No description
- `load_tide_windows_json()`: No description
- `extract_tide_for_window()`: No description
- `map_stages_to_tide()`: No description
- `main()`: No description

### valve_lineup_generator.py
Valve Lineup Generator (P1-3)
Generate detailed valve operation sequences from valve_map.json.

**Classes:**
- `ValveLineupGenerator`: Generate detailed valve operation sequences.

**Functions:**
- `__init__()`: Load valve map.
- `get_tank_valves()`: Get valve information for tank and action.
- `generate_valve_lineup_text()`: Generate human-readable valve lineup text.
- `enhance_ballast_sequence_with_valves()`: Enhance BALLAST_SEQUENCE.csv with detailed valve lineups.
