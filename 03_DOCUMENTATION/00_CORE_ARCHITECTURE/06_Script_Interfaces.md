# 제6장: 스크립트 인터페이스 및 API

**작성일:** 2025-12-20
**버전:** v2.4 (Updated: 2025-12-28)
**목적:** 각 스크립트의 명령줄 인터페이스, 입력/출력 형식, 데이터 흐름 이해

**최신 업데이트 (v2.4 - 2025-12-28):**
- Option 2 구현: Step 4b Ballast Sequence Generator 인터페이스 확장
  - `BALLAST_OPTION.csv` / `BALLAST_EXEC.csv` 분리 출력
  - `generate_sequence_with_carryforward()`: Start_t/Target_t carry-forward 구현
  - `exclude_optional_stages` 파라미터 추가 (Stage 6B 분리)

**최신 업데이트 (v2.3 - 2025-12-28):**
- I/O 최적화 모듈 인터페이스 추가 (섹션 6.6)
  - `perf_manifest.py`: Manifest logging API
  - `io_detect.py`: Encoding/delimiter detection API
  - `io_csv_fast.py`: Fast CSV reading API
  - `io_parquet_cache.py`: Parquet cache API (`read_table_any()`, `write_parquet_sidecar()`)
- MAMMOET Calculation Sheet Generator 인터페이스 추가 (섹션 6.7)

**최신 업데이트 (v2.2 - 2024-12-23):**
- Step 1 스크립트의 cfg 구조 변경 (2024-12-23 패치)
- `create_roro_sheet()` 함수의 SSOT 기반 동작
- Excel/CSV 일관성 보장 메커니즘

---

## 6.1 개요

이 장에서는 파이프라인을 구성하는 **4개 핵심 스크립트**의 인터페이스를 상세히 다룹니다:

1. **Step 1**: TR Excel Generator (`agi_tr_patched_v6_6_defsplit_v1.py`)
2. **Step 2**: OPS Integrated Report (`ops_final_r3_integrated_defs_split_v4.py`)
3. **Step 3**: Ballast Gate Solver (`ballast_gate_solver_v4.py`)
4. **Step 4**: Ballast Optimizer (`Untitled-2_patched_defsplit_v1_1.py`)

---

## 6.2 Step 1: TR Excel Generator

### 6.2.1 스크립트 정보

**파일명:** `agi_tr_patched_v6_6_defsplit_v1.py`

**역할:**
- Technical Report (TR) Excel 파일 생성
- Stage별 계산 결과 생성
- CSV 모드에서 `stage_results.csv` 생성

### 6.2.2 실행 모드

#### 기본 실행 (Excel 생성)

```bash
python agi_tr_patched_v6_6_defsplit_v1.py
```

**동작:**
- 모든 입력 JSON 파일을 읽어 TR Excel 파일 생성
- 출력: `LCT_BUSHRA_AGI_TR_Final_v6_2.xlsx`

#### CSV 모드 (Stage Results 생성)

```bash
python agi_tr_patched_v6_6_defsplit_v1.py csv
```

**동작:**
- Stage별 Draft 결과를 CSV로 출력
- 출력: `stage_results.csv`

### 6.2.3 입력 파일

다음 파일들이 작업 디렉토리에 있어야 합니다:

| 파일 | 설명 |
|------|------|
| `Hydro_Table_Engineering.json` | Hydrostatic Table (보통 `bplus_inputs/` 디렉토리) |
| `GM_Min_Curve.json` | GM 최소 곡선 |
| `Acceptance_Criteria.json` | 승인 기준 |
| `Structural_Limits.json` | 구조적 제한 |
| `Securing_Input.json` | 고정 입력 |
| `bplus_inputs/data/GZ_Curve_Stage_*.json` | Stage별 GZ 곡선 (10개 파일) |

### 6.2.4 출력 파일

**Excel 모드:**
- `LCT_BUSHRA_AGI_TR_Final_v6_2.xlsx`: Technical Report Excel 파일

**CSV 모드:**
- `stage_results.csv`: Stage별 Draft 결과
  - 컬럼: `Stage`, `Dfwd_m`, `Daft_m`, 기타 메타데이터

### 6.2.5 cfg 구조 변경 (2024-12-23 패치)

**변경 사항:**
- Line 4070의 중복 cfg 제거
- Line 7494의 cfg를 최신 `stage_results.csv` 기준으로 업데이트
- `create_roro_sheet()` 함수가 `stage_results.csv`를 동적으로 읽도록 수정

**변경 전 (중복 cfg 문제):**
```python
# Line 4070: 구버전 cfg (create_roro_sheet 내부)
cfg = {
    "W_TR": 271.20,
    "FR_TR1_RAMP_START": 40.15,  # ❌ 구버전
    "FR_TR1_STOW": 42.0,          # ❌ 구버전
    "FR_TR2_RAMP": 17.95,         # ❌ 구버전 (x=12.20m)
    "FR_TR2_STOW": 40.00,         # ❌ 구버전
    "FR_PREBALLAST": 3.0,         # ❌ 구버전
}

# Line 7494: 신버전 cfg (export_stages_to_csv 내부)
cfg = {
    "W_TR": 271.20,
    "FR_TR1_RAMP_START": 40.15,  # ❌ 여전히 구버전
    "FR_TR1_STOW": 42.0,
    "FR_TR2_RAMP": 17.95,
    "FR_TR2_STOW": 40.00,
    "FR_PREBALLAST": 3.0,
}
```
- **문제:** Excel과 CSV가 서로 다른 cfg 사용 가능
- **결과:** Stage 6C TR 위치 불일치 (x=-9.50m vs x=0.76m)

**변경 후 (SSOT 통일):**

**1. create_roro_sheet() - stage_results.csv 동적 읽기:**
```python
# Line 4068-4112 (구버전 cfg 대체)
import csv
from pathlib import Path

stage_results_path = Path("stage_results.csv")
if not stage_results_path.exists():
    # Fallback to default values
    cfg = {
        "W_TR": 271.20,
        "FR_TR2_STOW": 29.39,  # Latest value
    }
else:
    print("[INFO] Reading TR positions from stage_results.csv (SSOT)")
    stage_data = {}
    with open(stage_results_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            stage_name = row.get('Stage', '')
            x_stage_m = float(row.get('x_stage_m', 0.0))
            stage_data[stage_name] = {'x': x_stage_m}

    def x_to_fr(x_m: float) -> float:
        """Convert x position (m from midship) to Frame number"""
        return 30.151 - x_m

    cfg = {
        "W_TR": 271.20,
        "FR_TR1_RAMP_START": x_to_fr(stage_data.get('Stage 2', {}).get('x', 4.0)),
        "FR_TR1_RAMP_MID": x_to_fr(stage_data.get('Stage 3', {}).get('x', 4.0)),
        "FR_TR1_STOW": x_to_fr(stage_data.get('Stage 4', {}).get('x', 4.5)),
        "FR_TR2_RAMP": x_to_fr(stage_data.get('Stage 6A_Critical (Opt C)', {}).get('x', 5.11)),
        "FR_TR2_STOW": x_to_fr(stage_data.get('Stage 6C', {}).get('x', 0.76)),
        "FR_PREBALLAST": x_to_fr(stage_data.get('Stage 5_PreBallast', {}).get('x', 4.57)),
    }
    print(f"[INFO] cfg from stage_results.csv: {cfg}")
```

**2. export_stages_to_csv() - cfg 값 업데이트:**
```python
# Line 7494-7506 (stage_results.csv 기준)
cfg = {
    "W_TR": 271.20,
    # TR1 위치 (Frame) - ✅ stage_results.csv 기준
    "FR_TR1_RAMP_START": 26.15,  # Stage 2: x=+4.0m → Fr=30.151-4.0≈26.15
    "FR_TR1_RAMP_MID": 26.15,    # Stage 3: x=+4.0m (동일)
    "FR_TR1_STOW": 25.65,         # Stage 4/5: x=+4.5m → Fr=30.151-4.5≈25.65
    # TR2 위치 (Frame) - ✅ stage_results.csv 기준
    "FR_TR2_RAMP": 25.04,         # Stage 6A: x=+5.11m → Fr=30.151-5.11≈25.04
    "FR_TR2_STOW": 29.39,         # Stage 6C: x=+0.76m (LCF, even keel) → Fr=30.151-0.76≈29.39
    # Pre-ballast 중심 (FW2, AFT 쪽) - ✅ stage_results.csv 기준
    "FR_PREBALLAST": 25.58,       # Stage 5_PreBallast: x=+4.57m → Fr=30.151-4.57≈25.58
}
```

**효과:**
- Excel과 CSV가 **동일한** `stage_results.csv` 데이터 사용
- Stage 6C 예시: Excel/CSV 모두 `FR_TR2_STOW=29.39` (x=0.76m)
- Excel/CSV 일관성 완전 보장

**검증 로그:**
```
[INFO] Reading TR positions from stage_results.csv (SSOT)
[INFO] cfg from stage_results.csv: {
    'W_TR': 271.2,
    'FR_TR1_RAMP_START': 26.151,
    'FR_TR1_RAMP_MID': 26.151,
    'FR_TR1_STOW': 25.651,
    'FR_TR2_RAMP': 25.041,
    'FR_TR2_STOW': 29.391,  # ✅ Stage 6C: x=0.76m
    'FR_PREBALLAST': 25.581
}
```

### 6.2.6 파이프라인 통합

파이프라인에서는 다음과 같이 실행됩니다:

```python
# Step 1: Excel 생성 (선택적)
step_run_script(1, "TR_EXCEL", tr_script, args=[], ...)

# Step 1b: CSV 생성 (stage_results.csv가 없을 때)
step_run_script(2, "TR_STAGE_CSV", tr_script, args=["csv"], ...)
```

---

## 6.3 Step 2: OPS Integrated Report

### 6.3.1 스크립트 정보

**파일명:** `ops_final_r3_integrated_defs_split_v4.py`

**역할:**
- 운영 단계별 통합 리포트 생성 (Excel + Markdown)
- Tank 카탈로그와 Stage 결과 통합 분석
- Engineering-grade 계산 (Hydro table interpolation, GM 2D bilinear)

### 6.3.2 실행 방법

```bash
python ops_final_r3_integrated_defs_split_v4.py
```

**명령줄 인자:** 없음 (모든 입력은 작업 디렉토리에서 읽음)

### 6.3.3 입력 파일

| 파일 | 설명 |
|------|------|
| `tank_catalog_from_tankmd.json` | 탱크 카탈로그 |
| `stage_results.csv` | Stage 결과 (Step 1에서 생성) |
| `Hydro_Table_Engineering.json` | Hydrostatic Table |

### 6.3.4 출력 파일

| 파일 | 설명 |
|------|------|
| `OPS_FINAL_R3_AGI_Ballast_Integrated.xlsx` | 운영 리포트 Excel |
| `OPS_FINAL_R3_Report_Integrated.md` | 운영 리포트 Markdown |

### 6.3.5 주요 기능

- Engineering-grade stage calculations (hydro table interpolation)
- GM 2D bilinear interpolation
- Frame-based coordinate system
- VOID3 ballast analysis
- Discharge-only strategy

### 6.3.6 파이프라인 통합

```python
step_run_script(3, "OPS_INTEGRATED", ops_script, args=[], ...)

# 출력 파일 수집
expected_ops = [
    base_dir / "OPS_FINAL_R3_AGI_Ballast_Integrated.xlsx",
    base_dir / "OPS_FINAL_R3_Report_Integrated.md",
]
for p in expected_ops:
    if p.exists():
        shutil.copy2(p, out_dir / p.name)
```

---

## 6.4 Step 3: Ballast Gate Solver (LP)

### 6.4.1 스크립트 정보

**파일명:** `ballast_gate_solver_v4.py`

**역할:**
- Linear Programming 기반 Ballast 계획 최적화
- Definition-Split + Gate Unified System 구현
- 두 가지 모드 지원: `limit` (제약 조건) vs `target` (목표값)

### 6.4.2 실행 방법

#### 기본 실행 (Limit Mode)

```bash
python ballast_gate_solver_v4.py \
  --tank tank_ssot_for_solver.csv \
  --hydro hydro_table_for_solver.csv \
  --mode limit \
  --stage stage_table_unified.csv \
  --iterate_hydro 2 \
  --fwd_max 2.70 \
  --aft_min 2.70 \
  --d_vessel 3.65 \
  --fb_min 0.0 \
  --out_plan solver_ballast_plan.csv \
  --out_summary solver_ballast_summary.csv \
  --out_stage_plan solver_ballast_stage_plan.csv
```

#### Target Mode

```bash
python ballast_gate_solver_v4.py \
  --tank tank_ssot_for_solver.csv \
  --hydro hydro_table_for_solver.csv \
  --mode target \
  --target_fwd 2.70 \
  --target_aft 2.70 \
  --iterate_hydro 2 \
  --out_plan solver_ballast_plan.csv \
  --out_summary solver_ballast_summary.csv
```

### 6.4.3 명령줄 인자

#### 필수 인자

| 인자 | 설명 | 예시 |
|------|------|------|
| `--tank` | Tank SSOT CSV 경로 | `tank_ssot_for_solver.csv` |
| `--hydro` | Hydro Table CSV 경로 | `hydro_table_for_solver.csv` |
| `--mode` | 실행 모드 | `limit` 또는 `target` |

#### 단일 케이스 입력 (Stage 모드 미사용 시)

| 인자 | 타입 | 설명 |
|------|------|------|
| `--current_fwd` | float | 현재 Forward Draft (m) |
| `--current_aft` | float | 현재 Aft Draft (m) |

#### Target Mode 인자

| 인자 | 타입 | 설명 |
|------|------|------|
| `--target_fwd` | float | 목표 Forward Draft (m) |
| `--target_aft` | float | 목표 Aft Draft (m) |

#### Gate 인자 (Limit Mode)

| 인자 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `--fwd_max` | float | None | FWD 최대 Draft 게이트 (m) |
| `--aft_min` | float | None | AFT 최소 Draft 게이트 (m) |
| `--d_vessel` | float | None | 선체 깊이 (m, Freeboard 계산용) |
| `--fb_min` | float | None | 최소 Freeboard (m) |

#### UKC 관련 인자 (선택적)

| 인자 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `--forecast_tide` | float | None | 예보 조위 (m, Chart Datum) |
| `--depth_ref` | float | None | 기준 수심 (m, Chart Datum) |
| `--ukc_min` | float | None | 최소 UKC 요구값 (m) |
| `--ukc_ref` | string | "MAX" | UKC 계산 기준 ("FWD"\|"AFT"\|"MEAN"\|"MAX") |
| `--squat` | float | 0.0 | Squat 여유 (m) |
| `--safety_allow` | float | 0.0 | 추가 안전 여유 (m) |

#### 최적화 옵션

| 인자 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `--iterate_hydro` | int | 2 | Hydrostatic Table 반복 보간 횟수 |
| `--prefer_tons` | flag | False | 중량 최소화 우선 (기본: 시간 최소화) |

#### Penalty 파라미터

| 인자 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `--violation_penalty` | float | 1e7 | Gate 위반 Penalty (Limit Mode) |
| `--slack_weight_penalty` | float | 1e6 | Weight Slack Penalty (Target Mode) |
| `--slack_moment_penalty` | float | 1e3 | Moment Slack Penalty (Target Mode) |

#### Stage Mode 인자

| 인자 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `--stage` | string | "" | Stage Table CSV 경로 (제공 시 Stage별 처리) |
| `--out_plan` | string | "ballast_plan_out.csv" | Ballast Plan 출력 경로 |
| `--out_summary` | string | "ballast_summary_out.csv" | Summary 출력 경로 |
| `--out_stage_plan` | string | "ballast_stage_plan_out.csv" | Stage별 Plan 출력 경로 |

### 6.4.4 입력 파일 형식

#### Tank SSOT CSV

제2장 참조. 주요 컬럼:
- `Tank`, `x_from_mid_m`, `Current_t`, `Min_t`, `Max_t`, `mode`, `use_flag`, `pump_rate_tph`, `priority_weight`

#### Hydro Table SSOT CSV

제2장 참조. 주요 컬럼:
- `Tmean_m`, `TPC_t_per_cm`, `MTC_t_m_per_cm`, `LCF_m`, `LBP_m`

#### Stage Table CSV

제2장 참조. 주요 컬럼:
- `Stage`, `Current_FWD_m`, `Current_AFT_m`, `FWD_MAX_m`, `AFT_MIN_m`, 기타 게이트 파라미터

### 6.4.5 출력 파일 형식

#### Ballast Plan CSV

| Column | Description | Example |
|--------|-------------|---------|
| `Tank` | 탱크 식별자 | "FWB2" |
| `Action` | "Fill" 또는 "Discharge" | "Discharge" |
| `Delta_t` | 순 중량 변화 (tons) | -25.50 |
| `PumpTime_h` | 펌핑 시간 (hours) | 0.26 |

#### Summary CSV

**Limit Mode:**
- `FWD_new_m`, `AFT_new_m`, `Trim_new_m`, `Tmean_new_m`, `ΔW_t`
- `viol_fwd_max_m`, `viol_aft_min_m`, `viol_fb_min_m`, `viol_ukc_min_m`

**Target Mode:**
- `FWD_new_m`, `AFT_new_m`, `Trim_new_m`, `Tmean_new_m`, `ΔW_t`

### 6.4.6 파이프라인 통합

```python
solver_args = [
    "--tank", str(tank_ssot_csv),
    "--hydro", str(hydro_ssot_csv),
    "--mode", "limit",
    "--stage", str(stage_table_csv),
    "--iterate_hydro", "2",
    "--out_plan", str(solver_out_plan),
    "--out_summary", str(solver_out_sum),
    "--out_stage_plan", str(solver_out_stage_plan),
    "--fwd_max", str(args.fwd_max),
    "--aft_min", str(args.aft_min),
    "--d_vessel", str(D_VESSEL_M),
    "--fb_min", "0.0",
    "--squat", str(args.squat),
    "--safety_allow", str(args.safety_allow),
]
# 선택적 UKC 파라미터 추가
if args.forecast_tide is not None:
    solver_args += ["--forecast_tide", str(args.forecast_tide)]
if args.depth_ref is not None:
    solver_args += ["--depth_ref", str(args.depth_ref)]
if args.ukc_min is not None:
    solver_args += ["--ukc_min", str(args.ukc_min)]

step_run_script(4, "SOLVER_LP", solver_script, args=solver_args, ...)
```

---

## 6.5 Step 4: Ballast Optimizer

### 6.5.1 스크립트 정보

**파일명:** `Untitled-2_patched_defsplit_v1_1.py`

**역할:**
- 운영 휴리스틱과 LP를 결합한 최적화
- 배치 모드로 여러 Stage 처리
- Excel 출력 제공

### 6.5.2 실행 방법

```bash
python Untitled-2_patched_defsplit_v1_1.py \
  --batch \
  --tank tank_ssot_for_solver.csv \
  --hydro hydro_table_for_solver.csv \
  --stage stage_table_unified.csv \
  --prefer_time \
  --iterate_hydro 2 \
  --out_plan optimizer_plan.csv \
  --out_summary optimizer_summary.csv \
  --bwrb_out optimizer_bwrb_log.csv \
  --tanklog_out optimizer_tank_log.csv \
  --excel_out optimizer_ballast_plan.xlsx
```

### 6.5.3 명령줄 인자

#### 모드 스위치

| 인자 | 설명 |
|------|------|
| `--batch` | 배치 모드 실행 (필수, 인자 제공 시) |

#### 입력 파일

| 인자 | 설명 |
|------|------|
| `--tank` | Tank SSOT CSV 경로 |
| `--hydro` | Hydro Table CSV 경로 |
| `--stage` | Stage Table CSV 경로 |

#### Draft 입력 (단일 케이스 모드)

| 인자 | 타입 | 설명 |
|------|------|------|
| `--current_fwd` | float | 현재 Forward Draft (m) |
| `--current_aft` | float | 현재 Aft Draft (m) |
| `--target_fwd` | float | 목표 Forward Draft (m) |
| `--target_aft` | float | 목표 Aft Draft (m) |

#### 제한값 (Limits)

| 인자 | 타입 | 설명 |
|------|------|------|
| `--fwd_limit` | float | FWD 상한 (m) |
| `--aft_limit` | float | AFT 상한 (m) |
| `--trim_limit` | float | 절대 트림 제한 (m) |

**주의:** Optimizer는 `AFT_Limit`을 **상한(MAX)**으로 사용합니다. AFT 최소값 게이트가 필요한 경우 Step 3 Solver를 사용해야 합니다.

#### 최적화 옵션

| 인자 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `--prefer_time` | flag | False | 펌핑 시간 최소화 우선 |
| `--prefer_tons` | flag | False | 중량 변화 최소화 우선 |
| `--iterate_hydro` | int | 2 | Hydrostatic Table 반복 보간 횟수 |

#### 출력 파일

| 인자 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `--out_plan` | string | "" | Ballast Plan CSV (선택적) |
| `--out_summary` | string | "" | Summary CSV (선택적) |
| `--out_stage_plan` | string | "" | Stage별 Plan CSV (선택적) |
| `--bwrb_out` | string | "" | BWRB 로그 CSV (선택적) |
| `--tanklog_out` | string | "" | 탱크 로그 CSV (선택적) |
| `--excel_out` | string | "" | Excel 출력 (기본 출력 형식) |

### 6.5.4 입력/출력 파일 형식

입력 파일 형식은 Step 3과 동일합니다 (Tank SSOT, Hydro SSOT, Stage Table).

출력 형식은 Excel 중심이며, 선택적으로 CSV도 제공할 수 있습니다.

### 6.5.5 파이프라인 통합

```python
opt_args = [
    "--batch",
    "--tank", str(tank_ssot_csv),
    "--hydro", str(hydro_ssot_csv),
    "--stage", str(stage_table_csv),
    "--prefer_time",
    "--iterate_hydro", "2",
    "--out_plan", str(opt_out_plan),
    "--out_summary", str(opt_out_sum),
    "--bwrb_out", str(opt_out_bwrb),
    "--tanklog_out", str(opt_out_tanklog),
    "--excel_out", str(opt_excel),
]

step_run_script(5, "OPTIMIZER", optimizer_script, args=opt_args, ...)
```

---

## 6.6 데이터 흐름 다이어그램

```
┌─────────────────────────────────────────────────────────┐
│  INPUT LAYER (JSON)                                     │
├─────────────────────────────────────────────────────────┤
│  tank_catalog_from_tankmd.json                         │
│  Hydro_Table_Engineering.json                          │
│  GM_Min_Curve.json, Acceptance_Criteria.json, etc.     │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│  Step 1: TR Excel Generator                            │
├─────────────────────────────────────────────────────────┤
│  Input: JSON files                                     │
│  Output: LCT_BUSHRA_AGI_TR_Final_v6_2.xlsx            │
│          stage_results.csv (CSV 모드)                  │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│  Pipeline: SSOT Conversion                             │
├─────────────────────────────────────────────────────────┤
│  - convert_tank_catalog_json_to_solver_csv()           │
│  - convert_hydro_engineering_json_to_solver_csv()      │
│  - build_stage_table_from_stage_results()              │
│  - generate_stage_QA_csv()                             │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│  SSOT CSV Files                                        │
├─────────────────────────────────────────────────────────┤
│  tank_ssot_for_solver.csv                              │
│  hydro_table_for_solver.csv                            │
│  stage_table_unified.csv                               │
│  pipeline_stage_QA.csv                                 │
└──────────────────────┬──────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┬──────────────┐
        ▼              ▼              ▼              ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  Step 2:     │  │  Step 3:     │  │  Step 4:     │
│  OPS Report  │  │  LP Solver   │  │  Optimizer   │
├──────────────┤  ├──────────────┤  ├──────────────┤
│  Input:      │  │  Input:      │  │  Input:      │
│  - tank_*    │  │  - tank_ssot │  │  - tank_ssot │
│  - stage_*   │  │  - hydro_ssot│  │  - hydro_ssot│
│              │  │  - stage_*   │  │  - stage_*   │
│  Output:     │  │              │  │              │
│  - OPS_*.xlsx│  │  Output:     │  │  Output:     │
│  - OPS_*.md  │  │  - solver_*  │  │  - optimizer_│
│              │  │    .csv      │  │    .xlsx     │
└──────────────┘  └──────────────┘  └──────────────┘
```

---

## 6.7 공통 파라미터 및 상수

### 6.7.1 선박 상수

파이프라인 전체에서 일관되게 사용되는 상수:

| 상수 | 값 | 설명 |
|------|-----|------|
| `LPP_M` | 60.302 m | Length Between Perpendiculars |
| `MIDSHIP_FROM_AP_M` | 30.151 m | Midship 위치 (AP 기준) |
| `D_VESSEL_M` | 3.65 m | Molded Depth (Freeboard 계산용) |

### 6.7.2 기본 게이트 값

| 파라미터 | 기본값 | 설명 |
|----------|--------|------|
| `FWD_MAX_m` | 2.70 m | FWD 최대 Draft (Port/Ramp gate) |
| `AFT_MIN_m` | 2.70 m | AFT 최소 Draft (Captain gate) |
| `AFT_MAX_m` | 3.50 m | AFT 최대 Draft (Optimizer 상한) |
| `Trim_Abs_Limit_m` | 0.50 m | 절대 트림 제한 (Optimizer) |
| `UKC_MIN_m` | 0.50 m | 최소 UKC (프로젝트 기본값) |

### 6.7.3 기본 최적화 파라미터

| 파라미터 | 기본값 | 설명 |
|----------|--------|------|
| `iterate_hydro` | 2 | Hydrostatic Table 반복 보간 횟수 |
| `pump_rate_tph` | 100.0 | 기본 펌프 속도 (t/h) |
| `prefer_time` | False | 시간 최소화 우선 (기본: 중량 최소화) |

---

## 6.8 스크립트 독립 실행 가이드

### 6.8.1 Step 3 Solver만 실행

```bash
# SSOT CSV 준비 (파이프라인에서 생성하거나 수동 생성)
python integrated_pipeline_defsplit_v2.py --to_step 0  # SSOT만 생성

# Solver 실행
python ballast_gate_solver_v4.py \
  --tank ssot/tank_ssot_for_solver.csv \
  --hydro ssot/hydro_table_for_solver.csv \
  --mode limit \
  --stage ssot/stage_table_unified.csv \
  --fwd_max 2.70 \
  --aft_min 2.70 \
  --d_vessel 3.65 \
  --out_plan my_plan.csv \
  --out_summary my_summary.csv
```

### 6.8.2 Step 4 Optimizer만 실행

```bash
python Untitled-2_patched_defsplit_v1_1.py \
  --batch \
  --tank ssot/tank_ssot_for_solver.csv \
  --hydro ssot/hydro_table_for_solver.csv \
  --stage ssot/stage_table_unified.csv \
  --prefer_time \
  --excel_out my_optimizer.xlsx
```

---

## 6.9 오류 처리 및 검증

### 6.9.1 입력 파일 검증

각 스크립트는 실행 전에 다음을 검증합니다:

1. **파일 존재 확인**
2. **필수 컬럼/필드 존재 확인**
3. **데이터 타입 및 범위 검증**

### 6.9.2 오류 메시지

- 파일 누락: `FileNotFoundError` 또는 명확한 오류 메시지
- 컬럼 누락: `ValueError` with missing columns list
- 데이터 타입 오류: `TypeError` 또는 변환 오류

### 6.9.3 디버깅 팁

1. **Dry-Run 모드 사용**: 파이프라인의 `--dry_run` 옵션으로 경로 해석 확인
2. **로그 파일 확인**: 각 Step의 로그 파일(`pipeline_out_.../logs/`) 확인
3. **SSOT CSV 검증**: 중간 SSOT CSV 파일을 직접 확인하여 데이터 변환 정확성 검증

---

## 6.10 다음 단계

이 문서 시리즈를 통해 다음을 이해했을 것입니다:

- 파이프라인 전체 아키텍처 (제1장)
- 데이터 변환 및 SSOT 개념 (제2장)
- 실행 흐름 및 오류 처리 (제3장)
- LP Solver 수학적 모델 (제4장)
- Definition-Split 및 Gates (제5장)
- 스크립트 인터페이스 (제6장)

**추가 학습 자료:**
- 각 스크립트의 소스 코드 주석
- `README.md`: 빠른 시작 가이드
- `requirements.txt`: Python 패키지 의존성

---

## 6.11 I/O 최적화 모듈 (PR-01~05)

### 6.11.1 perf_manifest.py (PR-01)

**역할:** Subprocess-safe JSONL manifest logging

**API:**
```python
from perf_manifest import get_manifest_path, log_io

# Manifest 파일 경로 가져오기
manifest_path = get_manifest_path()
# Returns: Path("manifests/<run_id>/<step>_<pid>.jsonl")

# I/O 작업 로깅
log_io(
    operation="read",  # "read" | "write"
    file_path="stage_results.csv",
    file_type="csv",  # "csv" | "parquet" | "json" | "xlsx"
    size_bytes=10752,
    engine="pyarrow",  # "polars_lazy" | "pyarrow" | "pandas_c" | "pandas_python"
    cache_key="hit",  # "hit" | "miss" | None
    duration_ms=15.2
)
```

**환경 변수:**
- `PIPELINE_RUN_ID`: Run ID (예: "AGI_20251228_004405")
- `PIPELINE_MANIFEST_DIR`: Manifest 디렉토리 경로
- `PIPELINE_STEP`: 현재 step 이름 (예: "OPS_INTEGRATED")
- `PIPELINE_BASE_DIR`: 기본 디렉토리 경로

**출력 형식 (JSONL):**
```json
{"timestamp": "2025-12-28T00:44:11", "operation": "read", "file_path": "stage_results.csv", "file_type": "csv", "size_bytes": 10752, "engine": "pyarrow", "cache_key": "hit", "duration_ms": 15.2}
```

### 6.11.2 io_detect.py (PR-02)

**역할:** 1-pass encoding/delimiter detection

**API:**
```python
from io_detect import detect_encoding, guess_delimiter

# Encoding 탐지
encoding, confidence = detect_encoding("stage_results.csv")
# Returns: ("utf-8-sig", 0.99) or ("cp949", 0.95)

# Delimiter 추론
delimiter = guess_delimiter("stage_results.csv", encoding="utf-8")
# Returns: "," | ";" | "\t" | "|"
```

### 6.11.3 io_csv_fast.py (PR-03)

**역할:** Fast CSV reading with Polars lazy evaluation

**API:**
```python
from io_csv_fast import read_csv_fast

# Fast CSV 읽기 (Polars lazy → pandas fallback)
df = read_csv_fast(
    "stage_results.csv",
    columns=["Stage", "FWD_m", "AFT_m"],  # Optional: projection pushdown
    encoding="utf-8",
    sep=","
)
# Returns: pandas.DataFrame
```

**Fallback 순서:**
1. Polars lazy scan (projection pushdown)
2. pandas pyarrow engine
3. pandas c engine
4. pandas python engine

### 6.11.4 io_parquet_cache.py (PR-04, PR-05)

**역할:** Parquet sidecar cache and unified read API

**API:**
```python
from io_parquet_cache import write_parquet_sidecar, read_table_any

# Parquet sidecar 캐시 생성
parquet_path = write_parquet_sidecar(Path("stage_results.csv"))
# Returns: Path("stage_results.parquet")
# Side effect: Manifest 로깅

# Unified read API (Parquet 우선, CSV fallback)
df = read_table_any(
    Path("stage_results.csv"),  # 또는 Path("stage_results.parquet")
    columns=["Stage", "FWD_m"],  # Optional: projection pushdown
    encoding="utf-8"
)
# Returns: pandas.DataFrame
# Side effect: Manifest 로깅 (cache hit/miss)
```

**캐시 검증:**
- CSV와 Parquet의 mtime 비교
- Parquet가 더 오래되었으면 무시하고 CSV 읽기
- Parquet가 최신이면 Parquet 우선 로드

**통합 지점:**
- Orchestrator: Step 1b 직후 `write_parquet_sidecar()` 호출
- OPS: `df_stage_ssot = read_table_any(stage_results_path)`
- StageExcel: `df = read_table_any(stage_results_path)`

## 6.12 MAMMOET Calculation Sheet Generator

### 6.12.1 스크립트 정보

**파일명:** `create_mammoet_calculation_sheet.py`

**역할:**
- MAMMOET 스타일 기술 계산서 자동 생성
- Word 문서 형식 (.docx)

### 6.12.2 API

```python
from create_mammoet_calculation_sheet import create_mammoet_calculation_sheet
from pathlib import Path
from datetime import datetime

# 프로젝트 데이터
project_data = {
    "client": "SAMSUNG C&T",
    "project": "HVDC POWER TRANSFORMER (Al Ghallan)",
    "subject": "Stowage & Sea-Fastening Calcs",
    "project_number": "15111578",
    "document_number": "C15",
    "sap_number": "4000244577",
}

# 준비 정보
prep_data = {
    "prepared": "Your Name",
    "checked": "Reviewer Name",
    "date": datetime.now().strftime("%d-%m-%Y"),
    "revision": "00",
}

# Motion criteria
motion_data = {
    "roll_angle": 5.00,
    "roll_period": 10.00,
    "pitch_angle": 2.50,
    "pitch_period": 10.00,
    "heave": 0.10,
}

# Forces data
forces_data = {
    "weight": 217,  # t
    "transverse_dist": 0,  # mm
    "vertical_dist": 5762,  # mm
    "longitudinal_dist": 14160,  # mm
}

# 서명 정보 (선택적)
signature_data = {
    "prepared_by": "_________________",
    "prepared_name": "Your Name",
    "prepared_date": "28-12-2025",
    "checked_by": "_________________",
    "checked_name": "Reviewer Name",
    "checked_date": "28-12-2025",
}

# 문서 생성
create_mammoet_calculation_sheet(
    output_path=Path("MAMMOET_Calculation_Sheet.docx"),
    project_data=project_data,
    prep_data=prep_data,
    introduction_text="The following sea going characteristics...",
    motion_data=motion_data,
    forces_data=forces_data,
    signature_data=signature_data,
    company_name="MAMMOET",  # Optional
    title="STOWAGE & SEA-FASTENING CALCULATION"  # Optional
)
```

### 6.12.3 출력 형식

**Word 문서 구조:**
1. 헤더: 회사명 (빨간색, 왼쪽) + "Calculation Sheet" (회색, 오른쪽)
2. 제목: 중앙 정렬, 굵게
3. 프로젝트 정보 테이블 (2컬럼):
   - 왼쪽: CLIENT, PROJECT, SUBJECT, PROJECT NUMBER, DOCUMENT NUMBER, SAP NUMBER
   - 오른쪽: PREPARED, CHECKED, DATE, REVISION
4. 섹션:
   - INTRODUCTION
   - MOTION CRITERIA (Roll/Pitch 각도 및 주기, Heave)
   - FORCES EX-SHIPS MOTION (중량, CoF to CoG 거리)
   - ILLUSTRATION (PLAN VIEW, END ELEVATION 플레이스홀더)
5. 서명 섹션 (새 페이지):
   - Prepared by / Checked by / Approved by

### 6.12.4 의존성

```bash
pip install python-docx
```

---

## 6.13 Step 4b: Ballast Sequence Generator (Option 2)

### 6.13.1 스크립트 정보

**파일명:** `ballast_sequence_generator.py`

**역할:**
- Ballast 계획을 실행 시퀀스로 변환
- Option 2 구현: 옵션/실행 분리, Start_t/Target_t carry-forward

### 6.13.2 실행 방법

```python
from ballast_sequence_generator import (
    generate_sequence,
    generate_optional_sequence,
    export_to_option_dataframe,
    export_to_exec_dataframe,
)

# 옵션 계획 생성 (모든 Stage 포함)
option_df = export_to_option_dataframe(
    ballast_plan_df,
    profile,
    stage_drafts,
    tank_catalog_df
)

# 실행 시퀀스 생성 (Stage 6B 제외, Start_t/Target_t carry-forward)
exec_sequence = generate_sequence(
    ballast_plan_df,
    profile,
    stage_drafts,
    tank_catalog_df,
    exclude_optional_stages=True  # Stage 6B 제외
)
exec_df = export_to_exec_dataframe(exec_sequence)
```

### 6.13.3 주요 함수

#### `generate_sequence()`

**시그니처:**
```python
def generate_sequence(
    ballast_plan_df: pd.DataFrame,
    profile,
    stage_drafts: Dict[str, Dict[str, float]],
    tank_catalog_df: Optional[pd.DataFrame] = None,
    exclude_optional_stages: bool = True,  # Option 2: Stage 6B 제외
) -> List[BallastStep]:
```

**핵심 로직 (Option 2):**
- **Start_t/Target_t carry-forward**: 이전 step의 `target_t` → 다음 step의 `start_t`로 자동 전달
- **Stage 6B 분리**: `exclude_optional_stages=True` 시 실행 시퀀스에서 제외
- **탱크 용량 검증**: `target_t > Capacity_t` 시 클리핑

#### `export_to_option_dataframe()`

**출력 형식:**
- `BALLAST_OPTION.csv`: 계획 레벨 (Delta_t 중심, 모든 Stage 포함)
- 컬럼: `Stage`, `Tank`, `Action`, `Delta_t`, `PumpRate`, `Priority`, `Rationale`

#### `export_to_exec_dataframe()`

**출력 형식:**
- `BALLAST_EXEC.csv`: 실행 시퀀스 (Start_t/Target_t 체인, Stage 6B 제외)
- 컬럼: `Stage`, `Step`, `Tank`, `Action`, `Start_t`, `Target_t`, `Time_h`, `Valve_Lineup`, `Hold_Point`

### 6.13.4 파이프라인 통합

```python
# Step 4b 실행 (Option 2)
if args.enable_sequence:
    from ballast_sequence_generator import (
        generate_sequence,
        export_to_option_dataframe,
        export_to_exec_dataframe,
    )

    # 옵션 계획 생성
    option_df = export_to_option_dataframe(...)
    option_df.to_csv(out_dir / "BALLAST_OPTION.csv", index=False)

    # 실행 시퀀스 생성 (Stage 6B 제외)
    exec_sequence = generate_sequence(
        ...,
        exclude_optional_stages=True
    )
    exec_df = export_to_exec_dataframe(exec_sequence)
    exec_df.to_csv(out_dir / "BALLAST_EXEC.csv", index=False)
```

### 6.13.5 Option 1 패치 제안 (미구현)

**Bryan Pack에 Forecast_tide_m 주입:**
- `populate_template.py`에 `--qa-csv` 옵션 추가
- `pipeline_stage_QA.csv`의 `Forecast_tide_m`를 `Bryan_Submission_Data_Pack_Populated.xlsx`에 병합

---

**참고:**
- 제1장: 파이프라인 아키텍처 개요
- 제2장: 데이터 흐름과 SSOT
- 제3장: 파이프라인 실행 흐름
- 제4장: LP Solver 로직
- 제5장: Definition-Split과 Gates
- 각 스크립트의 소스 코드
