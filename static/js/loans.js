let loanTrendChart;
let loanIndex = new Map();
let selectedLoanIds = new Set();
let foreclosureLoanId = null;

document.addEventListener("DOMContentLoaded", () => {
    if (!document.getElementById("loanPlannerRoot")) {
        return;
    }

    document.getElementById("loanForm").addEventListener("submit", submitLoanForm);
    document.getElementById("loanConsolidationForm").addEventListener("submit", submitLoanConsolidation);
    document.getElementById("loanForeclosureForm").addEventListener("submit", submitLoanForeclosure);
    document.getElementById("loanCancelButton").addEventListener("click", resetLoanForm);
    document.getElementById("loanImportBtn").addEventListener("click", importLoanPdf);
    document.getElementById("loanDetectBtn").addEventListener("click", detectLoansFromExpenses);
    resetLoanForm();
    resetLoanConsolidationForm();
    resetForeclosureForm();
    loadLoanPage();
    Alfred.enableLiveRefresh("loans-live", loadLoanPage, { rootId: "loanPlannerRoot" });
});

function loadLoanPage() {
    return Alfred.fetchJSON("/api/loans/summary/")
        .then(renderLoanSummary)
        .then(() => Alfred.clearPageAlert("loanPlannerRoot"))
        .catch(error => {
            Alfred.upsertPageAlert("loanPlannerRoot", error.message, "danger");
        });
}

function renderLoanSummary(payload) {
    const summary = payload.summary;
    const behavior = payload.behavior;

    document.getElementById("loanDebtRatio").textContent = Alfred.formatPercent(behavior.debt_service_ratio);

    const cards = [
        {
            kicker: "Active Loans",
            value: summary.active_loans,
            caption: "Registered loans still marked active.",
        },
        {
            kicker: "Manual Outstanding",
            value: Alfred.formatCurrency(summary.manual_total_outstanding),
            caption: "Estimated outstanding balance across manual loans.",
        },
        {
            kicker: "Planned EMI",
            value: Alfred.formatCurrency(summary.manual_total_emi),
            caption: "Sum of configured monthly EMI commitments.",
        },
        {
            kicker: "Detected Repayments",
            value: Alfred.formatCurrency(summary.detected_repayment_total),
            caption: `${summary.projected_payoff_months} projected months to close current manual book.`,
        },
    ];

    document.getElementById("loanSummaryCards").innerHTML = cards.map(card => `
        <article class="metric-card">
            <p class="metric-kicker">${card.kicker}</p>
            <h2 class="metric-value">${card.value}</h2>
            <p class="metric-caption">${card.caption}</p>
        </article>
    `).join("");

    renderLoanChart(payload.chart);
    renderLoanTable(summary.manual_loans);
    renderDetectedRepayments(summary.detected_repayments);
}

function renderLoanChart(chart) {
    const ctx = document.getElementById("loanTrendChart");
    if (loanTrendChart) {
        loanTrendChart.destroy();
    }

    loanTrendChart = new Chart(ctx, {
        type: "line",
        data: {
            labels: chart.labels,
            datasets: [{
                label: "Detected loan repayments",
                data: chart.values,
                borderColor: "#c44a3d",
                backgroundColor: "rgba(196, 74, 61, 0.12)",
                fill: true,
                tension: 0.28,
                pointBackgroundColor: "#c44a3d",
            }],
        },
        options: {
            plugins: {
                legend: { position: "bottom" },
            },
            scales: {
                y: { beginAtZero: true },
            },
        },
    });
}

function renderLoanTable(loans) {
    loanIndex = new Map();
    const target = document.getElementById("loanTableBody");
    const activeIds = new Set(loans.filter(item => item.is_active).map(item => item.id));
    selectedLoanIds.forEach(id => {
        if (!activeIds.has(id)) {
            selectedLoanIds.delete(id);
        }
    });
    if (foreclosureLoanId && !activeIds.has(foreclosureLoanId)) {
        resetForeclosureForm();
    }

    if (!loans.length) {
        selectedLoanIds.clear();
        resetForeclosureForm();
        target.innerHTML = `<tr><td colspan="7" class="text-center muted py-4">No manual loans registered yet.</td></tr>`;
        renderConsolidationSelection();
        return;
    }

    target.innerHTML = loans.map(item => {
        loanIndex.set(item.id, item);
        const loanLabel = Alfred.escapeHtml(item.loan_type_label || formatLoanType(item.loan_type));
        const accountRef = item.loan_account_number
            ? `<div class="muted small">A/C ${Alfred.escapeHtml(item.loan_account_number)}</div>`
            : "";
        const statusCopy = item.closure_reason
            ? `<div class="muted small text-capitalize">${Alfred.escapeHtml(item.status || "closed")} | ${Alfred.escapeHtml(item.closure_reason)}</div>`
            : "";
        const consolidationCopy = item.consolidated_into_id
            ? `<div class="muted small">Consolidated into loan #${item.consolidated_into_id}</div>`
            : "";
        return `
            <tr>
                <td>
                    ${item.is_active ? `<input type="checkbox" class="form-check-input" ${selectedLoanIds.has(item.id) ? "checked" : ""} onchange="toggleLoanSelection(${item.id}, this.checked)">` : `<span class="muted small">-</span>`}
                </td>
                <td>
                    <div class="fw-semibold">${loanLabel}</div>
                    <div class="muted small">${Alfred.escapeHtml(item.lender || "Unspecified lender")}</div>
                    ${accountRef}
                    ${statusCopy}
                    ${consolidationCopy}
                </td>
                <td class="text-end">${Alfred.formatCurrency(item.emi)}</td>
                <td class="text-end">${Alfred.formatCurrency(item.estimated_balance)}</td>
                <td class="text-end">${item.months_remaining}</td>
                <td class="small">
                    <div>${Alfred.formatCurrency(item.recommended_prepayment)}</div>
                    <div class="muted">Projected end: ${Alfred.formatDate(item.projected_end_date)}</div>
                </td>
                <td class="text-end">
                    <button class="btn btn-sm btn-outline-primary me-2" type="button" onclick="editLoan(${item.id})">Edit</button>
                    ${item.is_active ? `<button class="btn btn-sm btn-soft-primary me-2" type="button" onclick="prepareForeclosure(${item.id})">Foreclose</button>` : ""}
                    <button class="btn btn-sm btn-outline-danger" type="button" onclick="deleteLoan(${item.id})">Delete</button>
                </td>
            </tr>
        `;
    }).join("");

    renderConsolidationSelection();
}

function renderDetectedRepayments(items) {
    const target = document.getElementById("loanDetectedRepayments");
    if (!items.length) {
        target.innerHTML = `<div class="detail-item">No loan repayments detected from imported statements yet.</div>`;
        return;
    }

    target.innerHTML = items.map(item => `
        <div class="detail-item mb-3">
            <div class="d-flex justify-content-between gap-3">
                <div>
                    <div class="fw-semibold">${Alfred.escapeHtml(item.merchant)}</div>
                    <div class="muted small">${Alfred.formatDate(item.date)} | ${Alfred.escapeHtml(item.category)}</div>
                    <div class="muted small">${Alfred.escapeHtml(item.description)}</div>
                    ${item.linked_loan ? `<div class="muted small">Matched loan: ${Alfred.escapeHtml(item.linked_loan)}${item.match_status ? ` | ${Alfred.escapeHtml(item.match_status)}` : ""}</div>` : ""}
                </div>
                <strong>${Alfred.formatCurrency(item.amount)}</strong>
            </div>
        </div>
    `).join("");
}

function submitLoanForm(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const payload = Object.fromEntries(new FormData(form).entries());
    const loanId = payload.id;
    delete payload.id;

    payload.principal = Number(payload.principal);
    payload.interest_rate = Number(payload.interest_rate);
    payload.emi = Number(payload.emi);
    payload.tenure_months = Number(payload.tenure_months);
    payload.remaining_balance = payload.remaining_balance ? Number(payload.remaining_balance) : null;
    payload.loan_account_number = payload.loan_account_number || "";
    payload.is_active = true;

    const errorBox = document.getElementById("loanFormError");
    errorBox.classList.add("d-none");
    errorBox.textContent = "";

    Alfred.fetchJSON(loanId ? `/api/loans/${loanId}/` : "/api/loans/", {
        method: loanId ? "PATCH" : "POST",
        body: JSON.stringify(payload),
    })
        .then(() => {
            resetLoanForm();
            loadLoanPage();
        })
        .catch(error => {
            errorBox.textContent = error.message;
            errorBox.classList.remove("d-none");
        });
}

function resetLoanForm() {
    const form = document.getElementById("loanForm");
    form.reset();
    form.elements.id.value = "";
    form.elements.loan_type.value = "home";
    form.elements.start_date.value = todayLocal();
    form.elements.tenure_months.value = 12;
    document.getElementById("loanSubmitButton").textContent = "Save Loan";
    document.getElementById("loanFormError").classList.add("d-none");
}

function resetLoanConsolidationForm() {
    const form = document.getElementById("loanConsolidationForm");
    form.reset();
    form.elements.loan_type.value = "personal";
    form.elements.start_date.value = todayLocal();
    form.elements.tenure_months.value = 12;
    document.getElementById("loanConsolidationFeedback").classList.add("d-none");
    renderConsolidationSelection();
}

function resetForeclosureForm() {
    foreclosureLoanId = null;
    const form = document.getElementById("loanForeclosureForm");
    form.reset();
    document.getElementById("foreclosureLoanId").value = "";
    document.getElementById("foreclosureLoanMeta").textContent = "Pick an active loan from the table below to start foreclosure.";
    document.getElementById("loanForeclosureFeedback").classList.add("d-none");
}

function editLoan(id) {
    const loan = loanIndex.get(id);
    if (!loan) {
        return;
    }

    const form = document.getElementById("loanForm");
    form.elements.id.value = loan.id;
    form.elements.loan_type.value = loan.loan_type;
    form.elements.lender.value = loan.lender || "";
    form.elements.loan_account_number.value = loan.loan_account_number || "";
    form.elements.principal.value = loan.principal;
    form.elements.interest_rate.value = loan.interest_rate;
    form.elements.emi.value = loan.emi;
    form.elements.tenure_months.value = loan.tenure_months;
    form.elements.remaining_balance.value = loan.remaining_balance || "";
    form.elements.start_date.value = loan.start_date;
    form.elements.notes.value = loan.notes || "";
    document.getElementById("loanSubmitButton").textContent = "Update Loan";
    window.scrollTo({ top: 0, behavior: "smooth" });
}

function deleteLoan(id) {
    if (!window.confirm("Delete this loan from the manual register?")) {
        return;
    }

    Alfred.fetchJSON(`/api/loans/${id}/`, { method: "DELETE" })
        .then(() => {
            resetLoanForm();
            loadLoanPage();
        })
        .catch(showLoanError);
}

function toggleLoanSelection(id, checked) {
    if (checked) {
        selectedLoanIds.add(id);
    } else {
        selectedLoanIds.delete(id);
    }
    renderConsolidationSelection();
}

function renderConsolidationSelection() {
    const target = document.getElementById("loanConsolidationSelection");
    const selected = [...selectedLoanIds].map(id => loanIndex.get(id)).filter(Boolean);
    if (!selected.length) {
        document.getElementById("consolidationPrincipal").value = "";
        target.innerHTML = "Select at least two active loans from the table below.";
        return;
    }

    const totalBalance = selected.reduce((sum, item) => sum + Number(item.estimated_balance || 0), 0);
    document.getElementById("consolidationPrincipal").value = totalBalance.toFixed(2);
    target.innerHTML = `
        <div><strong>${selected.length}</strong> loan(s) selected</div>
        <div class="muted small mt-1">${selected.map(item => Alfred.escapeHtml(item.lender || item.loan_type_label)).join(", ")}</div>
        <div class="muted small mt-1">Estimated carry balance ${Alfred.formatCurrency(totalBalance)}</div>
    `;
}

function submitLoanConsolidation(event) {
    event.preventDefault();
    if (selectedLoanIds.size < 2) {
        showLoanConsolidationFeedback("Select at least two active loans before consolidating.", "danger");
        return;
    }

    const payload = Object.fromEntries(new FormData(event.currentTarget).entries());
    payload.loan_ids = [...selectedLoanIds];
    payload.principal = Number(payload.principal || 0);
    payload.interest_rate = Number(payload.interest_rate || 0);
    payload.emi = Number(payload.emi || 0);
    payload.tenure_months = Number(payload.tenure_months || 0);

    Alfred.fetchJSON("/api/loans/consolidate/", {
        method: "POST",
        body: JSON.stringify(payload),
    })
        .then(data => {
            selectedLoanIds.clear();
            resetLoanConsolidationForm();
            showLoanConsolidationFeedback(data.message || "Loans consolidated.", "success");
            loadLoanPage();
        })
        .catch(error => showLoanConsolidationFeedback(error.message, "danger"));
}

function showLoanConsolidationFeedback(message, tone) {
    const box = document.getElementById("loanConsolidationFeedback");
    box.className = `alert alert-${tone} mb-0`;
    box.textContent = message;
    box.classList.remove("d-none");
}

function prepareForeclosure(id) {
    const loan = loanIndex.get(id);
    if (!loan) {
        return;
    }
    foreclosureLoanId = id;
    document.getElementById("foreclosureLoanId").value = id;
    document.getElementById("foreclosureAmount").value = loan.estimated_balance || loan.remaining_balance || "";
    document.getElementById("foreclosureLoanMeta").innerHTML = `
        <strong>${Alfred.escapeHtml(loan.lender || loan.loan_type_label)}</strong>
        <div class="muted small mt-1">Loan #${loan.id} | Estimated balance ${Alfred.formatCurrency(loan.estimated_balance || 0)}</div>
    `;
    window.scrollTo({ top: document.getElementById("loanForeclosureForm").getBoundingClientRect().top + window.scrollY - 80, behavior: "smooth" });
}

function submitLoanForeclosure(event) {
    event.preventDefault();
    if (!foreclosureLoanId) {
        showLoanForeclosureFeedback("Select an active loan first.", "danger");
        return;
    }

    const payload = new FormData(event.currentTarget);
    Alfred.fetchJSON(`/api/loans/${foreclosureLoanId}/payoff/`, {
        method: "POST",
        body: payload,
    })
        .then(data => {
            showLoanForeclosureFeedback(data.message || "Loan closed.", "success");
            resetForeclosureForm();
            loadLoanPage();
        })
        .catch(error => showLoanForeclosureFeedback(error.message, "danger"));
}

function showLoanForeclosureFeedback(message, tone) {
    const box = document.getElementById("loanForeclosureFeedback");
    box.className = `alert alert-${tone} mb-0`;
    box.textContent = message;
    box.classList.remove("d-none");
}

function showLoanError(error) {
    document.getElementById("loanFormError").textContent = error.message;
    document.getElementById("loanFormError").classList.remove("d-none");
}

function importLoanPdf() {
    const fileInput = document.getElementById("loanPdfFile");
    const file = fileInput.files[0];
    if (!file) {
        showLoanImportStatus("Choose a PDF loan document first.", "warning");
        return;
    }
    if (!file.name.toLowerCase().endsWith(".pdf")) {
        showLoanImportStatus("Only PDF loan documents are supported.", "warning");
        return;
    }

    const formData = new FormData();
    formData.append("file", file);
    const button = document.getElementById("loanImportBtn");
    button.disabled = true;
    button.textContent = "Importing...";

    Alfred.fetchJSON("/api/loans/import-pdf/", {
        method: "POST",
        body: formData,
    })
        .then(data => {
            fileInput.value = "";
            showLoanImportResult(data);
            loadLoanPage();
        })
        .catch(error => showLoanImportStatus(error.message, "danger"))
        .finally(() => {
            button.disabled = false;
            button.textContent = "Import Loan PDF";
        });
}

function detectLoansFromExpenses() {
    const button = document.getElementById("loanDetectBtn");
    button.disabled = true;
    button.textContent = "Detecting...";

    Alfred.fetchJSON("/api/loans/detect-from-expenses/", {
        method: "POST",
        body: JSON.stringify({}),
    })
        .then(data => {
            showLoanImportStatus(data.message || "Loan detection completed.", "success");
            loadLoanPage();
        })
        .catch(error => showLoanImportStatus(error.message, "danger"))
        .finally(() => {
            button.disabled = false;
            button.textContent = "Detect From Expenses";
        });
}

function showLoanImportStatus(message, tone) {
    document.getElementById("loanImportStatus").innerHTML = `
        <div class="alert alert-${tone} mb-0">${Alfred.escapeHtml(message)}</div>
    `;
}

function showLoanImportResult(payload) {
    const loans = Array.isArray(payload.loans) ? payload.loans : [];
    const chips = loans.map(item => {
        const label = Alfred.escapeHtml(item.loan_type_label || formatLoanType(item.loan_type));
        const lender = Alfred.escapeHtml(item.lender || "Unknown lender");
        const accountRef = item.loan_account_number ? ` | ${Alfred.escapeHtml(item.loan_account_number)}` : "";
        return `<span class="chip-neutral">${label} | ${lender}${accountRef}</span>`;
    }).join("");

    document.getElementById("loanImportStatus").innerHTML = `
        <div class="alert alert-success mb-0">
            <div>${Alfred.escapeHtml(payload.message || "Loan PDF imported successfully.")}</div>
            ${chips ? `<div class="chip-row mt-3">${chips}</div>` : ""}
        </div>
    `;
}

function formatLoanType(value) {
    return String(value || "other")
        .replaceAll("_", " ")
        .replace(/\b\w/g, match => match.toUpperCase());
}

function todayLocal() {
    const now = new Date();
    const offsetMs = now.getTimezoneOffset() * 60000;
    return new Date(now.getTime() - offsetMs).toISOString().slice(0, 10);
}

window.editLoan = editLoan;
window.deleteLoan = deleteLoan;
window.toggleLoanSelection = toggleLoanSelection;
window.prepareForeclosure = prepareForeclosure;
