/* Private local schedules; delivery is durable in-app data, never an external notification. */
window.TravelReminders = (() => {
    const esc=value=>Alfred.escapeHtml(String(value??''));
    const drafts=new Map();
    let current,send,reload,plan,pending,createId;
    function clear(){drafts.clear();plan=null;pending=null;createId=null;}
    function identity(){
        const bytes=crypto.getRandomValues(new Uint8Array(16));bytes[6]=(bytes[6]&15)|64;bytes[8]=(bytes[8]&63)|128;
        const hex=Array.from(bytes,b=>b.toString(16).padStart(2,'0')).join('');
        return `${hex.slice(0,8)}-${hex.slice(8,12)}-${hex.slice(12,16)}-${hex.slice(16,20)}-${hex.slice(20)}`;
    }
    const disabled=()=>pending?'disabled data-batch-unavailable="true"':'';
    function fields(key,row={}){
        const value=drafts.get(key)||row;
        return `<label>Reminder name<input class="form-control" name="label" maxlength="160" required data-reminder-control ${disabled()} value="${esc(value.label)}"></label><label>IANA timezone<input class="form-control" name="zone" maxlength="64" placeholder="e.g. Asia/Kolkata" required data-reminder-control ${disabled()} value="${esc(value.zone)}"></label><label>Local date and time<input class="form-control" type="datetime-local" name="local_time" step="60" required data-reminder-control ${disabled()} value="${esc(value.local_time)}"></label><label>If the clock repeats this time<select class="form-select" name="fold" data-reminder-control ${disabled()}><option value="" ${value.fold==null||value.fold===''?'selected':''}>Ask me if ambiguous</option><option value="0" ${String(value.fold)==='0'?'selected':''}>First occurrence</option><option value="1" ${String(value.fold)==='1'?'selected':''}>Second occurrence</option></select></label>`;
    }
    function render(session){
        if(plan!==session.plan_id){clear();plan=session.plan_id;}
        const policy=session.travel_reminders,panel=document.getElementById('plannerReminders');panel.hidden=false;
        if(!policy){Alfred.setHTMLIfChanged(panel,'<h2 class="h5">Local trip reminders</h2><p>Save this trip or a draft to choose reminders. Reminders are off by default.</p>');return;}
        Alfred.setHTMLIfChanged(panel,`<h2 class="h5">Local trip reminders</h2><p>Explicit opt-in applies only to this trip. Delivery appears here while the local ALFRED Huey worker runs; after downtime, overdue delivery is labelled late. No email, SMS or external notification is sent.</p><label class="travel-packing-check"><input type="checkbox" data-reminder-consent data-reminder-control ${policy.enabled?'checked':''} ${policy.closed?'disabled data-batch-unavailable="true"':disabled()}><span>Enable local in-app reminders for this trip</span></label><p role="status">Reminders ${policy.enabled?'ON':'OFF'} · revision ${policy.revision}${policy.closed?' · completed/cancelled trip; no delivery':''}. Opt-out cancels pending occurrences; enabling again does not revive them.</p><div class="travel-actions mb-3"><button type="button" class="btn btn-sm btn-outline-primary" data-reminder-reload data-reminder-control>Reload reminders, keep drafts</button>${pending?'<button type="button" class="btn btn-sm btn-outline-primary" data-reminder-retry data-reminder-control>Retry unconfirmed change</button><p role="alert">Change not confirmed. Retry or reload before another change. Your form draft is retained.</p>':''}</div><ul class="travel-reminder-list">${policy.reminders.map(row=>`<li data-reminder-id="${esc(row.id)}"><strong>${esc(row.label)}</strong><p>${esc(row.local_time.replace('T',' '))} · ${esc(row.zone)} · ${esc(row.status)}<br>UTC due: ${esc(row.due_at)}</p>${policy.enabled&&!policy.closed?`<details><summary>${row.status==='scheduled'?'Edit schedule':'Reschedule'} ${esc(row.label)}</summary><form data-reminder-form="${esc(row.id)}" data-reminder-operation="${row.status==='scheduled'?'edit':'reschedule'}">${fields(row.id,row)}<button class="btn btn-sm btn-primary" data-reminder-control ${disabled()}>${row.status==='scheduled'?'Save reminder changes':'Schedule new occurrence'}</button></form></details>`:''}${row.status==='scheduled'?`<button type="button" class="btn btn-sm btn-outline-secondary mt-2" data-reminder-cancel="${esc(row.id)}" data-reminder-control ${disabled()}>Cancel ${esc(row.label)}</button>`:''}</li>`).join('')||'<li>No reminders scheduled.</li>'}</ul>${policy.enabled&&!policy.closed?`<details open><summary>Create reminder</summary><form data-reminder-form="create" data-reminder-operation="create">${fields('create')}<button class="btn btn-sm btn-primary" data-reminder-control ${disabled()}>Schedule local reminder</button></form></details>`:''}<p class="small">Up to ${policy.limit} reminders and ${policy.delivery_limit} retained delivery occurrences per trip. Choose your timezone explicitly; nonexistent clock-change times are rejected.</p><h3 class="h6">Delivered in-app reminders</h3><p class="small">Delivery timestamps below use this browser’s timezone.</p><ol>${policy.deliveries.map(row=>`<li data-reminder-delivery="${esc(row.occurrence_id)}"><strong>${esc(row.label)}</strong> · ${row.late?'Delivered late':'Delivered on time'}<br>Due ${esc(new Date(row.due_at).toLocaleString())}; delivered ${esc(new Date(row.delivered_at).toLocaleString())}</li>`).join('')||'<li>No deliveries yet.</li>'}</ol>`);
    }
    async function dispatch(payload,key=null,retry=false){
        const session=current();if(!session?.travel_reminders||pending&&!retry)return;
        const selected=session.plan_id;
        pending??={action:'reminders',request_id:identity(),reminder_revision:session.travel_reminders.revision,...payload};
        const accepted=await send(pending,error=>{if(error.status>=400&&error.status<500&&error.status!==409)pending=null;});
        if(current()?.plan_id!==selected)return;
        if(accepted){pending=null;if(key!==null){drafts.delete(key);if(key==='create')createId=null;}}
        if(current()?.travel_reminders){render(current());const checkbox=document.querySelector('[data-reminder-consent]');if(checkbox)checkbox.checked=current().travel_reminders.enabled;}
    }
    async function refresh(){
        const done=await reload();
        if(done){if(pending?.operation==='create'&&current()?.travel_reminders?.reminders.some(r=>r.id===pending.reminder_id)){drafts.delete('create');createId=null;}pending=null;render(current());}
    }
    function init(options){
        ({current,send,reload}=options);
        const panel=document.getElementById('plannerReminders');
        const remember=event=>{const form=event.target.closest('[data-reminder-form]');if(form)drafts.set(form.dataset.reminderForm,Object.fromEntries(new FormData(form)));};
        panel.addEventListener('input',remember);
        panel.addEventListener('submit',async event=>{
            const form=event.target.closest('[data-reminder-form]');if(!form)return;event.preventDefault();
            const data=Object.fromEntries(new FormData(form)),key=form.dataset.reminderForm;
            if(data.fold==='')delete data.fold;else data.fold=Number(data.fold);
            if(key==='create')createId??=identity();
            await dispatch({operation:form.dataset.reminderOperation,reminder_id:key==='create'?createId:key,...data},key);
        });
        panel.addEventListener('change',async event=>{remember(event);if(event.target.hasAttribute('data-reminder-consent'))await dispatch({operation:'consent',enabled:event.target.checked});});
        panel.addEventListener('click',async event=>{
            const button=event.target.closest('button');if(!button)return;
            if(button.dataset.reminderCancel)await dispatch({operation:'cancel',reminder_id:button.dataset.reminderCancel});
            if(button.hasAttribute('data-reminder-retry'))await dispatch(null,pending?.operation==='create'?'create':pending?.reminder_id,true);
            if(button.hasAttribute('data-reminder-reload'))await refresh();
        });
    }
    return {init,render,clear};
})();
