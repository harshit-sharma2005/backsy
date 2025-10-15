# CSV/Excel Processing API (FastAPI)

A production-ready, lightweight FastAPI service to upload or fetch CSV/Excel files, clean and transform them, and return JSON or downloadable CSV/Excel outputs.

- Upload files or provide a URL or raw CSV text
- Detect delimiter and header rows
- Clean, impute, type-convert, normalize
- Filter, select, group, aggregate, and sort
- Export as JSON, CSV, or Excel with optional download link

## Quick start

Requirements: Python 3.10+

```powershell
# From repository root
python -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --reload
```

Open docs: http://127.0.0.1:8000/docs

## Endpoints

- GET `/health` — health check
- POST `/process/csv` — process CSV/Excel via upload, URL, or raw CSV text

Downloads are served from `/downloads/<filename>`.

## Request formats

You can send data either as multipart/form-data or application/json.

### Multipart example (file upload)

- file: UploadFile (CSV/Excel)
- url: string (alternative to file)
- raw_csv: string (alternative to file)
- output_format: json|csv|excel
- provide_download: boolean

### JSON example

```json
{
  "url": "https://example.com/data.csv",
  "raw_csv": null,
  "parsing": { "delimiter": null, "has_header": null, "skip_empty_rows": true, "trim_whitespace": true, "handle_quotes": true },
  "cleaning": { "drop_duplicates_rows": true, "drop_duplicates_columns": true, "fill_missing_enabled": true, "fill_missing_value": "NA", "auto_convert_types": true, "normalize_numeric": false, "drop_empty_rows": true, "drop_empty_columns": true },
  "selection": { "columns": ["col1", "col2"], "filters": [ {"column":"col1", "op": "=", "value": 5} ] },
  "aggregation": { "by": ["group_col"], "metrics": { "amount": ["sum", "mean", "std"] } },
  "sorting": { "sort": [{"column": "amount", "ascending": false}] },
  "export": { "output_format": "csv", "provide_download": true, "filename": "processed" }
}
```

## Response shape

```json
{
  "data": [ {"col1": 1, "col2": "x"} ],
  "stats": { "count": 10, "columns": ["col1", "col2"], "numeric_summary": {"col1": {"mean": 1.2}} },
  "download_url": "/downloads/processed.csv",
  "errors": [ {"message": "Aggregation failed", "detail": {"error": "..."}} ]
}
```

- `data` is omitted when `provide_download=true`.
- `download_url` is returned when exporting CSV/Excel.

## Notes on behavior

- Delimiter and header row are inferred if not provided.
- Excel files are read using `pandas.read_excel` (`openpyxl`).
- Duplicate columns are removed if they have identical content.
- Type conversion tries datetime then numeric for object columns.
- Normalization standardizes numeric columns to mean 0/std 1.
- Group-by returns either size per group or specified metrics.
- Basic stats are returned when no aggregation is requested.

## Development

- Format: follow PEP8; type hints included
- Run smoke tests:

```powershell
python -m pytest -q
```

- Env vars (prefix `CSVAPI_`):
  - `APP_NAME`
  - `EXPORT_DIR` (default: `exports`)
  - `EXPORT_TTL_SECONDS` (default 21600)
  - `CLEANUP_INTERVAL_SECONDS` (default 900)
  - `MAX_UPLOAD_MB` (default 50)
  - `CORS_ALLOW_ORIGINS` (default `*`)

## License

MIT
