from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd


def _require_cols(df: pd.DataFrame, cols: List[str], name: str) -> None:
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise ValueError(f"{name} missing required columns: {missing}")


def find_freeboard_anomalies(stage_qa: pd.DataFrame) -> Dict[str, pd.Series]:
    """
    Returns stage names grouped into:
      - negative: Freeboard_Min_m < 0 (or Freeboard_Min_BowStern_m if present)
      - zero:     Freeboard_Min_m == 0
      - ok:       Freeboard_Min_m > 0
    """
    fb_col = (
        "Freeboard_Min_BowStern_m"
        if "Freeboard_Min_BowStern_m" in stage_qa.columns
        else "Freeboard_Min_m"
    )
    _require_cols(stage_qa, ["Stage", fb_col], "pipeline_stage_QA")
    s = stage_qa[["Stage", fb_col]].copy()
    s[fb_col] = pd.to_numeric(s[fb_col], errors="coerce")

    neg = s.loc[s[fb_col] < 0, "Stage"]
    zero = s.loc[s[fb_col] == 0, "Stage"]
    ok = s.loc[s[fb_col] > 0, "Stage"]

    return {
        "negative": neg.reset_index(drop=True),
        "zero": zero.reset_index(drop=True),
        "ok": ok.reset_index(drop=True),
    }


def check_hydro_coverage(
    hydro_df: pd.DataFrame, tmean_series: pd.Series
) -> Dict[str, float]:
    """
    Checks whether encountered Tmean values fall within hydro table coverage.
    """
    _require_cols(hydro_df, ["Tmean_m"], "hydro_table_for_solver")
    t_h = pd.to_numeric(hydro_df["Tmean_m"], errors="coerce").dropna()
    if t_h.empty:
        raise ValueError("hydro_table_for_solver has no valid Tmean_m rows")

    mn = float(t_h.min())
    mx = float(t_h.max())

    t = pd.to_numeric(tmean_series, errors="coerce").dropna()
    below = int((t < mn).sum())
    above = int((t > mx).sum())

    return {
        "min_tmean_hydro": mn,
        "max_tmean_hydro": mx,
        "below_min_count": float(below),
        "above_max_count": float(above),
    }


def build_debug_flags(stage_qa: pd.DataFrame) -> pd.DataFrame:
    """
    Produces a compact per-stage flag table useful for quickly spotting
    negative/zero freeboard and whether drafts were clipped to D_vessel.
    """
    fb_col = (
        "Freeboard_Min_BowStern_m"
        if "Freeboard_Min_BowStern_m" in stage_qa.columns
        else "Freeboard_Min_m"
    )
    need = ["Stage", "Draft_FWD_m", "Draft_AFT_m", fb_col]
    _require_cols(stage_qa, need, "pipeline_stage_QA")

    df = stage_qa.copy()
    for col in ["Draft_FWD_m", "Draft_AFT_m", fb_col]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    if "D_vessel_m" in df.columns:
        df["D_vessel_m"] = pd.to_numeric(df["D_vessel_m"], errors="coerce")
        df["Clipped_FWD"] = (
            df["Draft_FWD_m"].round(6) == df["D_vessel_m"].round(6)
        )
        df["Clipped_AFT"] = (
            df["Draft_AFT_m"].round(6) == df["D_vessel_m"].round(6)
        )
    else:
        df["Clipped_FWD"] = False
        df["Clipped_AFT"] = False

    df["FB_Negative"] = df[fb_col] < 0
    df["FB_Zero"] = df[fb_col] == 0
    df["Clip_Status"] = "RAW_OK"
    if "Draft_Clipped_raw" in df.columns:
        df.loc[df["Draft_Clipped_raw"] == True, "Clip_Status"] = "RAW_CLIPPED"
    if "Draft_Clipped_solver" in df.columns:
        df.loc[df["Draft_Clipped_solver"] == True, "Clip_Status"] = "SOLVER_CLIPPED"

    keep = [
        "Stage",
        "Draft_FWD_m",
        "Draft_AFT_m",
        fb_col,
        "FB_Negative",
        "FB_Zero",
        "Clipped_FWD",
        "Clipped_AFT",
    ]
    if "Freeboard_Min_m" in df.columns and fb_col != "Freeboard_Min_m":
        keep.append("Freeboard_Min_m")
    keep.append("Clip_Status")
    if "Draft_Source" in df.columns:
        keep.append("Draft_Source")
    if "Draft_Clipped_raw" in df.columns:
        keep.append("Draft_Clipped_raw")
    if "Draft_Clipped_solver" in df.columns:
        keep.append("Draft_Clipped_solver")
    return df[keep].sort_values("Stage").reset_index(drop=True)


def write_debug_report(
    stage_qa_csv: Path,
    hydro_csv: Path,
    out_md: Path,
    out_flags_csv: Optional[Path] = None,
) -> None:
    qa = pd.read_csv(stage_qa_csv)
    hydro = pd.read_csv(hydro_csv)

    flags = build_debug_flags(qa)
    fb = find_freeboard_anomalies(qa)

    has_source = "Draft_Source" in qa.columns
    has_raw = "Draft_FWD_m_raw" in qa.columns or "Draft_AFT_m_raw" in qa.columns
    has_solver = "Draft_FWD_m_solver" in qa.columns or "Draft_AFT_m_solver" in qa.columns
    has_clip_raw = "Draft_Clipped_raw" in qa.columns
    has_clip_solver = "Draft_Clipped_solver" in qa.columns

    source_summary = "unknown"
    if has_source:
        source_summary = "pipeline_stage_QA"
    elif has_raw and not has_solver:
        source_summary = "raw_stage_results"

    if "Tmean_m" in qa.columns:
        tmean_series = qa["Tmean_m"]
    else:
        tmean_series = 0.5 * (
            pd.to_numeric(qa["Draft_FWD_m"], errors="coerce")
            + pd.to_numeric(qa["Draft_AFT_m"], errors="coerce")
        )
    cov = check_hydro_coverage(hydro, tmean_series)

    lines: List[str] = []
    lines.append("# Pipeline Feasibility Debug Report")
    lines.append("")
    lines.append("## Data source")
    lines.append(f"- Detected source: {source_summary}")
    if has_source:
        src_counts = qa["Draft_Source"].astype(str).value_counts().to_dict()
        lines.append(f"- Draft_Source breakdown: {src_counts}")
    if has_clip_raw:
        clip_raw = int(pd.to_numeric(qa["Draft_Clipped_raw"], errors="coerce").fillna(0).sum())
        lines.append(f"- Draft_Clipped_raw count: {clip_raw}")
    if has_clip_solver:
        clip_solver = int(pd.to_numeric(qa["Draft_Clipped_solver"], errors="coerce").fillna(0).sum())
        lines.append(f"- Draft_Clipped_solver count: {clip_solver}")
    lines.append("")

    lines.append("## Freeboard anomalies")
    lines.append(f"- Negative freeboard stages: {len(fb['negative'])}")
    lines.append(f"- Zero freeboard stages: {len(fb['zero'])}")
    lines.append("")
    if len(fb["negative"]) > 0:
        lines.append("### Negative freeboard stage list")
        lines.append(", ".join(fb["negative"].tolist()))
        lines.append("")
    if len(fb["zero"]) > 0:
        lines.append("### Zero freeboard stage list")
        lines.append(", ".join(fb["zero"].tolist()))
        lines.append("")

    lines.append("## Hydro coverage")
    lines.append(
        f"- Hydro Tmean range: {cov['min_tmean_hydro']:.3f} .. "
        f"{cov['max_tmean_hydro']:.3f} m"
    )
    lines.append(f"- Tmean below min: {int(cov['below_min_count'])}")
    lines.append(f"- Tmean above max: {int(cov['above_max_count'])}")
    lines.append("")

    lines.append("## Per-stage flags (see CSV)")
    lines.append(f"- Rows: {len(flags)}")
    lines.append("")

    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text("\n".join(lines), encoding="utf-8")

    if out_flags_csv is not None:
        out_flags_csv.parent.mkdir(parents=True, exist_ok=True)
        flags.to_csv(out_flags_csv, index=False, encoding="utf-8-sig")


def _build_parser() -> "argparse.ArgumentParser":
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("--stage_qa", required=True, type=Path)
    p.add_argument("--hydro", required=True, type=Path)
    p.add_argument("--out_md", required=True, type=Path)
    p.add_argument("--out_flags_csv", default=None, type=Path)
    return p


def main() -> int:
    args = _build_parser().parse_args()
    write_debug_report(
        stage_qa_csv=args.stage_qa,
        hydro_csv=args.hydro,
        out_md=args.out_md,
        out_flags_csv=args.out_flags_csv,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
