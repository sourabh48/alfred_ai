let allocationChart;
let growthChart;

document.addEventListener("DOMContentLoaded", () => {
    if (!document.getElementById("investmentRoot")) {
        return;
    }

    document.getElementById("investmentForm").addEventListener("submit", submitInvestmentForm);
    document.getElementById("uploadInvestmentPdfBtn").addEventListener("click", uploadInvestmentPdfs);
    loadInvestmentDashboard();
    initInvestmentReviewAlerts();
    initResearchJournal();
    initLookThrough();
    Alfred.enableLiveRefresh("investments-live", loadInvestmentDashboard, { rootId: "investmentRoot" });
});

function initInvestmentReviewAlerts() {
    const form=document.getElementById('investmentReviewForm');
    if (!form) return;
    const enabled=document.getElementById('investmentReviewEnabled'), days=document.getElementById('investmentReviewDays');
    const check=document.getElementById('investmentReviewCheck'), status=document.getElementById('investmentReviewStatus');
    const list=document.getElementById('investmentReviewItems');
    let policy=null, pending=false, active=true;
    function controls() {
        form.querySelector('button[type="submit"]').disabled=pending || !policy;
        check.disabled=pending || !policy?.enabled;
        enabled.disabled=pending || !policy; days.disabled=pending || !policy;
        list.querySelectorAll('button').forEach(button=>{button.disabled=pending;});
        form.setAttribute('aria-busy',String(pending));
    }
    function render(data) {
        policy=data; enabled.checked=data.enabled; days.value=String(data.days); list.replaceChildren();
        status.textContent=`${data.enabled ? 'Reminders on' : 'Reminders off'} · ${data.items.length} reminders · ${data.checked_at ? `last checked ${new Date(data.checked_at).toLocaleString()}` : 'not checked'}.`;
        if (data.unassessed_records) status.textContent+=` ${data.unassessed_records} future-dated records could not be assessed.`;
        for (const item of data.items) {
            const row=document.createElement('li'); row.className='mb-3';
            const text=document.createElement('p'); text.className='mb-1';
            text.textContent=`${item.name} · ${item.status} · record last edited ${new Date(item.source_updated_at).toLocaleString()}. This does not verify its price.`;
            const link=document.createElement('a'); link.href=item.url; link.textContent='Review owned record'; row.append(text,link);
            if (['unread','read'].includes(item.status)) {
                for (const [action,label] of [['read','Mark read'],['dismiss','Dismiss']]) {
                    if (action==='read' && item.status==='read') continue;
                    const button=document.createElement('button'); button.type='button'; button.className='btn btn-outline-secondary btn-sm ms-2';
                    button.textContent=label; button.addEventListener('click',()=>perform({action,id:item.id})); row.append(button);
                    button.setAttribute('aria-label',`${label}: ${item.name}`);
                }
            }
            list.append(row);
        }
    }
    async function perform(payload) {
        if (pending || !active) return;
        pending=true; controls();
        try {
            const data=await Alfred.fetchJSON('/api/investments/review-alerts/',payload ? {method:'POST',body:JSON.stringify({...payload,revision:policy.revision})} : {});
            if (active) render(data);
        } catch (error) {
            if (!active) return;
            status.textContent=`${error.message} Reload reminders before retrying; your form choice is preserved.`;
            if ([401,403].includes(error.status)) { list.replaceChildren(); policy=null; enabled.checked=false; }
        } finally { pending=false; if (active) controls(); }
    }
    form.addEventListener('submit',event=>{event.preventDefault();perform({action:'configure',enabled:enabled.checked,days:Number(days.value),consent:enabled.checked});});
    check.addEventListener('click',()=>perform({action:'evaluate'}));
    window.addEventListener('pagehide',()=>{active=false; policy=null; enabled.checked=false; list.replaceChildren(); controls();});
    window.addEventListener('pageshow',event=>{if(event.persisted){active=true; perform();}});
    perform();
}

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
            fillPacketHoldings(summaryData.positions || []);
            fillLookThroughHoldings(summaryData.positions || []);
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
    const otherPositions = (summary.other_currencies || []).reduce((count, group) => count + group.positions, 0);
    if (otherPositions) {
        copyParts.push(`${otherPositions} in other currencies, not in this total`);
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
        { title: "Unrealized Gain / Loss", value: Alfred.formatCurrency(summary.gain_loss || 0), copy: "Latest recorded value minus amount invested; excludes withdrawals and realized gains" },
        { title: "Monthly SIP", value: Alfred.formatCurrency(summary.monthly_sip || 0), copy: "Recurring monthly contribution" },
        { title: "Risk / Diversification", value: `${analysis.risk_level || summary.risk || "No data"}`, copy: `${Alfred.formatNumber(analysis.diversification_score || 0)} diversification score` },
        ...(summary.other_currencies || []).map(group => ({
            title: `${Alfred.escapeHtml(group.currency)} positions`,
            value: Alfred.formatCurrency(group.total_value, group.currency),
            copy: `${group.positions} position(s), invested ${Alfred.formatCurrency(group.total_invested, group.currency)}. Kept out of rupee totals.${group.approximate ? ` ${Alfred.formatApproximate(group.approximate, "total_value")} in your currency.` : ""} ${Alfred.approximateNote(summary.display_currency)}`,
        })),
    ];
    const display = summary.display_currency || {};
    if (display.totals?.total_value != null) {
        cards.push({ title: `All holdings in ${Alfred.escapeHtml(display.currency)}`, value: Alfred.formatApproximate({ currency: display.currency, total_value: display.totals.total_value }, "total_value"),
            copy: Alfred.approximateNote(display) });
    }

    Alfred.setHTML(document.getElementById("investmentSummaryCards"), cards.map(card => `
        <article class="metric-card">
            <p class="metric-kicker">${card.title}</p>
            <h2 class="metric-value">${card.value}</h2>
            <p class="metric-caption">${card.copy}</p>
        </article>
    `).join(""));
}

function renderAllocationChart(data) {
    const canvas = document.getElementById("allocationChart");
    allocationChart = Alfred.renderChart(allocationChart, canvas, {
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
    const status = document.getElementById("investmentGrowthStatus");
    const unavailable = data.available === false;
    status.textContent = unavailable ? data.unavailable_reason : "";
    status.hidden = !unavailable;
    canvas.hidden = unavailable;
    if (unavailable) {
        growthChart?.destroy();
        growthChart = null;
        return;
    }

    growthChart = Alfred.renderChart(growthChart, canvas, {
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
        Alfred.setHTML(target, `<li class="insight-item">Add holdings to unlock portfolio guidance.</li>`);
        return;
    }

    Alfred.setHTML(target, combined.map(item => `<li class="insight-item">${Alfred.escapeHtml(item)}</li>`).join(""));
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
    Alfred.setHTML(cardsTarget, cards.map(card => `
        <article class="metric-card metric-card--compact">
            <p class="metric-kicker">${card.title}</p>
            <h3 class="metric-value" style="font-size:1.35rem;">${card.value}</h3>
            <p class="metric-caption">${Alfred.escapeHtml(card.copy)}</p>
        </article>
    `).join(""));

    const notes = grounding.notes || [];
    const evidence = grounding.evidence || [];
    const evidenceItems = [
        ...notes.map(note => ({ note })),
        ...evidence.map(item => ({ proof: item })),
    ];
    Alfred.setHTML(evidenceTarget, evidenceItems.map(item => {
        if (item.note) {
            return `<li class="insight-item">${Alfred.escapeHtml(item.note)}</li>`;
        }
        const proof = item.proof || {};
        return `<li class="insight-item"><strong>${Alfred.escapeHtml(proof.source_name || proof.title || "Evidence")}</strong>: ${Alfred.escapeHtml(proof.summary || "")}${proof.source_url ? ` <a href="${Alfred.safeHref(proof.source_url)}" target="_blank" rel="noopener">Proof</a>` : ""}</li>`;
    }).join(""));
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
        Alfred.setHTML(cardsTarget, `<div class="empty-state">No proof-backed watchlist candidates are available right now.</div>`);
    } else {
        Alfred.setHTML(cardsTarget, items.map(item => {
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
                            <p class="metric-caption mb-0">Quoted NAV: ${Alfred.escapeHtml(item.nav_source_value ?? String(item.nav ?? "unavailable"))} · Source date: ${Alfred.escapeHtml(item.nav_date || "unknown")}</p>
                            <p class="metric-caption mb-0">${Alfred.escapeHtml(String(item.observation_count ?? "Unknown"))} observations · ${Alfred.escapeHtml(String(item.history_days ?? "Unknown"))}-day observed window. No currency conversion or holding revaluation.</p>
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
        }).join(""));
    }

    const algorithm = watchlist.algorithm || {};
    const factors = Array.isArray(algorithm.factors) ? algorithm.factors : [];
    Alfred.setHTML(algorithmTarget, `
        <div class="mini-card investment-algorithm-card">
            <div class="fw-semibold mb-2">${Alfred.escapeHtml(algorithm.name || "Transparent watchlist")}</div>
            <div class="muted small mb-2">Window: ${Alfred.formatNumber(algorithm.window_days || 0, 0)} days</div>
            <ul class="investment-watch-notes mb-3">
                ${factors.map(factor => `<li>${Alfred.escapeHtml(factor.label)} <span class="muted">(${Alfred.escapeHtml(factor.effect || "neutral")})</span></li>`).join("")}
            </ul>
            <p class="metric-caption mb-0">${Alfred.escapeHtml(algorithm.guardrail || "")}</p>
        </div>
    `);

    const evidenceItems = Array.isArray(watchlist.evidence) ? watchlist.evidence : [];
    Alfred.setHTML(evidenceTarget, evidenceItems.length
        ? evidenceItems.map(item => `
            <li class="insight-item">
                <strong>${Alfred.escapeHtml(item.source_name || item.title || "Evidence")}</strong>:
                ${Alfred.escapeHtml(item.summary || "")}
                ${item.source_url ? ` <a href="${Alfred.safeHref(item.source_url)}" target="_blank" rel="noopener">Proof</a>` : ""}
            </li>
        `).join("")
        : `<li class="insight-item">No external proof items are available right now.</li>`);
}

function renderInvestmentPositions(items) {
    const body = document.getElementById("investmentPositionsBody");
    if (!items.length) {
        Alfred.setHTML(body, `<tr><td colspan="6" class="text-center muted py-4">No registered positions yet.</td></tr>`);
        return;
    }

    Alfred.setHTML(body, items.map(item => `
        <tr>
            <td>
                <div class="fw-semibold">${Alfred.escapeHtml(item.asset_name)}</div>
                <div class="muted small">${Alfred.escapeHtml(item.asset_type.replaceAll("_", " "))} | ${Alfred.escapeHtml(item.institution || "Unspecified institution")}</div>
                <div class="muted small">Account: ${Alfred.escapeHtml(item.account_number ? `…${item.account_number.slice(-4)}` : "not recorded")}</div>
                <div class="muted small" data-position-currency>Currency: ${Alfred.escapeHtml(item.currency || "not recorded, shown in ₹")}</div>
            </td>
            <td class="text-end">${Alfred.formatCurrency(item.invested_amount, item.currency)}</td>
            <td class="text-end">${Alfred.formatCurrency(item.current_value, item.currency)}</td>
            <td class="text-end ${Number(item.gain_loss) < 0 ? "text-danger" : "text-success"}">${Alfred.formatCurrency(item.gain_loss, item.currency)}</td>
            <td class="text-end">${Alfred.formatCurrency(item.monthly_sip, item.currency)}</td>
            <td>${Alfred.escapeHtml(item.risk_level || "Not set")}</td>
        </tr>
    `).join(""));
}

function renderInvestmentImports(items) {
    const target = document.getElementById("investmentImportList");
    if (!target) {
        return;
    }
    if (!Array.isArray(items) || !items.length) {
        Alfred.setHTML(target, `<div class="empty-state">No portfolio imports tracked yet.</div>`);
        return;
    }

    Alfred.setHTML(target, items.slice(0, 8).map(item => {
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
                    ${item.review_state ? `<a class="btn btn-sm btn-outline-primary mt-2" href="/investments/import-uploads/${Number(item.id)}/review/">${item.review_state === "confirmed" ? "View confirmed review" : "Review extracted holdings"}</a>` : ""}
                    ${item.extracted_payload?.layout_review ? `<div class="muted small">Source extraction: ${Alfred.escapeHtml(item.extracted_payload.layout_review.reason || "Review the source table.")}${item.extracted_payload.review_queue_resolved ? " Owner corrections applied; source extraction is unchanged." : ""}</div>` : ""}
                </div>
            </div>
        `;
    }).join(""));
}

function submitInvestmentForm(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const payload = Object.fromEntries(new FormData(form).entries());
    ["invested_amount", "monthly_sip", "current_value", "annual_return_rate"].forEach(key => {
        payload[key] = Number(payload[key] || 0);
    });
    if (!payload.units) delete payload.units;  // units are a decimal string; empty means not recorded

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

// Fund picker: the name is looked up in AMFI's list; picking one stores its scheme code for daily revaluation.
let fundSearchTimer = null, fundMatches = [];
function setupFundPicker() {
    const input = document.getElementById("investmentFund"), list = document.getElementById("investmentFundList"), code = document.getElementById("investmentFundCode");
    if (!input) return;
    input.addEventListener("input", () => {
        const picked = fundMatches.find(fund => fund.name === input.value);
        code.value = picked ? picked.scheme_code : "";
        if (picked) {
            const name = document.getElementById("investmentName") || document.querySelector('[name="asset_name"]');
            if (name && !name.value) name.value = picked.name.slice(0, 120);
            return;
        }
        clearTimeout(fundSearchTimer);
        if (input.value.trim().length < 3) return;
        fundSearchTimer = setTimeout(async () => {
            try {
                fundMatches = (await Alfred.fetchJSON(`/api/investments/funds/?q=${encodeURIComponent(input.value.trim())}`)).funds;
                list.replaceChildren(...fundMatches.map(fund => Object.assign(document.createElement("option"), {value: fund.name, label: `NAV ₹${fund.nav} on ${fund.nav_date}`})));
            } catch (error) { fundMatches = []; }
        }, 300);
    });
}
document.addEventListener("DOMContentLoaded", setupFundPicker);

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

const RESEARCH_RATING = { buy: "Buy", overweight: "Own more", hold: "Hold", underweight: "Own less", sell: "Sell" };
const researchToday = () => new Date().toLocaleDateString("en-CA");
const researchInThreeMonths = () => { const d = new Date(); d.setMonth(d.getMonth() + 3); return d.toLocaleDateString("en-CA"); };

function resetResearchDates(form) {
    form.elements.decided_on.value = researchToday();
    form.elements.review_on.value = researchInThreeMonths();
}

function initResearchJournal() {
    const form = document.getElementById("researchDecisionForm");
    if (!form) return;
    resetResearchDates(form);
    form.addEventListener("submit", submitResearchDecision);
    form.elements.instrument.addEventListener("change", () => loadResearchLessons(form.elements.instrument.value));
    loadResearchDecisions();
    document.getElementById("researchPacketForm")?.addEventListener("submit", loadResearchPacket);
}

function fillPacketHoldings(items) {
    const select = document.getElementById("researchPacketHolding");
    if (!select) return;
    const chosen = select.value;
    select.replaceChildren(new Option("None", ""), ...items.map(item => new Option(item.asset_name, String(item.id))));
    select.value = items.some(item => String(item.id) === chosen) ? chosen : "";
}

async function loadResearchPacket(event) {
    event.preventDefault();
    const form = event.currentTarget, target = document.getElementById("researchPacket");
    const query = new URLSearchParams({ symbol: form.elements.symbol.value.trim() });
    if (form.elements.holding.value) query.set("holding", form.elements.holding.value);
    target.innerHTML = `<p class="muted small mb-0">Fetching dated public data…</p>`;
    try {
        const packet = await Alfred.fetchJSON(`/api/investments/research/packet/?${query}`);
        target.innerHTML = researchPacketHtml(packet);
        prefillResearchView(packet);
        document.getElementById("researchChallengeButton").addEventListener("click", () =>
            loadResearchChallenge(Object.fromEntries(query), document.getElementById("researchChallengeRole").value));
        document.getElementById("researchPersonalButton").addEventListener("click", () => loadResearchPersonalChallenge(Object.fromEntries(query)));
    } catch (error) {
        const e = Alfred.escapeHtml, matches = error.code === "choose_symbol" ? error.payload?.matches || [] : [];
        target.innerHTML = `<div class="alert alert-warning mb-0" role="alert">${e(error.message || "The packet could not be built.")}
            ${matches.length ? `<div class="d-flex flex-wrap gap-2 mt-2" id="researchSymbolMatches">${matches.map(m =>
                `<button type="button" class="btn btn-outline-secondary btn-sm" data-symbol="${e(m.symbol)}">${e(m.name || m.symbol)} · ${e(m.exchange)} (${e(m.symbol)})</button>`).join("")}</div>` : ""}</div>`;
        target.querySelectorAll("[data-symbol]").forEach(button => button.addEventListener("click", () => {
            form.elements.symbol.value = button.dataset.symbol;
            form.requestSubmit();
        }));
    }
}

function researchPacketHtml(p) {
    const e = Alfred.escapeHtml;
    const points = (title, items, id) => `<div class="col-md-6" id="${id}"><p class="fw-semibold mb-1">${title}</p>${items.length
        ? `<ul class="mb-0">${items.map(item => `<li>${e(item.point)} <span class="muted small">(${e(item.as_of)})</span></li>`).join("")}</ul>`
        : `<p class="muted small mb-0">None found.</p>`}</div>`;
    const list = items => `<ul class="mb-0">${items.map(item => `<li>${e(item)}</li>`).join("")}</ul>`;
    const v = p.valuation || {};
    const valuation = v.status === "estimated"
        ? `Price-to-earnings ${e(String(v.price_to_earnings))} (earnings yield ${e(String(v.earnings_yield_pct))}%) as of ${e(v.as_of)}. ${e(v.basis)} ${e(v.uncertainty)}`
        : `Unavailable: ${e(v.reason || "")}`;
    const b = p.beginner || {};
    return `<div class="mini-card" id="researchPacketResult">
        ${b.label ? `<div class="border-bottom pb-2 mb-2" id="researchBeginner">
            <p class="fw-semibold mb-1">In plain words: <span class="badge text-bg-${{ positive: "success", caution: "danger", mixed: "warning" }[b.lean] || "secondary"}">${e(b.label)}</span></p>
            <p class="mb-1">${e(b.headline)} (${e(String(b.good_signs))} good, ${e(String(b.warning_signs))} warning)</p>
            ${list(b.steps || [])}<p class="muted small mt-1 mb-0">${e(b.note)}</p></div>` : ""}
        <p class="metric-kicker mb-1">${e(p.symbol)} · statements to ${e(p.latest_period_end || "unknown")} · retrieved ${e((p.retrieved_at || "").slice(0, 10))}
            · <a href="${Alfred.safeHref(p.source_url)}" target="_blank" rel="noopener">Source</a></p>
        <div class="row g-3">${points("Good signs", p.bullish || [], "researchPacketBull")}${points("Warning signs", p.bearish || [], "researchPacketBear")}</div>
        <p class="mt-3 mb-1"><strong>Is the price high?</strong> <span id="researchPacketValuation">${valuation}</span></p>
        <p class="mb-1"><strong>Your money in it:</strong> ${e(p.portfolio?.detail || "")}</p>
        ${(p.thesis_changes || []).length ? `<p class="fw-semibold mt-2 mb-1">What to watch for</p>${list(p.thesis_changes)}` : ""}
        <p class="fw-semibold mt-2 mb-1">Not checked here</p>${list(p.missing_evidence || [])}
        <p class="fw-semibold mt-2 mb-1">What you can do</p>${list(p.options || [])}
        <p class="muted small mt-2 mb-0">${(p.limits || []).map(e).join(" ")}</p>
        <div class="d-flex flex-wrap gap-2 align-items-end mt-3">
            <div><label for="researchChallengeRole" class="form-label small mb-1">Second opinion from</label>
            <select id="researchChallengeRole" class="form-select form-select-sm">
                <option value="team" selected>The whole research team: for, against and risks</option>
                <option value="sceptic">Sceptic: reasons to doubt</option>
                <option value="advocate">Advocate: the case for</option>
                <option value="risk_manager">Risk manager: what could go wrong</option>
            </select></div>
            <button type="button" class="btn btn-outline-secondary btn-sm" id="researchChallengeButton">Ask the research team (local AI)</button>
        </div>
        <div id="researchChallenge" class="mt-2" aria-live="polite"></div>
        <div class="border-top mt-3 pt-2" id="researchPersonal">
            <p class="fw-semibold mb-1">Challenge your own view</p>
            <p class="muted small mb-1">The second opinion above sees only public data. This check also reads your saved view of this stock and your holding's share, on your local AI only.</p>
            <div class="form-check"><input class="form-check-input" type="checkbox" id="researchPersonalConsent">
                <label class="form-check-label small" for="researchPersonalConsent">Use my holding's share and my saved views of this stock for this check. They stay on this computer.</label></div>
            <button type="button" class="btn btn-outline-secondary btn-sm mt-2" id="researchPersonalButton">Challenge my own view (local AI)</button>
            <div id="researchPersonalResult" class="mt-2" aria-live="polite"></div>
        </div>
    </div>`;
}

async function loadResearchPersonalChallenge(params) {
    const target = document.getElementById("researchPersonalResult"), button = document.getElementById("researchPersonalButton");
    const e = Alfred.escapeHtml;
    button.disabled = true;
    target.innerHTML = `<p class="muted small mb-0">Your local AI is checking your view; on this PC it can take up to two minutes…</p>`;
    try {
        const body = { ...params, include_personal: document.getElementById("researchPersonalConsent").checked };
        const c = await Alfred.fetchJSON("/api/investments/research/packet/personal-challenge/", { method: "POST", body: JSON.stringify(body) });
        if (c.status !== "challenged") { target.innerHTML = `<p class="muted small mb-0">${e(c.detail || "")}</p>`; return; }
        target.innerHTML = `<div id="researchPersonalChallenge"><p class="small mb-1">Used: ${c.context_used.map(e).join("; ")}.</p>
            ${c.objections.length ? `<ul class="mb-2">${c.objections.map(o => `<li><span class="muted">${e(o.point)}</span> — ${e(o.objection)}</li>`).join("")}</ul>` : ""}
            ${c.overlooked.length ? `<p class="fw-semibold mb-1">Personal risks to check</p><ul class="mb-2">${c.overlooked.map(item => `<li>${e(item)}</li>`).join("")}</ul>` : ""}
            <p class="muted small mb-0">${c.dropped ? `${e(String(c.dropped))} reply item(s) were dropped. ` : ""}${c.limits.map(e).join(" ")}</p></div>`;
    } catch (error) {
        target.innerHTML = `<div class="alert alert-warning mb-0" role="alert">${e(error.message || "The check failed.")}</div>`;
    } finally {
        button.disabled = false;
    }
}

function prefillResearchView(packet) {
    const form = document.getElementById("researchDecisionForm");
    if (!form || form.elements.instrument.value.trim()) return;
    form.elements.instrument.value = packet.symbol;
    const price = packet.metrics?.price;
    if (price && !form.elements.entry_price.value) form.elements.entry_price.value = price.last_close;
    if ([...form.elements.currency.options].some(option => option.value && option.value === packet.price_currency)) form.elements.currency.value = packet.price_currency;
    loadResearchLessons(packet.symbol);
}

// TradingAgents-style team: the advocate (bull), the sceptic (bear) and the risk manager each review the public packet in turn.
async function loadResearchChallenge(params, choice) {
    const target = document.getElementById("researchChallenge"), button = document.getElementById("researchChallengeButton");
    const e = Alfred.escapeHtml, roles = choice === "team" ? ["advocate", "sceptic", "risk_manager"] : [choice];
    const done = [];
    const render = waiting => `<div id="researchChallengeResult">${done.join("")}</div>${waiting
        ? `<p class="muted small mb-0">Your local AI is reviewing this packet (${done.length + 1} of ${roles.length}); on this PC each view can take a few minutes…</p>` : ""}`;
    button.disabled = true;
    target.innerHTML = render(true);
    try {
        for (const role of roles) {
            const c = await Alfred.fetchJSON("/api/investments/research/packet/challenge/", { method: "POST", body: JSON.stringify({ ...params, role }) });
            done.push(c.status !== "challenged" ? `<p class="muted small mb-2">${e(c.detail || "")}</p>` : `<div class="mb-2" data-research-role="${e(role)}">
                <p class="fw-semibold mb-1">${e(c.role_label)} (${e(c.model)})</p>
                ${c.objections.length ? `<ul class="mb-1">${c.objections.map(o => `<li><span class="muted">${e(o.point)}</span> — ${e(o.objection)}</li>`).join("")}</ul>` : ""}
                ${c.overlooked.length ? `<p class="small fw-semibold mb-1">Not covered by the packet</p><ul class="mb-1">${c.overlooked.map(item => `<li>${e(item)}</li>`).join("")}</ul>` : ""}
                <p class="muted small mb-0">${c.dropped ? `${e(String(c.dropped))} reply item(s) were dropped for citing no packet point or stating a number. ` : ""}${c.limits.map(e).join(" ")}</p></div>`);
            target.innerHTML = render(done.length < roles.length);
            if (c.status !== "challenged") break;
        }
    } catch (error) {
        target.innerHTML = `${render(false)}<div class="alert alert-warning mb-0" role="alert">${e(error.message || "The challenge failed.")}</div>`;
    } finally {
        button.disabled = false;
    }
}

function researchPercent(value) {
    return value == null ? "unavailable" : `${Number(value) > 0 ? "+" : ""}${value}%`;
}

function researchOutcomeText(item) {
    const o = item.outcome || {};
    if (o.status !== "settled") return `Waiting until ${o.review_on}, then enter the price to see if you were right.`;
    const versus = o.alpha_percent != null
        ? ` ${item.benchmark} moved ${researchPercent(o.benchmark_return_percent)}, so you did ${researchPercent(o.alpha_percent)} against the market.`
        : "";
    const verdict = { supported: "You were right.", not_supported: "You were wrong this time.", not_judged: "Hold has no direction to judge." }[o.direction] || "";
    return `Checked ${item.settled_on}: the price moved ${researchPercent(o.return_percent)}.${versus} ${verdict}`;
}

function loadResearchLessons(instrument) {
    const target = document.getElementById("researchLessons");
    if (!instrument.trim()) { target.replaceChildren(); return; }
    Alfred.fetchJSON(`/api/investments/research/lessons/?instrument=${encodeURIComponent(instrument.trim())}`).then(data => {
        const row = item => `<li><strong>${Alfred.escapeHtml(item.instrument)}</strong> · ${Alfred.escapeHtml(RESEARCH_RATING[item.rating] || item.rating)} on ${Alfred.escapeHtml(item.decided_on)}: ${Alfred.escapeHtml(item.lesson)}</li>`;
        const parts = [];
        if (data.same_instrument.length) parts.push(`<p class="mb-1 fw-semibold">What you learned about this one before</p><ul class="mb-2">${data.same_instrument.map(row).join("")}</ul>`);
        if (data.other_instruments.length) parts.push(`<p class="mb-1 fw-semibold">Lessons from your other views</p><ul class="mb-0">${data.other_instruments.map(row).join("")}</ul>`);
        target.innerHTML = parts.length ? `<div class="mini-card" id="researchLessonsPanel">${parts.join("")}</div>` : "";
    }).catch(() => target.replaceChildren());
}

function researchDecisionCard(item, today) {
    const canSettle = item.outcome?.status === "pending" && item.review_on <= today;
    const settled = item.outcome?.status === "settled";
    const lessonField = `<div class="flex-grow-1"><label class="form-label small mb-1" for="researchLesson${item.id}">What did you learn?</label>
        <input class="form-control form-control-sm" id="researchLesson${item.id}" maxlength="2000" value="${Alfred.escapeHtml(item.lesson || "")}"></div>`;
    const settle = canSettle ? `
        <div class="d-flex flex-wrap gap-2 align-items-end mt-2">
            <div><label class="form-label small mb-1" for="researchExit${item.id}">Price now</label>
                <input class="form-control form-control-sm" id="researchExit${item.id}" type="number" min="0.0001" step="0.0001"></div>
            ${item.benchmark_entry != null ? `<div><label class="form-label small mb-1" for="researchBenchExit${item.id}">${Alfred.escapeHtml(item.benchmark)} level now</label>
                <input class="form-control form-control-sm" id="researchBenchExit${item.id}" type="number" min="0.0001" step="0.0001"></div>` : ""}
            ${lessonField}
            <button type="button" class="btn btn-outline-primary btn-sm" data-research-settle="${item.id}">See if I was right</button>
        </div>` : settled ? `
        <div class="d-flex flex-wrap gap-2 align-items-end mt-2">
            ${lessonField}
            <button type="button" class="btn btn-outline-secondary btn-sm" data-research-lesson="${item.id}">Save lesson</button>
        </div>` : "";
    return `
        <div class="mini-card" data-research-id="${item.id}">
            <div class="d-flex justify-content-between flex-wrap gap-2">
                <strong>${Alfred.escapeHtml(item.instrument)} · ${Alfred.escapeHtml(RESEARCH_RATING[item.rating] || item.rating)}</strong>
                <span class="muted small">${Alfred.escapeHtml(item.decided_on)} at ${Alfred.escapeHtml(item.entry_price)}${item.currency ? ` ${Alfred.escapeHtml(item.currency)}` : ""}</span>
            </div>
            <p class="small mb-1">${Alfred.escapeHtml(item.thesis)}</p>
            <p class="small mb-1" id="researchOutcome${item.id}">${Alfred.escapeHtml(researchOutcomeText(item))}</p>
            ${settle}
            <button type="button" class="btn btn-link btn-sm text-danger px-0" data-research-delete="${item.id}">Delete</button>
        </div>`;
}

function researchHistoryCard(row) {
    const e = Alfred.escapeHtml, rating = value => e(RESEARCH_RATING[value] || value);
    const current = row.versions[0];
    const state = {
        review_due: `Your view is past its check date (${e(current.review_on)}). Check it below or save a new view.`,
        current: `Next check on ${e(current.review_on)}.`,
        checked: "Your latest view has been checked.",
    }[row.freshness];
    const version = item => `<li class="mb-2"><strong>Version ${item.version}, ${e(item.decided_on)}: ${rating(item.rating)}</strong>${
        item.previous_rating && item.previous_rating !== item.rating ? ` (was ${rating(item.previous_rating)})` : ""}
        ${item.replaced_on ? `<span class="muted">· replaced on ${e(item.replaced_on)}${item.replaced_unchecked ? ", before you checked it" : ""}</span>` : `<span class="muted">· current</span>`}
        <div>${e(item.thesis)}</div></li>`;
    return `<div class="mini-card" data-research-history="${e(row.key)}">
        <div class="d-flex justify-content-between flex-wrap gap-2">
            <strong>${e(row.instrument)} · ${rating(current.rating)}</strong>
            <span class="small">${row.held ? "You own this" : "Watching only"} · ${row.versions.length} view${row.versions.length === 1 ? "" : "s"}</span>
        </div>
        <p class="small mb-1${row.freshness === "review_due" ? " fw-semibold" : ""}">${state}</p>
        ${row.versions.length > 1 ? `<details class="small"><summary>How your view changed</summary><ol class="list-unstyled mt-2 mb-0">${row.versions.map(version).join("")}</ol></details>` : ""}
    </div>`;
}

function loadResearchHistory() {
    const target = document.getElementById("researchHistory");
    return Alfred.fetchJSON("/api/investments/research/history/").then(data => {
        target.innerHTML = data.instruments.length ? data.instruments.map(researchHistoryCard).join("")
            : `<p class="small muted mb-0">No views saved yet.</p>`;
    }).catch(() => { target.innerHTML = `<p class="small mb-0">Your view history could not load. Reload the page to retry; nothing was changed.</p>`; });
}

function loadResearchDecisions() {
    loadResearchHistory();
    return Alfred.fetchJSON("/api/investments/research/").then(data => {
        const items = Array.isArray(data) ? data : (data.results || []);
        const target = document.getElementById("researchDecisionList");
        if (!items.length) { target.innerHTML = `<div class="empty-state">No views saved yet. Look up a stock or write down your first view above.</div>`; return; }
        const today = researchToday();
        target.innerHTML = items.map(item => researchDecisionCard(item, today)).join("");
        target.querySelectorAll("[data-research-settle]").forEach(button => button.addEventListener("click", () => settleResearchDecision(button.dataset.researchSettle)));
        target.querySelectorAll("[data-research-lesson]").forEach(button => button.addEventListener("click", () => settleResearchDecision(button.dataset.researchLesson, true)));
        target.querySelectorAll("[data-research-delete]").forEach(button => button.addEventListener("click", () => deleteResearchDecision(button.dataset.researchDelete)));
    }).catch(error => showResearchFeedback(error.message, "danger"));
}

function showResearchFeedback(message, tone) {
    const box = document.getElementById("researchFeedback");
    box.className = `alert alert-${tone} mb-0`;
    box.textContent = message;
}

function submitResearchDecision(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const button = form.querySelector("button[type=submit]");
    const payload = Object.fromEntries(new FormData(form).entries());
    if (!payload.benchmark_entry) delete payload.benchmark_entry;
    button.disabled = true;
    Alfred.fetchJSON("/api/investments/research/", { method: "POST", body: JSON.stringify(payload) })
        .then(() => {
            form.reset();
            resetResearchDates(form);
            document.getElementById("researchLessons").replaceChildren();
            showResearchFeedback(`View saved. Come back on ${payload.review_on} to see if you were right.`, "success");
            return loadResearchDecisions();
        })
        .catch(error => showResearchFeedback(error.message, "danger"))
        .finally(() => { button.disabled = false; });
}

function settleResearchDecision(id, lessonOnly = false) {
    const payload = { lesson: document.getElementById(`researchLesson${id}`).value };
    if (!lessonOnly) {
        payload.exit_price = document.getElementById(`researchExit${id}`).value;
        const bench = document.getElementById(`researchBenchExit${id}`);
        if (bench) payload.benchmark_exit = bench.value;
    }
    Alfred.fetchJSON(`/api/investments/research/${id}/settle/`, { method: "POST", body: JSON.stringify(payload) })
        .then(() => { showResearchFeedback(lessonOnly ? "Lesson saved." : "Checked. Your result is below.", "success"); return loadResearchDecisions(); })
        .catch(error => showResearchFeedback(error.message, "danger"));
}

function deleteResearchDecision(id) {
    if (!window.confirm("Delete this view? Your holdings are not affected.")) return;
    Alfred.fetchJSON(`/api/investments/research/${id}/`, { method: "DELETE" })
        .then(() => { showResearchFeedback("View deleted.", "success"); return loadResearchDecisions(); })
        .catch(error => showResearchFeedback(error.message, "danger"));
}

// WEALTH2-001: the owner uploads each fund's monthly portfolio file; the server keeps its parsed rows only when Save is ticked.
let lookThroughHoldings = [], lookThroughCount = 0;

function initLookThrough() {
    const form = document.getElementById("lookThroughForm");
    if (!form) return;
    addLookThroughRow();
    document.getElementById("lookThroughAdd").addEventListener("click", () => {
        addLookThroughRow();
        document.querySelector("#lookThroughRows fieldset:last-child select")?.focus();
    });
    form.addEventListener("submit", submitLookThrough);
    document.getElementById("lookThroughSavedForm").addEventListener("submit", submitSavedLookThrough);
    loadSavedPortfolios();
}

function loadSavedPortfolios() {
    return Alfred.fetchJSON("/api/investments/look-through/saved/").then(rows => {
        const latest = new Map();
        rows.forEach(row => { if (!latest.has(row.investment_id)) latest.set(row.investment_id, row); });  // newest first from the server
        const esc = Alfred.escapeHtml, list = document.getElementById("lookThroughSaved");
        Alfred.setHTML(list, [...latest.values()].map(row => `<li class="d-flex flex-wrap align-items-center gap-2 mb-1">
            <input class="form-check-input mt-0" type="checkbox" id="lookThroughSaved${row.id}" value="${row.investment_id}">
            <label class="form-check-label" for="lookThroughSaved${row.id}"><strong>${esc(row.holding)}</strong>: ${esc(row.scheme || "scheme name not found")},
                ${row.as_of ? `portfolio of ${esc(row.as_of)}` : "portfolio date not found"} · ${row.securities} companies</label>
            <button type="button" class="btn btn-link btn-sm p-0" data-remove-portfolio="${row.id}" aria-label="Remove the saved portfolio of ${esc(row.holding)}">Remove</button></li>`).join(""));
        list.querySelectorAll("[data-remove-portfolio]").forEach(button => button.addEventListener("click", () => removeSavedPortfolio(button.dataset.removePortfolio)));
        document.getElementById("lookThroughSavedBlock").hidden = latest.size === 0;
    }).catch(() => {});
}

function removeSavedPortfolio(id) {
    if (!window.confirm("Remove this saved portfolio? Your holdings are not affected.")) return;
    const status = document.getElementById("lookThroughStatus");
    Alfred.fetchJSON(`/api/investments/look-through/saved/${id}/`, { method: "DELETE" })
        .then(() => { status.textContent = "Saved portfolio removed."; return loadSavedPortfolios(); })
        .catch(error => { status.textContent = error.message || "The saved portfolio could not be removed."; });
}

async function submitSavedLookThrough(event) {
    event.preventDefault();
    const status = document.getElementById("lookThroughStatus"), button = document.getElementById("lookThroughSavedSubmit");
    const ids = [...document.querySelectorAll("#lookThroughSaved input:checked")].map(box => Number(box.value));
    if (!ids.length) { status.textContent = "Tick at least one saved portfolio."; document.querySelector("#lookThroughSaved input")?.focus(); return; }
    button.disabled = true;
    status.textContent = "Reading the saved portfolios…";
    try {
        const data = await Alfred.fetchJSON("/api/investments/look-through/saved/", { method: "POST", body: JSON.stringify({ investment: ids }) });
        renderLookThrough(data);
        status.textContent = `Used ${data.funds.length} saved portfolio(s).`;
    } catch (error) {
        document.getElementById("lookThroughResult").replaceChildren();
        status.textContent = error.message || "The saved portfolios could not be read.";
    } finally {
        button.disabled = false;
    }
}

function addLookThroughRow() {
    const rows = document.getElementById("lookThroughRows");
    if (rows.children.length >= 5) return;
    const n = ++lookThroughCount;
    const row = document.createElement("fieldset");
    row.className = "border rounded p-2";
    row.innerHTML = `<legend class="h6 small fw-bold float-none w-auto px-1 mb-1">Fund ${rows.children.length + 1}</legend>
        <div class="row g-2">
            <div class="col-md-5"><label class="form-label small" for="lookThroughHolding${n}">Your holding</label>
                <select class="form-select form-select-sm" id="lookThroughHolding${n}" name="investment" required></select></div>
            <div class="col-md-7"><label class="form-label small" for="lookThroughFile${n}">Its monthly portfolio file</label>
                <input class="form-control form-control-sm" id="lookThroughFile${n}" name="file" type="file" accept=".xlsx,.csv" required></div>
        </div>`;
    rows.append(row);
    // A different file may hold different funds, so an earlier "which fund" choice no longer applies.
    row.querySelector("input[type=file]").addEventListener("change", () => row.querySelector("[data-sheet-choice]")?.remove());
    fillLookThroughHoldings(lookThroughHoldings);
    document.getElementById("lookThroughAdd").disabled = rows.children.length >= 5;
}

function askWhichFund(row, funds, status) {
    row.querySelector("[data-sheet-choice]")?.remove();
    const id = `${row.querySelector("input[type=file]").id}Sheet`;
    const box = document.createElement("div");
    box.className = "col-12";
    box.dataset.sheetChoice = "";
    const label = document.createElement("label");
    label.className = "form-label small";
    label.htmlFor = id;
    label.textContent = "This file has several funds. Which one is this holding?";
    const select = document.createElement("select");
    select.className = "form-select form-select-sm";
    select.id = id;
    select.name = "sheet";
    select.append(new Option("Choose a fund", ""), ...funds.map(fund => new Option(fund.scheme === fund.sheet ? fund.sheet : `${fund.sheet}: ${fund.scheme}`, fund.sheet)));
    box.append(label, select);
    row.querySelector(".row").append(box);
    status.textContent = "This file has several funds. Choose which one belongs to the holding, then show again.";
    select.focus();
}

function fillLookThroughHoldings(items) {
    lookThroughHoldings = items;
    document.querySelectorAll("#lookThroughRows select[name=investment]").forEach(select => {
        const chosen = select.value;
        select.replaceChildren(new Option("Choose a holding", ""), ...items.map(item => new Option(item.asset_name, String(item.id))));
        select.value = items.some(item => String(item.id) === chosen) ? chosen : "";
    });
}

async function submitLookThrough(event) {
    event.preventDefault();
    const status = document.getElementById("lookThroughStatus"), result = document.getElementById("lookThroughResult");
    const button = document.getElementById("lookThroughSubmit");
    const payload = new FormData(), used = [];
    for (const row of document.querySelectorAll("#lookThroughRows fieldset")) {
        const select = row.querySelector("select[name=investment]"), file = row.querySelector("input[type=file]").files[0];
        if (!select.value && !file) continue;
        if (!select.value || !file) {
            status.textContent = "Choose both a holding and its file for each fund, or leave the row empty.";
            (select.value ? row.querySelector("input") : select).focus();
            return;
        }
        payload.append("investment", select.value);
        payload.append("file", file);
        payload.append("sheet", row.querySelector("select[name=sheet]")?.value || "");
        used.push(row);
    }
    if (!payload.has("file")) { status.textContent = "Add at least one fund's portfolio file."; return; }
    const save = document.getElementById("lookThroughSave").checked;
    if (save) payload.append("save", "1");
    button.disabled = true;
    status.textContent = "Reading the files…";
    try {
        const data = await Alfred.fetchJSON("/api/investments/look-through/analyze/", { method: "POST", body: payload });
        if (data.choose) { result.replaceChildren(); askWhichFund(used[data.choose.file_index], data.choose.funds, status); return; }
        renderLookThrough(data);
        const kept = data.funds.filter(fund => fund.saved_snapshot).length;
        status.textContent = save ? `Read ${data.funds.length} file(s). Saved ${kept} portfolio(s).` : `Read ${data.funds.length} file(s). Nothing was saved.`;
        if (save) loadSavedPortfolios();
    } catch (error) {
        result.replaceChildren();
        status.textContent = error.message || "The files could not be read.";
    } finally {
        button.disabled = false;
    }
}

function renderLookThrough(data) {
    const esc = Alfred.escapeHtml;
    const money = value => data.currency ? Alfred.formatCurrency(Number(value), data.currency) : `${Alfred.formatNumber(Number(value), 2)} (currency not recorded)`;
    const names = Object.fromEntries(data.funds.map(fund => [fund.investment_id, fund.holding]));
    const funds = data.funds.map(fund => `<li class="mb-2"><strong>${esc(fund.holding)}</strong>: ${esc(fund.scheme_in_file || "scheme name not found in the file")},
        ${fund.as_of ? `portfolio of ${esc(fund.as_of)}` : "portfolio date not found"} · ${fund.securities} companies · ${esc(fund.opaque_pct)}% not looked through
        ${fund.warnings.map(warning => `<div class="text-warning-emphasis">${esc(warning)}</div>`).join("")}</li>`).join("");
    const overlaps = data.overlaps.map(item => `<li>${esc(names[item.funds[0]])} and ${esc(names[item.funds[1]])}: ${item.common_securities} companies in common, ${esc(item.overlap_pct)}% overlap</li>`).join("");
    const companies = data.companies.slice(0, 15).map(item => `<tr><td>${esc(item.name)}</td><td>${esc(item.sector || "Not stated")}</td><td>${esc(item.country)}</td>
        <td class="text-end">${money(item.amount)}</td><td class="text-end">${esc(item.share_pct)}%</td><td>${item.funds.map(fund => esc(names[fund.investment_id])).join(", ")}</td></tr>`).join("");
    const groups = items => items.slice(0, 10).map(item => `<li>${esc(item.name)}: ${money(item.amount)} (${esc(item.share_pct)}%)</li>`).join("");
    Alfred.setHTML(document.getElementById("lookThroughResult"), `
        <p class="mb-2">Recorded value looked at: <strong>${money(data.total_value)}</strong>. Not looked through (cash, other funds' units, unlisted rows): ${money(data.opaque.amount)} (${esc(data.opaque.share_pct)}%).</p>
        <h3 class="h6">Files</h3><ul class="small">${funds}</ul>
        ${overlaps ? `<h3 class="h6">Overlap between funds</h3><ul class="small">${overlaps}</ul>` : ""}
        <h3 class="h6">Largest companies across your funds</h3>
        <div class="table-responsive"><table class="table table-sm small" id="lookThroughCompanies">
            <caption class="visually-hidden">Largest companies across the chosen funds</caption>
            <thead><tr><th scope="col">Company</th><th scope="col">Sector</th><th scope="col">Country</th><th scope="col" class="text-end">Amount</th><th scope="col" class="text-end">Share</th><th scope="col">In funds</th></tr></thead>
            <tbody>${companies}</tbody></table></div>
        <div class="row g-3 small"><div class="col-md-6"><h3 class="h6">By sector</h3><ul>${groups(data.sectors)}</ul></div>
            <div class="col-md-6"><h3 class="h6">By country</h3><ul>${groups(data.countries)}</ul></div></div>
        <p class="small mb-1">Currency: ${esc(data.currency_exposure)}</p>
        <ul class="small muted mb-0">${data.limits.map(item => `<li>${esc(item)}</li>`).join("")}</ul>`);
}
