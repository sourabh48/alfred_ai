let creditFactorChart;
let creditTrendChart;

document.addEventListener("DOMContentLoaded", () => {
    if (!document.getElementById("creditScoreRoot")) {
        return;
    }

    document.getElementById("bureauSelect").addEventListener("change", loadCreditDashboard);
    document.getElementById("creditRefreshBtn").addEventListener("click", refreshCreditScore);
    document.getElementById("creditReportUploadForm").addEventListener("submit", submitCreditReportUpload);
    loadCreditDashboard();
    Alfred.enableLiveRefresh("credit-live", loadCreditDashboard, { rootId: "creditScoreRoot" });
});

function loadCreditDashboard() {
    const bureau = document.getElementById("bureauSelect").value;
    return Promise.all([
        Alfred.fetchJSON(`/api/integrations/credit-score/?bureau=${bureau}`),
        Alfred.fetchJSON("/api/integrations/credit-score/uploads/"),
        Alfred.fetchJSON("/api/integrations/credit-score/trend/?months=12"),
        Alfred.fetchJSON("/api/integrations/credit-score/improvement-plan/"),
        Alfred.fetchJSON("/api/integrations/credit-score/peer-comparison/"),
        Alfred.fetchJSON("/api/integrations/credit-score/comprehensive-report/"),
    ])
        .then(([score, uploads, trend, improvement, peer, report]) => {
            renderCreditHero(score, report);
            renderCreditSummary(score, peer, report);
            renderCreditReportUploads(uploads || []);
            renderCreditFactorChart(score.factors || []);
            renderCreditTrendChart(trend.trend || []);
            renderCreditFactorList(report.factor_analysis || {}, report);
            renderCreditImprovement(improvement);
            renderCreditPeer(peer, report);
            renderCreditAlerts(report.alerts || []);
            Alfred.clearPageAlert("creditScoreRoot");
        })
        .catch(error => {
            Alfred.upsertPageAlert("creditScoreRoot", error.message, "danger");
        });
}

function renderCreditHero(score, report) {
    document.getElementById("creditScoreValue").textContent = Alfred.formatNumber(score.score || 0, 0);
    document.getElementById("creditScoreRating").textContent = score.rating || "Unknown";
    document.getElementById("creditScoreBureau").textContent = score.bureau || "CIBIL";
    const activeSource = report?.active_score_source || null;
    if (score.source_kind === "uploaded_report") {
        document.getElementById("creditScoreMeta").textContent = score.source_file_name
            ? `Uploaded report ${score.source_file_name} | parser ${Alfred.formatNumber((score.parse_confidence || 0) * 100, 0)}% | official snapshot active`
            : "Uploaded bureau report";
        return;
    }
    if (activeSource) {
        document.getElementById("creditScoreMeta").textContent = `Official ${activeSource.bureau} snapshot active since ${formatDateTimeSafe(activeSource.fetched_at)}`;
        return;
    }
    if (score.score_kind === "estimated") {
        document.getElementById("creditScoreMeta").textContent = score.detail || "Internal estimate from your Alfred data.";
        return;
    }
    document.getElementById("creditScoreMeta").textContent = score.cached
        ? `Cached until ${Alfred.formatDateTime(score.valid_until)}`
        : `Fetched ${Alfred.formatDateTime(score.fetched_at)}`;
}

function renderCreditSummary(score, peer, reportPayload) {
    const report = score.report_summary || {};
    const activeSource = reportPayload?.active_score_source || null;
    const cards = [
        {
            title: "Credit Score",
            value: Alfred.formatNumber(score.score || 0, 0),
            copy: score.score_kind === "estimated" ? "Internal estimate" : (activeSource ? `Official ${activeSource.bureau} snapshot` : (score.rating || "Unknown")),
        },
        { title: "Utilization", value: Alfred.formatPercent(report.credit_utilization || 0), copy: "Current credit utilization" },
        { title: "Active Accounts", value: Alfred.formatNumber(report.active_accounts || 0, 0), copy: `${Alfred.formatNumber(report.total_accounts || 0, 0)} total accounts` },
        {
            title: "Peer Percentile",
            value: peer.percentile != null ? `${Alfred.formatNumber(peer.percentile || 0, 0)}th` : "N/A",
            copy: peer.comparison_basis === "estimated_credit_health" ? "Estimated profile comparison" : (peer.comparison || "No comparison"),
        },
    ];

    document.getElementById("creditSummaryCards").innerHTML = cards.map(card => `
        <article class="metric-card">
            <p class="metric-kicker">${card.title}</p>
            <h2 class="metric-value">${card.value}</h2>
            <p class="metric-caption">${Alfred.escapeHtml(card.copy)}</p>
        </article>
    `).join("");
}

function renderCreditReportUploads(items) {
    const target = document.getElementById("creditReportUploadList");
    if (!items.length) {
        target.innerHTML = `<div class="empty-state">No uploaded credit reports yet.</div>`;
        return;
    }

    target.innerHTML = items.map(item => `
        <div class="mini-card">
            <div class="d-flex justify-content-between align-items-start gap-3">
                <div>
                    <div class="fw-semibold">${Alfred.escapeHtml(item.file_name || "Credit report")}</div>
                    <div class="muted small">${Alfred.escapeHtml(item.bureau || "Unknown bureau")} | ${Alfred.escapeHtml(item.parser_status || "pending")} | parser ${Alfred.formatNumber((item.parse_confidence || 0) * 100, 0)}%</div>
                    <div class="muted small mt-2">${item.report_date ? `Report date ${Alfred.formatDate(item.report_date)}` : "Report date not detected"}${item.report_number ? ` | ${Alfred.escapeHtml(item.report_number)}` : ""}</div>
                    <div class="muted small mt-2">${Alfred.escapeHtml(item.summary || item.parser_notes || "")}</div>
                </div>
                <div class="text-end">
                    <strong>${item.score ? Alfred.formatNumber(item.score, 0) : "Review"}</strong>
                    <div class="muted small">${item.uploaded_at ? Alfred.formatDateTime(item.uploaded_at) : ""}</div>
                </div>
            </div>
        </div>
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

function renderCreditFactorList(analysis, report) {
    const panel = document.getElementById("creditFactorList");
    const factors = analysis.factors || [];
    const strengths = analysis.strengths || [];
    const weaknesses = analysis.weaknesses || [];
    const cards = [];

    if (report?.active_score_source) {
        cards.push(`
            <div class="mini-card">
                <strong>Active source</strong>
                <div class="muted small mt-1">${Alfred.escapeHtml(`${report.active_score_source.bureau} official snapshot from ${formatDateTimeSafe(report.active_score_source.fetched_at)}`)}</div>
            </div>
        `);
    }

    panel.innerHTML = [
        ...cards,
        ...factors.map(item => `
            <div class="mini-card">
                <div class="d-flex justify-content-between align-items-start gap-3">
                    <div>
                        <div class="fw-semibold">${Alfred.escapeHtml(item.name)}</div>
                        <div class="muted small">${item.status || "Unknown"} | weight ${item.weight}%</div>
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

function renderCreditPeer(peer, report) {
    document.getElementById("creditPeerPanel").innerHTML = [
        ["Peer group", peer.peer_group || "Unknown"],
        ["Peer average", Alfred.formatNumber(peer.peer_average || 0, 0)],
        ["National average", Alfred.formatNumber(peer.national_average || 0, 0)],
        ["Ranking", peer.ranking || "Unknown"],
        ["Comparison basis", peer.comparison_basis || report?.bureau_status || "Unknown"],
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

function submitCreditReportUpload(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const fileInput = form.elements.report;
    const files = Array.from(fileInput?.files || []);
    if (!files.length) {
        showCreditReportFeedback("Choose at least one credit report first.", "warning");
        return;
    }

    const submitButton = form.querySelector("button[type='submit']");
    if (submitButton) {
        submitButton.disabled = true;
    }

    Alfred.showUploadProgress("creditReportFeedback", {
        phase: "preparing",
        percent: 0,
        current: 1,
        total: files.length,
    });

    Alfred.uploadFilesSequentially(
        files,
        (file, uploadContext) => {
            const payload = Alfred.buildSingleFileFormData(form, "report", file);
            payload.append("bureau", document.getElementById("bureauSelect").value);
            return Alfred.uploadJSON("/api/integrations/credit-score/upload-report/", {
                method: "POST",
                body: payload,
                onUploadState: uploadContext?.reportProgress,
            });
        },
        {
            onProgress: state => Alfred.showUploadProgress("creditReportFeedback", state),
        },
    )
        .then(results => {
            const summary = summarizeCreditReportBatch(results);
            if (summary.succeeded.length) {
                form.reset();
                loadCreditDashboard();
            }
            showCreditReportFeedback(summary.message, summary.tone);
        })
        .finally(() => {
            if (submitButton) {
                submitButton.disabled = false;
            }
        });
}

function showCreditReportFeedback(message, tone) {
    const target = document.getElementById("creditReportFeedback");
    target.className = `alert alert-${tone} mt-3 mb-0`;
    target.textContent = message;
    target.classList.remove("d-none");
}

function summarizeCreditReportBatch(results) {
    const summary = Alfred.summarizeUploadBatch(results, { itemLabel: "credit report", successVerb: "uploaded" });
    const parsedCount = summary.succeeded.filter(result => result.data?.upload?.parser_status === "parsed").length;
    const reviewCount = summary.succeeded.length - parsedCount;
    const officialCount = summary.succeeded.filter(result => result.data?.score?.score).length;
    const extras = [];

    if (parsedCount) {
        extras.push(`${parsedCount} parsed cleanly`);
    }
    if (reviewCount) {
        extras.push(`${reviewCount} marked for review`);
    }
    if (officialCount) {
        extras.push(`${officialCount} official snapshot${officialCount === 1 ? "" : "s"} created`);
    }

    return {
        ...summary,
        tone: reviewCount && !summary.failed.length ? "warning" : summary.tone,
        message: extras.length ? `${summary.message} ${extras.join(" | ")}.` : summary.message,
    };
}

function formatDateTimeSafe(value) {
    if (!value) {
        return "";
    }
    try {
        return Alfred.formatDateTime(value);
    } catch (error) {
        return String(value);
    }
}
