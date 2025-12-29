#!/usr/bin/env python3
"""
문서 커버리지 검증 스크립트
I/O 최적화 및 MAMMOET 관련 내용이 모든 주요 문서에 포함되었는지 확인
"""

import os
import re
from pathlib import Path

def check_keywords_in_file(file_path, keywords):
    """파일에서 키워드 검색"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        found = {}
        for keyword in keywords:
            if re.search(keyword, content, re.IGNORECASE):
                found[keyword] = True
            else:
                found[keyword] = False
        return found
    except Exception as e:
        return {k: f"ERROR: {e}" for k in keywords}

def main():
    base_dir = Path(".")

    # 주요 문서 목록
    main_docs = [
        "README.md",
        "00_System_Architecture_Complete.md",
        "01_Architecture_Overview.md",
        "02_Data_Flow_SSOT.md",
        "03_Pipeline_Execution_Flow.md",
        "06_Script_Interfaces.md",
        "10_System_Improvements_and_Patches.md",
    ]

    # 검증 키워드
    io_keywords = [
        r"PR-01",
        r"PR-02",
        r"PR-03",
        r"PR-04",
        r"PR-05",
        r"I/O.*[Oo]ptim",
        r"perf_manifest",
        r"io_detect",
        r"io_csv_fast",
        r"io_parquet_cache",
        r"read_table_any",
        r"Parquet",
        r"Manifest",
    ]

    mammoet_keywords = [
        r"MAMMOET",
        r"create_mammoet",
        r"Calculation Sheet",
    ]

    print("=" * 80)
    print("문서 커버리지 검증 리포트")
    print("=" * 80)
    print()

    # I/O 최적화 검증
    print("1. I/O 최적화 (PR-01~05) 커버리지")
    print("-" * 80)
    io_results = {}
    for doc in main_docs:
        if not (base_dir / doc).exists():
            continue
        results = check_keywords_in_file(base_dir / doc, io_keywords)
        found_count = sum(1 for v in results.values() if v is True)
        io_results[doc] = {
            "found": found_count,
            "total": len(io_keywords),
            "coverage": f"{found_count}/{len(io_keywords)}"
        }
        if found_count > 0:
            print(f"  [PASS] {doc}: {found_count}/{len(io_keywords)} 키워드 발견")
        else:
            print(f"  [FAIL] {doc}: 키워드 없음")
    print()

    # MAMMOET 검증
    print("2. MAMMOET Calculation Sheet Generator 커버리지")
    print("-" * 80)
    mammoet_results = {}
    for doc in main_docs:
        if not (base_dir / doc).exists():
            continue
        results = check_keywords_in_file(base_dir / doc, mammoet_keywords)
        found_count = sum(1 for v in results.values() if v is True)
        mammoet_results[doc] = {
            "found": found_count,
            "total": len(mammoet_keywords),
            "coverage": f"{found_count}/{len(mammoet_keywords)}"
        }
        if found_count > 0:
            print(f"  [PASS] {doc}: {found_count}/{len(mammoet_keywords)} 키워드 발견")
        else:
            print(f"  [WARN] {doc}: 키워드 없음 (선택적)")
    print()

    # 종합 결과
    print("=" * 80)
    print("종합 결과")
    print("=" * 80)

    io_covered = sum(1 for r in io_results.values() if r["found"] > 0)
    mammoet_covered = sum(1 for r in mammoet_results.values() if r["found"] > 0)

    print(f"I/O 최적화: {io_covered}/{len(io_results)} 문서에 포함")
    print(f"MAMMOET: {mammoet_covered}/{len(mammoet_results)} 문서에 포함")
    print()

    if io_covered >= len(io_results) * 0.8:  # 80% 이상
        print("[PASS] I/O 최적화 커버리지: PASS")
    else:
        print("[WARN] I/O 최적화 커버리지: PARTIAL")

    if mammoet_covered >= 2:  # 최소 2개 문서
        print("[PASS] MAMMOET 커버리지: PASS")
    else:
        print("[WARN] MAMMOET 커버리지: PARTIAL")

if __name__ == "__main__":
    main()

