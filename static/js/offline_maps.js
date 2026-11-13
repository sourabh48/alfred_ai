// Settings > Offline maps: check a country's size, download only after the owner confirms that size, remove any time.
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

    function row(m) {
        const name = e(m.name), buttons = [];
        let text;
        if (m.state === "sizing") text = `${name}: checking the size…`;
        else if (m.state === "ready") {
            text = `${name}: <strong>${size(m.bytes)}</strong> to download. Download it now?`;
            buttons.push(`<button type="button" class="btn btn-primary btn-sm" data-download="${e(m.code)}" data-build="${e(m.build)}" data-bytes="${Number(m.bytes)}">Download ${size(m.bytes)}</button>`,
                         `<button type="button" class="btn btn-outline-secondary btn-sm" data-remove="${e(m.code)}">Not now</button>`);
        } else if (m.state === "downloading") {
            const pct = m.bytes ? Math.floor(100 * (m.done || 0) / m.bytes) : 0;
            text = `${name}: downloading ${size(m.done || 0)} of ${size(m.bytes)}<div class="progress mt-1" role="progressbar" aria-label="${name} map download" aria-valuenow="${pct}" aria-valuemin="0" aria-valuemax="100"><div class="progress-bar" style="width:${pct}%">${pct}%</div></div>`;
            buttons.push(`<button type="button" class="btn btn-outline-danger btn-sm" data-remove="${e(m.code)}">Stop and remove</button>`);
        } else if (m.state === "failed") {
            text = `${name}: not finished because ${e(problems[m.error] || "the map could not be fetched")}. What was downloaded is kept; check the size again to continue.`;
            buttons.push(`<button type="button" class="btn btn-outline-primary btn-sm" data-size="${e(m.code)}">Check size again</button>`,
                         `<button type="button" class="btn btn-outline-danger btn-sm" data-remove="${e(m.code)}">Remove</button>`);
        } else {
            text = `${name}: on this PC (${size(m.installed_bytes)}).`;
            buttons.push(`<button type="button" class="btn btn-outline-danger btn-sm" data-remove="${e(m.code)}">Remove</button>`);
        }
        return `<div class="d-flex flex-wrap align-items-center gap-2"><div class="flex-grow-1 small">${text}</div>${canManage ? buttons.join("") : ""}</div>`;
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
            feedback.textContent = data.result === "stopping" ? "Stopping. The partial map is deleted when it stops." : done;
        }
        catch (error) { feedback.textContent = error.message || "Nothing was changed."; }
    }

    form.addEventListener("submit", event => {
        event.preventDefault();
        send({ action: "size", country: select.value }, "Checking the size. Nothing downloads until you confirm.");
    });
    list.addEventListener("click", event => {
        const b = event.target.closest("button");
        if (!b) return;
        if (b.dataset.download) send({ action: "download", country: b.dataset.download, build: b.dataset.build, bytes: Number(b.dataset.bytes) }, "Downloading. You can keep using ALFRED.");
        else if (b.dataset.size) send({ action: "size", country: b.dataset.size }, "Checking the size again.");
        else if (b.dataset.remove) send({ action: "remove", country: b.dataset.remove }, "Removed from this PC.");
    });
    load();
});
