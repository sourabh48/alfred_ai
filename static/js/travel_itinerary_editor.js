/* Manual edits share the existing planner request/session boundary. */
window.TravelItineraryEditor = (() => {
    const esc = value => Alfred.escapeHtml(String(value ?? ""));
    const drafts = new Map(), requests = new Map();
    let session, action, dragging;
    function requestId() {
        const bytes=crypto.getRandomValues(new Uint8Array(16));
        bytes[6]=(bytes[6]&15)|64; bytes[8]=(bytes[8]&63)|128;
        const hex=Array.from(bytes,b=>b.toString(16).padStart(2,'0')).join('');
        return `${hex.slice(0,8)}-${hex.slice(8,12)}-${hex.slice(12,16)}-${hex.slice(16,20)}-${hex.slice(20)}`;
    }
    const button = (label, attrs, disabled=false) => `<button type="button" class="btn btn-sm btn-outline-secondary" data-editor-control data-batch-unavailable="${disabled}" ${disabled ? 'disabled' : ''} ${attrs}>${esc(label)}</button>`;
    function fields(item, key) {
        const values = drafts.get(key) || item;
        return ["title", "period", "duration"].map(name=>`<label class="d-block">${esc(name[0].toUpperCase()+name.slice(1))}<input class="form-control form-control-sm" name="${name}" value="${esc(values[name])}" maxlength="${{title:240,period:120,duration:200}[name]}" required data-editor-control></label>`).join("")+
            `<label class="d-block">Priority<select class="form-select form-select-sm" name="priority" data-editor-control>${["Must Do","Recommended","Optional","Backup"].map(v=>`<option${values.priority===v?' selected':''}>${v}</option>`).join("")}</select></label>`;
    }
    function markup(next) {
        if (session?.id !== next.id) { drafts.clear(); requests.clear(); }
        session = next;
        const it = next.itinerary, meta = next.itinerary_editor;
        return `<section aria-label="Desktop itinerary editor" data-itinerary-editor><p>Drag activity blocks between days or drag the ordered stops above. Earlier/Later and day buttons provide the same keyboard-accessible controls. Travel legs follow stop order.</p><div class="travel-actions mb-3">${button("Undo last itinerary edit",'data-editor-undo',!meta.can_undo)}${button("Reload trip, keep activity drafts",'data-editor-reload')}<span role="status">Trip revision ${next.revision}</span></div>${it.budget?.status==='needs_recalculation'?`<p role="status" class="alert alert-warning">${esc(it.budget.recheck_note)} Route distance/time and edited activity prices are unverified. Save explicitly to retain this draft.</p>`:''}<details class="mb-3"><summary>Revision history (latest20; undo up to${meta.history_limit})</summary><ol>${meta.history.map(row=>`<li>Revision ${row.revision}: ${esc(row.operation.replaceAll('_',' '))} · ${esc(new Date(row.at).toLocaleString())}</li>`).join('') || '<li>No desktop edits yet.</li>'}</ol></details><div class="travel-itinerary-days">${it.days.map((day,dayIndex)=>`<article class="travel-day" data-day="${day.day}" data-editor-day="${esc(day.id)}"><p class="travel-fit">DAY ${day.day} ${esc(day.date || '· dates flexible')}</p><h3 class="h5">${esc(day.title)}</h3><ul>${day.items.map((item,index)=>`<li data-editor-item="${esc(item.id)}" ${item.type!=='travel'?'draggable="true"':''}><span class="travel-priority">${esc(item.priority)} · ${esc(item.period)}</span><br><strong>${esc(item.title)}</strong><p>${esc(item.duration)}${item.cost?` · Previous allowance ${esc(Alfred.formatCurrency(item.cost))}`:''}</p>${item.cost_note?`<p class="small">${esc(item.cost_note)}</p>`:''}${item.type==='travel'?'<p class="small">Generated travel leg; use stop controls to change the journey.</p>':`<div class="travel-actions">${button('Earlier',`data-editor-move="-1" aria-label="Move ${esc(item.title)} earlier"`,index===0)}${button('Later',`data-editor-move="1" aria-label="Move ${esc(item.title)} later"`,index===day.items.length-1)}${button('Previous day','data-editor-day-move="-1"',dayIndex===0)}${button('Next day','data-editor-day-move="1"',dayIndex===it.days.length-1)}${button('Remove activity','data-editor-remove')}</div><details class="mt-2"><summary>Edit ${esc(item.title)}</summary><form data-editor-form="update:${esc(item.id)}" data-editor-update="${esc(item.id)}">${fields(item,'update:'+item.id)}<button class="btn btn-sm btn-primary mt-2" data-editor-control>Save activity</button></form></details>`}</li>`).join('')}</ul><details><summary>Add activity to day ${day.day}</summary><form data-editor-form="add:${esc(day.id)}" data-editor-add><label class="d-block">Activity title<input class="form-control" name="title" maxlength="240" value="${esc(drafts.get('add:'+day.id)?.title || '')}" required data-editor-control></label><button class="btn btn-sm btn-primary mt-2" data-editor-control>Add activity</button></form></details><p><strong>Stay:</strong> ${esc(day.stay)}</p><p><strong>Meals:</strong> ${esc(day.meals)}</p><p>${esc(day.pace || 'balanced')} pace</p><strong>${it.budget?.status==='needs_recalculation'?'Previous day allowance':'Day allowance'}: ${esc(Alfred.formatCurrency(day.estimated_cost))}</strong></article>`).join('')}</div></section>`;
    }
    async function dispatch(operation, fields={}, key=operation) {
        if (!session || !action) return false;
        const signature = JSON.stringify({operation,...fields});
        let intent = requests.get(key);
        if (!intent || intent.signature!==signature) {
            intent = {signature,payload:{action:'itinerary_edit',operation,...fields,revision:session.revision,request_id:requestId()}};
            requests.set(key,intent);
        }
        const savedDraft = drafts.get(key); drafts.delete(key);
        const accepted = await action(intent.payload);
        if (accepted) requests.delete(key);
        else if (savedDraft) drafts.set(key,savedDraft);
        return accepted;
    }
    function orderStops(names) {
        const ids = new Map(session.itinerary_editor.stops.map(stop=>[stop.name,stop.id]));
        return dispatch('order_stops',{stops:names.map(name=>ids.get(name))},'stops');
    }
    function init(callback) {
        action = callback;
        document.addEventListener('input',event=>{
            const form=event.target.closest('[data-editor-form]');
            if (form) drafts.set(form.dataset.editorForm,Object.fromEntries(new FormData(form)));
        });
        document.addEventListener('submit',async event=>{
            const form=event.target.closest('[data-editor-form]');
            if (!form) return;
            event.preventDefault();
            if (!form.reportValidity()) return;
            const day=form.closest('[data-editor-day]');
            await dispatch(form.hasAttribute('data-editor-add')?'add':'update',{
                day_id:day.dataset.editorDay,...(form.dataset.editorUpdate?{item_id:form.dataset.editorUpdate}:{}),
                fields:Object.fromEntries(new FormData(form))},form.dataset.editorForm);
        });
        document.addEventListener('click',async event=>{
            const control=event.target.closest('[data-editor-control]');
            if (!control || control.disabled || control.matches('input,select')) return;
            const row=control.closest('[data-editor-item]'), day=control.closest('[data-editor-day]');
            if (control.hasAttribute('data-editor-undo')) await dispatch('undo');
            if (control.hasAttribute('data-editor-reload') && await window.TravelPlanner.reload()) requests.clear();
            if (control.hasAttribute('data-editor-remove')) await dispatch('remove',{day_id:day.dataset.editorDay,item_id:row.dataset.editorItem},'remove:'+row.dataset.editorItem);
            if (control.dataset.editorMove) {
                const model=session.itinerary.days.find(d=>d.id===day.dataset.editorDay), index=model.items.findIndex(i=>i.id===row.dataset.editorItem);
                const before = Number(control.dataset.editorMove)<0 ? model.items[index-1]?.id : model.items[index+2]?.id;
                await dispatch('move',{day_id:model.id,item_id:row.dataset.editorItem,before_id:before || null},'move:'+row.dataset.editorItem);
            }
            if (control.dataset.editorDayMove) {
                const index=session.itinerary.days.findIndex(d=>d.id===day.dataset.editorDay), target=session.itinerary.days[index+Number(control.dataset.editorDayMove)];
                if (target) await dispatch('move',{day_id:target.id,item_id:row.dataset.editorItem},'move:'+row.dataset.editorItem);
            }
        });
        document.addEventListener('dragstart',event=>{
            if (event.target.closest('input,select,textarea,button,a')) return;
            const item=event.target.closest('[data-editor-item][draggable="true"]'), stop=event.target.closest('[data-editor-stop][draggable="true"]');
            if (!item && !stop) return;
            dragging={kind:item?'item':'stop',id:item?.dataset.editorItem || stop.dataset.editorStop,session:session.id};
            event.dataTransfer.setData('text/plain','Reorder itinerary'); event.dataTransfer.effectAllowed='move';
        });
        document.addEventListener('dragover',event=>{
            if (dragging && event.target.closest(dragging.kind==='item'?'[data-editor-day]':'[data-editor-stop]')) event.preventDefault();
        });
        document.addEventListener('drop',async event=>{
            const source=dragging; dragging=null;
            if (!source || source.session!==session?.id) return;
            const target=event.target.closest(source.kind==='item'?'[data-editor-day]':'[data-editor-stop]');
            if (!target) return;
            event.preventDefault();
            if (source.kind==='item') {
                const before=event.target.closest('[data-editor-item]')?.dataset.editorItem;
                if (before===source.id) return;
                await dispatch('move',{day_id:target.dataset.editorDay,item_id:source.id,before_id:before || null},'move:'+source.id);
            } else {
                const order=session.itinerary_editor.stops.map(stop=>stop.id), from=order.indexOf(source.id), to=order.indexOf(target.dataset.editorStop);
                if (from<0 || to<0 || from===to) return;
                order.splice(from,1); order.splice(to,0,source.id);
                await dispatch('order_stops',{stops:order},'stops');
            }
        });
        document.addEventListener('dragend',()=>{dragging=null;});
        addEventListener('pagehide',()=>{drafts.clear();requests.clear();dragging=null;session=null;});
    }
    return {markup,init,orderStops};
})();
