# Ballast Pipeline 운영 가이드

**작성일:** 2025-12-21
**버전:** v2.5 (Updated: 2025-12-29)
**대상:** 운영자, 개발자, 시스템 관리자

**최신 업데이트 (v2.5 - 2025-12-29):**
- 파이프라인 실행 파일 전체 목록 추가 (21개 파일, 카테고리별 분류)
- 실행 방식별 분류 (subprocess, import 모듈, 동적 import)
- 활성화 조건 및 의존성 관계 명시

**최신 업데이트 (v2.4 - 2025-12-29):**
- Forecast_Tide_m 우선순위 변경: CLI `--forecast_tide` 값이 최우선 적용
  - `--forecast_tide` 옵션 사용 시 모든 Stage에 직접 적용되어 `stage_table_unified.csv`와 `solver_ballast_summary.csv` 간 일관성 보장
  - 자세한 내용: `17_TIDE_UKC_Calculation_Logic.md` 섹션 17.6.5 참조

**최신 업데이트 (v2.3 - 2025-12-28):**
- Option 2 구현 완료: Step 4b Ballast Sequence Generator (옵션/실행 분리)
  - `BALLAST_OPTION.csv`: 계획 레벨 (Delta_t 중심, 모든 Stage 포함)
  - `BALLAST_EXEC.csv`: 실행 시퀀스 (Start_t/Target_t carry-forward, Stage 6B 제외)
  - `BALLAST_SEQUENCE.xlsx`: Excel (Ballast_Option, Ballast_Exec, Ballast_Sequence sheets)
- Option 1 패치 제안 (미구현): Bryan Pack Forecast_tide_m 주입, Stage 5_PreBallast critical 적용

**최신 업데이트 (v2.2 - 2024-12-23):**
- 섹션 14: 패치 이력 추가 (2024-12-23)
- Excel/CSV 일관성 패치, 알려진 제약사항 및 완화 방안

---

## 목차

1. [개요](#1-개요)
2. [파이프라인 구조 및 실행 흐름](#2-파이프라인-구조-및-실행-흐름)
3. [주요 함수 상세 설명](#3-주요-함수-상세-설명)
4. [프로파일 시스템](#4-프로파일-시스템)
5. [센서 데이터 통합](#5-센서-데이터-통합)
6. [SSOT 변환 로직](#6-ssot-변환-로직)
7. [Gate FAIL 리포트](#7-gate-fail-리포트)
8. [CLI 옵션 완전 가이드](#8-cli-옵션-완전-가이드)
9. [운영 절차 및 예제](#9-운영-절차-및-예제)
10. [문제 해결 가이드](#10-문제-해결-가이드)
11. [모범 사례](#11-모범-사례)

---

## 1. 개요

### 1.1 목적

Ballast Pipeline은 선박의 Ballast Management 작업을 자동화하고 최적화하기 위한 통합 파이프라인입니다. 4개의 독립 스크립트를 순차 실행하여 다음을 수행합니다:

- **Definition Split**: 조위 예보와 요구 수면고 분리
- **Gate Unified System**: FWD/AFT/Freeboard/UKC 동시 강제
- **Linear Programming 최적화**: LP 기반 Ballast 계획 수립
- **자동화 워크플로우**: 4개 스크립트 순차 실행 자동화

### 1.2 핵심 특징

- **Site-Agnostic**: AGI/DAS 모두 동일 로직(파라미터만 변경)
- **SSOT**: JSON → CSV 변환 표준화
- **Iterative Refinement**: Hydrostatic Table 재보간으로 정확도 향상
- **Definition-Split Enforcement**: Draft/Freeboard/UKC 개념 분리

---

## 2. 파이프라인 구조 및 실행 흐름

### 2.1 전체 실행 흐름

```
START
  │
  ▼
[Site Profile 로딩] (AGI/DAS JSON)
  │
  ▼
[Step 1] TR Excel Generation (선택적)
  │
  ▼
[Step 1b] stage_results.csv 생성 (TR script CSV 모드)
  │
  ▼
[PREP] SSOT CSV 변환 (Tank, Hydro, Stage)
  │
  ├─→ [Current_t 센서 주입] (PLC/IoT CSV)
  │
  ├─→ [Tank Overrides 적용] (프로파일에서)
  │
  ▼
[Gate FAIL 리포트 생성] (자동)
  │
  ▼
[Step 2] OPS Integrated Report (Excel + Markdown)
  │
  ▼
[Step 3] Ballast Gate Solver (LP 최적화)
  │
  ▼
[Step 4] Ballast Optimizer (선택적)
  │
  ▼
END (Summary 출력)
```

### 2.2 실행 제어 옵션

```bash
# 전체 실행 (Step 1~4)
python integrated_pipeline_defsplit_v2.py

# Step 1~3만 실행 (Optimizer 제외)
python integrated_pipeline_defsplit_v2.py --to_step 3

# Step 2부터 실행 (Step 1 스킵, 이미 stage_results.csv 있음)
python integrated_pipeline_defsplit_v2.py --from_step 2

# Site 지정
python integrated_pipeline_defsplit_v2.py --site AGI
python integrated_pipeline_defsplit_v2.py --site DAS
```

### 2.3 출력 디렉토리 구조

```
pipeline_out_<timestamp>/
├── ssot/                              # SSOT CSV 파일
│   ├── tank_ssot_for_solver.csv
│   ├── hydro_table_for_solver.csv
│   ├── stage_table_unified.csv
│   └── pipeline_stage_QA.csv
│
├── logs/                              # 실행 로그
│   ├── 01_TR_EXCEL.log
│   ├── 02_TR_STAGE_CSV.log
│   ├── 03_OPS_INTEGRATED.log
│   ├── 04_SOLVER_LP.log
│   └── 05_OPTIMIZER.log
│
├── solver_ballast_plan.csv           # Step 3 출력
├── solver_ballast_summary.csv
├── solver_ballast_stage_plan.csv
│
├── OPS_FINAL_R3_AGI_Ballast_Integrated.xlsx  # Step 2 출력
├── OPS_FINAL_R3_Report_Integrated.md
│
├── optimizer_plan.csv                # Step 4 출력
├── optimizer_summary.csv
├── optimizer_bwrb_log.csv
├── optimizer_tank_log.csv
├── optimizer_ballast_plan.xlsx
│
├── BALLAST_OPTION.csv              # Step 4b 출력 (Option 2, 계획 레벨)
├── BALLAST_EXEC.csv                # Step 4b 출력 (Option 2, 실행 시퀀스)
├── BALLAST_SEQUENCE.csv            # Step 4b 출력 (Legacy, 호환성)
├── BALLAST_SEQUENCE.xlsx           # Step 4b 출력 (Excel, 3개 시트)
├── BALLAST_OPERATIONS_CHECKLIST.md # Step 4b 출력
├── BALLAST_SEQUENCE_WITH_VALVES.md # Step 4c 출력
├── HOLD_POINT_SUMMARY.csv          # Step 4b 출력
│
└── gate_fail_report.md               # Gate FAIL 자동 리포트
```

### 2.4 파이프라인 실행 파일 목록 (v2.5 업데이트)

**최신 검증일**: 2025-12-29
**총 실행 파일 수**: 21개 (중복 제외, 모듈 포함)

#### 2.4.1 필수 실행 파일 (Main Pipeline Steps)

| Step | 스크립트 파일명 | 기본 경로 | 실행 방식 | 설명 |
|------|---------------|---------|----------|------|
| **Step 0** | `agi_spmt_unified.py` | `spmt v1/agi_spmt_unified.py` | `subprocess` | SPMT cargo 입력 생성 (선택적) |
| **Step 1** | `agi_tr_patched_v6_6_defsplit_v1.py` | `agi_tr_patched_v6_6_defsplit_v1.py` | `subprocess` | TR Excel 생성 (선택적) |
| **Step 1b** | `agi_tr_patched_v6_6_defsplit_v1.py` | 동일 | `subprocess` | `stage_results.csv` 생성 (필수, csv 모드) |
| **Step 2** | `ops_final_r3_integrated_defs_split_v4_patched_TIDE_v1.py` | `ops_final_r3_integrated_defs_split_v4_patched_TIDE_v1.py` | `subprocess` | OPS Integrated 리포트 (Excel + MD) |
| **Step 3** | `ballast_gate_solver_v4_TIDE_v1.py` | `tide/ballast_gate_solver_v4_TIDE_v1.py` | `subprocess` | Ballast Gate Solver (LP) |
| **Step 4** | `Untitled-2_patched_defsplit_v1_1.py` | `Untitled-2_patched_defsplit_v1_1.py` | `subprocess` | Ballast Optimizer (선택적) |
| **Step 5** | `bryan_template_unified_TIDE_v1.py` | `tide/bryan_template_unified_TIDE_v1.py` | `subprocess` | Bryan Template 생성 및 채움 |

#### 2.4.2 선택적 실행 파일 (Optional Steps)

| Step | 스크립트 파일명 | 기본 경로 | 실행 방식 | 활성화 조건 |
|------|---------------|---------|----------|------------|
| **Step 4b** | `ballast_sequence_generator.py` | `ballast_sequence_generator.py` | `import` (모듈) | `--enable-sequence` |
| **Step 4b** | `checklist_generator.py` | `checklist_generator.py` | `import` (모듈) | `--enable-sequence` |
| **Step 4c** | `valve_lineup_generator.py` | `valve_lineup_generator.py` | `import` (모듈) | `--enable-valve-lineup` |

#### 2.4.3 의존 실행 파일 (Dependencies)

| 부모 스크립트 | 의존 스크립트 | 기본 경로 | 실행 방식 | 설명 |
|-------------|-------------|---------|----------|------|
| `bryan_template_unified_TIDE_v1.py` | `create_bryan_excel_template_NEW.py` | `create_bryan_excel_template_NEW.py` | `subprocess` | Bryan Template 생성 (Step 5 내부) |
| `bryan_template_unified_TIDE_v1.py` | `populate_template.py` | `populate_template.py` | `import` (임베디드) | Template 채움 로직 (Step 5 내부) |

#### 2.4.4 후처리 및 유틸리티

| 카테고리 | 스크립트 파일명 | 기본 경로 | 활성화 조건 |
|---------|---------------|---------|------------|
| **후처리** | `ballast_excel_finalize.py` | `tide/ballast_excel_finalize.py` | 파일 존재 시 자동 실행 |
| **후처리** | `excel_com_recalc_save.py` | `tide/excel_com_recalc_save.py` | `EXCEL_COM_RECALC_OUT` 환경 변수 |
| **유틸리티** | `compile_headers_registry.py` | `compile_headers_registry.py` | `HEADERS_MASTER.xlsx` 존재 시 |
| **유틸리티** | `debug_report.py` | `debug_report.py` | `--debug_report` 또는 `--auto_debug_report` |

#### 2.4.5 모듈 의존성 (Module Dependencies)

| 모듈 경로 | 사용 위치 | 실행 방식 | 설명 |
|---------|---------|----------|------|
| `ssot.gates_loader` | Step 4b | `import` | `SiteProfile`, `load_agi_profile` (프로파일 로딩) |
| `ssot.data_quality_validator` | Step 3, Step 4b | `import` | `DataQualityValidator` (Tidying First Implementation) |
| `tide.tide_ukc_engine` | 여러 Step | `import` | Tide/UKC 계산 SSOT 엔진 |
| `tide.tide_constants` | 여러 Step | `import` | Tide/UKC 상수 |

#### 2.4.6 Pre-Step 실행 파일 (선택적)

| 스크립트 파일명 | 기본 경로 | 실행 방식 | 활성화 조건 | 설명 |
|---------------|---------|----------|------------|------|
| `tide_stage_mapper.py` | `tide_stage_mapper.py` | 수동 실행 (Pre-Step) | `--tide_windows` 제공 시 | Stage별 조위 매핑 (AGI-only) |

#### 2.4.7 실행 파일 통계

| 카테고리 | 개수 | 비고 |
|---------|------|------|
| **필수 실행 파일 (subprocess)** | 4개 | Step 1b, Step 2, Step 3 (항상 실행) |
| **선택적 실행 파일 (subprocess)** | 3개 | Step 0, Step 1, Step 4, Step 5 |
| **선택적 실행 파일 (import 모듈)** | 3개 | Step 4b, Step 4c |
| **의존 실행 파일** | 2개 | Bryan Template 내부 호출 |
| **후처리 실행 파일** | 2개 | Excel 최종화 |
| **유틸리티 실행 파일** | 2개 | Headers registry 컴파일, Debug report |
| **모듈 의존성** | 4개 | SSOT 모듈들 (import) |
| **Pre-Step 실행 파일** | 1개 | Tide mapping (수동 실행) |
| **총계** | **21개** | (중복 제외, 모듈 포함) |

**참고**:
- 모든 실행 파일은 `integrated_pipeline_defsplit_v2_gate270_split_v3_auditpatched_autodetect_TIDE_v1.py`에서 호출됩니다.
- 스크립트 경로는 `resolve_script_path()` 함수로 자동 탐색됩니다 (`tide/` 디렉토리에서 실행해도 상위 폴더 스크립트 자동 인식).
- 자세한 목록은 `파이프라인 전체 아키텍처, 실행 파일, 로직 상세 설명.MD` 섹션 2.11 참조.

---

## 3. 주요 함수 상세 설명

### 3.1 프로파일 관리 함수

#### `resolve_site_profile_path()`

**위치:** `integrated_pipeline_defsplit_v2.py:226-250`

**기능:** Site 프로파일 JSON 경로 해결

**우선순위:**

1. 명시적 `--profile_json` 인자
2. `inputs_dir/profiles/{SITE}.json`
3. `inputs_dir/profiles/{site}.json`
4. `inputs_dir/profiles/site_{SITE}.json`
5. `inputs_dir/site_profile_{SITE}.json`

**예시:**

```python
profile_path = resolve_site_profile_path(
    profile_arg="",  # CLI에서 제공 안함
    base_dir=Path("/path/to/base"),
    inputs_dir=Path("/path/to/inputs"),
    site="AGI"
)
# → Path("/path/to/inputs/profiles/AGI.json")
```

#### `load_site_profile_json()`

**위치:** `integrated_pipeline_defsplit_v2.py:253-258`

**기능:** 프로파일 JSON 로딩 및 검증

**반환:** `Dict[str, object]` - 프로파일 데이터

#### `apply_site_profile_overrides()`

**위치:** `integrated_pipeline_defsplit_v2.py:261-283`

**기능:** 프로파일 값을 `argparse.Namespace`에 적용(CLI 플래그가 명시되지 않은 경우만)

**파라미터 매핑:**

```python
keymap = {
    "fwd_max_m": ("fwd_max", "--fwd_max"),
    "aft_min_m": ("aft_min", "--aft_min"),
    "aft_max_m": ("aft_max", "--aft_max"),
    "trim_abs_limit_m": ("trim_abs_limit", "--trim_abs_limit"),
    "pump_rate_tph": ("pump_rate", "--pump_rate"),
    "forecast_tide_m": ("forecast_tide", "--forecast_tide"),
    "depth_ref_m": ("depth_ref", "--depth_ref"),
    "ukc_min_m": ("ukc_min", "--ukc_min"),
    "squat_m": ("squat", "--squat"),
    "safety_allow_m": ("safety_allow", "--safety_allow"),
    "tank_keywords": ("tank_keywords", "--tank_keywords"),
    "current_t_csv": ("current_t_csv", "--current_t_csv"),
}
```

### 3.2 센서 데이터 통합 함수

#### `resolve_current_t_sensor_csv()`

**위치:** `integrated_pipeline_defsplit_v2.py:286-305`

**기능:** Current_t 센서 CSV 경로 해결

**탐색 순서:**

1. 명시적 `--current_t_csv` 인자
2. `inputs_dir/current_t_sensor.csv`
3. `inputs_dir/current_t.csv`
4. `inputs_dir/sensors/current_t_sensor.csv`
5. `inputs_dir/sensors/current_t.csv`
6. `inputs_dir/plc/current_t.csv`
7. `inputs_dir/iot/current_t.csv`

#### `inject_current_t_from_sensor_csv()`

**위치:** `integrated_pipeline_defsplit_v2.py:308-500`

**기능:** 센서 CSV에서 Current_t 값을 Tank SSOT에 주입

**지원 센서 컬럼 (대소문자 무시):**

- **Tank 식별자:** `Tank`, `tank_id`, `id`, `tag`, `name`
- **값 컬럼 (우선순위):**
  1. `Current_t`, `current_ton`, `current_tons`, `tons`, `ton`, `amount_t`, `value_t`
  2. `level_pct`, `level_percent`, `level_%` (Capacity_t 사용하여 변환)
  3. `volume_m3`, `vol_m3`, `m3` + 선택적 `spgr` (기본 1.0)

**전략:**

- **`override`**: 센서 값으로 덮어쓰기(기본값)
- **`fill_missing`**: Current_t가 0.0인 경우만 주입

**매칭 로직:**

1. **정확 매칭:** 센서의 `Tank` 컬럼과 SSOT의 `Tank` 컬럼 정확 일치 (대소문자 무시)
2. **그룹 매칭:** 베이스 이름 매칭 (예: `FWB1` → `FWB1.P`, `FWB1.S`에 균등 분배)

**예시:**

```python
sensor_stats = inject_current_t_from_sensor_csv(
    tank_ssot_csv=Path("ssot/tank_ssot_for_solver.csv"),
    sensor_csv=Path("sensors/current_t_sensor.csv"),
    strategy="override",
    out_csv=Path("ssot/tank_ssot_for_solver.csv")
)
# 반환: {
#   "sensor_csv": "sensors/current_t_sensor.csv",
#   "strategy": "override",
#   "value_mode": "Current_t",
#   "updated_exact": 15,
#   "updated_group": 3,
#   "bad_value_rows": [],
#   "tank_rows": 50
# }
```

### 3.3 Tank Overrides 함수

#### `apply_tank_overrides_from_profile()`

**위치:** `integrated_pipeline_defsplit_v2.py:506-612`

**기능:** 프로파일의 `tank_overrides`를 Tank SSOT에 적용

**프로파일 구조:**

```json
{
  "tank_overrides": {
    "VOID3": {
      "mode": "FIXED",
      "use_flag": "Y"
    },
    "FWCARGO1": {
      "mode": "FIXED",
      "use_flag": "N"
    }
  }
}
```

**지원 오버라이드 컬럼:**

- `use_flag` (str): "Y" | "N"
- `mode` (str): "FILL_DISCHARGE" | "DISCHARGE_ONLY" | "FILL_ONLY" | "FIXED" | "BLOCKED"
- `pump_rate_tph` (float)
- `Min_t`, `Max_t` (float)
- `priority_weight` (float)

**매칭 로직:**

- **정확 매칭:** Tank 이름 정확 일치 (대소문자 무시)
- **베이스 매칭:** `.` 이전 부분으로 매칭 (예: `VOID3` → `VOID3.P`, `VOID3.S` 모두 매칭)

### 3.4 SSOT 변환 함수

#### `convert_tank_catalog_json_to_solver_csv()`

**위치:** `integrated_pipeline_defsplit_v2.py:794-1035`

**기능:** Tank 카탈로그 JSON을 Solver용 CSV로 변환

**입력 형식:**

```json
{
  "tanks": [
    {
      "id": "FWB2",
      "category": "fresh_water_ballast",
      "lcg_m": 25.0,
      "tcg_m": 0.0,
      "vcg_m": 1.5,
      "cap_t": 50.0,
      "loc": "AFT"
    }
  ]
}
```

**출력 CSV 컬럼:**

- `Tank`: 탱크 식별자
- `Capacity_t`: 용량 (tons)
- `x_from_mid_m`: Midship 기준 X 좌표 (+AFT / -FWD)
- `Current_t`: 현재 중량 (tons, 기본 0.0)
- `Min_t`, `Max_t`: 최소/최대 중량 (tons)
- `mode`: 운영 모드
- `use_flag`: 사용 플래그 ("Y" | "N")
- `pump_rate_tph`: 펌프 속도 (t/h)
- `priority_weight`: 우선순위 가중치

**좌표 변환:**

```python
x_from_mid_m = MIDSHIP_FROM_AP_M - lcg_from_ap_m
# MIDSHIP_FROM_AP_M = 30.151 m (상수)
```

**키워드 필터링:**

- `include_keywords`에 포함된 키워드가 탱크 ID나 카테고리에 있으면 `use_flag="Y"`
- 기본값: `["BALLAST", "VOID", "FWB", "FW", "DB"]`
- 프로파일에서 `tank_keywords`로 오버라이드 가능

#### `convert_hydro_engineering_json_to_solver_csv()`

**위치:** `integrated_pipeline_defsplit_v2.py:1038-1183`

**기능:** Hydrostatic Table JSON을 Solver용 CSV로 변환

**필수 컬럼:**

- `Tmean_m`: 평균 Draft (m)
- `TPC_t_per_cm`: TPC (tons per cm)
- `MTC_t_m_per_cm`: MTC (tons m per cm) 또는 `MCTC_t_m_per_cm`
- `LCF_m`: LCF (m from midship) 또는 `LCF_m_from_midship`
- `LBP_m`: LBP (m, 없으면 기본값 사용)

**컬럼 정규화:**

- `MCTC_t_m_per_cm` → `MTC_t_m_per_cm`
- `LCF_m_from_midship` → `LCF_m`

#### `build_stage_table_from_stage_results()`

**위치:** `integrated_pipeline_defsplit_v2.py:1186-1292`

**기능:** `stage_results.csv`로부터 Solver/Optimizer용 Stage Table 생성

**입력 CSV 컬럼:**

- `Stage`: Stage 이름
- `Dfwd_m` 또는 `FWD_m`: Forward Draft (m)
- `Daft_m` 또는 `AFT_m`: Aft Draft (m)

**출력 CSV 컬럼:**

- `Stage`: Stage 이름
- `Current_FWD_m`, `Current_AFT_m`: 현재 Draft
- `FWD_MAX_m`, `AFT_MIN_m`: Solver용 게이트
- `FWD_Limit_m`, `AFT_Limit_m`, `Trim_Abs_Limit_m`: Optimizer용 제한
- `Forecast_Tide_m`, `DepthRef_m`, `UKC_Min_m`: 선택적 UKC 입력
- `D_vessel_m`: Molded Depth

#### `generate_stage_QA_csv()`

**위치:** `integrated_pipeline_defsplit_v2.py:1295-1414`

**기능:** Definition-split 기반 Stage QA CSV 생성

**계산 항목:**

1. **Freeboard (조위 무관):**

   ```
   Freeboard_FWD_m = D_vessel_m - Draft_FWD_m
   Freeboard_AFT_m = D_vessel_m - Draft_AFT_m
   Freeboard_Min_m = min(Freeboard_FWD, Freeboard_AFT)
   ```
2. **UKC (조위 의존):**

   ```
   Available_Depth = DepthRef_m + Forecast_Tide_m
   UKC_FWD_m = Available_Depth - (Draft_FWD + Squat + Safety)
   UKC_AFT_m = Available_Depth - (Draft_AFT + Squat + Safety)
   UKC_Min_m = min(UKC_FWD, UKC_AFT)
   ```
3. **Required_WL_for_UKC_m (역계산):**

   ```
   Required_WL = (Draft_max + Squat + Safety + UKC_MIN) - DepthRef
   ```

**Gate 검증:**

- `Gate_FWD_Max`: `FWD <= FWD_MAX_m` → "OK" | "NG"
- `Gate_AFT_Min`: `AFT >= AFT_MIN_m` → "OK" | "NG"
- `Gate_Freeboard`: `Freeboard_Min >= 0` → "OK" | "NG"
- `Gate_UKC`: `UKC_Min >= UKC_MIN_m` → "OK" | "NG" | "N/A"

### 3.5 Gate FAIL 리포트 함수

#### `generate_gate_fail_report_md()`

**위치:** `integrated_pipeline_defsplit_v2.py:614-748`

**기능:** Gate 위반 원인 분석 리포트 생성

**리포트 섹션:**

1. **Gate 위반 요약:** FWD_MAX, AFT_MIN, Freeboard, UKC 위반 건수
2. **SSOT(Current_t) 상태:** 탱크 수, Current_t=0.0인 탱크 수, 총 Current_t 합
3. **Sensor Sync 적용 결과:** 주입 통계
4. **UKC 입력 상태:** forecast_tide, depth_ref, ukc_min 등
5. **Stage별 Gate 상태:** 상세 테이블 (최대 50행)
6. **자동 원인 추정(Heuristics):**
   - Current_t가 전부 0.0인 경우
   - Freeboard_Min < 0인 경우
   - UKC Gate가 N/A인 경우
7. **권고 조치:** 개선 방안 제시

#### `append_solver_section_to_gate_report()`

**위치:** `integrated_pipeline_defsplit_v2.py:751-789`

**기능:** Solver 실행 후 결과를 Gate 리포트에 추가

**추가 내용:**

- Solver 출력 파일 존재 여부
- Solver Summary 주요 값 (New_FWD_m, New_AFT_m, 위반값 등)

### 3.6 실행 제어 함수

#### `step_run_script()`

**위치:** `integrated_pipeline_defsplit_v2.py:1427-1446`

**기능:** 서브프로세스로 스크립트 실행

**반환:** `StepResult` dataclass

```python
@dataclass
class StepResult:
    ok: bool           # 실행 성공 여부
    returncode: int    # 프로세스 반환 코드 (0=성공)
    log: Path          # 로그 파일 경로
```

**특징:**

- 로그 파일 자동 생성 (`logs/{step_id:02d}_{name}.log`)
- stdout/stderr를 콘솔과 로그에 동시 출력

---

1. 4. 프로파일 시스템

### 4.1 프로파일 구조

**위치:** `profiles/AGI.json`, `profiles/DAS.json`

**예시 (AGI.json):**

```json
{
  "site": "AGI",
  "_notes": "Populate with measured/approved operational values. CLI flags override these.",
  "fwd_max_m": 2.7,
  "aft_min_m": 2.7,
  "aft_max_m": 3.5,
  "trim_abs_limit_m": 2.4,
  "pump_rate_tph": 10.0,
  "tank_keywords": "FWB,VOIDDB,FW2",
  "forecast_tide_m": null,
  "depth_ref_m": null,
  "ukc_min_m": 0.50,
  "squat_m": 0.15,
  "safety_allow_m": 0.20,
  "current_t_csv": "sensors/current_t_sensor.csv",
  "tank_overrides": {
    "VOID3": {
      "mode": "FIXED",
      "use_flag": "Y"
    },
    "FWCARGO1": {
      "mode": "FIXED",
      "use_flag": "N"
    },
    "FWCARGO2": {
      "mode": "FIXED",
      "use_flag": "N"
    }
  },
  "provenance": {
    "_comment": "AGI-002: Captain/Ops Gate values, pump rate, UKC parameters from measured/approved operational limits",
    "trim_abs_limit_m": "Trim envelope ±2.40m (240cm) per LCT BUSHRA AGI TR params",
    "tank_keywords": "Keywords restricted to avoid fuel DB tanks (FODB*) and cargo water tanks (FWCARGO*)"
  }
}
```

### 4.2 파라미터 설명

| 파라미터             | 타입        | 설명                                     | 기본값                         |
| -------------------- | ----------- | ---------------------------------------- | ------------------------------ |
| `fwd_max_m`        | float       | FWD 최대 Draft 게이트 (m)                | 2.70                           |
| `aft_min_m`        | float       | AFT 최소 Draft 게이트 (m, Captain gate)  | 2.70                           |
| `aft_max_m`        | float       | AFT 최대 Draft 제한 (m, Optimizer용)     | 3.50                           |
| `trim_abs_limit_m` | float       | 절대 Trim 제한 (m)                       | 2.40                           |
| `pump_rate_tph`    | float       | 기본 펌프 속도 (t/h)                     | 10.0                           |
| `tank_keywords`    | string      | `use_flag=Y` 마킹용 키워드 (쉼표 구분) | "FWB,VOIDDB,FW2"               |
| `forecast_tide_m`  | float\|null | 예보 조위 (m, CD)                        | null                           |
| `depth_ref_m`      | float\|null | 기준 수심 (m, CD)                        | null                           |
| `ukc_min_m`        | float       | 최소 UKC 요구값 (m)                      | 0.50                           |
| `squat_m`          | float       | Squat 여유 (m)                           | 0.15                           |
| `safety_allow_m`   | float       | 추가 안전 여유 (m)                       | 0.20                           |
| `current_t_csv`    | string      | Current_t 센서 CSV 경로 (상대경로)       | "sensors/current_t_sensor.csv" |
| `tank_overrides`   | object      | 탱크별 오버라이드 설정                   | {}                             |

### 4.3 우선순위 규칙

1. 명시적 CLI 플래그 (예: `--fwd_max 2.8`)
2. 프로파일 JSON 값
3. argparse 기본값

**예시:**

```bash
# 프로파일에서 fwd_max_m=2.7 로드, CLI에서 --fwd_max 2.8 오버라이드
python integrated_pipeline_defsplit_v2.py --site AGI --fwd_max 2.8
# → 실제 사용값: 2.8

# 프로파일에서 fwd_max_m=2.7 사용
python integrated_pipeline_defsplit_v2.py --site AGI
# → 실제 사용값: 2.7
```

---

## 5. 센서 데이터 통합

### 5.1 센서 CSV 형식

**예시:**

```csv
Tank,Current_t,Timestamp
FWB2.P,125.5,2025-12-21T00:00:00Z
FWB2.S,125.3,2025-12-21T00:00:00Z
VOIDDB2.C,50.0,2025-12-21T00:00:00Z
VOID3.P,0.0,2025-12-21T00:00:00Z
VOID3.S,0.0,2025-12-21T00:00:00Z
```

**대체 컬럼 이름 (대소문자 무시):**

- **Tank 식별자:** `Tank`, `tank_id`, `id`, `tag`, `name`
- **값:**
  - 직접: `Current_t`, `current_ton`, `current_tons`, `tons`, `ton`, `amount_t`, `value_t`
  - 비율: `level_pct`, `level_percent`, `level_%` (Capacity_t 사용하여 변환)
  - 부피: `volume_m3`, `vol_m3`, `m3` + 선택적 `spgr` (기본 1.0)

### 5.2 주입 전략

#### `override` (기본값)

센서 값을 항상 사용. SSOT의 Current_t가 이미 값이 있어도 덮어씁니다.

**사용 시나리오:**

- PLC/IoT에서 실시간 값 제공
- 센서 값이 항상 신뢰할 수 있는 경우

#### `fill_missing`

Current_t가 0.0 (또는 거의 0.0)인 경우만 주입합니다.

**사용 시나리오:**

- 센서 값이 일부 탱크에만 있는 경우
- 기존 수동 입력값을 보존하고 싶은 경우

**예시:**

```bash
python integrated_pipeline_defsplit_v2.py \
  --site AGI \
  --current_t_csv sensors/current_t_sensor.csv \
  --current_t_strategy fill_missing
```

### 5.3 매칭 로직

1. **정확 매칭:** Tank 이름 정확 일치 (대소문자 무시)

   - 센서: `FWB2.P` → SSOT: `FWB2.P` ✓
2. **그룹 매칭:** 베이스 이름으로 매칭 후 균등 분배

   - 센서: `FWB1` → SSOT: `FWB1.P`, `FWB1.S` 각각 50%씩

**주의사항:**

- 센서 CSV에 Tank 컬럼이 없으면 오류 발생
- 값 컬럼이 없거나 모든 값이 유효하지 않으면 오류 발생
- 유효하지 않은 값이 있는 행은 무시되고 `bad_value_rows`에 기록

---

## 6. SSOT 변환 로직

### 6.1 SSOT 아키텍처

**Single Source of Truth (SSOT)** 원칙:

- 원본 데이터는 JSON으로 한 번만 정의
- 파이프라인이 표준화된 CSV로 변환
- 모든 스크립트가 동일한 CSV 형식 사용

**데이터 흐름:**

```
JSON (Source) → CSV (SSOT) → Scripts (Consumers)
```

### 6.2 Tank SSOT 변환 상세

**입력:** `tank_catalog_from_tankmd.json`

**변환 과정:**

1. **좌표 변환:**

   ```python
   x_from_mid_m = MIDSHIP_FROM_AP_M - lcg_from_ap_m
   # MIDSHIP_FROM_AP_M = 30.151 m
   ```
2. **use_flag 결정:**

   ```python
   key_blob = f"{tid} {cat}".upper()
   use_flag = "Y" if any(k in key_blob for k in include_keywords) else "N"
   ```
3. **priority_weight 휴리스틱:**

   - `FWB2`: 1.0
   - `VOIDDB2`: 2.0
   - `VOIDDB1`: 3.0
   - 기타: 5.0

**출력:** `tank_ssot_for_solver.csv`

### 6.3 Hydro SSOT 변환 상세

**입력:** `Hydro_Table_Engineering.json`

**컬럼 정규화:**

- `MCTC_t_m_per_cm` → `MTC_t_m_per_cm`
- `LCF_m_from_midship` → `LCF_m`

**출력:** `hydro_table_for_solver.csv`

**필수 컬럼:**

- `Tmean_m`: 평균 Draft
- `TPC_t_per_cm`: TPC
- `MTC_t_m_per_cm`: MTC
- `LCF_m`: LCF
- `LBP_m`: LBP

### 6.4 Stage Table 변환 상세

**입력:** `stage_results.csv`

**필수 컬럼:**

- `Stage` 또는 `stage_name` 또는 `name`
- `Dfwd_m` 또는 `FWD_m`
- `Daft_m` 또는 `AFT_m`

**출력:** `stage_table_unified.csv`

**Solver용 컬럼:**

- `FWD_MAX_m`, `AFT_MIN_m`: 게이트 값

**Optimizer용 컬럼:**

- `FWD_Limit_m`, `AFT_Limit_m`: 상한 제한
- `Trim_Abs_Limit_m`: 절대 Trim 제한

**선택적 컬럼:**

- `Forecast_Tide_m`, `DepthRef_m`, `UKC_Min_m`: UKC 계산용

---

## 7. Gate FAIL 리포트

### 7.1 리포트 생성

파이프라인은 Stage QA CSV 생성 후 자동으로 Gate FAIL 리포트를 생성합니다.

**생성 조건:**

- `--no_gate_report` 플래그가 없는 경우
- Stage QA CSV가 존재하는 경우

**출력 파일:** `gate_fail_report.md`

### 7.2 리포트 구조

#### 1. Gate 위반 요약

```
## 1) Gate 위반 요약

### 2.70m Split Gate Definitions
- Gate-A (Captain): **AFT draft ≥ 2.70 m** (propeller effectiveness in emergency)
- Gate-B (Mammoet, critical RoRo stages): **FWD draft ≤ 2.70 m** (Chart Datum referenced)

- FWD_Max: **3** stage(s)
- AFT_Min: **0** stage(s)
- Freeboard: **1** stage(s)
- UKC: **2** stage(s)
- GateA_AFT_MIN_2p70 (Captain): **1** stage(s)
- GateB_FWD_MAX_2p70_CD (Mammoet): **2** stage(s)
```

#### 2. SSOT(Current_t) 상태 요약

```
## 2) SSOT(Current_t) 상태 요약

- Tanks: 50
- Current_t == 0.0: 45/50
- Total Current_t (sum): 125.500 t

### 2.1 Sensor Sync 적용 결과

- Sensor CSV: sensors/current_t_sensor.csv
- Strategy: override
- Value mode: Current_t
- Updated (exact): 5
- Updated (group): 0
```

#### 3. UKC 입력 상태

```
## 3) UKC 입력 상태

- forecast_tide_m: 0.30
- depth_ref_m: 4.20
- ukc_min_m: 0.50
- squat_m: 0.15
- safety_allow_m: 0.20
```

#### 4. Stage별 Gate 상태

마크다운 테이블 형식으로 최대 50행 표시

**v2.1+ 포함 컬럼:**

- 기존 Gate 컬럼: `Gate_FWD_Max`, `Gate_AFT_Min`, `Gate_Freeboard`, `Gate_UKC`
- Split Gate 컬럼:
  - `GateA_AFT_MIN_2p70_PASS`, `GateA_AFT_MIN_2p70_Margin_m`
  - `GateB_FWD_MAX_2p70_CD_PASS`, `GateB_FWD_MAX_2p70_CD_Margin_m`, `GateB_FWD_MAX_2p70_CD_applicable`

#### 5. 자동 원인 추정(Heuristics)

시스템이 자동으로 감지한 주요 원인:

- **SSOT Current_t가 전부 0.0**: Deballast(Discharge) 기반 해결이 불가/왜곡될 수 있습니다. (센서/초기값 주입 필요)
- **Freeboard_Min_m < 0**: 일부 Stage에서 Draft가 Molded Depth를 초과했습니다.
- **UKC Gate 미평가(N/A)**: forecast_tide / depth_ref / ukc_min 입력이 없으면 UKC 원인 분석이 불가합니다.

#### 6. 권고 조치

- **Current_t 실측/센서 값 주입 후 재실행**
- **Site Profile(AGI/DAS)로 Gate/펌프율/UKC 입력값을 분리 관리**
- **Freeboard 음수 발생 시 Stage 하중/수조선 입력 재검증**

### 7.3 Solver 결과 추가

Step 3 실행 후, Solver 결과가 리포트에 자동 추가됩니다:

```
## 7) Step 3 (Gate Solver) 결과 요약

- solver_ballast_summary.csv: solver_ballast_summary.csv (OK)
- solver_ballast_plan.csv: solver_ballast_plan.csv (OK)
- solver_ballast_stage_plan.csv: solver_ballast_stage_plan.csv (OK)

### Solver Summary (first row)

- New_FWD_m: 2.65
- New_AFT_m: 2.72
- Freeboard_MIN_m: 0.05
- UKC_m: 1.45
- viol_fwd_max_m: 0.0
- viol_aft_min_m: 0.0
- viol_fb_min_m: 0.0
- viol_ukc_min_m: 0.0
```

---

## 8. CLI 옵션 완전 가이드

### 8.1 Site 및 프로파일

| 옵션               | 타입   | 기본값 | 설명                                  |
| ------------------ | ------ | ------ | ------------------------------------- |
| `--site`         | choice | "AGI"  | Site 레이블 ("AGI"\|"DAS")            |
| `--profile_json` | string | ""     | Site 프로파일 JSON 경로 (명시적 지정) |

**예시:**

```bash
python integrated_pipeline_defsplit_v2.py --site AGI
python integrated_pipeline_defsplit_v2.py --profile_json custom_profile.json
```

### 8.2 센서 데이터

| 옵션                     | 타입   | 기본값     | 설명                                   |
| ------------------------ | ------ | ---------- | -------------------------------------- |
| `--current_t_csv`      | string | ""         | Current_t 센서 CSV 경로                |
| `--current_t_strategy` | choice | "override" | 주입 전략 ("override"\|"fill_missing") |

**예시:**

```bash
python integrated_pipeline_defsplit_v2.py \
  --current_t_csv sensors/plc_data.csv \
  --current_t_strategy fill_missing
```

### 8.3 경로 설정

| 옵션             | 타입   | 기본값                                | 설명                             |
| ---------------- | ------ | ------------------------------------- | -------------------------------- |
| `--base_dir`   | string | (스크립트 위치)                       | 4개 스크립트가 있는 디렉토리     |
| `--inputs_dir` | string | `base_dir`                          | 입력 JSON 파일들이 있는 디렉토리 |
| `--out_dir`    | string | `base_dir/pipeline_out_<timestamp>` | 출력 디렉토리                    |

**예시:**

```bash
python integrated_pipeline_defsplit_v2.py \
  --base_dir /path/to/scripts \
  --inputs_dir /path/to/inputs \
  --out_dir /path/to/output
```

### 8.4 실행 제어

| 옵션                 | 타입 | 기본값 | 설명                           |
| -------------------- | ---- | ------ | ------------------------------ |
| `--from_step`      | int  | 1      | 시작 단계 (1~4)                |
| `--to_step`        | int  | 4      | 종료 단계 (1~4)                |
| `--dry_run`        | flag | False  | 경로 해석만 수행하고 종료      |
| `--no_gate_report` | flag | False  | Gate FAIL 리포트 생성 비활성화 |

**예시:**

```bash
# Step 2부터 3까지만 실행
python integrated_pipeline_defsplit_v2.py --from_step 2 --to_step 3

# Dry-run (경로 확인만)
python integrated_pipeline_defsplit_v2.py --dry_run
```

### 8.5 Gate 및 제한값

| 옵션                 | 타입  | 기본값 | 설명                                 |
| -------------------- | ----- | ------ | ------------------------------------ |
| `--fwd_max`        | float | 2.70   | FWD 최대 Draft 게이트 (m)            |
| `--aft_min`        | float | 2.70   | AFT 최소 Draft 게이트 (m)            |
| `--aft_max`        | float | 3.50   | AFT 최대 Draft 제한 (m, Optimizer용) |
| `--trim_abs_limit` | float | 0.50   | 절대 Trim 제한 (m)                   |

**예시:**

```bash
python integrated_pipeline_defsplit_v2.py \
  --fwd_max 2.80 \
  --aft_min 2.65 \
  --aft_max 3.60 \
  --trim_abs_limit 0.60
```

### 8.6 UKC 관련

| 옵션                | 타입  | 기본값 | 설명                |
| ------------------- | ----- | ------ | ------------------- |
| `--forecast_tide` | float | None   | 예보 조위 (m, CD)   |
| `--depth_ref`     | float | None   | 기준 수심 (m, CD)   |
| `--ukc_min`       | float | None   | 최소 UKC 요구값 (m) |
| `--squat`         | float | 0.0    | Squat 여유 (m)      |
| `--safety_allow`  | float | 0.0    | 추가 안전 여유 (m)  |

**예시:**

```bash
python integrated_pipeline_defsplit_v2.py \
  --forecast_tide 0.30 \
  --depth_ref 4.20 \
  --ukc_min 0.50 \
  --squat 0.15 \
  --safety_allow 0.20
```

**UKC 게이트 활성화 조건:**

- `--forecast_tide`, `--depth_ref`, `--ukc_min` 모두 제공 시 활성화
- 일부만 제공하면 해당 파라미터만 Stage Table에 추가 (게이트 비활성화)

### 8.7 데이터 변환 옵션

| 옵션                | 타입   | 기본값                   | 설명                                     |
| ------------------- | ------ | ------------------------ | ---------------------------------------- |
| `--pump_rate`     | float  | 100.0                    | 기본 펌프 속도 (t/h)                     |
| `--tank_keywords` | string | "BALLAST,VOID,FWB,FW,DB" | `use_flag=Y` 마킹용 키워드 (쉼표 구분) |

**예시:**

```bash
python integrated_pipeline_defsplit_v2.py \
  --pump_rate 15.0 \
  --tank_keywords "FWB,VOIDDB,FW2"
```

### 8.8 스크립트 경로 (고급)

| 옵션                   | 타입   | 기본값                                     | 설명            |
| ---------------------- | ------ | ------------------------------------------ | --------------- |
| `--tr_script`        | string | "agi_tr_patched_v6_6_defsplit_v1.py"       | Step 1 스크립트 |
| `--ops_script`       | string | "ops_final_r3_integrated_defs_split_v4.py" | Step 2 스크립트 |
| `--solver_script`    | string | "ballast_gate_solver_v4.py"                | Step 3 스크립트 |
| `--optimizer_script` | string | "Untitled-2_patched_defsplit_v1_1.py"      | Step 4 스크립트 |

### 8.9 입력 파일 (고급)

| 옵션                | 타입   | 기본값                          | 설명                                                                                   |
| ------------------- | ------ | ------------------------------- | -------------------------------------------------------------------------------------- |
| `--tank_catalog`  | string | "tank_catalog_from_tankmd.json" | 탱크 카탈로그 JSON                                                                     |
| `--hydro`         | string | ""                              | Hydrostatic Table JSON (기본:`inputs_dir/bplus_inputs/Hydro_Table_Engineering.json`) |
| `--stage_results` | string | ""                              | Stage 결과 CSV (기본:`base_dir/stage_results.csv`)                                   |

---

## 9. 운영 절차 및 예제

### 9.1 기본 실행 (AGI)

```bash
# 1. 프로파일 확인
cat profiles/AGI.json

# 2. 센서 데이터 확인 (선택)
cat sensors/current_t_sensor.csv

# 3. 파이프라인 실행
python integrated_pipeline_defsplit_v2.py --site AGI

# 4. 출력 확인
ls -la pipeline_out_*/
cat pipeline_out_*/gate_fail_report.md
```

### 9.2 UKC 검증 포함 실행

```bash
python integrated_pipeline_defsplit_v2.py \
  --site AGI \
  --forecast_tide 0.30 \
  --depth_ref 4.20 \
  --ukc_min 0.50 \
  --squat 0.15 \
  --safety_allow 0.20
```

### 9.3 센서 데이터 통합 실행

```bash
# 1. 센서 CSV 준비
# sensors/current_t_sensor.csv

# 2. 파이프라인 실행 (센서 데이터 자동 주입)
python integrated_pipeline_defsplit_v2.py \
  --site AGI \
  --current_t_csv sensors/current_t_sensor.csv \
  --current_t_strategy override
```

### 9.4 부분 실행 (Step 2~3만)

```bash
# Step 1 스킵 (이미 stage_results.csv 있음)
python integrated_pipeline_defsplit_v2.py \
  --site AGI \
  --from_step 2 \
  --to_step 3
```

### 9.5 프로파일 오버라이드

```bash
# 프로파일 값 사용하되, 일부만 CLI로 오버라이드
python integrated_pipeline_defsplit_v2.py \
  --site AGI \
  --fwd_max 2.75 \
  --aft_min 2.65
# → 프로파일의 다른 값들은 그대로 사용, fwd_max와 aft_min만 오버라이드
```

### 9.6 Dry-Run (검증)

```bash
# 실제 실행 없이 경로 및 파일 존재 여부만 확인
python integrated_pipeline_defsplit_v2.py --site AGI --dry_run
```

**출력 예시:**

```
================================================================================
DRY RUN - PATH RESOLUTION
================================================================================
Site:        AGI
Base dir:    C:\...\ballast_pipeline_defsplit_v2_complete
Inputs dir:  C:\...\ballast_pipeline_defsplit_v2_complete
Out dir:     C:\...\ballast_pipeline_defsplit_v2_complete\pipeline_out_20251221_120000

[SCRIPTS]
TR:          C:\...\agi_tr_patched_v6_6_defsplit_v1.py  (OK)
OPS:         C:\...\ops_final_r3_integrated_defs_split_v4.py  (OK)
SOLVER:      C:\...\ballast_gate_solver_v4.py  (OK)
OPTIMIZER:   C:\...\Untitled-2_patched_defsplit_v1_1.py  (OK)

[INPUTS]
Tank catalog: C:\...\tank_catalog_from_tankmd.json  (OK)
Hydro:        C:\...\bplus_inputs\Hydro_Table_Engineering.json  (OK)
StageRes:     C:\...\stage_results.csv  (OK)
```

---

## 10. 문제 해결 가이드

### 10.1 일반적인 오류

#### 오류: `[ERROR] Missing tank catalog`

**원인:** `tank_catalog_from_tankmd.json` 파일이 없음

**해결:**

```bash
# 파일 위치 확인
ls -la tank_catalog_from_tankmd.json

# 또는 --inputs_dir 지정
python integrated_pipeline_defsplit_v2.py --inputs_dir /path/to/inputs
```

#### 오류: `[ERROR] Step-1b failed and stage_results.csv not found`

**원인:** Step 1b (TR script CSV 모드) 실패

**해결:**

```bash
# 로그 확인
cat pipeline_out_*/logs/02_TR_STAGE_CSV.log

# 수동으로 stage_results.csv 생성 후 --from_step 2로 실행
python integrated_pipeline_defsplit_v2.py --from_step 2
```

#### 오류: `[WARN] Current_t injection failed`

**원인:** 센서 CSV 형식 오류 또는 파일 누락

**해결:**

1. 센서 CSV 형식 확인 (Tank 컬럼, 값 컬럼 필수)
2. 경로 확인:
   ```bash
   ls -la sensors/current_t_sensor.csv
   ```
3. `--current_t_csv`로 명시적 지정:
   ```bash
   python integrated_pipeline_defsplit_v2.py --current_t_csv /full/path/to/sensor.csv
   ```

### 10.2 Gate FAIL 문제

#### 문제: 모든 Stage에서 Gate 위반

**가능한 원인:**

1. Current_t가 전부 0.0 → 센서 데이터 주입 필요
2. Gate 값이 너무 엄격 → 프로파일에서 Gate 값 조정
3. Stage 입력(Draft)이 잘못됨 → `stage_results.csv` 검증

**해결:**

```bash
# 1. Gate FAIL 리포트 확인
cat pipeline_out_*/gate_fail_report.md

# 2. Current_t 확인
cat pipeline_out_*/ssot/tank_ssot_for_solver.csv | grep Current_t

# 3. 센서 데이터 주입 후 재실행
python integrated_pipeline_defsplit_v2.py --site AGI --current_t_csv sensors/current_t_sensor.csv
```

#### 문제: UKC Gate가 N/A로 표시

**원인:** UKC 입력값 누락 (`forecast_tide`, `depth_ref`, `ukc_min`)

**해결:**

```bash
# UKC 입력값 제공
python integrated_pipeline_defsplit_v2.py \
  --site AGI \
  --forecast_tide 0.30 \
  --depth_ref 4.20 \
  --ukc_min 0.50
```

### 10.3 성능 문제

#### 문제: 파이프라인 실행이 느림

**가능한 원인:**

1. Step 1 (TR Excel 생성)이 느림
2. Step 3 (Solver) 반복 계산이 많음
3. 대용량 입력 파일

**해결:**

```bash
# Step 1 스킵 (이미 Excel 생성됨)
python integrated_pipeline_defsplit_v2.py --from_step 2

# Step 4 (Optimizer) 스킵 (필요시)
python integrated_pipeline_defsplit_v2.py --to_step 3
```

### 10.4 프로파일 관련 문제

#### 문제: 프로파일이 로드되지 않음

**원인:** 프로파일 파일이 표준 위치에 없음

**해결:**

```bash
# 1. 프로파일 위치 확인
ls -la profiles/AGI.json

# 2. 명시적 지정
python integrated_pipeline_defsplit_v2.py --profile_json profiles/AGI.json

# 3. Dry-run으로 경로 확인
python integrated_pipeline_defsplit_v2.py --site AGI --dry_run
```

#### 문제: 프로파일 값이 적용되지 않음

**원인:** CLI 플래그가 명시적으로 제공되어 프로파일 값이 오버라이드됨

**해결:**

- CLI 플래그 제거하여 프로파일 값 사용
- 또는 프로파일 값을 CLI로 오버라이드 (의도한 경우)

---

## 11. 모범 사례

### 11.1 프로파일 관리

- **실측값 반영:** 프로파일에는 실제 측정/승인된 운영 값을 기록
- **버전 관리:** 프로파일 변경 이력을 Git 등으로 관리
- **프로비넌스 기록:** `provenance` 섹션에 값의 출처 기록

**예시:**

```json
{
  "provenance": {
    "_comment": "AGI-002: Captain/Ops Gate values from 2025-12-15 operational log",
    "fwd_max_m": "Measured max safe FWD draft during load-out",
    "pump_rate_tph": "Pump specification from manufacturer datasheet"
  }
}
```

### 11.2 센서 데이터 관리

- **정기 동기화:** PLC/IoT에서 최신 Current_t 값 정기적으로 가져오기
- **데이터 검증:** 센서 CSV에 유효하지 않은 값이 없는지 확인
- **백업:** 센서 데이터 백업 보관

**예시:**

```bash
# 1. 센서 데이터 수집 (외부 스크립트)
python collect_sensor_data.py --output sensors/current_t_sensor.csv

# 2. 파이프라인 실행
python integrated_pipeline_defsplit_v2.py --site AGI
```

### 11.3 실행 로그 관리

- **로그 검토:** 각 Step 실행 후 로그 파일 확인
- **오류 추적:** 오류 발생 시 `logs/` 디렉토리에서 해당 Step 로그 확인
- **보관:** 중요한 실행 결과는 별도 디렉토리에 보관

**예시:**

```bash
# 실행 후 로그 확인
cat pipeline_out_*/logs/04_SOLVER_LP.log | tail -50

# 중요 실행 결과 백업
cp -r pipeline_out_20251221_120000 /backup/runs/
```

### 11.4 Gate FAIL 분석

- **리포트 우선 확인:** `gate_fail_report.md`를 먼저 확인하여 자동 분석 결과 검토
- **근본 원인 파악:** Heuristics 섹션에서 제시된 원인 검토
- **단계별 검증:** Stage QA CSV → Solver 결과 → Optimizer 결과 순서로 검증

**예시 워크플로우:**

```bash
# 1. 파이프라인 실행
python integrated_pipeline_defsplit_v2.py --site AGI

# 2. Gate FAIL 리포트 확인
cat pipeline_out_*/gate_fail_report.md

# 3. Stage QA CSV 상세 확인
cat pipeline_out_*/ssot/pipeline_stage_QA.csv

# 4. Solver 결과 확인
cat pipeline_out_*/solver_ballast_summary.csv

# 5. 필요시 데이터 수정 후 재실행
```

### 11.5 부분 실행 활용

- **개발/디버깅:** 특정 Step만 실행하여 빠른 반복
- **재계산:** 일부 Step만 재실행하여 시간 절약

**예시:**

```bash
# Solver만 재실행 (Step 1, 2 스킵)
python integrated_pipeline_defsplit_v2.py --from_step 3 --to_step 3

# Optimizer 제외 실행 (빠른 검증)
python integrated_pipeline_defsplit_v2.py --to_step 3
```

### 11.6 Dry-Run 활용

- **실행 전 검증:** 실제 실행 전 경로 및 파일 존재 여부 확인
- **설정 확인:** CLI 옵션이 올바르게 해석되는지 확인

**예시:**

```bash
# 실행 전 검증
python integrated_pipeline_defsplit_v2.py --site AGI --dry_run

# 경로 확인 후 실제 실행
python integrated_pipeline_defsplit_v2.py --site AGI
```

---

## 12. Excel 수식 보존 검증 (배포 전 필수)

### 12.1 개요

파이프라인은 openpyxl로 Excel을 생성한 후 **자동으로 COM 후처리**를 실행합니다. 배포 전 다음 검증을 수행하세요.

### 12.2 Calc_Log 시트 확인 (필수)

**위치:** Excel 파일의 마지막 시트 (Calc_Log)

**확인 항목:**

| 항목 | 기대값 | 확인 |
|------|--------|------|
| FullRebuild_Completed | SUCCESS | [ ] |
| Engine | Python+COM | [ ] |
| ProcessingTime_sec | < 30초 | [ ] |
| Timestamp | 최근 실행 시간 | [ ] |

**예시:**
```
Parameter              | Value       | Timestamp
FullRebuild_Completed | SUCCESS     | 2025-12-25 00:24:11
Engine                | Python+COM  | 2025-12-25 00:24:11
ProcessingTime_sec    | 11.15       | 2025-12-25 00:24:11
```

### 12.3 수식 무결성 검증

**RORO_Stage_Scenarios 시트:**

1. **BC18:BR28 범위 확인**
   - BC18: `Draft_FWD_m_solver` (헤더)
   - BD18: `Draft_AFT_m_solver` (헤더)
   - BC25: Stage 6A FWD draft
   - BD25: Stage 6A AFT draft = **2.70m** ✅

2. **수식 에러 검색**
   - `Ctrl+F` → `#N/A` 검색 → **0건**
   - `#REF!` 검색 → **0건**
   - `#VALUE!` 검색 → **0건**

### 12.4 콘솔 로그 확인

**파이프라인 실행 로그 마지막 부분:**

```
================================================================================
[FORMULA FINALIZE] Running COM post-processing...
================================================================================
[STEP 1/7] Initializing Excel COM...
[STEP 2/7] Opening workbook...
[STEP 3/7] Setting Calculation=Automatic...
[STEP 4/7] RefreshAll()...
[STEP 5/7] CalculateFullRebuild()...
[STEP 6/7] Checking QueryTables & PivotCaches...
[STEP 7/7] Recording build log (Calc_Log sheet)...

✅ SUCCESS - Formula finalization completed!
[OK] Formula finalization completed successfully
  [RESULT] Processing time: 11.15 sec
  [RESULT] File: PIPELINE_CONSOLIDATED_AGI_20251225_002354.xlsx
```

**확인 사항:**
- [ ] `[FORMULA FINALIZE]` 섹션 존재
- [ ] `SUCCESS` 메시지 출력
- [ ] `[RESULT]` 라인 3개 출력
- [ ] 에러 메시지 없음

### 12.5 수동 재계산 테스트 (선택)

**Excel에서 직접 확인:**

1. Excel 파일 열기
2. `Ctrl+Alt+F9` (전체 재계산)
3. 값 변화 없음 확인
4. 저장 후 다시 열기
5. 값 변화 없음 재확인

### 12.6 문제 해결

#### 문제: Calc_Log 시트 없음

**원인:** COM 후처리 실패

**해결:**
```bash
cd new/ballast_pipeline_defsplit_v2_complete
python ballast_excel_finalize.py --auto
```

#### 문제: FullRebuild_Completed = FAIL

**원인:** COM 실행 중 에러

**해결:**
1. Excel 프로세스 종료: `taskkill /f /im EXCEL.EXE`
2. 재실행: `python ballast_excel_finalize.py --auto`

#### 문제: #N/A 에러 발생

**원인:** 외부 참조 또는 이름 범위 오류

**해결:**
1. 참조 대상 시트 확인
2. 이름 관리자 확인 (`Ctrl+F3`)
3. COM 재실행

#### 문제: pywin32 ImportError

**원인:** pywin32 미설치

**해결:**
```bash
pip install pywin32
python -m pywin32_postinstall -install
```

### 12.7 배포 승인 기준

**모든 항목이 ✅여야 배포 가능:**

- [ ] Calc_Log 시트 존재
- [ ] FullRebuild_Completed = SUCCESS
- [ ] 타임스탬프 최근 (< 1일)
- [ ] 수식 에러 0건
- [ ] BC-BR 범위 데이터 완성
- [ ] Stage 6A AFT = 2.70m
- [ ] 콘솔 로그 SUCCESS

### 12.8 참고 문서

- `docs/EXCEL_FORMULA_PRESERVATION.md` - 상세 기술 문서
- `ballast_excel_finalize.py` - COM 후처리 스크립트
- `docs/10_System_Improvements_and_Patches.md` - Patch v3.7 설명
- `docs/03_Pipeline_Execution_Flow.md` - Step 6 설명

---

## 부록 A: 주요 상수

```python
# Vessel Constants
D_VESSEL_M = 4.10  # Molded Depth (m)
LPP_M = 60.302     # Length between Perpendiculars (m)
MIDSHIP_FROM_AP_M = 30.151  # Midship position from AP (m)
```

## 부록 B: 파일 형식 요약

### 입력 파일

| 파일                              | 형식 | 위치                         | 필수 여부                    |
| --------------------------------- | ---- | ---------------------------- | ---------------------------- |
| `tank_catalog_from_tankmd.json` | JSON | `inputs_dir`               | 필수                         |
| `Hydro_Table_Engineering.json`  | JSON | `inputs_dir/bplus_inputs/` | 필수                         |
| `stage_results.csv`             | CSV  | `base_dir`                 | 필수 (Step 1b에서 생성 가능) |
| `current_t_sensor.csv`          | CSV  | `inputs_dir/sensors/`      | 선택                         |

### 출력 파일 (SSOT)

| 파일                           | 형식 | 위치              | 설명                           |
| ------------------------------ | ---- | ----------------- | ------------------------------ |
| `tank_ssot_for_solver.csv`   | CSV  | `out_dir/ssot/` | Solver/Optimizer용 탱크 데이터 |
| `hydro_table_for_solver.csv` | CSV  | `out_dir/ssot/` | Solver/Optimizer용 Hydro Table |
| `stage_table_unified.csv`    | CSV  | `out_dir/ssot/` | Solver/Optimizer용 Stage Table |
| `pipeline_stage_QA.csv`      | CSV  | `out_dir/ssot/` | Definition-split QA 검증 결과  |

---

## 부록 C: 관련 문서 참조

이 운영 가이드는 **실무 중심의 실용 가이드**입니다. 더 깊은 기술적 이해가 필요한 경우 다음 문서들을 참조하세요:

### 시스템 아키텍처 문서

1. **`00_System_Architecture_Complete.md`**

   - 전체 시스템 아키텍처 통합 개요
   - 데이터 흐름 및 실행 흐름 다이어그램
   - 컴포넌트 인터페이스 맵
   - **참조 시점:** 시스템 전체 구조 이해가 필요할 때
2. **`01_Architecture_Overview.md`**

   - 파이프라인 아키텍처 개요
   - 설계 원칙 (SSOT, Definition-Split, Gate Unified System)
   - 디렉토리 구조 및 실행 모드
   - **참조 시점:** 아키텍처 설계 철학 이해가 필요할 때

### 데이터 및 변환 문서

3. **`02_Data_Flow_SSOT.md`**
   - SSOT (Single Source of Truth) 개념 상세
   - JSON → CSV 변환 프로세스
   - Tank/Hydro/Stage SSOT 형식 상세
   - **참조 시점:** 데이터 변환 로직 이해가 필요할 때

### 실행 흐름 문서

4. **`03_Pipeline_Execution_Flow.md`**
   - Step-by-Step 실행 순서
   - 서브프로세스 관리 메커니즘
   - 오류 처리 전략
   - **참조 시점:** 실행 흐름 상세 이해가 필요할 때

### LP Solver 문서

5. **`04_LP_Solver_Logic.md`**
   - Linear Programming 수학적 모델
   - 결정 변수 및 제약 조건
   - 최적화 알고리즘 상세
   - **참조 시점:** Solver 알고리즘 이해가 필요할 때

### Definition-Split 문서

6. **`05_Definition_Split_Gates.md`**
   - Definition-Split 개념 배경
   - Forecast_Tide vs Required_WL 구분
   - Draft/Freeboard/UKC 정의 분리
   - Gate Unified System 구현
   - **참조 시점:** Definition-Split 개념 이해가 필요할 때

### 스크립트 인터페이스 문서

7. **`06_Script_Interfaces.md`**
   - 각 스크립트의 명령줄 인터페이스
   - 입력/출력 파일 형식 상세
   - 스크립트 독립 실행 가이드
   - **참조 시점:** 개별 스크립트 사용법이 필요할 때

### 문서 선택 가이드

**운영 작업 중심:**

- → 이 문서 (`Ballast Pipeline 운영 가이드.MD`)
- → `03_Pipeline_Execution_Flow.md` (실행 흐름)
- → `06_Script_Interfaces.md` (스크립트 사용법)

**시스템 이해 중심:**

- → `00_System_Architecture_Complete.md` (전체 구조)
- → `01_Architecture_Overview.md` (설계 원칙)
- → `02_Data_Flow_SSOT.md` (데이터 변환)

**알고리즘 이해 중심:**

- → `04_LP_Solver_Logic.md` (LP Solver)
- → `05_Definition_Split_Gates.md` (Definition-Split)

---

**문서 끝**

이 가이드가 파이프라인 운영에 도움이 되기를 바랍니다. 추가 질문이나 개선 사항이 있으면 알려주세요.

---

## 14. 패치 이력 (Patch History)

### 14.1 2024-12-23: Excel/CSV 일관성 패치

**문제:**
- Excel 생성과 CSV 생성이 서로 다른 TR 위치 데이터 사용
- `agi_tr_patched_v6_6_defsplit_v1.py` 내 중복 cfg 섹션 존재 (Line 4070, Line 7494)
- Stage 6C TR 위치 불일치: Excel (x=-9.50m) vs CSV (x=0.76m)

**해결:**
1. 중복 cfg 제거 + `create_roro_sheet()`가 `stage_results.csv` 직접 읽기
2. Draft clipping 메커니즘 (D_vessel=3.65m 초과 시 자동 clip)

**검증:**
- 파이프라인 재실행 성공 (2024-12-23 02:38)
- Excel/CSV 완전 일치 확인
- Stage 6C: Dfwd 3.80→3.65m (clipped)

**관련 문서:**
- `PATCH_CONSISTENCY_20251223.md`
- `PATCH_VERIFICATION_20251223.md`

---

### 14.2 2024-12-25: Excel 수식 보존 (COM 후처리)

**문제:**
openpyxl로 생성된 Excel 파일의 수식 의존성 그래프가 재구축되지 않아 다음 문제 발생:
- Stale calculated values
- #N/A, #REF! 에러
- 파일을 열 때마다 다른 계산 결과

**해결:**
Excel COM API를 통한 자동 후처리 통합:
1. CalculateFullRebuild() 실행
2. RefreshAll() 실행
3. Calc_Log 시트에 감사 추적 기록

**구현:**
- 신규 스크립트: `ballast_excel_finalize.py`
- 파이프라인 통합: `integrated_pipeline_defsplit_v2_gate270_split_v3.py` (Lines 4511-4549)
- 자동 실행: Step 5 (Excel 병합) 직후

**검증 절차:**

1. **Calc_Log 시트 확인**
   - Excel 파일 열기 → 마지막 시트 (Calc_Log)
   - FullRebuild_Completed = SUCCESS 확인
   - 최근 타임스탬프 확인

2. **콘솔 로그 확인**
   ```
   [FORMULA FINALIZE] Running COM post-processing...
   ✅ SUCCESS - Formula finalization completed!
   [RESULT] Processing time: 11.15 sec
   ```

3. **수식 무결성 검증**
   - RORO_Stage_Scenarios 시트
   - BC-BR 범위 (Col 55-70) 데이터 완전
   - Ctrl+F → `#N/A`, `#REF!` 검색 (0건)
   - Stage 6A AFT = 2.70m 확인

**수동 실행 (필요 시):**
```bash
python ballast_excel_finalize.py --auto
```

**요구사항:**
- Windows OS + Excel 설치
- `pip install pywin32`

**상태:** ✅ 구현 완료 (2024-12-25)

**참고 문서:**
- `docs/EXCEL_FORMULA_PRESERVATION.md` - 상세 가이드
- `docs/03_Pipeline_Execution_Flow.md` - Step 6 설명
- `docs/10_System_Improvements_and_Patches.md` - Patch v3.7

---

### 14.3 2025-12-28: Option 2 구현 완료 (BALLAST_SEQUENCE 옵션/실행 분리)

**구현 완료:**
- ✅ `ballast_sequence_generator.py` 확장:
  - `BallastOption` dataclass 추가
  - `generate_sequence_with_carryforward()`: Start_t/Target_t 체인 구현
  - `generate_option_plan()`: Delta_t 계획 생성 (Stage 6B 포함)
  - `export_to_option_dataframe()`, `export_to_exec_dataframe()`: 분리된 DataFrame 생성
  - `export_option_to_csv()`, `export_exec_to_csv()`: 분리된 CSV 생성
- ✅ `integrated_pipeline` Step 4b 업데이트:
  - `BALLAST_OPTION.csv` 생성 (계획 레벨)
  - `BALLAST_EXEC.csv` 생성 (실행 시퀀스)
  - `BALLAST_SEQUENCE.xlsx`에 3개 시트 포함 (Ballast_Option, Ballast_Exec, Ballast_Sequence)
  - 출력 수집에 `BALLAST_OPTION.csv`, `BALLAST_EXEC.csv` 포함

**핵심 기능:**
1. **Start_t/Target_t carry-forward**: 탱크별 상태 추적, 이전 step의 Target_t → 다음 Start_t 자동 전달
2. **Stage 6B 분리**: `exclude_optional_stages=True`로 실행 시퀀스에서 제외 (옵션 계획에는 포함)
3. **탱크 용량 검증**: `target_t > Capacity_t` 시 자동 클리핑

**출력 파일:**
- `BALLAST_OPTION.csv`: Stage, Tank, Action, Delta_t, PumpRate, Priority, Rationale (모든 Stage 포함)
- `BALLAST_EXEC.csv`: Stage, Step, Tank, Action, Start_t, Target_t, Time_h, Valve_Lineup, Hold_Point (Stage 6B 제외)
- `BALLAST_SEQUENCE.csv`: Legacy 형식 (호환성 유지)
- `BALLAST_SEQUENCE.xlsx`: Excel (3개 시트)

**검증 필요:**
- [ ] BALLAST_OPTION.csv에 Stage 6B 포함 확인
- [ ] BALLAST_EXEC.csv에 Stage 6B 제외 확인
- [ ] Start_t/Target_t 체인 연속성 확인 (동일 탱크)

**상태:** ✅ 구현 완료 (2025-12-28)

**참고 문서:**
- `03_DOCUMENTATION/02_IMPLEMENTATION_REPORTS/20251228/OPTION1_OPTION2_AGI_SUBMISSION_PATCHES_20251228.md`

---

### 14.4 알려진 제약사항

**Stage 6C: Freeboard=0.00m**
- 위험: Deck wet, green water
- 완화: Tidal assist (Jan 1-5, tide ≥1.85m) 또는 D_allow=3.35m 적용

**Stage 5/6A: AFT draft 부족**
- Stage 5: 2.16m (vs 2.70m 목표)
- Stage 6A: 2.36m (vs 2.70m 목표)
- 완화: Captain 승인 (AFT ≥2.35m) + 추가 stern ballast (50-80t)
