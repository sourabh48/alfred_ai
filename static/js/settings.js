const settingsState = {
    profile: null,
    links: null,
};

document.addEventListener("DOMContentLoaded", () => {
    if (!document.getElementById("accountSettingsRoot")) {
        return;
    }

    document.getElementById("accountProfileForm").addEventListener("submit", submitProfileForm);
    document.getElementById("settingsGenerateInviteBtn").addEventListener("click", generateFamilyInvite);
    document.getElementById("settingsRefreshLinksBtn").addEventListener("click", loadAccountSettings);
    document.getElementById("settingsAcceptInviteForm").addEventListener("submit", acceptFamilyInvite);
    document.getElementById("settingsLinkedAccountsList").addEventListener("click", handleFamilyLinkAction);

    loadAccountSettings();
});

function loadAccountSettings() {
    Alfred.setPageBusy("accountSettingsRoot", true);
    return Promise.all([
        Alfred.fetchJSON("/api/users/profile/"),
        Alfred.fetchJSON("/api/family/account-links/"),
    ])
        .then(([profile, links]) => {
            settingsState.profile = profile;
            settingsState.links = links || {};
            renderSettingsProfile(profile);
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

function renderFamilyContextSummary(snapshot = {}) {
    Alfred.setTextIfChanged("settingsLinkedAccountCount", Alfred.formatNumber(snapshot.accepted_link_count || 0, 0));
    Alfred.setTextIfChanged("settingsLinkStatus", snapshot.accepted_link_count ? "Connected" : "Not connected");
}

function renderFamilyLinks(snapshot = {}) {
    const target = document.getElementById("settingsLinkedAccountsList");
    const links = Array.isArray(snapshot.links) ? snapshot.links : [];
    const connectedLinks = links.filter(item => item.status === "accepted");
    if (!connectedLinks.length) {
        target.innerHTML = `<div class="empty-state">No members connected yet. Share or enter a link code above to connect an account.</div>`;
        return;
    }
    target.innerHTML = connectedLinks.map(link => {
        const profile = link.linked_profile || {};
        const title = profile.display_name || profile.username || "Connected member";
        const meta = [
            profile.username ? `@${profile.username}` : "",
            profile.city || "",
            profile.country || "",
        ].filter(Boolean).join(" | ");
        return `
            <article class="mini-card family-link-row">
                <div>
                    <div class="fw-semibold">${Alfred.escapeHtml(title)}</div>
                    <div class="metric-caption">${Alfred.escapeHtml(meta)}</div>
                </div>
                <div class="d-flex align-items-center gap-2">
                    <span class="status-pill status-stable">Connected</span>
                    <button class="btn btn-sm btn-outline-danger" type="button" data-family-link-action="revoke" data-family-link-id="${link.id}">Disconnect</button>
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
    if (!id || !window.confirm("Disconnect this member from your account?")) {
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
            showSettingsFeedback("settingsLinkFeedback", "Member disconnected.", "success");
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
