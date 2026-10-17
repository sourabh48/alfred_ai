document.addEventListener("DOMContentLoaded", () => {
    const panel = document.getElementById("privateMemoryPanel");
    if (!panel) return;
    const list = document.getElementById("memoryList");
    const feedback = document.getElementById("memoryFeedback");
    const expected = document.getElementById("memoryEvaluationExpected");
    const quality = document.getElementById("memoryEvaluationResult");
    const query = document.getElementById("memoryEvaluationQuery");
    const search = document.getElementById("memorySearch");
    const category = document.getElementById("memoryCategory");
    const selectedReset = document.getElementById("memorySelectedReset");
    const candidates = document.getElementById("memoryCandidates");
    const evaluationCases = document.getElementById("memoryEvaluationCases");
    const evaluationDetails = document.getElementById("memoryEvaluationDetails");
    const evaluationFeedback = document.getElementById("memoryEvaluationFeedback");
    const evaluationThreshold = document.getElementById("memoryEvaluationThreshold");
    const evaluationForm = document.getElementById("memoryEvaluationForm");
    const evaluationAdd = document.getElementById("memoryEvaluationAdd");
    const evaluationClear = document.getElementById("memoryEvaluationClear");
    let cases = [], currentMemories = new Map(), previousExpected = new Set([""]), editorNeedsReview = false, evaluationPending = false, evaluationController = null;
    let generation = 0;
    let active = true;
    function message(text) { if (active) feedback.textContent = text; }
    function clearEvaluationResult() { quality.textContent = ""; evaluationDetails.replaceChildren(); }
    function evaluationControls() {
        evaluationForm.querySelectorAll("button").forEach(button => { button.disabled = !active || evaluationPending; });
        query.readOnly = evaluationPending || !active; query.required = !cases.length;
        expected.disabled = !active || evaluationPending; expected.required = !cases.length || Boolean(query.value.trim());
        evaluationThreshold.disabled = !active || evaluationPending;
    }
    function renderCases() {
        evaluationCases.replaceChildren();
        cases.forEach((item,index) => {
            const row = document.createElement("li"); row.className = "memory-card";
            const question = document.createElement("p"); question.textContent = item.query;
            const label = document.createElement("p");
            label.textContent = item.expected_ids.some(id => !currentMemories.has(id))
                ? "An expected source changed or is unavailable. Remove this case and review current memories; your question is preserved here."
                : item.expected_ids.length ? `Expected relevant memories: ${item.expected_ids.map(id => currentMemories.get(id)).join('; ')}` : "Expected: no memory should match.";
            const remove = document.createElement("button"); remove.type = "button"; remove.className = "btn btn-outline-secondary btn-sm";
            remove.textContent = "Remove question"; remove.setAttribute("aria-label", `Remove question ${index+1}`);
            remove.addEventListener("click", () => { cases.splice(index,1); clearEvaluationResult(); renderCases(); });
            row.append(question,label,remove); evaluationCases.append(row);
        });
        evaluationControls();
    }
    function editorCase() {
        if (!query.reportValidity() || !expected.reportValidity()) throw new Error("Review the question and current expected memories.");
        return {query:query.value.trim(),expected_ids:[...expected.selectedOptions].map(option => option.value).filter(Boolean)};
    }
    function boundedCases(items) {
        if (!items.length || items.length>20 || items.reduce((size,item) => size+new TextEncoder().encode(item.query).length,0)>8192) throw new Error("Use one to twenty questions totaling at most 8192 UTF-8 bytes; no cases were dropped.");
        if (items.some(item => item.expected_ids.length>20 || item.expected_ids.some(id => !currentMemories.has(id)))) throw new Error("Review current expected sources. Changed or deleted memories cannot be substituted automatically.");
        return items;
    }
    expected.addEventListener("change", () => {
        const selected = [...expected.selectedOptions].map(option => option.value);
        const added = selected.filter(id => !previousExpected.has(id));
        if (added.includes("")) [...expected.options].forEach(option => { option.selected = !option.value; });
        else if (selected.some(Boolean)) expected.options[0].selected = false;
        previousExpected = new Set([...expected.selectedOptions].map(option => option.value)); clearEvaluationResult();
        editorNeedsReview = !expected.selectedOptions.length;
    });
    query.addEventListener("input", () => { clearEvaluationResult(); evaluationControls(); });
    evaluationThreshold.addEventListener("input", clearEvaluationResult);
    evaluationAdd.addEventListener("click", () => {
        try {
            cases = boundedCases([...cases,editorCase()]); query.value = "";
            [...expected.options].forEach(option => { option.selected = !option.value; }); previousExpected = new Set([""]); editorNeedsReview = false;
            clearEvaluationResult(); renderCases(); evaluationFeedback.textContent = `${cases.length} questions added. No inference has run.`;
        } catch (error) { evaluationFeedback.textContent = error.message; }
    });
    evaluationClear.addEventListener("click", () => {
        cases = []; query.value = ""; previousExpected = new Set([""]); editorNeedsReview = false;
        [...expected.options].forEach(option => { option.selected = !option.value; });
        clearEvaluationResult(); renderCases(); evaluationFeedback.textContent = "Questions and results cleared from this page.";
    });
    function filterMemories() {
        let shown = 0;
        list.querySelectorAll(".memory-card").forEach(row => {
            row.hidden = !row.dataset.search.includes(search.value.toLowerCase()) || Boolean(category.value && row.dataset.category !== category.value);
            if (!row.hidden) shown++;
        });
        document.getElementById("memoryCount").textContent = `${shown} of ${list.querySelectorAll('.memory-card').length} current memories · user-confirmed statements`;
    }
    search.addEventListener("input", filterMemories); category.addEventListener("change", filterMemories);
    list.addEventListener("change", () => { selectedReset.disabled = !list.querySelector('input[data-memory-select]:checked'); });
    async function refreshPrivacy() {
        const ticket = generation;
        const [sync, reasoning] = await Promise.all([Alfred.fetchJSON("/api/ai/memories/sync/"), Alfred.fetchJSON("/api/ai/memories/reason/")]);
        if (!active || ticket !== generation) return;
        document.getElementById("memorySyncStatus").textContent = `Provider: ${sync.provider}. ${sync.available ? "Available" : "Not connected"}. Revision ${sync.status.revision}; ${sync.status.pending ? "updates queued" : "no queued updates"}; ${sync.status.conflict ? "conflict requires review" : "no conflict"}; failures ${sync.status.failures}.`;
        document.getElementById("memorySyncEnabled").checked = sync.status.enabled;
        document.getElementById("memorySyncEnabled").disabled = !sync.available;
        document.querySelector("#memorySyncForm button[type=submit]").disabled = !sync.available;
        document.getElementById("memorySyncNow").disabled = !sync.available || !sync.status.enabled;
        document.getElementById("memorySyncNow").textContent = sync.status.failures ? "Retry encrypted updates" : "Sync Now";
        const stamp = value => value ? new Date(value*1000).toLocaleString() : "Not recorded";
        document.getElementById("memorySyncDetails").textContent = `${sync.provider === 'mock' ? 'Synthetic provider only. ' : ''}Sync ${sync.status.enabled ? 'enabled' : 'disabled'}. Last successful sync: ${stamp(sync.status.last_success_at)}. Retry after: ${stamp(sync.status.retry_at)}. Deletion propagation follows this encrypted queue; historical backups retain their original copies.`;
        document.getElementById("memorySyncRecover").hidden = !sync.available || !sync.status.enabled || !sync.status.conflict;
        document.getElementById("memoryReasoningStatus").textContent = !reasoning.real_provider_enabled ? "OpenAI disabled. Ollama-first local reasoning; synthetic test access, when configured, is not real OpenAI." : reasoning.provider_available ? "Approved OpenAI available; explicit public consent and budgets apply." : "OpenAI not connected. Local reasoning remains available.";
        document.getElementById("memoryReasoningUsage").textContent = `UTC day ${reasoning.usage.day}: ${reasoning.usage.reserved_tokens} tokens reserved; USD ${(reasoning.usage.reserved_microusd/1000000).toFixed(6)} conservatively reserved. Billing measurements are unavailable; these reservations enforce caps.`;
        document.getElementById("memoryReasoningEnabled").checked = reasoning.policy.enabled;
        document.getElementById("memoryReasoningTokens").value = reasoning.policy.daily_tokens;
        document.getElementById("memoryReasoningDollars").value = reasoning.policy.daily_microusd / 1000000;
    }
    async function refresh() {
        if (!active) return;
        const previousCategory = category.value, selectedExpected = [...expected.selectedOptions].map(option => option.value);
        const drafts = new Map([...list.querySelectorAll('.memory-card')].map(row => {
            const edit = row.querySelector('details[data-memory-correction]');
            return [row.id,{text:edit.querySelector('textarea').value,checked:edit.querySelector('input[type=checkbox]').checked,open:edit.open}];
        }));
        const proposedDrafts = new Map([...candidates.querySelectorAll('article')].map(row => [row.dataset.candidateId,{text:row.querySelector('textarea').value,checked:row.querySelector('input[type=checkbox]').checked}]));
        const ticket = ++generation;
        evaluationController?.abort(); evaluationController = null; evaluationPending = false; clearEvaluationResult();
        evaluationForm.setAttribute("aria-busy","false");
        evaluationControls();
        const [payload, review] = await Promise.all([Alfred.fetchJSON("/api/ai/memories/"), Alfred.fetchJSON("/api/ai/memories/learning/")]);
        if (!active || ticket !== generation) return;
        document.getElementById("memoryRetentionDays").value = payload.retention_days;
        list.replaceChildren();
        expected.replaceChildren(new Option("No memory should match", "",false,true));
        currentMemories = new Map(payload.memories.map(memory => {
            const text = typeof memory.content.statement === "string" ? memory.content.statement : JSON.stringify(memory.content);
            return [memory.id,`${text.length > 160 ? text.slice(0,160)+'…' : text} · ${memory.id.slice(0,8)}`];
        }));
        if (!evaluationThreshold.value) evaluationThreshold.value = review.evaluation_min_score;
        quality.textContent = "";
        category.replaceChildren(new Option("All categories", "")); selectedReset.disabled = true;
        const categories = new Set();
        if (!payload.memories.length) list.textContent = "No verified memories saved.";
        payload.memories.forEach(memory => {
            const row = document.createElement("div");
            row.className = "memory-card"; row.id = `memory-${memory.id}`;
            row.dataset.category = typeof memory.content.category === "string" ? memory.content.category : "Uncategorized";
            row.dataset.search = JSON.stringify([memory.content,memory.provenance]).toLowerCase(); categories.add(row.dataset.category);
            const selectLabel = document.createElement("label");
            const select = document.createElement("input"); select.type = "checkbox"; select.dataset.memorySelect = memory.id;
            selectLabel.append(select, " Select memory");
            const status = document.createElement("span"); status.className = "workspace-badge ms-2"; status.textContent = "USER-CONFIRMED";
            const text = document.createElement("p");
            text.textContent = typeof memory.content.statement === "string" ? memory.content.statement : JSON.stringify(memory.content);
            const detail = document.createElement("p");
            detail.textContent = `${memory.sensitivity} · ${memory.provenance.source}`;
            const provenance = document.createElement("details");
            const provenanceTitle = document.createElement("summary"); provenanceTitle.textContent = "Provenance & verification";
            const provenanceText = document.createElement("p"); provenanceText.textContent = `Verified by you: ${new Date(memory.verified_at).toLocaleString()}. Category: ${row.dataset.category}. Source: ${JSON.stringify(memory.provenance)}. This statement is not canonical financial evidence.`;
            provenance.append(provenanceTitle,provenanceText);
            const remove = document.createElement("button");
            remove.type = "button";
            remove.className = "btn btn-outline-danger";
            remove.textContent = "Delete Memory";
            remove.addEventListener("click", async () => {
                if (!window.confirm("Delete this memory and revoke its recovery?")) return;
                remove.disabled = true;
                try {
                    await Alfred.fetchJSON(`/api/ai/memories/${encodeURIComponent(memory.id)}/`, {method: "DELETE"});
                    await refresh();
                    message("Memory deleted.");
                } catch (error) { message(error.message); remove.disabled = false; }
            });
            const edit = document.createElement("details");
            edit.dataset.memoryCorrection = "true";
            const title = document.createElement("summary");
            title.textContent = "Correct Memory";
            const form = document.createElement("form");
            form.dataset.liveRefreshHold = "true";
            const description = document.createElement("p");
            description.textContent = "Replace this memory with your correction. Its source history and privacy level are preserved.";
            const label = document.createElement("label");
            label.textContent = "Your correction";
            const input = document.createElement("textarea");
            input.className = "form-control mb-2";
            input.rows = 3;
            input.maxLength = 8192;
            input.required = true;
            input.autocomplete = "off";
            input.value = Object.values(memory.content).map(value => typeof value === "string" ? value : JSON.stringify(value)).join("\n");
            label.append(input);
            const confirmation = document.createElement("label");
            const checked = document.createElement("input");
            checked.type = "checkbox";
            checked.required = true;
            const draft = drafts.get(row.id);
            if (draft) { input.value = draft.text; checked.checked = draft.checked; edit.open = draft.open; }
            confirmation.append(checked, " I have checked this correction.");
            const save = document.createElement("button");
            save.type = "submit";
            save.className = "btn btn-outline-primary d-block mt-2";
            save.textContent = "Save Verified Correction";
            form.append(description, label, confirmation, save);
            form.addEventListener("submit", async event => {
                event.preventDefault();
                if (!checked.checked || !input.value.trim()) return;
                save.disabled = true;
                try {
                    await Alfred.fetchJSON("/api/ai/memories/learning/", {method: "POST", body: JSON.stringify({action: "correct", id: memory.id, content: {statement: input.value.trim()}, verified: true})});
                    await refresh();
                    message("Verified correction saved.");
                } catch (error) { message(error.message); save.disabled = false; }
            });
            edit.append(title, form);
            row.append(selectLabel, status, text, detail, provenance, remove, edit);
            list.append(row);
            expected.append(new Option(currentMemories.get(memory.id), memory.id));
        });
        [...categories].sort().forEach(value => category.append(new Option(value,value)));
        if (categories.has(previousCategory)) category.value = previousCategory;
        const changedExpected = editorNeedsReview || selectedExpected.some(id => id && !currentMemories.has(id));
        editorNeedsReview = changedExpected;
        [...expected.options].forEach(option => { option.selected = !changedExpected && (selectedExpected.length ? selectedExpected.includes(option.value) : !option.value); });
        previousExpected = new Set([...expected.selectedOptions].map(option => option.value));
        if (changedExpected) evaluationFeedback.textContent = "Expected memories changed. Select current sources or explicitly choose no match; your question draft is preserved.";
        renderCases();
        filterMemories();
        candidates.replaceChildren();
        if (!review.candidates.length) candidates.textContent = "No suggestions awaiting review.";
        review.candidates.forEach(candidate => {
            const row = document.createElement("article"); row.className = "memory-card"; row.dataset.candidateId = candidate.id;
            const status = document.createElement("span"); status.className = "workspace-badge"; status.textContent = "NEEDS REVIEW · INFERRED";
            const detail = document.createElement("p"); detail.textContent = `${candidate.provenance.source} · ${candidate.sensitivity} · extraction confidence ${candidate.confidence} (not a truth score)`;
            const form = document.createElement("form"); form.dataset.liveRefreshHold = "true";
            const label = document.createElement("label"); label.textContent = "Review and correct suggestion";
            const input = document.createElement("textarea"); input.className = "form-control my-2"; input.rows = 3; input.required = true; input.maxLength = 8192; input.value = candidate.content.statement || JSON.stringify(candidate.content); label.append(input);
            const verification = document.createElement("label"), checked = document.createElement("input"); checked.type = "checkbox"; checked.required = true;
            const draft = proposedDrafts.get(candidate.id);
            if (draft) { input.value = draft.text; checked.checked = draft.checked; }
            verification.append(checked," I checked this fact and its source.");
            const accept = document.createElement("button"); accept.className = "btn btn-outline-primary d-block my-2"; accept.type = "submit"; accept.textContent = "Accept verified memory";
            const reject = document.createElement("button"); reject.className = "btn btn-outline-danger"; reject.type = "button"; reject.textContent = "Reject suggestion";
            form.append(label,verification,accept,reject); row.append(status,detail,form); candidates.append(row);
            form.addEventListener("submit", async event => {
                event.preventDefault(); if (!checked.checked) return; accept.disabled = true;
                try { await Alfred.fetchJSON("/api/ai/memories/learning/", {method:"POST",body:JSON.stringify({action:"verify",id:candidate.id,verified:true,content:{statement:input.value}})}); await refresh(); message("User-confirmed memory saved. It is now eligible for retrieval."); }
                catch (error) { message(error.message); accept.disabled = false; }
            });
            reject.addEventListener("click", async () => {
                reject.disabled = true;
                try { await Alfred.fetchJSON(`/api/ai/memories/${candidate.id}/`, {method:"DELETE"}); await refresh(); message("Suggestion rejected; recovery key revoked."); }
                catch (error) { message(error.message); reject.disabled = false; }
            });
        });
        if (/^#memory-[a-f0-9]{32}$/.test(location.hash)) document.getElementById(location.hash.slice(1))?.scrollIntoView({block:"center"});
        refreshPrivacy().catch(error => message(error.message));
    }
    document.getElementById("memoryRetentionForm").addEventListener("submit", async event => {
        event.preventDefault();
        try {
            await Alfred.fetchJSON("/api/ai/memories/retention/", {method: "PUT", body: JSON.stringify({days: Number(document.getElementById("memoryRetentionDays").value)})});
            await refresh();
            message("Memory retention saved.");
        } catch (error) { message(error.message); }
    });
    document.getElementById("memoryResetButton").addEventListener("click", async event => {
        if (!window.confirm("Delete all your memories and revoke their recovery?")) return;
        event.target.disabled = true;
        try {
            await Alfred.fetchJSON("/api/ai/memories/reset/", {method: "POST", body: JSON.stringify({confirm: true})});
            await refresh();
            message("Your memories were reset.");
        } catch (error) { message(error.message); }
        finally { event.target.disabled = false; }
    });
    document.getElementById("memoryRefreshButton").addEventListener("click", () => refresh().catch(error => message(error.message)));
    selectedReset.addEventListener("click", async () => {
        const ids = [...list.querySelectorAll('input[data-memory-select]:checked')].map(input=>input.dataset.memorySelect);
        if (ids.length>20) { message("Select at most twenty memories at a time."); return; }
        if (!ids.length || !window.confirm("Delete selected memories and revoke their journal recovery? Historical backups retain their original data.")) return;
        selectedReset.disabled = true;
        try { const result=await Alfred.fetchJSON("/api/ai/memories/reset/",{method:"POST",body:JSON.stringify({confirm:true,ids})}); await refresh(); message(`${result.deleted} selected memories deleted; encrypted deletion propagation follows the configured sync queue.`); }
        catch (error) { message(error.message); selectedReset.disabled = false; }
    });
    async function cloudAction(path, payload, text) {
        const ticket = generation;
        try {
            await Alfred.fetchJSON(`/api/ai/memories/${path}/`, {method: path === "reason" ? "PUT" : "POST", body: JSON.stringify(payload)});
            await refreshPrivacy();
            if (active && ticket === generation) document.getElementById("memoryCloudFeedback").textContent = text;
        } catch (error) { if (active && ticket === generation) document.getElementById("memoryCloudFeedback").textContent = error.message; }
    }
    document.getElementById("memorySyncForm").addEventListener("submit", event => {
        event.preventDefault();
        const enabled = document.getElementById("memorySyncEnabled").checked;
        cloudAction("sync", {action: "configure", enabled, consent: enabled}, "Synchronization consent saved.");
    });
    document.getElementById("memorySyncNow").addEventListener("click", () => cloudAction("sync", {action: "sync"}, "Synchronization attempt completed. Check queue and conflict status."));
    document.getElementById("memorySyncRecover").addEventListener("click", () => {
        if (window.confirm("Merge authenticated remote memory with local changes? Revoked memories stay deleted. Review recovery backups before continuing.")) cloudAction("sync", {action:"recover",confirm:true}, "Authenticated conflict recovery completed. Review the retained records.");
    });
    document.getElementById("memoryReasoningForm").addEventListener("submit", event => {
        event.preventDefault();
        const enabled = document.getElementById("memoryReasoningEnabled").checked;
        cloudAction("reason", {enabled, consent: enabled, daily_tokens: Number(document.getElementById("memoryReasoningTokens").value), daily_microusd: Math.round(Number(document.getElementById("memoryReasoningDollars").value) * 1000000)}, "Reasoning policy saved. Each cloud request still requires consent.");
    });
    evaluationForm.addEventListener("submit", async event => {
        event.preventDefault();
        if (!active || evaluationPending) return;
        const ticket = generation;
        let submitted;
        try { submitted = boundedCases([...cases,...(query.value.trim() ? [editorCase()] : [])]); }
        catch (error) { evaluationFeedback.textContent = error.message; return; }
        const controller = new AbortController(); evaluationController = controller; evaluationPending = true; evaluationControls();
        let timedOut = false;
        // Transport grace does not extend the server's shared processing budget.
        const timer = setTimeout(() => { timedOut = true; controller.abort(); },75000);
        clearEvaluationResult(); evaluationForm.setAttribute("aria-busy","true"); evaluationFeedback.textContent = `Checking ${submitted.length} questions locally…`;
        try {
            const result = await Alfred.fetchJSON("/api/ai/memories/learning/", {method: "POST",signal:controller.signal,body:JSON.stringify({action:"evaluate",cases:submitted,min_score:Number(evaluationThreshold.value)})});
            if (!active || ticket !== generation) return;
            const percent = value => value === null ? "not applicable" : `${(value*100).toFixed(1)}%`;
            const single = result.cases !== 1 ? "" : result.negative_cases
                ? (result.false_positive_rate ? "Unexpected match returned. " : "No memory returned, as expected. ")
                : `Expected match in first three: ${result.recall_at_3 ? 'yes' : 'no'}. First match correct: ${result.top_1_accuracy ? 'yes' : 'no'}. `;
            quality.textContent = [
                `${single}${result.cases} questions. Precision: ${percent(result.precision)}. Recall: ${percent(result.recall)}.`,
                `Top match: ${percent(result.top_1_accuracy)}. First relevant rank score (1 is best): ${result.mean_reciprocal_rank === null ? 'not applicable' : result.mean_reciprocal_rank.toFixed(3)}.`,
                `Negative-case abstention: ${percent(result.abstention_rate)}. False positives: ${percent(result.false_positive_rate)}. Exact matches: ${percent(result.exact_match_rate)}.`,
                `Owner-checked citations: ${result.checked_citations}; record correctness: ${percent(result.citation_correctness)}.`,
                `Cohort: ${result.positive_cases} with expected matches, ${result.negative_cases} no-match questions.`
            ].join(" ");
            result.per_case.forEach(item => {
                const row = document.createElement("li"); row.className = "memory-card";
                const question = document.createElement("p"); question.textContent = submitted[item.case-1].query;
                const detail = document.createElement("p"); detail.textContent = `${item.exact_match ? 'Matches reviewed expectation' : 'Review retrieval'} · ${item.matched} relevant, ${item.irrelevant} unexpected, ${item.missed} missed · precision ${percent(item.precision)} · recall ${percent(item.recall)}${item.abstained ? ' · abstained' : ''}`;
                row.append(question,detail);
                item.citations.forEach(cite => {
                    if (!/^[a-f0-9]{32}$/.test(cite.id) || !currentMemories.has(cite.id)) throw new Error("Sources changed. Refresh memories and rerun; no current result can be shown.");
                    const reference = document.createElement("p"), link = document.createElement("a");
                    link.href = `/settings/#memory-${cite.id}`; link.textContent = currentMemories.get(cite.id); link.title = `Memory ${cite.id}`;
                    reference.append(link,document.createTextNode(` · rank ${cite.rank} · cosine ${cite.score.toFixed(3)} · ${cite.relevant ? 'relevant' : 'unexpected'}`)); row.append(reference);
                });
                evaluationDetails.append(row);
            });
            evaluationFeedback.textContent = "Owner and current-source checks passed for this run. Results measure your relevance labels, not truth or financial authority. No queries or results saved.";
        } catch (error) {
            if (active && ticket === generation) {
                clearEvaluationResult(); evaluationFeedback.textContent = `${timedOut ? 'Local evaluation timed out. No partial results are displayed.' : error.message} Question drafts are preserved.`;
                if ([401,403].includes(error.status)) { window.dispatchEvent(new Event("pagehide")); feedback.textContent = "Session is no longer available. Sign in or reload before continuing."; }
            }
        }
        finally {
            clearTimeout(timer);
            if (evaluationController === controller) { evaluationController = null; evaluationPending = false; evaluationForm.setAttribute("aria-busy","false"); evaluationControls(); }
        }
    });
    refresh().catch(error => message(error.message));
    window.addEventListener("pagehide", () => {
        active = false; generation++; list.replaceChildren(); candidates.replaceChildren(); feedback.textContent = ""; search.value = "";
        category.replaceChildren(); document.getElementById("memoryCount").textContent = "";
        evaluationController?.abort(); evaluationController = null; evaluationPending = false;
        evaluationForm.setAttribute("aria-busy","false"); editorNeedsReview = false;
        cases = []; currentMemories.clear(); previousExpected.clear(); evaluationCases.replaceChildren();
        expected.replaceChildren(); query.value = ""; clearEvaluationResult(); evaluationFeedback.textContent = ""; evaluationThreshold.value = ""; evaluationControls();
        document.getElementById("memorySyncStatus").textContent = "";
        document.getElementById("memoryReasoningStatus").textContent = "";
        document.getElementById("memorySyncDetails").textContent = ""; document.getElementById("memoryReasoningUsage").textContent = "";
        document.getElementById("memoryCloudFeedback").textContent = "";
        document.getElementById("memorySyncEnabled").checked = false;
        document.getElementById("memorySyncEnabled").disabled = true;
        document.getElementById("memorySyncNow").disabled = true;
        document.getElementById("memoryReasoningEnabled").checked = false;
        document.getElementById("memoryReasoningTokens").value = "";
        document.getElementById("memoryReasoningDollars").value = "";
    });
    window.addEventListener("pageshow", event => {
        active = true;
        if (event.persisted) refresh().catch(error => message(error.message));
    });
});
