# 제3장: 파이프라인 실행 흐름

**작성일:** 2025-12-20
**버전:** v3.5 (Updated: 2025-12-29)
**목적:** 파이프라인의 Step-by-Step 실행 순서, 서브프로세스 관리, 오류 처리 이해

**최신 업데이트 (v3.5 - 2025-12-29):**
- Forecast_Tide_m 우선순위 변경: CLI `--forecast_tide` 값이 최우선 적용
  - Tide Integration 우선순위 재정의 (Priority 0: CLI 값)
  - `stage_table_unified.csv`와 `solver_ballast_summary.csv` 간 일관성 보장
  - 자세한 내용은 `17_TIDE_UKC_Calculation_Logic.md` 섹션 17.6.5 참조

**최신 업데이트 (v3.4 - 2025-12-27):**
- `tide/tide_ukc_engine.py` SSOT 엔진 문서화 추가
- Step 5c에 tide_ukc_engine.py 언급 추가
- Tide Integration 섹션에 stage_schedule 및 tide_ukc_engine.py 추가

**이전 업데이트 (v3.3 - 2025-12-27):**
- Pre-Step: Tide Stage Mapping (AGI-only) 추가
- Step 1b: stage_tide_AGI.csv merge 로직 추가
- Step 3: UKC 계산 고도화 (Tide-dependent), Tide_required_m, Tide_margin_m, Tide_verdict 계산
- Step 5: Bryan Template Generation 추가 (SPMT cargo 포함)
- Consolidated Excel: TIDE_BY_STAGE sheet 자동 생성
- AUTO-HOLD Warnings: Holdpoint stages 자동 경고

**최신 업데이트 (v3.2 - 2025-12-27):**
- AGENTS.md SSOT 통합 (좌표계 상수, Gate 정의)
- 좌표계 상수 명확화 (Frame↔x 변환, 부호 규칙)
- Gate 정의 명확화 (Gate-A: AFT_MIN_2p70, Gate-B: FWD_MAX_2p70_critical_only)

**최신 업데이트 (v3.1 - 2025-12-27):**
- Current_t 자동 탐색 기능 (current_t_*.csv 패턴 자동 감지)
- diff_audit.csv 생성 (센서 주입 이력 기록)

**최신 업데이트 (v2.2 - 2024-12-23):**
- Step 1 Excel 생성 시 `stage_results.csv` SSOT 읽기 로직 추가
- Draft clipping 메커니즘 상세 설명
- Excel/CSV 일관성 보장 프로세스

---

## 3.1 전체 실행 흐름 개요

### 3.1.1 실행 단계 순서

```
START
  │
  ▼
[Site Profile 로딩] (AGI JSON 프로파일)
  │
  ▼
[I/O Optimization Setup] (PR-01)
  │
  ├─→ Run ID 생성 (site_timestamp)
  ├─→ Manifest 디렉토리 생성 (manifests/<run_id>/)
  └─→ Environment variables 주입 (PIPELINE_RUN_ID, PIPELINE_MANIFEST_DIR)
  │
  ▼
[Pre-Step: Tide Stage Mapping] (AGI-only, 선택적)
  │
  ├─→ tide_table Excel (water tide_202512.xlsx)
  ├─→ tide_windows JSON (tide_windows_AGI.json)
  └─→ tide_stage_mapper.py → stage_tide_AGI.csv
  │
  ▼
[Step 1] TR Excel Generation (선택적)
  │
  ▼
[Step 1b] stage_results.csv 생성 (TR script CSV 모드)
  │
  ├─→ Merges stage_tide_AGI.csv (if available)
  ├─→ Adds Forecast_Tide_m, DatumOffset_m columns
  └─→ [PR-04] write_parquet_sidecar() → stage_results.parquet 생성
  │
  ▼
[PREP] SSOT CSV 변환 (Tank, Hydro, Stage)
  │
  ├─→ [PR-02] 1-pass encoding/delimiter 탐지
  ├─→ [PR-03] Fast CSV reading (Polars lazy → pandas fallback)
  ├─→ [PR-05] read_table_any() 사용 (Parquet 우선, CSV fallback)
  └─→ [PR-01] Manifest 로깅 (모든 I/O 작업)
  │
  ├─→ [Current_t 센서 주입] (자동 탐색: current_t_*.csv)
  │   └─→ diff_audit.csv 생성
  │
  ├─→ [Tank Overrides 적용] (프로파일에서)
  │
  └─→ [Stage Table with Tide data] (Forecast_tide_m 포함)
  │
  ▼
[Gate FAIL 리포트 생성] (자동)
  │
  ├─→ AUTO-HOLD warnings (holdpoint stages)
  └─→ Tide_margin_m < 0.10 경고
  │
  ▼
[Step 2] OPS Integrated Report (Excel + Markdown)
  │
  ├─→ [PR-05] read_table_any() 사용 (stage_results.parquet 우선)
  └─→ [PR-01] Manifest 로깅
  │
  ▼
[Step 3] Ballast Gate Solver (LP 최적화)
  │
  ├─→ UKC calculation (tide-dependent)
  ├─→ Tide_required_m (inverse UKC)
  ├─→ Tide_margin_m, Tide_verdict
  └─→ pipeline_stage_QA.csv (tide columns 포함)
  │
  ▼
[Step 4] Ballast Optimizer (선택적)
  │
  ▼
[Step 5] Bryan Template + SPMT Integration
  │
  ├─→ SPMT Integrated Excel (spmt_unified.py)
  ├─→ Bryan Template Generation
  └─→ Consolidated Excel (TIDE_BY_STAGE sheet)
  │
  ▼
END (Summary 출력)
```

### 3.1.2 실행 제어 옵션

파이프라인은 `--from_step`와 `--to_step` 인자로 실행 범위를 제어할 수 있습니다:

```bash
# 전체 실행 (Step 1~5, 기본값)
python integrated_pipeline_defsplit_v2_gate270_split_v3_auditpatched_autodetect.py --to_step 5

# Step 1~3만 실행 (Optimizer 제외)
python integrated_pipeline_defsplit_v2_gate270_split_v3_auditpatched_autodetect.py --to_step 3

# Step 2부터 실행 (Step 1 스킵, 이미 stage_results.csv 있음)
python integrated_pipeline_defsplit_v2_gate270_split_v3_auditpatched_autodetect.py --from_step 2

# Tide Integration 포함 (AGI-only)
python integrated_pipeline_defsplit_v2_gate270_split_v3_auditpatched_autodetect.py \
  --tide_table bplus_inputs/water\ tide_202512.xlsx \
  --tide_windows bplus_inputs/tide_windows_AGI.json \
  --datum_offset 0.0
```

---

## 3.2 명령줄 인자 처리

### 3.2.1 경로 관련 인자

| 인자 | 기본값 | 설명 |
|------|--------|------|
| `--base_dir` | (스크립트 위치) | 4개 스크립트가 있는 디렉토리 |
| `--inputs_dir` | `base_dir` | 입력 JSON 파일들이 있는 디렉토리 |
| `--out_dir` | `base_dir/pipeline_out_<timestamp>` | 출력 디렉토리 |

**경로 해결 순서:**
```python
base_dir = (
    Path(args.base_dir).resolve()
    if args.base_dir
    else Path(__file__).parent.resolve()
)
inputs_dir = Path(args.inputs_dir).resolve() if args.inputs_dir else base_dir
out_dir = (
    Path(args.out_dir).resolve()
    if args.out_dir
    else (base_dir / f"pipeline_out_{now_tag()}")
)
```

### 3.2.2 스크립트 경로 인자

| 인자 | 기본값 | 설명 |
|------|--------|------|
| `--tr_script` | `agi_tr_patched_v6_6_defsplit_v1.py` | Step 1 스크립트 |
| `--ops_script` | `ops_final_r3_integrated_defs_split_v4.py` | Step 2 스크립트 |
| `--solver_script` | `ballast_gate_solver_v4.py` | Step 3 스크립트 |
| `--optimizer_script` | `Untitled-2_patched_defsplit_v1_1.py` | Step 4 스크립트 |

**스크립트 경로 해결:**
```python
tr_script = (base_dir / args.tr_script).resolve()
ops_script = (base_dir / args.ops_script).resolve()
solver_script = (base_dir / args.solver_script).resolve()
optimizer_script = (base_dir / args.optimizer_script).resolve()
```

### 3.2.3 입력 파일 인자

| 인자 | 기본값 | 설명 |
|------|--------|------|
| `--tank_catalog` | `tank_catalog_from_tankmd.json` | 탱크 카탈로그 JSON |
| `--hydro` | `inputs_dir/bplus_inputs/Hydro_Table_Engineering.json` | Hydrostatic Table JSON |
| `--stage_results` | `base_dir/stage_results.csv` | Stage 결과 CSV (Step 1b에서 생성) |

### 3.2.4 게이트/제한값 인자 (SSOT - AGENTS.md 기준)

| 인자 | 기본값 | 설명 |
|------|--------|------|
| `--fwd_max` | 2.70 | FWD 최대 Draft 게이트 (m, Gate-B: Mammoet, Critical RoRo only) |
| `--aft_min` | 2.70 | AFT 최소 Draft 게이트 (m, Gate-A: Captain, 모든 Stage) |
| `--aft_max` | 3.50 | AFT 최대 Draft 제한 (m, Optimizer용) |
| `--trim_abs_limit` | 0.50 | 절대 트림 제한 (m, Optimizer용) |

**Gate Labels SSOT (모호한 "2.70m" 방지)**:
- **절대 "2.70m"만 쓰지 말 것**. 항상 라벨 포함:
  - **Gate-A**: `AFT_MIN_2p70` (Captain / Propulsion, 모든 Stage)
  - **Gate-B**: `FWD_MAX_2p70_critical_only` (Mammoet / Critical RoRo only)

**Gate-B 적용 범위**:
- Critical stages만 적용 (`Gate_B_Applies=True`)
- Non-critical stages는 `N/A`로 표기 (false failure 방지)
- Critical stage 판정: `DEFAULT_CRITICAL_STAGE_REGEX = r"(preballast.*critical|6a.*critical|stage\s*5.*preballast|stage\s*6a)"`

### 3.2.5 UKC 관련 인자 (선택적)

**Legacy 방식 (단일 시점 tide):**
| 인자 | 기본값 | 설명 |
|------|--------|------|
| `--forecast_tide` | None | 예보 조위 (m, Chart Datum 기준) |
| `--depth_ref` | None | 기준 수심 (m, Chart Datum 기준) |
| `--ukc_min` | None | 최소 UKC 요구값 (m) |
| `--squat` | 0.0 | Squat 여유 (m) |
| `--safety_allow` | 0.0 | 추가 안전 여유 (m) |

**Tide Integration 방식 (AGI-only, Stage-wise tide):**
| 인자 | 기본값 | 설명 |
|------|--------|------|
| `--tide_table` | "" | Tide table Excel 경로 (time-series, 예: `bplus_inputs/water tide_202512.xlsx`) |
| `--tide_windows` | "" | Tide windows JSON 경로 (stage time windows, 예: `bplus_inputs/tide_windows_AGI.json`) |
| `--stage_tide_csv` | "" | Precomputed `stage_tide_AGI.csv` 경로 (선택적, Pre-Step 스킵) |
| `--datum_offset` | 0.0 | Datum offset (m) applied to DepthRef for UKC calculation |

**UKC 계산 활성화:**
- **Legacy**: `--forecast_tide`, `--depth_ref`, `--ukc_min` 모두 제공 시 UKC 게이트 활성화
- **Tide Integration**: `--tide_table` + `--tide_windows` 제공 시 Pre-Step 실행, Stage-wise tide mapping
- 일부만 제공하면 해당 파라미터만 Stage Table에 추가 (게이트 비활성화)

**Tide Integration 우선순위 (v3.5 업데이트, 2025-12-29):**
0. `--forecast_tide` (CLI 값, 최우선) → 모든 Stage에 직접 적용, stage_tide_csv보다 우선
1. `--stage_tide_csv` (precomputed) → CLI가 없을 때만 사용, Pre-Step 스킵
2. `--tide_table` + `--tide_windows` → CLI가 없을 때만 사용, Pre-Step 실행
3. `--forecast_tide` (fallback fillna) → 누락된 Stage에만 적용

**변경 사항 (2025-12-29):**
- CLI `--forecast_tide` 값이 최우선으로 적용되어 `stage_table_unified.csv`와 `solver_ballast_summary.csv` 간 일관성 보장
- 자세한 내용은 `17_TIDE_UKC_Calculation_Logic.md` 섹션 17.6.5 참조

### 3.2.6 데이터 변환 옵션

| 인자 | 기본값 | 설명 |
|------|--------|------|
| `--pump_rate` | 100.0 | 기본 펌프 속도 (t/h) |
| `--tank_keywords` | "BALLAST,VOID,FWB,FW,DB" | `use_flag=Y` 마킹용 키워드 (쉼표 구분) |

### 3.2.7 Site 및 프로파일 관련 인자

| 인자 | 기본값 | 설명 |
|------|--------|------|
| `--site` | "AGI" | 사이트 레이블 (AGI 전용) |
| `--profile_json` | "" | Site 프로파일 JSON 경로 (명시적 지정, 기본: `inputs_dir/profiles/{site}.json` 자동 탐색) |

**프로파일 우선순위:**
1. 명시적 CLI 플래그 (예: `--fwd_max 2.8`)
2. 프로파일 JSON 값
3. argparse 기본값

### 3.2.8 센서 데이터 관련 인자

| 인자 | 기본값 | 설명 |
|------|--------|------|
| `--current_t_csv` | "" | Current_t 센서 CSV 경로 (기본: `inputs_dir/sensors/current_t_sensor.csv` 자동 탐색) |
| `--current_t_strategy` | "override" | 센서 값 주입 전략 ("override"\|"fill_missing") |

**센서 CSV 탐색 순서 (v3.1 업데이트):**
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

### 3.2.9 실행 제어 인자

| 인자 | 기본값 | 설명 |
|------|--------|------|
| `--from_step` | 1 | 시작 단계 (1~5) |
| `--to_step` | 5 | 종료 단계 (1~5, 기본값: 5) |
| `--dry_run` | False | 경로 해석만 수행하고 종료 |
| `--no_gate_report` | False | Gate FAIL 리포트 생성 비활성화 |

### 3.2.10 P0 Features 인자 (2025-12-25 추가)

| 인자 | 기본값 | 설명 |
|------|--------|------|
| `--gate_guard_band_cm` | 2.0 | Gate tolerance (cm) - 운영 여유 제공 |

**P0-3: Guard-Band Support**

Guard-Band는 gate 검사에 운영 여유(tolerance)를 제공합니다:

```
Strict Limit: AFT >= 2.70m
Guard-Band (2.0cm): AFT >= 2.68m → PASS (with warning)
```

**사용 예시:**

```bash
# Production 실행 (2.0cm tolerance, 권장)
python integrated_pipeline_defsplit_v2_gate270_split_v3.py \
  --site AGI \
  --gate_guard_band_cm 2.0

# Strict 모드 (개발/검증용, no tolerance)
python integrated_pipeline_defsplit_v2_gate270_split_v3.py \
  --site AGI \
  --gate_guard_band_cm 0.0
```

**효과:**
- ✅ 센서 측정 오차 고려 (±1-2cm)
- ✅ LP Solver 수치 정밀도 한계 극복 (±0.01m)
- ✅ 유체 동역학적 변동 허용 (sloshing, wave)
- ✅ 현장 실행 가능성 향상

**P0-2: Step-wise Gate-B Handling**

Gate-B (FWD_MAX_2p70_critical_only)는 **Critical RoRo stages에만** 적용됩니다:

- **Critical stages:** Stage 5_PreBallast, Stage 6A_Critical (Opt C)
- **Non-critical stages:** 자동으로 Gate-B 검사에서 제외

**QA 출력 컬럼:**
```csv
GateB_FWD_MAX_2p70_CD_applicable  # True=Critical, False=Non-critical
GateB_FWD_MAX_2p70_CD_PASS        # True/False
GateB_FWD_MAX_2p70_CD_Margin_m    # FWD margin (NaN for non-critical)
```

**Gate FAIL Report:**
- `GateB_..._CD` count는 **Critical stages만** 카운트
- Non-critical stages는 FAIL이어도 카운트되지 않음

**참고 문서:**
- `docs/16_P0_Guard_Band_and_Step_wise_Gate_B_Guide.md` - 완전 가이드

---

## 3.3 Dry-Run 모드

### 3.3.1 목적

실제 실행 전에 경로 해석과 파일 존재 여부를 확인하는 모드입니다.

### 3.3.2 실행 예시

```bash
python integrated_pipeline_defsplit_v2.py --dry_run
```

### 3.3.3 출력 형식

```
================================================================================
DRY RUN - PATH RESOLUTION
================================================================================
Site:        AGI
Base dir:    C:\...\ballast_pipeline_defsplit_v2_complete
Inputs dir:  C:\...\ballast_pipeline_defsplit_v2_complete
Out dir:     C:\...\ballast_pipeline_defsplit_v2_complete\pipeline_out_20251220_120000

[SCRIPTS]
TR:          C:\...\agi_tr_patched_v6_6_defsplit_v1.py  (OK)
OPS:         C:\...\ops_final_r3_integrated_defs_split_v4.py  (OK)
SOLVER:      C:\...\ballast_gate_solver_v4.py  (OK)
OPTIMIZER:   C:\...\Untitled-2_patched_defsplit_v1_1.py  (OK)

[INPUTS]
Tank catalog: C:\...\tank_catalog_from_tankmd.json  (OK)
Hydro:        C:\...\bplus_inputs\Hydro_Table_Engineering.json  (OK)
StageRes:     C:\...\stage_results.csv  (OK)

[OUTPUT SSOT]
Tank SSOT:   pipeline_out_20251220_120000\ssot\tank_ssot_for_solver.csv
Hydro SSOT:  pipeline_out_20251220_120000\ssot\hydro_table_for_solver.csv
Stage table: pipeline_out_20251220_120000\ssot\stage_table_unified.csv
```

---

## 3.4 서브프로세스 실행 메커니즘

### 3.4.1 `run_cmd` 함수

**위치:** `integrated_pipeline_defsplit_v2.py` (lines 111-138)

**기능:**
- 서브프로세스 실행
- stdout/stderr를 로그 파일과 콘솔에 동시 출력 (tee)
- UTF-8 인코딩 처리 (Windows 호환)

**구현:**
```python
def run_cmd(
    cmd: List[str], cwd: Path, log_path: Path, env: Optional[Dict[str, str]] = None
) -> int:
    log_path.parent.mkdir(parents=True, exist_ok=True)

    with log_path.open("w", encoding="utf-8", errors="replace") as f:
        f.write(f"[CMD] {' '.join(cmd)}\n")
        f.write(f"[CWD] {cwd}\n\n")
        f.flush()

        p = subprocess.Popen(
            cmd,
            cwd=str(cwd),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,  # stderr를 stdout으로 리다이렉트
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env or os.environ.copy(),
        )
        assert p.stdout is not None
        for line in p.stdout:
            sys.stdout.write(line)  # 콘솔 출력
            f.write(line)           # 로그 파일 기록
        return p.wait()  # 반환 코드 반환
```

**특징:**
- **실시간 출력**: 서브프로세스 출력이 즉시 콘솔과 로그에 기록됨
- **에러 복구**: `errors="replace"`로 인코딩 오류 시 문자 치환
- **환경 변수**: 선택적 `env` 파라미터로 환경 변수 오버라이드 가능

### 3.4.2 `step_run_script` 함수

**위치:** `integrated_pipeline_defsplit_v2.py` (lines 479-496)

**기능:**
- 스크립트 실행을 위한 래퍼 함수
- 스크립트 존재 여부 검증
- 로그 파일 경로 생성
- `StepResult` 반환

**구현:**
```python
@dataclass
class StepResult:
    ok: bool           # 실행 성공 여부
    returncode: int    # 프로세스 반환 코드 (0=성공)
    log: Path          # 로그 파일 경로

def step_run_script(
    step_id: int,
    name: str,
    script: Path,
    args: List[str],
    cwd: Path,
    out_dir: Path,
    env: Optional[Dict[str, str]] = None,
) -> StepResult:
    if not script.exists():
        log = out_dir / "logs" / f"{step_id:02d}_{name}_MISSING.log"
        log.write_text(f"Missing script: {script}\n", encoding="utf-8")
        return StepResult(False, 127, log)

    log = out_dir / "logs" / f"{step_id:02d}_{name}.log"
    cmd = [which_python(), str(script)] + args
    rc = run_cmd(cmd, cwd=cwd, log_path=log, env=env)
    return StepResult(rc == 0, rc, log)
```

**로그 파일 명명 규칙:**
- 성공: `{step_id:02d}_{name}.log` (예: `01_TR_EXCEL.log`)
- 스크립트 누락: `{step_id:02d}_{name}_MISSING.log`

---

## 3.5 Step-by-Step 실행 상세

### 3.5.1 Step 1: TR Excel Generation

**조건:** `args.from_step <= 1 <= args.to_step`

**실행:**
```python
r1 = step_run_script(
    1,
    "TR_EXCEL",
    tr_script,
    args=[],  # 인자 없음 (기본 실행 모드)
    cwd=base_dir,
    out_dir=out_dir,
)
```

**⭐ Excel 생성 시 SSOT 사용 (2024-12-23 업데이트):**

Step 1 (Excel 생성) 실행 시, `create_roro_sheet()` 함수는 `stage_results.csv`를 먼저 확인하고 TR 위치를 동적으로 로드합니다.

**실행 흐름:**
1. `stage_results.csv` 존재 여부 확인
2. 존재하면 → CSV에서 각 Stage의 `x_stage_m` 읽기
3. `x_stage_m` → Frame 번호 변환: `Fr = 30.151 - x`
4. cfg 딕셔너리 생성 (동적)
5. Excel RORO_Stage_Scenarios 시트 생성

**코드 예시 (create_roro_sheet 내부):**
```python
import csv
from pathlib import Path

stage_results_path = Path("stage_results.csv")
if not stage_results_path.exists():
    # Fallback to default cfg values
    cfg = {"W_TR": 271.20, "FR_TR2_STOW": 29.39, ...}
else:
    print("[INFO] Reading TR positions from stage_results.csv (SSOT)")
    stage_data = {}
    with open(stage_results_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            stage_name = row.get('Stage', '')
            x_m = float(row.get('x_stage_m', 0.0))
            stage_data[stage_name] = {'x': x_m}

    def x_to_fr(x_m: float) -> float:
        return 30.151 - x_m

    cfg = {
        "W_TR": 271.20,
        "FR_TR1_RAMP_START": x_to_fr(stage_data.get('Stage 2', {}).get('x', 4.0)),
        "FR_TR1_STOW": x_to_fr(stage_data.get('Stage 4', {}).get('x', 4.5)),
        "FR_TR2_RAMP": x_to_fr(stage_data.get('Stage 6A_Critical (Opt C)', {}).get('x', 5.11)),
        "FR_TR2_STOW": x_to_fr(stage_data.get('Stage 6C', {}).get('x', 0.76)),
        "FR_PREBALLAST": x_to_fr(stage_data.get('Stage 5_PreBallast', {}).get('x', 4.57)),
    }
    print(f"[INFO] cfg from stage_results.csv: {cfg}")
```

**로그 예시:**
```
[INFO] Reading TR positions from stage_results.csv (SSOT)
[INFO] cfg from stage_results.csv: {
    'W_TR': 271.2,
    'FR_TR1_RAMP_START': 26.151,
    'FR_TR1_STOW': 25.651,
    'FR_TR2_RAMP': 25.041,
    'FR_TR2_STOW': 29.391,  # Stage 6C: x=0.76m → Fr=29.391
    'FR_PREBALLAST': 25.581
}
```

**효과:**
- Excel과 CSV가 **동일한 TR 위치 데이터** 사용
- Stage 6C 예시: Excel/CSV 모두 `x=0.76m` (LCF, even keel)
- Excel/CSV 일관성 보장

**오류 처리:**
- 실패 시 `[WARN]` 메시지 출력
- 파이프라인 계속 진행 (Excel 파일이 필수는 아니므로)
- 사용자에게 `stage_results.csv`가 이미 있거나 Excel이 필요 없으면 계속 진행 가능하다고 안내

### 3.5.2 Step 1b: stage_results.csv 생성

**조건:** `args.from_step <= 1 <= args.to_step` AND `stage_results_path.exists() == False`

**실행:**
```python
if not stage_results_path.exists():
    r1b = step_run_script(
        2,
        "TR_STAGE_CSV",
        tr_script,
        args=["csv"],  # CSV 모드 실행
        cwd=base_dir,
        out_dir=out_dir,
    )
```

**오류 처리:**
- 실패 시 `[ERROR]` 메시지 출력
- **파이프라인 중단** (`return 1`) - `stage_results.csv`는 필수 입력

**검증:**
- 실행 후에도 파일이 없으면 추가 오류 메시지와 함께 중단

### 3.5.3 PREP: SSOT CSV 변환

**위치:** `integrated_pipeline_defsplit_v2.py` (lines 748-814)

**순서:**
1. **Tank SSOT 변환**
   ```python
   convert_tank_catalog_json_to_solver_csv(
       tank_catalog_json=tank_catalog,
       out_csv=tank_ssot_csv,
       pump_rate_tph=float(args.pump_rate),
       include_keywords=tank_keywords,
   )
   ```

2. **Current_t 센서 주입 (PLC/IoT) - v3.1 업데이트**
   ```python
   # 센서 CSV 경로 해결 (자동 탐색 포함)
   resolved_sensor_csv = resolve_current_t_sensor_csv(
       args.current_t_csv, base_dir=base_dir, inputs_dir=inputs_dir
   )
   if resolved_sensor_csv is not None:
       sensor_stats = inject_current_t_from_sensor_csv(
           tank_ssot_csv=tank_ssot_csv,
           sensor_csv=resolved_sensor_csv,
           strategy=str(args.current_t_strategy),  # "override" or "fill_missing"
           out_csv=tank_ssot_csv,
           out_audit_csv=out_dir / "ssot" / "diff_audit.csv",  # v3.1 신규
       )
   ```
   - 센서 CSV가 제공되면 Tank SSOT의 `Current_t` 값을 자동 주입
   - 전략: `override` (모든 값 덮어쓰기) 또는 `fill_missing` (0.0인 경우만 주입)
   - **diff_audit.csv 생성** (v3.1 신규):
     - 주입 전/후 값 비교 (`CurrentOld_t`, `ComputedNew_t`, `Delta_t`)
     - Clamping 여부 (`ClampedFlag`)
     - 업데이트 여부 (`Updated`)
     - 스킵 사유 (`SkipReason`)

3. **Tank Overrides 적용 (프로파일에서)**
   ```python
   # 프로파일의 tank_overrides를 Tank SSOT에 적용
   if profile_obj:
       apply_tank_overrides_from_profile(
           tank_ssot_csv=tank_ssot_csv,
           profile=profile_obj,
           out_csv=tank_ssot_csv,
       )
   ```
   - 프로파일의 `tank_overrides` 섹션에서 특정 탱크의 `mode`, `use_flag`, `pump_rate_tph` 등을 오버라이드
   - 예: `VOID3`를 `FIXED/Y`로 고정, `FWCARGO*`를 `FIXED/N`로 차단

4. **Hydro SSOT 변환**
   ```python
   convert_hydro_engineering_json_to_solver_csv(
       hydro_json=hydro_path,
       out_csv=hydro_ssot_csv,
       lbp_m=LPP_M,
   )
   ```

5. **Stage Table 구축**
   ```python
   build_stage_table_from_stage_results(
       stage_results_csv=stage_results_path,
       out_csv=stage_table_csv,
       fwd_max_m=float(args.fwd_max),
       aft_min_m=float(args.aft_min),
       ...
   )
   ```

6. **Stage QA CSV 생성**
   ```python
   generate_stage_QA_csv(
       stage_table_csv=stage_table_csv,
       out_qa_csv=stage_qa_csv,
       ...
   )
   ```

7. **Gate FAIL 리포트 생성 (자동)**
   ```python
   if not args.no_gate_report:
       generate_gate_fail_report_md(
           out_md=gate_report_md,
           site=str(args.site),
           profile_path=resolved_profile_path,
           stage_qa_csv=stage_qa_csv,
           tank_ssot_csv=tank_ssot_csv,
           sensor_stats=sensor_stats,
           ukc_inputs=ukc_inputs,
       )
   ```
   - `pipeline_stage_QA.csv` 기반으로 Gate 위반 원인 분석 리포트 자동 생성
   - Current_t 상태, 센서 동기화 결과, UKC 입력 상태 등을 포함
   - **v2.1+**: 2.70m Split Gates 포함 (Gate-A: Captain, Gate-B: Mammoet)
     - `GateA_AFT_MIN_2p70_PASS`: 모든 Stage에 적용
     - `GateB_FWD_MAX_2p70_CD_PASS`: Critical stages만 적용

**오류 처리:**
- 입력 파일 누락 시 `[ERROR]` 메시지와 함께 중단
- 센서 주입 실패 시 `[WARN]` 메시지 출력 후 계속 진행
- Tank Overrides 실패 시 `[WARN]` 메시지 출력 후 계속 진행
- 변환 함수 내부 오류는 예외로 전파되어 파이프라인 중단

### 3.5.4 Step 2: OPS Integrated Report

**조건:** `args.from_step <= 2 <= args.to_step`

**실행:**
```python
r2 = step_run_script(
    3,
    "OPS_INTEGRATED",
    ops_script,
    args=[],  # 인자 없음
    cwd=base_dir,
    out_dir=out_dir,
)
```

**출력 파일 수집:**
```python
expected_ops = [
    base_dir / "OPS_FINAL_R3_AGI_Ballast_Integrated.xlsx",
    base_dir / "OPS_FINAL_R3_Report_Integrated.md",
]
for p in expected_ops:
    if p.exists():
        shutil.copy2(p, out_dir / p.name)
        print(f"[OK] Collected output -> {out_dir / p.name}")
```

**오류 처리:**
- 실패 시 `[ERROR]` 메시지와 함께 파이프라인 중단 (`return 1`)

### 3.5.5 Step 3: Ballast Gate Solver (LP)

**조건:** `args.from_step <= 3 <= args.to_step`

**명령줄 인자 구성:**
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
```

**실행:**
```python
r3 = step_run_script(
    4,
    "SOLVER_LP",
    solver_script,
    args=solver_args,
    cwd=base_dir,
    out_dir=out_dir,
)
```

**오류 처리:**
- 실패 시 `[ERROR]` 메시지와 함께 파이프라인 중단

### 3.5.6 Step 4: Ballast Optimizer

**조건:** `args.from_step <= 4 <= args.to_step`

**명령줄 인자 구성:**
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
```

**실행:**
```python
r4 = step_run_script(
    5,
    "OPTIMIZER",
    optimizer_script,
    args=opt_args,
    cwd=base_dir,
    out_dir=out_dir,
)
```

**주의사항:**
- Optimizer는 `AFT_Limit_m`을 **상한(MAX)**으로 사용 (하한이 아님)
- Captain gate (AFT ≥ 2.70m)는 Step 3 Solver에서 강제됨

**오류 처리:**
- 실패 시 `[ERROR]` 메시지와 함께 파이프라인 중단

### 3.5.7 Step 5: SPMT Integration & Bryan Template Generation

**조건:** `args.from_step <= 5 <= args.to_step` (기본값: `--to_step 5`)

#### 3.5.7.1 Step 5a: SPMT Integrated Excel

**목적:** SPMT cargo input workbook 생성 및 통합

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
  - `00_Cover`: Workbook overview
  - `Stage_Config`: SSOT parameters
  - `Cargo_SPMT_Inputs`: Cargo data
  - `Submission_Stagewise`: Stage-wise submission
  - `Stage_Results`: SSOT-mapped stage results
  - `Stage-wise Cargo on Deck`: Bryan format

**실행 조건:**
- `spmt_config` 파일 존재 시 자동 실행
- `stage_results.csv` 없으면 `--ssot` 없이 실행

**오류 처리:**
- `spmt_config` 없으면 `[WARN]` 메시지 출력 후 Step 5a 스킵
- `stage_results.csv` 없으면 `[WARN]` 메시지 출력 후 `--ssot` 없이 실행

#### 3.5.7.2 Step 5b: Bryan Template Generation

**목적:** Bryan submission data pack 생성 (SPMT cargo 포함)

**입력:**
- `SPMT_Integrated_Complete.xlsx` (from Step 5a)
- `stage_results.csv` (SSOT)

**처리:**
- `bryan_template_unified.py one-click` 실행
  - `create` → `Bryan_Submission_Data_Pack_Template.xlsx`
  - `populate` → Uses `stage_results.csv`
  - `--spmt-xlsx` → Imports SPMT cargo into `04_Cargo_SPMT` sheet

**출력:**
- `Bryan_Submission_Data_Pack_Template.xlsx`
- `Bryan_Submission_Data_Pack_Populated.xlsx`
  - `04_Cargo_SPMT`: SPMT cargo data
  - `07_Stage_Calc`: Stage calculations
  - `06_Stage_Plan`: Stage-wise cargo positions

**오류 처리:**
- `SPMT_Integrated_Complete.xlsx` 없으면 Step 5a 자동 실행 후 재시도
- 실패 시 `[WARN]` 메시지 출력 후 Step 5b 스킵

#### 3.5.7.3 Step 5c: Consolidated Excel

**목적:** 모든 파이프라인 출력을 단일 Excel로 통합

**입력:**
- Step 2~4 출력 파일들
- `pipeline_stage_QA.csv` (tide columns 포함, `tide_ukc_engine.py` 사용)
- `SPMT_Integrated_Complete.xlsx` (optional)
- `Bryan_Submission_Data_Pack_Populated.xlsx` (optional)

**처리:**
- `ballast_excel_consolidator.py` 실행
  - 모든 Excel 파일 merge
  - `TIDE_BY_STAGE` sheet 생성 (from `pipeline_stage_QA.csv`)
  - UKC calculations from `tide_ukc_engine.py` (SSOT)

**출력:**
- `PIPELINE_CONSOLIDATED_AGI_<timestamp>.xlsx`
  - `TIDE_BY_STAGE`: Stage-wise tide & UKC summary (`tide_ukc_engine.py` 기반)
  - `Stage_QA`: Pipeline stage QA (tide columns 포함)
  - `Solver_Plan`: Step 3 solver output
  - `Optimizer_Plan`: Step 4 optimizer output (if available)
  - `SPMT_Integrated`: SPMT data (if available)
  - `Bryan_Submission`: Bryan template (if available)

**TIDE_BY_STAGE Sheet 컬럼:**
- `Stage`, `Forecast_tide_m`, `Tide_required_m`, `Tide_margin_m`
- `UKC_min_m`, `UKC_fwd_m`, `UKC_aft_m`, `Tide_verdict`
- (All calculated using `tide/tide_ukc_engine.py` SSOT engine)

**오류 처리:**
- 일부 Excel 파일 누락 시 `[WARN]` 메시지 출력 후 계속 진행
- `TIDE_BY_STAGE` sheet 생성 실패 시 `[WARN]` 메시지 출력 후 계속 진행

---

## 3.6 오류 처리 전략

### 3.6.1 오류 레벨 분류

1. **WARNING (경고)**
   - Step 1 실패: Excel 생성 실패는 경고로 처리, 파이프라인 계속 진행
   - 이유: Excel 파일은 선택적 출력, `stage_results.csv`가 더 중요

2. **ERROR (오류, 파이프라인 중단)**
   - 필수 입력 파일 누락
   - Step 1b 실패 (`stage_results.csv` 생성 실패)
   - SSOT 변환 실패
   - Step 2, 3, 4 실패
   - Step 5b 실패 (Bryan template 생성 실패, SPMT 없으면 WARNING)

### 3.6.2 오류 메시지 형식

```
[WARN] Step-1 failed (rc=1). Log: pipeline_out_.../logs/01_TR_EXCEL.log
       You can still proceed if you already have stage_results.csv or do not need the Excel.

[ERROR] Step-1b failed and stage_results.csv not found. rc=1
        Log: pipeline_out_.../logs/02_TR_STAGE_CSV.log
```

### 3.6.3 로그 파일 활용

각 Step의 로그 파일에는 다음이 포함됩니다:
- 실행 명령어 (`[CMD]`)
- 작업 디렉토리 (`[CWD]`)
- 서브프로세스의 전체 stdout/stderr 출력

**로그 파일 위치:**
```
pipeline_out_<timestamp>/
└── logs/
    ├── 01_TR_EXCEL.log
    ├── 02_TR_STAGE_CSV.log
    ├── 03_OPS_INTEGRATED.log
    ├── 04_SOLVER_LP.log
    └── 05_OPTIMIZER.log
```

---

## 3.7 출력 파일 관리

### 3.7.1 출력 디렉토리 구조

```
pipeline_out_<timestamp>/
├── ssot/                              # SSOT CSV 파일
│   ├── tank_ssot_for_solver.csv
│   ├── hydro_table_for_solver.csv
│   ├── stage_table_unified.csv
│   ├── pipeline_stage_QA.csv
│   └── diff_audit.csv                 # Current_t 주입 이력 (v3.1)
│
├── logs/                              # 실행 로그
│   ├── 01_TR_EXCEL.log
│   ├── 02_TR_STAGE_CSV.log
│   ├── 03_OPS_INTEGRATED.log
│   ├── 04_SOLVER_LP.log
│   ├── 05_OPTIMIZER.log
│   ├── 05a_SPMT_INTEGRATE.log
│   ├── 05b_BRYAN_TEMPLATE.log
│   └── 05c_EXCEL_CONSOLIDATE.log
│
├── gate_fail_report.md               # Gate FAIL 자동 리포트 (PREP 후 생성)
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
├── SPMT_Integrated_Complete.xlsx     # Step 5a 출력
├── Bryan_Submission_Data_Pack_Template.xlsx  # Step 5b 출력
├── Bryan_Submission_Data_Pack_Populated.xlsx
│
├── stage_tide_AGI.csv                 # Pre-Step 출력 (AGI-only)
└── PIPELINE_CONSOLIDATED_AGI_*.xlsx  # Step 5c 출력 (TIDE_BY_STAGE 포함)
```

### 3.7.2 파일 수집 메커니즘

**Step 2 출력 수집:**
- Step 2 스크립트는 작업 디렉토리(`base_dir`)에 파일 생성
- 파이프라인이 출력 디렉토리(`out_dir`)로 복사

**Step 3, 4 출력:**
- 명령줄 인자로 출력 경로 지정 (`--out_plan`, `--out_summary` 등)
- 직접 `out_dir`에 생성됨

### 3.7.3 완료 요약

파이프라인 완료 시 다음 정보를 출력합니다:

```
================================================================================
PIPELINE COMPLETE
================================================================================
Out dir: pipeline_out_20251220_120000
Key SSOT outputs:
 - tank_ssot_for_solver.csv
 - hydro_table_for_solver.csv
 - stage_table_unified.csv
 - pipeline_stage_QA.csv (definition-split QA)
Key reports:
 - gate_fail_report.md (Gate FAIL 원인 분석 리포트)
```

---

## 3.7 Step 6: Excel Formula Preservation (COM Post-Processing)

### 3.7.1 목적

openpyxl로 수정된 Excel 파일의 **수식 의존성 무결성**을 보장합니다. openpyxl은 계산 엔진이 아니므로, Excel COM을 통해 파일을 다시 열고 CalculateFullRebuild를 실행하여 의존성 그래프를 재구축합니다.

### 3.7.2 실행 조건

**자동 실행:**
- Step 5에서 merged_excel이 성공적으로 생성된 경우
- `ballast_excel_finalize.py` 스크립트가 존재하는 경우
- Windows 환경 + Excel 설치 + pywin32 설치

**실행 위치:**
```python
# integrated_pipeline_defsplit_v2_gate270_split_v3.py
# Line 4511-4549 (return 0 직전)
```

### 3.7.3 처리 단계

```
1. Excel COM 초기화
   ↓
2. 파일 재오픈 (merged_excel)
   ↓
3. Calculation = Automatic 설정
   ↓
4. RefreshAll() 실행 (외부 데이터)
   ↓
5. CalculateFullRebuild() 실행 (의존성 재구축)
   ↓
6. QueryTables & PivotCaches 갱신
   ↓
7. Calc_Log 시트 기록 (감사 추적)
   ↓
8. 저장 및 닫기
```

### 3.7.4 Calc_Log 시트 (자동 생성)

**위치:** Excel 파일의 마지막 시트

**내용:**

| Parameter | Value | Timestamp |
|-----------|-------|-----------|
| FullRebuild_Completed | SUCCESS | 2025-12-25 00:24:11 |
| Engine | Python+COM | 2025-12-25 00:24:11 |
| ProcessingTime_sec | 11.15 | 2025-12-25 00:24:11 |
| QueryTables_Count | 0 | 2025-12-25 00:24:11 |
| PivotCaches_Count | 0 | 2025-12-25 00:24:11 |

### 3.7.5 콘솔 출력

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

================================================================================
✅ SUCCESS - Formula finalization completed!
================================================================================
[OK] Formula finalization completed successfully
  [RESULT] Processing time: 11.15 sec
  [RESULT] File: PIPELINE_CONSOLIDATED_AGI_20251225_002354.xlsx
  [RESULT] Timestamp: 2025-12-25 00:24:11
```

### 3.7.6 에러 핸들링

**Non-critical 처리:**
- COM 후처리 실패 시에도 파이프라인은 정상 완료 (Exit code: 0)
- Warning 메시지 출력 후 계속 진행

**Timeout 설정:**
- 기본: 120초
- 초과 시: Warning 출력 후 skip

**Fallback:**
```bash
# 수동 실행
python ballast_excel_finalize.py --auto
```

### 3.7.7 검증 방법

**배포 전 확인:**

1. **Calc_Log 시트 확인**
   - Excel 파일 열기
   - Calc_Log 시트 존재 확인
   - FullRebuild_Completed = SUCCESS 확인
   - 최근 타임스탬프 확인

2. **수식 무결성 검증**
   - RORO_Stage_Scenarios 시트
   - BC18:BR28 범위 데이터 존재
   - Stage 6A AFT = 2.70m 확인
   - Ctrl+F → `#N/A`, `#REF!`, `#VALUE!` 검색 (0건)

3. **콘솔 로그 확인**
   - `[FORMULA FINALIZE]` 섹션 출력
   - `SUCCESS` 메시지
   - `[RESULT]` 라인 출력

### 3.7.8 성능

| 파일 크기 | 수식 수 | 처리 시간 | 상태 |
|-----------|---------|-----------|------|
| < 5 MB | < 1,000 | < 5초 | ✅ Excellent |
| 5-10 MB | 1,000-5,000 | 5-15초 | ✅ Good |
| 10-50 MB | 5,000-10,000 | 15-60초 | ⚠️ Acceptable |
| > 50 MB | > 10,000 | > 60초 | ❌ Review |

**현재 프로젝트:** 121 KB, 7,887 formulas → **~11초** ✅

### 3.7.9 요구사항

**필수:**
- Windows OS
- Microsoft Excel 설치
- Python 3.8+
- `pip install pywin32`

**선택:**
- pywin32 post-install: `python -m pywin32_postinstall -install`

### 3.7.10 참고 문서

- 스크립트: `ballast_excel_finalize.py`
- 가이드: `docs/EXCEL_FORMULA_PRESERVATION.md`
- Patch 정보: `docs/10_System_Improvements_and_Patches.md` (Patch v3.7)

---

## 3.9 실행 환경 요구사항

### 3.9.1 Python 환경

- Python 3.7 이상
- 현재 실행 중인 Python 인터프리터 사용 (`sys.executable`)
- Windows/Linux/macOS 모두 지원

### 3.9.2 필수 입력 파일

| 파일 | 위치 | 설명 |
|------|------|------|
| `tank_catalog_from_tankmd.json` | `inputs_dir` | 탱크 카탈로그 |
| `Hydro_Table_Engineering.json` | `inputs_dir/bplus_inputs/` | Hydrostatic Table |
| `stage_results.csv` | `base_dir` | Stage 결과 (Step 1b에서 생성 가능) |

### 3.9.3 선택적 입력 파일

**프로파일 및 센서 데이터:**
- `profiles/AGI.json`: Site 프로파일 (게이트 값, 펌프율, UKC 파라미터 등)
- `sensors/current_t_sensor.csv`: Current_t 센서 데이터 (PLC/IoT)

**Tide Integration (AGI-only, 선택적):**
- `bplus_inputs/water tide_202512.xlsx`: Time-series tide data (Excel)
- `bplus_inputs/tide_windows_AGI.json`: Stage time windows (JSON)
- `bplus_inputs/stage_schedule.csv`: Stage schedule with tide (fallback, Option B Hybrid)
- `tide/tide_ukc_engine.py`: SSOT engine for Tide/UKC calculations (3-tier fallback)

**SPMT Integration (선택적):**
- `spmt/cargo_spmt_inputs_config_example.json`: SPMT config (JSON)

**Step 1, 2 관련:**
Step 1, 2에서 사용되는 추가 JSON 파일들 (GM_Min_Curve.json, Acceptance_Criteria.json 등)은 각 스크립트의 요구사항에 따라 필요할 수 있습니다.

---

## 3.10 다음 장 안내

- **제4장**: LP Solver 로직 - 선형 프로그래밍 수학적 모델 및 최적화 알고리즘
- **제5장**: Definition-Split과 Gates - 개념 및 구현 상세
- **제6장**: 스크립트 인터페이스 및 API - 각 스크립트의 명령줄 인자 및 인터페이스

---

**참고:**
- 제1장: 파이프라인 아키텍처 개요
- 제2장: 데이터 흐름과 SSOT
- `Ballast Pipeline 운영 가이드.MD`: 프로파일 시스템, 센서 데이터 통합, Gate FAIL 리포트 등 최신 기능 상세
- `integrated_pipeline_defsplit_v2.py`: 메인 파이프라인 구현
- `03_DOCUMENTATION/AGENTS.md`: 좌표계, Gate 정의, Tank Direction SSOT

**문서 버전:** v3.4 (tide_ukc_engine.py SSOT 엔진 문서화 추가)
**최종 업데이트:** 2025-12-27
