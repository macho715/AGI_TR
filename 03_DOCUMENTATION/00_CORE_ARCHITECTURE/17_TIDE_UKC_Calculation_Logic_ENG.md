Chapter 17: TIDE/UKC Calculation Logic and Fallback Mechanisms

**Date:** 2025-12-28
**Last Modified:** 2025-12-29
**Version:** v1.1
**Purpose:** Mathematical model and implementation details of TIDE/UKC calculation formulas, fallback mechanisms, and validation logic

---

## 17.1 Overview

### 17.1.1 Purpose

This document details the **TIDE/UKC calculation logic** of the `tide_ukc_engine.py` module from mathematical formulas and implementation perspectives. Specifically:

- **Formula definitions**: All TIDE/UKC-related mathematical formulas
- **Fallback mechanisms**: None value handling and default value application logic
- **Validation logic**: Tide margin validation and determination criteria
- **Data conversion**: Input data normalization and conversion process

### 17.1.2 Core Definitions (Chart Datum Reference)

This module strictly separates **Forecast Tide (forecast water level)** and **Required WL (water level required for UKC satisfaction)**:

| Term | Definition | Unit | Reference |
|------|------------|------|-----------|
| **Forecast_tide_m** | Forecast tide (Chart Datum reference) | m | Forecast value (input) |
| **Tide_required_m** | Minimum water level required for UKC requirement satisfaction | m | Calculated value |
| **Tide_margin_m** | Forecast_tide_m - Tide_required_m | m | Calculated value |
| **UKC_fwd_m** | Forward Under Keel Clearance | m | Calculated value |
| **UKC_aft_m** | Aft Under Keel Clearance | m | Calculated value |
| **UKC_min_actual_m** | min(UKC_fwd_m, UKC_aft_m) | m | Calculated value |

---

## 17.2 Core Calculation Formulas

### 17.2.1 Required Tide Calculation

**Formula:**
```
Tide_required_m = max(0, (Draft_ref + Squat + Safety + UKC_min) - DepthRef)
```

**Implementation:**
```python
def required_tide_m(
    depth_ref_m: Optional[float],
    draft_ref_m: Optional[float],
    ukc_min_m: Optional[float],
    squat_m: float = 0.0,
    safety_allow_m: float = 0.0,
    clamp_zero: bool = True,
    fallback_depth: Optional[float] = None,
    fallback_draft: Optional[float] = None,
    fallback_ukc: Optional[float] = None,
) -> float:
    """Return required tide (m, CD) with fallbacks."""
    # Apply fallbacks
    depth = depth_ref_m if depth_ref_m is not None else (fallback_depth or DEFAULT_DEPTH_REF_M)
    draft = draft_ref_m if draft_ref_m is not None else (fallback_draft or 2.00)
    ukc = ukc_min_m if ukc_min_m is not None else (fallback_ukc or DEFAULT_UKC_MIN_M)

    req = float(draft + float(squat_m) + float(safety_allow_m) + float(ukc) - float(depth))
    if clamp_zero:
        return float(max(0.0, req))
    return float(req)
```

**Parameter Description:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `depth_ref_m` | Optional[float] | None | Reference depth (Chart Datum reference, m) |
| `draft_ref_m` | Optional[float] | None | Reference draft (m) |
| `ukc_min_m` | Optional[float] | None | Minimum UKC requirement (m) |
| `squat_m` | float | 0.0 | Squat allowance (m) |
| `safety_allow_m` | float | 0.0 | Safety allowance (m) |
| `clamp_zero` | bool | True | Limit result to 0 or above |

**Fallback Mechanism:**

1. **If depth_ref_m is None:**
   - Use `fallback_depth` (if provided)
   - Otherwise `DEFAULT_DEPTH_REF_M = 5.50` (AGI default)

2. **If draft_ref_m is None:**
   - Use `fallback_draft` (if provided)
   - Otherwise `2.00` (safe default)

3. **If ukc_min_m is None:**
   - Use `fallback_ukc` (if provided)
   - Otherwise `DEFAULT_UKC_MIN_M = 0.50` (safe minimum)

**Mathematical Meaning:**

- **Tide_required_m > 0**: Additional tide needed due to insufficient depth
- **Tide_required_m = 0**: Current depth sufficient (when clamp_zero applied)
- **Tide_required_m < 0**: Depth sufficient, no tide requirement (clamped to 0)

---

### 17.2.2 UKC Calculation (Single Position)

**Formula:**
```
UKC_end = DepthRef + Forecast_tide - Draft_end - Squat - Safety
```

**Implementation:**
```python
def ukc_end_m(
    depth_ref_m: Optional[float],
    forecast_tide_m: Optional[float],
    draft_end_m: Optional[float],
    squat_m: float = 0.0,
    safety_allow_m: float = 0.0,
) -> float:
    """Return UKC at one end (m)."""
    if depth_ref_m is None or forecast_tide_m is None or draft_end_m is None:
        return float("nan")
    return float(float(depth_ref_m) + float(forecast_tide_m) - float(draft_end_m) - float(squat_m) - float(safety_allow_m))
```

**Parameter Description:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `depth_ref_m` | Optional[float] | Reference depth (Chart Datum reference, m) |
| `forecast_tide_m` | Optional[float] | Forecast tide (Chart Datum reference, m) |
| `draft_end_m` | Optional[float] | Forward or aft draft (m) |
| `squat_m` | float | Squat allowance (m) |
| `safety_allow_m` | float | Safety allowance (m) |

**Mathematical Meaning:**

- **UKC_end > 0**: Clearance space exists between vessel bottom and sea bed
- **UKC_end = 0**: Vessel bottom contacts sea bed
- **UKC_end < 0**: Vessel bottom below sea bed (contact risk)

**None Handling:**

- Returns `float("nan")` if any input parameter is None
- Need to prevent NaN propagation in subsequent calculations

---

### 17.2.3 UKC FWD/AFT and Minimum Calculation

**Formula:**
```
UKC_fwd = DepthRef + Forecast_tide - Draft_fwd - Squat - Safety
UKC_aft = DepthRef + Forecast_tide - Draft_aft - Squat - Safety
UKC_min_actual = min(UKC_fwd, UKC_aft)
```

**Implementation:**
```python
def ukc_fwd_aft_min(
    depth_ref_m: Optional[float],
    forecast_tide_m: Optional[float],
    draft_fwd_m: Optional[float],
    draft_aft_m: Optional[float],
    squat_m: float = 0.0,
    safety_allow_m: float = 0.0,
) -> Tuple[float, float, float]:
    """Return (UKC_fwd, UKC_aft, UKC_min_actual)."""
    uf = ukc_end_m(depth_ref_m, forecast_tide_m, draft_fwd_m, squat_m, safety_allow_m)
    ua = ukc_end_m(depth_ref_m, forecast_tide_m, draft_aft_m, squat_m, safety_allow_m)
    try:
        umin = float(min(uf, ua))
    except Exception:
        umin = float("nan")
    return uf, ua, umin
```

**Return Values:**

- `(UKC_fwd_m, UKC_aft_m, UKC_min_actual_m)`: 3-tuple
- All values are `float` (NaN possible)

**Exception Handling:**

- If `ukc_end_m()` returns NaN, `UKC_min_actual` is also NaN
- Returns NaN if `min()` operation fails

---

### 17.2.4 Tide Margin Calculation

**Formula:**
```
Tide_margin_m = Forecast_tide_m - Tide_required_m
```

**Implementation Location:**
- No direct implementation in `tide_ukc_engine.py`
- Calculated in pipeline as `Forecast_tide_m - Tide_required_m`

**Determination Criteria:**

| Condition | Determination | Description |
|-----------|---------------|-------------|
| `Forecast_tide_m` missing | `VERIFY` | Forecast tide not provided |
| `Tide_margin_m < 0` | `FAIL` | Forecast tide < required tide |
| `0 ≤ Tide_margin_m < tolerance` | `LIMIT` | Insufficient margin (default tolerance = 0.10m) |
| `Tide_margin_m ≥ tolerance` | `OK` | Sufficient margin |

---

## 17.3 Validation Logic

### 17.3.1 Tide Validation Function

**Implementation:**
```python
def verify_tide(
    tide_required_m_val: float,
    forecast_tide_m_val: Optional[float],
    tolerance_m: float = DEFAULT_TIDE_TOL_M,
) -> Tuple[str, str]:
    """
    Return (status, note)
    - VERIFY: forecast missing (no official tide table / forecast not provided)
    - FAIL  : margin < 0
    - LIMIT : 0 <= margin < tolerance
    - OK    : margin >= tolerance
    """
    ft = _to_float(forecast_tide_m_val, fallback=None, warn=False)
    if ft is None or (isinstance(ft, float) and np.isnan(ft)):
        return "VERIFY", "Forecast tide not provided"
    try:
        req = float(tide_required_m_val)
    except Exception:
        return "VERIFY", "Tide_required_m invalid"

    margin = float(ft - req)
    if margin < 0.0:
        return "FAIL", f"Forecast {ft:.2f}m < required {req:.2f}m"
    if margin < float(tolerance_m):
        return "LIMIT", f"Margin {margin:.2f}m < tol {float(tolerance_m):.2f}m"
    return "OK", f"Margin {margin:.2f}m"
```

**Determination Logic Flow:**

```
┌─────────────────────────────────┐
│ verify_tide()                   │
└──────────────┬──────────────────┘
               │
               ▼
    ┌──────────────────────┐
    │ forecast_tide_m      │
    │ Convertible?          │
    └──────┬───────────────┘
           │
    ┌──────┴──────┐
    │ No          │ Yes
    ▼             ▼
VERIFY      ┌──────────────────────┐
            │ tide_required_m      │
            │ Convertible?           │
            └──────┬───────────────┘
                   │
            ┌──────┴──────┐
            │ No          │ Yes
            ▼             ▼
        VERIFY      ┌──────────────────────┐
                    │ Calculate margin      │
                    │ = ft - req            │
                    └──────┬───────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
        ▼                  ▼                  ▼
    margin < 0    0 ≤ margin < tol    margin ≥ tol
        │                  │                  │
        ▼                  ▼                  ▼
      FAIL              LIMIT                OK
```

**Defaults:**

- `DEFAULT_TIDE_TOL_M = 0.10` (m)
- Can be overridden in Profile JSON

---

## 17.4 Fallback Mechanisms

### 17.4.1 `_to_float()` Function

**Implementation:**
```python
def _to_float(x, fallback: Optional[float] = None, warn: bool = False) -> Optional[float]:
    """
    Convert to float with optional fallback.

    Args:
        x: Value to convert
        fallback: Default value if conversion fails (None = return None)
        warn: Log warning on failure

    Returns:
        float or fallback value
    """
    try:
        if x is None:
            return fallback
        if isinstance(x, str) and x.strip() == "":
            return fallback
        if pd.isna(x):
            return fallback
        return float(x)
    except Exception as e:
        if warn:
            import logging
            logging.debug(f"_to_float conversion failed: {e}, using fallback={fallback}")
        return fallback
```

**Processing Order:**

1. **None check**: `x is None` → return `fallback`
2. **Empty string check**: `x.strip() == ""` → return `fallback`
3. **NaN check**: `pd.isna(x)` → return `fallback`
4. **Type conversion**: Attempt `float(x)`
5. **Exception handling**: Return `fallback` on conversion failure

**Usage Examples:**

```python
# None handling (fallback=0.0)
tide_val = _to_float(None, fallback=0.0)  # → 0.0

# Empty string handling
tide_val = _to_float("", fallback=2.00)  # → 2.00

# NaN handling
tide_val = _to_float(np.nan, fallback=2.00)  # → 2.00

# Normal conversion
tide_val = _to_float("2.50", fallback=0.0)  # → 2.50
```

---

### 17.4.2 `required_tide_m()` Fallback Chain

**Fallback Priority:**

```
depth_ref_m
  ├─ None? → fallback_depth
  │           ├─ None? → DEFAULT_DEPTH_REF_M (5.50)
  │           └─ Has value → Use
  └─ Has value → Use

draft_ref_m
  ├─ None? → fallback_draft
  │           ├─ None? → 2.00 (safe default)
  │           └─ Has value → Use
  └─ Has value → Use

ukc_min_m
  ├─ None? → fallback_ukc
  │           ├─ None? → DEFAULT_UKC_MIN_M (0.50)
  │           └─ Has value → Use
  └─ Has value → Use
```

**Calculation Guarantee:**

- Calculation possible with defaults even if all parameters are None
- No `float("nan")` return (fallback applied)

---

## 17.5 Constant Definitions (SSOT)

### 17.5.1 `tide_constants.py` Module

**Defined Constants:**

```python
# Default values (fallback only)
DEFAULT_TIDE_TOL_M = 0.10  # Tide margin tolerance (m)
DEFAULT_DEPTH_REF_M = 5.50  # AGI default depth reference
DEFAULT_UKC_MIN_M = 0.50  # Minimum UKC requirement
DEFAULT_SQUAT_M = 0.15  # Default squat allowance
DEFAULT_SAFETY_ALLOW_M = 0.20  # Default safety allowance

# Timeout settings
FORMULA_TIMEOUT_SEC = 120  # Excel formula finalization timeout
```

**Profile JSON Integration:**

```python
def load_tide_constants_from_profile(profile_path: Optional[Path] = None) -> Dict[str, Any]:
    """Load tide/UKC constants from profile JSON with fallbacks."""
    if profile_path and profile_path.exists():
        # Attempt to load from Profile
        # Use defaults on failure
    return {
        "tide_tol_m": DEFAULT_TIDE_TOL_M,
        "depth_ref_m": DEFAULT_DEPTH_REF_M,
        # ...
    }
```

**Profile JSON Structure:**

```json
{
  "tide_ukc": {
    "tide_tol_m": 0.10,
    "depth_ref_m": 5.50,
    "ukc_min_m": 0.50,
    "squat_m": 0.15,
    "safety_allow_m": 0.20
  },
  "operational": {
    "formula_timeout_sec": 120
  }
}
```

**Default Value Application Priority:**

```
1. User input (CLI/Profile)
2. Profile JSON value
3. Function parameter fallback_* value
4. tide_constants.py default
5. Hardcoded safe value (2.00, etc.)
```

---

## 17.6 Data Conversion and Interpolation

### 17.6.1 Tide Table Loading

**Supported Formats:**

- CSV/TXT: `pd.read_csv()` (automatic delimiter detection)
- Excel: `pd.read_excel()` (.xlsx, .xls)
- JSON: `pd.read_json()` or `json.loads()` then DataFrame conversion

**Automatic Column Detection:**

1. **Datetime column detection:**
   - Select non-numeric column with 60%+ valid datetime
   - Otherwise try all columns

2. **Tide column detection:**
   - Priority: `tide_m` > `tide` > `tide_height_m` > `height_m` > `wl_m` > ...
   - Otherwise use first numeric column

**Output Format:**

```python
DataFrame with columns:
  - ts: datetime64[ns] (normalized timestamp)
  - tide_m: float (tide value, m)
```

---

### 17.6.2 Tide Interpolation (Linear Interpolation)

**Formula:**
```
tide(t) = interp(t, [t₁, t₂, ..., tₙ], [h₁, h₂, ..., hₙ])
```

**Implementation:**
```python
def tide_at_timestamp(tide_df: pd.DataFrame, ts: pd.Timestamp) -> float:
    """
    Linear interpolation of tide at timestamp.
    Returns NaN if outside table range.
    """
    # Convert timestamp to int64 (nanosecond unit)
    x = tide_df["ts"].astype("datetime64[ns]").view("int64").to_numpy()
    y = pd.to_numeric(tide_df["tide_m"], errors="coerce").to_numpy()
    xi = np.int64(ts.to_datetime64().astype("datetime64[ns]").astype("int64"))

    # Range check
    if xi < x.min() or xi > x.max():
        return float("nan")

    # Linear interpolation
    return float(np.interp(xi, x, y))
```

**Range Check:**

- `ts < tide_df["ts"].min()` → return `NaN`
- `ts > tide_df["ts"].max()` → return `NaN`
- Within range → return linear interpolation result

---

### 17.6.3 Stage Schedule Loading

**Supported Formats:**

- CSV/TXT: `pd.read_csv()` (automatic delimiter detection)
- Excel: `pd.read_excel()` (.xlsx, .xls)

**Automatic Column Detection:**

1. **Stage column:**
   - Priority: `stage` > `stage_id` > `stage name` > `stagename` > `stage_name`
   - Otherwise use first column

2. **Timestamp column:**
   - Priority: `timestamp` > `datetime` > `time` > `ts` > `start` > `start_time` > `eta`
   - Otherwise use `_detect_datetime_col()`

**Output Format:**

```python
DataFrame with columns:
  - StageKey: str (normalized Stage name)
  - ts: datetime64[ns] (timestamp)
```

**Stage Name Normalization:**

```python
def _norm_stage_key(x: str) -> str:
    s = str(x or "").strip().lower()
    s = " ".join(s.split())  # Remove consecutive spaces
    s = s.replace("_", " ").replace("-", " ")  # Unify separators
    s = " ".join(s.split())  # Reorganize
    return s
```

**Examples:**

- `"Stage 1"` → `"stage 1"`
- `"Stage_2"` → `"stage 2"`
- `"Stage-3"` → `"stage 3"`
- `"STAGE  4"` → `"stage 4"`

---

### 17.6.4 Forecast Tide Injection

**Strategy:**

1. **fillna**: Fill only if existing `Forecast_Tide_m` is NaN
2. **override**: Overwrite regardless of existing value

**Implementation:**
```python
def apply_forecast_tide_from_table(
    stage_df: pd.DataFrame,
    tide_df: pd.DataFrame,
    schedule_df: pd.DataFrame,
    *,
    stage_col: str = "Stage",
    out_col: str = "Forecast_Tide_m",
    strategy: str = "fillna",
) -> pd.DataFrame:
    # Stage → Timestamp mapping
    sched_map = {r["StageKey"]: r["ts"] for _, r in schedule_df.iterrows()}

    for i, r in df.iterrows():
        sk = _norm_stage_key(r.get(stage_col, ""))
        ts = sched_map.get(sk)
        if ts is None:
            continue
        tide_val = tide_at_timestamp(tide_df, ts)
        if np.isnan(tide_val):
            continue
        cur = _to_float(r.get(out_col), fallback=None, warn=False)
        if strategy == "override" or cur is None or (isinstance(cur, float) and np.isnan(cur)):
            df.at[i, out_col] = float(tide_val)
            assigned += 1
```

---

### 17.6.5 Forecast_Tide_m Priority (v1.1 Update)

**Changes (2025-12-29):**

The priority has been changed so that CLI `--forecast_tide` value takes highest priority. This ensures consistency of `Forecast_Tide_m` between `stage_table_unified.csv` and `solver_ballast_summary.csv`.

**New Priority (v1.1):**

```
Priority 0: CLI forecast_tide_m (Highest - if explicitly provided)
  ├─ Direct assignment in build_stage_table_from_stage_results()
  └─ Applied with priority over stage_tide_csv in enrich_stage_table_with_tide_ukc()

Priority 1: stage_tide_csv (only when CLI not provided)
  └─ Load stage-wise tide from stage_tide_AGI.csv, etc.

Priority 2: tide_table + stage_schedule (option)
  └─ Calculate stage-wise tide via Tide table interpolation
  └─ Input files:
     - `bplus_inputs/water tide_202512.xlsx`: Tide data (Excel, 576 lines)
     - `bplus_inputs/stage_schedule.csv`: Stage-wise timestamps (CSV, `Stage,Timestamp` format)
  └─ Usage example:
     ```python
     # stage_schedule.csv example
     Stage,Timestamp
     Stage 1,2025-12-01 08:00:00
     Stage 6A_Critical (Opt C),2025-12-01 20:00:00
     ```
  └─ Interpolation logic: Use `interpolate_tide_at_time()` function in `tide_ukc_engine.py`

Priority 3: CLI forecast_tide_m (fillna - safety mechanism)
  └─ Applied only to missing Stages
```

**Implementation Locations:**

1. **`build_stage_table_from_stage_results()` function (Line 2815-2820):**
   ```python
   if forecast_tide_m is not None:
       # If CLI value is explicitly provided, apply directly to all Stages (highest priority)
       out["Forecast_Tide_m"] = float(forecast_tide_m)
       print(f"[OK] Applied forecast_tide_m={forecast_tide_m} to stage_table (CLI override, all stages)")
   ```

2. **`enrich_stage_table_with_tide_ukc()` function (Line 3055-3063):**
   ```python
   # Priority 0: CLI forecast_tide_m (Highest - if explicitly provided)
   if forecast_tide_m is not None:
       # If CLI value exists, apply directly to all Stages (priority over stage_tide_csv)
       df["Forecast_Tide_m"] = float(forecast_tide_m)
       print(f"[OK] CLI forecast_tide_m={forecast_tide_m} applied (override stage_tide_csv and tide_table)")
   else:
       # Use stage_tide_csv only when CLI value not provided
       # Priority 1: Direct stage_tide_csv
       # ...
   ```

**Previous Priority (v1.0):**

```
Priority 1: stage_tide_csv (Highest)
Priority 2: tide_table + stage_schedule
Priority 3: CLI forecast_tide (fillna only)
```

**Reason for Change:**

- **Problem**: `stage_table_unified.csv` loaded values from `stage_tide_csv`, while `solver_ballast_summary.csv` used CLI values, causing inconsistency
- **Solution**: When CLI value is explicitly provided, ensure same value used from all sources
- **Effect**: Improved UKC calculation consistency, complete alignment of `Forecast_Tide_m` between `stage_table_unified.csv` and `solver_ballast_summary.csv`

**Usage Example:**

```bash
# CLI value takes highest priority
python integrated_pipeline_*.py --forecast_tide 1.5 ...

# Result:
# - stage_table_unified.csv: Forecast_Tide_m = 1.5 m for all Stages
# - solver_ballast_summary.csv: Forecast_Tide_m = 1.5 m for all Stages
# - Complete match ✅
```

**Notes:**

- If CLI `--forecast_tide` is not provided, previous priority (stage_tide_csv → tide_table → fallback) applies.
- If different tides per stage are needed, do not provide CLI value and use `stage_tide_csv`.

**Processing Flow:**

```
┌─────────────────────────────────┐
│ apply_forecast_tide_from_table()│
└──────────────┬──────────────────┘
               │
               ▼
    ┌──────────────────────┐
    │ Stage → Timestamp    │
    │ Mapping (schedule_df)│
    └──────┬───────────────┘
           │
    ┌──────┴──────┐
    │ Mapping     │
    │ success?    │
    └──────┬─────┘
           │
    ┌──────┴──────┐
    │ Yes         │ No
    ▼             ▼
┌──────────┐   Skip
│ Tide     │
│ Interpolate│
└────┬─────┘
     │
┌────┴────┐
│ Success?│
└────┬────┘
     │
┌────┴────┐
│ Yes     │ No
▼         ▼
┌──────────────┐   Skip
│ Strategy     │
│ Check        │
└────┬─────────┘
     │
┌────┴────┐
│ fillna  │ override
│ & NaN?   │
└────┬────┘
     │
     ▼
  Value injection
```

---

## 17.7 Integrated Calculation Examples

### 17.7.1 Overall Calculation Flow

**Input:**
- `DepthRef_m = 5.50` (m)
- `Forecast_Tide_m = 2.00` (m)
- `Draft_FWD_m = 3.27` (m)
- `Draft_AFT_m = 3.27` (m)
- `UKC_Min_m = 0.50` (m)
- `Squat_m = 0.15` (m)
- `SafetyAllow_m = 0.20` (m)

**Calculation Steps:**

1. **UKC Calculation:**
   ```
   UKC_fwd = 5.50 + 2.00 - 3.27 - 0.15 - 0.20 = 3.88 (m)
   UKC_aft = 5.50 + 2.00 - 3.27 - 0.15 - 0.20 = 3.88 (m)
   UKC_min_actual = min(3.88, 3.88) = 3.88 (m)
   ```

2. **Required Tide Calculation:**
   ```
   Draft_ref = max(3.27, 3.27) = 3.27 (m)
   Tide_required = max(0, (3.27 + 0.15 + 0.20 + 0.50) - 5.50)
                  = max(0, 4.12 - 5.50)
                  = max(0, -1.38)
                  = 0.00 (m)
   ```

3. **Tide Margin Calculation:**
   ```
   Tide_margin = 2.00 - 0.00 = 2.00 (m)
   ```

4. **Validation:**
   ```
   margin = 2.00 ≥ tolerance (0.10) → OK
   ```

---

### 17.7.2 Fallback Application Example

**Scenario: Forecast_Tide_m Missing**

**Input:**
- `Forecast_Tide_m = None`
- `DepthRef_m = 5.50`
- `Draft_FWD_m = 3.27`
- `Draft_AFT_m = 3.27`
- `UKC_Min_m = 0.50`

**Fallback Application:**

1. **UKC Calculation:**
   ```
   UKC_fwd = 5.50 + None - 3.27 - 0.15 - 0.20
   → ukc_end_m() returns: NaN
   ```

2. **Required Tide Calculation:**
   ```
   Tide_required = max(0, (3.27 + 0.15 + 0.20 + 0.50) - 5.50)
                  = 0.00 (m)  # Calculable without fallback
   ```

3. **Validation:**
   ```
   verify_tide(0.00, None, 0.10)
   → ("VERIFY", "Forecast tide not provided")
   ```

**Result:**
- `UKC_fwd_m = NaN`
- `UKC_aft_m = NaN`
- `UKC_min_actual_m = NaN`
- `Tide_required_m = 0.00`
- `Tide_margin_m = NaN`
- `Tide_verification = "VERIFY"`

---

## 17.8 Constants and Defaults

### 17.8.1 Constant Definitions

| Constant | Value | Unit | Description |
|----------|-------|------|-------------|
| `DEFAULT_TIDE_TOL_M` | 0.10 | m | Tide margin tolerance |
| `DEFAULT_DEPTH_REF_M` | 5.50 | m | AGI default depth reference |
| `DEFAULT_UKC_MIN_M` | 0.50 | m | Minimum UKC requirement |
| `DEFAULT_SQUAT_M` | 0.15 | m | Default squat allowance |
| `DEFAULT_SAFETY_ALLOW_M` | 0.20 | m | Default safety allowance |
| `FORMULA_TIMEOUT_SEC` | 120 | s | Excel formula finalization timeout |

### 17.8.2 Default Value Application Priority

```
1. User input (CLI/Profile)
2. Profile JSON value
3. Function parameter fallback_* value
4. tide_constants.py default
5. Hardcoded safe value (2.00, etc.)
```

---

## 17.9 I/O Optimization Integration

### 17.9.1 Fast-Path Reading

**Implementation:**
```python
def _read_df_any(path: Path) -> pd.DataFrame:
    """Read CSV/Excel/JSON with fast-path and parquet cache."""
    try:
        from io_parquet_cache import read_table_any
        has_fast_path = True
    except ImportError:
        has_fast_path = False

    suf = path.suffix.lower()
    if suf == ".csv":
        if has_fast_path:
            return read_table_any(path)  # ✅ fast-path + cache
        return pd.read_csv(path)  # Fallback
    # ...
```

**Performance Effect:**

- **1st execution**: CSV reading (same as before)
- **2nd execution**: Parquet cache hit → **2.5-3.3x faster**

---

## 17.10 Validation and Testing

### 17.10.1 Unit Test Examples

```python
def test_required_tide_m_with_fallbacks():
    """Test: required_tide_m with all None inputs uses fallbacks."""
    result = required_tide_m(None, None, None)
    # depth = 5.50, draft = 2.00, ukc = 0.50
    # req = max(0, (2.00 + 0.15 + 0.20 + 0.50) - 5.50)
    #     = max(0, -2.65) = 0.00
    assert result == 0.0

def test_ukc_end_m_none_handling():
    """Test: ukc_end_m returns NaN when inputs are None."""
    result = ukc_end_m(None, 2.00, 3.27)
    assert np.isnan(result)

def test_verify_tide_margin_logic():
    """Test: verify_tide returns correct status based on margin."""
    # FAIL case
    status, note = verify_tide(2.00, 1.50, 0.10)
    assert status == "FAIL"

    # LIMIT case
    status, note = verify_tide(2.00, 2.05, 0.10)
    assert status == "LIMIT"

    # OK case
    status, note = verify_tide(2.00, 2.20, 0.10)
    assert status == "OK"
```

---

## 17.11 Notes

### 17.11.1 Chart Datum (CD) Reference

All TIDE/UKC calculations are based on **Chart Datum (CD)**:

- **Forecast_tide_m**: CD-based tide
- **DepthRef_m**: CD-based depth
- **Tide_required_m**: CD-based required tide

**DatumOffset Integration:**

Some sites may apply DatumOffset:
```
Available_Depth = DepthRef + DatumOffset + Forecast_Tide
```

### 17.11.2 Unit Consistency

All calculations unified in **meters (m)**:

- Tide: m (CD reference)
- Depth: m (CD reference)
- Draft: m
- UKC: m
- Squat: m
- Safety Allowance: m

---

## 17.12 Change History

| Version | Date | Changes |
|---------|------|---------|
| v1.0 | 2025-12-28 | Initial: Detailed formulas, fallback mechanisms, validation logic |
| v1.1 | 2025-12-29 | Forecast_Tide_m priority change: CLI value highest priority to resolve consistency issue |

### v1.1 Change Details (2025-12-29)

**Key Changes:**

1. **Forecast_Tide_m Priority Redefinition**
   - CLI `--forecast_tide` value takes highest priority
   - `build_stage_table_from_stage_results()`: Direct CLI value assignment (instead of fillna)
   - `enrich_stage_table_with_tide_ukc()`: CLI value takes priority over stage_tide_csv if present

2. **Consistency Issue Resolution**
   - Complete alignment of `Forecast_Tide_m` between `stage_table_unified.csv` and `solver_ballast_summary.csv`
   - Improved UKC calculation consistency

3. **Impact Scope**
   - `integrated_pipeline_defsplit_v2_gate270_split_v3_auditpatched_autodetect_TIDE_v1.py`
   - `build_stage_table_from_stage_results()` function
   - `enrich_stage_table_with_tide_ukc()` function

**Verification Results:**

- ✅ Confirmed `Forecast_Tide_m = 1.5 m` match for all Stages
- ✅ UKC calculation accuracy verification completed
- ✅ Profile parameter (squat_m, safety_allow_m) auto-load working normally

---

**End of Document**
```

This translation maintains:
- Technical terms and code blocks unchanged
- Structure and formatting
- Code examples and implementations
- Version numbers and dates
- References and cross-references
- Mathematical formulas
- Tables and diagrams
- Flow charts and processing logic

The document is ready for use in English.
