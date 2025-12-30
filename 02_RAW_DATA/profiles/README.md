# Site Profiles

이 디렉토리는 각 사이트의 운영 프로필을 JSON 형식으로 저장합니다.

## 필수 필드

모든 site profile JSON 파일은 다음 필드를 포함해야 합니다:

- `site_name` (string): 사이트 고유 식별자 **[REQUIRED]**
- `location` (string): 지리적 위치
- `site_type` (string): 사이트 유형 (RORO, LCT, 등)
- `operations` (array): 지원 작업 목록

## 선택 필드

- `gates`: FWD/AFT draft 게이트 정의
- `tidal_info`: 조위 정보
- `berth_info`: 선석 정보
- `vessel_info`: 선박 설계 정보
- `cargo_info`: 화물 제한
- `environmental`: 환경 제한
- `metadata`: 메타데이터

## 파일 명명 규칙

`{SITE_NAME}.json` (예: AGI_SITE.json, BUSHRA_SITE.json)

## 검증

GitHub Actions가 자동으로 다음을 검증합니다:
- JSON 형식 유효성
- 필수 필드 존재 여부
- 데이터 일관성

## 예제

```json
{
  "site_name": "EXAMPLE_SITE",
  "location": "Abu Dhabi",
  "site_type": "RORO",
  "operations": ["LOAD", "DISCHARGE"]
}
```

