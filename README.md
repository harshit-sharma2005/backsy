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

## Examples

### 1) Upload a CSV file with curl (multipart)

This uploads a local CSV file, requests a CSV export, and asks the API to provide a downloadable link.

```bash
curl -X POST "http://127.0.0.1:8000/process/csv" \
  -H "accept: application/json" \
  -F "file=@sample.csv;type=text/csv" \
  -F "output_format=csv" \
  -F "provide_download=true"
```

Typical success response (truncated):

```json
{
  "data": null,
  "stats": { "count": 42, "columns": ["col1", "col2"] },
  "download_url": "/downloads/processed.csv",
  "errors": null
}
```

Open the returned download_url in your browser to fetch the exported file.

### 2) Python example (JSON mode)

This example sends raw CSV text and asks for JSON output inline (no download).

```python
import requests

API = "http://127.0.0.1:8000/process/csv"

payload = {
    "raw_csv": "name,age\nalice,30\nbob,25\n",
    "selection": {"columns": ["name", "age"]},
    "sorting": {"sort": [{"column": "age", "ascending": False}]},
    "export": {"output_format": "json", "provide_download": False}
}

resp = requests.post(API, json=payload, timeout=30)
resp.raise_for_status()
print(resp.json())
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

## Deploy on Render

You can deploy this service directly on Render using the included `render.yaml` or via the dashboard.

- Build Command: `pip install -r requirements.txt`
- Start Command: `python -m uvicorn main:app --host 0.0.0.0 --port $PORT --workers 2`
- Required environment variables (examples):
  - `CSVAPI_EXPORT_DIR` (e.g. `/srv/exports`) — where exported files are written and served from `/downloads`
  - `CSVAPI_MAX_UPLOAD_MB` (e.g. `100`) — soft upload size limit enforced by the app
  - Optional: `CSVAPI_CORS_ALLOW_ORIGINS` (e.g. `*`)

If you need persistent downloads across restarts, add a Disk in Render and mount it at the same path as `CSVAPI_EXPORT_DIR` (e.g. `/srv/exports`). The provided `render.yaml` shows an example disk configuration.

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

## Troubleshooting

- No UI found
  - The root route (`/`) renders `frontend/index.html` if present. If you see “No UI found”, either open the interactive docs at `/docs`, or add a simple HTML file at `frontend/index.html` and redeploy. In production, ensure the `frontend/` folder is included in your build.

- 413 upload too large
  - The API enforces a soft limit based on `CSVAPI_MAX_UPLOAD_MB`. Increase this env var and redeploy if needed. If you’re behind a proxy or platform that also limits request size, raise that limit there as well.

- Export directory/mount issues
  - Downloads are served from `/downloads`, backed by the path in `CSVAPI_EXPORT_DIR`. Ensure this directory exists and is writable at runtime. On Render, mount a persistent Disk at the same path (e.g. `/srv/exports`). If the path changes, update `CSVAPI_EXPORT_DIR` to match. A restart may be required after mounting.

## License

MIT
