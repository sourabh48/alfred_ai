// More career tools (Career Ops modes, owner approval 2026-11-18): master profile, GitHub, companies, gambit and retro.
(function () {
    const $ = id => document.getElementById(id), e = Alfred.escapeHtml, URL = "/api/career/tools/";
    if (!$("careerToolsTitle")) return;
    let retroRules = [], retroText = "";

    function say(text, kind = "success") {
        const box = $("careerToolsFeedback");
        box.className = `alert alert-${kind}`;
        box.textContent = text;
    }

    function post(body, button, done) {
        if (button) button.disabled = true;
        return Alfred.fetchJSON(URL, { method: "POST", body: JSON.stringify(body) })
            .then(data => { render(data); if (done) done(data.result); return data; })
            .catch(error => say(error.message, "danger"))
            .finally(() => { if (button) button.disabled = false; });
    }

    const factList = (facts, name, checked) => facts.length ? `<ul class="list-unstyled small mb-2">${facts.map(f => `<li class="form-check">
        <input class="form-check-input" type="checkbox" id="${name}-${e(f.id)}" data-${name}="${e(f.id)}" ${checked ? "checked" : ""}>
        <label class="form-check-label" for="${name}-${e(f.id)}"><span class="badge text-bg-light me-1">${e(f.kind)}</span>${e(f.text)}
            <span class="muted"> · ${e(f.source)}</span></label></li>`).join("")}</ul>` : "";

    function render(data) {
        const p = data.profile;
        $("careerProfileBody").innerHTML = `${p.facts.length ? `<p class="small fw-semibold mb-1">Kept (${p.facts.length}). Untick to drop one.</p>${factList(p.facts, "profile-kept", true)}` : ""}
            ${p.new.length ? `<p class="small fw-semibold mb-1">New from your CV (${p.new.length}). Tick the true ones.</p>${factList(p.new, "profile-new", false)}` : ""}
            ${p.facts.length || p.new.length ? `<button class="btn btn-outline-secondary btn-sm" type="button" id="careerProfileSave">Save my profile</button>` : `<p class="small mb-0">Upload your CV to build your profile.</p>`}
            <p class="small muted mt-2 mb-0">${e(p.basis)}${p.saved_at ? ` Saved ${e(new Date(p.saved_at).toLocaleString())}.` : ""}</p>`;
        if (!$("careerGithubUser").value && data.github) $("careerGithubUser").value = data.github;
        $("careerRepliesCheck").disabled = !data.replies_ready;
        if (!data.replies_ready && !$("careerRepliesBody").innerHTML) $("careerRepliesBody").innerHTML = '<p class="small mb-0">Choose your Career email address in Settings first; reply watch reads that inbox, only if you allowed reading.</p>';
        const s = data.sponsor || {};
        $("careerSponsorStatus").innerHTML = `Folder: <code>${e(s.imports_folder || "")}</code>. ${s.built_at
            ? `Read ${e(s.files.map(f => f.file).join(", "))} on ${e(new Date(s.built_at).toLocaleString())}: ${Alfred.formatNumber(s.employers)} employers.`
            : "No file read yet."}${s.waiting && s.waiting.length ? ` In the folder: ${e(s.waiting.join(", "))}.` : ""}`;
        const companies = data.companies || [];
        $("careerCompaniesBody").innerHTML = companies.length
            ? `<ul class="small mb-0">${companies.map(c => `<li>${e(c.name)} <span class="muted">(${e(c.board)})</span>
                <button type="button" class="btn btn-link btn-sm p-0 ms-1" data-company-remove="${e(c.name)}" aria-label="Stop watching ${e(c.name)}">Remove</button></li>`).join("")}</ul>`
            : '<p class="small mb-0">No companies yet.</p>';
    }

    function profileSave(button) {
        const keep = [...document.querySelectorAll("[data-profile-new]:checked, [data-github]:checked")].map(b => b.dataset.profileNew || b.dataset.github);
        const drop = [...document.querySelectorAll("[data-profile-kept]:not(:checked), [data-profile-new]:not(:checked)")]
            .map(b => b.dataset.profileKept || b.dataset.profileNew);
        const username = document.querySelector("[data-github]:checked") ? $("careerGithubUser").value.trim() : "";
        post({ operation: "profile_save", keep, drop, username }, button, () => {
            $("careerGithubBody").innerHTML = "";
            say("Profile saved.");
        });
    }

    function roles(result) {
        $("careerCompaniesBody").innerHTML = `${result.roles.length ? `<ul class="small mb-1">${result.roles.map(r => `<li><a href="${e(r.url)}" target="_blank" rel="noopener noreferrer">${e(r.title)}</a>
            <span class="muted"> · ${e(r.company)}${r.location ? ` · ${e(r.location)}` : ""}</span>
            <button type="button" class="btn btn-link btn-sm p-0 ms-1" data-role-check="${e(r.url)}">Check against my CV</button></li>`).join("")}</ul>`
            : '<p class="small mb-1">No open roles match your target roles right now.</p>'}
            ${result.more ? `<p class="small muted mb-1">${e(result.more)} more not shown.</p>` : ""}
            ${result.failed.length ? `<p class="small muted mb-1">Could not read: ${e(result.failed.join(", "))}.</p>` : ""}
            <p class="small muted mb-0">${e(result.basis)}${result.targets.length ? ` Matching: ${e(result.targets.join(", "))}.` : " No target roles set, so every role is listed."}</p>`;
    }

    document.addEventListener("click", event => {
        const save = event.target.closest("#careerProfileSave, #careerGithubSave");
        if (save) profileSave(save);
        const remove = event.target.closest("[data-company-remove]");
        if (remove) post({ operation: "company_remove", name: remove.dataset.companyRemove }, remove, () => say("Removed."));
        const check = event.target.closest("[data-role-check]");
        if (check) {
            $("careerJobUrl").value = check.dataset.roleCheck;
            $("careerJobUrl").focus();
            say("The job link is in “Check a job against your CV”. Press its check button to compare it with your CV.", "info");
        }
        const gambitSave = event.target.closest("#careerGambitSave");
        if (gambitSave) {
            gambitSave.disabled = true;
            Alfred.fetchJSON("/api/career/recruiter-match/", { method: "POST", body: JSON.stringify({ message_text: gambitSave.dataset.posting }) })
                .then(() => say("Saved as an opportunity. Triage, evaluation, CV and email drafts now work on it."))
                .catch(error => { gambitSave.disabled = false; say(error.message, "danger"); });
        }
        const stage = event.target.closest("[data-reply-apply]");
        if (stage) {
            stage.disabled = true;
            Alfred.fetchJSON(`/api/career/job-analyses/${encodeURIComponent(stage.dataset.replyApply)}/application/`,
                { method: "POST", body: JSON.stringify({ stage: stage.dataset.stage, ...(stage.dataset.on ? { on: stage.dataset.on } : {}) }) })
                .then(() => { stage.textContent = "Applied"; say(`Stage set to ${stage.dataset.stage}.`); })
                .catch(error => { stage.disabled = false; say(error.message, "danger"); });
        }
        const lead = event.target.closest("[data-lead-analyse]");
        if (lead) {  // CAREER-04: the chosen inbox email and its JD file go through the same recruiter intake as a paste
            lead.disabled = true;
            Alfred.fetchJSON("/api/career/recruiter-match/", { method: "POST", body: JSON.stringify({ mail_id: lead.dataset.leadAnalyse }) })
                .then(() => { lead.textContent = "Analysed and saved"; say("Saved as an opportunity. Triage, evaluation, CV and email drafts now work on it."); })
                .catch(error => { lead.disabled = false; say(error.message, "danger"); });
        }
        const apply = event.target.closest("#careerRetroApply");
        if (apply) {
            const rules = [...document.querySelectorAll("[data-retro]:checked")].map(b => retroRules[Number(b.dataset.retro)]);
            if (!rules.length) { say("Tick at least one rule.", "warning"); return; }
            post({ operation: "retro_apply", corrections: retroText, rules }, apply, r => {
                $("careerRetroBody").innerHTML = "";
                say(`Applied ${r.applied} rule(s). Your triage brief now starts from them.`);
            });
        }
    });

    $("careerGithubForm").addEventListener("submit", event => {
        event.preventDefault();
        post({ operation: "github", username: $("careerGithubUser").value.trim() }, event.submitter, r => {
            $("careerGithubBody").innerHTML = r.suggestions.length
                ? `<p class="small fw-semibold mb-1">On your public GitHub but not in your CV. Tick the true ones.</p>${factList(r.suggestions, "github", false)}
                   <button class="btn btn-outline-secondary btn-sm" type="button" id="careerGithubSave">Add ticked items to my profile</button>`
                : '<p class="small mb-0">Nothing new: your CV already mentions everything on your public GitHub.</p>';
        });
    });
    $("careerCompaniesForm").addEventListener("submit", event => {
        event.preventDefault();
        post({ operation: "companies_add", names: $("careerCompanyNames").value }, event.submitter, r => {
            const missed = r.results.filter(x => !x.board).map(x => x.name);
            $("careerCompanyNames").value = "";
            say(missed.length ? `No public Greenhouse, Lever or Ashby board found for: ${missed.join(", ")}.` : "Job boards found.", missed.length ? "warning" : "success");
        });
    });
    $("careerRepliesCheck").addEventListener("click", event => post({ operation: "replies" }, event.currentTarget, r => {
        $("careerRepliesBody").innerHTML = `${r.replies.length ? `<ul class="list-unstyled small mb-2">${r.replies.map(m => `<li class="mb-2">
            <span class="fw-semibold">${e(m.category)}</span> · ${e(m.company)}${m.role ? `, ${e(m.role)}` : ""} <span class="muted">(${e(m.on)}, now ${e(m.current_stage)})</span><br>
            <span class="muted">${e(m.subject)} · ${e(m.from)}${m.because ? ` · because it says “${e(m.because)}”` : ""}</span>
            ${m.suggested_stage ? `<br><button type="button" class="btn btn-outline-secondary btn-sm mt-1" data-reply-apply="${e(m.opportunity_id)}" data-stage="${e(m.suggested_stage)}" data-on="${e(m.on)}">Apply: set stage to ${e(m.suggested_stage)}</button>` : ""}</li>`).join("")}</ul>`
            : '<p class="small mb-2">No replies about your saved opportunities in the last 30 days.</p>'}
            ${(r.leads || []).length ? `<p class="small fw-semibold mb-1">New recruiter emails</p><ul class="list-unstyled small mb-2">${r.leads.map(m => `<li class="mb-2">
            ${e(m.subject)} <span class="muted">(${e(m.on)}, ${e(m.from_name || m.from)}${m.attachment ? ", has an attachment" : ""}; because it says “${e(m.because)}”)</span><br>
            <button type="button" class="btn btn-outline-secondary btn-sm mt-1" data-lead-analyse="${e(m.mail_id)}">Analyse${m.attachment ? " email and job description" : " this email"}</button></li>`).join("")}</ul>` : ""}
            <p class="small muted mb-0">${e(r.basis)}</p>`;
    }));
    $("careerSponsorImport").addEventListener("click", event => {
        say("Reading the LCA files. A full year can take a few minutes.", "info");
        post({ operation: "sponsor_import" }, event.currentTarget, r => say(`Read ${Alfred.formatNumber(r.employers)} employers.`));
    });
    $("careerSponsorForm").addEventListener("submit", event => {
        event.preventDefault();
        post({ operation: "sponsor_check", company: $("careerSponsorCompany").value }, event.submitter, r => {
            const label = { active: "Active sponsor", staffing: "Mostly third-party placements", weak: "Rare or old filings" };
            $("careerSponsorBody").innerHTML = `${r.matches.length ? `<ul class="list-unstyled small mb-2">${r.matches.map(m => `<li class="mb-2">
                <span class="fw-semibold">${e(m.name)}</span>: ${e(label[m.tier])}<br>
                <span class="muted">${Alfred.formatNumber(m.filings)} H-1B filings, ${Alfred.formatNumber(m.certified)} certified, latest ${e(m.latest || "unknown")}. ${e(m.why)}</span></li>`).join("")}</ul>` : ""}
                <p class="small muted mb-0">${e(r.basis)}</p>`;
        });
    });
    $("careerOpenRoles").addEventListener("click", event => post({ operation: "open_roles" }, event.currentTarget, roles));
    $("careerGambitForm").addEventListener("submit", event => {
        event.preventDefault();
        say("Your local AI is writing a proposal. This takes up to a minute.", "info");
        post({ operation: "gambit", company: $("careerGambitCompany").value, role: $("careerGambitRole").value, notes: $("careerGambitNotes").value },
            event.submitter, g => {
                const list = (title, items) => items.length ? `<p class="small fw-semibold mb-1">${title}</p><ul class="small mb-2">${items.map(x => `<li>${e(x)}</li>`).join("")}</ul>` : "";
                $("careerGambitBody").innerHTML = `<h3 class="h6">${e(g.title)} at ${e(g.company)}</h3>${list("Why they need it", g.why_they_need_it)}
                    ${list("Responsibilities", g.responsibilities)}${list("Requirements", g.requirements)}
                    ${g.pitch ? `<p class="small mb-2"><span class="fw-semibold">Pitch:</span> ${e(g.pitch)}</p>` : ""}
                    <button class="btn btn-outline-secondary btn-sm" type="button" id="careerGambitSave">Save as an opportunity</button>
                    <p class="small muted mt-2 mb-0">${e(g.basis)}</p>`;
                $("careerGambitSave").dataset.posting = g.posting;
                say("Proposal ready. Check every line before you use it.");
            });
    });
    $("careerRetroForm").addEventListener("submit", event => {
        event.preventDefault();
        retroText = $("careerRetroText").value;
        say("Your local AI is reading your corrections. This takes up to a minute.", "info");
        post({ operation: "retro", corrections: retroText }, event.submitter, r => {
            retroRules = r.rules;
            const label = rule => rule.field === "remote_ok" ? `Remote work: ${rule.value ? "yes" : "no"}`
                : rule.field === "pay_floor" ? `Pay floor: ${rule.currency} ${Alfred.formatNumber(rule.value, 0)}`
                : `${rule.action === "add" ? "Add" : "Remove"} “${rule.value}” ${rule.action === "add" ? "to" : "from"} ${rule.field.replaceAll("_", " ")}`;
            $("careerRetroBody").innerHTML = r.rules.length ? `<ul class="list-unstyled small mb-2">${r.rules.map((rule, i) => `<li class="form-check">
                <input class="form-check-input" type="checkbox" id="careerRetro-${i}" data-retro="${i}" checked>
                <label class="form-check-label" for="careerRetro-${i}">${e(label(rule))}${rule.why ? ` <span class="muted">· ${e(rule.why)}</span>` : ""}</label></li>`).join("")}</ul>
                <button class="btn btn-outline-secondary btn-sm" type="button" id="careerRetroApply">Apply ticked rules</button>
                <p class="small muted mt-2 mb-0">${e(r.basis)}</p>`
                : `<p class="small mb-0">No rule ALFRED can apply came out of that. Name the role, place, company or pay you mean.</p>`;
            say(r.rules.length ? "Rules ready. Untick any you do not want." : "No rules found.", r.rules.length ? "success" : "warning");
        });
    });
    Alfred.fetchJSON(URL).then(render).catch(error => say(error.message, "danger"));
})();
