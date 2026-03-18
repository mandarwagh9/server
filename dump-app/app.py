from fastapi import (
    FastAPI,
    UploadFile,
    File,
    HTTPException,
    Request,
    Form,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import uuid
import os
import sqlite3
import hashlib
import time
import mimetypes
import random
import string
import asyncio
from typing import Optional, Dict, Set
from collections import defaultdict

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
# Database (SQLite) for file metadata
# --------------------------------------------------
DB_PATH = UPLOAD_DIR / "files.db"


def get_db():
    conn = getattr(app.state, "db_conn", None)
    if conn is None:
        conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        app.state.db_conn = conn
    return app.state.db_conn


def init_db():
    conn = get_db()
    conn.execute("""
    CREATE TABLE IF NOT EXISTS files (
        id TEXT PRIMARY KEY,
        filename TEXT,
        mime TEXT,
        size INTEGER,
        uploaded_at INTEGER,
        checksum TEXT,
        folder TEXT DEFAULT '',
        is_deleted INTEGER DEFAULT 0,
        deleted_at INTEGER
    )
    """)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS folders (
        name TEXT PRIMARY KEY,
        created_at INTEGER
    )
    """)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS suggestions (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        description TEXT,
        author TEXT,
        upvotes INTEGER DEFAULT 0,
        status TEXT DEFAULT 'pending',
        created_at INTEGER,
        ip_address TEXT
    )
    """)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS suggestion_upvotes (
        suggestion_id TEXT NOT NULL,
        ip_address TEXT NOT NULL,
        created_at INTEGER,
        PRIMARY KEY (suggestion_id, ip_address)
    )
    """)
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_uploaded_at ON files(uploaded_at DESC)"
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_folder ON files(folder)")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_suggestion_created ON suggestions(created_at DESC)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_suggestion_upvotes ON suggestions(upvotes DESC)"
    )
    conn.execute("""
    CREATE TABLE IF NOT EXISTS pastes (
        id TEXT PRIMARY KEY,
        title TEXT,
        content TEXT NOT NULL,
        language TEXT DEFAULT 'plaintext',
        password_hash TEXT,
        expires_at INTEGER,
        views INTEGER DEFAULT 0,
        created_at INTEGER,
        ip_address TEXT
    )
    """)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS links (
        id TEXT PRIMARY KEY,
        url TEXT NOT NULL,
        title TEXT,
        description TEXT,
        tags TEXT DEFAULT '',
        clicks INTEGER DEFAULT 0,
        created_at INTEGER
    )
    """)
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_paste_created ON pastes(created_at DESC)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_link_created ON links(created_at DESC)"
    )
    conn.commit()


def migrate_existing_files():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(files)")
    columns = [column[1] for column in cur.fetchall()]
    if "folder" not in columns:
        cur.execute("ALTER TABLE files ADD COLUMN folder TEXT DEFAULT ''")

    cur.execute("PRAGMA table_info(folders)")
    folder_cols = [column[1] for column in cur.fetchall()]
    if "name" not in folder_cols:
        cur.execute("""
        CREATE TABLE folders (
            name TEXT PRIMARY KEY,
            created_at INTEGER
        )
        """)

    for f in UPLOAD_DIR.iterdir():
        if f.is_dir():
            continue
        if f.name == DB_PATH.name:
            continue
        if "_" not in f.name:
            continue
        file_id, name = f.name.split("_", 1)
        cur.execute("SELECT 1 FROM files WHERE id=?", (file_id,))
        if cur.fetchone():
            continue
        stat = f.stat()
        uploaded_at = int(stat.st_mtime)
        size = stat.st_size
        mime = mimetypes.guess_type(f.name)[0] or "application/octet-stream"
        cur.execute(
            "INSERT INTO files (id, filename, mime, size, uploaded_at, checksum) VALUES (?,?,?,?,?,?)",
            (file_id, name, mime, size, uploaded_at, None),
        )
    conn.commit()


try:
    init_db()
    migrate_existing_files()
except Exception as e:
    print("DB init/migration error:", e)


# --------------------------------------------------
# ROOT ROUTE (HOST-BASED)
# --------------------------------------------------
@app.get("/", response_class=HTMLResponse)
def root(request: Request):
    host = request.headers.get("host", "")

    if host == "writesomething.fun" or host.startswith("writesomething.fun"):
        landing = STATIC_DIR / "landing.html"
        if landing.exists():
            return landing.read_text(encoding="utf-8")
        return HTMLResponse("<h1>Landing page missing</h1>", status_code=500)

    index = STATIC_DIR / "index.html"
    if index.exists():
        return index.read_text(encoding="utf-8")

    return HTMLResponse("<h1>UI missing</h1>", status_code=500)


# --------------------------------------------------
# FOLDER MANAGEMENT API
# --------------------------------------------------
@app.get("/api/folders")
def get_folders():
    conn = get_db()
    cur = conn.cursor()
    # Get folders from both files and explicit folders table
    cur.execute(
        "SELECT DISTINCT folder FROM files WHERE folder != '' AND is_deleted = 0"
    )
    file_folders = [row[0] for row in cur.fetchall() if row[0]]

    cur.execute("SELECT name FROM folders ORDER BY name")
    explicit_folders = [row[0] for row in cur.fetchall()]

    # Merge and dedupe
    all_folders = list(set(file_folders + explicit_folders))
    all_folders.sort()
    return {"folders": all_folders}


@app.post("/api/folders")
def create_folder(folder_data: dict):
    folder_name = folder_data.get("name", "").strip()
    if not folder_name:
        raise HTTPException(status_code=400, detail="Folder name is required")

    # Validate folder name
    if "/" in folder_name or "\\" in folder_name:
        raise HTTPException(status_code=400, detail="Invalid folder name")

    # Create folder directory
    folder_path = UPLOAD_DIR / folder_name
    folder_path.mkdir(exist_ok=True)

    # Store in database
    conn = get_db()
    conn.execute(
        "INSERT OR IGNORE INTO folders (name, created_at) VALUES (?, ?)",
        (folder_name, int(time.time())),
    )
    conn.commit()

    return {
        "message": "Folder '" + folder_name + "' created successfully",
        "name": folder_name,
    }


@app.delete("/api/folders/{folder_name}")
def delete_folder(folder_name: str):
    folder_name = folder_name.strip()
    if not folder_name:
        raise HTTPException(status_code=400, detail="Folder name required")

    folder_path = UPLOAD_DIR / folder_name

    # Check if folder exists on disk
    if not folder_path.exists():
        raise HTTPException(status_code=404, detail="Folder not found")

    # Check if folder has files
    files_in_folder = list(folder_path.glob("*"))
    files_in_folder = [f for f in files_in_folder if f.name != "thumbs"]

    if files_in_folder:
        raise HTTPException(status_code=400, detail="Folder is not empty")

    # Remove from database
    conn = get_db()
    conn.execute("DELETE FROM folders WHERE name = ?", (folder_name,))
    conn.commit()

    # Remove directory
    folder_path.rmdir()

    return {"message": f"Folder '{folder_name}' deleted"}


# --------------------------------------------------
# PUBLIC FILE LIST (File Explorer UI)
# --------------------------------------------------
@app.get("/files", response_class=HTMLResponse)
def list_files(request: Request):
    current_folder = request.query_params.get("folder", "") or ""

    # Build breadcrumb
    if current_folder:
        parts = current_folder.split("/")
        breadcrumb = f'<a href="/files">📂 Root</a>'
        path_so_far = ""
        for i, part in enumerate(parts):
            path_so_far += part if i == 0 else "/" + part
            breadcrumb += f' <span>/</span> <span class="current">{part}</span>'
    else:
        breadcrumb = '<span class="current">📁 All Files</span>'

    # Get files and folders
    file_rows = ""
    files_count = 0

    if current_folder:
        folder_path = UPLOAD_DIR / current_folder
        if folder_path.exists():
            for item in sorted(
                folder_path.iterdir(), key=os.path.getmtime, reverse=True
            ):
                if "_" not in item.name or item.name == "files.db":
                    continue
                file_id, name = item.name.split("_", 1)
                size_mb = item.stat().st_size / (1024 * 1024)
                mime = mimetypes.guess_type(name)[0] or ""

                # Icon based on type
                if mime.startswith("image/"):
                    icon = f'<img src="/file/{file_id}/thumb" class="file-thumb" onerror="this.style.display=\'none\';this.parentElement.innerHTML=📄">'
                elif mime.startswith("video/"):
                    icon = "🎬"
                elif mime.startswith("audio/"):
                    icon = "🎵"
                elif mime.startswith("text/"):
                    icon = "📝"
                elif "pdf" in mime:
                    icon = "📕"
                elif "zip" in mime or "rar" in mime or "tar" in mime or "gz" in mime:
                    icon = "📦"
                else:
                    icon = "📄"

                file_rows += f"""
                <div class="file-row">
                  <div class="file-info">
                    <div class="file-icon">{icon}</div>
                    <span class="file-name">{name}</span>
                  </div>
                  <div class="file-size">{size_mb:.2f} MB</div>
                  <div class="file-actions">
                    <button class="file-action" onclick="window.open('/file/{file_id}', '_blank')" title="Download">⬇️</button>
                    <button class="file-action delete" onclick="deleteFile('{file_id}', '{name.replace("'", "\\'")}')" title="Delete">🗑️</button>
                  </div>
                </div>"""
                files_count += 1
    else:
        # Root folder - show folders first, then files
        folders = []
        files = []

        for item in sorted(UPLOAD_DIR.iterdir(), key=os.path.getmtime, reverse=True):
            if item.name == "files.db" or item.name == "thumbs":
                continue

            if item.is_dir():
                folder_files = [f for f in item.glob("*") if f.name != "thumbs"]
                folders.append((item.name, len(folder_files)))
            elif "_" in item.name:
                files.append(item)

        # Show folders
        for folder_name, count in sorted(folders):
            file_rows += f"""
            <div class="file-row folder" onclick="navigateToFolder('{folder_name}')">
              <div class="file-info">
                <div class="file-icon">📁</div>
                <span class="file-name">{folder_name}</span>
              </div>
              <div class="file-size">{count} item{"s" if count != 1 else ""}</div>
              <div class="file-actions">
                <button class="file-action delete" onclick="event.stopPropagation(); deleteFolder('{folder_name}')" title="Delete">🗑️</button>
              </div>
            </div>"""
            files_count += 1

        # Show files
        for item in files:
            file_id, name = item.name.split("_", 1)
            size_mb = item.stat().st_size / (1024 * 1024)
            mime = mimetypes.guess_type(name)[0] or ""

            if mime.startswith("image/"):
                icon = f'<img src="/file/{file_id}/thumb" class="file-thumb" onerror="this.style.display=\'none\';this.parentElement.innerHTML=📄">'
            elif mime.startswith("video/"):
                icon = "🎬"
            elif mime.startswith("audio/"):
                icon = "🎵"
            elif mime.startswith("text/"):
                icon = "📝"
            elif "pdf" in mime:
                icon = "📕"
            elif "zip" in mime or "rar" in mime or "tar" in mime or "gz" in mime:
                icon = "📦"
            else:
                icon = "📄"

            file_rows += f"""
            <div class="file-row">
              <div class="file-info">
                <div class="file-icon">{icon}</div>
                <span class="file-name">{name}</span>
              </div>
              <div class="file-size">{size_mb:.2f} MB</div>
              <div class="file-actions">
                <button class="file-action" onclick="window.open('/file/{file_id}', '_blank')" title="Download">⬇️</button>
                <button class="file-action delete" onclick="deleteFile('{file_id}', '{name.replace("'", "\\'")}')" title="Delete">🗑️</button>
              </div>
            </div>"""
            files_count += 1

    # Template
    template_path = STATIC_DIR / "files_template.html"
    template = template_path.read_text(encoding="utf-8")

    empty_state = ""
    if not file_rows:
        empty_state = '<div class="empty-state"><div class="empty-icon">📭</div><p>This folder is empty</p></div>'

    stats = f"<span>📁 {files_count} items</span>"

    html = (
        template.replace("BREADCRUMB", breadcrumb)
        .replace("FILE_ROWS", file_rows)
        .replace("EMPTY_STATE", empty_state)
        .replace("STAT_ITEMS", stats)
    )

    return HTMLResponse(html)


# --------------------------------------------------
# DELETE API
# --------------------------------------------------


@app.get("/api/files")
def api_list_files(
    page: int = 1,
    limit: int = 25,
    q: Optional[str] = None,
    folder: Optional[str] = None,
):
    if page < 1:
        page = 1
    if limit < 1 or limit > 100:
        limit = 25
    offset = (page - 1) * limit
    conn = get_db()
    cur = conn.cursor()

    base_query = "SELECT id, filename, mime, size, uploaded_at, folder FROM files WHERE is_deleted=0"
    count_query = "SELECT COUNT(*) FROM files WHERE is_deleted=0"
    params = []

    if folder is not None and folder != "":
        base_query += " AND folder = ?"
        count_query += " AND folder = ?"
        params.append(folder)

    if q:
        base_query += " AND filename LIKE ?"
        count_query += " AND filename LIKE ?"
        params.append("%" + q + "%")

    base_query += " ORDER BY uploaded_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    cur.execute(base_query, params)
    rows = cur.fetchall()

    cur2 = conn.execute(count_query, params[:-2])
    total = cur2.fetchone()[0]

    items = []
    for r in rows:
        items.append(
            {
                "id": r["id"],
                "filename": r["filename"],
                "mime": r["mime"],
                "size": r["size"],
                "uploaded_at": r["uploaded_at"],
                "folder": r["folder"] or "",
                "download_url": "/file/" + r["id"],
                "thumb_url": "/file/" + r["id"] + "/thumb"
                if (r["mime"] or "").startswith("image/")
                else None,
            }
        )
    return {"page": page, "limit": limit, "total": total, "items": items}


@app.get("/file/{file_id}/thumb")
def file_thumb(file_id: str):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "SELECT filename, mime, folder FROM files WHERE id=? AND is_deleted=0",
        (file_id,),
    )
    row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="File not found")
    mime = row["mime"] or ""
    if not mime.startswith("image/"):
        raise HTTPException(status_code=400, detail="Not an image")
    source_path = UPLOAD_DIR / (file_id + "_" + row["filename"])
    thumb_dir = UPLOAD_DIR / "thumbs"
    thumb_dir.mkdir(parents=True, exist_ok=True)
    thumb_path = thumb_dir / (file_id + ".jpg")
    if not thumb_path.exists():
        try:
            from PIL import Image

            with Image.open(source_path) as im:
                im.thumbnail((300, 300))
                if im.mode in ("RGBA", "LA"):
                    background = Image.new("RGB", im.size, (255, 255, 255))
                    background.paste(im, mask=im.split()[-1])
                    background.save(thumb_path, "JPEG", quality=85)
                else:
                    im.convert("RGB").save(thumb_path, "JPEG", quality=85)
        except Exception as e:
            raise HTTPException(
                status_code=500, detail="Thumbnail generation failed: " + str(e)
            )
    return FileResponse(thumb_path, media_type="image/jpeg", filename=file_id + ".jpg")


@app.delete("/file/{file_id}")
def delete_file(file_id: str, request: Request):
    current_folder = request.query_params.get("folder", "") or ""

    # Search in current folder first, then root
    if current_folder:
        folder_path = UPLOAD_DIR / current_folder
        matches = list(folder_path.glob(file_id + "_*"))
    else:
        matches = list(UPLOAD_DIR.glob(file_id + "_*"))
        # Also check subdirectories
        if not matches:
            for subdir in UPLOAD_DIR.iterdir():
                if subdir.is_dir() and subdir.name != "thumbs":
                    matches = list(subdir.glob(file_id + "_*"))
                    if matches:
                        break

    if not matches:
        raise HTTPException(status_code=404, detail="File not found")

    file_path = matches[0]

    try:
        os.remove(file_path)
        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            "UPDATE files SET is_deleted=1, deleted_at=? WHERE id=?",
            (int(time.time()), file_id),
        )
        conn.commit()
        return {"message": "File deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error deleting file: " + str(e))


# --------------------------------------------------
# UPLOAD API (FAST) with folder support
# --------------------------------------------------
@app.post("/upload")
async def upload_file(file: UploadFile = File(...), folder: str = Form(default="")):
    print(f"Received upload request - filename: {file.filename}, folder: '{folder}'")
    file_id = str(uuid.uuid4())
    safe_name = file.filename.replace("/", "_").replace("\\", "_")

    folder = folder.strip() if folder else ""

    if folder:
        folder_path = UPLOAD_DIR / folder
        folder_path.mkdir(exist_ok=True)
        file_path = folder_path / (file_id + "_" + safe_name)
    else:
        file_path = UPLOAD_DIR / (file_id + "_" + safe_name)

    BUFFER_SIZE = 1024 * 1024
    hasher = hashlib.sha256()
    total = 0

    with open(file_path, "wb") as f:
        while True:
            chunk = await file.read(BUFFER_SIZE)
            if not chunk:
                break
            f.write(chunk)
            try:
                hasher.update(chunk)
            except Exception:
                pass
            total += len(chunk)

    checksum = hasher.hexdigest()
    mime = (
        file.content_type
        or mimetypes.guess_type(safe_name)[0]
        or "application/octet-stream"
    )
    uploaded_at = int(time.time())

    try:
        conn = get_db()
        conn.execute(
            "INSERT OR REPLACE INTO files (id, filename, mime, size, uploaded_at, checksum, folder) VALUES (?,?,?,?,?,?,?)",
            (file_id, safe_name, mime, total, uploaded_at, checksum, folder),
        )

        # Also ensure folder is tracked
        if folder:
            conn.execute(
                "INSERT OR IGNORE INTO folders (name, created_at) VALUES (?, ?)",
                (folder, int(time.time())),
            )

        conn.commit()
    except Exception as e:
        print("DB insert error:", e)

    try:
        if mime.startswith("image/"):
            from threading import Thread

            thumb_dir = UPLOAD_DIR / "thumbs"
            thumb_dir.mkdir(parents=True, exist_ok=True)
            thumb_path = thumb_dir / (file_id + ".jpg")
            Thread(
                target=generate_thumbnail, args=(file_path, thumb_path), daemon=True
            ).start()
    except Exception as e:
        print("Thumbnail background start error:", e)

    return {
        "filename": safe_name,
        "download_url": "/file/" + file_id,
        "files_url": "/files",
        "id": file_id,
        "folder": folder,
    }


# --------------------------------------------------
# DOWNLOAD API
# --------------------------------------------------
@app.get("/file/{file_id}")
def download_file(file_id: str):
    matches = list(UPLOAD_DIR.glob(file_id + "_*"))
    if not matches:
        for subdir in UPLOAD_DIR.iterdir():
            if subdir.is_dir() and subdir.name != "thumbs":
                matches = list(subdir.glob(file_id + "_*"))
                if matches:
                    break

    if not matches:
        raise HTTPException(status_code=404, detail="File not found")

    file_path = matches[0]
    original_name = file_path.name.split("_", 1)[1]

    return FileResponse(
        file_path, filename=original_name, media_type="application/octet-stream"
    )


# --------------------------------------------------
# PASTE API
# --------------------------------------------------
@app.get("/api/pastes")
def list_pastes(limit: int = 50):
    if limit < 1 or limit > 100:
        limit = 50
    conn = get_db()
    cur = conn.cursor()
    now = int(time.time())
    cur.execute(
        "SELECT id, title, language, views, created_at FROM pastes WHERE (expires_at IS NULL OR expires_at > ?) ORDER BY created_at DESC LIMIT ?",
        (now, limit),
    )
    rows = cur.fetchall()
    return {
        "pastes": [
            {
                "id": r[0],
                "title": r[1] or "Untitled",
                "language": r[2],
                "views": r[3],
                "created_at": r[4],
                "created_date": time.strftime("%b %d, %Y", time.localtime(r[4]))
                if r[4]
                else "",
            }
            for r in rows
        ]
    }


@app.post("/api/pastes")
def create_paste(request: Request, paste_data: dict):
    content = paste_data.get("content", "").strip()
    if not content:
        raise HTTPException(status_code=400, detail="Content is required")

    if len(content) > 500000:
        raise HTTPException(status_code=400, detail="Content too large (max 500KB)")

    title = paste_data.get("title", "").strip()[:200] or None
    language = paste_data.get("language", "plaintext").strip()[:50] or "plaintext"
    password = paste_data.get("password", "").strip()
    expires_in = paste_data.get("expires_in", 0)

    paste_id = str(uuid.uuid4())[:8]
    ip_address = request.client.host if request.client else None

    password_hash = None
    if password:
        password_hash = hashlib.sha256(password.encode()).hexdigest()

    expires_at = None
    if expires_in > 0:
        expires_at = int(time.time()) + expires_in

    conn = get_db()
    conn.execute(
        "INSERT INTO pastes (id, title, content, language, password_hash, expires_at, views, created_at, ip_address) VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?)",
        (
            paste_id,
            title,
            content,
            language,
            password_hash,
            expires_at,
            int(time.time()),
            ip_address,
        ),
    )
    conn.commit()

    return {"id": paste_id, "url": "/p/" + paste_id}


@app.get("/api/pastes/{paste_id}")
def get_paste(paste_id: str):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, title, content, language, password_hash, expires_at, views, created_at FROM pastes WHERE id = ?",
        (paste_id,),
    )
    row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Paste not found")

    now = int(time.time())
    if row[5] and row[5] < now:
        conn.execute("DELETE FROM pastes WHERE id = ?", (paste_id,))
        conn.commit()
        raise HTTPException(status_code=404, detail="Paste expired")

    conn.execute("UPDATE pastes SET views = views + 1 WHERE id = ?", (paste_id,))
    conn.commit()

    return {
        "id": row[0],
        "title": row[1],
        "content": row[2],
        "language": row[3],
        "has_password": bool(row[4]),
        "views": row[7],
        "created_at": row[7],
    }


@app.get("/api/pastes/{paste_id}/verify")
def verify_paste_password(paste_id: str, password: str):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT password_hash, content FROM pastes WHERE id = ?", (paste_id,))
    row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Paste not found")

    if row[0] and row[0] != hashlib.sha256(password.encode()).hexdigest():
        raise HTTPException(status_code=401, detail="Wrong password")

    return {"content": row[1]}


@app.delete("/api/pastes/{paste_id}")
def delete_paste(paste_id: str):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM pastes WHERE id = ?", (paste_id,))
    if cur.rowcount == 0:
        raise HTTPException(status_code=404, detail="Paste not found")
    conn.commit()
    return {"message": "Paste deleted"}


@app.get("/p/{paste_id}", response_class=HTMLResponse)
def view_paste(paste_id: str):
    paste_html = STATIC_DIR / "paste_view.html"
    if paste_html.exists():
        return paste_html.read_text(encoding="utf-8")
    return HTMLResponse("<h1>Paste page not found</h1>", status_code=404)


@app.get("/paste", response_class=HTMLResponse)
def create_paste_page():
    paste_html = STATIC_DIR / "paste.html"
    if paste_html.exists():
        return paste_html.read_text(encoding="utf-8")
    return HTMLResponse("<h1>Paste page not found</h1>", status_code=404)


# --------------------------------------------------
# LINKS API
# --------------------------------------------------
@app.get("/api/links")
def list_links(q: Optional[str] = None, tag: Optional[str] = None):
    conn = get_db()
    cur = conn.cursor()

    query = "SELECT id, url, title, description, tags, clicks, created_at FROM links WHERE 1=1"
    params = []

    if q:
        query += " AND (title LIKE ? OR description LIKE ? OR url LIKE ?)"
        params.extend(["%" + q + "%", "%" + q + "%", "%" + q + "%"])

    if tag:
        query += " AND tags LIKE ?"
        params.append("%" + tag + "%")

    query += " ORDER BY created_at DESC"

    cur.execute(query, params)
    rows = cur.fetchall()

    all_tags = set()
    for r in rows:
        if r[4]:
            for t in r[4].split(","):
                if t.strip():
                    all_tags.add(t.strip())

    return {
        "links": [
            {
                "id": r[0],
                "url": r[1],
                "title": r[2] or r[1],
                "description": r[3] or "",
                "tags": r[4] or "",
                "clicks": r[5],
                "created_at": r[6],
                "created_date": time.strftime("%b %d, %Y", time.localtime(r[6]))
                if r[6]
                else "",
            }
            for r in rows
        ],
        "all_tags": sorted(all_tags),
    }


@app.post("/api/links")
def create_link(link_data: dict):
    url = link_data.get("url", "").strip()
    if not url:
        raise HTTPException(status_code=400, detail="URL is required")

    title = link_data.get("title", "").strip()[:200] or None
    description = link_data.get("description", "").strip()[:1000] or None
    tags = link_data.get("tags", "").strip()[:500] or ""

    link_id = str(uuid.uuid4())[:8]

    conn = get_db()
    conn.execute(
        "INSERT INTO links (id, url, title, description, tags, clicks, created_at) VALUES (?, ?, ?, ?, ?, 0, ?)",
        (link_id, url, title, description, tags, int(time.time())),
    )
    conn.commit()

    return {"id": link_id, "message": "Link saved"}


@app.get("/api/links/{link_id}")
def get_link(link_id: str):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, url, title, description, tags, clicks, created_at FROM links WHERE id = ?",
        (link_id,),
    )
    row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Link not found")
    return {
        "id": row[0],
        "url": row[1],
        "title": row[2] or row[1],
        "description": row[3] or "",
        "tags": row[4] or "",
        "clicks": row[5],
        "created_at": row[6],
    }


@app.put("/api/links/{link_id}")
def update_link(link_id: str, link_data: dict):
    url = link_data.get("url", "").strip()
    title = link_data.get("title", "").strip()[:200] or None
    description = link_data.get("description", "").strip()[:1000] or None
    tags = link_data.get("tags", "").strip()[:500] or ""

    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "UPDATE links SET url = ?, title = ?, description = ?, tags = ? WHERE id = ?",
        (url, title, description, tags, link_id),
    )
    if cur.rowcount == 0:
        raise HTTPException(status_code=404, detail="Link not found")
    conn.commit()
    return {"message": "Link updated"}


@app.delete("/api/links/{link_id}")
def delete_link(link_id: str):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM links WHERE id = ?", (link_id,))
    if cur.rowcount == 0:
        raise HTTPException(status_code=404, detail="Link not found")
    conn.commit()
    return {"message": "Link deleted"}


@app.post("/api/links/{link_id}/click")
def click_link(link_id: str):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE links SET clicks = clicks + 1 WHERE id = ?", (link_id,))
    if cur.rowcount == 0:
        raise HTTPException(status_code=404, detail="Link not found")
    conn.commit()
    cur.execute("SELECT url FROM links WHERE id = ?", (link_id,))
    row = cur.fetchone()
    return {"url": row[0]}


@app.get("/links", response_class=HTMLResponse)
def browse_links():
    links_html = STATIC_DIR / "links.html"
    if links_html.exists():
        return links_html.read_text(encoding="utf-8")
    return HTMLResponse("<h1>Links page not found</h1>", status_code=404)


# --------------------------------------------------
# SUGGESTIONS API
# --------------------------------------------------
@app.get("/api/suggestions")
def get_suggestions(sort: str = "newest", status: Optional[str] = None):
    conn = get_db()
    cur = conn.cursor()

    query = "SELECT id, title, description, author, upvotes, status, created_at FROM suggestions WHERE 1=1"
    params = []

    if status:
        query += " AND status = ?"
        params.append(status)

    if sort == "popular":
        query += " ORDER BY upvotes DESC, created_at DESC"
    else:
        query += " ORDER BY created_at DESC"

    cur.execute(query, params)
    rows = cur.fetchall()

    suggestions = []
    for r in rows:
        suggestions.append(
            {
                "id": r[0],
                "title": r[1],
                "description": r[2],
                "author": r[3],
                "upvotes": r[4],
                "status": r[5],
                "created_at": r[6],
                "created_date": time.strftime("%b %d, %Y", time.localtime(r[6]))
                if r[6]
                else "",
            }
        )

    return {"suggestions": suggestions, "total": len(suggestions)}


@app.post("/api/suggestions")
def create_suggestion(request: Request, suggestion: dict):
    title = suggestion.get("title", "").strip()
    description = suggestion.get("description", "").strip()
    author = suggestion.get("author", "").strip() or "Anonymous"

    if not title:
        raise HTTPException(status_code=400, detail="Title is required")

    if len(title) > 200:
        raise HTTPException(status_code=400, detail="Title too long (max 200 chars)")

    if len(description) > 2000:
        raise HTTPException(
            status_code=400, detail="Description too long (max 2000 chars)"
        )

    suggestion_id = str(uuid.uuid4())
    ip_address = request.client.host if request.client else None

    conn = get_db()
    conn.execute(
        "INSERT INTO suggestions (id, title, description, author, upvotes, status, created_at, ip_address) VALUES (?, ?, ?, ?, 0, 'pending', ?, ?)",
        (suggestion_id, title, description, author, int(time.time()), ip_address),
    )
    conn.commit()

    return {
        "id": suggestion_id,
        "message": "Suggestion submitted successfully",
        "title": title,
    }


@app.post("/api/suggestions/{suggestion_id}/upvote")
def upvote_suggestion(suggestion_id: str, request: Request):
    ip_address = request.client.host if request.client else None

    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT upvotes FROM suggestions WHERE id = ?", (suggestion_id,))
    row = cur.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Suggestion not found")

    cur.execute(
        "SELECT 1 FROM suggestion_upvotes WHERE suggestion_id = ? AND ip_address = ?",
        (suggestion_id, ip_address),
    )
    if cur.fetchone():
        raise HTTPException(status_code=400, detail="Already upvoted")

    new_upvotes = row[0] + 1
    conn.execute(
        "UPDATE suggestions SET upvotes = ? WHERE id = ?", (new_upvotes, suggestion_id)
    )
    conn.execute(
        "INSERT INTO suggestion_upvotes (suggestion_id, ip_address, created_at) VALUES (?, ?, ?)",
        (suggestion_id, ip_address, int(time.time())),
    )
    conn.commit()

    return {"upvotes": new_upvotes}


@app.put("/api/suggestions/{suggestion_id}/status")
def update_suggestion_status(suggestion_id: str, data: dict):
    status = data.get("status", "").strip()
    if status not in ["pending", "implemented", "rejected"]:
        raise HTTPException(status_code=400, detail="Invalid status")

    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "UPDATE suggestions SET status = ? WHERE id = ?", (status, suggestion_id)
    )
    if cur.rowcount == 0:
        raise HTTPException(status_code=404, detail="Suggestion not found")
    conn.commit()

    return {"message": "Status updated", "status": status}


@app.delete("/api/suggestions/{suggestion_id}")
def delete_suggestion(suggestion_id: str):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM suggestions WHERE id = ?", (suggestion_id,))
    if cur.rowcount == 0:
        raise HTTPException(status_code=404, detail="Suggestion not found")
    conn.commit()
    return {"message": "Suggestion deleted"}


# --------------------------------------------------
# SUGGESTIONS PAGE
# --------------------------------------------------
@app.get("/suggest", response_class=HTMLResponse)
def suggestions_page():
    suggest_html = STATIC_DIR / "suggestions.html"
    if suggest_html.exists():
        return suggest_html.read_text(encoding="utf-8")
    return HTMLResponse("<h1>Suggestions page not found</h1>", status_code=404)


def generate_thumbnail(source_path: Path, thumb_path: Path):
    try:
        from PIL import Image

        with Image.open(source_path) as im:
            im.thumbnail((300, 300))
            if im.mode in ("RGBA", "LA"):
                background = Image.new("RGB", im.size, (255, 255, 255))
                background.paste(im, mask=im.split()[-1])
                background.save(thumb_path, "JPEG", quality=85)
            else:
                im.convert("RGB").save(thumb_path, "JPEG", quality=85)
    except Exception as e:
        print("Thumbnail generation failed for " + str(source_path) + ": " + str(e))


def background_thumbnail_worker(poll_interval: int = 30):
    thumb_dir = UPLOAD_DIR / "thumbs"
    thumb_dir.mkdir(parents=True, exist_ok=True)
    while True:
        try:
            for f in UPLOAD_DIR.iterdir():
                if f.is_dir() or f.name == DB_PATH.name:
                    continue
                if "_" not in f.name:
                    continue
                file_id, name = f.name.split("_", 1)
                thumb = thumb_dir / (file_id + ".jpg")
                if thumb.exists():
                    continue
                mime = mimetypes.guess_type(name)[0] or ""
                if not mime.startswith("image/"):
                    continue
                source = UPLOAD_DIR / (file_id + "_" + name)
                if not source.exists():
                    continue
                generate_thumbnail(source, thumb)
        except Exception as e:
            print("Background thumbnail worker error:", e)
        time.sleep(poll_interval)


@app.on_event("startup")
def start_background_workers():
    from threading import Thread

    t = Thread(target=background_thumbnail_worker, daemon=True)
    t.start()


# --------------------------------------------------
# TINY CHAT ROOMS
# --------------------------------------------------
ADJECTIVES = [
    "Swift",
    "Lonely",
    "Cosmic",
    "Silent",
    "Fierce",
    "Gentle",
    "Mystic",
    "Wild",
    "Ancient",
    "Bold",
    "Calm",
    "Dark",
    "Electric",
    "Frozen",
    "Golden",
    "Hidden",
    "Infinite",
    "Jolly",
    "Keen",
    "Lunar",
    "Mighty",
    "Neon",
    "Old",
    "Purple",
    "Quiet",
    "Rapid",
    "Secret",
    "Tiny",
    "Ultra",
    "Vivid",
    "Wandering",
    "Xenial",
]
ANIMALS = [
    "Penguin",
    "Panda",
    "Tiger",
    "Eagle",
    "Fox",
    "Wolf",
    "Bear",
    "Owl",
    "Hawk",
    "Raven",
    "Falcon",
    "Lynx",
    "Otter",
    "Badger",
    "Crane",
    "Dolphin",
    "Elk",
    "Finch",
    "Gecko",
    "Heron",
    "Ibis",
    "Jaguar",
    "Koala",
    "Lemur",
    "Mink",
    "Newt",
    "Orca",
    "Parrot",
    "Quail",
    "Robin",
    "Salamander",
    "Tapir",
]
MAX_ROOM_USERS = 20
MAX_MESSAGES = 100


class Room:
    def __init__(self, room_id: str, topic: str = "", password: str = ""):
        self.id = room_id
        self.topic = topic
        self.password = password
        self.connections: Dict[str, WebSocket] = {}
        self.messages: list = []
        self.created_at = int(time.time())

    @property
    def user_count(self) -> int:
        return len(self.connections)


rooms: Dict[str, Room] = {}


def generate_nickname() -> str:
    adj = random.choice(ADJECTIVES)
    animal = random.choice(ANIMALS)
    return f"{adj} {animal}"


def generate_room_id() -> str:
    chars = string.ascii_lowercase + string.digits
    return "".join(random.choices(chars, k=6))


@app.get("/chat", response_class=HTMLResponse)
def chat_lobby():
    chat_html = STATIC_DIR / "chat.html"
    if chat_html.exists():
        return chat_html.read_text(encoding="utf-8")
    return HTMLResponse("<h1>Chat page not found</h1>", status_code=404)


@app.get("/chat/{room_id}", response_class=HTMLResponse)
def chat_room(room_id: str):
    chat_html = STATIC_DIR / "chat.html"
    if chat_html.exists():
        return chat_html.read_text(encoding="utf-8")
    return HTMLResponse("<h1>Chat page not found</h1>", status_code=404)


@app.get("/api/chat/room/{room_id}")
def get_room_info(room_id: str):
    if room_id not in rooms:
        return {"exists": False, "user_count": 0, "topic": "", "full": False}
    room = rooms[room_id]
    return {
        "exists": True,
        "user_count": room.user_count,
        "topic": room.topic,
        "full": room.user_count >= MAX_ROOM_USERS,
    }


@app.websocket("/ws/{room_id}")
async def websocket_chat(websocket: WebSocket, room_id: str):
    room_id = room_id.strip().lower()

    if room_id not in rooms:
        rooms[room_id] = Room(room_id)

    room = rooms[room_id]

    if room.user_count >= MAX_ROOM_USERS:
        await websocket.close(code=4001, reason="Room is full")
        return

    nickname = generate_nickname()
    client_id = str(uuid.uuid4())

    room.connections[client_id] = websocket

    await websocket.accept()

    join_msg = {
        "type": "system",
        "text": f"{nickname} joined the room",
        "time": int(time.time()),
        "nickname": nickname,
    }
    room.messages.append(join_msg)
    if len(room.messages) > MAX_MESSAGES:
        room.messages = room.messages[-MAX_MESSAGES:]

    for cid, conn in list(room.connections.items()):
        if cid != client_id:
            try:
                await conn.send_json(join_msg)
            except Exception:
                pass

    await websocket.send_json(
        {
            "type": "init",
            "nickname": nickname,
            "client_id": client_id,
            "messages": room.messages[-50:],
            "user_count": room.user_count,
        }
    )

    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type", "message")

            if msg_type == "message":
                text = data.get("text", "").strip()
                if not text or len(text) > 1000:
                    continue

                msg = {
                    "type": "message",
                    "text": text,
                    "nickname": nickname,
                    "client_id": client_id,
                    "time": int(time.time()),
                }
                room.messages.append(msg)
                if len(room.messages) > MAX_MESSAGES:
                    room.messages = room.messages[-MAX_MESSAGES:]

                for cid, conn in list(room.connections.items()):
                    try:
                        await conn.send_json(msg)
                    except Exception:
                        pass

            elif msg_type == "ping":
                await websocket.send_json({"type": "pong"})

            elif msg_type == "set_nickname":
                new_name = data.get("name", "").strip()[:30]
                if new_name:
                    old_name = nickname
                    nickname = new_name
                    update_msg = {
                        "type": "system",
                        "text": f"{old_name} is now {nickname}",
                        "time": int(time.time()),
                        "nickname": nickname,
                    }
                    room.messages.append(update_msg)
                    for cid, conn in list(room.connections.items()):
                        try:
                            await conn.send_json(update_msg)
                        except Exception:
                            pass

    except WebSocketDisconnect:
        pass
    finally:
        if client_id in room.connections:
            del room.connections[client_id]

        leave_msg = {
            "type": "system",
            "text": f"{nickname} left the room",
            "time": int(time.time()),
            "nickname": nickname,
        }
        for cid, conn in list(room.connections.items()):
            try:
                await conn.send_json(leave_msg)
                await conn.send_json(
                    {"type": "user_count", "user_count": room.user_count}
                )
            except Exception:
                pass

        if room.user_count == 0:
            del rooms[room_id]
