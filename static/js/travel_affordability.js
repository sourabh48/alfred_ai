/* Page-only private scenarios; canonical financial records are never modified. */
window.TravelAffordability=(()=>{
    const $=id=>document.getElementById(id),esc=value=>Alfred.escapeHtml(String(value??''));
    const fields={spendable_cash:'Gross spendable cash before protected allocations',emergency_reserve:'Protected emergency reserve',
        essential_expenses:'Canonical one-month living expenses, excluding loan obligations',loan_obligations:'Canonical one-month loan obligations',
        committed_savings:'Additional committed savings (owner assumption)',trip_budget:'Trip budget excluding extra contingency (owner assumption)',
        contingency:'Extra trip contingency (owner assumption)'};
    let current,request,key=null,data=null,pending=false,epoch=0,read=0;
    const panel=()=>$('plannerAffordability'),details=()=>$('plannerAffordabilityDetails');
    const form=()=>$('plannerAffordabilityForm');
    const endpoint=()=>`/api/mobility/planner/sessions/${current().id}/affordability/`;
    function invalidate(message='Scenario changed. Confirm the amounts and calculate again.'){
        $('plannerAffordabilityResult').replaceChildren();$('plannerAffordabilityStatus').textContent=message;
    }
    function clear(){epoch++;key=null;data=null;pending=false;panel().hidden=true;details().open=false;
        $('plannerAffordabilityBody').replaceChildren();invalidate('');}
    function draft(){
        if(!form())return {};
        const values={};
        for(const name of ['currency',...Object.keys(fields),'verified','complete','disjoint']){
            const input=form().elements.namedItem(name);
            values[name]=input.type==='checkbox'?(input.checked?'on':''):input.value;
        }
        return values;
    }
    function draw(saved={}){
        const source=data.source,trip=data.trip,estimate=trip.estimate;
        $('plannerAffordabilityBody').innerHTML=`<h2 class="h5 mt-3">${esc(trip.title)} · What-if</h2>
            <p>Choose and verify the common currency. No currency conversion is performed.</p>
            <p>Records checked ${esc(source.as_of_date)}. Cash observed ${esc(source.cash_observed_at?new Date(source.cash_observed_at).toLocaleString():'unknown')}; living spend through ${esc(source.spend_observed_through||'unknown')}.
            Evidence ${source.complete?'available for owner review':'incomplete'}.</p>
            <p>Observed cash cap: ${esc(source.amounts.cash_limit??'unknown')} · currency not recorded. Living costs and loan obligations are derived from canonical records.</p>
            <p>${estimate?`Saved planning estimate: ${esc(estimate.amount)} ${esc(estimate.currency)} (estimated, unverified; not copied or converted into your scenario).`:'Saved trip cost is unavailable or invalidated; enter an explicit estimate.'}</p>
            <p>Committed savings are your manual allocation for this scenario. No future income, investments or debt principal are added to cash.</p>
            ${source.issues.length?`<ul>${source.issues.map(issue=>`<li>${esc(issue.replaceAll('_',' '))}</li>`).join('')}</ul>`:''}
            <form id="plannerAffordabilityForm">
                <div class="travel-evidence-grid"><div><label for="affordCurrency">Verified common currency code</label><input id="affordCurrency" name="currency" class="form-control" maxlength="3" pattern="[A-Z]{3}" placeholder="Choose explicitly" required autocomplete="off"></div>
                ${Object.entries(fields).map(([name,label])=>`<div><label for="afford_${name}">${esc(label)}</label><input id="afford_${name}" name="${name}" class="form-control" inputmode="decimal" maxlength="40" required autocomplete="off" ${['essential_expenses','loan_obligations'].includes(name)?'readonly':''}></div>`).join('')}</div>
                <p class="small">Reserve, savings, living expenses and loan obligations must be separate allocations from gross cash. The trip budget excludes the extra contingency. Reducing canonical obligations is unsupported.</p>
                <label class="d-block"><input type="checkbox" name="verified"> I verified all seven amounts in the common currency above.</label>
                <label class="d-block"><input type="checkbox" name="complete"> These assumptions cover all relevant cash, one-month obligations and committed savings.</label>
                <label class="d-block"><input type="checkbox" name="disjoint"> Protected allocations do not overlap, and contingency is additional to the trip budget.</label>
                <button class="btn btn-primary mt-3" type="submit">Calculate What-if</button>
            </form>`;
        const defaults={spendable_cash:source.amounts.cash_limit,essential_expenses:source.amounts.essential_expenses,loan_obligations:source.amounts.loan_obligations};
        for(const name of ['currency',...Object.keys(fields)]){
            form().elements.namedItem(name).value=['essential_expenses','loan_obligations'].includes(name)?defaults[name]??'':saved[name]??defaults[name]??'';
        }
    }
    async function refresh(force=false){
        if(pending||panel().hidden||!details().open||!current()?.plan_id||document.hidden)return;
        const ticket=epoch,sequence=++read,identity=current().id,saved=draft();
        try{
            const next=await request(endpoint());
            if(ticket!==epoch||sequence!==read||pending||identity!==current()?.id||!details().open)return;
            const changed=!data||data.source.source_revision!==next.source.source_revision||data.trip.snapshot!==next.trip.snapshot;
            data=next;
            if(changed||force){draw(saved);invalidate('Evidence loaded or changed. Review and confirm all assumptions before calculating.');}
        }catch(error){if(ticket===epoch&&sequence===read){data=null;invalidate(error.message+' No financial record was changed. Reload evidence to retry.');}}
    }
    async function calculate(event){
        event.preventDefault();if(pending||!data)return;
        const values=draft(),confirmation={source_revision:data.source.source_revision,complete:values.complete==='on',disjoint_allocations:values.disjoint==='on'};
        for(const name of Object.keys(fields))confirmation[name]={amount:values[name],currency:values.currency,verified:values.verified==='on'};
        const ticket=epoch;pending=true;invalidate('Checking current evidence…');
        form().querySelectorAll('input,button').forEach(control=>control.disabled=true);
        try{
            const result=await request(endpoint(),{method:'POST',body:JSON.stringify({revision:data.trip.revision,snapshot:data.trip.snapshot,confirmation})});
            if(ticket!==epoch)return;
            $('plannerAffordabilityResult').innerHTML=`<h3 class="h5">${esc(result.label)} · scenario only</h3><p>${esc(result.interpretation)}</p>
                ${result.amounts?`<dl>${[['spendable_cash','Confirmed cash'],['protected_funds','Protected funds'],['available_trip_funds','Available trip funds'],['total_trip_budget','Trip plus extra contingency'],['headroom','Headroom'],['shortfall','Shortfall']].map(([name,label])=>`<dt>${label}</dt><dd>${esc(result.amounts[name])} ${esc(result.currency)}</dd>`).join('')}</dl>`:`<ul>${result.issues.map(issue=>`<li>${esc(issue.replaceAll('_',' '))}</li>`).join('')}</ul>`}`;
            $('plannerAffordabilityStatus').textContent='Current evidence checked. No financial record was changed.';
        }catch(error){if(ticket===epoch){invalidate(error.message);if(error.status===409){form()?.querySelectorAll('input,button').forEach(control=>control.disabled=false);pending=false;await refresh(true);}}}
        finally{if(ticket===epoch){pending=false;form()?.querySelectorAll('input,button').forEach(control=>control.disabled=false);}}
    }
    function sync(session){
        panel().hidden=!session.plan_id;if(!session.plan_id){clear();return;}
        const identity=`${session.id}:${session.plan_id}`;
        if(key?.identity!==identity||key.revision!==session.revision){
            if(key?.identity!==identity)$('plannerAffordabilityBody').replaceChildren();
            epoch++;key={identity,revision:session.revision};data=null;pending=false;
            invalidate('Saved trip changed. Reload evidence before calculating.');if(details().open)refresh(true);
        }
    }
    function init(options){
        ({current,request}=options);
        details().addEventListener('toggle',()=>{if(details().open)refresh(true);else{epoch++;data=null;pending=false;$('plannerAffordabilityBody').replaceChildren();invalidate('');}});
        $('plannerAffordabilityReload').addEventListener('click',()=>refresh(true));
        panel().addEventListener('submit',calculate);
        panel().addEventListener('input',event=>{if(event.target.closest('form')){invalidate();if(event.target.name!=='verified'&&event.target.type!=='checkbox')form().elements.namedItem('verified').checked=false;}});
        Alfred.enableLiveRefresh('travel-affordability',()=>refresh(),{rootId:'plannerAffordability',intervalMs:30000});
        addEventListener('focus',()=>{if(!panel().hidden&&details().open)refresh();});
    }
    return {init,sync,clear};
})();
