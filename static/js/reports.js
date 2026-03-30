document.addEventListener("DOMContentLoaded", () => {
    if (!document.getElementById("reportsRoot")) {
        return;
    }

    loadReportsDashboard();
    Alfred.enableLiveRefresh("reports-live", loadReportsDashboard, { rootId: "reportsRoot" });
});

function loadReportsDashboard() {
    const requests = [
        Alfred.fetchJSON("/api/reports/"),
        Alfred.fetchJSON("/api/expenses/dashboard/"),
        Alfred.fetchJSON("/api/reports/tickets/"),
    ];

    return Promise.all(requests)
        .then(results => {
            const [reports, dashboard, tickets] = results;
            renderReportsHero(reports, dashboard);
            renderReportsSummary(reports, dashboard);
            renderReportsTable(reports);
            renderCoveragePanel(dashboard);
            if (document.getElementById("reportTicketActivity")) {
                renderTicketActivity(tickets || []);
            }
            if (document.getElementById("reportTicketQueue")) {
                renderTicketQueue(tickets || []);
            }
            Alfred.clearPageAlert("reportsRoot");
        })
        .catch(error => {
            Alfred.upsertPageAlert("reportsRoot", error.message, "danger");
        });
}

function renderReportsHero(reports, dashboard) {
    document.getElementById("reportCountValue").textContent = Alfred.formatNumber(reports.length, 0);
    document.getElementById("reportHealthValue").textContent = Alfred.formatNumber(dashboard.summary.financial_health_score || 0, 0);
    document.getElementById("reportHeroCopy").textContent = reports.length
        ? `Latest report created ${Alfred.formatDateTime(reports[0].created_at)}`
        : "Run generators to populate downloadable artifacts.";
}

function renderReportsSummary(reports, dashboard) {
    const cards = [
        { title: "Reports", value: Alfred.formatNumber(reports.length, 0), copy: "Recorded output artifacts" },
        { title: "Transactions", value: Alfred.formatNumber(dashboard.summary.transactions || 0, 0), copy: "Available for reporting" },
        { title: "Recurring", value: Alfred.formatNumber((dashboard.recurring_commitments || []).length, 0), copy: "Commitments detected" },
        { title: "Active Loans", value: Alfred.formatNumber(dashboard.loan_portfolio.active_loans || 0, 0), copy: "Debt positions in live dataset" },
    ];

    document.getElementById("reportSummaryCards").innerHTML = cards.map(card => `
        <article class="metric-card">
            <p class="metric-kicker">${card.title}</p>
            <h2 class="metric-value">${card.value}</h2>
            <p class="metric-caption">${card.copy}</p>
        </article>
    `).join("");
}

function renderReportsTable(reports) {
    const body = document.getElementById("reportsTableBody");
    if (!reports.length) {
        body.innerHTML = `<tr><td colspan="2" class="text-center muted py-4">No generated reports are stored yet.</td></tr>`;
        return;
    }

    body.innerHTML = reports.map(report => `
        <tr>
            <td>${Alfred.formatDateTime(report.created_at)}</td>
            <td class="fw-semibold">${Alfred.escapeHtml(report.file_path)}</td>
        </tr>
    `).join("");
}

function renderCoveragePanel(dashboard) {
    const panel = document.getElementById("reportCoveragePanel");
    panel.innerHTML = [
        ["Reference month", dashboard.summary.reference_month],
        ["Health score", `${Alfred.formatNumber(dashboard.summary.financial_health_score || 0, 0)} / 100`],
        ["Stress score", `${Alfred.formatNumber(dashboard.summary.stress_score || 0, 0)} / 100`],
        ["Lifestyle diversity", `${Alfred.formatNumber(dashboard.summary.lifestyle_diversity_score || 0, 0)} / 100`],
        ["Lifestyle risk", dashboard.summary.lifestyle_risk_level || "No data"],
        ["Recent transactions", Alfred.formatNumber((dashboard.recent_transactions || []).length, 0)],
        ["Recurring commitments", Alfred.formatNumber((dashboard.recurring_commitments || []).length, 0)],
    ].map(([label, value]) => `
        <div class="data-row">
            <div class="data-label">${label}</div>
            <div class="data-value">${Alfred.escapeHtml(String(value))}</div>
        </div>
    `).join("");
}

function renderTicketActivity(tickets) {
    const target = document.getElementById("reportTicketActivity");
    const automated = tickets.filter(ticket => ticket.handled_by === "alfred").slice(0, 8);
    if (!automated.length) {
        target.innerHTML = `<div class="empty-state">No ALFRED auto-handled tickets are recorded yet.</div>`;
        return;
    }

    target.innerHTML = automated.map(ticket => `
        <div class="mini-card">
            <div class="d-flex justify-content-between align-items-start gap-3">
                <div>
                    <div class="fw-semibold">${Alfred.escapeHtml(ticket.title)}</div>
                    <div class="muted small">${Alfred.escapeHtml(ticket.module_label || ticket.module)} | ${Alfred.escapeHtml(ticket.severity_label || ticket.severity)} | ${Alfred.formatDateTime(ticket.created_at)}</div>
                    <div class="muted small mt-2">${Alfred.escapeHtml(ticket.summary || "")}</div>
                    <div class="small mt-2"><strong>Handled by:</strong> ${Alfred.escapeHtml(ticket.handled_by_label || ticket.handled_by || "Unknown")}</div>
                    <div class="small"><strong>Resolution:</strong> ${Alfred.escapeHtml(ticket.resolution_summary || "Pending developer review.")}</div>
                </div>
                <span class="status-pill ${ticket.handled_by === "alfred" ? "status-stable" : "status-high"}">${Alfred.escapeHtml(ticket.status_label || ticket.status)}</span>
            </div>
        </div>
    `).join("");
}

function renderTicketQueue(tickets) {
    const target = document.getElementById("reportTicketQueue");
    const developerQueue = tickets.filter(ticket => ticket.handled_by === "developer" && ticket.status !== "resolved");
    if (!developerQueue.length) {
        target.innerHTML = `<div class="empty-state">No open user tickets are in the queue right now.</div>`;
        return;
    }

    target.innerHTML = developerQueue.map(ticket => `
        <div class="mini-card">
            <div class="d-flex justify-content-between align-items-start gap-3">
                <div>
                    <div class="fw-semibold">${Alfred.escapeHtml(ticket.title)}</div>
                    <div class="muted small">${Alfred.escapeHtml(ticket.module_label || ticket.module)} | ${Alfred.escapeHtml(ticket.severity_label || ticket.severity)} | ${Alfred.escapeHtml(ticket.username || "Unknown user")} | ${Alfred.formatDateTime(ticket.created_at)}</div>
                    <div class="muted small mt-2">${Alfred.escapeHtml(ticket.summary || "")}</div>
                    <div class="small mt-2"><strong>Route:</strong> ${Alfred.escapeHtml(ticket.handled_by_label || ticket.handled_by || "Developer")}</div>
                    <div class="small"><strong>Resolution:</strong> ${Alfred.escapeHtml(ticket.resolution_summary || "Pending developer review.")}</div>
                </div>
                <span class="status-pill ${ticket.status === "resolved" ? "status-stable" : (ticket.status === "triaged" ? "status-guarded" : "status-high")}">${Alfred.escapeHtml(ticket.status_label || ticket.status)}</span>
            </div>
        </div>
    `).join("");
}
