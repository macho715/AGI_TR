# 제9장: 파라미터 기반 자동 계산 시스템

**BUSHRA Ballast System - 파라미터만 변경하면 자동으로 결과를 계산하는 시스템**

**버전:** v3.2 (Updated: 2025-12-27)
**최신 업데이트 (v3.2 - 2025-12-27):**
- Coordinate system (Frame ↔ x) SSOT 명시 (섹션 9.1.3)
- Gate-A/Gate-B 라벨 SSOT 명확화 (섹션 9.7.4)
- Draft 계산 Method B (Lpp/LCF 기반) 강조 (섹션 9.7.3)

---

## 9.1 시스템 개요

### 9.1.1 목적

**문제:**
- 기존 메인 파이프라인은 파라미터 변경 시 **CSV/JSON 수정 → Python 재실행 → 결과 확인** (30초 소요)
- 현장에서 **빠른 의사결정**이 어려움

**해결:**
- **숫자만 입력하면 즉시 결과 표시** (<1초)
- 스크립트 수정 없이 **파라미터만 변경**
- 실시간 What-If 분석 가능

---

### 9.1.2 시스템 컨셉

```
┌─────────────────────────────────────────────────┐
│  📊 입력: 파라미터 시트 (사용자)                 │
│  ┌──────────────────────────────────────────┐   │
│  │  FWB2 Inventory:  [21.45] t             │   │
│  │  Cargo LCG:       [30.68] Fr            │   │
│  │  Tide:            [0.30] m              │   │
│  └──────────────────────────────────────────┘   │
│                      ▼                          │
│  ⚙️ 자동 계산 엔진 (Excel 수식 또는 Python)      │
│                      ▼                          │
│  📈 출력: 결과 대시보드 (자동 업데이트)           │
│  ┌──────────────────────────────────────────┐   │
│  │  Stage 6A AFT:  2.58 m  ❌ (-0.12m)     │   │
│  │  Stage 5 AFT:   2.70 m  ✅              │   │
│  │  Gate-A:        FAIL/PASS               │   │
│  └──────────────────────────────────────────┘   │
└─────────────────────────────────────────────────┘
```

### 9.1.3 Coordinate System SSOT (Frame ↔ x)

**Frame Convention:**
- Frame 0 = AP (AFT), Frame increases toward FP (FWD)
- Frame 30.151 = Midship → x = 0.0

**x Sign Convention:**
- AFT (stern) = x > 0
- FWD (bow) = x < 0

**Canonical Conversion:**
- `x = 30.151 - Fr`
- Example: TR1 at Fr.30.68 → x = 30.151 - 30.68 = -0.529m (slightly FWD of midship)

**Golden Rule:**
FWD tanks (FWB1/FWB2) have x < 0 and are in the bow zone. They cannot be used as "stern ballast" to raise AFT draft.

---

## 9.2 자주 변경되는 파라미터 (Priority)

### 🔴 **High Priority** (매 항차 변경)

| 카테고리 | 파라미터 | 범위 | 기본값 | 영향 |
|---------|---------|------|-------|------|
| **Forward Inventory** | FWB1.P/S | 0~50.57 t | 50.57 | Stage 5 AFT draft ⭐⭐⭐ |
| | FWB2.P/S | 0~109.98 t | 21.45 | Stage 5/6A AFT draft ⭐⭐⭐ |
| **Cargo Position** | TR1 LCG(AP) | 0~63.0 Fr | 30.68 | Trim/Draft 분포 ⭐⭐ |
| | TR2 LCG(AP) | 0~63.0 Fr | 30.46 | Trim/Draft 분포 ⭐⭐ |
| **Cargo Weight** | TR1 Weight | 0~500 t | 325.0 | Displacement ⭐⭐ |
| | TR2 Weight | 0~500 t | 304.0 | Displacement ⭐⭐ |

---

### 🟡 **Medium Priority** (조건 변경 시)

| 카테고리 | 파라미터 | 범위 | 기본값 | 영향 |
|---------|---------|------|-------|------|
| **Environment** | Forecast Tide | -0.5~2.0 m | 0.30 | Gate-B (FWD draft CD) ⭐⭐ |
| | Wave Hmax | 0.0~3.0 m | 0.30 | Gate-FB (Freeboard) ⭐ |
| **Gate Criteria** | AFT_MIN (Gate-A) | 2.5~2.8 m | 2.70 | 승인 기준 ⭐ |
| | FWD_MAX (Gate-B) | 2.5~2.8 m | 2.70 | 승인 기준 ⭐ |

---

### 🟢 **Low Priority** (거의 불변)

| 카테고리 | 파라미터 | 값 | 설명 |
|---------|---------|---|------|
| **Vessel Constants** | MCTC | 34.00 t·m/cm | Moment to change trim 1cm |
| | LCF | 0.76 m | Longitudinal center of flotation |
| | TPC | 8.00 t/cm | Tonnes per cm immersion |
| | Lpp | 60.302 m | Length between perpendiculars |
| | D_vessel | 3.65 m | Molded depth |

---

## 9.3 구현 방법 (3가지 옵션)

### **Option A: Excel 기반 시스템** (비추천)

**개념:**
- Excel 시트에 입력/계산/출력 모두 구현
- 수식으로 Draft/Trim 계산

**장점:**
- Python 설치 불필요
- 엔지니어가 쉽게 편집 가능

**단점:**
- ❌ **Hydro Table 조회 어려움** (VLOOKUP 한계)
- ❌ Excel 수식 복잡도 증가
- ❌ 유지보수 어려움 (수식 오류)
- ❌ 버전 관리 불가

**결론:** ❌ **실용성 낮음, 구현 중단**

---

### **Option B: Python 경량 계산기** (부분 채택)

**개념:**
- CLI 기반 Python 스크립트
- 파라미터를 인자로 전달 → 결과 출력

**예시:**
```bash
python quick_calculator.py \
    --fwb2_p 21.45 \
    --fwb2_s 21.45 \
    --tr1_lcg 30.68 \
    --tr2_lcg 30.46 \
    --tide 0.30

# 출력:
Stage 6A: AFT=2.58m, Gate-A=FAIL (-0.12m)
Stage 5:  AFT=2.70m, Gate-A=PASS
```

**장점:**
- ✅ 빠른 실행 (<1초)
- ✅ 스크립트 쉽게 변경 가능
- ✅ 자동화 스크립트 통합 가능

**단점:**
- 🟡 CLI 인터페이스 (비직관적)
- 🟡 시각화 없음

**결론:** 🟡 **보조 도구로 채택** (고급 사용자용)

---

### **Option C: Streamlit 웹 UI** ⭐ (최종 채택)

**개념:**
- Streamlit 기반 웹 인터페이스
- 슬라이더/입력박스로 파라미터 조작 → 실시간 결과 표시

**구현:**
- **bushra_ballast_system_v0_2** ✅ 구현 완료

**장점:**
- ✅ **직관적 UI** (슬라이더, 입력박스)
- ✅ **실시간 반응** (<1초)
- ✅ **시각화 내장** (Plotly 차트)
- ✅ **Scenario 비교** 자동 생성
- ✅ **History/Undo** 기능

**단점:**
- 🟡 Python 환경 필요 (설치 1회)

**결론:** ✅ **메인 시스템으로 채택**

---

## 9.4 bushra_ballast_system_v0_2 상세

### 9.4.1 시스템 아키텍처

```
bushra_ballast_system_v0_2/
├─ bushra_app.py              # Streamlit 웹 UI (459 lines)
│  ├─ Tab 1: Single Calculation (실시간 계산)
│  ├─ Tab 2: Scenario Comparison (3-scenario)
│  ├─ Tab 3: Optimization (FWB2 최적값 탐색)
│  └─ Tab 4: History (Undo/Rollback)
│
├─ calculator_engine.py       # 핵심 계산 엔진 (312 lines)
│  ├─ BallastParams (Pydantic v2 검증)
│  ├─ calculate_stage_6a()
│  ├─ calculate_stage_5()
│  └─ gate_validation()
│
├─ optimizer.py               # SciPy 최적화 (117 lines)
│  ├─ optimize_fwb2_single_stage()
│  └─ optimize_fwb2_multi_stage()
│
├─ excel_generator.py         # Excel 보고서 생성 (217 lines)
│  └─ 4-sheet 보고서 자동 생성
│
├─ config.yaml                # 시스템 파라미터 (SSOT)
├─ requirements.txt           # Python 의존성
├─ data/
│  ├─ tank_ssot.csv           # Tank SSOT
│  └─ hydro_table.csv         # Hydrostatic data
│
└─ output/
   └─ BUSHRA_Ballast_Report_*.xlsx
```

---

### 9.4.2 파라미터 입력 방식

#### **A. Sidebar (실시간 조작)**

**Streamlit 슬라이더/숫자 입력박스:**

```python
# bushra_app.py
st.sidebar.header("Forward Inventory")
fwb2_p = st.slider("FWB2.P (tonnes)", 0.0, 50.0, 21.45, 0.01)
fwb2_s = st.slider("FWB2.S (tonnes)", 0.0, 50.0, 21.45, 0.01)

st.sidebar.header("Cargo Position")
tr1_lcg = st.number_input("TR1 LCG(AP) (Frame)", 0.0, 63.0, 30.68, 0.01)

st.sidebar.header("Environment")
tide_m = st.slider("Forecast Tide (m)", -0.5, 2.0, 0.30, 0.01)
```

**사용자 경험:**
1. 슬라이더를 드래그하면 즉시 계산 시작
2. 결과가 메인 화면에 실시간 업데이트 (<1초)
3. 차트도 자동으로 다시 그려짐

---

#### **B. config.yaml (시스템 설정)**

**고정 파라미터 (Low Priority):**

```yaml
vessel:
  name: "BUSHRA"
  lpp_m: 60.302
  lcf_m_from_midship: 0.76
  frame_offset: 30.151

hydrostatics:
  mtc_t_m_per_cm: 34.00
  tpc_t_per_cm: 8.00

gates:
  aft_min_m: 2.70
  fwd_max_m_cd: 2.70
  trim_max_cm: 240.0
  freeboard_nd_target_m: 0.28

pumps:
  ship_rate_tph: 10.0
  hired_rate_tph: 100.0
```

**변경 방법:**
1. `config.yaml` 편집
2. Streamlit 앱 재시작 (`Ctrl+R`)

---

### 9.4.3 계산 엔진 (자동화 흐름)

**파라미터 변경 → 계산 → 결과 표시 (1초 이내)**

```python
# calculator_engine.py
def calculate_stage_6a(params: BallastParams, config: dict,
                       tank_ssot: pd.DataFrame, hydro_table: pd.DataFrame) -> dict:
    """
    Stage 6A (Critical RoRo) 계산 자동화

    입력: BallastParams (Pydantic 검증 완료)
    출력: dict (Draft, Trim, Gate 결과)
    """
    # 1. Displacement 계산
    disp_t = (
        params.fwb1_p + params.fwb1_s +
        params.fwb2_p + params.fwb2_s +
        params.tr1_weight_t + params.tr2_weight_t +
        config["lightship"]["weight_t"]
    )

    # 2. Hydro Table에서 Tmean 조회 (보간)
    tmean_m = np.interp(disp_t, hydro_table["Disp_t"], hydro_table["Draft_m"])

    # 3. Trimming Moment 계산 (LCF 기준)
    tm_lcf = 0.0
    for item in weight_items:
        x_i = frame_to_x(item["lcg_ap"], config["frame_offset"])
        tm_lcf += item["weight_t"] * (x_i - config["lcf_m_from_midship"])

    # 4. Trim 계산
    trim_m = tm_lcf / config["mtc_t_m_per_cm"] / 100.0

    # 5. Draft 계산 (Lpp/LCF 기반 물리식)
    Lpp = config["lpp_m"]
    LCF = config["lcf_m_from_midship"]
    slope = trim_m / Lpp

    x_fp = frame_to_x(63.0, config["frame_offset"])  # FP
    x_ap = frame_to_x(0.0, config["frame_offset"])   # AP

    dfwd_m = tmean_m + slope * (x_fp - LCF)
    daft_m = tmean_m + slope * (x_ap - LCF)

    # 6. Gate-B CD 변환
    dfwd_cd = dfwd_m - params.forecast_tide_m

    # 7. Gate 검증
    gate_a = daft_m >= config["gates"]["aft_min_m"]
    gate_b = dfwd_cd <= config["gates"]["fwd_max_m_cd"]

    # 8. 결과 반환
    return {
        "displacement_t": disp_t,
        "tmean_m": tmean_m,
        "dfwd_m": dfwd_m,
        "dfwd_cd": dfwd_cd,
        "daft_m": daft_m,
        "trim_cm": trim_m * 100.0,
        "gate_a_pass": gate_a,
        "gate_b_pass": gate_b,
        # ... 기타 결과
    }
```

---

### 9.4.4 Scenario 비교 (자동 생성)

**Tab 2: Scenario Comparison**

**사용자가 "Set from current" 버튼 클릭 → 자동으로 3개 시나리오 생성:**

```python
# bushra_app.py
baseline_fwb2 = st.session_state.fwb2_p

scenarios = {
    "Conservative": baseline_fwb2 * 0.9,  # -10%
    "Baseline":     baseline_fwb2 * 1.0,
    "Aggressive":   baseline_fwb2 * 1.1,  # +10%
}

results = []
for name, fwb2_val in scenarios.items():
    # 파라미터 복사 후 FWB2만 변경
    params_copy = params.model_copy()
    params_copy.fwb2_p = fwb2_val
    params_copy.fwb2_s = fwb2_val

    # 계산 실행
    result = calculate_stage_6a(params_copy, config, tank_ssot, hydro_table)
    results.append({"Scenario": name, "FWB2": fwb2_val, **result})

# 표와 차트로 표시
df_scenarios = pd.DataFrame(results)
st.dataframe(df_scenarios)
fig = px.bar(df_scenarios, x="Scenario", y=["S6A_AFT", "S5_AFT"])
st.plotly_chart(fig)
```

**실행 시간:** ~0.9초 (3개 계산 + 차트 생성)

---

### 9.4.5 최적화 (자동 FWB2 탐색)

**Tab 3: Optimization**

**목표:** 주어진 AFT draft target (예: 2.70m)을 달성하는 FWB2 최적값 자동 탐색

```python
# optimizer.py
from scipy.optimize import minimize_scalar

def optimize_fwb2_single_stage(
    target_aft_m: float,
    stage: str,  # "6A" or "5"
    params: BallastParams,
    config: dict,
    ...
) -> dict:
    """
    SciPy로 FWB2 최적값 탐색

    Objective: |AFT_draft - target|²
    Bounds: [10.0, 50.0] tonnes
    """
    def objective(fwb2_val):
        params_temp = params.model_copy()
        params_temp.fwb2_p = fwb2_val
        params_temp.fwb2_s = fwb2_val

        if stage == "6A":
            result = calculate_stage_6a(params_temp, config, ...)
        else:
            result = calculate_stage_5(params_temp, config, ...)

        aft_draft = result["daft_m"]
        error = (aft_draft - target_aft_m) ** 2
        return error

    # Brent method (derivative-free optimization)
    res = minimize_scalar(objective, bounds=(10.0, 50.0), method="bounded")

    return {
        "success": res.success,
        "optimal_fwb2": res.x,
        "final_aft_m": sqrt(res.fun) + target_aft_m,  # back-calculate
        "iterations": res.nit
    }
```

**실행 시간:** ~2.5초 (12회 반복)

---

### 9.4.6 History & Undo (Session State)

**Tab 4: History**

**스냅샷 저장:**

```python
# bushra_app.py
def _push_history(label: str):
    snapshot = {
        "ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "label": label,
        "params": {
            "fwb2_p": st.session_state.fwb2_p,
            "fwb2_s": st.session_state.fwb2_s,
            "tr1_lcg_ap": st.session_state.tr1_lcg_ap,
            # ... 모든 파라미터
        }
    }
    st.session_state.history.append(snapshot)

    # 최대 20개 유지
    if len(st.session_state.history) > 20:
        st.session_state.history.pop(0)
```

**Undo (복원):**

```python
def _undo():
    if len(st.session_state.history) > 0:
        last_snapshot = st.session_state.history.pop()

        # 모든 파라미터 복원
        for key, val in last_snapshot["params"].items():
            st.session_state[key] = val

        st.success(f"Restored: {last_snapshot['label']}")
```

**사용 시나리오:**
1. 초기값 → Save Snapshot
2. FWB2 변경 → Save Snapshot
3. 결과 나쁨 → Undo → 이전 값 복원

---

## 9.5 파라미터 변경 시나리오 (실무 예시)

### **시나리오 1: FWB2 inventory 결정**

**문제:** "Stage 5 AFT draft 2.70m를 달성하려면 FWB2를 얼마나 채워야 하나?"

**절차:**
1. Streamlit 앱 실행
2. Tab 3 (Optimization) 이동
3. Target Stage: `Stage 5`
4. AFT Draft Target: `2.70m`
5. "Find optimal FWB2" 클릭
6. 결과: `FWB2.P/S = 21.45 tonnes`
7. Tab 1으로 복귀 → 슬라이더에 21.45 입력
8. Stage 5 AFT = 2.70m 확인 ✅

**소요 시간:** 1분

---

### **시나리오 2: Tide 변경 영향 분석**

**문제:** "조위가 0.30m → 0.50m로 증가하면 Gate-B는?"

**절차:**
1. Tab 1, Sidebar: Forecast Tide 슬라이더를 0.50으로 조정
2. 결과 즉시 업데이트 (<1초)
   - Draft_FWD(CD): 2.02m → 1.82m
   - Gate-B 여유: 0.68m → 0.88m (개선)
3. "Tide 증가 → FWD draft(CD) 감소 → Gate-B 여유 증가" 확인
4. Tab 4 (History) → Save Snapshot

**소요 시간:** 30초

---

### **시나리오 3: 화물 위치 변경 시뮬레이션**

**문제:** "TR1을 Frame 30.68 → 35.00 (AFT 방향)으로 이동하면?"

**절차:**
1. Tab 1, Sidebar: TR1 LCG(AP)를 35.00으로 변경
2. 결과 즉시 계산:
   - Stage 6A AFT: 2.58m → 2.64m (+0.06m)
   - Gate-A: 여전히 FAIL (0.06m 부족)
3. Tab 2 (Scenario) → "Set from current" 클릭
4. 3개 시나리오 자동 비교
5. 결론: "TR1 shift만으로는 부족, FWB2 inventory 증가 필요"

**소요 시간:** 1분

---

### **시나리오 4: 다중 Stage 최적화**

**문제:** "Stage 5와 Stage 6A를 모두 만족하는 FWB2는?"

**절차:**
1. Tab 3 (Optimization) 이동
2. "Find optimal FWB2 (Stage 5 + 6A)" 버튼 클릭
3. 결과 (7초 소요):
   ```
   Optimal FWB2.P/S: 21.45t

   Stage 5: AFT=2.70m ✅ (Priority 1 satisfied)
   Stage 6A: AFT=2.58m ❌ (0.12m short)

   Trade-off: Stage 5 우선, Stage 6A는 discharge 필요
   Discharge: 42.90t (4.29 hours @ 10 t/h)
   ```
4. 의사결정: "Stage 5 PASS 우선, Stage 6A는 현장 discharge로 해결"

---

## 9.6 vs 메인 파이프라인 역할 분담

### 9.6.1 시스템 선택 기준

| 작업 유형 | BUSHRA v0.2 | 메인 파이프라인 |
|----------|------------|---------------|
| **현장 의사결정** | ✅ 권장 (<1초) | ❌ 느림 (30초) |
| **What-If 분석** | ✅ 권장 (실시간) | ❌ CSV 수정 필요 |
| **파라미터 변경 실험** | ✅ 권장 (슬라이더) | ❌ 스크립트 재실행 |
| **최종 승인 보고서** | ❌ 4-sheet만 | ✅ 28-sheet 완전 |
| **전체 Stage 분석** | ❌ Stage 5/6A만 | ✅ 모든 Stage |
| **DNV Mitigation 문서** | ❌ 없음 | ✅ 자동 생성 |
| **LP Solver 완전 최적화** | ❌ SciPy 간소화 | ✅ PuLP 완전 |

---

### 9.6.2 통합 워크플로우 (권장)

```
Phase 1: 초기 설계 (BUSHRA v0.2)
├─ FWB2 최적값 탐색 (2초)
├─ Scenario 비교 (1초)
├─ 파라미터 확정
└─ History 저장

         ▼

Phase 2: 검증 (메인 파이프라인)
├─ sensors/current_t_sensor.csv 업데이트
├─ 전체 파이프라인 실행 (30초)
└─ 모든 Stage/Gate 검증

         ▼

Phase 3: 승인 (메인 파이프라인)
├─ DNV Mitigation 문서 생성
├─ 28-sheet Excel 보고서 생성
└─ Captain/Mammoet 승인

         ▼

Phase 4: 현장 운영 (BUSHRA v0.2)
├─ 실시간 조위 반영
├─ 긴급 What-If 분석
└─ 파라미터 미세 조정
```

---

## 9.7 기술 상세

### 9.7.1 Pydantic v2 파라미터 검증

**자동 범위 검증:**

```python
from pydantic import BaseModel, field_validator

class BallastParams(BaseModel):
    fwb2_p: float
    fwb2_s: float
    tr1_lcg_ap: float
    # ...

    @field_validator('fwb2_p', 'fwb2_s')
    @classmethod
    def check_fwb2_range(cls, v: float) -> float:
        if not (0.0 <= v <= 50.0):
            raise ValueError(f"FWB2 must be in [0, 50], got {v}")
        return v

    @field_validator('tr1_lcg_ap', 'tr2_lcg_ap')
    @classmethod
    def check_frame_range(cls, v: float) -> float:
        if not (0.0 <= v <= 63.0):
            raise ValueError(f"Frame must be in [0, 63], got {v}")
        return v
```

**장점:**
- 잘못된 입력 시 즉시 에러 발생
- 타입 체크 자동 (float, int, str)
- IDE 자동완성 지원

---

### 9.7.2 Hydro Table 보간 (numpy.interp)

**문제:** Hydro table은 이산적 (10t 간격 등), 실제 Displacement는 연속적

**해결:** 선형 보간

```python
import numpy as np

# Hydro Table (예시)
hydro_table = pd.DataFrame({
    "Disp_t": [800, 900, 1000, 1100, 1200],
    "Draft_m": [1.80, 2.00, 2.20, 2.40, 2.60]
})

# 실제 Displacement = 1050t
disp_actual = 1050.0

# 보간으로 Draft 계산
tmean_m = np.interp(
    x=disp_actual,                      # 찾을 값
    xp=hydro_table["Disp_t"],           # x 좌표
    fp=hydro_table["Draft_m"]           # y 좌표
)

# 결과: tmean_m = 2.30m (1000t와 1100t 사이 선형 보간)
```

---

### 9.7.3 Draft 계산 (Lpp/LCF 기반 물리식)

**기존 문제 (v0.1):** 단순 Trim/200 분배

**개선 (v0.2):** 물리적 정확 계산

```python
# 파라미터
Lpp_m = 60.302       # 선간장
LCF = 0.76           # LCF (midship 기준 +0.76m = AFT 방향)
trim_m = 0.26        # Trim (+ = stern down)

# Frame → x 변환
x_fp = 30.151 - 63.0 = -32.849  # FP (선수)
x_ap = 30.151 - 0.0 = +30.151   # AP (선미)

# Slope (m/m)
slope = trim_m / Lpp_m = 0.26 / 60.302 = 0.00431

# Draft at any x
draft_at_x = tmean_m + slope × (x - LCF)

# FWD/AFT Draft
dfwd_m = tmean_m + slope × (x_fp - LCF)
       = 2.45 + 0.00431 × (-32.849 - 0.76)
       = 2.45 + 0.00431 × (-33.609)
       = 2.45 - 0.145
       = 2.305 m

daft_m = tmean_m + slope × (x_ap - LCF)
       = 2.45 + 0.00431 × (30.151 - 0.76)
       = 2.45 + 0.00431 × 29.391
       = 2.45 + 0.127
       = 2.577 m
```

**장점:**
- Lpp 변경 시 자동 반영
- LCF 위치 변경 시 자동 반영
- 임의의 x 위치 draft 계산 가능

---

### 9.7.4 Gate 정의 및 Chart Datum 변환 (SSOT)

#### **Gate-A (Captain / Propulsion)**

**Gate Label:** `AFT_MIN_2p70`

**Definition:**
- AFT draft ≥ 2.70m (MSL) at defined "propulsion-relevant" stages
- **ITTC note:** Approval docs must report **shaft centreline immersion** (1.5D min, 2.0D recommended)

**BUSHRA System 적용:**
```python
gate_a_pass = daft_m >= config["gates"]["aft_min_m"]  # 2.70m
```

#### **Gate-B (Mammoet / Critical RoRo Only)**

**Gate Label:** `FWD_MAX_2p70_critical_only`

**Definition:**
- FWD draft (Chart Datum) ≤ 2.70m during **critical RoRo stages only**
- Critical stage list must be explicit (no regex guessing)

**MSL vs CD 차이:**

**물리적 관계:**

```
MSL (평균 해수면)
  ↕ Tide (조위, 예: +0.30m)
CD (해도 기준면, 최저 저조면)
```

**변환:**

```python
Draft_FWD_MSL = 2.32 m  # 계산 결과
Forecast_Tide = 0.30 m  # 예보 조위

Draft_FWD_CD = Draft_FWD_MSL - Forecast_Tide
             = 2.32 - 0.30
             = 2.02 m

# Gate-B 검증 (CD 기준)
FWD_MAX_CD = 2.70 m
Gate_B_PASS = (Draft_FWD_CD <= FWD_MAX_CD)
            = (2.02 <= 2.70)
            = True ✅
```

**왜 CD를 써야 하나?**
- RoRo ramp 높이는 고정 (조위 무관)
- Tide가 높으면 선박이 떠올라 ramp 간극 감소
- CD 기준 관리 → 안전 보장

**Important:** Never write "2.70m" alone. Always use the labels `AFT_MIN_2p70` or `FWD_MAX_2p70_critical_only` to prevent ambiguity.

---

## 9.8 제약사항 및 확장 계획

### 9.8.1 현재 제약사항

| 제약 | 설명 | 해결 방법 |
|------|------|----------|
| **Stage 제한** | Stage 5/6A만 지원 | 메인 파이프라인 사용 |
| **LP Solver 간소화** | SciPy만 사용 | 복잡한 최적화는 메인 파이프라인 |
| **Heel 계산 없음** | 좌우 경사 미계산 | FWB2.P = FWB2.S 대칭 유지 |
| **Windows COM 의존** | Excel 수식 재계산 | Linux/Mac은 수동 F9 |
| **Local 실행만** | 다중 사용자 불가 | Streamlit Cloud 배포 필요 |

---

### 9.8.2 향후 확장 계획

| 기능 | 우선순위 | 예상 작업량 | 상태 |
|------|---------|------------|------|
| **Stage 6B/7 추가** | 중 | 2일 | 계획 중 |
| **UKC 계산 통합** | 중 | 1일 | 계획 중 |
| **Heel(경사) 계산** | 중 | 3일 | 계획 중 |
| **다중 사용자 (Cloud)** | 낮 | 3일 | 미정 |
| **Database 연동** | 낮 | 5일 | 미정 |
| **Mobile UI 최적화** | 낮 | 2일 | 미정 |

---

## 9.9 요약

### 9.9.1 핵심 개념

**"파라미터만 변경하면 자동 계산"** = **bushra_ballast_system_v0_2**

- ✅ Streamlit 웹 UI (슬라이더/입력박스)
- ✅ 실시간 반응 (<1초)
- ✅ Pydantic v2 자동 검증
- ✅ Scenario 비교 (3-scenario)
- ✅ SciPy 최적화 (FWB2 탐색)
- ✅ History & Undo (20개 스냅샷)
- ✅ Excel 보고서 자동 생성

---

### 9.9.2 사용 시나리오

| 상황 | 추천 도구 | 소요 시간 |
|------|---------|----------|
| **현장 의사결정** | BUSHRA v0.2 | <1분 |
| **What-If 분석** | BUSHRA v0.2 | <1분 |
| **최종 승인** | 메인 파이프라인 | ~5분 |
| **전체 Stage 검증** | 메인 파이프라인 | ~5분 |

---

### 9.9.3 Quick Reference

**시작:**
```bash
cd bushra_ballast_system_v0_2
streamlit run bushra_app.py
```

**파라미터 변경:**
- FWB2 inventory → Stage 5/6A AFT draft
- Tide → Gate-B (FWD draft CD)
- TR1/TR2 Position → Trim/Draft 분포

**최적화:**
- Tab 3 → "Find optimal FWB2" → 2초

**문서:**
- 사용 가이드: `docs/08_Bushra_System_User_Guide.md`
- SSOT: `AGENTS.md`

---

**마지막 업데이트:** 2025-12-27
**문서 버전:** 1.1
**시스템 버전:** BUSHRA Ballast System v0.2

**최신 업데이트 (v1.1 - 2025-12-27):**
- 문서 버전 업데이트 (메인 파이프라인 v3.1과 일관성 유지)

