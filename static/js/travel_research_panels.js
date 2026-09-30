/* Research presentation stays separate from the persisted conversation controller. */
window.TravelResearchPanels = (() => {
    const esc = v => Alfred.escapeHtml(String(v ?? ""));
    const money = (v, currency="INR") => v == null ? "Not available" : `${esc(currency)} ${esc(Number(v).toLocaleString(undefined,{maximumFractionDigits:2}))}`;
    const stamp = v => v ? new Date(v).toLocaleString() : "Not checked";
    const label = r => r?.freshness || "UNKNOWN";
    let session, selectedName, map, layers, mapGeometry, mapEnabled = false;
    const $ = id => document.getElementById(id);
    function link(url, title) {
        try {
            const u = new URL(url);
            if (u.protocol === "https:" && !u.username && !u.password && (!u.port || u.port === "443"))
                return `<a href="${esc(u.href)}" target="_blank" rel="noopener noreferrer">${esc(title)}</a>`;
        } catch (_) { /* Unknown/unsafe URL stays plain text. */ }
        return esc(title);
    }
    function badge(r) { return `<span class="travel-freshness">${esc(label(r))}</span>`; }
    function provenance(r) {
        return `<p class="small">${badge(r)} ${link(r?.source_url,r?.provider || "Source unavailable")} · checked ${esc(stamp(r?.retrieved_at))}${r?.expires_at ? ` · expires ${esc(stamp(r.expires_at))}` : ""}</p>${r?.error ? `<p class="small travel-unknown">${esc(r.error.replaceAll("_"," "))}</p>` : ""}${r?.attribution ? `<p class="small">${esc(r.attribution)}</p>` : ""}`;
    }
    function selected() {
        const options = session?.candidates || [];
        return options.find(d=>d.name === selectedName) || (session?.itinerary?.days?.length ? session.itinerary : options[0]);
    }
    function searchLinks(d, categories) {
        return `<ul class="travel-external-links">${(d.external_links || []).filter(l=>categories.includes(l.category)).map(l=>`<li>${link(l.url,l.label)} <small>${l.kind === "reference" ? "Static reference — verify current details with the source." : "Search link — open to check latest availability."}</small></li>`).join("")}</ul>`;
    }
    function weather(d) {
        const r = d.weather_result || {};
        const days = r.payload?.days || [];
        return `<h3 class="h5">Weather for your dates</h3>${provenance(r)}<p>${esc(d.weather?.summary)}</p>${days.length ? `<div class="travel-comparison"><table class="table"><caption>Provider forecast, not a guarantee or official severe-weather warning.</caption><thead><tr><th>Date</th><th>Temperature</th><th>Rain</th><th>Wind</th><th>Daylight</th></tr></thead><tbody>${days.map(x=>`<tr><td>${esc(x.date)}</td><td>${esc(x.min_temp_c)}–${esc(x.max_temp_c)} °C</td><td>${esc(x.rain_mm)} mm</td><td>${esc(x.wind_kmh)} km/h</td><td>${esc(x.sunrise)} / ${esc(x.sunset)}</td></tr>`).join("")}</tbody></table></div>` : ""}${(d.weather_proposals || []).map(p=>`<p>${esc(p.date)}: ${esc(p.reason)}</p>`).join("")}${d.weather_proposals?.length ? '<button class="btn btn-sm btn-outline-primary" data-planner-message="Apply weather alternatives">Apply proposed weather changes</button>' : ""}`;
    }
    function stays(d) {
        const r = d.hotels_result || {};
        const options = (r.payload?.options || []).slice().sort((a,b)=>Number(a.total_price)-Number(b.total_price));
        const picks = options.length <= 3 ? options : [options[0],options[Math.floor(options.length/2)],options.at(-1)];
        return `<h3 class="h5">Stays · compare and open externally</h3>${provenance(r)}<p class="small">Search results require a fresh availability check on the provider. No room is reserved. Prices may exclude property charges.</p><div class="travel-research-cards">${picks.map((o,i)=>`<article><h4 class="h6">${esc(o.name)}</h4><p>${picks.length === 3 ? ["Lower listed price","Middle listed price","Higher listed price"][i] : "Search result"} · ${money(o.total_price,o.currency)} total</p><p>${money(o.nightly_rate,o.currency)} per night · ${esc(o.check_in)} to ${esc(o.check_out)}</p><p>${esc(o.availability)} · rating ${esc(o.review_score ?? o.rating ?? "unknown")}</p><p>Parking: ${esc(o.parking)} · Cancellation: ${esc(o.cancellation_policy)}</p><p>${link(o.booking_url || `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(o.name+" "+(d.name || d.destination))}`,"Open stay search")}</p></article>`).join("")}</div>${!picks.length ? '<p>Live stay pricing/availability could not be retrieved. These links open searches for you to check.</p>' : ""}${searchLinks(d,["hotels"])}`;
    }
    function transport(d) {
        return `<h3 class="h5">Train, bus and flight research</h3>${["trains","buses","flights"].map(kind=>{
            const r = d[kind+"_result"] || {};
            return `<details><summary>${esc(kind[0].toUpperCase()+kind.slice(1))} · ${esc(label(r))}</summary>${provenance(r)}${(r.payload?.options || []).slice(0,4).map(o=>`<article><strong>${esc(o.carrier || o.provider)} · ${esc(o.origin)} → ${esc(o.destination)}</strong><p>${esc(o.departure || "Time unknown")} – ${esc(o.arrival || "Time unknown")} · ${esc(o.duration || "Duration unknown")} · ${esc(o.transfers ?? "Unknown")} transfers</p><p>${money(o.fare,o.currency)} · ${esc(o.availability)}</p>${o.fare_scope ? `<p>${esc(o.fare_scope)}</p>` : ""}${link(o.booking_url,"Open operator")}</article>`).join("") || '<p>Current availability could not be verified. Check the operator externally.</p>'}${searchLinks(d,[kind])}</details>`;
        }).join("")}${(d.mode_comparison || []).length ? `<h4 class="h6 mt-3">Mode comparison · ESTIMATED budgets</h4><ul>${d.mode_comparison.map(m=>`<li>${esc(m.mode)}: ${money(m.budget.expected)} expected · ${esc(m.availability)}</li>`).join("")}</ul>` : ""}`;
    }
    function sources(d) {
        const r = d.permit_result || {}, p = r.payload || {};
        const research = d.web_research || [];
        return `<h3 class="h5">Permits, access and source evidence</h3>${provenance(r)}<p><strong>${esc(p.place || d.name || d.destination)}</strong>: ${esc(p.requirement || "Requirement unverified")}</p><p>Authority: ${esc(p.authority || "Unknown")} · Current access: ${esc(p.opening_status || "UNKNOWN")}</p><p>${esc(p.recheck || "Recheck entry rules, quotas and closures directly with the authority before departure.")}</p>${searchLinks(d,["permits","closures"])}${research.map(result=>`<details><summary>Research leads: ${esc(result.payload?.query || "Search unavailable")}</summary>${provenance(result)}<p>${esc(result.payload?.coverage)}</p>${(result.payload?.findings || []).map(f=>`<article class="travel-source">${link(f.source_url,f.title)}<br><small>${esc(f.source_type)} · UNVERIFIED LEAD</small><p>${esc(f.snippet)}</p></article>`).join("")}</details>`).join("")}<p class="small">Finding an official page in search does not verify a rule. Snippets are leads; current fees, restrictions and opening may still be unknown.</p>`;
    }
    function quality(d) {
        const q = d.quality || {};
        return `<h3 class="h5">What you can rely on</h3><p><strong>Provider results available:</strong> ${esc((q.verified || []).join(", ") || "None verified for this request")}</p><p><strong>Estimated:</strong> ${esc((q.estimated || ["budget","fallback route"]).join(", "))}</p><p><strong>Unavailable / unverified:</strong> ${esc((q.unavailable || []).map(x=>x.category).join(", ") || "See individual sources")}</p><p><strong>Before departure:</strong> ${esc((q.recheck || []).join("; "))}</p><p class="small">Saved research keeps its original check time. CACHED entries may be stale. Source freshness does not guarantee road safety, access or inventory.</p>`;
    }
    function costs(d) {
        return `<h3 class="h5">Budget formulas · ESTIMATED</h3>${d.budget?.recheck_note ? `<p>${esc(d.budget.recheck_note)}</p>` : ""}<ul>${(d.budget?.line_items || []).map(x=>`<li><strong>${esc(x.category)}: ${money(x.expected)}</strong><br>${esc(x.formula)} · inputs ${esc(x.input_freshness)}</li>`).join("")}</ul>`;
    }
    function places(d) {
        const r = d.places_result || {};
        return `<h3 class="h5">Places and useful stops</h3>${provenance(r)}${(r.payload?.places || []).slice(0,12).map(p=>`<article class="travel-source"><strong>${link(p.source_url,p.name)}</strong> · ${esc(p.category)}<p>${esc((p.reasons || []).join("; "))}</p><p class="small">${esc(p.opening_status || "UNKNOWN")} opening/access · popularity unverified</p></article>`).join("") || '<p>No current place results. Use the destination and map searches to investigate locally.</p>'}${searchLinks(d,["map","routing"])}`;
    }
    function render(nextSession) {
        if (session?.id !== nextSession.id) selectedName = null;
        session = nextSession;
        const d = selected();
        $("plannerEvidence").hidden = !d;
        if (!d) return;
        Alfred.setHTMLIfChanged("plannerResearchChoices", (session.candidates || []).map(x=>`<button class="btn btn-sm btn-outline-primary" data-research-destination="${esc(x.name)}" aria-pressed="${(d.name || d.destination)===x.name}">${esc(x.name)}</button>`).join(""));
        $("plannerEvidenceTitle").textContent = `Research for ${d.name || d.destination}`;
        Alfred.setHTMLIfChanged("plannerEvidenceBody", [quality(d),weather(d),stays(d),transport(d),sources(d),places(d),costs(d)].map(html=>`<section class="surface-card">${html}</section>`).join(""));
        $("plannerQuota").hidden = !session.can_view_provider_usage;
        renderMap(d);
    }
    function renderMap(d) {
        if (!mapEnabled || !window.L) return;
        $("plannerMap").hidden = false;
        if (!map) {
            map = L.map("plannerMap").setView([20,78],5);
            const tile = session.map_config?.tile_url;
            if (tile && tile.startsWith("https://")) {
                L.tileLayer(tile,{maxZoom:18,attribution:link(session.map_config.attribution_url,session.map_config.attribution)}).addTo(map)
                  .on("tileerror",()=>{$("plannerMapStatus").textContent="Map tiles unavailable. Saved route/place geometry is still shown where available.";});
            }
        }
        const geometry = JSON.stringify(d.map || {type:"FeatureCollection",features:[]});
        // Polling and itinerary edits should preserve the user's map position.
        if (geometry === mapGeometry) { map.invalidateSize(); return; }
        if (layers) map.removeLayer(layers);
        try {
            layers = L.geoJSON(d.map || {type:"FeatureCollection",features:[]},{
                style:f=>({color:f.properties?.freshness === "CACHED" ? "#946335" : "#206c65",weight:4}),
                pointToLayer:(f,latlng)=>L.circleMarker(latlng,{radius:7,color:"#206c65",fillOpacity:.8}),
                onEachFeature:(f,layer)=>layer.bindPopup(`<strong>${esc(f.properties?.name)}</strong><br>${esc(f.properties?.kind)} · ${esc(f.properties?.freshness || "UNKNOWN")}<br>${link(f.properties?.source_url,"Source")}`)
            }).addTo(map);
            if (layers.getBounds().isValid()) map.fitBounds(layers.getBounds(),{padding:[25,25],maxZoom:12,animate:false});
            map.invalidateSize();
            mapGeometry = geometry;
            $("plannerMapStatus").textContent = !layers.getBounds().isValid()
                ? "No saved coordinates or route geometry are available. Use the external map links."
                : session.map_config?.tile_url ? "Available routes and places shown. Check each source and its freshness."
                : "Map tiles are disabled. Available route and place geometry is shown without a background map.";
        } catch (_) { $("plannerMapStatus").textContent="Some map geometry could not be displayed. Use the external route links."; }
    }
    document.addEventListener("DOMContentLoaded",()=>{
        $("plannerEvidence")?.addEventListener("click",async e=>{
            const choice = e.target.closest("[data-research-destination]");
            if (choice) { selectedName=choice.dataset.researchDestination; render(session); }
            if (e.target.id === "plannerLoadMap") { mapEnabled=true; renderMap(selected()); e.target.hidden=true; }
            if (e.target.id === "plannerLoadQuota") {
                try {
                    const data = await Alfred.fetchJSON("/api/mobility/planner/providers/");
                    Alfred.setHTMLIfChanged("plannerQuotaBody",`<ul>${data.usage.map(r=>`<li>${esc(r.provider)}: ${r.calls_today} calls today · ${Math.round(r.cache_hit_ratio*100)}% cache hits · ${r.failures} failures · ${Math.round(r.average_latency_ms || 0)} ms average · remaining quota ${esc(r.quota_remaining ?? "not exposed")}</li>`).join("")}</ul><ul>${data.configuration.map(p=>`<li>${esc(p.provider)} · ${esc(p.category)}: ${esc(p.unavailable_reason?.replaceAll("_"," ") || "configured; live acceptance still required")}</li>`).join("")}</ul>`);
                } catch (err) { $("plannerQuotaBody").textContent=err.message; }
            }
        });
    });
    return {render,link};
})();
