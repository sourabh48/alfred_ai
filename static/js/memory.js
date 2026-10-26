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
    const hubPanel = document.getElementById("knowledgeHub"), hubPacks = document.getElementById("knowledgeHubPacks");
    const hubStatus = document.getElementById("knowledgeHubStatus"), hubFeedback = document.getElementById("knowledgeHubFeedback");
    const hubSources = document.getElementById("knowledgeHubSources"), hubParent = document.getElementById("knowledgeHubParent");
    let hubGeneration = 0, hubSessionGeneration = 0, hubReadController = null, hubActionController = null, hubBusy = false;
    async function hubRefresh() {
        if (!active) return;
        const ticket = ++hubGeneration;
        hubReadController?.abort(); hubReadController = new AbortController();
        const data = await Alfred.fetchJSON("/api/ai/memories/hub/", {signal: hubReadController.signal});
        if (!active || ticket !== hubGeneration) return;
        const selected = new Set([...hubSources.selectedOptions].map(option => option.value)), parent = hubParent.value;
        hubStatus.textContent = `Local learning revision ${data.revision}; durable checkpoint ${data.checkpoint}. ${data.pending ? 'Reviewed updates queued' : 'No reviewed updates queued'}. Failures ${data.failures}${data.conflict ? '; conflict needs operator review; history retained' : ''}.`;
        document.getElementById("knowledgeHubEnabled").checked = data.enabled;
        document.getElementById("knowledgeHubRemoteConsent").checked = data.remote_consent;
        hubSources.replaceChildren(); hubParent.replaceChildren(new Option("New pack", ""));
        data.sources.forEach(source => { const option = new Option(`${source.statement} · ${source.source}`, source.id); option.selected = selected.has(source.id); hubSources.append(option); });
        hubPacks.replaceChildren();
        if (!data.packs.length) hubPacks.textContent = "No knowledge packs. Select public source memories to prepare a draft.";
        data.packs.forEach(pack => {
            const row = document.createElement("article"); row.className = "memory-card"; row.dataset.packId = pack.id;
            const heading = document.createElement("h4"); heading.className = "h6"; heading.textContent = `Version ${pack.version} · ${pack.status}`;
            const integrity = document.createElement("p"); integrity.className = "small text-break"; integrity.textContent = `Digest ${pack.digest} · expires ${pack.expires_at}`;
            const entries = document.createElement("ul");
            pack.entries.forEach(entry => {
                const item = document.createElement("li"), citation = document.createElement("a");
                item.textContent = `${entry.statement} · `; citation.textContent = entry.source; citation.href = entry.citation; item.append(citation); entries.append(item);
            });
            row.append(heading, integrity, entries);
            if (pack.origin === "local") {
                if (pack.state === "promoted") hubParent.append(new Option(`Version ${pack.version} · ${pack.id.slice(0, 8)}`, pack.id));
                const label = document.createElement("label"), checked = document.createElement("input"); checked.type = "checkbox";
                label.append(checked, " I reviewed the exact text, citations, privacy and supplementary-data limits.");
                const promote = document.createElement("button"); promote.type = "button"; promote.className = "btn btn-outline-primary m-1"; promote.textContent = "Promote reviewed pack";
                promote.disabled = hubBusy || !data.enabled || pack.status !== "DRAFT";
                const withdraw = document.createElement("button"); withdraw.type = "button"; withdraw.className = "btn btn-outline-danger m-1"; withdraw.textContent = "Withdraw pack"; withdraw.disabled = hubBusy || pack.state === "withdrawn";
                const review = action => {
                    if (!checked.checked) { hubFeedback.textContent = "Review this pack and check its confirmation before continuing."; return; }
                    hubPerform({action, id: pack.id, digest: pack.digest, reviewed: true});
                };
                promote.addEventListener("click", () => review("promote")); withdraw.addEventListener("click", () => review("withdraw"));
                row.append(label, document.createElement("br"), promote, withdraw);
            }
            hubPacks.append(row);
        });
        if ([...hubParent.options].some(option => option.value === parent)) hubParent.value = parent;
        hubPanel.querySelectorAll("#knowledgeHubPolicy input, #knowledgeHubPolicy button, #knowledgeHubCheckpoint").forEach(node => { node.disabled = hubBusy; });
        hubPanel.querySelectorAll("#knowledgeHubDraft select, #knowledgeHubDraft button").forEach(node => { node.disabled = hubBusy || !data.enabled; });
        hubPanel.querySelectorAll("#knowledgeHubRemotePolicy input, #knowledgeHubRemotePolicy button").forEach(node => { node.disabled = hubBusy || !data.enabled || !data.remote_available; });
        document.getElementById("knowledgeHubSync").disabled = hubBusy || !data.remote_available || !data.remote_consent || !data.enabled;
        document.getElementById("knowledgeHubRefresh").disabled = hubBusy;
        const reconcile = document.getElementById("knowledgeHubReconcile");
        reconcile.hidden = !data.conflict || !data.review_head || !data.review_digest;
        document.getElementById("knowledgeHubReconcileLabel").hidden = reconcile.hidden;
        document.getElementById("knowledgeHubReconcileReviewed").checked = false;
        document.getElementById("knowledgeHubReconcileReviewed").disabled = hubBusy;
        reconcile.disabled = hubBusy || reconcile.hidden || !data.enabled || !data.remote_consent;
        reconcile.onclick = () => {
            if (!document.getElementById("knowledgeHubReconcileReviewed").checked) { hubFeedback.textContent = "Review cached remote packs before reconciling."; return; }
            hubPerform({action: "reconcile", head: data.review_head, digest: data.review_digest, reviewed: true});
        };
    }
    async function hubPerform(payload) {
        if (hubBusy || !active) return;
        hubBusy = true; hubFeedback.textContent = "Saving reviewed local state…";
        hubPanel.querySelectorAll("button,input,select").forEach(node => { node.disabled = true; });
        const controller = new AbortController(); hubActionController = controller;
        const sessionTicket = hubSessionGeneration;
        try {
            await Alfred.fetchJSON("/api/ai/memories/hub/", {method: "POST", body: JSON.stringify(payload), signal: controller.signal});
            if (!active || sessionTicket !== hubSessionGeneration) return;
            hubFeedback.textContent = payload.action === "draft" ? "Pack prepared. Review every statement before promotion." : "Local review saved. Remote uploads require separate authorization and consent.";
        } catch (error) {
            if (active && sessionTicket === hubSessionGeneration) { hubFeedback.textContent = `${error.message} Your selection is retained; refresh current sources before retrying.`; if ([401,403].includes(error.status)) window.dispatchEvent(new Event("pagehide")); }
        } finally {
            if (sessionTicket === hubSessionGeneration) {
                hubBusy = false; hubActionController = null;
                if (active) { document.getElementById("knowledgeHubRefresh").disabled = false; hubRefresh().catch(error => { if (active) hubStatus.textContent = error.message; }); }
            }
        }
    }
    document.getElementById("knowledgeHubPolicy").addEventListener("submit", event => { event.preventDefault(); hubPerform({action: "configure", enabled: document.getElementById("knowledgeHubEnabled").checked, consent: true}); });
    document.getElementById("knowledgeHubDraft").addEventListener("submit", event => { event.preventDefault(); const ids = [...hubSources.selectedOptions].map(option => option.value); if (ids.length > 8) { hubFeedback.textContent = "Select at most eight sources."; return; } hubPerform({action: "draft", ids, ...(hubParent.value ? {parent: hubParent.value} : {})}); });
    document.getElementById("knowledgeHubRemotePolicy").addEventListener("submit", event => { event.preventDefault(); hubPerform({action: "remote_consent", enabled: document.getElementById("knowledgeHubRemoteConsent").checked, consent: true}); });
    document.getElementById("knowledgeHubCheckpoint").addEventListener("click", () => hubPerform({action: "checkpoint"}));
    document.getElementById("knowledgeHubSync").addEventListener("click", () => hubPerform({action: "sync"}));
    document.getElementById("knowledgeHubRefresh").addEventListener("click", () => { hubRefresh().catch(error => { if (active) hubStatus.textContent = error.message; }); });
    const evaluationCases = document.getElementById("memoryEvaluationCases");
    const evaluationDetails = document.getElementById("memoryEvaluationDetails");
    const evaluationFeedback = document.getElementById("memoryEvaluationFeedback");
    const evaluationThreshold = document.getElementById("memoryEvaluationThreshold");
    const evaluationForm = document.getElementById("memoryEvaluationForm");
    const evaluationAdd = document.getElementById("memoryEvaluationAdd");
    const evaluationClear = document.getElementById("memoryEvaluationClear");
    const comparisonForm = document.getElementById("memoryComparisonForm"), comparisonStatus = document.getElementById("memoryComparisonStatus"), comparisonResults = document.getElementById("memoryComparisonResults");
    const baselineModel = document.getElementById("memoryComparisonBaseline"), candidateModel = document.getElementById("memoryComparisonCandidate");
    function comparisonSelect(id, text) {
        const label=document.createElement("label"), select=document.createElement("select");
        label.htmlFor=id; label.className="form-label"; label.textContent=text;
        select.id=id; select.className="form-select mb-2"; select.disabled=true; select.required=true;
        comparisonForm.insertBefore(label,comparisonForm.querySelector("button")); comparisonForm.insertBefore(select,comparisonForm.querySelector("button"));
        return select;
    }
    const comparisonSuite=comparisonSelect("memoryComparisonSuite","Fictional evaluation partition");
    const candidateProtocol=comparisonSelect("memoryComparisonProtocol","Candidate retrieval protocol (comparison only)");
    document.getElementById("memoryComparisonTitle").nextElementSibling.textContent="Development and independent held-out fictional cases test relevance, corrections, conflicting references and privacy guards. Held-out answers are evaluation-only: never tune from them. No private memory is read or trained on. Passing one partition is review evidence, never model activation or general accuracy.";
    let comparisonConfig=null;
    function comparisonPolicy() {
        if (!comparisonConfig) return;
        const suite=comparisonConfig.suite_options.find(item => item.id===comparisonSuite.value), policy=comparisonConfig.policy;
        document.getElementById("memoryComparisonPolicy").textContent=`${suite.cohorts} fictional cohorts, ${suite.cases} questions per model; ${suite.label}. Precision ≥ ${policy.min_precision}, recall ≥ ${policy.min_recall}, no-match abstention ≥ ${policy.min_abstention_rate}, citation identity = 1, owner violations = 0. Maximum metric drop: ${policy.max_metric_drop}. Installed models only; no download. ${comparisonConfig.seconds}-second shared budget. Baseline uses the unchanged default protocol.`;
    }
    comparisonSuite.addEventListener("change",comparisonPolicy);
    let comparisonController = null, comparisonEnabled = false;
    let cases = [], editingCase = null, currentMemories = new Map(), previousExpected = new Set([""]), editorNeedsReview = false, evaluationPending = false, evaluationController = null;
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
            const edit = document.createElement("button"); edit.type = "button"; edit.className = "btn btn-outline-secondary btn-sm me-2";
            edit.textContent = "Edit question"; edit.setAttribute("aria-label", `Edit question ${index+1}`);
            edit.addEventListener("click", () => {
                if (query.value.trim()) { evaluationFeedback.textContent = "Save or clear your current question draft before editing another case."; return; }
                editingCase = index; query.value = item.query;
                const missing = item.expected_ids.some(id => !currentMemories.has(id));
                [...expected.options].forEach(option => { option.selected = !missing && (item.expected_ids.length ? item.expected_ids.includes(option.value) : !option.value); });
                previousExpected = new Set([...expected.selectedOptions].map(option => option.value)); editorNeedsReview = missing;
                evaluationAdd.textContent = "Save question changes"; clearEvaluationResult(); evaluationControls(); query.focus();
                evaluationFeedback.textContent = missing ? "Expected sources changed. Explicitly review current sources before saving; the original case is retained." : `Editing question ${index+1}. Save changes before running.`;
            });
            const remove = document.createElement("button"); remove.type = "button"; remove.className = "btn btn-outline-secondary btn-sm";
            remove.textContent = "Remove question"; remove.setAttribute("aria-label", `Remove question ${index+1}`);
            remove.addEventListener("click", () => {
                cases.splice(index,1);
                if (editingCase === index) { editingCase = null; evaluationAdd.textContent = "Add question to run"; }
                else if (editingCase !== null && editingCase > index) editingCase--;
                clearEvaluationResult(); renderCases();
            });
            row.append(question,label,edit,remove); evaluationCases.append(row);
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
            const revised = [...cases], item = editorCase();
            if (editingCase === null) revised.push(item); else revised[editingCase] = item;
            cases = boundedCases(revised); editingCase = null; evaluationAdd.textContent = "Add question to run"; query.value = "";
            [...expected.options].forEach(option => { option.selected = !option.value; }); previousExpected = new Set([""]); editorNeedsReview = false;
            clearEvaluationResult(); renderCases(); evaluationFeedback.textContent = `${cases.length} questions added. No inference has run.`;
        } catch (error) { evaluationFeedback.textContent = error.message; }
    });
    evaluationClear.addEventListener("click", () => {
        cases = []; editingCase = null; evaluationAdd.textContent = "Add question to run"; query.value = ""; previousExpected = new Set([""]); editorNeedsReview = false;
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
        const comparisonCancelled = Boolean(comparisonController);
        comparisonController?.abort(); comparisonController=null; comparisonResults.replaceChildren();
        comparisonForm.setAttribute("aria-busy","false");
        comparisonForm.querySelectorAll("select,button").forEach(control => { control.disabled=!active || !comparisonEnabled; });
        if (comparisonCancelled) comparisonStatus.textContent="Comparison cancelled by refresh. Run again against the current view.";
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
        comparisonEnabled = review.comparison.enabled === true;
        [baselineModel,candidateModel].forEach(select => {
            const previous = select.value; select.replaceChildren();
            review.comparison.models.forEach(model => select.append(new Option(model,model)));
            if (review.comparison.models.includes(previous)) select.value = previous;
        });
        comparisonConfig=review.comparison;
        const previousSuite=comparisonSuite.value, previousProtocol=candidateProtocol.value;
        comparisonSuite.replaceChildren(); candidateProtocol.replaceChildren();
        comparisonConfig.suite_options.forEach(item => { const option=new Option(item.label+(item.available ? '' : ' — blocked: frozen policy unavailable'),item.id); option.disabled=!item.available; comparisonSuite.append(option); });
        comparisonConfig.protocols.forEach(protocol => candidateProtocol.append(new Option(protocol,protocol)));
        if (comparisonConfig.suite_options.some(item => item.id===previousSuite && item.available)) comparisonSuite.value=previousSuite;
        if (comparisonConfig.protocols.includes(previousProtocol)) candidateProtocol.value=previousProtocol;
        comparisonPolicy();
        comparisonForm.querySelectorAll("select,button").forEach(control => { control.disabled = !comparisonEnabled || Boolean(comparisonController); });
        if (!comparisonController) comparisonStatus.textContent = comparisonEnabled ? (comparisonCancelled ? "Comparison cancelled by refresh. Run again against the current view." : "Ready for a fictional local comparison; no runtime model will be changed.") : "Operator has not enabled synthetic model comparisons.";
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
        hubRefresh().catch(error => { if (active) hubStatus.textContent = error.message; });
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
        if (editingCase !== null) { evaluationFeedback.textContent = "Save question changes before running the evaluation."; return; }
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
            const context = result.retrieval_context;
            const single = result.cases !== 1 ? "" : result.negative_cases
                ? (result.false_positive_rate ? "Unexpected match returned. " : "No memory returned, as expected. ")
                : `Expected match in first three: ${result.recall_at_3 ? 'yes' : 'no'}. First match correct: ${result.top_1_accuracy ? 'yes' : 'no'}. `;
            quality.textContent = [
                `${single}${result.cases} questions. Precision: ${percent(result.precision)}. Recall: ${percent(result.recall)}.`,
                `Top match: ${percent(result.top_1_accuracy)}. First relevant rank score (1 is best): ${result.mean_reciprocal_rank === null ? 'not applicable' : result.mean_reciprocal_rank.toFixed(3)}.`,
                `Negative-case abstention: ${percent(result.abstention_rate)}. False positives: ${percent(result.false_positive_rate)}. Exact matches: ${percent(result.exact_match_rate)}.`,
                `Owner-checked citations: ${result.checked_citations}; record correctness: ${percent(result.citation_correctness)}.`,
                `Cohort: ${result.positive_cases} with expected matches, ${result.negative_cases} no-match questions.`,
                context.embedding_identity ? `Indexed model fingerprint: ${context.embedding_identity.slice(0,12)}; ${context.dimensions} dimensions; ${context.indexed_memories} memories.` : "No indexed model: empty memory vault.",
                "Compare only the same model, cutoff, reviewed questions and source revisions. This run alone cannot establish model drift."
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
    comparisonForm.addEventListener("submit", async event => {
        event.preventDefault();
        if (!active || !comparisonEnabled || comparisonController) return;
        const ticket = generation, controller = new AbortController(); comparisonController = controller;
        comparisonForm.querySelectorAll("select,button").forEach(control => { control.disabled = true; });
        comparisonForm.setAttribute("aria-busy","true"); comparisonResults.replaceChildren(); comparisonStatus.textContent = "Comparing fictional cohorts locally…";
        const timer = setTimeout(() => controller.abort(),135000);
        try {
            const result = await Alfred.fetchJSON("/api/ai/memories/learning/", {method:"POST",signal:controller.signal,body:JSON.stringify({action:"compare",baseline_model:baselineModel.value,candidate_model:candidateModel.value,suite:comparisonSuite.value,candidate_protocol:candidateProtocol.value})});
            if (!active || ticket !== generation) return;
            comparisonStatus.textContent = `${result.decision.replaceAll("_"," ")}. Active model unchanged. Fictional cohort evidence does not establish general accuracy or sustained drift.`;
            const execution=result.candidate_execution === 'baseline_reference_reused' ? 'one same-model reference; no independent candidate measured' : result.candidate_execution === 'independent_protocol_run' ? 'same installed model; independent protocol measurements with identical synthetic embeddings reused' : result.candidate_execution === 'independent_model_run' ? 'independent baseline and candidate measurements' : 'incomplete model evidence; no independent comparison established';
            const contract=document.createElement("p"); contract.textContent=`${result.suite === 'held_out' ? 'Independent held-out — evaluation only, no tuning' : 'Development — not independent acceptance'} · review contract ${result.cohort_id.slice(0,12)} · policy ${result.policy.version} · ${execution}. Only this partition was measured.`; comparisonResults.append(contract);
            if (result.suite === 'held_out') { const binding=document.createElement("p"); binding.textContent=`Retrieval source frozen at ${result.frozen_policy_commit.slice(0,12)} · SHA-256 ${result.frozen_policy_sha256.slice(0,12)}. New policy requires a new independent holdout.`; comparisonResults.append(binding); }
            result.reasons.forEach(reason => { const row=document.createElement("p"); row.textContent=reason.replaceAll("_"," "); comparisonResults.append(row); });
            (result.candidate?.results || []).forEach(cohort => {
                const row=document.createElement("article"); row.className="memory-card";
                const title=document.createElement("h4"); title.className="h6"; title.textContent=`${cohort.cohort}: ${cohort.cases} questions`;
                row.append(title);
                result.differences.filter(item => item.cohort===cohort.cohort).forEach(item => {
                    const line=document.createElement("p"); line.textContent=`${item.metric.replaceAll("_"," ")}: baseline ${(item.baseline*100).toFixed(1)}%, candidate ${(item.candidate*100).toFixed(1)}%, change ${(item.delta*100).toFixed(1)} percentage points.`; row.append(line);
                });
                const guard=document.createElement("p"); guard.textContent=`Owner violations: ${cohort.owner_violations}; foreign reference rejected: ${cohort.owner_reference_rejected}; stale source rejected: ${cohort.stale_rejected}.`; row.append(guard);
                const context=document.createElement("p"); context.textContent=`Indexed candidate model ${cohort.context.embedding_identity.slice(0,12)} · ${cohort.context.dimensions} dimensions. Source labels below belong only to this fictional contract.`; row.append(context);
                const ranking=document.createElement("p"); ranking.textContent=`Positive-case precision@k / recall@k: ${[1,2,3].map(k => `@${k}: ${(cohort.precision_at_k[k]*100).toFixed(1)}% / ${(cohort.recall_at_k[k]*100).toFixed(1)}%`).join('; ')}. Precision divides by k; recall divides by expected references. These differ from returned-reference precision above; sparse expected labels limit precision@3.`; row.append(ranking);
                const errors=document.createElement("p"), counts=cohort.retrieval_errors;
                errors.textContent=`Retrieval errors: ${counts.unexpected_references} unexpected references, ${counts.missed_references} missed references, ${counts.false_abstentions} false abstentions, ${counts.false_matches} false matches.`; row.append(errors);
                cohort.per_case.forEach(item => {
                    const detail=document.createElement("details"), title=document.createElement("summary"); title.textContent=`Case ${item.case}: ${item.matched} relevant, ${item.irrelevant} unexpected, ${item.missed} missed${item.abstained ? ', abstained' : ''}`;
                    const question=document.createElement("p"); question.textContent=`Fictional question: ${item.fictional_question}`;
                    const labels=document.createElement("p"); labels.textContent=`Expected: ${item.expected_sources.join(', ') || 'no match'}. Returned: ${item.returned_sources.join(', ') || 'no match'}. Unexpected: ${item.unexpected_sources.join(', ') || 'none'}. Missing: ${item.missing_sources.join(', ') || 'none'}.`;
                    detail.append(title,question,labels); row.append(detail);
                }); comparisonResults.append(row);
            });
        } catch (error) {
            if (active && ticket===generation) {
                comparisonResults.replaceChildren(); comparisonStatus.textContent=`Comparison incomplete: ${error.name === "AbortError" ? "processing stopped or timed out" : error.message}. No model changed.`;
                if ([401,403].includes(error.status)) window.dispatchEvent(new Event("pagehide"));
            }
        } finally {
            clearTimeout(timer);
            if (comparisonController===controller) { comparisonController=null; comparisonForm.setAttribute("aria-busy","false"); comparisonForm.querySelectorAll("select,button").forEach(control => { control.disabled=!active || !comparisonEnabled; }); }
        }
    });
    refresh().catch(error => message(error.message));
    window.addEventListener("pagehide", () => {
        hubGeneration++; hubSessionGeneration++; hubReadController?.abort(); hubActionController?.abort(); hubBusy = false; hubActionController = null;
        hubPacks.replaceChildren(); hubSources.replaceChildren(); hubParent.replaceChildren(); hubStatus.textContent = ""; hubFeedback.textContent = "";
        document.getElementById("knowledgeHubEnabled").checked = false; document.getElementById("knowledgeHubRemoteConsent").checked = false;
        hubPanel.querySelectorAll("button,input,select").forEach(node => { node.disabled = true; });
        active = false; generation++; list.replaceChildren(); candidates.replaceChildren(); feedback.textContent = ""; search.value = "";
        comparisonController?.abort(); comparisonController=null; comparisonEnabled=false; comparisonStatus.textContent=""; comparisonResults.replaceChildren(); baselineModel.replaceChildren(); candidateModel.replaceChildren(); document.getElementById("memoryComparisonPolicy").textContent="";
        comparisonConfig=null; comparisonSuite.replaceChildren(); candidateProtocol.replaceChildren();
        comparisonForm.setAttribute("aria-busy","false"); comparisonForm.querySelectorAll("select,button").forEach(control => { control.disabled=true; });
        category.replaceChildren(); document.getElementById("memoryCount").textContent = "";
        evaluationController?.abort(); evaluationController = null; evaluationPending = false;
        evaluationForm.setAttribute("aria-busy","false"); editorNeedsReview = false;
        cases = []; editingCase = null; evaluationAdd.textContent = "Add question to run"; currentMemories.clear(); previousExpected.clear(); evaluationCases.replaceChildren();
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
