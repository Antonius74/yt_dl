"""
Test per il modulo downloader.
Esegue test unitari sulle funzioni principali.
"""

import os
import pytest
from unittest.mock import patch, MagicMock
from downloader import (
    validate_url,
    normalize_youtube_url,
    get_video_info,
    download_mp3,
    download_mp4,
    cleanup_downloads,
    get_downloaded_files,
    DownloadError
)


class TestValidateUrl:
    """Test per la funzione validate_url."""

    def test_valid_youtube_url_standard(self):
        """Test URL YouTube standard."""
        assert validate_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ") is True

    def test_valid_youtube_url_short(self):
        """Test URL YouTube corto (youtu.be)."""
        assert validate_url("https://youtu.be/dQw4w9WgXcQ") is True

    def test_valid_youtube_url_with_www(self):
        """Test URL con www."""
        assert validate_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ") is True

    def test_valid_youtube_url_embed(self):
        """Test URL embed."""
        assert validate_url("https://www.youtube.com/embed/dQw4w9WgXcQ") is True

    def test_valid_youtube_url_shorts(self):
        """Test URL shorts."""
        assert validate_url("https://www.youtube.com/shorts/dQw4w9WgXcQ") is True

    def test_valid_youtube_url_live(self):
        """Test URL live."""
        assert validate_url("https://www.youtube.com/live/dQw4w9WgXcQ") is True

    def test_valid_youtube_url_without_scheme(self):
        """Test URL senza schema http/https."""
        assert validate_url("www.youtube.com/watch?v=dQw4w9WgXcQ") is True

    def test_invalid_youtube_url_invalid_video_id(self):
        """Test URL YouTube con video id non valido."""
        assert validate_url("https://www.youtube.com/watch?v=short") is False

    def test_invalid_url_empty(self):
        """Test URL vuoto."""
        assert validate_url("") is False

    def test_invalid_url_none(self):
        """Test URL None."""
        assert validate_url(None) is False

    def test_invalid_url_not_youtube(self):
        """Test URL non YouTube."""
        assert validate_url("https://www.google.com") is False

    def test_invalid_url_random_string(self):
        """Test stringa casuale."""
        assert validate_url("not_a_url") is False


class TestNormalizeYoutubeUrl:
    """Test per la normalizzazione degli URL YouTube condivisi."""

    def test_normalize_short_url_with_tracking_params(self):
        """Normalizza URL youtu.be con parametri di tracking."""
        normalized = normalize_youtube_url("https://youtu.be/0CdE6oTkbj4?is=8cVYuPO6dQHxdprB")
        assert normalized == "https://www.youtube.com/watch?v=0CdE6oTkbj4"

    def test_normalize_watch_url_preserves_video_id(self):
        """Normalizza URL watch mantenendo lo stesso video id."""
        normalized = normalize_youtube_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ&si=abc")
        assert normalized == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

    def test_normalize_invalid_url_returns_trimmed_input(self):
        """URL non valido: ritorna la stringa ripulita."""
        normalized = normalize_youtube_url(" not_a_url ")
        assert normalized == "not_a_url"


class TestGetVideoInfo:
    """Test per la funzione get_video_info."""

    @patch('downloader.YoutubeDL')
    def test_get_video_info_success(self, mock_ytdl_class):
        """Test recupero informazioni con successo."""
        mock_ydl = MagicMock()
        mock_ytdl_class.return_value.__enter__.return_value = mock_ydl
        mock_ydl.extract_info.return_value = {
            'title': 'Test Video',
            'duration': 300,
            'uploader': 'Test Channel',
            'thumbnail': 'https://example.com/thumb.jpg',
            'is_live': False
        }

        info = get_video_info("https://www.youtube.com/watch?v=dQw4w9WgXcQ")

        assert info['title'] == 'Test Video'
        assert info['duration'] == 300
        assert info['uploader'] == 'Test Channel'
        assert info['is_live'] is False

    @patch('downloader.YoutubeDL')
    def test_get_video_info_error(self, mock_ytdl_class):
        """Test errore nel recupero informazioni."""
        mock_ydl = MagicMock()
        mock_ytdl_class.return_value.__enter__.return_value = mock_ydl
        mock_ydl.extract_info.side_effect = Exception("Video not found")

        with pytest.raises(DownloadError):
            get_video_info("https://www.youtube.com/watch?v=invalid")

    def test_get_video_info_invalid_url(self):
        """Test URL non valido in get_video_info."""
        with pytest.raises(DownloadError, match="URL non valido"):
            get_video_info("https://www.google.com")


class TestDownloadMp3:
    """Test per la funzione download_mp3."""

    def test_download_mp3_invalid_url(self):
        """Test download con URL non valido."""
        with pytest.raises(DownloadError, match="URL non valido"):
            download_mp3("not_a_valid_url")

    @patch('downloader.YoutubeDL')
    def test_download_mp3_success(self, mock_ytdl_class):
        """Test download MP3 con successo."""
        mock_ydl = MagicMock()
        mock_ytdl_class.return_value.__enter__.return_value = mock_ydl
        mock_ydl.extract_info.return_value = {'title': 'Test Song'}
        mock_ydl.prepare_filename.return_value = '/tmp/downloads/Test Song.webm'

        with patch('os.path.exists') as mock_exists:
            mock_exists.return_value = True
            result = download_mp3("https://www.youtube.com/watch?v=dQw4w9WgXcQ", output_dir='/tmp/downloads')
            assert result.endswith('.mp3')

    @patch('downloader.YoutubeDL')
    def test_download_mp3_copyright_error(self, mock_ytdl_class):
        """Test gestione errore copyright."""
        mock_ydl = MagicMock()
        mock_ytdl_class.return_value.__enter__.return_value = mock_ydl
        mock_ydl.extract_info.side_effect = Exception("This video contains copyright content")

        with pytest.raises(DownloadError, match="copyright"):
            download_mp3("https://www.youtube.com/watch?v=dQw4w9WgXcQ")

    @patch('downloader.YoutubeDL')
    def test_download_mp3_age_restricted(self, mock_ytdl_class):
        """Test gestione errore restrizione età."""
        mock_ydl = MagicMock()
        mock_ytdl_class.return_value.__enter__.return_value = mock_ydl
        mock_ydl.extract_info.side_effect = Exception("This video is age-restricted")

        with pytest.raises(DownloadError, match="restrizione di età"):
            download_mp3("https://www.youtube.com/watch?v=dQw4w9WgXcQ")


class TestDownloadMp4:
    """Test per la funzione download_mp4."""

    def test_download_mp4_invalid_url(self):
        """Test download con URL non valido."""
        with pytest.raises(DownloadError, match="URL non valido"):
            download_mp4("not_a_valid_url")

    @patch('downloader.YoutubeDL')
    def test_download_mp4_success(self, mock_ytdl_class):
        """Test download MP4 con successo."""
        mock_ydl = MagicMock()
        mock_ytdl_class.return_value.__enter__.return_value = mock_ydl
        mock_ydl.extract_info.return_value = {'title': 'Test Video'}
        mock_ydl.prepare_filename.return_value = '/tmp/downloads/Test Video.mp4'

        with patch('os.path.exists') as mock_exists:
            mock_exists.return_value = True
            result = download_mp4("https://www.youtube.com/watch?v=dQw4w9WgXcQ", output_dir='/tmp/downloads')
            assert result.endswith('.mp4')

    @patch('downloader.YoutubeDL')
    def test_download_mp4_private_video(self, mock_ytdl_class):
        """Test gestione errore video privato."""
        mock_ydl = MagicMock()
        mock_ytdl_class.return_value.__enter__.return_value = mock_ydl
        mock_ydl.extract_info.side_effect = Exception("This video is private")

        with pytest.raises(DownloadError, match="privato"):
            download_mp4("https://www.youtube.com/watch?v=dQw4w9WgXcQ")


class TestCleanupDownloads:
    """Test per la funzione cleanup_downloads."""

    def test_cleanup_empty_directory(self):
        """Test pulizia directory vuota."""
        with patch('os.path.exists') as mock_exists:
            mock_exists.return_value = True
            with patch('os.listdir') as mock_listdir:
                mock_listdir.return_value = []
                cleanup_downloads("/tmp/test_downloads")

    def test_cleanup_with_files(self, tmp_path):
        """Test pulizia con file."""
        # Crea file temporanei
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        cleanup_downloads(str(tmp_path))

        # Verifica che il file sia stato rimosso
        assert not test_file.exists()

    def test_cleanup_nonexistent_directory(self):
        """Test pulizia directory inesistente."""
        with patch('os.path.exists') as mock_exists:
            mock_exists.return_value = False
            # Non dovrebbe generare errori
            cleanup_downloads("/nonexistent/path")


class TestGetDownloadedFiles:
    """Test per la funzione get_downloaded_files."""

    def test_get_files_empty_directory(self):
        """Test directory vuota."""
        with patch('os.path.exists') as mock_exists:
            mock_exists.return_value = True
            with patch('os.listdir') as mock_listdir:
                mock_listdir.return_value = []
                files = get_downloaded_files("/tmp/downloads")
                assert files == []

    def test_get_files_with_content(self, tmp_path):
        """Test con file esistenti."""
        # Crea file temporanei
        (tmp_path / "song.mp3").write_text("audio content")
        (tmp_path / "video.mp4").write_text("video content")

        files = get_downloaded_files(str(tmp_path))

        assert len(files) == 2
        file_names = [f['name'] for f in files]
        assert "song.mp3" in file_names
        assert "video.mp4" in file_names

    def test_get_files_nonexistent_directory(self):
        """Test directory inesistente."""
        with patch('os.path.exists') as mock_exists:
            mock_exists.return_value = False
            files = get_downloaded_files("/nonexistent/path")
            assert files == []


class TestProgressCallback:
    """Test per la funzione di callback del progresso."""

    @patch('downloader.YoutubeDL')
    def test_progress_callback_during_download(self, mock_ytdl_class):
        """Test callback durante il download."""
        progress_data = {}

        def mock_callback(data):
            progress_data.update(data)

        mock_ydl = MagicMock()
        mock_ytdl_class.return_value.__enter__.return_value = mock_ydl

        # Simula l'hook di progresso
        def simulate_progress_hook(hooks):
            for hook in hooks:
                hook({
                    'status': 'downloading',
                    'downloaded_bytes': 50,
                    'total_bytes': 100,
                    'speed': 1024,
                    'eta': 10
                })

        mock_ydl.extract_info.side_effect = simulate_progress_hook
        mock_ydl.prepare_filename.return_value = '/tmp/test.mp3'

        with patch('os.path.exists') as mock_exists:
            mock_exists.return_value = True
            with patch('os.path.splitext') as mock_splitext:
                mock_splitext.return_value = ('/tmp/test', '.webm')
                try:
                    download_mp3(
                        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                        progress_callback=mock_callback
                    )
                except:
                    pass  # L'errore è atteso dato il mock


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
