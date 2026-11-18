/* Research desk: ALFRED researches by itself each day and suggests; the owner only accepts or rejects. Nothing is traded. */
window.ResearchDesk = (() => {
    const $ = id => document.getElementById(id), e = v => Alfred.escapeHtml(String(v ?? ""));
    const URL = "/api/investments/research/desk/";
    const charts = {};
    let epoch = 0, state = null;
    const tone = rating => ({ buy: "status-buy", overweight: "status-buy", hold: "status-neutral", underweight: "status-warn", sell: "status-bad" }[rating] || "");

    function say(text, kind = "info") {
        const box = $("researchDeskFeedback");
        box.className = `alert alert-${kind} small mb-3`;
        box.textContent = text;
        box.hidden = !text;
    }

    function card(s) {
        const list = (items, title) => items.length ? `<div class="col-md-6"><div class="fw-semibold small">${title}</div><ul class="small mb-2">${items.map(p =>
            `<li>${e(p.point)} <span class="muted">(${e(p.as_of)})</span></li>`).join("")}</ul></div>` : "";
        const ind = s.indicators || {};
        const news = (s.news || []).length ? `<div class="small mb-2"><span class="fw-semibold">Headlines (not scored):</span><ul class="mb-0">${s.news.map(n =>
            `<li><a href="${e(n.url)}" target="_blank" rel="noopener noreferrer">${e(n.title)}</a> <span class="muted">${e(n.source)} ${e(n.published)}</span></li>`).join("")}</ul></div>` : "";
        return `<article class="mini-card" data-desk-card="${e(s.id)}">
            <div class="d-flex flex-wrap justify-content-between align-items-start gap-2">
                <div><div class="fw-semibold">${e(s.symbol)}${s.name !== s.symbol ? ` · ${e(s.name)}` : ""}${s.held ? ' <span class="muted small">(you own it)</span>' : ""}${s.idea ? ' <span class="badge text-bg-light border">Idea</span>' : ""}</div>
                    <div class="small muted">Research call: <span data-desk-label>${e(s.label)}</span>. ${e(s.summary)} Last daily close ${e(s.currency || "")} ${e(Alfred.formatNumber(s.price, 2))} on ${e(s.price_as_of)} (not a live quote).</div></div>
                <span class="status-pill ${s.status === "Not for you yet" ? "status-warn" : tone(s.rating)}" data-desk-status>${e(s.status)}</span>
            </div>
            <ul class="small mb-0 mt-2 desk-facts">
                ${fit(s)}
                <li><span class="fw-semibold">Why now:</span> ${e(s.why || "")} ${e(s.change || (s.first_seen && s.first_seen < s.for_date ? `Same call since ${s.first_seen}; the evidence has not changed.` : "First look at this share."))}</li>
                <li><span class="fw-semibold">Strongest reason against:</span> ${e(s.against)}</li>
                ${s.levels ? `<li><span class="fw-semibold">Example levels:</span> ${e(s.levels.text)}</li>` : ""}
                <li><span class="fw-semibold">What would change this:</span> ${e(s.change_if)}</li>
                <li><span class="fw-semibold">Next check:</span> ${e(nextCheck())}. Company results up to ${e(s.latest_period_end || "unknown")}.</li>
            </ul>
            <div class="d-flex flex-wrap gap-2 mt-2">
                <button type="button" class="btn btn-sm btn-primary" data-desk-accept="${e(s.id)}" aria-label="Accept and save to my journal: ${e(s.label)} ${e(s.symbol)}">Accept</button>
                <button type="button" class="btn btn-sm btn-outline-secondary" data-desk-reject="${e(s.id)}" aria-label="Reject: ${e(s.label)} ${e(s.symbol)}">Reject</button>
                <button type="button" class="btn btn-sm btn-outline-secondary" data-desk-later="${e(s.id)}" aria-label="Remind me in a week about ${e(s.symbol)}">Remind me in a week</button>
                ${(s.why === "You looked it up recently." || s.idea) && !(state?.settings.watch || []).some(w => w.symbol === s.symbol)
                    ? `<button type="button" class="btn btn-sm btn-outline-secondary" data-desk-watch="${e(s.symbol)}">Add to watch list</button>` : ""}
            </div>
            <details class="mt-2" data-desk-details="${e(s.id)}"><summary class="small">Why, with charts</summary>
                <ol class="small mt-2 mb-2">${s.steps.map(step => `<li><span class="fw-semibold">${e(step.role)}:</span> ${e(step.text)}</li>`).join("")}</ol>
                <div class="row g-2">
                    <div class="col-lg-7"><div class="small fw-semibold">Price over the past year, with its 50 and 200-day averages (${e(s.currency || "currency not recorded")})</div>
                        <div class="chart-box"><canvas id="deskPrice-${e(s.id)}" aria-label="${e(s.symbol)} price and averages chart"></canvas></div></div>
                    <div class="col-lg-5"><div class="small fw-semibold">Yearly revenue and profit (${e(s.charts.results.unit)})</div>
                        <div class="chart-box"><canvas id="deskResults-${e(s.id)}" aria-label="${e(s.symbol)} revenue and profit chart"></canvas></div></div>
                </div>
                <p class="small mt-2 mb-1">RSI ${e(ind.rsi14 ?? "n/a")} · 50-day average ${e(ind.sma50 ?? "n/a")} · 200-day average ${e(ind.sma200 ?? "n/a")} · MACD histogram ${e(ind.macd_histogram ?? "n/a")}. ${e(s.valuation)}</p>
                <div class="row g-2">${list(s.good, "Good signs")}${list(s.bad, "Warning signs")}</div>
                ${(s.macro || []).length ? `<p class="small mb-2"><span class="fw-semibold">Economy (context only, not scored):</span> ${s.macro.map(e).join(" ")}</p>` : ""}
                ${(s.context || []).length ? `<div class="small mb-2"><span class="fw-semibold">Company filings and earnings (not scored):</span><ul class="mb-0">${s.context.map(c =>
                    `<li>${c.url ? `<a href="${e(c.url)}" target="_blank" rel="noopener noreferrer">${e(c.text)}</a>` : e(c.text)}</li>`).join("")}</ul></div>` : ""}
                ${news}
                <ul class="small muted mb-1">${s.limits.map(l => `<li>${e(l)}</li>`).join("")}</ul>
                <a class="small" href="${e(s.source_url)}" target="_blank" rel="noopener noreferrer">Source: Yahoo Finance</a>
            </details>
        </article>`;
    }

    function fit(s) {
        const f = s.fit || {}, why = (f.reasons || []).join(" ");
        const ask = (f.missing || []).some(m => !m.startsWith("your current bank")) ? ` <button type="button" class="btn btn-link btn-sm p-0 align-baseline" data-desk-profile>Answer two questions</button>` : "";
        if (f.state === "fits") return `<li><span class="fw-semibold">Fits you?</span> Yes, on your answers and records: ${e(why)} ALFRED does not suggest an amount.</li>`;
        if (f.state === "does_not_fit") return `<li><span class="fw-semibold">Fits you?</span> Not now. ${e(why)}${ask}</li>`;
        if (f.state === "unknown") return `<li><span class="fw-semibold">Fits you?</span> Unknown. ${e(why)}${ask}</li>`;
        return "";
    }

    function nextCheck() {
        if (!state?.settings.enabled) return "Paused; press Research now to check";
        return state.next_run ? Alfred.formatDateTime(state.next_run) : "Daily";
    }

    function draw(id, canvasId, config) {
        const canvas = $(canvasId);
        if (canvas) charts[id + canvasId] = Alfred.renderChart(charts[id + canvasId], canvas, config);
    }

    function drawDetails(s) {
        const p = s.charts.price, r = s.charts.results;
        if (p) draw(s.id, `deskPrice-${s.id}`, { type: "line", data: { labels: p.labels, datasets: [
            { label: "Close", data: p.close, pointRadius: 0 }, { label: "50-day average", data: p.sma50, pointRadius: 0 },
            { label: "200-day average", data: p.sma200, pointRadius: 0, borderDash: [6, 4] }] },
            options: { interaction: { mode: "index", intersect: false }, scales: { x: { ticks: { maxTicksLimit: 6 } } } } });
        if (r.labels.length) draw(s.id, `deskResults-${s.id}`, { type: "bar", data: { labels: r.labels, datasets: [
            { label: "Revenue", data: r.revenue }, { label: "Profit", data: r.profit }] } });
        else $(`deskResults-${s.id}`)?.closest(".chart-box")?.replaceWith(Object.assign(document.createElement("p"), { className: "small muted", textContent: "No two dated years of results to draw." }));
    }

    function options(select, choices, value) {
        select.innerHTML = `<option value="">Not answered</option>` + Object.entries(choices).map(([key, text]) =>
            `<option value="${e(key)}"${key === value ? " selected" : ""}>${e(text)}</option>`).join("");
    }

    function render(data) {
        state = data;
        const enabled = data.settings.enabled, monitor = $("researchDeskMonitor");
        monitor.textContent = enabled ? "Pause daily research" : "Resume daily research";
        monitor.setAttribute("aria-pressed", String(!enabled));
        options($("researchDeskLoss"), data.loss_choices, data.settings.profile.loss);
        options($("researchDeskHorizon"), data.horizon_choices, data.settings.profile.horizon);
        Object.values(charts).forEach(chart => chart.destroy());
        Object.keys(charts).forEach(key => delete charts[key]);
        const run = data.last_run, suggestions = data.suggestions || [];
        $("researchDeskStatus").textContent = (run ? `Last researched ${Alfred.formatDateTime(run.at)}: ${run.researched} share(s) rated, ${run.skipped.length} skipped.`
            : "Not researched yet. ALFRED researches by itself once a day after markets close; press Research now to start.")
            + (enabled ? (data.next_run ? ` Next automatic check: ${Alfred.formatDateTime(data.next_run)}, after the market closes, while ALFRED is running (a missed check runs at the next start). A call changes only when its evidence does.` : "") : " Daily research is paused.")
            + (data.snoozed ? ` ${data.snoozed} call(s) put off for now.` : "");
        $("researchDeskSkipped").innerHTML = run && run.skipped.length ? `<summary class="small">Skipped (${run.skipped.length})</summary><ul class="small mb-0">${run.skipped.map(item =>
            `<li>${e(item.name)}: ${e(item.reason)}</li>`).join("")}</ul>` : "";
        $("researchDeskSkipped").hidden = !(run && run.skipped.length);
        $("researchDeskHoldings").checked = data.settings.include_holdings;
        $("researchDeskIdeas").checked = data.settings.discover;
        const ideas = data.last_ideas;
        $("researchDeskIdeasStatus").textContent = ideas ? `Last looked ${Alfred.formatDateTime(ideas.at)}: ${ideas.checked} companies checked, ${ideas.found} idea(s).` : "Not looked yet.";
        backtest(data.backtest);
        $("researchDeskWatch").innerHTML = data.settings.watch.map(item => `<span class="badge text-bg-light border me-1 mb-1">${e(item.symbol)}
            <button type="button" class="btn btn-link btn-sm p-0 ms-1" data-desk-remove="${e(item.symbol)}" aria-label="Remove ${e(item.symbol)} from the watch list">×</button></span>`).join("")
            || '<span class="small muted">Empty. Add a symbol below.</span>';
        $("researchDeskList").innerHTML = suggestions.map(card).join("") || '<p class="small muted mb-0">No open suggestions.</p>';
        $("researchDeskAnswered").innerHTML = (data.answered || []).map(a => `<li>${e(a.symbol)}: ${e(a.label)} · ${a.state === "accepted" ? "accepted" : "rejected"} ${e(a.decided_at ? Alfred.formatDateTime(a.decided_at) : "")}</li>`).join("");
        const overview = $("researchDeskOverview");
        overview.closest(".chart-box").hidden = !suggestions.length;
        if (suggestions.length) charts.overview = Alfred.renderChart(null, overview, { type: "bar",
            data: { labels: suggestions.map(s => `${s.symbol}: ${s.label}`), datasets: [
                { label: "Good signs", data: suggestions.map(s => s.good.length) }, { label: "Warning signs", data: suggestions.map(s => s.bad.length) }] },
            options: { indexAxis: "y", scales: { x: { ticks: { precision: 0 } } } } });
    }

    function backtest(b) {
        const box = $("researchDeskBacktest");
        box.hidden = !b;
        if (!b) return;
        const was = box.open, pct = value => value == null ? "n/a" : `${e(value)}%`;
        box.innerHTML = `<summary class="small">How these rules did on past data: ${b.calls ? `${e(b.calls)} past call(s)${b.went_its_way_pct != null ? `, ${e(b.went_its_way_pct)}% went their way` : ""}` : "not enough history"} (checked ${e(Alfred.formatDateTime(b.at))})</summary>
            ${b.calls ? `<p class="small mt-2 mb-1">Each past month from ${e(b.from)} to ${e(b.to)}, ALFRED re-ran today's rules on the prices and results known then, and checked the share 91 days later against NIFTY 50.</p>
            <div class="table-responsive"><table class="table table-sm small mb-2"><caption class="visually-hidden">Past calls by rating</caption>
                <thead><tr><th scope="col">Call</th><th scope="col">Calls</th><th scope="col">Average move</th><th scope="col">Against NIFTY 50</th><th scope="col">Went its way</th></tr></thead>
                <tbody>${b.by_rating.map(r => `<tr><td>${e(r.label)}</td><td>${e(r.calls)}</td><td>${pct(r.average_move_pct)}</td><td>${pct(r.average_vs_nifty_pct)}</td><td>${r.went_its_way_pct == null ? "not judged" : pct(r.went_its_way_pct)}</td></tr>`).join("")}</tbody></table></div>` : ""}
            ${b.skipped.length ? `<p class="small mb-1">Not replayed: ${b.skipped.map(item => `${e(item.name)} (${e(item.reason)})`).join("; ")}</p>` : ""}
            <ul class="small muted mb-0">${b.limits.map(l => `<li>${e(l)}</li>`).join("")}</ul>`;
        box.open = was;
    }

    async function load() {
        const ticket = ++epoch;
        try {
            const data = await Alfred.fetchJSON(URL);
            if (ticket === epoch) render(data);
        } catch (error) { if (ticket === epoch) say(error.message, "danger"); }
    }

    async function act(body, button, done) {
        if (button) button.disabled = true;
        try {
            const data = await Alfred.fetchJSON(URL, { method: "POST", body: JSON.stringify(body) });
            render(data.desk);
            say(done(data.result) || "", "success");
            if (body.operation === "accept") document.dispatchEvent(new CustomEvent("research:changed"));
        } catch (error) { say(error.message, "danger"); }
        finally { if (button && button.isConnected) button.disabled = false; }
    }

    document.addEventListener("DOMContentLoaded", () => {
        if (!$("researchDeskSection")) return;
        load();
        $("researchDeskRun").addEventListener("click", event => {
            say("Researching. This takes up to a minute.", "info");
            act({ operation: "run" }, event.currentTarget, r => `Rated ${r.researched} share(s).`);
        });
        $("researchDeskMonitor").addEventListener("click", event => act({ operation: "monitor", enabled: !state?.settings.enabled }, event.currentTarget,
            s => s.enabled ? "Daily research is on again." : "Daily research paused. Your calls and journal stay; Research now still works."));
        $("researchDeskProfileForm").addEventListener("submit", event => {
            event.preventDefault();
            act({ operation: "profile", profile: { loss: $("researchDeskLoss").value || null, horizon: $("researchDeskHorizon").value || null } },
                event.submitter, () => "Answers saved. Personal fit uses them from now on.");
        });
        $("researchDeskBacktestRun").addEventListener("click", event => {
            say("Checking past calls. Fetching several years of prices takes a minute or two.", "info");
            act({ operation: "backtest" }, event.currentTarget, r => { $("researchDeskBacktest").open = true;
                return r.calls ? `Replayed ${r.calls} past call(s). See How these rules did on past data.` : "Too little dated history to replay any call."; });
        });
        $("researchDeskIdeas").addEventListener("change", event => act({ operation: "discover", enabled: event.currentTarget.checked }, null,
            s => s.discover ? "ALFRED looks for ideas among NIFTY 50 companies each week." : "Weekly ideas switched off. Open ideas stay until you answer them."));
        $("researchDeskIdeasRun").addEventListener("click", event => {
            say("Looking for ideas among NIFTY 50 companies. This takes a minute or two.", "info");
            act({ operation: "ideas" }, event.currentTarget, r => `Checked ${r.checked} companies; ${r.found} idea(s) added above.`);
        });
        $("researchDeskHoldings").addEventListener("change", event => act({ operation: "holdings", include: event.currentTarget.checked }, null,
            s => s.include_holdings ? "Your shares recorded by symbol are included from the next research." : "Your shares are left out from the next research."));
        $("researchDeskAddForm").addEventListener("submit", event => {
            event.preventDefault();
            const input = $("researchDeskAdd");
            act({ operation: "watch_add", symbol: input.value }, event.submitter, () => { input.value = ""; return "Added to the watch list."; });
        });
        document.getElementById("researchDeskSection").addEventListener("click", event => {
            const accept = event.target.closest("[data-desk-accept]"), reject = event.target.closest("[data-desk-reject]"), remove = event.target.closest("[data-desk-remove]");
            const later = event.target.closest("[data-desk-later]"), watch = event.target.closest("[data-desk-watch]"), profile = event.target.closest("[data-desk-profile]");
            if (later) act({ operation: "later", id: later.dataset.deskLater }, later, r => r.message);
            if (watch) act({ operation: "watch_add", symbol: watch.dataset.deskWatch }, watch, () => "Added to the watch list.");
            if (profile) { $("researchDeskProfile").open = true; $("researchDeskLoss").focus(); }
            if (accept) act({ operation: "accept", id: accept.dataset.deskAccept }, accept, r => r.message);
            if (reject) act({ operation: "reject", id: reject.dataset.deskReject }, reject, r => r.message);
            if (remove) act({ operation: "watch_remove", symbol: remove.dataset.deskRemove }, remove, () => "Removed from the watch list.");
        });
        document.getElementById("researchDeskList").addEventListener("toggle", event => {
            const id = event.target.dataset?.deskDetails, s = id && (state?.suggestions || []).find(item => item.id === id);
            if (s && event.target.open) drawDetails(s);
        }, true);
        window.addEventListener("pagehide", () => { epoch++; });
    });
    return { load };
})();
