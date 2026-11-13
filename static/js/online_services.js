// Settings > Online services: free switches, the owner's own API keys and Career email, saved without editing files.
document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("onlineServicesForm");
    if (!form) return;
    const status = document.getElementById("onlineServicesStatus"), feedback = document.getElementById("onlineServicesFeedback");
    const e = Alfred.escapeHtml, url = "/api/settings/online-services/";
    const mail = id => document.getElementById(id);

    function render(data) {
        const ready = data.keys.filter(k => k.saved).length, on = data.switches.filter(s => s.on).length;
        status.textContent = `${on} of ${data.switches.length} free services on · ${ready} of ${data.keys.length} keys saved · Career email ${data.mail.ready ? "ready" : "off"}.`
            + (data.can_manage ? "" : " Only the person who manages ALFRED on this PC can change these.");
        document.getElementById("onlineServicesSwitches").innerHTML = data.switches.map(s => `<div class="form-check mb-1">
            <input class="form-check-input" type="checkbox" id="online-${e(s.name)}" data-switch="${e(s.name)}" ${s.on ? "checked" : ""} ${data.can_manage ? "" : "disabled"}>
            <label class="form-check-label small" for="online-${e(s.name)}">${e(s.detail)}</label></div>`).join("");
        document.getElementById("onlineServicesKeys").innerHTML = data.keys.map(k => `<div>
            <label class="form-label small mb-1" for="online-${e(k.name)}">${e(k.label)} ${k.saved ? `<span class="badge text-bg-success">Saved ${e(k.hint)}</span>` : ""}</label>
            <input class="form-control form-control-sm" type="password" id="online-${e(k.name)}" data-key="${e(k.name)}" maxlength="512" autocomplete="off" spellcheck="false"
                placeholder="${k.saved ? "Saved; paste a new key to replace it" : "Not set"}" aria-describedby="online-${e(k.name)}-help" ${data.can_manage ? "" : "disabled"}>
            <div class="form-text" id="online-${e(k.name)}-help">${e(k.use)} <a href="${Alfred.safeHref(k.signup)}" target="_blank" rel="noopener noreferrer">Get a key</a>
                ${k.saved && data.can_manage ? ` · <button type="button" class="btn btn-link btn-sm p-0 align-baseline" data-remove-key="${e(k.name)}">Remove</button>` : ""}</div></div>`).join("");
        mail("onlineMailAddress").value = data.mail.address || "";
        mail("onlineMailPassword").placeholder = data.mail.ready ? "Saved; type a new one to replace it" : "";
        mail("onlineMailRemove").hidden = !(data.mail.ready && data.can_manage);
        form.querySelectorAll("#onlineMailAddress, #onlineMailPassword, #onlineMailHost, #onlineMailPort, button").forEach(el => { el.disabled = !data.can_manage; });
        form.querySelectorAll("[data-remove-key]").forEach(button => button.addEventListener("click", () =>
            save({ keys: { [button.dataset.removeKey]: "" } }, "Key removed.")));
        form.hidden = false;
    }

    async function load() {
        try { render(await Alfred.fetchJSON(url)); } catch (error) { status.textContent = error.message || "Online services could not be loaded."; }
    }

    async function save(body, done) {
        feedback.textContent = "Saving…";
        try {
            render(await Alfred.fetchJSON(url, { method: "POST", body: JSON.stringify(body) }));
            feedback.textContent = done;
            mail("onlineMailPassword").value = "";
        } catch (error) {
            feedback.textContent = error.message || "Nothing was saved.";
        }
    }

    form.addEventListener("submit", event => {
        event.preventDefault();
        const body = { switches: {}, keys: {} };
        form.querySelectorAll("[data-switch]").forEach(box => { body.switches[box.dataset.switch] = box.checked; });
        form.querySelectorAll("[data-key]").forEach(input => { if (input.value.trim()) body.keys[input.dataset.key] = input.value.trim(); });
        if (mail("onlineMailPassword").value.trim()) {
            body.mail = { address: mail("onlineMailAddress").value.trim(), password: mail("onlineMailPassword").value,
                          host: mail("onlineMailHost").value.trim(), port: mail("onlineMailPort").value.trim() };
        }
        save(body, "Saved. ALFRED is using these settings now.");
    });
    mail("onlineMailRemove").addEventListener("click", () => save({ mail: {} }, "Career email is off."));
    load();
});
