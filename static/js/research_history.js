/* Successful symbol searches are retained locally; personal theses remain optional. */
window.ResearchSearches = (() => {
    const $ = id=>document.getElementById(id), esc=v=>Alfred.escapeHtml(String(v ?? ''));
    let epoch=0;
    async function refresh() {
        const ticket=++epoch;
        try {
            const data=await Alfred.fetchJSON('/api/investments/research/searches/');
            if(ticket!==epoch || document.hidden)return;
            Alfred.setHTMLIfChanged('researchSearches', data.searches.map(r=>`<article class="mini-card"><button type="button" class="btn btn-sm btn-outline-primary" data-research-symbol="${esc(r.symbol)}">${esc(r.symbol)} · refresh research</button><p class="small mt-2 mb-1">${esc(r.summary.headline)}</p><p class="small mb-0">${r.checked_at ? `Checked ${esc(new Date(r.checked_at).toLocaleString())}` : 'Not checked'} · market data ${esc(r.summary.freshness?.price_as_of || 'unavailable')}. ${esc(r.error || r.summary.freshness?.note)}</p></article>`).join('') || '<p class="small">Search a stock or market symbol to start. No journal entry is required.</p>');
            $('researchSearchClear').disabled=!data.searches.length;
        } catch(error) {if(ticket===epoch)$('researchSearches').textContent=error.message;}
    }
    document.addEventListener('DOMContentLoaded',()=>{
        if(!$('researchSearches'))return;
        refresh();
        $('researchSearches').addEventListener('click',event=>{
            const button=event.target.closest('[data-research-symbol]');
            if(!button)return;
            $('researchPacketSymbol').value=button.dataset.researchSymbol;
            $('researchPacketHolding').value='';
            $('researchPacketForm').requestSubmit();
        });
        $('researchSearchClear').addEventListener('click',async()=>{
            try {await Alfred.fetchJSON('/api/investments/research/searches/',{method:'DELETE'});await refresh();}
            catch(error){$('researchSearches').textContent=error.message;}
        });
        window.addEventListener('pagehide',()=>{epoch++;$('researchSearches').replaceChildren();});
        window.addEventListener('pageshow',event=>{if(event.persisted)refresh();});
    });
    return {refresh};
})();
