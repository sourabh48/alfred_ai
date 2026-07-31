let allocationChart;
let growthChart;

document.addEventListener("DOMContentLoaded", () => {
    if (!document.getElementById("investmentRoot")) {
        return;
    }

    document.getElementById("investmentForm").addEventListener("submit", submitInvestmentForm);
    document.getElementById("uploadInvestmentPdfBtn").addEventListener("click", uploadInvestmentPdfs);
    loadInvestmentDashboard();
    Alfred.enableLiveRefresh("investments-live", loadInvestmentDashboard, { rootId: "investmentRoot" });
});

function loadInvestmentDashboard() {
    return Promise.all([
        Alfred.fetchJSON("/api/investments/summary/"),
        Alfred.fetchJSON("/api/investments/allocation/"),
        Alfred.fetchJSON("/api/investments/growth/"),
        Alfred.fetchJSON("/api/investments/import-uploads/"),
    ])
        .then(([summaryData, allocationData, growthData, importUploads]) => {
            renderInvestmentHero(summaryData);
            renderInvestmentSummary(summaryData);
            renderAllocationChart(allocationData);
            renderGrowthChart(growthData);
            renderInvestmentRecommendations(summaryData.analysis?.recommendations || [], summaryData.market_context?.suggestions || []);
            renderInvestmentGrounding(summaryData.grounding || {});
            renderInvestmentWatchlist(summaryData.watchlist || {});
            renderInvestmentPositions(summaryData.positions || []);
            renderInvestmentImports(importUploads || []);
            Alfred.clearPageAlert("investmentRoot");
        })
        .catch(error => {
            Alfred.upsertPageAlert("investmentRoot", error.message, "danger");
        });
}

function renderInvestmentHero(data) {
    const summary = data.summary || {};
    const analysis = data.analysis || {};
    const watchlistItems = data.watchlist?.items || [];
    const copyParts = [
        `${summary.positions || 0} positions`,
        `diversification ${Alfred.formatNumber(analysis.diversification_score || 0)} / 100`,
    ];

    if (watchlistItems.length) {
        copyParts.push(`${watchlistItems.length} watchlist candidates`);
    }

    document.getElementById("investmentHeroValue").textContent = Alfred.formatCurrency(summary.total_value || 0);
    document.getElementById("investmentHeroRisk").textContent = analysis.risk_level || summary.risk || "No data";
    document.getElementById("investmentHeroCopy").textContent = copyParts.join(" | ");
}

function renderInvestmentSummary(data) {
    const summary = data.summary || {};
    const analysis = data.analysis || {};
    const cards = [
        { title: "Invested", value: Alfred.formatCurrency(summary.total_invested || 0), copy: "Capital deployed so far" },
        { title: "Gain / Loss", value: Alfred.formatCurrency(summary.gain_loss || 0), copy: `${Alfred.formatNumber(summary.annual_return || 0, 2)}% weighted annual return` },
        { title: "Monthly SIP", value: Alfred.formatCurrency(summary.monthly_sip || 0), copy: "Recurring monthly contribution" },
        { title: "Risk / Diversification", value: `${analysis.risk_level || summary.risk || "No data"}`, copy: `${Alfred.formatNumber(analysis.diversification_score || 0)} diversification score` },
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

function renderInvestmentWatchlist(watchlist) {
    const modeTarget = document.getElementById("investmentWatchlistMode");
    const summaryTarget = document.getElementById("investmentWatchlistSummary");
    const cardsTarget = document.getElementById("investmentWatchlistCards");
    const algorithmTarget = document.getElementById("investmentWatchlistAlgorithm");
    const evidenceTarget = document.getElementById("investmentWatchlistEvidence");

    const regimeLabel = watchlist.regime?.label
        ? watchlist.regime.label.replaceAll("_", " ")
        : "unavailable";
    modeTarget.textContent = watchlist.available ? titleCase(regimeLabel) : "Unavailable";
    summaryTarget.textContent = watchlist.summary || "Waiting for verified market data.";

    const items = Array.isArray(watchlist.items) ? watchlist.items : [];
    if (!items.length) {
        cardsTarget.innerHTML = `<div class="empty-state">No proof-backed watchlist candidates are available right now.</div>`;
    } else {
        cardsTarget.innerHTML = items.map(item => {
            const score = clamp(item.short_horizon_score || 0, 0, 100);
            const proofChips = (item.proof || []).slice(0, 3).map(proof => `
                <a class="chip-neutral investment-proof-chip" href="${Alfred.escapeHtml(proof.source_url || "#")}" target="_blank" rel="noopener">
                    ${Alfred.escapeHtml(proof.label || "Proof")}
                </a>
            `).join("");
            const reasons = (item.why_it_ranked || []).slice(0, 3).map(reason => `
                <li>${Alfred.escapeHtml(reason)}</li>
            `).join("");
            return `
                <article class="metric-card investment-watch-card">
                    <div class="d-flex justify-content-between align-items-start gap-3 mb-2">
                        <div>
                            <p class="metric-kicker mb-1">${Alfred.escapeHtml(item.family_label || item.family || "Fund")}</p>
                            <h3 class="investment-watch-title mb-1">${Alfred.escapeHtml(item.scheme_name || "Mutual fund")}</h3>
                            <p class="metric-caption mb-0">${Alfred.escapeHtml(item.fund_house || "Fund house unavailable")}</p>
                        </div>
                        <div class="investment-watch-score">
                            <span>${Alfred.formatNumber(score, 1)} / 100</span>
                            <small>${Alfred.escapeHtml(item.outlook_label || "Watch")}</small>
                        </div>
                    </div>
                    <div class="investment-score-track mb-3">
                        <div class="investment-score-fill" style="width: ${score}%;"></div>
                    </div>
                    <div class="investment-watch-metrics">
                        ${renderWatchMetric("10D", formatSignedPercent(item.return_10d_pct))}
                        ${renderWatchMetric("30D", formatSignedPercent(item.return_30d_pct))}
                        ${renderWatchMetric("Volatility", `${Alfred.formatNumber(item.realized_volatility_pct || 0, 2)}%`)}
                        ${renderWatchMetric("Drawdown", formatSignedPercent(item.max_drawdown_pct))}
                    </div>
                    <ul class="investment-watch-notes mt-3">${reasons}</ul>
                    <div class="chip-row mt-3">${proofChips}</div>
                    <p class="metric-caption mt-3 mb-0">${Alfred.escapeHtml(item.caution || "")}</p>
                </article>
            `;
        }).join("");
    }

    const algorithm = watchlist.algorithm || {};
    const factors = Array.isArray(algorithm.factors) ? algorithm.factors : [];
    algorithmTarget.innerHTML = `
        <div class="mini-card investment-algorithm-card">
            <div class="fw-semibold mb-2">${Alfred.escapeHtml(algorithm.name || "Transparent watchlist")}</div>
            <div class="muted small mb-2">Window: ${Alfred.formatNumber(algorithm.window_days || 0, 0)} days</div>
            <ul class="investment-watch-notes mb-3">
                ${factors.map(factor => `<li>${Alfred.escapeHtml(factor.label)} <span class="muted">(${Alfred.escapeHtml(factor.effect || "neutral")})</span></li>`).join("")}
            </ul>
            <p class="metric-caption mb-0">${Alfred.escapeHtml(algorithm.guardrail || "")}</p>
        </div>
    `;

    const evidenceItems = Array.isArray(watchlist.evidence) ? watchlist.evidence : [];
    evidenceTarget.innerHTML = evidenceItems.length
        ? evidenceItems.map(item => `
            <li class="insight-item">
                <strong>${Alfred.escapeHtml(item.source_name || item.title || "Evidence")}</strong>:
                ${Alfred.escapeHtml(item.summary || "")}
                ${item.source_url ? ` <a href="${item.source_url}" target="_blank" rel="noopener">Proof</a>` : ""}
            </li>
        `).join("")
        : `<li class="insight-item">No external proof items are available right now.</li>`;
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
                <div class="muted small">${Alfred.escapeHtml(item.asset_type.replaceAll("_", " "))} | ${Alfred.escapeHtml(item.institution || "Unspecified institution")}</div>
            </td>
            <td class="text-end">${Alfred.formatCurrency(item.invested_amount)}</td>
            <td class="text-end">${Alfred.formatCurrency(item.current_value)}</td>
            <td class="text-end ${Number(item.gain_loss) < 0 ? "text-danger" : "text-success"}">${Alfred.formatCurrency(item.gain_loss)}</td>
            <td class="text-end">${Alfred.formatCurrency(item.monthly_sip)}</td>
            <td>${Alfred.escapeHtml(item.risk_level || "Not set")}</td>
        </tr>
    `).join("");
}

function renderInvestmentImports(items) {
    const target = document.getElementById("investmentImportList");
    if (!target) {
        return;
    }
    if (!Array.isArray(items) || !items.length) {
        target.innerHTML = `<div class="empty-state">No portfolio imports tracked yet.</div>`;
        return;
    }

    target.innerHTML = items.slice(0, 8).map(item => {
        const linkedCount = Array.isArray(item.linked_investments) ? item.linked_investments.length : 0;
        const parserLabel = item.parser_status_label || item.parser_status || "Unknown";
        return `
            <div class="data-row align-items-start">
                <div class="data-label">
                    <div class="fw-semibold">${Alfred.escapeHtml(item.file_name || "Portfolio PDF")}</div>
                    <div class="muted small">${Alfred.formatDateTime(item.created_at)}</div>
                </div>
                <div class="data-value">
                    <div class="fw-semibold">${Alfred.escapeHtml(item.broker_name || "Portfolio import")}</div>
                    <div class="muted small">${Alfred.escapeHtml(parserLabel)} | ${(Number(item.parse_confidence || 0) * 100).toFixed(0)}% confidence</div>
                    <div class="muted small">${Alfred.escapeHtml(item.summary || `${linkedCount} holdings linked`)}</div>
                </div>
            </div>
        `;
    }).join("");
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

async function uploadInvestmentPdfs() {
    const input = document.getElementById("investmentPdfFiles");
    const button = document.getElementById("uploadInvestmentPdfBtn");
    const files = Array.from(input?.files || []);
    if (!files.length) {
        showInvestmentImportStatus("Choose at least one portfolio PDF first.", "warning");
        return;
    }

    Alfred.lockLiveRefresh(document.getElementById("investmentRoot"), 8000);
    Alfred.setDisabledIfChanged(button, true);
    Alfred.showUploadProgress("investmentImportStatus", {
        phase: "preparing",
        current: 1,
        total: files.length,
        percent: 0,
    });

    try {
        const results = await Alfred.uploadFilesSequentially(
            files,
            (file, helpers) => {
                const payload = new FormData();
                payload.append("file", file);
                return Alfred.uploadJSON("/api/investments/import-pdf/", {
                    body: payload,
                    onUploadState: state => helpers.reportProgress(state),
                });
            },
            {
                onProgress: state => Alfred.showUploadProgress("investmentImportStatus", state),
            },
        );
        const summary = Alfred.summarizeUploadBatch(results, {
            itemLabel: "portfolio document",
            successVerb: "processed",
        });
        const successfulMessages = summary.succeeded
            .map(item => item.data?.message)
            .filter(Boolean);
        showInvestmentImportStatus(successfulMessages[0] || summary.message, summary.tone);
        if (input) {
            input.value = "";
        }
        loadInvestmentDashboard();
    } catch (error) {
        showInvestmentImportStatus(error.message || "Could not upload the portfolio PDFs.", "danger");
    } finally {
        Alfred.setDisabledIfChanged(button, false);
    }
}

function showInvestmentImportStatus(message, tone) {
    const target = document.getElementById("investmentImportStatus");
    if (!target) {
        return;
    }
    target.className = `alert alert-${tone} mb-0`;
    target.textContent = message;
}

function renderWatchMetric(label, value) {
    return `
        <div class="mini-card investment-watch-metric">
            <span>${Alfred.escapeHtml(label)}</span>
            <strong>${Alfred.escapeHtml(value)}</strong>
        </div>
    `;
}

function clamp(value, min, max) {
    return Math.max(min, Math.min(max, Number(value || 0)));
}

function formatSignedPercent(value) {
    const number = Number(value || 0);
    return `${number >= 0 ? "+" : ""}${Alfred.formatNumber(number, 2)}%`;
}

function titleCase(value) {
    return String(value || "")
        .split(" ")
        .filter(Boolean)
        .map(token => token.charAt(0).toUpperCase() + token.slice(1))
        .join(" ");
}
