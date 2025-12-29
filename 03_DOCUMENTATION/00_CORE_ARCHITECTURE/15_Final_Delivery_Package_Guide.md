# Final Delivery Package 사용 가이드

**작성일:** 2025-12-25
**패키지:** FINAL_DELIVERY_20251225
**버전:** v3.2 (Updated: 2025-12-27)
**상태:** 배포 준비 완료

**최신 업데이트 (v3.2 - 2025-12-27):**
- Current_t 자동 탐색 기능 반영 (섹션 3.1)
- Gate-A/Gate-B 라벨 SSOT 명확화 (섹션 1.2)

---

## 목차

1. [패키지 개요](#1-패키지-개요)
2. [패키지 구조](#2-패키지-구조)
3. [파일 설명](#3-파일-설명)
4. [사용 방법](#4-사용-방법)
5. [검증 절차](#5-검증-절차)
6. [배포 가이드](#6-배포-가이드)

---

## 1. 패키지 개요

### 1.1 패키지 정보

**위치:**
```
c:\PATCH_PLAN_zzzzzqqqqssq.html\LCF\new\ballast_pipeline_defsplit_v2_complete\FINAL_DELIVERY_20251225\
```

**구성:**
- 총 28개 파일 + 1 README
- 5개 카테고리로 분류
- 배포 준비 완료

### 1.2 달성 목표

| 항목 | 목표 | 달성 | 상태 |
|------|------|------|------|
| **Stage 5 AFT** | 2.70m (`AFT_MIN_2p70`) | **2.70m** | ✅ 100% |
| **Stage 6A AFT** | 2.70m (`AFT_MIN_2p70`) | **2.70m** | ✅ 100% |
| **Gate-A** (`AFT_MIN_2p70`) | PASS | **PASS** | ✅ 양 stage |
| **Gate-B** (`FWD_MAX_2p70_critical_only`) | PASS | **PASS** | ✅ Critical stages |
| **재현성** | Required | **Verified** | ✅ Identical |

**Gate Labels SSOT:**
- Gate-A: `AFT_MIN_2p70` (Captain / Propulsion) - 모든 propulsion-relevant stages
- Gate-B: `FWD_MAX_2p70_critical_only` (Mammoet / Critical RoRo only) - Critical stages만
- **Important:** Never write "2.70m" alone. Always use the labels to prevent ambiguity.

---

## 2. 패키지 구조

### 2.1 전체 구조

```
FINAL_DELIVERY_20251225/
│
├── README.md                           ← 시작 여기서!
│
├── 01_PIPELINE_OUTPUT/     (8 files)
│   ├── PIPELINE_CONSOLIDATED_AGI_20251225_134917.xlsx  ← 최종 Excel
│   ├── pipeline_stage_QA.csv
│   ├── solver_ballast_stage_plan.csv
│   ├── solver_ballast_summary.csv
│   ├── tank_ssot_for_solver.csv
│   ├── tank_ssot_for_solver__aftmin.csv
│   ├── hydro_table_for_solver.csv
│   └── stage_table_unified.csv
│
├── 02_BALLAST_OPERATIONS/  (5 files)
│   ├── BALLAST_SEQUENCE.xlsx                  ← 21단계, 36.6시간
│   ├── BALLAST_SEQUENCE.csv
│   ├── BALLAST_OPERATIONS_CHECKLIST.md       ← 현장 체크리스트
│   ├── BALLAST_SEQUENCE_WITH_VALVES.md       ← 밸브 작업
│   └── OPS_FINAL_R3_AGI_Ballast_Integrated.xlsx
│
├── 03_REPORTS/             (8 files)
│   ├── MODIFIED_OPTION4_FINAL_REPORT_20251225.md  ← 최종 보고서
│   ├── STAGE5_AFT_ACHIEVEMENT_FINAL_REPORT_20251225.md
│   ├── FORWARD_INVENTORY_EXECUTION_REPORT_20251225.md
│   ├── FULL_PIPELINE_EXECUTION_REPORT_20251225.md
│   ├── P0_P1_COMPLETION_SUMMARY.md
│   ├── B1_EXECUTION_SUMMARY_20251225.md
│   ├── OPS_FINAL_R3_Report_Integrated.md
│   └── TUG_Operational_SOP_DNV_ST_N001.md
│
├── 04_INPUT_CONFIG/        (4 files)
│   ├── current_t_sensor.csv                   ← FWB2 28.50t/side
│   ├── site_profile_AGI_aft_ballast_EXACT_ONLY.json
│   ├── tank_catalog_from_tankmd.json
│   └── Hydro_Table_Engineering.json
│
└── 05_VALIDATION/          (3 files)
    ├── verify_reproducibility.py              ← 재현성 검증
    ├── BC_BR_CHECK_REPORT.md
    └── manifest.json
```

---

## 3. 파일 설명

### 3.1 필수 파일 (Top 5)

#### 1️⃣ PIPELINE_CONSOLIDATED_AGI_20251225_134917.xlsx

**위치:** `01_PIPELINE_OUTPUT/`

**내용:**
- 28 sheets 통합 Excel 워크북
- Stage별 draft 결과 (Stage 5: 2.70m, Stage 6A: 2.70m)
- Gate 검증 결과 (모두 PASS)
- Tank SSOT, Solver 결과

**사용:**
```
1. Excel 열기
2. RORO_Stage_Scenarios 시트 확인
3. BC-BR 컬럼에서 post-solver draft 확인
4. Tank_SSOT 시트에서 FWB2 = 28.50t 확인
```

#### 2️⃣ MODIFIED_OPTION4_FINAL_REPORT_20251225.md

**위치:** `03_REPORTS/`

**내용:**
- Modified Option 4 전체 과정
- 재현성 검증 결과
- 배포 승인 권고

**사용:**
- 엔지니어링 리뷰
- 승인 프로세스
- 기술 문서화

#### 3️⃣ BALLAST_SEQUENCE.xlsx

**위치:** `02_BALLAST_OPERATIONS/`

**내용:**
- 21단계 시간별 밸러스트 시퀀스
- 총 36.6시간 작업 계획
- 16개 Hold Points
- Fill/Discharge 작업 명세

**사용:**
```
1. 현장팀에 배포
2. 단계별 작업 순서 확인
3. Hold point에서 draft 측정
4. Go/No-Go 판정
```

#### 4️⃣ BALLAST_OPERATIONS_CHECKLIST.md

**위치:** `02_BALLAST_OPERATIONS/`

**내용:**
- 사전 점검 항목
- 단계별 체크리스트
- 안전 절차
- 비상 대응

**사용:**
- 작업 시작 전 점검
- 각 단계마다 확인
- 안전 확보

#### 5️⃣ current_t_sensor.csv (또는 current_t_*.csv - 자동 탐색 지원)

**위치:** `04_INPUT_CONFIG/` (또는 `sensors/` - 자동 탐색)

**참고 (v3.1):** 파이프라인은 `current_t_*.csv` 패턴을 자동으로 탐색합니다. 명시적 `--current_t_csv` 인자가 없어도 최신 파일을 자동으로 찾습니다.

**내용:**
```csv
Tank,Current_t,Timestamp
FWB1.P,50.57,2025-12-23T08:30:00Z
FWB1.S,50.57,2025-12-23T08:30:00Z
FWB2.P,28.50,2025-12-25T16:00:00Z  ← Modified Option 4
FWB2.S,28.50,2025-12-25T16:00:00Z  ← Modified Option 4
```

**사용:**
- Forward Inventory 설정 확인
- 재실행 시 입력 파일

---

## 4. 사용 방법

### 4.1 현장 운영팀 (Operations)

**Step 1: 사전 준비**
1. `README.md` 읽기
2. `BALLAST_OPERATIONS_CHECKLIST.md` 검토
3. 필요 장비 준비 (pumps, sensors, valves)

**Step 2: Forward Inventory 충전**
```bash
# 04_INPUT_CONFIG/current_t_sensor.csv 참조
FWB1.P/S: 50.57t/side
FWB2.P/S: 28.50t/side
VOID3.P/S: 100.0t/side (유지)
```

**Step 3: 밸러스트 작업 실행**
```bash
# 02_BALLAST_OPERATIONS/BALLAST_SEQUENCE.xlsx 따라
1. Step 1-21 순서대로 실행
2. Hold point마다 draft 측정
3. 목표값과 비교
4. Go/No-Go 판정
```

**Step 4: 밸브 작업**
```bash
# BALLAST_SEQUENCE_WITH_VALVES.md 참조
각 단계별 상세 밸브 작업 지침 따라 실행
```

### 4.2 엔지니어링 팀 (Engineering)

**Step 1: 결과 검증**
```bash
# 01_PIPELINE_OUTPUT/pipeline_stage_QA.csv 확인
Stage 5_PreBallast: AFT = 2.700m (Gate-A: PASS)
Stage 6A_Critical:  AFT = 2.700m (Gate-A: PASS)
```

**Step 2: 보고서 리뷰**
```bash
# 03_REPORTS/ 폴더
1. MODIFIED_OPTION4_FINAL_REPORT_20251225.md
2. STAGE5_AFT_ACHIEVEMENT_FINAL_REPORT_20251225.md
3. P0_P1_COMPLETION_SUMMARY.md
```

**Step 3: 재현성 검증 (선택)**
```bash
cd 05_VALIDATION
python verify_reproducibility.py
```

### 4.3 프로젝트 관리팀 (PM)

**배포 패키지 확인:**
1. 29개 파일 완전성 검증
2. 모든 필수 문서 존재 확인
3. 승인 프로세스 진행

---

## 5. 검증 절차

### 5.1 파일 무결성 검증

**PowerShell:**
```powershell
cd FINAL_DELIVERY_20251225

# 파일 수 확인
(Get-ChildItem -Recurse -File).Count  # 29개 (README 포함)

# 폴더별 파일 수
Get-ChildItem -Directory | ForEach-Object {
    $count = (Get-ChildItem $_.FullName -File).Count
    "$($_.Name): $count files"
}
```

**예상 결과:**
```
01_PIPELINE_OUTPUT: 8 files
02_BALLAST_OPERATIONS: 5 files
03_REPORTS: 8 files
04_INPUT_CONFIG: 4 files
05_VALIDATION: 3 files
```

### 5.2 주요 값 검증

**Stage 5 & 6A Draft:**
```python
import pandas as pd

# pipeline_stage_QA.csv 확인
df = pd.read_csv('01_PIPELINE_OUTPUT/pipeline_stage_QA.csv')

stage5 = df[df['Stage']=='Stage 5_PreBallast']
stage6a = df[df['Stage']=='Stage 6A_Critical (Opt C)']

print(f"Stage 5 AFT: {stage5['Draft_AFT_m'].values[0]:.3f}m")
print(f"Stage 6A AFT: {stage6a['Draft_AFT_m'].values[0]:.3f}m")
# 예상: 2.700m, 2.700m
```

**Forward Inventory:**
```python
# tank_ssot_for_solver__aftmin.csv 확인
df_tank = pd.read_csv('01_PIPELINE_OUTPUT/tank_ssot_for_solver__aftmin.csv')

fwb2_p = df_tank[df_tank['Tank']=='FWB2.P']['Current_t'].values[0]
fwb2_s = df_tank[df_tank['Tank']=='FWB2.S']['Current_t'].values[0]

print(f"FWB2.P: {fwb2_p:.2f}t")
print(f"FWB2.S: {fwb2_s:.2f}t")
# 예상: 28.50t, 28.50t
```

---

## 6. 배포 가이드

### 6.1 배포 전 체크리스트

- [ ] 29개 파일 모두 존재
- [ ] Excel 파일 열림 확인 (28 sheets)
- [ ] Stage 5/6A AFT = 2.70m 확인
- [ ] FWB2 = 28.50t/side 확인
- [ ] 모든 보고서 읽기 가능
- [ ] README.md 내용 확인

### 6.2 배포 방법

**Option 1: 압축 파일**
```powershell
Compress-Archive -Path "FINAL_DELIVERY_20251225" `
                  -DestinationPath "FINAL_DELIVERY_20251225.zip"
```

**Option 2: 네트워크 공유**
```
\\server\projects\BUSHRA\FINAL_DELIVERY_20251225\
```

**Option 3: SharePoint/클라우드**
```
Upload entire folder to SharePoint
Share link with stakeholders
```

### 6.3 배포 대상

**필수 배포:**
1. 현장 운영팀
2. 선장 (Captain)
3. 엔지니어링 팀
4. 프로젝트 관리자

**참고 배포:**
5. MWS (Marine Warranty Surveyor)
6. Class (선급)
7. Owner 대표

### 6.4 배포 시 포함 사항

**이메일 템플릿:**
```
Subject: [FINAL] LCT BUSHRA AGI Site Ballast Plan - Modified Option 4

안녕하세요,

LCT BUSHRA AGI Site의 최종 밸러스트 계획을 첨부합니다.

주요 성과:
- Stage 5_PreBallast: AFT = 2.70m (Gate-A PASS)
- Stage 6A_Critical: AFT = 2.70m (Gate-A PASS)
- 재현성 검증 완료 (2회 실행 identical)

패키지 내용:
- 최종 Excel 결과 (28 sheets)
- 밸러스트 작업 시퀀스 (21 steps, 36.6h)
- 현장 체크리스트
- 검증 보고서

시작 가이드:
1. FINAL_DELIVERY_20251225/README.md 먼저 읽기
2. 현장팀: 02_BALLAST_OPERATIONS/ 참조
3. 엔지니어링: 03_REPORTS/ 리뷰

문의사항은 회신 부탁드립니다.

감사합니다.
```

---

## 7. 자주 묻는 질문 (FAQ)

### Q1: Modified Option 4란?

**A:** FWB2 탱크를 28.50t/side로 설정하여 Stage 5/6A의 AFT draft를 정확히 2.70m로 달성하는 Forward Inventory 전략입니다.

### Q2: 재현성이 보장되나요?

**A:** 네, 2회 파이프라인 실행 결과가 identical (0.000000m 차이)로 검증되었습니다.

### Q3: 현장에서 즉시 사용 가능한가요?

**A:** 네, 모든 필수 문서와 체크리스트가 포함되어 있습니다. `02_BALLAST_OPERATIONS/` 폴더의 파일들을 따라 실행하시면 됩니다.

### Q4: DNV Mitigation이 필요한가요?

**A:** 아니요, Modified Option 4는 AFT = 2.70m를 정확히 달성하여 DNV Mitigation이 필요하지 않습니다.

### Q5: 파이프라인 재실행이 필요한가요?

**A:** 입력 조건이 동일하면 재실행 불필요합니다. `04_INPUT_CONFIG/current_t_sensor.csv`가 변경되면 재실행해야 합니다.

---

## 8. 지원 및 문의

**기술 지원:**
- Ballast Pipeline Team
- Date: 2025-12-25
- Version: Modified Option 4 Final

**패키지 위치:**
```
c:\PATCH_PLAN_zzzzzqqqqssq.html\LCF\new\ballast_pipeline_defsplit_v2_complete\FINAL_DELIVERY_20251225\
```

---

**Modified Option 4 Forward Inventory Strategy: COMPLETE SUCCESS!** 🎉

---

*이 가이드는 FINAL_DELIVERY_20251225 패키지의 완전한 사용법을 제공합니다.*

