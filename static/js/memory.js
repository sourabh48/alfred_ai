document.addEventListener("DOMContentLoaded", () => {
    const panel = document.getElementById("privateMemoryPanel");
    if (!panel) return;
    const list = document.getElementById("memoryList");
    const feedback = document.getElementById("memoryFeedback");
    let generation = 0;
    function message(text) { feedback.textContent = text; }
    async function refresh() {
        const ticket = ++generation;
        const payload = await Alfred.fetchJSON("/api/ai/memories/");
        if (ticket !== generation) return;
        document.getElementById("memoryRetentionDays").value = payload.retention_days;
        list.replaceChildren();
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
            row.append(text, detail, remove);
            list.append(row);
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
    refresh().catch(error => message(error.message));
    window.addEventListener("pagehide", () => { generation++; list.replaceChildren(); feedback.textContent = ""; });
    window.addEventListener("pageshow", event => {
        if (event.persisted) refresh().catch(error => message(error.message));
    });
});
