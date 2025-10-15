"""Router exposing the /process/csv endpoint.

Supports multipart upload or JSON body with URL/raw_csv and options.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi import Body
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.models.schemas import (
    ExportOptions,
    ParsingOptions,
    CleaningOptions,
    SelectionOptions,
    SortingOptions,
    AggregationSpec,
    ProcessRequestBody,
    ProcessResponse,
)
from app.services.processing import parse_input, process_dataframe
from app.utils.file_utils import download_to_temp

router = APIRouter()


@router.post("/csv", response_model=ProcessResponse)
async def process_csv(
    # multipart form parts (optional)
    file: Optional[UploadFile] = File(default=None, description="CSV/Excel file to upload"),
    url: Optional[str] = Form(default=None, description="URL to CSV/Excel file"),
    raw_csv: Optional[str] = Form(default=None, description="Raw CSV text"),

    # JSON body alternative (for clients sending application/json)
    json_body: Optional[ProcessRequestBody] = Body(default=None),

    # Top-level options for multipart scenario (basic overrides)
    output_format: Optional[str] = Form(default=None),
    provide_download: Optional[bool] = Form(default=None),
) -> ProcessResponse:
    """Process an uploaded file, URL, or raw CSV into cleaned/transformed data.

    Accepts either multipart form fields or a JSON body. If both are provided,
    JSON body takes precedence for options.
    """
    try:
        # Merge inputs
        if json_body:
            parsing = json_body.parsing
            cleaning = json_body.cleaning
            selection = json_body.selection
            aggregation = json_body.aggregation
            sorting = json_body.sorting
            export = json_body.export
            url_in = json_body.url
            raw_csv_in = json_body.raw_csv
        else:
            parsing = ParsingOptions()
            cleaning = CleaningOptions()
            selection = SelectionOptions()
            aggregation = None
            sorting = SortingOptions()
            export = ExportOptions()
            if output_format:
                from app.models.schemas import OutputFormat

                export.output_format = OutputFormat(output_format)
            if provide_download is not None:
                export.provide_download = provide_download
            url_in = url
            raw_csv_in = raw_csv

        # Determine source
        url_path: Optional[Path] = None
        if url_in:
            try:
                url_path, _ = await download_to_temp(url_in)
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Failed to download URL: {e}")

        file_bytes: Optional[bytes] = None
        filename: Optional[str] = None
        if file is not None:
            filename = file.filename
            file_bytes = await file.read()
            # Basic size check (soft)
            if file_bytes and len(file_bytes) > settings.MAX_UPLOAD_MB * 1024 * 1024:
                raise HTTPException(status_code=413, detail="Uploaded file too large")

        # Parse
        parsed = parse_input(file_bytes=file_bytes, filename=filename, url_path=url_path, raw_csv=raw_csv_in, parsing=parsing)

        # Process
        resp = process_dataframe(
            df=parsed.df,
            parsing=parsing,
            cleaning=cleaning,
            selection=selection,
            aggregation=aggregation,
            sorting=sorting,
            export=export,
        )
        return resp
    except HTTPException:
        raise
    except Exception as e:
        # Return structured error
        return JSONResponse(
            status_code=400,
            content=ProcessResponse(data=None, stats=None, download_url=None, errors=[{"message": str(e)}]).dict(),
        )
