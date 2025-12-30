# Ballast Pipeline - Final Results Review Guide

**Version**: v1.0
**Last Updated**: 2025-12-30
**Target Audience**: Operators, engineers, approval document preparers
**Purpose**: Step-by-step guide for reviewing and interpreting pipeline execution results

---

## Table of Contents

1. [Quick Start: Results Review Checklist](#1-quick-start-results-review-checklist)
2. [Output Directory Structure](#2-output-directory-structure)
3. [Critical Files Review](#3-critical-files-review)
4. [Gate Compliance Interpretation](#4-gate-compliance-interpretation)
5. [Ballast Plan Analysis](#5-ballast-plan-analysis)
6. [Troubleshooting Guide](#6-troubleshooting-guide)
7. [Approval Document Preparation](#7-approval-document-preparation)
8. [Common Scenarios](#8-common-scenarios)

---

## 1. Quick Start: Results Review Checklist

### 1.1 Immediate Checks (First 5 Minutes)

After pipeline execution, verify these items in order:

- [ ] **Output directory created**: Check `pipeline_out_<timestamp>/` exists
- [ ] **No critical errors**: Review terminal output for ERROR messages
- [ ] **Gate report exists**: `gate_fail_report.md` should be present
- [ ] **Solver completed**: `solver_ballast_summary.csv` should exist
- [ ] **SSOT files generated**: Check `ssot/` directory has 5 CSV files

### 1.2 Priority Review Order

1. **Gate Compliance** (5 min)
   - Open `gate_fail_report.md`
   - Check Gate-A and Gate-B status
   - Identify any FAIL stages

2. **Ballast Plan** (10 min)
   - Review `solver_ballast_summary.csv`
   - Check ballast quantities per stage
   - Verify pump times are reasonable

3. **Sequence Files** (if enabled) (5 min)
   - Review `BALLAST_EXEC.csv`
   - Check `HOLD_POINT_SUMMARY.csv`
   - Verify operational sequence

4. **Detailed Analysis** (as needed)
   - Review `pipeline_stage_QA.csv` for complete data
   - Check logs for warnings
   - Review sensor injection audit

---

## 2. Output Directory Structure

### 2.1 Standard Output Layout

```
pipeline_out_<timestamp>/
├── ssot/                              # SSOT CSV files (Single Source of Truth)
│   ├── tank_ssot_for_solver.csv      # Tank data for solver
│   ├── hydro_table_for_solver.csv    # Hydrostatic data
│   ├── stage_table_unified.csv       # Stage definitions
│   ├── pipeline_stage_QA.csv         # Complete QA data
│   └── diff_audit.csv                # Sensor injection audit
├── logs/                              # Execution logs
│   ├── 00_SPMT_UNIFIED.log           # Step 0 log (if executed)
│   ├── 01_TR_EXCEL.log
│   ├── 03_OPS_INTEGRATED.log
│   ├── 04_SOLVER_LP.log
│   ├── 05_OPTIMIZER.log
│   └── 06_BRYAN_TEMPLATE.log
├── spmt_output/                       # SPMT output files (if Step 0 executed)
│   ├── stage_loads.csv                # Stage-wise load data
│   └── stage_summary.csv              # Stage summary
├── gate_fail_report.md                # Gate compliance report (CRITICAL)
├── AGI_SPMT_Shuttle_Output.xlsx       # SPMT cargo input (if Step 0 executed)
├── solver_ballast_plan.csv            # Detailed ballast plan
├── solver_ballast_summary.csv         # Stage-wise summary
├── solver_ballast_stage_plan.csv      # Stage-by-stage plan
├── solver_state_trace.csv             # Stateful solver trace (if enabled)
├── OPS_FINAL_R3_AGI_Ballast_Integrated.xlsx  # OPS integrated report
├── PIPELINE_CONSOLIDATED_<timestamp>.xlsx     # Consolidated Excel
└── [Sequence files if enabled]
    ├── BALLAST_OPTION.csv
    ├── BALLAST_EXEC.csv
    ├── BALLAST_SEQUENCE.xlsx
    ├── BALLAST_OPERATIONS_CHECKLIST.md
    ├── BALLAST_SEQUENCE_WITH_VALVES.md  # Valve lineup (if enabled)
    └── HOLD_POINT_SUMMARY.csv
```

### 2.2 File Categories

| Category | Files | Purpose | Priority |
|----------|-------|---------|----------|
| **SPMT Output** | `AGI_SPMT_Shuttle_Output.xlsx`, `spmt_output/*.csv` | SPMT cargo input | **MEDIUM** (if Step 0 executed) |
| **Gate Compliance** | `gate_fail_report.md` | Gate violation analysis | **CRITICAL** |
| **Ballast Plan** | `solver_ballast_*.csv` | Ballast operations plan | **HIGH** |
| **QA Data** | `pipeline_stage_QA.csv` | Complete stage data | **HIGH** |
| **Sequence** | `BALLAST_*.csv`, `*.md` | Operational sequence | **MEDIUM** |
| **Reports** | `OPS_*.xlsx`, `PIPELINE_*.xlsx` | Integrated reports | **MEDIUM** |
| **SSOT** | `ssot/*.csv` | Source data | **REFERENCE** |
| **Logs** | `logs/*.log` | Execution logs | **DEBUG** |

---

## 3. Critical Files Review

### 3.1 `gate_fail_report.md` - Gate Compliance Report

**Location**: Root of output directory
**Priority**: **CRITICAL** - Review first

#### What to Check:

1. **Gate Violation Summary** (Section 1)
   - Count of FWD_Max violations
   - Count of AFT_Min violations
   - Count of Freeboard violations
   - Count of UKC violations

2. **Stage-wise Gate Status Table** (Section 4)
   - Look for `NG` (No Good) status
   - Check margin values (negative = violation)
   - Identify which stages need attention

3. **DNV Mitigation Measures** (Section 8)
   - Required for AFT_MIN violations
   - Includes RPM reduction, tug standby, abort criteria
   - **Must be included in approval documents**

#### Example Interpretation:

```markdown
| Stage | GateA_AFT_MIN_2p70_PASS | GateA_AFT_MIN_2p70_Margin_m |
|-------|-------------------------|------------------------------|
| Stage 5_PreBallast | False | -0.54 |
| Stage 6A_Critical | False | -0.34 |
```

**Interpretation**:
- Both stages FAIL Gate-A (AFT < 2.70m)
- Stage 5_PreBallast: AFT = 2.16m (0.54m below requirement)
- Stage 6A_Critical: AFT = 2.36m (0.34m below requirement)
- **Action Required**: Review DNV mitigation measures section

---

### 3.2 `solver_ballast_summary.csv` - Ballast Plan Summary

**Location**: Root of output directory
**Priority**: **HIGH** - Review for operational planning

#### Key Columns:

| Column | Description | How to Read |
|--------|-------------|-------------|
| `Stage` | Stage name | Identify which stage |
| `New_FWD_m` | Forward draft after ballast | Compare with Gate-B limit (2.70m) |
| `New_AFT_m` | Aft draft after ballast | Compare with Gate-A limit (2.70m) |
| `viol_aft_min_m` | AFT violation amount | 0.0 = PASS, >0 = FAIL |
| `viol_fwd_max_m` | FWD violation amount | 0.0 = PASS, >0 = FAIL |
| `Plan_Rows` | Number of tank operations | 0 = No ballast needed |
| `Plan_Diagnosis` | Solver status message | Check for warnings |

#### Example Interpretation:

```csv
Stage,New_FWD_m,New_AFT_m,viol_aft_min_m,Plan_Rows,Plan_Diagnosis
Stage 5_PreBallast,2.2,2.7,0.0,13,
Stage 6A_Critical,2.14,2.64,0.058,9,
```

**Interpretation**:
- Stage 5_PreBallast: Solver achieved AFT 2.70m (PASS), 13 tank operations
- Stage 6A_Critical: AFT 2.64m (0.058m violation), 9 tank operations
- **Action Required**: Stage 6A_Critical needs additional ballast or mitigation

---

### 3.3 `solver_ballast_plan.csv` - Detailed Ballast Plan

**Location**: Root of output directory
**Priority**: **HIGH** - Use for operations

#### Key Columns:

| Column | Description | How to Read |
|--------|-------------|-------------|
| `Stage` | Stage name | Filter by stage |
| `Tank` | Tank identifier | Which tank to operate |
| `Action` | FILL or DISCHARGE | Operation type |
| `Delta_t` | Ballast amount (tonnes) | Positive = fill, Negative = discharge |
| `PumpTime_h` | Pumping time (hours) | Based on pump rate |

#### Example Interpretation:

```csv
Stage,Tank,Action,Delta_t,PumpTime_h
Stage 5_PreBallast,VOID3.S,FILL,152.08,1.52
Stage 5_PreBallast,VOID3.P,FILL,147.15,1.47
Stage 5_PreBallast,FWB2.S,FILL,48.98,0.49
```

**Interpretation**:
- Stage 5_PreBallast requires:
  - Fill VOID3.S with 152.08t (1.52 hours)
  - Fill VOID3.P with 147.15t (1.47 hours)
  - Fill FWB2.S with 48.98t (0.49 hours)
- **Total time**: ~3.5 hours (at 100 t/h pump rate)

---

### 3.4 `pipeline_stage_QA.csv` - Complete QA Data

**Location**: `ssot/pipeline_stage_QA.csv`
**Priority**: **HIGH** - Reference for detailed analysis

#### Key Columns:

| Column | Description | Use Case |
|--------|-------------|----------|
| `Draft_FWD_m`, `Draft_AFT_m` | Final drafts | Verify against gates |
| `Freeboard_Min_m` | Minimum freeboard | Check deck wetting risk |
| `UKC_min_actual_m` | Actual UKC | Verify grounding clearance |
| `Gate_AFT_MIN_2p70_PASS` | Gate-A status | Boolean: True/False |
| `Gate_FWD_MAX_2p70_critical_only_PASS` | Gate-B status | Boolean: True/False |
| `HardStop_Any` | Critical issues | True = immediate review needed |

#### Example Interpretation:

```csv
Stage,Gate_AFT_MIN_2p70_PASS,Gate_FWD_MAX_2p70_critical_only_PASS,UKC_min_actual_m,Freeboard_Min_m
Stage 5_PreBallast,True,True,3.95,0.95
Stage 6A_Critical,False,True,4.01,1.01
```

**Interpretation**:
- Stage 5_PreBallast: All gates PASS, UKC 3.95m (safe), Freeboard 0.95m (safe)
- Stage 6A_Critical: Gate-A FAIL, Gate-B PASS, UKC 4.01m (safe), Freeboard 1.01m (safe)
- **Action Required**: Stage 6A_Critical Gate-A violation needs mitigation

---

### 3.5 `BALLAST_EXEC.csv` - Execution Sequence

**Location**: Root of output directory (if `--enable-sequence`)
**Priority**: **MEDIUM** - Use for operations

#### Key Columns:

| Column | Description | How to Read |
|--------|-------------|-------------|
| `Step` | Sequence step number | Execution order |
| `Stage` | Stage name | Which stage |
| `Tank` | Tank identifier | Which tank |
| `Action` | FILL or DISCHARGE | Operation type |
| `Delta_t` | Ballast amount | Operation quantity |
| `Start_t` | Starting tank level | Current level before operation |
| `Target_t` | Target tank level | Level after operation |
| `Draft_FWD_m`, `Draft_AFT_m` | Expected drafts | Verify after operation |

#### Example Interpretation:

```csv
Step,Stage,Tank,Action,Delta_t,Start_t,Target_t,Draft_FWD_m,Draft_AFT_m
1,Stage 5_PreBallast,VOID3.S,FILL,152.08,0.0,152.08,2.2,2.7
2,Stage 5_PreBallast,VOID3.P,FILL,147.15,0.0,147.15,2.2,2.7
```

**Interpretation**:
- Step 1: Fill VOID3.S from 0.0t to 152.08t
- Step 2: Fill VOID3.P from 0.0t to 147.15t
- After Step 2, expected drafts: FWD 2.2m, AFT 2.7m
- **Action**: Execute in sequence order, verify drafts at each step

---

### 3.6 `HOLD_POINT_SUMMARY.csv` - Hold Point Decisions

**Location**: Root of output directory (if `--enable-sequence`)
**Priority**: **MEDIUM** - Use for operational decisions

#### Key Columns:

| Column | Description | Decision Logic |
|--------|-------------|----------------|
| `Step` | Sequence step | Hold point location |
| `Stage` | Stage name | Which stage |
| `Tank` | Tank identifier | Which tank operation |
| `Draft_FWD_m`, `Draft_AFT_m` | Target drafts | Measured vs predicted |
| `Tolerance_cm` | Allowable deviation | ±2cm = GO, ±4cm = RECALC, >4cm = STOP |

#### Decision Rules:

| Deviation | Decision | Action |
|-----------|----------|--------|
| ≤ ±2cm | **GO** | Proceed to next step |
| ±2cm ~ ±4cm | **RECALCULATE** | Re-run solver with measured values |
| > ±4cm | **STOP** | Abort and investigate |

---

## 4. Gate Compliance Interpretation

### 4.1 Gate-A (AFT_MIN_2p70) - Captain/Propulsion

**Definition**: AFT draft must be ≥ 2.70m for propeller effectiveness

**Status Values**:
- `True` or `PASS`: AFT ≥ 2.70m ✅
- `False` or `NG`: AFT < 2.70m ❌

**Margin Interpretation**:
- Positive margin: Safe margin above requirement
- Negative margin: Violation amount (must be addressed)

**Example**:
```
GateA_AFT_MIN_2p70_PASS: False
GateA_AFT_MIN_2p70_Margin_m: -0.54
```
**Meaning**: AFT = 2.16m (0.54m below 2.70m requirement)

**Required Actions**:
1. Review DNV mitigation measures in `gate_fail_report.md`
2. Prepare approval document with mitigation plan
3. Record ITTC shaft centreline immersion (not just AFT draft)

---

### 4.2 Gate-B (FWD_MAX_2p70_critical_only) - Mammoet/RoRo

**Definition**: FWD draft (Chart Datum) must be ≤ 2.70m during critical RoRo stages

**Status Values**:
- `True` or `PASS`: FWD ≤ 2.70m ✅
- `False` or `NG`: FWD > 2.70m ❌
- `N/A`: Not applicable (non-critical stage)

**Applicability**:
- Only applies to critical stages (Stage 5_PreBallast, Stage 6A_Critical)
- Non-critical stages show `N/A`

**Margin Interpretation**:
- Positive margin: Safe margin below limit
- Negative margin: Violation amount

**Example**:
```
GateB_FWD_MAX_2p70_CD_PASS: True
GateB_FWD_MAX_2p70_CD_Margin_m: 2.56
GateB_FWD_MAX_2p70_CD_applicable: True
```
**Meaning**: FWD = 0.14m (2.56m below 2.70m limit) ✅

---

### 4.3 Freeboard Gate

**Definition**: Minimum freeboard to prevent deck wetting

**Status Values**:
- `OK`: Freeboard ≥ requirement ✅
- `NG`: Freeboard < requirement ❌

**Calculation**:
```
Freeboard = D_vessel_m - Draft
Freeboard_Min = min(Freeboard_FWD, Freeboard_AFT)
```

**Example**:
```
Freeboard_Min_m: 0.95
Gate_Freeboard_MIN: OK
```
**Meaning**: Minimum freeboard 0.95m (safe) ✅

---

### 4.4 UKC Gate

**Definition**: Under Keel Clearance to prevent grounding

**Status Values**:
- `OK`: UKC ≥ requirement ✅
- `NG`: UKC < requirement ❌
- `N/A`: UKC parameters not provided

**Calculation**:
```
UKC = (DepthRef + Forecast_Tide) - (Draft + Squat + Safety_Allow)
```

**Example**:
```
UKC_min_actual_m: 3.95
UKC_min_m: 0.5
Gate_UKC: OK
```
**Meaning**: UKC 3.95m (well above 0.5m requirement) ✅

---

## 5. Ballast Plan Analysis

### 5.1 Understanding Ballast Quantities

**Total Ballast Change**:
- Sum all `Delta_t` values for a stage
- Positive = net ballast added
- Negative = net ballast discharged

**Example**:
```
Stage 5_PreBallast:
- VOID3.S: +152.08t
- VOID3.P: +147.15t
- FWB2.S: +48.98t
- Total: +448.21t (net ballast added)
```

### 5.2 Pump Time Estimation

**Calculation**:
```
PumpTime_h = |Delta_t| / PumpRate_tph
```

**Total Time**:
- Sum all `PumpTime_h` for sequential operations
- For parallel operations, use maximum time

**Example**:
```
Stage 5_PreBallast (sequential):
- VOID3.S: 1.52h
- VOID3.P: 1.47h
- FWB2.S: 0.49h
- Total: 3.48h (if sequential)
- Total: 1.52h (if VOID3.P/S parallel)
```

### 5.3 Tank Selection Analysis

**Check**:
- Are AFT zone tanks used for AFT draft correction? ✅
- Are FWD tanks excluded from AFT ballast? ✅
- Are tank capacities respected? ✅

**Example**:
```
Stage 5_PreBallast uses:
- VOID3.P/S (AFT zone) ✅
- FWB2.S (FWD zone) ⚠️ (check if allowed)
```

---

## 6. Troubleshooting Guide

### 6.1 Gate-A Violations

**Symptoms**:
- `GateA_AFT_MIN_2p70_PASS: False`
- Negative `GateA_AFT_MIN_2p70_Margin_m`

**Possible Causes**:
1. Insufficient AFT ballast capacity
2. FWD tanks used instead of AFT tanks
3. Cargo distribution too forward
4. Solver constraints too restrictive

**Solutions**:
1. Check `solver_ballast_plan.csv` - are AFT tanks being used?
2. Review tank operability in profile JSON

**⚠️ Pre-Execution Adjustment**
The site profile JSON file (`01_EXECUTION_FILES/bplus_inputs/profiles/AGI.json`) can be edited **before pipeline execution** to adjust:
- Tank operability constraints
- Gate limits and guard bands
- Pump rates and operational parameters
- Critical stage definitions

**Note**: Profile changes must be made **before running the pipeline**, as profile values are loaded at startup.

3. Consider DNV mitigation measures
4. Adjust cargo LCG if possible

---

### 6.2 Gate-B Violations

**Symptoms**:
- `GateB_FWD_MAX_2p70_CD_PASS: False` (critical stages only)
- Negative `GateB_FWD_MAX_2p70_CD_Margin_m`

**Possible Causes**:
1. Insufficient FWD ballast discharge
2. Cargo too forward
3. Tide forecast too low

**Solutions**:
1. Check FWD tank discharge in ballast plan
2. Verify forward inventory discharge applied
3. Review tide forecast values
4. Consider cargo repositioning

---

### 6.3 Empty Solver Plan

**Symptoms**:
- `Plan_Rows: 0`
- `Plan_Diagnosis: "Solver returned empty plan"`

**Possible Causes**:
1. No feasible solution (constraints too tight)
2. Tank operability restrictions
3. Insufficient tank capacity

**Solutions**:
1. Check `gate_fail_report.md` for constraint analysis
2. Review tank `use_flag` and `mode` in SSOT
3. Relax constraints if operationally acceptable
4. Check tank capacity vs required ballast

---

### 6.4 Sensor Data Issues

**Symptoms**:
- `diff_audit.csv` shows many `NO_MATCH`
- Tank levels not updated

**Possible Causes**:
1. Tank name mismatch (exact vs base name)
2. Sensor CSV format incorrect
3. Strategy set to `fill_missing` when values exist

**Solutions**:
1. Check `diff_audit.csv` for match status
2. Verify tank names match exactly
3. Use `override` strategy for authoritative sensor data
4. Review sensor CSV column names

---

## 7. Approval Document Preparation

### 7.1 Required Information

When preparing approval documents, include:

1. **Gate Compliance Status**
   - Gate-A status for all stages
   - Gate-B status for critical stages
   - Margin values

2. **DNV Mitigation Measures** (if Gate-A violations)
   - RPM/Power reduction
   - Steering angle limitation
   - Tug standby requirements
   - Abort criteria
   - Monitoring requirements

3. **ITTC Shaft Centreline Immersion**
   - **Not AFT draft** - must calculate shaft immersion
   - Minimum: 1.5D (D = propeller diameter)
   - Recommended: 2.0D
   - Formula: `immersion_shaftCL = draft_at_prop - z_shaftCL`

4. **UKC Verification**
   - Chart Datum reference
   - Tide forecast source
   - Depth reference
   - Safety margins

### 7.2 Document Structure

**Recommended Sections**:

1. **Executive Summary**
   - Overall gate compliance status
   - Critical stages identified
   - Mitigation measures summary

2. **Stage-wise Analysis**
   - Draft values (FWD, AFT)
   - Gate status per stage
   - Ballast plan summary

3. **Mitigation Measures** (if violations)
   - DNV guidance compliance
   - Operational restrictions
   - Monitoring requirements

4. **Appendices**
   - Complete ballast plan
   - Sequence files
   - Sensor data audit

---

## 8. Common Scenarios

### 8.1 Scenario 1: All Gates PASS

**Status**: All gates satisfied

**Actions**:
1. ✅ Review ballast plan for operational feasibility
2. ✅ Verify pump times are acceptable
3. ✅ Check sequence files for hold points
4. ✅ Proceed with operations

---

### 8.2 Scenario 2: Gate-A Violations Only

**Status**: AFT draft below 2.70m

**Actions**:
1. ⚠️ Review DNV mitigation measures
2. ⚠️ Calculate ITTC shaft immersion
3. ⚠️ Prepare approval document with mitigation
4. ⚠️ Obtain Captain/Owner acceptance
5. ⚠️ Set up monitoring and abort criteria

---

### 8.3 Scenario 3: Gate-B Violations Only

**Status**: FWD draft above 2.70m (critical stages)

**Actions**:
1. ⚠️ Review FWD tank discharge plan
2. ⚠️ Check forward inventory discharge
3. ⚠️ Verify tide forecast
4. ⚠️ Consider cargo repositioning
5. ⚠️ Re-run solver with adjusted parameters

---

### 8.4 Scenario 4: Both Gates Violated

**Status**: Both Gate-A and Gate-B failed

**Actions**:
1. 🚨 **CRITICAL** - Review constraints and cargo distribution
2. 🚨 Check if solution is feasible
3. 🚨 Consider operational sequence changes
4. 🚨 May require cargo weight/position adjustment
5. 🚨 Consult with engineering team

---

### 8.5 Scenario 5: Empty Solver Plan

**Status**: Solver returned no solution

**Actions**:
1. 🔍 Check `gate_fail_report.md` for constraint analysis
2. 🔍 Review tank operability in profile
3. 🔍 Verify tank capacities are sufficient
4. 🔍 Consider relaxing constraints
5. 🔍 Check if manual ballast adjustment needed

---

## 9. Quick Reference Tables

### 9.1 Gate Status Quick Lookup

| Status Value | Meaning | Action |
|--------------|---------|--------|
| `True` / `PASS` / `OK` | Gate satisfied | ✅ Proceed |
| `False` / `NG` | Gate violated | ⚠️ Review mitigation |
| `N/A` | Not applicable | ℹ️ Normal (non-critical stage) |

### 9.2 Margin Interpretation

| Margin Value | Interpretation | Action |
|--------------|----------------|--------|
| > 0.10m | Safe margin | ✅ Good |
| 0.0m ~ 0.10m | Minimum margin | ⚠️ Monitor closely |
| < 0.0m | Violation | 🚨 Requires mitigation |

### 9.3 Hold Point Decision

| Deviation | Decision | Action |
|-----------|----------|--------|
| ≤ ±2cm | **GO** | Proceed |
| ±2cm ~ ±4cm | **RECALCULATE** | Re-run solver |
| > ±4cm | **STOP** | Abort and investigate |

---

## 10. File Priority Matrix

### 10.1 Review Priority by Role

| Role | Priority Files | Review Time |
|------|----------------|-------------|
| **Operator** | `gate_fail_report.md`, `BALLAST_EXEC.csv`, `HOLD_POINT_SUMMARY.csv` | 15 min |
| **Engineer** | `solver_ballast_summary.csv`, `pipeline_stage_QA.csv`, logs | 30 min |
| **Approval Prep** | `gate_fail_report.md`, `solver_ballast_plan.csv`, DNV section | 45 min |
| **Manager** | `gate_fail_report.md` (summary), `PIPELINE_CONSOLIDATED_*.xlsx` | 10 min |

---

## 11. Best Practices

### 11.1 Review Workflow

1. **Always start with `gate_fail_report.md`**
   - Quick overview of compliance status
   - Identifies critical issues immediately

2. **Verify ballast plan feasibility**
   - Check pump times
   - Verify tank capacities
   - Review operational sequence

3. **Cross-reference multiple files**
   - Compare `solver_ballast_summary.csv` with `pipeline_stage_QA.csv`
   - Verify consistency across files

4. **Check logs for warnings**
   - Review `logs/04_SOLVER_LP.log` for solver issues
   - Check `diff_audit.csv` for sensor data problems

### 11.2 Documentation Standards

- **Always record ITTC shaft immersion** (not just AFT draft)
- **Include Chart Datum reference** for FWD draft
- **Document mitigation measures** for any violations
- **Keep audit trail** of sensor data injection

---

## 12. Glossary

| Term | Definition |
|------|------------|
| **Gate-A** | AFT_MIN_2p70 - Captain/Propulsion gate (AFT ≥ 2.70m) |
| **Gate-B** | FWD_MAX_2p70_critical_only - Mammoet/RoRo gate (FWD ≤ 2.70m, critical stages) |
| **UKC** | Under Keel Clearance - Distance from keel to seabed |
| **Freeboard** | Distance from waterline to deck (tide-independent) |
| **Chart Datum** | Reference level for charted depths and tides |
| **SSOT** | Single Source of Truth - Authoritative data source |
| **Hold Point** | Operational checkpoint for draft verification |

---

## Appendix A: Example Review Session

### Step-by-Step Example

**Scenario**: Review results for Stage 5_PreBallast and Stage 6A_Critical

1. **Open `gate_fail_report.md`** (2 min)
   - Section 1: Gate Violation Summary
   - Find: Gate-A violations in 2 stages
   - Section 4: Stage-wise table
   - Find: Stage 5_PreBallast (-0.54m), Stage 6A_Critical (-0.34m)

2. **Review `solver_ballast_summary.csv`** (3 min)
   - Filter: Stage 5_PreBallast, Stage 6A_Critical
   - Check: `New_AFT_m` values
   - Verify: `viol_aft_min_m` amounts

3. **Check `solver_ballast_plan.csv`** (5 min)
   - Filter: Stage 5_PreBallast
   - Verify: AFT tanks used (VOID3.P/S)
   - Check: Total ballast quantities
   - Calculate: Total pump time

4. **Review DNV Mitigation Section** (5 min)
   - Section 8: DNV Mitigation Measures
   - Note: Required measures for both stages
   - Prepare: Approval document checklist

5. **Verify Sequence Files** (5 min)
   - Check: `BALLAST_EXEC.csv` for operational sequence
   - Review: `HOLD_POINT_SUMMARY.csv` for decision points
   - Verify: Draft targets at each step

**Total Time**: ~20 minutes

---

## Appendix B: Checklist Template

### Results Review Checklist

**Date**: _______________
**Pipeline Run**: `pipeline_out_<timestamp>/`
**Reviewer**: _______________

#### Initial Checks
- [ ] Output directory exists
- [ ] No critical errors in terminal
- [ ] All expected files present

#### Gate Compliance
- [ ] Gate-A status reviewed
- [ ] Gate-B status reviewed
- [ ] Violations identified and documented
- [ ] Mitigation measures reviewed (if violations)

#### Ballast Plan
- [ ] Ballast quantities verified
- [ ] Pump times acceptable
- [ ] Tank capacities respected
- [ ] Operational sequence reviewed

#### Sequence Files (if enabled)
- [ ] Execution sequence verified
- [ ] Hold points identified
- [ ] Decision criteria understood

#### Approval Preparation (if violations)
- [ ] DNV mitigation measures documented
- [ ] ITTC shaft immersion calculated
- [ ] Approval document prepared
- [ ] Captain/Owner acceptance obtained

#### Final Verification
- [ ] All critical issues addressed
- [ ] Operations team briefed
- [ ] Approval documents ready
- [ ] Monitoring plan in place

**Review Status**: ☐ PASS ☐ FAIL ☐ CONDITIONAL
**Notes**: _______________________________________

---

**End of Guide**

For additional support:
- Technical documentation: `03_DOCUMENTATION/00_CORE_ARCHITECTURE/`
- Options reference: `Ballast Pipeline - Complete Options Reference Guide.md`
- User guide: `Ballast Pipeline - Complete User Guide for First-Time Users.md`
