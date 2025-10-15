"""Pydantic models for request and response payloads."""
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Sequence, Union

from pydantic import BaseModel, Field, field_validator


class OutputFormat(str, Enum):
    json = "json"
    csv = "csv"
    excel = "excel"


class FilterOp(str, Enum):
    eq = "="
    lt = "<"
    lte = "<="
    gt = ">"
    gte = ">="
    ne = "!="
    regex = "regex"
    contains = "contains"


class FilterCondition(BaseModel):
    column: str = Field(..., description="Column to filter on")
    op: FilterOp = Field(..., description="Operation to apply")
    value: Any = Field(..., description="Value for comparison or pattern")


class SortOption(BaseModel):
    column: str
    ascending: bool = True


class AggregationFunc(str, Enum):
    count = "count"
    nunique = "nunique"
    sum = "sum"
    mean = "mean"
    median = "median"
    std = "std"


class AggregationSpec(BaseModel):
    by: Optional[Sequence[str]] = Field(None, description="Columns to group by")
    metrics: Dict[str, Sequence[AggregationFunc]] = Field(
        default_factory=dict,
        description="Mapping of column -> aggregation functions",
    )


class ParsingOptions(BaseModel):
    delimiter: Optional[str] = Field(None, description="Explicit CSV delimiter; if None, auto-detect")
    has_header: Optional[bool] = Field(None, description="Explicit header presence; if None, infer")
    skip_empty_rows: bool = True
    trim_whitespace: bool = True
    handle_quotes: bool = True


class CleaningOptions(BaseModel):
    drop_duplicates_rows: bool = True
    drop_duplicates_columns: bool = True
    fill_missing_enabled: bool = False
    fill_missing_value: Optional[Any] = None
    auto_convert_types: bool = True
    normalize_numeric: bool = False
    drop_empty_rows: bool = True
    drop_empty_columns: bool = True


class SelectionOptions(BaseModel):
    columns: Optional[Sequence[str]] = None
    filters: Optional[Sequence[FilterCondition]] = None


class SortingOptions(BaseModel):
    sort: Optional[Sequence[SortOption]] = None


class ExportOptions(BaseModel):
    output_format: OutputFormat = OutputFormat.json
    provide_download: bool = False
    filename: Optional[str] = None


class ProcessRequestBody(BaseModel):
    url: Optional[str] = Field(None, description="URL to a CSV or Excel file")
    raw_csv: Optional[str] = Field(None, description="Raw CSV text provided inline")

    parsing: ParsingOptions = Field(default_factory=ParsingOptions)
    cleaning: CleaningOptions = Field(default_factory=CleaningOptions)
    selection: SelectionOptions = Field(default_factory=SelectionOptions)
    aggregation: Optional[AggregationSpec] = Field(None)
    sorting: SortingOptions = Field(default_factory=SortingOptions)
    export: ExportOptions = Field(default_factory=ExportOptions)

    @field_validator("raw_csv")
    @classmethod
    def validate_raw_csv(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not isinstance(v, str):
            raise ValueError("raw_csv must be a string if provided")
        return v


class ErrorDetail(BaseModel):
    message: str
    detail: Optional[Dict[str, Any]] = None


class ProcessResponse(BaseModel):
    data: Optional[List[Dict[str, Any]]]
    stats: Optional[Dict[str, Any]] = None
    download_url: Optional[str] = None
    errors: Optional[List[ErrorDetail]] = None
