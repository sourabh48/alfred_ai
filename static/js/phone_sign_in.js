// Phone sign-in with a code (owner decision 2026-11-19): the phone waits; the signed-in PC approves.
(function () {
    const $ = id => document.getElementById(id);
    if ($("phoneCode")) {
        const check = () => fetch("/phone/?check=1", { credentials: "same-origin", headers: { Accept: "application/json" } })
            .then(r => r.json()).then(data => {
                if (data.state === "approved") { $("phoneStatus").textContent = "Approved. Opening ALFRED…"; location.assign(data.next || "/"); }
                else if (data.state === "expired") { $("phoneStatus").textContent = "This code expired. Get a new code."; }
                else setTimeout(check, 3000);
            }).catch(() => setTimeout(check, 5000));
        setTimeout(check, 3000);
    }
    const form = $("phoneApproveForm");
    if (form) form.addEventListener("submit", event => {
        event.preventDefault();
        const status = $("phoneApproveStatus");
        Alfred.fetchJSON("/phone/approve/", { method: "POST", body: JSON.stringify({ code: $("phoneApproveCode").value }) })
            .then(data => { status.textContent = data.detail; form.reset(); })
            .catch(error => { status.textContent = error.message; });
    });
})();
