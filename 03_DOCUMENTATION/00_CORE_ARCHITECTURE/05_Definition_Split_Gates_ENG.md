
Chapter 5: Definition-Split and Gates

*Date:** 2025-12-20
**Version:** v3.3 (Updated: 2025-12-28)
**Purpose:** Understanding the Definition-Split concept and implementation of the Gate Unified System

**Latest Update (v3.3 - 2025-12-28):**

- Option 1 patch proposal: Stage 5_PreBallast critical application (AGI rule)
- Current_* vs Draft_* unification (QA table SSOT standardization)
- Gate-B critical stage definition clarification

**Latest Update (v3.2 - 2025-12-27):**

- AGENTS.md SSOT integration (Gate definitions, Draft vs Freeboard vs UKC distinction)
- Gate definition clarification (Gate-A: AFT_MIN_2p70, Gate-B: FWD_MAX_2p70_critical_only)
- Draft vs Freeboard vs UKC distinction clarification (tide dependency)

**Latest Update (v3.1 - 2025-12-27):**

- Document version update (maintaining consistency with other documents)

---

## 5.1 Definition-Split Concept Background

### 5.1.1 Problem Situation

In past systems, the following confusion could occur:

1. **Water Level Concept Confusion**

   - No distinction between forecast tide (Forecast Tide) and required water level (Required WL)
   - Unclear which value to use for UKC calculation
2. **Draft, Freeboard, UKC Relationship Confusion**

   - Calculating Draft and Freeboard in relation to tide
   - Misunderstanding UKC and Freeboard as the same concept
3. **Gate Constraint Inconsistency**

   - Checking FWD_MAX and AFT_MIN independently
   - Not enforcing multiple gates simultaneously

### 5.1.2 Definition-Split Solution

According to the **2025-12-16 document**, the following concepts are **clearly separated**:

- **Forecast_Tide_m**: Forecast tide (predicted value, input)
- **Required_WL_for_UKC_m**: Required water level for UKC satisfaction (reverse-calculated value, output)
- **Draft**: Hull draft independent of tide
- **Freeboard**: Deck clearance independent of tide
- **UKC**: Under keel clearance dependent on tide

---

## 5.2 Water Level Related Definitions

### 5.2.1 Forecast_Tide_m (Forecast Tide)

**Definition:**

- Predicted tide height (Chart Datum reference)
- **Predicted value** provided by meteorological agency or tide tables
- Value that changes over time

**Characteristics:**

- **Input value**: Provided by user or from external data source
- **Time dependent**: Forecast value for specific time period
- **Usage**: Used for calculating available depth in UKC calculation

**Example:**

Forecast_Tide_m = 0.30 m (Chart Datum reference)

```

### 5.2.2 Required_WL_for_UKC_m (Required Water Level)

**Definition:**
- **Minimum water level** required to satisfy UKC_MIN requirement
- **Reverse-calculated** value based on current Draft
- Inverse function of UKC calculation

**Calculation formula:**
```

UKC = (DepthRef + WaterLevel) - (Draft_ref + Squat + Safety)

To satisfy UKC_MIN:
  UKC_MIN ≤ (DepthRef + Required_WL) - (Draft_ref + Squat + Safety)

Therefore:
  Required_WL_for_UKC_m = (Draft_ref_max + Squat + Safety + UKC_MIN) - DepthRef

```

**Characteristics:**
- **Output value**: Calculated and provided by system
- **Draft dependent**: Larger current Draft requires larger Required_WL
- **Usage**: Provides information that "if water level is above this, UKC requirement is satisfied"

**Example:**
```

Current Draft_max = 2.70 m
DepthRef = 4.20 m
Squat = 0.0 m
Safety = 0.0 m
UKC_MIN = 0.50 m

Required_WL_for_UKC_m = (2.70 + 0.0 + 0.0 + 0.50) - 4.20 = -1.00 m

→ Negative, so clipped to 0.0 m (already satisfies UKC_MIN)

```

### 5.2.3 Relationship Between Two Concepts

```

┌─────────────────────────────────────────────────────────┐
│  Forecast_Tide_m (Forecast)                             │
│  - Input value                                           │
│  - "Tomorrow 10 AM tide is expected to be 0.30m"        │
│                                                         │
│  ▼ Usage                                                │
│                                                         │
│  UKC calculation:                                       │
│    UKC = (DepthRef + Forecast_Tide) - (Draft + ...)    │
│                                                         │
│  ▼ Reverse calculation                                  │
│                                                         │
│  Required_WL_for_UKC_m (Required value)                 │
│  - Output value                                          │
│  - "To satisfy UKC_MIN with this Draft, minimum 0.50m required" │
└─────────────────────────────────────────────────────────┘

```

**Important:** Clearly distinguish the two values to avoid confusion.

---

## 5.3 Draft, Freeboard, UKC Definitions

### 5.3.1 Draft (Draft) - Tide Independent

**Definition:**
- Depth of hull submerged in water (from Keel to Waterline)
- **Tide independent**: Draft itself is independent of tide changes

**Calculation:**
```

Draft = Physical submerged depth of hull

```

**Characteristics:**
- Changes with Ballast weight changes
- Draft does not change when tide rises (fixed value relative to hull)
- However, when tide rises, Waterline rises, so **absolute Draft measurement** may appear different depending on tide, but **hull-referenced Draft** is constant

**Important**: Draft is **tide independent**. Tide only affects UKC and does not affect Freeboard.

### 5.3.2 Freeboard (Deck Clearance) - Tide Independent

**Definition:**
- Height from Waterline to Deck
- **Tide independent**: Complementary concept to Draft

**Calculation formula:**
```

Freeboard = D_vessel_m - Draft

```

**Specific:**
```

Freeboard_FWD = D_vessel_m - Draft_FWD
Freeboard_AFT = D_vessel_m - Draft_AFT
Freeboard_Min = min(Freeboard_FWD, Freeboard_AFT)
Freeboard_Min_BowStern_m = Freeboard_Min_m  # Explicit label (distinguished from linkspan freeboard)

```

**Characteristics:**
- Freeboard decreases as Draft increases
- **Tide independent** (hull-fixed value)
- Clearance height to prevent green water (deck flooding)

**Important**: Freeboard is **tide independent**. Tide only affects UKC and does not affect Freeboard. Do not claim that "Tide solves Freeboard."

**Example:**
```

D_vessel_m = 3.65 m (Molded Depth)
Draft_FWD = 2.50 m
Draft_AFT = 2.70 m

Freeboard_FWD = 3.65 - 2.50 = 1.15 m
Freeboard_AFT = 3.65 - 2.70 = 0.95 m
Freeboard_Min = 0.95 m

```

### 5.3.3 UKC (Under Keel Clearance) - Tide Dependent

**Definition:**
- Clearance from sea bed to Keel
- **Tide dependent**: UKC increases when tide rises

**Calculation formula:**
```

UKC = Available_Depth - (Draft_ref + Squat + Safety)

Available_Depth = Charted_Depth + Water_Level
Water_Level = Forecast_Tide_m (forecast tide)

```

**Specific:**
```

UKC_FWD = (DepthRef + Forecast_Tide) - (Draft_FWD + Squat + Safety)
UKC_AFT = (DepthRef + Forecast_Tide) - (Draft_AFT + Squat + Safety)
UKC_Min = min(UKC_FWD, UKC_AFT)

```

**Characteristics:**
- UKC increases when tide rises (more clearance)
- UKC decreases when tide falls (increased contact risk)
- Safety clearance to prevent sea bed contact

**Important**: UKC is **tide dependent**. Tide only affects UKC and does not affect Freeboard.

**Example:**
```

DepthRef = 4.20 m (Charted Depth)
Forecast_Tide = 0.30 m
Draft_FWD = 2.50 m
Draft_AFT = 2.70 m
Squat = 0.0 m
Safety = 0.0 m

Available_Depth = 4.20 + 0.30 = 4.50 m

UKC_FWD = 4.50 - (2.50 + 0.0 + 0.0) = 2.00 m
UKC_AFT = 4.50 - (2.70 + 0.0 + 0.0) = 1.80 m
UKC_Min = 1.80 m

```

### 5.3.4 Summary of Three Concepts

```

┌─────────────────────────────────────────────────────────┐
│  Draft (Tide Independent)                                │
│  - Hull submerged depth                                  │
│  - Changes with Ballast                                  │
│                                                         │
│  Freeboard (Tide Independent)                            │
│  = D_vessel - Draft                                     │
│  - Deck clearance height                                │
│                                                         │
│  ─────────────────────────────────────────────────────  │
│                                                         │
│  UKC (Tide Dependent)                                    │
│  = (DepthRef + Forecast_Tide) - (Draft + Squat + Safety)│
│  - Under keel clearance                                 │
│  - Increases when tide rises                            │
└─────────────────────────────────────────────────────────┘

```

**Key point:** Draft and Freeboard are tide independent, but UKC is tide dependent.

---

## 5.4 Gate Unified System

### 5.4.1 Gate Concept

**Gate** is an **operational constraint** that represents minimum/maximum values to ensure safe vessel operation.

### 5.4.2 FWD_MAX Gate (Gate-B: Mammoet / Critical RoRo only)

**Purpose:**
- Ramp height limitation in Critical RoRo stages
- Mammoet's operational constraint (Chart Datum reference)

**Constraint:**
```

Draft_FWD ≤ FWD_MAX_m (Chart Datum referenced)

```

**Default:** `MAMMOET_FWD_MAX_DRAFT_M_CD = 2.70 m` (Chart Datum reference)

**Gate-B definition (SSOT - AGENTS.md standard)**:
- `GATE_B_LABEL = "FWD_MAX_2p70_critical_only"`: Gate-B label (prevents ambiguous "2.70m")
- **Definition**: FWD draft (Chart Datum) ≤ 2.70m, **Critical RoRo stages only**

**Critical Stage definition (AGI rule):**
- `DEFAULT_CRITICAL_STAGE_REGEX = r"(preballast.*critical|6a.*critical|stage\s*5.*preballast|stage\s*6a)"`
- **AGI rule**: `Stage 5_PreBallast` is **always considered critical** (Option 1 patch proposal)
- **Current implementation**: Regex-based matching (explicit check addition recommended with Option 1 patch)

**Option 1 patch proposal:**
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

- **Application scope**: Critical stages only (`Gate_B_Applies=True`)
- **Critical Stage definition**: `DEFAULT_CRITICAL_STAGE_REGEX = r"(preballast.*critical|6a.*critical|stage\s*5.*preballast|stage\s*6a)"`
- **Non-critical stages**: `Gate_FWD_MAX_2p70_critical_only = "N/A"` (prevents false failures)

**Implementation (LP Solver):**

```python
# Limit Mode
if fwd_max is not None:
    row = np.zeros(len(var_names), dtype=float)
    row[:2*n] = coef_dfwd  # Draft_FWD change coefficient
    row[var_names.index("viol_fwd")] = -1.0
    A_ub.append(row)
    b_ub.append(float(fwd_max - dfwd0))
```

**Gate-B Margin Calculation (SSOT):**

**Formula:**
```
GateB_FWD_MAX_2p70_CD_Margin_m = 2.70 - Draft_FWD_m_CD
```

**Where:**
- `Draft_FWD_m_CD` = `Draft_FWD_m - Forecast_Tide_m` (Chart Datum reference)
- Positive margin: FWD draft within limit
- Negative margin: FWD draft exceeds 2.70m (Gate-B violation)

**Example (Stage 5_PreBallast):**
- `Draft_FWD_m` = 2.19 m (MSL reference)
- `Forecast_Tide_m` = 2.0 m
- `Draft_FWD_m_CD` = 2.19 - 2.0 = 0.19 m (Chart Datum reference)
- `GateB_FWD_MAX_2p70_CD_Margin_m` = 2.70 - 0.19 = 2.51 m ✓

**⚠️ Important:** Always check `Draft_FWD_m_CD` (not `Draft_FWD_m`) when interpreting Gate-B margins. Reports must clearly distinguish MSL vs CD references to prevent confusion (e.g., "FWD 3.42 m (MSL) → 1.42 m (CD), Gate-B PASS (+1.28 m margin)").

### 5.4.3 AFT_MIN Gate (Gate-A: Captain / Propulsion)

**Purpose:**

- Ensure propeller efficiency/thrust in emergencies
- Captain's safe navigation requirement

**Constraint:**

```
Draft_AFT ≥ AFT_MIN_m
```

**Default:** `CAPTAIN_AFT_MIN_DRAFT_M = 2.70 m` (Captain requirement reference)

**Gate-A definition (SSOT - AGENTS.md standard)**:

- `GATE_A_LABEL = "AFT_MIN_2p70"`: Gate-A label (prevents ambiguous "2.70m")
- **Definition**: AFT draft ≥ 2.70m (ensure propeller efficiency/thrust in emergencies)
- **Application scope**: All stages (universal gate)
- **ITTC reference**: Approval documents should report **shaft centreline immersion** (based on propeller diameter)
  - Minimum: 1.5D, Recommended: 2.0D (D = propeller diameter)
  - Calculation: `immersion_shaftCL = draft_at_prop - z_shaftCL`

**Implementation (LP Solver):**

```python
# Limit Mode (converting ≥ to ≤)
if aft_min is not None:
    row = np.zeros(len(var_names), dtype=float)
    row[:2*n] = -coef_daft  # Negative (inequality inversion)
    row[var_names.index("viol_aft")] = -1.0
    A_ub.append(row)
    b_ub.append(float(-(aft_min - daft0)))
```

### 5.4.4 Freeboard Gate (Tide Independent)

**Purpose:**

- Prevent green water (deck flooding)
- Ensure deck clearance

**Constraint:**

```
Freeboard ≥ FB_MIN
D_vessel - Draft ≥ FB_MIN
Draft ≤ D_vessel - FB_MIN
```

**Default:** `FB_MIN = 0.0 m` (prevents negative, effectively Freeboard ≥ 0)

**Important**: Freeboard is **tide independent**. Tide only affects UKC and does not affect Freeboard. Do not claim that "Tide solves Freeboard."

**⚠️ SSOT Gap - Operational Minimum Freeboard:**

- **Current Implementation:** Geometric definition only (`Freeboard = D_vessel - Draft`)
- **Gate Check:** Only prevents negative freeboard (`Freeboard_Min_m >= -tol_m`)
- **Missing:** Operational minimum freeboard requirement not defined in SSOT (AGENTS.md)
- **Default `freeboard_min_m = 0.0`:** No operational buffer (only prevents deck wet)
- **Recommendation:** Define operational minimum freeboard in SSOT (e.g., 0.20m, 0.50m for operations)
- **Documentation Requirement:** When `freeboard = 0.00m`, explicitly state whether this is acceptable or requires mitigation

**Implementation (LP Solver):**

```python
if d_vessel is not None and fb_min is not None:
    draft_max = float(d_vessel - fb_min)

    # FWD constraint
    row = np.zeros(len(var_names), dtype=float)
    row[:2*n] = coef_dfwd
    row[var_names.index("viol_fb")] = -1.0
    A_ub.append(row)
    b_ub.append(float(draft_max - dfwd0))

    # AFT constraint
    row = np.zeros(len(var_names), dtype=float)
    row[:2*n] = coef_daft
    row[var_names.index("viol_fb")] = -1.0
    A_ub.append(row)
    b_ub.append(float(draft_max - daft0))
```

### 5.4.5 UKC Gate (Tide Dependent)

**Purpose:**

- Prevent sea bed contact
- Ensure sufficient under keel clearance

**Constraint:**

```
UKC ≥ UKC_MIN
(DepthRef + Forecast_Tide) - (Draft_ref + Squat + Safety) ≥ UKC_MIN
Draft_ref ≤ (DepthRef + Forecast_Tide) - (Squat + Safety + UKC_MIN)
```

**Default:** `UKC_MIN = 0.50 m` (project default, Port/Vessel requirements should be verified)

**Important**: UKC is **tide dependent**. Tide only affects UKC and does not affect Freeboard.

**Draft_ref selection:**

- `UKC_Ref = "FWD"`: FWD Draft reference
- `UKC_Ref = "AFT"`: AFT Draft reference
- `UKC_Ref = "MEAN"`: Mean Draft reference
- `UKC_Ref = "MAX"` (default): Constraint applied to both FWD and AFT (stricter)

**Implementation (LP Solver):**

```python
if ukc_min is not None and depth_ref is not None and forecast_tide is not None:
    draft_max = float(
        depth_ref + forecast_tide - squat - safety_allow - ukc_min
    )

    ref = (ukc_ref or "MAX").upper().strip()

    if ref == "FWD":
        add_ukc_row(coef_dfwd, dfwd0)
    elif ref == "AFT":
        add_ukc_row(coef_daft, daft0)
    elif ref == "MEAN":
        coef_mean = 0.5 * (coef_dfwd + coef_daft)
        add_ukc_row(coef_mean, 0.5 * (dfwd0 + daft0))
    else:  # MAX
        add_ukc_row(coef_dfwd, dfwd0)
        add_ukc_row(coef_daft, daft0)
```

### 5.4.6 Meaning of Gate Unified System

**Unified**: All gates are **enforced simultaneously**.

- Past: Each gate checked independently
- Current: LP Solver finds a solution that **satisfies all gates simultaneously**

**Advantages:**

- Early detection of conflicting gate requirements
- Optimal solution satisfies all gates simultaneously
- Violation values can measure violation degree for each gate

### 5.4.7 2.70m Split Gates (v2.1+)

From pipeline v2.1, `gate_fail_report.md` reports 2.70m gates split into two:

#### Gate-A (Captain): AFT_MIN_2p70 (SSOT - AGENTS.md standard)

**Purpose:**

- Ensure propeller efficiency/thrust in emergencies
- Captain's safe navigation requirement

**Definition:**

```
GateA_AFT_MIN_2p70: AFT draft ≥ 2.70 m
```

**SSOT definition (AGENTS.md standard)**:

- `CAPTAIN_AFT_MIN_DRAFT_M = 2.70`: Captain AFT minimum Draft (m)
- `GATE_A_LABEL = "AFT_MIN_2p70"`: Gate-A label (prevents ambiguous "2.70m")
- **Definition**: AFT draft ≥ 2.70m (ensure propeller efficiency/thrust in emergencies)
- **Application scope**: Applied to all stages (universal gate)
- **ITTC reference**: Approval documents should report **shaft centreline immersion** (based on propeller diameter)
  - Minimum: 1.5D, Recommended: 2.0D (D = propeller diameter)
  - Calculation: `immersion_shaftCL = draft_at_prop - z_shaftCL`

**Implementation:**

```python
df["GateA_AFT_MIN_2p70_PASS"] = df["new_aft_m"] >= 2.70
df["GateA_AFT_MIN_2p70_Margin_m"] = (df["new_aft_m"] - 2.70).round(2)
```

#### Gate-B (Mammoet): FWD_MAX_2p70_CD (SSOT - AGENTS.md standard)

**Purpose:**

- Ramp height limitation in Critical RoRo stages
- Mammoet's operational constraint (Chart Datum reference)

**Definition:**

```
GateB_FWD_MAX_2p70_CD: FWD draft ≤ 2.70 m (Chart Datum referenced)
```

**SSOT definition (AGENTS.md standard)**:

- `MAMMOET_FWD_MAX_DRAFT_M_CD = 2.70`: Mammoet FWD maximum Draft (Chart Datum reference, m)
- `GATE_B_LABEL = "FWD_MAX_2p70_critical_only"`: Gate-B label (prevents ambiguous "2.70m")
- **Definition**: FWD draft (Chart Datum) ≤ 2.70m, **Critical RoRo stages only**
- **Application scope**: Critical stages only (`Gate_B_Applies=True`)
- **Critical Stage definition**: `DEFAULT_CRITICAL_STAGE_REGEX = r"(preballast.*critical|6a.*critical|stage\s*5.*preballast|stage\s*6a)"`
- **Non-critical stages**: `Gate_FWD_MAX_2p70_critical_only = "N/A"` (prevents false failures)

**Implementation:**

```python
# Critical stage determination
df["GateB_FWD_MAX_2p70_CD_applicable"] = df["Stage"].apply(
    lambda s: bool(re.search(DEFAULT_CRITICAL_STAGE_REGEX,
                              str(s), flags=re.IGNORECASE))
)

# PASS determination (only check if applicable)
mask_app = df["GateB_FWD_MAX_2p70_CD_applicable"] == True
df.loc[mask_app, "GateB_FWD_MAX_2p70_CD_PASS"] = (
    df.loc[mask_app, "new_fwd_m"] <= 2.70
)
# Gate-B Margin calculation (Chart Datum reference)
# Formula: Margin = 2.70 - Draft_FWD_m_CD
# Where: Draft_FWD_m_CD = Draft_FWD_m - Forecast_Tide_m
df["Draft_FWD_m_CD"] = df["new_fwd_m"] - df.get("Forecast_Tide_m", 0.0)
df["GateB_FWD_MAX_2p70_CD_Margin_m"] = (2.70 - df["Draft_FWD_m_CD"]).round(2)
df.loc[~mask_app, "GateB_FWD_MAX_2p70_CD_Margin_m"] = None  # Non-critical is NaN
```

**Meaning of Split Gate:**

- Same 2.70m threshold, but different purpose and application scope
- Gate-A: Captain's safety requirement (all stages)
- Gate-B: Operator's constraint (Critical stages only)
- Separate aggregation in reports to clearly distinguish each stakeholder's requirements

**Gate Labels SSOT (prevents ambiguous "2.70m")**:

- **Never use just "2.70m"**. Always include label:
  - **Gate-A**: `AFT_MIN_2p70` (Captain / Propulsion)
  - **Gate-B**: `FWD_MAX_2p70_critical_only` (Mammoet / Critical RoRo only)

---

## 5.5 Implementation Details

### 5.5.1 Stage QA CSV Generation

**Location:** `integrated_pipeline_defsplit_v2.py` (lines 347-466)

**Function:** `generate_stage_QA_csv`

**Purpose:**

- Explicitly record Definition-Split concept in CSV
- Verify gate compliance for each stage
- Clearly distinguish Forecast_Tide vs Required_WL_for_UKC

**Key calculations:**

1. **Freeboard calculation (tide independent)**

   ```python
   freeboard_fwd = d_vessel_m - dfwd
   freeboard_aft = d_vessel_m - daft
   freeboard_min = min(freeboard_fwd, freeboard_aft)
   ```
2. **UKC calculation (tide dependent)**

   ```python
   if depth_ref_m is not None and forecast_tide_m is not None:
       available_depth = depth_ref_m + forecast_tide_m
       ukc_fwd = available_depth - (dfwd + squat_m + safety_allow_m)
       ukc_aft = available_depth - (daft + squat_m + safety_allow_m)
       ukc_min = min(ukc_fwd, ukc_aft)
   ```
3. **Required_WL_for_UKC_m reverse calculation**

   ```python
   if ukc_min_m is not None:
       draft_ref_max = max(dfwd, daft)
       required_wl_for_ukc = (
           draft_ref_max + squat_m + safety_allow_m + ukc_min_m
       ) - depth_ref_m
       required_wl_for_ukc = max(required_wl_for_ukc, 0.0)  # Prevent negative
   ```
4. **Gate verification**

   ```python
   gate_fwd_ok = dfwd <= fwd_max_m
   gate_aft_ok = daft >= aft_min_m
   gate_freeboard_ok = freeboard_min >= 0.0
   gate_ukc_ok = ukc_min >= ukc_min_m  # (if provided)
   ```

### 5.5.2 Helper Functions

**Location:** `ballast_gate_solver_v4.py` (lines 264-302)

#### `pick_draft_ref_for_ukc`

Select Draft reference value for UKC calculation:

```python
def pick_draft_ref_for_ukc(ref: str, dfwd: float, daft: float) -> float:
    r = (ref or "MAX").upper().strip()
    if r == "FWD":
        return float(dfwd)
    if r == "AFT":
        return float(daft)
    if r == "MEAN":
        return float(0.5 * (dfwd + daft))
    return float(max(dfwd, daft))  # MAX (default)
```

#### `ukc_value`

Calculate UKC value:

```python
def ukc_value(
    depth_ref_m: Optional[float],
    wl_forecast_m: Optional[float],
    draft_ref_m: Optional[float],
    squat_m: float,
    safety_allow_m: float,
) -> float:
    if depth_ref_m is None or wl_forecast_m is None or draft_ref_m is None:
        return float("nan")
    return float(
        depth_ref_m + wl_forecast_m - draft_ref_m - squat_m - safety_allow_m
    )
```

#### `required_wl_for_ukc`

Reverse calculate required water level to satisfy UKC_MIN:

```python
def required_wl_for_ukc(
    depth_ref_m: Optional[float],
    ukc_min_m: Optional[float],
    draft_ref_m: Optional[float],
    squat_m: float,
    safety_allow_m: float,
) -> float:
    if depth_ref_m is None or ukc_min_m is None or draft_ref_m is None:
        return float("nan")
    return float(
        ukc_min_m + draft_ref_m + squat_m + safety_allow_m - depth_ref_m
    )
```

#### `freeboard_min`

Calculate minimum Freeboard:

```python
def freeboard_min(d_vessel_m: Optional[float], dfwd: float, daft: float) -> float:
    if d_vessel_m is None:
        return float("nan")
    return float(min(d_vessel_m - dfwd, d_vessel_m - daft))
```

### 5.5.3 Gate Implementation in LP Solver

**Location:** `ballast_gate_solver_v4.py` (lines 479-546)

**Limit Mode constraint formulation:**

1. FWD_MAX: `coef_dfwd^T · x - viol_fwd ≤ FWD_MAX - Dfwd0`
2. AFT_MIN: `-coef_daft^T · x - viol_aft ≤ -AFT_MIN + Daft0`
3. Freeboard: `coef_dfwd^T · x - viol_fb ≤ (D_vessel - FB_MIN) - Dfwd0` (FWD, AFT each)
4. UKC: `coef_draft_ref^T · x - viol_ukc ≤ draft_max - Draft0` (depending on UKC_Ref)

**See Chapter 4 for details.**

---

## 5.6 QA CSV Output Format

### 5.6.1 Column Structure

**Definition-Split columns:**

| Column                    | Type  | Description                                                    |
| ------------------------- | ----- | -------------------------------------------------------------- |
| `Forecast_Tide_m`       | float | Forecast tide (input value)                                    |
| `Required_WL_for_UKC_m` | float | Required water level for UKC satisfaction (reverse-calculated) |
| `Freeboard_FWD_m`       | float | FWD Freeboard (tide independent)                               |
| `Freeboard_AFT_m`       | float | AFT Freeboard (tide independent)                               |
| `Freeboard_Min_m`       | float | Minimum Freeboard                                              |
| `UKC_FWD_m`             | float | FWD UKC (tide dependent)                                       |
| `UKC_AFT_m`             | float | AFT UKC (tide dependent)                                       |
| `UKC_Min_m`             | float | Minimum UKC                                                    |

**Gate verification columns:**

| Column            | Type  | Description                         | Option 1 Change                         |
| ----------------- | ----- | ----------------------------------- | --------------------------------------- |
| `Current_FWD_m` | float | Current Forward Draft (input value) | ⚠️ Remove or unify to `Draft_FWD_m` |
| `Current_AFT_m` | float | Current AFT Draft (input value)     | ⚠️ Remove or unify to `Draft_AFT_m` |
| `Draft_FWD_m`   | float | Forward Draft (Solver result)       | ✅ SSOT (Gate determination standard)   |
| `Draft_AFT_m`   | float | AFT Draft (Solver result)           | ✅ SSOT (Gate determination standard)   |

**Option 1 patch proposal: Current_* vs Draft_* unification**

**Problem:**

- SSOT reliability risk due to mismatch between `Current_*` and `Draft_*` values
- Ambiguity about which value to use for Gate determination

**Solution (Option 1):**

- Remove `Current_*` columns or unify to `Draft_*`
- Gate determination always unified to `Draft_*` (Solver result) standard

**Gate verification columns (existing):**

| Column                               | Type   | Values              | Description                                  |
| ------------------------------------ | ------ | ------------------- | -------------------------------------------- |
| `Gate_FWD_Max`                     | string | "OK" / "NG"         | FWD ≤ FWD_MAX                               |
| `Gate_AFT_Min`                     | string | "OK" / "NG"         | AFT ≥ AFT_MIN                               |
| `Gate_Freeboard`                   | string | "OK" / "NG"         | Freeboard ≥ 0                               |
| `Gate_UKC`                         | string | "OK" / "NG" / "N/A" | UKC ≥ UKC_MIN (only if provided)            |
| `GateA_AFT_MIN_2p70_PASS`          | bool   | True / False        | AFT ≥ 2.70m (Captain, all stages)           |
| `GateB_FWD_MAX_2p70_CD_PASS`       | bool   | True / False        | FWD ≤ 2.70m (Mammoet, Critical stages only) |
| `GateB_FWD_MAX_2p70_CD_applicable` | bool   | True / False        | Gate-B application target flag               |

**Margin columns:**

| Column                             | Type  | Description                                                              |
| ---------------------------------- | ----- | ------------------------------------------------------------------------ |
| `FWD_Margin_m`                   | float | `FWD_MAX_m - Current_FWD_m` (positive if margin exists)                |
| `AFT_Margin_m`                   | float | `Current_AFT_m - AFT_MIN_m` (positive if margin exists)                |
| `UKC_Margin_m`                   | float | `UKC_Min_m - UKC_Min_Required_m` (if provided)                         |
| `GateA_AFT_MIN_2p70_Margin_m`    | float | `Current_AFT_m - 2.70` (positive if margin exists)                     |
| `GateB_FWD_MAX_2p70_CD_Margin_m` | float | `2.70 - Draft_FWD_m_CD` (positive if margin exists, only if applicable). **Note:** Uses Chart Datum (CD) reference: `Draft_FWD_m_CD = Draft_FWD_m - Forecast_Tide_m`. Always check `Draft_FWD_m_CD` (not `Draft_FWD_m`) when interpreting Gate-B margins. |

### 5.6.2 Example Output

```csv
Stage,Current_FWD_m,Current_AFT_m,Forecast_Tide_m,Required_WL_for_UKC_m,Freeboard_FWD_m,Freeboard_AFT_m,Freeboard_Min_m,UKC_FWD_m,UKC_AFT_m,UKC_Min_m,Gate_FWD_Max,Gate_AFT_Min,Gate_Freeboard,Gate_UKC,FWD_Margin_m,AFT_Margin_m
Stage_1,2.50,2.70,0.30,-1.00,1.15,0.95,0.95,2.00,1.80,1.80,OK,OK,OK,OK,0.20,0.00
Stage_6B,2.65,2.75,0.30,-0.85,1.00,0.90,0.90,1.85,1.75,1.75,OK,OK,OK,OK,0.05,-0.05
```

**Stage_6B analysis:**

- `AFT_Margin_m = -0.05`: AFT_MIN gate violation (NG)
- Displayed as `Gate_AFT_Min = "NG"`
- `Required_WL_for_UKC_m = -0.85`: Negative, so clipped to 0.0 (already satisfies UKC_MIN)

**Gate-B Margin Calculation Example (Stage 2):**

- `Draft_FWD_m` = 3.42 m (MSL reference)
- `Forecast_Tide_m` = 2.0 m
- `Draft_FWD_m_CD` = 3.42 - 2.0 = 1.42 m (Chart Datum reference)
- `GateB_FWD_MAX_2p70_CD_Margin_m` = 2.70 - 1.42 = 1.28 m ✓
- **⚠️ Important:** Always use `Draft_FWD_m_CD` (not `Draft_FWD_m`) for Gate-B margin interpretation. Reports must clearly distinguish MSL vs CD references to prevent confusion.

---

## 5.7 Usage Examples

### 5.7.1 Basic Execution (Gates only)

```bash
python integrated_pipeline_defsplit_v2.py \
  --fwd_max 2.70 \
  --aft_min 2.70
```

- Only FWD_MAX, AFT_MIN gates activated
- Freeboard, UKC not calculated

### 5.7.2 Including UKC Gate

```bash
python integrated_pipeline_defsplit_v2.py \
  --fwd_max 2.70 \
  --aft_min 2.70 \
  --forecast_tide 0.30 \
  --depth_ref 4.20 \
  --ukc_min 0.50 \
  --squat 0.0 \
  --safety_allow 0.0
```

- All gates activated
- UKC calculation and verification performed
- Required_WL_for_UKC_m reverse calculation

### 5.7.3 QA CSV Verification

```python
import pandas as pd

qa_df = pd.read_csv("pipeline_out_.../ssot/pipeline_stage_QA.csv")

# Check stages with gate violations
violations = qa_df[
    (qa_df["Gate_FWD_Max"] == "NG") |
    (qa_df["Gate_AFT_Min"] == "NG") |
    (qa_df["Gate_Freeboard"] == "NG") |
    (qa_df["Gate_UKC"] == "NG")
]

print(violations[["Stage", "Gate_FWD_Max", "Gate_AFT_Min", "Gate_Freeboard", "Gate_UKC"]])
```

---

## 5.8 Next Chapter Guide

- **Chapter 6**: Script Interface and API - Command-line arguments and usage of each script

---

**References:**

- Chapter 1: Pipeline Architecture Overview
- Chapter 2: Data Flow and SSOT
- Chapter 4: LP Solver Logic
- `03_DOCUMENTATION/AGENTS.md`: Coordinate system, Gate definitions, Tank Direction SSOT
- 2025-12-16 document: Definition-Split requirements

**Document Version:** v3.2 (AGENTS.md SSOT integration)
**Last Updated:** 2025-12-27
