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

// A withheld or missing alignment has no factors; its numeric 0 is not a measured score.
const alignmentLabel = alignment => (alignment.factors || []).length ? `${Alfred.formatNumber(alignment.alignment_score || 0, 0)}%` : "—";

function renderRelationshipHero(alignment) {
    document.getElementById("relationshipScoreValue").textContent = alignmentLabel(alignment);
    document.getElementById("relationshipCompatibilityValue").textContent = alignment.compatibility || "Unknown";
    document.getElementById("relationshipHeroCopy").textContent = alignment.message || "Relationship insights are active.";
}

function renderRelationshipSummary(profiles, alignment) {
    const latest = profiles[0];
    const cards = [
        { title: "Profiles", value: Alfred.formatNumber(profiles.length, 0), copy: "Saved partner profiles" },
        { title: "Alignment", value: alignmentLabel(alignment), copy: alignment.compatibility || "Unknown" },
        { title: "Partner Score", value: latest ? Alfred.formatNumber(latest.partner_financial_score || 0, 0) : "—", copy: latest ? latest.partner_name : "No partner profile yet" },
        { title: "Savings Habit", value: latest ? `${Alfred.formatNumber((latest.partner_savings_habits || 0) * 20, 0)} / 100` : "—", copy: "Converted from 1-5 habit score" },
    ];

    Alfred.setHTML(document.getElementById("relationshipSummaryCards"), cards.map(card => `
        <article class="metric-card">
            <p class="metric-kicker">${card.title}</p>
            <h2 class="metric-value">${card.value}</h2>
            <p class="metric-caption">${Alfred.escapeHtml(card.copy)}</p>
        </article>
    `).join(""));
}

function renderRelationshipChart(profiles, alignment) {
    const latest = profiles[0];
    const canvas = document.getElementById("relationshipRadar");
    // Plot only the factors that were scored; unavailable factors are listed in the message instead.
    const factors = alignment.factors || [];
    if (!factors.length) {
        relationshipChart?.destroy();
        relationshipChart = null;
        return;
    }
    relationshipChart = Alfred.renderChart(relationshipChart, canvas, {
        type: "bar",
        data: {
            labels: factors.map(item => item.label),
            datasets: [{
                label: latest?.partner_name ? `Alignment with ${latest.partner_name}` : "Alignment factors",
                data: factors.map(item => item.score),
                backgroundColor: "rgba(24, 88, 214, 0.45)",
            }],
        },
        options: { indexAxis: "y", scales: { x: { min: 0, max: 100 } } },
    });
}

function renderRelationshipInsights(items) {
    const target = document.getElementById("relationshipInsightList");
    Alfred.setHTML(target, items.map(item => `<li class="insight-item">${Alfred.escapeHtml(item)}</li>`).join(""));
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

    Alfred.setHTML(cardsTarget, factors.map(item => `
        <article class="metric-card metric-card--compact">
            <p class="metric-kicker">${Alfred.escapeHtml(item.label)}</p>
            <h3 class="metric-value" style="font-size:1.35rem;">${Alfred.formatNumber(item.score || 0, 0)}/100</h3>
            <p class="metric-caption">${Alfred.escapeHtml(item.detail || "")}</p>
        </article>
    `).join(""));

    Alfred.setHTML(metaTarget, [
        ["Monthly income", Number(history.monthly_income) > 0 ? Alfred.formatCurrency(history.monthly_income) : "Unavailable", "Household income basis"],
        ["Monthly spend", history.spend_observed ? Alfred.formatCurrency(history.monthly_expenses || 0) : "Unavailable", "Recent spend basis"],
        ["Fixed load", Alfred.formatCurrency(history.fixed_load || 0), "Rent plus EMI pressure"],
        ["Fresh evidence", Alfred.formatNumber(freshness.fresh_records || 0, 0), `${Alfred.formatNumber(freshness.tracked_records || 0, 0)} records tracked`],
    ].map(([label, value, copy]) => `
        <article class="metric-card metric-card--compact">
            <p class="metric-kicker">${Alfred.escapeHtml(label)}</p>
            <h3 class="metric-value" style="font-size:1.35rem;">${Alfred.escapeHtml(String(value))}</h3>
            <p class="metric-caption">${Alfred.escapeHtml(copy)}</p>
        </article>
    `).join(""));

    const details = [
        `Monthly EMI grounding: ${Alfred.formatCurrency(history.monthly_emi || 0)}`,
        `Debt pressure: ${Number(history.monthly_income) > 0 ? `${Alfred.formatNumber(history.debt_pressure || 0, 0)}/100` : "unavailable"}`,
        `Savings rate: ${history.spend_observed ? `${Alfred.formatNumber(history.savings_rate || 0, 0)}%` : "unavailable"}`,
        freshness.next_stale_after ? `Next evidence refresh due after ${Alfred.formatDateTime(freshness.next_stale_after)}` : "No external refresh deadline attached yet.",
        ...((grounding.notes || []).map(item => item)),
    ];
    Alfred.setHTML(listTarget, details.map(item => `<li class="insight-item">${Alfred.escapeHtml(item)}</li>`).join(""));

    const evidence = grounding.evidence || [];
    Alfred.setHTML(evidenceTarget, evidence.length ? evidence.map(item => `
        <div class="mini-card">
            <div class="d-flex justify-content-between gap-3 align-items-start">
                <div>
                    <div class="fw-semibold">${Alfred.escapeHtml(item.source_name || item.title || "Evidence")}</div>
                    <div class="muted small">${Alfred.escapeHtml(item.status || "unknown")} ${item.verified_at ? `| refreshed ${Alfred.formatDateTime(item.verified_at)}` : ""}</div>
                    <div class="muted small mt-2">${Alfred.escapeHtml(item.summary || "")}</div>
                    ${item.stale_after ? `<div class="muted small mt-2">Next stale after ${Alfred.formatDateTime(item.stale_after)}</div>` : ""}
                </div>
                ${item.source_url ? `<a href="${Alfred.safeHref(item.source_url)}" target="_blank" rel="noopener">Proof</a>` : ""}
            </div>
        </div>
    `).join("") : `<div class="empty-state">No external proof items are attached yet.</div>`);
}

function renderRelationshipTable(items) {
    const body = document.getElementById("relationshipTableBody");
    if (!items.length) {
        Alfred.setHTML(body, `<tr><td colspan="4" class="text-center muted py-4">No relationship profiles saved yet.</td></tr>`);
        return;
    }

    Alfred.setHTML(body, items.map(item => `
        <tr>
            <td class="fw-semibold">${Alfred.escapeHtml(item.partner_name)}</td>
            <td class="text-end">${Alfred.formatNumber(item.partner_financial_score, 0)}</td>
            <td class="text-end">${Alfred.formatNumber(item.partner_savings_habits, 0)} / 5</td>
            <td class="text-end">${Alfred.formatNumber(item.compatibility_score, 0)}</td>
        </tr>
    `).join(""));
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
