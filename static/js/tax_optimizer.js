let taxComparisonChart;
let taxDashboardQuery = "";

document.addEventListener("DOMContentLoaded", () => {
    if (!document.getElementById("taxRoot")) {
        return;
    }

    document.getElementById("taxInputForm").addEventListener("submit", submitTaxForm);
    loadTaxDashboard();
    Alfred.enableLiveRefresh("tax-live", loadTaxDashboard, { rootId: "taxRoot" });
});

function loadTaxDashboard(queryOrOptions = taxDashboardQuery) {
    const live = typeof queryOrOptions === "object" && queryOrOptions !== null;
    if (live) {
        queryOrOptions = taxDashboardQuery;
    }
    taxDashboardQuery = queryOrOptions || "";
    return Alfred.fetchJSON(`/api/integrations/tax/overview/${taxDashboardQuery ? `?${taxDashboardQuery}` : ""}`)
        .then(data => {
            renderTaxHero(data);
            renderTaxSummary(data);
            renderTaxChart(data.regime_comparison);
            if (!live) {
                renderTaxInputs(data.inputs);
            }
            renderTaxActions(data.tax_savings.action_plan || []);
            renderTaxBenefits(data.hra, data.home_loan);
            renderTaxDeductions(data.deduction_catalog || []);
            Alfred.clearPageAlert("taxRoot");
        })
        .catch(error => {
            Alfred.upsertPageAlert("taxRoot", error.message, "danger");
        });
}

function renderTaxHero(data) {
    const comparison = data.regime_comparison;
    const recommendedTax = comparison.recommendation === "old"
        ? comparison.old_regime.final_tax
        : comparison.new_regime.final_tax;

    document.getElementById("taxRegimeValue").textContent = String(comparison.recommendation || "either").toUpperCase();
    document.getElementById("taxAnnualValue").textContent = Alfred.formatCurrency(recommendedTax || 0);
    document.getElementById("taxHeroCopy").textContent = comparison.message || "Tax comparison ready.";
}

function renderTaxSummary(data) {
    const comparison = data.regime_comparison;
    const cards = [
        { title: "Old Regime Tax", value: Alfred.formatCurrency(comparison.old_regime.final_tax), copy: `Effective ${Alfred.formatNumber(comparison.old_regime.effective_tax_rate, 2)}%` },
        { title: "New Regime Tax", value: Alfred.formatCurrency(comparison.new_regime.final_tax), copy: `Effective ${Alfred.formatNumber(comparison.new_regime.effective_tax_rate, 2)}%` },
        { title: "Regime Savings", value: Alfred.formatCurrency(comparison.savings), copy: comparison.message },
        { title: "Optimization Potential", value: Alfred.formatCurrency(data.tax_savings.potential_savings || 0), copy: `${Alfred.formatNumber(data.tax_savings.roi_on_tax_savings || 0, 1)}% ROI on tax-saving capital` },
    ];

    document.getElementById("taxSummaryCards").innerHTML = cards.map(card => `
        <article class="metric-card">
            <p class="metric-kicker">${card.title}</p>
            <h2 class="metric-value">${card.value}</h2>
            <p class="metric-caption">${Alfred.escapeHtml(card.copy)}</p>
        </article>
    `).join("");
}

function renderTaxChart(comparison) {
    const canvas = document.getElementById("taxComparisonChart");
    if (taxComparisonChart) {
        taxComparisonChart.destroy();
    }

    taxComparisonChart = new Chart(canvas, {
        type: "bar",
        data: {
            labels: ["Old Regime", "New Regime"],
            datasets: [{
                label: "Annual tax",
                data: [comparison.old_regime.final_tax, comparison.new_regime.final_tax],
                backgroundColor: ["rgba(24, 88, 214, 0.72)", "rgba(255, 130, 92, 0.72)"],
                borderRadius: 10,
            }],
        },
        options: {
            plugins: { legend: { display: false } },
        },
    });
}

function renderTaxInputs(inputs) {
    const form = document.getElementById("taxInputForm");
    form.annual_income.value = inputs.annual_income;
    form.basic_salary.value = inputs.basic_salary;
    form.hra_received.value = inputs.hra_received;
    form.rent_paid.value = inputs.rent_paid;
    form.metro.value = String(inputs.metro);
}

function renderTaxActions(items) {
    const target = document.getElementById("taxActionList");
    target.innerHTML = items.length
        ? items.map(item => `<li class="insight-item">${Alfred.escapeHtml(`${item.action} • ${Alfred.formatCurrency(item.amount)} • tax benefit ${Alfred.formatCurrency(item.tax_benefit)}`)}</li>`).join("")
        : `<li class="insight-item">No tax-saving action items available.</li>`;
}

function renderTaxBenefits(hra, homeLoan) {
    const panel = document.getElementById("taxBenefitPanel");
    const rows = [
        ["HRA exemption", Alfred.formatCurrency(hra.hra_exemption || 0)],
        ["HRA tax saved", Alfred.formatCurrency(hra.tax_saved || 0)],
        ["Monthly HRA shield", Alfred.formatCurrency(hra.monthly_exemption || 0)],
    ];

    if (homeLoan) {
        rows.push(["Home loan deduction", Alfred.formatCurrency(homeLoan.total_deduction || 0)]);
        rows.push(["Home loan tax saved", Alfred.formatCurrency(homeLoan.total_tax_saved || 0)]);
    }

    panel.innerHTML = rows.map(([label, value]) => `
        <div class="data-row">
            <div class="data-label">${label}</div>
            <div class="data-value">${value}</div>
        </div>
    `).join("");
}

function renderTaxDeductions(items) {
    const target = document.getElementById("taxDeductionList");
    target.innerHTML = items.map(item => `
        <div class="mini-card">
            <div class="fw-semibold">${Alfred.escapeHtml(item.section)} • ${Alfred.escapeHtml(item.name)}</div>
            <div class="muted small mt-1">Max limit ${item.max_limit === null ? "Variable" : Alfred.formatCurrency(item.max_limit)}</div>
            <div class="muted small mt-2">${Alfred.escapeHtml(item.instruments.slice(0, 2).join(" • "))}</div>
        </div>
    `).join("");
}

function submitTaxForm(event) {
    event.preventDefault();
    const query = new URLSearchParams(new FormData(event.currentTarget)).toString();
    loadTaxDashboard(query);
}
