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
    const historyRename = document.getElementById("conversationHistoryRename");
    const historySearch = document.getElementById("conversationHistorySearch");
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
    let pageDialogue = [];
    let registeredTools = [];
    const toolPolicy = document.getElementById('intelligenceToolPolicy');
    const toolList = document.getElementById('intelligenceToolsList');
    let streamRequest = null;
    const stopGeneration = document.getElementById('intelligenceStop');
    stopGeneration.addEventListener('click', () => streamRequest?.abort());
    let sourceRequest = 0, picker = null;
    const modelPanel=document.getElementById('modelReadinessPanel'), modelItems=document.getElementById('modelReadinessItems');
    const modelStatus=document.getElementById('modelReadinessStatus'), modelRefresh=document.getElementById('modelReadinessRefresh');
    let modelPending=false, modelLoaded=false;
    const mic = document.getElementById("intelligenceMic"), speechHint = document.getElementById("intelligenceSpeechHint");
    let speech = {listen:false, speak:false}, recording = null, player = null;
    async function refreshModelReadiness() {
        if (!active || modelPending) return;
        const ticket=generation;
        modelPending=true; modelRefresh.disabled=true; modelItems.replaceChildren();
        document.getElementById('modelReadinessScope').textContent='';
        modelStatus.textContent='Checking local registry gates…'; modelPanel.setAttribute('aria-busy','true');
        try {
            const data=await Alfred.fetchJSON('/api/ai/runtime-status/?serving_readiness=1');
            if (!active || ticket!==generation) return;
            for (const item of data.models) {
                const row=document.createElement('li'); row.className='mb-3';
                const title=document.createElement('strong'); title.textContent=`${item.name} · ${item.registry_eligible ? 'Registry eligible' : item.status==='fallback' ? 'Fallback' : 'Unavailable'}`;
                const reason=document.createElement('p'); reason.className='mb-1'; reason.textContent=item.reason;
                const fallback=document.createElement('p'); fallback.className='small mb-0'; fallback.textContent=`Fallback: ${item.fallback}`;
                row.append(title,reason,fallback); modelItems.append(row);
            }
            document.getElementById('modelReadinessScope').textContent=data.scope;
            modelStatus.textContent=`Registry checked ${new Date(data.checked_at).toLocaleString()}. Recheck to see current gates.`; modelLoaded=true;
        } catch(error) {
            if (!active || ticket!==generation) return;
            if ([401,403].includes(error.status)) forgetPrivatePage();
            modelStatus.textContent=`${error.message} Readiness is unknown; no model was activated.`;
        } finally { modelPending=false; modelRefresh.disabled=!active; modelPanel.setAttribute('aria-busy','false'); }
    }
    modelPanel.addEventListener('toggle',()=>{if(modelPanel.open && !modelLoaded) refreshModelReadiness();});
    modelRefresh.addEventListener('click',refreshModelReadiness);
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
            const text = document.createElement("span"); text.textContent = picker.documentMode ? `${item.record_type} record #${item.record_id} · ${item.name}` : item.name;
            const remove = document.createElement("button"); remove.type = "button"; remove.className = "btn btn-outline-secondary btn-sm";
            remove.textContent = "Remove"; remove.setAttribute("aria-label", `Remove ${text.textContent}`);
            remove.addEventListener("click", () => {
                const identity = picker.documentMode ? item.record_id : item.document_id;
                picker.explicit = true; picker.selected.delete(identity);
                const input = sourceItems.querySelector(`input[value="${identity}"]`); if (input) input.checked = false;
                renderSelection();
            });
            row.append(text,remove); sourceSelected.append(row);
        }
        if (!picker.selected.size) {
            const item = document.createElement("li"); item.textContent = picker.explicit || picker.count > 5
                ? (picker.documentMode ? "No records selected. Select reviewed records before sending." : "No sources selected. Select a reviewed file before sending.")
                : "Automatic review of all linked files (up to five); choose files to use explicit selection.";
            sourceSelected.append(item);
        }
        sourceStatus.textContent = `Page ${picker.index + 1} · ${picker.count} linked ${picker.documentMode ? 'records' : 'files'} · ${picker.selected.size}/${picker.limit} selected. ${picker.documentMode || picker.count > 5 ? 'Explicit selection required.' : ''}`;
        sourceReset.textContent = picker.documentMode || picker.count > 5 ? "Clear selection" : "Use automatic sources";
        sourceControls();
    }
    async function loadSourcePage(cursor = null, index = 0) {
        if (!picker || pending || !active) return;
        const request = ++sourceRequest, state = picker, ticket = generation;
        state.loading = true; state.blocked = false; sourceStatus.textContent = "Checking source revisions…";
        sourcePanel.classList.remove("d-none"); sourcePanel.setAttribute("aria-busy", "true"); sourceControls();
        const [kind,id] = state.key.split(":");
        try {
            const path = state.documentMode ? `/api/ai/financial-documents/${kind}/${id}/` : `/api/ai/financial-evidence/${kind}/${id}/documents/`;
            const page = await Alfred.fetchJSON(`${path}${cursor ? `?cursor=${encodeURIComponent(cursor)}` : ''}`);
            if (!active || ticket !== generation || request !== sourceRequest || picker !== state) return;
            if ((!state.documentMode && !page.supported) || !page.count) {
                state.count = 0;
                if (state.documentMode) { state.blocked = true; sourceItems.replaceChildren(); sourceStatus.textContent = "No supported linked records. Choose another document in Documents; no evidence can be inferred."; }
                else sourcePanel.classList.add("d-none");
                return;
            }
            if (state.catalog && state.catalog !== page.catalog_token) throw Object.assign(new Error("The source list changed. Refresh and select current revisions."), {status:409});
            state.catalog = page.catalog_token; state.count = page.count; state.next = page.next_cursor; state.index = index;
            state.pages[index] = page.page_cursor; sourceItems.replaceChildren();
            if (state.documentMode) document.getElementById("intelligenceFinancialDocumentContext").textContent = `${page.document_name} · ${kind} import · reviewed fields only. Answers are page-only, not saved to history. No totals, inferred currency or arbitrary PDF questions.`;
            page.items.forEach(item => {
                const row = document.createElement("li"); row.className = "mb-3";
                const label = document.createElement("label"); label.className = "d-flex gap-2 align-items-start";
                const identity = state.documentMode ? item.record_id : item.document_id;
                const input = document.createElement("input"); input.type = "checkbox"; input.value = identity;
                input.dataset.selectable = String(item.selectable); input.checked = state.selected.has(identity);
                const detail = document.createElement("span"); detail.textContent = `${state.documentMode ? `${item.record_type} record #${item.record_id} · ` : ''}${item.name || 'Source unavailable'} · ${(item.type || kind).replaceAll('_',' ')} · uploaded ${item.uploaded_at ? new Date(item.uploaded_at).toLocaleDateString() : 'not recorded'} · ${(item.verification || 'unavailable').replaceAll('_',' ')} · ${(item.freshness || 'unavailable').replaceAll('_',' ')}`;
                input.addEventListener("change", () => {
                    if (input.checked && state.selected.size >= state.limit) { input.checked = false; sourceStatus.textContent = `${state.documentMode ? 'Three-record' : 'Five-source'} limit reached. Remove a selected source first; your selection is preserved.`; return; }
                    state.explicit = true;
                    if (input.checked) state.selected.set(identity,item); else state.selected.delete(identity);
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
        const documentMode = scope.value === "financial_document";
        const key = active ? (documentMode ? requestedDocumentKey : scope.value === "financial_records" ? financialChoice.value : "") : "";
        if (picker?.key === key && picker?.documentMode === documentMode) { sourceControls(); return; }
        if (pending) { sourceControls(); return; }
        resetSources();
        if (!key) return;
        document.getElementById("intelligenceSourcesTitle").textContent = documentMode ? "Choose reviewed records from this document" : "Choose financial source documents";
        document.getElementById("intelligenceSourcesHelp").textContent = documentMode ? "Select one to three current reviewed records across pages. No records are chosen automatically; only reviewed fields from this document are used. Owner review does not establish independent authenticity." : "Browse every linked source. Select one to five reviewed files across pages. Only selected revisions will be used; other files are not silently included. Owner confirmation is not independent authentication.";
        picker = {key,documentMode,limit:documentMode ? 3 : 5,loading:false,blocked:false,count:0,catalog:null,next:null,index:0,pages:[null],explicit:documentMode,selected:new Map()};
        loadSourcePage();
    }
    sourcePrevious.addEventListener("click", () => loadSourcePage(picker.pages[picker.index - 1],picker.index - 1));
    sourceNext.addEventListener("click", () => loadSourcePage(picker.next,picker.index + 1));
    sourceRefresh.addEventListener("click", () => { resetSources(); ensureSources(); });
    sourceReset.addEventListener("click", () => {
        picker.selected.clear(); picker.explicit = picker.documentMode || picker.count > 5;
        sourceItems.querySelectorAll("input").forEach(input => { input.checked = false; }); renderSelection();
    });
    const historyEnabled = () => Boolean(historyPolicy?.available && historyPolicy.enabled);
    function updateHistoryControls() {
        const locked = !active || pending || !historyPolicy?.available;
        historyConsent.disabled = locked; historyDays.disabled = locked;
        historyForm.querySelector("button").disabled = locked;
        historyTitle.disabled = locked || !historyEnabled();
        historyRename.disabled = locked || !historyEnabled() || !conversation;
        historySearch.disabled = locked || !historyEnabled();
        historyClear.disabled = !active || pending || !historyPolicy?.conversations;
        historyDisable.disabled = !active || pending || !(historyPolicy?.enabled || historyPolicy?.conversations);
        historyList.querySelectorAll("button").forEach(button => { button.disabled = !active || pending; });
        updateScope(false);
    }
    function clearConversation(clearDraft = false) {
        streamRequest?.abort();
        generation++; conversation = null; requestToken = null; historyBlocked = false;
        pageDialogue = [];
        resetSources();
        answers.replaceChildren(); empty.hidden = false; retry.hidden = true; consent.checked = false;
        if (clearDraft) { query.value = ""; historyTitle.value = ""; }
        updateHistoryControls();
    }
    function forgetPrivatePage() {
        streamRequest?.abort();
        active = false; generation++; conversation = null; historyPolicy = null; requestToken = null; historyBlocked = false;
        pageDialogue = [];
        resetSources();
        answers.replaceChildren(); documentChoice.replaceChildren(); statementChoice.replaceChildren(); financialChoice.replaceChildren(); empty.hidden = false;
        document.getElementById("intelligenceFinancialDocumentContext").textContent = "";
        historyList.replaceChildren(); historyTitle.value = ""; historySearch.value = "";
        document.getElementById("conversationHistoryMatches").textContent = "";
        historyConsent.checked = false; historyDays.value = "7";
        query.value = ""; memoryText.value = ""; verified.checked = false; consent.checked = false;
        modelItems.replaceChildren(); modelLoaded=false; modelRefresh.disabled=true;
        document.getElementById('modelReadinessScope').textContent=''; modelStatus.textContent='Reopen to check current registry gates.';
        feedback.textContent = ""; historyFeedback.textContent = ""; retry.hidden = true;
        document.getElementById("conversationHistoryStatus").textContent = "Checking local policy";
        updateHistoryControls(); consent.disabled = true;
    }
    function applyHistory(data) {
        historyPolicy = data.policy;
        if (!historyEnabled()) historySearch.value = "";
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
                historyTitle.value = saved.title;
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
        filterHistory();
        updateHistoryControls();
    }
    function filterHistory() {
        const term = historySearch.value.trim().toLocaleLowerCase();
        let matches = 0;
        historyList.querySelectorAll("li").forEach(item => {
            const match = item.firstElementChild.textContent.toLocaleLowerCase().includes(term);
            item.classList.toggle("d-none", !match);
            if (match) matches++;
        });
        document.getElementById("conversationHistoryMatches").textContent = historyEnabled()
            ? `Showing ${matches} of ${historyList.children.length} saved titles. Search stays on this page.` : "";
    }
    historySearch.addEventListener("input", filterHistory);
    function dialogueSnippet(text) {
        const encoder = new TextEncoder(); let snippet = "", size = 0;
        for (const character of text) {
            const bytes = encoder.encode(character).length;
            if (size + bytes > 768) break;
            snippet += character; size += bytes;
        }
        return snippet;
    }
    document.getElementById("conversationTitleForm").addEventListener("submit", event => {
        event.preventDefault();
        if (!conversation || !historyEnabled()) return;
        historyRequest(`/api/ai/conversations/${conversation.id}/`, {method:"PATCH",body:JSON.stringify({title:historyTitle.value,revision:conversation.revision})}, saved => {
            conversation = {...conversation,...saved}; requestToken = null;
            historyFeedback.textContent = "Title saved locally. The transcript and original expiry are unchanged.";
        }, true);
    });
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
                if (error.status === 409 && conversation) {
                    historyBlocked = true;
                    historyFeedback.textContent += " Reopen the conversation before another change. Your draft is preserved.";
                }
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
        const tool = active ? registeredTools.find(item => item.scope === scope.value) : null;
        toolPolicy.textContent = !active ? 'Tool access is unavailable. Sign in or reload to check your session.' : scope.value === 'general'
            ? "Choose local records to include a module's evidence for this question."
            : tool ? `Selected data tool: ${tool.title}. Reads only your records; does not change them or contact external providers.`
            : 'Tool permission details are unavailable. Source reads still require server checks; reload to recheck permissions.';
        toolPolicy.dataset.tool = tool?.name || '';
        if (active && scope.value === 'career') toolPolicy.textContent += ' Page-only progress snapshot; saved stages do not verify submissions. Open Career to review or update them.';
        scope.disabled = !active || pending;
        const documents = scope.value === "documents";
        document.getElementById("intelligenceDocumentField").classList.toggle("d-none", !documents);
        documentChoice.disabled = !documents || pending || !active;
        const statements = scope.value === "bank_statements";
        document.getElementById("intelligenceStatementField").classList.toggle("d-none", !statements);
        statementChoice.disabled = !statements || pending || !active;
        const financial = scope.value === "financial_records";
        document.getElementById("intelligenceFinancialField").classList.toggle("d-none", !financial);
        financialChoice.disabled = !financial || pending || !active;
        const documentQuestion = scope.value === "financial_document";
        document.getElementById("intelligenceFinancialDocumentField").classList.toggle("d-none", !documentQuestion);
        historyCurrent.textContent = documentQuestion ? "Document questions are page-only · never saved to conversation history"
            : scope.value === 'career' ? 'Career progress is page-only · never saved to conversation history'
            : conversation ? `Saved locally: ${conversation.title} · expires ${new Date(conversation.expires_at).toLocaleString()}`
            : historyEnabled() ? "New local conversation · saved only after a successful local answer" : "Page-only conversation";
        ensureSources();
        if (resetConsent || scope.value !== "general" || !cloudAvailable || historyEnabled()) consent.checked = false;
        consent.disabled = scope.value !== "general" || !cloudAvailable || historyEnabled();
    }
    async function refreshControls() {
        const ticket = generation;
        cloudAvailable = false; consent.checked = false; consent.disabled = true;
        // Cloud policy status must not gate independent owner-only source browsing.
        const [insights, history, policy, tools] = await Promise.all([
            Alfred.fetchJSON("/api/ai/personal-insights/?assistant_status=1"),
            Alfred.fetchJSON("/api/ai/conversations/").catch(error => {
                // One local read retry covers transient cold-vault contention; auth errors never retry.
                if (active && ticket === generation && error.status === 503) return Alfred.fetchJSON("/api/ai/conversations/");
                throw error;
            }).then(data => ({data}), error => ({error})),
            Alfred.fetchJSON("/api/ai/memories/reason/").then(data => ({data}), error => ({error})),
            Alfred.fetchJSON('/api/ai/tools/').then(data => ({data}), error => ({error}))
        ]);
        if (!active || ticket !== generation) return;
        if ([policy.error,history.error,tools.error].some(error => error && [401,403].includes(error.status))) {
            forgetPrivatePage(); feedback.textContent = "Session or policy permission is no longer available. Sign in or reload before continuing."; return;
        }
        const reasoning = policy.data;
        registeredTools = Array.isArray(tools.data?.tools) ? tools.data.tools : [];
        toolList.replaceChildren();
        registeredTools.forEach(tool => {
            const item = document.createElement('li'); item.textContent = `${tool.title} · Read only · Your records only`;
            toolList.append(item);
        });
        if (!registeredTools.length) { const item = document.createElement('li'); item.textContent = 'Tool permissions are unavailable. Reload to retry.'; toolList.append(item); }
        if (history.data) applyHistory(history.data);
        else {
            historyPolicy=null; historyBlocked=true; conversation=null; requestToken=null;
            historyList.replaceChildren(); updateHistoryControls();
            document.getElementById('conversationHistoryStatus').textContent='Unavailable · reload to recheck';
            historyFeedback.textContent='History is unavailable. Sources remain browsable; reload before asking a question. Your draft is preserved.';
        }
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
        cloudAvailable = Boolean(reasoning?.provider_available && reasoning.policy.enabled);
        setLocalStatus(insights.local_model_status === "available" ? "Ollama available" : "Ollama unavailable", insights.local_model_status === "available" ? "ready" : "unavailable");
        document.getElementById("intelligenceCloudStatus").textContent = !reasoning ? "Cloud policy unavailable · cloud disabled" : !reasoning.real_provider_enabled
            ? (cloudAvailable ? "Synthetic cloud testing · OpenAI disabled" : "OpenAI disabled")
            : (cloudAvailable ? "OpenAI · consent required per question" : "OpenAI · owner consent or configuration required");
        if (policy.error) feedback.textContent = `${policy.error.message} Cloud is disabled. Reload to recheck its policy; local sources remain available.`;
        updateScope();
    }
    scope.addEventListener("change", updateScope);
    financialChoice.addEventListener("change", ensureSources);
    const requestedScope = new URLSearchParams(location.search).get("scope");
    const requestedTransaction = new URLSearchParams(location.search).get("transaction");
    const requestedDocument = new URLSearchParams(location.search).get("document");
    const requestedFinancial = `${new URLSearchParams(location.search).get("record_type")}:${new URLSearchParams(location.search).get("record_id")}`;
    const documentKind = new URLSearchParams(location.search).get("record_type"), documentId = new URLSearchParams(location.search).get("document_id");
    const requestedDocumentKey = /^(expense|loan|investment)$/.test(documentKind || "") && /^[1-9]\d*$/.test(documentId || "") && Number.isSafeInteger(Number(documentId)) ? `${documentKind}:${documentId}` : "";
    if (["finance","travel","career","bank_statements","financial_records","financial_document","documents"].includes(requestedScope)) scope.value = requestedScope;
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
        return ['/career/','/loans/','/expenses/','/mobility/'].includes(url) || /^\/settings\/#memory-[a-f0-9]{32}$/.test(url || "") || /^\/documents\/statements\/\d+\/transactions\/\d+\/$/.test(url || "") || /^\/documents\/(investments|loans)\/\d+\/records\/\d+\/$/.test(url || "") || /^\/documents\/loan-closures\/\d+\/$/.test(url || "") || /^\/ai\/financial-records\/(expense|budget|loan|investment|baseline)\/\d+\/$/.test(url || "");
    }
    function renderTurn(payload, result, ticket, historical = false) {
        const row = document.createElement("article");
        const userMessage = document.createElement("div"); userMessage.className = "conversation-message conversation-message--user";
        const userLabel = document.createElement("span"); userLabel.className = "conversation-label"; userLabel.textContent = "You";
        const question = document.createElement("p"); question.textContent = payload.query; userMessage.append(userLabel, question);
        const assistantMessage = document.createElement("div"); assistantMessage.className = "conversation-message mt-3";
        const label = document.createElement("span"); label.className = "conversation-label";
        label.textContent = result.grounding === "canonical_record_overview" ? "Recorded sources · AI unavailable" : result.provider === "local_evidence" ? "Local evidence check · no model used" : `AI hypothesis · ${result.provider === "ollama" ? "Ollama (local)" : result.provider === "mock" ? "Mock (synthetic)" : "Approved cloud"}`;
        const answer = result.provider !== 'local_evidence' && !result.narrative_withheld
            ? Alfred.renderAnswerMarkdown(result.answer) : document.createElement('p');
        if (result.provider === 'local_evidence' || result.narrative_withheld) answer.textContent = result.answer;
        if (historical) label.textContent = `Historical AI hypothesis · Ollama (local) · saved ${new Date(result.saved_at).toLocaleString()}`;
        assistantMessage.append(label, answer); row.append(userMessage, assistantMessage);
        const evidence = document.createElement("details"); evidence.className = "conversation-evidence";
        const summary = document.createElement("summary"); summary.textContent = `Sources & evidence (${(result.sources || []).length})`;
        evidence.append(summary); assistantMessage.append(evidence);
        if (!result.sources?.length) { const note = document.createElement("p"); note.textContent = "Insufficient evidence for personal facts. This answer has no matching verified source."; evidence.append(note); }
        (result.sources || []).forEach(source => {
            const reference = document.createElement("p"); reference.textContent = `Source: ${source.ref} · ${source.classification}`;
            evidence.append(reference);
            const types = {owner_reviewed_document_record:"Owner-reviewed document fields · not independent authentication", owner_verified_statement:"Owner-confirmed memory", canonical_financial_baseline:"Canonical financial records (currency-limited)", canonical_record:"Canonical stored record · not independent authentication", owner_travel_preferences:"Your saved Travel preferences", verified_document_evidence:"Verified loan closure evidence", owner_confirmed_statement_record:"Owner-confirmed bank-statement record (not independently bank-authenticated)", unverified_statement_record:"Bank-statement record · source review required"};
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
                if (['limitations','progress','recent_opportunities'].includes(key) && Array.isArray(value) && value.every(item => typeof item === 'string')) {
                    fact.textContent = `${key.replaceAll('_',' ')}: ${value.length ? '' : 'None recorded'}`;
                    evidence.append(fact);
                    if (value.length) {
                        const list = document.createElement('ul');
                        value.forEach(text => { const item = document.createElement('li'); item.textContent = text; list.append(item); });
                        evidence.append(list);
                    }
                    return;
                }
                const display = value === null ? "Not recorded" : (typeof value === "object" ? JSON.stringify(value) : String(value));
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
        assistantMessage.append(reviewButton, readAloudButton(result.answer));
        reviewButton.hidden = historical || Boolean(result.narrative_withheld) || result.provider === "local_evidence";
        while (answers.children.length > 20) answers.firstElementChild.remove();
        evidence.open = true;
    }
    function renderActionProposal(text, result) {
        // AI-17: a proposed change is shown with its exact values; only Confirm saves it.
        const row = document.createElement("article"); row.dataset.actionProposal = "true";
        const userMessage = document.createElement("div"); userMessage.className = "conversation-message conversation-message--user";
        const userLabel = document.createElement("span"); userLabel.className = "conversation-label"; userLabel.textContent = "You";
        const question = document.createElement("p"); question.textContent = text; userMessage.append(userLabel, question);
        const reply = document.createElement("div"); reply.className = "conversation-message mt-3";
        const label = document.createElement("span"); label.className = "conversation-label"; label.textContent = "Action review · no model used";
        const summary = document.createElement("p"); summary.textContent = result.proposal ? result.proposal.summary : result.detail;
        reply.append(label, summary); row.append(userMessage, reply);
        if (result.proposal) {
            const status = document.createElement("p"); status.className = "small"; status.setAttribute("role", "status");
            status.textContent = `Review the exact values above. This proposal expires at ${new Date(result.proposal.expires_at).toLocaleTimeString()}.`;
            const actions = document.createElement("div"); actions.className = "d-flex gap-2";
            const confirmButton = document.createElement("button"); confirmButton.type = "button"; confirmButton.className = "btn btn-primary btn-sm"; confirmButton.textContent = "Confirm";
            const cancelButton = document.createElement("button"); cancelButton.type = "button"; cancelButton.className = "btn btn-outline-secondary btn-sm"; cancelButton.textContent = "Cancel";
            const finish = message => { actions.remove(); status.textContent = message; status.tabIndex = -1; status.focus(); };
            confirmButton.addEventListener("click", async () => {
                confirmButton.disabled = cancelButton.disabled = true;
                try {
                    const {proposal_id, action, fields} = result.proposal;
                    const saved = await Alfred.fetchJSON("/api/ai/actions/confirm/", {method:"POST", body:JSON.stringify({proposal_id, action, fields, confirmed:true})});
                    finish(saved.message);
                    const link = document.createElement("a"); link.href = saved.url; link.textContent = "Open Budgets"; status.append(" ", link);
                } catch (error) { confirmButton.disabled = cancelButton.disabled = false; status.textContent = `${error.message} Retry this same card safely, or check Budgets.`; }
            });
            cancelButton.addEventListener("click", async () => {
                confirmButton.disabled = cancelButton.disabled = true;
                try {
                    const cancelled = await Alfred.fetchJSON("/api/ai/actions/cancel/", {method:"POST", body:JSON.stringify({proposal_id:result.proposal.proposal_id})});
                    finish(cancelled.message);
                } catch (error) { confirmButton.disabled = cancelButton.disabled = false; status.textContent = error.message; }
            });
            actions.append(confirmButton, cancelButton); reply.append(actions, status);
        }
        reply.append(readAloudButton(summary.textContent));
        answers.append(row);
        while (answers.children.length > 20) answers.firstElementChild.remove();
    }
    // AI-18: offline speech. The microphone is on only between Speak and Stop listening.
    function readAloudButton(text) {
        const button = document.createElement("button"); button.type = "button"; button.className = "btn btn-outline-secondary btn-sm mt-3 ms-2";
        button.textContent = "Read aloud"; button.dataset.readAloud = "true"; button.hidden = !speech.speak;
        button.addEventListener("click", async () => {
            button.disabled = true;
            try {
                const response = await fetch("/api/ai/speech/speak/", {method:"POST", credentials:"same-origin", headers:{"Content-Type":"application/json", "X-CSRFToken":getCookie("csrftoken")}, body:JSON.stringify({text})});
                if (!response.ok) throw new Error((await response.json().catch(() => ({}))).detail || "The offline voice could not read this.");
                // Web Audio plays the WAV without a blob: URL, which the page's Content Security Policy blocks.
                const audio = await response.arrayBuffer();
                if (player) player.close();
                player = new AudioContext();
                const sound = player.createBufferSource(); sound.buffer = await player.decodeAudioData(audio);
                sound.connect(player.destination); sound.start();
            } catch (error) { feedback.textContent = error.message; }
            finally { button.disabled = false; }
        });
        return button;
    }
    function wav16k(chunks, rate) {
        const total = chunks.reduce((sum, chunk) => sum + chunk.length, 0), input = new Float32Array(total);
        let at = 0; chunks.forEach(chunk => { input.set(chunk, at); at += chunk.length; });
        const length = Math.floor(total * 16000 / rate), view = new DataView(new ArrayBuffer(44 + length * 2));
        const tag = (offset, value) => [...value].forEach((char, index) => view.setUint8(offset + index, char.charCodeAt(0)));
        tag(0, "RIFF"); view.setUint32(4, 36 + length * 2, true); tag(8, "WAVE"); tag(12, "fmt "); view.setUint32(16, 16, true);
        view.setUint16(20, 1, true); view.setUint16(22, 1, true); view.setUint32(24, 16000, true); view.setUint32(28, 32000, true);
        view.setUint16(32, 2, true); view.setUint16(34, 16, true); tag(36, "data"); view.setUint32(40, length * 2, true);
        // Fallback only when the browser refuses a 16 kHz context: nearest-sample downsampling.
        for (let i = 0; i < length; i++) view.setInt16(44 + i * 2, Math.max(-1, Math.min(1, input[Math.floor(i * rate / 16000)] || 0)) * 0x7fff, true);
        return new Blob([view], {type:"audio/wav"});
    }
    async function startRecording() {
        // The browser's own free noise suppression and echo cancellation clean the voice before Whisper hears it.
        const stream = await navigator.mediaDevices.getUserMedia({audio:{channelCount:1, noiseSuppression:true, echoCancellation:true, autoGainControl:true}});
        // A 16 kHz context lets the browser resample with filtering; naive downsampling garbled words.
        let context; try { context = new AudioContext({sampleRate:16000}); } catch { context = new AudioContext(); }
        const source = context.createMediaStreamSource(stream), processor = context.createScriptProcessor(4096, 1, 1), chunks = [];
        processor.onaudioprocess = event => chunks.push(new Float32Array(event.inputBuffer.getChannelData(0)));
        source.connect(processor); processor.connect(context.destination); await context.resume();
        recording = {stream, context, chunks, timer:setTimeout(stopRecording, 30000)};
        mic.textContent = "Stop listening"; mic.setAttribute("aria-pressed", "true");
        feedback.textContent = "Listening. Press Stop listening when you finish.";
    }
    async function stopRecording() {
        const current = recording; if (!current) return;
        recording = null; clearTimeout(current.timer);
        current.stream.getTracks().forEach(track => track.stop());
        const rate = current.context.sampleRate; await current.context.close();
        mic.textContent = "Speak"; mic.setAttribute("aria-pressed", "false"); mic.disabled = true;
        feedback.textContent = "Turning your speech into text on this PC.";
        try {
            const result = await Alfred.fetchJSON("/api/ai/speech/transcribe/", {method:"POST", headers:{"Content-Type":"audio/wav"}, body:wav16k(current.chunks, rate)});
            if (result.text && !query.readOnly) query.value = [query.value.trim(), result.text].filter(Boolean).join(" ");
            feedback.textContent = result.text ? "Check the text, then press Ask ALFRED. Nothing has been asked yet." : "No speech was heard.";
            query.focus();
        } catch (error) { feedback.textContent = error.message; }
        finally { mic.disabled = false; }
    }
    mic.addEventListener("click", () => recording ? stopRecording() : startRecording().catch(error => {
        feedback.textContent = error.name === "NotAllowedError" ? "Microphone access was not allowed." : "The microphone could not start.";
    }));
    Alfred.fetchJSON("/api/ai/speech/status/").then(state => {
        speech = state; mic.hidden = speechHint.hidden = !state.listen || !navigator.mediaDevices?.getUserMedia;
        document.querySelectorAll("[data-read-aloud]").forEach(button => { button.hidden = !state.speak; });
    }).catch(() => {});
    async function streamAnswer(payload, ticket) {
        const controller = new AbortController(); streamRequest = controller;
        stopGeneration.hidden = false;
        const partial = document.createElement('article'); partial.className = 'conversation-message mt-3';
        partial.dataset.status = 'generating'; partial.setAttribute('aria-live','off');
        const label = document.createElement('span'); label.className = 'conversation-label';
        label.textContent = 'Unverified local preview - still generating. Figures and sources are buffered.';
        const text = document.createElement('p'); partial.append(label,text); answers.append(partial); empty.hidden = true;
        let reader, timedOut = false, received = 0, buffer = '', preview = '';
        const timeout = setTimeout(() => { timedOut = true; controller.abort(); },33000);
        try {
            const response = await fetch('/api/ai/personal-insights/stream/', {method:'POST',credentials:'same-origin',
                signal:controller.signal,headers:{'Content-Type':'application/json','X-CSRFToken':getCookie('csrftoken')},body:JSON.stringify(payload)});
            if (!response.ok) {
                const data = await response.json().catch(() => ({}));
                throw Object.assign(new Error(data.detail || 'Local stream unavailable. Your draft is preserved.'),{status:response.status,code:data.code,reference:data.error_id});
            }
            if (!response.body || response.headers.get('Content-Type')?.split(';')[0] !== 'application/x-ndjson') throw new Error('Invalid local stream. Your draft is preserved.');
            reader = response.body.getReader();
            const decoder = new TextDecoder('utf-8',{fatal:true});
            while (true) {
                const {done,value} = await reader.read();
                if (done) break;
                if (!active || ticket !== generation) throw new Error('This page no longer owns the stream.');
                received += value.byteLength;
                if (received > 262144) throw new Error('Local stream exceeded its limit.');
                buffer += decoder.decode(value,{stream:true});
                let newline;
                while ((newline = buffer.indexOf('\n')) >= 0) {
                    const line = buffer.slice(0,newline); buffer = buffer.slice(newline+1);
                    if (new TextEncoder().encode(line).length > 65536) throw new Error('Local stream frame exceeded its limit.');
                    const event = JSON.parse(line);
                    if (event.type === 'delta') {
                        if (typeof event.text !== 'string' || /[\p{N}\p{Sc}]/u.test(event.text)) throw new Error('Invalid unverified preview.');
                        preview += event.text;
                        if (new TextEncoder().encode(preview).length > 8192) throw new Error('Local preview exceeded its limit.');
                        text.textContent = preview;
                    } else if (event.type === 'buffering') {
                        preview = ''; text.textContent = ''; label.textContent = 'Validating full local output. Figures and sources are buffered.';
                    } else if (event.type === 'error') {
                        throw Object.assign(new Error(event.detail || 'Local output is incomplete. Your draft is preserved.'),{status:event.status,code:event.code,reference:event.error_id});
                    } else if (event.type === 'final') {
                        if (!event.result || event.result.provider !== 'ollama' || typeof event.result.answer !== 'string') throw new Error('Invalid final local answer.');
                        partial.remove(); return event.result;
                    } else if (!['started','heartbeat'].includes(event.type)) throw new Error('Invalid local stream event.');
                }
                if (new TextEncoder().encode(buffer).length > 65536) throw new Error('Local stream frame exceeded its limit.');
            }
            throw new Error('Connection ended before validation. Your draft is preserved; retry when ready.');
        } catch (error) {
            if (active && ticket === generation) {
                partial.dataset.status = 'partial'; label.textContent = 'Partial, unverified - not saved. Retry to request a complete answer.';
                if ([401,403,409].includes(error.status)) text.textContent = '';
            }
            if (controller.signal.aborted) throw Object.assign(new Error(timedOut
                ? 'Local generation timed out. Your draft is preserved; retry when ready.'
                : 'Local generation stopped. The partial preview is unverified and not saved; your draft is preserved.'),{code:timedOut ? 'local_stream_timeout' : 'local_stream_stopped'});
            throw error;
        } finally {
            clearTimeout(timeout);
            await reader?.cancel().catch(() => {});
            reader?.releaseLock(); controller.abort();
            if (streamRequest === controller) streamRequest = null;
            const restoreFocus = document.activeElement === stopGeneration;
            stopGeneration.hidden = true;
            if (restoreFocus && active && ticket === generation) query.focus();
        }
    }
    form.addEventListener("submit", async event => {
        event.preventDefault();
        if (pending) return;
        if (!historyPolicy || (!["financial_document","career"].includes(scope.value) && historyBlocked)) { feedback.textContent = "Reopen the saved conversation or reload local history status before sending. Your draft is preserved."; return; }
        if ((scope.value === "financial_document" && !picker) || (["financial_records","financial_document"].includes(scope.value) && picker && (picker.loading || picker.blocked || ((picker.explicit || picker.count > 5) && !picker.selected.size)))) {
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
        const payload = {query: query.value, scope: scope.value, answer_style:document.getElementById('intelligenceAnswerStyle').value, cloud_consent: consent.checked, query_sensitivity: consent.checked ? "public" : "sensitive"};
        if (!historyEnabled() && payload.scope === "general" && !payload.cloud_consent && pageDialogue.length) payload.page_context = pageDialogue;
        if (scope.value === "documents") payload.document_id = Number(documentChoice.value);
        if (scope.value === "bank_statements") payload.transaction_id = Number(statementChoice.value);
        if (scope.value === "financial_document") {
            const [kind,id] = picker.key.split(":");
            Object.assign(payload, {record_type:kind,document_id:Number(id),source_catalog:picker.catalog,
                selected_records:[...picker.selected.values()].map(item => ({id:item.record_id,revision:item.revision}))});
        }
        if (scope.value === "financial_records") {
            const [kind,id] = financialChoice.value.split(":");
            payload.record_type = kind; payload.record_id = Number(id);
            if (picker?.explicit) {
                payload.selected_documents = [...picker.selected.values()].map(item => ({id:item.document_id,revision:item.revision}));
                payload.source_catalog = picker.catalog;
            }
        }
        try {
            const action = await Alfred.fetchJSON("/api/ai/actions/propose/", {method:"POST", body:JSON.stringify({text:query.value})});
            if (!active || ticket !== generation) return;
            if (action?.proposal || action?.detail) {
                renderActionProposal(query.value, action);
                feedback.textContent = action.proposal ? "Review the proposed change. Nothing is saved until you press Confirm." : "That request could not be turned into an action. Nothing was saved.";
                setLocalStatus("Action proposal · no model used", "ready");
                query.value = ""; requestToken = null;
                return;
            }
            if (historyEnabled() && !["financial_document","career"].includes(payload.scope)) {
                if (!conversation) conversation = await Alfred.fetchJSON("/api/ai/conversations/", {method:"POST", body:JSON.stringify({title:historyTitle.value.trim() || "Private conversation"})});
                if (!active || ticket !== generation) return;
                const fingerprint = JSON.stringify(payload);
                if (requestToken?.fingerprint !== fingerprint) requestToken = {fingerprint, id:crypto.randomUUID().replaceAll("-", "")};
                Object.assign(payload, {cloud_consent:false, conversation_id:conversation.id, conversation_revision:conversation.revision, request_id:requestToken.id});
            }
            const result = payload.scope === 'general' && !payload.cloud_consent && !historyEnabled() && window.ReadableStream && window.AbortController
                ? await streamAnswer(payload,ticket)
                : await Alfred.fetchJSON("/api/ai/personal-insights/", {method: "POST", body: JSON.stringify(payload)});
            if (!active || ticket !== generation) return;
            if (result.conversation) conversation.revision = result.conversation.revision;
            renderTurn(payload, result, ticket, Boolean(result.historical));
            feedback.textContent = result.retrieval_error?.detail || "Answer ready. Review the sources before acting.";
            if (result.conversation_context_turns) feedback.textContent += ` Used ${result.conversation_context_turns} recent local turn(s) as unverified follow-up context.`;
            if (result.narrative_withheld) feedback.textContent = `Unsupported model figures were withheld. Only source-card amounts are shown. ${result.retrieval_error?.detail || ''}`;
            if (result.provider === "local_evidence") {
                if (result.grounding === "recorded_career_progress") {
                    feedback.textContent = 'Recorded Career progress ready. Review the source records; no model or saved conversation turn was used.';
                    setLocalStatus('Career records ready', 'ready');
                    query.value = ''; requestToken = null; retry.hidden = true;
                } else if (result.grounding === "canonical_record_overview") {
                    feedback.textContent = "Recorded values ready. Local AI is unavailable; review the current source cards. No cloud fallback was used and no conversation turn was saved.";
                    setLocalStatus("Recorded sources · AI unavailable", "review");
                    query.value = ""; requestToken = null; retry.hidden = true;
                } else if (["owner_confirmed_transaction_date", "owner_confirmed_transaction_classification", "owner_confirmed_statement_period", "owner_confirmed_transaction_direction"].includes(result.grounding)) {
                    const label = result.grounding === "owner_confirmed_statement_period" ? "statement periods"
                        : result.grounding === "owner_confirmed_transaction_direction" ? "transaction directions"
                        : result.grounding === "owner_confirmed_transaction_date" ? "transaction dates" : "transaction classifications";
                    feedback.textContent = `Recorded ${label} ready. Review the owner-only sources. No model, cloud or saved conversation turn was used.`;
                    setLocalStatus("Owner-reviewed evidence · no model used", "ready");
                    query.value = ""; requestToken = null; retry.hidden = true;
                } else {
                    feedback.textContent = "Insufficient evidence. Review the source citation, then retry. Your draft is preserved; no model or cloud was used and no turn was saved.";
                    setLocalStatus("Evidence review required · no model used", "review");
                    retry.hidden = false;
                }
            } else {
                setLocalStatus(result.provider === "ollama" ? "Ollama available" : "Ollama unavailable · consented fallback used", result.provider === "ollama" ? "ready" : "unavailable");
                query.value = ""; requestToken = null;
            }
            if (!historyEnabled() && payload.scope === "general" && !payload.cloud_consent && result.provider === "ollama" && !result.narrative_withheld) {
                pageDialogue = [...pageDialogue, {role:"user",content:dialogueSnippet(payload.query)},
                    {role:"assistant",content:dialogueSnippet(result.answer)}].slice(-6);
            }
            if (historyEnabled() && !["financial_document","career"].includes(payload.scope)) await refreshHistory().catch(() => { historyPolicy = null; historyFeedback.textContent = `${result.conversation_saved === true ? 'Answer saved, but history' : 'History'} status could not refresh. Reload before another question.`; });
        } catch (error) {
            if (active && ticket === generation) {
                feedback.textContent = `${error.message}${error.reference ? ` Reference: ${error.reference}` : ""}`;
                retry.hidden = error.status === 409 || error.status === 429 || error.status === 400;
                if (picker && (error.code === "financial_sources_changed" || (picker.documentMode && [404,409].includes(error.status)))) {
                    picker.blocked = true; sourceStatus.textContent = "Selected evidence changed or is unavailable. Refresh the source list and select current revisions. Your draft is preserved.";
                } else if (error.status === 409 && conversation) {
                    historyBlocked = true; feedback.textContent += " Reopen this conversation to review newer turns; your draft is preserved.";
                    await refreshHistory().catch(() => { historyPolicy = null; });
                    if (active && !conversation) feedback.textContent = "Conversation no longer available. Displayed turns cleared; your draft is preserved for a new conversation.";
                }
                setLocalStatus(error.code === 'local_stream_stopped' ? 'Local generation stopped'
                    : error.code === "local_model_unavailable" ? "Ollama unavailable" : "Local request did not complete",
                    error.code === 'local_stream_stopped' ? 'ready' : 'unavailable');
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
        if (event.persisted) {
            modelRefresh.disabled=modelPending;
            if (modelPanel.open) refreshModelReadiness();
            refreshControls().catch(error => { if (active) feedback.textContent = error.message; });
        }
    });
});
