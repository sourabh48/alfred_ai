let dashboardMonthlyChart;
let dashboardCategoryChart;

document.addEventListener("DOMContentLoaded", () => {
    if (!document.getElementById("dashboardRoot")) {
        return;
    }

    loadDashboard();
    Alfred.enableLiveRefresh("dashboard-live", loadDashboard, { rootId: "dashboardRoot" });
});

function loadDashboard() {
    Alfred.setPageBusy("dashboardRoot", true, { label: "Loading dashboard intelligence" });
    return Alfred.fetchJSON("/api/expenses/dashboard/")
        .then(renderDashboard)
        .then(() => Alfred.clearPageAlert("dashboardRoot"))
        .catch(error => {
            Alfred.upsertPageAlert("dashboardRoot", error.message, "danger");
        })
        .finally(() => Alfred.setPageBusy("dashboardRoot", false));
}

function renderDashboard(data) {
    renderHero(data.summary, data.behavior);
    renderSummaryCards(data.summary, data.loan_portfolio);
    renderFocusStrip(data.summary, data.loan_portfolio, data.behavior);
    renderMonthlyChart(data.charts);
    renderCategoryChart(data.charts);
    renderBehavior(data.summary, data.behavior);
    renderRecurring(data.recurring_commitments);
    renderStress(data.behavior, data.spike_days);
    renderTransactions(data.recent_transactions);
}

function renderFocusStrip(summary, loanPortfolio, behavior) {
    const target = document.getElementById("dashboardFocusStrip");
    if (!target) {
        return;
    }
    const homeSummary = loanPortfolio.home_ownership_summary || {};

    const items = [
        {
            label: "Recorded Cash Left",
            value: Alfred.formatCurrency(summary.current_month_net),
            meta: `${summary.reference_month}: income minus confirmed outflow`,
            tone: summary.current_month_net >= 0 ? "success" : "danger",
        },
        {
            label: "Debt Payments / Income",
            value: summary.history_income > 0 ? Alfred.formatPercent(summary.debt_service_ratio) : "—",
            meta: "All recorded months; includes loan and card payments",
            tone: "primary",
        },
        {
            label: "Cash Retained / Income",
            value: summary.history_income > 0 ? Alfred.formatPercent(summary.savings_rate) : "—",
            meta: "All recorded months; after investments and card payments",
            tone: "good",
        },
        {
            label: "Spending Pattern",
            value: behavior.personality || "Calibrating",
            meta: "Estimated from your recorded history",
            tone: "accent",
        },
    ];
    if (Number(homeSummary.positions || 0) > 0) {
        items.push({
            label: "Home Equity",
            value: Alfred.formatCurrency(homeSummary.equity_built_total || 0),
            meta: `Upfront cash ${Alfred.formatCurrency(homeSummary.upfront_cash_invested_total || 0)}`,
            tone: "good",
        });
    }

    document.getElementById("dashboardFocusStrip").innerHTML = items.map(item => `
        <article class="dashboard-focus-card dashboard-focus-${item.tone}">
            <div class="dashboard-focus-label">${item.label}</div>
            <div class="dashboard-focus-value">${Alfred.escapeHtml(String(item.value))}</div>
            <div class="dashboard-focus-meta">${Alfred.escapeHtml(item.meta)}</div>
        </article>
    `).join("");
}

function renderHero(summary, behavior) {
    const scoreRing = document.getElementById("healthScoreRing");
    const needsReview = Number(summary.history_review_required || 0) > 0;
    const hasScore = summary.transactions && !needsReview;
    scoreRing.style.setProperty("--score", hasScore ? Math.round(summary.financial_health_score || 0) : 0);
    document.getElementById("healthScoreValue").textContent = hasScore ? Math.round(summary.financial_health_score || 0) : "—";
    document.getElementById("healthRiskPill").className = `status-pill ${needsReview ? "status-guarded" : statusClass(summary.risk_level)}`;
    document.getElementById("healthRiskPill").textContent = needsReview ? "Review transactions first" : (summary.transactions ? `${summary.risk_level} estimated risk` : "No data");
    document.getElementById("dashboardPersonality").textContent = behavior.personality;
    document.getElementById("dashboardReferenceMonth").textContent = summary.reference_month;
    document.getElementById("dashboardPeriodNote").textContent = summary.transactions
        ? `Showing ${summary.reference_month}, the latest month with recorded transactions. Rates below cover all recorded months.`
        : "No transactions yet. Add expenses or import a bank statement to see your totals.";
    const review = document.getElementById("dashboardReviewNotice");
    const amount = Number(summary.current_month_review_required || 0);
    review.hidden = amount <= 0;
    review.textContent = `${Alfred.formatCurrency(amount)} in debits needs review and is excluded from these totals. Cash left may be lower until you confirm these transactions on Expenses.`;
}

function renderSummaryCards(summary, loanPortfolio) {
    const cards = [
        {
            kicker: "Living Expenses",
            value: Alfred.formatCurrency(summary.current_month_expense),
            caption: `${summary.reference_month}; includes recorded rent`,
        },
        {
            kicker: "Recorded Income",
            value: Alfred.formatCurrency(summary.current_month_income),
            caption: `${summary.reference_month}; excludes transfers between accounts`,
        },
        {
            kicker: "Confirmed Outflow",
            value: Alfred.formatCurrency(summary.current_month_outflow || 0),
            caption: "Living costs, loan payments, investments, card payments and other confirmed debits",
        },
        {
            kicker: "Recorded Loan Balance",
            value: Alfred.formatCurrency(loanPortfolio.manual_total_outstanding),
            caption: `${loanPortfolio.active_loans} active loan${loanPortfolio.active_loans === 1 ? "" : "s"}`,
        },
    ];
    const homeSummary = loanPortfolio.home_ownership_summary || {};
    if (Number(homeSummary.positions || 0) > 0) {
        cards.push({
            kicker: "Home Acquisition Base",
            value: Alfred.formatCurrency(homeSummary.property_acquisition_cost_total || 0),
            caption: `${Alfred.formatCurrency(homeSummary.down_payment_total || 0)} down payment | ${Alfred.formatCurrency(homeSummary.other_upfront_payments_total || 0)} other upfront`,
        });
    }

    document.getElementById("dashboardSummaryCards").innerHTML = cards.map(card => `
        <article class="metric-card">
            <p class="metric-kicker">${card.kicker}</p>
            <h2 class="metric-value">${card.value}</h2>
            <p class="metric-caption">${card.caption}</p>
        </article>
    `).join("");
}

function renderMonthlyChart(charts) {
    const ctx = document.getElementById("dashboardMonthlyChart");
    if (dashboardMonthlyChart) {
        dashboardMonthlyChart.destroy();
    }

    dashboardMonthlyChart = new Chart(ctx, {
        data: {
            labels: charts.monthly_labels,
            datasets: [
                {
                    type: "bar",
                    label: "Expenses",
                    data: charts.monthly_expense_values,
                    backgroundColor: "rgba(24, 88, 214, 0.72)",
                    borderRadius: 10,
                },
                {
                    type: "bar",
                    label: "Loans",
                    data: charts.monthly_loan_values,
                    backgroundColor: "rgba(196, 74, 61, 0.72)",
                    borderRadius: 10,
                },
                {
                    type: "bar",
                    label: "Card payments",
                    data: charts.monthly_credit_card_payment_values || [],
                    backgroundColor: "rgba(122, 87, 209, 0.72)",
                    borderRadius: 10,
                },
                {
                    type: "bar",
                    label: "Investments",
                    data: charts.monthly_investment_values || [],
                    backgroundColor: "rgba(217, 121, 4, 0.72)",
                    borderRadius: 10,
                },
                {
                    type: "bar",
                    label: "Other",
                    data: charts.monthly_other_values,
                    backgroundColor: "rgba(255, 130, 92, 0.72)",
                    borderRadius: 10,
                },
                {
                    type: "line",
                    label: "Income",
                    data: charts.monthly_income_values,
                    borderColor: "#148f63",
                    pointBackgroundColor: "#148f63",
                    borderWidth: 3,
                    tension: 0.3,
                },
            ],
        },
        options: {
            responsive: true,
            interaction: { mode: "index", intersect: false },
            plugins: {
                legend: { position: "bottom" },
            },
            scales: {
                x: { stacked: true },
                y: { stacked: true, beginAtZero: true },
            },
        },
    });
}

function renderCategoryChart(charts) {
    const ctx = document.getElementById("dashboardCategoryChart");
    if (dashboardCategoryChart) {
        dashboardCategoryChart.destroy();
    }

    dashboardCategoryChart = new Chart(ctx, {
        type: "doughnut",
        data: {
            labels: charts.category_labels,
            datasets: [{
                data: charts.category_values,
                backgroundColor: ["#1858d6", "#ff825c", "#148f63", "#7a57d1", "#d97904", "#5c6a7f"],
                borderWidth: 0,
            }],
        },
        options: {
            plugins: { legend: { position: "bottom" } },
            cutout: "68%",
        },
    });

    document.getElementById("dashboardCategoryList").innerHTML = charts.category_labels.map((label, index) => `
        <div class="d-flex justify-content-between py-2 border-top">
            <span>${Alfred.escapeHtml(label)}</span>
            <strong>${Alfred.formatCurrency(charts.category_values[index])}</strong>
        </div>
    `).join("");
}

function renderBehavior(summary, behavior) {
    const cards = [
        { kicker: "Cash Retained / Income", value: summary.history_income > 0 ? Alfred.formatPercent(summary.savings_rate) : "—", caption: "All recorded months; after investments and card payments." },
        { kicker: "Discretionary Mix", value: Alfred.formatPercent(summary.discretionary_ratio), caption: "Lifestyle categories as a share of debit outflow." },
        { kicker: "Spending Stability", value: summary.transactions ? `${Math.round(summary.stability_score)}/100` : "—", caption: "Estimated from how much monthly spending changes." },
    ];

    document.getElementById("dashboardBehaviorCards").innerHTML = cards.map(card => `
        <div class="metric-card">
            <p class="metric-kicker">${card.kicker}</p>
            <div class="metric-value">${card.value}</div>
            <p class="metric-caption">${card.caption}</p>
        </div>
    `).join("");

    renderList("dashboardPatternFlags", behavior.pattern_flags, "No behavior flags yet.");
}

function renderRecurring(items) {
    const target = document.getElementById("dashboardRecurring");
    if (!items.length) {
        target.innerHTML = `<div class="detail-item">Recurring patterns will appear once ALFRED has repeated months of history.</div>`;
        return;
    }

    target.innerHTML = items.map(item => `
        <div class="detail-item mb-3">
            <div class="d-flex justify-content-between align-items-start gap-3">
                <div>
                    <div class="fw-semibold">${Alfred.escapeHtml(item.merchant)}</div>
                    <div class="muted small">${Alfred.escapeHtml(item.category)} • ${item.count} observations</div>
                </div>
                <strong>${Alfred.formatCurrency(item.average_amount)}</strong>
            </div>
        </div>
    `).join("");
}

function renderStress(behavior, spikeDays) {
    renderList("dashboardStressDrivers", behavior.stress_drivers, "Stress drivers are currently under control.");

    const target = document.getElementById("dashboardSpikeDays");
    if (!spikeDays.length) {
        target.innerHTML = `<div class="detail-item">No material spike days detected in the current history window.</div>`;
        return;
    }

    target.innerHTML = spikeDays.map(item => `
        <div class="detail-item mb-3">
            <div class="d-flex justify-content-between align-items-start gap-3">
                <div>
                    <div class="fw-semibold">${Alfred.formatDate(item.date)}</div>
                    <div class="muted small">${Alfred.escapeHtml(item.driver)}</div>
                </div>
                <strong>${Alfred.formatCurrency(item.amount)}</strong>
            </div>
        </div>
    `).join("");
}

function renderTransactions(items) {
    const target = document.getElementById("dashboardRecentTransactions");
    if (!items.length) {
        target.innerHTML = `<tr><td colspan="6" class="text-center muted py-4">No transaction history available yet.</td></tr>`;
        return;
    }

    target.innerHTML = items.map(item => `
        <tr>
            <td>${Alfred.formatDate(item.date)}</td>
            <td>
                <div class="fw-semibold">${Alfred.escapeHtml(item.merchant)}</div>
            </td>
            <td>${Alfred.escapeHtml(item.classification_label)}</td>
            <td>${Alfred.escapeHtml(item.category_label)}</td>
            <td class="text-end fw-semibold ${item.direction === "credit" ? "text-success" : ""}">
                ${item.direction === "credit" ? "+" : "-"}${Alfred.formatCurrency(item.amount)}
            </td>
            <td class="muted small">${Alfred.escapeHtml(item.description)}</td>
        </tr>
    `).join("");
}

function renderList(elementId, items, emptyCopy) {
    const target = document.getElementById(elementId);
    if (!items.length) {
        target.innerHTML = `<li class="insight-item">${Alfred.escapeHtml(emptyCopy)}</li>`;
        return;
    }

    target.innerHTML = items.map(item => `<li class="insight-item">${Alfred.escapeHtml(item)}</li>`).join("");
}

function statusClass(level) {
    const normalized = String(level || "").toLowerCase();
    if (normalized === "high") {
        return "status-high";
    }
    if (normalized === "guarded") {
        return "status-guarded";
    }
    if (normalized === "low") {
        return "status-low";
    }
    return "status-stable";
}
