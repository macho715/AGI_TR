# ZERO STOP LOG

| 단계 | 이유 | 위험 | 요청데이터 | 다음조치 |
|---|---|---|---|---|
| 중단(B+ Preflight) | B+ 필수 입력 데이터 누락 또는 Engineering-grade hydro columns 미충족 | MWS/HM 제출 근거 부족 → 잘못된 승인 판단/UKC·Ramp 오판 가능 | - GZ_Curve_<Stage>.json (at least one) under ./bplus_inputs/data/ | 1) prep_bplus_inputs.py 실행 → ./bplus_inputs 생성  2) Approved Booklet/NAPA export 값 채움  3) 재실행 |


## Search Roots
- C:\AGI RORO TR\AGI TR\02_RAW_DATA\bplus_inputs
- C:\AGI RORO TR\AGI TR\02_RAW_DATA\additional_inputs
- C:\AGI RORO TR\AGI TR\01_EXECUTION_FILES\bplus_inputs
- C:\AGI RORO TR\AGI TR\01_EXECUTION_FILES\bplus_inputs\data
- C:\AGI RORO TR\AGI TR\01_EXECUTION_FILES
- C:\AGI RORO TR\AGI TR
- C:\mnt\data
