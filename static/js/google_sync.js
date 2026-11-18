// Settings > Phone calendar and tasks (Google): status, sync now, disconnect. Connecting is a normal Google sign-in link.
(function () {
    const $ = id => document.getElementById(id), URL = "/api/settings/google-sync/";
    if (!$("settingsGoogleSync")) return;

    function say(text, kind) {
        const box = $("googleSyncFeedback");
        box.className = text ? `alert alert-${kind} mb-2` : "d-none alert mb-2";
        box.textContent = text;
    }

    function render(data) {
        const show = (id, on) => $(id).classList.toggle("d-none", !on);
        show("googleSyncConnect", data.available && !data.connected);
        show("googleSyncNow", data.connected);
        show("googleSyncDisconnect", data.connected);
        $("googleSyncStatus").textContent = !data.available ? "Google sign-in is not set up yet. Add its client id and secret under Online services first."
            : !data.connected ? "Not connected."
            : `Connected to ${data.account}. ${data.last_sync ? `Last sync ${new Date(data.last_sync).toLocaleString()}: ${data.events} events and ${data.tasks} tasks.` : "Not synced yet."}`;
        if (data.error || data.last_error) say(data.error || data.last_error, "danger");
    }

    function act(action, button, done) {
        button.disabled = true;
        Alfred.fetchJSON(URL, { method: "POST", body: JSON.stringify({ action }) })
            .then(data => { say("", ""); render(data); say(done, "success"); })
            .catch(error => { if (error.payload && "connected" in error.payload) render(error.payload); say(error.message, "danger"); })
            .finally(() => { button.disabled = false; });
    }

    Alfred.fetchJSON(URL).then(render).catch(error => say(error.message, "danger"));
    $("googleSyncNow").addEventListener("click", event => act("sync", event.currentTarget, "Synced. Your phone shows the changes within a few minutes."));
    $("googleSyncDisconnect").addEventListener("click", event => {
        if (window.confirm("Stop syncing and remove ALFRED's access to your Google Calendar and Tasks?")) act("disconnect", event.currentTarget, "Disconnected.");
    });
})();
