/* Page-only private scenarios; canonical financial records are never modified. */
window.TravelAffordability=(()=>{
    const $=id=>document.getElementById(id),esc=value=>Alfred.escapeHtml(String(value??''));
    const fields={spendable_cash:'Gross spendable cash before protected allocations',emergency_reserve:'Protected emergency reserve',
        essential_expenses:'Canonical one-month living expenses, excluding loan obligations',loan_obligations:'Canonical one-month loan obligations',
        committed_savings:'Additional committed savings (owner assumption)',trip_budget:'Trip budget excluding extra contingency (owner assumption)',
        contingency:'Extra trip contingency (owner assumption)'};
    const futureFields={departure:'Future trip departure (departure day excluded)',income_from:'Verified income effective from',
        income_until:'Verified income effective through',verified_on:'Income and schedules verified on (today)',
        monthly_income:'Verified canonical monthly income',monthly_goals:'Additional recurring monthly goals (not already reserved)',
        monthly_contribution:'Planned monthly contribution to this trip'};
    let current,request,key=null,data=null,pending=false,epoch=0,read=0;
    const panel=()=>$('plannerAffordability'),details=()=>$('plannerAffordabilityDetails');
    const form=()=>$('plannerAffordabilityForm');
    const endpoint=(future=false)=>`/api/mobility/planner/sessions/${current().id}/${future?'savings':'affordability'}/`;
    function invalidate(message='Scenario changed. Confirm the amounts and calculate again.'){
        $('plannerAffordabilityResult').replaceChildren();$('plannerAffordabilityStatus').textContent=message;
    }
    function clear(){epoch++;key=null;data=null;pending=false;panel().hidden=true;details().open=false;
        $('plannerAffordabilityBody').replaceChildren();invalidate('');}
    function draft(){
        if(!form())return {};
        const values={};
        for(const input of form().querySelectorAll('input[name]')){
            const name=input.name;
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
                <label class="d-block mt-3"><input type="checkbox" name="projection"> Include future-date savings scenarios</label>
                <div id="affordFuture" hidden>
                    <h3 class="h5 mt-3">Future savings · estimates only</h3>
                    <p>Future salary is uncertain. This daily accrual model excludes today and departure day; it does not predict paydays or guarantee interim liquidity. Current cash and projected funds remain separate.</p>
                    <p>Canonical income: ${esc(data.savings_source.monthly_income??'unknown')} · ${esc(data.savings_source.income_state.status||'unavailable')} / ${esc(data.savings_source.income_state.source||'unknown')}. Latest income transaction: ${esc(data.savings_source.income_observed_through||'unknown; owner effective-period verification required')}.</p>
                    <div class="travel-evidence-grid">${Object.entries(futureFields).map(([name,label])=>`<div><label for="future_${name}">${esc(label)}</label><input id="future_${name}" name="${name}" class="form-control" ${['departure','income_from','income_until','verified_on'].includes(name)?'type="date"':'inputmode="decimal" maxlength="40"'} ${name==='monthly_income'?'readonly':''} autocomplete="off"></div>`).join('')}</div>
                    <p>Each loan needs its next unpaid monthly due date. Leave final due blank to continue charging the EMI throughout the horizon. Final due means the last verified payment date, not an inferred tenure.</p>
                    ${data.savings_source.loans.map(loan=>`<fieldset class="mt-2"><legend class="h6">Owned loan ${esc(loan.id)} · EMI ${esc(loan.emi)} · starts ${esc(loan.start)}</legend><div class="travel-evidence-grid"><div><label for="due_${loan.id}">Next unpaid due</label><input id="due_${loan.id}" name="due_${loan.id}" type="date" class="form-control"></div><div><label for="final_${loan.id}">Verified final due (optional)</label><input id="final_${loan.id}" name="final_${loan.id}" type="date" class="form-control" data-optional></div></div></fieldset>`).join('')}
                    <p>Explicit what-if assumptions: retained income 0–100%; living expenses 100–200%. No growth, investments or FX. Each monthly contribution is capped by net cash flow; negative flow reduces trip funds. Existing reserve and goals are protected once; monthly goals are additional and disjoint.</p>
                    ${['conservative','baseline','optimistic'].map(name=>`<fieldset class="mt-2"><legend class="h6">${esc(name)} assumptions</legend><div class="travel-evidence-grid"><div><label for="${name}_income">Income retained (%)</label><input id="${name}_income" name="${name}_income" inputmode="decimal" maxlength="8" class="form-control"></div><div><label for="${name}_expense">Living expenses (%)</label><input id="${name}_expense" name="${name}_expense" inputmode="decimal" maxlength="8" class="form-control"></div></div></fieldset>`).join('')}
                    <label class="d-block mt-3"><input type="checkbox" name="future_confirmed"> I verified this income, currency, effective period and unpaid EMI schedule today. Recurring expenses/goals are not already paid or reserved; the contribution is an allocation, not extra income. These assumptions are complete and disjoint. Future income remains uncertain.</label>
                </div>
                <button class="btn btn-primary mt-3" type="submit">Calculate What-if</button>
            </form>`;
        const defaults={spendable_cash:source.amounts.cash_limit,essential_expenses:source.amounts.essential_expenses,loan_obligations:source.amounts.loan_obligations};
        for(const name of ['currency',...Object.keys(fields)]){
            form().elements.namedItem(name).value=['essential_expenses','loan_obligations'].includes(name)?defaults[name]??'':saved[name]??defaults[name]??'';
        }
        const futureDefaults={monthly_income:data.savings_source.monthly_income,conservative_income:'75',baseline_income:'90',optimistic_income:'100',conservative_expense:'110',baseline_expense:'100',optimistic_expense:'100'};
        for(const input of $('affordFuture').querySelectorAll('input:not([type="checkbox"])'))input.value=input.name==='monthly_income'?futureDefaults.monthly_income??'':saved[input.name]??futureDefaults[input.name]??'';
        form().elements.namedItem('projection').checked=saved.projection==='on';toggleFuture();
    }
    function toggleFuture(){const enabled=form().elements.namedItem('projection').checked;$('affordFuture').hidden=!enabled;
        $('affordFuture').querySelectorAll('input').forEach(input=>{input.disabled=!enabled;input.required=enabled&&!input.hasAttribute('data-optional');});}
    async function refresh(force=false){
        if(pending||panel().hidden||!details().open||!current()?.plan_id||document.hidden)return;
        const ticket=epoch,sequence=++read,identity=current().id;
        try{
            const next=await request(endpoint(true));
            if(ticket!==epoch||sequence!==read||pending||identity!==current()?.id||!details().open)return;
            const changed=!data||data.source.source_revision!==next.source.source_revision||data.trip.snapshot!==next.trip.snapshot||data.savings_source.revision!==next.savings_source.revision;
            data=next;
            if(changed||force){const saved=draft();draw(saved);invalidate('Evidence loaded or changed. Review and confirm all assumptions before calculating.');}
        }catch(error){if(ticket===epoch&&sequence===read){data=null;invalidate(error.message+' No financial record was changed. Reload evidence to retry.');}}
    }
    async function calculate(event){
        event.preventDefault();if(pending||!data)return;
        const values=draft(),confirmation={source_revision:data.source.source_revision,complete:values.complete==='on',disjoint_allocations:values.disjoint==='on'};
        for(const name of Object.keys(fields))confirmation[name]={amount:values[name],currency:values.currency,verified:values.verified==='on'};
        const future=values.projection==='on',payload={revision:data.trip.revision,snapshot:data.trip.snapshot,confirmation};
        if(future){const verified=values.future_confirmed==='on',money=name=>({amount:values[name],currency:values.currency,verified});
            payload.savings={source_revision:data.savings_source.revision,departure:values.departure,income_from:values.income_from,income_until:values.income_until,verified_on:values.verified_on,
                monthly_income:money('monthly_income'),monthly_goals:money('monthly_goals'),monthly_contribution:money('monthly_contribution'),confirmed:verified,
                schedules:data.savings_source.loans.map(loan=>({id:loan.id,next_due:values[`due_${loan.id}`],final_due:values[`final_${loan.id}`],verified})),
                scenarios:Object.fromEntries(['conservative','baseline','optimistic'].map(name=>[name,{income_percent:values[`${name}_income`],expense_percent:values[`${name}_expense`]}]))};}
        const ticket=epoch;pending=true;invalidate('Checking current evidence…');
        form().querySelectorAll('input,button').forEach(control=>control.disabled=true);
        try{
            const result=await request(endpoint(future),{method:'POST',body:JSON.stringify(payload)});
            if(ticket!==epoch)return;
            $('plannerAffordabilityResult').innerHTML=future?futureResult(result):`<h3 class="h5">${esc(result.label)} · scenario only</h3><p>${esc(result.interpretation)}</p>
                ${result.amounts?`<dl>${[['spendable_cash','Confirmed cash'],['protected_funds','Protected funds'],['available_trip_funds','Available trip funds'],['total_trip_budget','Trip plus extra contingency'],['headroom','Headroom'],['shortfall','Shortfall']].map(([name,label])=>`<dt>${label}</dt><dd>${esc(result.amounts[name])} ${esc(result.currency)}</dd>`).join('')}</dl>`:`<ul>${result.issues.map(issue=>`<li>${esc(issue.replaceAll('_',' '))}</li>`).join('')}</ul>`}`;
            $('plannerAffordabilityStatus').textContent='Current evidence checked. No financial record was changed.';
        }catch(error){if(ticket===epoch){invalidate(error.message);if(error.status===409){form()?.querySelectorAll('input,button').forEach(control=>control.disabled=false);pending=false;await refresh(true);}}}
        finally{if(ticket===epoch){pending=false;form()?.querySelectorAll('input,button').forEach(control=>control.disabled=false);if(form())toggleFuture();}}
    }
    function futureResult(result){
        if(!result.scenarios)return `<h3 class="h5">Insufficient Data · projection unavailable</h3><ul>${result.issues.map(issue=>`<li>${esc(issue.replaceAll('_',' '))}</li>`).join('')}</ul>`;
        return `<h3 class="h5">Future savings · projected estimates only</h3><p>Available today after one month of protected obligations: ${esc(result.current.amounts.available_trip_funds)} ${esc(result.currency)}. Starting unallocated cash before future expenses: ${esc(result.starting_unallocated_cash)}. Departure: ${esc(result.departure)}.</p><ul>${result.limitations.map(item=>`<li>${esc(item)}</li>`).join('')}</ul>`+
            Object.entries(result.scenarios).map(([name,scenario])=>`<h4 class="h6">${esc(name)} · ${esc(scenario.status.replaceAll('_',' '))}</h4><p>Projected trip funds ${esc(scenario.projected_trip_funds)} ${esc(result.currency)}; headroom ${esc(scenario.headroom)}; shortfall ${esc(scenario.shortfall)}; protected funding deficit ${esc(scenario.protected_funding_deficit)}. Required monthly saving lower bound: ${esc(scenario.required_monthly_saving??'no accrual period')}.</p><div class="table-responsive" role="region" tabindex="0" aria-label="${esc(name)} monthly projection"><table class="table table-sm"><caption>${esc(name)} monthly projection · ${esc(result.currency)} · end dates exclusive</caption><thead><tr>${['Period','Income','Living expenses','Goals','EMIs','Net flow','Trip allocation','Projected funds'].map(label=>`<th scope="col">${label}</th>`).join('')}</tr></thead><tbody>${scenario.months.map(row=>`<tr><th scope="row">${esc(row.start)}–${esc(row.end_exclusive)}</th>${['income','essentials','goals','emi','net_cashflow','trip_allocation','projected_funds'].map(key=>`<td>${esc(row[key])}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`).join('');
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
        panel().addEventListener('input',event=>{if(event.target.closest('form')){invalidate();if(event.target.name==='projection')toggleFuture();if(event.target.type!=='checkbox'){form().elements.namedItem('verified').checked=false;form().elements.namedItem('future_confirmed').checked=false;}}});
        Alfred.enableLiveRefresh('travel-affordability',()=>refresh(),{rootId:'plannerAffordability',intervalMs:30000});
        addEventListener('focus',()=>{if(!panel().hidden&&details().open)refresh();});
    }
    return {init,sync,clear};
})();
