let taxComparisonChart;
let taxDashboardQuery = "";

document.addEventListener("DOMContentLoaded", () => {
    if (!document.getElementById("taxRoot")) {
        return;
    }

    const form = document.getElementById("taxInputForm");
    form.addEventListener("submit", submitTaxForm);
    form.financial_year.addEventListener("change", () => {
        form.qualified_80c.value = "";
        form.qualified_home_loan_interest.value = "";
    });
    loadTaxDashboard();
    Alfred.enableLiveRefresh("tax-live", loadTaxDashboard, { rootId: "taxRoot" });
    setupCapitalGains();
});

const CAPITAL_GAIN_ASSETS = [
    ["listed_equity", "Listed shares or equity fund"],
    ["listed_other", "Other listed security"],
    ["debt_fund", "Debt fund (bought from 1 Apr 2023)"],
    ["unlisted_bond", "Market-linked or unlisted bond"],
    ["land_building", "Land or building"],
    ["other", "Gold, unlisted shares, other"],
];

function setupCapitalGains() {
    const form = document.getElementById("capitalGainsForm");
    if (!form) return;
    document.getElementById("capitalGainsAdd").addEventListener("click", () => addCapitalGainRow());
    document.getElementById("capitalGainsRows").addEventListener("click", event => {
        const button = event.target.closest("[data-remove-sale]");
        if (button) button.closest("tr").remove();
    });
    form.addEventListener("submit", submitCapitalGains);
    addCapitalGainRow();
}

function addCapitalGainRow() {
    const body = document.getElementById("capitalGainsRows");
    const n = body.rows.length + 1;
    const row = body.insertRow();
    const options = CAPITAL_GAIN_ASSETS.map(([value, label]) => `<option value="${value}">${Alfred.escapeHtml(label)}</option>`).join("");
    Alfred.setHTML(row, `
        <td><select class="form-select" name="asset_type" aria-label="Asset, sale ${n}">${options}</select></td>
        <td><input class="form-control" type="date" name="bought" required aria-label="Bought on, sale ${n}"></td>
        <td><input class="form-control" type="date" name="sold" required min="2026-04-01" max="2027-03-31" aria-label="Sold on, sale ${n}"></td>
        <td><input class="form-control" type="number" name="cost" min="0" step="0.01" required aria-label="Cost, sale ${n}"></td>
        <td><input class="form-control" type="number" name="sale_value" min="0" step="0.01" required aria-label="Sale value, sale ${n}"></td>
        <td><input class="form-check-input" type="checkbox" name="stt_paid" checked aria-label="STT paid, sale ${n}"></td>
        <td><input class="form-control" type="number" name="indexed_cost" min="0" step="0.01" aria-label="Indexed cost, sale ${n}"></td>
        <td><button class="btn btn-sm btn-outline-danger" type="button" data-remove-sale aria-label="Remove sale ${n}">Remove</button></td>`);
}

function submitCapitalGains(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const sales = [...document.getElementById("capitalGainsRows").rows].map(row => {
        const field = name => row.querySelector(`[name="${name}"]`);
        return {
            asset_type: field("asset_type").value, bought: field("bought").value, sold: field("sold").value,
            cost: field("cost").value, sale_value: field("sale_value").value, stt_paid: field("stt_paid").checked,
            indexed_cost: field("indexed_cost").value || null,
        };
    });
    const target = document.getElementById("capitalGainsResult");
    Alfred.fetchJSON("/api/integrations/tax/capital-gains/", {
        method: "POST",
        body: JSON.stringify({
            regime: form.regime.value, annual_income: form.annual_income.value || 0,
            deductions_total: form.deductions_total.value || 0, age_group: form.age_group.value, sales,
        }),
    }).then(data => renderCapitalGains(target, data))
        .catch(error => Alfred.setHTML(target, `<div class="alert alert-danger mb-0" role="alert">${Alfred.escapeHtml(error.message)}</div>`));
}

function renderCapitalGains(target, data) {
    const money = value => Alfred.formatCurrency(Number(value));
    const buckets = Object.entries(data.net_gains)
        .filter(([, value]) => Number(value))
        .map(([key, value]) => `<li>${Alfred.escapeHtml(data.sales.find(s => s.bucket === key)?.bucket_label || key)}: ${money(value)}</li>`)
        .join("");
    const setoffs = data.loss_setoffs.map(item => `<li>Loss of ${money(item.amount)} set off</li>`).join("");
    const unused = Number(data.unused_losses.short_term) + Number(data.unused_losses.long_term);
    const review = data.needs_review.map(text => `<p class="mb-0 fw-semibold">${Alfred.escapeHtml(text)}</p>`).join("");
    Alfred.setHTML(target, `
        <div class="mini-card">
            <div class="fw-semibold">Estimated total tax: ${money(data.final_tax)}</div>
            <div class="muted small mt-1">Includes tax on your other income, rebate ${money(data.rebate)}, surcharge ${money(data.surcharge)} and cess ${money(data.cess)}.</div>
            ${buckets ? `<ul class="small mt-2 mb-0">${buckets}</ul>` : ""}
            ${setoffs ? `<ul class="small mt-2 mb-0">${setoffs}</ul>` : ""}
            ${unused ? `<p class="small mt-2 mb-0">${money(unused)} of losses are left to carry forward (file your return on time to keep them).</p>` : ""}
            ${review}
            <p class="muted small mt-2 mb-0">Estimate under the Income-tax Act, 2025, sections ${Alfred.escapeHtml(Object.values(data.policy.sections).join(", "))}. Check with your tax filing before you rely on it.</p>
        </div>`);
}

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
            renderTaxChart(data.regime_comparison, taxIncomeUnavailable(data));
            if (!live) {
                renderTaxInputs(data.inputs);
            }
            renderTaxActions(taxIncomeUnavailable(data) ? [] : data.tax_savings.action_plan || [], taxIncomeUnavailable(data));
            renderTaxBenefits(data.hra, data.home_loan, taxIncomeUnavailable(data));
            renderTaxDeductions(data.deduction_catalog || []);
            Alfred.clearPageAlert("taxRoot");
        })
        .catch(error => {
            Alfred.upsertPageAlert("taxRoot", error.message, "danger");
        });
}

function taxIncomeUnavailable(data) {
    return !Number(data.annual_income);
}

function renderTaxHero(data) {
    const comparison = data.regime_comparison;
    const recommendedTax = comparison.recommendation === "old"
        ? comparison.old_regime.final_tax
        : comparison.new_regime.final_tax;

    document.getElementById("taxRegimeValue").textContent = String(comparison.recommendation || "either").toUpperCase();
    document.getElementById("taxAnnualValue").textContent = Alfred.formatCurrency(recommendedTax || 0);
    document.getElementById("taxHeroCopy").textContent = comparison.message || "Tax comparison ready.";
    if (taxIncomeUnavailable(data)) {
        document.getElementById("taxRegimeValue").textContent = "Unavailable";
        document.getElementById("taxAnnualValue").textContent = "Unavailable";
        document.getElementById("taxHeroCopy").textContent = "Confirm your income in Settings, or enter an annual income here, to estimate tax.";
    }
    const policy = data.tax_policy;
    const year = policy.assessment_year ? `FY ${policy.financial_year} · AY ${policy.assessment_year}` : `Tax year ${policy.financial_year}`;
    document.getElementById("taxPolicyCopy").textContent = `${year} (${policy.act}). Official-source rules verified ${policy.verified_at}; salary planning estimate before return-filing rounding.`;
    const coverage = data.tax_policy_coverage || {};
    const notice = document.getElementById("taxPolicyNotice");
    const check = coverage.budget_check;
    const checked = check ? `Official Budget site last checked ${check.checked_at.slice(0, 10)}: latest Budget ${check.latest_budget_year}.` : "";
    const filing = coverage.filing_year === policy.financial_year ? "" : coverage.filing_hint;
    notice.textContent = [coverage.notice, filing, checked].filter(Boolean).join(" ");
    notice.hidden = !notice.textContent;
}

function renderTaxSummary(data) {
    const comparison = data.regime_comparison;
    const cards = [
        { title: "Old Regime Tax", value: Alfred.formatCurrency(comparison.old_regime.final_tax), copy: `Effective ${Alfred.formatNumber(comparison.old_regime.effective_tax_rate, 2)}%` },
        { title: "New Regime Tax", value: Alfred.formatCurrency(comparison.new_regime.final_tax), copy: `Effective ${Alfred.formatNumber(comparison.new_regime.effective_tax_rate, 2)}%` },
        { title: "Regime Savings", value: Alfred.formatCurrency(comparison.savings), copy: comparison.message },
        { title: "Optimization Potential", value: Alfred.formatCurrency(data.tax_savings.potential_savings || 0), copy: `${Alfred.formatNumber(data.tax_savings.roi_on_tax_savings || 0, 1)}% ROI on tax-saving capital` },
    ];

    const shown = taxIncomeUnavailable(data)
        ? cards.map(card => ({ ...card, value: "Unavailable", copy: "Needs a confirmed income." }))
        : cards;
    Alfred.setHTML(document.getElementById("taxSummaryCards"), shown.map(card => `
        <article class="metric-card">
            <p class="metric-kicker">${card.title}</p>
            <h2 class="metric-value">${card.value}</h2>
            <p class="metric-caption">${Alfred.escapeHtml(card.copy)}</p>
        </article>
    `).join(""));
}

function renderTaxChart(comparison, incomeUnavailable) {
    const canvas = document.getElementById("taxComparisonChart");
    if (incomeUnavailable) {
        taxComparisonChart?.destroy();
        taxComparisonChart = null;
        return;
    }

    taxComparisonChart = Alfred.renderChart(taxComparisonChart, canvas, {
        type: "bar",
        data: {
            labels: ["Old Regime", "New Regime"],
            datasets: [{
                label: "Annual tax",
                data: [comparison.old_regime.final_tax, comparison.new_regime.final_tax],
                alfredByPoint: true,
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
    form.financial_year.value = inputs.financial_year;
    form.annual_income.value = inputs.annual_income;
    form.basic_salary.value = inputs.basic_salary;
    form.hra_received.value = inputs.hra_received;
    form.rent_paid.value = inputs.rent_paid;
    form.metro.value = String(inputs.metro);
    form.qualified_80c.value = inputs.qualified_80c ?? "";
    form.qualified_home_loan_interest.value = inputs.qualified_home_loan_interest ?? "";
    const gainsIncome = document.getElementById("cgIncome");
    if (gainsIncome && !gainsIncome.value) gainsIncome.value = inputs.annual_income || "";
}

function renderTaxActions(items, incomeUnavailable) {
    const target = document.getElementById("taxActionList");
    Alfred.setHTML(target, items.length
        ? items.map(item => `<li class="insight-item">${Alfred.escapeHtml(`${item.action} • ${Alfred.formatCurrency(item.amount)} • tax benefit ${Alfred.formatCurrency(item.tax_benefit)}`)}</li>`).join("")
        : `<li class="insight-item">${incomeUnavailable ? "Tax benefits need a confirmed income." : "No tax-saving action items available."}</li>`);
}

function renderTaxBenefits(hra, homeLoan, incomeUnavailable) {
    const panel = document.getElementById("taxBenefitPanel");
    const rows = incomeUnavailable ? [["HRA estimate", "Unavailable"]] : [
        ["HRA exemption", Alfred.formatCurrency(hra.hra_exemption || 0)],
        ["HRA tax saved", Alfred.formatCurrency(hra.tax_saved || 0)],
        ["Monthly HRA shield", Alfred.formatCurrency(hra.monthly_exemption || 0)],
    ];

    if (homeLoan) {
        rows.push(["Recorded home loan principal", Alfred.formatCurrency(homeLoan.principal_paid)]);
        rows.push(["Recorded home loan interest", Alfred.formatCurrency(homeLoan.interest_paid)]);
    }

    Alfred.setHTML(panel, rows.map(([label, value]) => `
        <div class="data-row">
            <div class="data-label">${label}</div>
            <div class="data-value">${value}</div>
        </div>
    `).join(""));
}

function renderTaxDeductions(items) {
    const target = document.getElementById("taxDeductionList");
    Alfred.setHTML(target, items.map(item => `
        <div class="mini-card">
            <div class="fw-semibold">${Alfred.escapeHtml(item.section)} • ${Alfred.escapeHtml(item.name)}</div>
            <div class="muted small mt-1">Max limit ${item.max_limit === null ? "Variable" : Alfred.formatCurrency(item.max_limit)}</div>
            <div class="muted small mt-2">${Alfred.escapeHtml(item.instruments.slice(0, 2).join(" • "))}</div>
        </div>
    `).join(""));
}

function submitTaxForm(event) {
    event.preventDefault();
    const query = new URLSearchParams(new FormData(event.currentTarget)).toString();
    loadTaxDashboard(query);
}
