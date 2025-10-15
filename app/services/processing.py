"""Data processing service encapsulating CSV/Excel parsing and transformations."""
from __future__ import annotations

import io
import csv
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import pandas as pd

from app.core.config import settings
from app.models.schemas import (
    AggregationFunc,
    AggregationSpec,
    CleaningOptions,
    FilterOp,
    ExportOptions,
    FilterCondition,
    OutputFormat,
    ParsingOptions,
    ProcessResponse,
    SelectionOptions,
    SortingOptions,
)
from app.utils.file_utils import build_download_url, safe_filename


@dataclass
class ParsedInput:
    df: pd.DataFrame
    source_name: str


def _detect_delimiter(text: str) -> str:
    """Detect delimiter among comma, semicolon, or tab by simple heuristic."""
    sample = "\n".join(text.splitlines()[:10])
    counts = {",": sample.count(","), ";": sample.count(";"), "\t": sample.count("\t")}
    # Prefer comma when ties, then semicolon, then tab
    return max(counts, key=lambda k: (counts[k], -[",",";","\t"].index(k)))


def _maybe_infer_header(text: str) -> bool:
    """Infer if a header exists by checking first two rows for non-numeric tokens."""
    lines = [ln for ln in text.splitlines() if ln.strip()][:3]
    if len(lines) < 2:
        return True
    delim = _detect_delimiter(text)
    first = [c.strip() for c in lines[0].split(delim)]
    second = [c.strip() for c in lines[1].split(delim)]
    # Heuristic: first row has more alphabetic tokens than second
    alpha_first = sum(bool(re.search(r"[A-Za-z]", c)) for c in first)
    alpha_second = sum(bool(re.search(r"[A-Za-z]", c)) for c in second)
    return alpha_first >= alpha_second


def _read_csv_text(text: str, parsing: ParsingOptions) -> pd.DataFrame:
    delim = parsing.delimiter or _detect_delimiter(text)
    header = "infer" if parsing.has_header is None else (0 if parsing.has_header else None)
    read_kwargs = dict(
        sep=delim,
        header=header,
        engine="python",
        skip_blank_lines=parsing.skip_empty_rows,
        skipinitialspace=parsing.trim_whitespace,
    )
    if parsing.handle_quotes:
        read_kwargs.update(dict(quotechar='"'))
    else:
        read_kwargs.update(dict(quoting=csv.QUOTE_NONE, escapechar='\\'))
    df = pd.read_csv(io.StringIO(text), **read_kwargs)
    return df


def _read_file(path: Path, parsing: ParsingOptions) -> pd.DataFrame:
    # Decide based on extension
    ext = path.suffix.lower()
    if ext in {".xls", ".xlsx", ".xlsm", ".xlsb"}:
        df = pd.read_excel(path)
    else:
        # Read as text to allow delimiter detection and options
        text = path.read_text(encoding="utf-8", errors="ignore")
        if parsing.has_header is None:
            parsing = parsing.copy(update={"has_header": _maybe_infer_header(text)})
        df = _read_csv_text(text, parsing)
    return df


def _trim_and_drop_empty(df: pd.DataFrame, options: CleaningOptions) -> pd.DataFrame:
    # Trim whitespace
    if options:
        if options.drop_empty_rows or options.drop_empty_columns or options.auto_convert_types or options.normalize_numeric:
            pass
    # Apply whitespace trimming on object columns
    for col in df.select_dtypes(include=["object", "string"]).columns:
        df[col] = df[col].astype(str).str.strip()
    # Drop empty rows/cols if requested
    if options.drop_empty_rows:
        df = df.dropna(how="all")
    if options.drop_empty_columns:
        df = df.dropna(axis=1, how="all")
    return df


def _drop_duplicate_columns(df: pd.DataFrame) -> pd.DataFrame:
    # First remove duplicate column names (keep first occurrence)
    df = df.loc[:, ~df.columns.duplicated()]
    # Then identify duplicate columns by identical content
    duplicated = []
    seen: Dict[str, pd.Series] = {}
    for c in df.columns:
        s = df[c]
        for k, v in seen.items():
            if s.equals(v):
                duplicated.append(c)
                break
        else:
            seen[c] = s
    if duplicated:
        df = df.drop(columns=duplicated)
    return df


def _fill_missing(df: pd.DataFrame, options: CleaningOptions) -> pd.DataFrame:
    if not options.fill_missing_enabled:
        return df
    value = options.fill_missing_value
    return df.fillna(value)


def _auto_convert_types(df: pd.DataFrame) -> pd.DataFrame:
    # Try to convert to numeric and datetime where possible
    for col in df.columns:
        s = df[col]
        if s.dtype == object:
            # Try datetime then numeric
            converted_datetime = pd.to_datetime(s, errors="ignore")
            if converted_datetime.dtype.kind in {"M"}:
                df[col] = converted_datetime
                continue
            converted_numeric = pd.to_numeric(s, errors="ignore")
            if converted_numeric.dtype.kind in {"i", "u", "f"}:
                df[col] = converted_numeric
                continue
            # Try boolean conversion for common string booleans
            lower = s.astype(str).str.lower()
            if lower.isin(["true", "false", "1", "0", "yes", "no"]).any():
                map_bool = {"true": True, "1": True, "yes": True, "false": False, "0": False, "no": False}
                df[col] = lower.map(map_bool).where(~lower.isin(map_bool.keys()), other=s)
    return df


def _normalize_numeric(df: pd.DataFrame) -> pd.DataFrame:
    num_cols = df.select_dtypes(include=["number"]).columns
    for col in num_cols:
        s = df[col]
        std = s.std()
        if std and std != 0:
            df[col] = (s - s.mean()) / std
    return df


def _apply_filters(df: pd.DataFrame, filters: Sequence[FilterCondition]) -> pd.DataFrame:
    mask = pd.Series([True] * len(df), index=df.index)
    for f in filters:
        if f.column not in df.columns:
            continue
        col = df[f.column]
        op = f.op
        val = f.value
        try:
            if op == FilterOp.eq:
                mask &= col == val
            elif op == FilterOp.ne:
                mask &= col != val
            elif op == FilterOp.lt:
                mask &= col < val
            elif op == FilterOp.lte:
                mask &= col <= val
            elif op == FilterOp.gt:
                mask &= col > val
            elif op == FilterOp.gte:
                mask &= col >= val
            elif op == FilterOp.contains:
                mask &= col.astype(str).str.contains(str(val), na=False)
            elif op == FilterOp.regex:
                mask &= col.astype(str).str.contains(str(val), na=False, regex=True)
        except Exception:
            # If comparison fails due to type mismatch, skip this filter
            pass
    return df[mask]


def _aggregate(df: pd.DataFrame, agg: AggregationSpec) -> pd.DataFrame:
    if not agg.metrics:
        # If only group-by is provided, return size per group
        if agg.by:
            return df.groupby(list(agg.by), dropna=False).size().reset_index(name="count")
        return df
    # Build aggregation dict
    agg_dict: Dict[str, List[str]] = {k: [v.value for v in vals] for k, vals in agg.metrics.items()}
    grouped = df.groupby(list(agg.by) if agg.by else None, dropna=False)
    out = grouped.agg(agg_dict).reset_index()
    # Flatten MultiIndex columns if present
    if isinstance(out.columns, pd.MultiIndex):
        out.columns = ["_".join([str(c) for c in tup if c != ""]) for tup in out.columns.values]
    return out


def _sort(df: pd.DataFrame, sorting: SortingOptions) -> pd.DataFrame:
    if not sorting.sort:
        return df
    by = [s.column for s in sorting.sort if s.column in df.columns]
    ascending = [s.ascending for s in sorting.sort if s.column in df.columns]
    if by:
        df = df.sort_values(by=by, ascending=ascending)
    return df


def _export(df: pd.DataFrame, export: ExportOptions) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
    """Export data to desired format. Returns (json_list, download_url)."""
    if export.output_format == OutputFormat.json and not export.provide_download:
        return df.to_dict(orient="records"), None

    # Create file in exports directory
    base = safe_filename(export.filename or f"export_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}")
    if export.output_format == OutputFormat.csv:
        path = settings.EXPORT_DIR / f"{base}.csv"
        df.to_csv(path, index=False)
    elif export.output_format == OutputFormat.excel:
        path = settings.EXPORT_DIR / f"{base}.xlsx"
        df.to_excel(path, index=False)
    else:
        # JSON download as CSV fallback
        path = settings.EXPORT_DIR / f"{base}.csv"
        df.to_csv(path, index=False)

    return (None if export.provide_download else df.to_dict(orient="records")), build_download_url(path)


def process_dataframe(
    df: pd.DataFrame,
    parsing: ParsingOptions,
    cleaning: CleaningOptions,
    selection: SelectionOptions,
    aggregation: Optional[AggregationSpec],
    sorting: SortingOptions,
    export: ExportOptions,
) -> ProcessResponse:
    """Apply the full pipeline to the provided DataFrame and create a response."""
    errors: List[Dict[str, Any]] = []

    # Cleaning and preparation
    df = _trim_and_drop_empty(df, cleaning)

    if cleaning.drop_duplicates_rows:
        df = df.drop_duplicates()
    if cleaning.drop_duplicates_columns:
        df = _drop_duplicate_columns(df)

    if cleaning.fill_missing_enabled:
        df = _fill_missing(df, cleaning)

    if cleaning.auto_convert_types:
        df = _auto_convert_types(df)

    if cleaning.normalize_numeric:
        df = _normalize_numeric(df)

    # Selection and filtering
    if selection.columns:
        cols = [c for c in selection.columns if c in df.columns]
        df = df.loc[:, cols]
    if selection.filters:
        df = _apply_filters(df, selection.filters)

    # Aggregation
    stats: Optional[Dict[str, Any]] = None
    if aggregation:
        try:
            agg_df = _aggregate(df, aggregation)
            df = agg_df
        except Exception as e:
            errors.append({"message": "Aggregation failed", "detail": {"error": str(e)}})

    # Sorting
    df = _sort(df, sorting)

    # Basic stats if requested via aggregation omitted but maybe useful
    if not aggregation:
        try:
            numeric = df.select_dtypes(include=["number"])  # compute basic stats for numeric columns
            stats = {
                "count": int(len(df)),
                "columns": list(map(str, df.columns)),
                "numeric_summary": numeric.describe().to_dict(),
            }
        except Exception:
            pass

    # Export or return JSON
    data_json, download_url = _export(df, export)

    return ProcessResponse(data=data_json, stats=stats, download_url=download_url)


def parse_input(
    file_bytes: Optional[bytes],
    filename: Optional[str],
    url_path: Optional[Path],
    raw_csv: Optional[str],
    parsing: ParsingOptions,
) -> ParsedInput:
    """Parse incoming content from file bytes, local path, or raw CSV text."""
    if raw_csv:
        if parsing.has_header is None:
            parsing = parsing.copy(update={"has_header": _maybe_infer_header(raw_csv)})
        df = _read_csv_text(raw_csv, parsing)
        return ParsedInput(df=df, source_name=filename or "raw.csv")

    if url_path is not None:
        df = _read_file(url_path, parsing)
        return ParsedInput(df=df, source_name=url_path.name)

    if file_bytes is not None and filename:
        # Write to buffer for pandas
        ext = Path(filename).suffix.lower()
        if ext in {".xls", ".xlsx", ".xlsm", ".xlsb"}:
            df = pd.read_excel(io.BytesIO(file_bytes))
        else:
            text = file_bytes.decode("utf-8", errors="ignore")
            if parsing.has_header is None:
                parsing = parsing.copy(update={"has_header": _maybe_infer_header(text)})
            df = _read_csv_text(text, parsing)
        return ParsedInput(df=df, source_name=filename)

    raise ValueError("No input provided: expected file upload, URL, or raw_csv text")
