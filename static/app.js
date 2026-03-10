(function () {
    "use strict";

    const i18n = JSON.parse(document.getElementById("i18n-data").textContent || "{}");
    const config = JSON.parse(document.getElementById("config-data").textContent || "{}");

    const urlInput = document.getElementById("url-input");
    const downloadBtn = document.getElementById("download-btn");
    const downloadBtnBottom = document.getElementById("download-btn-bottom");
    const inlineStatus = document.getElementById("inline-status");
    const bottomInlineStatus = document.getElementById("bottom-inline-status");
    const bottomFormat = document.getElementById("bottom-format");
    const messageArea = document.getElementById("message-area");

    const previewCard = document.getElementById("preview-card");
    const previewThumb = document.getElementById("preview-thumb");
    const previewTitle = document.getElementById("preview-video-title");
    const previewChannel = document.getElementById("preview-channel");
    const previewDuration = document.getElementById("preview-duration");
    const previewViews = document.getElementById("preview-views");
    const previewLive = document.getElementById("preview-live");

    const jobsList = document.getElementById("jobs-list");
    const filesList = document.getElementById("files-list");
    const formatInputs = Array.from(document.querySelectorAll("input[name='output-format']"));

    let previewRequestToken = 0;
    let lastPreviewUrl = "";

    function t(key) {
        return i18n[key] || key;
    }

    function escapeHtml(value) {
        return String(value || "")
            .replaceAll("&", "&amp;")
            .replaceAll("<", "&lt;")
            .replaceAll(">", "&gt;")
            .replaceAll('"', "&quot;")
            .replaceAll("'", "&#39;");
    }

    function formatBytes(value) {
        if (!value || value <= 0) {
            return "0 B";
        }

        const units = ["B", "KB", "MB", "GB", "TB"];
        let amount = Number(value);
        let idx = 0;

        while (amount >= 1024 && idx < units.length - 1) {
            amount /= 1024;
            idx += 1;
        }

        return `${amount.toFixed(1)} ${units[idx]}`;
    }

    function formatDuration(seconds) {
        if (!seconds || seconds <= 0) {
            return t("unknown");
        }

        const total = Number(seconds);
        const hours = Math.floor(total / 3600);
        const minutes = Math.floor((total % 3600) / 60);
        const secs = Math.floor(total % 60);

        if (hours > 0) {
            return `${hours}:${String(minutes).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;
        }
        return `${minutes}:${String(secs).padStart(2, "0")}`;
    }

    function formatViews(value) {
        if (!value || value <= 0) {
            return t("unknown");
        }
        return Number(value).toLocaleString();
    }

    function formatEta(seconds) {
        if (!seconds || seconds <= 0) {
            return "--";
        }

        const eta = Math.floor(Number(seconds));
        const minutes = Math.floor(eta / 60);
        const secs = eta % 60;
        if (minutes > 0) {
            return `${minutes}m ${String(secs).padStart(2, "0")}s`;
        }
        return `${secs}s`;
    }

    function setInlineStatus(text) {
        const value = text || "";
        inlineStatus.textContent = value;
        if (bottomInlineStatus) {
            bottomInlineStatus.textContent = value;
        }
    }

    function setActionButtonsDisabled(disabled) {
        if (downloadBtn) {
            downloadBtn.disabled = disabled;
        }
        if (downloadBtnBottom) {
            downloadBtnBottom.disabled = disabled;
        }
    }

    function syncFormatLabel() {
        if (!bottomFormat) {
            return;
        }
        const selected = getSelectedFormat();
        bottomFormat.textContent = selected === "mp3" ? t("format_mp3") : t("format_mp4");
    }

    function showMessage(type, text) {
        messageArea.innerHTML = `<div class="alert ${type}">${escapeHtml(text)}</div>`;
    }

    function clearMessage() {
        messageArea.innerHTML = "";
    }

    function hidePreview() {
        previewCard.classList.add("hidden");
        previewThumb.removeAttribute("src");
        previewTitle.textContent = "";
        previewChannel.textContent = "";
        previewDuration.textContent = "";
        previewViews.textContent = "";
        previewLive.classList.add("hidden");
        previewLive.textContent = "";
    }

    function renderPreview(info) {
        previewCard.classList.remove("hidden");
        previewThumb.src = info.thumbnail || "";
        previewTitle.textContent = info.title || t("unknown");
        previewChannel.textContent = `${t("channel")}: ${info.uploader || t("unknown")}`;
        previewDuration.textContent = `${t("duration")}: ${formatDuration(info.duration)}`;
        previewViews.textContent = `${t("views")}: ${formatViews(info.view_count)}`;

        if (info.is_live) {
            previewLive.classList.remove("hidden");
            previewLive.textContent = t("live_warning");
        } else {
            previewLive.classList.add("hidden");
            previewLive.textContent = "";
        }
    }

    function isYouTubeCandidate(url) {
        if (!url) {
            return false;
        }
        return /(youtube\.com|youtu\.be|youtube-nocookie\.com)/i.test(url);
    }

    async function fetchPreview(url) {
        if (!url || !isYouTubeCandidate(url)) {
            hidePreview();
            setInlineStatus("");
            return;
        }

        const token = ++previewRequestToken;
        setInlineStatus(t("loading_preview"));

        try {
            const response = await fetch(`/api/preview?url=${encodeURIComponent(url)}`);
            const payload = await response.json();

            if (token !== previewRequestToken) {
                return;
            }

            if (!payload.ok) {
                hidePreview();
                setInlineStatus(payload.error || t("preview_error"));
                return;
            }

            renderPreview(payload.info);
            setInlineStatus("");
            lastPreviewUrl = url;
        } catch (_) {
            if (token !== previewRequestToken) {
                return;
            }
            hidePreview();
            setInlineStatus(t("preview_error"));
        }
    }

    function debounce(fn, waitMs) {
        let timerId = null;
        return (...args) => {
            window.clearTimeout(timerId);
            timerId = window.setTimeout(() => fn(...args), waitMs);
        };
    }

    function getSelectedFormat() {
        const selected = document.querySelector("input[name='output-format']:checked");
        return selected ? selected.value : "mp4";
    }

    function statusLabel(status) {
        const map = {
            queued: t("status_queued"),
            downloading: t("status_downloading"),
            finished: t("status_finished"),
            error: t("status_error"),
        };
        return map[status] || status;
    }

    function renderJobs(jobs) {
        if (!jobs || jobs.length === 0) {
            jobsList.innerHTML = `<p class="empty-state">${escapeHtml(t("no_downloads"))}</p>`;
            return;
        }

        jobsList.innerHTML = jobs
            .map((job) => {
                const progress = Math.max(0, Math.min(100, Number(job.progress || 0)));
                const showProgress = job.status === "downloading" || job.status === "queued";
                const errorHtml = job.error
                    ? `<p class="meta-row">${escapeHtml(t("status_error"))}: ${escapeHtml(job.error)}</p>`
                    : "";
                const downloadHtml = job.status === "finished"
                    ? `<a class="download-link" href="/api/downloads/${encodeURIComponent(job.id)}/file">${escapeHtml(t("download_ready"))}: ${escapeHtml(job.file_name || "file")}</a>`
                    : "";

                return `
                    <article class="list-item">
                        <div class="list-head">
                            <span class="list-title">${escapeHtml(job.url)}</span>
                            <span class="badge">${escapeHtml(job.format.toUpperCase())} · ${escapeHtml(statusLabel(job.status))}</span>
                        </div>
                        ${showProgress ? `<div class="progress-wrap"><div class="progress-bar" style="width:${progress}%"></div></div>` : ""}
                        <p class="meta-row">${formatBytes(job.downloaded)} / ${formatBytes(job.total)} · ${formatBytes(job.speed)}/s · ETA ${escapeHtml(formatEta(job.eta))}</p>
                        ${errorHtml}
                        ${downloadHtml}
                    </article>
                `;
            })
            .join("");
    }

    function renderFiles(files) {
        if (!files || files.length === 0) {
            filesList.innerHTML = `<p class="empty-state">${escapeHtml(t("no_files"))}</p>`;
            return;
        }

        filesList.innerHTML = files
            .map((file) => {
                const modifiedDate = new Date(Number(file.modified || 0) * 1000);
                return `
                    <article class="list-item">
                        <div class="list-head">
                            <span class="list-title">${escapeHtml(file.name)}</span>
                            <span class="badge">${escapeHtml(formatBytes(file.size))}</span>
                        </div>
                        <p class="meta-row">${escapeHtml(modifiedDate.toLocaleString())}</p>
                        <a class="download-link" href="${escapeHtml(file.url)}">${escapeHtml(t("download_button"))}</a>
                    </article>
                `;
            })
            .join("");
    }

    async function refreshDownloads() {
        try {
            const response = await fetch("/api/downloads");
            const payload = await response.json();
            if (!payload.ok) {
                return;
            }
            renderJobs(payload.jobs || []);
            renderFiles(payload.files || []);
        } catch (_) {
            // Ignora errori temporanei di polling.
        }
    }

    const debouncedPreview = debounce((url) => {
        fetchPreview(url);
    }, 550);

    urlInput.addEventListener("input", () => {
        const url = urlInput.value.trim();
        setActionButtonsDisabled(!isYouTubeCandidate(url));

        if (!url) {
            previewRequestToken += 1;
            hidePreview();
            setInlineStatus("");
            clearMessage();
            lastPreviewUrl = "";
            return;
        }

        if (url !== lastPreviewUrl) {
            debouncedPreview(url);
        }
    });

    async function startDownload() {
        clearMessage();

        const url = urlInput.value.trim();
        if (!url) {
            showMessage("error", t("invalid_url"));
            return;
        }

        const payload = {
            url,
            format: getSelectedFormat(),
        };

        setActionButtonsDisabled(true);
        setInlineStatus(t("status_queued"));

        try {
            const response = await fetch("/api/download", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify(payload),
            });
            const data = await response.json();

            if (!data.ok) {
                showMessage("error", data.error || t("download_failed"));
                setInlineStatus("");
                setActionButtonsDisabled(!isYouTubeCandidate(urlInput.value.trim()));
                return;
            }

            showMessage("ok", data.message || t("download_started"));
            setInlineStatus(t("status_queued"));
            setActionButtonsDisabled(!isYouTubeCandidate(urlInput.value.trim()));
            refreshDownloads();
        } catch (_) {
            showMessage("error", t("download_failed"));
            setInlineStatus("");
            setActionButtonsDisabled(!isYouTubeCandidate(urlInput.value.trim()));
        }
    }

    if (downloadBtn) {
        downloadBtn.addEventListener("click", startDownload);
    }
    if (downloadBtnBottom) {
        downloadBtnBottom.addEventListener("click", startDownload);
    }

    formatInputs.forEach((input) => {
        input.addEventListener("change", syncFormatLabel);
    });

    syncFormatLabel();
    setActionButtonsDisabled(!isYouTubeCandidate(urlInput.value.trim()));
    refreshDownloads();
    const pollInterval = Number(config.pollIntervalMs || 1500);
    window.setInterval(refreshDownloads, pollInterval);
})();
