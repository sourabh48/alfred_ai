let riskChart;

document.addEventListener("DOMContentLoaded", () => {
    if (!document.getElementById("riskRoot")) {
        return;
    }

    document.getElementById("riskForm").addEventListener("submit", submitRiskForm);
    loadRiskDashboard();
    Alfred.enableLiveRefresh("risk-live", loadRiskDashboard, { rootId: "riskRoot" });
});

function loadRiskDashboard() {
    return Alfred.fetchJSON("/api/risk/outlook/")
        .then(data => {
            const items = data.history || [];
            renderRiskHero(data.summary || {}, data.outlook || {}, items);
            renderRiskSummary(data.summary || {}, data.outlook || {}, data.consolidated_risks || [], items);
            renderRiskBoard(data.consolidated_risks || []);
            renderRiskChart(data.consolidated_risks || []);
            renderRiskInsights(data.insights || []);
            renderRiskMacroContext(data.macro_context || {});
            renderRiskGrounding(data.grounding || {}, data.evidence_freshness || {});
            renderRiskEvidence(data.evidence || []);
            renderRiskSignals(data.module_signals || {});
            renderRiskActions(data.action_items || []);
            renderRiskTable(items);
            renderRiskNews(data.related_news || []);
            Alfred.clearPageAlert("riskRoot");
        })
        .catch(error => {
            Alfred.upsertPageAlert("riskRoot", error.message, "danger");
        });
}

function renderRiskHero(summary, outlook, items) {
    const latest = items[0];
    document.getElementById("riskHighestValue").textContent = Alfred.formatNumber(summary.highest_score || 0, 0);
    document.getElementById("riskHighestLabel").textContent = summary.highest_label || "No data";
    document.getElementById("riskHeroCopy").textContent = latest
        ? `Latest snapshot ${Alfred.formatDateTime(latest.timestamp)} | consolidated average ${Alfred.formatNumber(outlook.average || 0, 0)}`
        : "Capture a risk snapshot to start consolidated trend monitoring.";
}

function renderRiskSummary(summary, outlook, consolidated, items) {
    const cards = [
        {
            title: "Overall Risk",
            value: `${Alfred.formatNumber(outlook.average || 0, 0)}/100`,
            copy: `${consolidated.length} consolidated categories tracked`,
        },
        {
            title: "Highest Pressure",
            value: Alfred.formatNumber(summary.highest_score || 0, 0),
            copy: summary.highest_label || "No category yet",
        },
        {
            title: "Related News",
            value: Alfred.formatNumber(summary.news_count || 0, 0),
            copy: "Verified internet-backed articles in the current view",
        },
        {
            title: "Action Queue",
            value: Alfred.formatNumber(summary.action_count || 0, 0),
            copy: `${items.length} manual snapshots stored`,
        },
    ];

    document.getElementById("riskSummaryCards").innerHTML = cards.map(card => `
        <article class="metric-card">
            <p class="metric-kicker">${card.title}</p>
            <h2 class="metric-value">${card.value}</h2>
            <p class="metric-caption">${card.copy}</p>
        </article>
    `).join("");
}

function renderRiskBoard(items) {
    const target = document.getElementById("riskBoard");
    target.innerHTML = items.length ? items.map(item => `
        <div class="mini-card">
            <div class="d-flex justify-content-between align-items-start gap-3">
                <div>
                    <div class="fw-semibold">${Alfred.escapeHtml(item.label)} <span class="muted small">${Alfred.escapeHtml(item.trend || "stable")}</span></div>
                    <div class="muted small mt-2">${Alfred.escapeHtml(item.note || "")}</div>
                    <div class="chip-row mt-2">
                        ${(item.drivers || []).map(driver => `<span class="chip-neutral">${Alfred.escapeHtml(driver)}</span>`).join("")}
                    </div>
                </div>
                <span class="status-pill ${riskTone(item.level)}">${Alfred.escapeHtml(item.level)} | ${Alfred.formatNumber(item.score || 0, 0)}</span>
            </div>
        </div>
    `).join("") : `<div class="empty-state">No consolidated risk items yet.</div>`;
}

function renderRiskChart(items) {
    const canvas = document.getElementById("riskRadar");
    const meta = document.getElementById("riskRadarMeta");
    if (riskChart) {
        riskChart.destroy();
    }

    if (!items.length) {
        meta.textContent = "No live consolidated risk items are available yet. Save a snapshot to render the radar.";
        riskChart = new Chart(canvas, {
            type: "radar",
            data: { labels: [], datasets: [{ label: "Current risk", data: [] }] },
            options: {
                plugins: { legend: { display: false } },
                scales: { r: { min: 0, max: 100 } },
            },
        });
        return;
    }

    meta.textContent = "Current category spread from live consolidated risk items only.";
    const labels = items.map(item => item.label);
    const values = items.map(item => item.score || 0);

    riskChart = new Chart(canvas, {
        type: "radar",
        data: {
            labels,
            datasets: [{
                label: "Current risk",
                data: values,
                borderColor: "#c44a3d",
                backgroundColor: "rgba(196, 74, 61, 0.16)",
                borderWidth: 2,
            }],
        },
        options: {
            scales: {
                r: {
                    min: 0,
                    max: 100,
                },
            },
        },
    });
}

function renderRiskInsights(items) {
    const target = document.getElementById("riskInsightList");
    target.innerHTML = items.length
        ? items.map(item => `<li class="insight-item">${Alfred.escapeHtml(item)}</li>`).join("")
        : `<li class="insight-item">Mitigation guidance will appear once a snapshot is captured.</li>`;
}

function renderRiskMacroContext(context) {
    document.getElementById("riskMacroContext").innerHTML = [
        ["Unemployment", context.unemployment?.latest_value ?? "N/A", context.unemployment?.latest_year || "Latest available"],
        ["Inflation", context.inflation?.latest_value ?? "N/A", context.inflation?.latest_year || "Latest available"],
        ["NIFTY 1M Return", context.market?.one_month_return_pct ?? "N/A", "Market snapshot"],
        ["India VIX", context.market?.india_vix ?? context.market?.realized_volatility_pct ?? "N/A", "Volatility context"],
    ].map(([label, value, note]) => `
        <div class="data-row">
            <div class="data-label">${label}</div>
            <div class="data-value">${Alfred.escapeHtml(String(value))} <span class="muted small">${Alfred.escapeHtml(String(note))}</span></div>
        </div>
    `).join("");
}

function renderRiskEvidence(items) {
    const target = document.getElementById("riskEvidenceList");
    target.innerHTML = items.length ? items.map(item => `
        <div class="mini-card">
            <div class="fw-semibold">${Alfred.escapeHtml(item.title || item.source_name)}</div>
            <div class="muted small">${Alfred.escapeHtml(item.source_name || "Source")} | ${Alfred.escapeHtml(item.status || "unknown")}${item.verified_at ? ` | refreshed ${Alfred.formatDateTime(item.verified_at)}` : ""}</div>
            <div class="muted small mt-2">${Alfred.escapeHtml(item.summary || "")}</div>
            ${item.stale_after ? `<div class="muted small mt-2">Next stale after ${Alfred.formatDateTime(item.stale_after)}</div>` : ""}
            ${item.source_url ? `<div class="mt-2"><a href="${item.source_url}" target="_blank" rel="noopener">Open source</a></div>` : ""}
        </div>
    `).join("") : `<div class="empty-state">No external evidence cached yet.</div>`;
}

function renderRiskGrounding(grounding, freshness) {
    const cardsTarget = document.getElementById("riskEvidenceFreshnessCards");
    const listTarget = document.getElementById("riskGroundingList");
    const history = grounding.history || {};
    const notes = grounding.notes || [];
    const activeFreshness = Object.keys(grounding.freshness || {}).length ? grounding.freshness : freshness;

    cardsTarget.innerHTML = [
        ["Evidence tracked", Alfred.formatNumber(activeFreshness.tracked_records || 0, 0), "Verified records attached"],
        ["Fresh now", Alfred.formatNumber(activeFreshness.fresh_records || 0, 0), activeFreshness.next_stale_after ? `Next stale after ${Alfred.formatDateTime(activeFreshness.next_stale_after)}` : "No stale deadline attached"],
        ["Snapshots", Alfred.formatNumber(history.tracked_snapshots || 0, 0), `${Alfred.formatCurrency(history.monthly_income || 0)} income basis`],
    ].map(([label, value, copy]) => `
        <article class="metric-card metric-card--compact">
            <p class="metric-kicker">${Alfred.escapeHtml(label)}</p>
            <h3 class="metric-value" style="font-size:1.35rem;">${Alfred.escapeHtml(String(value))}</h3>
            <p class="metric-caption">${Alfred.escapeHtml(copy)}</p>
        </article>
    `).join("");

    const entries = [
        `Liquid cash basis: ${Alfred.formatCurrency(history.liquid_cash || 0)}`,
        `Monthly EMI basis: ${Alfred.formatCurrency(history.monthly_emi || 0)}`,
        `Dependents tracked: ${Alfred.formatNumber(history.dependents || 0, 0)}`,
        ...notes,
    ];
    listTarget.innerHTML = entries.length
        ? entries.map(item => `<li class="insight-item">${Alfred.escapeHtml(item)}</li>`).join("")
        : `<li class="insight-item">No grounding notes are attached yet.</li>`;
}

function renderRiskSignals(signals) {
    document.getElementById("riskSignalBoard").innerHTML = [
        ["Career market risk", signals.career_market_risk ?? "N/A"],
        ["Job fit score", signals.job_fit_score ?? "N/A"],
        ["Debt burden %", signals.debt_burden_pct ?? "N/A"],
        ["Emergency months", signals.emergency_months ?? "N/A"],
        ["Average stress", signals.average_stress ?? "N/A"],
        ["Average sleep", signals.average_sleep ?? "N/A"],
        ["Vehicle compliance", signals.mobility_document_compliance ?? "N/A"],
        ["Vehicle condition", signals.mobility_condition_score ?? "N/A"],
    ].map(([label, value]) => `
        <div class="data-row">
            <div class="data-label">${label}</div>
            <div class="data-value">${Alfred.escapeHtml(String(value))}</div>
        </div>
    `).join("");
}

function renderRiskActions(items) {
    const target = document.getElementById("riskActionList");
    target.innerHTML = items.length ? items.map(item => `
        <div class="mini-card">
            <div class="d-flex justify-content-between gap-3 align-items-start">
                <div>
                    <div class="fw-semibold">${Alfred.escapeHtml(item.title)}</div>
                    <div class="muted small mt-2">${Alfred.escapeHtml(item.note || "")}</div>
                </div>
                <span class="status-pill ${riskTone(item.priority)}">${Alfred.escapeHtml(item.priority || "low")}</span>
            </div>
        </div>
    `).join("") : `<div class="empty-state">No action items yet.</div>`;
}

function renderRiskTable(items) {
    const body = document.getElementById("riskTableBody");
    if (!items.length) {
        body.innerHTML = `<tr><td colspan="4" class="text-center muted py-4">No risk snapshots stored yet.</td></tr>`;
        return;
    }

    body.innerHTML = items.map(item => `
        <tr>
            <td>${Alfred.formatDateTime(item.timestamp)}</td>
            <td class="text-end">${Alfred.formatNumber(item.layoff_risk, 0)}</td>
            <td class="text-end">${Alfred.formatNumber(item.illness_risk, 0)}</td>
            <td class="text-end">${Alfred.formatNumber(item.relocation_risk, 0)}</td>
        </tr>
    `).join("");
}

function renderRiskNews(items) {
    const target = document.getElementById("riskNewsList");
    target.innerHTML = items.length ? items.map(item => `
        <div class="mini-card">
            <div class="d-flex justify-content-between gap-3 align-items-start">
                <div>
                    <div class="fw-semibold">${Alfred.escapeHtml(item.title || "News item")}</div>
                    <div class="muted small">${Alfred.escapeHtml(item.bucket || "Risk")} | ${Alfred.escapeHtml(item.source || "Unknown source")}</div>
                    <div class="muted small">${Alfred.escapeHtml(item.published || "No publish date")}</div>
                </div>
                <a href="${item.link}" target="_blank" rel="noopener">Open</a>
            </div>
        </div>
    `).join("") : `<div class="empty-state">No related news was returned right now.</div>`;
}

function submitRiskForm(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const payload = Object.fromEntries(new FormData(form).entries());
    ["layoff_risk", "illness_risk", "relocation_risk"].forEach(key => {
        payload[key] = Number(payload[key] || 0);
    });

    Alfred.fetchJSON("/api/risk/", {
        method: "POST",
        body: JSON.stringify(payload),
    })
        .then(() => {
            form.reset();
            showRiskFeedback("Risk snapshot saved.", "success");
            loadRiskDashboard();
        })
        .catch(error => showRiskFeedback(error.message, "danger"));
}

function showRiskFeedback(message, tone) {
    const box = document.getElementById("riskFormFeedback");
    box.className = `alert alert-${tone} mb-0`;
    box.textContent = message;
    box.classList.remove("d-none");
}

function riskTone(value) {
    if (value === "critical" || value === "high") {
        return "status-high";
    }
    if (value === "guarded" || value === "medium") {
        return "status-guarded";
    }
    return "status-low";
}
