# AGENTS.md — HVDC LCT BUSHRA Ballast / RoRo SSOT (Cursor + Codex)

> Purpose
>
> - Prevent recurring conceptual errors (FWD/AFT tank direction, Frame↔x sign, draft vs freeboard vs UKC).
> - Force single-source-of-truth (SSOT) parameters and calculation definitions across scripts, solver, and reports.
> - Make Codex/Cursor edits safe: no manual patching of derived outputs; always regenerate from inputs.

**Version:** v3.2 (Updated: 2025-12-27)

---

## 0) Non-Negotiable SSOT (Read this first)

### 0.1 Coordinate system (Frame ↔ x)

- Frame convention (BUSHRA TCP / tank.md):
  - **Fr.0 = AP (AFT)**, Frame increases toward **FP (FWD)**.
- Midship reference:
  - **Frame 30.151 = Midship → x = 0.0**
- x sign convention:
  - **AFT (stern) = x > 0**
  - **FWD (bow)  = x < 0**
- Canonical conversion (do not reinterpret):
  - `x = _FRAME_SLOPE * (Fr - _FRAME_OFFSET)`
  - Default: `_FRAME_SLOPE = -1.0`, `_FRAME_OFFSET = 30.151`
  - Therefore: **x = 30.151 − Fr**

**Golden rule:**
If you treat a **bow tank (high Fr / high LCG(AP))** as "stern ballast," you will flip the physics and break every gate.

### 0.2 "Draft / Depth / Freeboard / UKC / Tide" are different gates

- **Draft**: keel → waterline (FWD/AFT/Mean).
- **Molded depth (D_vessel_m)**: keel → main deck (geometry).
- **Freeboard**: deck (or openings) → waterline (risk: deck wet/downflooding).
- **UKC**: seabed/chart depth + tide − draft (risk: grounding).
- **Tide** affects **UKC**, not **freeboard** (vessel rises with tide).

### 0.3 Stage artifacts (DO NOT MIX)

- `stage_results.csv`: TR/script stage geometry result (often **TR position only**, may not include solver ballast unless explicitly integrated).
  - **SSOT for AGI Stage definitions**: Stage set, names, and order must match `stage_results.csv` exactly.
  - AGI Stage set: Stage 1, 2, 3, 4, 5, 5_PreBallast, 6A_Critical (Opt C), 6C, 7 (9 stages total).
  - **DO NOT** mix AGI stages with DAS micro-stages (S0-Sx).
- `tank_ssot_for_solver.csv`: solver's tank universe, constraints, and *current_t*.
- `solver_ballast_summary.csv` / ballast plan: **delta** ballast moves the solver chose.
- `pipeline_stage_QA.csv`: must clearly state whether drafts are:
  - **raw** from stage_results, or
  - **post-solve** after applying solver deltas.

**Hard rule:** Never "hand edit" `stage_results.csv` to inject ballast effects for approvals.
If ballast must affect drafts, integrate that in a deterministic pipeline step and re-run.

### 0.4 Current_t Sensor Data SSOT (v3.1+)

- **Auto-detection**: Pipeline automatically searches for `current_t_*.csv` files if `--current_t_csv` not provided.
  - Search paths: `inputs_dir`, `inputs_dir/sensors/`, `base_dir`, `base_dir/sensors/`
  - Selection: Latest modified time (mtime) wins.
- **Injection strategy**: `override` (default) always overwrites with sensor values.
- **Audit trail**: `diff_audit.csv` records all injections:
  - Columns: `TS`, `Tank`, `CurrentOld_t`, `ComputedNew_t`, `Delta_t`, `ClampedFlag`, `Updated`, `SkipReason`
  - **Never edit `diff_audit.csv` manually**; it is a read-only audit log.

---

## 1) SSOT Parameters (must match code constants)

These are canonical unless explicitly overridden with documented evidence.

### 1.1 Hydro / geometry

- `MTC_t_m_per_cm` = **34.00** t·m/cm
- `LCF_m_from_midship` = **0.76** m
- `TPC_t_per_cm` = **8.00** t/cm
- `Lpp_m` = **60.302** m
- `D_vessel_m` = **3.65** m (molded depth parameter; confirm vs class/load line docs)

### 1.2 Ops / limits

- `max_fwd_draft_ops_m` = **2.70** m (critical RoRo ops limit)
- `max_fwd_draft_m` = **3.50** m (structural/nautical forward limit)
- `min_fwd_draft_m` = **1.50** m
- `trim_limit_abs_cm` = **240.00** cm
- `gm_target_m` = **1.50** m
- `gm_min_m` = **1.50** m (minimum GM requirement)
- `linkspan_freeboard_target_m` = **0.28** m (project target; distinct from MWS effective freeboard)

### 1.3 Pumping

- `pump_rate_tph` = **10.00** t/h (ship pump)
- `pump_rate_tph_hired` = **100.00** t/h (hired/shore pump nominal)

### 1.4 Guard-Band (P0-3, v3.1+)

- `gate_guard_band_cm` = **2.0** cm (default operational tolerance)
  - Production: 2.0cm (sensor error, fluid dynamics)
  - Development: 1.0cm (minimal margin)
  - Strict: 0.0cm (exact validation)

---

## 2) Tank Direction SSOT (FWD/AFT classification — do not argue with it)

### 2.1 Frame zones (tank.md)

- **AFT zone (stern)**:
  - `FW2 P/S`: **Fr.0–6** (aft fresh water)
  - `VOIDDB4 P/S`, `SLUDGE.C`, `SEWAGE.P`: **Fr.19–24** (mid-aft)
  - Fuel tanks `DO`, `FODB1`, `FOW1`, `LRFO P/S/C`: **Fr.22–33** (midship-ish; confirm allow-list)
- **MID zone**:
  - `VOID3 P/S`: **Fr.33–38**
- **MID-FWD zone**:
  - `FWCARGO2 P/S`: **Fr.38–43**
  - `FWCARGO1 P/S`: **Fr.43–48**
- **FWD/BOW zone (forward)**:
  - `FWB2 P/S`: **Fr.48–53** (forward ballast)
  - `VOIDDB1.C`: **Fr.48–56**
  - `FWB1 P/S`: **Fr.56–FE** (bow ballast)
  - `CL P/S`: **Fr.56–59** (chain lockers)

### 2.2 Practical consequence (common recurring error)

- `FWB1.*` and `FWB2.*` are **forward/bow** tanks. In the x system, they tend to have **x < 0**.
- They **cannot be used as "stern ballast"** to raise AFT draft without contradicting SSOT physics.
- If you need AFT-up / stern-down moment, use **AFT zone tanks** and/or shift cargo LCG aft.

---

## 3) Core Calculations (definitions used everywhere)

### 3.1 Trimming moment about LCF

- `TM_LCF_tm = Σ (w_i * (x_i − LCF))`

### 3.2 Trim

- `Trim_cm = TM_LCF_tm / MTC_t_m_per_cm`

### 3.3 Drafts (two methods)

**Method A (legacy / quick check):**

- `Dfwd_m = Tmean_m - (Trim_cm / 100) / 2`
- `Daft_m = Tmean_m + (Trim_cm / 100) / 2`
- Use only for quick approximation (small trim).

**Method B (v0.2 recommended, Lpp/LCF-based):**

- `trim_m = Trim_cm / 100`
- `slope = trim_m / Lpp_m`
- `x_fp = -Lpp_m / 2`
- `x_ap = +Lpp_m / 2`
- `Dfwd_m = Tmean_m + slope * (x_fp - LCF_m)`
- `Daft_m = Tmean_m + slope * (x_ap - LCF_m)`

Note: Method B is physically consistent for all trim ranges. If you change the formula, update it in one place and propagate.

### 3.4 Tide / UKC (do not mix with freeboard)

- UKC check uses: `UKC = ChartDepth + Tide − Draft`
- **Never claim Tide solves deck wet**; Tide is for UKC and under-keel constraints.

---

## 4) Gate Definitions (approval-oriented)

### Gate-A (Captain / propulsion)

- Default: **AFT draft >= 2.70 m** at defined "propulsion-relevant" stages.
- **Label SSOT:** Always use `AFT_MIN_2p70` (never write "2.70m" alone).
- **ITTC note:** approval docs must report **shaft centreline immersion** (not just AFT draft).
  - Minimum: 1.5D, Recommended: 2.0D (D = propeller diameter)
  - Calculation: immersion_shaftCL = draft_at_prop - z_shaftCL
- If proposing relaxation, must include:
  - risk statement (ventilation / loss of thrust / bearing risk),
  - mitigation (tug standby, RPM limit, steering limit, abort criteria),
  - written Captain/Owner acceptance.

### Gate-B (RoRo critical-only)

- **FWD draft (Chart Datum) ≤ 2.70 m** during **critical RoRo stages only**.
- **Label SSOT:** Always use `FWD_MAX_2p70_critical_only` (never write "2.70m" alone).
- Critical stage list must be explicit (no regex guessing in approvals).

## Gate Labels SSOT (No ambiguous "2.70m")

- **Never write "2.70m" alone.** Always label:
  - **Gate-A:** `AFT_MIN_2p70` (Captain / Propulsion)
  - **Gate-B:** `FWD_MAX_2p70_critical_only` (Mammoet / Critical RoRo only)

### Gate-B Scope Rule

- `FWD_MAX_2p70_critical_only` applies only when `Gate_B_Applies=True` (critical stages).
- Non-critical stages must show `N/A` for Gate-B (prevent false failures).

### Guard-Band Support (P0-3, v3.1+)

- **Purpose:** Operational tolerance for sensor error and fluid dynamics.
- **Default:** 2.0cm guard-band applied to gate checks.
- **Gate-A with Guard-Band:**
  - Strict: `AFT >= 2.70m` → PASS
  - Guard-Band (2.0cm): `AFT >= 2.68m` → PASS (with warning if 2.68m ≤ AFT < 2.70m)
  - Fail: `AFT < 2.68m` → FAIL
- **Gate-B with Guard-Band:**
  - Strict: `FWD (CD) <= 2.70m` → PASS
  - Guard-Band (2.0cm): `FWD (CD) <= 2.72m` → PASS (with warning if 2.70m < FWD ≤ 2.72m)
  - Fail: `FWD (CD) > 2.72m` → FAIL
- **CLI:** `--gate_guard_band_cm 2.0` (default), `0.0` (strict mode)

### Gate-FB (MWS load-out effective freeboard) ? REQUIRED for real ops packages

- **GL Noble Denton 0013/ND effective freeboard gate**:
  - With 4-corner monitoring: Freeboard_Req = 0.50 + 0.50*Hmax
  - Without monitoring: Freeboard_Req = 0.80 + 0.50*Hmax
- Pipeline flags:
  - --hmax_wave_m (required for ND gate)
  - --four_corner_monitoring (reduces requirement)
- If not available, flag as "MWS evidence missing" and stop approval claims.

### Gate-LL / Class

- If any stage implies exceedance of load-line/allowable draft, require class acceptance.

### Hold Point Band Logic (v3.2+)

- **Purpose:** Operational decision criteria for hold points (Stage 2, Stage 6A_Critical).
- **Band definitions:**
  - **GO:** Draft deviation ≤ ±2cm from target
  - **RECALC:** Draft deviation ±2cm ~ ±4cm from target
  - **STOP:** Draft deviation > ±4cm from target (requires rollback/recalculation)
- **Implementation:**
  - Hold point decisions must use band logic, not simple PASS/FAIL.
  - Band logic applies to both Gate-A (AFT) and Gate-B (FWD) at hold points.
- **Output:** `hold_point_analysis.csv` with `go_no_go`, `hp_band`, `draft_deviation_cm`.

---

## 5) Pipeline Inputs/Outputs (what each file means)

### Inputs

- `sensors/current_t_sensor.csv` (or `current_t_*.csv` - auto-detected)
  - Provides **Current_t** only (not mode/use_flag).
  - **Auto-detection (v3.1+):** Pipeline searches for `current_t_*.csv` if `--current_t_csv` not provided.
- `site_profile_*.json`
  - Tank overrides: `mode`, `use_flag`, `Min_t`, `Max_t`, etc.
  - Beware base matching: overriding `FWB1` may hit both `.P` and `.S`.

### SSOT outputs

- `ssot/tank_ssot_for_solver.csv`
  - Columns include (typical): `Tank,Cap_t,x_from_mid_m,Current_t,Min_t,Max_t,Mode,use_flag,...`
- `ssot/diff_audit.csv` (v3.1+)
  - Audit trail for Current_t sensor injections.
  - Columns: `TS`, `Tank`, `CurrentOld_t`, `ComputedNew_t`, `Delta_t`, `ClampedFlag`, `Updated`, `SkipReason`
  - **Read-only:** Never edit manually.

### Solver outputs

- Ballast plan / summary
  - Deltas applied by solver; must be mapped back to stage drafts deterministically.

### QA outputs

- `pipeline_stage_QA.csv`
  - Must specify whether drafts are **raw** (stage_results) or **post-solve**.
- `hold_point_analysis.csv` (v3.2+)
  - Hold point decisions with band logic (GO/RECALC/STOP).

### GM Verification outputs (v3.1+)

- `gm_stability_verification_v2b.csv`
  - GM verification results with CLAMP detection and FSM status.
  - Columns: `Stage`, `Disp_t`, `Trim_m`, `GM_raw_m`, `GM_min_m`, `GM_margin_m`, `GM_grid_source`, `GM_is_fallback`, `FSM_status`, `FSM_total_tm`, `GM_eff_m`, `Status`, `Note`
  - **Status values:**
    - `GOOD`: GM_raw >= GM_min, no CLAMP, FSM OK
    - `MINIMUM`: GM_raw >= GM_min but margin < 0.10m
    - `VERIFY_CLAMP_RANGE`: GM from fallback or CLAMP detected
    - `VERIFY_FSM_MISSING`: Partial tanks exist but FSM coeffs missing
    - `FAIL`: GM_raw < GM_min

---

## 6) Override Rules (avoid recurring "base matching" traps)

1) Prefer **explicit tank IDs** (`FWB1.P`) over base keys (`FWB1`).
2) Base keys are **disabled by default**. Use base match only with explicit flag:
   - `"match": "base"` in the override dict.
3) If overriding both `.P` and `.S`, ensure both overrides are **identical** unless you want asymmetry.
4) Never create an override for `.S` that unintentionally resets `.P` via base match.

## 6.1 FWD tank exclusion options (solver candidate control)

- `--exclude_fwd_tanks`: global ban (set `use_flag=N` for all tanks with `x_from_mid_m < 0`).
- `--exclude_fwd_tanks_aftmin_only`: for **AFT-min violating stages**, set FWD tanks to
  `DISCHARGE_ONLY` (fill prohibited, discharge allowed).
  - Implemented via stage table flag `Ban_FWD_Tanks=True` (solver applies per stage).

---

## 7) Review Guidelines (Codex + PRs)

- Reject any change that:
  - flips x sign convention,
  - re-labels FWB1/2 as AFT/stern tanks,
  - edits derived outputs (CSV) "by hand" to force PASS.
- Require evidence:
  - show `tank_ssot_for_solver.csv` row(s),
  - show stage table inputs,
  - show post-solve QA results.

---

## 8) Quick Debug Checklist (when results look "impossible")

1) Confirm x sign:
   - pick one tank: `Fr56` must map to x ≈ 30.151 − 56 = **negative**.
2) Confirm tank direction:
   - `FW2` must be in AFT zone; `FWB1/2` must be in FWD zone.
3) Confirm stage drafts source:
   - are QA drafts from stage_results or post-solve?
4) If drafts exceed `D_vessel_m`, ask:
   - is this a **load-line** issue (class) or a **UKC** issue (tide)?
5) If Gate-A fails:
   - do not "fix" with bow tanks; use AFT tanks or cargo shift.
6) If GM verification shows VERIFY:
   - check `GM_grid_source` (fallback vs JSON file)
   - check `FSM_status` (MISSING_COEFF vs OK)
   - check `CLAMP` warnings in verification output

---

## 9) Codex discovery notes

Codex loads instructions from global and project `AGENTS.md` files in a precedence chain.
Keep this file <32KiB and put deeper overrides near specialized folders if needed.

---

## 10) References (for approval packages)

- Add MWS/load-out references (effective freeboard, class acceptance) when generating approval docs.
- Add propulsion/immersion references only after converting from "draft" to "shaft immersion".

---

**Last Updated:** 2025-12-27
**Version:** v3.2
**Status:** Production Ready
