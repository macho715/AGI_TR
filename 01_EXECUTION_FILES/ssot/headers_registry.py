#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Headers Registry - SSOT for all pipeline output headers
Supports both validation (read) and schema application (write)
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import json
import re

import pandas as pd


def _norm(s: str, mode: str = "loose") -> str:
    """Normalize header strings for matching."""
    if s is None:
        return ""
    s = str(s).strip()
    if mode == "strict":
        return s
    # Remove spaces, underscores, hyphens, slashes, dots, convert to lowercase
    return re.sub(r"[^a-z0-9]", "", s.lower())


@dataclass(frozen=True)
class FieldDef:
    key: str
    default_header: str
    aliases: List[str]
    unit: str = ""
    type: str = "string"
    description: str = ""


@dataclass(frozen=True)
class Deliverable:
    id: str
    file_pattern: str
    sheet: Optional[str]
    header_row: Optional[int]
    columns: List[str]  # Ordered list of field keys
    output_headers: Dict[str, str]  # field_key -> output header override
    strict: bool
    version: str = ""


@dataclass(frozen=True)
class HeaderRegistry:
    version: str
    normalize: str
    fields: Dict[str, FieldDef]
    deliverables: Dict[str, Deliverable]
    alias_to_key: Dict[str, str]  # Precomputed: normalized alias -> canonical key


def load_registry(path: str | Path) -> HeaderRegistry:
    """Load registry from JSON file."""
    p = Path(path)
    raw = json.loads(p.read_text(encoding="utf-8"))

    meta = raw.get("meta") or {}
    version = str(meta.get("version", "0.0.0"))
    normalize = str(meta.get("normalize", "loose"))

    # Load fields
    fields_raw: Dict[str, Any] = raw.get("fields") or {}
    fields: Dict[str, FieldDef] = {}
    for k, v in fields_raw.items():
        fields[k] = FieldDef(
            key=k,
            default_header=str(v.get("default_header") or k),
            aliases=[str(a) for a in (v.get("aliases") or [])],
            unit=str(v.get("unit", "")),
            type=str(v.get("type", "string")),
            description=str(v.get("description", "")),
        )

    # Load deliverables
    deliv_raw: Dict[str, Any] = raw.get("deliverables") or {}
    deliverables: Dict[str, Deliverable] = {}
    for did, v in deliv_raw.items():
        deliverables[did] = Deliverable(
            id=did,
            file_pattern=str(v.get("file_pattern", "")),
            sheet=v.get("sheet"),
            header_row=v.get("header_row"),
            columns=[str(x) for x in (v.get("columns") or [])],
            output_headers={str(k): str(val) for k, val in (v.get("output_headers") or {}).items()},
            strict=bool(v.get("strict", True)),
            version=str(v.get("version", version)),
        )

    # Build alias map (normalized alias -> canonical field key)
    # Process fields in sorted order to ensure consistent precedence
    # (e.g., 'stage' should be matched before 'stage_id' for ambiguous aliases)
    alias_to_key: Dict[str, str] = {}
    for fkey in sorted(fields.keys()):
        fdef = fields[fkey]
        candidates = set([fdef.default_header, fkey] + list(fdef.aliases))
        for a in candidates:
            norm_a = _norm(a, normalize)
            # Only set if not already mapped (first match wins)
            if norm_a not in alias_to_key:
                alias_to_key[norm_a] = fkey

    return HeaderRegistry(
        version=version,
        normalize=normalize,
        fields=fields,
        deliverables=deliverables,
        alias_to_key=alias_to_key,
    )


def _find_field_key_for_col(reg: HeaderRegistry, col_name: str) -> Optional[str]:
    """Find canonical field key for a column name."""
    return reg.alias_to_key.get(_norm(col_name, reg.normalize))


def apply_schema(
    df: pd.DataFrame,
    reg: HeaderRegistry,
    deliverable_id: str,
    *,
    keep_extra: bool = False,
    fill_missing: bool = True,
    fill_value: Any = pd.NA,
) -> pd.DataFrame:
    """
    Apply header schema to DataFrame.

    Args:
        df: Input DataFrame (may have mismatched headers)
        reg: HeaderRegistry instance
        deliverable_id: Deliverable ID from registry
        keep_extra: Keep columns not in schema
        fill_missing: Fill missing columns with fill_value
        fill_value: Value to use for missing columns

    Returns:
        DataFrame with standardized headers and column order
    """
    if deliverable_id not in reg.deliverables:
        raise KeyError(f"Unknown deliverable_id: {deliverable_id}")

    d = reg.deliverables[deliverable_id]
    fields = reg.fields

    # Build mapping: existing df columns -> canonical field key
    col_to_key: Dict[str, str] = {}
    for c in df.columns:
        k = _find_field_key_for_col(reg, str(c))
        if k and k not in col_to_key.values():  # First match wins
            col_to_key[str(c)] = k

    # Build output columns in order
    out_cols: List[str] = []
    key_to_out_header: Dict[str, str] = {}
    for key in d.columns:
        if key not in fields:
            raise KeyError(f"Deliverable {deliverable_id} refers to unknown field key: {key}")
        # Use output_headers override if available, otherwise default_header
        out_header = d.output_headers.get(key) or fields[key].default_header
        key_to_out_header[key] = out_header
        out_cols.append(out_header)

    # Create output frame
    out = pd.DataFrame(index=df.index)

    # Copy/move values from input to output
    used_input_cols = set()
    for in_col, key in col_to_key.items():
        if key not in d.columns:
            continue
        used_input_cols.add(in_col)
        out_header = key_to_out_header[key]
        out[out_header] = df[in_col]

    # Fill missing columns
    if fill_missing:
        for key in d.columns:
            oh = key_to_out_header[key]
            if oh not in out.columns:
                out[oh] = fill_value

    # Keep extra columns if requested
    if keep_extra:
        extra_cols = [c for c in df.columns if c not in used_input_cols]
        for c in extra_cols:
            out[str(c)] = df[c]

    # Strict validation
    if d.strict:
        rep = validate_df(out, reg, deliverable_id, treat_out_headers_as_true=True)
        if rep["missing_keys"]:
            raise ValueError(
                f"Header schema violation (missing): {rep['missing_keys']} "
                f"for deliverable {deliverable_id}"
            )
        if rep["unexpected_cols"] and not keep_extra:
            raise ValueError(
                f"Header schema violation (unexpected): {rep['unexpected_cols']} "
                f"for deliverable {deliverable_id}"
            )

    return out


def validate_df(
    df: pd.DataFrame,
    reg: HeaderRegistry,
    deliverable_id: str,
    *,
    treat_out_headers_as_true: bool = False,
) -> Dict[str, Any]:
    """
    Validate DataFrame against deliverable schema.

    Returns:
        {
            "missing_keys": [...],
            "unexpected_cols": [...],
            "expected_headers": [...]
        }
    """
    d = reg.deliverables[deliverable_id]
    fields = reg.fields

    # Build expected headers
    expected_headers: List[str] = []
    header_to_key: Dict[str, str] = {}
    for key in d.columns:
        expected_header = d.output_headers.get(key) or fields[key].default_header
        expected_headers.append(expected_header)
        header_to_key[expected_header] = key

    cols = [str(c) for c in df.columns]

    if treat_out_headers_as_true:
        # Direct header name comparison
        missing_headers = [h for h in expected_headers if h not in cols]
        unexpected = [c for c in cols if c not in expected_headers]
        missing_keys = [header_to_key.get(h) for h in missing_headers if header_to_key.get(h)]
        return {
            "missing_keys": missing_keys,
            "unexpected_cols": unexpected,
            "expected_headers": expected_headers,
        }

    # Otherwise: treat df columns as "input" and check if they map to required keys
    present_keys = set()
    for c in cols:
        k = _find_field_key_for_col(reg, c)
        if k in d.columns:
            present_keys.add(k)

    missing_keys = [k for k in d.columns if k not in present_keys]
    unexpected = []
    for c in cols:
        k = _find_field_key_for_col(reg, c)
        if (k is None) or (k not in d.columns):
            unexpected.append(c)

    return {
        "missing_keys": missing_keys,
        "unexpected_cols": unexpected,
        "expected_headers": expected_headers,
    }


def get_header_row(reg: HeaderRegistry, deliverable_id: str) -> Optional[int]:
    """Get header row number for deliverable."""
    if deliverable_id not in reg.deliverables:
        return None
    return reg.deliverables[deliverable_id].header_row


def get_sheet_name(reg: HeaderRegistry, deliverable_id: str) -> Optional[str]:
    """Get sheet name for deliverable."""
    if deliverable_id not in reg.deliverables:
        return None
    return reg.deliverables[deliverable_id].sheet

