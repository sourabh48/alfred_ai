let recommendationQuery = "";

document.addEventListener("DOMContentLoaded", () => {
    if (!document.getElementById("recommendationsRoot")) {
        return;
    }

    document.getElementById("recommendationFilters").addEventListener("submit", submitRecommendationFilters);
    loadRecommendations();
    Alfred.enableLiveRefresh("recommendations-live", loadRecommendations, { rootId: "recommendationsRoot" });
});

function loadRecommendations(queryOrOptions = recommendationQuery) {
    if (typeof queryOrOptions === "object" && queryOrOptions !== null) {
        queryOrOptions = recommendationQuery;
    }
    recommendationQuery = queryOrOptions || "";
    return Alfred.fetchJSON(`/api/integrations/recommendations/overview/${recommendationQuery ? `?${recommendationQuery}` : ""}`)
        .then(data => {
            renderRecommendationHero(data.profile);
            renderRecommendationSummary(data);
            renderCreditCardRecommendations(data.credit_cards.recommendations || []);
            renderLoanRecommendations(data.loans.recommendations || []);
            renderInvestmentRecommendations(data.investments);
            renderInsuranceRecommendations(data.insurance.recommendations || []);
            Alfred.clearPageAlert("recommendationsRoot");
        })
        .catch(error => {
            Alfred.upsertPageAlert("recommendationsRoot", error.message, "danger");
        });
}

function renderRecommendationHero(profile) {
    document.getElementById("recommendationPersonaValue").textContent = (profile.persona || [])[0] || "Unknown";
    document.getElementById("recommendationRiskValue").textContent = profile.risk_appetite || "Unknown";
    document.getElementById("recommendationHeroCopy").textContent = `Top spending category ${profile.top_category || "other"} • savings rate ${Alfred.formatNumber(profile.savings_rate || 0)}%`;
}

function renderRecommendationSummary(data) {
    const profile = data.profile;
    const cards = [
        { title: "Income", value: Alfred.formatCurrency(profile.income), copy: "Monthly income used for eligibility" },
        { title: "Monthly Spend", value: Alfred.formatCurrency(profile.monthly_expenses), copy: "Derived from recent history" },
        { title: "Savings Rate", value: `${Alfred.formatNumber(profile.savings_rate || 0)}%`, copy: `${Alfred.formatCurrency(profile.monthly_savings || 0)} monthly savings` },
        { title: "Debt Load", value: `${Alfred.formatNumber(profile.dti_ratio || 0)}%`, copy: `${Alfred.formatCurrency(data.insurance.total_annual_premium || 0)} annual essential premium` },
    ];

    document.getElementById("recommendationSummaryCards").innerHTML = cards.map(card => `
        <article class="metric-card">
            <p class="metric-kicker">${card.title}</p>
            <h2 class="metric-value">${card.value}</h2>
            <p class="metric-caption">${card.copy}</p>
        </article>
    `).join("");
}

function renderCreditCardRecommendations(items) {
    const target = document.getElementById("recommendationCardsList");
    target.innerHTML = renderRecommendationStack(items, item => `
        <div class="fw-semibold">${Alfred.escapeHtml(item.card.name)}</div>
        <div class="muted small">${Alfred.escapeHtml(item.card.type)} • annual fee ${Alfred.formatCurrency(item.card.annual_fee)}</div>
        <div class="chip-row mt-2">${item.card.benefits.map(benefit => `<span class="chip-neutral">${Alfred.escapeHtml(benefit)}</span>`).join("")}</div>
        <div class="muted small mt-2">${Alfred.escapeHtml(item.match_reason)}</div>
    `, "No credit card recommendations available.");
}

function renderLoanRecommendations(items) {
    const target = document.getElementById("recommendationLoansList");
    target.innerHTML = renderRecommendationStack(items, item => `
        <div class="fw-semibold">${Alfred.escapeHtml(item.loan.name)}</div>
        <div class="muted small">${Alfred.formatNumber(item.loan.interest_rate, 2)}% • ${item.loan.tenure_months} months</div>
        <div class="data-row">
            <div class="data-label">EMI</div>
            <div class="data-value">${Alfred.formatCurrency(item.emi)}</div>
        </div>
        <div class="data-row">
            <div class="data-label">Suggested amount</div>
            <div class="data-value">${Alfred.formatCurrency(item.suggested_amount)}</div>
        </div>
        <div class="muted small mt-2">${item.is_affordable ? "Fits current savings buffer." : "May stretch the current savings buffer."}</div>
    `, "No eligible loan products found.");
}

function renderInvestmentRecommendations(data) {
    const recommendations = data.recommendations || [];
    const target = document.getElementById("recommendationInvestmentsList");
    target.innerHTML = renderRecommendationStack(recommendations, item => `
        <div class="fw-semibold">${Alfred.escapeHtml(item.investment.name)}</div>
        <div class="muted small">${Alfred.escapeHtml(item.investment.type)} • ${Alfred.escapeHtml(item.investment.risk)} risk</div>
        <div class="data-row">
            <div class="data-label">Suggested amount</div>
            <div class="data-value">${Alfred.formatCurrency(item.suggested_amount)}</div>
        </div>
        <div class="data-row">
            <div class="data-label">Expected 1Y value</div>
            <div class="data-value">${Alfred.formatCurrency(item.expected_value_1y)}</div>
        </div>
        <div class="muted small mt-2">${Alfred.escapeHtml(item.match_reason)}</div>
    `, "No investment recommendations available.");

    const portfolioTarget = document.getElementById("recommendationPortfolioList");
    const allocations = data.suggested_portfolio?.allocations || [];
    portfolioTarget.innerHTML = allocations.length
        ? allocations.map(item => `
            <div class="mini-card">
                <div class="d-flex justify-content-between align-items-start gap-3">
                    <div>
                        <div class="fw-semibold">${Alfred.escapeHtml(item.product)}</div>
                        <div class="muted small">${Alfred.formatNumber(item.percentage, 0)}% allocation</div>
                    </div>
                    <strong>${Alfred.formatCurrency(item.amount)}</strong>
                </div>
            </div>
        `).join("")
        : `<div class="empty-state">No diversified portfolio suggestion yet.</div>`;
}

function renderInsuranceRecommendations(items) {
    const target = document.getElementById("recommendationInsuranceList");
    target.innerHTML = renderRecommendationStack(items, item => `
        <div class="fw-semibold">${Alfred.escapeHtml(item.insurance.name)}</div>
        <div class="muted small">${Alfred.escapeHtml(item.insurance.type)} • premium ${Alfred.formatCurrency(item.insurance.premium_estimate)}</div>
        <div class="chip-row mt-2">${item.insurance.benefits.map(benefit => `<span class="chip-neutral">${Alfred.escapeHtml(benefit)}</span>`).join("")}</div>
        <div class="muted small mt-2">${item.is_essential ? "Marked essential." : "Optional coverage."} ${Alfred.escapeHtml(item.match_reason)}</div>
    `, "No insurance recommendations available.");
}

function renderRecommendationStack(items, renderer, emptyCopy) {
    if (!items.length) {
        return `<div class="empty-state">${Alfred.escapeHtml(emptyCopy)}</div>`;
    }

    return items.map(item => `<div class="mini-card">${renderer(item)}</div>`).join("");
}

function submitRecommendationFilters(event) {
    event.preventDefault();
    const query = new URLSearchParams(new FormData(event.currentTarget)).toString();
    loadRecommendations(query);
}
