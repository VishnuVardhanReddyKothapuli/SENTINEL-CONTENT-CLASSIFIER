/**
 * NSFWGuard - Classifying Lab JavaScript
 * Pure vanilla JS, no frameworks needed.
 * Handles: file upload, drag+drop, YouTube preview, API calls, results rendering.
 */

let currentMode = "classify";   // "classify" or "blur"
let currentTab = "upload";      // "upload" or "youtube"
let selectedFile = null;

// ── Mode Toggle ─────────────────────────────────────────────────────────────

function setMode(mode) {
    currentMode = mode;
    document.getElementById("mode-classify").classList.toggle("active", mode === "classify");
    document.getElementById("mode-blur").classList.toggle("active", mode === "blur");
}

// ── Tab Toggle ──────────────────────────────────────────────────────────────

function switchTab(tab) {
    currentTab = tab;
    document.getElementById("tab-upload").classList.toggle("active", tab === "upload");
    document.getElementById("tab-youtube").classList.toggle("active", tab === "youtube");
    document.getElementById("panel-upload").classList.toggle("hidden", tab !== "upload");
    document.getElementById("panel-youtube").classList.toggle("hidden", tab !== "youtube");
}

// ── File Upload Handling ─────────────────────────────────────────────────────

const fileInput = document.getElementById("file-input");
const dropZone = document.getElementById("drop-zone");

fileInput.addEventListener("change", (e) => {
    if (e.target.files.length > 0) showFilePreview(e.target.files[0]);
});

dropZone.addEventListener("click", () => fileInput.click());

dropZone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropZone.classList.add("drag-over");
});

dropZone.addEventListener("dragleave", () => dropZone.classList.remove("drag-over"));

dropZone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropZone.classList.remove("drag-over");
    const file = e.dataTransfer.files[0];
    if (file) showFilePreview(file);
});

function showFilePreview(file) {
    selectedFile = file;
    const container = document.getElementById("file-preview-container");
    const imgEl = document.getElementById("preview-image");
    const vidEl = document.getElementById("preview-video");
    const nameEl = document.getElementById("preview-name");

    imgEl.classList.add("hidden");
    vidEl.classList.add("hidden");

    const url = URL.createObjectURL(file);

    if (file.type.startsWith("image/")) {
        imgEl.src = url;
        imgEl.classList.remove("hidden");
    } else if (file.type.startsWith("video/")) {
        vidEl.src = url;
        vidEl.classList.remove("hidden");
    }

    nameEl.textContent = file.name;
    container.classList.remove("hidden");
}

// ── YouTube Preview ──────────────────────────────────────────────────────────

document.getElementById("yt-url-input").addEventListener("input", debounce(loadYouTubePreview, 600));

function loadYouTubePreview() {
    const url = document.getElementById("yt-url-input").value.trim();
    if (!url) return;

    const videoId = extractYouTubeId(url);
    if (!videoId) return;

    const iframe = document.getElementById("yt-preview-iframe");
    iframe.src = `https://www.youtube.com/embed/${videoId}`;
    document.getElementById("yt-preview-container").classList.remove("hidden");
}

function extractYouTubeId(url) {
    const regex = /(?:v=|youtu\.be\/|embed\/)([a-zA-Z0-9_-]{11})/;
    const match = url.match(regex);
    return match ? match[1] : null;
}

// ── Main Analysis ─────────────────────────────────────────────────────────────

async function runAnalysis() {
    const btn = document.getElementById("analyze-btn");
    const btnText = document.getElementById("btn-text");
    const spinner = document.getElementById("btn-spinner");

    // show loading state
    btn.disabled = true;
    btnText.textContent = "Analyzing...";
    spinner.classList.remove("hidden");
    hideResults();

    try {
        let result;
        if (currentTab === "youtube") {
            result = await classifyYouTube();
        } else {
            result = await classifyFile();
        }

        if (result.error) {
            alert("Error: " + result.error);
            return;
        }

        renderResults(result);
    } catch (err) {
        alert("Something went wrong. Please try again.");
        console.error(err);
    } finally {
        btn.disabled = false;
        btnText.textContent = "Analyze Content";
        spinner.classList.add("hidden");
    }
}

async function classifyFile() {
    if (!selectedFile) {
        alert("Please select a file first.");
        return { error: "No file selected" };
    }

    const formData = new FormData();
    formData.append("file", selectedFile);

    const endpoint = currentMode === "blur" ? "/classify/blur" : "/classify/run";
    const response = await fetch(endpoint, { method: "POST", body: formData });
    return await response.json();
}

async function classifyYouTube() {
    const url = document.getElementById("yt-url-input").value.trim();
    if (!url) {
        alert("Please enter a YouTube URL first.");
        return { error: "No URL" };
    }

    const formData = new FormData();
    formData.append("youtube_url", url);
    formData.append("mode", currentMode);

    const response = await fetch("/classify/youtube", { method: "POST", body: formData });
    return await response.json();
}

// ── Results Rendering ─────────────────────────────────────────────────────────

function renderResults(data) {
    const panel = document.getElementById("results-panel");
    const mediaWrapper = document.getElementById("result-media-wrapper");

    // pick which media URL to display (blurred if available, else original)
    const displayUrl = data.blurred_url || data.file_url || data.original_url;
    const mediaType = data.media_type;

    // render media
    mediaWrapper.innerHTML = "";
    mediaWrapper.className = "result-media-wrapper";
    mediaWrapper.classList.add(`border-${data.label}`);

    if (displayUrl) {
        if (mediaType === "image") {
            const img = document.createElement("img");
            img.src = displayUrl;
            img.alt = "Classified media";
            mediaWrapper.appendChild(img);
        } else {
            const vid = document.createElement("video");
            vid.src = displayUrl;
            vid.controls = true;
            mediaWrapper.appendChild(vid);
        }
    }

    // badge
    const badge = document.getElementById("result-badge");
    const icon = document.getElementById("result-badge-icon");
    const label = document.getElementById("result-badge-label");

    badge.className = `result-badge ${data.label}`;
    const icons = { safe: "✅", suggestive: "⚠️", nsfw: "🚫" };
    const labels = {
        safe: "SAFE",
        suggestive: "SUGGESTIVE",
        nsfw: "NOT SAFE"
    };
    icon.textContent = icons[data.label] || "?";
    label.textContent = (data.was_blurred && data.label !== "safe") ? labels[data.label] + " (Blurred)" : labels[data.label];

    // confidence bar
    const pct = Math.round(data.confidence_score * 100);
    document.getElementById("conf-bar-fill").style.width = `${pct}%`;
    document.getElementById("conf-value").textContent = `${pct}%`;

    // category breakdown
    const categoryList = document.getElementById("category-list");
    categoryList.innerHTML = "";
    const cats = data.category_scores || {};

    if (Object.keys(cats).length > 0) {
        Object.entries(cats)
            .sort((a, b) => b[1] - a[1])
            .slice(0, 8)
            .forEach(([name, score]) => {
                const row = document.createElement("div");
                row.className = "category-item";
                const pctScore = Math.round(score * 100);
                row.innerHTML = `
                    <span class="cat-name">${name}</span>
                    <span class="cat-score">${pctScore}%</span>
                `;
                categoryList.appendChild(row);
            });
        document.getElementById("category-breakdown").classList.remove("hidden");
    } else {
        document.getElementById("category-breakdown").classList.add("hidden");
    }

    // show upload links if content is safe or was blurred (i.e. cleaned)
    const isClean = data.label === "safe" || (data.was_blurred && data.label !== "safe");
    const uploadLinks = document.getElementById("upload-links");

    if (isClean && displayUrl) {
        renderUploadLinks(displayUrl);
        uploadLinks.classList.remove("hidden");
        document.getElementById("download-btn").href = displayUrl;
    } else {
        uploadLinks.classList.add("hidden");
    }

    panel.classList.remove("hidden");
    panel.scrollIntoView({ behavior: "smooth", block: "start" });
}

function renderUploadLinks(fileUrl) {
    const fullUrl = window.location.origin + fileUrl;
    const platforms = [
        { name: "YouTube Studio", icon: "▶️", url: "https://studio.youtube.com/channel/upload" },
        { name: "Instagram", icon: "📸", url: "https://www.instagram.com/" },
        { name: "Reddit", icon: "🤖", url: "https://www.reddit.com/submit" },
        { name: "Discord", icon: "💬", url: "https://discord.com/app" },
        { name: "Twitter/X", icon: "🐦", url: "https://x.com/compose/post" },
        { name: "TikTok", icon: "🎵", url: "https://www.tiktok.com/upload" },
    ];

    const container = document.getElementById("platform-links");
    container.innerHTML = "";

    platforms.forEach(p => {
        const a = document.createElement("a");
        a.href = p.url;
        a.target = "_blank";
        a.rel = "noopener noreferrer";
        a.className = "platform-link";
        a.innerHTML = `<span>${p.icon}</span> ${p.name}`;
        container.appendChild(a);
    });
}

function hideResults() {
    document.getElementById("results-panel").classList.add("hidden");
}

// ── Utilities ─────────────────────────────────────────────────────────────────

function debounce(fn, delay) {
    let timer;
    return (...args) => {
        clearTimeout(timer);
        timer = setTimeout(() => fn.apply(this, args), delay);
    };
}
