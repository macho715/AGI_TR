# Ballast Pipeline - Core Functions Reference

**Purpose**: Core functions used in HVDC LCT BUSHRA RORO / Ballast Pipeline

**Version**: v1.1
**Last Updated**: 2025-12-30
**Target Audience**: Developers, system architects, technical users

---

## Table of Contents

1. [Orchestrator (Main Pipeline) Functions](#1-orchestrator-main-pipeline-functions)
2. [SSOT Conversion Functions](#2-ssot-conversion-functions)
3. [LP Solver Core Functions](#3-lp-solver-core-functions)
4. [Draft Calculation Functions](#4-draft-calculation-functions)
5. [Gate-related Functions](#5-gate-related-functions)
6. [Stage-wise/RoRo Functions](#6-stage-wiseroro-functions)
7. [Hold Point Functions](#7-hold-point-functions)
8. [Sequence Generator Functions](#8-sequence-generator-functions)
9. [Utility Functions](#9-utility-functions)

## 1. Orchestrator (Main Pipeline) Functions

### 1.1 `main()` - Pipeline Entry Point

**Location:** `integrated_pipeline_defsplit_v2_gate270_split_v3.py:3506`

**Functionality:**

- Controls overall pipeline execution order
- Parses command-line arguments and resolves paths
- Executes Steps 1~4 sequentially
- Automatically generates Gate FAIL report

**Call Sequence:**

```python
main()
  → resolve_site_profile_path() / load_site_profile_json()
  → step_run_script(1, "TR_EXCEL", ...)
  → step_run_script(2, "TR_STAGE_CSV", ...)  # if stage_results.csv missing
  → convert_tank_catalog_json_to_solver_csv()
  → convert_hydro_engineering_json_to_solver_csv()
  → build_stage_table_from_stage_results()
  → generate_stage_QA_csv()
  → inject_current_t_from_sensor_csv()
  → apply_tank_overrides_from_profile()
  → generate_gate_fail_report_md()
  → step_run_script(3, "OPS_INTEGRATED", ...)
  → step_run_script(4, "SOLVER_LP", ...)
  → step_run_script(5, "OPTIMIZER", ...)
```


### 1.2 `step_run_script()` - Script Execution Wrapper

**Location:** `integrated_pipeline_defsplit_v2_gate270_split_v3.py:2830`

**Signature:**

```python
def step_run_script(
    step_id: int,
    name: str,
    script: Path,
    args: List[str],
    cwd: Path,
    out_dir: Path,
    env: Optional[Dict[str, str]] = None,
) -> StepResult
```

**Functionality:**

- Validates script existence
- Generates log file path (`{step_id:02d}_{name}.log`)
- Executes subprocess via `run_cmd()` call
- Returns `StepResult` (ok, returncode, log)

---

### 1.3 `run_cmd()` - Subprocess Execution and Logging

**Location:** `integrated_pipeline_defsplit_v2_gate270_split_v3.py:153`

**Signature:**

```python
def run_cmd(
    cmd: List[str],
    cwd: Path,
    log_path: Path,
    env: Optional[Dict[str, str]] = None,
) -> int
```

**Functionality:**

- Executes subprocess (UTF-8 encoding)
- Simultaneously outputs stdout/stderr to log file and console (tee)
- Returns exit code

---

## 2. SSOT Conversion Functions

### 2.1 `convert_tank_catalog_json_to_solver_csv()` - Tank Catalog Conversion

**Location:** `integrated_pipeline_defsplit_v2_gate270_split_v3.py:1671`

**Signature:**

```python
def convert_tank_catalog_json_to_solver_csv(
    tank_catalog_json: Path,
    out_csv: Path,
    pump_rate_tph: float = 100.0,
    include_keywords: str = "BALLAST,VOID,FWB,FW,DB",
) -> Path
```

**Functionality:**

- Converts JSON tank catalog to SSOT CSV
- Coordinate system conversion: `x_from_mid_m = MIDSHIP_FROM_AP_M - lcg_m`
- Tank filtering and `use_flag` marking
- Priority weight assignment
- Output: `tank_ssot_for_solver.csv`

**Output CSV Columns:**

- `Tank`, `Capacity_t`, `x_from_mid_m`, `Current_t`, `Min_t`, `Max_t`
- `mode`, `use_flag`, `pump_rate_tph`, `priority_weight`

---

### 2.2 `convert_hydro_engineering_json_to_solver_csv()` - Hydro Table Conversion

**Location:** `integrated_pipeline_defsplit_v2_gate270_split_v3.py:1915`

**Signature:**

```python
def convert_hydro_engineering_json_to_solver_csv(
    hydro_json: Path,
    out_csv: Path,
    lbp_m: float = LPP_M,
) -> Path
```

**Functionality:**

- Converts Hydrostatic Table JSON to SSOT CSV
- Supports flexible JSON structures (list, dict with "rows", single dict)
- Column name normalization (`MCTC` → `MTC`, `LCF_m_from_midship` → `LCF_m`)
- Sorts in ascending order by `Tmean_m`
- Output: `hydro_table_for_solver.csv`

**Output CSV Columns:**

- `Tmean_m`, `TPC_t_per_cm`, `MTC_t_m_per_cm`, `LCF_m`, `LBP_m`

---

### 2.3 `build_stage_table_from_stage_results()` - Stage Table Construction

**Location:** `integrated_pipeline_defsplit_v2_gate270_split_v3.py:2063`

**Signature:**

```python
def build_stage_table_from_stage_results(
    stage_results_csv: Path,
    out_csv: Path,
    fwd_max_m: float = 2.70,
    aft_min_m: float = 2.70,
    aft_max_m: float = 3.50,
    trim_abs_limit_m: float = 0.50,
    d_vessel_m: Optional[float] = D_VESSEL_M,
    forecast_tide_m: Optional[float] = None,
    depth_ref_m: Optional[float] = None,
    ukc_min_m: Optional[float] = None,
    squat_m: float = 0.0,
    safety_allow_m: float = 0.0,
) -> Path
```

**Functionality:**

- Reads `stage_results.csv` to generate Stage Table SSOT
- Flexible column recognition (`Stage`/`stage_name`, `Dfwd_m`/`FWD_m`, `Daft_m`/`AFT_m`)
- Draft clipping (automatically clips when exceeding `D_vessel_m`)
- Gate value assignment (for Solver + Optimizer)
- Adds UKC parameters (when provided)
- Output: `stage_table_unified.csv`

**Core Logic:**

```python
# Draft clipping
if dfwd > d_vessel_m:
    dfwd = d_vessel_m  # Clip to physical limit
if daft > d_vessel_m:
    daft = d_vessel_m
```

---

### 2.4 `generate_stage_QA_csv()` - Stage QA CSV Generation

**Location:** `integrated_pipeline_defsplit_v2_gate270_split_v3.py:2383`

**Signature:**

```python
def generate_stage_QA_csv(
    stage_table_csv: Path,
    out_qa_csv: Path,
    fwd_max_m: float = None,
    aft_min_m: float = None,
    d_vessel_m: float = None,
    forecast_tide_m: Optional[float] = None,
    depth_ref_m: Optional[float] = None,
    ukc_min_m: Optional[float] = None,
    critical_only: bool = False,
    critical_stage_list: Optional[List[str]] = None,
    critical_regex: str = DEFAULT_CRITICAL_STAGE_REGEX,
    gateb_fwd_max_m_cd: Optional[float] = None,
    squat_m: float = 0.0,
    safety_allow_m: float = 0.0,
    ...
) -> Path
```

**Functionality:**

- Implements Definition-Split concept (Forecast_Tide vs Required_WL_for_UKC)
- Freeboard calculation (tide-independent)
- UKC calculation (tide-dependent)
- Gate validation (Gate-A, Gate-B, Freeboard, UKC)
- Output: `pipeline_stage_QA.csv`

**Key Calculations:**

```python
# Freeboard (tide-independent)
freeboard_fwd = d_vessel_m - dfwd
freeboard_aft = d_vessel_m - daft
freeboard_min = min(freeboard_fwd, freeboard_aft)

# UKC (tide-dependent)
if depth_ref_m and forecast_tide_m:
    available_depth = depth_ref_m + forecast_tide_m
    ukc_fwd = available_depth - (dfwd + squat_m + safety_allow_m)
    ukc_aft = available_depth - (daft + squat_m + safety_allow_m)
    ukc_min = min(ukc_fwd, ukc_aft)

# Required_WL_for_UKC_m (inverse calculation)
if ukc_min_m:
    draft_ref_max = max(dfwd, daft)
    required_wl_for_ukc = (
        draft_ref_max + squat_m + safety_allow_m + ukc_min_m
    ) - depth_ref_m
    required_wl_for_ukc = max(required_wl_for_ukc, 0.0)  # Prevent negative
```

---

### 2.5 `inject_current_t_from_sensor_csv()` - Sensor Data Injection

**Location:** `integrated_pipeline_defsplit_v2_gate270_split_v3.py:367`

**Signature:**

```python
def inject_current_t_from_sensor_csv(
    tank_ssot_csv: Path,
    sensor_csv: Path,
    strategy: str = "override",
    out_csv: Path = None,
) -> Dict[str, Any]
```

**Functionality:**

- Injects `Current_t` values from PLC/IoT sensor CSV into Tank SSOT
- Strategy: `override` (overwrites all values) or `fill_missing` (only when 0.0)
- Supports base name matching (`FWB1` → `FWB1.P`, `FWB1.S`)

---

### 2.6 `apply_tank_overrides_from_profile()` - Tank Overrides Application

**Location:** `integrated_pipeline_defsplit_v2_gate270_split_v3.py:567`

**Signature:**

```python
def apply_tank_overrides_from_profile(
    tank_ssot_csv: Path,
    profile: Dict[str, object],
    out_csv: Path = None,
) -> None
```

**Functionality:**

- Applies `tank_overrides` section from Site profile to Tank SSOT
- Supported overrides: `mode`, `use_flag`, `pump_rate_tph`, `Min_t`, `Max_t`, `priority_weight`
- Supports base name matching

---

## 3. LP Solver Core Functions

### 3.1 `solve_lp()` - LP Problem Solving

**Location:** `ballast_gate_solver_v4.py:381`

**Signature:**

```python
def solve_lp(
    dfwd0: float,
    daft0: float,
    hydro: HydroPoint,
    tanks: List[Tank],
    fwd_max: Optional[float] = None,
    aft_min: Optional[float] = None,
    d_vessel: Optional[float] = None,
    fb_min: float = 0.0,
    depth_ref: Optional[float] = None,
    forecast_tide: Optional[float] = None,
    ukc_min: Optional[float] = None,
    ukc_ref: str = "MAX",
    squat: float = 0.0,
    safety_allow: float = 0.0,
    mode: str = "limit",
    target_fwd: Optional[float] = None,
    target_aft: Optional[float] = None,
    prefer_time: bool = False,
    iterate_hydro: int = 2,
) -> Dict[str, Any]
```

**Functionality:**

- Linear Programming-based Ballast optimization
- Iterative Hydrostatic Table interpolation (default 2 iterations)
- Limit Mode (constraints) or Target Mode (target values)
- Enforces all Gates simultaneously (FWD_MAX, AFT_MIN, Freeboard, UKC)
- Calls `scipy.optimize.linprog(method='highs')`

**Return Value:**

```python
{
    "ballast_plan": List[Dict],  # Tank-wise Fill/Discharge plan
    "predicted": {
        "FWD_new_m": float,
        "AFT_new_m": float,
        "Trim_new_m": float,
        "Tmean_new_m": float,
        "ΔW_t": float,
    },
    "violations": {
        "viol_fwd_max_m": float,
        "viol_aft_min_m": float,
        "viol_fb_min_m": float,
        "viol_ukc_min_m": float,
    },
    "hydro_used": HydroPoint,
}
```

---

### 3.2 `predict_drafts()` - Draft Prediction

**Location:** `ballast_gate_solver_v4.py:313`

**Signature:**

```python
def predict_drafts(
    dfwd0: float,
    daft0: float,
    hydro: HydroPoint,
    tanks: List[Tank],
    delta: Dict[str, float],
) -> Dict[str, float]
```

**Functionality:**

- Calculates final Draft from ballast changes
- Uses Method B (LCF-based)

**Calculation Formula:**

```python
# Total weight change
total_w = Σ(Δw_i)
total_m = Σ(Δw_i × (x_i - LCF))

# Mean draft change
ΔTmean = total_w / (TPC × 100)

# Trim change
ΔTrim = total_m / (MTC × 100)

# Forward/Aft Draft change
ΔDfwd = ΔTmean - 0.5 × ΔTrim
ΔDaft = ΔTmean + 0.5 × ΔTrim

# Final Draft
Dfwd_new = Dfwd0 + ΔDfwd
Daft_new = Daft0 + ΔDaft
```

---

### 3.3 `build_rows()` - LP Coefficient Matrix Construction

**Location:** `ballast_gate_solver_v4.py:362`

**Signature:**

```python
def build_rows(
    hydro: HydroPoint,
    tanks: List[Tank],
) -> Tuple[np.ndarray, np.ndarray]
```

**Functionality:**

- Generates coefficient matrix for LP constraint construction
- `rowW`: Weight change coefficients (`ΣΔw`)
- `rowM`: Moment change coefficients (`Σ(Δw × (x-LCF))`)

**Return Value:**

- `rowW`: `[1.0, -1.0, 1.0, -1.0, ...]` (p_i=+1, n_i=-1)
- `rowM`: `[arm_0, -arm_0, arm_1, -arm_1, ...]` (arm_i = x_i - LCF)

---

### 3.4 `interp_hydro()` - Hydrostatic Table Interpolation

**Location:** `ballast_gate_solver_v4.py:123`

**Signature:**

```python
def interp_hydro(
    hdf: pd.DataFrame,
    tmean_m: float,
) -> HydroPoint
```

**Functionality:**

- Interpolates Hydrostatic values for current Tmean
- Linear interpolation
- Uses nearest value when Tmean is out of range

**Return Value:**

```python
@dataclass
class HydroPoint:
    tmean_m: float
    tpc_t_per_cm: float
    mtc_t_m_per_cm: float
    lcf_m: float  # from midship, +AFT/-FWD
    lbp_m: float
```

---

## 4. Draft Calculation Functions

### 4.1 `calc_drafts()` - Draft Calculation (Method B)

**Location:** `ssot/draft_calc.py:257`

**Signature:**

```python
def calc_drafts(
    tmean_m: float,
    trim_cm: float,
    lcf_m: float,
    lbp_m: float,
) -> Tuple[float, float]
```

**Functionality:**

- Method B (LCF-based) Draft calculation
- `Draft(x) = Tmean + slope × (x - LCF)`

**Formula:**

```python
slope = trim_cm / 100.0 / lbp_m  # m/m
fwd = tmean_m - slope * (lbp_m / 2.0 + lcf_m)
aft = tmean_m + slope * (lbp_m / 2.0 - lcf_m)
```

---

### 4.2 `calc_draft_with_lcf()` - LCF-based Draft Calculation

**Location:** `ssot/draft_calc.py` (Helper)

**Signature:**

```python
def calc_draft_with_lcf(
    tmean_m: float,
    trim_cm: float,
    lcf_m: float,
    lbp_m: float,
) -> Tuple[float, float]
```

**Functionality:**

- Method B Draft calculation (simplified version)
- Returns FWD/AFT Draft

---

## 5. Gate-related Functions

### 5.1 `pick_draft_ref_for_ukc()` - Draft Reference Selection for UKC Calculation

**Location:** `ballast_gate_solver_v4.py:269`

**Signature:**

```python
def pick_draft_ref_for_ukc(
    ref: str,
    dfwd: float,
    daft: float,
) -> float
```

**Functionality:**

- Selects Draft reference value for UKC calculation
- Options: `"FWD"`, `"AFT"`, `"MEAN"`, `"MAX"` (default)

---

### 5.2 `ukc_value()` - UKC Value Calculation

**Location:** `ballast_gate_solver_v4.py:280`

**Signature:**

```python
def ukc_value(
    depth_ref_m: Optional[float],
    wl_forecast_m: Optional[float],
    draft_ref_m: Optional[float],
    squat_m: float,
    safety_allow_m: float,
) -> float
```

**Functionality:**

- Calculates UKC (Under Keel Clearance)

**Formula:**

```python
UKC = (depth_ref_m + wl_forecast_m) - (draft_ref_m + squat_m + safety_allow_m)
```

---

### 5.3 `required_wl_for_ukc()` - Required Water Level Inverse Calculation

**Location:** `ballast_gate_solver_v4.py:292`

**Signature:**

```python
def required_wl_for_ukc(
    depth_ref_m: Optional[float],
    ukc_min_m: Optional[float],
    draft_ref_m: Optional[float],
    squat_m: float,
    safety_allow_m: float,
) -> float
```

**Functionality:**

- Inverse calculation of required water level to satisfy UKC_MIN

**Formula:**

```python
Required_WL = (ukc_min_m + draft_ref_m + squat_m + safety_allow_m) - depth_ref_m
```

---

### 5.4 `freeboard_min()` - Minimum Freeboard Calculation

**Location:** `ballast_gate_solver_v4.py:304`

**Signature:**

```python
def freeboard_min(
    d_vessel_m: Optional[float],
    dfwd: float,
    daft: float,
) -> float
```

**Functionality:**

- Calculates minimum Freeboard (tide-independent)

**Formula:**

```python
Freeboard_min = min(d_vessel_m - dfwd, d_vessel_m - daft)
```

---

### 5.5 `add_split_270_gates()` - 2.70m Split Gates Addition

**Location:** `integrated_pipeline_defsplit_v2_gate270_split_v3.py:832`

**Signature:**

```python
def add_split_270_gates(
    df: pd.DataFrame,
    critical_only: bool = True,
    critical_regex: str = DEFAULT_CRITICAL_STAGE_REGEX,
    gatea_aft_min_m: float = 2.70,
    gateb_fwd_max_m_cd: float = 2.70,
    guard_band_cm: float = 2.0,
) -> pd.DataFrame
```

**Functionality:**

- Gate-A (Captain): AFT ≥ 2.70m (all Stages)
- Gate-B (Mammoet): FWD ≤ 2.70m (Critical stages only)
- Applies Guard-Band (operational margin)

---

### 5.6 `generate_gate_fail_report_md()` - Gate FAIL Report Generation

**Location:** `integrated_pipeline_defsplit_v2_gate270_split_v3.py:942`

**Signature:**

```python
def generate_gate_fail_report_md(
    out_md: Path,
    site: str,
    profile_path: Optional[Path],
    stage_qa_csv: Path,
    tank_ssot_csv: Path,
    sensor_stats: Optional[Dict[str, Any]] = None,
    ukc_inputs: Optional[Dict[str, Any]] = None,
) -> Path
```

**Functionality:**

- Automatically generates Gate violation analysis report
- Includes Current_t status, sensor synchronization results, UKC input status
- Analyzes 2.70m Split Gates (Gate-A, Gate-B)

---

## 6. Stage-wise/RoRo Functions

### 6.1 `build_roro_stage_loads()` - RoRo Stage Load Construction

**Location:** `Untitled-2_patched_defsplit_v1_1.py:3787` (or `stage_wise_load_transfer.py`)

**Signature:**

```python
def build_roro_stage_loads(
    stage_name: str,
    preballast_t: float,
    w_tr: float = 271.20,
    fr_tr1_stow: float = 42.0,
    fr_tr1_ramp_start: float = 40.15,
    fr_tr1_ramp_mid: float = 37.00,
    fr_tr2_ramp: float = 17.95,
    fr_tr2_stow: float = 40.00,
    fr_preballast: float = 3.0,
) -> List[Dict[str, Any]]
```

**Functionality:**

- Calculates RoRo load distribution per stage
- Load distribution by SPMT position (Jetty/Linkspan/Vessel)
- Output: Load list (each load includes `weight_t`, `x_from_mid_m`)

**Stage Structure:**

- Stage 1~5: TR1 loading phase
- Stage 5_PreBallast: Pre-ballast state
- Stage 6A_Critical (Opt C): TR2 50% (Critical)
- Stage 6C: TR2 100% complete
- Stage 7: Post-deballast

---

### 6.2 `calculate_roro_stage_drafts()` - RoRo Stage Draft Calculation

**Location:** `Untitled-2_patched_defsplit_v1_1.py:3958`

**Signature:**

```python
def calculate_roro_stage_drafts(
    stage_name: str,
    loads: List[Dict[str, Any]],
    base_disp: float,
    base_tmean: float,
    hydro_df: Optional[pd.DataFrame],
    params: Dict[str, Any],
) -> Dict[str, Any]
```

**Functionality:**

- Calculates Draft/Trim for RoRo Stage
- Includes Hydrostatic Table interpolation
- Output: `FWD_m`, `AFT_m`, `Trim_cm`, `Tmean_m`, `ΔW_t`, `TM_LCF_tm`

---

### 6.3 `solve_stage()` - Stage Analysis (AGI TR Engine)

**Location:** `agi_tr_patched_v6_6_defsplit_v1.py:2253`

**Signature:**

```python
def solve_stage(
    base_disp_t: float,
    base_tmean_m: float,
    loads: List[LoadItem],
    **params
) -> Dict[str, Any]
```

**Functionality:**

- Executes stage-wise analysis (Hydro table interpolation, GM calculation)
- GM 2D bilinear interpolation
- Frame-based coordinate system
- Hydro table passed via `params["hydro_table"]` (optional)

**Parameters:**

- `base_disp_t`: Base displacement (t)
- `base_tmean_m`: Base mean draft (m)
- `loads`: List of LoadItem objects
- `**params`: Additional parameters including:
  - `hydro_table`: Optional list[dict] of hydrostatic table data
  - `MTC` or `MTC_t_m_per_cm`: Moment to change trim (t·m/cm)
  - `LCF` or `LCF_m_from_midship`: Longitudinal center of floatation (m)
  - `TPC` or `TPC_t_per_cm`: Tons per centimeter
  - `LBP` or `Lpp_m`: Length between perpendiculars (m)
  - `D_vessel` or `D_vessel_m`: Molded depth (m)

**Return Value:**

```python
{
    "Dfwd_m": float,      # Forward draft (m)
    "Daft_m": float,      # Aft draft (m)
    "Trim_cm": float,     # Trim (cm, positive = stern down)
    "Tmean_m": float,     # Mean draft (m)
    "Disp_t": float,      # Displacement (t)
    "GM_m": float,        # Metacentric height (m)
    # ... additional metadata
}
```

---

### 6.4 `optimize_early_stages_for_freeboard()` - Early Stage Freeboard Optimization

**Location:** `stage_wise_load_transfer.py:1215`

**Signature:**

```python
def optimize_early_stages_for_freeboard(
    base_disp_t: float,
    base_tmean_m: float,
    base_loads: List[LoadItem],
    hydro_table: List[Dict[str, Any]],
    params: Dict[str, Any],
    d_vessel_m: float = DEFAULT_D_VESSEL_M,
    freeboard_min_m: float = DEFAULT_FREEBOARD_MIN_M,
    max_ballast_t: float = 200.0,
    step_t: float = 5.0,
    tank_catalog_path: Optional[Path] = None,
    ssot_profile_path: Optional[Path] = None,
    use_ssot: bool = True,
) -> Dict[str, float]
```

**Functionality:**

- SSOT-compliant early-stage freeboard optimization
- Uses tank catalog for AFT zone tank selection (AGENTS.md compliant)
- Respects tank capacity constraints
- Optionally loads freeboard_min_m from SSOT profile
- Returns tank-wise ballast distribution

**SSOT Integration:**

- **Tank Catalog**: Loads `tank_catalog_from_tankmd.json` if provided
- **AFT Zone Filtering**: Only uses tanks with Frame < 30.151 (AGENTS.md rule)
- **Tank Categories**: Filters for `fresh_water` or `fresh_water_ballast` category
- **SSOT Profile**: Optionally loads `freeboard_min_m` from SSOT profile gate definitions
- **Fallback Mode**: If SSOT unavailable, uses legacy single-frame position logic

**Return Value:**

```python
{
    "FW2.P": 13.92,  # Tank ID -> ballast amount (t)
    "FW2.S": 13.92,
    # ... other AFT zone tanks
}
# Returns empty dict {} if no feasible solution found
```

**Tank Selection Priority:**

1. Most AFT tanks first (smallest LCG_m, i.e., closest to AP)
2. Capacity constraints respected (cannot exceed `cap_t`)
3. Stops when freeboard constraint satisfied

**Example Usage:**

```python
# With SSOT (recommended)
result = optimize_early_stages_for_freeboard(
    base_disp_t=2800.0,
    base_tmean_m=2.00,
    base_loads=loads,
    hydro_table=hydro_table,
    params=params,
    tank_catalog_path=Path("02_RAW_DATA/tank_catalog_from_tankmd.json"),
    ssot_profile_path=Path("patch1225/AGI_site_profile_COMPLETE_v1.json"),
    use_ssot=True,
)
# Result: {"FW2.P": 13.92, "FW2.S": 13.92}

# Legacy mode (fallback)
result = optimize_early_stages_for_freeboard(
    ...,
    use_ssot=False,
)
# Result: {"EarlyStage_Ballast": 27.84}
```

---

### 6.5 `build_stage_loads_explicit()` - Explicit Stage Load Construction

**Location:** `stage_wise_load_transfer.py:701`

**Signature:**

```python
def build_stage_loads_explicit(
    stage_name: str,
    preballast_t: float,
    params: Dict[str, Any],
    tr1_weight_t: float,
    tr2_weight_t: float,
    apply_forward_inventory: bool = True,
) -> List[LoadItem]
```

**Functionality:**

- Builds stage loads using document-defined Stage 1~7 mapping
- Explicitly defines loads for each stage (Stage 1 to Stage 7)
- Handles forward inventory discharge for critical stages
- Returns List[LoadItem] for use with `solve_stage()`

**Stage Definitions:**

- **Stage 1**: Arrival (no variable loads)
- **Stage 2**: TR1 ramp start
- **Stage 3**: TR1 mid-ramp
- **Stage 4**: TR1 on deck
- **Stage 5**: TR1 final stow
- **Stage 5_PreBallast**: TR1 stow + TR2 partial (71.4% by default) + pre-ballast
- **Stage 6A_Critical (Opt C)**: TR1 stow + TR2 ramp + pre-ballast
- **Stage 6C**: TR1 stow + TR2 stow + pre-ballast
- **Stage 7**: Post-deballast (same as Stage 6C)

**Forward Inventory Discharge:**

- Applied to critical stages (Stage 5_PreBallast, Stage 6A_Critical)
- Discharges FWB1.P/S and FWB2.P/S tanks
- Default values: FWB1 = -21.45t each, FWB2 = -21.45t each
- Controlled by `apply_forward_inventory` parameter

**Parameters:**

- `stage_name`: Stage identifier (e.g., "Stage 5_PreBallast")
- `preballast_t`: Pre-ballast weight (t)
- `params`: Dictionary containing frame positions and other parameters:
  - `FR_TR1_STOW`: TR1 final stow frame (default: 42.0)
  - `FR_TR1_RAMP_START`: TR1 ramp start frame (default: 40.15)
  - `FR_TR1_RAMP_MID`: TR1 ramp mid frame (default: 37.00)
  - `FR_TR2_RAMP`: TR2 ramp frame (default: 17.95)
  - `FR_TR2_STOW`: TR2 final stow frame (default: 40.00)
  - `FR_PREBALLAST`: Pre-ballast frame (default: 3.0)
  - `STAGE5_PROGRESS_PCT`: Stage 5 progress percentage (default: 71.4)
- `tr1_weight_t`: TR1 + SPMT weight (t)
- `tr2_weight_t`: TR2 + SPMT weight (t)
- `apply_forward_inventory`: Whether to apply forward inventory discharge

**Example Usage:**

```python
loads = build_stage_loads_explicit(
    stage_name="Stage 5_PreBallast",
    preballast_t=150.0,
    params={
        "FR_TR1_STOW": 42.0,
        "FR_TR2_RAMP": 17.95,
        "FR_PREBALLAST": 3.0,
        "STAGE5_PROGRESS_PCT": 71.4,
    },
    tr1_weight_t=280.0,
    tr2_weight_t=280.0,
    apply_forward_inventory=True,
)
# Returns: List[LoadItem] with TR1, TR2 partial, PreBallast, and FWB discharge loads
```

---

### 6.6 `calculate_stage_wise_reaction()` - Stage-wise Load Transfer Calculation

**Location:** `stage_wise_load_transfer.py:1508`

**Signature:**

```python
def calculate_stage_wise_reaction(
    base_disp_t: float = DEFAULT_BASE_DISP_T,
    base_tmean_m: Optional[float] = DEFAULT_BASE_TMEAN_M,
    total_cargo_t: float = DEFAULT_TOTAL_CARGO_T,
    tide_m: float = DEFAULT_TIDE_M,
    depth_ref_m: float = DEFAULT_DEPTH_REF_M,
    ukc_min_m: float = DEFAULT_UKC_MIN_M,
    d_vessel_m: float = DEFAULT_D_VESSEL_M,
    fwd_max_m: float = DEFAULT_FWD_MAX_M,
    aft_min_m: float = DEFAULT_AFT_MIN_M,
    trim_limit_cm: float = DEFAULT_TRIM_LIMIT_CM,
    tilt_limit_pct: Tuple[float, float] = DEFAULT_TILT_LIMIT_PCT,
    freeboard_min_m: float = DEFAULT_FREEBOARD_MIN_M,
    even_keel_tol_cm: float = DEFAULT_EVEN_KEEL_TOL_CM,
    pump_rate_tph: float = DEFAULT_PUMP_RATE_TPH,
    hydro_table: Optional[object] = None,
    params: Optional[Dict[str, Any]] = None,
    gate_b_critical_stages: Optional[Sequence[str]] = None,
    apply_forward_inventory: bool = True,
    optimize_preballast: bool = False,
    optimize_even_keel: bool = False,
    optimize_early_stages: bool = False,
    tank_catalog_path: Optional[Path] = None,
    ssot_profile_path: Optional[Path] = None,
) -> List[StageResult]
```

**Functionality:**

- Main orchestrator for stage-wise load transfer calculations
- Calculates draft/trim/tilt for all stages (Stage 1 to Stage 7)
- Performs gate compliance checks (Gate-A, Gate-B, Freeboard, UKC, Trim, etc.)
- Supports optional optimizations (pre-ballast, even-keel, early-stage freeboard)
- Returns List[StageResult] with comprehensive stage data

**Key Features:**

- **Stage Load Construction**: Uses `build_stage_loads_explicit()` for stage-specific loads
- **Early-Stage Optimization**: Optional SSOT-compliant freeboard optimization via `optimize_early_stages_for_freeboard()`
- **Pre-ballast Optimization**: Optional Gate-A compliance optimization via `optimize_preballast_for_gate_a()`
- **Even-Keel Optimization**: Optional trim minimization via `optimize_preballast_for_even_keel()`
- **Gate Compliance**: Comprehensive gate checking (AFT, FWD, Trim, UKC, Freeboard, GM, etc.)
- **Iterative Correction**: Applies `iterative_ballast_correction()` for Gate-B critical stages when FWD draft exceeds limit

**Return Value:**

```python
List[StageResult]  # One StageResult per stage
```

**StageResult Fields:**

- `stage_name`: Stage identifier
- `fwd_draft_m`, `aft_draft_m`: Draft values (m)
- `trim_cm`, `tilt_deg`: Trim and tilt values
- `gm_m`: Metacentric height (m)
- `freeboard_min_m`: Minimum freeboard (m)
- `gate_aft_pass`, `gate_fwd_pass`, `gate_trim_pass`, `gate_ukc_pass`, `gate_fb_pass`: Gate compliance flags
- `go_no_go`: Decision (GO/NO-GO/ABORT)
- `ballast_action`: Ballast operation description
- `pump_time_h`: Pump time (hours)
- `spmt_position`: SPMT position breakdown
- And many more fields for comprehensive stage analysis

**Example Usage:**

```python
results = calculate_stage_wise_reaction(
    base_disp_t=2800.0,
    base_tmean_m=2.00,
    optimize_early_stages=True,
    optimize_preballast=True,
    optimize_even_keel=True,
    tank_catalog_path=Path("02_RAW_DATA/tank_catalog_from_tankmd.json"),
    ssot_profile_path=Path("patch1225/AGI_site_profile_COMPLETE_v1.json"),
)
# Returns: List[StageResult] with 9 stages (Stage 1 to Stage 7)
```

---

## 7. Hold Point Functions

### 7.1 `process_hold_point()` - Hold Point Decision Making

**Location:** `hold_point_manager.py:29`

**Signature:**

```python
def process_hold_point(
    step_data: Dict,
    measured_drafts: Dict[str, float],
    tolerance_cm: float = 2.0,
    critical_tolerance_cm: float = 4.0,
) -> HoldPointDecision
```

**Functionality:**

- Compares measured values with predicted values
- Calculates deviation and makes decision (GO/RECALCULATE/NO-GO)

**Decision Rules:**

```python
if |Delta| <= 2.00cm:
    decision = "GO"
elif 2.01 <= |Delta| <= 4.00cm:
    decision = "RECALCULATE"
elif |Delta| > 4.00cm:
    decision = "NO-GO"
```

**Return Value:**

```python
@dataclass
class HoldPointDecision:
    step: int
    stage: str
    tank: str
    passed: bool
    deviation_fwd_cm: float
    deviation_aft_cm: float
    deviation_trim_cm: float
    decision: str  # "GO", "RECALCULATE", "NO-GO"
    notes: str
    timestamp: str
```

---

### 7.2 `log_hold_point()` - Hold Point Logging

**Location:** `hold_point_manager.py:111`

**Signature:**

```python
def log_hold_point(
    decision: HoldPointDecision,
    log_path: str,
) -> None
```

**Functionality:**

- Records Hold Point decision to log file
- Saves in CSV format

---

### 7.3 `recalculate_at_hold()` - Hold Point Recalculation

**Location:** `hold_point_recalculator.py` (or similar function)

**Functionality:**

- Recalculates remaining sequence based on measured values at Hold Point
- Updates SSOT and re-executes Solver

---

## 8. Sequence Generator Functions

### 8.1 `generate_sequence()` - Ballast Sequence Generation

**Location:** `ballast_sequence_generator.py`

**Signature:**

```python
def generate_sequence(
    ballast_plan: Dict[str, float],  # Tank-wise Delta_t
    tanks: List[Tank],
    pump_rate_tph: float = 100.0,
    daylight_only: bool = False,
) -> BallastSequence
```

**Functionality:**

- Converts Ballast plan to step-wise Sequence
- Time calculation based on pump rate
- Automatically inserts Hold Points
- Applies daylight window (optional)

---

### 8.2 `generate_checklist()` - Checklist Generation

**Location:** `checklist_generator.py:12`

**Signature:**

```python
def generate_checklist(
    sequence: List,
    profile,
    output_path: str = "BALLAST_OPERATIONS_CHECKLIST.md",
) -> str
```

**Functionality:**

- Automatically generates Ballast operations checklist
- Includes Hold Point decision logic
- Output in Markdown format

---

### 8.3 `generate_valve_lineup()` - Valve Lineup Generation

**Location:** `valve_lineup_generator.py`

**Functionality:**

- Adds valve operation information to Ballast Sequence
- Mapping based on Valve Map JSON
- Output: `BALLAST_SEQUENCE_WITH_VALVES.md`

---

## 9. Utility Functions

### 9.1 `resolve_site_profile_path()` - Site Profile Path Resolution

**Location:** `integrated_pipeline_defsplit_v2_gate270_split_v3.py:281`

**Functionality:**

- Automatically searches for Site Profile JSON path
- Priority: CLI flag → `inputs_dir/profiles/{site}.json` → default

---

### 9.2 `load_site_profile_json()` - Site Profile Loading

**Location:** `integrated_pipeline_defsplit_v2_gate270_split_v3.py:308`

**⚠️ Pre-Execution Configuration**
The site profile JSON file is loaded at pipeline startup. To adjust profile parameters (gates, pump rates, tank operability, etc.), **edit the profile file before executing the pipeline**. Profile values can be overridden by CLI arguments, but the profile file itself must be modified **prior to execution**.

**Functionality:**

- Parses and validates Site Profile JSON
- Returns: Profile dictionary

---

### 9.3 `resolve_current_t_sensor_csv()` - Sensor CSV Path Resolution

**Location:** `integrated_pipeline_defsplit_v2_gate270_split_v3.py:343`

**Functionality:**

- Automatically searches for Current_t sensor CSV path
- Priority: CLI flag → `inputs_dir/sensors/current_t_sensor.csv` → other standard paths

---

### 9.4 `fr_to_x()` - Frame → X Coordinate Conversion

**Location:** `agi_tr_patched_v6_6_defsplit_v1.py` (Helper)

**Signature:**

```python
def fr_to_x(fr: float) -> float
```

**Functionality:**

- Converts Frame number to Midship-referenced X coordinate
- `x = MIDSHIP_FROM_AP_M - fr`

---

### 9.5 `x_to_fr()` - X Coordinate → Frame Conversion

**Location:** `integrated_pipeline_defsplit_v2_gate270_split_v3.py` (Helper)

**Signature:**

```python
def x_to_fr(x_m: float) -> float
```

**Functionality:**

- Converts Midship-referenced X coordinate to Frame number
- `fr = MIDSHIP_FROM_AP_M - x_m`

---

## 10. Function Call Chain (Execution Flow)

### 10.1 Full Pipeline Execution

```
main()
  ├─ resolve_site_profile_path()
  ├─ load_site_profile_json()
  ├─ step_run_script(1, "TR_EXCEL", ...)
  │   └─ run_cmd()
  ├─ step_run_script(2, "TR_STAGE_CSV", ...)  # if needed
  │   └─ run_cmd()
  ├─ convert_tank_catalog_json_to_solver_csv()
  ├─ resolve_current_t_sensor_csv()
  ├─ inject_current_t_from_sensor_csv()
  ├─ apply_tank_overrides_from_profile()
  ├─ convert_hydro_engineering_json_to_solver_csv()
  ├─ build_stage_table_from_stage_results()
  ├─ generate_stage_QA_csv()
  │   ├─ add_split_270_gates()
  │   ├─ pick_draft_ref_for_ukc()
  │   ├─ ukc_value()
  │   └─ required_wl_for_ukc()
  ├─ generate_gate_fail_report_md()
  ├─ step_run_script(3, "OPS_INTEGRATED", ...)
  │   └─ run_cmd()
  ├─ step_run_script(4, "SOLVER_LP", ...)
  │   └─ run_cmd()
  │       → ballast_gate_solver_v4.py:main()
  │           ├─ load_tanks()
  │           ├─ load_hydro_table()
  │           ├─ load_stage_table()
  │           ├─ solve_lp()
  │           │   ├─ interp_hydro()
  │           │   ├─ build_rows()
  │           │   ├─ predict_drafts()
  │           │   └─ (iteration)
  │           └─ (CSV output)
  └─ step_run_script(5, "OPTIMIZER", ...)
      └─ run_cmd()
```

### 10.2 LP Solver Internal Execution

```
solve_lp()
  ├─ interp_hydro()  # Interpolate with initial Tmean
  ├─ build_rows()    # Construct coefficient matrix
  ├─ (LP problem construction)
  ├─ scipy.optimize.linprog()
  ├─ predict_drafts()  # Validate results
  ├─ (iteration: iterate_hydro times)
  │   ├─ interp_hydro()  # Interpolate with new Tmean
  │   ├─ build_rows()
  │   └─ solve_lp()
  └─ (return final results)
```

### 10.3 Hold Point Processing Flow

```
process_hold_point()
  ├─ Deviation calculation (measured - predicted)
  ├─ Decision making (GO/RECALCULATE/NO-GO)
  ├─ log_hold_point()  # Logging
  └─ (if NO-GO)
      └─ recalculate_at_hold()  # Recalculate
          ├─ SSOT update
          └─ solve_lp() re-execution
```

### 10.4 Stage-wise Load Transfer with Early-Stage Optimization

```
calculate_stage_wise_reaction()
  ├─ build_stage_loads_explicit()  # Stage-specific loads
  ├─ (if optimize_early_stages)
  │   └─ optimize_early_stages_for_freeboard()
  │       ├─ Load tank catalog (SSOT)
  │       ├─ Filter AFT zone tanks (Frame < 30.151)
  │       ├─ Load SSOT profile (optional)
  │       ├─ Optimize per tank (respecting capacity)
  │       └─ Return tank-wise ballast dict
  ├─ solve_stage()  # Draft/trim calculation
  └─ Gate compliance checks
```

---

## 11. Key Constants

### 11.1 Vessel Constants

```python
LPP_M = 60.302  # m (Length Between Perpendiculars)
MIDSHIP_FROM_AP_M = 30.151  # m
D_VESSEL_M = 3.65  # m (molded depth)
```

### 11.2 Gate Thresholds

```python
FWD_MAX_m = 2.70  # Gate-B (Critical stages)
AFT_MIN_m = 2.70  # Gate-A (all Stages)
AFT_MAX_m = 3.50  # Optimizer upper limit
UKC_MIN_m = 0.50  # Project default
```

### 11.3 Hold Point Thresholds

```python
GO_TOLERANCE_CM = 2.00      # GO allowable deviation
RECALC_TOLERANCE_CM = 4.00  # RECALCULATE upper limit
NO_GO_THRESHOLD_CM = 4.00   # NO-GO threshold
GUARD_BAND_CM = 2.00        # Gate operational margin
```

### 11.4 Defaults

```python
DEFAULT_PUMP_RATE_TPH = 100.0
DEFAULT_ITERATE_HYDRO = 2
DEFAULT_SQUAT_M = 0.0
DEFAULT_SAFETY_ALLOW_M = 0.0
```

---

## 12. Function Classification Summary

### 12.1 Orchestrator (Entry Point)

- `main()`, `step_run_script()`, `run_cmd()`

### 12.2 SSOT Conversion

- `convert_tank_catalog_json_to_solver_csv()`
- `convert_hydro_engineering_json_to_solver_csv()`
- `build_stage_table_from_stage_results()`
- `generate_stage_QA_csv()`

### 12.3 LP Solver

- `solve_lp()`, `predict_drafts()`, `build_rows()`, `interp_hydro()`

### 12.4 Draft Calculation

- `calc_drafts()`, `calc_draft_with_lcf()`

### 12.5 Gate

- `pick_draft_ref_for_ukc()`, `ukc_value()`, `required_wl_for_ukc()`, `freeboard_min()`
- `add_split_270_gates()`, `generate_gate_fail_report_md()`

### 12.6 Stage-wise/RoRo

- `build_roro_stage_loads()`, `calculate_roro_stage_drafts()`, `solve_stage()`
- `build_stage_loads_explicit()` (Explicit Stage 1~7 load construction)
- `calculate_stage_wise_reaction()` (Main stage-wise orchestrator)
- `optimize_early_stages_for_freeboard()` (SSOT-compliant early-stage optimization)

### 12.7 Hold Point

- `process_hold_point()`, `log_hold_point()`, `recalculate_at_hold()`

### 12.8 Sequence Generator

- `generate_sequence()`, `generate_checklist()`, `generate_valve_lineup()`

---

## 13. Pipeline Execution Files Reference

**Last Updated**: 2025-12-30
**Total Files**: 22 (excluding duplicates, including modules)

### 13.1 Main Pipeline Steps

| Step    | Script File                                                  | Execution Method | Description                                           | Dependencies |
| ------- | ------------------------------------------------------------ | ---------------- | ----------------------------------------------------- | ------------- |
| Step 0  | `agi_spmt_unified.py`                                      | `subprocess`   | SPMT cargo input generation (optional)                | `agi_ssot.py` (same directory) |
| Step 1  | `agi_tr_patched_v6_6_defsplit_v1.py`                       | `subprocess`   | TR Excel generation (optional)                        | - |
| Step 1b | `agi_tr_patched_v6_6_defsplit_v1.py`                       | `subprocess`   | `stage_results.csv` generation (required, csv mode) | - |
| Step 2  | `ops_final_r3_integrated_defs_split_v4_patched_TIDE_v1.py` | `subprocess`   | OPS Integrated Report (Excel + MD)                    | - |
| Step 3  | `ballast_gate_solver_v4_TIDE_v1.py`                        | `subprocess`   | Ballast Gate Solver (LP)                              | - |
| Step 4  | `Untitled-2_patched_defsplit_v1_1.py`                      | `subprocess`   | Ballast Optimizer (optional)                          | - |
| Step 5  | `bryan_template_unified_TIDE_v1.py`                        | `subprocess`   | Bryan Template generation and population              | - |

### 13.2 Optional Steps

| Step    | Script File                       | Execution Method    | Activation Condition      |
| ------- | --------------------------------- | ------------------- | ------------------------- |
| Step 4b | `ballast_sequence_generator.py` | `import` (module) | `--enable-sequence`     |
| Step 4b | `checklist_generator.py`        | `import` (module) | `--enable-sequence`     |
| Step 4c | `valve_lineup_generator.py`     | `import` (module) | `--enable-valve-lineup` |

### 13.3 Dependencies

| Parent Script                         | Dependent Script                       | Execution Method      | Description                                 |
| ------------------------------------- | -------------------------------------- | --------------------- | ------------------------------------------- |
| `bryan_template_unified_TIDE_v1.py` | `create_bryan_excel_template_NEW.py` | `subprocess`        | Bryan Template creation (Step 5 internal)   |
| `bryan_template_unified_TIDE_v1.py` | `populate_template.py`               | `import` (embedded) | Template population logic (Step 5 internal) |

### 13.4 Post-Processing and Utilities

| Category        | Script File                     | Base Path                          | Activation Condition                           |
| --------------- | ------------------------------- | ---------------------------------- | ---------------------------------------------- |
| Post-Processing | `ballast_excel_finalize.py`   | `tide/ballast_excel_finalize.py` | Auto-execute if file exists                    |
| Post-Processing | `excel_com_recalc_save.py`    | `tide/excel_com_recalc_save.py`  | `EXCEL_COM_RECALC_OUT` environment variable  |
| Utility         | `compile_headers_registry.py` | `compile_headers_registry.py`    | Auto-execute if `HEADERS_MASTER.xlsx` exists |
| Utility         | `debug_report.py`             | `debug_report.py`                | `--debug_report` or `--auto_debug_report`  |

### 13.5 Module Dependencies

| Module Path                     | Usage Location  | Execution Method | Description                                             |
| ------------------------------- | --------------- | ---------------- | ------------------------------------------------------- |
| `ssot.gates_loader`           | Step 4b         | `import`       | `SiteProfile`, `load_agi_profile` (profile loading) |
| `ssot.data_quality_validator` | Step 3, Step 4b | `import`       | `DataQualityValidator` (Tidying First Implementation) |
| `tide.tide_ukc_engine`        | Multiple Steps  | `import`       | Tide/UKC calculation SSOT engine                        |
| `tide.tide_constants`         | Multiple Steps  | `import`       | Tide/UKC constants                                      |

### 13.6 Pre-Step Execution Files (Optional)

| Script File              | Base Path                | Execution Method            | Activation Condition             | Description                        |
| ------------------------ | ------------------------ | --------------------------- | -------------------------------- | ---------------------------------- |
| `tide_stage_mapper.py` | `tide_stage_mapper.py` | Manual execution (Pre-Step) | When `--tide_windows` provided | Stage-wise tide mapping (AGI-only) |

### 13.7 Execution File Statistics

| Category                           | Count        | Notes                                      |
| ---------------------------------- | ------------ | ------------------------------------------ |
| **Required (subprocess)**    | 4            | Step 1b, Step 2, Step 3 (always executed)  |
| **Optional (subprocess)**    | 3            | Step 0, Step 1, Step 4, Step 5             |
| **Optional (import module)** | 3            | Step 4b, Step 4c                           |
| **Dependencies**             | 2            | Bryan Template internal calls              |
| **Post-Processing**          | 2            | Excel finalization                         |
| **Utilities**                | 2            | Headers registry compilation, Debug report |
| **Module Dependencies**      | 4            | SSOT modules (import)                      |
| **Pre-Step**                 | 1            | Tide mapping (manual execution)            |
| **Total**                    | **21** | (excluding duplicates, including modules)  |

**Note**:

- All execution files are called from `integrated_pipeline_defsplit_v2_gate270_split_v3_auditpatched_autodetect_TIDE_v1.py`.
- Script paths are automatically resolved by `resolve_script_path()` function (scripts in parent folders are automatically recognized even when running from `tide/` directory).
- For complete list, see `파이프라인 전체 아키텍처, 실행 파일, 로직 상세 설명.MD` Section 2.11.

---

## Reference Documents

- `03_DOCUMENTATION/00_CORE_ARCHITECTURE/00_System_Architecture_Complete.md`: Overall architecture
- `03_DOCUMENTATION/00_CORE_ARCHITECTURE/02_Data_Flow_SSOT.md`: SSOT conversion details
- `03_DOCUMENTATION/00_CORE_ARCHITECTURE/03_Pipeline_Execution_Flow.md`: Execution flow
- `03_DOCUMENTATION/00_CORE_ARCHITECTURE/04_LP_Solver_Logic.md`: LP Solver mathematical model
- `03_DOCUMENTATION/00_CORE_ARCHITECTURE/05_Definition_Split_Gates.md`: Definition-Split and Gates
- `03_DOCUMENTATION/00_CORE_ARCHITECTURE/Pipeline Complete Architecture and Execution Files Logic Detailed.md`: Complete pipeline architecture and execution files list (Section 2.11)
- `AGENTS.md`: Agent roles and rules

---

**Document Version:** v1.1 (Pipeline Execution Files Reference added)
**Last Updated:** 2025-12-30

**Document File**: `03_DOCUMENTATION/00_CORE_ARCHITECTURE/Ballast_Pipeline_Core_Functions.md`

---
