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
            renderInvestmentRecommendations(summaryData.analysis?.recommendations || []);
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

function renderInvestmentRecommendations(items) {
    const target = document.getElementById("investmentRecommendationList");
    if (!items.length) {
        target.innerHTML = `<li class="insight-item">Add holdings to unlock portfolio guidance.</li>`;
        return;
    }

    target.innerHTML = items.map(item => `<li class="insight-item">${Alfred.escapeHtml(item)}</li>`).join("");
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
