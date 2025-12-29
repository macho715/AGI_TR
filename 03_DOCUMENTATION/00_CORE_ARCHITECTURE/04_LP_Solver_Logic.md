# 제4장: LP Solver 로직

**작성일:** 2025-12-20
**버전:** v3.3 (Updated: 2025-12-28)
**목적:** Linear Programming 기반 Ballast 최적화의 수학적 모델 및 알고리즘 이해

**최신 업데이트 (v3.3 - 2025-12-28):**
- Option 2 구현: Trim/Freeboard Gate 강제 로직 (Option B 패치)
  - `trim_abs_limit`, `trim_limit_enforced` 파라미터 추가
  - `freeboard_min_m`, `freeboard_min_enforced` 파라미터 추가
  - LP 제약 조건에 Trim/Freeboard hard constraint 추가

**최신 업데이트 (v3.2 - 2025-12-27):**
- AGENTS.md SSOT 통합 (좌표계 변환, Gate 정의)
- 좌표계 변환 공식 명확화 (x = 30.151 - Fr)
- Gate 정의 명확화 (Gate-A: AFT_MIN_2p70, Gate-B: FWD_MAX_2p70_critical_only)

**최신 업데이트 (v3.1 - 2025-12-27):**
- 문서 버전 업데이트 (다른 문서들과 일관성 유지)

---

## 4.1 LP 모델 개요

### 4.1.1 문제 정의

Ballast Gate Solver는 **선형 프로그래밍(Linear Programming)**을 사용하여 다음 문제를 해결합니다:

- **목표**: 게이트 제약 조건을 만족하면서 최소 비용(중량 또는 시간)의 Ballast 계획 수립
- **결정 변수**: 각 탱크별 Fill/Discharge 양
- **제약 조건**: FWD_MAX, AFT_MIN, Freeboard, UKC 게이트
- **목적 함수**: 총 중량 변화 최소화 또는 총 펌핑 시간 최소화

### 4.1.2 솔버 구조

```
┌─────────────────────────────────────────────────────────┐
│  Input: Initial Drafts, Tanks, Hydro Table, Gates      │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│  Iterative Hydro Refinement Loop (기본 2회)            │
│  ┌───────────────────────────────────────────────────┐ │
│  │ 1. Hydrostatic Table 보간 (현재 Tmean 기준)      │ │
│  │ 2. LP 문제 구성                                    │ │
│  │    - Decision Variables: p_i, n_i                 │ │
│  │    - Objective Function                           │ │
│  │    - Constraints (Gates)                          │ │
│  │ 3. scipy.optimize.linprog 실행                    │ │
│  │ 4. 결과로 새로운 Tmean 계산                       │ │
│  └──────────────────────┬────────────────────────────┘ │
│                         │                               │
│                         ▼                               │
│              수렴 또는 반복 횟수 도달?                   │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│  Output: Ballast Plan, Predicted Drafts, Violations    │
└─────────────────────────────────────────────────────────┘
```

---

## 4.2 결정 변수 (Decision Variables)

### 4.2.1 변수 정의

각 탱크 `i`에 대해 **두 개의 비음수 변수**를 정의합니다:

- `p_i ≥ 0`: 탱크 `i`의 Fill 양 (tons)
- `n_i ≥ 0`: 탱크 `i`의 Discharge 양 (tons)

**순 중량 변화:**
```
Δw_i = p_i - n_i
```
- `Δw_i > 0`: Fill (중량 증가)
- `Δw_i < 0`: Discharge (중량 감소)
- `Δw_i = 0`: 변화 없음

### 4.2.2 변수 경계 (Bounds)

각 탱크의 `bounds_pos_neg()` 메서드가 다음을 반환합니다:

```python
def bounds_pos_neg(self) -> Tuple[float, float, float, float]:
    # Returns: (p_lo, p_hi, n_lo, n_hi)
    # p_lo, n_lo: 항상 0.0 (비음수)
    # p_hi: max_fill = max(0, Max_t - Current_t)
    # n_hi: max_dis = max(0, Current_t - Min_t)
```

**탱크 모드별 제한:**

| Mode | p_hi | n_hi | 설명 |
|------|------|------|------|
| `FILL_DISCHARGE` | `max(0, Max_t - Current_t)` | `max(0, Current_t - Min_t)` | 양방향 |
| `FILL_ONLY` | `max(0, Max_t - Current_t)` | `0.0` | Fill만 |
| `DISCHARGE_ONLY` | `0.0` | `max(0, Current_t - Min_t)` | Discharge만 |
| `BLOCKED` / `FIXED` | `0.0` | `0.0` | 사용 불가 |
| `use_flag = "N"` | `0.0` | `0.0` | 사용 불가 |

### 4.2.3 변수 배열 구조

LP 문제에서 변수는 다음과 같이 배열됩니다:

```python
variables = [
    p_0, n_0,  # Tank 0: Fill, Discharge
    p_1, n_1,  # Tank 1: Fill, Discharge
    ...
    p_{n-1}, n_{n-1},  # Tank n-1
    slack_vars...  # Slack variables (나중에 추가)
]
```

총 변수 개수: `2 * n_tanks + n_slacks`

---

## 4.3 Draft 예측 모델

### 4.3.1 Hydrostatic 관계식

**평균 흘수 변화 (ΔTmean):**
```
ΔTmean = ΣΔw / (TPC × 100)
```
- `TPC` (Tons Per Centimeter): 흘수 1cm당 중량 변화
- `100`: cm → m 변환 계수

**트림 변화 (ΔTrim):**
```
ΔTrim = Σ(Δw × (x - LCF)) / (MTC × 100)
```
- `x`: 탱크 LCG (Midship 기준, `x_from_mid_m`)
  - `x > 0`: AFT (선미 방향)
  - `x < 0`: FWD (선수 방향)
- `LCF` (Longitudinal Center of Flotation): 부력 중심 (Midship 기준, +AFT/-FWD)
- `MTC` (Moment to Change Trim): 트림 1cm 변화에 필요한 모멘트

**좌표계 변환 (SSOT - AGENTS.md 기준)**:
- Frame → x: `x = 30.151 - Fr` (재해석 금지)
- LCG (AP 기준) → x (Midship 기준): `x_from_mid_m = 30.151 - lcg_from_ap_m`

**Forward/Aft Draft 변화:**
```
ΔDfwd = ΔTmean - 0.5 × ΔTrim
ΔDaft = ΔTmean + 0.5 × ΔTrim
```

**최종 Draft:**
```
Dfwd_new = Dfwd0 + ΔDfwd
Daft_new = Daft0 + ΔDaft
```

### 4.3.2 `predict_drafts` 함수

**위치:** `ballast_gate_solver_v4.py` (lines 308-342)

**구현:**
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

### 4.3.3 LP 계수 행렬 구성

**`build_rows` 함수:**
```python
def build_rows(hydro: HydroPoint, tanks: List[Tank]) -> Tuple[np.ndarray, np.ndarray]:
    n = len(tanks)
    rowW = np.zeros(2 * n, dtype=float)  # ΣΔw 계수
    rowM = np.zeros(2 * n, dtype=float)  # Σ(Δw × (x-LCF)) 계수
    for i, t in enumerate(tanks):
        arm = t.x_from_mid_m - hydro.lcf_m
        rowW[2 * i] = 1.0      # p_i 계수 (+1)
        rowW[2 * i + 1] = -1.0 # n_i 계수 (-1)
        rowM[2 * i] = arm      # p_i 모멘트 계수
        rowM[2 * i + 1] = -arm # n_i 모멘트 계수
    return rowW, rowM
```

**Draft 변화 계수:**
```python
coef_tmean = rowW / (hydro.tpc_t_per_cm * 100.0)
coef_trim = rowM / (hydro.mtc_t_m_per_cm * 100.0)
coef_dfwd = coef_tmean - 0.5 * coef_trim
coef_daft = coef_tmean + 0.5 * coef_trim
```

---

## 4.4 목적 함수 (Objective Function)

### 4.4.1 목적 함수 선택

두 가지 모드를 지원합니다:

1. **Weight Minimization** (`prefer_time=False`)
   ```python
   c_i = priority_weight_i
   ```
   - 목표: 총 중량 변화 최소화
   - 우선순위가 낮은 탱크 우선 사용

2. **Time Minimization** (`prefer_time=True`)
   ```python
   c_i = priority_weight_i / pump_rate_tph_i
   ```
   - 목표: 총 펌핑 시간 최소화
   - 펌프 속도가 빠른 탱크 우선 사용

### 4.4.2 목적 함수 구성

```python
c = []  # Objective function coefficients
for t in tanks:
    w = t.priority_weight
    if prefer_time:
        c += [w / t.pump_rate_tph, w / t.pump_rate_tph]  # [p_i, n_i]
    else:
        c += [w, w]  # [p_i, n_i]

# Slack variables에 대한 penalty 추가
if mode == "limit":
    c += [violation_penalty] * 4  # viol_fwd, viol_aft, viol_fb, viol_ukc
else:  # target mode
    c += [slack_weight_penalty, slack_weight_penalty,
          slack_moment_penalty, slack_moment_penalty]  # slackW_pos, slackW_neg, slackM_pos, slackM_neg
```

**최소화 문제:**
```
minimize: c^T · x
```

---

## 4.5 제약 조건 (Constraints)

### 4.5.1 Limit Mode 제약 조건

**Limit Mode**에서는 **불등식 제약** (`A_ub · x ≤ b_ub`)을 사용합니다.

#### 1) FWD_MAX Gate (Gate-B: Mammoet / Critical RoRo only)

**제약:**
```
Dfwd_new ≤ FWD_MAX
```

**LP 형식:**
```
Dfwd0 + coef_dfwd^T · x ≤ FWD_MAX
coef_dfwd^T · x ≤ FWD_MAX - Dfwd0
```

**Slack 변수 포함 (Soft Constraint):**
```
coef_dfwd^T · x - viol_fwd ≤ FWD_MAX - Dfwd0
viol_fwd ≥ 0
```

**구현:**
```python
row = np.zeros(len(var_names), dtype=float)
row[:2*n] = coef_dfwd  # Tank variables
row[var_names.index("viol_fwd")] = -1.0
A_ub.append(row)
b_ub.append(float(fwd_max - dfwd0))
```

**Gate-B 정의 (SSOT - AGENTS.md 기준)**:
- `MAMMOET_FWD_MAX_DRAFT_M_CD = 2.70`: Mammoet FWD 최대 Draft (Chart Datum 기준, m)
- `GATE_B_LABEL = "FWD_MAX_2p70_critical_only"`: Gate-B 라벨 (모호한 "2.70m" 방지)
- **정의**: FWD draft (Chart Datum) ≤ 2.70m, **Critical RoRo stages만** 적용
- **적용 범위**: Critical stages만 (`Gate_B_Applies=True`)
- **Critical Stage 정의**: `DEFAULT_CRITICAL_STAGE_REGEX = r"(preballast.*critical|6a.*critical|stage\s*5.*preballast|stage\s*6a)"`
- **Non-critical stages**: `Gate_FWD_MAX_2p70_critical_only = "N/A"` (false failure 방지)

#### 2) AFT_MIN Gate (Gate-A: Captain / Propulsion)

**제약:**
```
Daft_new ≥ AFT_MIN
```

**LP 형식 (≥를 ≤로 변환):**
```
-Daft_new ≤ -AFT_MIN
-Daft0 - coef_daft^T · x ≤ -AFT_MIN
-coef_daft^T · x ≤ -AFT_MIN + Daft0
```

**Slack 변수 포함:**
```
-coef_daft^T · x - viol_aft ≤ -AFT_MIN + Daft0
viol_aft ≥ 0
```

**구현:**
```python
row = np.zeros(len(var_names), dtype=float)
row[:2*n] = -coef_daft  # Negative coefficient
row[var_names.index("viol_aft")] = -1.0
A_ub.append(row)
b_ub.append(float(-(aft_min - daft0)))
```

**Gate-A 정의 (SSOT - AGENTS.md 기준)**:
- `CAPTAIN_AFT_MIN_DRAFT_M = 2.70`: Captain AFT 최소 Draft (m)
- `GATE_A_LABEL = "AFT_MIN_2p70"`: Gate-A 라벨 (모호한 "2.70m" 방지)
- **정의**: AFT draft ≥ 2.70m (비상 시 프로펠러 효율/추진 확보)
- **적용 범위**: 모든 Stage (universal gate)
- **ITTC 참고**: 승인 문서에는 **shaft centreline immersion** (프로펠러 직경 기준)을 보고해야 함

#### 3) Freeboard Gate

**제약:**
```
Freeboard ≥ FB_MIN
D_vessel - Draft ≥ FB_MIN
Draft ≤ D_vessel - FB_MIN
```

**LP 형식 (FWD와 AFT 모두에 적용):**
```
Dfwd_new ≤ D_vessel - FB_MIN
Daft_new ≤ D_vessel - FB_MIN
```

**구현:**
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

**제약:**
```
|Trim_new| ≤ Trim_Abs_Limit
```

**LP 형식:**
```
Trim_new = Draft_AFT_new - Draft_FWD_new
-Trim_Abs_Limit ≤ Trim_new ≤ Trim_Abs_Limit
```

**구현:**
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

**제약:**
```
Freeboard_Min ≥ Freeboard_Min_m
```

**구현:**
```python
if freeboard_min_enforced and d_vessel is not None and freeboard_min_m is not None:
    draft_max = float(d_vessel - freeboard_min_m)
    # FWD와 AFT 모두에 제약 적용
    # (기존 Freeboard Gate와 동일하지만 enforced 플래그로 강제)
```

#### 4) UKC Gate

**제약:**
```
UKC ≥ UKC_MIN
(DepthRef + Forecast_Tide) - (Draft_ref + Squat + Safety) ≥ UKC_MIN
Draft_ref ≤ DepthRef + Forecast_Tide - Squat - Safety - UKC_MIN
```

**Draft_ref 선택:**
- `UKC_Ref = "FWD"`: FWD Draft 사용
- `UKC_Ref = "AFT"`: AFT Draft 사용
- `UKC_Ref = "MEAN"`: 평균 Draft 사용
- `UKC_Ref = "MAX"` (기본값): FWD와 AFT 모두에 제약 (더 엄격)

**구현:**
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

### 4.5.2 Target Mode 제약 조건

**Target Mode**에서는 **등식 제약** (`A_eq · x = b_eq`)을 사용합니다.

**목표:**
- `Dfwd_new = Target_FWD`
- `Daft_new = Target_AFT`

**등식 변환:**
```
Target_Tmean = 0.5 × (Target_FWD + Target_AFT)
Target_Trim = Target_AFT - Target_FWD

ΔTmean = Target_Tmean - Initial_Tmean
ΔTrim = Target_Trim - Initial_Trim

Required_ΔW = ΔTmean × TPC × 100
Required_ΔM = ΔTrim × MTC × 100
```

**등식 제약 (Slack 포함):**
```
ΣΔw + slackW_pos - slackW_neg = Required_ΔW
Σ(Δw × (x-LCF)) + slackM_pos - slackM_neg = Required_ΔM
```

**구현:**
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

## 4.6 반복 Hydrostatic Table 보간

### 4.6.1 반복의 필요성

Hydrostatic Table의 `TPC`, `MTC`, `LCF` 값은 **현재 Draft (Tmean)**에 따라 변합니다. 그러나 초기 Draft로 계산한 LP 결과는 새로운 Draft를 예측하므로, 이를 반영하여 다시 보간해야 정확도가 향상됩니다.

### 4.6.2 반복 알고리즘

```python
tmean = 0.5 * (dfwd0 + daft0)  # Initial Tmean
hydro_used = interp_hydro(hdf, tmean)

for iteration in range(max(1, iterate_hydro)):
    # 1. 현재 Tmean으로 Hydro Point 보간
    hydro_used = interp_hydro(hdf, tmean)

    # 2. LP 문제 구성 및 해결
    # ... (위의 LP 구성 코드)
    res = linprog(...)

    # 3. 결과에서 새로운 Tmean 계산
    delta = extract_delta_from_solution(res.x)
    pred = predict_drafts(dfwd0, daft0, hydro_used, tanks, delta)
    tmean = pred["Tmean_new_m"]  # 다음 반복을 위한 Tmean 업데이트
```

**기본 반복 횟수:** `iterate_hydro = 2` (명령줄 인자로 조정 가능)

### 4.6.3 수렴

일반적으로 2~3회 반복으로 충분히 수렴합니다. 더 많은 반복이 필요한 경우는 드뭅니다.

---

## 4.7 scipy.optimize.linprog 호출

### 4.7.1 함수 시그니처

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
- Interior point method 기반
- 대규모 LP 문제에 효율적
- Open-source, MIT license

### 4.7.3 결과 검증

```python
if not res.success:
    raise RuntimeError(f"LP failed: {res.message}")
```

---

## 4.8 해 해석 (Solution Interpretation)

### 4.8.1 변수 추출

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

### 4.8.2 Violation 추출 (Limit Mode)

```python
if mode == "limit":
    pred["viol_fwd_max_m"] = float(x[var_names.index("viol_fwd")])
    pred["viol_aft_min_m"] = float(x[var_names.index("viol_aft")])
    pred["viol_fb_min_m"] = float(x[var_names.index("viol_fb")])
    pred["viol_ukc_min_m"] = float(x[var_names.index("viol_ukc")])
```

**Violation 의미:**
- `viol_fwd_max_m > 0`: FWD_MAX 게이트 위반 (m 단위)
- `viol_aft_min_m > 0`: AFT_MIN 게이트 위반 (m 단위)
- `viol_fb_min_m > 0`: Freeboard 게이트 위반 (m 단위)
- `viol_ukc_min_m > 0`: UKC 게이트 위반 (m 단위)

**주의:** Violation이 있어도 LP는 해를 반환합니다 (Soft Constraint). Violation 값으로 위반 정도를 측정할 수 있습니다.

### 4.8.3 최종 Draft 예측

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

## 4.9 출력 형식

### 4.9.1 Ballast Plan CSV

| Column | Description | Example |
|--------|-------------|---------|
| `Tank` | 탱크 식별자 | "FWB2" |
| `Action` | "Fill" 또는 "Discharge" | "Discharge" |
| `Delta_t` | 순 중량 변화 (tons) | -25.50 |
| `PumpTime_h` | 펌핑 시간 (hours) | 0.26 |

**정렬:** `PumpTime_h` 내림차순, 그 다음 `Tank` 오름차순

### 4.9.2 Summary 출력

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

## 4.10 수학적 정리

### 4.10.1 표준 LP 형식

**목적:**
```
minimize: c^T · x
```

**제약:**
```
A_eq · x = b_eq        (등식 제약, Target Mode)
A_ub · x ≤ b_ub        (불등식 제약, Limit Mode)
l ≤ x ≤ u              (변수 경계)
```

**변수:**
```
x = [p_0, n_0, p_1, n_1, ..., p_{n-1}, n_{n-1}, slacks...]^T
```

### 4.10.2 문제 크기

- **변수 개수**: `2 × n_tanks + n_slacks`
  - `n_slacks = 4` (Limit Mode: viol_fwd, viol_aft, viol_fb, viol_ukc)
  - `n_slacks = 4` (Target Mode: slackW_pos, slackW_neg, slackM_pos, slackM_neg)
- **제약 개수**:
  - Limit Mode: `0 ~ 6` (게이트 개수에 따라)
  - Target Mode: `2` (등식 제약: Weight, Moment)

---

## 4.11 다음 장 안내

- **제5장**: Definition-Split과 Gates - 게이트 시스템의 개념적 배경 및 구현 상세
- **제6장**: 스크립트 인터페이스 및 API - Solver의 명령줄 인자 및 사용법

---

**참고:**
- 제1장: 파이프라인 아키텍처 개요
- 제2장: 데이터 흐름과 SSOT
- 제3장: 파이프라인 실행 흐름
- `ballast_gate_solver_v4.py`: LP Solver 구현
- `03_DOCUMENTATION/AGENTS.md`: 좌표계, Gate 정의, Tank Direction SSOT
- scipy.optimize.linprog 문서: [SciPy Documentation](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.linprog.html)

**문서 버전:** v3.2 (AGENTS.md SSOT 통합)
**최종 업데이트:** 2025-12-27
