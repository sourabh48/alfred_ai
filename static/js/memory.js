document.addEventListener("DOMContentLoaded", () => {
    const panel = document.getElementById("privateMemoryPanel");
    if (!panel) return;
    const list = document.getElementById("memoryList");
    const feedback = document.getElementById("memoryFeedback");
    const expected = document.getElementById("memoryEvaluationExpected");
    const quality = document.getElementById("memoryEvaluationResult");
    const query = document.getElementById("memoryEvaluationQuery");
    let generation = 0;
    let active = true;
    function message(text) { if (active) feedback.textContent = text; }
    async function refresh() {
        if (!active) return;
        const ticket = ++generation;
        const payload = await Alfred.fetchJSON("/api/ai/memories/");
        if (!active || ticket !== generation) return;
        document.getElementById("memoryRetentionDays").value = payload.retention_days;
        list.replaceChildren();
        expected.replaceChildren(new Option("No memory should match", ""));
        quality.textContent = "";
        query.value = "";
        if (!payload.memories.length) list.textContent = "No verified memories saved.";
        payload.memories.forEach(memory => {
            const row = document.createElement("div");
            const text = document.createElement("p");
            text.textContent = JSON.stringify(memory.content);
            const detail = document.createElement("p");
            detail.textContent = `${memory.sensitivity} · ${memory.provenance.source}`;
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
            row.append(text, detail, remove, edit);
            list.append(row);
            expected.append(new Option(JSON.stringify(memory.content), memory.id));
        });
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
    document.getElementById("memoryEvaluationForm").addEventListener("submit", async event => {
        event.preventDefault();
        const ticket = generation;
        const button = event.target.querySelector("button");
        button.disabled = true;
        quality.textContent = "";
        try {
            const result = await Alfred.fetchJSON("/api/ai/memories/learning/", {method: "POST", body: JSON.stringify({action: "evaluate", cases: [{query: query.value, expected_id: expected.value || null}]})});
            if (!active || ticket !== generation) return;
            quality.textContent = result.negative_cases
                ? (result.false_positive_rate ? "Unexpected match returned. Review relevance before using this memory." : "No memory returned, as expected.")
                : `Expected match in first three: ${result.recall_at_3 ? "yes" : "no"}. First match correct: ${result.top_1_accuracy ? "yes" : "no"}.`;
        } catch (error) { if (ticket === generation) message(error.message); }
        finally { button.disabled = false; }
    });
    refresh().catch(error => message(error.message));
    window.addEventListener("pagehide", () => {
        active = false; generation++; list.replaceChildren(); feedback.textContent = "";
        expected.replaceChildren(); query.value = ""; quality.textContent = "";
    });
    window.addEventListener("pageshow", event => {
        active = true;
        if (event.persisted) refresh().catch(error => message(error.message));
    });
});
