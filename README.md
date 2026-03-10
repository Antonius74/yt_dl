# YouTube Downloader Web (FastAPI)

Servizio web Python nativo (senza Streamlit) per scaricare contenuti YouTube in formato MP3/MP4 con:
- UI custom HTML/CSS/JS
- sessione utente via cookie HTTP-only
- anteprima automatica del video
- download paralleli tra sessioni diverse
- directory locale separata per ogni sessione (`downloads/<session_id>`)
- lingua automatica da browser (fallback lingua del sistema operativo)

## 1) Prerequisiti

## Software obbligatorio
- Python `3.10+`
- `pip`
- `venv`
- `ffmpeg` nel `PATH`

## Software consigliato
- `git`
- Node.js (opzionale; migliora compatibilita in alcuni casi yt-dlp)

## Verifica prerequisiti
```bash
python3 --version
pip3 --version
ffmpeg -version
```

Installazione `ffmpeg`:
- macOS: `brew install ffmpeg`
- Ubuntu/Debian: `sudo apt update && sudo apt install -y ffmpeg`

## 2) Installazione locale

```bash
cd /percorso/progetto/yt_dl
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## Avvio rapido consigliato

```bash
cd /percorso/progetto/yt_dl
source venv/bin/activate
python -m uvicorn app:app --reload --host 0.0.0.0 --port 8501
```

## 3) Avvio servizio (sviluppo)

```bash
source venv/bin/activate
python -m uvicorn app:app --reload --host 0.0.0.0 --port 8501
```

URL locale: `http://localhost:8501`

## 4) Uso applicazione

1. Apri il browser e incolla un URL YouTube.
2. L'anteprima compare automaticamente se il link e valido.
3. Seleziona formato `MP3` o `MP4`.
4. Clicca `Scarica`.
5. Monitora stato/progresso nella lista download della tua sessione.
6. Scarica il file completato dalla lista.

## 5) Architettura sessione e storage

- Cookie sessione: `yt_session_id` (HTTP-only, SameSite=Lax).
- Ogni sessione ha una directory dedicata: `downloads/<session_id>`.
- I file di una sessione non compaiono nelle altre sessioni.
- Download concorrenti tra sessioni differenti gestiti in parallelo tramite thread pool backend.

## 6) Endpoints principali

- `GET /` -> UI web
- `GET /api/preview?url=...` -> metadata anteprima
- `POST /api/download` -> avvio job download
- `GET /api/downloads` -> stato job + file sessione
- `GET /api/downloads/{job_id}/file` -> download file job completato
- `GET /api/files/{file_name}` -> download diretto file locale sessione

## 7) Gestione operativa

## Test
```bash
python -m pytest -q
```

## Riavvio rapido locale
```bash
pkill -f "uvicorn app:app" || true
uvicorn app:app --reload --host 0.0.0.0 --port 8501
```

## Log runtime (se eseguito in foreground)
- Log direttamente nel terminale dove gira `uvicorn`.

## 8) Installazione come servizio

## 8.1 Linux (systemd)

Crea `/etc/systemd/system/yt-downloader.service`:

```ini
[Unit]
Description=YT Downloader FastAPI Service
After=network.target

[Service]
Type=simple
User=<utente>
WorkingDirectory=/percorso/assoluto/yt_dl
ExecStart=/percorso/assoluto/yt_dl/venv/bin/uvicorn app:app --host 0.0.0.0 --port 8501
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Comandi gestione:
```bash
sudo systemctl daemon-reload
sudo systemctl enable yt-downloader
sudo systemctl start yt-downloader
sudo systemctl status yt-downloader
sudo systemctl restart yt-downloader
sudo systemctl stop yt-downloader
sudo journalctl -u yt-downloader -f
```

## 8.2 macOS (launchd)

Crea `~/Library/LaunchAgents/com.ytdl.fastapi.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.ytdl.fastapi</string>

  <key>ProgramArguments</key>
  <array>
    <string>/percorso/assoluto/yt_dl/venv/bin/uvicorn</string>
    <string>app:app</string>
    <string>--host</string>
    <string>0.0.0.0</string>
    <string>--port</string>
    <string>8501</string>
  </array>

  <key>WorkingDirectory</key>
  <string>/percorso/assoluto/yt_dl</string>

  <key>RunAtLoad</key>
  <true/>

  <key>KeepAlive</key>
  <true/>

  <key>StandardOutPath</key>
  <string>/tmp/yt-downloader.out.log</string>

  <key>StandardErrorPath</key>
  <string>/tmp/yt-downloader.err.log</string>
</dict>
</plist>
```

Comandi gestione:
```bash
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.ytdl.fastapi.plist
launchctl kickstart -k gui/$(id -u)/com.ytdl.fastapi
launchctl print gui/$(id -u)/com.ytdl.fastapi
launchctl bootout gui/$(id -u)/com.ytdl.fastapi
```

## 9) Aggiornamento

```bash
cd /percorso/assoluto/yt_dl
source venv/bin/activate
pip install -r requirements.txt --upgrade
```

Riavvia servizio:
- systemd: `sudo systemctl restart yt-downloader`
- launchd: `launchctl kickstart -k gui/$(id -u)/com.ytdl.fastapi`

## 10) Troubleshooting

## `FFmpeg not found`
Verifica installazione e `PATH`.

## `ModuleNotFoundError: No module named 'yt_dlp'`
Stai avviando `uvicorn` fuori dal virtualenv.
```bash
cd /percorso/progetto/yt_dl
source venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn app:app --reload --host 0.0.0.0 --port 8501
```

## Porta occupata
```bash
uvicorn app:app --host 0.0.0.0 --port 8510
```

## Cookie/sessione non persistente
Verifica che il browser accetti cookie per `localhost` o dominio usato.

## 11) Sicurezza e note legali

- Non esporre token o segreti nel codice.
- Mantieni `downloads/` protetta a livello host.
- Rispetta copyright, termini YouTube e normativa locale.
