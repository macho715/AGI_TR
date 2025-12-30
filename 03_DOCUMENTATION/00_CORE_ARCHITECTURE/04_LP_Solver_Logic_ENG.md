
Chapter 4: LP Solver Logic

*Date:** 2025-12-20
**Version:** v3.3 (Updated: 2025-12-28)
**Purpose:** Understanding the mathematical model and algorithms for Linear Programming-based Ballast optimization

**Latest Update (v3.3 - 2025-12-28):**

- Option 2 implementation: Trim/Freeboard Gate enforcement logic (Option B patch)
  - Added `trim_abs_limit`, `trim_limit_enforced` parameters
  - Added `freeboard_min_m`, `freeboard_min_enforced` parameters
  - Added Trim/Freeboard hard constraints to LP constraints

**Latest Update (v3.2 - 2025-12-27):**

- AGENTS.md SSOT integration (coordinate system conversion, Gate definitions)
- Clarified coordinate system conversion formula (x = 30.151 - Fr)
- Clarified Gate definitions (Gate-A: AFT_MIN_2p70, Gate-B: FWD_MAX_2p70_critical_only)

**Latest Update (v3.1 - 2025-12-27):**

- Document version update (maintaining consistency with other documents)

---

## 4.1 LP Model Overview

### 4.1.1 Problem Definition

The Ballast Gate Solver uses **Linear Programming (LP)** to solve the following problem:

- **Objective**: Establish a Ballast plan that satisfies gate constraints while minimizing cost (weight or time)
- **Decision Variables**: Fill/Discharge amount for each tank
- **Constraints**: FWD_MAX, AFT_MIN, Freeboard, UKC gates
- **Objective Function**: Minimize total weight change or minimize total pumping time

### 4.1.2 Solver Structure

┌─────────────────────────────────────────────────────────┐
│  Input: Initial Drafts, Tanks, Hydro Table, Gates      │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│  Iterative Hydro Refinement Loop (default 2 iterations)│
│  ┌───────────────────────────────────────────────────┐ │
│  │ 1. Hydrostatic Table interpolation (based on current Tmean)│ │
│  │ 2. LP problem formulation                          │ │
│  │    - Decision Variables: p_i, n_i                 │ │
│  │    - Objective Function                           │ │
│  │    - Constraints (Gates)                          │ │
│  │ 3. Execute scipy.optimize.linprog                 │ │
│  │ 4. Calculate new Tmean from results               │ │
│  └──────────────────────┬────────────────────────────┘ │
│                         │                               │
│                         ▼                               │
│              Convergence or iteration limit reached?    │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│  Output: Ballast Plan, Predicted Drafts, Violations   │
└─────────────────────────────────────────────────────────┘

```

---

## 4.2 Decision Variables

### 4.2.1 Variable Definition

For each tank `i`, we define **two non-negative variables**:

- `p_i ≥ 0`: Fill amount for tank `i` (tons)
- `n_i ≥ 0`: Discharge amount for tank `i` (tons)

**Net weight change:**
```

Δw_i = p_i - n_i

```
- `Δw_i > 0`: Fill (weight increase)
- `Δw_i < 0`: Discharge (weight decrease)
- `Δw_i = 0`: No change

### 4.2.2 Variable Bounds

Each tank's `bounds_pos_neg()` method returns:

```python
def bounds_pos_neg(self) -> Tuple[float, float, float, float]:
    # Returns: (p_lo, p_hi, n_lo, n_hi)
    # p_lo, n_lo: always 0.0 (non-negative)
    # p_hi: max_fill = max(0, Max_t - Current_t)
    # n_hi: max_dis = max(0, Current_t - Min_t)
```

**Tank mode-specific limits:**

| Mode                    | p_hi                          | n_hi                          | Description    |
| ----------------------- | ----------------------------- | ----------------------------- | -------------- |
| `FILL_DISCHARGE`      | `max(0, Max_t - Current_t)` | `max(0, Current_t - Min_t)` | Bidirectional  |
| `FILL_ONLY`           | `max(0, Max_t - Current_t)` | `0.0`                       | Fill only      |
| `DISCHARGE_ONLY`      | `0.0`                       | `max(0, Current_t - Min_t)` | Discharge only |
| `BLOCKED` / `FIXED` | `0.0`                       | `0.0`                       | Not available  |
| `use_flag = "N"`      | `0.0`                       | `0.0`                       | Not available  |

### 4.2.3 Variable Array Structure

In the LP problem, variables are arranged as follows:

```python
variables = [
    p_0, n_0,  # Tank 0: Fill, Discharge
    p_1, n_1,  # Tank 1: Fill, Discharge
    ...
    p_{n-1}, n_{n-1},  # Tank n-1
    slack_vars...  # Slack variables (added later)
]
```

Total number of variables: `2 * n_tanks + n_slacks`

---

## 4.3 Draft Prediction Model

### 4.3.1 Hydrostatic Relationship

**Mean draft change (ΔTmean):**

```
ΔTmean = ΣΔw / (TPC × 100)
```

- `TPC` (Tons Per Centimeter): Weight change per 1cm draft change
- `100`: cm → m conversion factor

**Trim change (ΔTrim):**

```
ΔTrim = Σ(Δw × (x - LCF)) / (MTC × 100)
```

- `x`: Tank LCG (relative to Midship, `x_from_mid_m`)
  - `x > 0`: AFT (stern direction)
  - `x < 0`: FWD (bow direction)
- `LCF` (Longitudinal Center of Flotation): Center of buoyancy (relative to Midship, +AFT/-FWD)
- `MTC` (Moment to Change Trim): Moment required for 1cm trim change

**Coordinate system conversion (SSOT - AGENTS.md standard)**:

- Frame → x: `x = 30.151 - Fr` (no reinterpretation)
- LCG (AP reference) → x (Midship reference): `x_from_mid_m = 30.151 - lcg_from_ap_m`

**Forward/Aft Draft change:**

```
ΔDfwd = ΔTmean - 0.5 × ΔTrim
ΔDaft = ΔTmean + 0.5 × ΔTrim
```

**Final Draft:**

```
Dfwd_new = Dfwd0 + ΔDfwd
Daft_new = Daft0 + ΔDaft
```

### 4.3.2 `predict_drafts` Function

**Location:** `ballast_gate_solver_v4.py` (lines 308-342)

**Implementation:**

```python
def predict_drafts(
    dfwd0: float,
    daft0: float,
    hydro: HydroPoint,
    tanks: List[Tank],
    delta: Dict[str, float],
) -> Dict[str, float]:
    total_w = 0.0
    total_m = 0.0
    for t in tanks:
        dw = float(delta.get(t.name, 0.0))
        total_w += dw
        total_m += dw * (t.x_from_mid_m - hydro.lcf_m)

    d_tmean = total_w / (hydro.tpc_t_per_cm * 100.0)
    d_trim = total_m / (hydro.mtc_t_m_per_cm * 100.0)

    dfwd = dfwd0 + d_tmean - 0.5 * d_trim
    daft = daft0 + d_tmean + 0.5 * d_trim

    return {
        "ΔW_t": float(total_w),
        "ΔM_t_m": float(total_m),
        "FWD_new_m": float(dfwd),
        "AFT_new_m": float(daft),
        "Trim_new_m": float(daft - dfwd),
        "Tmean_new_m": float(0.5 * (dfwd + daft)),
    }
```

### 4.3.3 LP Coefficient Matrix Construction

**`build_rows` function:**

```python
def build_rows(hydro: HydroPoint, tanks: List[Tank]) -> Tuple[np.ndarray, np.ndarray]:
    n = len(tanks)
    rowW = np.zeros(2 * n, dtype=float)  # ΣΔw coefficients
    rowM = np.zeros(2 * n, dtype=float)  # Σ(Δw × (x-LCF)) coefficients
    for i, t in enumerate(tanks):
        arm = t.x_from_mid_m - hydro.lcf_m
        rowW[2 * i] = 1.0      # p_i coefficient (+1)
        rowW[2 * i + 1] = -1.0 # n_i coefficient (-1)
        rowM[2 * i] = arm      # p_i moment coefficient
        rowM[2 * i + 1] = -arm # n_i moment coefficient
    return rowW, rowM
```

**Draft change coefficients:**

```python
coef_tmean = rowW / (hydro.tpc_t_per_cm * 100.0)
coef_trim = rowM / (hydro.mtc_t_m_per_cm * 100.0)
coef_dfwd = coef_tmean - 0.5 * coef_trim
coef_daft = coef_tmean + 0.5 * coef_trim
```

---

## 4.4 Objective Function

### 4.4.1 Objective Function Selection

Two modes are supported:

1. **Weight Minimization** (`prefer_time=False`)

   ```python
   c_i = priority_weight_i
   ```

   - Objective: Minimize total weight change
   - Prefer tanks with lower priority
2. **Time Minimization** (`prefer_time=True`)

   ```python
   c_i = priority_weight_i / pump_rate_tph_i
   ```

   - Objective: Minimize total pumping time
   - Prefer tanks with faster pump rates

### 4.4.2 Objective Function Construction

```python
c = []  # Objective function coefficients
for t in tanks:
    w = t.priority_weight
    if prefer_time:
        c += [w / t.pump_rate_tph, w / t.pump_rate_tph]  # [p_i, n_i]
    else:
        c += [w, w]  # [p_i, n_i]

# Add penalty for slack variables
if mode == "limit":
    c += [violation_penalty] * 4  # viol_fwd, viol_aft, viol_fb, viol_ukc
else:  # target mode
    c += [slack_weight_penalty, slack_weight_penalty,
          slack_moment_penalty, slack_moment_penalty]  # slackW_pos, slackW_neg, slackM_pos, slackM_neg
```

**Minimization problem:**

```
minimize: c^T · x
```

---

## 4.5 Constraints

### 4.5.1 Limit Mode Constraints

**Limit Mode** uses **inequality constraints** (`A_ub · x ≤ b_ub`).

#### 1) FWD_MAX Gate (Gate-B: Mammoet / Critical RoRo only)

**Constraint:**

```
Dfwd_new ≤ FWD_MAX
```

**LP format:**

```
Dfwd0 + coef_dfwd^T · x ≤ FWD_MAX
coef_dfwd^T · x ≤ FWD_MAX - Dfwd0
```

**With slack variable (Soft Constraint):**

```
coef_dfwd^T · x - viol_fwd ≤ FWD_MAX - Dfwd0
viol_fwd ≥ 0
```

**Implementation:**

```python
row = np.zeros(len(var_names), dtype=float)
row[:2*n] = coef_dfwd  # Tank variables
row[var_names.index("viol_fwd")] = -1.0
A_ub.append(row)
b_ub.append(float(fwd_max - dfwd0))
```

**Gate-B definition (SSOT - AGENTS.md standard)**:

- `MAMMOET_FWD_MAX_DRAFT_M_CD = 2.70`: Mammoet FWD maximum Draft (Chart Datum reference, m)
- `GATE_B_LABEL = "FWD_MAX_2p70_critical_only"`: Gate-B label (prevents ambiguous "2.70m")
- **Definition**: FWD draft (Chart Datum) ≤ 2.70m, **Critical RoRo stages only**
- **Application scope**: Critical stages only (`Gate_B_Applies=True`)
- **Critical Stage definition**: `DEFAULT_CRITICAL_STAGE_REGEX = r"(preballast.*critical|6a.*critical|stage\s*5.*preballast|stage\s*6a)"`
- **Non-critical stages**: `Gate_FWD_MAX_2p70_critical_only = "N/A"` (prevents false failures)

#### 2) AFT_MIN Gate (Gate-A: Captain / Propulsion)

**Constraint:**

```
Daft_new ≥ AFT_MIN
```

**LP format (converting ≥ to ≤):**

```
-Daft_new ≤ -AFT_MIN
-Daft0 - coef_daft^T · x ≤ -AFT_MIN
-coef_daft^T · x ≤ -AFT_MIN + Daft0
```

**With slack variable:**

```
-coef_daft^T · x - viol_aft ≤ -AFT_MIN + Daft0
viol_aft ≥ 0
```

**Implementation:**

```python
row = np.zeros(len(var_names), dtype=float)
row[:2*n] = -coef_daft  # Negative coefficient
row[var_names.index("viol_aft")] = -1.0
A_ub.append(row)
b_ub.append(float(-(aft_min - daft0)))
```

**Gate-A definition (SSOT - AGENTS.md standard)**:

- `CAPTAIN_AFT_MIN_DRAFT_M = 2.70`: Captain AFT minimum Draft (m)
- `GATE_A_LABEL = "AFT_MIN_2p70"`: Gate-A label (prevents ambiguous "2.70m")
- **Definition**: AFT draft ≥ 2.70m (ensures propeller efficiency/thrust in emergencies)
- **Application scope**: All stages (universal gate)
- **ITTC reference**: Approval documents should report **shaft centreline immersion** (based on propeller diameter)

#### 3) Freeboard Gate

**Constraint:**

```
Freeboard ≥ FB_MIN
D_vessel - Draft ≥ FB_MIN
Draft ≤ D_vessel - FB_MIN
```

**LP format (applied to both FWD and AFT):**

```
Dfwd_new ≤ D_vessel - FB_MIN
Daft_new ≤ D_vessel - FB_MIN
```

**Implementation:**

```python
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

#### 5) Trim Gate (Option B - Hard Constraint)

**Constraint:**

```
|Trim_new| ≤ Trim_Abs_Limit
```

**LP format:**

```
Trim_new = Draft_AFT_new - Draft_FWD_new
-Trim_Abs_Limit ≤ Trim_new ≤ Trim_Abs_Limit
```

**Implementation:**

```python
if trim_limit_enforced and trim_abs_limit is not None:
    # Trim = AFT - FWD
    # coef_trim = coef_daft - coef_dfwd
    coef_trim = coef_daft - coef_dfwd

    # Upper bound: Trim ≤ Trim_Abs_Limit
    row = np.zeros(len(var_names), dtype=float)
    row[:2*n] = coef_trim
    A_ub.append(row)
    b_ub.append(float(trim_abs_limit - (daft0 - dfwd0)))

    # Lower bound: -Trim ≤ Trim_Abs_Limit (→ Trim ≥ -Trim_Abs_Limit)
    row = np.zeros(len(var_names), dtype=float)
    row[:2*n] = -coef_trim
    A_ub.append(row)
    b_ub.append(float(trim_abs_limit + (daft0 - dfwd0)))
```

#### 6) Freeboard Gate (Option B - Hard Constraint)

**Constraint:**

```
Freeboard_Min ≥ Freeboard_Min_m
```

**Implementation:**

```python
if freeboard_min_enforced and d_vessel is not None and freeboard_min_m is not None:
    draft_max = float(d_vessel - freeboard_min_m)
    # Apply constraint to both FWD and AFT
    # (Same as existing Freeboard Gate but enforced with flag)
```

#### 4) UKC Gate

**Constraint:**

```
UKC ≥ UKC_MIN
(DepthRef + Forecast_Tide) - (Draft_ref + Squat + Safety) ≥ UKC_MIN
Draft_ref ≤ DepthRef + Forecast_Tide - Squat - Safety - UKC_MIN
```

**Draft_ref selection:**

- `UKC_Ref = "FWD"`: Use FWD Draft
- `UKC_Ref = "AFT"`: Use AFT Draft
- `UKC_Ref = "MEAN"`: Use mean Draft
- `UKC_Ref = "MAX"` (default): Apply constraint to both FWD and AFT (stricter)

**Implementation:**

```python
draft_max = float(
    depth_ref + forecast_tide - squat - safety_allow - ukc_min
)

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

### 4.5.2 Target Mode Constraints

**Target Mode** uses **equality constraints** (`A_eq · x = b_eq`).

**Objective:**

- `Dfwd_new = Target_FWD`
- `Daft_new = Target_AFT`

**Equality conversion:**

```
Target_Tmean = 0.5 × (Target_FWD + Target_AFT)
Target_Trim = Target_AFT - Target_FWD

ΔTmean = Target_Tmean - Initial_Tmean
ΔTrim = Target_Trim - Initial_Trim

Required_ΔW = ΔTmean × TPC × 100
Required_ΔM = ΔTrim × MTC × 100
```

**Equality constraints (with slack):**

```
ΣΔw + slackW_pos - slackW_neg = Required_ΔW
Σ(Δw × (x-LCF)) + slackM_pos - slackM_neg = Required_ΔM
```

**Implementation:**

```python
eqW = np.zeros(len(var_names), dtype=float)
eqW[:2*n] = rowW  # ΣΔw coefficients
eqW[var_names.index("slackW_pos")] = 1.0
eqW[var_names.index("slackW_neg")] = -1.0

eqM = np.zeros(len(var_names), dtype=float)
eqM[:2*n] = rowM  # Σ(Δw × (x-LCF)) coefficients
eqM[var_names.index("slackM_pos")] = 1.0
eqM[var_names.index("slackM_neg")] = -1.0

A_eq = [eqW, eqM]
b_eq = [reqW, reqM]
```

---

## 4.6 Iterative Hydrostatic Table Interpolation

### 4.6.1 Need for Iteration

The `TPC`, `MTC`, and `LCF` values in the Hydrostatic Table vary with **current Draft (Tmean)**. However, the LP result calculated from the initial Draft predicts a new Draft, so re-interpolating with this value improves accuracy.

### 4.6.2 Iteration Algorithm

```python
tmean = 0.5 * (dfwd0 + daft0)  # Initial Tmean
hydro_used = interp_hydro(hdf, tmean)

for iteration in range(max(1, iterate_hydro)):
    # 1. Interpolate Hydro Point with current Tmean
    hydro_used = interp_hydro(hdf, tmean)

    # 2. Formulate and solve LP problem
    # ... (LP formulation code above)
    res = linprog(...)

    # 3. Calculate new Tmean from results
    delta = extract_delta_from_solution(res.x)
    pred = predict_drafts(dfwd0, daft0, hydro_used, tanks, delta)
    tmean = pred["Tmean_new_m"]  # Update Tmean for next iteration
```

**Default iteration count:** `iterate_hydro = 2` (adjustable via command-line argument)

### 4.6.3 Convergence

Generally, 2-3 iterations are sufficient for convergence. Cases requiring more iterations are rare.

---

## 4.7 scipy.optimize.linprog Call

### 4.7.1 Function Signature

```python
from scipy.optimize import linprog

res = linprog(
    c=c,                    # Objective function coefficients
    A_ub=(np.vstack(A_ub) if A_ub else None),  # Inequality constraints
    b_ub=(np.array(b_ub, dtype=float) if b_ub else None),
    A_eq=(np.vstack(A_eq) if A_eq else None),  # Equality constraints
    b_eq=(np.array(b_eq, dtype=float) if b_eq else None),
    bounds=bounds,          # Variable bounds
    method="highs",         # Solver method (HiGHS interior point)
)
```

### 4.7.2 Solver Method: "highs"

- **HiGHS**: High-performance optimization software
- Based on interior point method
- Efficient for large-scale LP problems
- Open-source, MIT license

### 4.7.3 Result Validation

```python
if not res.success:
    raise RuntimeError(f"LP failed: {res.message}")
```

---

## 4.8 Solution Interpretation

### 4.8.1 Variable Extraction

```python
x = res.x  # Solution vector
delta: Dict[str, float] = {}
plan_rows = []

for i, t in enumerate(tanks):
    p = float(x[2 * i])      # Fill amount
    nvar = float(x[2 * i + 1])  # Discharge amount
    dw = p - nvar            # Net weight change
    pumped = p + nvar        # Total pumped (for time calculation)

    if abs(dw) < 1e-10 and pumped < 1e-10:
        continue  # Skip tanks with no change

    delta[t.name] = dw
    plan_rows.append({
        "Tank": t.name,
        "Action": "Fill" if dw > 0 else "Discharge",
        "Delta_t": round(dw, 2),
        "PumpTime_h": round(pumped / t.pump_rate_tph, 2),
    })
```

### 4.8.2 Violation Extraction (Limit Mode)

```python
if mode == "limit":
    pred["viol_fwd_max_m"] = float(x[var_names.index("viol_fwd")])
    pred["viol_aft_min_m"] = float(x[var_names.index("viol_aft")])
    pred["viol_fb_min_m"] = float(x[var_names.index("viol_fb")])
    pred["viol_ukc_min_m"] = float(x[var_names.index("viol_ukc")])
```

**Violation meaning:**

- `viol_fwd_max_m > 0`: FWD_MAX gate violation (in m)
- `viol_aft_min_m > 0`: AFT_MIN gate violation (in m)
- `viol_fb_min_m > 0`: Freeboard gate violation (in m)
- `viol_ukc_min_m > 0`: UKC gate violation (in m)

**Note:** Even with violations, LP returns a solution (Soft Constraint). Violation values can be used to measure the degree of violation.

### 4.8.3 Final Draft Prediction

```python
pred = predict_drafts(dfwd0, daft0, hydro_used, tanks, delta)
# Returns: {
#     "ΔW_t": total_weight_change,
#     "ΔM_t_m": total_moment_change,
#     "FWD_new_m": predicted_forward_draft,
#     "AFT_new_m": predicted_aft_draft,
#     "Trim_new_m": predicted_trim,
#     "Tmean_new_m": predicted_mean_draft,
# }
```

---

## 4.9 Output Format

### 4.9.1 Ballast Plan CSV

| Column         | Description              | Example     |
| -------------- | ------------------------ | ----------- |
| `Tank`       | Tank identifier          | "FWB2"      |
| `Action`     | "Fill" or "Discharge"    | "Discharge" |
| `Delta_t`    | Net weight change (tons) | -25.50      |
| `PumpTime_h` | Pumping time (hours)     | 0.26        |

**Sorting:** Descending by `PumpTime_h`, then ascending by `Tank`

### 4.9.2 Summary Output

**Limit Mode:**

```python
{
    "FWD_new_m": 2.65,
    "AFT_new_m": 2.72,
    "Trim_new_m": 0.07,
    "Tmean_new_m": 2.685,
    "ΔW_t": -50.0,
    "viol_fwd_max_m": 0.0,    # No violation
    "viol_aft_min_m": 0.02,    # Slight violation (soft constraint)
    "viol_fb_min_m": 0.0,
    "viol_ukc_min_m": 0.0,
}
```

**Target Mode:**

```python
{
    "FWD_new_m": 2.70,  # Target achieved (within slack)
    "AFT_new_m": 2.70,
    "Trim_new_m": 0.00,
    "Tmean_new_m": 2.70,
    "ΔW_t": -45.0,
}
```

---

## 4.10 Mathematical Summary

### 4.10.1 Standard LP Format

**Objective:**

```
minimize: c^T · x
```

**Constraints:**

```
A_eq · x = b_eq        (equality constraints, Target Mode)
A_ub · x ≤ b_ub        (inequality constraints, Limit Mode)
l ≤ x ≤ u              (variable bounds)
```

**Variables:**

```
x = [p_0, n_0, p_1, n_1, ..., p_{n-1}, n_{n-1}, slacks...]^T
```

### 4.10.2 Problem Size

- **Number of variables**: `2 × n_tanks + n_slacks`
  - `n_slacks = 4` (Limit Mode: viol_fwd, viol_aft, viol_fb, viol_ukc)
  - `n_slacks = 4` (Target Mode: slackW_pos, slackW_neg, slackM_pos, slackM_neg)
- **Number of constraints**:
  - Limit Mode: `0 ~ 6` (depending on number of gates)
  - Target Mode: `2` (equality constraints: Weight, Moment)

---

## 4.11 Next Chapter Guide

- **Chapter 5**: Definition-Split and Gates - Conceptual background and implementation details of the gate system
- **Chapter 6**: Script Interface and API - Command-line arguments and usage of the Solver

---

**References:**

- Chapter 1: Pipeline Architecture Overview
- Chapter 2: Data Flow and SSOT
- Chapter 3: Pipeline Execution Flow
- `ballast_gate_solver_v4.py`: LP Solver implementation
- `03_DOCUMENTATION/AGENTS.md`: Coordinate system, Gate definitions, Tank Direction SSOT
- scipy.optimize.linprog documentation: [SciPy Documentation](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.linprog.html)

**Document Version:** v3.2 (AGENTS.md SSOT integration)
**Last Updated:** 2025-12-27

```

This translation maintains:
- Technical terms and code blocks unchanged
- Mathematical formulas and structure
- Code examples and implementations
- Version numbers and dates
- References and cross-references

The document is ready for use in English.
```
