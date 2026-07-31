let stressChart;

document.addEventListener("DOMContentLoaded", () => {
    if (!document.getElementById("behavioralRoot")) {
        return;
    }

    document.getElementById("behavioralForm").addEventListener("submit", submitBehavioralForm);
    loadBehavioralDashboard();
    Alfred.enableLiveRefresh("behavioral-live", loadBehavioralDashboard, { rootId: "behavioralRoot" });
});

function loadBehavioralDashboard() {
    return Promise.all([
        Alfred.fetchJSON("/api/behavioral/"),
        Alfred.fetchJSON("/api/behavioral/stress/"),
        Alfred.fetchJSON("/api/behavioral/fingerprint/"),
    ])
        .then(([history, stress, fingerprint]) => {
            showBehavioralAlert("", "secondary");
            renderBehavioralHero(stress, fingerprint);
            renderBehavioralSummary(history, stress, fingerprint);
            renderStressChart(stress.weekly_data || []);
            renderBehavioralInsights(stress, fingerprint);
            renderFingerprintPanel(stress, fingerprint);
            renderPressureMap(stress, fingerprint);
            renderBehavioralGrounding(stress.grounding || fingerprint.grounding || {});
            renderBehavioralHistory(history);
        })
        .catch(error => showBehavioralAlert(error.message, "danger"));
}

function renderBehavioralHero(stress, fingerprint) {
    document.getElementById("behavioralFingerprintValue").textContent = fingerprint.fingerprint || "No data";
    document.getElementById("behavioralStressValue").textContent = Alfred.formatNumber(stress.current_stress || 0, 1);
    document.getElementById("behavioralHeroCopy").textContent = fingerprint.message || stress.message || "No behavioral baseline yet.";
}

function renderBehavioralSummary(history, stress, fingerprint) {
    const linkedData = fingerprint.linked_data || {};
    const cards = [
        {
            title: "Current Pressure",
            value: Alfred.formatNumber(stress.current_stress || 0, 1),
            copy: stress.trend || "Unknown trend",
        },
        {
            title: "Average Pressure",
            value: Alfred.formatNumber(stress.average_stress || 0, 1),
            copy: "Blended from manual logs and linked spending windows",
        },
        {
            title: "Signals Linked",
            value: Alfred.formatNumber(linkedData.transactions || 0, 0),
            copy: `${Alfred.formatNumber(history.length, 0)} manual log${history.length === 1 ? "" : "s"} | ${Alfred.formatNumber(linkedData.recurring_commitments || 0, 0)} recurring`,
        },
        {
            title: "Decision Style",
            value: fingerprint.decision_style || "Unknown",
            copy: fingerprint.spending_pattern || "Pattern unavailable",
        },
    ];

    document.getElementById("behavioralSummaryCards").innerHTML = cards.map(card => `
        <article class="metric-card">
            <p class="metric-kicker">${card.title}</p>
            <h2 class="metric-value">${Alfred.escapeHtml(String(card.value))}</h2>
            <p class="metric-caption">${Alfred.escapeHtml(card.copy)}</p>
        </article>
    `).join("");
}

function renderStressChart(values) {
    const canvas = document.getElementById("stressChart");
    if (stressChart) {
        stressChart.destroy();
    }

    const ordered = values.length ? [...values].reverse() : [0];
    stressChart = new Chart(canvas, {
        type: "line",
        data: {
            labels: values.length ? ordered.map((_, index) => `T-${ordered.length - index - 1}`) : ["No data"],
            datasets: [{
                label: "Stress",
                data: ordered,
                borderColor: "#c44a3d",
                backgroundColor: "rgba(196, 74, 61, 0.14)",
                fill: true,
                tension: 0.3,
            }],
        },
        options: { plugins: { legend: { display: false } }, scales: { y: { suggestedMin: 0, suggestedMax: 10 } } },
    });
}

function renderBehavioralInsights(stress, fingerprint) {
    const insights = Array.from(new Set([
        ...(fingerprint.insights || []),
        ...(fingerprint.pattern_flags || []),
        ...(stress.recommendations || []),
        ...(fingerprint.minute_details || []),
    ])).slice(0, 8);
    const target = document.getElementById("behavioralInsightList");
    if (!insights.length) {
        target.innerHTML = `<li class="insight-item">Behavioral guidance will appear after a few logs are captured.</li>`;
        return;
    }

    target.innerHTML = insights.map(item => `<li class="insight-item">${Alfred.escapeHtml(item)}</li>`).join("");
}

function renderFingerprintPanel(stress, fingerprint) {
    const linkedData = fingerprint.linked_data || {};
    document.getElementById("behavioralFingerprintPanel").innerHTML = [
        ["Fingerprint", fingerprint.fingerprint || "No data"],
        ["Stress level", Alfred.formatNumber(fingerprint.stress_level || stress.current_stress || 0, 1)],
        ["Spending pattern", fingerprint.spending_pattern || "Unknown"],
        ["Decision style", fingerprint.decision_style || "Unknown"],
        ["Trend", stress.trend || "Unknown"],
        ["Coach tone", fingerprint.coach_tone || "Calibrating"],
        ["Reference month", linkedData.reference_month || "Unknown"],
        ["Top categories", (linkedData.top_categories || []).join(", ") || "Not enough data"],
        ["Peak pressure day", linkedData.peak_day || "No spike day detected"],
    ].map(([label, value]) => `
        <div class="data-row">
            <div class="data-label">${label}</div>
            <div class="data-value">${Alfred.escapeHtml(String(value))}</div>
        </div>
    `).join("");
}

function renderPressureMap(stress, fingerprint) {
    const items = (fingerprint.pressure_map && fingerprint.pressure_map.length ? fingerprint.pressure_map : stress.pressure_map) || [];
    const target = document.getElementById("behavioralPressureMap");
    if (!target) {
        return;
    }
    if (!items.length) {
        target.innerHTML = `<div class="empty-state">Pressure mapping will appear once ALFRED has linked enough transaction history.</div>`;
        return;
    }

    target.innerHTML = items.map(item => `
        <div class="mini-card">
            <div class="d-flex justify-content-between align-items-center gap-3 mb-2">
                <div class="fw-semibold">${Alfred.escapeHtml(item.label || "Pressure")}</div>
                <div class="small fw-semibold">${Alfred.formatNumber(item.score || 0, 1)} / 100</div>
            </div>
            <div class="progress mb-2" role="progressbar" aria-valuenow="${Math.round(item.score || 0)}" aria-valuemin="0" aria-valuemax="100">
                <div class="progress-bar" style="width: ${Math.max(0, Math.min(100, Number(item.score || 0)))}%;"></div>
            </div>
            <div class="muted small">${Alfred.escapeHtml(item.detail || "")}</div>
        </div>
    `).join("");
}

function renderBehavioralGrounding(grounding) {
    const target = document.getElementById("behavioralGroundingPanel");
    if (!target) {
        return;
    }
    const history = grounding.history || {};
    const freshness = grounding.freshness || {};
    const notes = grounding.notes || [];
    target.innerHTML = [
        `
        <div class="mini-card">
            <div class="data-row">
                <div class="data-label">Verified evidence</div>
                <div class="data-value">${Alfred.formatNumber(freshness.fresh_records || 0, 0)} / ${Alfred.formatNumber(freshness.tracked_records || 0, 0)}</div>
            </div>
            <div class="data-row">
                <div class="data-label">Linked transactions</div>
                <div class="data-value">${Alfred.formatNumber(history.transactions || 0, 0)}</div>
            </div>
            <div class="data-row">
                <div class="data-label">Manual logs</div>
                <div class="data-value">${Alfred.formatNumber(history.manual_signal_count || 0, 0)}</div>
            </div>
            <div class="data-row">
                <div class="data-label">Reference month</div>
                <div class="data-value">${Alfred.escapeHtml(history.reference_month || "Unknown")}</div>
            </div>
            ${freshness.next_stale_after ? `<div class="muted small mt-2">Next stale after ${Alfred.escapeHtml(Alfred.formatDateTime(freshness.next_stale_after))}</div>` : ""}
        </div>
        `,
        ...notes.map(item => `<div class="mini-card muted small">${Alfred.escapeHtml(item)}</div>`),
    ].join("");
}

function renderBehavioralHistory(items) {
    const target = document.getElementById("behavioralHistory");
    if (!items.length) {
        target.innerHTML = `<div class="empty-state">No manual behavioral signals logged yet. ALFRED is still using linked financial activity where available.</div>`;
        return;
    }

    target.innerHTML = items.slice(0, 6).map(item => `
        <div class="mini-card">
            <div class="d-flex justify-content-between align-items-start gap-3">
                <div>
                    <div class="fw-semibold">Stress ${Alfred.formatNumber(item.stress_score, 1)} | Sleep ${Alfred.formatNumber(item.sleep_hours, 1)}h</div>
                    <div class="muted small">Work ${Alfred.formatNumber(item.work_hours, 1)}h</div>
                </div>
                <span class="muted small">${Alfred.formatDateTime(item.timestamp)}</span>
            </div>
        </div>
    `).join("");
}

function submitBehavioralForm(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const payload = Object.fromEntries(new FormData(form).entries());
    payload.stress_score = Number(payload.stress_score || 0);
    payload.sleep_hours = Number(payload.sleep_hours || 0);
    payload.work_hours = Number(payload.work_hours || 0);
    const validationMessage = validateBehavioralPayload(payload);
    if (validationMessage) {
        showBehavioralFeedback(validationMessage, "warning");
        return;
    }

    Alfred.fetchJSON("/api/behavioral/", {
        method: "POST",
        body: JSON.stringify(payload),
    })
        .then(() => {
            form.reset();
            showBehavioralFeedback("Behavioral signal saved.", "success");
            loadBehavioralDashboard();
        })
        .catch(error => showBehavioralFeedback(error.message, "danger"));
}

function showBehavioralFeedback(message, tone) {
    const box = document.getElementById("behavioralFormFeedback");
    box.className = `alert alert-${tone} mb-0`;
    box.textContent = message;
    box.classList.remove("d-none");
}

function showBehavioralAlert(message, tone) {
    const target = document.getElementById("behavioralPageAlert");
    target.className = message ? `alert alert-${tone} mb-4` : "d-none mb-4";
    target.textContent = message;
}

function validateBehavioralPayload(payload) {
    if (payload.stress_score < 0 || payload.stress_score > 10) {
        return "Stress score must be between 0 and 10.";
    }
    if (payload.sleep_hours < 0 || payload.sleep_hours > 24) {
        return "Sleep hours must be between 0 and 24.";
    }
    if (payload.work_hours < 0 || payload.work_hours > 24) {
        return "Work hours must be between 0 and 24.";
    }
    return "";
}
