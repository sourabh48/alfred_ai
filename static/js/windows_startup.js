// Settings > Start with Windows: shows ALFRED's entry in the Windows user's startup list as Windows reads it back.
document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("startupForm");
    if (!form) return;
    const $ = id => document.getElementById(id), url = "/api/settings/windows-startup/";
    const on = $("startupOn"), browser = $("startupBrowser"), status = $("startupStatus"), feedback = $("startupFeedback");

    function render(data) {
        if (!data.available) {
            status.textContent = `Windows startup cannot be read here: ${data.error || "Windows did not answer."}`;
            form.hidden = true;
            return;
        }
        on.checked = data.on;
        browser.checked = data.opens_browser;
        status.textContent = (data.on ? `On: ALFRED starts when you sign in to Windows, ${data.opens_browser ? "and opens in the browser" : "quietly in the notification area"}.`
            : data.turned_off_in_windows ? "Off: ALFRED's startup entry is switched off in Windows Settings > Apps > Startup. Turning it on here switches it back on."
            : "Off: ALFRED does not start with Windows.")
            + (data.registered && !data.this_copy ? ` Windows starts a different ALFRED copy or data folder: ${data.command}. Saving here replaces it with this one.` : "")
            + (data.can_manage ? "" : " Only the person who manages ALFRED on this PC can change it.");
        [on, browser, $("startupSave")].forEach(control => { control.disabled = !data.can_manage; });
        form.hidden = false;
    }

    async function call(options) {
        try { return await Alfred.fetchJSON(url, options); }
        catch (error) {
            if (error.payload && "available" in error.payload) render(error.payload);
            throw error;
        }
    }

    form.addEventListener("submit", async event => {
        event.preventDefault();
        feedback.textContent = "Saving…";
        try {
            render(await call({ method: "POST", body: JSON.stringify({ on: on.checked, open_browser: browser.checked }) }));
            feedback.textContent = on.checked ? "Saved. Windows will start ALFRED at your next sign-in." : "Saved. ALFRED will not start with Windows. It keeps running now.";
        } catch (error) {
            feedback.textContent = error.message || "Nothing was changed.";
        }
    });
    call().then(render).catch(error => { status.textContent = error.message || "Windows startup could not be read."; });
});
