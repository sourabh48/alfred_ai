/* Export-only owner selections; source identities and dates come from the saved trip. */
window.TravelCalendar = (() => {
    let choices=null;
    const panel=()=>document.getElementById('plannerCalendar');
    const esc=value=>Alfred.escapeHtml(String(value??''));
    function clear(){choices=null;panel().replaceChildren();panel().hidden=true;}
    function render(data){
        if(choices?.snapshot===data.snapshot){panel().hidden=false;return;}
        const previous=choices?options():null,oldChoices=choices;
        choices=data;panel().hidden=false;
        panel().innerHTML=`<h3 class="h6">Review saved calendar dates</h3><p>Saved location: ${esc(data.location)}</p><p>Only owner-confirmed saved dates are included. Date-only entries do not establish departure times or durations. Optional selections apply only to this download; your trip is unchanged.</p>
            <p role="status">${esc(data.warnings.join(' ')||'No date omissions reported.')}</p>
            <label for="calendarZone">IANA timezone (required for exact times)</label><input id="calendarZone" class="form-control mb-2" type="text" maxlength="64" placeholder="e.g. Asia/Kolkata" autocomplete="off">
            ${data.activities.map((row,index)=>`<details data-calendar-event="${esc(row.id)}" class="mb-2"><summary>${esc(row.date)} — ${esc(row.title)}</summary>
                <label for="calendarMode${index}">Timing evidence</label><select id="calendarMode${index}" class="form-select" data-calendar-field="mode"><option value="date">Saved date only</option><option value="range">Confirm last included date</option><option value="timed">Use my confirmed exact start/end</option></select>
                <div data-calendar-mode="range" hidden><label for="calendarThrough${index}">Last included date</label><input id="calendarThrough${index}" type="date" class="form-control" data-calendar-field="through"></div>
                <div data-calendar-mode="timed" hidden>${['start','end'].map(kind=>`<label for="calendar${kind}${index}">Confirmed local ${kind} date/time</label><input id="calendar${kind}${index}" type="datetime-local" class="form-control" data-calendar-field="${kind}">
                    <label for="calendar${kind}Fold${index}">If this ${kind} time occurs twice</label><select id="calendar${kind}Fold${index}" class="form-select" data-calendar-field="${kind}_fold"><option value="">Choose only if the clock repeats</option><option value="0">First occurrence</option><option value="1">Second occurrence</option></select>`).join('')}</div></details>`).join('')}
            ${data.activities.length?'':'<p>No exportable activities. Confirm and save trip dates first.</p>'}`;
        if(previous){
            document.getElementById('calendarZone').value=previous.zone;
            for(const draft of previous.events){
                const old=oldChoices.activities.find(row=>row.id===draft.id),current=data.activities.find(row=>row.id===draft.id);
                if(!current || old.date!==current.date || old.title!==current.title || oldChoices.location!==data.location)continue;
                const row=panel().querySelector(`[data-calendar-event="${draft.id}"]`),mode=row.querySelector('[data-calendar-field="mode"]');
                mode.value=draft.through!==undefined?'range':'timed';
                for(const [key,value] of Object.entries(draft)){const input=row.querySelector(`[data-calendar-field="${key}"]`);if(input)input.value=value;}
                row.querySelectorAll('[data-calendar-mode]').forEach(part=>part.hidden=part.dataset.calendarMode!==mode.value);
            }
        }
    }
    function options(){
        if(!choices)throw new Error('Review the saved calendar dates before downloading.');
        const events=[];
        panel().querySelectorAll('[data-calendar-event]').forEach(row=>{
            const field=name=>row.querySelector(`[data-calendar-field="${name}"]`).value;
            const mode=field('mode');if(mode==='date')return;
            const event={id:row.dataset.calendarEvent,confirmed:true};
            if(mode==='range')event.through=field('through');
            else{event.start=field('start');event.end=field('end');for(const name of ['start_fold','end_fold'])if(field(name)!=='')event[name]=Number(field(name));}
            events.push(event);
        });
        return {snapshot:choices.snapshot,zone:document.getElementById('calendarZone').value.trim(),events};
    }
    document.addEventListener('change',event=>{if(event.target.matches('[data-calendar-field="mode"]')){const row=event.target.closest('[data-calendar-event]');row.querySelectorAll('[data-calendar-mode]').forEach(part=>part.hidden=part.dataset.calendarMode!==event.target.value);}});
    return {clear,render,options,ready:()=>Boolean(choices?.activities.length),busy:value=>panel().querySelectorAll('input,select').forEach(input=>input.disabled=value)};
})();
