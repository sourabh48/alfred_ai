/* Persisted chat UI. All dynamic text is escaped; evidence links are HTTPS only. */
window.TravelPlanner = (() => {
    const api = "/api/mobility/planner/";
    const $ = id => document.getElementById(id);
    const esc = value => Alfred.escapeHtml(String(value ?? ""));
    const money = value => Alfred.formatCurrency(value || 0);
    const state = {session: null, busy: false, timer: null, comparison: false, plans: []};
    const field = key => state.session?.state?.[key]?.value;
    function alert(message) { $("plannerAlert").textContent = message; $("plannerAlert").hidden = !message; }
    function link(url, title) {
        try { if (new URL(url).protocol === "https:") return `<a href="${esc(url)}" target="_blank" rel="noopener noreferrer">${esc(title)}</a>`; } catch (_) { /* no link */ }
        return esc(title);
    }
    function sourceMarkup(sources) {
        return (sources || []).map(s => `<div class="travel-source"><strong>${esc(s.data_type)} · ${esc(s.confidence)}${s.freshness === "stale" ? " · STALE" : ""}</strong><div>${esc(s.finding?.summary || s.finding?.assumptions?.join(" ") || "Planning allowance")}</div><div>${link(s.source_url, s.source_name)} · ${s.retrieved_at ? `Checked ${esc(new Date(s.retrieved_at).toLocaleString())}` : "Not live-verified"}</div>${(s.finding?.reports || []).map(r=>`<p>${link(r.link,r.title)}<br>${esc(r.source)} · ${esc(r.published)}</p>`).join("")}</div>`).join("") || "No live evidence yet. Research is pending.";
    }
    async function list() {
        const data = await Alfred.fetchJSON(api+"sessions/");
        state.plans = data.plans;
        Alfred.setHTMLIfChanged("plannerPlans", data.plans.map(p=>`<button class="btn btn-sm btn-outline-primary" data-open-plan="${p.id}"><span class="travel-saved-status">${esc(p.status_label)}</span><strong class="d-block">${esc(p.title)}</strong><span class="small">${money(p.budget)} · ${p.duration_days || "Flexible"} days</span></button>`).join("") || '<p class="small">Save a draft whenever you like. No destination required.</p>');
        Alfred.setHTMLIfChanged("plannerSessions", data.sessions.map(s => `<button class="btn btn-sm btn-outline-primary" data-session="${s.id}">${esc(s.title)}<span class="d-block small">${esc(s.status.replaceAll("_", " "))}</span></button>`).join("") || "No conversations yet.");
        return data;
    }
    async function open(id) {
        if (state.busy) return;
        clearTimeout(state.timer);
        state.session = await Alfred.fetchJSON(api+`sessions/${id}/`);
        history.replaceState(null, "", `?session=${state.session.id}`);
        state.comparison = false;
        render();
    }
    async function create(planId) {
        const data = await Alfred.fetchJSON(api+"sessions/", {method:"POST", body:JSON.stringify(planId ? {plan_id: planId} : {})});
        state.session = data;
        history.replaceState(null, "", `?session=${data.id}`);
        state.comparison = false;
        render();
        await list();
    }
    async function action(payload) {
        if (state.busy || !state.session) return;
        state.busy = true;
        $("plannerSend").disabled = true;
        alert("");
        try {
            state.session = await Alfred.fetchJSON(api+`sessions/${state.session.id}/`, {method:"POST", body:JSON.stringify(payload)});
            render();
            await list();
            if (state.session.plan_id) populateDetails(state.session.plan_id);
            if (payload.action === "save") {
                await loadMobilityDashboard();
                alert(payload.draft ? "Draft saved." : "Travel Plan saved. Open it from Your Plans below.");
            }
            return true;
        } catch (err) { alert(err.message); return false; }
        finally { state.busy = false; $("plannerSend").disabled = false; schedulePoll(); }
    }
    async function message(text) {
        const accepted = await action({action:"message", text});
        if (accepted) {
            $("plannerInput").value = "";
            if (/compare/i.test(text)) { state.comparison = true; comparison(); }
        }
    }
    function schedulePoll() {
        clearTimeout(state.timer);
        if (state.session?.research && !["ready", "failed", "superseded"].includes(state.session.research.status)) {
            state.timer = setTimeout(async () => {
                if (state.busy || document.hidden) { schedulePoll(); return; }
                try { state.session = await Alfred.fetchJSON(api+`sessions/${state.session.id}/`); render(); }
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
        candidates(); comparison(); itinerary();
        if (session.plan_id) populateDetails(session.plan_id);
        else $("planDetails").hidden = true;
        if (field("vehicle_profile")) $("plannerVehicle").value = String(field("vehicle_profile"));
        schedulePoll();
    }
    function candidates() {
        Alfred.setHTMLIfChanged("plannerCandidates", state.session.candidates.map((d,i) => `<article class="travel-candidate" data-destination="${esc(d.name)}"><header><span class="travel-fit">Option ${i+1} / ${esc(d.fit)}</span><h3 class="mt-2 mb-0">${esc(d.name)}</h3><p class="small mt-2 mb-0">${esc(d.styles.slice(0,3).join(" · "))}</p></header><div class="travel-candidate-body"><dl><dt>Expected trip budget</dt><dd>${money(d.budget.expected)} · range ${money(d.budget.minimum)}–${money(d.budget.comfortable)}</dd><dt>Travel from ${esc(field("origin"))}</dt><dd>${d.distance_km ? `~${esc(d.distance_km)} km / ~${esc(d.travel_hours)} hours one way` : "Distance and travel time unverified"}<br><small>Estimate · includes no live traffic</small></dd><dt>Weather</dt><dd>${esc(d.weather.summary)}</dd></dl><strong>Why it fits</strong><ul>${d.why.map(w=>`<li>${esc(w)}</li>`).join("")}</ul><strong>Watch out</strong><p class="small">${esc(d.issues.join(" "))}</p><div class="travel-actions"><button type="button" class="btn btn-primary btn-sm" data-planner-message="Choose ${esc(d.name)}">Choose ${esc(d.name)}</button><button type="button" class="btn btn-outline-secondary btn-sm" data-reject="${esc(d.name)}">Not this time</button></div><details class="mt-3"><summary>Details · Why this recommendation?</summary><div class="small mt-2">${Object.entries(d.factors).map(([k,v])=>`<p><strong>${esc(k)}</strong>: ${esc(v)}</p>`).join("")}<p>Ranking uses budget, travel time, your stated preferences and recorded visits. Fit labels are guidance, not probabilities.</p></div></details><details class="mt-2"><summary>Sources</summary>${sourceMarkup(d.sources)}</details></div></article>`).join(""));
    }
    function comparison() {
        $("plannerComparison").hidden = !state.comparison;
        if (!state.comparison) return;
        const options = state.session.candidates;
        const rows = [["Expected budget",d=>money(d.budget.expected)],["One-way distance",d=>d.distance_km ? `~${d.distance_km} km (estimate)` : "Unknown"],["Weather",d=>d.weather.summary],["Photography",d=>d.factors.Photography],["Crowds",()=>"Unverified"],["Ride difficulty",()=>"Needs route verification"],["Novelty",d=>d.novelty],["Stay availability",()=>"Unverified"]];
        Alfred.setHTMLIfChanged("plannerComparison", `<h3 class="h5">Compare your options</h3><div class="travel-comparison" tabindex="0" role="region" aria-label="Scrollable destination comparison"><table class="table"><caption>Estimates and unknowns are labelled. No live availability guarantee.</caption><thead><tr><th scope="col">Factor</th>${options.map(d=>`<th scope="col">${esc(d.name)}</th>`).join("")}</tr></thead><tbody>${rows.map(([label,fn])=>`<tr><th scope="row">${label}</th>${options.map(d=>`<td>${esc(fn(d))}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`);
    }
    function itinerary() {
        const it = state.session.itinerary;
        $("plannerItinerary").hidden = !it?.days?.length;
        if (!it?.days?.length) return;
        const b = it.budget;
        Alfred.setHTMLIfChanged("plannerItinerary", `<div class="surface-card mb-3"><p class="metric-kicker">YOUR FLEXIBLE ITINERARY · PRELIMINARY</p><h2>${esc(it.destination)}</h2><p>${esc(it.summary)}</p><p><strong>Route:</strong> ${esc(it.route.summary)}</p><p class="small">${esc(it.route.note)}</p><p>${esc(it.weather.summary)}</p><div class="travel-budget-grid">${["minimum","expected","comfortable"].map(k=>`<div>${esc(k[0].toUpperCase()+k.slice(1))}<strong>${money(b[k])}</strong></div>`).join("")}</div>${b.over_budget ? `<p class="alert alert-warning">About ${money(b.over_budget)} over target. ${esc(b.adaptations.join(" · "))}</p>` : ""}<details><summary>Budget breakdown and assumptions</summary><table class="table"><tbody>${Object.entries(b.categories).map(([k,v])=>`<tr><th scope="row">${esc(k)}</th><td>${money(v)}</td></tr>`).join("")}</tbody></table><ul>${b.assumptions.map(a=>`<li>${esc(a)}</li>`).join("")}</ul></details></div><div class="travel-itinerary-days">${it.days.map(d=>`<article class="travel-day" data-day="${d.day}"><p class="travel-fit">DAY ${d.day} ${esc(d.date || "· dates flexible")}</p><h3 class="h5">${esc(d.title)}</h3><ul>${d.items.map(item=>`<li><span class="travel-priority">${esc(item.priority)} · ${esc(item.period)}</span><br><strong>${esc(item.title)}</strong><br><small>${esc(item.duration)}</small></li>`).join("")}</ul><p class="small"><strong>Stay:</strong> ${esc(d.stay)}<br><strong>Meals:</strong> ${esc(d.meals)}</p><strong>Day allowance: ${money(d.estimated_cost)}</strong></article>`).join("")}</div><div class="surface-card mt-3"><details><summary>Packing, vehicle and pre-trip checks</summary><ul>${it.packing.concat(it.checks).map(p=>`<li>${esc(p)}</li>`).join("")}</ul>${it.bike ? `<p>${esc(it.bike.profile)} · ${it.bike.nominal_range_km ? `Nominal profile range ~${esc(it.bike.nominal_range_km)} km` : "Range not available from your profile"}</p><p>${esc(it.bike.range_note)} ${esc(it.bike.notes)}</p>` : ""}<ul>${it.route.options.map(o=>`<li>${esc(o.name)}: ${esc(o.status)}</li>`).join("")}</ul></details><details class="mt-2"><summary>Research sources</summary>${sourceMarkup(it.sources)}</details></div>`);
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
        const [feedback, media] = await Promise.all([Alfred.fetchJSON(api+"feedback/"), Alfred.fetchJSON(api+"media-suggestions/")]);
        $("plannerPostTrip").hidden = !feedback.due.length && !media.suggestions.length;
        Alfred.setHTMLIfChanged("plannerFeedback", feedback.due.map(p=>`<div class="mb-3"><p>How was ${esc(p.title)}? Feedback is optional.</p><details><summary>What did you like or dislike? (optional)</summary>${["liked","disliked"].map(kind=>`<fieldset class="mt-2"><legend class="h6">${kind === "liked" ? "Enjoyed" : "Could be better"}</legend><div class="travel-chips">${["photography","scenery","ride","food","stay","weather","activities","crowds","roads","distance","cost"].map(tag=>`<label class="small"><input type="checkbox" data-feedback-plan="${p.id}" data-feedback-kind="${kind}" value="${tag}"> ${tag}</label>`).join("")}</div></fieldset>`).join("")}</details><div class="travel-chips">${[["loved","Loved it"],["good","Good"],["okay","Okay"],["disliked","Didn't enjoy it"]].map(([v,l])=>`<button data-rating="${v}" data-plan="${p.id}">${l}</button>`).join("")}</div></div>`).join(""));
        Alfred.setHTMLIfChanged("plannerMedia", media.suggestions.map(s=>`<div class="mb-3"><p>Photo near ${esc(s.location)} matches ${esc(s.plan_title)}. ${esc(s.reason)}</p><details><summary>Review photo</summary><img class="travel-media-preview" src="${esc(s.photo_url)}" alt="${esc(s.caption || 'Trip photo')}"></details><button class="btn btn-sm btn-primary" data-media="add" data-photo="${s.photo_id}" data-plan="${s.plan_id}">Add to trip</button> <button class="btn btn-sm btn-outline-secondary" data-media="ignore" data-photo="${s.photo_id}" data-plan="${s.plan_id}">Ignore</button></div>`).join(""));
    }
    async function init() {
        if (!$("travelPlanner")) return;
        $("plannerComposer").addEventListener("submit", e=>{e.preventDefault(); message($("plannerInput").value);});
        $("plannerNew").addEventListener("click", ()=>create().catch(e=>alert(e.message)));
        $("plannerDraft").addEventListener("click", ()=>action({action:"save",draft:true}));
        $("plannerSave").addEventListener("click", ()=>action({action:"save"}));
        $("plannerCompare").addEventListener("click", ()=>{state.comparison=!state.comparison;comparison();});
        $("plannerVehicle").addEventListener("change", e=>{if(e.target.value)action({action:"vehicle",vehicle_id:Number(e.target.value)});});
        document.addEventListener("click", async e=>{
            const button = e.target.closest("button");
            if (!button) return;
            try {
                if (button.dataset.plannerMessage) await message(button.dataset.plannerMessage);
                if (button.dataset.session) await open(Number(button.dataset.session));
                if (button.dataset.openPlan) await create(Number(button.dataset.openPlan));
                if (button.dataset.reject) await action({action:"reject",destination:button.dataset.reject});
                if (button.dataset.rating) {const tags=kind=>Array.from(document.querySelectorAll(`input[data-feedback-plan="${Number(button.dataset.plan)}"][data-feedback-kind="${kind}"]:checked`)).map(e=>e.value);await Alfred.fetchJSON(api+"feedback/",{method:"POST",body:JSON.stringify({plan_id:Number(button.dataset.plan),rating:button.dataset.rating,liked:tags("liked"),disliked:tags("disliked")})});await postTrip();}
                if (button.dataset.media) {await Alfred.fetchJSON(api+"media-suggestions/",{method:"POST",body:JSON.stringify({plan_id:Number(button.dataset.plan),photo_id:Number(button.dataset.photo),action:button.dataset.media})});await postTrip();await loadMobilityDashboard();}
            } catch(err) { alert(err.message); }
        });
        try {
            const data = await list();
            const id = Number(new URLSearchParams(location.search).get("session")) || data.sessions[0]?.id;
            if (id) await open(id); else await create();
            const [profiles,prefs] = await Promise.all([Alfred.fetchJSON("/api/mobility/bikes/"), Alfred.fetchJSON(api+"preferences/")]);
            $("plannerVehicle").innerHTML = '<option value="">Choose when relevant</option>'+(profiles.results || profiles).map(p=>`<option value="${p.id}">${esc(p.display_name)}</option>`).join("");
            if (field("vehicle_profile")) $("plannerVehicle").value=field("vehicle_profile");
            $("plannerStyle").innerHTML=Object.entries(prefs.preferences).filter(([,v])=>v.value === true).slice(0,6).map(([k])=>`<span class="badge text-bg-light">${esc(k)}</span>`).join("") || '<span class="small">Your style grows with choices and feedback.</span>';
            await postTrip();
        } catch(err) { alert(err.message); }
    }
    document.addEventListener("DOMContentLoaded", init);
    return {openPlan:async id=>{await create(id);$("travelPlanner").scrollIntoView({behavior:"smooth"});},message,refreshPostTrip:postTrip};
})();
