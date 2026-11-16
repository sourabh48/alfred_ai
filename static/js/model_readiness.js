document.addEventListener('DOMContentLoaded',()=>{
    const $=id=>document.getElementById(id), panel=$('modelReadinessPanel');
    if(!panel)return;
    let pending=false, loaded=false, epoch=0, controller;
    function clear() {
        epoch++;controller?.abort();pending=false;loaded=false;
        $('modelReadinessItems').replaceChildren();$('modelReadinessScope').textContent='';
        $('modelReadinessStatus').textContent='Reopen to check current registry gates.';
    }
    async function refresh() {
        if(pending || document.hidden)return;
        const ticket=++epoch;pending=true;controller=new AbortController();
        $('modelReadinessRefresh').disabled=true;$('modelReadinessItems').replaceChildren();
        $('modelReadinessScope').textContent='';$('modelReadinessStatus').textContent='Checking local registry gates…';
        panel.setAttribute('aria-busy','true');
        try {
            const data=await Alfred.fetchJSON('/api/ai/runtime-status/?serving_readiness=1',{signal:controller.signal});
            if(ticket!==epoch)return;
            for(const item of data.models) {
                const row=document.createElement('li'),title=document.createElement('strong'),reason=document.createElement('p'),fallback=document.createElement('p');
                row.className='mb-3';title.textContent=`${item.name} · ${item.registry_eligible?'Registry eligible':item.status==='fallback'?'Fallback':'Unavailable'}`;
                reason.textContent=item.reason;fallback.textContent=`Fallback: ${item.fallback}`;
                row.append(title,reason,fallback);$('modelReadinessItems').append(row);
            }
            $('modelReadinessScope').textContent=data.scope;
            $('modelReadinessStatus').textContent=`Registry checked ${new Date(data.checked_at).toLocaleString()}. Recheck to see current gates.`;loaded=true;
        } catch(error) {
            if(ticket===epoch)$('modelReadinessStatus').textContent=`${error.message} Readiness is unknown; no model was activated.`;
        } finally {if(ticket===epoch){pending=false;$('modelReadinessRefresh').disabled=false;panel.setAttribute('aria-busy','false');}}
    }
    panel.addEventListener('toggle',()=>{if(panel.open && !loaded)refresh();});
    $('modelReadinessRefresh').addEventListener('click',refresh);
    window.addEventListener('pagehide',clear);
    document.addEventListener('visibilitychange',()=>{if(document.hidden)clear();else if(panel.open)refresh();});
    window.addEventListener('pageshow',()=>{if(panel.open && !loaded)refresh();});
});
