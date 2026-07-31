let aiSignalChart;

document.addEventListener("DOMContentLoaded", () => {
    if (!document.getElementById("aiInsightsRoot")) {
        return;
    }

    loadAIInsights();
    Alfred.enableLiveRefresh("ai-insights-live", loadAIInsights, { rootId: "aiInsightsRoot" });
});

function loadAIInsights() {
    return Alfred.fetchJSON("/api/ai/personal-insights/")
        .then(renderAIInsights)
        .then(() => Alfred.clearPageAlert("aiInsightsRoot"))
        .catch(error => {
            Alfred.upsertPageAlert("aiInsightsRoot", error.message, "danger");
        });
}

function renderAIInsights(data) {
    const { summary, behavior, recurring_commitments: recurring, spike_days: spikes } = data;

    document.getElementById("aiPersonality").textContent = behavior.personality;
    document.getElementById("aiCoachTone").textContent = behavior.coach_tone;
    document.getElementById("aiStrategy").textContent = behavior.strategy;

    renderSummary(summary, behavior.signature, behavior.signature_readability || {});
    renderRecommendations(behavior.ai_insights);
    renderSignalChart(summary, behavior.signature);
    renderSimpleList("aiPatternFlags", behavior.pattern_flags, "No pattern flags yet.");
    renderSimpleList("aiStressDrivers", behavior.stress_drivers, "Stress drivers are currently subdued.");
    renderSimpleList("aiMinuteDetails", behavior.minute_details, "ALFRED needs more repetition in your spending history for micro-observations.");
    renderRecurring(recurring);
    renderSpikes(spikes);
}

function renderSummary(summary, signature, readability) {
    const volatility = readability.volatility || {
        label: "No pattern yet",
        summary: "ALFRED needs more months of history before it can describe spending variation clearly.",
    };
    const spikeFactor = readability.spike_factor || {
        label: "No pattern yet",
        summary: "ALFRED needs more months of history before it can describe spending jumps clearly.",
    };
    const cards = [
        { title: "Stress Score", value: `${Math.round(summary.stress_score)}/100`, copy: `${summary.risk_level} operating state` },
        { title: "Discipline Score", value: `${Math.round(summary.discipline_score)}/100`, copy: "Ability to convert inflows into durable savings" },
        { title: "Spending variation", value: volatility.label, copy: volatility.summary },
        { title: "Peak spending jumps", value: spikeFactor.label, copy: spikeFactor.summary },
    ];

    document.getElementById("aiInsightSummary").innerHTML = cards.map(card => `
        <article class="metric-card">
            <p class="metric-kicker">${card.title}</p>
            <h2 class="metric-value">${card.value}</h2>
            <p class="metric-caption">${card.copy}</p>
        </article>
    `).join("");
}

function renderRecommendations(items) {
    renderSimpleList("aiRecommendationList", items, "Import more history to unlock recommendations.");
}

function renderSignalChart(summary, signature) {
    const ctx = document.getElementById("aiSignalChart");
    if (aiSignalChart) {
        aiSignalChart.destroy();
    }

    aiSignalChart = new Chart(ctx, {
        type: "radar",
        data: {
            labels: ["Health", "Stability", "Discipline", "Liquidity", "Stress", "Savings"],
            datasets: [{
                label: "ALFRED signal map",
                data: [
                    summary.financial_health_score,
                    summary.stability_score,
                    summary.discipline_score,
                    summary.liquidity_score,
                    summary.stress_score,
                    Math.min(summary.savings_rate, 100),
                ],
                borderColor: "#1858d6",
                backgroundColor: "rgba(24, 88, 214, 0.16)",
                pointBackgroundColor: "#1858d6",
                borderWidth: 2.5,
            }],
        },
        options: {
            plugins: {
                legend: { display: false },
            },
            scales: {
                r: {
                    suggestedMin: 0,
                    suggestedMax: 100,
                    pointLabels: { font: { size: 12 } },
                },
            },
        },
    });
}

function renderRecurring(items) {
    const target = document.getElementById("aiRecurringCommitments");
    if (!items.length) {
        target.innerHTML = `<div class="detail-item">No recurring commitments detected yet.</div>`;
        return;
    }

    target.innerHTML = items.map(item => `
        <div class="detail-item mb-3">
            <div class="d-flex justify-content-between align-items-start gap-3">
                <div>
                    <div class="fw-semibold">${Alfred.escapeHtml(item.merchant)}</div>
                    <div class="muted small">${Alfred.escapeHtml(item.category)} • ${item.count} cycles</div>
                </div>
                <strong>${Alfred.formatCurrency(item.average_amount)}</strong>
            </div>
        </div>
    `).join("");
}

function renderSpikes(items) {
    const target = document.getElementById("aiSpikeDays");
    if (!items.length) {
        target.innerHTML = `<div class="detail-item">No major anomalies detected in the current ledger.</div>`;
        return;
    }

    target.innerHTML = items.map(item => `
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

function renderSimpleList(elementId, items, emptyCopy) {
    const target = document.getElementById(elementId);
    if (!items.length) {
        target.innerHTML = `<li class="insight-item">${Alfred.escapeHtml(emptyCopy)}</li>`;
        return;
    }

    target.innerHTML = items.map(item => `<li class="insight-item">${Alfred.escapeHtml(item)}</li>`).join("");
}
