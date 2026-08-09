let familyChart;

document.addEventListener("DOMContentLoaded", () => {
    if (!document.getElementById("familyRoot")) {
        return;
    }

    document.getElementById("dependentForm").addEventListener("submit", submitDependentForm);
    loadFamilyDashboard();
    Alfred.enableLiveRefresh("family-live", loadFamilyDashboard, { rootId: "familyRoot" });
});

function loadFamilyDashboard() {
    return Promise.all([
        Alfred.fetchJSON("/api/family/"),
        Alfred.fetchJSON("/api/family/growth/"),
    ])
        .then(([dependents, growth]) => {
            renderFamilyHero(growth);
            renderFamilySummary(dependents, growth);
            renderFamilyChart(growth.projections || []);
            renderFamilyInsights(growth.insights || []);
            renderFamilyTable(dependents);
            Alfred.clearPageAlert("familyRoot");
        })
        .catch(error => {
            Alfred.upsertPageAlert("familyRoot", error.message, "danger");
        });
}

function renderFamilyHero(growth) {
    document.getElementById("familyNetWorthValue").textContent = Alfred.formatCurrency(growth.current_net_worth || 0);
    document.getElementById("familyDependentCount").textContent = Alfred.formatNumber(growth.dependents_count || 0, 0);
    const linkedAccounts = Number(growth.linked_family_account_count || 0);
    document.getElementById("familyHeroCopy").textContent = linkedAccounts
        ? `${Alfred.formatNumber(linkedAccounts, 0)} linked account${linkedAccounts === 1 ? "" : "s"} in family context`
        : `Projected growth rate ${Alfred.formatNumber(growth.growth_rate || 0)}%`;
}

function renderFamilySummary(dependents, growth) {
    const yearTen = (growth.projections || []).at(-1);
    const cards = [
        { title: "Dependents", value: Alfred.formatNumber(growth.dependents_count || dependents.length, 0), copy: "Household members tracked" },
        { title: "Linked Accounts", value: Alfred.formatNumber(growth.linked_family_account_count || 0, 0), copy: "Accepted family links" },
        { title: "Current Net Worth", value: Alfred.formatCurrency(growth.current_net_worth || 0), copy: "Assets minus active debt" },
        { title: "10-Year Projection", value: Alfred.formatCurrency(yearTen?.projected_net_worth || 0), copy: "Projected household base in year 10" },
    ];

    document.getElementById("familySummaryCards").innerHTML = cards.map(card => `
        <article class="metric-card">
            <p class="metric-kicker">${card.title}</p>
            <h2 class="metric-value">${card.value}</h2>
            <p class="metric-caption">${card.copy}</p>
        </article>
    `).join("");
}

function renderFamilyChart(items) {
    const canvas = document.getElementById("familyNetChart");
    if (familyChart) {
        familyChart.destroy();
    }

    familyChart = new Chart(canvas, {
        type: "line",
        data: {
            labels: items.map(item => `Year ${item.year}`),
            datasets: [{
                label: "Projected net worth",
                data: items.map(item => item.projected_net_worth),
                borderColor: "#1858d6",
                backgroundColor: "rgba(24, 88, 214, 0.1)",
                fill: true,
                tension: 0.25,
            }],
        },
        options: { plugins: { legend: { display: false } } },
    });
}

function renderFamilyInsights(items) {
    const target = document.getElementById("familyInsightList");
    if (!items.length) {
        target.innerHTML = `<li class="insight-item">Family planning insights will appear after data is added.</li>`;
        return;
    }
    target.innerHTML = items.map(item => `<li class="insight-item">${Alfred.escapeHtml(item)}</li>`).join("");
}

function renderFamilyTable(items) {
    const body = document.getElementById("familyTableBody");
    if (!items.length) {
        body.innerHTML = `<tr><td colspan="3" class="text-center muted py-4">No dependents registered yet.</td></tr>`;
        return;
    }

    body.innerHTML = items.map(item => `
        <tr>
            <td class="fw-semibold">${Alfred.escapeHtml(item.name)}</td>
            <td>${Alfred.escapeHtml(item.relation)}</td>
            <td class="text-end">${Alfred.formatNumber(item.age, 0)}</td>
        </tr>
    `).join("");
}

function submitDependentForm(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const payload = Object.fromEntries(new FormData(form).entries());
    payload.age = Number(payload.age || 0);

    Alfred.fetchJSON("/api/family/", {
        method: "POST",
        body: JSON.stringify(payload),
    })
        .then(() => {
            form.reset();
            showFamilyFeedback("Dependent added.", "success");
            loadFamilyDashboard();
        })
        .catch(error => showFamilyFeedback(error.message, "danger"));
}

function showFamilyFeedback(message, tone) {
    const box = document.getElementById("dependentFormFeedback");
    box.className = `alert alert-${tone} mb-0`;
    box.textContent = message;
    box.classList.remove("d-none");
}
