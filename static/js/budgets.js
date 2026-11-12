let budgetForecastChart;

document.addEventListener("DOMContentLoaded", () => {
    if (!document.getElementById("budgetRoot")) {
        return;
    }

    document.getElementById("budgetPlanForm").addEventListener("submit", submitBudgetPlan);
    document.getElementById("savingsGoalForm").addEventListener("submit", submitSavingsGoal);
    loadSavingsGoals();
    setBudgetMonthDefault();
    loadBudgetDashboard();
    Alfred.enableLiveRefresh("budget-live", loadBudgetDashboard, { rootId: "budgetRoot" });
});

let budgetCurrency = "INR";  // FIN-15: the active plan's currency; its spend is in the same currency
const planMoney = value => Alfred.formatCurrency(value, budgetCurrency);

function loadBudgetDashboard(options = {}) {
    return Alfred.fetchJSON("/api/budgets/dashboard/")
        .then(data => {
            budgetCurrency = data.summary.currency || "INR";
            renderBudgetHero(data.summary, data.plan);
            renderBudgetSummary(data.summary, data.daily_affordability || {});
            renderBudgetForecast(data.forecast || [], data.forecast_evidence || {});
            renderBudgetAffordability(data.daily_affordability || {});
            renderBudgetCategories(data.budgets || []);
            renderBudgetSuggestions(data.ai_suggestions || []);
            renderBudgetHistory(data.budget_history || []);
            if (!options.live) {
                hydrateBudgetForm(data.plan, data.summary.month);
            }
            if (data.unavailable_sections?.length) {
                Alfred.upsertPageAlert("budgetRoot", `Some guidance is unavailable: ${data.unavailable_sections.join(", ")}. Your saved budget is preserved.`, "warning");
            } else {
                Alfred.clearPageAlert("budgetRoot");
            }
        })
        .catch(error => {
            Alfred.upsertPageAlert("budgetRoot", error.message, "danger");
        });
}

function renderBudgetHero(summary, plan) {
    document.getElementById("budgetPlanValue").textContent = planMoney(summary.total_budget);
    document.getElementById("budgetRemainingValue").textContent = planMoney(summary.total_remaining);
    document.getElementById("budgetMonthLabel").textContent = plan ? `${plan.month} plan loaded` : summary.month;
}

function renderBudgetSummary(summary, affordability) {
    const cards = [
        { title: "Flexible Budget", value: planMoney(summary.total_budget), copy: budgetCurrency === "INR" ? summary.month : `${summary.month} | ${budgetCurrency} plan, ${budgetCurrency} spending only` },
        { title: "Living Spend", value: planMoney(summary.total_spent), copy: summary.percent_used == null ? "No positive budget for utilization" : `${Alfred.formatPercent(summary.percent_used)} of flexible budget used` },
        { title: "Housing + Loan EMIs", value: Alfred.formatCurrency(summary.fixed_obligations), copy: "Reserved separately from flexible spending" },
        { title: "Daily Budget Guide", value: affordability.safe_daily_spend == null ? "Unavailable" : Alfred.formatCurrency(affordability.safe_daily_spend), copy: `${affordability.days_remaining || 0} days left, including today` },
    ];

    Alfred.setHTML(document.getElementById("budgetSummaryCards"), cards.map(card => `
        <article class="metric-card">
            <p class="metric-kicker">${card.title}</p>
            <h2 class="metric-value">${card.value}</h2>
            <p class="metric-caption">${card.copy}</p>
        </article>
    `).join(""));
}

function renderBudgetForecast(items, evidence) {
    const canvas = document.getElementById("budgetForecastChart");
    const uncertainty = evidence.uncertainty || {};
    const backtest = evidence.backtest || {};
    const assumptionsOpen = document.querySelector('#budgetForecastEvidence details')?.open || false;
    Alfred.setHTML(document.getElementById("budgetForecastEvidence"), `
        <p>${items.length ? "Planning estimate" : "Forecast unavailable: add income evidence and a completed recorded spending month"}. As of ${Alfred.escapeHtml(evidence.as_of || "unavailable")}. Not calibrated.</p>
        <p>${Alfred.escapeHtml(evidence.method || "Forecast evidence is unavailable.")}</p>
        <p>${uncertainty.status === "HISTORICAL_RANGE" ? `Historical monthly living-spend range: ${Alfred.formatCurrency(uncertainty.expense_low)} to ${Alfred.formatCurrency(uncertainty.expense_high)}.` : "Uncertainty range unavailable: fewer than three completed recorded months."} ${Alfred.escapeHtml(uncertainty.method || "No calibrated prediction interval is available.")}</p>
        <p>${backtest.status === "OBSERVED_ERROR" ? `Walk-forward spending error (MAE): ${Alfred.formatCurrency(backtest.mae)} across ${Alfred.formatNumber(backtest.samples, 0)} held-out recorded months. The previous three-month range contained the actual month in ${Alfred.formatNumber(backtest.range_hits, 0)} of ${Alfred.formatNumber(backtest.samples, 0)}. This does not establish future forecast accuracy.` : "Chronological backtest unavailable: at least four completed recorded months are needed."}</p>
        <details ${assumptionsOpen ? "open" : ""}><summary>Assumptions and recorded months</summary>
            <ul>${(evidence.assumptions || []).map(item => `<li>${Alfred.escapeHtml(item)}</li>`).join("")}</ul>
            <ul>${(evidence.observations || []).map(row => `<li>${Alfred.escapeHtml(row.month)}: ${Alfred.formatCurrency(row.living_spend)}</li>`).join("") || "<li>No completed recorded living-spend months.</li>"}</ul>
        </details>`);
    canvas.hidden = !items.length;
    if (!items.length) return;
    budgetForecastChart = Alfred.renderChart(budgetForecastChart, canvas, {
        data: {
            labels: items.map(item => item.month),
            datasets: [
                {
                    type: "bar",
                    label: "Estimated living costs",
                    data: items.map(item => item.predicted_expense || 0),
                    backgroundColor: "rgba(24, 88, 214, 0.72)",
                    borderRadius: 10,
                },
                {
                    type: "line",
                    label: "Income left before investments",
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
    Alfred.setHTML(panel, [
        ["Remaining Budget", affordability.remaining_budget == null ? "Unavailable" : Alfred.formatCurrency(affordability.remaining_budget)],
        ["Days Remaining", Alfred.formatNumber(affordability.days_remaining, 0)],
        ["Today's Spend", Alfred.formatCurrency(affordability.today_spending)],
        ["Average Daily Spend", Alfred.formatCurrency(affordability.avg_daily_spending)],
    ].map(([label, value]) => `
        <div class="data-row">
            <div class="data-label">${label}</div>
            <div class="data-value">${value}</div>
        </div>
    `).join(""));

    const tones = {
        GOOD: "status-stable",
        WARNING: "status-guarded",
        OVER_BUDGET: "status-high",
        PLAN_ONLY: "status-guarded",
        UNAVAILABLE: "status-guarded",
    };
    Alfred.setHTML(document.getElementById("budgetDailyStatus"), `
        <div class="d-flex justify-content-between align-items-center flex-wrap gap-3">
            <span class="status-pill ${tones[affordability.status] || "status-stable"}">${Alfred.escapeHtml(affordability.status || "UNKNOWN")}</span>
            <span>${Alfred.escapeHtml(affordability.message || "No affordability signal yet.")}</span>
        </div>
    `);
}

function renderBudgetCategories(items) {
    const body = document.getElementById("budgetCategoryBody");
    if (!items.length) {
        Alfred.setHTML(body, `<tr><td colspan="5" class="text-center muted py-4">No category signals yet. Add a budget and some expenses first.</td></tr>`);
        return;
    }

    Alfred.setHTML(body, items.map(item => `
        <tr>
            <td>
                <div class="fw-semibold">${Alfred.escapeHtml(item.label)}</div>
                <div class="muted small">Monthly average ${Alfred.formatCurrency(item.historical_avg)}</div>
            </td>
            <td class="text-end">${planMoney(item.limit)}</td>
            <td class="text-end">${planMoney(item.spent)}</td>
            <td class="text-end ${item.remaining < 0 ? "text-danger" : ""}">${planMoney(item.remaining)}</td>
            <td class="text-end"><span class="status-pill ${categoryTone(item.status)}">${item.percent_used == null ? "—" : Alfred.formatPercent(item.percent_used)}</span></td>
        </tr>
    `).join(""));
}

function renderBudgetSuggestions(items) {
    const target = document.getElementById("budgetSuggestionList");
    if (!items.length) {
        Alfred.setHTML(target, `<li class="insight-item surface-card">Budget recommendations will appear once income and transaction patterns are available.</li>`);
        return;
    }

    Alfred.setHTML(target, items.map(item => `<li class="insight-item surface-card">${Alfred.escapeHtml(item)}</li>`).join(""));
}

function renderBudgetHistory(items) {
    const target = document.getElementById("budgetHistoryList");
    if (!items.length) {
        Alfred.setHTML(target, `<div class="empty-state">No stored budget plans yet.</div>`);
        return;
    }

    Alfred.setHTML(target, items.map(item => `
        <div class="mini-card surface-card">
            <div class="d-flex justify-content-between align-items-start gap-3">
                <div>
                    <div class="fw-semibold">${Alfred.escapeHtml(item.month)}</div>
                    <div class="muted small">Base ${Alfred.formatCurrency(item.base_budget, item.currency || "INR")} • Adjusted ${Alfred.formatCurrency(item.inflation_adjusted, item.currency || "INR")}</div>
                </div>
                <strong>${Alfred.formatCurrency(item.spent, item.currency || "INR")}</strong>
            </div>
        </div>
    `).join(""));
}

function hydrateBudgetForm(plan, month) {
    if (!plan) {
        document.getElementById("budgetPlanForm").month.value = month;
        return;
    }

    const form = document.getElementById("budgetPlanForm");
    form.month.value = plan.month;
    form.base_budget.value = plan.base_budget;
    form.inflation_adjusted.value = plan.inflation_adjusted;
    form.currency.value = plan.currency || "";
}

function submitBudgetPlan(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const payload = Object.fromEntries(new FormData(form).entries());
    const button = form.querySelector('button[type="submit"]');
    if (button.disabled) return;
    button.disabled = true;

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
        .catch(error => showBudgetFeedback(error.message, "danger"))
        .finally(() => { button.disabled = false; });
}

function loadSavingsGoals() {
    return Alfred.fetchJSON("/api/budgets/goals/")
        .then(renderSavingsGoals)
        .catch(error => showSavingsGoalFeedback(error.message, "danger"));
}

function renderSavingsGoals(goals) {
    const target = document.getElementById("savingsGoalList");
    if (!goals.length) {
        target.innerHTML = `<div class="empty-state">No savings goals yet.</div>`;
        return;
    }
    target.innerHTML = goals.map(goal => {
        const p = goal.progress || {};
        const money = value => Alfred.formatCurrency(value, goal.currency || "INR");
        const plan = p.status === "reached" ? "Target reached."
            : p.status === "overdue" ? `Target date passed with ${money(p.remaining)} left.`
            : p.monthly_needed != null ? `${money(p.monthly_needed)} a month for ${p.months_left} month(s) reaches it.`
            : `${money(p.remaining)} left. Add a target date to see a monthly amount.`;
        return `
        <div class="mini-card surface-card" data-goal-id="${goal.id}">
            <div class="d-flex justify-content-between flex-wrap gap-2">
                <strong>${Alfred.escapeHtml(goal.name)}</strong>
                <span class="muted small">${money(goal.saved_amount)} of ${money(goal.target_amount)}${goal.target_date ? ` by ${Alfred.formatDate(goal.target_date)}` : ""}</span>
            </div>
            <div class="progress my-2" role="progressbar" aria-label="${Alfred.escapeHtml(goal.name)} progress" aria-valuenow="${p.percent}" aria-valuemin="0" aria-valuemax="100">
                <div class="progress-bar" style="width: ${Number(p.percent) || 0}%"></div>
            </div>
            <p class="small mb-2">${Alfred.escapeHtml(`${p.percent}% saved. ${plan}`)}</p>
            <div class="d-flex flex-wrap gap-2 align-items-end">
                <div>
                    <label class="form-label small mb-1" for="savingsGoalUpdate${goal.id}">Saved so far</label>
                    <input class="form-control form-control-sm" id="savingsGoalUpdate${goal.id}" type="number" min="0" step="0.01" value="${Alfred.escapeHtml(String(goal.saved_amount))}">
                </div>
                <button type="button" class="btn btn-outline-primary btn-sm" data-goal-save="${goal.id}">Update</button>
                <button type="button" class="btn btn-outline-danger btn-sm" data-goal-delete="${goal.id}">Delete</button>
            </div>
            ${p.status === "open" && p.months_left ? `
            <div class="d-flex flex-wrap gap-2 align-items-end mt-2">
                <div>
                    <label class="form-label small mb-1" for="savingsGoalPlanAmount${goal.id}">If I save each month</label>
                    <input class="form-control form-control-sm" id="savingsGoalPlanAmount${goal.id}" type="number" min="0" step="0.01">
                </div>
                <button type="button" class="btn btn-outline-secondary btn-sm" data-goal-plan="${goal.id}">Return needed</button>
            </div>
            <p class="small mt-2 mb-0" id="savingsGoalPlanResult${goal.id}" aria-live="polite"></p>` : ""}
        </div>`;
    }).join("");
    target.querySelectorAll("[data-goal-save]").forEach(button => button.addEventListener("click", () => updateSavingsGoal(button)));
    target.querySelectorAll("[data-goal-delete]").forEach(button => button.addEventListener("click", () => deleteSavingsGoal(button)));
    target.querySelectorAll("[data-goal-plan]").forEach(button => button.addEventListener("click", () => planSavingsGoal(button)));
}

const GOAL_RETURN_BANDS = {
    no_growth: "No growth needed: saving this much reaches the target on its own.",
    conservative: "Conservative (up to 4% a year).",
    moderate: "Moderate (up to 8% a year).",
    aggressive: "Aggressive (up to 12% a year).",
    unrealistic: "Unrealistic: above 12% a year. Save more each month or move the date.",
};

function planSavingsGoal(button) {
    const id = button.dataset.goalPlan;
    const amount = document.getElementById(`savingsGoalPlanAmount${id}`).value;
    const result = document.getElementById(`savingsGoalPlanResult${id}`);
    button.disabled = true;
    Alfred.fetchJSON(`/api/budgets/goals/${id}/plan/?monthly_contribution=${encodeURIComponent(amount || "0")}`)
        .then(data => {
            const needed = data.required_annual_return_percent;
            const lead = needed == null ? "Even 100% a month would not reach this target." : `Needs about ${needed}% a year.`;
            result.textContent = `${lead} ${GOAL_RETURN_BANDS[data.band] || ""} ${data.assumptions.join(" ")}`;
        })
        .catch(error => { result.textContent = error.message; })
        .finally(() => { button.disabled = false; });
}

function submitSavingsGoal(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const button = form.querySelector('button[type="submit"]');
    if (button.disabled) return;
    const payload = Object.fromEntries(new FormData(form).entries());
    payload.saved_amount = payload.saved_amount || "0";
    if (!payload.target_date) delete payload.target_date;
    button.disabled = true;
    Alfred.fetchJSON("/api/budgets/goals/", { method: "POST", body: JSON.stringify(payload) })
        .then(() => { form.reset(); showSavingsGoalFeedback("Goal saved.", "success"); return loadSavingsGoals(); })
        .catch(error => showSavingsGoalFeedback(error.message, "danger"))
        .finally(() => { button.disabled = false; });
}

function updateSavingsGoal(button) {
    const id = button.dataset.goalSave;
    const value = document.getElementById(`savingsGoalUpdate${id}`).value;
    button.disabled = true;
    Alfred.fetchJSON(`/api/budgets/goals/${id}/`, { method: "PATCH", body: JSON.stringify({ saved_amount: value || "0" }) })
        .then(() => { showSavingsGoalFeedback("Progress updated.", "success"); return loadSavingsGoals(); })
        .catch(error => { button.disabled = false; showSavingsGoalFeedback(error.message, "danger"); });
}

function deleteSavingsGoal(button) {
    if (!window.confirm("Delete this savings goal? Your transactions and budgets are not affected.")) return;
    button.disabled = true;
    Alfred.fetchJSON(`/api/budgets/goals/${button.dataset.goalDelete}/`, { method: "DELETE" })
        .then(() => { showSavingsGoalFeedback("Goal deleted.", "success"); return loadSavingsGoals(); })
        .catch(error => { button.disabled = false; showSavingsGoalFeedback(error.message, "danger"); });
}

function showSavingsGoalFeedback(message, tone) {
    const box = document.getElementById("savingsGoalFeedback");
    box.className = `alert alert-${tone}`;
    box.textContent = message;
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
