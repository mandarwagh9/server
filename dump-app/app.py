from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import uuid
import os

# --------------------------------------------------
# Paths
# --------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
UPLOAD_DIR = Path("/data/dump")

STATIC_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# --------------------------------------------------
# App
# --------------------------------------------------
app = FastAPI(title="writesomething.fun", version="1.0.0")

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# --------------------------------------------------
# ROOT ROUTE (HOST-BASED)
# --------------------------------------------------
@app.get("/", response_class=HTMLResponse)
def root(request: Request):
    host = request.headers.get("host", "")

    # Root domain → Landing page
    if host == "writesomething.fun" or host.startswith("writesomething.fun"):
        landing = STATIC_DIR / "landing.html"
        if landing.exists():
            return landing.read_text(encoding="utf-8")
        return HTMLResponse("<h1>Landing page missing</h1>", status_code=500)

    # Dump subdomain → Upload UI
    index = STATIC_DIR / "index.html"
    if index.exists():
        return index.read_text(encoding="utf-8")

    return HTMLResponse("<h1>UI missing</h1>", status_code=500)

# --------------------------------------------------
# PUBLIC FILE LIST
# --------------------------------------------------
@app.get("/files", response_class=HTMLResponse)
def list_files():
    rows = []

    for file in sorted(UPLOAD_DIR.iterdir(), key=os.path.getmtime, reverse=True):
        if "_" not in file.name:
            continue

        file_id, name = file.name.split("_", 1)
        size_mb = file.stat().st_size / (1024 * 1024)

        rows.append(f"""
        <tr>
          <td>{name}</td>
          <td>{size_mb:.2f} MB</td>
          <td><a href="/file/{file_id}" target="_blank">Download</a></td>
        </tr>
        """)

    return HTMLResponse(f"""
    <html>
    <head>
      <title>Public Files</title>
      <style>
        body {{
          font-family: system-ui;
          background: #0f172a;
          color: #e5e7eb;
          padding: 40px;
        }}
        table {{
          width: 100%;
          border-collapse: collapse;
        }}
        th, td {{
          padding: 12px;
          border-bottom: 1px solid #334155;
        }}
        a {{
          color: #38bdf8;
        }}
      </style>
    </head>
    <body>
      <h1>Public Files</h1>
      <p><a href="/">⬅ Back</a></p>
      <table>
        <tr>
          <th>File</th>
          <th>Size</th>
          <th></th>
        </tr>
        {''.join(rows)}
      </table>
    </body>
    </html>
    """)

# --------------------------------------------------
# UPLOAD API (FAST)
# --------------------------------------------------
@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    file_id = str(uuid.uuid4())
    safe_name = file.filename.replace("/", "_").replace("\\", "_")
    file_path = UPLOAD_DIR / f"{file_id}_{safe_name}"

    BUFFER_SIZE = 1024 * 1024  # 1MB

    with open(file_path, "wb") as f:
        while True:
            chunk = await file.read(BUFFER_SIZE)
            if not chunk:
                break
            f.write(chunk)

    return {
        "filename": safe_name,
        "download_url": f"/file/{file_id}",
        "files_url": "/files"
    }

# --------------------------------------------------
# DOWNLOAD API
# --------------------------------------------------
@app.get("/file/{file_id}")
def download_file(file_id: str):
    matches = list(UPLOAD_DIR.glob(f"{file_id}_*"))
    if not matches:
        raise HTTPException(status_code=404, detail="File not found")

    file_path = matches[0]
    original_name = file_path.name.split("_", 1)[1]

    return FileResponse(
        file_path,
        filename=original_name,
        media_type="application/octet-stream"
    )
