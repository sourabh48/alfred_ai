/* Home > Your assistants: run a bot, review its proposal, then Confirm or Dismiss (AI-17 propose-then-confirm). */
(() => {
    const esc = value => Alfred.escapeHtml(String(value ?? ""));
    const $ = id => document.getElementById(id);
    let proposals = [];
    const post = body => Alfred.fetchJSON("/api/ai/bots/", {method: "POST", body: JSON.stringify(body)});
    const say = text => { $("taskBotsStatus").textContent = text; };

    function describe(action) {
        if (action.type === "recheck") return "Recheck weather and route now";
        if (action.type === "categorise") return `File under ${action.label}`;
        return `Add reminder at ${action.local_time.replace("T", " ")}${action.enable ? " (turns on reminders for this trip)" : ""}`;
    }

    function card(p) {
        return `<article class="surface-card mb-3" data-bot-proposal="${esc(p.proposal_id)}"><h3 class="h6">${esc(p.label)} <span class="small">· ${esc(p.for_date)}</span></h3><ul class="home-attention-list">${p.items.map(item =>
            `<li><span><strong>${esc(item.title)}</strong><br>${esc(item.detail)}${item.action ? `<br><label class="small"><input type="checkbox" data-bot-item="${esc(item.id)}"${item.action.type === "categorise" ? " checked" : ""}> ${esc(describe(item.action))}</label>` : ""}</span><a class="btn btn-sm btn-outline-primary ms-auto" href="${esc(item.url)}">Open</a></li>`).join("")}</ul>
            <button type="button" class="btn btn-sm btn-primary" data-bot-confirm="${esc(p.proposal_id)}">Confirm</button> <button type="button" class="btn btn-sm btn-outline-secondary" data-bot-dismiss="${esc(p.proposal_id)}">Dismiss</button>
            <p class="small mb-0 mt-2">Confirm marks this review done and does only the ticked steps.</p></article>`;
    }

    async function load() {
        const data = await Alfred.fetchJSON("/api/ai/bots/");
        proposals = data.proposals;
        if ($("taskBots").dataset.recovery === "true" && !$("taskBotsRun").childElementCount) Alfred.setHTMLIfChanged("taskBotsRun", '<button type="button" class="btn btn-sm btn-primary" data-bot-run-all="1">Run all bots</button>'
            + `<details class="mt-2"><summary>Run one bot</summary><div class="d-flex flex-wrap gap-2 mt-2">${data.bots.map(b => `<button type="button" class="btn btn-sm btn-outline-primary" data-bot-run="${esc(b.name)}" title="${esc(b.description)}">Run ${esc(b.label)}</button>`).join("")}</div></details>`);
        Alfred.setHTMLIfChanged("taskBotsList", proposals.map(card).join("") || '<p class="small mb-0">No reviews waiting.</p>');
    }

    async function handle(button) {
        if (button.dataset.botRun) {
            const result = await post({operation: "run", bot: button.dataset.botRun});
            say(result.proposal ? `${result.proposal.label} is ready to review.` : "Nothing due right now.");
        }
        if (button.dataset.botRunAll) {
            let ready = 0, failed = 0;
            for (const bot of Array.from(document.querySelectorAll("[data-bot-run]"), b => b.dataset.botRun)) {
                say(`Running bots... ${ready} ready so far.`);
                try { if ((await post({operation: "run", bot})).proposal) ready++; } catch (error) { failed++; }
            }
            say(`${ready} review(s) ready. ${failed ? `${failed} failed; check the worker and retry later.` : "All checks completed."}`);
        }
        if (button.dataset.botDismiss) say((await post({operation: "dismiss", proposal_id: button.dataset.botDismiss})).message);
        if (button.dataset.botConfirm) {
            const p = proposals.find(row => row.proposal_id === button.dataset.botConfirm);
            const box = button.closest("[data-bot-proposal]");
            const ticked = [...box.querySelectorAll("[data-bot-item]:checked")].map(input => input.dataset.botItem);
            const reviewed = p.items.filter(item => !item.action).map(item => item.id);
            say((await post({operation: "confirm", proposal_id: p.proposal_id, item_ids: [...reviewed, ...ticked], fingerprint: p.fingerprint, confirmed: true})).message);
        }
        await load();
    }

    document.addEventListener("DOMContentLoaded", () => {
        if (!$("taskBots")) return;
        $("taskBots").addEventListener("click", async event => {
            const button = event.target.closest("button");
            if (!button) return;
            button.disabled = true;
            try { await handle(button); } catch (error) { say(error.message); await load().catch(() => {}); }
            finally { button.disabled = false; }
        });
        load().catch(error => say(error.message));
    });
})();
