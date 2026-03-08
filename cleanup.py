#!/usr/bin/env python3
"""
Script di pulizia per rimuovere i file scaricati.
Può essere eseguito manualmente o automaticamente.
"""

import os
import sys
import argparse
from datetime import datetime, timedelta


def cleanup_downloads(output_dir: str = "downloads", older_than_hours: int = None):
    """
    Pulisce la cartella dei download.

    Args:
        output_dir: Directory da pulire
        older_than_hours: Se specificato, rimuove solo i file più vecchi di X ore
    """
    if not os.path.exists(output_dir):
        print(f"ℹ️ La directory '{output_dir}' non esiste.")
        return 0

    files_removed = 0
    total_size_freed = 0

    for filename in os.listdir(output_dir):
        file_path = os.path.join(output_dir, filename)

        if not os.path.isfile(file_path):
            continue

        # Controlla l'età del file se richiesto
        if older_than_hours is not None:
            file_stat = os.stat(file_path)
            file_time = datetime.fromtimestamp(file_stat.st_mtime)
            cutoff_time = datetime.now() - timedelta(hours=older_than_hours)

            if file_time > cutoff_time:
                continue  # File troppo recente, salta

        try:
            file_size = os.path.getsize(file_path)
            os.remove(file_path)
            files_removed += 1
            total_size_freed += file_size
            print(f"🗑️ Rimosso: {filename}")
        except Exception as e:
            print(f"❌ Errore nel rimuovere {filename}: {e}")

    return files_removed, total_size_freed


def format_size(bytes_value):
    """Formatta i byte in formato leggibile."""
    if bytes_value == 0:
        return "0 B"
    for unit in ['B', 'KB', 'MB', 'GB']:
        if abs(bytes_value) < 1024.0:
            return f"{bytes_value:.2f} {unit}"
        bytes_value /= 1024.0
    return f"{bytes_value:.2f} TB"


def main():
    """Funzione principale dello script."""
    parser = argparse.ArgumentParser(
        description="Pulisce i file scaricati nella cartella downloads/"
    )
    parser.add_argument(
        "--older-than",
        type=int,
        metavar="ORE",
        help="Rimuovi solo i file più vecchi di N ore"
    )
    parser.add_argument(
        "--directory",
        type=str,
        default="downloads",
        help="Directory da pulire (default: downloads)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Mostra cosa verrebbe rimosso senza cancellare"
    )

    args = parser.parse_args()

    print(f"🧹 Pulizia file scaricati...")
    print(f"📁 Directory: {args.directory}")

    if args.older_than:
        print(f"⏰ Solo file più vecchi di {args.older_than} ore")

    if args.dry_run:
        print("🔍 Modalità dry-run: nessun file verrà rimosso")

    if args.dry_run:
        # Solo simulazione
        if os.path.exists(args.directory):
            for filename in os.listdir(args.directory):
                file_path = os.path.join(args.directory, filename)
                if os.path.isfile(file_path):
                    print(f"   [SIMULATO] Rimuoverebbe: {filename}")
        print("✅ Simulazione completata.")
        return 0

    files_removed, size_freed = cleanup_downloads(
        args.directory,
        older_than_hours=args.older_than
    )

    if files_removed > 0:
        print(f"\n✅ Pulizia completata!")
        print(f"   File rimossi: {files_removed}")
        print(f"   Spazio liberato: {format_size(size_freed)}")
    else:
        print(f"\n✅ Nessun file da rimuovere.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
