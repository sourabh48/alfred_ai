/* Local saved-trip checklist. Drafts stay in memory, never browser storage. */
window.TravelPacking = (() => {
    const esc = value => Alfred.escapeHtml(String(value ?? ''));
    const drafts = new Map();
    let current, send, reload, plan, pendingId;
    function clear() { drafts.clear(); pendingId=null; plan=null; }
    function identity() {
        const bytes=crypto.getRandomValues(new Uint8Array(16));
        bytes[6]=(bytes[6]&15)|64;bytes[8]=(bytes[8]&63)|128;
        const hex=Array.from(bytes,b=>b.toString(16).padStart(2,'0')).join('');
        return `${hex.slice(0,8)}-${hex.slice(8,12)}-${hex.slice(12,16)}-${hex.slice(16,20)}-${hex.slice(20)}`;
    }
    function render(session) {
        if (plan!==session.plan_id) {clear();plan=session.plan_id;}
        const list=session.packing_checklist;
        const panel=document.getElementById('plannerPacking');
        panel.hidden=false;
        if (!list) {
            Alfred.setHTMLIfChanged(panel,'<h2 class="h5">Private packing checklist</h2><p>Save this trip or a draft to start a persistent checklist.</p>');
            return;
        }
        Alfred.setHTMLIfChanged(panel,`<h2 class="h5">Private packing checklist</h2><p>Changes save automatically to this trip on your local ALFRED server. No internet connection is needed. Suggestions are editable; they do not confirm safety or a booking.</p><p id="packingStatus" role="status">${list.items.filter(i=>i.packed).length} of ${list.items.length} packed · checklist revision ${list.revision}</p><button type="button" class="btn btn-sm btn-outline-primary mb-3" data-packing-reload data-packing-control>Reload checklist, keep drafts</button><ul class="travel-packing-list">${list.items.map(item=>`<li data-packing-item="${esc(item.id)}"><label class="travel-packing-check"><input type="checkbox" data-packing-toggle="${esc(item.id)}" data-packing-control ${item.packed?'checked':''}><span>${esc(item.label)}</span></label><div class="travel-actions"><details><summary>Edit ${esc(item.label)}</summary><form data-packing-edit="${esc(item.id)}"><label>Item name<input class="form-control" name="label" maxlength="160" required data-packing-control value="${esc(drafts.get(item.id)??item.label)}"></label><button class="btn btn-sm btn-primary" data-packing-control>Save item</button></form></details><button type="button" class="btn btn-sm btn-outline-secondary" aria-label="Remove ${esc(item.label)}" data-packing-remove="${esc(item.id)}" data-packing-control>Remove</button></div></li>`).join('')}</ul><form data-packing-add><label class="d-block">Packing item<input class="form-control" name="label" maxlength="160" required data-packing-control value="${esc(drafts.get('add')??'')}"></label><button class="btn btn-sm btn-primary mt-2" data-packing-control ${list.items.length>=list.limit?'disabled data-batch-unavailable="true"':''}>Add packing item</button><p class="small">Up to ${list.limit} items; repeated names are rejected. Uncheck to mark an item unpacked. Reminders are not enabled.</p></form>`);
    }
    async function change(operation,itemId,fields={},draftKey=null) {
        const session=current(), list=session?.packing_checklist;
        if (!list) return;
        const selectedPlan=session.plan_id;
        const accepted=await send({action:'packing',operation,item_id:itemId,checklist_revision:list.revision,...fields});
        if (current()?.plan_id!==selectedPlan) return;
        if (accepted && draftKey!==null) {drafts.delete(draftKey);if(draftKey==='add')pendingId=null;}
        if (current()?.packing_checklist) render(current());
        document.querySelectorAll('[data-packing-toggle]').forEach(input=>{
            input.checked=!!current()?.packing_checklist?.items.find(item=>item.id===input.dataset.packingToggle)?.packed;
        });
        const target=operation==='add'?'[data-packing-add] input':`[data-packing-item="${itemId}"] input`;
        document.querySelector(target)?.focus();
    }
    function init(options) {
        ({current,send,reload}=options);
        const panel=document.getElementById('plannerPacking');
        panel.addEventListener('input',event=>{
            const form=event.target.closest('form');
            if(form && event.target.name==='label')drafts.set(form.dataset.packingEdit||'add',event.target.value);
        });
        panel.addEventListener('submit',async event=>{
            event.preventDefault();
            const form=event.target, label=form.elements.label.value;
            if(form.hasAttribute('data-packing-add')) {pendingId??=identity();await change('add',pendingId,{label},'add');}
            else await change('update',form.dataset.packingEdit,{label},form.dataset.packingEdit);
        });
        panel.addEventListener('change',async event=>{
            if(event.target.dataset.packingToggle)await change('update',event.target.dataset.packingToggle,{packed:event.target.checked});
        });
        panel.addEventListener('click',async event=>{
            const button=event.target.closest('button');
            if(button?.dataset.packingRemove)await change('remove',button.dataset.packingRemove);
            if(button?.hasAttribute('data-packing-reload'))await reload();
        });
    }
    return {init,render,clear};
})();
