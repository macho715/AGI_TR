# 제8장: BUSHRA Ballast System 사용자 가이드

**BUSHRA Ballast Management System v0.2 - 실시간 파라미터 기반 자동 계산 시스템**

**버전:** v3.3 (Updated: 2025-12-28)
**최신 업데이트 (v3.3 - 2025-12-28):**
- Option 1/2 패치 맥락 추가 (메인 파이프라인 관련)
  - Option 1: Bryan Pack Forecast_tide_m 주입, Stage 5_PreBallast critical 적용
  - Option 2: BALLAST_SEQUENCE 옵션/실행 분리, Start_t/Target_t carry-forward

**최신 업데이트 (v3.2 - 2025-12-27):**
- Coordinate system (Frame ↔ x) SSOT 명시 (섹션 8.1.3)
- Gate-A/Gate-B 라벨 SSOT 명확화 (섹션 8.4.4)
- Draft vs Freeboard vs UKC 구분 명확화 (섹션 8.4.4)

---

## 8.1 시스템 개요

### 8.1.1 BUSHRA System이란?

**BUSHRA Ballast System**은 기존 메인 파이프라인(`integrated_pipeline_defsplit_v2_gate270_split_v3.py`)을 **경량화·실시간화**한 **파라미터 기반 자동 계산 시스템**입니다.

**핵심 차이점:**

| 항목 | 메인 파이프라인 | BUSHRA System v0.2 |
|------|----------------|-------------------|
| **실행 방식** | CLI 배치 실행 (Python 스크립트) | 웹 UI 실시간 (Streamlit) |
| **파라미터 변경** | CSV/JSON 수정 필요 | 슬라이더/입력박스 직접 조작 |
| **계산 속도** | ~30초 (전체 파이프라인) | **<1초** (실시간 응답) |
| **LP Solver** | PuLP 완전 최적화 | SciPy 간소화 최적화 |
| **Excel 생성** | 28-sheet 통합 보고서 | 4-sheet 핵심 요약 보고서 |
| **사용 대상** | 최종 승인용 공식 보고서 | **현장 의사결정·What-if 분석** |

---

### 8.1.2 v0.1 → v0.2 주요 개선사항

| 기능 | v0.1 | v0.2 (현재) |
|------|------|------------|
| **Draft 계산** | 단순 Trim/200 분배 | **Lpp/LCF 기반 물리식** ✅ |
| **Gate-B 기준** | MSL 불명확 | **Chart Datum 명시** ✅ |
| **Pydantic** | v1 API (`@validator`) | **v2 API (`@field_validator`)** ✅ |
| **Excel 수식** | 캐싱 문제 | **COM 강제 재계산** ✅ |
| **시나리오 비교** | 없음 | **3개 시나리오 자동 비교** ✅ |
| **Undo/History** | 없음 | **20개 스냅샷 저장/복원** ✅ |
| **다중 Stage 최적화** | 단일 Stage만 | **Stage 5+6A 동시 최적화** ✅ |
| **단위 테스트** | 없음 | **pytest 194 lines** ✅ |

### 8.1.3 Coordinate System SSOT (Frame ↔ x)

**Frame Convention:**
- Frame 0 = AP (AFT), Frame increases toward FP (FWD)
- Frame 30.151 = Midship → x = 0.0

**x Sign Convention:**
- AFT (stern) = x > 0
- FWD (bow) = x < 0

**Canonical Conversion:**
- `x = 30.151 - Fr`
- Example: FWB2 at Fr.50 → x = 30.151 - 50 = -19.849m (FWD zone)

**Golden Rule:**
FWD tanks (FWB1/FWB2) have x < 0 and are in the bow zone. They cannot be used as "stern ballast" to raise AFT draft.

---

## 8.2 시스템 아키텍처

### 8.2.1 파일 구조

```
bushra_ballast_system_v0_2/
├─ bushra_app.py              # Streamlit 웹 UI (459 lines)
│  ├─ Tab 1: Single Calculation
│  ├─ Tab 2: Scenario Comparison
│  ├─ Tab 3: Optimization
│  └─ Tab 4: History
│
├─ calculator_engine.py       # 핵심 계산 엔진 (312 lines)
│  ├─ BallastParams (Pydantic v2)
│  ├─ calculate_stage_6a()
│  ├─ calculate_stage_5()
│  └─ gate_validation()
│
├─ optimizer.py               # SciPy 최적화 (117 lines)
│  ├─ optimize_fwb2_single_stage()
│  └─ optimize_fwb2_multi_stage()
│
├─ excel_generator.py         # Excel 보고서 생성 (217 lines)
│  └─ ExcelReportGenerator.generate()
│
├─ excel_com_utils.py         # Windows COM 유틸 (79 lines)
│  └─ excel_com_recalc_save()  # 수식 강제 재계산
│
├─ config.yaml                # 시스템 설정
├─ requirements.txt           # Python 의존성
├─ pytest.ini                 # 테스트 설정
├─ data/
│  ├─ tank_ssot.csv           # Tank SSOT
│  └─ hydro_table.csv         # Hydrostatic 데이터
│
├─ tests/
│  ├─ test_calculator_engine.py  # 계산 엔진 테스트
│  └─ test_optimizer.py          # 최적화 테스트
│
└─ output/
   └─ BUSHRA_Ballast_Report_*.xlsx  # 생성된 Excel 보고서
```

---

### 8.2.2 데이터 흐름

```
┌─────────────────────────────────────────────────┐
│  1. 사용자 입력 (Streamlit UI)                   │
│     • FWB1/FWB2 Inventory (tonnes)               │
│     • TR1/TR2 Position & Weight                  │
│     • Tide, Wave Height                          │
└──────────────────┬──────────────────────────────┘
                   ▼
┌─────────────────────────────────────────────────┐
│  2. Pydantic v2 검증 (BallastParams)             │
│     • 용량 범위 검증 (0~50t)                      │
│     • 타입 검증 (float)                           │
│     • 필수 필드 검증                              │
└──────────────────┬──────────────────────────────┘
                   ▼
┌─────────────────────────────────────────────────┐
│  3. 계산 엔진 (calculator_engine.py)             │
│     A. Displacement 계산                         │
│        disp_t = Σ(FWB1+FWB2+TR1+TR2+Lightship)  │
│     B. Tmean 조회 (hydro_table.csv)              │
│     C. TM_LCF 계산                               │
│        TM_LCF = Σ(w_i × (x_i - LCF))            │
│     D. Trim 계산                                 │
│        trim_m = TM_LCF / MCTC                    │
│     E. Draft 계산 (Lpp/LCF 기반)                 │
│        slope = trim_m / Lpp_m                    │
│        dfwd = tmean + slope × (x_fp - LCF)       │
│        daft = tmean + slope × (x_ap - LCF)       │
│     F. Gate-B CD 변환                            │
│        dfwd_cd = dfwd_m - tide_m                 │
│     G. Gate 검증                                 │
│        Gate-A: daft ≥ 2.70m (MSL)                │
│        Gate-B: dfwd_cd ≤ 2.70m (CD)              │
│        Gate-FB: freeboard ≥ 0.28m                │
│        Gate-TRIM: |trim| ≤ 240cm                 │
└──────────────────┬──────────────────────────────┘
                   ▼
┌─────────────────────────────────────────────────┐
│  4. 결과 출력 (Streamlit / Excel)                │
│     • 표: Stage 6A/5 결과                        │
│     • 차트: Draft 비교 (Plotly)                  │
│     • Excel: 4-sheet 보고서                      │
└─────────────────────────────────────────────────┘
```

---

## 8.3 사용 가이드

### 8.3.1 설치 및 실행

**1단계: 의존성 설치**

```bash
cd bushra_ballast_system_v0_2
pip install -r requirements.txt
```

**필수 라이브러리:**
- `streamlit` 1.32+
- `pandas` 2.0+
- `pydantic` 2.0+
- `scipy` 1.11+
- `openpyxl` 3.1+
- `plotly` 5.18+
- `pyyaml` 6.0+
- `pywin32` (Windows only, Excel COM용)

---

**2단계: Streamlit 실행**

```bash
streamlit run bushra_app.py
```

**실행 결과:**
```
You can now view your Streamlit app in your browser.

Local URL: http://localhost:8501
Network URL: http://192.168.x.x:8501
```

브라우저가 자동으로 열립니다. 열리지 않으면 URL을 직접 입력하세요.

---

### 8.3.2 Tab 1: Single Calculation (단일 계산)

**목적:** Stage 6A와 Stage 5의 Draft/Trim/Gate를 **실시간**으로 계산합니다.

#### **입력 파라미터 (Sidebar)**

**A. Forward Inventory (tonnes)**
- `FWB1.P` (Port): 0.0 ~ 50.57 (기본값: 50.57)
- `FWB1.S` (Starboard): 0.0 ~ 50.57 (기본값: 50.57)
- `FWB2.P`: 0.0 ~ 50.0 (기본값: 21.45) ⭐ **핵심 조정 변수**
- `FWB2.S`: 0.0 ~ 50.0 (기본값: 21.45)

**B. Cargo Position (Frame Number)**
- `TR1 LCG(AP)`: 0.0 ~ 63.0 (기본값: 30.68)
- `TR2 LCG(AP)`: 0.0 ~ 63.0 (기본값: 30.46)

**C. Cargo Weight (tonnes)**
- `TR1 Weight`: 0.0 ~ 500.0 (기본값: 325.0)
- `TR2 Weight`: 0.0 ~ 500.0 (기본값: 304.0)

**D. Environment**
- `Forecast Tide`: -2.0 ~ 2.0 (기본값: 0.30) ⭐ **Gate-B CD 영향**
- `Wave Height Hmax`: 0.0 ~ 3.0 (기본값: 0.30)

---

#### **출력 결과 (Main Area)**

**1. Stage 6A 결과 (Critical RoRo)**

| 항목 | 값 예시 | 단위 | 설명 |
|------|--------|------|------|
| Displacement | 1,230.25 | tonnes | 총 배수량 |
| Tmean | 2.45 | m | 평균 Draft (MSL) |
| Draft FWD (MSL) | 2.32 | m | 선수 Draft (평균 해수면) |
| Draft FWD (CD) | 2.02 | m | 선수 Draft (Chart Datum) ⭐ |
| Draft AFT | 2.58 | m | 선미 Draft |
| Trim | 26.00 | cm | Trim (+ = stern down) |
| Freeboard (ND) | 1.37 | m | 유효 Freeboard |
| **Gate-A** | ❌ FAIL | - | AFT ≥ 2.70m (0.12m 부족) |
| **Gate-B** | ✅ PASS | - | FWD(CD) ≤ 2.70m (0.68m 여유) |
| **Gate-FB** | ✅ PASS | - | Freeboard ≥ 0.28m (1.09m 여유) |
| **Gate-TRIM** | ✅ PASS | - | \|Trim\| ≤ 240cm (214cm 여유) |

**2. Stage 5 결과 (Pre-Ballast)**

(동일 형식, 다른 값)

**3. Draft Comparison Chart (Plotly)**
- X축: Stage (6A, 5)
- Y축: Draft (m)
- 3개 바: FWD(MSL), FWD(CD), AFT
- Color: Gate 통과 여부 (녹색/빨간색)

**4. Excel 보고서 생성**
- 버튼 클릭: "Generate Excel Report"
- 저장 경로: `output/BUSHRA_Ballast_Report_YYYYMMdd_HHmmss.xlsx`

---

### 8.3.3 Tab 2: Scenario Comparison (시나리오 비교)

**목적:** FWB2 inventory를 3가지 시나리오로 자동 비교합니다.

#### **사용 방법**

**1단계: 기준값 설정**
- Tab 1에서 원하는 파라미터 설정
- Tab 2로 이동
- "Set from current" 버튼 클릭

**2단계: 자동 시나리오 생성**

시스템이 자동으로 3개 시나리오를 생성합니다:

| 시나리오 | FWB2.P/S | 설명 |
|---------|---------|------|
| **Conservative** | 기준값 × 0.9 | 안전 여유 확보 (AFT draft 낮음) |
| **Baseline** | 기준값 × 1.0 | 현재 설정값 |
| **Aggressive** | 기준값 × 1.1 | 최대 AFT draft 확보 |

**3단계: 결과 확인**

**A. 비교 표 (Comparison Table)**

| Scenario | FWB2.P | FWB2.S | S6A AFT | S6A Gate-A | S5 AFT | S5 Gate-A |
|----------|--------|--------|---------|------------|--------|-----------|
| Conservative | 19.31 | 19.31 | 2.56 | ❌ FAIL | 2.68 | ❌ FAIL |
| Baseline | 21.45 | 21.45 | 2.58 | ❌ FAIL | 2.70 | ✅ PASS |
| Aggressive | 23.60 | 23.60 | 2.61 | ❌ FAIL | 2.72 | ✅ PASS |

**B. 비교 차트 (Bar Chart)**
- X축: 3개 시나리오
- Y축: AFT Draft (m)
- 2개 바: Stage 6A, Stage 5
- 기준선: 2.70m (Gate-A 목표)

**의사결정 지원:**
- Conservative가 모두 FAIL → FWB2 inventory 부족
- Aggressive가 PASS → FWB2 inventory 충분
- Baseline이 경계선 → 최적 지점 근처

---

### 8.3.4 Tab 3: Optimization (최적화)

**목적:** 주어진 AFT draft 목표를 달성하는 **최적 FWB2 inventory**를 자동 탐색합니다.

#### **A. Single-Stage Optimization (단일 Stage 최적화)**

**1단계: 파라미터 설정**
- Target Stage: `Stage 6A` 또는 `Stage 5` 선택
- AFT Draft Target: 2.70m (기본값, 조정 가능)

**2단계: 최적화 실행**
- "Find optimal FWB2" 버튼 클릭

**3단계: 결과 확인**
```
Optimization Result:
✅ SUCCESS

Optimal FWB2.P: 21.45 tonnes
Optimal FWB2.S: 21.45 tonnes

Achieved AFT Draft: 2.70m (Target: 2.70m)
Gate-A: ✅ PASS

Solver Details:
- Search Range: [10.0, 50.0] tonnes
- Iterations: 12
- Convergence: 0.0001m tolerance
- Execution Time: 2.3 seconds
```

**알고리즘:**
- SciPy `minimize_scalar` (Brent method)
- Objective: `|AFT_draft - target|²`
- Bounds: [10.0, 50.0] tonnes
- Symmetry: FWB2.P = FWB2.S (heel 방지)

---

#### **B. Multi-Stage Optimization (다중 Stage 최적화)**

**목적:** Stage 5와 Stage 6A를 **동시에 만족**하는 FWB2 inventory 탐색

**사용 시나리오:**
- Stage 5 AFT ≥ 2.70m (우선순위 1)
- Stage 6A AFT ≥ 2.70m (우선순위 2)
- Discharge time 최소화 (우선순위 3)

**실행:**
- "Find optimal FWB2 (Stage 5 + 6A)" 버튼 클릭

**결과:**
```
Multi-Stage Optimization Result:
✅ SUCCESS

Optimal FWB2.P: 21.45 tonnes
Optimal FWB2.S: 21.45 tonnes

Stage 5:
- AFT Draft: 2.70m ✅
- Gate-A: PASS
- Discharge: 0.00t (no discharge needed)

Stage 6A:
- AFT Draft: 2.58m ❌ (0.12m short)
- Gate-A: FAIL
- Discharge from FWB2: 21.45t × 2 = 42.90t
- Discharge Time: 4.29 hours (ship pump @ 10 t/h)

Trade-off Analysis:
Stage 5 prioritized over Stage 6A.
Consider:
1. Increase FWB2 further (risky, capacity limit)
2. Fill AFT tanks (FW1/FW2) for Stage 6A
3. Shift TR cargo AFT
```

**알고리즘:**
- SciPy `minimize` (SLSQP method)
- Multi-objective:
  ```python
  penalty = 0
  if s5_aft < 2.70: penalty += 1000 × (2.70 - s5_aft)²  # Priority 1
  if s6a_aft < 2.70: penalty += 100 × (2.70 - s6a_aft)²  # Priority 2
  penalty += discharge_time / 10.0  # Priority 3
  ```

---

### 8.3.5 Tab 4: History (이력 관리)

**목적:** 파라미터 변경 이력을 저장하고 Undo/Restore 기능을 제공합니다.

#### **A. Save Snapshot (스냅샷 저장)**

**사용법:**
1. Tab 1에서 파라미터 조정
2. Tab 4로 이동
3. "Save Snapshot" 버튼 클릭

**저장 내용:**
- 타임스탬프 (YYYY-MM-DD HH:MM:SS)
- Label (자동: "Snapshot #N")
- 모든 입력 파라미터 (FWB1/FWB2, TR1/TR2, Tide, Wave)

**제약:**
- 최대 20개 스냅샷 유지
- 21번째부터 자동으로 가장 오래된 항목 삭제

---

#### **B. Undo (되돌리기)**

**사용법:**
- "Undo" 버튼 클릭

**동작:**
- 가장 최근 스냅샷으로 파라미터 복원
- History stack에서 해당 항목 제거
- 최대 20번 Undo 가능

**시나리오 예시:**
```
1. 초기값: FWB2.P=21.45 → Save Snapshot → "Snapshot #1"
2. 변경: FWB2.P=25.00 → Save Snapshot → "Snapshot #2"
3. 변경: FWB2.P=30.00
4. Undo 클릭 → FWB2.P=25.00으로 복원 (Snapshot #2)
5. Undo 클릭 → FWB2.P=21.45로 복원 (Snapshot #1)
```

---

#### **C. History Table (이력 테이블)**

**표시 내용:**

| Timestamp | Label | FWB2.P | FWB2.S | TR1_LCG | TR2_LCG | Tide |
|-----------|-------|--------|--------|---------|---------|------|
| 2024-12-23 10:15:32 | Snapshot #1 | 21.45 | 21.45 | 30.68 | 30.46 | 0.30 |
| 2024-12-23 10:18:45 | Snapshot #2 | 25.00 | 25.00 | 30.68 | 30.46 | 0.30 |
| 2024-12-23 10:22:11 | Snapshot #3 | 19.31 | 19.31 | 32.00 | 28.00 | 0.50 |

**활용:**
- 감사 추적 (Audit Trail)
- 파라미터 변경 이력 문서화
- 승인 프로세스 증적 자료

---

## 8.4 고급 기능

### 8.4.1 Excel 보고서 상세

#### **4-Sheet 구조**

**Sheet 1: Dashboard**
- 요약 정보 (Stage 6A/5 핵심 결과)
- Gate 통과 여부 시각적 표시 (✅/❌)
- Color coding: 녹색(PASS), 빨간색(FAIL)

**Sheet 2: Stage 6A Details**
- 전체 파라미터 입력값
- 상세 계산 과정 (Displacement, TM_LCF, Trim, Draft)
- Gate 판정 기준 및 마진

**Sheet 3: Stage 5 Details**
- Stage 5 상세 결과 (동일 구조)

**Sheet 4: Parameters**
- 모든 입력 파라미터 요약
- Config.yaml 설정값
- 실행 타임스탬프

---

#### **Excel COM Force Recalculation (Windows Only)**

**문제:** OpenPyXL로 생성한 Excel 수식이 파일 열었을 때 계산되지 않음 (캐시 문제)

**해결:** `excel_com_utils.py`의 `excel_com_recalc_save()` 함수

```python
def excel_com_recalc_save(in_path, out_path, visible=False):
    """
    Windows Excel COM으로 파일 열고 강제 재계산 후 저장
    """
    import win32com.client
    excel = win32com.client.Dispatch("Excel.Application")
    excel.Visible = visible
    wb = excel.Workbooks.Open(in_path)
    wb.RefreshAll()  # 모든 수식 강제 재계산
    excel.Calculate()
    wb.Save()
    wb.Close()
    excel.Quit()
```

**자동 적용:**
- `excel_generator.py`의 `generate()` 메서드에서 자동 호출
- Windows 환경에서만 실행 (Linux/Mac에서는 skip)

---

### 8.4.2 Pydantic v2 검증 상세

#### **BallastParams 클래스**

```python
from pydantic import BaseModel, field_validator

class BallastParams(BaseModel):
    fwb1_p: float
    fwb1_s: float
    fwb2_p: float
    fwb2_s: float
    # ... 기타 필드

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

**v1 vs v2 비교:**

| 항목 | Pydantic v1 (v0.1) | Pydantic v2 (v0.2) |
|------|-------------------|-------------------|
| Validator | `@validator` | `@field_validator` ✅ |
| Classmethod | 선택적 | **필수** (`@classmethod`) |
| 성능 | Baseline | **5~50× 빠름** |
| Type Hint | 약함 | **강화된 타입 체크** |

---

### 8.4.3 Draft 계산 물리식 상세

#### **기존 방식 (v0.1) - 단순 선형 분배**

```python
# 문제: Lpp와 LCF 위치를 무시
dfwd = tref_m - (trim_cm / 200.0)  # 단순히 Trim을 절반씩 분배
daft = tref_m + (trim_cm / 200.0)
```

**한계:**
- Lpp(선간장)가 60.302m인데 고정 200cm로 가정
- LCF(부심 종방향 위치)가 midship에서 0.76m 떨어져 있는데 무시

---

#### **개선 방식 (v0.2) - Lpp/LCF 기반 물리식**

```python
# 물리적으로 정확한 계산
Lpp_m = 60.302
LCF = 0.76  # from midship (positive = AFT)

# Frame 기준 x 좌표 (midship = x=0)
x_fp = 30.151 - 63.0 = -32.849  # FP (선수)
x_ap = 30.151 - 0.0 = +30.151   # AP (선미)

# Trim slope (m/m)
slope = trim_m / Lpp_m

# Draft at any longitudinal position
draft_at_x = tmean_m + slope × (x - LCF)

# FWD/AFT Draft
dfwd_m = tmean_m + slope × (x_fp - LCF)
daft_m = tmean_m + slope × (x_ap - LCF)
```

**장점:**
- Lpp 변경 시 자동 반영
- LCF 위치 변경 시 자동 반영
- 임의의 x 위치에서 draft 계산 가능 (센서 위치 등)

---

### 8.4.4 Gate 정의 및 Chart Datum 변환 (SSOT)

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

| 용어 | 정의 | Gate-B 적용 |
|------|------|------------|
| **MSL** (Mean Sea Level) | 평균 해수면 | ❌ 부적절 (조위 영향 무시) |
| **CD** (Chart Datum) | 해도 기준면 (최저 저조면) | ✅ **정확** (조위 반영) |

**물리적 관계:**
```
MSL (평균 해수면)
  ↕ Tide (조위)
CD (해도 기준면)

Draft_CD = Draft_MSL - Tide
```

**Gate-B 검증:**
```python
# Stage 6A 예시
Draft_FWD_MSL = 2.32m
Forecast_Tide = 0.30m

Draft_FWD_CD = 2.32 - 0.30 = 2.02m  # ← Gate-B는 이 값 사용

Gate-B 판정:
- Draft_FWD_CD (2.02m) ≤ 2.70m → ✅ PASS (0.68m 여유)
```

**왜 CD를 써야 하나?**
- RoRo ramp 높이는 **고정** (조위와 무관)
- Tide가 높으면 선박이 떠올라 ramp와의 간극 감소
- CD 기준으로 관리해야 **안전한 ramp 접근** 보장

#### **Draft vs Freeboard vs UKC 구분 (SSOT)**

**Draft:**
- Keel → waterline (FWD/AFT/Mean)
- BUSHRA System에서 계산하는 값

**Freeboard:**
- Deck (or openings) → waterline
- Risk: deck wet/downflooding
- **Tide does NOT affect freeboard** (vessel rises with tide)

**UKC (Under-Keel Clearance):**
- Seabed/chart depth + Tide − Draft
- Risk: grounding
- **Tide affects UKC** (higher tide → more UKC)

**Important:** Never claim Tide solves deck wet. Tide is for UKC and under-keel constraints only.

---

## 8.5 운영 시나리오

### 8.5.1 시나리오 1: 현장 의사결정 (What-If 분석)

**상황:**
선장이 현장에서 "FWB2를 얼마나 채워야 AFT draft 2.70m를 달성할 수 있나?"를 즉시 알고 싶음.

**절차:**
1. Streamlit 앱 실행 (`streamlit run bushra_app.py`)
2. Tab 3 (Optimization) 이동
3. Target: Stage 5, AFT Target: 2.70m
4. "Find optimal FWB2" 클릭 (2초 소요)
5. 결과: "FWB2.P/S = 21.45 tonnes" 확인
6. Tab 1으로 복귀하여 21.45t 입력
7. Stage 5 AFT = 2.70m 확인 → 승인

**소요 시간:** ~1분 (vs 메인 파이프라인 10분)

---

### 8.5.2 시나리오 2: 조위 변경 영향 분석

**상황:**
예보 조위가 0.30m → 0.50m로 변경됨. Gate-B에 미치는 영향은?

**절차:**
1. Tab 1, Sidebar에서 Forecast Tide: 0.30 → 0.50
2. 결과 즉시 업데이트 (1초 이내)
   - Stage 6A Draft_FWD(CD): 2.02m → 1.82m
   - Gate-B 마진: 0.68m → 0.88m (개선)
3. "Tide 증가 → Gate-B 여유 증가" 확인
4. Save Snapshot으로 기록

---

### 8.5.3 시나리오 3: 화물 위치 변경 시뮬레이션

**상황:**
TR1을 Frame 30.68 → 35.00 (AFT 방향)으로 이동하면 AFT draft가 얼마나 증가하나?

**절차:**
1. Tab 1, Sidebar에서 TR1 LCG(AP): 30.68 → 35.00
2. 결과 즉시 계산:
   - Stage 6A AFT: 2.58m → 2.64m (+0.06m)
   - Gate-A: ❌ FAIL → ❌ FAIL (여전히 부족)
3. Scenario Comparison (Tab 2)로 추가 분석
4. 결론: "TR1 shift만으로는 불충분, FWB2 inventory 필요"

---

### 8.5.4 시나리오 4: 승인 패키지 생성

**상황:**
최종 파라미터가 확정되어 Captain/Mammoet 승인용 Excel 보고서 필요.

**절차:**
1. Tab 1에서 최종 파라미터 설정
   - FWB2.P/S: 21.45t
   - TR1/TR2: 확정 위치
   - Tide: 최신 예보
2. "Generate Excel Report" 클릭
3. `output/BUSHRA_Ballast_Report_20241223_105432.xlsx` 생성
4. Windows에서 Excel 열기 (COM이 자동으로 수식 재계산 완료)
5. Sheet 1 (Dashboard) 인쇄 또는 PDF 변환
6. 승인 서류에 첨부

---

## 8.6 제약사항 및 해결 방법

### 8.6.1 알려진 제약사항

| 제약 | 설명 | 해결 방법 |
|------|------|----------|
| **LP Solver 간소화** | PuLP 대신 SciPy 사용 | 복잡한 최적화는 메인 파이프라인 사용 |
| **Stage 제한** | Stage 6A와 5만 지원 | 다른 Stage는 메인 파이프라인에서 처리 |
| **Excel COM (Windows만)** | Linux/Mac에서 수식 재계산 불가 | 수동으로 Excel 열어 F9 (재계산) 실행 |
| **Heel 계산 없음** | 좌우 경사(Heel) 미계산 | FWB2.P = FWB2.S로 대칭 유지 필수 |
| **다중 사용자 불가** | Local 실행만 지원 | 팀 공유 시 Streamlit Cloud 배포 필요 |

---

### 8.6.2 문제 해결 (Troubleshooting)

#### **문제 1: Pydantic 검증 오류**

**증상:**
```
ValueError: FWB2.P must be in [0, 50], got 55.0
```

**원인:** Tank 용량 초과 (Cap_t=50.0t)

**해결:**
1. `config.yaml`에서 `tank_capacities` 확인
2. 슬라이더 범위 조정
3. 또는 SSOT CSV에서 Cap_t 수정

---

#### **문제 2: 최적화 실패**

**증상:**
```
Optimization failed to converge.
Try widening bounds or adjusting target.
```

**원인:** 목표 AFT draft가 FWB2 범위 [10, 50]로 달성 불가능

**해결:**
1. Target AFT draft 낮추기 (2.70m → 2.65m)
2. 또는 다른 탱크 조합 고려 (메인 파이프라인 사용)

---

#### **문제 3: Excel 수식 비어 있음**

**증상:** Excel 파일 열었을 때 Dashboard의 수식 셀이 비어 있음

**원인:**
- Windows가 아닌 OS (COM 불가)
- 또는 `pywin32` 미설치

**해결:**
```bash
# Windows: pywin32 설치
pip install pywin32

# Linux/Mac: 수동 재계산
Excel 열고 → Ctrl+Alt+F9 (모든 수식 재계산)
```

---

#### **문제 4: Streamlit 포트 충돌**

**증상:**
```
OSError: [Errno 48] Address already in use
```

**해결:**
```bash
# 다른 포트 사용
streamlit run bushra_app.py --server.port 8502

# 또는 기존 프로세스 종료
# Windows:
taskkill /F /IM streamlit.exe

# Linux/Mac:
pkill -f streamlit
```

---

## 8.7 메인 파이프라인과의 역할 분담

### 8.7.1 시스템 선택 가이드

| 작업 유형 | 추천 시스템 | 이유 |
|----------|-----------|------|
| **현장 의사결정** | BUSHRA v0.2 | 실시간 (<1초) |
| **What-If 분석** | BUSHRA v0.2 | 파라미터 즉시 변경 |
| **시나리오 비교** | BUSHRA v0.2 | 3-scenario 자동 생성 |
| **최종 승인 보고서** | 메인 파이프라인 | 28-sheet 완전 보고서 |
| **전체 Stage 분석** (5/6A/6B/7) | 메인 파이프라인 | 모든 Stage 지원 |
| **LP Solver 완전 최적화** | 메인 파이프라인 | PuLP 다중 제약 |
| **DNV Mitigation 문서** | 메인 파이프라인 | Gate 실패 시 자동 생성 |
| **Gate-FB 4-corner 모니터링** | 메인 파이프라인 | 상세 Freeboard 계산 |
| **AGI 제출 패키지 생성** | 메인 파이프라인 | Option 1/2 패치 적용 |
| **BALLAST_SEQUENCE 분리** | 메인 파이프라인 | Option 2: BALLAST_OPTION/EXEC 분리 |

---

### 8.7.2 통합 워크플로우 (권장)

```
1. 초기 설계 (BUSHRA v0.2)
   ├─ 현장에서 FWB2 최적값 탐색 (2초)
   ├─ 시나리오 비교로 안전 여유 확인 (5초)
   └─ 파라미터 확정 및 스냅샷 저장

2. 중간 검증 (메인 파이프라인)
   ├─ sensors/current_t_sensor.csv에 BUSHRA 결과 입력
   ├─ 전체 파이프라인 실행 (30초)
   └─ 모든 Stage/Gate 검증

3. 최종 승인 (메인 파이프라인)
   ├─ DNV Mitigation 문서 자동 생성
   ├─ 28-sheet Excel 보고서 생성
   └─ Captain/Mammoet 서명

4. 현장 운영 (BUSHRA v0.2)
   ├─ 실시간 조위 변경 반영
   ├─ 긴급 What-If 분석
   └─ 작업 중 파라미터 조정
```

---

## 8.8 테스트 및 검증

### 8.8.1 단위 테스트 (pytest)

**실행:**
```bash
cd bushra_ballast_system_v0_2
pytest
```

**결과:**
```
tests/test_calculator_engine.py ........ [100%]
tests/test_optimizer.py .... [100%]

========== 12 passed in 1.23s ==========
```

**커버리지:**
```bash
pytest --cov=. --cov-report=html
```

---

### 8.8.2 통합 테스트

**수동 체크리스트:**

- [ ] **Tab 1**: FWB2 슬라이더 조작 → 결과 즉시 업데이트
- [ ] **Tab 1**: Tide 변경 → Draft_FWD(CD) 변경 확인
- [ ] **Tab 1**: Excel 보고서 생성 → output/ 폴더에 파일 생성
- [ ] **Tab 2**: "Set from current" → 3-scenario 자동 생성
- [ ] **Tab 2**: 차트에 3개 바 표시
- [ ] **Tab 3**: Single-stage 최적화 → <5초 내 결과
- [ ] **Tab 3**: Multi-stage 최적화 → <10초 내 결과
- [ ] **Tab 4**: Save Snapshot → History 테이블에 추가
- [ ] **Tab 4**: Undo → 이전 값 복원

---

### 8.8.3 성능 벤치마크

| 작업 | 목표 | 실제 | 상태 |
|------|------|------|------|
| 단일 계산 (Stage 6A+5) | <1초 | ~0.3초 | ✅ |
| 시나리오 비교 (3개) | <2초 | ~0.9초 | ✅ |
| Single-stage 최적화 | <5초 | ~2.5초 | ✅ |
| Multi-stage 최적화 | <10초 | ~7.2초 | ✅ |
| Excel 생성 (COM 포함) | <5초 | ~3.8초 | ✅ |

---

## 8.9 확장 가능성

### 8.9.1 향후 개선 계획

| 기능 | 우선순위 | 예상 작업량 | 상태 |
|------|---------|------------|------|
| **Stage 6B/7 추가** | 중 | 2일 | 계획 중 |
| **UKC 계산 통합** | 중 | 1일 | 계획 중 |
| **Heel(경사) 계산** | 중 | 3일 | 계획 중 |
| **Database 연동** | 낮 | 5일 | 미정 |
| **Multi-user (Streamlit Cloud)** | 낮 | 3일 | 미정 |
| **Mobile UI 최적화** | 낮 | 2일 | 미정 |

---

### 8.9.2 커스터마이징 가이드

**A. 새 Tank 추가**

1. `data/tank_ssot.csv` 편집:
   ```csv
   Tank,Cap_t,x_from_mid_m
   FW3.P,15.00,25.00
   ```

2. `calculator_engine.py` 수정 (불필요, 자동 로드)

3. `bushra_app.py` Sidebar 추가:
   ```python
   fwb3_p = st.slider("FW3.P", 0.0, 15.0, 0.0)
   ```

**B. 새 Gate 추가**

1. `config.yaml` 편집:
   ```yaml
   gates:
     ukc_min_m: 0.50  # 신규 Gate-UKC
   ```

2. `calculator_engine.py`에 검증 로직 추가:
   ```python
   def gate_validation(...):
       # 기존 Gate-A/B/FB/TRIM
       ukc = chart_depth - daft_m - tide_m
       gate_ukc = ukc >= 0.50
   ```

---

## 8.10 요약 및 체크리스트

### 8.10.1 빠른 참조 카드

**시스템 시작:**
```bash
cd bushra_ballast_system_v0_2
streamlit run bushra_app.py
```

**핵심 조작:**
- FWB2.P/S 슬라이더: Stage 5 AFT draft 주요 조정 변수
- Tide: Gate-B (FWD draft CD) 영향
- Tab 3 Optimization: AFT target 달성 자동 탐색

**주의사항:**
- FWB2.P = FWB2.S 유지 (heel 방지)
- Gate-B는 Chart Datum 기준
- Excel COM은 Windows 전용

---

### 8.10.2 운영 체크리스트

**사전 준비:**
- [ ] Python 3.9+ 설치
- [ ] `requirements.txt` 의존성 설치
- [ ] `data/tank_ssot.csv` 최신 버전 확인
- [ ] `config.yaml` 파라미터 검증

**실행 전:**
- [ ] Streamlit 포트 충돌 확인 (8501)
- [ ] Windows에서 Excel COM 가용 확인
- [ ] `output/` 폴더 쓰기 권한 확인

**사용 중:**
- [ ] 파라미터 변경 시 Save Snapshot
- [ ] 주요 결정은 Excel 보고서로 문서화
- [ ] Gate 실패 시 메인 파이프라인으로 DNV Mitigation 생성

**사후 관리:**
- [ ] Streamlit 프로세스 정리 (`Ctrl+C`)
- [ ] 생성된 Excel 보고서 백업
- [ ] History 스냅샷 중요 항목 별도 저장

---

**문의 및 지원:**
- 기술 문서: `docs/00_System_Architecture_Complete.md`
- SSOT 정의: `AGENTS.md`
- 메인 파이프라인: `Ballast Pipeline 운영 가이드.MD`

---

**마지막 업데이트:** 2025-12-27
**문서 버전:** 1.1
**시스템 버전:** BUSHRA Ballast System v0.2

**최신 업데이트 (v1.1 - 2025-12-27):**
- 문서 버전 업데이트 (메인 파이프라인 v3.1과 일관성 유지)

