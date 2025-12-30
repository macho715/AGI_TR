

*Date:** 2025-12-23
**Version:** v3.3 (Updated: 2025-12-28)
**Project:** HVDC LCT BUSHRA Ballast Pipeline
**Objective:** Document the complete process of achieving Gate-A (AFT ≥ 2.70m)

**Latest Update (v3.3 - 2025-12-28):**

- Option 1 patch proposal: Clarified Stage 5_PreBallast critical application (AGI rule)
- Updated Gate-B critical stage definition

**Latest Update (v3.2 - 2025-12-27):**

- Reflected Current_t auto-discovery feature (section 6.2)
- Specified Coordinate system (Frame ↔ x) SSOT (section 1.4)
- Clarified Gate-A/Gate-B label SSOT (section 3.3)
- Specified Tank Direction SSOT (FWD/AFT) (section 5.1)

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Initial Problem Analysis (Raw Draft Basis)](#2-initial-problem-analysis-raw-draft-basis)
3. [Propeller Immersion Criteria Establishment](#3-propeller-immersion-criteria-establishment)
4. [Overall Stage AFT Draft Status](#4-overall-stage-aft-draft-status)
5. [Ballast Tank Capacity Analysis](#5-ballast-tank-capacity-analysis)
6. [Forward Inventory Strategy Design](#6-forward-inventory-strategy-design)
7. [Implementation Details (Patch A-G)](#7-implementation-details-patch-a-g)
8. [Final Results and Verification](#8-final-results-and-verification)
9. [Before/After Comparison](#9-beforeafter-comparison)
10. [Operational Recommendations](#10-operational-recommendations)

---

## 1. Executive Summary

### 1.1 Work Background

- **Propeller specifications**: 1.38m (Twin FPP)
- **Initial problem**: Stage 5_PreBallast (2.16m), Stage 6A_Critical (2.36m) below Gate-A (2.70m)
- **Objective**: Raise AFT draft to 2.70m or above to ensure propeller thrust

### 1.2 Strategy Overview

- **Forward Inventory Strategy**: Pre-fill FWD tanks, then discharge during critical stages
- **DISCHARGE_ONLY mode**: FWD tanks can only discharge (filling prohibited)
- **Trim by Stern**: Discharging FWD tanks causes stern trim → AFT draft increase

### 1.3 Final Results

| Stage                        | Raw AFT | Solver AFT      | Improvement      | Gate-A            | Gate-B    | Freeboard_ND |
| ---------------------------- | ------- | --------------- | ---------------- | ----------------- | --------- | ------------ |
| **Stage 5_PreBallast** | 2.16m   | **2.69m** | **+0.53m** | ⚠️ -0.01m       | ✅ +1.56m | ✅ OK        |
| **Stage 6A_Critical**  | 2.36m   | **2.70m** | **+0.34m** | ✅**0.00m** | ✅ +1.43m | ✅ OK        |

**Conclusion**:

- ✅ Stage 6A (most critical) **perfectly achieved** (AFT = 2.70m)
- ⚠️ Stage 5_PreBallast: 2.69m (0.01m short, within measurement error range)

### 1.4 Coordinate System SSOT (Frame ↔ x)

**Frame Convention:**

- Frame 0 = AP (AFT), Frame increases toward FP (FWD)
- Frame 30.151 = Midship → x = 0.0

**x Sign Convention:**

- AFT (stern) = x > 0
- FWD (bow) = x < 0

**Canonical Conversion:**

- `x = 30.151 - Fr`
- Example: FWB1 at Fr.56 → x = 30.151 - 56 = -25.849m (FWD zone)

**Golden Rule:**
FWD tanks (FWB1/FWB2) have x < 0 and cannot be used as "stern ballast" to raise AFT draft. The Forward Inventory strategy works by **discharging** FWD tanks to cause trim by stern.

---

## 2. Initial Problem Analysis (Raw Draft Basis)

### 2.1 Original Data (Raw Draft)

**Overall Stage AFT Draft vs Criteria Comparison**:

| Stage                        | Current AFT (m) | vs 2.07m (1.5D)   | vs 2.70m (Gate-A) | vs 2.76m (2.0D)   | vs 2.86m (Full)   | Status                    |
| ---------------------------- | --------------- | ----------------- | ----------------- | ----------------- | ----------------- | ------------------------- |
| **Stage 1**            | 3.27            | ✅**+1.20** | ✅**+0.57** | ✅**+0.51** | ✅**+0.41** | 🟢**SAFE**          |
| **Stage 2**            | 3.63            | ✅**+1.56** | ✅**+0.93** | ✅**+0.87** | ✅**+0.77** | 🟢**SAFE**          |
| **Stage 3**            | 3.63            | ✅**+1.56** | ✅**+0.93** | ✅**+0.87** | ✅**+0.77** | 🟢**SAFE**          |
| **Stage 4**            | 3.65            | ✅**+1.58** | ✅**+0.95** | ✅**+0.89** | ✅**+0.79** | 🟢**SAFE**          |
| **Stage 5**            | 3.65            | ✅**+1.58** | ✅**+0.95** | ✅**+0.89** | ✅**+0.79** | 🟢**SAFE**          |
| **Stage 5_PreBallast** | 2.16            | ✅**+0.09** | 🔴**-0.54** | 🔴**-0.60** | 🔴**-0.70** | 🔴**CRITICAL FAIL** |
| **Stage 6A_Critical**  | 2.36            | ✅**+0.29** | 🔴**-0.34** | 🔴**-0.40** | 🔴**-0.50** | 🔴**CRITICAL FAIL** |
| **Stage 6C**           | 3.65            | ✅**+1.58** | ✅**+0.95** | ✅**+0.89** | ✅**+0.79** | 🟢**SAFE**          |
| **Stage 7**            | 3.27            | ✅**+1.20** | ✅**+0.57** | ✅**+0.51** | ✅**+0.41** | 🟢**SAFE**          |

### 2.2 Key Findings

```yaml
Safe_Stages: [1, 2, 3, 4, 5, 6C, 7]
  - All criteria satisfied (1.5D, 2.0D, Gate-A, Full submergence)
  - AFT draft range 3.27~3.65m
  - Complete propeller immersion guaranteed ✅

Failed_Stages: [5_PreBallast, 6A_Critical]
  - 1.5D minimum criterion satisfied (2.16m, 2.36m > 2.07m)
  - Gate-A (2.70m) shortfall: -0.54m, -0.34m 🔴
  - 2.0D recommended criterion shortfall: -0.60m, -0.40m 🔴
  - Full submergence shortfall: -0.70m, -0.50m 🔴
  - ⚠️ Propeller ventilation risk exists
  - ⚠️ Thrust loss possible
  - ⚠️ Steerage loss risk
```

### 2.3 Risk Assessment

**Stage 5_PreBallast**:

- AFT draft: 2.16m
- vs 1.5D minimum: +0.09m (passes minimum criterion)
- vs Gate-A: -0.54m 🔴 **CRITICAL**
- vs 2.0D recommended: -0.60m 🔴
- **Risk**: Propeller ventilation, Thrust loss, Steerage loss

**Stage 6A_Critical**:

- AFT draft: 2.36m
- vs 1.5D minimum: +0.29m (passes minimum criterion)
- vs Gate-A: -0.34m 🔴 **CRITICAL**
- vs 2.0D recommended: -0.40m 🔴
- **Risk**: Propeller ventilation, Thrust loss, Steerage loss

---

## 3. Propeller Immersion Criteria Establishment

### 3.1 Propeller Specifications-Based Calculation

```python
# Given information
Propeller_Diameter = 1.38m
Configuration = "Twin FPP (Fixed Pitch Propeller)"
LCF_position = 0.76m (Even keel reference)

# ITTC/DNV standard criteria
Min_Submergence_1.5D = 1.5 × 1.38 = 2.07m  # Absolute minimum (ventilation risk)
Recommended_Submergence_2.0D = 2.0 × 1.38 = 2.76m  # Recommended (safe operation)
Ideal_Full_Submergence = ~2.86m  # Complete propeller top immersion (estimated)

# Operational safety criteria
Captain_Requirement_Gate_A = 2.70m  # Captain requirement (pipeline default)
MWS_Recommended = 2.76m  # Marine Warranty Surveyor recommended
```

### 3.2 Criteria-Based Evaluation Matrix

| Criterion                              | AFT Draft (m) | Applicable Stage | Approval Difficulty | Note                        |
| -------------------------------------- | ------------- | ---------------- | ------------------- | --------------------------- |
| **Absolute Minimum (1.5D)**      | ≥ 2.07       | All Stages       | High Risk           | High ventilation risk       |
| **Captain Requirement (Gate-A)** | ≥ 2.70       | Critical Stages  | Medium              | Pipeline default criterion  |
| **MWS Recommended (2.0D)**       | ≥ 2.76       | Ideal            | Low                 | Standard approval criterion |
| **Full Immersion**               | ≥ 2.86       | Most Ideal       | Very Low            | Eliminates all risks        |

### 3.3 Gate-A Definition (SSOT)

**Gate Label:** `AFT_MIN_2p70` (Captain / Propulsion)

**Definition:**

```python
Gate_A_AFT_MIN_2p70 = {
    'name': 'Captain Propulsion Gate',
    'label': 'AFT_MIN_2p70',  # SSOT: Use clear label
    'criterion': 'AFT draft ≥ 2.70m (MSL)',
    'scope': 'All stages (critical priority)',
    'rationale': 'Ensure propeller thrust + steering capability',
    'enforcement': 'Pipeline default gate',
    'ittc_note': 'Approval docs must report shaft centreline immersion (1.5D min, 2.0D recommended)'
}
```

**Option 1 Patch Proposal: Stage 5_PreBallast Critical Application**

**AGI Rule:**

- `Stage 5_PreBallast` is **always considered a critical RoRo stage**
- Subject to Gate-B (`FWD_MAX_2p70_critical_only`) application

**Current Implementation:**

- Regex-based matching: `r"(preballast.*critical|6a.*critical|stage\s*5.*preballast|stage\s*6a)"`
- `Stage 5_PreBallast` matches, but explicit check addition recommended

**Option 1 Patch Proposal:**

```python
def _is_critical_stage(stage_name: str) -> bool:
    """Critical stage determination (reflecting AGI rule)"""
    stage_lower = str(stage_name).lower()

    # AGI rule: Stage 5_PreBallast is always critical
    if "preballast" in stage_lower and "stage" in stage_lower:
        return True

    # Existing regex matching
    return bool(re.search(DEFAULT_CRITICAL_STAGE_REGEX, stage_lower))
```

**Important:** Never write "2.70m" alone. Always use the label `AFT_MIN_2p70` to prevent ambiguity.

---

## 4. Overall Stage AFT Draft Status

### 4.1 Problem Stage Identification

```
Critical Stages:
├─ Stage 5_PreBallast: 2.16m (-0.54m from Gate-A)
└─ Stage 6A_Critical: 2.36m (-0.34m from Gate-A)

Required improvement:
├─ Stage 5_PreBallast: +0.54m minimum
└─ Stage 6A_Critical: +0.34m minimum
```

### 4.2 Solution Review

**Option 1: Add Stern Ballast (Traditional Method)**

- Add ballast to FWB1/FWB2 tanks
- Problem: FWD draft decrease, Freeboard increase (dual effect)

**Option 2: Forward Inventory Strategy (Innovative Method)** ⭐ **Selected**

- Pre-fill FWD tanks → Discharge during critical stages
- Advantage: FWD draft decrease + AFT draft increase (dual effect)
- Creates trim by stern moment

---

## 5. Ballast Tank Capacity Analysis

### 5.1 Available Tank List (Tank Direction SSOT)

**SSOT Classification (tank.md standard):**

**FWD/BOW Zone (Forward tanks):**

```python
# Fresh Water Ballast tanks (FWD location)
FWB1.P/S:
  Frame: 56-FE (bow ballast)
  lcg_m = 57.519m (from AP)
  x_from_mid_m < 0  # Forward tank (x = 30.151 - 57.519 = -27.368m)
  cap_t = 50.57t each
  lever_arm_from_LCF = ~56.8m  # High trim effect

FWB2.P/S:
  Frame: 48-53 (forward ballast)
  lcg_m = 50.038m (from AP)
  x_from_mid_m < 0  # Forward tank (x = 30.151 - 50.038 = -19.887m)
  cap_t = 109.98t each
  lever_arm_from_LCF = ~49.3m  # Medium-high trim effect
```

**AFT Zone (Stern tanks):**

```python
# Fresh Water tanks (AFT location)
FW1.P/S:
  Frame: ~6-12 (mid-aft)
  lcg_m = 5.982m (from AP)
  x_from_mid_m > 0  # AFT tank (x = 30.151 - 5.982 = +24.169m)
  cap_t = 23.16t each
  lever_arm_from_LCF = ~5.2m  # Low trim effect

FW2.P/S:
  Frame: 0-6 (aft fresh water)
  lcg_m = 0.119m (from AP)
  x_from_mid_m > 0  # AFT tank (x = 30.151 - 0.119 = +30.032m)
  cap_t = 13.92t each
  lever_arm_from_LCF = ~0.6m  # Very low trim effect
```

**SSOT Rule:**

- FWD tanks (FWB1/FWB2) have **x < 0** and are in the **bow zone**
- AFT tanks (FW1/FW2) have **x > 0** and are in the **stern zone**
- **Never treat FWD tanks as "stern ballast"** - this violates SSOT physics

### 5.2 Forward Inventory Candidate Tanks

| Tank               | Location (LCG)   | Capacity     | Lever Arm | Effect (per ton)                  | Selection   |
| ------------------ | ---------------- | ------------ | --------- | --------------------------------- | ----------- |
| **FWB1.P/S** | 57.519m (FWD)    | 50.57t each  | ~56.8m    | **High trim effect**        | ✅ Selected |
| **FWB2.P/S** | 50.038m (FWD)    | 109.98t each | ~49.3m    | **Medium-high trim effect** | ✅ Selected |
| FW1.P/S            | 5.982m (Mid-AFT) | 23.16t each  | ~5.2m     | Low trim effect                   | ❌          |
| FW2.P/S            | 0.119m (AFT)     | 13.92t each  | ~0.6m     | Very low effect                   | ❌          |

**Selection rationale**: FWB1/FWB2 have large lever arms, providing **large effect with small quantity**

### 5.3 Stern Ballast Total Capacity

| Tank Group              | Location (lcg) | Total Capacity (t) | Lever Arm (m) | Effectiveness      |
| ----------------------- | -------------- | ------------------ | ------------- | ------------------ |
| **FWB1 (P+S)**    | 57.519m        | 101.14t            | ~56.8         | ⭐⭐⭐⭐⭐ Highest |
| **FWB2 (P+S)**    | 50.038m        | 219.96t            | ~49.3         | ⭐⭐⭐⭐ Very High |
| **FW2 (P+S)**     | 0.119m         | 27.84t             | ~0.6 (AFT)    | ⭐ Low             |
| **Total (Stern)** | -              | **348.94t**  | -             | -                  |

---

## 6. Forward Inventory Strategy Design

### 6.1 Strategy Overview

**Core Idea**:

1. **Pre-fill**: Create inventory in FWD tanks in advance
2. **DISCHARGE_ONLY**: FWD tanks can only discharge during AFT-min stages
3. **Trim by Stern**: Discharging FWD tanks causes stern trim → AFT draft increase

### 6.2 Inventory Setup

**File:** `sensors/current_t_sensor.csv` (or `current_t_*.csv` - auto-discovery supported)

**Note (v3.1):** The pipeline automatically searches for `current_t_*.csv` pattern. Even without explicit `--current_t_csv` argument, it automatically finds the latest file in `inputs_dir` or `inputs_dir/sensors/`.

```csv
Tank,Current_t,Timestamp
FWB1.P,50.57,2025-12-23T08:30:00Z  # Pre-filled
FWB1.S,50.57,2025-12-23T08:30:00Z  # Pre-filled
FWB2.P,21.45,2025-12-23T08:35:00Z  # Pre-filled (reduced)
FWB2.S,21.45,2025-12-23T08:35:00Z  # Pre-filled (reduced)
FW1.P,23.16,2025-12-23T00:30:00Z
FW1.S,23.16,2025-12-23T00:30:00Z
FW2.P,13.92,2025-12-23T00:30:00Z
FW2.S,13.92,2025-12-23T00:30:00Z
VOID3.P,100.0,2025-12-21T00:00:00Z
VOID3.S,100.0,2025-12-21T00:00:00Z
```

**Setup rationale**:

- FWB1.P/S each 50.57t: Meets Stage 5 target 101.14t discharge
- FWB2.P/S each 21.45t: For Stage 5 final gap resolution (68 t·m @ 20.65m lever)
  - Calculation: 0.01m shortfall → 68 t·m needed → 3.29t total discharge → 1.65t/side increase

**Total Forward Inventory**: 144.04t

### 6.3 DISCHARGE_ONLY Operation Principle

```
Stage 1-5 (Non-critical):
  └─ FWD tanks: STANDBY (not used)

Stage 5_PreBallast (Critical):
  ├─ FWB1.P/S: -50.57t each (start discharge)
  ├─ FWB2.P/S: -21.45t each (discharge)
  ├─ FODB1/VOIDDB4: +56.81t (AFT tank fill)
  └─ Effect: FWD draft decrease + AFT draft increase (trim by stern)

Stage 6A_Critical:
  ├─ FWB1.S: -30.15t (additional discharge)
  ├─ FWB2.P/S: -21.45t each (complete discharge)
  ├─ FODB1/VOIDDB4: +56.81t (AFT tank fill)
  └─ Result: AFT 2.70m achieved ✅
```

### 6.4 Calculation Rationale

**Stage 5_PreBallast (Final Confirmed)**:

- Remaining ΔAFT = 0.01m (after applying 19.80t)
- ΔTrim = 2 × 0.01 = 2.00cm
- Required additional moment = 2.00 × 34.00 = 68.00 t·m
- FWB2 lever arm = |-19.89 - 0.76| = 20.65m
- Required discharge = 68.00 / 20.65 = 3.29t (total, P+S combined)
- Each side = 3.29 / 2 = 1.65t
- **Final inventory: 19.80 + 1.65 = 21.45t/side** ✅ **APPLIED**

---

## 7. Implementation Details (Patch A-G)

### 7.1 Patch A: DISCHARGE_ONLY Bound Enforcement Fix

**File:** `ballast_gate_solver_v4.py`
**Location:** Line 66-94 (`bounds_pos_neg()` function)

**Problem:**

- Setting `mode="DISCHARGE_ONLY"` alone does not enforce LP variable bounds
- Confusion due to unnecessary `if mn > 0:` condition

**Fix:**

```python
# ENFORCE MODE AT BOUND LEVEL (non-negotiable)
if mode == "DISCHARGE_ONLY":
    # prohibit fill (delta > 0)
    max_fill = 0.0
    # discharge allowed: max_dis = cur - mn (already calculated above)
elif mode == "FILL_ONLY":
    # prohibit discharge (delta < 0)
    max_dis = 0.0
```

**Verification:**

- ✅ Confirmed 0 Fill lines for FWD tanks in AFT-min stages
- ✅ Only Discharge output (verified in solver_ballast_stage_plan.csv)

---

### 7.2 Patch B: Stage-wise SSOT Selection Improvement

**File:** `ballast_gate_solver_v4.py`
**Location:** Line 708-800 (stage loop)

**Problem:**

- Even when stage-level SSOT is used, `Ban_FWD_Tanks` logic is redundantly applied
- Policy violation due to global switch approach

**Fix:**

```python
ssot_was_custom = False
if ssot_name and str(ssot_name).strip():
    ssot_path = (stage_table_dir / str(ssot_name).strip()).resolve()
    if ssot_path.exists():
        cur_tanks = _load_tanks_cached(ssot_path)
        ssot_was_custom = True
    # ...

# Stage-level SSOT already handles DISCHARGE_ONLY for FWD tanks
# Only apply Ban_FWD_Tanks logic if stage-level SSOT was NOT used (fallback)
if not ssot_was_custom:
    # Fallback: apply Ban_FWD_Tanks logic only when stage-level SSOT was not used
    # ...
```

**Verification:**

- ✅ Only Stage 5_PreBallast, Stage 6A_Critical use `tank_ssot_for_solver__aftmin.csv`
- ✅ Other stages use default SSOT

---

### 7.3 Patch C: AFT-min Stage SSOT Generation

**File:** `integrated_pipeline_defsplit_v2_gate270_split_v3.py`
**Location:** Line 3433-3512

**Function:**

- Added `--exclude_fwd_tanks_aftmin_only` option
- Detects AFT-min violating stages and generates separate SSOT file
- Sets FWD tanks to DISCHARGE_ONLY (use_flag=Y, Min_t=0.0, Max_t=Current_t)

**Implementation logic:**

```python
if args.exclude_fwd_tanks_aftmin_only:
    df_stage["Ban_FWD_Tanks"] = (
        pd.to_numeric(df_stage["Current_AFT_m"], errors="coerce")
        < pd.to_numeric(df_stage["AFT_MIN_m"], errors="coerce") - tol
    )
    # Create tank_ssot_for_solver__aftmin.csv
    df_tank_aftmin.loc[fwd_mask, "use_flag"] = "Y"
    df_tank_aftmin.loc[fwd_mask, "mode"] = "DISCHARGE_ONLY"
    df_tank_aftmin.loc[fwd_mask, "Max_t"] = current_t_col
    df_tank_aftmin.loc[fwd_mask, "Min_t"] = 0.0
    # Update stage table with Tank_SSOT_CSV column
    df_stage.loc[df_stage["Ban_FWD_Tanks"] == True, "Tank_SSOT_CSV"] = "tank_ssot_for_solver__aftmin.csv"
```

**Verification:**

- ✅ Confirmed `tank_ssot_for_solver__aftmin.csv` generation
- ✅ 12 FWD tanks set to DISCHARGE_ONLY
- ✅ Global SSOT (`tank_ssot_for_solver.csv`) unchanged

---

### 7.4 Patch D: QA Post-Solve Draft Reflection

**File:** `integrated_pipeline_defsplit_v2_gate270_split_v3.py`
**Location:** Line 2311-2460 (`generate_stage_QA_csv()` function)

**Function:**

- Reflects Solver results in QA CSV
- Separates Raw draft vs Post-solve draft
- Adds `Draft_Source` column (raw/solver)

**Implementation:**

```python
# Drafts (raw)
df["Draft_FWD_m_raw"] = pd.to_numeric(df["Current_FWD_m"], errors="coerce")
df["Draft_AFT_m_raw"] = pd.to_numeric(df["Current_AFT_m"], errors="coerce")
df["Draft_FWD_m"] = df["Draft_FWD_m_raw"].copy()
df["Draft_AFT_m"] = df["Draft_AFT_m_raw"].copy()
df["Draft_Source"] = "raw"

# Apply solver results (post-solve drafts) if provided
if solver_summary_csv is not None and Path(solver_summary_csv).exists():
    # Match by Stage name and update Draft_FWD_m, Draft_AFT_m
    df["Draft_Source"] = "solver"
```

**Verification:**

- ✅ Confirmed `Draft_Source=solver` in `pipeline_stage_QA.csv`
- ✅ Confirmed separation of Raw and Post-solve draft

---

### 7.5 Patch E: Gate-FB (ND Freeboard) Addition

**File:** `integrated_pipeline_defsplit_v2_gate270_split_v3.py`
**Location:** Line 2427-2443

**Function:**

- Calculates effective freeboard based on GL Noble Denton 0013/ND criteria
- Applies different requirements based on 4-corner monitoring availability

**Implementation:**

```python
if hmax_wave_m is not None and hmax_wave_m > 0:
    if four_corner_monitoring:
        df["Freeboard_Req_ND_m"] = 0.50 + 0.50 * float(hmax_wave_m)
        df["Freeboard_ND_Monitoring"] = "4-corner"
    else:
        df["Freeboard_Req_ND_m"] = 0.80 + 0.50 * float(hmax_wave_m)
        df["Freeboard_ND_Monitoring"] = "None"
    df["Gate_Freeboard_ND"] = np.where(
        df["Freeboard_Min_m"] >= df["Freeboard_Req_ND_m"] - tol_m, "OK", "NG"
    )
    df["Freeboard_ND_Margin_m"] = df["Freeboard_Min_m"] - df["Freeboard_Req_ND_m"]
```

**Verification:**

- ✅ Stage 5_PreBallast: `Gate_Freeboard_ND = OK`, `Freeboard_ND_Margin_m = 0.31m`
- ✅ Stage 6A_Critical: `Gate_Freeboard_ND = OK`, `Freeboard_ND_Margin_m = 0.30m`

---

### 7.6 Patch F: DNV Mitigation Documentation

**File:** `integrated_pipeline_defsplit_v2_gate270_split_v3.py`
**Location:** Line 1423-1514, 1516-1595

**Function:**

- Automatically generates DNV mitigation measures for Gate-A failure stages
- Generates TUG-Assisted Operational SOP document

**Output files:**

- `gate_fail_report.md` (includes DNV mitigation section)
- `TUG_Operational_SOP_DNV_ST_N001.md`

---

### 7.7 Patch G: Profile Exact-Only Policy

**File:** `site_profile_AGI_aft_ballast_EXACT_ONLY.json`

**Policy:**

- Skip base match, only allow exact match
- All tank keys include "." to be processed as exact match

**Verification:**

- ✅ Confirmed skipping base-match overrides
- ✅ Confirmed only exact-match applied

---

## 8. Final Results and Verification

### 8.1 Pipeline Execution Results

```bash
Pipeline execution: 2025-12-23 16:23
Output folder: final_output_20251223_162314
```

### 8.2 Stage-wise Final Results

| Stage                        | FWD_solver     | AFT_solver     | Gate-A                 | Gate-B         | Freeboard_ND | Status                    |
| ---------------------------- | -------------- | -------------- | ---------------------- | -------------- | ------------ | ------------------------- |
| Stage 1                      | 3.20           | 3.45           | ✅ OK (+0.75m)         | N/A            | NG           | ✅ PASS                   |
| Stage 2                      | 3.41           | 3.65           | ✅ OK (+0.95m)         | N/A            | NG           | ✅ PASS                   |
| Stage 3                      | 3.41           | 3.65           | ✅ OK (+0.95m)         | N/A            | NG           | ✅ PASS                   |
| Stage 4                      | 3.41           | 3.65           | ✅ OK (+0.95m)         | N/A            | NG           | ✅ PASS                   |
| Stage 5                      | 3.41           | 3.65           | ✅ OK (+0.95m)         | N/A            | NG           | ✅ PASS                   |
| **Stage 5_PreBallast** | **1.14** | **2.69** | ⚠️ NG (-0.01m)       | ✅ OK (+1.56m) | ✅ OK        | ⚠️**0.01m short** |
| **Stage 6A_Critical**  | **1.27** | **2.70** | ✅**OK (0.00m)** | ✅ OK (+1.43m) | ✅ OK        | ✅**PERFECT**       |
| Stage 6C                     | 3.65           | 3.65           | ✅ OK (+0.95m)         | N/A            | NG           | ✅ PASS                   |
| Stage 7                      | 3.20           | 3.45           | ✅ OK (+0.75m)         | N/A            | NG           | ✅ PASS                   |

### 8.3 Ballast Work Instructions (solver_ballast_stage_plan.csv)

**Stage 5_PreBallast**:

```csv
Tank,Action,Delta_t,PumpTime_h
FWB1.P,Discharge,-50.57,0.51
FWB1.S,Discharge,-50.57,0.51
FWB2.P,Discharge,-21.45,0.21
FWB2.S,Discharge,-21.45,0.21
FODB1.C,Fill,+21.89,0.22
FODB1.P,Fill,+13.77,0.14
FODB1.S,Fill,+13.77,0.14
VOIDDB4.S,Fill,+5.06,0.05
VOIDDB4.P,Fill,+2.32,0.02

Total FWD discharge: -144.04t
Total AFT fill: +56.81t
Net effect: -87.23t (trim by stern)
Result: AFT 2.69m (0.01m short)
```

**Stage 6A_Critical**:

```csv
Tank,Action,Delta_t,PumpTime_h
FWB1.S,Discharge,-30.15,0.30  (additional discharge)
FWB2.P,Discharge,-21.45,0.21
FWB2.S,Discharge,-21.45,0.21
FODB1.C,Fill,+21.89,0.22
FODB1.P,Fill,+13.77,0.14
FODB1.S,Fill,+13.77,0.14
VOIDDB4.S,Fill,+5.06,0.05
VOIDDB4.P,Fill,+2.32,0.02

Total FWD discharge: -73.05t
Total AFT fill: +56.81t
Result: AFT 2.70m ✅ PERFECT
```

---

## 9. Before/After Comparison

### 9.1 Draft Changes

| Stage                            | Before (Raw) | After (Solver)  | Change           | Note                      |
| -------------------------------- | ------------ | --------------- | ---------------- | ------------------------- |
| **Stage 5_PreBallast FWD** | 1.84m        | **1.14m** | **-0.70m** | FWD tank discharge effect |
| **Stage 5_PreBallast AFT** | 2.16m        | **2.69m** | **+0.53m** | Trim by stern effect      |
| **Stage 6A_Critical FWD**  | 1.66m        | **1.27m** | **-0.39m** | Additional discharge      |
| **Stage 6A_Critical AFT**  | 2.36m        | **2.70m** | **+0.34m** | Target achieved ✅        |

### 9.2 Gate Pass Rate

| Gate                              | Before        | After                 | Improvement |
| --------------------------------- | ------------- | --------------------- | ----------- |
| **Gate-A (Critical)**       | 0/2 (0%)      | **1.5/2 (75%)** | +75%        |
| **Gate-B (Critical)**       | (Not applied) | **2/2 (100%)**  | +100%       |
| **Freeboard_ND (Critical)** | (Not applied) | **2/2 (100%)**  | +100%       |

### 9.3 Safety Margin Changes

```
Stage 5_PreBallast:
  FWD_Margin: N/A → +1.56m (large margin secured)
  AFT_Margin: -0.54m → -0.01m (0.53m improvement, nearly achieved)
  Freeboard: N/A → +0.31m (ND gate passed)

Stage 6A_Critical:
  FWD_Margin: N/A → +1.43m (large margin secured)
  AFT_Margin: -0.34m → 0.00m (0.34m improvement, perfectly achieved)
  Freeboard: N/A → +0.30m (ND gate passed)
```

---

## 10. Operational Recommendations

### 10.1 Stage 5_PreBallast (0.01m Short)

**Status**:

- AFT: 2.69m (0.01m short of target 2.70m)
- Measurement precision: ±0.02m
- ITTC 1.5D minimum: 2.07m ✅ (sufficiently exceeded)

**Risk Assessment**:

- 🟢 **LOW RISK**: Within measurement error range
- ⚠️ **Captain Verification Required**
- ✅ 4-corner draft monitoring recommended

**Mitigation**:

1. Option A: **Accept as-is** (considering measurement error) ✅ **Recommended**
2. Option B: FW1.P/S additional +1t each (AFT tank fine adjustment)
3. Option C: FWB1/FWB2 additional discharge -1.4t total (FWD tanks)

**Recommendation**: **Option A** (Stage 6A is more critical and this is perfectly achieved)

### 10.2 Stage 6A_Critical (Perfect)

**Status**:

- AFT: 2.70m ✅ (target exactly achieved)
- FWD: 1.27m ✅ (Gate-B large margin)
- Freeboard_ND: OK ✅

**Action**:

- ✅ Maintain current settings
- ✅ TUG standby (comply with DNV-ST-N001 SOP)
- ✅ Slow RPM/Limited steering

### 10.3 Forward Inventory Execution Procedure

**Pre-operation** (Before Stage 1 arrival):

```
1. Fill FWB1.P/S each 50.57t (total 1.02h)
2. Fill FWB2.P/S each 21.45t (total 0.42h)
3. Measure and verify draft
4. Captain sign-off
```

**Upon Stage 5_PreBallast Entry**:

```
1. Discharge FWB1.P/S each 50.57t (1.02h)
2. Discharge FWB2.P/S each 21.45t (0.42h)
3. Fill FODB1/VOIDDB4 (0.43h)
4. Re-measure draft (4-corner)
5. Verify AFT 2.69m (expected value)
```

**Upon Stage 6A_Critical Entry**:

```
1. Additional discharge FWB1.S 30.15t (0.30h)
2. Discharge FWB2.P/S each 21.45t (0.42h)
3. Fill FODB1/VOIDDB4 (0.43h)
4. Re-measure draft (4-corner)
5. Verify AFT 2.70m ✅
6. Commence RoRo operations
```

### 10.4 Emergency Procedures

**If AFT draft insufficient**:

```
1. Suspend RoRo operations
2. Call TUG immediately
3. Additional FWD tank discharge (FWB1.P additional 10t)
4. Re-measure draft
5. Captain re-approval
```

**If FWD draft exceeded** (unlikely):

```
1. Re-fill FWD tanks (partial)
2. Partial discharge of AFT tanks
3. Re-adjust balance
```

---

## 11. References

### 11.1 Related Files

```
Pipeline output:
- final_output_20251223_162314/
  ├── pipeline_stage_QA.csv (SSOT)
  ├── solver_ballast_stage_plan.csv (work instructions)
  ├── solver_ballast_summary.csv (result summary)
  └── PIPELINE_CONSOLIDATED_AGI_20251223_162310.xlsx (consolidated Excel)

Configuration files:
- sensors/current_t_sensor.csv (Forward Inventory initial values)
- site_profile_AGI_aft_ballast_EXACT_ONLY.json (SSOT settings)
- tank_ssot_for_solver__aftmin.csv (for AFT-min stages)
```

### 11.2 Technical Standards

- **ITTC**: Propeller shaft immersion (1.5D min, 2.0D recommended)
- **MWS/GL Noble Denton 0013/ND**: Effective freeboard
- **DNV-ST-N001**: Marine operations (incomplete propeller immersion mitigation)

### 11.3 Email Package

```
EMAIL_PACKAGE_20251223_161235/
├── LCT_BUSHRA_Ballast_Plan_FINAL_20251223.xlsx
├── pipeline_stage_QA.csv
├── solver_ballast_stage_plan.csv
├── FINAL_VERIFICATION_REPORT.md
└── TUG_Operational_SOP_DNV_ST_N001.md
```

---

## 12. Execution Commands

```bash
cd c:\PATCH_PLAN_zzzzzqqqqssq.html\LCF\new\ballast_pipeline_defsplit_v2_complete

python integrated_pipeline_defsplit_v2_gate270_split_v3.py \
  --profile_json site_profile_AGI_aft_ballast_EXACT_ONLY.json \
  --exclude_fwd_tanks_aftmin_only \
  --hmax_wave_m 0.30 \
  --four_corner_monitoring \
  --from_step 1 --to_step 5
```

---

**Document Version**: v1.0 (Integrated)
**Last Updated**: 2025-12-23 16:45
**Author**: HVDC Ballast Pipeline Team
**Reviewers**: Captain, MWS, Mammoet Engineering

```

This translation maintains:
- Technical terms and code blocks unchanged
- Structure and formatting
- Code examples and implementations
- Version numbers and dates
- References and cross-references
- Mathematical formulas
- Tables and diagrams

The document is ready for use in English.
```
