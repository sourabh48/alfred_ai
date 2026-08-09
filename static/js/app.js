function getCookie(name) {
    const cookieValue = document.cookie
        .split(";")
        .map(item => item.trim())
        .find(item => item.startsWith(`${name}=`));
    return cookieValue ? decodeURIComponent(cookieValue.split("=")[1]) : "";
}

let uiConfigCache = null;
const NAV_SCROLL_STORAGE_KEY = "alfred.nav.scrollTop";
const NAV_ACTIVE_LINK_STORAGE_KEY = "alfred.nav.lastHref";

function getUiConfigRoot() {
    if (uiConfigCache !== null) {
        return uiConfigCache;
    }
    const node = document.getElementById("alfred-ui-config");
    if (!node) {
        uiConfigCache = {};
        return uiConfigCache;
    }
    try {
        uiConfigCache = JSON.parse(node.textContent || "{}");
    } catch (_error) {
        uiConfigCache = {};
    }
    return uiConfigCache;
}

function getUiConfig(path, fallback = "") {
    const segments = String(path || "")
        .split(".")
        .map(item => item.trim())
        .filter(Boolean);
    let current = getUiConfigRoot();
    for (const segment of segments) {
        if (!current || typeof current !== "object" || !(segment in current)) {
            return fallback;
        }
        current = current[segment];
    }
    return current ?? fallback;
}

let activeRequestCount = 0;
let requestProgressTimer = null;
let requestProgressValue = 0;

function getSessionValue(key) {
    try {
        return window.sessionStorage.getItem(key) || "";
    } catch (_error) {
        return "";
    }
}

function setSessionValue(key, value) {
    try {
        window.sessionStorage.setItem(key, String(value ?? ""));
    } catch (_error) {
        // Ignore storage failures in locked-down browsers.
    }
}

function syncShellOffsets() {
    const navbar = document.querySelector(".alfred-navbar");
    const height = navbar ? navbar.offsetHeight : 78;
    document.documentElement.style.setProperty("--alfred-nav-height", `${Math.max(height, 64)}px`);
}

function getGlobalProgressElements() {
    const root = document.getElementById("alfredTopProgress");
    if (!root) {
        return {};
    }
    return {
        root,
        bar: root.querySelector(".alfred-top-progress-bar"),
    };
}

function paintGlobalProgress(value) {
    const { bar } = getGlobalProgressElements();
    if (!bar) {
        return;
    }
    bar.style.transform = `scaleX(${Math.max(0, Math.min(Number(value || 0), 100)) / 100})`;
}

function startGlobalProgressTicker() {
    if (requestProgressTimer) {
        return;
    }
    requestProgressTimer = window.setInterval(() => {
        if (activeRequestCount <= 0) {
            return;
        }
        requestProgressValue = Math.min(88, requestProgressValue + Math.max(1.5, (88 - requestProgressValue) * 0.16));
        paintGlobalProgress(requestProgressValue);
    }, 120);
}

function stopGlobalProgressTicker() {
    if (!requestProgressTimer) {
        return;
    }
    window.clearInterval(requestProgressTimer);
    requestProgressTimer = null;
}

function beginGlobalProgress() {
    const { root } = getGlobalProgressElements();
    activeRequestCount += 1;
    if (!root || activeRequestCount !== 1) {
        return;
    }
    requestProgressValue = 12;
    root.classList.remove("is-complete");
    root.classList.add("is-visible");
    paintGlobalProgress(requestProgressValue);
    startGlobalProgressTicker();
}

function endGlobalProgress() {
    const { root } = getGlobalProgressElements();
    activeRequestCount = Math.max(0, activeRequestCount - 1);
    if (!root || activeRequestCount > 0) {
        return;
    }
    stopGlobalProgressTicker();
    requestProgressValue = 100;
    paintGlobalProgress(requestProgressValue);
    root.classList.add("is-complete");
    window.setTimeout(() => {
        if (activeRequestCount > 0) {
            return;
        }
        root.classList.remove("is-visible", "is-complete");
        requestProgressValue = 0;
        paintGlobalProgress(0);
    }, 280);
}

function ensurePageBusyIndicator(root, label, options = {}) {
    if (options.mode !== "upload") {
        return null;
    }
    if (!root) {
        return null;
    }
    let indicator = root.querySelector("[data-alfred-page-progress]");
    if (!indicator) {
        indicator = document.createElement("div");
        indicator.className = "alfred-page-progress";
        indicator.dataset.alfredPageProgress = "true";
        indicator.innerHTML = `
            <div class="alfred-page-progress-copy"></div>
            <div class="alfred-page-progress-track">
                <div class="alfred-page-progress-bar"></div>
            </div>
        `;
        root.prepend(indicator);
    }
    const copy = indicator.querySelector(".alfred-page-progress-copy");
    if (copy) {
        copy.textContent = label || "Loading data";
    }
    return indicator;
}

function setPageBusy(rootId, busy, options = {}) {
    const root = resolveElement(rootId);
    if (!root) {
        return;
    }
    root.dataset.pageBusy = busy ? "true" : "false";
    const indicator = ensurePageBusyIndicator(root, options.label || "", options);
    if (!indicator) {
        return;
    }

    if (busy) {
        indicator.classList.remove("is-complete");
        indicator.classList.add("is-visible");
        return;
    }

    indicator.classList.add("is-complete");
    window.setTimeout(() => {
        if (root.dataset.pageBusy === "true") {
            return;
        }
        indicator.classList.remove("is-visible", "is-complete");
    }, 260);
}

function installInteractiveSurfaceMotion() {
    if (window.__alfredSurfaceMotionInstalled) {
        return;
    }
    window.__alfredSurfaceMotionInstalled = true;
    const selector = ".surface-card, .metric-card, .auth-panel, .auth-hero, .status-card, .alfred-hero, .card";

    document.addEventListener("pointermove", event => {
        const surface = event.target instanceof Element ? event.target.closest(selector) : null;
        if (!surface) {
            return;
        }
        const bounds = surface.getBoundingClientRect();
        const x = ((event.clientX - bounds.left) / Math.max(bounds.width, 1)) * 100;
        const y = ((event.clientY - bounds.top) / Math.max(bounds.height, 1)) * 100;
        surface.style.setProperty("--pointer-x", `${Math.max(0, Math.min(x, 100)).toFixed(2)}%`);
        surface.style.setProperty("--pointer-y", `${Math.max(0, Math.min(y, 100)).toFixed(2)}%`);
        surface.classList.add("is-surface-active");
    });

    document.addEventListener("pointerout", event => {
        const surface = event.target instanceof Element ? event.target.closest(selector) : null;
        if (!surface) {
            return;
        }
        const related = event.relatedTarget instanceof Element ? event.relatedTarget.closest(selector) : null;
        if (related === surface) {
            return;
        }
        surface.classList.remove("is-surface-active");
    });
}

function installNavAnchorPersistence() {
    if (window.__alfredNavAnchorInstalled) {
        return;
    }
    window.__alfredNavAnchorInstalled = true;

    const sidebar = document.querySelector(".alfred-sidebar");
    if (!sidebar) {
        return;
    }

    const restoreSidebarPosition = () => {
        const savedTop = Number(getSessionValue(NAV_SCROLL_STORAGE_KEY) || 0);
        if (Number.isFinite(savedTop) && savedTop > 0) {
            sidebar.scrollTop = savedTop;
        }

        const savedHref = getSessionValue(NAV_ACTIVE_LINK_STORAGE_KEY);
        const links = Array.from(sidebar.querySelectorAll("a.nav-link"));
        const targetLink = links.find(link => (link.getAttribute("href") || "") === savedHref)
            || sidebar.querySelector("a.nav-link.active");
        if (targetLink instanceof HTMLElement) {
            window.requestAnimationFrame(() => {
                targetLink.scrollIntoView({ block: "nearest", inline: "nearest" });
            });
        }
    };

    restoreSidebarPosition();
    sidebar.addEventListener("scroll", () => {
        setSessionValue(NAV_SCROLL_STORAGE_KEY, Math.round(sidebar.scrollTop));
    }, { passive: true });

    sidebar.querySelectorAll("a.nav-link").forEach(link => {
        if (link.dataset.navAnchorBound === "true") {
            return;
        }
        link.dataset.navAnchorBound = "true";
        link.addEventListener("click", () => {
            setSessionValue(NAV_SCROLL_STORAGE_KEY, Math.round(sidebar.scrollTop));
            setSessionValue(NAV_ACTIVE_LINK_STORAGE_KEY, link.getAttribute("href") || "");
        });
    });
}

function fetchJSON(url, options = {}) {
    const config = {
        credentials: "same-origin",
        headers: { ...(options.headers || {}) },
        ...options,
    };

    if (!(config.body instanceof FormData) && !config.headers["Content-Type"] && config.body) {
        config.headers["Content-Type"] = "application/json";
    }

    if (!["GET", "HEAD", "OPTIONS", undefined].includes(config.method)) {
        config.headers["X-CSRFToken"] = getCookie("csrftoken");
    }

    beginGlobalProgress();
    return fetch(url, config)
        .then(async response => {
            const payload = await response.json().catch(() => ({}));
            if (!response.ok) {
                throw new Error(payload.detail || payload.error || payload.message || "Request failed.");
            }
            return payload;
        })
        .finally(() => {
            endGlobalProgress();
        });
}

function formatCurrency(value) {
    return new Intl.NumberFormat("en-IN", {
        style: "currency",
        currency: "INR",
        maximumFractionDigits: 2,
    }).format(Number(value || 0));
}

function formatPercent(value) {
    return `${Number(value || 0).toFixed(1)}%`;
}

function formatDate(value) {
    return new Date(`${value}T00:00:00`).toLocaleDateString("en-IN", {
        day: "2-digit",
        month: "short",
        year: "numeric",
    });
}

function formatDateTime(value) {
    return new Date(value).toLocaleString("en-IN", {
        day: "2-digit",
        month: "short",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
    });
}

function formatNumber(value, maximumFractionDigits = 1) {
    return new Intl.NumberFormat("en-IN", {
        maximumFractionDigits,
    }).format(Number(value || 0));
}

function escapeHtml(value) {
    return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll("\"", "&quot;")
        .replaceAll("'", "&#39;");
}

const clientIssueRegistry = new Map();
const SESSION_REFRESH_THROTTLE_MS = 60000;

function formatSessionCountdown(totalSeconds) {
    const seconds = Math.max(0, Math.floor(Number(totalSeconds || 0)));
    const minutes = Math.floor(seconds / 60);
    const remainder = seconds % 60;
    return `${minutes}:${String(remainder).padStart(2, "0")}`;
}

function installSessionSecurityTimer() {
    if (window.__alfredSessionTimerInstalled || document.body.dataset.authenticated !== "true") {
        return;
    }

    const timer = document.querySelector("[data-session-timer]");
    const countdown = timer?.querySelector("[data-session-countdown]");
    const timeoutSeconds = Number(document.body.dataset.sessionTimeoutSeconds || 0);
    if (!timer || !countdown || !Number.isFinite(timeoutSeconds) || timeoutSeconds <= 0) {
        return;
    }

    window.__alfredSessionTimerInstalled = true;
    timer.hidden = false;

    const warningSeconds = Math.max(0, Math.min(Number(document.body.dataset.sessionWarningSeconds || 0), timeoutSeconds));
    const pingUrl = document.body.dataset.sessionPingUrl || "/api/session/ping/";
    const logoutUrl = document.body.dataset.logoutUrl || "/logout/";
    const loginUrl = document.body.dataset.loginUrl || "/login/";
    const refreshThrottleMs = Math.min(SESSION_REFRESH_THROTTLE_MS, Math.max(15000, (timeoutSeconds * 1000) / 3));
    let sessionTimeoutSeconds = timeoutSeconds;
    let sessionWarningSeconds = warningSeconds;
    let expiresAt = Date.now() + sessionTimeoutSeconds * 1000;
    let lastRefreshAt = 0;
    let expired = false;

    function renderSessionState() {
        const remainingSeconds = Math.ceil((expiresAt - Date.now()) / 1000);
        countdown.textContent = formatSessionCountdown(remainingSeconds);
        timer.classList.toggle("is-warning", remainingSeconds > 0 && remainingSeconds <= sessionWarningSeconds);
        timer.classList.toggle("is-expired", remainingSeconds <= 0);
        if (remainingSeconds <= 0) {
            expireSession();
        }
    }

    function applySessionPayload(payload = {}) {
        const nextTimeout = Number(payload.timeout_seconds || sessionTimeoutSeconds);
        const nextWarning = Number(payload.warning_seconds || sessionWarningSeconds);
        if (Number.isFinite(nextTimeout) && nextTimeout > 0) {
            sessionTimeoutSeconds = nextTimeout;
        }
        if (Number.isFinite(nextWarning) && nextWarning >= 0) {
            sessionWarningSeconds = Math.min(nextWarning, sessionTimeoutSeconds);
        }
        expiresAt = Date.now() + sessionTimeoutSeconds * 1000;
        renderSessionState();
    }

    function refreshSession() {
        const now = Date.now();
        if (expired || now - lastRefreshAt < refreshThrottleMs) {
            return;
        }
        lastRefreshAt = now;
        fetch(pingUrl, {
            method: "POST",
            credentials: "same-origin",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": getCookie("csrftoken"),
            },
            body: JSON.stringify({}),
        })
            .then(async response => {
                if (response.redirected || response.status === 401 || response.status === 403) {
                    expireSession();
                    return null;
                }
                if (!response.ok) {
                    return null;
                }
                return response.json().catch(() => null);
            })
            .then(payload => {
                if (payload) {
                    applySessionPayload(payload);
                }
            })
            .catch(() => {});
    }

    function handleActivity() {
        if (expired) {
            return;
        }
        expiresAt = Date.now() + sessionTimeoutSeconds * 1000;
        renderSessionState();
        refreshSession();
    }

    function expireSession() {
        if (expired) {
            return;
        }
        expired = true;
        timer.classList.add("is-expired");
        countdown.textContent = "0:00";
        fetch(logoutUrl, {
            method: "POST",
            credentials: "same-origin",
            keepalive: true,
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": getCookie("csrftoken"),
            },
            body: JSON.stringify({}),
        }).finally(() => {
            window.location.assign(loginUrl);
        });
    }

    ["click", "keydown", "pointerdown", "touchstart"].forEach(eventName => {
        document.addEventListener(eventName, handleActivity, { passive: true });
    });
    document.addEventListener("scroll", handleActivity, { capture: true, passive: true });

    renderSessionState();
    window.setInterval(renderSessionState, 1000);
}

const liveRefreshRegistry = new Map();
const liveRefreshGuardRegistry = new WeakMap();

function isEditableElement(element) {
    if (!element) {
        return false;
    }
    return ["INPUT", "TEXTAREA", "SELECT"].includes(element.tagName) || Boolean(element.isContentEditable);
}

function lockLiveRefresh(root, durationMs = 3000) {
    if (!root) {
        return;
    }
    const currentUntil = Number(root.dataset.liveRefreshLockedUntil || 0);
    const nextUntil = Date.now() + Number(durationMs || 0);
    root.dataset.liveRefreshLockedUntil = String(Math.max(currentUntil, nextUntil));
}

function installLiveRefreshGuards(root, options = {}) {
    if (!root || liveRefreshGuardRegistry.has(root)) {
        return;
    }

    const holdMs = Number(options.interactionHoldMs || 3200);
    const shouldLockTarget = target => {
        if (!(target instanceof Element)) {
            return false;
        }
        return Boolean(
            target.closest(
                "form, details, summary, select, input, textarea, button, label, [role='button'], [data-live-refresh-hold], .dropdown, .dropdown-menu, .dropdown-toggle"
            )
        );
    };
    const lock = event => {
        if (!root.contains(event.target) || !shouldLockTarget(event.target)) {
            return;
        }
        lockLiveRefresh(root, holdMs);
    };
    const extendForTyping = event => {
        if (!root.contains(event.target) || !isEditableElement(event.target)) {
            return;
        }
        lockLiveRefresh(root, Math.max(holdMs, 4500));
    };

    root.addEventListener("pointerdown", lock, true);
    root.addEventListener("click", lock, true);
    root.addEventListener("focusin", lock, true);
    root.addEventListener("change", lock, true);
    root.addEventListener("keydown", extendForTyping, true);
    root.addEventListener("input", extendForTyping, true);
    root.addEventListener("toggle", lock, true);
    liveRefreshGuardRegistry.set(root, { holdMs });
}

function shouldPauseLiveRefresh(root) {
    if (document.hidden) {
        return true;
    }
    if (document.querySelector(".modal.show")) {
        return true;
    }
    if (root && Number(root.dataset.liveRefreshLockedUntil || 0) > Date.now()) {
        return true;
    }
    if (root && root.querySelector("details[open], .dropdown-menu.show, [data-live-refresh-busy='true']")) {
        return true;
    }
    const active = document.activeElement;
    if (!isEditableElement(active)) {
        return false;
    }
    if (!root) {
        return true;
    }
    return root.contains(active);
}

function enableLiveRefresh(key, loadFn, options = {}) {
    const intervalMs = Number(options.intervalMs || 1000);
    const rootId = options.rootId || "";
    disableLiveRefresh(key);

    let inFlight = false;
    const tick = () => {
        const root = rootId ? document.getElementById(rootId) : document.body;
        if (rootId && !root) {
            disableLiveRefresh(key);
            return;
        }
        installLiveRefreshGuards(root, options);
        if (inFlight || shouldPauseLiveRefresh(root)) {
            return;
        }
        inFlight = true;
        Promise.resolve(loadFn({ live: true }))
            .catch(() => {})
            .finally(() => {
                inFlight = false;
            });
    };

    const timer = window.setInterval(tick, intervalMs);
    liveRefreshRegistry.set(key, timer);
}

function disableLiveRefresh(key) {
    const timer = liveRefreshRegistry.get(key);
    if (timer) {
        window.clearInterval(timer);
        liveRefreshRegistry.delete(key);
    }
}

function upsertPageAlert(rootId, message, tone = "danger") {
    const root = rootId ? document.getElementById(rootId) : null;
    if (!root) {
        return;
    }
    let alert = root.querySelector("[data-alfred-page-alert]");
    if (!alert) {
        alert = document.createElement("div");
        alert.dataset.alfredPageAlert = "true";
        alert.className = `alert alert-${tone} mt-4 mb-0`;
        root.appendChild(alert);
    }
    alert.className = `alert alert-${tone} mt-4 mb-0`;
    alert.textContent = message;
}

function clearPageAlert(rootId) {
    const root = rootId ? document.getElementById(rootId) : null;
    const alert = root ? root.querySelector("[data-alfred-page-alert]") : null;
    if (alert) {
        alert.remove();
    }
}

function resolveElement(target) {
    if (!target) {
        return null;
    }
    if (typeof target === "string") {
        return document.getElementById(target);
    }
    return target instanceof Element ? target : null;
}

function setTextIfChanged(target, value) {
    const node = resolveElement(target);
    if (!node) {
        return;
    }
    const nextValue = String(value ?? "");
    if (node.textContent !== nextValue) {
        node.textContent = nextValue;
    }
}

function setHTMLIfChanged(target, html) {
    const node = resolveElement(target);
    if (!node) {
        return;
    }
    const nextHtml = String(html ?? "");
    if (node.innerHTML !== nextHtml) {
        node.innerHTML = nextHtml;
    }
}

function setDisabledIfChanged(target, disabled) {
    const node = resolveElement(target);
    if (!node) {
        return;
    }
    const nextValue = Boolean(disabled);
    if (node.disabled !== nextValue) {
        node.disabled = nextValue;
    }
}

function syncSelectOptions(target, items, options = {}) {
    const select = resolveElement(target);
    if (!select) {
        return;
    }
    const previousValue = String(options.currentValue ?? select.value ?? "");
    const includeBlank = options.includeBlank !== false;
    const blankLabel = options.blankLabel ?? "";
    const preferredValue = String(options.preferredValue ?? "");
    const entries = Array.isArray(items) ? items : [];
    const optionHtml = [];
    if (includeBlank) {
        optionHtml.push(`<option value="">${escapeHtml(blankLabel)}</option>`);
    }
    entries.forEach(item => {
        const value = String(options.getValue ? options.getValue(item) : item?.value ?? "");
        const label = String(options.getLabel ? options.getLabel(item) : item?.label ?? value);
        optionHtml.push(`<option value="${escapeHtml(value)}">${escapeHtml(label)}</option>`);
    });
    setHTMLIfChanged(select, optionHtml.join(""));

    const candidateValues = new Set(entries.map(item => String(options.getValue ? options.getValue(item) : item?.value ?? "")));
    const fallbackValue = entries.length
        ? String(options.fallbackValue ?? (options.getValue ? options.getValue(entries[0]) : entries[0]?.value ?? ""))
        : "";
    const nextValue = candidateValues.has(previousValue)
        ? previousValue
        : (preferredValue && candidateValues.has(preferredValue) ? preferredValue : fallbackValue);
    if (select.value !== nextValue) {
        select.value = nextValue;
    }
    setDisabledIfChanged(select, Boolean(options.disableWhenEmpty && !entries.length));
}

function buildSingleFileFormData(form, fileFieldName, file) {
    const payload = new FormData(form);
    payload.delete(fileFieldName);
    payload.append(fileFieldName, file);
    return payload;
}

function uploadLogForPhase(phase) {
    switch (phase) {
        case "preparing":
            return "Preparing secure upload right now";
        case "uploading":
            return "Sending document to Alfred now";
        case "processing":
            return "Waiting for parser response now";
        case "success":
            return "Upload finished, syncing workspace now";
        case "error":
            return "Upload failed, review status now";
        default:
            return "Preparing secure upload right now";
    }
}

function showUploadProgress(target, state = {}) {
    const host = resolveElement(target);
    if (!host) {
        return;
    }

    const percent = Math.max(0, Math.min(Math.round(Number(state.percent || 0)), 100));
    const current = Number(state.current || 1);
    const total = Math.max(1, Number(state.total || 1));
    const label = total > 1 ? `File ${current} of ${total}` : "Document upload";
    const log = state.log || uploadLogForPhase(state.phase);
    const spacingClasses = Array.from(host.classList).filter(className => /^m[trblxy]?-\d+$/.test(className));

    host.className = ["alfred-upload-progress-host", ...spacingClasses].join(" ").trim();
    host.innerHTML = `
        <div class="alfred-upload-progress" role="status" aria-live="polite">
            <div class="alfred-upload-progress-head">
                <span class="alfred-upload-progress-label">${escapeHtml(label)}</span>
                <span class="alfred-upload-progress-percent">${percent}%</span>
            </div>
            <div class="alfred-upload-progress-row">
                <div class="alfred-upload-progress-track">
                    <div class="alfred-upload-progress-bar" style="transform: scaleX(${percent / 100});"></div>
                </div>
                <div class="alfred-upload-progress-log">${escapeHtml(log)}</div>
            </div>
        </div>
    `;
}

function uploadJSON(url, options = {}) {
    const config = {
        method: options.method || "POST",
        headers: { ...(options.headers || {}) },
        body: options.body || null,
    };

    if (!(config.body instanceof FormData)) {
        return fetchJSON(url, options);
    }

    if (!["GET", "HEAD", "OPTIONS", undefined].includes(config.method)) {
        config.headers["X-CSRFToken"] = getCookie("csrftoken");
    }

    beginGlobalProgress();
    return new Promise((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        xhr.open(config.method || "POST", url, true);
        xhr.withCredentials = true;
        Object.entries(config.headers).forEach(([key, value]) => {
            if (value != null) {
                xhr.setRequestHeader(key, value);
            }
        });

        options.onUploadState?.({ phase: "preparing", percent: 0 });

        xhr.upload.addEventListener("progress", event => {
            if (!event.lengthComputable) {
                return;
            }
            const percent = Math.max(1, Math.min(Math.round((event.loaded / Math.max(event.total, 1)) * 100), 100));
            options.onUploadState?.({
                phase: "uploading",
                percent,
                loaded: event.loaded,
                total: event.total,
            });
        });

        xhr.upload.addEventListener("load", () => {
            options.onUploadState?.({ phase: "processing", percent: 100 });
        });

        xhr.addEventListener("load", () => {
            let payload = {};
            try {
                payload = xhr.responseText ? JSON.parse(xhr.responseText) : {};
            } catch (_error) {
                payload = {};
            }
            if (xhr.status >= 200 && xhr.status < 300) {
                resolve(payload);
                return;
            }
            reject(new Error(payload.detail || payload.error || payload.message || "Request failed."));
        });

        xhr.addEventListener("error", () => {
            reject(new Error("Request failed."));
        });

        xhr.addEventListener("abort", () => {
            reject(new Error("Upload was cancelled."));
        });

        xhr.send(config.body);
    }).finally(() => {
        endGlobalProgress();
    });
}

async function uploadFilesSequentially(files, uploadFile, options = {}) {
    const results = [];
    const items = Array.from(files || []).filter(Boolean);
    const total = items.length;
    const emitProgress = state => {
        if (typeof options.onProgress === "function") {
            options.onProgress({
                total,
                ...state,
                log: state.log || uploadLogForPhase(state.phase),
            });
        }
    };

    for (let index = 0; index < items.length; index += 1) {
        const file = items[index];
        emitProgress({
            phase: "preparing",
            current: index + 1,
            fileName: file.name,
            percent: Math.round((index / Math.max(total, 1)) * 100),
        });
        try {
            const data = await uploadFile(file, {
                index,
                total,
                reportProgress(progress = {}) {
                    const filePercent = Math.max(0, Math.min(Number(progress.percent || 0), 100));
                    const overallPercent = Math.round((((index) + (filePercent / 100)) / Math.max(total, 1)) * 100);
                    emitProgress({
                        phase: progress.phase || (filePercent >= 100 ? "processing" : "uploading"),
                        current: index + 1,
                        fileName: file.name,
                        percent: overallPercent,
                        filePercent,
                    });
                },
            });
            emitProgress({
                phase: "success",
                current: index + 1,
                fileName: file.name,
                percent: Math.round(((index + 1) / Math.max(total, 1)) * 100),
            });
            results.push({ file, ok: true, data });
        } catch (error) {
            emitProgress({
                phase: "error",
                current: index + 1,
                fileName: file.name,
                percent: Math.round(((index + 1) / Math.max(total, 1)) * 100),
            });
            results.push({ file, ok: false, error: error?.message || "Request failed." });
        }
    }
    return results;
}

function summarizeUploadBatch(results, options = {}) {
    const itemLabel = options.itemLabel || "file";
    const successVerb = options.successVerb || "processed";
    const succeeded = results.filter(result => result.ok);
    const failed = results.filter(result => !result.ok);
    const total = results.length;
    const label = `${itemLabel}${total === 1 ? "" : "s"}`;
    let message = `${succeeded.length}/${total} ${label} ${successVerb}.`;

    if (failed.length) {
        const failureDetails = failed
            .slice(0, 3)
            .map(result => `${result.file?.name || "File"}: ${result.error}`)
            .join(" | ");
        message += ` ${failed.length} failed.${failureDetails ? ` ${failureDetails}` : ""}`;
    }

    return {
        total,
        succeeded,
        failed,
        tone: failed.length ? (succeeded.length ? "warning" : "danger") : "success",
        message,
    };
}

function installUserDataResetAction() {
    const button = document.getElementById("navbarClearDataBtn");
    if (!button || button.dataset.bound === "true") {
        return;
    }

    button.dataset.bound = "true";
    button.addEventListener("click", () => {
        if (!window.confirm(getUiConfig("prompts.remove_data_confirm", "Remove all Alfred data for this account, including uploaded documents and cached summaries? Your login stays active, and you can start fresh afterward."))) {
            return;
        }

        const originalLabel = button.textContent;
        button.disabled = true;
        button.textContent = "Removing...";

        fetchJSON("/api/users/profile/clear-data/", {
            method: "POST",
            body: JSON.stringify({}),
        })
            .then(data => {
                window.alert(data.detail || getUiConfig("prompts.remove_data_success", "Your Alfred data has been removed."));
                window.location.assign(document.body.dataset.homeUrl || "/");
            })
            .catch(error => {
                window.alert(error.message || getUiConfig("prompts.remove_data_failure", "Could not remove your Alfred data."));
            })
            .finally(() => {
                button.disabled = false;
                button.textContent = originalLabel;
            });
    });
}

function installMlRuntimeBanner() {
    const host = document.getElementById("alfredMlRuntimeBannerHost");
    if (!host || document.body.dataset.authenticated !== "true") {
        return;
    }

    fetchJSON("/api/ai/runtime-status/")
        .then(payload => {
            renderMlRuntimeBanner(host, payload || {});
        })
        .catch(() => {
            host.innerHTML = "";
        });
}

function renderMlRuntimeBanner(host, payload) {
    const canManage = Boolean(payload.can_manage);
    const setupState = String(payload.setup_state || "");
    const runtime = payload.runtime || {};
    const approval = payload.approval || {};
    const recommendedSteps = Array.isArray(payload.recommended_steps) ? payload.recommended_steps : [];
    const sklearnReady = Boolean(runtime.sklearn_ready);
    const showSklearnGuidance = Boolean(approval.granted && runtime.ready && !sklearnReady);

    if (!canManage || (setupState === "ready" && !showSklearnGuidance) || setupState === "disabled") {
        host.innerHTML = "";
        return;
    }

    const tone = (setupState === "runtime_blocked" || showSklearnGuidance) ? "warning" : "info";
    const title = setupState === "awaiting_approval"
        ? getUiConfig("ml_runtime.banner.approval_title", "ALFRED ML startup needs first-run approval")
        : getUiConfig("ml_runtime.banner.runtime_title", "ALFRED ML runtime needs attention");
    const body = setupState === "awaiting_approval"
        ? getUiConfig("ml_runtime.banner.approval_body", "Approve startup auto-training once. After that, ALFRED can run training automatically on future startups when the local runtime is healthy.")
        : getUiConfig("ml_runtime.banner.runtime_body", "Training can still use the built-in Alfred fallback models, but scikit-learn-backed training needs the local Windows policy to allow its native files.");
    const approvalMeta = approval.granted
        ? `<div class="small muted mt-2">Approved by ${escapeHtml(approval.approved_by || "superuser")}${approval.approved_at ? ` on ${escapeHtml(formatDateTime(approval.approved_at))}` : ""}.</div>`
        : "";
    const runtimeMeta = runtime.reason
        ? `<div class="small muted mt-2"><strong>${escapeHtml(getUiConfig("ml_runtime.banner.runtime_detail_label", "Runtime detail"))}:</strong> ${escapeHtml(runtime.reason)}</div>`
        : "";
    const sklearnMeta = approval.granted
        ? `<div class="small muted mt-2"><strong>${escapeHtml(getUiConfig("ml_runtime.banner.sklearn_status_label", "Scikit-learn backend"))}:</strong> ${escapeHtml(sklearnReady ? "ready" : (runtime.sklearn_reason || "blocked or unavailable"))}</div>`
        : "";
    const steps = recommendedSteps.length
        ? `<ul class="mb-0 mt-2">${recommendedSteps.map(step => `<li>${escapeHtml(step)}</li>`).join("")}</ul>`
        : "";
    const sklearnDetails = `
        <details class="mt-2">
            <summary class="fw-semibold">${escapeHtml(getUiConfig("ml_runtime.banner.help_open_label", "Why scikit-learn?"))}</summary>
            <div class="small mt-2">${escapeHtml(getUiConfig("ml_runtime.banner.sklearn_body", "ALFRED prefers scikit-learn for classic tabular model training because it is stable, explainable, and well-suited for salary, risk, parser-confidence, and relationship-style estimators. If Windows blocks sklearn DLLs, Alfred falls back to lighter in-repo models so the app still works."))}</div>
        </details>
    `;
    const actions = `
        <div class="d-flex flex-wrap gap-2 mt-3">
            ${!approval.granted ? `<button type="button" class="btn btn-sm btn-primary" data-ml-runtime-action="approve">${escapeHtml(getUiConfig("ml_runtime.banner.approve_label", "Approve Auto-Training"))}</button>` : ""}
            ${approval.granted && runtime.ready ? `<button type="button" class="btn btn-sm btn-outline-primary" data-ml-runtime-action="run_now">${escapeHtml(getUiConfig("ml_runtime.banner.run_now_label", "Run Initial Training Now"))}</button>` : ""}
            ${approval.granted ? `<button type="button" class="btn btn-sm btn-outline-secondary" data-ml-runtime-action="revoke">${escapeHtml(getUiConfig("ml_runtime.banner.revoke_label", "Revoke Approval"))}</button>` : ""}
        </div>
    `;

    host.innerHTML = `
        <div class="alert alert-${tone} d-flex flex-column gap-2" data-ml-runtime-banner="true">
            <div class="fw-semibold">${escapeHtml(title)}</div>
            <div>${escapeHtml(body)}</div>
            ${approvalMeta}
            ${runtimeMeta}
            ${sklearnMeta}
            ${steps}
            ${sklearnDetails}
            ${actions}
        </div>
    `;
    host.querySelectorAll("[data-ml-runtime-action]").forEach(button => {
        if (button.dataset.bound === "true") {
            return;
        }
        button.dataset.bound = "true";
        button.addEventListener("click", () => handleMlRuntimeAction(button.dataset.mlRuntimeAction, host));
    });
}

function handleMlRuntimeAction(action, host) {
    const buttons = Array.from(host.querySelectorAll("[data-ml-runtime-action]"));
    buttons.forEach(button => {
        button.disabled = true;
    });
    fetchJSON("/api/ai/runtime-control/", {
        method: "POST",
        body: JSON.stringify({ action }),
    })
        .then(data => {
            if (data.detail) {
                window.alert(data.detail);
            }
            if (data.status) {
                renderMlRuntimeBanner(host, data.status);
            } else {
                return fetchJSON("/api/ai/runtime-status/").then(payload => renderMlRuntimeBanner(host, payload || {}));
            }
        })
        .catch(error => {
            window.alert(error.message || "Could not update ALFRED ML runtime settings.");
        })
        .finally(() => {
            buttons.forEach(button => {
                button.disabled = false;
            });
        });
}

function logClientIssue(issue = {}) {
    if (!document.querySelector(".alfred-layout")) {
        return Promise.resolve();
    }

    const payload = {
        module: issue.module || "frontend",
        category: issue.category || "visualization",
        scope: issue.scope || "",
        event_type: issue.eventType || issue.event_type || "client_issue",
        severity: issue.severity || "warning",
        document_id: issue.documentId || issue.document_id || null,
        file_name: issue.fileName || issue.file_name || "",
        message: issue.message || "Client issue logged.",
        payload: {
            page_context: document.body.dataset.shellMode || "unknown",
            ...(issue.payload || {}),
        },
    };

    const signature = JSON.stringify([
        payload.module,
        payload.category,
        payload.scope,
        payload.event_type,
        payload.message,
        payload.payload.page_context,
    ]);
    const now = Date.now();
    const lastSentAt = clientIssueRegistry.get(signature) || 0;
    if (now - lastSentAt < 15000) {
        return Promise.resolve();
    }
    clientIssueRegistry.set(signature, now);

    return fetch("/api/operational/logs/client/", {
        method: "POST",
        credentials: "same-origin",
        keepalive: true,
        headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": getCookie("csrftoken"),
        },
        body: JSON.stringify(payload),
    }).catch(() => {});
}

function installClientDiagnostics() {
    if (window.__alfredClientDiagnosticsInstalled || !document.querySelector(".alfred-layout")) {
        return;
    }
    window.__alfredClientDiagnosticsInstalled = true;

    window.addEventListener("error", event => {
        const target = event.target;
        if (target && target !== window) {
            logClientIssue({
                module: "frontend",
                category: "visualization",
                eventType: "asset_error",
                severity: "warning",
                message: `Asset failed to load: ${target.tagName || "unknown asset"}`,
            });
            return;
        }
        logClientIssue({
            module: "frontend",
            category: "visualization",
            eventType: "runtime_error",
            severity: "error",
            message: event.message || "Unhandled client runtime error.",
            payload: {
                source: event.filename ? "browser-script" : "",
                line: event.lineno || 0,
                column: event.colno || 0,
            },
        });
    }, true);

    window.addEventListener("unhandledrejection", event => {
        logClientIssue({
            module: "frontend",
            category: "visualization",
            eventType: "promise_rejection",
            severity: "error",
            message: event.reason?.message || String(event.reason || "Unhandled promise rejection."),
        });
    });
}

installUserDataResetAction();
installSessionSecurityTimer();
installMlRuntimeBanner();
installClientDiagnostics();
syncShellOffsets();
installInteractiveSurfaceMotion();
installNavAnchorPersistence();
window.addEventListener("resize", syncShellOffsets);

window.Alfred = {
    fetchJSON,
    uploadJSON,
    formatCurrency,
    formatPercent,
    formatDate,
    formatDateTime,
    formatNumber,
    escapeHtml,
    enableLiveRefresh,
    disableLiveRefresh,
    upsertPageAlert,
    clearPageAlert,
    buildSingleFileFormData,
    showUploadProgress,
    lockLiveRefresh,
    logClientIssue,
    installSessionSecurityTimer,
    setDisabledIfChanged,
    setHTMLIfChanged,
    setTextIfChanged,
    syncSelectOptions,
    uploadFilesSequentially,
    summarizeUploadBatch,
    getUiConfig,
    setPageBusy,
    syncShellOffsets,
};
