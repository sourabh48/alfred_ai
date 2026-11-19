/* One photo at the top of each suggested place (owner request 2026-11-19); photo bytes stay in this view only. */
window.TravelPhotos = (() => {
    const esc = value => Alfred.escapeHtml(String(value ?? ""));
    const cache = new Map();  // "session|place" -> {status, image, credit}
    let queue = Promise.resolve();  // Google photos are fetched one at a time: the provider turns away a second call in flight.
    const wait = ms => new Promise(done => setTimeout(done, ms));

    function html(id, name) {
        const entry = cache.get(id);
        if (entry.status === "ready") {
            return `<figure class="travel-card-photo" data-travel-photo="${esc(id)}"><img src="${entry.image}" alt="${esc(name)}"><figcaption class="small">Photo: ${entry.credit}</figcaption></figure>`;
        }
        return entry.status === "none" ? "" : `<div class="travel-card-photo travel-card-photo-loading" data-travel-photo="${esc(id)}" aria-hidden="true"></div>`;
    }

    // Only the photo element is swapped when it arrives, so open panels, focus and disabled buttons around it stay as they are.
    function arrived(id, name) {
        document.querySelectorAll("[data-travel-photo]").forEach(node => { if (node.dataset.travelPhoto === id) node.outerHTML = html(id, name); });
    }

    function markup(sessionId, place) {
        if (!sessionId || !place?.name) return "";
        const id = `${sessionId}|${place.param || ""}${place.key || place.name}`;
        if (!cache.has(id)) {
            cache.set(id, {status: "loading"});
            const query = place.key ? `${place.param || "place"}=${encodeURIComponent(place.key)}` : `name=${encodeURIComponent(place.name)}`;
            const url = `/api/mobility/planner/sessions/${sessionId}/photos/?${query}&index=0`;
            queue = queue.then(() => Alfred.fetchJSON(url))
                .then(data => data.busy ? wait(3000).then(() => Alfred.fetchJSON(url)) : data)
                .then(data => cache.set(id, data.status === "ready" && /^data:image\/(jpeg|png|webp|gif);base64,[A-Za-z0-9+\/=]+$/.test(data.image || "")
                    ? {status: "ready", image: data.image, credit: (data.authors || []).map(a => window.TravelResearchPanels.link(a.url, a.name)).join(" · ") || "Google Maps"}
                    : {status: "none"}))
                .catch(() => cache.set(id, {status: "none"}))
                .finally(() => arrived(id, place.name));
        }
        return html(id, place.name);
    }
    return {markup};
})();
