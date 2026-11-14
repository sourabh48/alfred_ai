/* Proactive next steps and free-weekend ideas. A step's action runs only after Confirm, through the Travel preparation bot. */
window.TravelSuggestions = (() => {
    const esc = value => Alfred.escapeHtml(String(value ?? ""));
    const panel = () => document.getElementById("plannerSuggestions");
    let reload, data = null, reviewing = null, sessionId = null, status = "";

    function describe(action) {
        if (action.type === "recheck") return "ALFRED will recheck the weather and route for this trip now. This uses your Google key's daily allowance.";
        return `ALFRED will add the reminder "${action.label}" at ${action.local_time.replace("T", " ")} (${action.zone})`
            + (action.enable ? " and turn on reminders for this trip." : ".");
    }

    function step(s) {
        const links = s.links.map(l => `<a href="${esc(l.url)}" target="_blank" rel="noopener noreferrer">${esc(l.label)}</a>`).join(" · ");
        const review = s.action && reviewing === s.id
            ? `<div class="mt-2" role="group" aria-label="Confirm ${esc(s.title)}"><p class="mb-1">${esc(describe(s.action))}</p><button type="button" class="btn btn-sm btn-primary" data-suggestion-confirm="${esc(s.id)}">Confirm</button> <button type="button" class="btn btn-sm btn-outline-secondary" data-suggestion-cancel>Cancel</button></div>`
            : s.action ? `<div><button type="button" class="btn btn-sm btn-outline-primary mt-1" data-suggestion-review="${esc(s.id)}">Review</button></div>` : "";
        return `<li data-suggestion="${esc(s.id)}"><strong>${esc(s.title)}</strong>${s.due_on ? ` <span class="small">· ${esc(s.due_on)}</span>` : ""}<br>${esc(s.detail)}<br><span class="small">${esc(s.basis)}</span>${links ? `<br>${links}` : ""}${review}</li>`;
    }

    function render() {
        const target = panel();
        if (!data) { target.hidden = true; return; }
        const ideas = data.trip_ideas;
        target.hidden = !data.next_steps.length && !ideas.ideas.length;
        Alfred.setHTMLIfChanged(target, `<h2 class="h5" id="plannerSuggestionsTitle">Suggested for you</h2>`
            + (data.next_steps.length ? `<h3 class="h6">Next steps for your trip</h3><ul class="travel-suggestion-list">${data.next_steps.map(step).join("")}</ul>` : "")
            + `<p role="status" aria-live="polite" id="plannerSuggestionsStatus">${esc(status)}</p>`
            + (ideas.ideas.length ? `<h3 class="h6">Ideas for your free weekend, ${esc(ideas.free_dates.start)} to ${esc(ideas.free_dates.end)}</h3><ul class="travel-suggestion-list">${ideas.ideas.map(i =>
                `<li><strong>${esc(i.name)}</strong> · ${esc(i.fit)}<br>${esc((i.why || []).join(" "))}<br><span class="small">${esc(i.distance_basis || "")}</span><br><button type="button" class="btn btn-sm btn-outline-primary mt-1" data-suggestion-idea="${esc(`Plan a 2-day trip to ${i.name} from ${ideas.free_dates.start} to ${ideas.free_dates.end}`)}">Plan this</button></li>`).join("")}</ul><p class="small">${esc(ideas.note)}</p>` : ""));
    }

    async function load(id) {
        sessionId = id; reviewing = null;
        try { data = await Alfred.fetchJSON(`/api/mobility/planner/suggestions/?session=${encodeURIComponent(id)}`); }
        catch (_) { data = null; }
        if (sessionId === id) render();
    }

    async function confirm(id) {
        // The bot re-reads the trip and refuses if anything changed since this review (stale proposals are rejected).
        const run = await Alfred.fetchJSON("/api/ai/bots/", {method: "POST", body: JSON.stringify({operation: "run", bot: "travel_prep"})});
        const item = run.proposal?.items.find(row => row.id === `travel:${id}`);
        if (!item) throw new Error("This step is no longer needed. The list is refreshed.");
        const done = await Alfred.fetchJSON("/api/ai/bots/", {method: "POST", body: JSON.stringify({operation: "confirm", proposal_id: run.proposal.proposal_id,
            item_ids: [item.id], fingerprint: run.proposal.fingerprint, confirmed: true})});
        return done.message;
    }

    function init(options) {
        ({reload} = options);
        panel().addEventListener("click", async event => {
            const button = event.target.closest("button");
            if (!button) return;
            if (button.dataset.suggestionReview) { reviewing = button.dataset.suggestionReview; status = ""; render(); }
            if (button.hasAttribute("data-suggestion-cancel")) { reviewing = null; status = "Cancelled. Nothing changed."; render(); }
            if (button.dataset.suggestionIdea) { const input = document.getElementById("plannerInput"); input.value = button.dataset.suggestionIdea; input.focus(); }
            if (button.dataset.suggestionConfirm) {
                button.disabled = true;
                try { status = await confirm(button.dataset.suggestionConfirm); await reload(); }
                catch (error) { status = error.message; }
                await load(sessionId);
            }
        });
    }
    return {init, load};
})();
