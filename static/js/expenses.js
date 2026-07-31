let expenseChart;
let expenseIndex = new Map();
let expenseModal;
let expenseChartGranularity = "monthly";
let latestStatementUpload = null;
let recentStatementUploads = [];
let currentTimelineFilters = {
    q: "",
    transaction_id: "",
    classification: "",
    source: "",
    limit: "60",
};

document.addEventListener("DOMContentLoaded", () => {
    if (!document.getElementById("expenseRoot")) {
        return;
    }

    expenseModal = new bootstrap.Modal(document.getElementById("expenseModal"));

    document.getElementById("expenseForm").addEventListener("submit", submitExpenseForm);
    document.getElementById("uploadStatementBtn").addEventListener("click", uploadStatement);
    document.getElementById("timelineFilterForm").addEventListener("submit", applyTimelineFilters);
    document.getElementById("timelineFilterResetBtn").addEventListener("click", resetTimelineFilters);
    document.getElementById("expenseChartGranularity").addEventListener("change", event => {
        expenseChartGranularity = event.currentTarget.value || "monthly";
        loadChart();
    });

    syncTimelineFilterForm();
    refreshExpenseWorkspace();
    Alfred.enableLiveRefresh("expenses-live", refreshExpenseWorkspace, { rootId: "expenseRoot" });
});

function apiFetch(url, options = {}) {
    return Alfred.fetchJSON(url, options);
}

function loadTimeline(options = {}) {
    const params = new URLSearchParams();
    Object.entries(currentTimelineFilters).forEach(([key, value]) => {
        if (String(value || "").trim()) {
            params.set(key, value);
        }
    });
    const queryString = params.toString();
    return apiFetch(`/api/expenses/timeline/${queryString ? `?${queryString}` : ""}`)
        .then(data => {
            renderSummary(data.summary);
            renderLatestUpload(data.latest_upload);
            renderMonthlyWindow(data.monthly_window || {});
            renderUnwantedExpenses(data.unwanted_expenses || {});
            renderTimeline(data.timeline, data.timeline_meta || {});
        })
        .catch(error => {
            if (options.surfaceError !== false) {
                showUploadStatus(error.message, "danger");
            }
            throw error;
        });
}

function loadStatementUploads(options = {}) {
    return apiFetch("/api/expenses/uploads/")
        .then(items => {
            recentStatementUploads = Array.isArray(items) ? items : [];
            latestStatementUpload = recentStatementUploads[0] || latestStatementUpload;
            renderStatementUploads(recentStatementUploads);
            if (!document.getElementById("lastUploadMeta")?.textContent?.trim() && latestStatementUpload) {
                renderLatestUpload(latestStatementUpload);
            }
        })
        .catch(error => {
            if (options.surfaceError !== false) {
                showUploadStatus(error.message, "danger");
            }
            throw error;
        });
}

function loadChart(options = {}) {
    const granularityControl = document.getElementById("expenseChartGranularity");
    const granularity = granularityControl?.value || expenseChartGranularity || "monthly";
    expenseChartGranularity = granularity;
    return apiFetch(`/api/expenses/chart/?granularity=${encodeURIComponent(granularity)}`)
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
                        title: {
                            display: true,
                            text: `${capitalizeFlowGranularity(data.granularity || granularity)} Financial Flow`,
                        },
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
    Alfred.setPageBusy("expenseRoot", true, { label: "Loading expense intelligence" });
    return Promise.all([
        loadTimeline({ surfaceError: false }),
        loadStatementUploads({ surfaceError: false }),
        loadChart({ surfaceError: false }),
        loadBalanceSheet({ surfaceError: false }),
    ])
        .then(() => Alfred.clearPageAlert("expenseRoot"))
        .catch(error => {
            Alfred.upsertPageAlert("expenseRoot", error.message, "danger");
        })
        .finally(() => Alfred.setPageBusy("expenseRoot", false));
}

function renderSummary(summary) {
    const target = document.getElementById("summaryCards");
    if (!target) {
        return;
    }

    const cards = [
        { key: "expense", label: "Expense Spend", value: summary.expense_total, tone: "primary" },
        { key: "loan", label: "Loan Payments", value: summary.loan_total, tone: "danger" },
        { key: "other", label: "Other Outflows", value: summary.other_total, tone: "secondary" },
        { key: "income", label: "Income / Credits", value: summary.income_total, tone: "success" },
        { key: "unwanted", label: "Potential Unwanted", value: summary.unwanted_total, tone: "warning", meta: `${summary.unwanted_count || 0} flagged entries` },
    ];

    ensureSummaryCards(target, cards);
    cards.forEach(card => {
        const cardNode = target.querySelector(`[data-expense-summary-key="${card.key}"]`);
        if (!cardNode) {
            return;
        }
        const labelNode = cardNode.querySelector('[data-role="label"]');
        const valueNode = cardNode.querySelector('[data-role="value"]');
        const metaNode = cardNode.querySelector('[data-role="meta"]');
        if (labelNode) {
            labelNode.className = `text-uppercase text-${card.tone} fw-semibold`;
            Alfred.setTextIfChanged(labelNode, card.label);
        }
        Alfred.setTextIfChanged(valueNode, formatCurrency(card.value));
        Alfred.setTextIfChanged(metaNode, card.meta || `${summary.transaction_count} total transactions tracked`);
    });
}

function ensureSummaryCards(target, cards) {
    const expectedKeys = cards.map(card => card.key);
    const currentNodes = Array.from(target.querySelectorAll("[data-expense-summary-key]"));
    const currentKeys = currentNodes.map(node => node.dataset.expenseSummaryKey);

    if (currentKeys.length === expectedKeys.length && currentKeys.every((key, index) => key === expectedKeys[index])) {
        return;
    }

    target.innerHTML = cards.map(card => `
        <div class="col-md-6 col-xl-${cards.length > 4 ? "4" : "3"}" data-expense-summary-key="${card.key}">
            <div class="card shadow-sm border-0 h-100">
                <div class="card-body">
                    <small class="text-uppercase text-${card.tone} fw-semibold" data-role="label">${escapeHtml(card.label)}</small>
                    <h3 class="fw-bold mt-2 mb-1" data-role="value">${formatCurrency(card.value)}</h3>
                    <div class="text-muted small" data-role="meta">${escapeHtml(card.meta || "")}</div>
                </div>
            </div>
        </div>
    `).join("");
}

function renderMonthlyWindow(windowData) {
    const summaryTarget = document.getElementById("expenseWindowSummary");
    const railTarget = document.getElementById("expenseWindowRail");
    if (!summaryTarget || !railTarget) {
        return;
    }

    const current = windowData.current || {};
    const previous = windowData.previous || {};
    const currentOutflow = Number(current.outflow_total || 0);
    const previousOutflow = Number(previous.outflow_total || 0);
    const delta = currentOutflow - previousOutflow;

    Alfred.setTextIfChanged("expenseWindowMonthChip", windowData.reference_month || "No month yet");
    Alfred.setTextIfChanged(
        "expenseWindowCountChip",
        `${Alfred.formatNumber(Number(current.transaction_count || 0), 0)} transactions`
    );

    Alfred.setHTMLIfChanged(summaryTarget, [
        {
            label: "Current outflow",
            value: formatCurrency(currentOutflow),
            meta: `${formatCurrency(current.expense_total || 0)} direct expenses`,
        },
        {
            label: "Previous month",
            value: formatCurrency(previousOutflow),
            meta: windowData.previous_month || "Previous month",
        },
        {
            label: "Delta",
            value: `${delta >= 0 ? "+" : ""}${formatCurrency(delta)}`,
            meta: delta >= 0 ? "Above previous month" : "Below previous month",
        },
        {
            label: "Net flow",
            value: formatCurrency(current.net_total || 0),
            meta: `${formatCurrency(current.income_total || 0)} credits this month`,
        },
    ].map(item => `
        <div class="hero-signal">
            <p class="hero-signal-label">${escapeHtml(item.label)}</p>
            <p class="hero-signal-value">${escapeHtml(item.value)}</p>
            <p class="hero-signal-meta">${escapeHtml(item.meta)}</p>
        </div>
    `).join(""));

    const items = Array.isArray(windowData.window) ? windowData.window : [];
    if (!items.length) {
        Alfred.setHTMLIfChanged(railTarget, `<div class="empty-state">Import statements or add transactions to open the monthly expense window.</div>`);
        return;
    }

    Alfred.setHTMLIfChanged(railTarget, items.map(item => {
        const itemOutflow = Number(item.outflow_total || 0);
        const itemIncome = Number(item.income_total || 0);
        const itemUnwanted = Number(item.unwanted_total || 0);
        const unwantedShare = itemOutflow ? Math.min(100, Math.round((itemUnwanted / itemOutflow) * 100)) : 0;
        return `
            <article class="window-card">
                <div class="d-flex justify-content-between align-items-start gap-3 mb-2">
                    <div class="fw-semibold">${escapeHtml(item.label || "")}</div>
                    <span class="status-pill ${item.net_total >= 0 ? "status-low" : "status-high"}">${item.net_total >= 0 ? "Positive" : "Tight"}</span>
                </div>
                <div class="window-card-value">${formatCurrency(itemOutflow)}</div>
                <div class="window-card-meta">Outflow | ${Alfred.formatNumber(Number(item.transaction_count || 0), 0)} transactions</div>
                <div class="window-card-strip mt-3">
                    <div class="window-card-fill" style="width: ${unwantedShare}%;"></div>
                </div>
                <div class="window-card-detail mt-3">
                    <span>Income ${formatCurrency(itemIncome)}</span>
                    <span>Unwanted ${formatCurrency(itemUnwanted)}</span>
                </div>
            </article>
        `;
    }).join(""));
}

function renderUnwantedExpenses(unwanted) {
    const summaryTarget = document.getElementById("unwantedExpenseSummary");
    const listTarget = document.getElementById("unwantedExpenseList");
    const chipsTarget = document.getElementById("unwantedExpenseCategoryChips");
    if (!summaryTarget || !listTarget || !chipsTarget) {
        return;
    }

    const ratio = Number(unwanted.current_month_ratio || 0);
    Alfred.setTextIfChanged("unwantedExpenseRatioPill", `${Alfred.formatNumber(ratio, 1)}% this month`);

    Alfred.setHTMLIfChanged(summaryTarget, [
        {
            label: "Current month",
            value: formatCurrency(unwanted.current_month_total || 0),
            meta: "Flagged for review or trimming",
        },
        {
            label: "Overall flagged",
            value: formatCurrency(unwanted.overall_total || 0),
            meta: `${Alfred.formatNumber(Number(unwanted.count || 0), 0)} entries tracked`,
        },
        {
            label: "Emotional",
            value: formatCurrency(unwanted.emotional_total || 0),
            meta: "Behavior-led signal",
        },
        {
            label: "Discretionary",
            value: formatCurrency(unwanted.discretionary_total || 0),
            meta: "Lifestyle-led spend",
        },
    ].map(item => `
        <div class="insight-stat">
            <p class="insight-stat-label">${escapeHtml(item.label)}</p>
            <p class="insight-stat-value">${escapeHtml(item.value)}</p>
            <p class="insight-stat-meta">${escapeHtml(item.meta)}</p>
        </div>
    `).join(""));

    const categories = Array.isArray(unwanted.top_categories) ? unwanted.top_categories : [];
    Alfred.setHTMLIfChanged(
        chipsTarget,
        categories.length
            ? categories.map(item => `<span class="chip-neutral">${escapeHtml(item.label)} ${formatCurrency(item.amount)}</span>`).join("")
            : `<span class="chip-neutral">No dominant flagged categories yet</span>`
    );

    const items = Array.isArray(unwanted.items) ? unwanted.items : [];
    if (!items.length) {
        Alfred.setHTMLIfChanged(listTarget, `<div class="empty-state">No flagged unwanted expenses yet.</div>`);
        return;
    }

    Alfred.setHTMLIfChanged(listTarget, items.map(item => `
        <div class="timeline-card mini-card">
            <div class="d-flex justify-content-between align-items-start gap-3">
                <div>
                    <div class="fw-semibold">${escapeHtml(item.merchant || "Unspecified")}</div>
                    <div class="muted small">${escapeHtml(item.signal || "Flagged")} | ${escapeHtml(item.category_label || item.category || "Other")} | ${formatDate(item.transaction_date)}</div>
                </div>
                <div class="text-end">
                    <div class="fw-semibold">${formatCurrency(item.amount)}</div>
                    <div class="muted small">Confidence ${(Number(item.model_confidence || 0) * 100).toFixed(0)}%</div>
                </div>
            </div>
            ${item.description ? `<div class="muted small mt-2">${escapeHtml(item.description)}</div>` : ""}
        </div>
    `).join(""));
}

function renderLatestUpload(upload) {
    const target = document.getElementById("lastUploadMeta");
    if (!upload) {
        target.textContent = "No statement imported yet. Upload a PDF to auto-populate your timeline and document history.";
        return;
    }

    latestStatementUpload = upload;
    const previewInfo = statementPreviewInfo(upload);
    const statusCopy = previewInfo
        ? previewInfo
        : (upload.imported_count
            ? `${upload.imported_count} new row${upload.imported_count === 1 ? "" : "s"}`
            : `${upload.parser_status_label || upload.parser_status || "Review"} | metadata only`);
    const note = upload.parser_notes ? `<div class="text-warning-emphasis small mt-1">${escapeHtml(upload.parser_notes)}</div>` : "";

    target.innerHTML = `
        <div><strong>Last import:</strong> ${upload.file_name}</div>
        <div>${upload.source ? upload.source.replaceAll("_", " ") : "Statement"} | parser ${(Number(upload.parse_confidence || 0) * 100).toFixed(0)}%</div>
        <div>${upload.account_holder || upload.institution_name || "Account"} ${upload.account_number ? `| ${maskAccount(upload.account_number)}` : ""}</div>
        <div>${upload.statement_start || "?"} to ${upload.statement_end || "?"} | ${statusCopy}</div>
        ${note}
    `;
}

function renderStatementUploads(items) {
    const target = document.getElementById("statementUploadReviewList");
    if (!target) {
        return;
    }
    if (!items.length) {
        target.innerHTML = `<div class="empty-state">No statement uploads tracked yet.</div>`;
        return;
    }

    target.innerHTML = items.slice(0, 10).map(item => {
        const parserLabel = item.parser_status_label || item.parser_status || "Unknown";
        const toneClass = item.imported_count ? "text-success" : (item.parser_status === "needs_review" ? "text-warning" : "text-danger");
        const previewInfo = statementPreviewInfo(item);
        const summary = previewInfo
            ? previewInfo
            : (item.imported_count
                ? `${item.imported_count} row${item.imported_count === 1 ? "" : "s"} imported`
                : "No transactions imported; metadata retained");
        return `
            <div class="data-row align-items-start">
                <div class="data-label">
                    <div class="fw-semibold">${escapeHtml(item.file_name || "Statement")}</div>
                    <div class="muted small">${formatDateTime(item.uploaded_at)}</div>
                </div>
                <div class="data-value">
                    <div class="${toneClass} fw-semibold">${escapeHtml(parserLabel)} | ${(Number(item.parse_confidence || 0) * 100).toFixed(0)}%</div>
                    <div class="muted small">${escapeHtml(item.bank_name || item.institution_name || "Unknown institution")} ${item.account_number ? `| ${escapeHtml(maskAccount(item.account_number))}` : ""}</div>
                    <div class="muted small">${escapeHtml(`${item.statement_start || "?"} to ${item.statement_end || "?"}`)} | ${escapeHtml(summary)}</div>
                    ${item.parser_notes ? `<div class="small mt-1">${escapeHtml(item.parser_notes)}</div>` : ""}
                </div>
            </div>
        `;
    }).join("");
}

function renderBalanceSheet(balanceSheet) {
    const cardsTarget = document.getElementById("balanceSheetCards");
    const panelTarget = document.getElementById("balanceSheetPanel");
    if (!cardsTarget || !panelTarget) {
        return;
    }
    const cards = [
        { key: "assets", label: "Assets", value: balanceSheet.total_assets || 0, tone: "success" },
        { key: "liabilities", label: "Liabilities", value: balanceSheet.total_liabilities || 0, tone: "danger" },
        { key: "net-worth", label: "Net Worth", value: balanceSheet.net_worth || 0, tone: (balanceSheet.net_worth || 0) >= 0 ? "primary" : "warning" },
        { key: "ratio", label: "A/L Ratio", value: Number(balanceSheet.asset_liability_ratio || 0).toFixed(2), tone: "secondary", raw: true },
    ];
    const sharedSummary = balanceSheet.summary || "Balance sheet view is waiting for richer data.";

    ensureBalanceSheetCards(cardsTarget, cards);
    cards.forEach(card => {
        const cardNode = cardsTarget.querySelector(`[data-balance-sheet-key="${card.key}"]`);
        if (!cardNode) {
            return;
        }
        const labelNode = cardNode.querySelector('[data-role="label"]');
        const valueNode = cardNode.querySelector('[data-role="value"]');
        const metaNode = cardNode.querySelector('[data-role="meta"]');
        if (labelNode) {
            labelNode.className = `text-uppercase text-${card.tone} fw-semibold`;
            Alfred.setTextIfChanged(labelNode, card.label);
        }
        Alfred.setTextIfChanged(valueNode, card.raw ? String(card.value) : formatCurrency(card.value));
        Alfred.setTextIfChanged(metaNode, sharedSummary);
    });

    const assets = balanceSheet.assets || [];
    const liabilities = balanceSheet.liabilities || [];
    const homeOwnership = balanceSheet.home_ownership_positions || [];
    const vehicles = balanceSheet.vehicle_positions || [];
    const rows = [
        {
            key: "assets",
            label: "Assets",
            value: assets.map(item => `${Alfred.escapeHtml(item.label)} ${formatCurrency(item.amount)}`).join(" | ") || "No assets tracked",
        },
        {
            key: "liabilities",
            label: "Liabilities",
            value: liabilities.map(item => `${Alfred.escapeHtml(item.label)} ${formatCurrency(item.amount)}`).join(" | ") || "No liabilities tracked",
        },
        {
            key: "home-ownership",
            label: "Home ownership",
            value: homeOwnership.length
                ? homeOwnership.map(item => (
                    `${Alfred.escapeHtml(item.lender || "Home loan")} | `
                    + `Acquisition base ${formatCurrency(item.property_acquisition_cost || item.financed_asset_value)} | `
                    + `Upfront cash ${formatCurrency(item.upfront_cash_invested || 0)} | `
                    + `Loan left ${formatCurrency(item.current_loan_balance)} | `
                    + `Equity ${formatCurrency(item.equity_built)} | `
                    + `Recorded cost ${formatCurrency(item.interest_and_cost_paid_recorded)}`
                )).join(" | ")
                : "No home-loan-backed property position tracked",
        },
        {
            key: "vehicles",
            label: "Vehicles",
            value: vehicles.length ? vehicles.map(item => `${Alfred.escapeHtml(item.vehicle)} ${Alfred.escapeHtml(item.bucket)} ${formatCurrency(item.recognized_value)}`).join(" | ") : "No vehicle classification yet",
        },
    ];

    ensureBalanceSheetPanel(panelTarget, rows);
    rows.forEach(row => {
        const rowNode = panelTarget.querySelector(`[data-balance-sheet-row="${row.key}"]`);
        if (!rowNode) {
            return;
        }
        const labelNode = rowNode.querySelector('[data-role="label"]');
        const valueNode = rowNode.querySelector('[data-role="value"]');
        Alfred.setTextIfChanged(labelNode, row.label);
        Alfred.setHTMLIfChanged(valueNode, row.value);
    });
}

function ensureBalanceSheetCards(target, cards) {
    const expectedKeys = cards.map(card => card.key);
    const currentNodes = Array.from(target.querySelectorAll("[data-balance-sheet-key]"));
    const currentKeys = currentNodes.map(node => node.dataset.balanceSheetKey);

    if (currentKeys.length === expectedKeys.length && currentKeys.every((key, index) => key === expectedKeys[index])) {
        return;
    }

    target.innerHTML = cards.map(card => `
        <div class="col-md-6" data-balance-sheet-key="${card.key}">
            <div class="card shadow-sm border-0 h-100">
                <div class="card-body">
                    <small class="text-uppercase text-${card.tone} fw-semibold" data-role="label">${escapeHtml(card.label)}</small>
                    <h4 class="fw-bold mt-2 mb-1" data-role="value">${card.raw ? escapeHtml(card.value) : formatCurrency(card.value)}</h4>
                    <div class="text-muted small" data-role="meta"></div>
                </div>
            </div>
        </div>
    `).join("");
}

function ensureBalanceSheetPanel(target, rows) {
    const expectedKeys = rows.map(row => row.key);
    const currentNodes = Array.from(target.querySelectorAll("[data-balance-sheet-row]"));
    const currentKeys = currentNodes.map(node => node.dataset.balanceSheetRow);

    if (currentKeys.length === expectedKeys.length && currentKeys.every((key, index) => key === expectedKeys[index])) {
        return;
    }

    target.innerHTML = rows.map(row => `
        <div class="data-row" data-balance-sheet-row="${row.key}">
            <div class="data-label" data-role="label">${escapeHtml(row.label)}</div>
            <div class="data-value" data-role="value"></div>
        </div>
    `).join("");
}

function renderTimeline(timeline, meta = {}) {
    expenseIndex = new Map();
    const body = document.getElementById("timelineBody");
    const metaBar = document.getElementById("timelineMetaBar");
    const summaryCard = document.getElementById("timelineFilteredSummary");
    const matchingCount = Number(meta.total_matching_count || 0);
    const visibleCount = Number(meta.visible_count || 0);
    const filteredExpenseTotal = Number(meta.filtered_expense_total || 0);
    const filteredLoanTotal = Number(meta.filtered_loan_total || 0);
    const filteredOtherTotal = Number(meta.filtered_other_total || 0);
    const filteredOutflowTotal = Number(meta.filtered_outflow_total || 0);
    const filteredCreditTotal = Number(meta.filtered_credit_total || 0);
    const hasMore = Boolean(meta.has_more);

    if (summaryCard) {
        const summaryConfigLabel = getUiConfig("expenses.timeline.filtered_total_label", "Filtered Expense Total");
        const activeClassification = String(meta.classification || "").trim().toLowerCase();
        let summaryLabel = summaryConfigLabel;
        let summaryValue = filteredExpenseTotal;

        if (activeClassification === "loan") {
            summaryLabel = "Filtered Loan Total";
            summaryValue = filteredLoanTotal;
        } else if (activeClassification === "other") {
            summaryLabel = "Filtered Other Total";
            summaryValue = filteredOtherTotal;
        } else if (activeClassification === "expense") {
            summaryLabel = "Filtered Expense Total";
            summaryValue = filteredExpenseTotal;
        } else if (filteredOutflowTotal > 0) {
            summaryLabel = "Filtered Spend Total";
            summaryValue = filteredOutflowTotal;
        } else if (filteredCreditTotal > 0) {
            summaryLabel = "Filtered Credit Total";
            summaryValue = filteredCreditTotal;
        }

        const breakdown = [
            `Expense ${formatCurrency(filteredExpenseTotal)}`,
            `Loan ${formatCurrency(filteredLoanTotal)}`,
            `Other ${formatCurrency(filteredOtherTotal)}`,
        ];
        if (filteredCreditTotal > 0) {
            breakdown.push(`Credits ${formatCurrency(filteredCreditTotal)}`);
        }

        summaryCard.innerHTML = `
            <div class="expense-filter-summary-label">${escapeHtml(summaryLabel)}</div>
            <div class="expense-filter-summary-value">${formatCurrency(summaryValue)}</div>
            <div class="expense-filter-summary-meta">
                ${Alfred.formatNumber(matchingCount, 0)} ${matchingCount === 1 ? "result" : "results"} | ${Alfred.formatNumber(visibleCount, 0)} visible
                <br>${escapeHtml(breakdown.join(" | "))}
            </div>
        `;
    }

    if (metaBar) {
        const pieces = [
            `${Alfred.formatNumber(matchingCount, 0)} matching`,
            `${Alfred.formatNumber(visibleCount, 0)} visible`,
        ];
        if (hasMore) {
            pieces.push(`showing latest ${Alfred.formatNumber(Number(meta.limit || visibleCount), 0)}`);
        }
        if (meta.query) {
            pieces.push(`search "${meta.query}"`);
        }
        if (meta.transaction_id) {
            pieces.push(`ID ${meta.transaction_id}`);
        }
        metaBar.textContent = pieces.join(" | ");
    }

    if (!timeline.length) {
        const uploadHint = latestStatementUpload
            ? `
                <div class="small mt-2">
                    Latest statement: ${escapeHtml(latestStatementUpload.file_name || "Statement")}
                    ${latestStatementUpload.imported_count ? `| ${latestStatementUpload.imported_count} row${latestStatementUpload.imported_count === 1 ? "" : "s"} imported` : "| metadata saved for review"}
                </div>
                ${latestStatementUpload.parser_notes ? `<div class="small text-warning-emphasis mt-1">${escapeHtml(latestStatementUpload.parser_notes)}</div>` : ""}
            `
            : "";
        body.innerHTML = `
            <tr>
                <td colspan="9" class="text-center text-muted py-4">
                    No matching transactions. Adjust the filters, add one manually, or import a bank statement.
                    ${uploadHint}
                </td>
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

function applyTimelineFilters(event) {
    event.preventDefault();
    const form = event.currentTarget;
    currentTimelineFilters = {
        q: String(form.elements.q.value || "").trim(),
        transaction_id: String(form.elements.transaction_id.value || "").trim(),
        classification: String(form.elements.classification.value || "").trim(),
        source: String(form.elements.source.value || "").trim(),
        limit: String(form.elements.limit.value || "60").trim(),
    };
    refreshExpenseWorkspace();
}

function resetTimelineFilters() {
    currentTimelineFilters = {
        q: "",
        transaction_id: "",
        classification: "",
        source: "",
        limit: "60",
    };
    syncTimelineFilterForm();
    refreshExpenseWorkspace();
}

function syncTimelineFilterForm() {
    const form = document.getElementById("timelineFilterForm");
    if (!form) {
        return;
    }
    form.elements.q.value = currentTimelineFilters.q || "";
    form.elements.transaction_id.value = currentTimelineFilters.transaction_id || "";
    form.elements.classification.value = currentTimelineFilters.classification || "";
    form.elements.source.value = currentTimelineFilters.source || "";
    form.elements.limit.value = currentTimelineFilters.limit || "60";
}

function capitalizeFlowGranularity(value) {
    const normalized = String(value || "monthly").trim().toLowerCase();
    return normalized ? `${normalized.charAt(0).toUpperCase()}${normalized.slice(1)}` : "Monthly";
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
    const files = Array.from(fileInput.files || []);
    if (!files.length) {
        showUploadStatus("Choose at least one PDF statement first.", "warning");
        return;
    }

    const button = document.getElementById("uploadStatementBtn");
    const statementKind = document.getElementById("statementKind").value;

    button.disabled = true;
    Alfred.showUploadProgress("statementUploadStatus", {
        phase: "preparing",
        percent: 0,
        current: 1,
        total: files.length,
    });

    Alfred.uploadFilesSequentially(
        files,
        (file, uploadContext) => {
            const formData = new FormData();
            formData.append("statement", file);
            if (statementKind) {
                formData.append("statement_kind", statementKind);
            }
            return Alfred.uploadJSON("/api/expenses/import-statement/", {
                method: "POST",
                body: formData,
                onUploadState: uploadContext?.reportProgress,
            });
        },
        {
            onProgress: state => Alfred.showUploadProgress("statementUploadStatus", state),
        },
    )
        .then(results => {
            const summary = summarizeStatementBatch(results);
            if (summary.succeeded.length) {
                fileInput.value = "";
                document.getElementById("statementKind").value = "";
                refreshExpenseWorkspace();
            }
            showUploadStatus(summary.message, summary.tone);
        })
        .catch(error => showUploadStatus(error.message, "danger"))
        .finally(() => {
            button.disabled = false;
        });
}

function summarizeStatementBatch(results) {
    const summary = Alfred.summarizeUploadBatch(results, { itemLabel: "statement", successVerb: "processed" });
    const importedCount = summary.succeeded.reduce((sum, result) => sum + Number(result.data?.imported_count || 0), 0);
    const skippedCount = summary.succeeded.reduce((sum, result) => sum + Number(result.data?.skipped_count || 0), 0);
    const metadataOnly = summary.succeeded.filter(result => Number(result.data?.imported_count || 0) === 0).length;
    const partialImports = summary.succeeded.filter(result => result.data?.upload?.extracted_payload?.preview_only).length;
    const reviewNote = summary.succeeded
        .map(result => result.data?.parser_notes)
        .find(note => note && String(note).trim());
    const extras = [];

    if (summary.succeeded.length) {
        extras.push(`${Alfred.formatNumber(importedCount, 0)} transactions imported`);
    }
    if (skippedCount) {
        extras.push(`${Alfred.formatNumber(skippedCount, 0)} duplicates skipped`);
    }
    if (metadataOnly) {
        extras.push(`${metadataOnly} retained as metadata-only upload${metadataOnly === 1 ? "" : "s"}`);
    }
    if (partialImports) {
        extras.push(`${partialImports} partial OCR import${partialImports === 1 ? "" : "s"} still deepening in background`);
    }
    if (metadataOnly && reviewNote) {
        extras.push(String(reviewNote));
    }

    return {
        ...summary,
        message: extras.length ? `${summary.message} ${extras.join(" | ")}.` : summary.message,
    };
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

function statementPreviewInfo(upload) {
    const payload = upload?.extracted_payload || {};
    const progress = payload.ocr_progress || {};
    const isPartial = Boolean(payload.preview_only || progress.is_partial);
    if (!isPartial) {
    return "";
}

function getUiConfig(path, fallback = "") {
    return Alfred.getUiConfig(path, fallback);
}
    const importedCount = Number(upload?.imported_count || payload.preview_transaction_count || 0);
    const processedPages = Number(progress.processed_pages || 0);
    const totalPages = Number(progress.total_pages || processedPages || 0);
    const parts = [];
    if (importedCount) {
        parts.push(`${importedCount} preview row${importedCount === 1 ? "" : "s"} imported`);
    } else if (Number(payload.preview_transaction_count || 0)) {
        const previewCount = Number(payload.preview_transaction_count || 0);
        parts.push(`${previewCount} OCR preview row${previewCount === 1 ? "" : "s"} detected`);
    } else {
        parts.push("partial OCR preview retained");
    }
    if (processedPages) {
        parts.push(`${processedPages}/${totalPages || processedPages} pages processed`);
    }
    return `Partial OCR import | ${parts.join(" | ")}`;
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
