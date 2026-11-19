// Settings > Backup key: lock the key with a passphrase, save or fetch the locked copy in Google Drive, open a fetched copy.
(function () {
    const $ = id => document.getElementById(id), URL = "/api/settings/backup-key/";
    if (!$("settingsBackupKey")) return;

    function say(text, kind) {
        const box = $("backupKeyFeedback");
        box.className = text ? `alert alert-${kind} mb-2` : "d-none alert mb-2";
        box.textContent = text;
    }

    function render(data) {
        const show = (id, on) => $(id).classList.toggle("d-none", !on);
        $("backupKeyStatus").textContent = !data.key && !data.locked_copy ? "No backup key on this PC yet. Choose a passphrase to make one."
            : !data.key ? `A locked copy was fetched from ${data.google || "Google Drive"}. Type its passphrase to open it.`
            : data.in_drive && data.saved_on ? `Backup key on this PC. Locked copy saved in the Google Drive of ${data.google} on ${data.saved_on}. Key file: ${data.key_file}`
            : data.locked_copy ? `Backup key on this PC and locked with your passphrase, but not yet in Google Drive. Key file: ${data.key_file}`
            : `Backup key on this PC, not locked yet. Key file: ${data.key_file}`;
        $("backupKeyMake").textContent = data.key ? "Lock the key with a new passphrase" : "Make the key and lock it";
        show("backupKeySave", data.key && data.locked_copy);
        show("backupKeyRestoreForm", !data.key && data.locked_copy);
        if (data.error) say(data.error, "danger");
    }

    function post(payload, done, form) {
        const button = form.querySelector("button[type=submit]");
        button.disabled = true;
        Alfred.fetchJSON(URL, { method: "POST", body: JSON.stringify(payload) })
            .then(data => { render(data); say(done, "success"); form.reset(); })
            .catch(error => { if (error.payload && "key" in error.payload) render(error.payload); say(error.message, "danger"); })
            .finally(() => { button.disabled = false; });
    }

    Alfred.fetchJSON(URL).then(render).catch(error => {
        say(error.message, error.status === 403 ? "secondary" : "danger");
        ["backupKeyMakeForm", "backupKeyFetch"].forEach(id => $(id).classList.add("d-none"));
    });
    $("backupKeyMakeForm").addEventListener("submit", event => {
        event.preventDefault();
        post({ action: "make", passphrase: $("backupKeyPassphrase").value, repeat: $("backupKeyRepeat").value },
            "Key locked. Now save the locked copy to Google Drive.", event.currentTarget);
    });
    $("backupKeyRestoreForm").addEventListener("submit", event => {
        event.preventDefault();
        post({ action: "restore", passphrase: $("backupKeyRestorePassphrase").value }, "Backup key restored on this PC.", event.currentTarget);
    });
    window.addEventListener("pagehide", () => ["backupKeyPassphrase", "backupKeyRepeat", "backupKeyRestorePassphrase"].forEach(id => { $(id).value = ""; }));
})();
