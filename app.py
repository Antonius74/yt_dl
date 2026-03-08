"""
Interfaccia web Streamlit con Material Design e UX ispirata a YouTube.
"""

from __future__ import annotations

import html
import os
from datetime import datetime
from typing import Any

import streamlit as st

from downloader import (
    DownloadError,
    cleanup_downloads,
    download_mp3,
    download_mp4,
    get_downloaded_files,
    get_video_info,
    validate_url,
)


# Configurazione pagina principale.
st.set_page_config(
    page_title="YT Downloader",
    page_icon="▶️",
    layout="wide",
    initial_sidebar_state="collapsed",
)


APP_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&display=swap');

    :root {
        --bg: #0f0f0f;
        --surface: #1c1c1c;
        --surface-soft: #242424;
        --text: #f1f1f1;
        --muted: #a8a8a8;
        --accent: #ff0033;
        --accent-dark: #d1002a;
        --outline: rgba(255, 255, 255, 0.14);
        --ok-bg: rgba(46, 125, 50, 0.25);
        --ok-border: rgba(46, 125, 50, 0.45);
        --err-bg: rgba(198, 40, 40, 0.24);
        --err-border: rgba(198, 40, 40, 0.5);
    }

    * {
        font-family: 'Roboto', sans-serif !important;
    }

    #MainMenu,
    header,
    footer {
        visibility: hidden;
    }

    .stApp {
        background:
            radial-gradient(900px 400px at 8% -10%, rgba(255, 0, 51, 0.22), transparent 60%),
            radial-gradient(600px 280px at 92% -5%, rgba(255, 255, 255, 0.06), transparent 65%),
            var(--bg);
        color: var(--text);
    }

    .block-container {
        max-width: 980px;
        padding-top: 1.2rem;
        padding-bottom: 2.4rem;
    }

    .yt-topbar {
        position: sticky;
        top: 0;
        z-index: 9;
        background: transparent;
        backdrop-filter: none;
        border: none;
        border-radius: 18px;
        padding: 0;
        margin-bottom: 1rem;
        display: flex;
        align-items: center;
        justify-content: flex-start;
        gap: 1rem;
    }

    .yt-brand {
        display: flex;
        align-items: center;
        gap: 0.6rem;
        font-weight: 700;
        letter-spacing: 0.2px;
        color: var(--text);
    }

    .yt-logo {
        width: 40px;
        height: 28px;
        border-radius: 8px;
        background: var(--accent);
        display: inline-flex;
        align-items: center;
        justify-content: center;
        color: white;
        font-size: 14px;
        box-shadow: 0 8px 24px rgba(255, 0, 51, 0.35);
    }

    .yt-topbar .muted {
        color: var(--muted);
        font-size: 0.9rem;
    }

    .surface {
        background: transparent;
        border: none;
        border-radius: 24px;
        padding: 0;
        box-shadow: none;
        margin-bottom: 1.2rem;
    }

    .hero-title {
        font-size: clamp(1.4rem, 2.3vw, 2rem);
        font-weight: 700;
        margin: 0;
        color: var(--text);
    }

    .hero-subtitle {
        margin-top: 0.35rem;
        color: var(--muted);
        font-size: 0.98rem;
    }

    .chip-row {
        margin-top: 0.75rem;
        display: flex;
        flex-wrap: wrap;
        gap: 0.45rem;
    }

    .chip {
        background: rgba(255, 255, 255, 0.08);
        border: 1px solid rgba(255, 255, 255, 0.12);
        border-radius: 999px;
        padding: 0.35rem 0.65rem;
        font-size: 0.8rem;
        color: var(--text);
    }

    .preview-title {
        font-size: 1.2rem;
        margin: 0;
        line-height: 1.35;
    }

    .preview-meta {
        color: var(--muted);
        font-size: 0.9rem;
        margin-top: 0.35rem;
    }

    .status-msg {
        margin-top: 0.7rem;
        color: var(--muted);
        font-size: 0.92rem;
    }

    .alert-ok,
    .alert-error {
        border-radius: 16px;
        padding: 0.8rem 1rem;
        border: 1px solid;
        margin-bottom: 0.8rem;
        font-size: 0.95rem;
    }

    .alert-ok {
        background: var(--ok-bg);
        border-color: var(--ok-border);
    }

    .alert-error {
        background: var(--err-bg);
        border-color: var(--err-border);
    }

    .library-label {
        color: var(--muted);
        font-size: 0.86rem;
    }

    .library-name {
        color: var(--text);
        font-size: 0.95rem;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }

    .stTextInput label,
    .stRadio label,
    .stMarkdown,
    .stCaption,
    .stAlert {
        color: var(--text) !important;
    }

    .stTextInput input {
        background: transparent !important;
        border: none !important;
        border-bottom: none !important;
        border-radius: 0 !important;
        box-shadow: none !important;
        color: var(--text) !important;
    }

    .stTextInput [data-baseweb='input'] {
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
    }

    .stTextInput [data-baseweb='input']:focus-within {
        border: none !important;
        box-shadow: none !important;
    }

    .stTextInput input:focus {
        border: none !important;
        border-bottom: none !important;
        box-shadow: none !important;
    }

    .stRadio [role='radiogroup'] {
        gap: 1rem;
        background: transparent !important;
        border: none !important;
        border-radius: 0 !important;
        padding: 0 !important;
    }

    .stButton button,
    .stDownloadButton button {
        border-radius: 999px !important;
        border: 1px solid var(--outline) !important;
        font-weight: 600 !important;
        letter-spacing: 0.2px;
    }

    .stButton button[kind='primary'],
    .stDownloadButton button[kind='primary'] {
        background: linear-gradient(180deg, var(--accent), var(--accent-dark)) !important;
        color: #ffffff !important;
        border: none !important;
        box-shadow: 0 10px 30px rgba(255, 0, 51, 0.35) !important;
    }

    .stButton button:hover,
    .stDownloadButton button:hover {
        transform: translateY(-1px);
    }

    @media (max-width: 760px) {
        .block-container {
            padding-top: 0.8rem;
            padding-bottom: 1.4rem;
        }

        .yt-topbar {
            border-radius: 14px;
            padding: 0.6rem 0.8rem;
        }

        .surface {
            border-radius: 18px;
            padding: 0.9rem;
        }
    }
</style>
"""


def init_session_state() -> None:
    """Inizializza lo stato della sessione usato dalla UI."""
    defaults: dict[str, Any] = {
        "url_input": "",
        "format_choice": "MP4 Video",
        "preview_url": "",
        "video_info": None,
        "is_downloading": False,
        "download_progress": 0,
        "download_status": "",
        "current_file": "",
        "error_message": "",
        "success_message": "",
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def format_bytes(bytes_value: float | int | None) -> str:
    """Formatta byte in formato leggibile (KB, MB, GB)."""
    if not bytes_value:
        return "0 B"

    size = float(bytes_value)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} PB"


def format_duration(seconds: int | float | None) -> str:
    """Formatta i secondi in HH:MM:SS o MM:SS."""
    if not seconds:
        return "N/D"

    total = int(seconds)
    minutes, sec = divmod(total, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{sec:02d}"
    return f"{minutes}:{sec:02d}"


def format_eta(seconds: int | float | None) -> str:
    """Formatta ETA in stringa breve per la barra di progresso."""
    if seconds is None or seconds <= 0:
        return "calcolo..."

    eta = int(seconds)
    minutes, sec = divmod(eta, 60)
    if minutes:
        return f"{minutes}m {sec:02d}s"
    return f"{sec}s"


def format_views(value: int | None) -> str:
    """Formatta il numero di visualizzazioni."""
    if not value:
        return "N/D"
    return f"{value:,}".replace(",", ".")


def safe_text(value: str) -> str:
    """Esegue escaping HTML per contenuti dinamici mostrati in markdown HTML."""
    return html.escape(value or "")


def render_topbar() -> None:
    """Renderizza la topbar in stile YouTube."""
    st.markdown(
        """
        <div class="yt-topbar">
            <div class="yt-brand">
                <span class="yt-logo">▶</span>
                <span>YouTube Downloader</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_intro() -> None:
    """Renderizza il blocco introduttivo dell'app."""
    st.markdown(
        """
        <div class="surface">
            <h1 class="hero-title">Scarica da YouTube in modo rapido</h1>
            <p class="hero-subtitle">
                Incolla un link, verifica l'anteprima e scarica in MP3 o MP4.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_controls() -> tuple[str, str, bool]:
    """Renderizza input URL, formato e azione principale."""
    st.markdown('<div class="surface">', unsafe_allow_html=True)

    url = st.text_input(
        "URL video YouTube",
        key="url_input",
        placeholder="https://www.youtube.com/watch?v=...",
        disabled=st.session_state.is_downloading,
    ).strip()

    format_choice = st.radio(
        "Formato",
        ["MP3 Audio", "MP4 Video"],
        horizontal=True,
        key="format_choice",
        disabled=st.session_state.is_downloading,
    )

    download_clicked = st.button(
        "Scarica",
        type="primary",
        use_container_width=True,
        disabled=st.session_state.is_downloading or not validate_url(url),
    )

    st.markdown("</div>", unsafe_allow_html=True)
    return url, format_choice, download_clicked


def load_preview(url: str, strict: bool = False) -> bool:
    """Carica e salva in sessione i metadati video dell'URL richiesto."""
    st.session_state.error_message = ""

    if not validate_url(url):
        st.session_state.video_info = None
        st.session_state.preview_url = ""
        if strict and url:
            st.session_state.error_message = "URL non valido. Inserisci un link YouTube corretto."
        return False

    if st.session_state.preview_url == url and st.session_state.video_info:
        return True

    try:
        with st.spinner("Recupero anteprima video..."):
            info = get_video_info(url)
        st.session_state.video_info = info
        st.session_state.preview_url = url
        return True
    except DownloadError as exc:
        st.session_state.video_info = None
        st.session_state.preview_url = ""
        st.session_state.error_message = str(exc)
    except Exception as exc:
        st.session_state.video_info = None
        st.session_state.preview_url = ""
        st.session_state.error_message = f"Errore imprevisto durante l'anteprima: {exc}"

    return False


def render_video_preview() -> None:
    """Mostra la card anteprima del video caricato."""
    info = st.session_state.video_info
    if not info:
        return

    st.markdown('<div class="surface">', unsafe_allow_html=True)
    col_thumb, col_details = st.columns([1.1, 1.5], gap="large")

    with col_thumb:
        if info.get("thumbnail"):
            st.image(info["thumbnail"], use_container_width=True)
        else:
            st.caption("Anteprima immagine non disponibile")

    with col_details:
        st.markdown(
            f"<p class='preview-title'>{safe_text(info.get('title', 'Titolo non disponibile'))}</p>",
            unsafe_allow_html=True,
        )
        st.markdown(
            f"<p class='preview-meta'>Canale: {safe_text(info.get('uploader', 'Sconosciuto'))}</p>",
            unsafe_allow_html=True,
        )

        st.markdown(
            f"""
            <div class="chip-row">
                <span class="chip">Durata: {format_duration(info.get('duration'))}</span>
                <span class="chip">Visualizzazioni: {format_views(info.get('view_count'))}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if info.get("is_live"):
            st.warning("Live stream rilevato: il download potrebbe non essere disponibile.")

    st.markdown("</div>", unsafe_allow_html=True)


def run_download(url: str, format_choice: str) -> None:
    """Esegue il download e aggiorna in tempo reale stato e progresso."""
    st.session_state.is_downloading = True
    st.session_state.error_message = ""
    st.session_state.success_message = ""
    st.session_state.download_progress = 0
    st.session_state.download_status = ""

    progress_container = st.container()
    with progress_container:
        st.markdown('<div class="surface">', unsafe_allow_html=True)
        progress_bar = st.progress(0)
        status_placeholder = st.empty()
        st.markdown("</div>", unsafe_allow_html=True)

    def progress_callback(data: dict[str, Any]) -> None:
        status = data.get("status")

        if status == "downloading":
            percentage = max(0, min(100, int(data.get("percentage", 0))))
            st.session_state.download_progress = percentage

            speed = data.get("speed")
            speed_text = f"{format_bytes(speed)}/s" if speed else "N/D"
            eta_text = format_eta(data.get("eta"))
            downloaded = format_bytes(data.get("downloaded"))
            total = format_bytes(data.get("total"))

            progress_bar.progress(percentage)
            status_placeholder.markdown(
                f"<p class='status-msg'>Download {percentage}% · {downloaded}/{total} · {speed_text} · ETA {eta_text}</p>",
                unsafe_allow_html=True,
            )

        elif status == "finished":
            st.session_state.download_progress = 100
            progress_bar.progress(100)
            status_placeholder.markdown(
                "<p class='status-msg'>Download completato. Preparazione file finale...</p>",
                unsafe_allow_html=True,
            )

    try:
        downloader = download_mp3 if format_choice == "MP3 Audio" else download_mp4
        downloaded_file = downloader(url, progress_callback=progress_callback)

        if not downloaded_file or not os.path.exists(downloaded_file):
            raise DownloadError("Download completato ma file non trovato nella cartella downloads.")

        file_name = os.path.basename(downloaded_file)
        st.session_state.current_file = downloaded_file
        st.session_state.success_message = f"Download completato: {file_name}"
    except DownloadError as exc:
        st.session_state.error_message = str(exc)
    except Exception as exc:
        st.session_state.error_message = f"Errore imprevisto durante il download: {exc}"
    finally:
        st.session_state.is_downloading = False


def render_messages() -> None:
    """Renderizza eventuali messaggi di successo o errore."""
    if st.session_state.success_message:
        st.markdown(
            f"<div class='alert-ok'>✅ {safe_text(st.session_state.success_message)}</div>",
            unsafe_allow_html=True,
        )

    if st.session_state.error_message:
        st.markdown(
            f"<div class='alert-error'>❌ {safe_text(st.session_state.error_message)}</div>",
            unsafe_allow_html=True,
        )


def render_download_result() -> None:
    """Mostra i dettagli finali e il pulsante di download verso il dispositivo locale."""
    file_path = st.session_state.current_file
    if not file_path:
        return

    if not os.path.exists(file_path):
        st.session_state.current_file = ""
        st.session_state.error_message = "Il file scaricato non è più disponibile nella cartella downloads."
        return

    file_name = os.path.basename(file_path)
    file_size = os.path.getsize(file_path)
    mime_type = "audio/mpeg" if file_name.lower().endswith(".mp3") else "video/mp4"

    st.markdown('<div class="surface">', unsafe_allow_html=True)
    st.subheader("File pronto")
    st.caption(f"{file_name} · {format_bytes(file_size)}")

    with open(file_path, "rb") as file_obj:
        st.download_button(
            "Scarica sul dispositivo",
            data=file_obj.read(),
            file_name=file_name,
            mime=mime_type,
            type="primary",
            use_container_width=True,
        )

    st.markdown("</div>", unsafe_allow_html=True)


def render_library() -> None:
    """Mostra i file disponibili in `downloads` e consente pulizia rapida."""
    files = get_downloaded_files()

    st.markdown('<div class="surface">', unsafe_allow_html=True)
    st.subheader("Libreria locale")

    if not files:
        st.caption("Nessun file presente in downloads.")
    else:
        for index, item in enumerate(files[:8]):
            col_name, col_size, col_time = st.columns([3.2, 1.1, 1.3])
            with col_name:
                st.markdown(
                    f"<div class='library-name'>{safe_text(item['name'])}</div>",
                    unsafe_allow_html=True,
                )
            with col_size:
                st.markdown(
                    f"<div class='library-label'>{format_bytes(item['size'])}</div>",
                    unsafe_allow_html=True,
                )
            with col_time:
                modified = datetime.fromtimestamp(item["modified"]).strftime("%d/%m %H:%M")
                st.markdown(
                    f"<div class='library-label'>{modified}</div>",
                    unsafe_allow_html=True,
                )

    if st.button("Pulisci cartella downloads", use_container_width=True):
        cleanup_downloads()
        if st.session_state.current_file and not os.path.exists(st.session_state.current_file):
            st.session_state.current_file = ""
        st.session_state.success_message = "Cartella downloads pulita."
        st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


def render_footer() -> None:
    """Renderizza il footer legale minimale."""
    st.caption("Usa l'app responsabilmente e nel rispetto di copyright e termini di servizio.")


def main() -> None:
    """Entry point dell'app Streamlit."""
    init_session_state()
    st.markdown(APP_CSS, unsafe_allow_html=True)

    render_topbar()
    render_intro()

    url, format_choice, download_clicked = render_controls()

    # Se l'utente cambia URL, invalida l'anteprima precedente.
    if url and st.session_state.preview_url and url != st.session_state.preview_url:
        st.session_state.video_info = None
        st.session_state.preview_url = ""

    if not url and st.session_state.preview_url:
        st.session_state.video_info = None
        st.session_state.preview_url = ""
        st.session_state.error_message = ""

    # Anteprima automatica non appena l'URL YouTube diventa valido.
    if url and not st.session_state.is_downloading and url != st.session_state.preview_url and validate_url(url):
        load_preview(url)

    if download_clicked:
        if load_preview(url, strict=True):
            run_download(url, format_choice)

    render_messages()
    render_video_preview()
    render_download_result()
    render_library()
    render_footer()


if __name__ == "__main__":
    main()
