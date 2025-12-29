#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unified header writer for all pipeline steps
Provides backward-compatible wrapper functions
"""

from pathlib import Path
from typing import List, Optional, Dict, Any
import pandas as pd
from openpyxl.worksheet.worksheet import Worksheet

from ssot.headers_registry import (
    load_registry,
    apply_schema,
    get_header_row,
    get_sheet_name,
    HeaderRegistry,
)


class HeadersWriter:
    """Unified writer with header registry support."""
    
    def __init__(self, registry_path: Optional[Path] = None):
        self.registry: Optional[HeaderRegistry] = None
        if registry_path and registry_path.exists():
            self.registry = load_registry(registry_path)
    
    def write_csv_with_schema(
        self,
        df: pd.DataFrame,
        output_path: Path,
        deliverable_id: str,
        *,
        keep_extra: bool = False,
        fill_missing: bool = True,
    ) -> pd.DataFrame:
        """
        Write CSV with schema application.
        
        Returns:
            Standardized DataFrame (for chaining)
        """
        if self.registry:
            df_std = apply_schema(
                df,
                self.registry,
                deliverable_id,
                keep_extra=keep_extra,
                fill_missing=fill_missing,
            )
        else:
            df_std = df
        
        df_std.to_csv(output_path, index=False, encoding="utf-8-sig")
        return df_std
    
    def write_excel_sheet_with_schema(
        self,
        ws: Worksheet,
        df: pd.DataFrame,
        deliverable_id: str,
        *,
        header_row: Optional[int] = None,
        keep_extra: bool = False,
        fill_missing: bool = True,
    ) -> pd.DataFrame:
        """
        Write Excel sheet with schema application.
        
        Args:
            ws: Worksheet to write to
            deliverable_id: Deliverable ID from registry
            header_row: Override header row (uses registry if None)
            keep_extra: Keep extra columns
            fill_missing: Fill missing columns
        
        Returns:
            Standardized DataFrame
        """
        if self.registry:
            # Get header row from registry if not provided
            if header_row is None:
                header_row = get_header_row(self.registry, deliverable_id) or 1
            
            # Apply schema
            df_std = apply_schema(
                df,
                self.registry,
                deliverable_id,
                keep_extra=keep_extra,
                fill_missing=fill_missing,
            )
        else:
            df_std = df
            if header_row is None:
                header_row = 1
        
        # Write headers
        for col_idx, header in enumerate(df_std.columns, start=1):
            ws.cell(row=header_row, column=col_idx).value = header
        
        # Write data
        for row_idx, (_, row) in enumerate(df_std.iterrows(), start=header_row + 1):
            for col_idx, val in enumerate(row, start=1):
                ws.cell(row=row_idx, column=col_idx).value = val
        
        return df_std
    
    def get_headers_for_deliverable(
        self,
        deliverable_id: str,
    ) -> Optional[List[str]]:
        """Get header list for deliverable (for legacy writerow compatibility)."""
        if not self.registry:
            return None
        
        if deliverable_id not in self.registry.deliverables:
            return None
        
        d = self.registry.deliverables[deliverable_id]
        headers = []
        for key in d.columns:
            if key in self.registry.fields:
                header = d.output_headers.get(key) or self.registry.fields[key].default_header
                headers.append(header)
        return headers

