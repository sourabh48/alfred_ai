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
            renderRecommendationHero(data.profile || {});
            renderRecommendationSummary(data);
            renderDisabledModules(data.disabled_modules || []);
            renderInvestmentRecommendations(data.investments || {});
            renderInsuranceRecommendations(data.insurance || {});
            renderGrounding(data.grounding || {});
            Alfred.clearPageAlert("recommendationsRoot");
        })
        .catch(error => {
            Alfred.upsertPageAlert("recommendationsRoot", error.message, "danger");
        });
}

function renderRecommendationHero(profile) {
    document.getElementById("recommendationPersonaValue").textContent = (profile.persona || [])[0] || "Unknown";
    document.getElementById("recommendationRiskValue").textContent = profile.risk_appetite || "Unknown";
    document.getElementById("recommendationHeroCopy").textContent = `Top spending category ${profile.top_category || "other"} | savings rate ${Alfred.formatNumber(profile.savings_rate || 0)}%`;
}

function renderRecommendationSummary(data) {
    const profile = data.profile || {};
    const cards = [
        { title: "Income", value: Alfred.formatCurrency(profile.income || 0), copy: "Monthly income used for suitability" },
        { title: "Monthly Spend", value: Alfred.formatCurrency(profile.monthly_expenses || 0), copy: "Derived from recent history" },
        { title: "Savings Rate", value: `${Alfred.formatNumber(profile.savings_rate || 0)}%`, copy: `${Alfred.formatCurrency(profile.monthly_savings || 0)} monthly savings` },
        { title: "Debt Load", value: `${Alfred.formatNumber(profile.dti_ratio || 0)}%`, copy: `${Alfred.formatCurrency(data.insurance?.total_annual_premium || 0)} annual essential premium` },
    ];

    document.getElementById("recommendationSummaryCards").innerHTML = cards.map(card => `
        <article class="metric-card">
            <p class="metric-kicker">${card.title}</p>
            <h2 class="metric-value">${card.value}</h2>
            <p class="metric-caption">${card.copy}</p>
        </article>
    `).join("");
}

function renderDisabledModules(items) {
    const target = document.getElementById("recommendationDisabledList");
    if (!items.length) {
        target.innerHTML = `<div class="empty-state">All strategy modules are active.</div>`;
        return;
    }

    target.innerHTML = items.map(item => `
        <div class="data-row align-items-start">
            <div class="data-label">
                <div class="fw-semibold">${Alfred.escapeHtml(item.label || item.key || "Module")}</div>
            </div>
            <div class="data-value muted small">${Alfred.escapeHtml(item.reason || "Disabled by configuration.")}</div>
        </div>
    `).join("");
}

function renderInvestmentRecommendations(data) {
    const recommendations = data.recommendations || [];
    renderModuleGrounding("recommendationInvestmentGrounding", data.grounding || {}, {
        emptyCopy: "No investment proof metadata is attached yet.",
        title: "Investment grounding",
    });
    const target = document.getElementById("recommendationInvestmentsList");
    target.innerHTML = renderRecommendationStack(recommendations, item => `
        <div class="fw-semibold">${Alfred.escapeHtml(item.investment.name)}</div>
        <div class="muted small">${Alfred.escapeHtml(item.investment.type)} | ${Alfred.escapeHtml(item.investment.risk)} risk</div>
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

function renderInsuranceRecommendations(data) {
    const items = data.recommendations || [];
    renderModuleGrounding("recommendationInsuranceGrounding", data.grounding || {}, {
        emptyCopy: "No insurance proof metadata is attached yet.",
        title: "Insurance grounding",
    });
    const target = document.getElementById("recommendationInsuranceList");
    target.innerHTML = renderRecommendationStack(items, item => `
        <div class="fw-semibold">${Alfred.escapeHtml(item.insurance.name)}</div>
        <div class="muted small">${Alfred.escapeHtml(item.insurance.type)} | premium ${Alfred.formatCurrency(item.insurance.premium_estimate)}</div>
        <div class="chip-row mt-2">${item.insurance.benefits.map(benefit => `<span class="chip-neutral">${Alfred.escapeHtml(benefit)}</span>`).join("")}</div>
        <div class="muted small mt-2">${item.is_essential ? "Marked essential." : "Optional coverage."} ${Alfred.escapeHtml(item.match_reason)}</div>
    `, "No insurance recommendations available.");
}

function renderGrounding(grounding) {
    const cardsTarget = document.getElementById("recommendationGroundingCards");
    const evidenceTarget = document.getElementById("recommendationGroundingEvidence");
    const history = grounding.history || {};
    const freshness = grounding.freshness || {};
    const modules = grounding.modules || [];
    const cards = [
        { title: "Monthly Income", value: Alfred.formatCurrency(history.monthly_income || 0), copy: "Current income basis" },
        { title: "Monthly Spend", value: Alfred.formatCurrency(history.monthly_expenses || 0), copy: "Recent history basis" },
        { title: "Tracked Personas", value: Alfred.formatNumber((history.tracked_personas || []).length, 0), copy: "Behavior personas influencing the stack" },
        { title: "Fresh Evidence", value: Alfred.formatNumber(freshness.fresh_records || 0, 0), copy: `${Alfred.formatNumber(freshness.tracked_records || 0, 0)} evidence records attached` },
    ];
    cardsTarget.innerHTML = cards.map(card => `
        <article class="metric-card metric-card--compact">
            <p class="metric-kicker">${card.title}</p>
            <h3 class="metric-value" style="font-size:1.35rem;">${card.value}</h3>
            <p class="metric-caption">${Alfred.escapeHtml(card.copy)}</p>
        </article>
    `).join("");

    const notes = grounding.notes || [];
    const evidence = grounding.evidence || [];
    const moduleSummaries = modules.map(item => {
        const itemFreshness = item.freshness || {};
        return `${item.label || item.key}: ${Alfred.formatNumber(itemFreshness.fresh_records || 0, 0)} fresh of ${Alfred.formatNumber(itemFreshness.tracked_records || 0, 0)} evidence item(s)`;
    });
    const entries = [
        ...notes.map(note => ({ note })),
        ...moduleSummaries.map(note => ({ note })),
        ...evidence.map(item => ({ proof: item })),
    ];
    evidenceTarget.innerHTML = entries.length
        ? entries.map(item => {
            if (item.note) {
                return `<li class="insight-item">${Alfred.escapeHtml(item.note)}</li>`;
            }
            const proof = item.proof || {};
            return `<li class="insight-item"><strong>${Alfred.escapeHtml(proof.source_name || proof.title || "Evidence")}</strong>: ${Alfred.escapeHtml(proof.summary || "")}${proof.source_url ? ` <a href="${proof.source_url}" target="_blank" rel="noopener">Proof</a>` : ""}</li>`;
        }).join("")
        : `<li class="insight-item">No supporting evidence is attached yet.</li>`;
}

function renderModuleGrounding(targetId, grounding, options = {}) {
    const target = document.getElementById(targetId);
    if (!target) {
        return;
    }
    const history = grounding.history || {};
    const freshness = grounding.freshness || {};
    const notes = grounding.notes || [];
    const evidence = grounding.evidence || [];
    if (!Object.keys(history).length && !notes.length && !evidence.length) {
        target.innerHTML = `<div class="muted small">${Alfred.escapeHtml(options.emptyCopy || "No grounding metadata attached.")}</div>`;
        return;
    }

    const pieces = [];
    if (options.title) {
        pieces.push(`<div class="fw-semibold mb-2">${Alfred.escapeHtml(options.title)}</div>`);
    }
    pieces.push(`
        <div class="data-row">
            <div class="data-label">Fresh evidence</div>
            <div class="data-value">${Alfred.formatNumber(freshness.fresh_records || 0, 0)} / ${Alfred.formatNumber(freshness.tracked_records || 0, 0)}</div>
        </div>
    `);
    if (freshness.next_stale_after) {
        pieces.push(`
            <div class="data-row">
                <div class="data-label">Next stale after</div>
                <div class="data-value">${Alfred.escapeHtml(Alfred.formatDateTime(freshness.next_stale_after))}</div>
            </div>
        `);
    }
    Object.entries(history).slice(0, 3).forEach(([key, value]) => {
        pieces.push(`
            <div class="data-row">
                <div class="data-label">${Alfred.escapeHtml(humanizeKey(key))}</div>
                <div class="data-value">${Alfred.escapeHtml(formatGroundingValue(value))}</div>
            </div>
        `);
    });
    if (notes[0]) {
        pieces.push(`<div class="muted small mt-2">${Alfred.escapeHtml(notes[0])}</div>`);
    }
    if (evidence[0]?.source_url) {
        pieces.push(`<div class="mt-2"><a href="${evidence[0].source_url}" target="_blank" rel="noopener">Open proof</a></div>`);
    }
    target.innerHTML = pieces.join("");
}

function humanizeKey(value) {
    return String(value || "")
        .replace(/_/g, " ")
        .replace(/\b\w/g, char => char.toUpperCase());
}

function formatGroundingValue(value) {
    if (Array.isArray(value)) {
        return value.join(", ") || "None";
    }
    if (typeof value === "number") {
        return Number.isInteger(value) ? Alfred.formatNumber(value, 0) : Alfred.formatNumber(value, 2);
    }
    return String(value ?? "None");
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
