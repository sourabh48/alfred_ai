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
    const cards = [
        { title: "Current Stress", value: Alfred.formatNumber(stress.current_stress || 0, 1), copy: stress.trend || "Unknown trend" },
        { title: "Average Stress", value: Alfred.formatNumber(stress.average_stress || 0, 1), copy: "Last seven readings" },
        { title: "Logs Captured", value: Alfred.formatNumber(history.length, 0), copy: "Signals stored in behavioral log" },
        { title: "Decision Style", value: fingerprint.decision_style || "Unknown", copy: fingerprint.spending_pattern || "Pattern unavailable" },
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
    const insights = Array.from(new Set([...(fingerprint.insights || []), ...(stress.recommendations || [])])).slice(0, 6);
    const target = document.getElementById("behavioralInsightList");
    if (!insights.length) {
        target.innerHTML = `<li class="insight-item">Behavioral guidance will appear after a few logs are captured.</li>`;
        return;
    }

    target.innerHTML = insights.map(item => `<li class="insight-item">${Alfred.escapeHtml(item)}</li>`).join("");
}

function renderFingerprintPanel(stress, fingerprint) {
    document.getElementById("behavioralFingerprintPanel").innerHTML = [
        ["Fingerprint", fingerprint.fingerprint || "No data"],
        ["Stress level", Alfred.formatNumber(fingerprint.stress_level || stress.current_stress || 0, 1)],
        ["Spending pattern", fingerprint.spending_pattern || "Unknown"],
        ["Decision style", fingerprint.decision_style || "Unknown"],
        ["Trend", stress.trend || "Unknown"],
    ].map(([label, value]) => `
        <div class="data-row">
            <div class="data-label">${label}</div>
            <div class="data-value">${Alfred.escapeHtml(String(value))}</div>
        </div>
    `).join("");
}

function renderBehavioralHistory(items) {
    const target = document.getElementById("behavioralHistory");
    if (!items.length) {
        target.innerHTML = `<div class="empty-state">No behavioral signals logged yet.</div>`;
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
