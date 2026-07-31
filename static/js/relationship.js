let relationshipChart;

document.addEventListener("DOMContentLoaded", () => {
    if (!document.getElementById("relationshipRoot")) {
        return;
    }

    document.getElementById("relationshipForm").addEventListener("submit", submitRelationshipForm);
    loadRelationshipDashboard();
    Alfred.enableLiveRefresh("relationship-live", loadRelationshipDashboard, { rootId: "relationshipRoot" });
});

function loadRelationshipDashboard(options = {}) {
    return Promise.all([
        Alfred.fetchJSON("/api/relationship/"),
        Alfred.fetchJSON("/api/relationship/alignment/"),
    ])
        .then(([profiles, alignment]) => {
            renderRelationshipHero(alignment);
            renderRelationshipSummary(profiles, alignment);
            renderRelationshipChart(profiles, alignment);
            renderRelationshipInsights(alignment.insights || [alignment.message || "No relationship insights yet."]);
            renderRelationshipGrounding(alignment);
            renderRelationshipTable(profiles);
            if (!options.live) {
                hydrateRelationshipForm(profiles[0]);
            }
            Alfred.clearPageAlert("relationshipRoot");
        })
        .catch(error => {
            Alfred.upsertPageAlert("relationshipRoot", error.message, "danger");
        });
}

function renderRelationshipHero(alignment) {
    document.getElementById("relationshipScoreValue").textContent = `${Alfred.formatNumber(alignment.alignment_score || 0, 0)}%`;
    document.getElementById("relationshipCompatibilityValue").textContent = alignment.compatibility || "Unknown";
    document.getElementById("relationshipHeroCopy").textContent = alignment.message || "Relationship insights are active.";
}

function renderRelationshipSummary(profiles, alignment) {
    const latest = profiles[0];
    const cards = [
        { title: "Profiles", value: Alfred.formatNumber(profiles.length, 0), copy: "Saved partner profiles" },
        { title: "Alignment", value: `${Alfred.formatNumber(alignment.alignment_score || 0, 0)}%`, copy: alignment.compatibility || "Unknown" },
        { title: "Partner Score", value: Alfred.formatNumber(latest?.partner_financial_score || 0, 0), copy: latest ? latest.partner_name : "No partner profile yet" },
        { title: "Savings Habit", value: `${Alfred.formatNumber((latest?.partner_savings_habits || 0) * 20, 0)} / 100`, copy: "Converted from 1-5 habit score" },
    ];

    document.getElementById("relationshipSummaryCards").innerHTML = cards.map(card => `
        <article class="metric-card">
            <p class="metric-kicker">${card.title}</p>
            <h2 class="metric-value">${card.value}</h2>
            <p class="metric-caption">${Alfred.escapeHtml(card.copy)}</p>
        </article>
    `).join("");
}

function renderRelationshipChart(profiles, alignment) {
    const latest = profiles[0];
    const canvas = document.getElementById("relationshipRadar");
    if (relationshipChart) {
        relationshipChart.destroy();
    }

    const factorMap = Object.fromEntries((alignment.factors || []).map(item => [item.label, item.score]));
    const partner = [
        factorMap["Financial Alignment"] || latest?.partner_financial_score || 0,
        factorMap["Savings Habit Fit"] || (latest?.partner_savings_habits || 0) * 20,
        factorMap["Shared Resilience"] || latest?.compatibility_score || 0,
        alignment.alignment_score || 0,
    ];
    const baseline = [
        alignment.alignment_score || 0,
        factorMap["Savings Habit Fit"] || 75,
        factorMap["Planning Pressure"] || Math.max(60, alignment.alignment_score || 0),
        80,
    ];

    relationshipChart = new Chart(canvas, {
        type: "radar",
        data: {
            labels: ["Financial", "Savings", "Compatibility", "Alignment"],
            datasets: [
                {
                    label: "You",
                    data: baseline,
                    borderColor: "#1858d6",
                    backgroundColor: "rgba(24, 88, 214, 0.14)",
                },
                {
                    label: latest?.partner_name || "Partner",
                    data: partner,
                    borderColor: "#ff825c",
                    backgroundColor: "rgba(255, 130, 92, 0.16)",
                },
            ],
        },
        options: {
            scales: {
                r: {
                    suggestedMin: 0,
                    suggestedMax: 100,
                },
            },
        },
    });
}

function renderRelationshipInsights(items) {
    const target = document.getElementById("relationshipInsightList");
    target.innerHTML = items.map(item => `<li class="insight-item">${Alfred.escapeHtml(item)}</li>`).join("");
}

function renderRelationshipGrounding(alignment) {
    const factors = alignment.factors || [];
    const grounding = alignment.grounding || {};
    const history = grounding.history || {};
    const freshness = grounding.freshness || {};
    const cardsTarget = document.getElementById("relationshipFactorCards");
    const metaTarget = document.getElementById("relationshipGroundingMeta");
    const listTarget = document.getElementById("relationshipGroundingList");
    const evidenceTarget = document.getElementById("relationshipEvidenceLog");

    cardsTarget.innerHTML = factors.map(item => `
        <article class="metric-card metric-card--compact">
            <p class="metric-kicker">${Alfred.escapeHtml(item.label)}</p>
            <h3 class="metric-value" style="font-size:1.35rem;">${Alfred.formatNumber(item.score || 0, 0)}/100</h3>
            <p class="metric-caption">${Alfred.escapeHtml(item.detail || "")}</p>
        </article>
    `).join("");

    metaTarget.innerHTML = [
        ["Monthly income", Alfred.formatCurrency(history.monthly_income || 0), "Household income basis"],
        ["Monthly spend", Alfred.formatCurrency(history.monthly_expenses || 0), "Recent spend basis"],
        ["Fixed load", Alfred.formatCurrency(history.fixed_load || 0), "Rent plus EMI pressure"],
        ["Fresh evidence", Alfred.formatNumber(freshness.fresh_records || 0, 0), `${Alfred.formatNumber(freshness.tracked_records || 0, 0)} records tracked`],
    ].map(([label, value, copy]) => `
        <article class="metric-card metric-card--compact">
            <p class="metric-kicker">${Alfred.escapeHtml(label)}</p>
            <h3 class="metric-value" style="font-size:1.35rem;">${Alfred.escapeHtml(String(value))}</h3>
            <p class="metric-caption">${Alfred.escapeHtml(copy)}</p>
        </article>
    `).join("");

    const details = [
        `Monthly EMI grounding: ${Alfred.formatCurrency(history.monthly_emi || 0)}`,
        `Debt pressure: ${Alfred.formatNumber(history.debt_pressure || 0, 0)}/100`,
        `Savings rate: ${Alfred.formatNumber(history.savings_rate || 0, 0)}%`,
        freshness.next_stale_after ? `Next evidence refresh due after ${Alfred.formatDateTime(freshness.next_stale_after)}` : "No external refresh deadline attached yet.",
        ...((grounding.notes || []).map(item => item)),
    ];
    listTarget.innerHTML = details.map(item => `<li class="insight-item">${Alfred.escapeHtml(item)}</li>`).join("");

    const evidence = grounding.evidence || [];
    evidenceTarget.innerHTML = evidence.length ? evidence.map(item => `
        <div class="mini-card">
            <div class="d-flex justify-content-between gap-3 align-items-start">
                <div>
                    <div class="fw-semibold">${Alfred.escapeHtml(item.source_name || item.title || "Evidence")}</div>
                    <div class="muted small">${Alfred.escapeHtml(item.status || "unknown")} ${item.verified_at ? `| refreshed ${Alfred.formatDateTime(item.verified_at)}` : ""}</div>
                    <div class="muted small mt-2">${Alfred.escapeHtml(item.summary || "")}</div>
                    ${item.stale_after ? `<div class="muted small mt-2">Next stale after ${Alfred.formatDateTime(item.stale_after)}</div>` : ""}
                </div>
                ${item.source_url ? `<a href="${item.source_url}" target="_blank" rel="noopener">Proof</a>` : ""}
            </div>
        </div>
    `).join("") : `<div class="empty-state">No external proof items are attached yet.</div>`;
}

function renderRelationshipTable(items) {
    const body = document.getElementById("relationshipTableBody");
    if (!items.length) {
        body.innerHTML = `<tr><td colspan="4" class="text-center muted py-4">No relationship profiles saved yet.</td></tr>`;
        return;
    }

    body.innerHTML = items.map(item => `
        <tr>
            <td class="fw-semibold">${Alfred.escapeHtml(item.partner_name)}</td>
            <td class="text-end">${Alfred.formatNumber(item.partner_financial_score, 0)}</td>
            <td class="text-end">${Alfred.formatNumber(item.partner_savings_habits, 0)} / 5</td>
            <td class="text-end">${Alfred.formatNumber(item.compatibility_score, 0)}</td>
        </tr>
    `).join("");
}

function hydrateRelationshipForm(profile) {
    if (!profile) {
        return;
    }

    const form = document.getElementById("relationshipForm");
    form.partner_name.value = profile.partner_name || "";
    form.partner_financial_score.value = profile.partner_financial_score ?? 0;
    form.partner_savings_habits.value = profile.partner_savings_habits ?? 3;
    form.compatibility_score.value = profile.compatibility_score ?? 0;
}

function submitRelationshipForm(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const payload = Object.fromEntries(new FormData(form).entries());
    ["partner_financial_score", "partner_savings_habits", "compatibility_score"].forEach(key => {
        payload[key] = Number(payload[key] || 0);
    });

    Alfred.fetchJSON("/api/relationship/", {
        method: "POST",
        body: JSON.stringify(payload),
    })
        .then(() => {
            form.reset();
            showRelationshipFeedback("Relationship profile saved.", "success");
            loadRelationshipDashboard();
        })
        .catch(error => showRelationshipFeedback(error.message, "danger"));
}

function showRelationshipFeedback(message, tone) {
    const box = document.getElementById("relationshipFormFeedback");
    box.className = `alert alert-${tone} mb-0`;
    box.textContent = message;
    box.classList.remove("d-none");
}
