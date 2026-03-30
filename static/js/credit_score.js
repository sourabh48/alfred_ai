let creditFactorChart;
let creditTrendChart;

document.addEventListener("DOMContentLoaded", () => {
    if (!document.getElementById("creditScoreRoot")) {
        return;
    }

    document.getElementById("bureauSelect").addEventListener("change", loadCreditDashboard);
    document.getElementById("creditRefreshBtn").addEventListener("click", refreshCreditScore);
    loadCreditDashboard();
    Alfred.enableLiveRefresh("credit-live", loadCreditDashboard, { rootId: "creditScoreRoot" });
});

function loadCreditDashboard() {
    const bureau = document.getElementById("bureauSelect").value;
    return Promise.all([
        Alfred.fetchJSON(`/api/integrations/credit-score/?bureau=${bureau}`),
        Alfred.fetchJSON("/api/integrations/credit-score/trend/?months=12"),
        Alfred.fetchJSON("/api/integrations/credit-score/improvement-plan/"),
        Alfred.fetchJSON("/api/integrations/credit-score/peer-comparison/"),
        Alfred.fetchJSON("/api/integrations/credit-score/comprehensive-report/"),
    ])
        .then(([score, trend, improvement, peer, report]) => {
            renderCreditHero(score);
            renderCreditSummary(score, peer);
            renderCreditFactorChart(score.factors || []);
            renderCreditTrendChart(trend.trend || []);
            renderCreditFactorList(report.factor_analysis || {});
            renderCreditImprovement(improvement);
            renderCreditPeer(peer);
            renderCreditAlerts(report.alerts || []);
            Alfred.clearPageAlert("creditScoreRoot");
        })
        .catch(error => {
            Alfred.upsertPageAlert("creditScoreRoot", error.message, "danger");
        });
}

function renderCreditHero(score) {
    document.getElementById("creditScoreValue").textContent = Alfred.formatNumber(score.score || 0, 0);
    document.getElementById("creditScoreRating").textContent = score.rating || "Unknown";
    document.getElementById("creditScoreBureau").textContent = score.bureau || "CIBIL";
    if (score.score_kind === "estimated") {
        document.getElementById("creditScoreMeta").textContent = score.detail || "Internal estimate from your Alfred data.";
        return;
    }
    document.getElementById("creditScoreMeta").textContent = score.cached
        ? `Cached until ${Alfred.formatDateTime(score.valid_until)}`
        : `Fetched ${Alfred.formatDateTime(score.fetched_at)}`;
}

function renderCreditSummary(score, peer) {
    const report = score.report_summary || {};
    const cards = [
        { title: "Credit Score", value: Alfred.formatNumber(score.score || 0, 0), copy: score.score_kind === "estimated" ? "Internal estimate" : (score.rating || "Unknown") },
        { title: "Utilization", value: Alfred.formatPercent(report.credit_utilization || 0), copy: "Current credit utilization" },
        { title: "Active Accounts", value: Alfred.formatNumber(report.active_accounts || 0, 0), copy: `${Alfred.formatNumber(report.total_accounts || 0, 0)} total accounts` },
        { title: "Peer Percentile", value: peer.percentile != null ? `${Alfred.formatNumber(peer.percentile || 0, 0)}th` : "N/A", copy: peer.comparison_basis === "estimated_credit_health" ? "Estimated profile comparison" : (peer.comparison || "No comparison") },
    ];

    document.getElementById("creditSummaryCards").innerHTML = cards.map(card => `
        <article class="metric-card">
            <p class="metric-kicker">${card.title}</p>
            <h2 class="metric-value">${card.value}</h2>
            <p class="metric-caption">${Alfred.escapeHtml(card.copy)}</p>
        </article>
    `).join("");
}

function renderCreditFactorChart(items) {
    const canvas = document.getElementById("creditFactorChart");
    if (creditFactorChart) {
        creditFactorChart.destroy();
    }

    creditFactorChart = new Chart(canvas, {
        type: "bar",
        data: {
            labels: items.map(item => item.name || item.factor_name),
            datasets: [{
                label: "Factor score",
                data: items.map(item => item.score || 0),
                backgroundColor: "rgba(24, 88, 214, 0.72)",
                borderRadius: 10,
            }],
        },
        options: {
            plugins: { legend: { display: false } },
            scales: { y: { suggestedMin: 0, suggestedMax: 100 } },
        },
    });
}

function renderCreditTrendChart(items) {
    const canvas = document.getElementById("creditTrendChart");
    if (creditTrendChart) {
        creditTrendChart.destroy();
    }

    creditTrendChart = new Chart(canvas, {
        type: "line",
        data: {
            labels: items.map(item => item.month),
            datasets: [{
                label: "Score",
                data: items.map(item => item.score),
                borderColor: "#148f63",
                backgroundColor: "rgba(20, 143, 99, 0.12)",
                fill: true,
                tension: 0.3,
            }],
        },
        options: {
            plugins: { legend: { display: false } },
        },
    });
}

function renderCreditFactorList(analysis) {
    const panel = document.getElementById("creditFactorList");
    const factors = analysis.factors || [];
    const strengths = analysis.strengths || [];
    const weaknesses = analysis.weaknesses || [];

    panel.innerHTML = [
        ...factors.map(item => `
            <div class="mini-card">
                <div class="d-flex justify-content-between align-items-start gap-3">
                    <div>
                        <div class="fw-semibold">${Alfred.escapeHtml(item.name)}</div>
                        <div class="muted small">${item.status || "Unknown"} • weight ${item.weight}%</div>
                    </div>
                    <strong>${Alfred.formatNumber(item.score || 0, 0)}</strong>
                </div>
            </div>
        `),
        ...strengths.map(item => `<div class="mini-card"><strong>Strength</strong><div class="muted small mt-1">${Alfred.escapeHtml(item)}</div></div>`),
        ...weaknesses.map(item => `<div class="mini-card"><strong>Risk</strong><div class="muted small mt-1">${Alfred.escapeHtml(item)}</div></div>`),
    ].join("");
}

function renderCreditImprovement(plan) {
    const items = [
        ...(plan.action_items || []).map(item => `${item.priority}: ${item.action} (${item.timeline})`),
        ...(plan.quick_wins || []).map(item => `Quick win: ${item.action}`),
        ...(plan.long_term_goals || []),
    ];
    const target = document.getElementById("creditImprovementList");
    target.innerHTML = items.length
        ? items.map(item => `<li class="insight-item">${Alfred.escapeHtml(item)}</li>`).join("")
        : `<li class="insight-item">No improvement actions available yet.</li>`;
}

function renderCreditPeer(peer) {
    document.getElementById("creditPeerPanel").innerHTML = [
        ["Peer group", peer.peer_group || "Unknown"],
        ["Peer average", Alfred.formatNumber(peer.peer_average || 0, 0)],
        ["National average", Alfred.formatNumber(peer.national_average || 0, 0)],
        ["Ranking", peer.ranking || "Unknown"],
    ].map(([label, value]) => `
        <div class="data-row">
            <div class="data-label">${label}</div>
            <div class="data-value">${Alfred.escapeHtml(String(value))}</div>
        </div>
    `).join("");
}

function renderCreditAlerts(items) {
    const target = document.getElementById("creditAlertList");
    target.innerHTML = items.length
        ? items.map(item => `<li class="insight-item">${Alfred.escapeHtml(item.message)}</li>`).join("")
        : `<li class="insight-item">No active alerts right now.</li>`;
}

function refreshCreditScore() {
    const bureau = document.getElementById("bureauSelect").value;
    Alfred.fetchJSON("/api/integrations/credit-score/refresh/", {
        method: "POST",
        body: JSON.stringify({ bureau }),
    })
        .then(() => loadCreditDashboard())
        .catch(error => {
            document.getElementById("creditScoreMeta").textContent = error.message;
        });
}
