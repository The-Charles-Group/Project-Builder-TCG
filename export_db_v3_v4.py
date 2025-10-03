#!/usr/bin/env python3
"""
Export v4/v4b and (optionally) v3 databases from the Replit project into separate Excel workbooks.

Usage (inside your Replit project root):
    pip install pandas openpyxl
    python export_db_v3_v4.py

Outputs (created next to the script):
    - DB_v4_export.xlsx      (or a DB_v4_export_csvs/ folder if openpyxl is unavailable)
    - DB_v3_export.xlsx      (or a DB_v3_export_csvs/ folder if openpyxl is unavailable)
"""
import os
import sys
from typing import Dict, Tuple, Optional
import pandas as pd

# ---- Where the codebase looks for database files ----
V4_XLSX_CANDIDATES = [
    "Replit_App_DB_READABLE_FullRows_v4b.xlsx",
    "Replit_App_DB_READABLE_FullRows_v4.xlsx",
]
V4_CSV_DIR = "Replit_App_DB_READABLE_FullRows_v4_csvs"

V3_CANDIDATES = [
    os.getenv("APB_V3_DB"),
    "Replit_App_DB_READABLE_FullRows_v3.xlsx",
    "data/Replit_App_DB_READABLE_FullRows_v3.xlsx",
    "static/data/Replit_App_DB_READABLE_FullRows_v3.xlsx",
]

# ---- Sheets the app loads from the v4 workbook (or v4 CSV bundle) ----
V4_SHEETS = [
    "All_Task_Rows",
    "Deliverable_Index",
    "Bundle_Rules_Table",
    "Bundle_Scenario_Defaults",
    "Bundles_By_Deliverable",
    "Bundles_Hours_By_Role",
    "Role_Rate_Card",
    "Role_Rate_Matrix",
    "Rate_Bands",
    "Timeline_Params",
    "Timeline_Scaling",
    "Timeline_Weighting",
    "Slack_Settings",
    "Pricing_Settings",
    "Scenario_Templates",
    "UI_Options",
    "RFP_Matching_Rules",
]

def _find_v4() -> Tuple[Optional[str], Optional[str]]:
    """
    Returns ('xlsx', path) if a v4/v4b workbook is found,
            ('csv', dir) if a v4 CSV directory is found,
            (None, None) otherwise.
    """
    for p in V4_XLSX_CANDIDATES:
        if p and os.path.exists(p):
            return ("xlsx", p)
    if os.path.isdir(V4_CSV_DIR):
        return ("csv", V4_CSV_DIR)
    return (None, None)

def _safe_sheet_name(name: str) -> str:
    # Excel sheet name rules: max 31 chars, remove invalid characters
    bad = ':/\\?*[]'
    n = ''.join('-' if ch in bad else ch for ch in (name or 'Sheet'))
    n = n.strip() or 'Sheet'
    return n[:31]

def export_v4() -> Optional[str]:
    kind, src = _find_v4()
    if not kind:
        print("[v4] No v4/v4b workbook or CSV directory found.")
        return None

    print(f"[v4] Source type: {kind} | Source: {src}")
    dfs: Dict[str, pd.DataFrame] = {}

    if kind == "xlsx":
        for sh in V4_SHEETS:
            try:
                dfs[sh] = pd.read_excel(src, sheet_name=sh)
                print(f"[v4] Loaded sheet: {sh} ({dfs[sh].shape[0]} rows, {dfs[sh].shape[1]} cols)")
            except Exception as e:
                print(f"[v4] WARN: could not read sheet '{sh}' from {src}: {e}")
    else:  # CSV bundle
        for sh in V4_SHEETS:
            path = os.path.join(src, f"{sh}.csv")
            if os.path.exists(path):
                try:
                    dfs[sh] = pd.read_csv(path)
                    print(f"[v4] Loaded CSV: {path} ({dfs[sh].shape[0]} rows)")
                except Exception as e:
                    print(f"[v4] WARN: could not read CSV '{path}': {e}")
            else:
                print(f"[v4] NOTE: CSV not found: {path} (skipping)")

    if not dfs:
        print("[v4] No v4 dataframes were read; nothing to export.")
        return None

    out_xlsx = "DB_v4_export.xlsx"
    try:
        with pd.ExcelWriter(out_xlsx, engine="openpyxl") as xw:
            for name, df in dfs.items():
                df.to_excel(xw, sheet_name=_safe_sheet_name(name), index=False)
        print(f"[v4] Wrote {out_xlsx}")
        return out_xlsx
    except Exception as e:
        print(f"[v4] Could not write Excel ({e}); exporting CSVs instead.")
        out_dir = "DB_v4_export_csvs"
        os.makedirs(out_dir, exist_ok=True)
        for name, df in dfs.items():
            df.to_csv(os.path.join(out_dir, f"{name}.csv"), index=False)
        print(f"[v4] Wrote CSVs to {out_dir}/")
        return out_dir

def _find_v3() -> Optional[str]:
    for p in V3_CANDIDATES:
        if p and os.path.exists(p):
            return p
    return None

def export_v3() -> Optional[str]:
    v3 = _find_v3()
    if not v3:
        print("[v3] No v3 workbook found (set APB_V3_DB or place the file in project root/data/static/data).")
        return None

    dfs: Dict[str, pd.DataFrame] = {}
    for sh in ("All_Task_Rows", "Drivers"):
        try:
            dfs[sh] = pd.read_excel(v3, sheet_name=sh)
            print(f"[v3] Loaded sheet: {sh} ({dfs[sh].shape[0]} rows, {dfs[sh].shape[1]} cols)")
        except Exception as e:
            print(f"[v3] WARN: could not read sheet '{sh}' from {v3}: {e}")

    if not dfs:
        print("[v3] No v3 sheets were read; nothing to export.")
        return None

    out_xlsx = "DB_v3_export.xlsx"
    try:
        with pd.ExcelWriter(out_xlsx, engine="openpyxl") as xw:
            for name, df in dfs.items():
                df.to_excel(xw, sheet_name=_safe_sheet_name(name), index=False)
        print(f"[v3] Wrote {out_xlsx}")
        return out_xlsx
    except Exception as e:
        print(f"[v3] Could not write Excel ({e}); exporting CSVs instead.")
        out_dir = "DB_v3_export_csvs"
        os.makedirs(out_dir, exist_ok=True)
        for name, df in dfs.items():
            df.to_csv(os.path.join(out_dir, f"{name}.csv"), index=False)
        print(f"[v3] Wrote CSVs to {out_dir}/")
        return out_dir

if __name__ == "__main__":
    print("=== Database Exporter ===")
    v4_out = export_v4()
    v3_out = export_v3()
    print("=== Done ===")
    if not v4_out and not v3_out:
        sys.exit(1)
