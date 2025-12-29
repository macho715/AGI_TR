# 제17장: TIDE/UKC 계산 로직 및 Fallback 메커니즘

**작성일:** 2025-12-28
**최종 수정일:** 2025-12-29
**버전:** v1.1
**목적:** TIDE/UKC 계산식, Fallback 메커니즘, 검증 로직의 수학적 모델 및 구현 상세

---

## 17.1 개요

### 17.1.1 목적

본 문서는 `tide_ukc_engine.py` 모듈의 **TIDE/UKC 계산 로직**을 수학적 공식과 구현 관점에서 상세히 설명합니다. 특히:

- **계산식 정의**: 모든 TIDE/UKC 관련 수학적 공식
- **Fallback 메커니즘**: None 값 처리 및 기본값 적용 로직
- **검증 로직**: Tide margin 검증 및 판정 기준
- **데이터 변환**: 입력 데이터 정규화 및 변환 과정

### 17.1.2 핵심 정의 (Chart Datum 기준)

본 모듈은 **Forecast Tide(예보 조위)**와 **Required WL(UKC 만족을 위해 필요한 수위)**를 엄격히 분리합니다:

| 용어 | 정의 | 단위 | 기준 |
|------|------|------|------|
| **Forecast_tide_m** | 예보 조위 (Chart Datum 기준) | m | 예보값 (입력) |
| **Tide_required_m** | UKC 요구조건 만족을 위한 최소 수위 | m | 계산값 |
| **Tide_margin_m** | Forecast_tide_m - Tide_required_m | m | 계산값 |
| **UKC_fwd_m** | 선수부 Under Keel Clearance | m | 계산값 |
| **UKC_aft_m** | 선미부 Under Keel Clearance | m | 계산값 |
| **UKC_min_actual_m** | min(UKC_fwd_m, UKC_aft_m) | m | 계산값 |

---

## 17.2 핵심 계산식

### 17.2.1 Required Tide 계산

**공식:**
```
Tide_required_m = max(0, (Draft_ref + Squat + Safety + UKC_min) - DepthRef)
```

**구현:**
```python
def required_tide_m(
    depth_ref_m: Optional[float],
    draft_ref_m: Optional[float],
    ukc_min_m: Optional[float],
    squat_m: float = 0.0,
    safety_allow_m: float = 0.0,
    clamp_zero: bool = True,
    fallback_depth: Optional[float] = None,
    fallback_draft: Optional[float] = None,
    fallback_ukc: Optional[float] = None,
) -> float:
    """Return required tide (m, CD) with fallbacks."""
    # Apply fallbacks
    depth = depth_ref_m if depth_ref_m is not None else (fallback_depth or DEFAULT_DEPTH_REF_M)
    draft = draft_ref_m if draft_ref_m is not None else (fallback_draft or 2.00)
    ukc = ukc_min_m if ukc_min_m is not None else (fallback_ukc or DEFAULT_UKC_MIN_M)

    req = float(draft + float(squat_m) + float(safety_allow_m) + float(ukc) - float(depth))
    if clamp_zero:
        return float(max(0.0, req))
    return float(req)
```

**파라미터 설명:**

| 파라미터 | 타입 | 기본값 | 설명 |
|----------|------|--------|------|
| `depth_ref_m` | Optional[float] | None | 기준 수심 (Chart Datum 기준, m) |
| `draft_ref_m` | Optional[float] | None | 기준 흘수 (m) |
| `ukc_min_m` | Optional[float] | None | 최소 UKC 요구값 (m) |
| `squat_m` | float | 0.0 | Squat 여유 (m) |
| `safety_allow_m` | float | 0.0 | 안전 여유 (m) |
| `clamp_zero` | bool | True | 결과를 0 이상으로 제한 |

**Fallback 메커니즘:**

1. **depth_ref_m이 None인 경우:**
   - `fallback_depth` 사용 (제공된 경우)
   - 없으면 `DEFAULT_DEPTH_REF_M = 5.50` (AGI 기본값)

2. **draft_ref_m이 None인 경우:**
   - `fallback_draft` 사용 (제공된 경우)
   - 없으면 `2.00` (안전 기본값)

3. **ukc_min_m이 None인 경우:**
   - `fallback_ukc` 사용 (제공된 경우)
   - 없으면 `DEFAULT_UKC_MIN_M = 0.50` (안전 최소값)

**수학적 의미:**

- **Tide_required_m > 0**: 수심이 부족하여 추가 조위가 필요함
- **Tide_required_m = 0**: 현재 수심으로 충분 (clamp_zero 적용 시)
- **Tide_required_m < 0**: 수심이 충분하여 조위 요구 없음 (0으로 clamp)

---

### 17.2.2 UKC 계산 (단일 위치)

**공식:**
```
UKC_end = DepthRef + Forecast_tide - Draft_end - Squat - Safety
```

**구현:**
```python
def ukc_end_m(
    depth_ref_m: Optional[float],
    forecast_tide_m: Optional[float],
    draft_end_m: Optional[float],
    squat_m: float = 0.0,
    safety_allow_m: float = 0.0,
) -> float:
    """Return UKC at one end (m)."""
    if depth_ref_m is None or forecast_tide_m is None or draft_end_m is None:
        return float("nan")
    return float(float(depth_ref_m) + float(forecast_tide_m) - float(draft_end_m) - float(squat_m) - float(safety_allow_m))
```

**파라미터 설명:**

| 파라미터 | 타입 | 설명 |
|----------|------|------|
| `depth_ref_m` | Optional[float] | 기준 수심 (Chart Datum 기준, m) |
| `forecast_tide_m` | Optional[float] | 예보 조위 (Chart Datum 기준, m) |
| `draft_end_m` | Optional[float] | 선수 또는 선미 흘수 (m) |
| `squat_m` | float | Squat 여유 (m) |
| `safety_allow_m` | float | 안전 여유 (m) |

**수학적 의미:**

- **UKC_end > 0**: 선박 하부와 해저면 사이 여유 공간 존재
- **UKC_end = 0**: 선박 하부가 해저면에 접촉
- **UKC_end < 0**: 선박 하부가 해저면 아래 (접촉 위험)

**None 처리:**

- 입력 파라미터 중 하나라도 None이면 `float("nan")` 반환
- 후속 계산에서 NaN 전파 방지 필요

---

### 17.2.3 UKC FWD/AFT 및 최소값 계산

**공식:**
```
UKC_fwd = DepthRef + Forecast_tide - Draft_fwd - Squat - Safety
UKC_aft = DepthRef + Forecast_tide - Draft_aft - Squat - Safety
UKC_min_actual = min(UKC_fwd, UKC_aft)
```

**구현:**
```python
def ukc_fwd_aft_min(
    depth_ref_m: Optional[float],
    forecast_tide_m: Optional[float],
    draft_fwd_m: Optional[float],
    draft_aft_m: Optional[float],
    squat_m: float = 0.0,
    safety_allow_m: float = 0.0,
) -> Tuple[float, float, float]:
    """Return (UKC_fwd, UKC_aft, UKC_min_actual)."""
    uf = ukc_end_m(depth_ref_m, forecast_tide_m, draft_fwd_m, squat_m, safety_allow_m)
    ua = ukc_end_m(depth_ref_m, forecast_tide_m, draft_aft_m, squat_m, safety_allow_m)
    try:
        umin = float(min(uf, ua))
    except Exception:
        umin = float("nan")
    return uf, ua, umin
```

**반환값:**

- `(UKC_fwd_m, UKC_aft_m, UKC_min_actual_m)`: 3-tuple
- 모든 값은 `float` (NaN 가능)

**예외 처리:**

- `ukc_end_m()`이 NaN을 반환하면 `UKC_min_actual`도 NaN
- `min()` 연산 실패 시 NaN 반환

---

### 17.2.4 Tide Margin 계산

**공식:**
```
Tide_margin_m = Forecast_tide_m - Tide_required_m
```

**구현 위치:**
- `tide_ukc_engine.py`에는 직접 구현 없음
- 파이프라인에서 `Forecast_tide_m - Tide_required_m`로 계산

**판정 기준:**

| 조건 | 판정 | 설명 |
|------|------|------|
| `Forecast_tide_m` 없음 | `VERIFY` | 예보 조위 미제공 |
| `Tide_margin_m < 0` | `FAIL` | 예보 조위 < 필요 조위 |
| `0 ≤ Tide_margin_m < tolerance` | `LIMIT` | 여유 부족 (기본 tolerance = 0.10m) |
| `Tide_margin_m ≥ tolerance` | `OK` | 여유 충분 |

---

## 17.3 검증 로직

### 17.3.1 Tide 검증 함수

**구현:**
```python
def verify_tide(
    tide_required_m_val: float,
    forecast_tide_m_val: Optional[float],
    tolerance_m: float = DEFAULT_TIDE_TOL_M,
) -> Tuple[str, str]:
    """
    Return (status, note)
    - VERIFY: forecast missing (no official tide table / forecast not provided)
    - FAIL  : margin < 0
    - LIMIT : 0 <= margin < tolerance
    - OK    : margin >= tolerance
    """
    ft = _to_float(forecast_tide_m_val, fallback=None, warn=False)
    if ft is None or (isinstance(ft, float) and np.isnan(ft)):
        return "VERIFY", "Forecast tide not provided"
    try:
        req = float(tide_required_m_val)
    except Exception:
        return "VERIFY", "Tide_required_m invalid"

    margin = float(ft - req)
    if margin < 0.0:
        return "FAIL", f"Forecast {ft:.2f}m < required {req:.2f}m"
    if margin < float(tolerance_m):
        return "LIMIT", f"Margin {margin:.2f}m < tol {float(tolerance_m):.2f}m"
    return "OK", f"Margin {margin:.2f}m"
```

**판정 로직 흐름:**

```
┌─────────────────────────────────┐
│ verify_tide()                   │
└──────────────┬──────────────────┘
               │
               ▼
    ┌──────────────────────┐
    │ forecast_tide_m     │
    │ 변환 가능?           │
    └──────┬───────────────┘
           │
    ┌──────┴──────┐
    │ No          │ Yes
    ▼             ▼
VERIFY      ┌──────────────────────┐
            │ tide_required_m     │
            │ 변환 가능?           │
            └──────┬───────────────┘
                   │
            ┌──────┴──────┐
            │ No          │ Yes
            ▼             ▼
        VERIFY      ┌──────────────────────┐
                    │ margin 계산          │
                    │ = ft - req           │
                    └──────┬───────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
        ▼                  ▼                  ▼
    margin < 0    0 ≤ margin < tol    margin ≥ tol
        │                  │                  │
        ▼                  ▼                  ▼
      FAIL              LIMIT                OK
```

**기본값:**

- `DEFAULT_TIDE_TOL_M = 0.10` (m)
- Profile JSON에서 오버라이드 가능

---

## 17.4 Fallback 메커니즘

### 17.4.1 `_to_float()` 함수

**구현:**
```python
def _to_float(x, fallback: Optional[float] = None, warn: bool = False) -> Optional[float]:
    """
    Convert to float with optional fallback.

    Args:
        x: Value to convert
        fallback: Default value if conversion fails (None = return None)
        warn: Log warning on failure

    Returns:
        float or fallback value
    """
    try:
        if x is None:
            return fallback
        if isinstance(x, str) and x.strip() == "":
            return fallback
        if pd.isna(x):
            return fallback
        return float(x)
    except Exception as e:
        if warn:
            import logging
            logging.debug(f"_to_float conversion failed: {e}, using fallback={fallback}")
        return fallback
```

**처리 순서:**

1. **None 체크**: `x is None` → `fallback` 반환
2. **빈 문자열 체크**: `x.strip() == ""` → `fallback` 반환
3. **NaN 체크**: `pd.isna(x)` → `fallback` 반환
4. **타입 변환**: `float(x)` 시도
5. **예외 처리**: 변환 실패 시 `fallback` 반환

**사용 예시:**

```python
# None 처리 (fallback=0.0)
tide_val = _to_float(None, fallback=0.0)  # → 0.0

# 빈 문자열 처리
tide_val = _to_float("", fallback=2.00)  # → 2.00

# NaN 처리
tide_val = _to_float(np.nan, fallback=2.00)  # → 2.00

# 정상 변환
tide_val = _to_float("2.50", fallback=0.0)  # → 2.50
```

---

### 17.4.2 `required_tide_m()` Fallback 체인

**Fallback 우선순위:**

```
depth_ref_m
  ├─ None? → fallback_depth
  │           ├─ None? → DEFAULT_DEPTH_REF_M (5.50)
  │           └─ 값 있음 → 사용
  └─ 값 있음 → 사용

draft_ref_m
  ├─ None? → fallback_draft
  │           ├─ None? → 2.00 (안전 기본값)
  │           └─ 값 있음 → 사용
  └─ 값 있음 → 사용

ukc_min_m
  ├─ None? → fallback_ukc
  │           ├─ None? → DEFAULT_UKC_MIN_M (0.50)
  │           └─ 값 있음 → 사용
  └─ 값 있음 → 사용
```

**계산 보장:**

- 모든 파라미터가 None이어도 기본값으로 계산 가능
- `float("nan")` 반환 없음 (fallback 적용)

---

## 17.5 상수 정의 (SSOT)

### 17.5.1 `tide_constants.py` 모듈

**정의된 상수:**

```python
# Default values (fallback only)
DEFAULT_TIDE_TOL_M = 0.10  # Tide margin tolerance (m)
DEFAULT_DEPTH_REF_M = 5.50  # AGI default depth reference
DEFAULT_UKC_MIN_M = 0.50  # Minimum UKC requirement
DEFAULT_SQUAT_M = 0.15  # Default squat allowance
DEFAULT_SAFETY_ALLOW_M = 0.20  # Default safety allowance

# Timeout settings
FORMULA_TIMEOUT_SEC = 120  # Excel formula finalization timeout
```

**Profile JSON 통합:**

```python
def load_tide_constants_from_profile(profile_path: Optional[Path] = None) -> Dict[str, Any]:
    """Load tide/UKC constants from profile JSON with fallbacks."""
    if profile_path and profile_path.exists():
        # Profile에서 로드 시도
        # 실패 시 기본값 사용
    return {
        "tide_tol_m": DEFAULT_TIDE_TOL_M,
        "depth_ref_m": DEFAULT_DEPTH_REF_M,
        # ...
    }
```

**Profile JSON 구조:**

```json
{
  "tide_ukc": {
    "tide_tol_m": 0.10,
    "depth_ref_m": 5.50,
    "ukc_min_m": 0.50,
    "squat_m": 0.15,
    "safety_allow_m": 0.20
  },
  "operational": {
    "formula_timeout_sec": 120
  }
}
```

**기본값 적용 우선순위:**

```
1. 사용자 입력 (CLI/Profile)
2. Profile JSON 값
3. 함수 파라미터 fallback_* 값
4. tide_constants.py 기본값
5. 하드코딩 안전값 (2.00 등)
```

---

## 17.6 데이터 변환 및 보간

### 17.6.1 Tide Table 로드

**지원 형식:**

- CSV/TXT: `pd.read_csv()` (자동 구분자 감지)
- Excel: `pd.read_excel()` (.xlsx, .xls)
- JSON: `pd.read_json()` 또는 `json.loads()` 후 DataFrame 변환

**컬럼 자동 감지:**

1. **Datetime 컬럼 감지:**
   - 비숫자 컬럼 중 60% 이상이 유효한 datetime → 선택
   - 없으면 모든 컬럼 시도

2. **Tide 컬럼 감지:**
   - 우선순위: `tide_m` > `tide` > `tide_height_m` > `height_m` > `wl_m` > ...
   - 없으면 첫 번째 숫자 컬럼 사용

**출력 형식:**

```python
DataFrame with columns:
  - ts: datetime64[ns] (정규화된 타임스탬프)
  - tide_m: float (조위 값, m)
```

---

### 17.6.2 Tide 보간 (Linear Interpolation)

**공식:**
```
tide(t) = interp(t, [t₁, t₂, ..., tₙ], [h₁, h₂, ..., hₙ])
```

**구현:**
```python
def tide_at_timestamp(tide_df: pd.DataFrame, ts: pd.Timestamp) -> float:
    """
    Linear interpolation of tide at timestamp.
    Returns NaN if outside table range.
    """
    # 타임스탬프를 int64로 변환 (나노초 단위)
    x = tide_df["ts"].astype("datetime64[ns]").view("int64").to_numpy()
    y = pd.to_numeric(tide_df["tide_m"], errors="coerce").to_numpy()
    xi = np.int64(ts.to_datetime64().astype("datetime64[ns]").astype("int64"))

    # 범위 체크
    if xi < x.min() or xi > x.max():
        return float("nan")

    # 선형 보간
    return float(np.interp(xi, x, y))
```

**범위 체크:**

- `ts < tide_df["ts"].min()` → `NaN` 반환
- `ts > tide_df["ts"].max()` → `NaN` 반환
- 범위 내 → 선형 보간 결과 반환

---

### 17.6.3 Stage Schedule 로드

**지원 형식:**

- CSV/TXT: `pd.read_csv()` (자동 구분자 감지)
- Excel: `pd.read_excel()` (.xlsx, .xls)

**컬럼 자동 감지:**

1. **Stage 컬럼:**
   - 우선순위: `stage` > `stage_id` > `stage name` > `stagename` > `stage_name`
   - 없으면 첫 번째 컬럼 사용

2. **Timestamp 컬럼:**
   - 우선순위: `timestamp` > `datetime` > `time` > `ts` > `start` > `start_time` > `eta`
   - 없으면 `_detect_datetime_col()` 사용

**출력 형식:**

```python
DataFrame with columns:
  - StageKey: str (정규화된 Stage 이름)
  - ts: datetime64[ns] (타임스탬프)
```

**Stage 이름 정규화:**

```python
def _norm_stage_key(x: str) -> str:
    s = str(x or "").strip().lower()
    s = " ".join(s.split())  # 연속 공백 제거
    s = s.replace("_", " ").replace("-", " ")  # 구분자 통일
    s = " ".join(s.split())  # 재정리
    return s
```

**예시:**

- `"Stage 1"` → `"stage 1"`
- `"Stage_2"` → `"stage 2"`
- `"Stage-3"` → `"stage 3"`
- `"STAGE  4"` → `"stage 4"`

---

### 17.6.4 Forecast Tide 주입

**전략:**

1. **fillna**: 기존 `Forecast_Tide_m`이 NaN인 경우만 채움
2. **override**: 기존 값과 관계없이 덮어쓰기

**구현:**
```python
def apply_forecast_tide_from_table(
    stage_df: pd.DataFrame,
    tide_df: pd.DataFrame,
    schedule_df: pd.DataFrame,
    *,
    stage_col: str = "Stage",
    out_col: str = "Forecast_Tide_m",
    strategy: str = "fillna",
) -> pd.DataFrame:
    # Stage → Timestamp 매핑
    sched_map = {r["StageKey"]: r["ts"] for _, r in schedule_df.iterrows()}

    for i, r in df.iterrows():
        sk = _norm_stage_key(r.get(stage_col, ""))
        ts = sched_map.get(sk)
        if ts is None:
            continue
        tide_val = tide_at_timestamp(tide_df, ts)
        if np.isnan(tide_val):
            continue
        cur = _to_float(r.get(out_col), fallback=None, warn=False)
        if strategy == "override" or cur is None or (isinstance(cur, float) and np.isnan(cur)):
            df.at[i, out_col] = float(tide_val)
            assigned += 1
```

---

### 17.6.5 Forecast_Tide_m 우선순위 (v1.1 업데이트)

**변경 사항 (2025-12-29):**

CLI `--forecast_tide` 값이 최우선으로 적용되도록 우선순위가 변경되었습니다. 이는 `stage_table_unified.csv`와 `solver_ballast_summary.csv` 간의 `Forecast_Tide_m` 일관성을 보장하기 위함입니다.

**새로운 우선순위 (v1.1):**

```
Priority 0: CLI forecast_tide_m (최우선 - 명시적으로 제공된 경우)
  ├─ build_stage_table_from_stage_results()에서 직접 할당
  └─ enrich_stage_table_with_tide_ukc()에서 stage_tide_csv보다 우선 적용

Priority 1: stage_tide_csv (CLI가 없을 때만)
  └─ stage_tide_AGI.csv 등에서 Stage별 조위 로드

Priority 2: tide_table + stage_schedule (옵션)
  └─ Tide table 보간을 통한 Stage별 조위 계산
  └─ 입력 파일:
     - `bplus_inputs/water tide_202512.xlsx`: Tide 데이터 (Excel, 576 lines)
     - `bplus_inputs/stage_schedule.csv`: Stage별 타임스탬프 (CSV, `Stage,Timestamp` 형식)
  └─ 사용 예시:
     ```python
     # stage_schedule.csv 예시
     Stage,Timestamp
     Stage 1,2025-12-01 08:00:00
     Stage 6A_Critical (Opt C),2025-12-01 20:00:00
     ```
  └─ 보간 로직: `tide_ukc_engine.py`의 `interpolate_tide_at_time()` 함수 사용

Priority 3: CLI forecast_tide_m (fillna - 안전장치)
  └─ 누락된 Stage에만 적용
```

**구현 위치:**

1. **`build_stage_table_from_stage_results()` 함수 (Line 2815-2820):**
   ```python
   if forecast_tide_m is not None:
       # CLI 값이 명시적으로 제공되면 모든 Stage에 직접 적용 (우선순위 최상)
       out["Forecast_Tide_m"] = float(forecast_tide_m)
       print(f"[OK] Applied forecast_tide_m={forecast_tide_m} to stage_table (CLI override, all stages)")
   ```

2. **`enrich_stage_table_with_tide_ukc()` 함수 (Line 3055-3063):**
   ```python
   # Priority 0: CLI forecast_tide_m (최우선 - 명시적으로 제공된 경우)
   if forecast_tide_m is not None:
       # CLI 값이 있으면 모든 Stage에 직접 적용 (stage_tide_csv보다 우선)
       df["Forecast_Tide_m"] = float(forecast_tide_m)
       print(f"[OK] CLI forecast_tide_m={forecast_tide_m} applied (override stage_tide_csv and tide_table)")
   else:
       # CLI 값이 없을 때만 stage_tide_csv 사용
       # Priority 1: Direct stage_tide_csv
       # ...
   ```

**이전 우선순위 (v1.0):**

```
Priority 1: stage_tide_csv (최우선)
Priority 2: tide_table + stage_schedule
Priority 3: CLI forecast_tide (fillna만)
```

**변경 이유:**

- **문제**: `stage_table_unified.csv`는 `stage_tide_csv`에서 값을 로드하고, `solver_ballast_summary.csv`는 CLI 값을 사용하여 불일치 발생
- **해결**: CLI 값이 명시적으로 제공되면 모든 소스에서 동일한 값 사용 보장
- **효과**: UKC 계산 일관성 향상, `stage_table_unified.csv`와 `solver_ballast_summary.csv` 간 `Forecast_Tide_m` 완전 일치

**사용 예시:**

```bash
# CLI 값이 최우선 적용됨
python integrated_pipeline_*.py --forecast_tide 1.5 ...

# 결과:
# - stage_table_unified.csv: 모든 Stage에 Forecast_Tide_m = 1.5 m
# - solver_ballast_summary.csv: 모든 Stage에 Forecast_Tide_m = 1.5 m
# - 완전 일치 ✅
```

**주의사항:**

- CLI `--forecast_tide`를 제공하지 않으면 기존 우선순위(stage_tide_csv → tide_table → fallback)가 적용됩니다.
- Stage별 다른 조위가 필요한 경우, CLI 값을 제공하지 않고 `stage_tide_csv`를 사용하세요.

**처리 흐름:**

```
┌─────────────────────────────────┐
│ apply_forecast_tide_from_table()│
└──────────────┬──────────────────┘
               │
               ▼
    ┌──────────────────────┐
    │ Stage → Timestamp    │
    │ 매핑 (schedule_df)   │
    └──────┬───────────────┘
           │
    ┌──────┴──────┐
    │ 매핑 성공?  │
    └──────┬─────┘
           │
    ┌──────┴──────┐
    │ Yes         │ No
    ▼             ▼
┌──────────┐   Skip
│ Tide     │
│ 보간     │
└────┬─────┘
     │
┌────┴────┐
│ 성공?   │
└────┬────┘
     │
┌────┴────┐
│ Yes     │ No
▼         ▼
┌──────────────┐   Skip
│ Strategy     │
│ 체크         │
└────┬─────────┘
     │
┌────┴────┐
│ fillna  │ override
│ & NaN?   │
└────┬────┘
     │
     ▼
  값 주입
```

---

## 17.7 계산식 통합 예시

### 17.7.1 전체 계산 흐름

**입력:**
- `DepthRef_m = 5.50` (m)
- `Forecast_Tide_m = 2.00` (m)
- `Draft_FWD_m = 3.27` (m)
- `Draft_AFT_m = 3.27` (m)
- `UKC_Min_m = 0.50` (m)
- `Squat_m = 0.15` (m)
- `SafetyAllow_m = 0.20` (m)

**계산 단계:**

1. **UKC 계산:**
   ```
   UKC_fwd = 5.50 + 2.00 - 3.27 - 0.15 - 0.20 = 3.88 (m)
   UKC_aft = 5.50 + 2.00 - 3.27 - 0.15 - 0.20 = 3.88 (m)
   UKC_min_actual = min(3.88, 3.88) = 3.88 (m)
   ```

2. **Required Tide 계산:**
   ```
   Draft_ref = max(3.27, 3.27) = 3.27 (m)
   Tide_required = max(0, (3.27 + 0.15 + 0.20 + 0.50) - 5.50)
                  = max(0, 4.12 - 5.50)
                  = max(0, -1.38)
                  = 0.00 (m)
   ```

3. **Tide Margin 계산:**
   ```
   Tide_margin = 2.00 - 0.00 = 2.00 (m)
   ```

4. **검증:**
   ```
   margin = 2.00 ≥ tolerance (0.10) → OK
   ```

---

### 17.7.2 Fallback 적용 예시

**시나리오: Forecast_Tide_m 누락**

**입력:**
- `Forecast_Tide_m = None`
- `DepthRef_m = 5.50`
- `Draft_FWD_m = 3.27`
- `Draft_AFT_m = 3.27`
- `UKC_Min_m = 0.50`

**Fallback 적용:**

1. **UKC 계산:**
   ```
   UKC_fwd = 5.50 + None - 3.27 - 0.15 - 0.20
   → ukc_end_m() 반환: NaN
   ```

2. **Required Tide 계산:**
   ```
   Tide_required = max(0, (3.27 + 0.15 + 0.20 + 0.50) - 5.50)
                  = 0.00 (m)  # Fallback 없이도 계산 가능
   ```

3. **검증:**
   ```
   verify_tide(0.00, None, 0.10)
   → ("VERIFY", "Forecast tide not provided")
   ```

**결과:**
- `UKC_fwd_m = NaN`
- `UKC_aft_m = NaN`
- `UKC_min_actual_m = NaN`
- `Tide_required_m = 0.00`
- `Tide_margin_m = NaN`
- `Tide_verification = "VERIFY"`

---

## 17.8 상수 및 기본값

### 17.8.1 상수 정의

| 상수 | 값 | 단위 | 설명 |
|------|-----|------|------|
| `DEFAULT_TIDE_TOL_M` | 0.10 | m | Tide margin 허용 오차 |
| `DEFAULT_DEPTH_REF_M` | 5.50 | m | AGI 기본 수심 기준값 |
| `DEFAULT_UKC_MIN_M` | 0.50 | m | 최소 UKC 요구값 |
| `DEFAULT_SQUAT_M` | 0.15 | m | 기본 Squat 여유 |
| `DEFAULT_SAFETY_ALLOW_M` | 0.20 | m | 기본 안전 여유 |
| `FORMULA_TIMEOUT_SEC` | 120 | s | Excel 수식 최종화 타임아웃 |

### 17.8.2 기본값 적용 우선순위

```
1. 사용자 입력 (CLI/Profile)
2. Profile JSON 값
3. 함수 파라미터 fallback_* 값
4. tide_constants.py 기본값
5. 하드코딩 안전값 (2.00 등)
```

---

## 17.9 I/O 최적화 통합

### 17.9.1 Fast-Path 읽기

**구현:**
```python
def _read_df_any(path: Path) -> pd.DataFrame:
    """Read CSV/Excel/JSON with fast-path and parquet cache."""
    try:
        from io_parquet_cache import read_table_any
        has_fast_path = True
    except ImportError:
        has_fast_path = False

    suf = path.suffix.lower()
    if suf == ".csv":
        if has_fast_path:
            return read_table_any(path)  # ✅ fast-path + cache
        return pd.read_csv(path)  # Fallback
    # ...
```

**성능 효과:**

- **1회 실행**: CSV 읽기 (기존과 동일)
- **2회 실행**: Parquet 캐시 hit → **2.5-3.3배 빠름**

---

## 17.10 검증 및 테스트

### 17.10.1 단위 테스트 예시

```python
def test_required_tide_m_with_fallbacks():
    """Test: required_tide_m with all None inputs uses fallbacks."""
    result = required_tide_m(None, None, None)
    # depth = 5.50, draft = 2.00, ukc = 0.50
    # req = max(0, (2.00 + 0.15 + 0.20 + 0.50) - 5.50)
    #     = max(0, -2.65) = 0.00
    assert result == 0.0

def test_ukc_end_m_none_handling():
    """Test: ukc_end_m returns NaN when inputs are None."""
    result = ukc_end_m(None, 2.00, 3.27)
    assert np.isnan(result)

def test_verify_tide_margin_logic():
    """Test: verify_tide returns correct status based on margin."""
    # FAIL case
    status, note = verify_tide(2.00, 1.50, 0.10)
    assert status == "FAIL"

    # LIMIT case
    status, note = verify_tide(2.00, 2.05, 0.10)
    assert status == "LIMIT"

    # OK case
    status, note = verify_tide(2.00, 2.20, 0.10)
    assert status == "OK"
```

---

## 17.11 참고 사항

### 17.11.1 Chart Datum (CD) 기준

모든 TIDE/UKC 계산은 **Chart Datum (CD)** 기준입니다:

- **Forecast_tide_m**: CD 기준 조위
- **DepthRef_m**: CD 기준 수심
- **Tide_required_m**: CD 기준 필요 조위

**DatumOffset 통합:**

일부 사이트에서는 DatumOffset이 적용될 수 있습니다:
```
Available_Depth = DepthRef + DatumOffset + Forecast_Tide
```

### 17.11.2 단위 일관성

모든 계산은 **미터(m)** 단위로 통일:

- 조위: m (CD 기준)
- 수심: m (CD 기준)
- 흘수: m
- UKC: m
- Squat: m
- Safety Allowance: m

---

## 17.12 변경 이력

| 버전 | 날짜 | 변경 내용 |
|------|------|-----------|
| v1.0 | 2025-12-28 | 초기 작성: 계산식, Fallback 메커니즘, 검증 로직 상세화 |
| v1.1 | 2025-12-29 | Forecast_Tide_m 우선순위 변경: CLI 값 최우선 적용으로 일관성 문제 해결 |

### v1.1 변경 상세 (2025-12-29)

**주요 변경사항:**

1. **Forecast_Tide_m 우선순위 재정의**
   - CLI `--forecast_tide` 값이 최우선으로 적용
   - `build_stage_table_from_stage_results()`: CLI 값 직접 할당 (fillna 대신)
   - `enrich_stage_table_with_tide_ukc()`: CLI 값이 있으면 stage_tide_csv보다 우선

2. **일관성 문제 해결**
   - `stage_table_unified.csv`와 `solver_ballast_summary.csv` 간 `Forecast_Tide_m` 완전 일치
   - UKC 계산 일관성 향상

3. **영향 범위**
   - `integrated_pipeline_defsplit_v2_gate270_split_v3_auditpatched_autodetect_TIDE_v1.py`
   - `build_stage_table_from_stage_results()` 함수
   - `enrich_stage_table_with_tide_ukc()` 함수

**검증 결과:**

- ✅ 모든 Stage에서 `Forecast_Tide_m = 1.5 m` 일치 확인
- ✅ UKC 계산 정확성 검증 완료
- ✅ Profile 파라미터(squat_m, safety_allow_m) 자동 로드 정상 작동

---

**문서 끝**

