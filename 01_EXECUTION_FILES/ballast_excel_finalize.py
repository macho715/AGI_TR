"""
Ballast Pipeline - Excel Formula Preservation (COM Post-Processing)

Purpose:
    Preserve formula dependency integrity after openpyxl writes by using Excel COM.
    - CalculateFullRebuild (dependency graph rebuild)
    - RefreshAll (external queries/data)
    - Calc_Log sheet append

Requirements:
    - Windows OS + Excel installed
    - pip install pywin32

Usage:
    python ballast_excel_finalize.py --auto
    python ballast_excel_finalize.py "file.xlsx"
    python ballast_excel_finalize.py --batch "pattern/*.xlsx"
"""

from __future__ import annotations

import glob
import sys
import time
from datetime import datetime
from pathlib import Path


def finalize_excel_com(excel_path: Path, verbose: bool = True) -> bool:
    """
    Excel COM post-processing for formula preservation.

    Process:
        1. Excel COM open
        2. Calculation = Automatic
        3. RefreshAll
        4. CalculateFullRebuild
        5. QueryTables and PivotCaches refresh
        6. Calc_Log write
        7. Save
    """
    try:
        import win32com.client as win32
    except ImportError:
        print("[ERROR] pywin32 not installed")
        print("[FIX] Run: pip install pywin32")
        return False

    if not excel_path.exists():
        print(f"[ERROR] File not found: {excel_path}")
        return False

    start_time = time.time()

    if verbose:
        print("\n" + "=" * 80)
        print(f"[FORMULA FINALIZE] {excel_path.name}")
        print("=" * 80)
        print(f"[INFO] Size: {excel_path.stat().st_size / 1024:.2f} KB")
        print(f"[INFO] Modified: {datetime.fromtimestamp(excel_path.stat().st_mtime)}")

    xl = None
    wb = None

    try:
        if verbose:
            print("[STEP 1/7] Initializing Excel COM...")

        xl = win32.DispatchEx("Excel.Application")
        xl.Visible = False
        xl.DisplayAlerts = False
        xl.ScreenUpdating = False

        if verbose:
            print("[STEP 2/7] Opening workbook...")

        wb = xl.Workbooks.Open(str(excel_path.absolute()))

        if verbose:
            print("[STEP 3/7] Setting Calculation=Automatic...")

        xl.Calculation = -4105  # xlCalculationAutomatic

        if verbose:
            print("[STEP 4/7] RefreshAll()...")

        wb.RefreshAll()

        max_wait = 30
        wait_count = 0
        while xl.CalculationState != 0:  # xlDone
            time.sleep(0.2)
            wait_count += 1
            if wait_count > max_wait * 5:
                if verbose:
                    print("[WARN] RefreshAll timeout (30s)")
                break

        if verbose:
            print("[STEP 5/7] CalculateFullRebuild()...")

        xl.CalculateFullRebuild()

        wait_count = 0
        while xl.CalculationState != 0:
            time.sleep(0.2)
            wait_count += 1
            if wait_count > max_wait * 5:
                if verbose:
                    print("[WARN] FullRebuild timeout (30s)")
                break

        if verbose:
            print("[STEP 6/7] Checking QueryTables & PivotCaches...")

        query_count = 0
        for ws in wb.Worksheets:
            for qt in ws.QueryTables:
                query_count += 1
                wait_count = 0
                while qt.Refreshing:
                    time.sleep(0.2)
                    wait_count += 1
                    if wait_count > max_wait * 5:
                        break

        pivot_count = 0
        try:
            for pc in wb.PivotCaches():
                pc.Refresh()
                pivot_count += 1
        except Exception:
            pass

        if verbose:
            if query_count > 0:
                print(f"[INFO] Processed {query_count} QueryTables")
            if pivot_count > 0:
                print(f"[INFO] Refreshed {pivot_count} PivotCaches")

        if verbose:
            print("[STEP 7/7] Recording build log (Calc_Log sheet)...")

        try:
            log_sheet = None
            for ws in wb.Worksheets:
                if ws.Name == "Calc_Log":
                    log_sheet = ws
                    break

            if log_sheet is None:
                log_sheet = wb.Worksheets.Add()
                log_sheet.Name = "Calc_Log"
                log_sheet.Range("A1").Value = "Parameter"
                log_sheet.Range("B1").Value = "Value"
                log_sheet.Range("C1").Value = "Timestamp"

            last_row = log_sheet.UsedRange.Rows.Count + 1

            logs = [
                ("FullRebuild_Completed", "SUCCESS"),
                ("Engine", "Python+COM"),
                ("ProcessingTime_sec", round(time.time() - start_time, 2)),
                ("QueryTables_Count", query_count),
                ("PivotCaches_Count", pivot_count),
            ]

            for param, value in logs:
                log_sheet.Cells(last_row, 1).Value = param
                log_sheet.Cells(last_row, 2).Value = value
                log_sheet.Cells(last_row, 3).Value = datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
                last_row += 1
        except Exception as exc:
            if verbose:
                print(f"[WARN] Calc_Log update failed: {exc}")

        if verbose:
            print("[SAVING] Writing to disk...")

        wb.Save()

        elapsed = time.time() - start_time

        if verbose:
            print("\n" + "=" * 80)
            print("SUCCESS - Formula finalization completed.")
            print("=" * 80)
            print(f"[RESULT] Processing time: {elapsed:.2f} sec")
            print(f"[RESULT] File: {excel_path.name}")
            print(f"[RESULT] Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print("=" * 80 + "\n")

        return True
    except Exception as exc:
        print(f"\n[ERROR] COM processing failed: {exc}")
        import traceback

        traceback.print_exc()
        return False
    finally:
        if wb:
            wb.Close(SaveChanges=False)
        if xl:
            xl.Quit()


def find_latest_pipeline_output() -> Path:
    """Detect the most recent pipeline output Excel file."""
    base_dir = Path(".")
    pipeline_dirs = sorted(base_dir.glob("pipeline_out_*"), reverse=True)

    if not pipeline_dirs:
        raise FileNotFoundError("No pipeline_out_* directory found")

    latest_dir = pipeline_dirs[0]
    excel_files = list(latest_dir.glob("PIPELINE_CONSOLIDATED_*.xlsx"))

    if not excel_files:
        raise FileNotFoundError(f"No PIPELINE_CONSOLIDATED_*.xlsx in {latest_dir}")

    return excel_files[0]


def main() -> None:
    """CLI entry point."""
    if len(sys.argv) < 2:
        print("Ballast Pipeline - Excel Formula Finalization")
        print()
        print("Usage:")
        print("  python ballast_excel_finalize.py --auto")
        print("  python ballast_excel_finalize.py <excel_file>")
        print("  python ballast_excel_finalize.py --batch <pattern>")
        print()
        print("Examples:")
        print("  python ballast_excel_finalize.py --auto")
        print('  python ballast_excel_finalize.py "output.xlsx"')
        print(
            '  python ballast_excel_finalize.py --batch "pipeline_out_*/PIPELINE_*.xlsx"'
        )
        sys.exit(1)

    arg = sys.argv[1]

    if arg == "--auto":
        try:
            excel_path = find_latest_pipeline_output()
            print(f"[AUTO] Detected: {excel_path}")
            success = finalize_excel_com(excel_path)
            sys.exit(0 if success else 1)
        except FileNotFoundError as exc:
            print(f"[ERROR] {exc}")
            sys.exit(1)
    elif arg == "--batch":
        if len(sys.argv) < 3:
            print("[ERROR] --batch requires pattern argument")
            sys.exit(1)

        pattern = sys.argv[2]
        files = glob.glob(pattern, recursive=True)

        if not files:
            print(f"[ERROR] No files match: {pattern}")
            sys.exit(1)

        print(f"[BATCH] Found {len(files)} files\n")

        success_count = 0
        for file_path in files:
            if finalize_excel_com(Path(file_path)):
                success_count += 1

        print(f"\n[BATCH] {success_count}/{len(files)} files processed successfully")
        sys.exit(0 if success_count == len(files) else 1)
    else:
        excel_path = Path(arg)
        success = finalize_excel_com(excel_path)
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
