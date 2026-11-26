// Settings > Backup key: lock the key with a passphrase, save or fetch the locked copy in Cloudflare R2 or Google Drive,
// open a fetched copy, and show the nightly backup.
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
            : !data.key ? "A locked copy was fetched. Type its passphrase to open it."
            : data.in_r2 || (data.in_drive && data.saved_on) ? `Backup key on this PC. Locked copy saved in ${[
                data.in_r2 ? `Cloudflare R2 on ${data.r2_saved_on}` : "", data.in_drive && data.saved_on ? `the Google Drive of ${data.google} on ${data.saved_on}` : "",
              ].filter(Boolean).join(" and ")}. Key file: ${data.key_file}`
            : data.locked_copy ? `Backup key on this PC and locked with your passphrase, but no copy is saved off this PC yet. Key file: ${data.key_file}`
            : `Backup key on this PC, not locked yet. Key file: ${data.key_file}`;
        $("backupKeyMake").textContent = data.key ? "Lock the key with a new passphrase" : "Make the key and lock it";
        show("backupKeySave", data.key && data.locked_copy);
        const cloud = data.cloud || {}, auto = data.auto || {};
        const copySaved = data.key && (data.in_r2 || (data.in_drive && data.saved_on));
        show("backupCloudForm", !cloud.on);
        show("backupTurnOff", cloud.on);
        show("backupNow", cloud.on && copySaved);
        show("backupKeySaveR2", data.key && data.locked_copy && cloud.on);
        show("backupKeyFetchR2", !data.key && cloud.on);
        const last = auto.last_ok ? new Date(auto.last_ok.replace(" UTC", "Z").replace(" ", "T")) : null;
        const stale = last && Date.now() - last > 2 * 86400000;  // a bank app warns when backups stop
        const box = $("backupAutoStatus");
        box.classList.toggle("text-danger", Boolean(stale || (cloud.on && auto.error)));
        box.textContent = !cloud.on ? "Off. Connect your Cloudflare R2 bucket to back up every night."
            : !copySaved ? `Connected to bucket ${cloud.bucket}. Make the key and save its locked copy above, then backups start.`
            : last ? `${stale ? "No backup for over two days. " : ""}Last saved to bucket ${cloud.bucket} on ${auto.last_ok}, ${auto.kept} kept.${auto.error ? ` The last try failed: ${auto.error}` : ""}`
            : `Connected to bucket ${cloud.bucket}. The first backup runs tonight, or press Back up now.${auto.error ? ` Last try: ${auto.error}` : ""}`;
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
        ["backupKeyMakeForm", "backupKeyFetch", "backupKeyFetchR2"].forEach(id => $(id).classList.add("d-none"));
    });
    $("backupKeyMakeForm").addEventListener("submit", event => {
        event.preventDefault();
        post({ action: "make", passphrase: $("backupKeyPassphrase").value, repeat: $("backupKeyRepeat").value },
            "Key locked. Now save the locked copy to Cloudflare R2 or Google Drive.", event.currentTarget);
    });
    [["backupKeySaveR2", "save_r2", "Locked copy saved to Cloudflare R2."], ["backupKeyFetchR2", "fetch_r2", "Locked copy fetched. Type its passphrase to open it."],
     ["backupNow", "backup_now", "Backup started. It takes a few minutes; reopen this page to see the result."],
     ["backupTurnOff", "turn_off", "Nightly backup is off. Backups already in Cloudflare stay there."]]
        .forEach(([id, action, done]) => $(id).addEventListener("click", () => {
            $(id).disabled = true;
            Alfred.fetchJSON(URL, { method: "POST", body: JSON.stringify({ action }) })
                .then(data => { render(data); say(done, "success"); })
                .catch(error => { if (error.payload && "key" in error.payload) render(error.payload); say(error.message, "danger"); })
                .finally(() => { $(id).disabled = false; });
        }));
    $("backupCloudForm").addEventListener("submit", event => {
        event.preventDefault();
        const r2 = Object.fromEntries(new FormData(event.currentTarget));
        post({ action: "connect_r2", r2 }, "Connected. Nightly backup is on.", event.currentTarget);
    });
    $("backupKeyRestoreForm").addEventListener("submit", event => {
        event.preventDefault();
        post({ action: "restore", passphrase: $("backupKeyRestorePassphrase").value }, "Backup key restored on this PC.", event.currentTarget);
    });
    window.addEventListener("pagehide", () => ["backupKeyPassphrase", "backupKeyRepeat", "backupKeyRestorePassphrase", "backupCloudSecret"].forEach(id => { $(id).value = ""; }));
})();
