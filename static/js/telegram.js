// Settings > Telegram: a one-time code links a private chat to this person; unlink removes all of their chats.
(function () {
    const $ = id => document.getElementById(id), URL = "/api/settings/telegram/";
    if (!$("settingsTelegram")) return;

    function say(text, kind) {
        const box = $("telegramFeedback");
        box.className = text ? `alert alert-${kind} mb-2` : "d-none alert mb-2";
        box.textContent = text;
    }

    function render(data) {
        $("telegramCode").classList.toggle("d-none", !data.configured);
        $("telegramUnlink").classList.toggle("d-none", !data.linked);
        $("telegramStatus").textContent = !data.configured ? "No Telegram bot is set up yet (see below)."
            : data.linked ? `${data.linked} chat${data.linked > 1 ? "s" : ""} linked.` : "No chat linked yet.";
        if (data.code) say(`Send this to your ALFRED bot in Telegram within ${data.code_minutes} minutes: /link ${data.code}`, "info");
    }

    function act(action, button) {
        button.disabled = true;
        Alfred.fetchJSON(URL, { method: "POST", body: JSON.stringify({ action }) })
            .then(data => { say("", ""); render(data); if (action === "unlink") say("Unlinked.", "success"); })
            .catch(error => say(error.message, "danger"))
            .finally(() => { button.disabled = false; });
    }

    Alfred.fetchJSON(URL).then(render).catch(error => say(error.message, "danger"));
    $("telegramCode").addEventListener("click", event => act("code", event.currentTarget));
    $("telegramUnlink").addEventListener("click", event => {
        if (window.confirm("Unlink every Telegram chat linked to you? They get no more answers.")) act("unlink", event.currentTarget);
    });
})();
