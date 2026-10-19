document.addEventListener("DOMContentLoaded", () => {
    if (!document.getElementById("intelligencePanel")) return;
    const query = document.getElementById("intelligenceQuery");
    const scope = document.getElementById("intelligenceScope");
    const documentChoice = document.getElementById("intelligenceDocument");
    const statementChoice = document.getElementById("intelligenceStatement");
    const financialChoice = document.getElementById("intelligenceFinancial");
    const consent = document.getElementById("intelligenceCloudConsent");
    const feedback = document.getElementById("intelligenceFeedback");
    const answers = document.getElementById("intelligenceAnswers");
    const memoryText = document.getElementById("intelligenceMemoryText");
    const verified = document.getElementById("intelligenceMemoryVerified");
    const form = document.getElementById("intelligenceForm");
    const newConversation = document.getElementById("intelligenceNew");
    const retry = document.getElementById("intelligenceRetry");
    const empty = document.getElementById("intelligenceEmpty");
    const localStatus = document.getElementById("intelligenceLocalStatus");
    const historyForm = document.getElementById("conversationHistoryForm");
    const historyConsent = document.getElementById("conversationHistoryConsent");
    const historyDays = document.getElementById("conversationHistoryDays");
    const historyTitle = document.getElementById("conversationHistoryTitle");
    const historyList = document.getElementById("conversationHistoryList");
    const historyFeedback = document.getElementById("conversationHistoryFeedback");
    const historyCurrent = document.getElementById("conversationHistoryCurrent");
    const historyClear = document.getElementById("conversationHistoryClear");
    const historyDisable = document.getElementById("conversationHistoryDisable");
    const sourcePanel = document.getElementById("intelligenceSources");
    const sourceItems = document.getElementById("intelligenceSourceItems");
    const sourceStatus = document.getElementById("intelligenceSourcesStatus");
    const sourceSelected = document.getElementById("intelligenceSourcesSelected");
    const sourcePrevious = document.getElementById("intelligenceSourcesPrevious");
    const sourceNext = document.getElementById("intelligenceSourcesNext");
    const sourceRefresh = document.getElementById("intelligenceSourcesRefresh");
    const sourceReset = document.getElementById("intelligenceSourcesReset");
    let active = true, generation = 0, cloudAvailable = false, pending = false;
    let historyPolicy = null, conversation = null, requestToken = null, historyBlocked = false;
    let sourceRequest = 0, picker = null;
    function resetSources() {
        sourceRequest++; picker = null; sourcePanel.classList.add("d-none");
        sourceItems.replaceChildren(); sourceSelected.replaceChildren(); sourceStatus.textContent = "";
    }
    function sourceControls() {
        const locked = !active || pending || picker?.loading || picker?.blocked;
        form.querySelector('button[type="submit"]').disabled = !active || pending || Boolean(picker?.loading);
        sourcePrevious.disabled = locked || !picker?.index;
        sourceNext.disabled = locked || !picker?.next;
        sourceRefresh.disabled = !active || pending || picker?.loading;
        sourceReset.disabled = !active || pending || picker?.loading || picker?.blocked;
        sourceItems.querySelectorAll("input").forEach(input => { input.disabled = locked || input.dataset.selectable !== "true"; });
        sourceSelected.querySelectorAll("button").forEach(button => { button.disabled = locked; });
    }
    function renderSelection() {
        sourceSelected.replaceChildren();
        for (const item of picker.selected.values()) {
            const row = document.createElement("li"); row.className = "d-flex flex-wrap gap-2 align-items-center mb-2";
            const text = document.createElement("span"); text.textContent = item.name;
            const remove = document.createElement("button"); remove.type = "button"; remove.className = "btn btn-outline-secondary btn-sm";
            remove.textContent = "Remove"; remove.setAttribute("aria-label", `Remove ${item.name}`);
            remove.addEventListener("click", () => {
                picker.explicit = true; picker.selected.delete(item.document_id);
                const input = sourceItems.querySelector(`input[value="${item.document_id}"]`); if (input) input.checked = false;
                renderSelection();
            });
            row.append(text,remove); sourceSelected.append(row);
        }
        if (!picker.selected.size) {
            const item = document.createElement("li"); item.textContent = picker.explicit || picker.count > 5
                ? "No sources selected. Select a reviewed file before sending."
                : "Automatic review of all linked files (up to five); choose files to use explicit selection.";
            sourceSelected.append(item);
        }
        sourceStatus.textContent = `Page ${picker.index + 1} · ${picker.count} linked files · ${picker.selected.size}/5 selected. ${picker.count > 5 ? 'Explicit selection required.' : ''}`;
        sourceReset.textContent = picker.count > 5 ? "Clear selection" : "Use automatic sources";
        sourceControls();
    }
    async function loadSourcePage(cursor = null, index = 0) {
        if (!picker || pending || !active) return;
        const request = ++sourceRequest, state = picker, ticket = generation;
        state.loading = true; state.blocked = false; sourceStatus.textContent = "Checking source revisions…";
        sourcePanel.classList.remove("d-none"); sourcePanel.setAttribute("aria-busy", "true"); sourceControls();
        const [kind,id] = state.key.split(":");
        try {
            const page = await Alfred.fetchJSON(`/api/ai/financial-evidence/${kind}/${id}/documents/${cursor ? `?cursor=${encodeURIComponent(cursor)}` : ''}`);
            if (!active || ticket !== generation || request !== sourceRequest || picker !== state) return;
            if (!page.supported || !page.count) { state.count = 0; sourcePanel.classList.add("d-none"); return; }
            if (state.catalog && state.catalog !== page.catalog_token) throw Object.assign(new Error("The source list changed. Refresh and select current revisions."), {status:409});
            state.catalog = page.catalog_token; state.count = page.count; state.next = page.next_cursor; state.index = index;
            state.pages[index] = page.page_cursor; sourceItems.replaceChildren();
            page.items.forEach(item => {
                const row = document.createElement("li"); row.className = "mb-3";
                const label = document.createElement("label"); label.className = "d-flex gap-2 align-items-start";
                const input = document.createElement("input"); input.type = "checkbox"; input.value = item.document_id;
                input.dataset.selectable = String(item.selectable); input.checked = state.selected.has(item.document_id);
                const detail = document.createElement("span"); detail.textContent = `${item.name} · ${item.type.replaceAll('_',' ')} · uploaded ${new Date(item.uploaded_at).toLocaleDateString()} · ${item.verification.replaceAll('_',' ')} · ${item.freshness.replaceAll('_',' ')}`;
                input.addEventListener("change", () => {
                    if (input.checked && state.selected.size >= 5) { input.checked = false; sourceStatus.textContent = "Five-source limit reached. Remove a selected source first; your selection is preserved."; return; }
                    state.explicit = true;
                    if (input.checked) state.selected.set(item.document_id,item); else state.selected.delete(item.document_id);
                    renderSelection();
                });
                label.append(input,detail); row.append(label);
                const eligibility = document.createElement("p"); eligibility.className = "small mb-1";
                const grounding = item.grounding;
                eligibility.textContent = grounding?.status === "reviewed_fields_only"
                    ? `Eligible fields only: ${grounding.eligible_fields.map(field => field.replaceAll('_',' ')).join(', ')}. `
                    : `Not eligible: ${(grounding?.status || 'source_unavailable').replaceAll('_',' ')}. `;
                eligibility.append(document.createTextNode("Full-document Q&A is unsupported. Owner review is not bank/broker authentication; currency is not inferred. Sources are rechecked when sending."));
                row.append(eligibility);
                if (safeCitation(item.url)) { const link = document.createElement("a"); link.href = item.url; link.textContent = "Review source"; row.append(link); }
                sourceItems.append(row);
            });
            renderSelection();
        } catch (error) {
            if (!active || ticket !== generation || request !== sourceRequest || picker !== state) return;
            state.blocked = true; sourceStatus.textContent = `${error.message} Refresh the source list; your question draft is preserved.`;
            if ([401,403].includes(error.status)) forgetPrivatePage();
        } finally {
            if (picker === state && request === sourceRequest) { state.loading = false; sourcePanel.setAttribute("aria-busy", "false"); sourceControls(); }
        }
    }
    function ensureSources() {
        const key = active && scope.value === "financial_records" ? financialChoice.value : "";
        if (picker?.key === key) { sourceControls(); return; }
        resetSources();
        if (!key) return;
        picker = {key,loading:false,blocked:false,count:0,catalog:null,next:null,index:0,pages:[null],explicit:false,selected:new Map()};
        loadSourcePage();
    }
    sourcePrevious.addEventListener("click", () => loadSourcePage(picker.pages[picker.index - 1],picker.index - 1));
    sourceNext.addEventListener("click", () => loadSourcePage(picker.next,picker.index + 1));
    sourceRefresh.addEventListener("click", () => { resetSources(); ensureSources(); });
    sourceReset.addEventListener("click", () => {
        picker.selected.clear(); picker.explicit = picker.count > 5;
        sourceItems.querySelectorAll("input").forEach(input => { input.checked = false; }); renderSelection();
    });
    const historyEnabled = () => Boolean(historyPolicy?.available && historyPolicy.enabled);
    function updateHistoryControls() {
        const locked = !active || pending || !historyPolicy?.available;
        historyConsent.disabled = locked; historyDays.disabled = locked;
        historyForm.querySelector("button").disabled = locked;
        historyTitle.disabled = locked || !historyEnabled() || Boolean(conversation);
        historyClear.disabled = !active || pending || !historyPolicy?.conversations;
        historyDisable.disabled = !active || pending || !(historyPolicy?.enabled || historyPolicy?.conversations);
        historyList.querySelectorAll("button").forEach(button => { button.disabled = !active || pending; });
        historyCurrent.textContent = conversation ? `Saved locally: ${conversation.title} · expires ${new Date(conversation.expires_at).toLocaleString()}`
            : historyEnabled() ? "New local conversation · saved only after a successful local answer" : "Page-only conversation";
        updateScope(false);
    }
    function clearConversation(clearDraft = false) {
        generation++; conversation = null; requestToken = null; historyBlocked = false;
        resetSources();
        answers.replaceChildren(); empty.hidden = false; retry.hidden = true; consent.checked = false;
        if (clearDraft) { query.value = ""; historyTitle.value = ""; }
        updateHistoryControls();
    }
    function forgetPrivatePage() {
        active = false; generation++; conversation = null; historyPolicy = null; requestToken = null; historyBlocked = false;
        resetSources();
        answers.replaceChildren(); documentChoice.replaceChildren(); statementChoice.replaceChildren(); financialChoice.replaceChildren(); empty.hidden = false;
        historyList.replaceChildren(); historyTitle.value = ""; historyConsent.checked = false; historyDays.value = "7";
        query.value = ""; memoryText.value = ""; verified.checked = false; consent.checked = false;
        feedback.textContent = ""; historyFeedback.textContent = ""; retry.hidden = true;
        document.getElementById("conversationHistoryStatus").textContent = "Checking local policy";
        updateHistoryControls(); consent.disabled = true;
    }
    function applyHistory(data) {
        historyPolicy = data.policy;
        if (conversation && (!historyEnabled() || !(data.conversations || []).some(record => record.id === conversation.id))) {
            clearConversation();
            historyFeedback.textContent = "Conversation no longer available. Its displayed turns were cleared; your unsent draft is preserved.";
        }
        document.getElementById("conversationHistoryStatus").textContent = !historyPolicy.available
            ? "Unavailable · operator retention/recovery approval required" : historyEnabled() ? "On · local only" : "Off";
        if (historyPolicy.retention_days) historyDays.value = historyPolicy.retention_days;
        historyList.replaceChildren();
        (data.conversations || []).forEach(record => {
            const item = document.createElement("li"); item.className = "d-flex flex-wrap gap-2 align-items-center mb-2";
            const open = document.createElement("button"); open.type = "button"; open.className = "btn btn-outline-primary btn-sm";
            open.textContent = record.title; open.setAttribute("aria-label", `Reopen ${record.title}`);
            open.addEventListener("click", () => historyRequest(`/api/ai/conversations/${record.id}/`, {}, saved => {
                clearConversation(); conversation = saved;
                saved.turns.forEach(turn => renderTurn(turn, turn, generation, true));
                historyFeedback.textContent = "Historical hypotheses only. Reopen source records or ask again for current evidence. Your unsent draft is preserved.";
            }));
            const remove = document.createElement("button"); remove.type = "button"; remove.className = "btn btn-outline-danger btn-sm";
            remove.textContent = "Delete"; remove.setAttribute("aria-label", `Delete ${record.title}`);
            remove.addEventListener("click", () => {
                if (!confirm("Delete this conversation from current local history? Older backups may retain it.")) return;
                historyRequest(`/api/ai/conversations/${record.id}/`, {method:"DELETE"}, () => {
                    if (conversation?.id === record.id) clearConversation();
                    historyFeedback.textContent = "Conversation deleted locally. Older backups may retain copies.";
                }, true);
            });
            const age = document.createElement("span"); age.className = "small text-muted";
            age.textContent = `Expires ${new Date(record.expires_at).toLocaleString()}`;
            item.append(open, remove, age); historyList.append(item);
        });
        updateHistoryControls();
    }
    async function refreshHistory() {
        const ticket = generation;
        let data;
        try { data = await Alfred.fetchJSON("/api/ai/conversations/"); }
        catch (error) { if (active && ticket === generation && [401,403].includes(error.status)) forgetPrivatePage(); throw error; }
        if (active && ticket === generation) applyHistory(data);
    }
    async function historyRequest(url, options, completed, refresh = false) {
        if (pending || !active) return;
        const ticket = generation, askButton = form.querySelector('button[type="submit"]');
        pending = true; query.readOnly = true; askButton.disabled = true; answers.setAttribute("aria-busy", "true");
        updateHistoryControls(); newConversation.disabled = true;
        try {
            const data = await Alfred.fetchJSON(url, options);
            if (!active || ticket !== generation) return;
            completed(data);
            if (refresh) {
                historyPolicy = null;
                await refreshHistory().catch(error => { if (active) historyFeedback.textContent = `History status could not refresh. Reload before sending. ${error.message}`; });
            }
        } catch (error) {
            if (active && ticket === generation) {
                if ([401,403].includes(error.status)) forgetPrivatePage();
                historyFeedback.textContent = error.message;
            }
        }
        finally {
            pending = false; query.readOnly = false; askButton.disabled = !active;
            answers.setAttribute("aria-busy", "false"); newConversation.disabled = !active; updateHistoryControls();
        }
    }
    historyForm.addEventListener("submit", event => {
        event.preventDefault();
        historyRequest("/api/ai/conversations/policy/", {method:"PUT", body:JSON.stringify({enabled:true, consent:historyConsent.checked, days:Number(historyDays.value)})}, () => {
            historyConsent.checked = false;
            historyFeedback.textContent = "Local history choice saved. Earlier page-only messages are not imported.";
            clearConversation();
        }, true);
    });
    historyDisable.addEventListener("click", () => {
        if (!confirm("Disable history and clear all current local conversations? Backups may retain copies.")) return;
        historyRequest("/api/ai/conversations/policy/", {method:"PUT", body:JSON.stringify({enabled:false})}, () => {
            clearConversation(); historyConsent.checked = false; historyFeedback.textContent = "History disabled and cleared locally.";
        }, true);
    });
    historyClear.addEventListener("click", () => {
        if (!confirm("Clear all current local conversations? Your history choice stays on; backups may retain copies.")) return;
        historyRequest("/api/ai/conversations/clear/", {method:"POST", body:JSON.stringify({confirm:true})}, () => {
            clearConversation(); historyFeedback.textContent = "All current local conversations cleared. Backups may retain copies.";
        }, true);
    });
    function setLocalStatus(text, state) {
        localStatus.textContent = text; localStatus.dataset.state = state;
    }
    function updateScope(resetConsent = true) {
        const documents = scope.value === "documents";
        document.getElementById("intelligenceDocumentField").classList.toggle("d-none", !documents);
        documentChoice.disabled = !documents;
        const statements = scope.value === "bank_statements";
        document.getElementById("intelligenceStatementField").classList.toggle("d-none", !statements);
        statementChoice.disabled = !statements;
        const financial = scope.value === "financial_records";
        document.getElementById("intelligenceFinancialField").classList.toggle("d-none", !financial);
        financialChoice.disabled = !financial || pending || !active;
        ensureSources();
        if (resetConsent || scope.value !== "general" || !cloudAvailable || historyEnabled()) consent.checked = false;
        consent.disabled = scope.value !== "general" || !cloudAvailable || historyEnabled();
    }
    async function refreshControls() {
        const ticket = generation;
        const [insights, reasoning, history] = await Promise.all([Alfred.fetchJSON("/api/ai/personal-insights/?assistant_status=1"), Alfred.fetchJSON("/api/ai/memories/reason/"), Alfred.fetchJSON("/api/ai/conversations/")]);
        if (!active || ticket !== generation) return;
        applyHistory(history);
        documentChoice.replaceChildren(new Option("Choose verified evidence", ""));
        (insights.assistant_documents || []).forEach(item => documentChoice.append(new Option(item.label, item.id)));
        const selectedDocument = documentChoice.value || requestedDocument;
        if (/^[1-9]\d{0,15}$/.test(selectedDocument || "") && ![...documentChoice.options].some(option => option.value === selectedDocument)) {
            const record = await Alfred.fetchJSON(`/api/ai/closure-evidence/${selectedDocument}/`);
            if (!active || ticket !== generation) return;
            documentChoice.append(new Option(`Verified closure record #${record.record_id}`, record.record_id));
        }
        if ([...documentChoice.options].some(option => option.value === selectedDocument)) documentChoice.value = selectedDocument;
        const selectedStatement = statementChoice.value || requestedTransaction;
        statementChoice.replaceChildren(new Option("Choose a source transaction", ""));
        (insights.assistant_statement_records || []).forEach(item => statementChoice.append(new Option(item.label, item.id)));
        if (/^[1-9]\d{0,15}$/.test(selectedStatement || "") && ![...statementChoice.options].some(option => option.value === selectedStatement)) {
            const record = await Alfred.fetchJSON(`/api/ai/statement-evidence/${selectedStatement}/`);
            if (!active || ticket !== generation) return;
            statementChoice.append(new Option(`${record.statement.document_name} · ${record.current.transaction_date} · record #${record.transaction_id}`, record.transaction_id));
        }
        if ([...statementChoice.options].some(option => option.value === selectedStatement)) statementChoice.value = selectedStatement;
        const selectedFinancial = financialChoice.value || requestedFinancial;
        financialChoice.replaceChildren(new Option("Choose a canonical record", ""));
        (insights.assistant_financial_records || []).forEach(item => financialChoice.append(new Option(item.label, `${item.kind}:${item.id}`)));
        if (/^(expense|budget|loan|investment|baseline):[1-9]\d{0,15}$/.test(selectedFinancial || "") && ![...financialChoice.options].some(option => option.value === selectedFinancial)) {
            const [kind,id] = selectedFinancial.split(":");
            const record = await Alfred.fetchJSON(`/api/ai/financial-evidence/${kind}/${id}/`);
            if (!active || ticket !== generation) return;
            financialChoice.append(new Option(`${kind} record #${record.record_id}`, selectedFinancial));
        }
        if ([...financialChoice.options].some(option => option.value === selectedFinancial)) financialChoice.value = selectedFinancial;
        cloudAvailable = reasoning.provider_available && reasoning.policy.enabled;
        setLocalStatus(insights.local_model_status === "available" ? "Ollama available" : "Ollama unavailable", insights.local_model_status === "available" ? "ready" : "unavailable");
        document.getElementById("intelligenceCloudStatus").textContent = !reasoning.real_provider_enabled
            ? (cloudAvailable ? "Synthetic cloud testing · OpenAI disabled" : "OpenAI disabled")
            : (cloudAvailable ? "OpenAI · consent required per question" : "OpenAI · owner consent or configuration required");
        updateScope();
    }
    scope.addEventListener("change", updateScope);
    financialChoice.addEventListener("change", ensureSources);
    const requestedScope = new URLSearchParams(location.search).get("scope");
    const requestedTransaction = new URLSearchParams(location.search).get("transaction");
    const requestedDocument = new URLSearchParams(location.search).get("document");
    const requestedFinancial = `${new URLSearchParams(location.search).get("record_type")}:${new URLSearchParams(location.search).get("record_id")}`;
    if (["finance","travel","bank_statements","financial_records","documents"].includes(requestedScope)) scope.value = requestedScope;
    query.addEventListener("keydown", event => {
        if (event.key === "Enter" && (event.ctrlKey || event.metaKey) && !event.isComposing) { event.preventDefault(); form.requestSubmit(); }
    });
    retry.addEventListener("click", () => form.requestSubmit());
    newConversation.addEventListener("click", () => {
        if (pending) return;
        clearConversation(true);
        consent.checked = false; feedback.textContent = "New conversation. Previous messages cleared from this page."; retry.hidden = true; query.focus();
    });
    function safeCitation(url) {
        return ['/loans/','/expenses/','/mobility/'].includes(url) || /^\/settings\/#memory-[a-f0-9]{32}$/.test(url || "") || /^\/documents\/statements\/\d+\/transactions\/\d+\/$/.test(url || "") || /^\/documents\/(investments|loans)\/\d+\/records\/\d+\/$/.test(url || "") || /^\/documents\/loan-closures\/\d+\/$/.test(url || "") || /^\/ai\/financial-records\/(expense|budget|loan|investment|baseline)\/\d+\/$/.test(url || "");
    }
    function renderTurn(payload, result, ticket, historical = false) {
        const row = document.createElement("article");
        const userMessage = document.createElement("div"); userMessage.className = "conversation-message conversation-message--user";
        const userLabel = document.createElement("span"); userLabel.className = "conversation-label"; userLabel.textContent = "You";
        const question = document.createElement("p"); question.textContent = payload.query; userMessage.append(userLabel, question);
        const assistantMessage = document.createElement("div"); assistantMessage.className = "conversation-message mt-3";
        const label = document.createElement("span"); label.className = "conversation-label";
        label.textContent = result.provider === "local_evidence" ? "Local evidence check · no model used" : `AI hypothesis · ${result.provider === "ollama" ? "Ollama (local)" : result.provider === "mock" ? "Mock (synthetic)" : "Approved cloud"}`;
        const answer = document.createElement("p"); answer.textContent = result.answer;
        if (historical) label.textContent = `Historical AI hypothesis · Ollama (local) · saved ${new Date(result.saved_at).toLocaleString()}`;
        assistantMessage.append(label, answer); row.append(userMessage, assistantMessage);
        const evidence = document.createElement("details"); evidence.className = "conversation-evidence";
        const summary = document.createElement("summary"); summary.textContent = `Sources & evidence (${(result.sources || []).length})`;
        evidence.append(summary); assistantMessage.append(evidence);
        if (!result.sources?.length) { const note = document.createElement("p"); note.textContent = "Insufficient evidence for personal facts. This answer has no matching verified source."; evidence.append(note); }
        (result.sources || []).forEach(source => {
            const reference = document.createElement("p"); reference.textContent = `Source: ${source.ref} · ${source.classification}`;
            evidence.append(reference);
            const types = {owner_verified_statement:"Owner-confirmed memory", canonical_financial_baseline:"Canonical financial records (currency-limited)", canonical_record:"Canonical stored record · not independent authentication", owner_travel_preferences:"Your saved Travel preferences", verified_document_evidence:"Verified loan closure evidence", owner_confirmed_statement_record:"Owner-confirmed bank-statement record (not independently bank-authenticated)", unverified_statement_record:"Bank-statement record · source review required"};
            const description = document.createElement("p"); description.textContent = `${types[source.classification] || 'Source'} · ${source.verified_at ? `Checked ${new Date(source.verified_at).toLocaleString()}` : 'Verification timestamp not recorded'}`; evidence.append(description);
            if (historical) description.textContent = "Saved reference only; current existence and verification have not been checked.";
            if (!historical && source.source_file_status === "not_retained") {
                const note = document.createElement("p"); note.textContent = "Verified metadata record only; original source file is not retained. This does not prove independent bank authenticity."; evidence.append(note);
            }
            if (safeCitation(source.url)) {
                const link = document.createElement("a"); link.href = source.url; link.textContent = source.classification === "owner_verified_statement" ? "Review or correct this memory" : "Open source records"; evidence.append(link);
            }
            if (!historical) (source.data?.document_sources || []).forEach(item => {
                if (item.url === source.url || !safeCitation(item.url)) return;
                const reference = document.createElement("p");
                const link = document.createElement("a"); link.href = item.url; link.textContent = `Source document: ${item.name}`;
                reference.append(link,document.createTextNode(` · ${item.verification.replaceAll('_',' ')} · ${item.freshness.replaceAll('_',' ')}`)); evidence.append(reference);
            });
            if (!historical && source.data) Object.entries(source.data).forEach(([key, value]) => {
                if (["metric_states","amounts","document_sources","document_selection","applied_payment_source"].includes(key) || Object.hasOwn(source.data.amounts || {},key)) return;
                const fact = document.createElement("p");
                const monetary = source.classification === "canonical_financial_baseline" || key === "closure_amount";
                const display = value === null ? "Not recorded" : monetary && typeof value === "number" ? Alfred.formatCurrency(value) : (typeof value === "object" ? JSON.stringify(value) : String(value));
                const state = source.data.metric_states?.[key]?.status;
                fact.textContent = `${key.replaceAll("_", " ")}: ${display}${state ? ` (${state})` : ""}`;
                evidence.append(fact);
            });
            Object.entries(historical ? {} : source.data?.amounts || {}).forEach(([key,value]) => {
                const fact = document.createElement("p"); fact.className = "recorded-amount";
                fact.textContent = `${key.replaceAll('_',' ')}: ${Alfred.formatRecordedMoney(value)} · ${value.evidence_status}`;
                evidence.append(fact);
            });
        });
        answers.append(row); empty.hidden = true;
        const reviewButton = document.createElement("button"); reviewButton.type = "button"; reviewButton.className = "btn btn-outline-secondary btn-sm mt-3"; reviewButton.textContent = "Save answer as an unverified suggestion";
        reviewButton.addEventListener("click", async () => {
            reviewButton.disabled = true;
            try { await Alfred.fetchJSON("/api/ai/memories/learning/",{method:"POST",body:JSON.stringify({action:"extract",text:result.answer.replaceAll("\n"," "),provenance:{source:"owner-proposed AI hypothesis",source_refs:(result.sources || []).map(source=>source.ref)},sensitivity:"sensitive"})}); if (active && ticket===generation) feedback.textContent = "Suggestion saved for review in AI Memory. It is not a verified fact."; }
            catch (error) { if (active && ticket===generation) feedback.textContent = error.message; reviewButton.disabled = false; }
        });
        assistantMessage.append(reviewButton);
        reviewButton.hidden = historical || Boolean(result.narrative_withheld) || result.provider === "local_evidence";
        while (answers.children.length > 20) answers.firstElementChild.remove();
        evidence.open = true;
    }
    form.addEventListener("submit", async event => {
        event.preventDefault();
        if (pending) return;
        if (!historyPolicy || historyBlocked) { feedback.textContent = "Reopen the saved conversation or reload local history status before sending. Your draft is preserved."; return; }
        if (scope.value === "financial_records" && picker && (picker.loading || picker.blocked || ((picker.explicit || picker.count > 5) && !picker.selected.size))) {
            feedback.textContent = "Choose current reviewed source documents, or refresh the source list before sending. Your draft is preserved."; return;
        }
        const ticket = generation, button = event.target.querySelector('button[type="submit"]');
        pending = true; button.disabled = true; newConversation.disabled = true; query.readOnly = true; retry.hidden = true;
        updateHistoryControls();
        answers.setAttribute("aria-busy", "true");
        setLocalStatus("Local model processing", "processing");
        feedback.textContent = "ALFRED is processing locally.";
        const spinner = document.createElement("span"); spinner.className = "conversation-spinner me-2"; spinner.setAttribute("aria-hidden", "true"); feedback.prepend(spinner);
        button.textContent = "Thinking…";
        const payload = {query: query.value, scope: scope.value, cloud_consent: consent.checked, query_sensitivity: consent.checked ? "public" : "sensitive"};
        if (scope.value === "documents") payload.document_id = Number(documentChoice.value);
        if (scope.value === "bank_statements") payload.transaction_id = Number(statementChoice.value);
        if (scope.value === "financial_records") {
            const [kind,id] = financialChoice.value.split(":");
            payload.record_type = kind; payload.record_id = Number(id);
            if (picker?.explicit) {
                payload.selected_documents = [...picker.selected.values()].map(item => ({id:item.document_id,revision:item.revision}));
                payload.source_catalog = picker.catalog;
            }
        }
        try {
            if (historyEnabled()) {
                if (!conversation) conversation = await Alfred.fetchJSON("/api/ai/conversations/", {method:"POST", body:JSON.stringify({title:historyTitle.value.trim() || "Private conversation"})});
                if (!active || ticket !== generation) return;
                const fingerprint = JSON.stringify(payload);
                if (requestToken?.fingerprint !== fingerprint) requestToken = {fingerprint, id:crypto.randomUUID().replaceAll("-", "")};
                Object.assign(payload, {cloud_consent:false, conversation_id:conversation.id, conversation_revision:conversation.revision, request_id:requestToken.id});
            }
            const result = await Alfred.fetchJSON("/api/ai/personal-insights/", {method: "POST", body: JSON.stringify(payload)});
            if (!active || ticket !== generation) return;
            if (result.conversation) conversation.revision = result.conversation.revision;
            renderTurn(payload, result, ticket, Boolean(result.historical));
            feedback.textContent = result.retrieval_error?.detail || "Answer ready. Review the sources before acting.";
            if (result.narrative_withheld) feedback.textContent = `Unsupported model figures were withheld. Only source-card amounts are shown. ${result.retrieval_error?.detail || ''}`;
            if (result.provider === "local_evidence") {
                feedback.textContent = "Insufficient evidence. Review the source citation, then retry. Your draft is preserved; no model or cloud was used and no turn was saved.";
                setLocalStatus("Evidence review required · no model used", "review");
                retry.hidden = false;
            } else {
                setLocalStatus(result.provider === "ollama" ? "Ollama available" : "Ollama unavailable · consented fallback used", result.provider === "ollama" ? "ready" : "unavailable");
                query.value = ""; requestToken = null;
            }
            if (historyEnabled()) await refreshHistory().catch(() => { historyPolicy = null; historyFeedback.textContent = "Answer saved, but history status could not refresh. Reload before another question."; });
        } catch (error) {
            if (active && ticket === generation) {
                feedback.textContent = `${error.message}${error.reference ? ` Reference: ${error.reference}` : ""}`;
                retry.hidden = error.status === 409 || error.status === 429 || error.status === 400;
                if (error.code === "financial_sources_changed" && picker) {
                    picker.blocked = true; sourceStatus.textContent = "Selected evidence changed or is unavailable. Refresh the source list and select current revisions. Your draft is preserved.";
                } else if (error.status === 409 && conversation) {
                    historyBlocked = true; feedback.textContent += " Reopen this conversation to review newer turns; your draft is preserved.";
                    await refreshHistory().catch(() => { historyPolicy = null; });
                    if (active && !conversation) feedback.textContent = "Conversation no longer available. Displayed turns cleared; your draft is preserved for a new conversation.";
                }
                setLocalStatus(error.code === "local_model_unavailable" ? "Ollama unavailable" : "Local request did not complete", "unavailable");
                if (error.code === "reasoning_budget_reached") document.getElementById("intelligenceCloudStatus").textContent = "Cloud budget reached";
                if ([401,403].includes(error.status)) { forgetPrivatePage(); feedback.textContent = "Session or history permission is no longer available. Sign in or reload before continuing."; }
            }
        }
        finally { pending = false; consent.checked = false; button.disabled = !active; button.textContent = "Ask ALFRED"; newConversation.disabled = !active; query.readOnly = false; answers.setAttribute("aria-busy", "false"); updateHistoryControls(); }
    });
    document.getElementById("intelligenceMemoryForm").addEventListener("submit", async event => {
        event.preventDefault();
        if (!verified.checked) return;
        const ticket = generation, button = event.target.querySelector("button");
        button.disabled = true;
        try {
            await Alfred.fetchJSON("/api/ai/memories/", {method: "POST", body: JSON.stringify({content: {statement: memoryText.value}, provenance: {source: "owner verification in Insights"}, sensitivity: document.getElementById("intelligenceMemorySensitivity").value, verified: true})});
            if (!active || ticket !== generation) return;
            memoryText.value = ""; verified.checked = false;
            feedback.textContent = "Verified memory saved locally.";
        } catch (error) { if (active && ticket === generation) feedback.textContent = error.message; }
        finally { button.disabled = false; }
    });
    refreshControls().catch(error => { if (active) feedback.textContent = error.message; });
    window.addEventListener("pagehide", () => {
        forgetPrivatePage();
        document.getElementById("intelligenceMemorySensitivity").value = "sensitive";
    });
    window.addEventListener("pageshow", event => {
        active = true;
        if (event.persisted) refreshControls().catch(error => { if (active) feedback.textContent = error.message; });
    });
});
