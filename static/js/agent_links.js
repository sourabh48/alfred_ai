// Settings > Agent links: a token is shown once; removing takes away every token this person made.
(function () {
    const $ = id => document.getElementById(id), URL = "/api/settings/agent-links/";
    if (!$("settingsAgentLinks")) return;

    function say(text, kind) {
        const box = $("agentLinksFeedback");
        box.className = text ? `alert alert-${kind} mb-2 text-break` : "d-none alert mb-2";
        box.textContent = text;
    }

    function render(data) {
        $("agentLinksRevoke").classList.toggle("d-none", !data.tokens);
        $("agentLinksStatus").textContent = `${data.tokens ? `${data.tokens} token${data.tokens > 1 ? "s" : ""} in use.` : "No tokens yet."} Agent card: ${data.card}`;
        if (data.token) say(`Copy this token into the other agent now; it is not shown again: ${data.token}`, "info");
    }

    function act(action, button, done) {
        button.disabled = true;
        Alfred.fetchJSON(URL, { method: "POST", body: JSON.stringify({ action }) })
            .then(data => { say(done || "", "success"); render(data); })
            .catch(error => say(error.message, "danger"))
            .finally(() => { button.disabled = false; });
    }

    Alfred.fetchJSON(URL).then(render).catch(error => say(error.message, "danger"));
    $("agentLinksCreate").addEventListener("click", event => act("create", event.currentTarget));
    $("agentLinksRevoke").addEventListener("click", event => {
        if (window.confirm("Remove all your agent tokens? Agents using them stop getting answers.")) act("revoke", event.currentTarget, "Removed.");
    });
})();
