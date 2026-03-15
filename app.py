"""Server web nativo (FastAPI) per YouTube Downloader con UI custom HTML/CSS/JS."""

from __future__ import annotations

import locale
import os
import re
import shutil
import threading
import time
import uuid
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal
from urllib.parse import quote

from fastapi import FastAPI, Request, Response
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from downloader import DownloadError, download_mp3, download_mp4, get_video_info, validate_url


BASE_DIR = Path(__file__).resolve().parent
DOWNLOAD_ROOT = BASE_DIR / "downloads"
DOWNLOAD_ARCHIVE_DIR = DOWNLOAD_ROOT / "all_youtube_downloads"
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

SESSION_COOKIE_NAME = "yt_session_id"
SESSION_COOKIE_MAX_AGE = 60 * 60 * 24 * 30  # 30 giorni
SESSION_COOKIE_PATTERN = re.compile(r"^[a-f0-9]{32}$")

MAX_PARALLEL_DOWNLOADS = int(os.getenv("YT_DL_MAX_WORKERS", "8"))


TRANSLATIONS: dict[str, dict[str, str]] = {
    "it": {
        "app_title": "YouTube Downloader",
        "hero_title": "Scarica da YouTube in modo rapido",
        "hero_subtitle": "Incolla un link, verifica l'anteprima e scarica in MP3 o MP4.",
        "url_label": "URL video YouTube",
        "url_placeholder": "https://www.youtube.com/watch?v=...",
        "format_label": "Formato",
        "format_mp3": "MP3 Audio",
        "format_mp4": "MP4 Video",
        "download_button": "Scarica",
        "bottom_bar_label": "Azione rapida",
        "preview_title": "Anteprima",
        "downloads_title": "Download della sessione",
        "no_downloads": "Nessun download in questa sessione.",
        "no_files": "Nessun file locale nella sessione.",
        "session_files": "File locali sessione",
        "status_queued": "In coda",
        "status_downloading": "Download in corso",
        "status_finished": "Completato",
        "status_error": "Errore",
        "loading_preview": "Recupero anteprima...",
        "invalid_url": "URL non valido. Inserisci un link YouTube corretto.",
        "preview_error": "Impossibile recuperare l'anteprima.",
        "download_started": "Download avviato.",
        "download_failed": "Download fallito.",
        "download_ready": "File pronto",
        "channel": "Canale",
        "duration": "Durata",
        "views": "Visualizzazioni",
        "live_warning": "Live stream rilevato: il download potrebbe non essere disponibile.",
        "copyright_note": "Usa l'app nel rispetto di copyright, ToS YouTube e normativa locale.",
        "unknown": "N/D",
    },
    "en": {
        "app_title": "YouTube Downloader",
        "hero_title": "Download from YouTube quickly",
        "hero_subtitle": "Paste a link, check preview, then download MP3 or MP4.",
        "url_label": "YouTube video URL",
        "url_placeholder": "https://www.youtube.com/watch?v=...",
        "format_label": "Format",
        "format_mp3": "MP3 Audio",
        "format_mp4": "MP4 Video",
        "download_button": "Download",
        "bottom_bar_label": "Quick action",
        "preview_title": "Preview",
        "downloads_title": "Session downloads",
        "no_downloads": "No downloads in this session.",
        "no_files": "No local files in this session.",
        "session_files": "Local session files",
        "status_queued": "Queued",
        "status_downloading": "Downloading",
        "status_finished": "Completed",
        "status_error": "Error",
        "loading_preview": "Loading preview...",
        "invalid_url": "Invalid URL. Please enter a valid YouTube link.",
        "preview_error": "Unable to load preview.",
        "download_started": "Download started.",
        "download_failed": "Download failed.",
        "download_ready": "File ready",
        "channel": "Channel",
        "duration": "Duration",
        "views": "Views",
        "live_warning": "Live stream detected: download may not be available.",
        "copyright_note": "Use responsibly and respect copyright and YouTube terms.",
        "unknown": "N/A",
    },
}


@dataclass
class SessionMeta:
    """Metadati base associati a una sessione utente."""

    session_id: str
    language: str
    created_at: float = field(default_factory=time.time)


@dataclass
class DownloadJob:
    """Stato di un download asincrono avviato da una sessione utente."""

    job_id: str
    session_id: str
    url: str
    output_format: Literal["mp3", "mp4"]
    language: str
    status: Literal["queued", "downloading", "finished", "error"] = "queued"
    progress: float = 0.0
    downloaded: int = 0
    total: int = 0
    speed: float = 0.0
    eta: float = 0.0
    file_path: str = ""
    file_name: str = ""
    error: str = ""
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


class DownloadRequest(BaseModel):
    """Payload API per avvio download."""

    url: str
    format: Literal["mp3", "mp4"]


class SessionContext(BaseModel):
    """Contesto risolto per la sessione corrente."""

    session_id: str
    language: str
    is_new_cookie: bool


app = FastAPI(title="YT Downloader", version="2.0.0")
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

DOWNLOAD_ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)


_store_lock = threading.RLock()
_executor = ThreadPoolExecutor(max_workers=MAX_PARALLEL_DOWNLOADS, thread_name_prefix="yt-download")
_sessions: dict[str, SessionMeta] = {}
_jobs: dict[str, DownloadJob] = {}
_session_jobs: dict[str, list[str]] = defaultdict(list)


def _t(language: str, key: str) -> str:
    """Restituisce traduzione per chiave/lingua con fallback inglese."""
    return TRANSLATIONS.get(language, TRANSLATIONS["en"]).get(key, key)


def _detect_system_language() -> str:
    """Rileva lingua OS come fallback quando header browser non disponibile."""
    lang_code = ""
    try:
        locale_value = locale.getlocale()[0]
        if locale_value:
            lang_code = locale_value.split("_")[0].lower()
    except Exception:
        lang_code = ""

    if lang_code in TRANSLATIONS:
        return lang_code
    return "en"


def _detect_language_from_request(request: Request) -> str:
    """Rileva lingua da browser (Accept-Language), fallback a lingua OS."""
    header = request.headers.get("accept-language", "")
    if header:
        for token in header.split(","):
            code = token.split(";")[0].strip().lower()
            if not code:
                continue
            base_code = code.split("-")[0]
            if base_code in TRANSLATIONS:
                return base_code
    return _detect_system_language()


def _session_download_dir(session_id: str) -> Path:
    """Restituisce la directory locale dedicata alla sessione utente."""
    session_dir = DOWNLOAD_ROOT / session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    return session_dir


def _archive_download(file_path: Path, job: DownloadJob) -> Path | None:
    """Duplica il file completato in una cartella archivio comune."""
    try:
        DOWNLOAD_ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        safe_name = file_path.name.replace("/", "_")
        archive_name = f"{timestamp}_{job.session_id}_{job.job_id[:8]}_{safe_name}"
        destination = DOWNLOAD_ARCHIVE_DIR / archive_name
        shutil.copy2(file_path, destination)
        return destination
    except Exception:
        return None


def _get_or_create_session(request: Request) -> SessionContext:
    """Recupera o crea sessione tramite cookie HTTP-only."""
    raw_cookie = request.cookies.get(SESSION_COOKIE_NAME, "")
    valid_cookie = bool(SESSION_COOKIE_PATTERN.match(raw_cookie))

    session_id = raw_cookie if valid_cookie else uuid.uuid4().hex
    is_new_cookie = not valid_cookie

    with _store_lock:
        if session_id not in _sessions:
            language = _detect_language_from_request(request)
            _sessions[session_id] = SessionMeta(session_id=session_id, language=language)
        else:
            language = _sessions[session_id].language

    _session_download_dir(session_id)

    return SessionContext(session_id=session_id, language=language, is_new_cookie=is_new_cookie)


def _apply_session_cookie(response: Response, context: SessionContext) -> None:
    """Applica cookie sessione al client quando necessario."""
    if not context.is_new_cookie:
        return

    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=context.session_id,
        max_age=SESSION_COOKIE_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=False,
        path="/",
    )


def _update_job(job_id: str, **kwargs: Any) -> None:
    """Aggiorna in modo thread-safe lo stato di un job."""
    with _store_lock:
        job = _jobs.get(job_id)
        if not job:
            return

        for key, value in kwargs.items():
            setattr(job, key, value)
        job.updated_at = time.time()


def _progress_callback_factory(job_id: str):
    """Crea callback progresso per propagare stato da yt-dlp al job."""

    def _callback(payload: dict[str, Any]) -> None:
        status = payload.get("status")
        if status == "downloading":
            _update_job(
                job_id,
                status="downloading",
                progress=float(payload.get("percentage", 0.0)),
                downloaded=int(payload.get("downloaded", 0)),
                total=int(payload.get("total", 0)),
                speed=float(payload.get("speed") or 0.0),
                eta=float(payload.get("eta") or 0.0),
            )
        elif status == "finished":
            _update_job(job_id, progress=100.0)

    return _callback


def _execute_download(job_id: str) -> None:
    """Esegue il download in thread separato, isolato per sessione utente."""
    with _store_lock:
        job = _jobs.get(job_id)
        if not job:
            return
        session_id = job.session_id
        url = job.url
        output_format = job.output_format

    _update_job(job_id, status="downloading", progress=0.0, error="")

    output_dir = _session_download_dir(session_id)
    progress_cb = _progress_callback_factory(job_id)

    try:
        if output_format == "mp3":
            file_path = download_mp3(url, output_dir=str(output_dir), progress_callback=progress_cb)
        else:
            file_path = download_mp4(url, output_dir=str(output_dir), progress_callback=progress_cb)

        resolved_path = Path(file_path).resolve()
        _archive_download(resolved_path, job)
        _update_job(
            job_id,
            status="finished",
            progress=100.0,
            file_path=str(resolved_path),
            file_name=resolved_path.name,
            error="",
        )
    except DownloadError as exc:
        _update_job(job_id, status="error", error=str(exc))
    except Exception as exc:
        _update_job(job_id, status="error", error=str(exc))


def _serialize_job(job: DownloadJob) -> dict[str, Any]:
    """Serializza job per API JSON."""
    return {
        "id": job.job_id,
        "url": job.url,
        "format": job.output_format,
        "status": job.status,
        "progress": round(job.progress, 2),
        "downloaded": job.downloaded,
        "total": job.total,
        "speed": job.speed,
        "eta": job.eta,
        "file_name": job.file_name,
        "error": job.error,
        "created_at": job.created_at,
        "updated_at": job.updated_at,
    }


def _list_session_files(session_id: str) -> list[dict[str, Any]]:
    """Restituisce file locali presenti nella directory dedicata alla sessione."""
    session_dir = _session_download_dir(session_id)
    files: list[dict[str, Any]] = []

    for entry in session_dir.iterdir():
        if not entry.is_file():
            continue
        files.append(
            {
                "name": entry.name,
                "size": entry.stat().st_size,
                "modified": entry.stat().st_mtime,
                "url": f"/api/files/{quote(entry.name)}",
            }
        )

    files.sort(key=lambda item: item["modified"], reverse=True)
    return files


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    """Render pagina principale con lingua e sessione risolte."""
    session = _get_or_create_session(request)
    translations = TRANSLATIONS.get(session.language, TRANSLATIONS["en"])

    response = templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "lang": session.language,
            "texts": translations,
            "config": {
                "pollIntervalMs": 1500,
                "maxParallelDownloads": MAX_PARALLEL_DOWNLOADS,
            },
        },
    )
    _apply_session_cookie(response, session)
    return response


@app.get("/api/preview")
async def api_preview(request: Request, response: Response, url: str) -> Any:
    """Restituisce anteprima video se URL valido."""
    session = _get_or_create_session(request)
    _apply_session_cookie(response, session)

    if not validate_url(url):
        return {"ok": False, "error": _t(session.language, "invalid_url")}

    try:
        info = get_video_info(url)
        return {"ok": True, "info": info}
    except DownloadError as exc:
        return {"ok": False, "error": str(exc) or _t(session.language, "preview_error")}
    except Exception:
        return {"ok": False, "error": _t(session.language, "preview_error")}


@app.post("/api/download")
async def api_download(
    payload: DownloadRequest,
    request: Request,
    response: Response,
) -> dict[str, Any]:
    """Avvia un nuovo job download asincrono per la sessione corrente."""
    session = _get_or_create_session(request)
    _apply_session_cookie(response, session)

    if not validate_url(payload.url):
        return {"ok": False, "error": _t(session.language, "invalid_url")}

    job_id = uuid.uuid4().hex
    job = DownloadJob(
        job_id=job_id,
        session_id=session.session_id,
        url=payload.url,
        output_format=payload.format,
        language=session.language,
    )

    with _store_lock:
        _jobs[job_id] = job
        _session_jobs[session.session_id].append(job_id)

    _executor.submit(_execute_download, job_id)

    return {"ok": True, "job_id": job_id, "message": _t(session.language, "download_started")}


@app.get("/api/downloads")
async def api_downloads(request: Request, response: Response) -> dict[str, Any]:
    """Lista job e file locali visibili per la sessione corrente."""
    session = _get_or_create_session(request)
    _apply_session_cookie(response, session)

    with _store_lock:
        job_ids = list(_session_jobs.get(session.session_id, []))
        jobs_payload = [_serialize_job(_jobs[job_id]) for job_id in job_ids if job_id in _jobs]

    jobs_payload.sort(key=lambda item: item["created_at"], reverse=True)

    return {
        "ok": True,
        "jobs": jobs_payload,
        "files": _list_session_files(session.session_id),
    }


@app.get("/api/downloads/{job_id}/file")
async def api_download_file(job_id: str, request: Request, response: Response) -> Any:
    """Scarica il file associato a un job completato della sessione corrente."""
    session = _get_or_create_session(request)
    _apply_session_cookie(response, session)

    with _store_lock:
        job = _jobs.get(job_id)
        if not job or job.session_id != session.session_id:
            return JSONResponse({"ok": False, "error": "Not found"}, status_code=404)

        file_path = Path(job.file_path)

    if not file_path.exists() or not file_path.is_file():
        return JSONResponse({"ok": False, "error": "File not found"}, status_code=404)

    return FileResponse(path=str(file_path), filename=job.file_name or file_path.name)


@app.get("/api/files/{file_name}")
async def api_download_session_file(
    file_name: str,
    request: Request,
    response: Response,
) -> Any:
    """Scarica file diretto dalla directory della sessione corrente."""
    session = _get_or_create_session(request)
    _apply_session_cookie(response, session)

    safe_name = Path(file_name).name
    target = _session_download_dir(session.session_id) / safe_name

    if not target.exists() or not target.is_file():
        return JSONResponse({"ok": False, "error": "File not found"}, status_code=404)

    return FileResponse(path=str(target), filename=safe_name)


@app.on_event("shutdown")
def on_shutdown() -> None:
    """Rilascia thread pool su stop applicazione."""
    _executor.shutdown(wait=False, cancel_futures=False)
