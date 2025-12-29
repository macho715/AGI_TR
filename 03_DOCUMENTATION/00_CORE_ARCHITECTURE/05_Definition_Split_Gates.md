# 제5장: Definition-Split과 Gates

**작성일:** 2025-12-20
**버전:** v3.3 (Updated: 2025-12-28)
**목적:** Definition-Split 개념과 Gate Unified System의 구현 이해

**최신 업데이트 (v3.3 - 2025-12-28):**
- Option 1 패치 제안: Stage 5_PreBallast critical 적용 (AGI 규칙)
- Current_* vs Draft_* 단일화 (QA 테이블 SSOT 통일)
- Gate-B critical stage 정의 명확화

**최신 업데이트 (v3.2 - 2025-12-27):**
- AGENTS.md SSOT 통합 (Gate 정의, Draft vs Freeboard vs UKC 구분)
- Gate 정의 명확화 (Gate-A: AFT_MIN_2p70, Gate-B: FWD_MAX_2p70_critical_only)
- Draft vs Freeboard vs UKC 구분 명확화 (조위 의존성)

**최신 업데이트 (v3.1 - 2025-12-27):**
- 문서 버전 업데이트 (다른 문서들과 일관성 유지)

---

## 5.1 Definition-Split 개념 배경

### 5.1.1 문제 상황

과거 시스템에서는 다음과 같은 혼동이 발생할 수 있었습니다:

1. **조위(Water Level) 개념 혼동**
   - 예보 조위(Forecast Tide)와 요구 수면고(Required WL)를 구분하지 않음
   - UKC 계산 시 어떤 값을 사용해야 하는지 불명확

2. **Draft, Freeboard, UKC의 관계 혼동**
   - Draft와 Freeboard를 조위와 연관하여 계산
   - UKC와 Freeboard를 동일한 개념으로 오해

3. **게이트 제약의 불일치**
   - FWD_MAX와 AFT_MIN을 독립적으로 검사
   - 여러 게이트를 동시에 강제하지 않음

### 5.1.2 Definition-Split 해결책

**2025-12-16 문서**에 따라 다음 개념들을 **명확히 분리**합니다:

- **Forecast_Tide_m**: 예보 조위 (예측값, 입력)
- **Required_WL_for_UKC_m**: UKC 만족을 위한 요구 수면고 (역계산값, 출력)
- **Draft**: 조위와 무관한 선체 흘수
- **Freeboard**: 조위와 무관한 갑판 여유 높이
- **UKC**: 조위 의존적인 선저 여유 수심

---

## 5.2 조위(Water Level) 관련 정의

### 5.2.1 Forecast_Tide_m (예보 조위)

**정의:**
- 예측된 조위 높이 (Chart Datum 기준)
- 기상청 또는 조석표에서 제공되는 **예측값**
- 시간에 따라 변하는 값

**특성:**
- **입력값**: 사용자가 제공하거나 외부 데이터 소스에서 가져옴
- **시간 의존**: 특정 시간대의 예보값
- **용도**: UKC 계산 시 사용 가능한 수심 계산

**예시:**
```
Forecast_Tide_m = 0.30 m (Chart Datum 기준)
```

### 5.2.2 Required_WL_for_UKC_m (요구 수면고)

**정의:**
- UKC_MIN 요구값을 만족하기 위해 필요한 **최소 수면고**
- 현재 Draft를 기준으로 **역계산**된 값
- UKC 계산의 역함수

**계산 공식:**
```
UKC = (DepthRef + WaterLevel) - (Draft_ref + Squat + Safety)

UKC_MIN을 만족하려면:
  UKC_MIN ≤ (DepthRef + Required_WL) - (Draft_ref + Squat + Safety)

따라서:
  Required_WL_for_UKC_m = (Draft_ref_max + Squat + Safety + UKC_MIN) - DepthRef
```

**특성:**
- **출력값**: 시스템이 계산하여 제공
- **Draft 의존**: 현재 Draft가 크면 Required_WL도 커짐
- **용도**: "이 수면고 이상이면 UKC 요구값을 만족한다"는 정보 제공

**예시:**
```
현재 Draft_max = 2.70 m
DepthRef = 4.20 m
Squat = 0.0 m
Safety = 0.0 m
UKC_MIN = 0.50 m

Required_WL_for_UKC_m = (2.70 + 0.0 + 0.0 + 0.50) - 4.20 = -1.00 m

→ 음수이므로 0.0 m로 클리핑 (이미 UKC_MIN 만족)
```

### 5.2.3 두 개념의 관계

```
┌─────────────────────────────────────────────────────────┐
│  Forecast_Tide_m (예보)                                 │
│  - 입력값                                               │
│  - "내일 오전 10시 조위는 0.30m일 것으로 예상"         │
│                                                         │
│  ▼ 사용                                                │
│                                                         │
│  UKC 계산:                                             │
│    UKC = (DepthRef + Forecast_Tide) - (Draft + ...)    │
│                                                         │
│  ▼ 역계산                                              │
│                                                         │
│  Required_WL_for_UKC_m (요구값)                        │
│  - 출력값                                               │
│  - "이 Draft에서 UKC_MIN을 만족하려면 최소 0.50m 필요" │
└─────────────────────────────────────────────────────────┘
```

**중요:** 두 값을 혼동하지 않도록 명확히 구분합니다.

---

## 5.3 Draft, Freeboard, UKC 정의

### 5.3.1 Draft (흘수) - 조위 무관

**정의:**
- 선체가 물에 잠긴 깊이 (Keel부터 Waterline까지)
- **조위와 무관**: Draft 자체는 조위 변화와 독립적

**계산:**
```
Draft = 선체의 물리적 침수 깊이
```

**특성:**
- Ballast 중량 변화에 따라 변함
- 조위가 올라가도 Draft는 변하지 않음 (선체에 고정된 값)
- 단, 조위가 올라가면 Waterline이 상승하므로 **절대적 Draft 측정값**은 조위에 따라 달라 보일 수 있지만, **선체 기준 Draft**는 불변

**중요**: Draft는 **조위와 무관**합니다. Tide는 UKC에만 영향을 주며, Freeboard에도 영향을 주지 않습니다.

### 5.3.2 Freeboard (갑판 여유 높이) - 조위 무관

**정의:**
- Waterline부터 Deck까지의 높이
- **조위와 무관**: Draft의 보수(補數) 개념

**계산 공식:**
```
Freeboard = D_vessel_m - Draft
```

**구체적:**
```
Freeboard_FWD = D_vessel_m - Draft_FWD
Freeboard_AFT = D_vessel_m - Draft_AFT
Freeboard_Min = min(Freeboard_FWD, Freeboard_AFT)
Freeboard_Min_BowStern_m = Freeboard_Min_m  # 명시적 라벨 (linkspan freeboard와 구분)
```

**특성:**
- Draft가 증가하면 Freeboard 감소
- **조위와 무관** (선체 고정값)
- Green water (갑판 침수) 방지를 위한 여유 높이

**중요**: Freeboard는 **조위와 무관**합니다. Tide는 UKC에만 영향을 주며, Freeboard에는 영향을 주지 않습니다. "Tide가 Freeboard를 해결한다"고 주장하지 말 것.

**예시:**
```
D_vessel_m = 3.65 m (Molded Depth)
Draft_FWD = 2.50 m
Draft_AFT = 2.70 m

Freeboard_FWD = 3.65 - 2.50 = 1.15 m
Freeboard_AFT = 3.65 - 2.70 = 0.95 m
Freeboard_Min = 0.95 m
```

### 5.3.3 UKC (Under Keel Clearance, 선저 여유 수심) - 조위 의존

**정의:**
- 해저(Sea Bed)부터 Keel까지의 여유 수심
- **조위 의존**: 조위가 올라가면 UKC 증가

**계산 공식:**
```
UKC = Available_Depth - (Draft_ref + Squat + Safety)

Available_Depth = Charted_Depth + Water_Level
Water_Level = Forecast_Tide_m (예보 조위)
```

**구체적:**
```
UKC_FWD = (DepthRef + Forecast_Tide) - (Draft_FWD + Squat + Safety)
UKC_AFT = (DepthRef + Forecast_Tide) - (Draft_AFT + Squat + Safety)
UKC_Min = min(UKC_FWD, UKC_AFT)
```

**특성:**
- 조위가 올라가면 UKC 증가 (더 많은 여유 수심)
- 조위가 내려가면 UKC 감소 (접촉 위험 증가)
- 해저 접촉 방지를 위한 안전 여유

**중요**: UKC는 **조위에 의존**합니다. Tide는 UKC에만 영향을 주며, Freeboard에는 영향을 주지 않습니다.

**예시:**
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

### 5.3.4 세 개념의 관계 정리

```
┌─────────────────────────────────────────────────────────┐
│  Draft (조위 무관)                                       │
│  - 선체 침수 깊이                                        │
│  - Ballast에 따라 변함                                   │
│                                                         │
│  Freeboard (조위 무관)                                  │
│  = D_vessel - Draft                                     │
│  - 갑판 여유 높이                                        │
│                                                         │
│  ─────────────────────────────────────────────────────  │
│                                                         │
│  UKC (조위 의존)                                        │
│  = (DepthRef + Forecast_Tide) - (Draft + Squat + Safety)│
│  - 선저 여유 수심                                        │
│  - 조위가 올라가면 증가                                  │
└─────────────────────────────────────────────────────────┘
```

**핵심:** Draft와 Freeboard는 조위와 무관하지만, UKC는 조위에 의존합니다.

---

## 5.4 Gate Unified System

### 5.4.1 Gate 개념

**Gate**는 **운영 제약 조건**으로, 선박의 안전한 운영을 보장하기 위한 최소/최대값입니다.

### 5.4.2 FWD_MAX Gate (Gate-B: Mammoet / Critical RoRo only)

**목적:**
- Critical RoRo stages에서 Ramp 높이 제한
- Mammoet의 운영 제약 조건 (Chart Datum 기준)

**제약:**
```
Draft_FWD ≤ FWD_MAX_m (Chart Datum referenced)
```

**기본값:** `MAMMOET_FWD_MAX_DRAFT_M_CD = 2.70 m` (Chart Datum 기준)

**Gate-B 정의 (SSOT - AGENTS.md 기준)**:
- `GATE_B_LABEL = "FWD_MAX_2p70_critical_only"`: Gate-B 라벨 (모호한 "2.70m" 방지)
- **정의**: FWD draft (Chart Datum) ≤ 2.70m, **Critical RoRo stages만** 적용

**Critical Stage 정의 (AGI 규칙):**
- `DEFAULT_CRITICAL_STAGE_REGEX = r"(preballast.*critical|6a.*critical|stage\s*5.*preballast|stage\s*6a)"`
- **AGI 규칙**: `Stage 5_PreBallast`는 **항상 critical**로 간주 (Option 1 패치 제안)
- **현재 구현**: Regex 기반 매칭 (Option 1 패치로 명시적 체크 추가 권장)

**Option 1 패치 제안:**
```python
def _is_critical_stage(stage_name: str) -> bool:
    """Critical stage 판정 (AGI 규칙 반영)"""
    stage_lower = str(stage_name).lower()

    # AGI 규칙: Stage 5_PreBallast는 항상 critical
    if "preballast" in stage_lower and "stage" in stage_lower:
        return True

    # 기존 regex 매칭
    return bool(re.search(DEFAULT_CRITICAL_STAGE_REGEX, stage_lower))
```
- **적용 범위**: Critical stages만 (`Gate_B_Applies=True`)
- **Critical Stage 정의**: `DEFAULT_CRITICAL_STAGE_REGEX = r"(preballast.*critical|6a.*critical|stage\s*5.*preballast|stage\s*6a)"`
- **Non-critical stages**: `Gate_FWD_MAX_2p70_critical_only = "N/A"` (false failure 방지)

**구현 (LP Solver):**
```python
# Limit Mode
if fwd_max is not None:
    row = np.zeros(len(var_names), dtype=float)
    row[:2*n] = coef_dfwd  # Draft_FWD 변화 계수
    row[var_names.index("viol_fwd")] = -1.0
    A_ub.append(row)
    b_ub.append(float(fwd_max - dfwd0))
```

### 5.4.3 AFT_MIN Gate (Gate-A: Captain / Propulsion)

**목적:**
- 비상 시 프로펠러 효율/추진 확보
- Captain의 안전 운항 요구사항

**제약:**
```
Draft_AFT ≥ AFT_MIN_m
```

**기본값:** `CAPTAIN_AFT_MIN_DRAFT_M = 2.70 m` (Captain 요구사항 기준)

**Gate-A 정의 (SSOT - AGENTS.md 기준)**:
- `GATE_A_LABEL = "AFT_MIN_2p70"`: Gate-A 라벨 (모호한 "2.70m" 방지)
- **정의**: AFT draft ≥ 2.70m (비상 시 프로펠러 효율/추진 확보)
- **적용 범위**: 모든 Stage (universal gate)
- **ITTC 참고**: 승인 문서에는 **shaft centreline immersion** (프로펠러 직경 기준)을 보고해야 함
  - 최소: 1.5D, 권장: 2.0D (D = 프로펠러 직경)
  - 계산: `immersion_shaftCL = draft_at_prop - z_shaftCL`

**구현 (LP Solver):**
```python
# Limit Mode (≥를 ≤로 변환)
if aft_min is not None:
    row = np.zeros(len(var_names), dtype=float)
    row[:2*n] = -coef_daft  # Negative (부등호 반전)
    row[var_names.index("viol_aft")] = -1.0
    A_ub.append(row)
    b_ub.append(float(-(aft_min - daft0)))
```

### 5.4.4 Freeboard Gate (조위 무관)

**목적:**
- Green water (갑판 침수) 방지
- Deck clearance 보장

**제약:**
```
Freeboard ≥ FB_MIN
D_vessel - Draft ≥ FB_MIN
Draft ≤ D_vessel - FB_MIN
```

**기본값:** `FB_MIN = 0.0 m` (음수 방지, 실질적으로 Freeboard ≥ 0)

**중요**: Freeboard는 **조위와 무관**합니다. Tide는 UKC에만 영향을 주며, Freeboard에는 영향을 주지 않습니다. "Tide가 Freeboard를 해결한다"고 주장하지 말 것.

**구현 (LP Solver):**
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

### 5.4.5 UKC Gate (조위 의존)

**목적:**
- 해저 접촉 방지
- 충분한 선저 여유 수심 보장

**제약:**
```
UKC ≥ UKC_MIN
(DepthRef + Forecast_Tide) - (Draft_ref + Squat + Safety) ≥ UKC_MIN
Draft_ref ≤ (DepthRef + Forecast_Tide) - (Squat + Safety + UKC_MIN)
```

**기본값:** `UKC_MIN = 0.50 m` (프로젝트 기본값, Port/Vessel 요구사항 확인 필요)

**중요**: UKC는 **조위에 의존**합니다. Tide는 UKC에만 영향을 주며, Freeboard에는 영향을 주지 않습니다.

**Draft_ref 선택:**
- `UKC_Ref = "FWD"`: FWD Draft 기준
- `UKC_Ref = "AFT"`: AFT Draft 기준
- `UKC_Ref = "MEAN"`: 평균 Draft 기준
- `UKC_Ref = "MAX"` (기본값): FWD와 AFT 모두에 제약 (더 엄격)

**구현 (LP Solver):**
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

### 5.4.6 Gate Unified System의 의미

**Unified (통합)**: 모든 Gate를 **동시에 강제**합니다.

- 과거: 각 Gate를 독립적으로 검사
- 현재: LP Solver에서 모든 Gate를 **동시에 만족**하는 해를 찾음

**장점:**
- 서로 모순되는 Gate 요구사항 조기 발견
- 최적해가 모든 Gate를 동시에 만족
- Violation 값으로 각 Gate별 위반 정도 측정 가능

### 5.4.7 2.70m Split Gates (v2.1+)

파이프라인 v2.1부터 `gate_fail_report.md`에 2.70m 게이트를 두 개로 분리하여 보고합니다:

#### Gate-A (Captain): AFT_MIN_2p70 (SSOT - AGENTS.md 기준)

**목적:**
- 비상 시 프로펠러 효율/추진 확보
- Captain의 안전 운항 요구사항

**정의:**
```
GateA_AFT_MIN_2p70: AFT draft ≥ 2.70 m
```

**SSOT 정의 (AGENTS.md 기준)**:
- `CAPTAIN_AFT_MIN_DRAFT_M = 2.70`: Captain AFT 최소 Draft (m)
- `GATE_A_LABEL = "AFT_MIN_2p70"`: Gate-A 라벨 (모호한 "2.70m" 방지)
- **정의**: AFT draft ≥ 2.70m (비상 시 프로펠러 효율/추진 확보)
- **적용 범위**: 모든 Stage에 적용 (universal gate)
- **ITTC 참고**: 승인 문서에는 **shaft centreline immersion** (프로펠러 직경 기준)을 보고해야 함
  - 최소: 1.5D, 권장: 2.0D (D = 프로펠러 직경)
  - 계산: `immersion_shaftCL = draft_at_prop - z_shaftCL`

**구현:**
```python
df["GateA_AFT_MIN_2p70_PASS"] = df["new_aft_m"] >= 2.70
df["GateA_AFT_MIN_2p70_Margin_m"] = (df["new_aft_m"] - 2.70).round(2)
```

#### Gate-B (Mammoet): FWD_MAX_2p70_CD (SSOT - AGENTS.md 기준)

**목적:**
- Critical RoRo stages에서 Ramp 높이 제한
- Mammoet의 운영 제약 조건 (Chart Datum 기준)

**정의:**
```
GateB_FWD_MAX_2p70_CD: FWD draft ≤ 2.70 m (Chart Datum referenced)
```

**SSOT 정의 (AGENTS.md 기준)**:
- `MAMMOET_FWD_MAX_DRAFT_M_CD = 2.70`: Mammoet FWD 최대 Draft (Chart Datum 기준, m)
- `GATE_B_LABEL = "FWD_MAX_2p70_critical_only"`: Gate-B 라벨 (모호한 "2.70m" 방지)
- **정의**: FWD draft (Chart Datum) ≤ 2.70m, **Critical RoRo stages만** 적용
- **적용 범위**: Critical stages만 (`Gate_B_Applies=True`)
- **Critical Stage 정의**: `DEFAULT_CRITICAL_STAGE_REGEX = r"(preballast.*critical|6a.*critical|stage\s*5.*preballast|stage\s*6a)"`
- **Non-critical stages**: `Gate_FWD_MAX_2p70_critical_only = "N/A"` (false failure 방지)

**구현:**
```python
# Critical stage 판정
df["GateB_FWD_MAX_2p70_CD_applicable"] = df["Stage"].apply(
    lambda s: bool(re.search(DEFAULT_CRITICAL_STAGE_REGEX,
                              str(s), flags=re.IGNORECASE))
)

# PASS 판정 (applicable인 경우만 검사)
mask_app = df["GateB_FWD_MAX_2p70_CD_applicable"] == True
df.loc[mask_app, "GateB_FWD_MAX_2p70_CD_PASS"] = (
    df.loc[mask_app, "new_fwd_m"] <= 2.70
)
df["GateB_FWD_MAX_2p70_CD_Margin_m"] = (2.70 - df["new_fwd_m"]).round(2)
df.loc[~mask_app, "GateB_FWD_MAX_2p70_CD_Margin_m"] = None  # Non-critical은 NaN
```

**Split Gate의 의미:**
- 동일한 2.70m 임계값이지만, 목적과 적용 범위가 다름
- Gate-A: 선장의 안전 요구사항 (모든 Stage)
- Gate-B: 운영사의 제약 조건 (Critical stages만)
- 리포트에서 별도 집계하여 각 이해관계자의 요구사항을 명확히 구분

**Gate Labels SSOT (모호한 "2.70m" 방지)**:
- **절대 "2.70m"만 쓰지 말 것**. 항상 라벨 포함:
  - **Gate-A**: `AFT_MIN_2p70` (Captain / Propulsion)
  - **Gate-B**: `FWD_MAX_2p70_critical_only` (Mammoet / Critical RoRo only)

---

## 5.5 구현 상세

### 5.5.1 Stage QA CSV 생성

**위치:** `integrated_pipeline_defsplit_v2.py` (lines 347-466)

**함수:** `generate_stage_QA_csv`

**목적:**
- Definition-Split 개념을 CSV에 명시적으로 기록
- 각 Stage별 게이트 준수 여부 검증
- Forecast_Tide vs Required_WL_for_UKC 명확히 구분

**주요 계산:**

1. **Freeboard 계산 (조위 무관)**
   ```python
   freeboard_fwd = d_vessel_m - dfwd
   freeboard_aft = d_vessel_m - daft
   freeboard_min = min(freeboard_fwd, freeboard_aft)
   ```

2. **UKC 계산 (조위 의존)**
   ```python
   if depth_ref_m is not None and forecast_tide_m is not None:
       available_depth = depth_ref_m + forecast_tide_m
       ukc_fwd = available_depth - (dfwd + squat_m + safety_allow_m)
       ukc_aft = available_depth - (daft + squat_m + safety_allow_m)
       ukc_min = min(ukc_fwd, ukc_aft)
   ```

3. **Required_WL_for_UKC_m 역계산**
   ```python
   if ukc_min_m is not None:
       draft_ref_max = max(dfwd, daft)
       required_wl_for_ukc = (
           draft_ref_max + squat_m + safety_allow_m + ukc_min_m
       ) - depth_ref_m
       required_wl_for_ukc = max(required_wl_for_ukc, 0.0)  # 음수 방지
   ```

4. **Gate 검증**
   ```python
   gate_fwd_ok = dfwd <= fwd_max_m
   gate_aft_ok = daft >= aft_min_m
   gate_freeboard_ok = freeboard_min >= 0.0
   gate_ukc_ok = ukc_min >= ukc_min_m  # (if provided)
   ```

### 5.5.2 Helper 함수들

**위치:** `ballast_gate_solver_v4.py` (lines 264-302)

#### `pick_draft_ref_for_ukc`

UKC 계산 시 사용할 Draft 참조값 선택:

```python
def pick_draft_ref_for_ukc(ref: str, dfwd: float, daft: float) -> float:
    r = (ref or "MAX").upper().strip()
    if r == "FWD":
        return float(dfwd)
    if r == "AFT":
        return float(daft)
    if r == "MEAN":
        return float(0.5 * (dfwd + daft))
    return float(max(dfwd, daft))  # MAX (기본값)
```

#### `ukc_value`

UKC 값을 계산:

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

UKC_MIN을 만족하기 위한 요구 수면고 역계산:

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

최소 Freeboard 계산:

```python
def freeboard_min(d_vessel_m: Optional[float], dfwd: float, daft: float) -> float:
    if d_vessel_m is None:
        return float("nan")
    return float(min(d_vessel_m - dfwd, d_vessel_m - daft))
```

### 5.5.3 LP Solver에서의 Gate 구현

**위치:** `ballast_gate_solver_v4.py` (lines 479-546)

**Limit Mode 제약 조건 구성:**

1. FWD_MAX: `coef_dfwd^T · x - viol_fwd ≤ FWD_MAX - Dfwd0`
2. AFT_MIN: `-coef_daft^T · x - viol_aft ≤ -AFT_MIN + Daft0`
3. Freeboard: `coef_dfwd^T · x - viol_fb ≤ (D_vessel - FB_MIN) - Dfwd0` (FWD, AFT 각각)
4. UKC: `coef_draft_ref^T · x - viol_ukc ≤ draft_max - Draft0` (UKC_Ref에 따라)

**자세한 내용은 제4장 참조.**

---

## 5.6 QA CSV 출력 형식

### 5.6.1 컬럼 구조

**Definition-Split 컬럼:**

| Column | Type | Description |
|--------|------|-------------|
| `Forecast_Tide_m` | float | 예보 조위 (입력값) |
| `Required_WL_for_UKC_m` | float | UKC 만족을 위한 요구 수면고 (역계산) |
| `Freeboard_FWD_m` | float | FWD Freeboard (조위 무관) |
| `Freeboard_AFT_m` | float | AFT Freeboard (조위 무관) |
| `Freeboard_Min_m` | float | 최소 Freeboard |
| `UKC_FWD_m` | float | FWD UKC (조위 의존) |
| `UKC_AFT_m` | float | AFT UKC (조위 의존) |
| `UKC_Min_m` | float | 최소 UKC |

**Gate 검증 컬럼:**

| Column | Type | Description | Option 1 변경 |
|--------|------|-------------|---------------|
| `Current_FWD_m` | float | 현재 Forward Draft (입력값) | ⚠️ 제거 또는 `Draft_FWD_m`로 통일 |
| `Current_AFT_m` | float | 현재 AFT Draft (입력값) | ⚠️ 제거 또는 `Draft_AFT_m`로 통일 |
| `Draft_FWD_m` | float | Forward Draft (Solver 결과) | ✅ SSOT (Gate 판정 기준) |
| `Draft_AFT_m` | float | AFT Draft (Solver 결과) | ✅ SSOT (Gate 판정 기준) |

**Option 1 패치 제안: Current_* vs Draft_* 단일화**

**문제점:**
- `Current_*`와 `Draft_*` 값 불일치로 인한 SSOT 신뢰도 리스크
- Gate 판정 시 어떤 값을 사용해야 하는지 모호

**해결 방안 (Option 1):**
- `Current_*` 컬럼 제거 또는 `Draft_*`로 통일
- Gate 판정은 항상 `Draft_*` (Solver 결과) 기준으로 단일화

**Gate 검증 컬럼 (기존):**

| Column | Type | Values | Description |
|--------|------|--------|-------------|
| `Gate_FWD_Max` | string | "OK" / "NG" | FWD ≤ FWD_MAX |
| `Gate_AFT_Min` | string | "OK" / "NG" | AFT ≥ AFT_MIN |
| `Gate_Freeboard` | string | "OK" / "NG" | Freeboard ≥ 0 |
| `Gate_UKC` | string | "OK" / "NG" / "N/A" | UKC ≥ UKC_MIN (제공 시만) |
| `GateA_AFT_MIN_2p70_PASS` | bool | True / False | AFT ≥ 2.70m (Captain, 모든 Stage) |
| `GateB_FWD_MAX_2p70_CD_PASS` | bool | True / False | FWD ≤ 2.70m (Mammoet, Critical stages만) |
| `GateB_FWD_MAX_2p70_CD_applicable` | bool | True / False | Gate-B 적용 대상 여부 |

**Margin 컬럼:**

| Column | Type | Description |
|--------|------|-------------|
| `FWD_Margin_m` | float | `FWD_MAX_m - Current_FWD_m` (양수면 여유 있음) |
| `AFT_Margin_m` | float | `Current_AFT_m - AFT_MIN_m` (양수면 여유 있음) |
| `UKC_Margin_m` | float | `UKC_Min_m - UKC_Min_Required_m` (제공 시) |
| `GateA_AFT_MIN_2p70_Margin_m` | float | `Current_AFT_m - 2.70` (양수면 여유 있음) |
| `GateB_FWD_MAX_2p70_CD_Margin_m` | float | `2.70 - Current_FWD_m` (양수면 여유 있음, applicable인 경우만) |

### 5.6.2 예시 출력

```csv
Stage,Current_FWD_m,Current_AFT_m,Forecast_Tide_m,Required_WL_for_UKC_m,Freeboard_FWD_m,Freeboard_AFT_m,Freeboard_Min_m,UKC_FWD_m,UKC_AFT_m,UKC_Min_m,Gate_FWD_Max,Gate_AFT_Min,Gate_Freeboard,Gate_UKC,FWD_Margin_m,AFT_Margin_m
Stage_1,2.50,2.70,0.30,-1.00,1.15,0.95,0.95,2.00,1.80,1.80,OK,OK,OK,OK,0.20,0.00
Stage_6B,2.65,2.75,0.30,-0.85,1.00,0.90,0.90,1.85,1.75,1.75,OK,OK,OK,OK,0.05,-0.05
```

**Stage_6B 분석:**
- `AFT_Margin_m = -0.05`: AFT_MIN 게이트 위반 (NG)
- `Gate_AFT_Min = "NG"`로 표시됨
- `Required_WL_for_UKC_m = -0.85`: 음수이므로 0.0으로 클리핑 (이미 UKC_MIN 만족)

---

## 5.7 사용 예시

### 5.7.1 기본 실행 (Gate만)

```bash
python integrated_pipeline_defsplit_v2.py \
  --fwd_max 2.70 \
  --aft_min 2.70
```

- FWD_MAX, AFT_MIN 게이트만 활성화
- Freeboard, UKC는 계산하지 않음

### 5.7.2 UKC Gate 포함

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

- 모든 Gate 활성화
- UKC 계산 및 검증 수행
- Required_WL_for_UKC_m 역계산

### 5.7.3 QA CSV 확인

```python
import pandas as pd

qa_df = pd.read_csv("pipeline_out_.../ssot/pipeline_stage_QA.csv")

# Gate 위반 Stage 확인
violations = qa_df[
    (qa_df["Gate_FWD_Max"] == "NG") |
    (qa_df["Gate_AFT_Min"] == "NG") |
    (qa_df["Gate_Freeboard"] == "NG") |
    (qa_df["Gate_UKC"] == "NG")
]

print(violations[["Stage", "Gate_FWD_Max", "Gate_AFT_Min", "Gate_Freeboard", "Gate_UKC"]])
```

---

## 5.8 다음 장 안내

- **제6장**: 스크립트 인터페이스 및 API - 각 스크립트의 명령줄 인자 및 사용법

---

**참고:**
- 제1장: 파이프라인 아키텍처 개요
- 제2장: 데이터 흐름과 SSOT
- 제4장: LP Solver 로직
- `03_DOCUMENTATION/AGENTS.md`: 좌표계, Gate 정의, Tank Direction SSOT
- 2025-12-16 문서: Definition-Split 요구사항

**문서 버전:** v3.2 (AGENTS.md SSOT 통합)
**최종 업데이트:** 2025-12-27
