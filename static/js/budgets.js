let budgetForecastChart;

document.addEventListener("DOMContentLoaded", () => {
    if (!document.getElementById("budgetRoot")) {
        return;
    }

    document.getElementById("budgetPlanForm").addEventListener("submit", submitBudgetPlan);
    setBudgetMonthDefault();
    loadBudgetDashboard();
    Alfred.enableLiveRefresh("budget-live", loadBudgetDashboard, { rootId: "budgetRoot" });
});

function loadBudgetDashboard(options = {}) {
    return Alfred.fetchJSON("/api/budgets/dashboard/")
        .then(data => {
            renderBudgetHero(data.summary, data.plan);
            renderBudgetSummary(data.summary, data.daily_affordability || {});
            renderBudgetForecast(data.forecast || []);
            renderBudgetAffordability(data.daily_affordability || {});
            renderBudgetCategories(data.budgets || []);
            renderBudgetSuggestions(data.ai_suggestions || []);
            renderBudgetHistory(data.budget_history || []);
            if (!options.live) {
                hydrateBudgetForm(data.plan);
            }
            Alfred.clearPageAlert("budgetRoot");
        })
        .catch(error => {
            Alfred.upsertPageAlert("budgetRoot", error.message, "danger");
        });
}

function renderBudgetHero(summary, plan) {
    document.getElementById("budgetPlanValue").textContent = Alfred.formatCurrency(summary.total_budget);
    document.getElementById("budgetRemainingValue").textContent = Alfred.formatCurrency(summary.total_remaining);
    document.getElementById("budgetMonthLabel").textContent = plan ? `${plan.month} plan loaded` : summary.month;
}

function renderBudgetSummary(summary, affordability) {
    const cards = [
        { title: "Total Budget", value: Alfred.formatCurrency(summary.total_budget), copy: summary.month },
        { title: "Spent", value: Alfred.formatCurrency(summary.total_spent), copy: `${Alfred.formatPercent(summary.percent_used)} consumed` },
        { title: "Fixed Obligations", value: Alfred.formatCurrency(summary.fixed_obligations), copy: "Recurring structural commitments" },
        { title: "Safe Daily Spend", value: Alfred.formatCurrency(affordability.safe_daily_spend), copy: `${summary.tracked_categories} categories tracked` },
    ];

    document.getElementById("budgetSummaryCards").innerHTML = cards.map(card => `
        <article class="metric-card">
            <p class="metric-kicker">${card.title}</p>
            <h2 class="metric-value">${card.value}</h2>
            <p class="metric-caption">${card.copy}</p>
        </article>
    `).join("");
}

function renderBudgetForecast(items) {
    const canvas = document.getElementById("budgetForecastChart");
    if (budgetForecastChart) {
        budgetForecastChart.destroy();
    }

    budgetForecastChart = new Chart(canvas, {
        data: {
            labels: items.map(item => item.month),
            datasets: [
                {
                    type: "bar",
                    label: "Projected Expense",
                    data: items.map(item => item.predicted_expense || 0),
                    backgroundColor: "rgba(24, 88, 214, 0.72)",
                    borderRadius: 10,
                },
                {
                    type: "line",
                    label: "Projected Savings",
                    data: items.map(item => item.predicted_savings || 0),
                    borderColor: "#148f63",
                    backgroundColor: "rgba(20, 143, 99, 0.12)",
                    fill: true,
                    tension: 0.3,
                },
            ],
        },
        options: {
            responsive: true,
            plugins: { legend: { position: "bottom" } },
        },
    });
}

function renderBudgetAffordability(affordability) {
    const panel = document.getElementById("budgetAffordabilityPanel");
    panel.innerHTML = [
        ["Remaining Budget", Alfred.formatCurrency(affordability.remaining_budget)],
        ["Days Remaining", Alfred.formatNumber(affordability.days_remaining, 0)],
        ["Today's Spend", Alfred.formatCurrency(affordability.today_spending)],
        ["Average Daily Spend", Alfred.formatCurrency(affordability.avg_daily_spending)],
    ].map(([label, value]) => `
        <div class="data-row">
            <div class="data-label">${label}</div>
            <div class="data-value">${value}</div>
        </div>
    `).join("");

    const tones = {
        GOOD: "status-stable",
        WARNING: "status-guarded",
        OVER_BUDGET: "status-high",
    };
    document.getElementById("budgetDailyStatus").innerHTML = `
        <div class="d-flex justify-content-between align-items-center flex-wrap gap-3">
            <span class="status-pill ${tones[affordability.status] || "status-stable"}">${Alfred.escapeHtml(affordability.status || "UNKNOWN")}</span>
            <span>${Alfred.escapeHtml(affordability.message || "No affordability signal yet.")}</span>
        </div>
    `;
}

function renderBudgetCategories(items) {
    const body = document.getElementById("budgetCategoryBody");
    if (!items.length) {
        body.innerHTML = `<tr><td colspan="5" class="text-center muted py-4">No category signals yet. Add a budget and some expenses first.</td></tr>`;
        return;
    }

    body.innerHTML = items.map(item => `
        <tr>
            <td>
                <div class="fw-semibold">${Alfred.escapeHtml(item.label)}</div>
                <div class="muted small">Historical avg ${Alfred.formatCurrency(item.historical_avg)}</div>
            </td>
            <td class="text-end">${Alfred.formatCurrency(item.limit)}</td>
            <td class="text-end">${Alfred.formatCurrency(item.spent)}</td>
            <td class="text-end ${item.remaining < 0 ? "text-danger" : ""}">${Alfred.formatCurrency(item.remaining)}</td>
            <td class="text-end"><span class="status-pill ${categoryTone(item.status)}">${Alfred.formatPercent(item.percent_used)}</span></td>
        </tr>
    `).join("");
}

function renderBudgetSuggestions(items) {
    const target = document.getElementById("budgetSuggestionList");
    if (!items.length) {
        target.innerHTML = `<li class="insight-item">Budget recommendations will appear once income and transaction patterns are available.</li>`;
        return;
    }

    target.innerHTML = items.map(item => `<li class="insight-item">${Alfred.escapeHtml(item)}</li>`).join("");
}

function renderBudgetHistory(items) {
    const target = document.getElementById("budgetHistoryList");
    if (!items.length) {
        target.innerHTML = `<div class="empty-state">No stored budget plans yet.</div>`;
        return;
    }

    target.innerHTML = items.map(item => `
        <div class="mini-card">
            <div class="d-flex justify-content-between align-items-start gap-3">
                <div>
                    <div class="fw-semibold">${Alfred.escapeHtml(item.month)}</div>
                    <div class="muted small">Base ${Alfred.formatCurrency(item.base_budget)} • Adjusted ${Alfred.formatCurrency(item.inflation_adjusted)}</div>
                </div>
                <strong>${Alfred.formatCurrency(item.spent)}</strong>
            </div>
        </div>
    `).join("");
}

function hydrateBudgetForm(plan) {
    if (!plan) {
        return;
    }

    const form = document.getElementById("budgetPlanForm");
    form.month.value = plan.month;
    form.base_budget.value = plan.base_budget;
    form.inflation_adjusted.value = plan.inflation_adjusted;
    form.spent.value = plan.spent;
}

function submitBudgetPlan(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const payload = Object.fromEntries(new FormData(form).entries());
    payload.base_budget = Number(payload.base_budget);
    payload.inflation_adjusted = Number(payload.inflation_adjusted);
    payload.spent = Number(payload.spent || 0);

    Alfred.fetchJSON("/api/budgets/", {
        method: "POST",
        body: JSON.stringify(payload),
    })
        .then(() => {
            showBudgetFeedback("Budget plan saved.", "success");
            form.reset();
            setBudgetMonthDefault();
            loadBudgetDashboard();
        })
        .catch(error => showBudgetFeedback(error.message, "danger"));
}

function showBudgetFeedback(message, tone) {
    const box = document.getElementById("budgetPlanFeedback");
    box.className = `alert alert-${tone} mb-0`;
    box.textContent = message;
    box.classList.remove("d-none");
}

function setBudgetMonthDefault() {
    const field = document.getElementById("budgetMonth");
    if (!field.value) {
        field.value = new Date().toLocaleDateString("en-IN", { month: "short", year: "numeric" });
    }
}

function categoryTone(status) {
    if (status === "over") {
        return "status-high";
    }
    if (status === "warning") {
        return "status-guarded";
    }
    return "status-stable";
}
