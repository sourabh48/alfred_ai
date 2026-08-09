const settingsState = {
    profile: null,
    dependents: [],
    links: null,
};

document.addEventListener("DOMContentLoaded", () => {
    if (!document.getElementById("accountSettingsRoot")) {
        return;
    }

    document.getElementById("accountProfileForm").addEventListener("submit", submitProfileForm);
    document.getElementById("settingsDependentForm").addEventListener("submit", submitSettingsDependentForm);
    document.getElementById("settingsDependentCancelBtn").addEventListener("click", resetDependentForm);
    document.getElementById("settingsGenerateInviteBtn").addEventListener("click", generateFamilyInvite);
    document.getElementById("settingsRefreshLinksBtn").addEventListener("click", loadAccountSettings);
    document.getElementById("settingsAcceptInviteForm").addEventListener("submit", acceptFamilyInvite);
    document.getElementById("settingsDependentTableBody").addEventListener("click", handleDependentTableAction);
    document.getElementById("settingsLinkedAccountsList").addEventListener("click", handleFamilyLinkAction);

    loadAccountSettings();
});

function loadAccountSettings() {
    Alfred.setPageBusy("accountSettingsRoot", true);
    return Promise.all([
        Alfred.fetchJSON("/api/users/profile/"),
        Alfred.fetchJSON("/api/family/"),
        Alfred.fetchJSON("/api/family/account-links/"),
    ])
        .then(([profile, dependents, links]) => {
            settingsState.profile = profile;
            settingsState.dependents = Array.isArray(dependents) ? dependents : [];
            settingsState.links = links || {};
            renderSettingsProfile(profile);
            renderSettingsDependents(settingsState.dependents);
            renderFamilyLinks(settingsState.links);
            renderFamilyContextSummary(settingsState.links);
            Alfred.clearPageAlert("accountSettingsRoot");
        })
        .catch(error => {
            Alfred.upsertPageAlert("accountSettingsRoot", error.message, "danger");
        })
        .finally(() => {
            Alfred.setPageBusy("accountSettingsRoot", false);
        });
}

function renderSettingsProfile(profile = {}) {
    const form = document.getElementById("accountProfileForm");
    const fields = [
        "first_name",
        "last_name",
        "email",
        "city",
        "country",
        "monthly_income",
        "variable_income",
        "rent_or_emi",
    ];
    fields.forEach(field => {
        if (form.elements[field]) {
            form.elements[field].value = profile[field] ?? "";
        }
    });
    Alfred.setTextIfChanged("settingsUsername", profile.username || "");
    Alfred.setTextIfChanged("settingsProfileStatus", "Synced");
}

function submitProfileForm(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const payload = Object.fromEntries(new FormData(form).entries());
    ["monthly_income", "variable_income", "rent_or_emi"].forEach(field => {
        payload[field] = Number(payload[field] || 0);
    });

    Alfred.fetchJSON("/api/users/profile/", {
        method: "PATCH",
        body: JSON.stringify(payload),
    })
        .then(profile => {
            settingsState.profile = profile;
            renderSettingsProfile(profile);
            showSettingsFeedback("settingsProfileFeedback", "Profile saved.", "success");
        })
        .catch(error => showSettingsFeedback("settingsProfileFeedback", error.message, "danger"));
}

function renderSettingsDependents(items = []) {
    const body = document.getElementById("settingsDependentTableBody");
    Alfred.setTextIfChanged("settingsDependentStatus", `${items.length} saved`);
    if (!items.length) {
        body.innerHTML = `<tr><td colspan="4" class="text-center muted py-4">No dependents registered yet.</td></tr>`;
        return;
    }
    body.innerHTML = items.map(item => `
        <tr>
            <td class="fw-semibold">${Alfred.escapeHtml(item.name)}</td>
            <td>${Alfred.escapeHtml(item.relation)}</td>
            <td class="text-end">${Alfred.formatNumber(item.age, 0)}</td>
            <td class="text-end">
                <div class="btn-group btn-group-sm" role="group" aria-label="Dependent actions">
                    <button type="button" class="btn btn-outline-primary" data-dependent-action="edit" data-dependent-id="${item.id}">Edit</button>
                    <button type="button" class="btn btn-outline-danger" data-dependent-action="delete" data-dependent-id="${item.id}">Delete</button>
                </div>
            </td>
        </tr>
    `).join("");
}

function submitSettingsDependentForm(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const payload = Object.fromEntries(new FormData(form).entries());
    const id = String(payload.id || "").trim();
    delete payload.id;
    payload.age = Number(payload.age || 0);
    const url = id ? `/api/family/${id}/` : "/api/family/";
    const method = id ? "PATCH" : "POST";

    Alfred.fetchJSON(url, {
        method,
        body: JSON.stringify(payload),
    })
        .then(() => {
            resetDependentForm();
            showSettingsFeedback("settingsDependentFeedback", "Family details saved.", "success");
            return loadAccountSettings();
        })
        .catch(error => showSettingsFeedback("settingsDependentFeedback", error.message, "danger"));
}

function handleDependentTableAction(event) {
    const button = event.target instanceof Element ? event.target.closest("[data-dependent-action]") : null;
    if (!button) {
        return;
    }
    const id = Number(button.dataset.dependentId || 0);
    const item = settingsState.dependents.find(candidate => Number(candidate.id) === id);
    if (!item) {
        return;
    }
    if (button.dataset.dependentAction === "edit") {
        editDependent(item);
        return;
    }
    if (button.dataset.dependentAction === "delete") {
        deleteDependent(item);
    }
}

function editDependent(item) {
    const form = document.getElementById("settingsDependentForm");
    form.elements.id.value = item.id;
    form.elements.name.value = item.name || "";
    form.elements.age.value = item.age ?? "";
    form.elements.relation.value = item.relation || "";
    document.getElementById("settingsDependentSubmitBtn").textContent = "Update";
    document.getElementById("settingsDependentCancelBtn").classList.remove("d-none");
}

function resetDependentForm() {
    const form = document.getElementById("settingsDependentForm");
    form.reset();
    form.elements.id.value = "";
    document.getElementById("settingsDependentSubmitBtn").textContent = "Add";
    document.getElementById("settingsDependentCancelBtn").classList.add("d-none");
}

function deleteDependent(item) {
    if (!window.confirm(`Delete ${item.name || "this dependent"}?`)) {
        return;
    }
    Alfred.fetchJSON(`/api/family/${item.id}/`, { method: "DELETE" })
        .then(() => {
            showSettingsFeedback("settingsDependentFeedback", "Dependent deleted.", "success");
            return loadAccountSettings();
        })
        .catch(error => showSettingsFeedback("settingsDependentFeedback", error.message, "danger"));
}

function renderFamilyContextSummary(snapshot = {}) {
    Alfred.setTextIfChanged("settingsFamilyContextCount", Alfred.formatNumber(snapshot.family_context_user_count || 1, 0));
    Alfred.setTextIfChanged("settingsLinkedAccountCount", Alfred.formatNumber(snapshot.accepted_link_count || 0, 0));
    Alfred.setTextIfChanged("settingsSharedDependentCount", Alfred.formatNumber(snapshot.shared_dependent_count || 0, 0));
    const financialCount = Number(snapshot.family_financial_user_count || snapshot.family_context_user_count || 1);
    Alfred.setTextIfChanged("settingsLinkStatus", snapshot.accepted_link_count ? `Linked | ${Alfred.formatNumber(financialCount, 0)} financial profile${financialCount === 1 ? "" : "s"}` : "Private");
}

function renderFamilyLinks(snapshot = {}) {
    const target = document.getElementById("settingsLinkedAccountsList");
    const links = Array.isArray(snapshot.links) ? snapshot.links : [];
    const activeLinks = links.filter(item => item.status === "accepted" || item.status === "pending");
    if (!activeLinks.length) {
        target.innerHTML = `<div class="empty-state">No active family links.</div>`;
        return;
    }
    target.innerHTML = activeLinks.map(link => {
        const profile = link.linked_profile || {};
        const title = link.status === "accepted"
            ? (profile.display_name || profile.username || "Linked account")
            : `Pending invite ending ${link.invite_code_hint || "----"}`;
        const meta = link.status === "accepted"
            ? [
                profile.username ? `@${profile.username}` : "",
                profile.city || "",
                profile.country || "",
                `${Alfred.formatNumber(profile.dependent_count || 0, 0)} dependent${Number(profile.dependent_count || 0) === 1 ? "" : "s"}`,
                link.share_financial_summary ? "financial summary shared" : "",
            ].filter(Boolean).join(" | ")
            : `Expires ${formatSettingsDateTime(link.expires_at)}`;
        return `
            <article class="mini-card family-link-row">
                <div>
                    <div class="fw-semibold">${Alfred.escapeHtml(title)}</div>
                    <div class="metric-caption">${Alfred.escapeHtml(meta)}</div>
                </div>
                <div class="d-flex align-items-center gap-2">
                    <span class="status-pill ${link.status === "accepted" ? "status-stable" : "status-guarded"}">${Alfred.escapeHtml(link.status)}</span>
                    <button class="btn btn-sm btn-outline-danger" type="button" data-family-link-action="revoke" data-family-link-id="${link.id}">Revoke</button>
                </div>
            </article>
        `;
    }).join("");
}

function generateFamilyInvite() {
    Alfred.fetchJSON("/api/family/account-links/", {
        method: "POST",
        body: JSON.stringify({}),
    })
        .then(payload => {
            settingsState.links = payload;
            renderFamilyLinks(payload);
            renderFamilyContextSummary(payload);
            renderGeneratedInvite(payload.invite || {});
            showSettingsFeedback("settingsLinkFeedback", "Family link code generated.", "success");
        })
        .catch(error => showSettingsFeedback("settingsLinkFeedback", error.message, "danger"));
}

function renderGeneratedInvite(invite = {}) {
    const panel = document.getElementById("settingsInviteCodePanel");
    panel.classList.remove("d-none");
    Alfred.setTextIfChanged("settingsInviteCode", invite.invite_code || "");
    Alfred.setTextIfChanged("settingsInviteExpiry", invite.expires_at ? `Expires ${formatSettingsDateTime(invite.expires_at)}` : "");
}

function acceptFamilyInvite(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const inviteCode = String(new FormData(form).get("invite_code") || "").trim();
    Alfred.fetchJSON("/api/family/account-links/accept/", {
        method: "POST",
        body: JSON.stringify({ invite_code: inviteCode }),
    })
        .then(payload => {
            form.reset();
            settingsState.links = payload;
            renderFamilyLinks(payload);
            renderFamilyContextSummary(payload);
            showSettingsFeedback("settingsLinkFeedback", "Family account connected.", "success");
            return loadAccountSettings();
        })
        .catch(error => showSettingsFeedback("settingsLinkFeedback", error.message, "danger"));
}

function handleFamilyLinkAction(event) {
    const button = event.target instanceof Element ? event.target.closest("[data-family-link-action]") : null;
    if (!button) {
        return;
    }
    if (button.dataset.familyLinkAction !== "revoke") {
        return;
    }
    const id = Number(button.dataset.familyLinkId || 0);
    if (!id || !window.confirm("Revoke this family account link?")) {
        return;
    }
    Alfred.fetchJSON(`/api/family/account-links/${id}/revoke/`, {
        method: "POST",
        body: JSON.stringify({}),
    })
        .then(payload => {
            settingsState.links = payload;
            renderFamilyLinks(payload);
            renderFamilyContextSummary(payload);
            showSettingsFeedback("settingsLinkFeedback", "Family account link revoked.", "success");
            return loadAccountSettings();
        })
        .catch(error => showSettingsFeedback("settingsLinkFeedback", error.message, "danger"));
}

function formatSettingsDateTime(value) {
    if (!value) {
        return "";
    }
    try {
        return Alfred.formatDateTime(value);
    } catch (_error) {
        return String(value);
    }
}

function showSettingsFeedback(elementId, message, tone) {
    const box = document.getElementById(elementId);
    if (!box) {
        return;
    }
    box.className = `alert alert-${tone} mb-0`;
    box.textContent = message;
    box.classList.remove("d-none");
}
