"""
Modulo per il download di video/audio da YouTube utilizzando yt-dlp.
Supporta formati MP3 (audio) e MP4 (video).
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from typing import Any, Callable, Optional
from urllib.parse import parse_qs, urlparse

from yt_dlp import YoutubeDL


class DownloadError(Exception):
    """Eccezione personalizzata per errori di download."""


TEMPORARY_DOWNLOAD_SUFFIXES = (".part", ".ytdl", ".tmp")
ANSI_ESCAPE_RE = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")


def _configure_js_runtime(ydl: YoutubeDL) -> None:
    """
    Configura il runtime JavaScript per yt-dlp.
    Aggiunge Node.js manualmente se trovato nel sistema.
    """
    node_path = shutil.which("node")
    if not node_path:
        return

    try:
        from yt_dlp.utils._jsruntime import NodeJsRuntime

        # Attributo interno di yt-dlp: può non esistere in alcune versioni.
        ydl._js_runtimes["node"] = NodeJsRuntime(node_path)  # type: ignore[attr-defined]
    except Exception:
        # Non interrompe il download se la configurazione del runtime fallisce.
        pass


def _get_yt_dlp_opts(base_opts: dict[str, Any]) -> dict[str, Any]:
    """
    Aggiunge configurazione opzionale per componenti remoti utili al challenge solving.
    """
    opts = base_opts.copy()
    opts["remote_components"] = ["ejs:github"]
    opts["noplaylist"] = True

    # Supporto opzionale cookie per superare challenge anti-bot di YouTube.
    cookie_file = os.getenv("YT_COOKIES_FILE", "").strip()
    if cookie_file:
        opts["cookiefile"] = cookie_file

    cookie_browser = os.getenv("YT_COOKIES_BROWSER", "").strip().lower()
    if cookie_browser:
        opts["cookiesfrombrowser"] = (cookie_browser, None, None, None)

    return opts


def _sanitize_error_message(raw_message: str) -> str:
    """Rimuove codici ANSI e normalizza il testo errore da librerie esterne."""
    no_ansi = ANSI_ESCAPE_RE.sub("", raw_message or "")
    return " ".join(no_ansi.split())


def _is_video_id(candidate: str) -> bool:
    """Valida la forma minima dell'ID video YouTube (11 caratteri)."""
    if not candidate:
        return False
    return len(candidate) == 11 and all(ch.isalnum() or ch in "-_" for ch in candidate)


def _extract_video_id(url: str) -> Optional[str]:
    """Estrae l'ID video da URL YouTube supportati."""
    normalized = url.strip()
    if not normalized:
        return None

    if not normalized.startswith(("http://", "https://")):
        normalized = f"https://{normalized}"

    try:
        parsed = urlparse(normalized)
    except ValueError:
        return None

    host = parsed.netloc.lower()
    path_parts = [part for part in parsed.path.split("/") if part]

    if "youtu.be" in host:
        if not path_parts:
            return None
        return path_parts[0]

    if "youtube" not in host and "youtube-nocookie" not in host:
        return None

    query_video_id = parse_qs(parsed.query).get("v", [""])[0]
    if query_video_id:
        return query_video_id

    if not path_parts:
        return None

    if path_parts[0] in {"shorts", "embed", "live", "v"} and len(path_parts) > 1:
        return path_parts[1]

    return None


def normalize_youtube_url(url: str) -> str:
    """
    Normalizza URL YouTube condivisi in formato canonico watch?v=<id>.

    Questo elimina parametri di tracking (es. ?si=...) che possono comparire
    nei link short condivisi.
    """
    if not isinstance(url, str):
        return ""

    raw = url.strip()
    video_id = _extract_video_id(raw)
    if video_id and _is_video_id(video_id):
        return f"https://www.youtube.com/watch?v={video_id}"
    return raw


def validate_url(url: Optional[str]) -> bool:
    """
    Valida se l'URL è un URL YouTube valido.

    Args:
        url: L'URL da validare

    Returns:
        True se l'URL è valido, False altrimenti
    """
    if not isinstance(url, str):
        return False

    video_id = _extract_video_id(url)
    return bool(video_id and _is_video_id(video_id))


def _map_download_error(raw_error: Exception) -> str:
    """Converte gli errori tecnici in messaggi utente più chiari."""
    cleaned_message = _sanitize_error_message(str(raw_error))
    error_msg = cleaned_message.lower()

    if "not a bot" in error_msg or "cookies-from-browser" in error_msg:
        return (
            "YouTube richiede verifica anti-bot. Configura i cookie impostando "
            "YT_COOKIES_FILE (file cookie Netscape) o YT_COOKIES_BROWSER "
            "(es. chrome, firefox, safari)."
        )

    if "copyright" in error_msg or "blocked" in error_msg:
        return "Questo video è bloccato per restrizioni di copyright."
    if "age" in error_msg:
        return "Questo video ha una restrizione di età."
    if "private" in error_msg:
        return "Questo video è privato."
    if "not available" in error_msg or "unavailable" in error_msg:
        return "Video non disponibile o rimosso."
    if "ffmpeg" in error_msg:
        return "FFmpeg non è installato o non è configurato correttamente."
    if "failed to resolve" in error_msg or "name resolution" in error_msg:
        return "Errore di rete/DNS: impossibile raggiungere YouTube dal server."

    return f"Errore durante il download: {cleaned_message}"


def get_video_info(url: str) -> dict[str, Any]:
    """
    Recupera le informazioni del video senza scaricarlo.

    Args:
        url: L'URL del video YouTube

    Returns:
        Dizionario con le informazioni del video

    Raises:
        DownloadError: Se il video non è accessibile
    """
    normalized_url = normalize_youtube_url(url)

    if not validate_url(normalized_url):
        raise DownloadError("URL non valido. Inserisci un URL YouTube valido.")

    try:
        opts = _get_yt_dlp_opts({"quiet": True, "skip_download": True})
        with YoutubeDL(opts) as ydl:
            _configure_js_runtime(ydl)
            info = ydl.extract_info(normalized_url, download=False)

        return {
            "title": info.get("title", "Sconosciuto"),
            "duration": info.get("duration", 0),
            "uploader": info.get("uploader", "Sconosciuto"),
            "thumbnail": info.get("thumbnail", ""),
            "is_live": info.get("is_live", False),
            "view_count": info.get("view_count", 0),
        }
    except DownloadError:
        raise
    except Exception as exc:
        raise DownloadError(f"Impossibile recuperare le informazioni del video: {exc}") from exc


def _progress_hook(progress_callback: Optional[Callable[[dict[str, Any]], None]], data: dict[str, Any]) -> None:
    """
    Hook interno per il monitoraggio del progresso del download.

    Args:
        progress_callback: Funzione di callback per aggiornare il progresso
        data: Dizionario con le informazioni sullo stato del download
    """
    if progress_callback is None:
        return

    if data.get("status") == "downloading":
        downloaded = data.get("downloaded_bytes", 0)
        total = data.get("total_bytes") or data.get("total_bytes_estimate", 0)

        if total > 0:
            percentage = (downloaded / total) * 100
            speed = data.get("speed", 0)
            eta = data.get("eta", 0)
            progress_callback(
                {
                    "status": "downloading",
                    "percentage": percentage,
                    "downloaded": downloaded,
                    "total": total,
                    "speed": speed,
                    "eta": eta,
                }
            )

    elif data.get("status") == "finished":
        progress_callback({"status": "finished", "percentage": 100})


def _resolve_output_path(prepared_filename: str, expected_extension: str) -> str:
    """Restituisce il percorso finale del file prodotto da yt-dlp."""
    base_path, _ = os.path.splitext(prepared_filename)
    expected_path = f"{base_path}.{expected_extension}"

    if os.path.exists(expected_path):
        return expected_path

    if os.path.exists(prepared_filename):
        return prepared_filename

    directory = os.path.dirname(prepared_filename) or "."
    stem = os.path.basename(base_path)

    try:
        candidates: list[str] = []
        for entry in os.listdir(directory):
            if entry.startswith(stem):
                candidate = os.path.join(directory, entry)
                if os.path.isfile(candidate) and not candidate.endswith(TEMPORARY_DOWNLOAD_SUFFIXES):
                    candidates.append(candidate)

        if candidates:
            # Seleziona il file piu recente per evitare collisioni con download precedenti.
            candidates.sort(key=lambda item: os.path.getmtime(item), reverse=True)
            return candidates[0]
    except OSError:
        pass

    return expected_path


def _probe_media_duration(file_path: str) -> float:
    """Recupera la durata media del file usando ffprobe."""
    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        file_path,
    ]

    try:
        result = subprocess.run(command, check=False, capture_output=True, text=True)
    except OSError:
        return 0.0

    if result.returncode != 0:
        return 0.0

    output = (result.stdout or "").strip()
    try:
        return float(output)
    except ValueError:
        return 0.0


def verify_download_integrity(file_path: str, expected_duration: float | int) -> tuple[bool, str]:
    """Verifica che il file scaricato non sia troncato usando size e durata."""
    if not os.path.exists(file_path) or not os.path.isfile(file_path):
        return False, "File non trovato al termine del download."

    file_size = os.path.getsize(file_path)
    if file_size < 10 * 1024:
        return False, "File troppo piccolo: probabile download incompleto."

    try:
        expected_seconds = float(expected_duration)
    except (TypeError, ValueError):
        expected_seconds = 0.0

    if expected_seconds <= 0:
        return True, ""

    actual_seconds = _probe_media_duration(file_path)
    if actual_seconds <= 0:
        return False, "Impossibile misurare la durata del file con ffprobe."

    tolerance = max(2.5, expected_seconds * 0.08)
    if actual_seconds + tolerance < expected_seconds:
        return (
            False,
            (
                f"Durata file inferiore all'atteso (atteso {expected_seconds:.2f}s, "
                f"ottenuto {actual_seconds:.2f}s)."
            ),
        )

    return True, ""


def download_mp3(
    url: str,
    output_dir: str = "downloads",
    progress_callback: Optional[Callable[[dict[str, Any]], None]] = None,
) -> str:
    """
    Scarica l'audio di un video YouTube in formato MP3.

    Args:
        url: L'URL del video YouTube
        output_dir: Directory di output per il file scaricato
        progress_callback: Funzione opzionale per ricevere aggiornamenti sul progresso

    Returns:
        Percorso del file scaricato

    Raises:
        DownloadError: Se il download fallisce
    """
    normalized_url = normalize_youtube_url(url)

    if not validate_url(normalized_url):
        raise DownloadError("URL non valido. Inserisci un URL YouTube valido.")

    os.makedirs(output_dir, exist_ok=True)

    ydl_opts = _get_yt_dlp_opts(
        {
            "format": "bestaudio/best",
            "outtmpl": os.path.join(output_dir, "%(title)s.%(ext)s"),
            "quiet": True,
            "no_warnings": True,
            "retries": 10,
            "fragment_retries": 10,
            "continuedl": True,
            "skip_unavailable_fragments": False,
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }
            ],
            "progress_hooks": [lambda data: _progress_hook(progress_callback, data)],
        }
    )

    for attempt in range(2):
        try:
            with YoutubeDL(ydl_opts) as ydl:
                _configure_js_runtime(ydl)
                info = ydl.extract_info(normalized_url, download=True)
                prepared_filename = ydl.prepare_filename(info)
                downloaded_path = _resolve_output_path(prepared_filename, "mp3")
                expected_duration = info.get("duration", 0)

            is_valid, reason = verify_download_integrity(downloaded_path, expected_duration)
            if is_valid:
                return downloaded_path

            if attempt == 0:
                try:
                    os.remove(downloaded_path)
                except OSError:
                    pass
                continue

            raise DownloadError(f"Download MP3 incompleto: {reason}")
        except DownloadError:
            raise
        except Exception as exc:
            raise DownloadError(_map_download_error(exc)) from exc

    raise DownloadError("Download MP3 incompleto dopo piu tentativi.")


def download_mp4(
    url: str,
    output_dir: str = "downloads",
    progress_callback: Optional[Callable[[dict[str, Any]], None]] = None,
) -> str:
    """
    Scarica un video YouTube in formato MP4 (video + audio).

    Args:
        url: L'URL del video YouTube
        output_dir: Directory di output per il file scaricato
        progress_callback: Funzione opzionale per ricevere aggiornamenti sul progresso

    Returns:
        Percorso del file scaricato

    Raises:
        DownloadError: Se il download fallisce
    """
    normalized_url = normalize_youtube_url(url)

    if not validate_url(normalized_url):
        raise DownloadError("URL non valido. Inserisci un URL YouTube valido.")

    os.makedirs(output_dir, exist_ok=True)

    ydl_opts = _get_yt_dlp_opts(
        {
            "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "outtmpl": os.path.join(output_dir, "%(title)s.%(ext)s"),
            "quiet": True,
            "no_warnings": True,
            "retries": 10,
            "fragment_retries": 10,
            "continuedl": True,
            "skip_unavailable_fragments": False,
            "merge_output_format": "mp4",
            "progress_hooks": [lambda data: _progress_hook(progress_callback, data)],
        }
    )

    for attempt in range(2):
        try:
            with YoutubeDL(ydl_opts) as ydl:
                _configure_js_runtime(ydl)
                info = ydl.extract_info(normalized_url, download=True)
                prepared_filename = ydl.prepare_filename(info)
                downloaded_path = _resolve_output_path(prepared_filename, "mp4")
                expected_duration = info.get("duration", 0)

            is_valid, reason = verify_download_integrity(downloaded_path, expected_duration)
            if is_valid:
                return downloaded_path

            if attempt == 0:
                try:
                    os.remove(downloaded_path)
                except OSError:
                    pass
                continue

            raise DownloadError(f"Download MP4 incompleto: {reason}")
        except DownloadError:
            raise
        except Exception as exc:
            raise DownloadError(_map_download_error(exc)) from exc

    raise DownloadError("Download MP4 incompleto dopo piu tentativi.")


def cleanup_downloads(output_dir: str = "downloads") -> None:
    """
    Pulisce la cartella dei download rimuovendo tutti i file.

    Args:
        output_dir: Directory da pulire
    """
    if not os.path.exists(output_dir):
        return

    for filename in os.listdir(output_dir):
        file_path = os.path.join(output_dir, filename)
        try:
            if os.path.isfile(file_path):
                os.remove(file_path)
        except Exception:
            pass


def get_downloaded_files(output_dir: str = "downloads") -> list[dict[str, Any]]:
    """
    Restituisce la lista dei file scaricati nella directory.

    Args:
        output_dir: Directory da scansionare

    Returns:
        Lista dei metadati dei file
    """
    if not os.path.exists(output_dir):
        return []

    files: list[dict[str, Any]] = []
    for filename in os.listdir(output_dir):
        file_path = os.path.join(output_dir, filename)
        if os.path.isfile(file_path):
            files.append(
                {
                    "name": filename,
                    "path": file_path,
                    "size": os.path.getsize(file_path),
                    "modified": os.path.getmtime(file_path),
                }
            )

    return sorted(files, key=lambda item: item["modified"], reverse=True)
