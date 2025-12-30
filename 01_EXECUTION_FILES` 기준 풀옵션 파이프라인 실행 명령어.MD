`01_EXECUTION_FILES` 기준 풀옵션 파이프라인 실행 명령어 구성 중. 모든 옵션 확인 중.


[5 tools called]


풀옵션 파이프라인 실행 명령어 구성 중. 모든 옵션 확인 중.


[3 tools called]


`01_EXECUTION_FILES` 기준 풀옵션 파이프라인 실행 명령어:

## 풀옵션 파이프라인 실행 명령어

### 기본 풀옵션 실행 (모든 Step + 모든 기능 활성화)

```bash
cd "C:\AGI RORO TR\01_EXECUTION_FILES"

python tide\integrated_pipeline_defsplit_v2_gate270_split_v3_auditpatched_autodetect_TIDE_v1.py ^
    --site AGI ^
    --from_step 0 ^
    --to_step 5 ^
    --enable-sequence ^
    --enable-valve-lineup ^
    --enable-headers-ssot ^
    --headers-registry headers_registry.json ^
    --head-registry HEAD_REGISTRY_AGI_v3.0.yaml ^
    --auto-head-guard ^
    --auto_debug_report ^
    --stateful_solver ^
    --four_corner_monitoring ^
    --forecast_tide 2.00 ^
    --depth_ref 5.50 ^
    --ukc_min 0.50 ^
    --squat 0.15 ^
    --safety_allow 0.20 ^
    --tide_tol 0.10 ^
    --gate_guard_band_cm 2.0 ^
    --fwd_max 2.70 ^
    --aft_min 2.70 ^
    --aft_max 3.50 ^
    --trim_abs_limit 0.50 ^
    --trim-limit-enforced ^
    --freeboard-min-m 0.0 ^
    --freeboard-min-enforced ^
    --pump_rate 100.0 ^
    --tank_keywords "BALLAST,VOID,FWB,FW,DB" ^
    --base_dir . ^
    --inputs_dir . ^
    --profile_json "bplus_inputs\profiles\AGI.json"
```

### 고급 풀옵션 실행 (Tide Table + Stage Schedule 포함)

```bash
cd "C:\AGI RORO TR\01_EXECUTION_FILES"

python tide\integrated_pipeline_defsplit_v2_gate270_split_v3_auditpatched_autodetect_TIDE_v1.py ^
    --site AGI ^
    --from_step 0 ^
    --to_step 5 ^
    --enable-sequence ^
    --enable-valve-lineup ^
    --enable-headers-ssot ^
    --headers-registry headers_registry.json ^
    --head-registry HEAD_REGISTRY_AGI_v3.0.yaml ^
    --auto-head-guard ^
    --auto_debug_report ^
    --stateful_solver ^
    --state_trace_csv "pipeline_out_%TIMESTAMP%\solver_state_trace.csv" ^
    --four_corner_monitoring ^
    --forecast_tide 2.00 ^
    --depth_ref 5.50 ^
    --ukc_min 0.50 ^
    --squat 0.15 ^
    --safety_allow 0.20 ^
    --tide_tol 0.10 ^
    --tide_table "bplus_inputs\water tide_202512.xlsx" ^
    --stage_schedule "bplus_inputs\stage_schedule.csv" ^
    --tide_strategy "override_from_table" ^
    --hmax_wave_m 2.0 ^
    --gate_guard_band_cm 2.0 ^
    --fwd_max 2.70 ^
    --aft_min 2.70 ^
    --aft_max 3.50 ^
    --trim_abs_limit 0.50 ^
    --trim-limit-enforced ^
    --freeboard-min-m 0.0 ^
    --freeboard-min-enforced ^
    --pump_rate 100.0 ^
    --tank_keywords "BALLAST,VOID,FWB,FW,DB" ^
    --current_t_csv "sensors\current_t_final_verified.csv" ^
    --current_t_strategy "override" ^
    --tank_operability_json "bplus_inputs\profiles\AGI.json" ^
    --operational_stage_regex "(6a|critical|ramp|roll|loadout)" ^
    --base_dir . ^
    --inputs_dir . ^
    --profile_json "bplus_inputs\profiles\AGI.json" ^
    --hydro "bplus_inputs\Hydro_Table_Engineering.json" ^
    --tank_catalog "tank_catalog_from_tankmd.json" ^
    --spmt_config "spmt v1\spmt_shuttle_example_config_AGI_FR_M.json"
```

### 최대 풀옵션 실행 (모든 고급 기능 + 센서 데이터)

```bash
cd "C:\AGI RORO TR\01_EXECUTION_FILES"

# 환경 변수 설정 (선택적)
set EXCEL_COM_RECALC=1
set EXCEL_INJECT_ALL_SHEETS=1
set EXCEL_INJECT_DEBUG=0

python tide\integrated_pipeline_defsplit_v2_gate270_split_v3_auditpatched_autodetect_TIDE_v1.py ^
    --site AGI ^
    --from_step 0 ^
    --to_step 5 ^
    --enable-sequence ^
    --enable-valve-lineup ^
    --enable-headers-ssot ^
    --headers-registry headers_registry.json ^
    --head-registry HEAD_REGISTRY_AGI_v3.0.yaml ^
    --auto-head-guard ^
    --auto_debug_report ^
    --stateful_solver ^
    --state_trace_csv "solver_state_trace.csv" ^
    --four_corner_monitoring ^
    --forecast_tide 2.00 ^
    --depth_ref 5.50 ^
    --ukc_min 0.50 ^
    --squat 0.15 ^
    --safety_allow 0.20 ^
    --tide_tol 0.10 ^
    --tide_table "bplus_inputs\water tide_202512.xlsx" ^
    --stage_schedule "bplus_inputs\stage_schedule.csv" ^
    --stage_tide_csv "stage_tide_AGI.csv" ^
    --tide_strategy "override_from_table" ^
    --hmax_wave_m 2.0 ^
    --gate_guard_band_cm 2.0 ^
    --fwd_max 2.70 ^
    --aft_min 2.70 ^
    --aft_max 3.50 ^
    --trim_abs_limit 0.50 ^
    --trim-limit-enforced ^
    --freeboard-min-m 0.0 ^
    --freeboard-min-enforced ^
    --pump_rate 100.0 ^
    --tank_keywords "BALLAST,VOID,FWB,FW,DB" ^
    --current_t_csv "sensors\current_t_final_verified.csv" ^
    --current_t_strategy "override" ^
    --tank_operability_json "bplus_inputs\profiles\AGI.json" ^
    --operational_stage_regex "(6a|critical|ramp|roll|loadout)" ^
    --exclude_fwd_tanks_aftmin_only ^
    --base_dir . ^
    --inputs_dir . ^
    --profile_json "bplus_inputs\profiles\AGI.json" ^
    --hydro "bplus_inputs\Hydro_Table_Engineering.json" ^
    --tank_catalog "tank_catalog_from_tankmd.json" ^
    --spmt_config "spmt v1\spmt_shuttle_example_config_AGI_FR_M.json" ^
    --tr_script "agi_tr_patched_v6_6_defsplit_v1.py" ^
    --ops_script "tide\ops_final_r3_integrated_defs_split_v4_patched_TIDE_v1.py" ^
    --solver_script "tide\ballast_gate_solver_v4_TIDE_v1.py" ^
    --optimizer_script "Untitled-2_patched_defsplit_v1_1.py" ^
    --spmt_script "spmt v1\agi_spmt_unified.py" ^
    --bryan_template_script "tide\bryan_template_unified_TIDE_v1.py"
```

### PowerShell 버전 (권장)

```powershell
cd "C:\AGI RORO TR\01_EXECUTION_FILES"

# 환경 변수 설정 (선택적)
$env:EXCEL_COM_RECALC = "1"
$env:EXCEL_INJECT_ALL_SHEETS = "1"
$env:EXCEL_INJECT_DEBUG = "0"

python tide\integrated_pipeline_defsplit_v2_gate270_split_v3_auditpatched_autodetect_TIDE_v1.py `
    --site AGI `
    --from_step 0 `
    --to_step 5 `
    --enable-sequence `
    --enable-valve-lineup `
    --enable-headers-ssot `
    --headers-registry headers_registry.json `
    --head-registry HEAD_REGISTRY_AGI_v3.0.yaml `
    --auto-head-guard `
    --auto_debug_report `
    --stateful_solver `
    --state_trace_csv "solver_state_trace.csv" `
    --four_corner_monitoring `
    --forecast_tide 2.00 `
    --depth_ref 5.50 `
    --ukc_min 0.50 `
    --squat 0.15 `
    --safety_allow 0.20 `
    --tide_tol 0.10 `
    --tide_table "bplus_inputs\water tide_202512.xlsx" `
    --stage_schedule "bplus_inputs\stage_schedule.csv" `
    --tide_strategy "override_from_table" `
    --hmax_wave_m 2.0 `
    --gate_guard_band_cm 2.0 `
    --fwd_max 2.70 `
    --aft_min 2.70 `
    --aft_max 3.50 `
    --trim_abs_limit 0.50 `
    --trim-limit-enforced `
    --freeboard-min-m 0.0 `
    --freeboard-min-enforced `
    --pump_rate 100.0 `
    --tank_keywords "BALLAST,VOID,FWB,FW,DB" `
    --current_t_csv "sensors\current_t_final_verified.csv" `
    --current_t_strategy "override" `
    --tank_operability_json "bplus_inputs\profiles\AGI.json" `
    --operational_stage_regex "(6a|critical|ramp|roll|loadout)" `
    --exclude_fwd_tanks_aftmin_only `
    --base_dir . `
    --inputs_dir . `
    --profile_json "bplus_inputs\profiles\AGI.json"
```

### 주요 옵션 설명

| 옵션 | 설명 |
|------|------|
| `--from_step 0 --to_step 5` | Step 0(SPMT) ~ Step 5(Bryan Template) 모두 실행 |
| `--enable-sequence` | Step 4b: Ballast Sequence & Checklist 생성 |
| `--enable-valve-lineup` | Step 4c: Valve Lineup 생성 |
| `--enable-headers-ssot` | Headers SSOT 활성화 |
| `--auto-head-guard` | Head Guard 자동 검증 |
| `--auto_debug_report` | 디버그 리포트 자동 생성 |
| `--stateful_solver` | Stateful solver (Current_t carry-forward) |
| `--four_corner_monitoring` | 4-corner freeboard 모니터링 |
| `--tide_table` + `--stage_schedule` | Tide table 기반 stage별 tide 보간 |
| `--current_t_csv` | 센서 데이터 주입 |

### 실행 전 확인사항

1. 필수 파일 존재 확인:
   - `tank_catalog_from_tankmd.json`
   - `bplus_inputs/Hydro_Table_Engineering.json`
   - `bplus_inputs/profiles/AGI.json`
   - `headers_registry.json`
   - `HEAD_REGISTRY_AGI_v3.0.yaml`

2. 선택적 파일 (없어도 실행 가능):
   - `sensors/current_t_final_verified.csv`
   - `bplus_inputs/water tide_202512.xlsx`
   - `bplus_inputs/stage_schedule.csv`
   - `stage_tide_AGI.csv`

3. 출력 폴더:
   - 자동 생성: `pipeline_out_YYYYMMDD_HHMMSS/`
   - 최종 출력: `final_output_YYYYMMDD_HHMMSS/`

위 명령어 중 하나를 선택해 실행하세요. PowerShell 버전을 권장합니다.
