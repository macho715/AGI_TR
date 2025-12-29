# AGI_TR - Ballast Management Pipeline

AGI RORO TR (Transport) 프로젝트를 위한 통합 Ballast Management 파이프라인 시스템입니다.

## 📋 프로젝트 개요

이 프로젝트는 선박의 **Ballast Management** 작업을 자동화하고 최적화하기 위한 통합 파이프라인입니다. SSOT (Single Source of Truth) 원칙을 기반으로 Gate 정의, Tank catalog, Site profile을 통합 관리하며, Linear Programming 기반의 최적화를 통해 Ballast 계획을 자동 생성합니다.

## ✨ 주요 기능

- **SSOT (Single Source of Truth)**: Gate 정의, Tank catalog, Site profile의 단일 소스 통합
- **Definition Split**: 조위 예보(Forecast Tide)와 요구 수면고(Required WL)의 명확한 분리
- **Gate Unified System**: FWD 최대값과 AFT 최소값을 동시에 강제하는 게이트 시스템
- **Linear Programming 최적화**: LP Solver 기반 Ballast 계획 최적화
- **자동화 워크플로우**: 6개의 독립 단계를 순차적으로 실행
- **운영 준비**: Ballast sequence, Hold point, Valve lineup 자동 생성
- **Tide Integration**: 조위 기반 UKC 계산 및 검증
- **SPMT Integration**: SPMT cargo 자동 import 및 통합

## 📁 디렉토리 구조

```
AGI_TR/
├── 01_EXECUTION_FILES/      # 실행 파일 및 스크립트
│   ├── agi_tr_patched_v6_6_defsplit_v1.py
│   ├── ballast_sequence_generator.py
│   ├── bplus_inputs/        # B+ 입력 데이터
│   ├── ssot/                # SSOT 모듈
│   ├── tide/                # Tide 계산 모듈
│   └── spmt v1/             # SPMT 통합 모듈
├── 02_RAW_DATA/             # 원시 데이터
│   ├── profiles/            # Site profile JSON
│   ├── sensors/             # 센서 데이터
│   └── additional_inputs/   # 추가 입력 파일
└── 03_DOCUMENTATION/        # 문서
    └── 00_CORE_ARCHITECTURE/ # 핵심 아키텍처 문서
```

## 🚀 설치 방법

### 필수 요구사항

- Python 3.8 이상
- Git

### 의존성 설치

```bash
cd 01_EXECUTION_FILES
pip install -r requirements.txt
```

주요 의존성:
- `pandas>=1.5.0`
- `numpy>=1.23.0`
- `openpyxl>=3.0.0`
- `scipy>=1.9.0`
- `polars>=0.19.0` (고성능 I/O)
- `pydantic>=2.0.0` (데이터 검증)

## 📖 사용 방법

### 기본 실행

```bash
cd 01_EXECUTION_FILES
python agi_tr_patched_v6_6_defsplit_v1.py
```

### 주요 스크립트

- **메인 파이프라인**: `agi_tr_patched_v6_6_defsplit_v1.py`
- **Ballast Sequence 생성**: `ballast_sequence_generator.py`
- **Excel 템플릿 생성**: `create_bryan_excel_template_NEW.py`
- **Valve Lineup 생성**: `valve_lineup_generator.py`

## 📚 문서

상세한 문서는 `03_DOCUMENTATION/00_CORE_ARCHITECTURE/` 디렉토리에서 확인할 수 있습니다.

### 권장 읽기 순서

1. **시작**: `00_System_Architecture_Complete.md`
2. **데이터 흐름 이해**: `02_Data_Flow_SSOT.md`, `03_Pipeline_Execution_Flow.md`
3. **Solver 이해**: `04_LP_Solver_Logic.md`, `05_Definition_Split_Gates.md`
4. **사용 가이드**: `08_Bushra_System_User_Guide.md`

## 🔄 최신 버전 정보

### v3.7 (2025-12-29)
- Forecast_Tide_m 우선순위 변경 (일관성 문제 해결)
- CLI `--forecast_tide` 값 최우선 적용

### v3.6 (2025-12-28)
- Option 2 구현 완료 (BALLAST_SEQUENCE 옵션/실행 분리)
- Start_t/Target_t carry-forward 구현
- Stage 6B 분리 처리

### v3.5 (2025-12-28)
- I/O 최적화 (PR-01~05)
- Polars lazy scan, Parquet sidecar cache
- Manifest 로깅 통합

### v3.4 (2025-12-27)
- Tide Integration (AGI-only)
- SPMT Integration
- Step 5 추가 (SPMT Integrated Excel, Bryan Template)

## 🛠️ 개발

### 프로젝트 구조

- **SSOT 모듈**: `01_EXECUTION_FILES/ssot/`
  - `gates_loader.py`: Gate 정의 로더
  - `draft_calc.py`: Draft 계산
  - `validators.py`: 데이터 검증

- **Tide 모듈**: `01_EXECUTION_FILES/tide/`
  - `tide_ukc_engine.py`: UKC 계산 엔진
  - `tide_constants.py`: Tide 상수

## 📝 라이선스

이 프로젝트는 AGI 전용 프로젝트입니다.

## 👥 기여

프로젝트 개선을 위한 제안이나 버그 리포트는 Issues를 통해 제출해주세요.

## 📞 문의

프로젝트 관련 문의사항이 있으시면 저장소의 Issues를 통해 연락해주세요.

