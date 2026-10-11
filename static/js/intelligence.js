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
    let active = true, generation = 0, cloudAvailable = false;
    function updateScope() {
        const documents = scope.value === "documents";
        document.getElementById("intelligenceDocumentField").classList.toggle("d-none", !documents);
        documentChoice.disabled = !documents;
        consent.checked = false;
        consent.disabled = scope.value !== "general" || !cloudAvailable;
    }
    async function refreshControls() {
        const ticket = generation;
        const [insights, reasoning] = await Promise.all([Alfred.fetchJSON("/api/ai/personal-insights/"), Alfred.fetchJSON("/api/ai/memories/reason/")]);
        if (!active || ticket !== generation) return;
        documentChoice.replaceChildren(new Option("Choose verified evidence", ""));
        (insights.assistant_documents || []).forEach(item => documentChoice.append(new Option(item.label, item.id)));
        cloudAvailable = reasoning.provider_available && reasoning.policy.enabled;
        updateScope();
    }
    scope.addEventListener("change", updateScope);
    document.getElementById("intelligenceForm").addEventListener("submit", async event => {
        event.preventDefault();
        const ticket = generation, button = event.target.querySelector("button");
        button.disabled = true;
        feedback.textContent = "ALFRED is processing locally.";
        const payload = {query: query.value, scope: scope.value, cloud_consent: consent.checked, query_sensitivity: consent.checked ? "public" : "sensitive"};
        if (scope.value === "documents") payload.document_id = Number(documentChoice.value);
        try {
            const result = await Alfred.fetchJSON("/api/ai/personal-insights/", {method: "POST", body: JSON.stringify(payload)});
            if (!active || ticket !== generation) return;
            const row = document.createElement("article");
            const question = document.createElement("p"); question.textContent = payload.query;
            const label = document.createElement("strong"); label.textContent = `AI hypothesis · ${result.provider}`;
            const answer = document.createElement("p"); answer.textContent = result.answer; answer.style.whiteSpace = "pre-wrap";
            row.append(question, label, answer);
            (result.sources || []).forEach(source => {
                const reference = document.createElement("p"); reference.textContent = `Source: ${source.ref} · ${source.classification}`;
                row.append(reference);
                if (source.data) Object.entries(source.data).forEach(([key, value]) => {
                    if (key === "metric_states") return;
                    const fact = document.createElement("p");
                    const monetary = source.classification === "canonical_financial_baseline" || key === "closure_amount";
                    const display = monetary && typeof value === "number" ? Alfred.formatCurrency(value) : (typeof value === "object" ? JSON.stringify(value) : String(value));
                    const state = source.data.metric_states?.[key]?.status;
                    fact.textContent = `${key.replaceAll("_", " ")}: ${display}${state ? ` (${state})` : ""}`;
                    row.append(fact);
                });
            });
            answers.append(row);
            while (answers.children.length > 10) answers.firstElementChild.remove();
            feedback.textContent = "Answer ready. Review the sources before acting.";
            query.value = "";
        } catch (error) { if (active && ticket === generation) feedback.textContent = error.message; }
        finally { consent.checked = false; button.disabled = false; }
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
        active = false; generation++; answers.replaceChildren(); documentChoice.replaceChildren();
        query.value = ""; memoryText.value = ""; verified.checked = false; consent.checked = false; feedback.textContent = "";
        consent.disabled = true;
        document.getElementById("intelligenceMemorySensitivity").value = "sensitive";
    });
    window.addEventListener("pageshow", event => {
        active = true;
        if (event.persisted) refreshControls().catch(error => { if (active) feedback.textContent = error.message; });
    });
});
