# Modified Option 4 완전 가이드

**작성일:** 2025-12-25
**버전:** v3.2 (Updated: 2025-12-27)
**프로젝트:** HVDC LCT BUSHRA Ballast Pipeline
**목표:** Modified Option 4 (FWB2 28.50t/side) 전체 과정 문서화

**최신 업데이트 (v3.2 - 2025-12-27):**
- Current_t 자동 탐색 기능 반영 (섹션 4.1)
- Gate-A 라벨 SSOT 명확화 (섹션 1.1)
- Tank Direction SSOT 명시 (섹션 3.2)

---

## 목차

1. [Executive Summary](#1-executive-summary)
2. [문제 정의](#2-문제-정의)
3. [해결 전략 개발](#3-해결-전략-개발)
4. [Modified Option 4 구현](#4-modified-option-4-구현)
5. [재현성 검증](#5-재현성-검증)
6. [최종 결과 및 배포](#6-최종-결과-및-배포)
7. [운영 권장사항](#7-운영-권장사항)

---

## 1. Executive Summary

### 1.1 목표 및 달성

**초기 목표:**
- Stage 5_PreBallast: AFT ≥ 2.70m (`AFT_MIN_2p70` - Gate-A)
- Stage 6A_Critical: AFT ≥ 2.70m (`AFT_MIN_2p70` - Gate-A)

**최종 달성:**
- ✅ **Stage 5_PreBallast: AFT = 2.70m** (100%)
- ✅ **Stage 6A_Critical: AFT = 2.70m** (100%)
- ✅ **재현성 검증**: 2회 실행 identical (0.000000m 차이)

**Gate Labels SSOT:**
- Gate-A: `AFT_MIN_2p70` (Captain / Propulsion)
- Gate-B: `FWD_MAX_2p70_critical_only` (Mammoet / Critical RoRo only)
- **Important:** Never write "2.70m" alone. Always use the labels to prevent ambiguity.

### 1.2 핵심 전략

**Modified Option 4 (FWB2 28.50t/side):**
- 원래 문서 계획: FWB2 21.45t/side → AFT 2.68m (FAIL)
- Modified Option 4: FWB2 28.50t/side → AFT 2.70m (PASS) ✅
- 개선량: +0.02m (정확히 2.70m 달성)

---

## 2. 문제 정의

### 2.1 초기 상황

**Raw Draft (솔버 적용 전):**
- Stage 5_PreBallast: AFT = 2.16m (목표 -0.54m)
- Stage 6A_Critical: AFT = 2.36m (목표 -0.34m)

**문제점:**
- Gate-A (AFT ≥ 2.70m) 미달
- Propeller ventilation 위험
- 추진력 손실 가능성

### 2.2 제약 조건

**Tank Capacity:**
- FW1.P/S: 23.16t (100% 사용 중, 추가 fill 불가)
- FWB2.P/S: 109.98t (capacity), 21.45t (초기 설정)

**물리적 제약:**
- LP Solver 수치 정밀도 한계
- Forward Inventory 전략만 가능 (FWD 탱크 discharge)

---

## 3. 해결 전략 개발

### 3.1 Option 비교

| Option | FWB2 (t/side) | Stage 5 AFT | Stage 6A AFT | 판정 |
|--------|---------------|-------------|--------------|------|
| Original | 21.45 | 2.68m | 2.70m | FAIL (-0.02m) |
| Option 5 | 25.00 + FODB1 | 2.65m | - | FAIL (역효과) |
| Option 6 | 27.00 | 2.69m | 2.70m | FAIL (-0.01m) |
| **Modified Option 4** | **28.50** | **2.70m** | **2.70m** | **PASS** ✅ |

### 3.2 Modified Option 4 설계 (Tank Direction SSOT)

**Forward Inventory 설정:**
```csv
Tank          Current_t    Role                    x_from_mid_m    Zone
FWB1.P/S      50.57t      Primary discharge       ~-27.4m         FWD/BOW
FWB2.P/S      28.50t      Enhanced discharge       ~-19.9m         FWD/BOW
Total         158.14t     Optimized
```

**Tank Direction SSOT:**
- FWB1/FWB2는 **FWD/BOW zone** 탱크 (Frame 48-56, x < 0)
- **Cannot be used as "stern ballast"** - SSOT physics 위반
- Forward Inventory 전략은 FWD 탱크를 **배출**하여 trim by stern 유발

**추가 모멘트 계산:**
```
추가 discharge = (28.50 - 21.45) × 2 = 14.10t
Lever = 19.887m (x_from_mid_m = -19.887m, FWD zone)
추가 모멘트 = +280.4 t·m (목표 136 t·m의 206%)
```

---

## 4. Modified Option 4 구현

### 4.1 입력 설정

**`sensors/current_t_sensor.csv` 수정 (또는 `current_t_*.csv` - 자동 탐색 지원):**

**참고 (v3.1):** 파이프라인은 `current_t_*.csv` 패턴을 자동으로 탐색합니다. 명시적 `--current_t_csv` 인자가 없어도 `inputs_dir` 또는 `inputs_dir/sensors/`에서 최신 파일을 자동으로 찾습니다.
```csv
Tank,Current_t,Timestamp
FWB1.P,50.57,2025-12-23T08:30:00Z
FWB1.S,50.57,2025-12-23T08:30:00Z
FWB2.P,28.50,2025-12-25T16:00:00Z  ← Modified Option 4
FWB2.S,28.50,2025-12-25T16:00:00Z  ← Modified Option 4
```

### 4.2 Site Profile 설정

**`site_profile_AGI_aft_ballast_EXACT_ONLY.json`:**
- FWD 탱크: `DISCHARGE_ONLY` 모드
- AFT-min gate 적용: Stage 5, 6A

### 4.3 파이프라인 실행

**실행 명령:**
```bash
python integrated_pipeline_defsplit_v2_gate270_split_v3.py \
  --site AGI \
  --profile_json site_profile_AGI_aft_ballast_EXACT_ONLY.json \
  --exclude_fwd_tanks_aftmin_only \
  --hmax_wave_m 0.30 \
  --four_corner_monitoring \
  --bplus_strict \
  --forecast_tide 0.70 \
  --depth_ref 5.50 \
  --ukc_min 0.50
```

**실행 결과:**
- Stage 5_PreBallast: AFT = 2.700m ✅
- Stage 6A_Critical: AFT = 2.700m ✅

---

## 5. 재현성 검증

### 5.1 검증 방법

**2회 파이프라인 실행:**
1. Run 1: `final_output_20251225_133729`
2. Run 2: `final_output_20251225_134918`

**검증 스크립트:**
```python
# verify_reproducibility.py
import pandas as pd

df_prev = pd.read_csv('final_output_20251225_133729/pipeline_stage_QA.csv')
df_curr = pd.read_csv('final_output_20251225_134918/pipeline_stage_QA.csv')

target_stages = ['Stage 5_PreBallast', 'Stage 6A_Critical (Opt C)']

for stage in target_stages:
    prev_aft = df_prev[df_prev['Stage']==stage]['Draft_AFT_m'].values[0]
    curr_aft = df_curr[df_curr['Stage']==stage]['Draft_AFT_m'].values[0]
    diff = curr_aft - prev_aft
    print(f'{stage}: diff = {diff:+.6f}m')
```

### 5.2 검증 결과

```
============================================================================
REPRODUCIBILITY VERIFICATION - Modified Option 4
============================================================================
Stage 5_PreBallast:
  Previous AFT: 2.700m (Gate-A Pass: True)
  Current AFT:  2.700m (Gate-A Pass: True)
  Difference:   +0.000000m [OK] IDENTICAL

Stage 6A_Critical (Opt C):
  Previous AFT: 2.700m (Gate-A Pass: True)
  Current AFT:  2.700m (Gate-A Pass: True)
  Difference:   +0.000000m [OK] IDENTICAL

[SUCCESS] Pipeline is REPRODUCIBLE - All results identical!
```

---

## 6. 최종 결과 및 배포

### 6.1 기술적 성과

| 지표 | 목표 | 달성 | 상태 |
|------|------|------|------|
| **Stage 5 AFT** | 2.70m | **2.70m** | ✅ 100% |
| **Stage 6A AFT** | 2.70m | **2.70m** | ✅ 100% |
| **Gate-A** | PASS | **PASS** | ✅ 양 stage |
| **재현성** | Required | **Verified** | ✅ 0.000000m |
| **Forward Inventory** | - | **158.14t** | ✅ 최적화 |

### 6.2 FINAL_DELIVERY 패키지

**패키지 구조:**
```
FINAL_DELIVERY_20251225/
├── 01_PIPELINE_OUTPUT/     (8 files)
├── 02_BALLAST_OPERATIONS/  (5 files)
├── 03_REPORTS/             (8 files)
├── 04_INPUT_CONFIG/        (4 files)
└── 05_VALIDATION/          (3 files)
```

**주요 파일:**
1. `PIPELINE_CONSOLIDATED_AGI_20251225_134917.xlsx` (28 sheets)
2. `MODIFIED_OPTION4_FINAL_REPORT_20251225.md`
3. `BALLAST_SEQUENCE.xlsx` (21 steps, 36.6h)
4. `BALLAST_OPERATIONS_CHECKLIST.md`
5. `current_t_sensor.csv` (FWB2 28.50t/side)

---

## 7. 운영 권장사항

### 7.1 Forward Inventory 준비

**사전 작업:**
1. FWB1.P/S를 50.57t/side로 충전
2. FWB2.P/S를 28.50t/side로 충전
3. VOID3.P/S는 100.0t/side 유지 (PRE_BALLAST_ONLY)

**검증:**
- 총 Forward Inventory: 158.14t
- DISCHARGE_ONLY 모드 확인

### 7.2 현장 실행

**Stage 5_PreBallast:**
1. 목표: AFT = 2.70m
2. FWD 탱크 discharge 시작
3. Hold point에서 draft 측정
4. 2.70m 확인 → GO

**Stage 6A_Critical:**
1. 목표: AFT = 2.70m, FWD ≤ 2.70m
2. 추가 discharge 계속
3. 양 draft limit 확인
4. 2.70m 달성 → RoRo 작업 시작

### 7.3 비상 대응

**Draft 부족 시 (<2.70m):**
1. Hold point에서 중단
2. `hold_point_recalculator.py` 실행
3. 실측 draft 입력
4. 재계산된 계획 따라 추가 discharge

**Draft 초과 시 (>2.70m):**
1. FWD 탱크 discharge 중단
2. Trim 안정화 대기
3. 목표 범위 확인

---

## 8. 참고 문서

### 8.1 관련 보고서

1. `MODIFIED_OPTION4_FINAL_REPORT_20251225.md` - 최종 검증 보고서
2. `STAGE5_AFT_ACHIEVEMENT_FINAL_REPORT_20251225.md` - Stage 5 분석
3. `FORWARD_INVENTORY_EXECUTION_REPORT_20251225.md` - 실행 보고서
4. `FINAL_DELIVERY_PACKAGE_SUMMARY_20251225.md` - 패키지 요약

### 8.2 운영 가이드

1. `02_BALLAST_OPERATIONS/BALLAST_SEQUENCE.xlsx`
2. `02_BALLAST_OPERATIONS/BALLAST_OPERATIONS_CHECKLIST.md`
3. `02_BALLAST_OPERATIONS/BALLAST_SEQUENCE_WITH_VALVES.md`

---

## 9. 결론

**Modified Option 4 (FWB2 28.50t/side):**
- 🎯 **Stage 5 AFT = 2.70m 정확히 달성**
- 🎯 **Stage 6A AFT = 2.70m 유지**
- 🎯 **재현성 검증 완료**
- 🎯 **현장 배포 준비 완료**

**Forward Inventory 전략 완전 성공!** 🎉

---

*이 문서는 Modified Option 4의 전체 개발, 검증, 배포 과정을 상세히 기록합니다.*

