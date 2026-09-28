document.addEventListener("DOMContentLoaded", () => {
    const root = document.getElementById("travelPreferences");
    if (!root) return;
    const $ = id=>document.getElementById(id);
    const esc = x=>Alfred.escapeHtml(String(x ?? ""));
    const url = "/api/mobility/planner/preferences/";
    function render(p) {
        $("travelNovelty").value=p.novelty;
        $("travelLearning").checked=p.learning_enabled;
        $("travelMediaLearning").checked=p.media_learning_enabled;
        $("travelPreferenceList").innerHTML=Object.entries(p.preferences).map(([k,v])=>`<div class="travel-preference"><div><strong>${esc(k)}: ${esc(v.value)}</strong><small>${v.confirmed_by_user ? "Set by you" : "Tentative inference"} · confidence ${esc(v.confidence)}</small><small>${esc((v.reasons || [v.source]).join(" · "))}</small></div><div><button class="btn btn-sm btn-outline-primary" data-preference="${esc(k)}" data-preference-action="accept">Accept</button> <button class="btn btn-sm btn-outline-secondary" data-preference="${esc(k)}" data-preference-action="remove">Remove</button></div></div>`).join("") || "No travel preferences learned yet.";
    }
    async function update(data) {
        try {render(await Alfred.fetchJSON(url,{method:"PATCH",body:JSON.stringify(data)}));$("travelPreferencesAlert").textContent="Travel preferences saved.";}
        catch(e){$("travelPreferencesAlert").textContent=e.message;}
    }
    $("travelNovelty").addEventListener("change", e=>update({novelty:e.target.value}));
    $("travelLearning").addEventListener("change", e=>update({learning_enabled:e.target.checked}));
    $("travelMediaLearning").addEventListener("change", e=>update({media_learning_enabled:e.target.checked}));
    $("travelResetPreferences").addEventListener("click", ()=>update({action:"reset"}));
    $("travelPreferenceForm").addEventListener("submit", e=>{e.preventDefault();update({key:$("travelPreferenceKey").value,value:true});});
    root.addEventListener("click", e=>{const b=e.target.closest("button[data-preference]");if(b)update({key:b.dataset.preference,action:b.dataset.preferenceAction,value:true});});
    Alfred.fetchJSON(url).then(render).catch(e=>{$("travelPreferencesAlert").textContent=e.message;});
});
