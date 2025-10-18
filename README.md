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

## Examples

### Upload CSV via curl

```bash
curl -X POST "http://127.0.0.1:8000/process/csv" \
  -F "file=@data.csv" \
  -F "output_format=json" \
  -F "provide_download=false"
```

### Call JSON mode with Python

```python
import requests

url = "http://127.0.0.1:8000/process/csv"
payload = {
    "url": "https://example.com/data.csv",
    "cleaning": {
        "drop_duplicates_rows": True,
        "fill_missing_enabled": True,
        "fill_missing_value": "NA"
    },
    "export": {
        "output_format": "json",
        "provide_download": False
    }
}

response = requests.post(url, json=payload)
data = response.json()
print(data)
```

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

## Deploy on Render

To deploy this service on Render:

1. Create a new **Web Service** in your Render dashboard
2. Connect your repository
3. Use the following configuration:

**Start Command:**
```
python -m uvicorn main:app --host 0.0.0.0 --port $PORT --workers 2
```

**Required Environment Variables:**
- `CSVAPI_EXPORT_DIR` — Directory for temporary exports (default: `exports`)
- `CSVAPI_MAX_UPLOAD_MB` — Maximum file upload size in MB (default: `50`)
- `CSVAPI_EXPORT_TTL_SECONDS` — Time-to-live for exported files (default: `21600`)
- `CSVAPI_CLEANUP_INTERVAL_SECONDS` — Cleanup interval in seconds (default: `900`)
- `CSVAPI_CORS_ALLOW_ORIGINS` — CORS allowed origins (default: `*`)

**Note:** Make sure to configure a persistent disk or volume mounted at your `CSVAPI_EXPORT_DIR` path if you need exports to survive across deployments.

## Troubleshooting

### No UI found

If you visit the root URL and don't see a UI, navigate to `/docs` for the interactive Swagger documentation or use the API endpoints directly.

### 413 Upload Too Large

If you get a 413 error when uploading files:
- Check the `CSVAPI_MAX_UPLOAD_MB` environment variable (default is 50 MB)
- Increase it if needed: `CSVAPI_MAX_UPLOAD_MB=100`
- If deploying behind a reverse proxy (nginx, Apache), also verify its upload size limit

### Export Directory/Mount Issues

If downloads fail or exports are not persisted:
- Ensure the `CSVAPI_EXPORT_DIR` directory exists and is writable
- On cloud platforms (Render, Railway, etc.), configure a persistent volume/disk mounted at this path
- Check file permissions: the app user must have read/write access to the export directory
- Verify the cleanup job is not deleting files too aggressively (adjust `CSVAPI_EXPORT_TTL_SECONDS`)

- Env vars (prefix `CSVAPI_`):
  - `APP_NAME`
  - `EXPORT_DIR` (default: `exports`)
  - `EXPORT_TTL_SECONDS` (default 21600)
  - `CLEANUP_INTERVAL_SECONDS` (default 900)
  - `MAX_UPLOAD_MB` (default 50)
  - `CORS_ALLOW_ORIGINS` (default `*`)

## License

MIT
