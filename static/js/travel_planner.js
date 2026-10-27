/* Persisted chat UI. All dynamic text is escaped; evidence links are HTTPS only. */
window.TravelPlanner = (() => {
    const api = "/api/mobility/planner/";
    const $ = id => document.getElementById(id);
    const esc = value => Alfred.escapeHtml(String(value ?? ""));
    const money = value => Alfred.formatCurrency(value || 0);
    const state = {session: null, busy: false, timer: null, comparison: false, plans: []};
    let documentEpoch=0, documentActive=true, documentRefreshPending=false;
    function clearDocuments() {
        documentEpoch++; documentActive=false;
        if (state.session) {state.session.trip_documents=[];delete state.session.document_choices;}
        const panel=$('plannerDocuments'); if(panel){panel.replaceChildren();panel.hidden=true;}
    }
    async function fetchPlanner(url,options) {
        const epoch=documentEpoch;
        try {
            const data=await Alfred.fetchJSON(url,options);
            if (data?.trip_documents && (!documentActive || epoch!==documentEpoch)) {
                data.trip_documents=[];delete data.document_choices;
            }
            return data;
        } catch(error) {
            if ([401,403].includes(error.status)) clearDocuments();
            throw error;
        }
    }
    async function refreshDocumentContext() {
        if (state.busy) {documentRefreshPending=true;return;}
        documentRefreshPending=false;
        documentEpoch++;documentActive=true;
        const epoch=documentEpoch;
        if (!state.session) return;
        const identity=state.session.id;
        try {
            const next=await fetchPlanner(api+`sessions/${identity}/`);
            if (documentActive && epoch===documentEpoch && state.session?.id===identity && next.id===identity && next.revision>=state.session.revision) {state.session=next;render();}
        } catch(error) {clearDocuments();alert(error.message);}
    }
    const field = key => state.session?.state?.[key]?.value;
    function syncActionState() {
        document.querySelectorAll('#plannerSend, #plannerNew, #plannerVehicle, #plannerChips button, [data-planner-message], [data-reject], [data-route-choice], [data-restriction-fields], [data-restriction-withdraw], [data-add-stop], [data-stop-index], #plannerCompareOrder, #plannerApplyOrder, #plannerDraft, #plannerSave, #plannerRecheck, #plannerPlans button, #plannerSessions button, [data-editor-control], #plannerDocuments button')
            .forEach(control => { control.disabled = state.busy || control.dataset.batchUnavailable === "true"; });
    }
    function alert(message) { $("plannerAlert").textContent = message; $("plannerAlert").hidden = !message; }
    function link(url, title) {
        return window.TravelResearchPanels.link(url,title);
    }
    function sourceMarkup(sources) {
        return (sources || []).map(s => `<div class="travel-source"><strong>${esc(s.data_type)} · ${esc(s.confidence)}${s.freshness === "stale" ? " · STALE" : ""}</strong><div>${esc(s.finding?.summary || s.finding?.assumptions?.join(" ") || "Planning allowance")}</div><div>${link(s.source_url, s.source_name)} · ${s.retrieved_at ? `Checked ${esc(new Date(s.retrieved_at).toLocaleString())}` : "Not live-verified"}</div>${(s.finding?.reports || []).map(r=>`<p>${link(r.link,r.title)}<br>${esc(r.source)} · ${esc(r.published)}</p>`).join("")}</div>`).join("") || "No live evidence yet. Research is pending.";
    }
    async function list() {
        const data = await fetchPlanner(api+"sessions/");
        state.plans = data.plans;
        Alfred.setHTMLIfChanged("plannerPlans", data.plans.map(p=>`<button class="btn btn-sm btn-outline-primary" data-open-plan="${p.id}"><span class="travel-saved-status">${esc(p.status_label)}</span><strong class="d-block">${esc(p.title)}</strong><span class="small">${money(p.budget)} · ${p.duration_days || "Flexible"} days</span></button>`).join("") || '<p class="small">Save a draft whenever you like. No destination required.</p>');
        Alfred.setHTMLIfChanged("plannerSessions", data.sessions.map(s => `<button class="btn btn-sm btn-outline-primary" data-session="${s.id}">${esc(s.title)}<span class="d-block small">${esc(s.status.replaceAll("_", " "))}</span></button>`).join("") || "No conversations yet.");
        syncActionState();
        return data;
    }
    async function open(id) {
        if (state.busy) return false;
        const epoch=++documentEpoch;documentActive=true;
        clearTimeout(state.timer);
        const next = await fetchPlanner(api+`sessions/${id}/`);
        if (!documentActive || epoch!==documentEpoch) return false;
        state.session = next;
        history.replaceState(null, "", `?session=${state.session.id}`);
        state.comparison = false;
        render();
        return true;
    }
    async function create(planId) {
        if (state.busy) return;
        const epoch=++documentEpoch;documentActive=true;
        const data = await fetchPlanner(api+"sessions/", {method:"POST", body:JSON.stringify(planId ? {plan_id: planId} : {})});
        if (!documentActive || epoch!==documentEpoch) return;
        state.session = data;
        history.replaceState(null, "", `?session=${data.id}`);
        state.comparison = false;
        render();
        await list();
    }
    async function action(payload) {
        if (state.busy || !state.session) return;
        documentEpoch++;
        const identity=state.session.id;
        let accepted=false;
        if (payload.action === 'save') payload = {...payload,revision:state.session.revision};
        state.busy = true;
        syncActionState();
        alert("");
        try {
            const next = await fetchPlanner(api+`sessions/${identity}/`, {method:"POST", body:JSON.stringify(payload)});
            if (state.session?.id!==identity || next.id!==identity) return false;
            accepted=true;
            if (next.revision>=state.session.revision) state.session = next;
            render();
            await list();
            if (state.session?.id!==identity) return accepted;
            if (state.session.plan_id) populateDetails(state.session.plan_id);
            if (payload.action === "save") {
                await loadMobilityDashboard();
                alert(payload.draft ? "Draft saved." : "Travel Plan saved. Open it from Your Plans below.");
            }
            return true;
        } catch (err) { alert(err.message); return accepted; }
        finally { state.busy = false; syncActionState(); schedulePoll(); if(documentRefreshPending && !document.hidden)refreshDocumentContext(); }
    }
    async function message(text) {
        const accepted = await action({action:"message", text});
        if (accepted) {
            if ($("plannerInput").value.trim() === String(text).trim()) $("plannerInput").value = "";
            if (/compare/i.test(text)) { state.comparison = true; comparison(); }
        }
    }
    function schedulePoll() {
        clearTimeout(state.timer);
        if (state.session?.research && !["ready", "failed", "superseded"].includes(state.session.research.status)) {
            state.timer = setTimeout(async () => {
                if (state.busy || document.hidden) { schedulePoll(); return; }
                const identity=state.session.id, epoch=documentEpoch;
                try { const next=await fetchPlanner(api+`sessions/${identity}/`);
                    if(epoch===documentEpoch && state.session?.id===identity && next.id===identity && next.revision>=state.session.revision){state.session=next;render();} }
                catch (err) { alert(`Progress could not refresh: ${err.message}. Your request is saved.`); schedulePoll(); }
            }, 2500);
        }
    }
    function render() {
        const session = state.session;
        $("plannerTitle").textContent = session.title;
        const messages = $("plannerMessages");
        const oldLast = messages.dataset.last;
        const last = session.messages.at(-1);
        Alfred.setHTMLIfChanged(messages, session.messages.map(m => `<article class="travel-message ${m.role === "user" ? "user" : "assistant"}" data-message-id="${m.id}"><strong>${m.role === "user" ? "You" : "Alfred"}</strong>${esc(m.text)}</article>`).join(""));
        if (oldLast !== String(last?.id)) { messages.scrollTop = messages.scrollHeight; messages.dataset.last = last?.id || ""; }
        Alfred.setHTMLIfChanged("plannerChips", (last?.chips || []).map(c => `<button type="button" data-planner-message="${esc(c)}">${esc(c)}</button>`).join(""));
        const labels = {origin:"Starting from", trip_duration:"Days available", budget:"Target budget", budget_type:"Budget style", selected_destination:"Your choice", transport_mode:"Travel mode", available_start_date:"Start", available_end_date:"Return"};
        Alfred.setHTMLIfChanged("plannerContext", Object.entries(labels).filter(([k]) => field(k)).map(([k,l]) => `<strong>${l}</strong>${esc(k === "budget" ? money(field(k)) : field(k))}${session.state[k].confirmed_by_user ? "" : " · please confirm"}`).join("") || "Start with an idea. We'll fill in the details together.");
        Alfred.setHTMLIfChanged("plannerProvenance", Object.entries(session.state).filter(([k]) => k !== "pending_question").map(([k,v]) => `<div class="travel-fact"><strong>${esc(k.replaceAll("_", " "))}</strong>: ${esc(Array.isArray(v.value) ? v.value.join(", ") : v.value)}<br>${esc(v.source)} · ${v.confirmed_by_user ? "Confirmed by you" : "Unconfirmed"} · confidence ${esc(v.confidence)}</div>`).join(""));
        const r = session.research;
        $("plannerResearch").textContent = r ? `${r.stage} · ${r.sources_checked} source checks. ${r.completed_at ? `Updated ${Math.max(0,Math.floor((Date.now()-new Date(r.completed_at))/60000))} minutes ago. ` : ""}${r.error || r.summary || "You can leave this page and return later."}` : "Discovery starts with your idea. Research begins when we have enough context.";
        $("plannerSave").hidden = !session.itinerary?.days?.length;
        $("plannerRecheck").hidden = !session.candidates?.length;
        $("plannerResults").hidden = !session.candidates.length;
        candidates(); comparison(); itinerary(); stops(); documents();
        window.TravelResearchPanels.render(session);
        if (session.plan_id) populateDetails(session.plan_id);
        else $("planDetails").hidden = true;
        if (field("vehicle_profile")) $("plannerVehicle").value = String(field("vehicle_profile"));
        syncActionState();
        schedulePoll();
    }
    function restrictionMarkup(d, route, index, current) {
        const proof = d.motorcycle_restrictions?.[route.route_id] || {status:route.route_id ? "UNKNOWN" : "UNAVAILABLE",evidence:[]};
        const researching = state.session.research && !["ready","failed","superseded"].includes(state.session.research.status);
        const unavailable = !route.route_id || !current || researching || field("transport_mode") !== "ride";
        return `<div class="travel-restriction" data-restriction-route="${esc(route.route_id)}"><p><strong>Restriction reference: ${esc(proof.status)}${proof.status === "VERIFIED" ? " (your reviewed reference)" : ""}</strong>${proof.restriction ? ` · ${esc(proof.restriction)}` : ""}</p><p class="small">${esc(proof.note || "No route-bound reviewed restriction is established. Motorcycle legality remains UNKNOWN.")}</p>${proof.conflicting ? '<p class="alert alert-warning">Reviewed references conflict. No current restriction conclusion is established; review or withdraw incorrect references.</p>' : ''}${(proof.evidence || []).map(e=>`<article class="travel-source"><strong>${esc(e.road)} · ${esc(e.status)}${e.withdrawn ? " · withdrawn" : ""}</strong><blockquote>${esc(e.quote)}</blockquote>${link(e.source_url,"Public reference")}<p class="small">Checked ${esc(e.checked_at)} · Expires ${esc(e.expires_at)}. Quoted restriction: ${esc(e.restriction)}; stale/withdrawn text is historical evidence.</p>${!e.withdrawn ? `<button type="button" class="btn btn-sm btn-outline-secondary" data-restriction-withdraw="${e.id}">Withdraw this review</button>` : ''}</article>`).join("")}<details><summary>Record a reviewed public restriction</summary><form data-restriction-form data-route-id="${esc(route.route_id)}" data-candidate-index="${index}"><fieldset data-restriction-fields data-batch-unavailable="${unavailable}"><legend class="h6">Your public-source review, not legal clearance</legend><p class="small">Indian government .gov.in/.nic.in references only. No page is fetched or authenticated automatically. Quote a prohibition or conditional rule, never permission for the whole route. Check/expiry must be current and at most 24 hours apart.</p><label class="d-block">Road or segment <input class="form-control" name="road" maxlength="160" required></label><label class="d-block">Restriction <select class="form-select" name="restriction"><option value="PROHIBITED">Motorcycles prohibited</option><option value="CONDITIONAL">Conditional motorcycle access</option></select></label><label class="d-block">Public government reference URL <input class="form-control" type="url" name="source_url" maxlength="1000" required></label><label class="d-block">Exact supporting quotation <textarea class="form-control" name="quote" maxlength="1200" required></textarea></label><label class="d-block">Checked at (your local time) <input class="form-control" type="datetime-local" name="checked_at" required></label><label class="d-block">Review expires (your local time) <input class="form-control" type="datetime-local" name="expires_at" required></label><label class="d-block my-2"><input type="checkbox" name="reviewed" required> I reviewed this public source and confirmed the quoted rule applies to this exact displayed route, dates and motorcycle mode.</label><button class="btn btn-sm btn-outline-primary" type="submit">Save reviewed restriction</button></fieldset></form>${unavailable ? '<p>Choose motorcycle mode and finish/recheck current route research before recording a reference.</p>' : ''}</details></div>`;
    }
    function routeChoices(d, index) {
        const result = d.route_result || {}, routes = result.payload?.routes || [];
        const current = result.success && !result.stale && Date.parse(result.retrieved_at) <= Date.now() && Date.now() < Date.parse(result.expires_at);
        if (!routes.length) return '<p class="small">Restriction reference: UNAVAILABLE. No current route identity is available; motorcycle legality remains UNKNOWN.</p>';
        return `<details class="mt-2 travel-route-choices"><summary>Compare provider routes</summary><p>${esc(d.route_alternatives_note || "A single provider geometry is available; alternatives are not established.")}</p><p class="small">${esc(result.provider)} · ${esc(result.freshness)} · checked ${esc(result.retrieved_at || "unknown")}. Motorcycle legality, closures, traffic and scenic quality are unverified. Choosing a route rebuilds this destination's draft days and budget allowances; save explicitly afterwards.</p>${routes.map((r, i)=>`<div class="mb-2"><strong>Route ${i+1}</strong>: ${esc(r.distance_km)} km · ${esc(r.duration_hours)} hours (model estimate) ${r.route_id && r.route_id === d.selected_route_id ? '<span class="badge text-bg-secondary">Selected</span>' : ''}${r.route_id ? `<button type="button" class="btn btn-sm btn-outline-primary ms-2" data-route-choice="${esc(r.route_id)}" data-route-candidate="${index}" data-batch-unavailable="${!current || (state.session.itinerary_stops || []).length > 1 || r.route_id === d.selected_route_id}">Use route ${i+1} and rebuild draft</button>` : ''}${restrictionMarkup(d,r,index,current)}</div>`).join("")}${!current ? '<p>Cached or unavailable route: Recheck Trip before choosing.</p>' : ''}${(state.session.itinerary_stops || []).length > 1 ? '<p>Home-to-destination routes do not establish ordered inter-stop legs; selection is unavailable for multi-stop drafts.</p>' : ''}</details>`;
    }
    function candidates() {
        const pool = state.session.destination_pool;
        const pending = state.session.research && !["ready", "failed", "superseded"].includes(state.session.research.status);
        Alfred.setHTMLIfChanged("plannerCandidatePages", pool?.total && (!field("selected_destination") || state.session.itinerary_stops?.length) ?
            `<p>Showing ${pool.offset+1}–${pool.offset+state.session.candidates.length} of ${pool.total} ranked candidates (at most 20). Research runs three at a time; source freshness and unknown availability remain separate.</p>`+
            `<div class="travel-actions"><button id="plannerPreviousCandidates" type="button" class="btn btn-outline-primary" data-planner-message="Previous destinations" data-batch-unavailable="${!pool.has_previous || pending}">Previous destinations</button>`+
            `<button id="plannerMoreCandidates" type="button" class="btn btn-outline-primary" data-planner-message="Show more destinations" data-batch-unavailable="${!pool.has_more || pending}">Show more destinations</button></div>` : "");
        Alfred.setHTMLIfChanged("plannerCandidates", state.session.candidates.map((d,i) => `<article class="travel-candidate" data-destination="${esc(d.name)}"><header><span class="travel-fit">Option ${i+1} / ${esc(d.fit)}</span><h3 class="mt-2 mb-0">${esc(d.name)}</h3><p class="small mt-2 mb-0">${esc(d.styles.slice(0,3).join(" · "))}</p></header><div class="travel-candidate-body"><dl><dt>Expected trip budget</dt><dd>${money(d.budget.expected)} · range ${money(d.budget.minimum)}–${money(d.budget.comfortable)}</dd><dt>Travel from ${esc(field("origin"))}</dt><dd>${d.distance_km ? `~${esc(d.distance_km)} km / ~${esc(d.travel_hours)} hours one way` : "Distance and travel time unverified"}<br><small>Estimate · includes no live traffic</small></dd><dt>Weather</dt><dd>${esc(d.weather.summary)}</dd></dl><strong>Why it fits</strong><ul>${d.why.map(w=>`<li>${esc(w)}</li>`).join("")}</ul><strong>Watch out</strong><p class="small">${esc(d.issues.join(" "))}</p><div class="travel-actions"><button type="button" class="btn btn-primary btn-sm" data-planner-message="Choose ${esc(d.name)}">Choose ${esc(d.name)}</button><button type="button" class="btn btn-outline-secondary btn-sm" data-reject="${esc(d.name)}">Not this time</button></div>${routeChoices(d,i)}<details class="mt-3"><summary>Details · Why this recommendation?</summary><div class="small mt-2">${Object.entries(d.factors).map(([k,v])=>`<p><strong>${esc(k)}</strong>: ${esc(v)}</p>`).join("")}<p>Ranking uses budget, travel time, your stated preferences and recorded visits. Fit labels are guidance, not probabilities.</p></div></details><details class="mt-2"><summary>Sources</summary>${sourceMarkup(d.sources)}</details></div></article>`).join(""));
    }
    function stops() {
        const names = state.session.itinerary_stops || [];
        const supported = ["ride", "roadtrip"].includes(field("transport_mode"));
        const proposal = state.session.stop_order_proposal;
        Alfred.setHTMLIfChanged("plannerStops", `<h2 class="h5">Ordered stops</h2><p class="small">Add up to five destinations shown in this conversation for your own motorcycle or car. Allow at least one night per stop plus a return day. Earlier/Later and dragging preserve activities and nights. Adding/removing stops or applying an optimized order rebuilds the draft. Routes, permits and stays need separate verification.</p>`+
            `<ol>${names.map((name,i)=>`<li class="mb-2" data-editor-stop="${esc(state.session.itinerary_editor.stops[i]?.id || '')}" draggable="${names.length>1}"><strong>${esc(name)}</strong><div class="travel-actions"><button type="button" class="btn btn-sm btn-outline-secondary" data-stop-index="${i}" data-stop-move="-1" data-batch-unavailable="${i===0}" aria-label="Move ${esc(name)} earlier">Earlier</button><button type="button" class="btn btn-sm btn-outline-secondary" data-stop-index="${i}" data-stop-move="1" data-batch-unavailable="${i===names.length-1}" aria-label="Move ${esc(name)} later">Later</button><button type="button" class="btn btn-sm btn-outline-secondary" data-stop-index="${i}" data-stop-remove="true" aria-label="Remove ${esc(name)}">Remove</button></div></li>`).join("")}</ol>`+
            (names.length >= 3 ? '<button type="button" id="plannerCompareOrder" class="btn btn-sm btn-outline-primary mb-3">Compare estimated stop order</button>' : '')+
            (proposal ? `<div id="plannerOrderProposal" class="alert alert-info"><p>Current order: ~${esc(proposal.current_distance_km)} km. Suggested order: ~${esc(proposal.suggested_distance_km)} km.</p><p>${esc(proposal.stops.join(" \u2192 "))}</p><p>${esc(proposal.basis)}</p>${proposal.changed ? '<button type="button" id="plannerApplyOrder" class="btn btn-primary btn-sm">Apply order and rebuild draft</button>' : '<p>Your current order already has the shortest estimated distance; no change was made.</p>'}</div>` : '')+
            (supported ? `<div class="travel-actions">${state.session.candidates.map(d=>`<button type="button" class="btn btn-sm btn-outline-primary" data-add-stop="${esc(d.name)}" data-batch-unavailable="${names.includes(d.name) || names.length===5}">Add ${esc(d.name)} as stop</button>`).join("")}</div>` : `<p>Choose motorcycle or car travel to build a multi-stop draft.</p>`));
    }
    function comparison() {
        $("plannerComparison").hidden = !state.comparison;
        if (!state.comparison) return;
        const options = state.session.candidates;
        const rows = [["Expected budget",d=>money(d.budget.expected)],["One-way distance",d=>d.distance_km ? `~${d.distance_km} km (estimate)` : "Unknown"],["Weather",d=>d.weather.summary],["Photography",d=>d.factors.Photography],["Crowds",()=>"Unverified"],["Ride difficulty",()=>"Needs route verification"],["Novelty",d=>d.novelty],["Stay availability",()=>"Unverified"]];
        Alfred.setHTMLIfChanged("plannerComparison", `<h3 class="h5">Compare your options</h3><div class="travel-comparison" tabindex="0" role="region" aria-label="Scrollable destination comparison"><table class="table"><caption>Estimates and unknowns are labelled. No live availability guarantee.</caption><thead><tr><th scope="col">Factor</th>${options.map(d=>`<th scope="col">${esc(d.name)}</th>`).join("")}</tr></thead><tbody>${rows.map(([label,fn])=>`<tr><th scope="row">${label}</th>${options.map(d=>`<td>${esc(fn(d))}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`);
    }
    function documents() {
        $('plannerDocuments').hidden=!documentActive;
        if (!documentActive) return;
        const linked=state.session.trip_documents || [], choices=state.session.document_choices;
        Alfred.setHTMLIfChanged('plannerDocuments',`<h2 class="h5">Private trip documents</h2><p>Link an existing private PDF/text copy from <a href="/documents/">Document Center</a>. Originals stay in their current encrypted store and expire under their retention settings. A document link does not confirm a booking or permit.</p><button type="button" class="btn btn-outline-primary" data-trip-document-list>Review available private copies</button><ul class="mt-3">${linked.map(row=>`<li class="mb-2">${row.status==='available'?`<a href="${esc(row.original_path)}" target="_blank" rel="noopener noreferrer">${esc(row.name)}</a> · copy expires ${esc(new Date(row.expires_at).toLocaleString())}`:`<span>${esc(row.name)}</span>`} <button type="button" class="btn btn-sm btn-outline-secondary" data-trip-document-unlink="${esc(row.id)}">Unlink reference</button></li>`).join('') || '<li>No private documents linked to this trip.</li>'}</ul>${choices?`<div role="group" aria-label="Available private documents">${choices.map(row=>`<p>${esc(row.name)} · expires ${esc(new Date(row.expires_at).toLocaleString())} <button type="button" class="btn btn-sm btn-outline-primary" data-trip-document-link="${esc(row.id)}" data-trip-document-fingerprint="${esc(row.fingerprint)}">Link to this trip</button></p>`).join('') || '<p>No current uploaded private copies. Add one in Document Center with explicit consent and retention first.</p>'}</div>`:''}`);
    }
    function itinerary() {
        const it = state.session.itinerary;
        $("plannerItinerary").hidden = !it?.days?.length;
        if (!it?.days?.length) return;
        const b = it.budget;
        const legs = it.stops?.length ? `<details class="surface-card mb-3"><summary>Ordered leg estimates and stop evidence</summary><ul>${(it.route.legs || []).map(l=>`<li>${esc(l.from)} → ${esc(l.to)}: ~${esc(l.distance_km)} km · estimate, not a verified road route</li>`).join("")}</ul>${it.stops.map(s=>`<details><summary>${esc(s.name)} · ${s.nights} night(s) · sources apply only to this stop</summary>${s.date_context_changed ? "<p>Stop dates/order changed. Retained sources are historical leads; recheck weather, prices and access for the revised dates.</p>" : ""}${sourceMarkup(s.sources)}</details>`).join("")}${b.recheck_note ? `<p>${esc(b.recheck_note)}</p>` : ""}</details>` : "";
        Alfred.setHTMLIfChanged("plannerItinerary", `<div class="surface-card mb-3"><p class="metric-kicker">YOUR FLEXIBLE ITINERARY · PRELIMINARY</p><h2>${esc(it.destination)}</h2><p>${esc(it.summary)}</p><p><strong>Route:</strong> ${esc(it.route.summary)}</p><p class="small">${esc(it.route.note)}</p><p>${esc(it.weather.summary)}</p><div class="travel-budget-grid">${["minimum","expected","comfortable"].map(k=>`<div>${b.status === "needs_recalculation" ? "Previous " : ""}${esc(k[0].toUpperCase()+k.slice(1))}<strong>${money(b[k])}</strong></div>`).join("")}</div>${b.over_budget ? `<p class="alert alert-warning">About ${money(b.over_budget)} over target. ${esc(b.adaptations.join(" · "))}</p>` : ""}<details><summary>Budget breakdown and assumptions</summary><table class="table"><tbody>${Object.entries(b.categories).map(([k,v])=>`<tr><th scope="row">${esc(k)}</th><td>${money(v)}</td></tr>`).join("")}</tbody></table><ul>${b.assumptions.map(a=>`<li>${esc(a)}</li>`).join("")}</ul></details></div>${window.TravelItineraryEditor.markup(state.session)}<div class="surface-card mt-3"><details><summary>Packing, vehicle and pre-trip checks</summary><ul>${it.packing.concat(it.checks).map(p=>`<li>${esc(p)}</li>`).join("")}</ul>${it.bike ? `<p>${esc(it.bike.profile)} · ${it.bike.nominal_range_km ? `Nominal profile range ~${esc(it.bike.nominal_range_km)} km` : "Range not available from your profile"}</p><p>${esc(it.bike.range_note)} ${esc(it.bike.notes)}</p>` : ""}<ul>${it.route.options.map(o=>`<li>${esc(o.name)}: ${esc(o.status)}</li>`).join("")}</ul></details><details class="mt-2"><summary>Research sources</summary>${sourceMarkup(it.sources)}</details></div>${legs}`);
    }
    function populateDetails(planId) {
        const plan = state.plans.find(p=>p.id === planId);
        if (!plan) return;
        $("planDetails").hidden = false;
        const form = $("travelPlanForm");
        form.dataset.planId = planId;
        if (form.contains(document.activeElement)) return;
        for (const field of form.elements) if (field.name && plan[field.name] !== undefined) field.value = plan[field.name] ?? "";
    }
    async function postTrip() {
        const [feedback, media] = await Promise.all([fetchPlanner(api+"feedback/"), fetchPlanner(api+"media-suggestions/")]);
        $("plannerPostTrip").hidden = !feedback.due.length && !media.suggestions.length;
        Alfred.setHTMLIfChanged("plannerFeedback", feedback.due.map(p=>`<div class="mb-3"><p>How was ${esc(p.title)}? Feedback is optional.</p><details><summary>What did you like or dislike? (optional)</summary>${["liked","disliked"].map(kind=>`<fieldset class="mt-2"><legend class="h6">${kind === "liked" ? "Enjoyed" : "Could be better"}</legend><div class="travel-chips">${["photography","scenery","ride","food","stay","weather","activities","crowds","roads","distance","cost"].map(tag=>`<label class="small"><input type="checkbox" data-feedback-plan="${p.id}" data-feedback-kind="${kind}" value="${tag}"> ${tag}</label>`).join("")}</div></fieldset>`).join("")}</details><div class="travel-chips">${[["loved","Loved it"],["good","Good"],["okay","Okay"],["disliked","Didn't enjoy it"]].map(([v,l])=>`<button data-rating="${v}" data-plan="${p.id}">${l}</button>`).join("")}</div></div>`).join(""));
        Alfred.setHTMLIfChanged("plannerMedia", media.suggestions.map(s=>`<div class="mb-3"><p>Photo near ${esc(s.location)} matches ${esc(s.plan_title)}. ${esc(s.reason)}</p><details><summary>Review photo</summary><img class="travel-media-preview" src="${esc(s.photo_url)}" alt="${esc(s.caption || 'Trip photo')}"></details><button class="btn btn-sm btn-primary" data-media="add" data-photo="${s.photo_id}" data-plan="${s.plan_id}">Add to trip</button> <button class="btn btn-sm btn-outline-secondary" data-media="ignore" data-photo="${s.photo_id}" data-plan="${s.plan_id}">Ignore</button></div>`).join(""));
    }
    async function init() {
        if (!$("travelPlanner")) return;
        window.TravelItineraryEditor.init(action);
        $("plannerComposer").addEventListener("submit", e=>{e.preventDefault(); message($("plannerInput").value);});
        $("plannerNew").addEventListener("click", ()=>create().catch(e=>alert(e.message)));
        $("plannerDraft").addEventListener("click", ()=>action({action:"save",draft:true}));
        $("plannerSave").addEventListener("click", ()=>action({action:"save"}));
        $("plannerCompare").addEventListener("click", ()=>{state.comparison=!state.comparison;comparison();});
        $("plannerVehicle").addEventListener("change", e=>{if(e.target.value)action({action:"vehicle",vehicle_id:Number(e.target.value)});});
        document.addEventListener("submit", async e=>{
            const form = e.target.closest("[data-restriction-form]");
            if (!form) return;
            e.preventDefault();
            if (state.busy || !form.reportValidity()) return;
            try {
                const data = Object.fromEntries(new FormData(form));
                data.checked_at = new Date(data.checked_at).toISOString();
                data.expires_at = new Date(data.expires_at).toISOString();
                data.reviewed = form.elements.reviewed.checked;
                await action({...data,action:"restriction_review",candidate_index:Number(form.dataset.candidateIndex),route_id:form.dataset.routeId,revision:state.session.revision});
            } catch (_) { alert("Choose valid local check and expiry times. Your draft is preserved."); }
        });
        document.addEventListener("click", async e=>{
            const button = e.target.closest("button");
            if (!button) return;
            try {
                if (button.dataset.plannerMessage) await message(button.dataset.plannerMessage);
                if (button.dataset.session) await open(Number(button.dataset.session));
                if (button.dataset.openPlan) await create(Number(button.dataset.openPlan));
                if (button.dataset.reject) await action({action:"reject",destination:button.dataset.reject});
                if (button.hasAttribute('data-trip-document-list')) await action({action:'trip_documents',operation:'list'});
                if (button.dataset.tripDocumentLink) await action({action:'trip_documents',operation:'link',document_id:button.dataset.tripDocumentLink,fingerprint:button.dataset.tripDocumentFingerprint,revision:state.session.revision});
                if (button.dataset.tripDocumentUnlink) await action({action:'trip_documents',operation:'unlink',document_id:button.dataset.tripDocumentUnlink,revision:state.session.revision});
                if (button.dataset.restrictionWithdraw) await action({action:"restriction_withdraw",evidence_id:Number(button.dataset.restrictionWithdraw),revision:state.session.revision});
                if (button.dataset.routeChoice) await action({action:"route_choice",candidate_index:Number(button.dataset.routeCandidate),route_id:button.dataset.routeChoice,revision:state.session.revision});
                if (button.id === "plannerCompareOrder") await action({action:"itinerary_order_preview",revision:state.session.revision});
                if (button.id === "plannerApplyOrder") await action({action:"itinerary_stops",stops:state.session.stop_order_proposal.stops,revision:state.session.revision});
                if (button.dataset.addStop || button.dataset.stopIndex !== undefined) {
                    const names = [...(state.session.itinerary_stops || [])];
                    if (button.dataset.addStop) names.push(button.dataset.addStop);
                    else {
                        const i = Number(button.dataset.stopIndex);
                        if (button.dataset.stopRemove) names.splice(i, 1);
                        else { const j = i + Number(button.dataset.stopMove); [names[i], names[j]] = [names[j], names[i]]; }
                    }
                    if (button.dataset.stopMove && state.session.itinerary?.days?.length) await window.TravelItineraryEditor.orderStops(names);
                    else await action({action:"itinerary_stops",stops:names,revision:state.session.revision});
                }
                if (button.dataset.rating) {const tags=kind=>Array.from(document.querySelectorAll(`input[data-feedback-plan="${Number(button.dataset.plan)}"][data-feedback-kind="${kind}"]:checked`)).map(e=>e.value);await fetchPlanner(api+"feedback/",{method:"POST",body:JSON.stringify({plan_id:Number(button.dataset.plan),rating:button.dataset.rating,liked:tags("liked"),disliked:tags("disliked")})});await postTrip();}
                if (button.dataset.media) {await fetchPlanner(api+"media-suggestions/",{method:"POST",body:JSON.stringify({plan_id:Number(button.dataset.plan),photo_id:Number(button.dataset.photo),action:button.dataset.media})});await postTrip();await loadMobilityDashboard();}
            } catch(err) { alert(err.message); }
        });
        try {
            const data = await list();
            const id = Number(new URLSearchParams(location.search).get("session")) || data.sessions[0]?.id;
            if (id) await open(id); else await create();
            const [profiles,prefs] = await Promise.all([fetchPlanner("/api/mobility/bikes/"), fetchPlanner(api+"preferences/")]);
            $("plannerVehicle").innerHTML = '<option value="">Choose when relevant</option>'+(profiles.results || profiles).map(p=>`<option value="${p.id}">${esc(p.display_name)}</option>`).join("");
            if (field("vehicle_profile")) $("plannerVehicle").value=field("vehicle_profile");
            $("plannerStyle").innerHTML=Object.entries(prefs.preferences).filter(([,v])=>v.value === true).slice(0,6).map(([k])=>`<span class="badge text-bg-light">${esc(k)}</span>`).join("") || '<span class="small">Your style grows with choices and feedback.</span>';
            await postTrip();
        } catch(err) { alert(err.message); }
    }
    document.addEventListener("DOMContentLoaded", init);
    addEventListener('pagehide',clearDocuments);
    addEventListener('pageshow',event=>{if(event.persisted)refreshDocumentContext();});
    document.addEventListener('visibilitychange',()=>{if(document.hidden)clearDocuments();else if(!documentActive)refreshDocumentContext();});
    return {openPlan:async id=>{await create(id);$("travelPlanner").scrollIntoView({behavior:"smooth"});},message,refreshPostTrip:postTrip,
        reload:async()=>{try {return await open(state.session.id);} catch(err){alert(err.message);return false;}}};
})();
