# Gate FAIL 원인별 자동 리포트

- **Generated:** 2025-12-30 18:34:06
- **Site:** AGI
- **Profile:** C:\AGI TR\01_EXECUTION_FILES\bplus_inputs\profiles\AGI.json
- **Stage QA:** pipeline_stage_QA.csv
- **Tank SSOT:** tank_ssot_for_solver.csv

## 1) Gate 위반 요약

### Exec Summary (Captain vs Mammoet 기준 2.70m 정의)

* **Captain(선장) 기준 2.70m:** **AFT 최소 흘수(AFT draft ≥ 2.70m)** — 비상 시 **프로펠러 효율/추진 확보** 목적.
* **Mammoet(계산/시뮬레이션/플랜) 기준 2.70m:** **FWD 흘수 상한(FWD draft ≤ 2.70m, Chart Datum reference)** — **Critical RoRo 단계에서 Forward draft를 2.70m limit 내**로 유지.
* 따라서 2.70m는 단일 조건이 아니라 **“AFT_MIN(≥2.70)” + “FWD_MAX(≤2.70)” 2개 Gate**로 분리해 표기한다.

ENG-KR 1L: *Captain = AFT minimum 2.70m; Mammoet = FWD limit 2.70m (critical RoRo, chart datum referenced).*

### Visual-first (Gate 정의표 — 문서/계산에 그대로 복붙)

| Owner/Source | Gate Name | Definition | Direction | When applied | Evidence |
|---|---|---|---|---|---|
| **Captain** | **AFT_MIN_DRAFT** | AFT draft shall be **≥ 2.70m** for propeller effectiveness in emergency | Min | Emergency propulsion 필요 운영구간(특히 RoRo 포함) | |
| **Mammoet / Ballast Plan** | **FWD_MAX_DRAFT (CD ref)** | Forward draft (Chart Datum referenced) shall be **≤ 2.70m** during **critical RoRo stages** | Max | Critical RoRo stages (램프/롤온 피크 구간) | |

### (승인/검토용) “Chart Datum”이 붙는 이유 — 정의만

* **Chart Datum**은 해도 수심(Charted depth)과 조위(Height of tide)의 기준면으로, **charted depth + tide height**로 해당 시간의 수심을 산정할 수 있다. ([IHO C-51](https://docs.iho.int/iho_pubs/CB/C_51/C_51_Ed500_062014.pdf))
* BLU Code Ship–Shore Safety Checklist는 **berth available depth** 및 **arrival/departure draft**를 ship–shore가 합의해 기입하도록 요구한다. ([IMO BLU Code checklist](https://www.imorules.com/GUID-87E4BBE7-3CE1-4BDC-92F6-CDFDC8850810.html))

### 운영 적용 룰(혼선 방지 3줄)

1. 문서/리포트에는 반드시 **AFT_MIN 2.70** 과 **FWD_MAX 2.70**를 **각각 별도 Gate로 표기**
2. Stage별로 어떤 Gate가 “강제(applicable)”인지 명시(특히 Mammoet는 “critical RoRo stages”만 적용)
3. “Chart Datum” 관련 계산은 **동일 datum 기반의 charted depth + 공식 tide** 조합으로만 수행(승인 대응)

### Gate 위반 요약 (Counts)

- FWD_Max: **0** stage(s)
- AFT_Min: **2** stage(s)
- Freeboard: **0** stage(s)
- UKC: **0** stage(s) (N/A=0)
- GateA_AFT_MIN_2p70 (Captain): **2** stage(s)
- GateB_FWD_MAX_2p70_CD (Mammoet): **0** stage(s)
- Gate_Hydro_Range: **0** stage(s) (Hydro Table range out-of-domain 감지)
- HS_Any: **0** stage(s) (HardStop=TRUE → 즉시 데이터/정의역 점검 권고)

## 2) SSOT(Current_t) 상태 요약

- Tanks: 31
- Current_t == 0.0: 16/31
- Total Current_t (sum): 373.200 t

### 2.1 Sensor Sync 적용 결과

- Sensor CSV: C:\AGI TR\01_EXECUTION_FILES\sensors\current_t_final_verified.csv
- Strategy: override
- Value mode: Current_t
- Updated (exact): 19
- Updated (group): 0

## 3) UKC 입력 상태

- forecast_tide_m: 2.0
- depth_ref_m: 5.5
- ukc_min_m: 0.5
- squat_m: 0.15
- safety_allow_m: 0.2

## 4) Stage별 Gate 상태

| Stage                     | Gate_FWD_Max   |   FWD_Margin_m | Gate_AFT_Min   |   AFT_Margin_m | Gate_Freeboard   |   Freeboard_Min_m | Gate_UKC   | GateA_AFT_MIN_2p70_PASS   |   GateA_AFT_MIN_2p70_Margin_m | GateB_FWD_MAX_2p70_CD_PASS   |   GateB_FWD_MAX_2p70_CD_Margin_m | GateB_FWD_MAX_2p70_CD_applicable   | Gate_Hydro_Range   | HS_Any   | HardStop_Reason   |
|:--------------------------|:---------------|---------------:|:---------------|---------------:|:-----------------|------------------:|:-----------|:--------------------------|------------------------------:|:-----------------------------|---------------------------------:|:-----------------------------------|:-------------------|:---------|:------------------|
| Stage 6A_Critical (Opt C) | OK             |           3.06 | NG             |          -0.34 | OK               |              1.29 | OK         | False                     |                         -0.34 | True                         |                             3.06 | True                               | OK                 | False    | TrimLimit         |
| Stage 5_PreBallast        | OK             |           2.86 | NG             |          -0.54 | OK               |              1.49 | OK         | False                     |                         -0.54 | True                         |                             2.86 | True                               | OK                 | False    | nan               |
| Stage 1                   | OK             |         nan    | OK             |           0.57 | OK               |              0.38 | OK         | True                      |                          0.57 | True                         |                           nan    | False                              | OK                 | False    | nan               |
| Stage 2                   | OK             |           1.28 | OK             |           0.93 | OK               |              0.02 | OK         | True                      |                          0.93 | True                         |                             1.28 | True                               | OK                 | False    | nan               |
| Stage 3                   | OK             |         nan    | OK             |           0.93 | OK               |              0.02 | OK         | True                      |                          0.93 | True                         |                           nan    | False                              | OK                 | False    | nan               |
| Stage 5                   | OK             |         nan    | OK             |           0.95 | OK               |              0    | OK         | True                      |                          0.95 | True                         |                           nan    | False                              | OK                 | False    | nan               |
| Stage 4                   | OK             |         nan    | OK             |           0.95 | OK               |              0    | OK         | True                      |                          0.95 | True                         |                           nan    | False                              | OK                 | False    | nan               |
| Stage 6C                  | OK             |         nan    | OK             |           0.95 | OK               |              0    | OK         | True                      |                          0.95 | True                         |                           nan    | False                              | OK                 | False    | nan               |
| Stage 7                   | OK             |         nan    | OK             |           0.57 | OK               |              0.38 | OK         | True                      |                          0.57 | True                         |                           nan    | False                              | OK                 | False    | nan               |

## 5) 자동 원인 추정(Heuristics)

- **⚠️ Freeboard_Min_m = 0.00m (Draft Clipping)**: Stage Stage 4, Stage 5, Stage 6C에서 Draft가 D_vessel을 초과하여 클리핑되었습니다. Freeboard = 0.00m은 deck edge가 waterline에 위치함을 의미하며, engineering verification (class acceptance, load-line compliance)이 필요합니다.

## 6) 권고 조치

- **Current_t 실측/센서 값 주입 후 재실행** (Stage QA → Solver → Optimizer 순)
- **Site Profile(AGI/DAS)로 Gate/펌프율/UKC 입력값을 분리 관리** (코드 수정 없이 JSON 수정)
- **Freeboard 음수 발생 시 Stage 하중/수조선 입력 재검증** (Draft > Molded Depth 케이스)

---

## 8) DNV Mitigation Measures (Incomplete Propeller Immersion)

**Reference:** DNV Guidance on incomplete propeller immersion risk

**Risk:** Aft bearing damage and propulsion loss due to excessive eccentric thrust.

### Stages Requiring Mitigation:

#### Stage 5_PreBallast
- AFT Draft: 2.16 m (Required: 2.7 m)
- Deficit: 0.54 m

Required Mitigation Measures (DNV):
1. RPM/Power reduction (specify % based on engine guidance)
2. Steering angle limitation (specify degrees)
3. Tug standby (immediately available; operational control with tug)
4. Abort criteria:
   - AFT draft falls below 2.50 m
   - Propeller shaft bearing temperature exceeds normal range
   - Loss of propulsion effectiveness detected
   - Weather exceeds operational limits
5. Monitoring: 4-corner draft + bearing temperature

#### Stage 6A_Critical (Opt C)
- AFT Draft: 2.36 m (Required: 2.7 m)
- Deficit: 0.34 m

Required Mitigation Measures (DNV):
1. RPM/Power reduction (specify % based on engine guidance)
2. Steering angle limitation (specify degrees)
3. Tug standby (immediately available; operational control with tug)
4. Abort criteria:
   - AFT draft falls below 2.50 m
   - Propeller shaft bearing temperature exceeds normal range
   - Loss of propulsion effectiveness detected
   - Weather exceeds operational limits
5. Monitoring: 4-corner draft + bearing temperature

### ITTC Shaft Centreline Immersion Note
**Important:** Record shaft centreline immersion (not AFT draft) in approval docs.
- Propeller Diameter (D): 1.38 m
- Minimum: 1.5D = 2.07 m
- Recommended: 2.0D = 2.76 m
- Calculation: immersion_shaftCL = draft_at_prop - z_shaftCL
- Do not confuse AFT draft with shaft immersion in approval documentation.
---

## 7) Step 3 (Gate Solver) 결과 요약

- solver_ballast_summary.csv: solver_ballast_summary.csv (OK)
- solver_ballast_plan.csv: solver_ballast_plan.csv (OK)
- solver_ballast_stage_plan.csv: solver_ballast_stage_plan.csv (OK)

### Solver Summary (first row)

- New_FWD_m: 3.27
- New_AFT_m: 3.27
- Freeboard_MIN_m: 0.38
- UKC_m: 3.88
- viol_fwd_max_m: 0.0
- viol_aft_min_m: 0.0
- viol_fb_min_m: 0.0
- viol_ukc_min_m: 0.0