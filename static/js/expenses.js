let expenseChart;
let expenseIndex = new Map();
let expenseModal;

document.addEventListener("DOMContentLoaded", () => {
    if (!document.getElementById("expenseRoot")) {
        return;
    }

    expenseModal = new bootstrap.Modal(document.getElementById("expenseModal"));

    document.getElementById("expenseForm").addEventListener("submit", submitExpenseForm);
    document.getElementById("uploadStatementBtn").addEventListener("click", uploadStatement);

    refreshExpenseWorkspace();
    Alfred.enableLiveRefresh("expenses-live", refreshExpenseWorkspace, { rootId: "expenseRoot" });
});

function getCookie(name) {
    const cookieValue = document.cookie
        .split(";")
        .map(item => item.trim())
        .find(item => item.startsWith(`${name}=`));
    return cookieValue ? decodeURIComponent(cookieValue.split("=")[1]) : "";
}

function apiFetch(url, options = {}) {
    const config = {
        credentials: "same-origin",
        headers: { ...(options.headers || {}) },
        ...options,
    };

    if (!(config.body instanceof FormData) && !config.headers["Content-Type"] && config.body) {
        config.headers["Content-Type"] = "application/json";
    }

    if (!["GET", "HEAD", "OPTIONS", undefined].includes(config.method)) {
        config.headers["X-CSRFToken"] = getCookie("csrftoken");
    }

    return fetch(url, config).then(async response => {
        const payload = await response.json().catch(() => ({}));
        if (!response.ok) {
            throw new Error(payload.detail || "Request failed.");
        }
        return payload;
    });
}

function loadTimeline(options = {}) {
    return apiFetch("/api/expenses/timeline/")
        .then(data => {
            renderSummary(data.summary);
            renderLatestUpload(data.latest_upload);
            renderTimeline(data.timeline);
        })
        .catch(error => {
            if (options.surfaceError !== false) {
                showUploadStatus(error.message, "danger");
            }
            throw error;
        });
}

function loadChart(options = {}) {
    return apiFetch("/api/expenses/chart/")
        .then(data => {
            const canvas = document.getElementById("expenseTrend");
            if (expenseChart) {
                expenseChart.destroy();
            }

            expenseChart = new Chart(canvas, {
                type: "bar",
                data: {
                    labels: data.labels,
                    datasets: [
                        {
                            label: "Expenses",
                            data: data.expense_values,
                            backgroundColor: "rgba(13, 110, 253, 0.75)",
                        },
                        {
                            label: "Loans",
                            data: data.loan_values,
                            backgroundColor: "rgba(220, 53, 69, 0.75)",
                        },
                        {
                            label: "Other",
                            data: data.other_values,
                            backgroundColor: "rgba(108, 117, 125, 0.75)",
                        },
                        {
                            label: "Income",
                            data: data.income_values,
                            backgroundColor: "rgba(25, 135, 84, 0.75)",
                        },
                    ],
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: { position: "bottom" },
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                        },
                    },
                },
            });
        })
        .catch(error => {
            if (options.surfaceError !== false) {
                showUploadStatus(error.message, "danger");
            }
            throw error;
        });
}

function loadBalanceSheet(options = {}) {
    return apiFetch("/api/expenses/dashboard/")
        .then(data => renderBalanceSheet(data.balance_sheet || {}))
        .catch(error => {
            if (options.surfaceError !== false) {
                showUploadStatus(error.message, "danger");
            }
            throw error;
        });
}

function refreshExpenseWorkspace() {
    return Promise.all([
        loadTimeline({ surfaceError: false }),
        loadChart({ surfaceError: false }),
        loadBalanceSheet({ surfaceError: false }),
    ])
        .then(() => Alfred.clearPageAlert("expenseRoot"))
        .catch(error => {
            Alfred.upsertPageAlert("expenseRoot", error.message, "danger");
        });
}

function renderSummary(summary) {
    const cards = [
        { label: "Expense Spend", value: summary.expense_total, tone: "primary" },
        { label: "Loan Payments", value: summary.loan_total, tone: "danger" },
        { label: "Other Outflows", value: summary.other_total, tone: "secondary" },
        { label: "Income / Credits", value: summary.income_total, tone: "success" },
    ];

    document.getElementById("summaryCards").innerHTML = cards.map(card => `
        <div class="col-md-6 col-xl-3">
            <div class="card shadow-sm border-0 h-100">
                <div class="card-body">
                    <small class="text-uppercase text-${card.tone} fw-semibold">${card.label}</small>
                    <h3 class="fw-bold mt-2 mb-1">${formatCurrency(card.value)}</h3>
                    <div class="text-muted small">${summary.transaction_count} total transactions tracked</div>
                </div>
            </div>
        </div>
    `).join("");
}

function renderLatestUpload(upload) {
    const target = document.getElementById("lastUploadMeta");
    if (!upload) {
        target.textContent = "No statement imported yet. Upload a PDF to auto-populate your timeline and document history.";
        return;
    }

    target.innerHTML = `
        <div><strong>Last import:</strong> ${upload.file_name}</div>
        <div>${upload.source ? upload.source.replaceAll("_", " ") : "Statement"} | parser ${(Number(upload.parse_confidence || 0) * 100).toFixed(0)}%</div>
        <div>${upload.account_holder || upload.institution_name || "Account"} ${upload.account_number ? `| ${maskAccount(upload.account_number)}` : ""}</div>
        <div>${upload.statement_start || "?"} to ${upload.statement_end || "?"} | ${upload.imported_count} new rows</div>
    `;
}

function renderBalanceSheet(balanceSheet) {
    const cards = [
        { label: "Assets", value: balanceSheet.total_assets || 0, tone: "success" },
        { label: "Liabilities", value: balanceSheet.total_liabilities || 0, tone: "danger" },
        { label: "Net Worth", value: balanceSheet.net_worth || 0, tone: (balanceSheet.net_worth || 0) >= 0 ? "primary" : "warning" },
        { label: "A/L Ratio", value: Number(balanceSheet.asset_liability_ratio || 0).toFixed(2), tone: "secondary", raw: true },
    ];

    document.getElementById("balanceSheetCards").innerHTML = cards.map(card => `
        <div class="col-md-6">
            <div class="card shadow-sm border-0 h-100">
                <div class="card-body">
                    <small class="text-uppercase text-${card.tone} fw-semibold">${card.label}</small>
                    <h4 class="fw-bold mt-2 mb-1">${card.raw ? Alfred.escapeHtml(card.value) : formatCurrency(card.value)}</h4>
                    <div class="text-muted small">${balanceSheet.summary || "Balance sheet view is waiting for richer data."}</div>
                </div>
            </div>
        </div>
    `).join("");

    const assets = balanceSheet.assets || [];
    const liabilities = balanceSheet.liabilities || [];
    const vehicles = balanceSheet.vehicle_positions || [];
    document.getElementById("balanceSheetPanel").innerHTML = `
        <div class="data-row">
            <div class="data-label">Assets</div>
            <div class="data-value">${assets.map(item => `${Alfred.escapeHtml(item.label)} ${formatCurrency(item.amount)}`).join(" | ") || "No assets tracked"}</div>
        </div>
        <div class="data-row">
            <div class="data-label">Liabilities</div>
            <div class="data-value">${liabilities.map(item => `${Alfred.escapeHtml(item.label)} ${formatCurrency(item.amount)}`).join(" | ") || "No liabilities tracked"}</div>
        </div>
        <div class="data-row">
            <div class="data-label">Vehicles</div>
            <div class="data-value">${vehicles.length ? vehicles.map(item => `${Alfred.escapeHtml(item.vehicle)} ${Alfred.escapeHtml(item.bucket)} ${formatCurrency(item.recognized_value)}`).join(" | ") : "No vehicle classification yet"}</div>
        </div>
    `;
}

function renderTimeline(timeline) {
    expenseIndex = new Map();
    const body = document.getElementById("timelineBody");

    if (!timeline.length) {
        body.innerHTML = `
            <tr>
                <td colspan="9" class="text-center text-muted py-4">No expenses yet. Add one manually or import a bank statement.</td>
            </tr>
        `;
        return;
    }

    body.innerHTML = timeline.map(group => {
        const rows = group.items.map(item => {
            expenseIndex.set(item.id, item);
            const amountClass = item.direction === "credit" ? "text-success" : "text-dark";

            return `
                <tr>
                    <td>${formatDate(item.transaction_date)}</td>
                    <td>
                        <div class="fw-semibold">${escapeHtml(item.merchant || "Unspecified")}</div>
                        <div class="small text-muted">${escapeHtml(item.external_reference || "")}</div>
                    </td>
                    <td>${badge(item.classification_label, classificationTone(item.classification))}</td>
                    <td>${badge(item.category_label, "light text-dark border")}</td>
                    <td>${escapeHtml(item.payment_mode || "BANK")}</td>
                    <td class="text-end fw-semibold ${amountClass}">${item.direction === "credit" ? "+" : "-"}${formatCurrency(item.amount)}</td>
                    <td>${escapeHtml(item.source_label)}</td>
                    <td class="text-muted small">${escapeHtml(item.description || item.raw_description || "")}</td>
                    <td class="text-end">
                        <button class="btn btn-sm btn-outline-primary me-1" type="button" onclick="openEditModal(${item.id})">Edit</button>
                        <button class="btn btn-sm btn-outline-danger" type="button" onclick="deleteExpense(${item.id})">Delete</button>
                    </td>
                </tr>
            `;
        }).join("");

        return `
            <tr class="table-light">
                <td colspan="9" class="fw-semibold">
                    ${formatDate(group.date)}<span class="text-muted fw-normal"> | Outflow ${formatCurrency(group.day_total)}</span>
                </td>
            </tr>
            ${rows}
        `;
    }).join("");
}

function submitExpenseForm(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const payload = Object.fromEntries(new FormData(form).entries());
    const expenseId = payload.id;
    delete payload.id;
    payload.amount = Number(payload.amount);

    const method = expenseId ? "PATCH" : "POST";
    const url = expenseId ? `/api/expenses/${expenseId}/` : "/api/expenses/";
    const errorBox = document.getElementById("expenseFormError");
    errorBox.classList.add("d-none");
    errorBox.textContent = "";

    apiFetch(url, {
        method,
        body: JSON.stringify(payload),
    })
        .then(() => {
            expenseModal.hide();
            form.reset();
            refreshExpenseWorkspace();
        })
        .catch(error => {
            errorBox.textContent = error.message;
            errorBox.classList.remove("d-none");
        });
}

function uploadStatement() {
    const fileInput = document.getElementById("statementFile");
    const file = fileInput.files[0];
    if (!file) {
        showUploadStatus("Choose a PDF statement first.", "warning");
        return;
    }

    const button = document.getElementById("uploadStatementBtn");
    const statementKind = document.getElementById("statementKind").value;
    const formData = new FormData();
    formData.append("statement", file);
    if (statementKind) {
        formData.append("statement_kind", statementKind);
    }

    button.disabled = true;
    button.textContent = "Importing...";

    apiFetch("/api/expenses/import-statement/", {
        method: "POST",
        body: formData,
    })
        .then(data => {
            showUploadStatus(
                `${data.detail} Skipped ${data.skipped_count} duplicate rows.`,
                "success"
            );
            fileInput.value = "";
            document.getElementById("statementKind").value = "";
            refreshExpenseWorkspace();
        })
        .catch(error => showUploadStatus(error.message, "danger"))
        .finally(() => {
            button.disabled = false;
            button.textContent = "Import statement";
        });
}

function openCreateModal() {
    const form = document.getElementById("expenseForm");
    form.reset();
    form.elements.source.value = "manual";
    form.elements.direction.value = "debit";
    form.elements.classification.value = "expense";
    form.elements.transaction_date.value = todayLocal();
    document.getElementById("expenseId").value = "";
    document.getElementById("expenseModalTitle").textContent = "Add Expense";
    document.getElementById("expenseSubmitBtn").textContent = "Save Expense";
    document.getElementById("expenseFormError").classList.add("d-none");
    expenseModal.show();
}

function openEditModal(id) {
    const expense = expenseIndex.get(id);
    if (!expense) {
        return;
    }

    const form = document.getElementById("expenseForm");
    form.elements.id.value = expense.id;
    form.elements.transaction_date.value = expense.transaction_date;
    form.elements.classification.value = expense.classification;
    form.elements.category.value = expense.category;
    form.elements.amount.value = expense.amount;
    form.elements.payment_mode.value = expense.payment_mode || "";
    form.elements.direction.value = expense.direction;
    form.elements.merchant.value = expense.merchant || "";
    form.elements.source.value = expense.source;
    form.elements.description.value = expense.description || expense.raw_description || "";
    document.getElementById("expenseModalTitle").textContent = "Edit Transaction";
    document.getElementById("expenseSubmitBtn").textContent = "Update Expense";
    document.getElementById("expenseFormError").classList.add("d-none");
    expenseModal.show();
}

function deleteExpense(id) {
    if (!window.confirm("Delete this transaction?")) {
        return;
    }

    apiFetch(`/api/expenses/${id}/`, { method: "DELETE" })
        .then(() => {
            refreshExpenseWorkspace();
        })
        .catch(error => showUploadStatus(error.message, "danger"));
}

function showUploadStatus(message, tone) {
    document.getElementById("statementUploadStatus").innerHTML = `
        <div class="alert alert-${tone} mb-0">${escapeHtml(message)}</div>
    `;
}

function classificationTone(value) {
    if (value === "expense") {
        return "primary";
    }
    if (value === "loan") {
        return "danger";
    }
    return "secondary";
}

function badge(text, toneClass) {
    return `<span class="badge rounded-pill bg-${toneClass}">${escapeHtml(text)}</span>`;
}

function formatCurrency(value) {
    return new Intl.NumberFormat("en-IN", {
        style: "currency",
        currency: "INR",
        maximumFractionDigits: 2,
    }).format(Number(value || 0));
}

function formatDate(value) {
    return new Date(`${value}T00:00:00`).toLocaleDateString("en-IN", {
        day: "2-digit",
        month: "short",
        year: "numeric",
    });
}

function todayLocal() {
    const now = new Date();
    const offsetMs = now.getTimezoneOffset() * 60000;
    return new Date(now.getTime() - offsetMs).toISOString().slice(0, 10);
}

function maskAccount(value) {
    const digits = String(value || "").replace(/\D/g, "");
    if (digits.length < 4) {
        return value || "";
    }
    return `****${digits.slice(-4)}`;
}

function escapeHtml(value) {
    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll("\"", "&quot;")
        .replaceAll("'", "&#39;");
}

window.openCreateModal = openCreateModal;
window.openEditModal = openEditModal;
window.deleteExpense = deleteExpense;
