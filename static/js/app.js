function getCookie(name) {
    const cookieValue = document.cookie
        .split(";")
        .map(item => item.trim())
        .find(item => item.startsWith(`${name}=`));
    return cookieValue ? decodeURIComponent(cookieValue.split("=")[1]) : "";
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

    return fetch(url, config).then(async response => {
        const payload = await response.json().catch(() => ({}));
        if (!response.ok) {
            throw new Error(payload.detail || payload.error || payload.message || "Request failed.");
        }
        return payload;
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

const liveRefreshRegistry = new Map();

function isEditableElement(element) {
    if (!element) {
        return false;
    }
    return ["INPUT", "TEXTAREA", "SELECT"].includes(element.tagName) || Boolean(element.isContentEditable);
}

function shouldPauseLiveRefresh(root) {
    if (document.hidden) {
        return true;
    }
    if (document.querySelector(".modal.show")) {
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

window.Alfred = {
    fetchJSON,
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
};
