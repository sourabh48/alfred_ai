document.addEventListener("DOMContentLoaded", () => {
    const root = document.getElementById("projectDetailsRoot");
    if (!root) {
        return;
    }
    loadProjectDetails();
    Alfred.enableLiveRefresh("project-details-live", loadProjectDetails, { rootId: "projectDetailsRoot", interactionHoldMs: 4200 });
});

function loadProjectDetails() {
    const root = document.getElementById("projectDetailsRoot");
    if (!root) {
        return Promise.resolve();
    }
    const apiUrl = root.dataset.projectDetailsApi || "/api/project-details/";
    return Alfred.fetchJSON(apiUrl)
        .then(payload => {
            renderClock(payload.clock || {});
            renderSummaryCards(payload.summary_cards || []);
            renderOperationalMetrics(payload.operational_metrics || []);
            renderLearningSnapshot(payload.learning_snapshot || {});
            renderInProgressTracks(payload.in_progress_tracks || []);
            renderCompletedTracks(payload.completed_tracks || []);
            renderReportRows("projectDetailsReportLibrary", payload.report_library || [], item => `
                <div class="data-row">
                    <div class="data-label">${Alfred.escapeHtml(formatDateTimeValue(item.created_at))}</div>
                    <div class="data-value">${Alfred.escapeHtml(item.file_path || "")}</div>
                </div>
            `, "No generated report artifacts are stored yet.");
            renderReportRows("projectDetailsDeveloperQueue", payload.developer_queue || [], item => `
                <div class="data-row">
                    <div class="data-label">${Alfred.escapeHtml(`${item.username || ""} | ${item.module || ""} | ${item.severity || ""}`)}</div>
                    <div class="data-value">${Alfred.escapeHtml(item.title || "")} <span class="muted small">${Alfred.escapeHtml(formatDateTimeValue(item.created_at))}</span></div>
                </div>
            `, "No open developer escalations are waiting right now.");
            renderReportRows("projectDetailsAutoTicketActivity", payload.auto_ticket_activity || [], item => `
                <div class="data-row">
                    <div class="data-label">${Alfred.escapeHtml(`${item.module || ""} | ${formatDateTimeValue(item.created_at)}`)}</div>
                    <div class="data-value">${Alfred.escapeHtml(item.title || "")} <span class="muted small">${Alfred.escapeHtml(item.resolution_summary || "")}</span></div>
                </div>
            `, "No ALFRED auto-resolutions are stored yet.");
            Alfred.clearPageAlert("projectDetailsRoot");
        })
        .catch(error => {
            Alfred.upsertPageAlert("projectDetailsRoot", error.message || "Unable to refresh project details.");
        });
}

function renderClock(clock) {
    setText("projectDetailsClockTime", clock.local_time || "--:--");
    setText("projectDetailsClockLabel", `${clock.local_date || ""}${clock.timezone ? ` | ${clock.timezone}` : ""}`.trim());
    setText("projectDetailsClockUtc", `UTC: ${clock.generated_at_utc || ""}`.trim());
}

function renderSummaryCards(cards) {
    const container = document.getElementById("projectDetailsSummaryCards");
    if (!container) {
        return;
    }
    Alfred.setHTMLIfChanged(container, cards.map(card => `
        <article class="hero-signal project-hero-signal">
            <p class="hero-signal-label">${Alfred.escapeHtml(card.label || "")}</p>
            <p class="hero-signal-value">${Alfred.escapeHtml(card.value || "")}</p>
            <p class="hero-signal-meta">${Alfred.escapeHtml(card.copy || "")}</p>
        </article>
    `).join(""));
}

function renderOperationalMetrics(items) {
    const container = document.getElementById("projectDetailsOperationalMetrics");
    if (!container) {
        return;
    }
    Alfred.setHTMLIfChanged(container, items.map(item => `
        <div class="data-row">
            <div class="data-label">${Alfred.escapeHtml(item.label || "")}</div>
            <div class="data-value">${Alfred.escapeHtml(String(item.value ?? ""))} <span class="muted small">${Alfred.escapeHtml(item.copy || "")}</span></div>
        </div>
    `).join(""));
}

function renderLearningSnapshot(snapshot) {
    const overallProgress = normalizePercent(snapshot.overall_progress);
    setText("projectDetailsLearningSummary", snapshot.summary || "");
    setText("projectDetailsOverallProgressValue", `${overallProgress}%`);
    const bar = document.getElementById("projectDetailsOverallProgressBar");
    if (bar) {
        setProgressBar(bar, overallProgress);
    }
    const container = document.getElementById("projectDetailsLearningTracks");
    if (!container) {
        return;
    }
    Alfred.setHTMLIfChanged(container, (snapshot.tracks || []).map(track => renderProgressCard(track, "learning-track-card", track.blocker_label || "Still blocked by", "blocker")).join(""));
}

function renderInProgressTracks(items) {
    const container = document.getElementById("projectDetailsInProgressTracks");
    if (!container) {
        return;
    }
    Alfred.setHTMLIfChanged(container, items.map(item => renderProgressCard(item, "mini-card", "Next focus", "next_focus", "status-guarded")).join(""));
}

function renderCompletedTracks(items) {
    const container = document.getElementById("projectDetailsCompletedTracks");
    if (!container) {
        return;
    }
    Alfred.setHTMLIfChanged(container, items.map(item => renderProgressCard(item, "mini-card", "Maintenance focus", "maintenance_focus", "status-good")).join(""));
}

function renderProgressCard(item, className, footerLabel, footerKey, statusClass = "status-guarded") {
    const progress = normalizePercent(item.progress);
    const effectiveStatusClass = progress >= 100 ? "status-good" : statusClass;
    const signals = Array.isArray(item.signals) ? item.signals : [];
    return `
        <div class="${className}">
            <div class="d-flex justify-content-between align-items-start gap-3 mb-2">
                <div class="fw-semibold">${Alfred.escapeHtml(item.title || "")}</div>
                <span class="status-pill ${Alfred.escapeHtml(effectiveStatusClass)}">${progress}%</span>
            </div>
            <div class="progress alfred-progress mb-2">
                <div class="progress-bar" role="progressbar" style="width: ${progress}%;" aria-valuenow="${progress}" aria-valuemin="0" aria-valuemax="100"></div>
            </div>
            <p class="muted small mb-2">${Alfred.escapeHtml(item.detail || "")}</p>
            ${signals.length ? `<div class="chip-row mb-2">${signals.map(signal => `<span class="chip-neutral">${Alfred.escapeHtml(signal)}</span>`).join("")}</div>` : ""}
            <div class="muted small"><strong>${Alfred.escapeHtml(footerLabel)}:</strong> ${Alfred.escapeHtml(item[footerKey] || "")}</div>
        </div>
    `;
}

function normalizePercent(value) {
    const numeric = Number(value);
    if (!Number.isFinite(numeric)) {
        return 0;
    }
    return Math.max(0, Math.min(100, Math.round(numeric)));
}

function setProgressBar(bar, progress) {
    const width = `${progress}%`;
    if (bar.style.width !== width) {
        bar.style.width = width;
    }
    if (bar.getAttribute("aria-valuenow") !== String(progress)) {
        bar.setAttribute("aria-valuenow", String(progress));
    }
}

function renderReportRows(containerId, items, rowRenderer, emptyMessage) {
    const container = document.getElementById(containerId);
    if (!container) {
        return;
    }
    if (!items.length) {
        Alfred.setHTMLIfChanged(container, `<div class="empty-state">${Alfred.escapeHtml(emptyMessage)}</div>`);
        return;
    }
    Alfred.setHTMLIfChanged(container, `<div class="data-stack">${items.map(item => rowRenderer(item)).join("")}</div>`);
}

function setText(id, value) {
    Alfred.setTextIfChanged(id, value);
}

function formatDateTimeValue(value) {
    if (!value) {
        return "";
    }
    try {
        return Alfred.formatDateTime(value);
    } catch (error) {
        return String(value);
    }
}
