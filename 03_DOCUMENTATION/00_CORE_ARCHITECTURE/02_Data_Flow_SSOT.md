# 제2장: 데이터 흐름과 SSOT (Single Source of Truth)

**작성일:** 2025-12-20
**버전:** v3.7 (Updated: 2025-12-29)
**목적:** JSON에서 CSV로의 데이터 변환 프로세스와 SSOT 아키텍처 이해

**최신 업데이트 (v3.7 - 2025-12-29):**
- 파이프라인 실행 파일 → 출력 파일 → 헤더 구조 매핑 추가
- 각 Step이 생성하는 Excel/CSV 파일과 헤더 관계 명시
- 상세 내용: `00_System_Architecture_Complete.md` 섹션 8 참조

**최신 업데이트 (v3.6 - 2025-12-29):**
- Forecast_Tide_m 우선순위 변경: CLI `--forecast_tide` 값이 최우선 적용
  - `stage_table_unified.csv`와 `solver_ballast_summary.csv` 간 `Forecast_Tide_m` 완전 일치 보장
  - SSOT 규칙 업데이트: CLI 값 → stage_tide_csv → tide_table 순서
  - 자세한 내용은 `17_TIDE_UKC_Calculation_Logic.md` 섹션 17.6.5 참조

**최신 업데이트 (v3.5 - 2025-12-28):**
- Option 2 구현: BALLAST_SEQUENCE 옵션/실행 분리
  - `BALLAST_OPTION.csv`: 계획 레벨 (Delta_t 중심, 모든 Stage 포함)
  - `BALLAST_EXEC.csv`: 실행 시퀀스 (Start_t/Target_t carry-forward, Stage 6B 제외)
  - Start_t/Target_t 체인: 이전 step의 Target_t → 다음 Start_t 자동 전달
  - Stage 6B 분리: OPTIONAL_STAGES 상수로 실행 시퀀스에서 제외
- Option 1 패치 제안 (미구현)
  - Bryan Pack Forecast_tide_m 주입 (pipeline_stage_QA.csv 병합)
  - Stage 5_PreBallast GateB critical 강제 (AGI 규칙)
  - Current_* vs Draft_* 단일화 (QA 테이블)

**최신 업데이트 (v3.4 - 2025-12-28):**
- I/O Optimization (PR-01~05): Parquet cache, Manifest logging, Fast CSV reading
  - Parquet sidecar cache: stage_results.parquet 자동 생성 (Step 1b 직후)
  - read_table_any() 통합 API: Parquet 우선 로드, CSV fallback
  - Manifest logging: 모든 I/O 작업 자동 추적 (manifests/<run_id>/<step>_<pid>.jsonl)
  - Fast CSV: Polars lazy scan 우선, pandas fallback (pyarrow → c → python)
- SSOT CSV 읽기: 모든 지점에서 read_table_any() 사용 (OPS, StageExcel, Orchestrator)

**최신 업데이트 (v3.3 - 2025-12-27):**
- Tide Integration (AGI-only): stage_tide_AGI.csv, Forecast_tide_m, Tide_required_m, Tide_margin_m
- Stage Table 확장: DatumOffset_m, Forecast_Tide_m, Tide_Source, Tide_QC 컬럼 추가
- QA CSV 확장: Tide alias columns (Forecast_tide_m, Tide_required_m, UKC_min_m, UKC_fwd_m, UKC_aft_m)
- SPMT Integration: SPMT cargo data flow 추가

**최신 업데이트 (v3.2 - 2025-12-27):**
- AGENTS.md SSOT 통합 (좌표계 변환 공식, Tank Direction SSOT)
- 좌표계 변환 공식 명확화 (x = 30.151 - Fr, 재해석 금지)
- Tank Direction SSOT 추가 (FWD/AFT Zone 분류, Golden Rule)

**최신 업데이트 (v3.1 - 2025-12-27):**
- Current_t 자동 탐색 기능 (current_t_*.csv 패턴 자동 감지)
- diff_audit.csv 생성 (센서 주입 이력 기록)
- GM 검증 및 FSM 통합 (CLAMP 감지, FSM 검증, GM_eff 계산)

**최신 업데이트 (v2.2 - 2024-12-23):**
- Excel/CSV 일관성 패치 (2024-12-23)
- Excel 생성 시 `stage_results.csv` SSOT 읽기
- Draft clipping 로직 상세 설명

---

## 2.1 SSOT (Single Source of Truth) 개념

### 2.1.1 SSOT의 필요성

Ballast Pipeline은 **4개의 독립적인 Python 스크립트**로 구성되어 있습니다. 각 스크립트는 서로 다른 데이터 형식과 구조를 요구할 수 있으며, 이로 인해 다음과 같은 문제가 발생할 수 있습니다:

- **데이터 불일치**: 동일한 탱크 정보를 각 스크립트가 서로 다르게 해석
- **좌표계 혼동**: LCG 표현 방식의 차이 (AP 기준 vs Midship 기준)
- **버전 관리 어려움**: 여러 스크립트가 동일한 소스 데이터를 각각 다르게 수정
- **디버깅 복잡성**: 중간 데이터 형식의 불일치로 인한 오류 추적 어려움

SSOT 아키텍처는 이러한 문제를 해결하기 위해 **원본 데이터는 JSON으로 한 번만 정의**하고, 파이프라인이 필요에 따라 **표준화된 CSV 형식으로 변환**합니다.

### 2.1.2 SSOT 데이터 흐름

**입력 데이터 소스 (`bplus_inputs/` 폴더)**:
- `Hydro_Table_Engineering.json`: Hydrostatic 테이블 (Step 1, 2, 3)
- `profiles/AGI.json`: Site profile (Step 2, 3)
- `data/Frame_x_from_mid_m.json`: Frame ↔ x 변환 (Step 1)
- `stage_schedule.csv`: Stage별 타임스탬프 (Tide Integration, 선택적)
- `water tide_202512.xlsx`: Tide 데이터 (Tide Integration, 선택적)
- `tide_windows_AGI.json`: Stage별 tide window 정의 (Tide Integration, 선택적)

**탐색 순서**:
1. `inputs_dir/bplus_inputs/` (또는 `base_dir/bplus_inputs/`)
2. `02_RAW_DATA/` (fallback)

**참고**: 자세한 내용은 `파이프라인 전체 아키텍처, 실행 파일, 로직 상세 설명.MD` 섹션 2.12 참조.

```
┌─────────────────────────────────────────────────────────┐
│          SOURCE DATA (JSON - Single Source)             │
├─────────────────────────────────────────────────────────┤
│  tank_catalog_from_tankmd.json                         │
│    └─> {"tanks": [{"id": "FWB2", "lcg_m": 25.0, ...}]} │
│                                                         │
│  Hydro_Table_Engineering.json                          │
│    └─> [{"Tmean_m": 2.0, "TPC_t_per_cm": 8.0, ...}]   │
│                                                         │
│  stage_results.csv (from Step 1)                       │
│    └─> Stage, Dfwd_m, Daft_m, ...                      │
└──────────────────────┬──────────────────────────────────┘
                       │
                       │ Pipeline Conversion Functions
                       ▼
┌─────────────────────────────────────────────────────────┐
│        SSOT CSV (Standardized - Multiple Consumers)     │
├─────────────────────────────────────────────────────────┤
│  ssot/tank_ssot_for_solver.csv                         │
│    └─> Tank, x_from_mid_m, Current_t, Min_t, Max_t... │
│                                                         │
│  ssot/hydro_table_for_solver.csv                       │
│    └─> Tmean_m, TPC_t_per_cm, MTC_t_m_per_cm, ...     │
│                                                         │
│  ssot/stage_table_unified.csv                          │
│    └─> Stage, Current_FWD_m, Current_AFT_m, Gates...  │
│         Forecast_Tide_m, DatumOffset_m (AGI-only)      │
│                                                         │
│  ssot/pipeline_stage_QA.csv                            │
│    └─> Definition-split validation & Gate status      │
│         Forecast_tide_m, Tide_required_m, Tide_margin_m│
│         UKC_min_m, UKC_fwd_m, UKC_aft_m, Tide_verdict  │
│         Draft_FWD_m, Draft_AFT_m (SSOT, Current_* 제거 권장) │
│                                                         │
│  BALLAST_OPTION.csv (Option 2, 계획 레벨)              │
│    └─> Stage, Tank, Action, Delta_t, PumpRate_tph, Priority, Rationale │
│                                                         │
│  BALLAST_EXEC.csv (Option 2, 실행 시퀀스)              │
│    └─> Stage, Step, Tank, Start_t, Target_t, Delta_t, Time_h, Hold_Point │
│         (Start_t/Target_t carry-forward, Stage 6B 제외) │
│                                                         │
│  BALLAST_SEQUENCE.csv (Legacy, 호환성)                 │
│    └─> 기존 형식 (Option 2와 병행)                     │
│                                                         │
│  stage_tide_AGI.csv (AGI-only, Pre-Step)               │
│    └─> StageKey, Forecast_tide_m, tide_src, tide_qc    │
│                                                         │
│  stage_results.parquet (PR-04, Parquet cache)          │
│    └─> Parquet sidecar cache (mtime validation)        │
│                                                         │
│  manifests/<run_id>/<step>_<pid>.jsonl (PR-01)         │
│    └─> I/O operation logs (JSONL format)              │
└──────────────────────┬──────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
   Step 2: OPS    Step 3: LP    Step 4: OPT
   Report Gen     Solver        Optimizer
   (read_table_any) (read_table_any) (read_table_any)
```

---

## 2.2 탱크 카탈로그 변환

### 2.2.1 입력 형식: `tank_catalog_from_tankmd.json`

```json
{
  "source_file": "tank.md",
  "tanks": [
    {
      "id": "FWB2",
      "category": "fresh_water_ballast",
      "lcg_m": 25.0,
      "tcg_m": 0.0,
      "vcg_m": 1.5,
      "cap_t": 50.0,
      "loc": "AFT",
      "fr_start": 40,
      "fr_end": 45
    },
    ...
  ]
}
```

**중요 필드:**
- `id`: 탱크 식별자
- `lcg_m`: LCG (Longitudinal Center of Gravity) from AP (After Perpendicular), 단위: m
- `cap_t`: 탱크 용량 (tons)
- `category`: 탱크 카테고리 (ballast 관련 키워드 포함 여부 확인용)

### 2.2.2 출력 형식: `tank_ssot_for_solver.csv`

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| `Tank` | string | 탱크 식별자 | "FWB2" |
| `Capacity_t` | float | 탱크 용량 (tons) | 50.0 |
| `x_from_mid_m` | float | Midship 기준 X 좌표 (+AFT / -FWD) | -5.151 |
| `Current_t` | float | 현재 탱크 중량 (tons) | 0.0 |
| `Min_t` | float | 최소 허용 중량 (tons) | 0.0 |
| `Max_t` | float | 최대 허용 중량 (tons) | 50.0 |
| `mode` | string | 작동 모드 | "FILL_DISCHARGE" |
| `use_flag` | string | 사용 여부 (Y/N) | "Y" |
| `pump_rate_tph` | float | 펌프 속도 (tons/hour) | 100.0 |
| `priority_weight` | float | 우선순위 가중치 (낮을수록 우선) | 1.0 |

### 2.2.3 좌표계 변환 (SSOT - AGENTS.md 기준, 재해석 금지)

**Frame 좌표계 (BUSHRA TCP / tank.md 기준)**:
- `Fr.0 = AP (AFT)`: After Perpendicular (선미 수직선)
- `Frame 증가 방향 = FWD`: Frame이 증가할수록 선수 방향
- `Frame 30.151 = Midship → x = 0.0`: Midship 기준점

**X 좌표계 (계산용, Midship 기준)**:
- `LPP_M = 60.302`: Length between perpendiculars (m)
- `MIDSHIP_FROM_AP_M = 30.151`: Midship 위치 (AP 기준, m)
- `_FRAME_SLOPE = -1.0`: Frame→x 변환 기울기
- `_FRAME_OFFSET = 30.151`: Frame→x 변환 오프셋

**좌표 변환 공식 (표준, 재해석 금지)**:
```python
# Constants (from integrated_pipeline_defsplit_v2.py)
LPP_M = 60.302  # m (Length Between Perpendiculars)
MIDSHIP_FROM_AP_M = LPP_M / 2.0  # 30.151 m

# Coordinate transformation (LCG from AP → x from Midship)
lcg_from_ap = tank["lcg_m"]  # LCG from AP (stern)
x_from_mid_m = MIDSHIP_FROM_AP_M - lcg_from_ap

# Frame → x 변환 (일반적)
x = _FRAME_SLOPE * (Fr - _FRAME_OFFSET)
x = 30.151 - Fr
```

**좌표계 규칙:**
- **입력 (JSON)**: `lcg_m`은 AP (After Perpendicular, 선미) 기준
- **출력 (CSV)**: `x_from_mid_m`은 Midship 기준
  - 양수 (+) = AFT (선미 방향, `x > 0`)
  - 음수 (-) = FWD (선수 방향, `x < 0`)

**예시:**
- 탱크 LCG가 AP에서 25.0m → `x_from_mid_m = 30.151 - 25.0 = +5.151m` (AFT)
- 탱크 LCG가 AP에서 35.0m → `x_from_mid_m = 30.151 - 35.0 = -4.849m` (FWD)
- Frame 25.0 → `x = 30.151 - 25.0 = +5.151m` (AFT)
- Frame 35.0 → `x = 30.151 - 35.0 = -4.849m` (FWD)

**Golden Rule**: 선수 탱크(높은 Fr / 높은 LCG(AP))를 "선미 ballast"로 취급하면 물리 법칙이 뒤집혀 모든 Gate가 깨집니다.

### 2.2.4 Tank Direction SSOT (FWD/AFT 분류 - 재논의 금지)

**AFT Zone (선미)**:
- `FW2 P/S`: Fr.0-6 (선미 담수)
- `VOIDDB4 P/S`, `SLUDGE.C`, `SEWAGE.P`: Fr.19-24 (중선미)
- 연료 탱크 `DO`, `FODB1`, `FOW1`, `LRFO P/S/C`: Fr.22-33 (Midship 근처)

**MID Zone**:
- `VOID3 P/S`: Fr.33-38

**MID-FWD Zone**:
- `FWCARGO2 P/S`: Fr.38-43
- `FWCARGO1 P/S`: Fr.43-48

**FWD/BOW Zone (선수)**:
- `FWB2 P/S`: Fr.48-53 (선수 ballast)
- `VOIDDB1.C`: Fr.48-56
- `FWB1 P/S`: Fr.56-FE (선수 ballast)
- `CL P/S`: Fr.56-59 (Chain lockers)

**실무적 결과**: `FWB1.*` 및 `FWB2.*`는 **선수/선수 탱크**입니다. X 좌표계에서 `x < 0`을 가지며, **"선미 ballast"로 사용할 수 없습니다**. AFT-up / stern-down 모멘트가 필요하면 **AFT zone 탱크** 및/또는 화물 LCG를 선미로 이동해야 합니다.

### 2.2.4 변환 함수: `convert_tank_catalog_json_to_solver_csv`

**위치:** `integrated_pipeline_defsplit_v2.py` (lines 151-220)

**주요 로직:**

1. **JSON 파싱 및 검증**
   ```python
   obj = json.loads(tank_catalog_json.read_text(encoding="utf-8"))
   tanks = obj.get("tanks", [])
   if not isinstance(tanks, list):
       raise ValueError(f"Unexpected tank catalog structure")
   ```

2. **탱크 필터링 및 분류**
   - 기본 키워드: `["BALLAST", "VOID", "FWB", "FW", "DB"]`
   - `use_flag = "Y"`로 마킹되어 LP Solver에서 사용 가능
   - 키워드가 없으면 `use_flag = "N"` (사용 불가)

3. **우선순위 할당 (Priority Weight)**
   ```python
   if "FWB2" in tid.upper():
       priority_weight = 1.0  # 최우선 (Primary discharge source)
   elif "VOIDDB2" in tid.upper():
       priority_weight = 2.0  # 차순위
   elif "VOIDDB1" in tid.upper():
       priority_weight = 3.0  # 삼순위
   else:
       priority_weight = 5.0  # 기본값
   ```
   - 낮은 값이 더 높은 우선순위 (LP 목적함수에서 가중치로 사용)

4. **CSV 출력**
   - UTF-8 with BOM (`encoding="utf-8-sig"`)로 Excel 호환성 보장
   - 모든 수치 값은 적절한 정밀도로 반올림

---

## 2.3 Hydrostatic Table 변환

### 2.3.1 입력 형식: `Hydro_Table_Engineering.json`

JSON 구조는 유연하게 처리됩니다:
- 리스트 형식: `[{...}, {...}]`
- 딕셔너리 with "rows": `{"rows": [{...}, {...}]}`
- 단일 딕셔너리: `{...}` (DataFrame으로 직접 변환 시도)

**필수 컬럼:**
- `Tmean_m`: 평균 흘수 (m)
- `TPC_t_per_cm`: Tons Per Centimeter (흘수 1cm당 중량 변화)
- `MTC_t_m_per_cm`: Moment to Change Trim (트림 1cm당 모멘트)
- `LCF_m` 또는 `LCF_m_from_midship`: Longitudinal Center of Flotation (m)
- `LBP_m`: Length Between Perpendiculars (m) - 없으면 기본값 사용

### 2.3.2 출력 형식: `hydro_table_for_solver.csv`

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| `Tmean_m` | float | 평균 흘수 (m) | 2.50 |
| `TPC_t_per_cm` | float | Tons Per Centimeter | 8.00 |
| `MTC_t_m_per_cm` | float | Moment to Change Trim (t·m/cm) | 34.00 |
| `LCF_m` | float | LCF from Midship (m, +AFT/-FWD) | 0.76 |
| `LBP_m` | float | Length Between Perpendiculars (m) | 60.302 |

**정렬:** `Tmean_m` 기준 오름차순 (보간을 위해 필수)

### 2.3.3 변환 함수: `convert_hydro_engineering_json_to_solver_csv`

**위치:** `integrated_pipeline_defsplit_v2.py` (lines 223-263)

**주요 로직:**

1. **유연한 JSON 파싱**
   ```python
   raw = json.loads(hydro_json.read_text(encoding="utf-8"))
   if isinstance(raw, list):
       df = pd.DataFrame(raw)
   elif isinstance(raw, dict) and "rows" in raw:
       df = pd.DataFrame(raw.get("rows", []))
   else:
       df = pd.DataFrame(raw)
   ```

2. **컬럼명 정규화**
   ```python
   colmap = {}
   if "MCTC_t_m_per_cm" in df.columns and "MTC_t_m_per_cm" not in df.columns:
       colmap["MCTC_t_m_per_cm"] = "MTC_t_m_per_cm"
   if "LCF_m_from_midship" in df.columns and "LCF_m" not in df.columns:
       colmap["LCF_m_from_midship"] = "LCF_m"
   df = df.rename(columns=colmap)
   ```
   - 다양한 네이밍 컨벤션 지원 (예: `MCTC` vs `MTC`)

3. **필수 컬럼 검증**
   ```python
   required = ["Tmean_m", "TPC_t_per_cm", "MTC_t_m_per_cm", "LCF_m"]
   missing = [c for c in required if c not in df.columns]
   if missing:
       raise ValueError(f"Hydro table missing required columns: {missing}")
   ```

4. **LBP 기본값 처리**
   ```python
   if "LBP_m" not in df.columns:
       df["LBP_m"] = float(lbp_m)  # 기본값: LPP_M = 60.302
   ```

5. **정렬 및 필터링**
   - `Tmean_m` 기준 오름차순 정렬
   - `Tmean_m`이 NaN인 행 제거

---

## 2.4 Stage Table 구축

### 2.4.1 입력: `stage_results.csv` (Step 1 출력)

Step 1 (TR Excel Generator)가 CSV 모드로 실행되면 생성되는 파일입니다.

**예상 컬럼 (유연한 인식):**
- `Stage` 또는 `stage_name` 또는 `name`: Stage 식별자
- `Dfwd_m` 또는 `FWD_m`: Forward Draft (m)
- `Daft_m` 또는 `AFT_m`: Aft Draft (m)
- 기타 메타데이터 (선택적)

### 2.4.2 출력: `stage_table_unified.csv`

**Solver용 컬럼:**
- `Stage`: Stage 식별자
- `Current_FWD_m`: 현재 Forward Draft (m)
- `Current_AFT_m`: 현재 Aft Draft (m)
- `FWD_MAX_m`: FWD 최대값 게이트 (예: 2.70m)
- `AFT_MIN_m`: AFT 최소값 게이트 (예: 2.70m)
- `D_vessel_m`: 선체 깊이 (m, Freeboard 계산용)
- `Forecast_Tide_m`: 예보 조위 (m, 선택적, UKC 계산용)
- `DepthRef_m`: 기준 수심 (m, 선택적, UKC 계산용)
- `UKC_Min_m`: 최소 UKC 요구값 (m, 선택적)

**Optimizer용 컬럼:**
- `FWD_Limit_m`: FWD 상한 (m, = FWD_MAX_m)
- `AFT_Limit_m`: AFT 상한 (m, Optimizer 전용, 예: 3.50m)
- `Trim_Abs_Limit_m`: 절대 트림 제한 (m, 예: 0.50m)

### 2.4.3 변환 함수: `build_stage_table_from_stage_results`

**위치:** `integrated_pipeline_defsplit_v2.py` (lines 266-344)

**주요 로직:**

1. **유연한 컬럼 인식**
   ```python
   stage_col = "Stage" if "Stage" in df.columns else None
   if stage_col is None:
       for c in df.columns:
           if str(c).strip().lower() in ("stage_name", "name"):
               stage_col = c
               break
   ```
   - 다양한 네이밍 컨벤션 자동 인식

2. **Draft 컬럼 매핑**
   ```python
   dfwd_col = ("Dfwd_m" if "Dfwd_m" in df.columns
               else ("FWD_m" if "FWD_m" in df.columns else None))
   daft_col = ("Daft_m" if "Daft_m" in df.columns
               else ("AFT_m" if "AFT_m" in df.columns else None))
   ```

3. **게이트 값 할당**
   - Solver용: `FWD_MAX_m`, `AFT_MIN_m` (필수)
   - Optimizer용: `FWD_Limit_m`, `AFT_Limit_m`, `Trim_Abs_Limit_m`

4. **선택적 UKC 파라미터**
   - `forecast_tide_m`, `depth_ref_m`, `ukc_min_m`이 제공되면 컬럼 추가
   - UKC 계산을 위한 필수 입력 (제5장 참조)

---

## 2.5 Stage QA CSV 생성

### 2.5.1 목적

Definition-Split 개념을 검증하고, 각 Stage별 게이트 준수 여부를 명확히 확인하기 위한 QA CSV를 생성합니다.

**위치:** `integrated_pipeline_defsplit_v2.py` (lines 347-466)

### 2.5.2 출력: `pipeline_stage_QA.csv`

**Definition-Split 컬럼:**

| Column | Description | Formula |
|--------|-------------|---------|
| `Forecast_Tide_m` | 예보 조위 (예측값) | 입력값 (예: 0.30m) |
| `Required_WL_for_UKC_m` | UKC 만족을 위한 요구 수면고 (역계산) | `(Draft_max + Squat + Safety + UKC_MIN) - DepthRef` |
| `Freeboard_FWD_m` | Freeboard at FWD (조위 무관) | `D_vessel_m - Current_FWD_m` |
| `Freeboard_AFT_m` | Freeboard at AFT (조위 무관) | `D_vessel_m - Current_AFT_m` |
| `Freeboard_Min_m` | 최소 Freeboard | `min(Freeboard_FWD, Freeboard_AFT)` |
| `UKC_FWD_m` | UKC at FWD (조위 의존) | `(DepthRef + Forecast_Tide) - (FWD + Squat + Safety)` |
| `UKC_AFT_m` | UKC at AFT (조위 의존) | `(DepthRef + Forecast_Tide) - (AFT + Squat + Safety)` |
| `UKC_Min_m` | 최소 UKC | `min(UKC_FWD, UKC_AFT)` |

**Gate 검증 컬럼:**

| Column | Values | Description |
|--------|--------|-------------|
| `Gate_FWD_Max` | "OK" / "NG" | FWD ≤ FWD_MAX_m 여부 |
| `Gate_AFT_Min` | "OK" / "NG" | AFT ≥ AFT_MIN_m 여부 |
| `Gate_Freeboard` | "OK" / "NG" | Freeboard ≥ 0 여부 |
| `Gate_UKC` | "OK" / "NG" / "N/A" | UKC ≥ UKC_MIN_m 여부 (파라미터 제공 시만) |

**Margin 컬럼:**

| Column | Description |
|--------|-------------|
| `FWD_Margin_m` | `FWD_MAX_m - Current_FWD_m` (양수면 여유 있음) |
| `AFT_Margin_m` | `Current_AFT_m - AFT_MIN_m` (양수면 여유 있음) |
| `UKC_Margin_m` | `UKC_Min_m - UKC_Min_Required_m` (제공 시) |

### 2.5.3 주요 계산 로직

**Freeboard (조위 무관):**
```python
freeboard_fwd = d_vessel_m - dfwd
freeboard_aft = d_vessel_m - daft
freeboard_min = min(freeboard_fwd, freeboard_aft)
```

**UKC (조위 의존):**
```python
if depth_ref_m is not None and forecast_tide_m is not None:
    available_depth = depth_ref_m + forecast_tide_m
    ukc_fwd = available_depth - (dfwd + squat_m + safety_allow_m)
    ukc_aft = available_depth - (daft + squat_m + safety_allow_m)
    ukc_min = min(ukc_fwd, ukc_aft)
```

**Required_WL_for_UKC_m (역계산):**
```python
if ukc_min_m is not None:
    draft_ref_max = max(dfwd, daft)
    required_wl_for_ukc = (
        draft_ref_max + squat_m + safety_allow_m + ukc_min_m
    ) - depth_ref_m
    required_wl_for_ukc = max(required_wl_for_ukc, 0.0)  # 음수 방지
```

---

## 2.6 데이터 검증 및 오류 처리

### 2.6.1 입력 검증

각 변환 함수는 다음과 같은 검증을 수행합니다:

1. **파일 존재 확인**
   - `Path.exists()` 체크
   - 파일이 없으면 명확한 오류 메시지와 함께 `FileNotFoundError`

2. **JSON 구조 검증**
   - 예상된 최상위 키 존재 확인 (`tanks`, `rows` 등)
   - 데이터 타입 검증 (list, dict 등)

3. **필수 컬럼 검증**
   - CSV: 필수 컬럼 존재 여부 확인
   - JSON: 필수 필드 존재 여부 확인
   - 누락 시 `ValueError`와 함께 누락된 컬럼 목록 제공

4. **수치 데이터 검증**
   - `pd.to_numeric(..., errors="coerce")`로 안전한 변환
   - NaN 값 처리 (드롭 또는 기본값 할당)

### 2.6.2 좌표계 일관성 검증

**검증 항목:**
- `x_from_mid_m` 범위: 일반적으로 `[-LPP_M/2, +LPP_M/2]` 범위 내
- `LCF_m` 범위: 일반적으로 `[-2.0, +2.0]` m 범위 내 (선박 설계에 따라 다름)

**일관성 체크:**
- 파이프라인 전체에서 동일한 상수 사용 (`LPP_M = 60.302`, `MIDSHIP_FROM_AP_M = 30.151`)
- 모든 변환 함수에서 동일한 좌표계 변환 공식 사용

### 2.6.3 오류 복구 전략

1. **부분 실패 허용**
   - 일부 탱크 변환 실패 시 나머지 탱크는 계속 처리
   - 최종적으로 빈 결과가 되면 `ValueError` 발생

2. **로깅**
   - 변환 과정의 주요 단계를 콘솔에 출력
   - 오류 발생 시 상세한 컨텍스트 정보 제공

3. **기본값 할당**
   - 선택적 파라미터는 합리적인 기본값 사용
   - 예: `pump_rate_tph = 100.0`, `priority_weight = 5.0`

---

## 2.7 CSV 스키마 요약

### 2.7.1 Tank SSOT Schema

```python
{
    "Tank": str,                    # Required
    "Capacity_t": float,            # Required, > 0
    "x_from_mid_m": float,          # Required, +AFT/-FWD
    "Current_t": float,             # Required, ≥ 0, ≤ Capacity_t
    "Min_t": float,                 # Required, ≥ 0
    "Max_t": float,                 # Required, ≥ Min_t, ≤ Capacity_t
    "mode": str,                    # Required, "FILL_DISCHARGE"|"FILL_ONLY"|"DISCHARGE_ONLY"|"BLOCKED"|"FIXED"
    "use_flag": str,                # Required, "Y"|"N"
    "pump_rate_tph": float,         # Required, > 0
    "priority_weight": float        # Required, > 0 (낮을수록 우선)
}
```

### 2.7.2 Hydro Table SSOT Schema

```python
{
    "Tmean_m": float,               # Required, sorted ascending, > 0
    "TPC_t_per_cm": float,          # Required, > 0
    "MTC_t_m_per_cm": float,        # Required, > 0
    "LCF_m": float,                 # Required, +AFT/-FWD
    "LBP_m": float                  # Required, > 0 (typically 60.302)
}
```

### 2.7.3 Stage Table SSOT Schema

```python
{
    "Stage": str,                   # Required
    "Current_FWD_m": float,         # Required
    "Current_AFT_m": float,         # Required
    "FWD_MAX_m": float,             # Required, > 0
    "AFT_MIN_m": float,             # Required, > 0
    "FWD_Limit_m": float,           # Optional (Optimizer)
    "AFT_Limit_m": float,           # Optional (Optimizer)
    "Trim_Abs_Limit_m": float,      # Optional (Optimizer)
    "D_vessel_m": float,            # Optional, > 0
    "Forecast_Tide_m": float,       # Optional (UKC)
    "DepthRef_m": float,            # Optional (UKC), > 0
    "UKC_Min_m": float              # Optional (UKC), ≥ 0
}
```

---

## 2.8 Tank SSOT 후처리 (센서 데이터 및 Overrides)

Tank SSOT CSV 생성 후, 다음 후처리 단계가 수행됩니다:

### 2.8.1 Current_t 센서 데이터 주입 (v3.1 업데이트)

PLC/IoT 시스템에서 제공하는 센서 CSV 파일을 읽어 Tank SSOT의 `Current_t` 값을 자동 주입합니다.

#### 자동 탐색 기능 (v3.1)

**함수**: `resolve_current_t_sensor_csv()`

**탐색 순서:**
1. 명시적 `--current_t_csv` 인자
2. 고정 경로 후보:
   - `inputs_dir/current_t_sensor.csv`
   - `inputs_dir/current_t.csv`
   - `inputs_dir/sensors/current_t_sensor.csv`
   - `inputs_dir/sensors/current_t.csv`
   - `inputs_dir/plc/current_t.csv`
   - `inputs_dir/iot/current_t.csv`
3. **Fallback 자동 탐색** (v3.1 신규):
   - 탐색 디렉토리: `inputs_dir`, `inputs_dir/sensors`, `base_dir`, `base_dir/sensors`
   - 패턴: `current_t_*.csv`, `current_t-*.csv`
   - 선택 기준: 최신 수정 시간 (mtime) 우선

#### 주입 함수

**함수**: `inject_current_t_from_sensor_csv()`

**입력**: 센서 CSV (`sensors/current_t_final_verified.csv` 등)

**전략**:
- `override` (기본값): 모든 값 덮어쓰기
- `fill_missing`: 0.0인 경우만 주입

**매칭**:
- 정확 매칭: `LRFO.P` → `LRFO.P`
- 베이스 이름 매칭: `FWB1` → `FWB1.P`, `FWB1.S`

#### diff_audit.csv 생성 (v3.1 신규)

**위치**: `ssot/diff_audit.csv`

**컬럼**:
- `Tank`, `TankKey`, `TankBase`
- `CurrentOld_t`, `ComputedNew_t`, `Delta_t`
- `ClampedFlag` (N/Y), `Updated` (Y/N)
- `SkipReason` (NO_MATCH 등)

**용도**:
- 센서 주입 이력 추적
- 주입 전/후 값 비교
- Clamping 여부 확인

**참고**: 상세 내용은 `Ballast Pipeline 운영 가이드.MD` 섹션 5 참조.

### 2.8.2 Tank Overrides 적용

Site 프로파일의 `tank_overrides` 섹션에 정의된 특정 탱크의 설정을 Tank SSOT에 적용합니다.

- **함수**: `apply_tank_overrides_from_profile()`
- **입력**: 프로파일 JSON의 `tank_overrides` 객체
- **지원 오버라이드**: `mode`, `use_flag`, `pump_rate_tph`, `Min_t`, `Max_t`, `priority_weight`
- **매칭**: 정확 매칭 또는 베이스 이름 매칭 (예: `VOID3` → `VOID3.P`, `VOID3.S`)

**참고**: 상세 내용은 `Ballast Pipeline 운영 가이드.MD` 섹션 4.1 및 3.3 참조.

---

## 2.9 Excel Generation과 SSOT (2024-12-23 업데이트)

### 2.9.1 Excel이 stage_results.csv를 읽는 이유

기존에는 Excel 생성(`create_roro_sheet()`)이 하드코딩된 cfg를 사용했으나, **2024-12-23 패치 이후** `stage_results.csv`를 직접 읽어 TR 위치를 동적으로 결정합니다.

**변경 전 (중복 cfg 문제):**
```python
# agi_tr_patched_v6_6_defsplit_v1.py
# Line 4070: 구버전 cfg
cfg = {
    "FR_TR2_STOW": 40.00,  # 구버전 값
}

# Line 7494: 신버전 cfg
cfg = {
    "FR_TR2_STOW": 29.39,  # 최신 값
}
```
- 문제: Excel과 CSV가 서로 다른 cfg 사용 가능
- 결과: Stage 6C TR 위치 불일치 (x=-9.50m vs x=0.76m)

**변경 후 (SSOT 통일):**
```python
# agi_tr_patched_v6_6_defsplit_v1.py - create_roro_sheet() 내부
import csv
from pathlib import Path

stage_results_path = Path("stage_results.csv")
if stage_results_path.exists():
    print("[INFO] Reading TR positions from stage_results.csv (SSOT)")
    stage_data = {}
    with open(stage_results_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            stage_name = row.get('Stage', '')
            x_stage_m = float(row.get('x_stage_m', 0.0))
            stage_data[stage_name] = {'x': x_stage_m}

    # x (m from midship) → Frame 번호 변환
    def x_to_fr(x_m: float) -> float:
        return 30.151 - x_m

    cfg = {
        "W_TR": 271.20,
        "FR_TR2_STOW": x_to_fr(stage_data.get('Stage 6C', {}).get('x', 0.76)),
        # x=0.76m → Fr=29.391
    }
    print(f"[INFO] cfg from stage_results.csv: {cfg}")
```

**효과:**
- Excel과 CSV가 **동일한** `stage_results.csv` 데이터 사용
- TR 위치 데이터 단일화 (Single Source of Truth)
- Excel/CSV 불일치 문제 완전 해결

### 2.9.2 Draft Clipping 로직

Stage 데이터가 선박의 물리적 한계(`D_vessel` = 3.65m, molded depth)를 초과하면 자동으로 clip합니다.

**구현 위치:** `build_stage_table_from_stage_results()` 함수 내부

```python
D_vessel_m = 3.65  # LCT BUSHRA molded depth (keel to main deck)

# Draft clipping
if dfwd > D_vessel_m:
    print(f"[WARNING] Draft clipped: FWD {dfwd:.2f} -> {D_vessel_m:.2f}m")
    dfwd = D_vessel_m

if daft > D_vessel_m:
    print(f"[WARNING] Draft clipped: AFT {daft:.2f} -> {D_vessel_m:.2f}m")
    daft = D_vessel_m

# Freeboard 계산
freeboard_fwd = D_vessel_m - dfwd
freeboard_aft = D_vessel_m - daft
freeboard_min = min(freeboard_fwd, freeboard_aft)
```

**실제 예시 (Stage 6C):**

| 항목 | stage_results.csv (Input) | pipeline_stage_QA.csv (Output) | 비고 |
|------|---------------------------|-------------------------------|------|
| x_stage_m | 0.76m | - | LCF (even keel) |
| Dfwd_m (calculated) | 3.80m | 3.65m | Clipped to D_vessel |
| Daft_m (calculated) | 3.80m | 3.65m | Clipped to D_vessel |
| Trim_cm | 0.0 | 0.0 | Even keel maintained |
| Freeboard_Min_m | - | 0.00m | **⚠️ Deck edge at waterline** |

**파이프라인 로그 예시:**
```
[WARNING] Draft values clipped to D_vessel (3.65m) for 1 stages:
  - Stage 6C: FWD 3.80 -> 3.65m, AFT 3.80 -> 3.65m
```

### 2.9.3 Freeboard = 0.00m 위험성 및 완화 방안

**위험:**
- Draft = D_vessel → **Deck edge at waterline**
- 파도/swell로 인한 **green water** (deck wet) 가능성
- 화물 손상, 안전 위험

**완화 방안:**

**1. Tidal Assist (권장)**
```
Mina Zayed Tidal Data (Jan 1-5, 2026):
- High Tide: 2.10-2.22m (Chart Datum)
- Effective Freeboard: Freeboard_calc + Tide_height
- Stage 6C 예시: 0.00m + 2.22m = +2.22m 실효 freeboard
```

**2. D_allow 재설정 (대안)**
```python
# 현재: D_allow = 3.65m (zero freeboard)
# 권장: D_allow = 3.35m (safety margin +0.30m)

D_allow_revised = 3.35  # m
Required_deballast = (Current_Draft - D_allow_revised) * TPC
# Stage 6C 예시: (3.65 - 3.35) * 10.5 ≈ 3.15 t
```

**3. 운영 제약**
- 기상 조건: Sea state ≤ 2
- 실시간 draft 모니터링
- 비상 deballast 계획 준비

### 2.9.4 데이터 흐름 다이어그램 (업데이트)

```
┌─────────────────────────────────────────────────────────┐
│          SOURCE DATA (JSON - Single Source)             │
├─────────────────────────────────────────────────────────┤
│  tank_catalog_from_tankmd.json                         │
│  Hydro_Table_Engineering.json                          │
│  stage_results.csv (from Step 1b) ⭐ NEW: Excel도 사용  │
└──────────────────────┬──────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        ↓              ↓              ↓
   [Step 1]       [Pipeline]     [Step 2-4]
   Excel Gen      SSOT Conv      OPS/Solver
        ↓              ↓              ↓
   ✅ Reads        Converts       Consumes
   stage_results   to SSOT CSV    SSOT CSV
        ↓              ↓              ↓
   Excel =        Stage QA       Ballast
   CSV data       (clipped)      Plans
```

---

## 2.10 GM 검증 및 FSM 통합 (v3.1 신규)

### 2.10.1 GM 2D Grid 통합

**파일**: `LCT_BUSHRA_GM_2D_Grid.json`

**구조**:
```json
{
  "description": "LCT BUSHRA GM 2D Grid",
  "grid_axis": "disp_x_trim",  // 표준 축: DISP×TRIM
  "disp": [3200, 3400, 3600, ...],  // Displacement (t)
  "trim": [-1.5, -1.0, -0.5, ...],  // Trim (m)
  "gm_grid": [
    [1.552, 1.598, ...],  // gm_grid[disp_idx][trim_idx]
    ...
  ]
}
```

**축 정렬 규칙**:
- 파이프라인 엔진 기준: `DISP×TRIM` (`gm_grid[disp_idx][trim_idx]`)
- 입력 Grid가 `TRIM×DISP`인 경우 자동 전치

### 2.10.2 CLAMP 감지

**상태**: `VERIFY_CLAMP_RANGE`

**조건**:
- `Disp < disp_min` → `CLAMP_LOW`
- `Disp > disp_max` → `CLAMP_HIGH`
- `Trim < trim_min` → `CLAMP_LOW`
- `Trim > trim_max` → `CLAMP_HIGH`

**영향**:
- GM 값이 Grid 경계값으로 강제 보정
- 제출용으로는 `VERIFY` 상태 (범위 확장 필요)

### 2.10.3 FSM (Free Surface Moment) 통합

**파일**: `Tank_FSM_Coeff.json`

**구조** (nested 지원):
```json
{
  "tanks": {
    "LRFO.P": {"fsm_tm_max": 45.2},
    "LRFO.S": {"fsm_tm_max": 45.2},
    ...
  }
}
```

**계산**:
- `FSM_total_tm = Σ fsm_from_coeff(tank, fill_pct)`
- `GM_eff = GM_raw - (FSM_total_tm / Displacement)`

**상태**:
- `FSM_status = OK`: 계수 존재, 계산 완료
- `FSM_status = MISSING_COEFF`: 부분 채워진 탱크 존재하나 계수 없음
- `FSM_status = NOT_REQUIRED`: 부분 채워진 탱크 없음

### 2.10.4 GM 검증 출력

**파일**: `gm_stability_verification_v2b.csv`

**주요 컬럼**:
- `GM_raw_m`: Grid에서 보간된 GM
- `GM_grid_source`: Grid 파일 경로 또는 "fallback_minimal_safe_1.50"
- `GM_is_fallback`: fallback 사용 여부
- `FSM_status`: FSM 상태 (OK/MISSING_COEFF/NOT_REQUIRED)
- `FSM_total_tm`: 총 FSM (t·m)
- `GM_eff_m`: 유효 GM (GM_raw - FSM/Δ)
- `Status`: GOOD/MINIMUM/FAIL/VERIFY_CLAMP_RANGE/VERIFY_FSM_MISSING

**참고**: 상세 내용은 `verify_gm_stability_v2b.py` 스크립트 참조.

---

## 2.11 Tide Integration 데이터 흐름 (AGI-only, v3.3 신규)

### 2.11.1 Tide Stage Mapping (Pre-Step)

**입력 파일:**
- `bplus_inputs/water tide_202512.xlsx` (time-series tide data)
  - `datetime_gst`: Timestamp (GST)
  - `tide_m (Chart Datum)`: Tide height (m, CD)
- `bplus_inputs/tide_windows_AGI.json` (stage time windows)
  - `windows`: Array of `{Stage, start, end, stat, note}`
  - `stat`: "min" or "mean" (tide statistic selection)

**처리:**
- `tide_stage_mapper.py` 실행 (Pre-Step)
- 각 Stage의 time window에 대해 min/mean tide 추출
- Stage alias 매핑 지원 (예: "Stage 6 50% TR2 loaded (HOLD)" → "Stage 6A_Critical (Opt C)")

**출력:**
- `stage_tide_AGI.csv`
  - `StageKey`: Stage name
  - `Forecast_tide_m`: Stage-wise tide (m, CD)
  - `tide_src`: "window_min" or "window_mean"
  - `tide_qc`: "OK", "VERIFY", or "MISSING_WINDOW"

### 2.11.2 Stage Table Merge (Step 1b)

**Merge 로직:**
- `stage_table_unified.csv` 생성 시 `stage_tide_AGI.csv` merge
- `Forecast_Tide_m` 컬럼 추가 (stage_tide에서 overwrite)
- `DatumOffset_m` 컬럼 추가 (CLI `--datum_offset` 파라미터)
- `Tide_Source`, `Tide_QC` 컬럼 추가 (데이터 출처 추적)

**SSOT 규칙 (v3.6 업데이트, 2025-12-29):**
- `Forecast_Tide_m` 우선순위:
  0. CLI `--forecast_tide` (최우선, 명시적으로 제공된 경우 모든 Stage에 직접 적용)
  1. `stage_tide_AGI.csv` (CLI가 없을 때만 사용)
  2. `tide_table` + `stage_schedule` 보간 (옵션)
  3. CLI `--forecast_tide` (fillna, 안전장치)
- `DatumOffset_m`는 CLI 파라미터가 SSOT (기본값: 0.0 m)

**변경 사항 (2025-12-29):**
- CLI `--forecast_tide` 값이 최우선으로 적용되어 `stage_table_unified.csv`와 `solver_ballast_summary.csv` 간 `Forecast_Tide_m` 완전 일치 보장
- 자세한 내용은 `17_TIDE_UKC_Calculation_Logic.md` 섹션 17.6.5 참조

### 2.11.3 UKC 계산 (Step 3)

**계산식 (고정):**
- `AvailableDepth_m = DepthRef_m + DatumOffset_m + Forecast_tide_m`
- `UKC_fwd_m = AvailableDepth_m - (Dfwd_m + Squat_m + SafetyAllow_m)`
- `UKC_aft_m = AvailableDepth_m - (Daft_m + Squat_m + SafetyAllow_m)`
- `UKC_min_calc_m = min(UKC_fwd_m, UKC_aft_m)`
- `Tide_required_m = max(0.00, (Draft_ref_m + Squat_m + SafetyAllow_m + UKC_min_m) - (DepthRef_m + DatumOffset_m))`
- `Tide_margin_m = Forecast_tide_m - Tide_required_m`

**Tide Verdict:**
- `FAIL`: `Tide_margin_m < 0.00`
- `LIMIT`: `0.00 ≤ Tide_margin_m < 0.10`
- `OK`: `Tide_margin_m ≥ 0.10`
- `VERIFY`: `Tide_QC == "VERIFY"` (missing window or data quality issue)

### 2.11.4 QA CSV Alias Columns

**pipeline_stage_QA.csv에 추가되는 alias 컬럼:**
- `Forecast_tide_m` ← `Forecast_Tide_m`
- `Tide_required_m` ← `Required_WL_for_UKC_m`
- `UKC_min_m` ← `UKC_Min_Required_m`
- `UKC_fwd_m` ← `UKC_FWD_m`
- `UKC_aft_m` ← `UKC_AFT_m`

**목적:** 사용자 친화적 컬럼명 제공, 일관성 유지

### 2.11.5 AUTO-HOLD Warnings

**Trigger 조건:**
- Holdpoint stages: Stage 2, Stage 6A_Critical (Opt C)
- `Tide_margin_m < 0.10` (10cm margin threshold)

**출력:**
- `gate_fail_report.md`에 자동 삽입
- 형식: `**HOLD**: {stage_name} Tide_margin_m={value:.3f} (< 0.10m)`

### 2.11.6 Consolidated Excel TIDE_BY_STAGE Sheet

**생성 위치:** `merge_excel_files_to_one()` 함수
**데이터 소스:** `pipeline_stage_QA.csv`
**컬럼:**
- `Stage`, `Forecast_tide_m`, `Tide_required_m`, `Tide_margin_m`
- `UKC_min_m`, `UKC_fwd_m`, `UKC_aft_m`, `Tide_verdict`

---

## 2.12 SPMT Integration 데이터 흐름 (v3.3 신규)

### 2.12.1 SPMT Cargo Input Generation

**입력:**
- `spmt/cargo_spmt_inputs_config_example.json` (SPMT config)
- `stage_results.csv` (SSOT, optional for SSOT mapping)

**처리:**
- `spmt_unified.py integrate` 실행
  - `cargo-autofill` → `Cargo_SPMT_Inputs.xlsx`
  - `shuttle-builder` → `stage_loads.csv`, `stage_summary.csv`
  - `stage-autocalc` → `Stage_Results` (with SSOT mapping)
  - `lct-shuttle` → `LCT_Stages_Summary` (optional)

**출력:**
- `SPMT_Integrated_Complete.xlsx`
  - `Stage_Config`: SSOT parameters
  - `Cargo_SPMT_Inputs`: Cargo data
  - `Stage_Results`: SSOT-mapped stage results
  - `Stage-wise Cargo on Deck`: Bryan format

### 2.12.2 Bryan Template Integration

**입력:**
- `SPMT_Integrated_Complete.xlsx` (from Step 5a)
- `stage_results.csv` (SSOT)

**처리:**
- `bryan_template_unified.py one-click` 실행
  - `create` → `Bryan_Submission_Data_Pack_Template.xlsx`
  - `populate` → Uses `stage_results.csv`
  - `--spmt-xlsx` → Imports SPMT cargo into `04_Cargo_SPMT` sheet

**출력:**
- `Bryan_Submission_Data_Pack_Populated.xlsx`
  - `04_Cargo_SPMT`: SPMT cargo data
  - `07_Stage_Calc`: Stage calculations
  - `06_Stage_Plan`: Stage-wise cargo positions

### 2.12.3 Coordinate System Alignment

**SPMT ↔ Pipeline:**
- **SPMT uses:** `x_from_midship = midship_from_ap_m - Fr(m)`
- **Pipeline uses:** Same formula (AGENTS.md Method B)
- **Midship reference:** 30.151 m from AP (consistent)

**Stage Definition Alignment:**
- SPMT stages: Stage 1, 2, 3, 4, 5, 5_PreBallast, 6A_Critical, 6C, 7
- Pipeline stages: Same 9-stage set (from `stage_results.csv`)
- SSOT enforcement: Stage names must match exactly

---

## 2.14 Ballast Sequence 데이터 흐름 (Option 2, v3.5 신규)

### 2.14.1 옵션 계획 vs 실행 시퀀스 분리

**문제점:**
- 기존 `BALLAST_SEQUENCE.csv`에 Delta_t/Target_t NaN 문제
- Stage 6B가 실행 시퀀스에 혼입되어 Start_t/Target_t 누적 오류 발생
- 계획 레벨과 실행 레벨이 혼재

**해결 (Option 2):**
- **BALLAST_OPTION.csv**: 계획/옵션 레벨 (Delta_t 중심, 모든 Stage 포함)
- **BALLAST_EXEC.csv**: 실행 시퀀스 (Start_t/Target_t 체인, Stage 6B 제외)

### 2.14.2 BALLAST_OPTION.csv 구조

**목적:** 계획 레벨에서 모든 Stage의 ballast 변경사항을 Delta_t 중심으로 표현

**컬럼:**
- `Stage`: Stage name (모든 Stage 포함, Stage 6B 포함)
- `Tank`: Tank ID
- `Action`: FILL/DISCHARGE
- `Delta_t`: Mass change (t)
- `PumpRate_tph`: Pump rate (t/h)
- `Priority`: 1=highest (critical), 2=PreBallast, 3=Standard, 5=Optional (Stage 6B)
- `Rationale`: Why this action is needed

**특징:**
- Start_t/Target_t 없음 (Delta_t만)
- 모든 Stage 포함 (Stage 6B 포함)
- Priority 및 Rationale로 계획 의도 명확화

### 2.14.3 BALLAST_EXEC.csv 구조

**목적:** 실행 레벨에서 단계별 Start_t/Target_t 체인을 명확히 표현

**컬럼:**
- `Stage`: Stage name (Stage 6B 제외)
- `Step`: Sequential step number
- `Tank`: Tank ID
- `Action`: FILL/DISCHARGE
- `Start_t`: Start mass (t, 이전 step의 Target_t에서 carry-forward)
- `Target_t`: Target mass (t, Start_t + Delta_t)
- `Delta_t`: Mass change (t)
- `Time_h`: Duration (h)
- `Pump_ID`: Pump identifier
- `PumpRate_tph`: Pump rate (t/h)
- `Valve_Lineup`: Valve IDs
- `Hold_Point`: Y/N
- `Draft_FWD`, `Draft_AFT`, `Trim_cm`, `UKC`: Predicted conditions
- `Notes`: Warnings/notes

**핵심 로직:**
```python
# Tank state tracking across steps (carry-forward)
tank_state: Dict[str, float] = initial_tank_current.copy()

for step in sequence:
    tank_id = step.tank
    # Start_t = current tank state (carry-forward from previous step)
    start_t = tank_state.get(tank_id, 0.0)
    target_t = start_t + step.delta_t

    # Update tank state for next step
    tank_state[tank_id] = target_t
```

**특징:**
- Start_t/Target_t 체인: 동일 탱크에 대한 연속 작업 시 상태 유지
- Stage 6B 제외: OPTIONAL_STAGES 상수로 필터링
- Tank capacity validation: Target_t > Capacity_t 시 클리핑

### 2.14.4 Stage 6B 분리 로직

**OPTIONAL_STAGES 상수:**
```python
OPTIONAL_STAGES = [
    "Stage 6B Tide Window",  # 옵션/분석 시나리오 - 실행 시퀀스에서 제외
]
```

**필터링:**
```python
stage_order = _stage_order_from_df(ballast_plan_df)
if exclude_optional_stages:
    stage_order = [s for s in stage_order if s not in OPTIONAL_STAGES]
```

**결과:**
- `BALLAST_OPTION.csv`: Stage 6B 포함 (계획 레벨)
- `BALLAST_EXEC.csv`: Stage 6B 제외 (실행 레벨)

### 2.14.5 데이터 흐름 다이어그램

```
┌─────────────────────────────────────────────────────────┐
│          SOLVER/OPTIMIZER OUTPUT                        │
├─────────────────────────────────────────────────────────┤
│  solver_ballast_stage_plan.csv                         │
│    └─> Stage, Tank, Delta_t/Weight_t                    │
└──────────────────────┬──────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        ↓              ↓              ↓
   [Option Plan]  [Exec Sequence]  [Legacy]
        ↓              ↓              ↓
BALLAST_OPTION.csv  BALLAST_EXEC.csv  BALLAST_SEQUENCE.csv
(모든 Stage)       (Stage 6B 제외)   (호환성)
        ↓              ↓              ↓
   Priority        Start_t/Target_t  기존 형식
   Rationale       Carry-forward
   Delta_t         Time_h
```

---

## 2.15 Option 1 패치 제안 (AGI 제출 가능성 개선, 미구현)

### 배경

AGI 제출 가능성 검증 결과, 다음 3가지 패치가 필요합니다:

1. **Bryan Pack Forecast_tide_m 주입**
   - 문제: `Bryan_Submission_Data_Pack_Populated.xlsx`의 `07_Stage_Calc`에 `Forecast_tide_m` 미주입
   - 해결: `pipeline_stage_QA.csv`에서 `Forecast_tide_m`을 읽어 `stage_results.csv`에 병합 후 populate
   - 구현 위치: `integrated_pipeline` Step 5 (Bryan Pack 생성 전)

2. **Stage 5_PreBallast GateB Critical 강제**
   - 문제: `Stage 5_PreBallast`가 GateB critical 적용 대상으로 잡히지 않음
   - 해결: `_is_critical_stage()` 함수에 명시적 체크 추가
   - 구현 위치: `integrated_pipeline` Gate 계산 로직

3. **Current_* vs Draft_* 단일화**
   - 문제: `pipeline_stage_QA.csv`에 `Current_*`와 `Draft_*`가 동시 존재하여 혼란
   - 해결: QA 생성 시 `Current_*` 컬럼 제거 또는 `Draft_*`로 통일
   - 구현 위치: `generate_stage_QA_csv()` 함수

**상세 내용:** `02_IMPLEMENTATION_REPORTS/20251228/OPTION1_OPTION2_AGI_SUBMISSION_PATCHES_20251228.md` 참조

---

## 2.17 실행 파일 → 출력 파일 → 헤더 구조 매핑 (v3.7 신규)

### 2.17.1 파이프라인 실행 흐름 → 출력 파일 → 헤더 구조

#### Step 0: SPMT Cargo Generation (선택적)
- **실행 파일**: `spmt v1/agi_spmt_unified.py`
- **출력 파일**: `AGI_SPMT_Shuttle_Output.xlsx`
- **생성 헤더**:
  - `Stage_Summary`: `Stage`, `Stage_Name`, `Total_onDeck_t`, `LCG_x_from_Midship_m`, `LCG_Fr_from_AP_m`, `Note`
  - `Stage_Loads`: `Stage`, `Stage_Name`, `Item`, `Weight_t`, `Fr_m_from_AP`, `x_m_from_Midship`
  - `Stage_Results`: `Stage`, `Cargo Total(t) [calc]`, `LCGx(m) [calc]`, `Cargo Total(t) [SSOT]`, `LCGx(m) [SSOT]`, `ΔCargo(t)`, `ΔLCGx(m)`, `Note`
  - `Stage-wise Cargo on Deck`: Stage_Results와 동일 (8개 컬럼)

#### Step 1: TR Excel Generation (선택적)
- **실행 파일**: `agi_tr_patched_v6_6_defsplit_v1.py`
- **출력 파일**: `LCT_BUSHRA_AGI_TR_Final_v*.xlsx`
- **생성 헤더**:
  - `Ballast_Tanks`: `TankName`, `x_from_mid_m`, `max_t`, `SG`, `use_flag`, `air_vent_mm`
  - `CONST_TANKS`: `Tank`, `Type`, `Weight_t`, `LCG_m`, `FSM_mt_m`, `Remarks`
  - `Hydro_Table`: `Disp_t`, `Tmean_m`, `Trim_m`, `GM_m`, `Draft_FWD`, `Draft_AFT`, `LCF_m_from_midship`, `MCTC_t_m_per_cm`, `TPC_t_per_cm`, `GM_min_m`, `LCF_m`, `KM_m`
  - `Hourly_FWD_AFT_Heights`: `DateTime (GST)`, `Tide_m`, `Dfwd_req_m (even)`, `Trim_m (optional)`, `Dfwd_adj_m`, `Daft_adj_m`, `Ramp_Angle_deg`, `Status`, `FWD_Height_m`, `AFT_Height_m`, `Notes`

#### Step 1b: stage_results.csv 생성 (필수)
- **실행 파일**: `agi_tr_patched_v6_6_defsplit_v1.py csv`
- **출력 파일**: `stage_results.csv`
- **생성 헤더**: `Stage`, `Dfwd_m`, `Daft_m`, `Disp_t`, `Tmean_m`, `Trim_cm` 등
- **SSOT 역할**: 이후 모든 리포트/검증 스크립트의 Stage 정의 SSOT

#### Step 2: OPS Integrated Report
- **실행 파일**: `ops_final_r3_integrated_defs_split_v4_patched_TIDE_v1.py`
- **출력 파일**: `OPS_FINAL_R3_AGI_Ballast_Integrated.xlsx`
- **생성 헤더**:
  - `Stage_Calculations`: 37개 컬럼 (Stage, Description, Mass_t, LCG_m, FWD_m, AFT_m, Trim_cm, Mean_m, Forecast_Tide_m, Water_Level_m, Max_Draft_m, Freeboard_Min_m, Gate_FWD_Max, Gate_AFT_Min, Gate_Freeboard, GM_m, GM_min_m, LCF_used_m, MCTC_used, TPC_used, FWD_Margin_m, AFT_Margin_m, Discharge_Needed_t, Status, Engineering_Grade, PreBallast_t, UKC_Min_m, Required_WL_m, Tide_required_m, Forecast_tide_m, Tide_margin_m, UKC_min_m, UKC_fwd_m, UKC_aft_m, UKC_min_actual_m, Gate_UKC, Gate_Overall)
  - `Tank_SSOT`: `Tank_ID`, `Category`, `Location`, `Fr_Start`, `Fr_End`, `Capacity_t`, `LCG_stern_m`, `LCG_midship_m`, `TCG_m`, `TCG_Side`, `VCG_m`
  - `Discharge_Matrix`: `Tank_ID`, `Capacity_t`, `LCG_m`, `Delta_FWD_per_10t_cm`, `Priority`, `Priority_Label`, `Effectiveness`, `Operational_Status`
  - `BWRB_Log`: `Date/Time`, `Operation`, `Tank_ID`, `Amount_t`, `Source`, `Destination`, `FWD_Before_m`, `FWD_After_m`, `Port_Approval`, `Master_Sign`, `BWMP_Status`

#### Step 3: Ballast Gate Solver (LP)
- **실행 파일**: `tide/ballast_gate_solver_v4_TIDE_v1.py`
- **출력 파일**:
  - `solver_ballast_plan.csv`
  - `solver_ballast_summary.csv` (TIDE_v1: 8개 Tide 컬럼)
  - `solver_ballast_stage_plan.csv`
  - `solver_state_trace.csv`
- **생성 헤더**:
  - `solver_ballast_summary.csv`: `Stage`, `Forecast_tide_m`, `DepthRef_m`, `UKC_min_m`, `Tide_required_m`, `Tide_margin_m`, `UKC_fwd_m`, `UKC_aft_m`, `Tide_verdict` (TIDE_v1 버전)
  - `solver_ballast_stage_plan.csv`: `Stage`, `Tank`, `Action`, `Delta_t`, `Target_t`, `Current_t` 등

#### Step 4: Ballast Optimizer (선택적)
- **실행 파일**: `Untitled-2_patched_defsplit_v1_1.py`
- **출력 파일**: `optimizer_ballast_plan.xlsx`
- **생성 헤더**:
  - `Plan`: `Stage`, `Tank`, `Action`, `Weight_t`, `Start_%`, `End_%`, `Time_h`
  - `Summary`: `Stage`, `Current_FWD_m`, `Current_AFT_m`, `New_FWD_m`, `New_AFT_m`, `ΔW_t`, `PumpTime_h`, `viol_fwd_m`
  - `Tank Log`: `Tank`, `UseFlag`, `Mode`, `Freeze`, `x_from_mid_m`, `Start_t`, `Δt_t`, `End_t`, `Min_t`, `Max_t`
  - `BWRB Log`: `Vessel`, `Location`, `Lat`, `Lon`, `Date`, `Start`, `End`, `Tank`, `Operation`, `Volume_m3`, `Weight_t`, `Officer`, `MasterVerified`, `Remarks`

#### Step 4b: Ballast Sequence Generator (선택적)
- **실행 파일**: `ballast_sequence_generator.py` (import 모듈)
- **출력 파일**:
  - `BALLAST_EXEC.csv` (17개 컬럼)
  - `BALLAST_OPTION.csv` (7개 컬럼)
  - `BALLAST_SEQUENCE.csv` (19개 컬럼)
  - `BALLAST_SEQUENCE.xlsx` (3개 시트: Ballast_Exec, Ballast_Option, Ballast_Sequence)
- **생성 헤더**:
  - `BALLAST_EXEC.csv`: `Stage`, `Step`, `Tank`, `Action`, `Start_t`, `Target_t`, `Delta_t`, `Time_h`, `Pump_ID`, `PumpRate_tph`, `Valve_Lineup`, `Hold_Point`, `Draft_FWD`, `Draft_AFT`, `Trim_cm`, `UKC`, `Notes`
  - `BALLAST_OPTION.csv`: `Stage`, `Tank`, `Action`, `Delta_t`, `PumpRate_tph`, `Priority`, `Rationale`
  - `BALLAST_SEQUENCE.csv`: BALLAST_EXEC (17개) + `Valve_Sequence`, `Valve_Notes` (2개 추가)

#### Step 4c: Valve Lineup Generator (선택적)
- **실행 파일**: `valve_lineup_generator.py` (import 모듈)
- **출력 파일**: `BALLAST_SEQUENCE_WITH_VALVES.md`
- **역할**: Ballast Sequence에 밸브 라인업 정보 추가

#### Step 5: Bryan Template Generation
- **실행 파일**: `tide/bryan_template_unified_TIDE_v1.py`
- **의존 스크립트**:
  - `create_bryan_excel_template_NEW.py` (subprocess)
  - `populate_template.py` (import 임베디드)
- **출력 파일**: `Bryan_Submission_Data_Pack_Populated.xlsx`
- **생성 헤더**:
  - `07_Stage_Calc`: Row 20 헤더 (33-35개 컬럼) - `Stage_ID`, `HoldPoint`, `GateB_Critical`, `Stage_Remark`, `Progress_%`, `x_stage_m`, `W_stage_t`, `Displacement_t`, `Tmean_m`, `Trim_cm`, `Draft_FWD_m`, `Draft_AFT_m`, `Freeboard_min_m`, `Tide_required_m`, `Forecast_tide_m`, `Tide_margin_m`, `UKC_min_m`, `UKC_fwd_m`, `UKC_aft_m`, `Ramp_angle_deg`, `GM_m`, `Gate_FWD`, `Gate_AFT`, `Gate_TRIM`, `Gate_UKC`, `Gate_RAMP`, `HoldPoint_Band`, `Go/No-Go`, `Ballast_Action`, `Ballast_Time_h`, `Ballast_Net_t`, `Ballast_Alloc`, `Notes`
  - `01_SSOT_Master`: `Control / Input`, `Value`, `Unit`, `Notes`, `Owner`, `Source/Ref`
  - `02_Vessel_Hydro`: `#`, `Disp_t`, `Tmean_m`, `TPC_t/cm`, `MTC_t·m/cm`, `LCF_m`, `GM_m`, `Source/Remark`
  - `03_Berth_Tide`: `Field`, `Value`, `Unit`, `Notes`, `Source`
  - `04_Cargo_SPMT`: `Item`, `Weight_t`, `CoG_x_m`, `CoG_y_m`, `CoG_z_m`, `Final_Frame`, `Ramp_Frame`, `L_m`, `W_m`, `Remarks/Source`
  - `05_Ballast_Tanks`: 다중 섹션 구조
  - `06_Stage_Plan`: `Stage_ID`, `Progress_%`, `Planned_Start`, `Planned_End`, `HoldPoint`, `GateB_Critical(Y/N)`, `Stage_Status`, `Remarks`
  - `08_HoldPoint_Log`: Row 2 헤더 (12개 컬럼)
  - `09_Evidence_Log`: `Site`, `Category`, `Document / Evidence Item`, `Req`, `Status`, `Due/Submitted`, `Portal`, `Ref No.`, `File/Link`, `Remarks`
  - `10_RACI`: `Activity / Deliverable`, `SCT Logistics`, `DSV/3PL`, `Vessel Master`, `Chief Officer/Ballast`, `Port Authority`, `HSE`, `Notes`
  - `11_Assumptions_Issues`: `ID`, `Type`, `Description`, `Value`, `Unit`, `Impact`, `Owner`, `Due`, `Status`, `Evidence/Ref`
  - `12_DataDictionary`: `Sheet`, `Field`, `Unit`, `Type`, `Definition / Rule`

#### 후처리: Excel 통합 및 최종화
- **실행 파일**:
  - `tide/excel_com_recalc_save.py` (선택적, COM 재계산)
  - `tide/ballast_excel_finalize.py` (자동 실행)
- **출력 파일**: `PIPELINE_CONSOLIDATED_AGI_*.xlsx`
- **생성 헤더**:
  - 기본 CSV 헤더 + 확장 컬럼 28개 (Draft/Freeboard/Gate 관련)
  - 버전별 차이: 14개 시트 (213110) vs 29개 시트 (205824/213758)

### 2.17.2 헤더 확장 패턴

**Consolidated Excel 확장 컬럼 (28개)**:
1. `Draft_FWD_m_solver`
2. `Draft_AFT_m_solver`
3. `Draft_Source`
4. `Forecast_tide_m`
5. `DepthRef_m`
6. `UKC_min_m`
7. `UKC_fwd_m`
8. `UKC_aft_m`
9. `Tide_required_m`
10. `Tide_margin_m`
11. `Tide_verdict`
12. `Freeboard_Min_m`
13. `Freeboard_Min_BowStern_m`
14. `Freeboard_FWD_m`
15. `Freeboard_AFT_m`
16. `Gate_AFT_MIN_2p70_PASS`
17. `AFT_Margin_2p70_m`
18. `Gate_B_Applies`
19. `Gate_FWD_MAX_2p70_critical_only`
20. `FWD_Margin_2p70_m`
21. `Gate_Freeboard_ND`
22. `Freeboard_Req_ND_m`
23. `Freeboard_ND_Margin_m`
24. `D_vessel_m`
25. `Draft_Max_raw_m`
26. `Draft_Max_solver_m`
27. `Draft_Clipped_raw`
28. `Draft_Clipped_solver`

**확장 패턴 적용 대상**:
- `BALLAST_EXEC.csv` (17개) → `Sequence_Ballast_Exec` (45개)
- `BALLAST_OPTION.csv` (7개) → `Sequence_Ballast_Option` (35개)
- `BALLAST_SEQUENCE.csv` (19개) → `Sequence_Ballast_Sequence` (47개)
- `TIDE_BY_STAGE` 기본 (9개) → 확장 (35개)
- `OPS Stage_Calculations` (37개) → Consolidated (56-58개)
- `Optimizer Plan` (7개) → Consolidated (27-35개)
- `Optimizer Summary` (8개) → Consolidated (28-36개)

### 2.17.3 SSOT 데이터 흐름 (실행 파일 관점)

```
Step 1b (stage_results.csv)
  → Step 2 (OPS 리포트)
  → Step 3 (Solver 입력: stage_table_unified.csv)
  → Step 4 (Optimizer 입력)
  → Step 4b (Sequence Generator 입력)
  → Step 5 (Bryan Template 입력)
  → Consolidated Excel (최종 통합)
```

**SSOT 계층**:
1. **Stage 정의 SSOT**: `stage_results.csv` (Step 1b)
2. **Tank SSOT**: `tank_ssot_for_solver.csv` (Pipeline 생성)
3. **Hydro SSOT**: `hydro_ssot_for_solver.csv` (Pipeline 생성)
4. **Stage Table SSOT**: `stage_table_unified.csv` (Pipeline 생성, Tide/UKC 포함)

**참고**: 상세 실행 파일 목록은 `00_System_Architecture_Complete.md` 섹션 8 참조.

---

## 2.18 다음 장 안내

- **제3장**: 파이프라인 실행 흐름 - Step-by-Step 실행 순서와 서브프로세스 관리
- **제4장**: LP Solver 로직 - 선형 프로그래밍 수학적 모델
- **제5장**: Definition-Split과 Gates - 개념 및 구현 상세
- **GM 검증**: `verify_gm_stability_v2b.py` - CLAMP 감지, FSM 검증, GM_eff 계산
- **파이프라인 실행 파일 목록**: `00_System_Architecture_Complete.md` 섹션 8 - 전체 실행 파일 목록 및 매핑

---

**참고:**
- 제1장: 파이프라인 아키텍처 개요
- `Ballast Pipeline 운영 가이드.MD`: 센서 데이터 통합 및 프로파일 시스템 상세
- `integrated_pipeline_defsplit_v2.py`: 변환 함수 구현
- `verify_gm_stability_v2b.py`: GM 검증 스크립트
- `tide_stage_mapper.py`: Tide stage mapping (AGI-only)
- `spmt_unified.py`: SPMT unified entrypoint
- `03_DOCUMENTATION/AGENTS.md`: 좌표계, Gate 정의, Tank Direction SSOT
- `03_DOCUMENTATION/Pipeline Integration.md`: SPMT/Tide integration 상세
- `00_System_Architecture_Complete.md`: 파이프라인 실행 파일 전체 목록 (섹션 8)
- 2025-12-16 문서: Definition-Split 요구사항

**문서 버전:** v3.7 (실행 파일 → 출력 파일 → 헤더 매핑 추가)
**최종 업데이트:** 2025-12-29
