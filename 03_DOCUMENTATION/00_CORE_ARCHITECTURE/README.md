# 00_CORE_ARCHITECTURE

핵심 아키텍처 문서 모음 (00-16 번호 체계)

**생성일**: 2025-12-27

## 문서 목록

### 시스템 아키텍처 (00-01)
- **00_System_Architecture_Complete.md** - 전체 시스템 아키텍처 통합 문서
- **01_Architecture_Overview.md** - 아키텍처 개요

### 데이터 흐름 및 SSOT (02-03)
- **02_Data_Flow_SSOT.md** - 데이터 흐름 및 SSOT (Single Source of Truth)
- **03_Pipeline_Execution_Flow.md** - 파이프라인 실행 흐름

### Solver 및 Gate (04-05)
- **04_LP_Solver_Logic.md** - LP Solver 로직 상세
- **05_Definition_Split_Gates.md** - Gate 정의 및 Definition Split

### 인터페이스 및 가이드 (06-09)
- **06_Script_Interfaces.md** - 스크립트 인터페이스
- **07_AFT_Draft_Analysis_and_Forward_Inventory_Strategy.md** - AFT Draft 분석 및 Forward Inventory 전략
- **08_Bushra_System_User_Guide.md** - BUSHRA 시스템 사용자 가이드
- **09_Parameter_Based_Auto_Calculator.md** - 파라미터 기반 자동 계산기

### 개선사항 및 도구 (10, 12)
- **10_System_Improvements_and_Patches.md** - 시스템 개선사항 및 패치 이력
- **12_Development_Tools_Integration.md** - 개발 도구 통합

### 완료 보고서 및 가이드 (13-16)
- **13_AGI_TR_Core_Engine_Completion_Report.md** - AGI TR 코어 엔진 완료 보고서
- **14_Modified_Option4_Complete_Guide.md** - 수정된 Option4 완전 가이드
- **15_Final_Delivery_Package_Guide.md** - 최종 배포 패키지 가이드
- **16_P0_Guard_Band_and_Step_wise_Gate_B_Guide.md** - P0 Guard Band 및 단계별 Gate-B 가이드

### 통합 문서
- **파이프라인 전체 아키텍처, 실행 파일, 로직 상세 설명.MD** - 파이프라인 전체 아키텍처 상세 문서 (v4.1)
- **Ballast Pipeline 운영 가이드.MD** - Ballast Pipeline 운영 가이드
- **Ballast_Pipeline_Core_Functions.md** - Ballast Pipeline 핵심 함수 문서

## 문서 읽기 순서 권장

1. **시작**: `00_System_Architecture_Complete.md` 또는 `01_Architecture_Overview.md`
2. **데이터 흐름 이해**: `02_Data_Flow_SSOT.md`, `03_Pipeline_Execution_Flow.md`
3. **상세 로직**: `파이프라인 전체 아키텍처, 실행 파일, 로직 상세 설명.MD`
4. **Solver 이해**: `04_LP_Solver_Logic.md`, `05_Definition_Split_Gates.md`
5. **사용 가이드**: `08_Bushra_System_User_Guide.md`, `Ballast Pipeline 운영 가이드.MD`

## 버전 정보

- **v3.7 (2025-12-29)**: Forecast_Tide_m 우선순위 변경 (일관성 문제 해결)
  - CLI `--forecast_tide` 값이 최우선 적용
  - `stage_table_unified.csv`와 `solver_ballast_summary.csv` 간 `Forecast_Tide_m` 완전 일치 보장
  - `17_TIDE_UKC_Calculation_Logic.md`: v1.1 (우선순위 변경 상세)
  - `02_Data_Flow_SSOT.md`: v3.6 (SSOT 규칙 업데이트)
  - `03_Pipeline_Execution_Flow.md`: v3.5 (우선순위 업데이트)

- **v3.6 (2025-12-28)**: Option 2 구현 완료 (BALLAST_SEQUENCE 옵션/실행 분리)
  - Step 4b: Ballast Sequence Generator 확장
    - `generate_sequence_with_carryforward()`: Start_t/Target_t carry-forward 구현
    - `generate_option_plan()`: Delta_t 계획 생성 (Stage 6B 포함)
    - `BALLAST_OPTION.csv`: 계획 레벨 (모든 Stage 포함)
    - `BALLAST_EXEC.csv`: 실행 시퀀스 (Stage 6B 제외, Start_t/Target_t 체인)
    - `BALLAST_SEQUENCE.xlsx`: Excel (Ballast_Option, Ballast_Exec, Ballast_Sequence 시트)
  - Option 1 패치 제안 (미구현): Bryan Pack Forecast_tide_m 주입, Stage 5_PreBallast critical 적용
  - `01_Architecture_Overview.md`: v3.5 (Option 2 반영)
  - `02_Data_Flow_SSOT.md`: v3.5 (Option 2 반영)
  - `06_Script_Interfaces.md`: v2.4 (Step 4b 인터페이스 추가)
  - `Ballast Pipeline 운영 가이드.MD`: v2.3 (Option 2 반영)
  - `파이프라인 전체 아키텍처, 실행 파일, 로직 상세 설명.MD`: v4.2 (Option 2 반영)

- **v3.5 (2025-12-28)**: I/O Optimization (PR-01~05), MAMMOET Calculation Sheet Generator
  - I/O Performance: Polars lazy scan, Parquet sidecar cache, Manifest logging
  - `00_System_Architecture_Complete.md`: v3.5
  - `01_Architecture_Overview.md`: v3.4
  - `02_Data_Flow_SSOT.md`: v3.4
  - `03_Pipeline_Execution_Flow.md`: v3.4
  - `06_Script_Interfaces.md`: v2.3
  - `10_System_Improvements_and_Patches.md`: v3.3 (PR-01~05 추가)
- **v3.4 (2025-12-27)**: Tide Integration, SPMT Integration, Step 5 추가
  - `00_System_Architecture_Complete.md`: v3.4
  - `02_Data_Flow_SSOT.md`: v3.3
  - `03_Pipeline_Execution_Flow.md`: v3.3
- **v3.1-v3.3 (2025-12-27)**: Current_t 자동 탐색, diff_audit.csv, GM 검증 v2b
- 파이프라인 전체 아키텍처: v4.1 (2025-12-27 업데이트)

## 최신 기능

### v3.6 (2025-12-28): Option 2 구현 완료 (BALLAST_SEQUENCE 옵션/실행 분리)
- **Step 4b 확장**: `ballast_sequence_generator.py`
  - `generate_sequence_with_carryforward()`: 실행 시퀀스 생성 (Stage 6B 제외, Start_t/Target_t carry-forward)
  - `generate_option_plan()`: 옵션 계획 생성 (Delta_t 중심, Stage 6B 포함)
  - `export_to_option_dataframe()` / `export_to_exec_dataframe()`: 분리된 DataFrame 생성
  - `export_option_to_csv()` / `export_exec_to_csv()`: 분리된 CSV 생성
- **출력 파일 분리**:
  - `BALLAST_OPTION.csv`: 계획 레벨 (Delta_t 중심, 모든 Stage 포함)
  - `BALLAST_EXEC.csv`: 실행 시퀀스 (Start_t/Target_t 체인, Stage 6B 제외)
  - `BALLAST_SEQUENCE.xlsx`: Excel (Ballast_Option, Ballast_Exec, Ballast_Sequence 시트)
- **핵심 기능**:
  - Start_t/Target_t carry-forward: 탱크별 상태 추적, 이전 step의 Target_t → 다음 Start_t 자동 전달
  - Stage 6B 분리: 옵션 계획에는 포함, 실행 시퀀스에서는 제외
  - 탱크 용량 검증: target_t > Capacity_t 시 자동 클리핑
- **Option 1 패치 제안 (미구현)**:
  - Bryan Pack Forecast_tide_m 주입
  - Stage 5_PreBallast GateB critical 강제
  - Current_* vs Draft_* 단일화

### v3.5 (2025-12-28): I/O Optimization (PR-01~05)
- **PR-01 (Manifest)**: Subprocess-safe JSONL 로깅 (`perf_manifest.py`)
  - Run ID 기반 manifest 파일 생성
  - Step별 PID 기반 파일 분리
  - I/O 작업 자동 추적
- **PR-02 (Encoding/Delimiter)**: 1-pass 탐지 (`io_detect.py`)
  - BOM-first encoding detection
  - Delimiter 자동 추론
- **PR-03 (Fast CSV)**: Polars lazy scan (`io_csv_fast.py`)
  - Polars lazy evaluation 우선 사용
  - pandas fallback (pyarrow → c → python)
  - Manifest 로깅 통합
- **PR-04 (Parquet Cache)**: Sidecar 캐시 (`io_parquet_cache.py`)
  - `stage_results.parquet` 자동 생성
  - mtime 기반 캐시 검증
  - Cache hit/miss 자동 로깅
- **PR-05 (Wiring)**: Orchestrator/OPS/StageExcel 통합
  - `read_table_any()` 우선 사용 (Parquet → CSV fast-path)
  - 모든 CSV 읽기 지점 최적화

### v3.4 (2025-12-27): Tide Integration & SPMT Integration
- **Tide Integration (AGI-only)**:
  - Pre-Step: `tide_stage_mapper.py` - Stage-wise tide mapping
  - Stage Table: `Forecast_Tide_m`, `DatumOffset_m` 컬럼 추가
  - UKC 계산: Tide-dependent UKC, `Tide_required_m`, `Tide_margin_m`, `Tide_verdict`
  - AUTO-HOLD Warnings: Holdpoint stages 자동 경고
  - Consolidated Excel: `TIDE_BY_STAGE` sheet 자동 생성
- **SPMT Integration**:
  - `spmt_unified.py`: SPMT unified entrypoint
  - `spmt_integrated_excel.py`: SPMT integrated Excel builder
  - Bryan Template: SPMT cargo 자동 import
- **Step 5 추가**:
  - Step 5a: SPMT Integrated Excel generation
  - Step 5b: Bryan Template Generation (SPMT cargo 포함)
  - Step 5c: Consolidated Excel (TIDE_BY_STAGE sheet 포함)

### 추가 도구 (2025-12-28)
- **MAMMOET Calculation Sheet Generator**: `create_mammoet_calculation_sheet.py`
  - MAMMOET 스타일 기술 계산서 자동 생성
  - Word 문서 형식 (python-docx)
  - 서명 섹션 포함
