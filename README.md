# YouTube Downloader Web

Applicazione Streamlit per scaricare contenuti YouTube in formato MP3 o MP4 usando `yt-dlp`.

## 1) Prerequisiti

### Software obbligatorio
- Python `3.10+`
- `pip`
- `venv` (modulo standard Python)
- `ffmpeg` installato e disponibile nel `PATH`

### Software consigliato
- `git` (per aggiornare il progetto)
- `pytest` (gia incluso in `requirements.txt`)
- Node.js (opzionale, migliora compatibilita con alcuni challenge JavaScript)

### Verifiche rapide prerequisiti
```bash
python3 --version
pip3 --version
ffmpeg -version
```

Se `ffmpeg` non e presente:
- macOS: `brew install ffmpeg`
- Ubuntu/Debian: `sudo apt update && sudo apt install -y ffmpeg`

## 2) Installazione locale

### 2.1 Clona o copia il progetto
```bash
cd /percorso/dove/vuoi
# se usi git
# git clone <repo-url> yt_dl
cd yt_dl
```

### 2.2 Crea e attiva ambiente virtuale
```bash
python3 -m venv venv
source venv/bin/activate
```

### 2.3 Installa dipendenze
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

## 3) Avvio applicazione

```bash
streamlit run app.py
```

Per esposizione in rete locale:
```bash
streamlit run app.py --server.address 0.0.0.0 --server.port 8501
```

URL di default: `http://localhost:8501`

## 4) Uso operativo

### Download
1. Incolla URL YouTube valido.
2. Seleziona formato (`MP3` o `MP4`).
3. Clicca `Scarica`.
4. Usa il pulsante di download finale per salvare il file sul dispositivo.

### Pulizia file temporanei
Da UI: pulsante `Pulisci cartella downloads`.

Da terminale:
```bash
python cleanup.py
```

Simulazione senza cancellare:
```bash
python cleanup.py --dry-run
```

### Esecuzione test
```bash
python -m pytest -q
```

## 5) Installazione come servizio

## 5.1 Linux (systemd)

Crea `/etc/systemd/system/yt-downloader.service`:

```ini
[Unit]
Description=YT Downloader Streamlit Service
After=network.target

[Service]
Type=simple
User=<utente>
WorkingDirectory=/percorso/assoluto/yt_dl
ExecStart=/percorso/assoluto/yt_dl/venv/bin/python -m streamlit run app.py --server.address 0.0.0.0 --server.port 8501 --server.headless true
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Attiva il servizio:
```bash
sudo systemctl daemon-reload
sudo systemctl enable yt-downloader
sudo systemctl start yt-downloader
```

Gestione:
```bash
sudo systemctl status yt-downloader
sudo systemctl restart yt-downloader
sudo systemctl stop yt-downloader
sudo journalctl -u yt-downloader -f
```

## 5.2 macOS (launchd)

Crea `~/Library/LaunchAgents/com.ytdl.streamlit.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.ytdl.streamlit</string>

  <key>ProgramArguments</key>
  <array>
    <string>/percorso/assoluto/yt_dl/venv/bin/python</string>
    <string>-m</string>
    <string>streamlit</string>
    <string>run</string>
    <string>app.py</string>
    <string>--server.address</string>
    <string>0.0.0.0</string>
    <string>--server.port</string>
    <string>8501</string>
    <string>--server.headless</string>
    <string>true</string>
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
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.ytdl.streamlit.plist
launchctl kickstart -k gui/$(id -u)/com.ytdl.streamlit
launchctl print gui/$(id -u)/com.ytdl.streamlit
launchctl bootout gui/$(id -u)/com.ytdl.streamlit
```

## 6) Aggiornamento servizio

```bash
cd /percorso/assoluto/yt_dl
source venv/bin/activate
pip install -r requirements.txt --upgrade
```

Poi riavvia:
- systemd: `sudo systemctl restart yt-downloader`
- launchd: `launchctl kickstart -k gui/$(id -u)/com.ytdl.streamlit`

## 7) Troubleshooting

### `FFmpeg not found`
Verifica installazione di `ffmpeg` e presenza nel `PATH`.

### `Video non disponibile` / `age restriction` / `private`
Errore lato sorgente YouTube: il contenuto puo essere non accessibile.

### Porta 8501 occupata
Avvia su altra porta:
```bash
streamlit run app.py --server.port 8510
```

### Ambiente virtuale rotto
Ricrea venv:
```bash
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 8) Sicurezza e note legali

- Non esporre token o segreti nel codice.
- Non salvare percorsi locali sensibili in output condivisi.
- Usa il tool nel rispetto di copyright, ToS di YouTube e normativa locale.
