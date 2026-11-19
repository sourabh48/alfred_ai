// Settings > Online services > Gemini: the person's own free key and daily limits (replaced OpenAI, owner decision 2026-11-19).
document.addEventListener("DOMContentLoaded", () => {
    const box = document.getElementById("settingsGemini");
    if (!box) return;
    const $ = id => document.getElementById(id);
    const feedback = $("geminiFeedback");
    let generation = 0;
    async function refresh() {
        const ticket = ++generation;
        const reasoning = await Alfred.fetchJSON("/api/ai/memories/reason/");
        if (ticket !== generation) return;
        $("memoryReasoningStatus").textContent = !reasoning.key_saved ? "Gemini off: no key saved. Answers use the local model." : reasoning.policy.enabled ? "Gemini on with your key for public questions; consent and daily limits apply." : "Key saved. Tick the opt-in below and save to turn Gemini on.";
        $("memoryReasoningKeyStatus").textContent = reasoning.key_saved ? `Key saved (ends ${reasoning.key_hint}).` : "No key saved.";
        $("memoryReasoningKeyRemove").hidden = !reasoning.key_saved;
        $("memoryReasoningUsage").textContent = `UTC day ${reasoning.usage.day}: ${reasoning.usage.reserved_tokens} tokens reserved; USD ${(reasoning.usage.reserved_microusd / 1000000).toFixed(6)} conservatively reserved. Billing measurements are unavailable; these reservations enforce caps.`;
        $("memoryReasoningEnabled").checked = reasoning.policy.enabled;
        $("memoryReasoningTokens").value = reasoning.policy.daily_tokens;
        $("memoryReasoningDollars").value = reasoning.policy.daily_microusd / 1000000;
    }
    async function act(path, payload, text, method) {
        try {
            await Alfred.fetchJSON(`/api/ai/memories/${path}/`, {method: method || (path === "reason" ? "PUT" : "POST"), ...(payload ? {body: JSON.stringify(payload)} : {})});
            await refresh();
            feedback.textContent = text;
        } catch (error) { feedback.textContent = error.message; }
    }
    $("memoryReasoningKeyForm").addEventListener("submit", async event => {
        event.preventDefault();
        const input = $("memoryReasoningKey");
        await act("reason/key", {key: input.value.trim()}, "Key saved. Tick the opt-in and save to turn Gemini on.");
        input.value = "";
    });
    $("memoryReasoningKeyRemove").addEventListener("click", () => {
        if (window.confirm("Remove your Gemini key? Gemini is switched off until you add a key again.")) act("reason/key", null, "Key removed. Gemini is off.", "DELETE");
    });
    $("memoryReasoningForm").addEventListener("submit", event => {
        event.preventDefault();
        const enabled = $("memoryReasoningEnabled").checked;
        act("reason", {enabled, consent: enabled, daily_tokens: Number($("memoryReasoningTokens").value), daily_microusd: Math.round(Number($("memoryReasoningDollars").value) * 1000000)}, "Gemini settings saved. Each cloud question still asks first.");
    });
    // Clear what the page showed when it goes into the back/forward cache, and reload it on return.
    window.addEventListener("pagehide", () => { generation++; feedback.textContent = ""; $("memoryReasoningUsage").textContent = ""; $("memoryReasoningKey").value = ""; });
    window.addEventListener("pageshow", event => { if (event.persisted) refresh().catch(error => { feedback.textContent = error.message; }); });
    refresh().catch(error => { $("memoryReasoningStatus").textContent = error.message; });
});
