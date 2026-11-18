// Settings > Offline maps: one Download press sizes then downloads; Pause keeps what arrived, Cancel deletes it.
document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("offlineMapsForm");
    if (!form) return;
    const e = Alfred.escapeHtml, url = "/api/settings/offline-maps/";
    const status = document.getElementById("offlineMapsStatus"), feedback = document.getElementById("offlineMapsFeedback");
    const select = document.getElementById("offlineMapsCountry"), list = document.getElementById("offlineMapsList");
    const size = n => n >= 1e9 ? `${(n / 1e9).toFixed(2)} GB` : `${Math.max(0.1, n / 1e6).toFixed(1)} MB`;
    const problems = { timeout: "the map server did not answer in time", network_error: "there is no internet connection",
        quota_exhausted: "the map server is busy", incomplete_response: "the connection dropped", cancelled: "it was stopped" };
    let timer = null, canManage = false;

    // One row per country: a progress ring, the name and its size line, then the actions (owner, 2026-11-19).
    function ring(kind, pct, label) {
        if (kind === "busy") return `<div class="offline-map-ring"><span class="spinner-border" role="status" aria-label="${label}"></span></div>`;
        const inner = kind === "done" ? "✓" : kind === "failed" ? "!" : `${pct}%`;
        return `<div class="offline-map-ring is-${kind}" style="--pct:${pct}" role="progressbar" aria-label="${label}" aria-valuenow="${pct}" aria-valuemin="0" aria-valuemax="100"><span>${inner}</span></div>`;
    }
    const button = (kind, attr, code, label) => `<button type="button" class="btn btn-sm btn-${kind}" data-${attr}="${e(code)}">${label}</button>`;

    function row(m) {
        const name = e(m.name), code = m.code, pct = m.bytes ? Math.min(100, Math.floor(100 * (m.done || 0) / m.bytes)) : 0;
        let graphic, detail, buttons;
        if (m.state === "sizing") {
            graphic = ring("busy", 0, `Checking the size of the ${name} map`);
            detail = "Working out the size; the download starts by itself.";
            buttons = [button("outline-danger", "remove", code, "Cancel")];
        } else if (m.state === "ready") {
            graphic = ring("paused", 0, `${name} map not downloaded`);
            detail = `${size(m.bytes)} to download.`;
            buttons = [`<button type="button" class="btn btn-sm btn-primary" data-download="${e(code)}" data-build="${e(m.build)}" data-bytes="${Number(m.bytes)}">Download</button>`,
                       button("outline-secondary", "remove", code, "Not now")];
        } else if (m.state === "downloading") {
            graphic = ring("active", pct, `${name} map download`);
            detail = `Downloading ${size(m.done || 0)} of ${size(m.bytes)}`;
            buttons = [button("outline-secondary", "pause", code, "Pause"), button("outline-danger", "remove", code, "Cancel")];
        } else if (m.state === "paused") {
            graphic = ring("paused", pct, `${name} map download, paused`);
            detail = `Paused at ${size(m.done || 0)} of ${size(m.bytes || 0)}. What arrived is kept.`;
            buttons = [button("primary", "get", code, "Resume"), button("outline-danger", "remove", code, "Cancel")];
        } else if (m.state === "failed") {
            graphic = ring("failed", pct, `${name} map download stopped`);
            detail = `Not finished because ${e(problems[m.error] || "the map could not be fetched")}. What arrived is kept.`;
            buttons = [button("primary", "get", code, "Resume"), button("outline-danger", "remove", code, "Remove")];
        } else {
            graphic = ring("done", 100, `${name} map on this PC`);
            detail = `On this PC · ${size(m.installed_bytes)}`;
            buttons = [button("outline-danger", "remove", code, "Remove")];
        }
        return `<div class="offline-map">${graphic}<div class="offline-map-body"><strong>${name}</strong><span class="small muted">${detail}</span></div>`
            + `<div class="offline-map-actions">${canManage ? buttons.join("") : ""}</div></div>`;
    }

    function render(data) {
        canManage = data.can_manage;
        const home = data.countries.find(c => c.code === data.home);
        const ready = data.maps.filter(m => !m.state).map(m => m.name);
        status.textContent = (ready.length ? `Offline maps on this PC: ${ready.join(", ")}.` : "No offline maps yet.")
            + (home && !data.maps.some(m => m.code === home.code) ? ` This PC is set to ${home.name}; its map is selected below.` : "")
            + (canManage ? "" : " Only the person who manages ALFRED on this PC can add or remove maps.");
        Alfred.setHTMLIfChanged("offlineMapsList", data.maps.map(row).join(""));
        if (!select.options.length) {
            select.innerHTML = data.countries.map(c => `<option value="${e(c.code)}">${e(c.name)}</option>`).join("");
            select.value = data.home || data.countries[0]?.code || "";
        }
        form.hidden = !canManage;
        clearTimeout(timer);
        if (data.maps.some(m => m.state === "sizing" || m.state === "downloading")) timer = setTimeout(load, 3000);
    }

    async function load() {
        try { render(await Alfred.fetchJSON(url)); } catch (error) { status.textContent = error.message || "Offline maps could not be loaded."; }
    }

    async function send(body, done) {
        feedback.textContent = "";
        try {
            const data = await Alfred.fetchJSON(url, { method: "POST", body: JSON.stringify(body) });
            render(data);
            feedback.textContent = data.result === "stopping" ? "Cancelling. The partial map is deleted when it stops." : done;
        }
        catch (error) { feedback.textContent = error.message || "Nothing was changed."; }
    }

    form.addEventListener("submit", event => {
        event.preventDefault();
        send({ action: "get", country: select.value }, "Working out the size, then downloading. You can keep using ALFRED.");
    });
    list.addEventListener("click", event => {
        const b = event.target.closest("button");
        if (!b) return;
        if (b.dataset.download) send({ action: "download", country: b.dataset.download, build: b.dataset.build, bytes: Number(b.dataset.bytes) }, "Downloading. You can keep using ALFRED.");
        else if (b.dataset.size) send({ action: "size", country: b.dataset.size }, "Checking the size again.");
        else if (b.dataset.get) send({ action: "get", country: b.dataset.get }, "Resuming. What arrived before is kept.");
        else if (b.dataset.pause) send({ action: "pause", country: b.dataset.pause }, "Pausing. What arrived is kept.");
        else if (b.dataset.remove) send({ action: "remove", country: b.dataset.remove }, "Removed from this PC.");
    });
    load();
});
