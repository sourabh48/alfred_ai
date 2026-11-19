// Settings > Online services: each person's own keys and Career email address; the manager's free switches.
document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("onlineServicesForm");
    if (!form) return;
    const status = document.getElementById("onlineServicesStatus"), feedback = document.getElementById("onlineServicesFeedback");
    const e = Alfred.escapeHtml, url = "/api/settings/online-services/";
    const mail = id => document.getElementById(id);
    const pick = mail("careerMailChoices"), use = mail("careerMailUse"), off = mail("careerMailOff"), mailNote = mail("careerMailFeedback");
    let manager = false;

    function render(data) {
        const ready = data.keys.filter(k => k.saved).length, on = data.switches.filter(s => s.on).length;
        manager = data.can_manage;
        status.textContent = (data.switches.length ? `${on} of ${data.switches.length} free services on · ` : "") + `${ready} of ${data.keys.length} of your own keys saved · Career email ${data.mail.ready ? `from ${data.mail.address}` : "off"}.`
            + (data.can_manage || !data.switches.length ? "" : " Free services are set by the person who manages ALFRED on this PC.");
        document.getElementById("onlineServicesSwitchArea").hidden = !data.switches.length;
        document.getElementById("onlineServicesSwitches").innerHTML = data.switches.map(s => `<div class="form-check mb-1">
            <input class="form-check-input" type="checkbox" id="online-${e(s.name)}" data-switch="${e(s.name)}" ${s.on ? "checked" : ""} ${data.can_manage ? "" : "disabled"}>
            <label class="form-check-label small" for="online-${e(s.name)}">${e(s.detail)}</label></div>`).join("");
        document.getElementById("onlineServicesKeys").innerHTML = data.keys.map(k => `<div>
            <label class="form-label small mb-1" for="online-${e(k.name)}">${e(k.label)} ${k.saved ? `<span class="badge text-bg-success">Yours, saved ${e(k.hint)}</span>` : k.shared ? `<span class="badge text-bg-secondary">Using the shared key</span>` : ""}</label>
            <input class="form-control form-control-sm" type="password" id="online-${e(k.name)}" data-key="${e(k.name)}" maxlength="512" autocomplete="off" spellcheck="false"
                placeholder="${k.saved ? "Saved; paste a new key to replace it" : k.shared ? "Optional: paste your own key" : "Not set"}" aria-describedby="online-${e(k.name)}-help">
            <div class="form-text" id="online-${e(k.name)}-help">${e(k.use)} <a href="${Alfred.safeHref(k.signup)}" target="_blank" rel="noopener noreferrer">Get a key</a>
                ${k.saved ? ` · <button type="button" class="btn btn-link btn-sm p-0 align-baseline" data-remove-key="${e(k.name)}">Remove</button>` : ""}</div></div>`).join("");
        const m = data.mail, current = c => m.ready && c.email === m.address;
        pick.innerHTML = m.choices.length ? m.choices.map((c, i) => `<div class="form-check mb-1">
            <input class="form-check-input" type="radio" name="careerMailFrom" id="careerMail${i}" value="${e(c.email)}" data-via="${e(c.via)}" ${current(c) ? "checked" : ""} ${c.can_send ? "" : "disabled"}>
            <label class="form-check-label small" for="careerMail${i}">${e(c.email)} <span class="muted">· you sign in with ${e(c.signed_in_with.join(" and "))}${current(c) ? ` · sending${m.reads_replies ? " and reply watch" : ""} on` : ""}</span>
                ${c.why ? `<span class="d-block muted">${e(c.why)}</span>` : ""}</label></div>`).join("")
            : '<p class="small muted mb-0">Sign in with Google or Microsoft to send Career email from that address.</p>';
        const ticked = () => pick.querySelector("input:checked");
        const sync = () => { use.disabled = !ticked() || ticked().value === m.address && m.ready; };
        pick.querySelectorAll("input").forEach(radio => radio.addEventListener("change", sync));
        sync();
        off.hidden = !m.ready;
        if (m.error) mailNote.textContent = m.error;
        mail("settingsCareerMail").hidden = false;
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
        } catch (error) {
            feedback.textContent = error.message || "Nothing was saved.";
        }
    }

    form.addEventListener("submit", event => {
        event.preventDefault();
        const body = { keys: {} };
        if (manager) {
            body.switches = {};
            form.querySelectorAll("[data-switch]").forEach(box => { body.switches[box.dataset.switch] = box.checked; });
        }
        form.querySelectorAll("[data-key]").forEach(input => { if (input.value.trim()) body.keys[input.dataset.key] = input.value.trim(); });
        save(body, "Saved. ALFRED is using these settings now.");
    });
    use.addEventListener("click", () => {  // the address's own provider asks the person to allow sending, then returns here
        const radio = pick.querySelector("input:checked");
        if (radio) location.assign(`/auth/${encodeURIComponent(radio.dataset.via)}/start/?purpose=mail&email=${encodeURIComponent(radio.value)}`);
    });
    off.addEventListener("click", () => save({ mail_off: true }, "Career email is off.").then(() => { mailNote.textContent = "Career email is off."; }));
    load();
});
