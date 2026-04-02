let allocationChart;
let growthChart;

document.addEventListener("DOMContentLoaded", () => {
    if (!document.getElementById("investmentRoot")) {
        return;
    }

    document.getElementById("investmentForm").addEventListener("submit", submitInvestmentForm);
    loadInvestmentDashboard();
    Alfred.enableLiveRefresh("investments-live", loadInvestmentDashboard, { rootId: "investmentRoot" });
});

function loadInvestmentDashboard() {
    return Promise.all([
        Alfred.fetchJSON("/api/investments/summary/"),
        Alfred.fetchJSON("/api/investments/allocation/"),
        Alfred.fetchJSON("/api/investments/growth/"),
    ])
        .then(([summaryData, allocationData, growthData]) => {
            renderInvestmentHero(summaryData);
            renderInvestmentSummary(summaryData);
            renderAllocationChart(allocationData);
            renderGrowthChart(growthData);
            renderInvestmentRecommendations(summaryData.analysis?.recommendations || [], summaryData.market_context?.suggestions || []);
            renderInvestmentGrounding(summaryData.grounding || {});
            renderInvestmentPositions(summaryData.positions || []);
            Alfred.clearPageAlert("investmentRoot");
        })
        .catch(error => {
            Alfred.upsertPageAlert("investmentRoot", error.message, "danger");
        });
}

function renderInvestmentHero(data) {
    const summary = data.summary;
    const analysis = data.analysis || {};
    document.getElementById("investmentHeroValue").textContent = Alfred.formatCurrency(summary.total_value);
    document.getElementById("investmentHeroRisk").textContent = analysis.risk_level || summary.risk;
    document.getElementById("investmentHeroCopy").textContent = `${summary.positions} positions • diversification ${Alfred.formatNumber(analysis.diversification_score || 0)} / 100`;
}

function renderInvestmentSummary(data) {
    const summary = data.summary;
    const analysis = data.analysis || {};
    const cards = [
        { title: "Invested", value: Alfred.formatCurrency(summary.total_invested), copy: "Capital deployed so far" },
        { title: "Gain / Loss", value: Alfred.formatCurrency(summary.gain_loss), copy: `${Alfred.formatNumber(summary.annual_return, 2)}% weighted annual return` },
        { title: "Monthly SIP", value: Alfred.formatCurrency(summary.monthly_sip), copy: "Recurring monthly contribution" },
        { title: "Risk / Diversification", value: `${analysis.risk_level || summary.risk}`, copy: `${Alfred.formatNumber(analysis.diversification_score || 0)} diversification score` },
    ];

    document.getElementById("investmentSummaryCards").innerHTML = cards.map(card => `
        <article class="metric-card">
            <p class="metric-kicker">${card.title}</p>
            <h2 class="metric-value">${card.value}</h2>
            <p class="metric-caption">${card.copy}</p>
        </article>
    `).join("");
}

function renderAllocationChart(data) {
    const canvas = document.getElementById("allocationChart");
    if (allocationChart) {
        allocationChart.destroy();
    }

    allocationChart = new Chart(canvas, {
        type: "doughnut",
        data: {
            labels: data.labels,
            datasets: [{
                data: data.values,
                backgroundColor: ["#1858d6", "#ff825c", "#148f63", "#d97904", "#5c6a7f", "#0f9d8a"],
                borderWidth: 0,
            }],
        },
        options: {
            plugins: { legend: { position: "bottom" } },
            cutout: "68%",
        },
    });
}

function renderGrowthChart(data) {
    const canvas = document.getElementById("growthChart");
    if (growthChart) {
        growthChart.destroy();
    }

    growthChart = new Chart(canvas, {
        type: "line",
        data: {
            labels: data.labels,
            datasets: [{
                label: "Projected Value",
                data: data.values,
                borderColor: "#1858d6",
                backgroundColor: "rgba(24, 88, 214, 0.12)",
                fill: true,
                tension: 0.3,
            }],
        },
        options: {
            plugins: { legend: { display: false } },
        },
    });
}

function renderInvestmentRecommendations(items, marketItems) {
    const target = document.getElementById("investmentRecommendationList");
    const combined = [...items, ...(marketItems || []).map(item => item.message)];
    if (!combined.length) {
        target.innerHTML = `<li class="insight-item">Add holdings to unlock portfolio guidance.</li>`;
        return;
    }

    target.innerHTML = combined.map(item => `<li class="insight-item">${Alfred.escapeHtml(item)}</li>`).join("");
}

function renderInvestmentGrounding(grounding) {
    const cardsTarget = document.getElementById("investmentGroundingCards");
    const evidenceTarget = document.getElementById("investmentGroundingEvidence");
    const history = grounding.history || {};
    const freshness = grounding.freshness || {};
    const cards = [
        { title: "Tracked Positions", value: Alfred.formatNumber(history.positions || 0, 0), copy: "User portfolio records in this view" },
        { title: "Evidence Records", value: Alfred.formatNumber(freshness.tracked_records || 0, 0), copy: `${Alfred.formatNumber(freshness.fresh_records || 0, 0)} currently fresh` },
        { title: "Monthly SIP", value: Alfred.formatCurrency(history.monthly_sip || 0), copy: "Recurring contribution grounding" },
        { title: "Total Value", value: Alfred.formatCurrency(history.total_value || 0), copy: "Position-backed market value" },
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
    const evidenceItems = [
        ...notes.map(note => ({ note })),
        ...evidence.map(item => ({ proof: item })),
    ];
    evidenceTarget.innerHTML = evidenceItems.map(item => {
        if (item.note) {
            return `<li class="insight-item">${Alfred.escapeHtml(item.note)}</li>`;
        }
        const proof = item.proof || {};
        return `<li class="insight-item"><strong>${Alfred.escapeHtml(proof.source_name || proof.title || "Evidence")}</strong>: ${Alfred.escapeHtml(proof.summary || "")}${proof.source_url ? ` <a href="${proof.source_url}" target="_blank" rel="noopener">Proof</a>` : ""}</li>`;
    }).join("");
}

function renderInvestmentPositions(items) {
    const body = document.getElementById("investmentPositionsBody");
    if (!items.length) {
        body.innerHTML = `<tr><td colspan="6" class="text-center muted py-4">No registered positions yet.</td></tr>`;
        return;
    }

    body.innerHTML = items.map(item => `
        <tr>
            <td>
                <div class="fw-semibold">${Alfred.escapeHtml(item.asset_name)}</div>
                <div class="muted small">${Alfred.escapeHtml(item.asset_type.replaceAll("_", " "))} • ${Alfred.escapeHtml(item.institution || "Unspecified institution")}</div>
            </td>
            <td class="text-end">${Alfred.formatCurrency(item.invested_amount)}</td>
            <td class="text-end">${Alfred.formatCurrency(item.current_value)}</td>
            <td class="text-end ${Number(item.gain_loss) < 0 ? "text-danger" : "text-success"}">${Alfred.formatCurrency(item.gain_loss)}</td>
            <td class="text-end">${Alfred.formatCurrency(item.monthly_sip)}</td>
            <td>${Alfred.escapeHtml(item.risk_level || "Not set")}</td>
        </tr>
    `).join("");
}

function submitInvestmentForm(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const payload = Object.fromEntries(new FormData(form).entries());
    ["invested_amount", "monthly_sip", "current_value", "annual_return_rate"].forEach(key => {
        payload[key] = Number(payload[key] || 0);
    });

    Alfred.fetchJSON("/api/investments/", {
        method: "POST",
        body: JSON.stringify(payload),
    })
        .then(() => {
            form.reset();
            showInvestmentFeedback("Position saved.", "success");
            loadInvestmentDashboard();
        })
        .catch(error => showInvestmentFeedback(error.message, "danger"));
}

function showInvestmentFeedback(message, tone) {
    const box = document.getElementById("investmentFormFeedback");
    box.className = `alert alert-${tone} mb-0`;
    box.textContent = message;
    box.classList.remove("d-none");
}
