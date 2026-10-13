document.addEventListener("DOMContentLoaded", () => {
    if (!document.getElementById("intelligencePanel")) return;
    const query = document.getElementById("intelligenceQuery");
    const scope = document.getElementById("intelligenceScope");
    const documentChoice = document.getElementById("intelligenceDocument");
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
    let active = true, generation = 0, cloudAvailable = false, pending = false;
    function setLocalStatus(text, state) {
        localStatus.textContent = text; localStatus.dataset.state = state;
    }
    function updateScope() {
        const documents = scope.value === "documents";
        document.getElementById("intelligenceDocumentField").classList.toggle("d-none", !documents);
        documentChoice.disabled = !documents;
        consent.checked = false;
        consent.disabled = scope.value !== "general" || !cloudAvailable;
    }
    async function refreshControls() {
        const ticket = generation;
        const [insights, reasoning] = await Promise.all([Alfred.fetchJSON("/api/ai/personal-insights/?assistant_status=1"), Alfred.fetchJSON("/api/ai/memories/reason/")]);
        if (!active || ticket !== generation) return;
        documentChoice.replaceChildren(new Option("Choose verified evidence", ""));
        (insights.assistant_documents || []).forEach(item => documentChoice.append(new Option(item.label, item.id)));
        cloudAvailable = reasoning.provider_available && reasoning.policy.enabled;
        setLocalStatus(insights.local_model_status === "available" ? "Ollama available" : "Ollama unavailable", insights.local_model_status === "available" ? "ready" : "unavailable");
        document.getElementById("intelligenceCloudStatus").textContent = !reasoning.real_provider_enabled
            ? (cloudAvailable ? "Synthetic cloud testing · OpenAI disabled" : "OpenAI disabled")
            : (cloudAvailable ? "OpenAI · consent required per question" : "OpenAI · owner consent or configuration required");
        updateScope();
    }
    scope.addEventListener("change", updateScope);
    query.addEventListener("keydown", event => {
        if (event.key === "Enter" && (event.ctrlKey || event.metaKey) && !event.isComposing) { event.preventDefault(); form.requestSubmit(); }
    });
    retry.addEventListener("click", () => form.requestSubmit());
    newConversation.addEventListener("click", () => {
        if (pending) return;
        generation++; answers.replaceChildren(); empty.hidden = false; query.value = "";
        consent.checked = false; feedback.textContent = "New conversation. Previous messages cleared from this page."; retry.hidden = true; query.focus();
    });
    form.addEventListener("submit", async event => {
        event.preventDefault();
        if (pending) return;
        const ticket = generation, button = event.target.querySelector("button");
        pending = true; button.disabled = true; newConversation.disabled = true; query.readOnly = true; retry.hidden = true;
        answers.setAttribute("aria-busy", "true");
        setLocalStatus("Local model processing", "processing");
        feedback.textContent = "ALFRED is processing locally.";
        const spinner = document.createElement("span"); spinner.className = "conversation-spinner me-2"; spinner.setAttribute("aria-hidden", "true"); feedback.prepend(spinner);
        button.textContent = "Thinking…";
        const payload = {query: query.value, scope: scope.value, cloud_consent: consent.checked, query_sensitivity: consent.checked ? "public" : "sensitive"};
        if (scope.value === "documents") payload.document_id = Number(documentChoice.value);
        try {
            const result = await Alfred.fetchJSON("/api/ai/personal-insights/", {method: "POST", body: JSON.stringify(payload)});
            if (!active || ticket !== generation) return;
            const row = document.createElement("article");
            const userMessage = document.createElement("div"); userMessage.className = "conversation-message conversation-message--user";
            const userLabel = document.createElement("span"); userLabel.className = "conversation-label"; userLabel.textContent = "You";
            const question = document.createElement("p"); question.textContent = payload.query; userMessage.append(userLabel, question);
            const assistantMessage = document.createElement("div"); assistantMessage.className = "conversation-message mt-3";
            const label = document.createElement("span"); label.className = "conversation-label";
            label.textContent = `AI hypothesis · ${result.provider === "ollama" ? "Ollama (local)" : result.provider === "mock" ? "Mock (synthetic)" : "Approved cloud"}`;
            const answer = document.createElement("p"); answer.textContent = result.answer;
            assistantMessage.append(label, answer); row.append(userMessage, assistantMessage);
            const evidence = document.createElement("details"); evidence.className = "conversation-evidence";
            const summary = document.createElement("summary"); summary.textContent = `Sources & evidence (${(result.sources || []).length})`;
            evidence.append(summary); assistantMessage.append(evidence);
            if (!result.sources?.length) { const note = document.createElement("p"); note.textContent = "Insufficient evidence for personal facts. This answer has no matching verified source."; evidence.append(note); }
            (result.sources || []).forEach(source => {
                const reference = document.createElement("p"); reference.textContent = `Source: ${source.ref} · ${source.classification}`;
                evidence.append(reference);
                const types = {owner_verified_statement:"Owner-confirmed memory", canonical_financial_baseline:"Canonical financial records", owner_travel_preferences:"Your saved Travel preferences", verified_document_evidence:"Verified loan closure evidence"};
                const description = document.createElement("p"); description.textContent = `${types[source.classification] || 'Source'} · ${source.verified_at ? `Checked ${new Date(source.verified_at).toLocaleString()}` : 'Verification timestamp not recorded'}`; evidence.append(description);
                if (['/loans/','/expenses/','/mobility/'].includes(source.url) || /^\/settings\/#memory-[a-f0-9]{32}$/.test(source.url || "")) {
                    const link = document.createElement("a"); link.href = source.url; link.textContent = source.classification === "owner_verified_statement" ? "Review or correct this memory" : "Open source records"; evidence.append(link);
                }
                if (source.data) Object.entries(source.data).forEach(([key, value]) => {
                    if (key === "metric_states") return;
                    const fact = document.createElement("p");
                    const monetary = source.classification === "canonical_financial_baseline" || key === "closure_amount";
                    const display = monetary && typeof value === "number" ? Alfred.formatCurrency(value) : (typeof value === "object" ? JSON.stringify(value) : String(value));
                    const state = source.data.metric_states?.[key]?.status;
                    fact.textContent = `${key.replaceAll("_", " ")}: ${display}${state ? ` (${state})` : ""}`;
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
            while (answers.children.length > 10) answers.firstElementChild.remove();
            feedback.textContent = result.retrieval_error?.detail || "Answer ready. Review the sources before acting.";
            setLocalStatus(result.provider === "ollama" ? "Ollama available" : "Ollama unavailable · consented fallback used", result.provider === "ollama" ? "ready" : "unavailable");
            query.value = "";
            evidence.open = true;
        } catch (error) {
            if (active && ticket === generation) {
                feedback.textContent = `${error.message}${error.reference ? ` Reference: ${error.reference}` : ""}`;
                retry.hidden = error.status === 409 || error.status === 429 || error.status === 400;
                setLocalStatus(error.code === "local_model_unavailable" ? "Ollama unavailable" : "Local request did not complete", "unavailable");
                if (error.code === "reasoning_budget_reached") document.getElementById("intelligenceCloudStatus").textContent = "Cloud budget reached";
            }
        }
        finally { pending = false; consent.checked = false; button.disabled = false; button.textContent = "Ask ALFRED"; newConversation.disabled = false; query.readOnly = false; answers.setAttribute("aria-busy", "false"); }
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
        active = false; generation++; answers.replaceChildren(); documentChoice.replaceChildren(); empty.hidden = false;
        query.value = ""; memoryText.value = ""; verified.checked = false; consent.checked = false; feedback.textContent = "";
        consent.disabled = true; retry.hidden = true;
        document.getElementById("intelligenceMemorySensitivity").value = "sensitive";
    });
    window.addEventListener("pageshow", event => {
        active = true;
        if (event.persisted) refreshControls().catch(error => { if (active) feedback.textContent = error.message; });
    });
});
