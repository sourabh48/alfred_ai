// Settings > Skills: read a GitHub skill file into the form for review; saving approves exactly that text.
(function () {
    const $ = id => document.getElementById(id), URL = "/api/settings/skills/";
    if (!$("settingsSkills")) return;
    const scopes = { general: "General", travel: "Travel", career: "Career", finance: "Money", documents: "Documents" };

    function say(text, kind) {
        const box = $("skillsFeedback");
        box.className = text ? `alert alert-${kind} mb-2` : "d-none alert mb-2";
        box.textContent = text;
    }

    function render(data) {
        const list = $("skillsList");
        list.replaceChildren(...data.skills.map(skill => {
            const item = document.createElement("li"), title = document.createElement("strong"), remove = document.createElement("button");
            item.className = "d-flex align-items-center gap-2 mb-1";
            title.textContent = skill.name;
            remove.type = "button"; remove.className = "btn btn-link btn-sm text-danger ms-auto"; remove.textContent = "Delete";
            remove.setAttribute("aria-label", `Delete skill ${skill.name}`);
            remove.addEventListener("click", () => send({ action: "delete", id: skill.id }, "Deleted."));
            item.append(title, document.createTextNode(` · ${scopes[skill.scope] || skill.scope}${skill.description ? " · " + skill.description : ""}`), remove);
            return item;
        }));
        if (!data.skills.length) list.textContent = "No skills yet.";
        if (data.draft) {
            $("skillsName").value = data.draft.name; $("skillsDescription").value = data.draft.description;
            $("skillsText").value = data.draft.text; $("skillsSource").value = data.draft.source;
            say(`Read from GitHub${data.draft.cut ? " (cut to 4,000 characters)" : ""}. Check the instructions below, choose what it is used for, then approve.`, "info");
        }
    }

    function send(body, done) {
        return Alfred.fetchJSON(URL, { method: "POST", body: JSON.stringify(body) })
            .then(data => { say(done || "", "success"); render(data); return data; })
            .catch(error => { say(error.message, "danger"); return null; });
    }

    Alfred.fetchJSON(URL).then(render).catch(error => say(error.message, "danger"));
    $("skillsImportForm").addEventListener("submit", event => { event.preventDefault(); send({ action: "import", url: $("skillsImportUrl").value }); });
    $("skillsForm").addEventListener("submit", event => {
        event.preventDefault();
        const form = event.currentTarget;
        send({ action: "save", name: $("skillsName").value, description: $("skillsDescription").value, scope: $("skillsScope").value,
               text: $("skillsText").value, source: $("skillsSource").value }, "Saved.").then(data => { if (data) form.reset(); });
    });
})();
