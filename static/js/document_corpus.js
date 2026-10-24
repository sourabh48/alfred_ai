function initDocumentCorpus(getSelected) {
    const base='/api/ai/document-corpus/';
    const ingest=document.getElementById('documentCorpusStore'), consent=document.getElementById('documentCorpusConsent');
    const days=document.getElementById('documentCorpusDays'), refresh=document.getElementById('documentCorpusRefresh');
    const form=document.getElementById('documentCorpusSearch'), query=document.getElementById('documentCorpusQuery');
    const listing=document.getElementById('documentCorpusList'), results=document.getElementById('documentCorpusResults');
    const status=document.getElementById('documentCorpusStatus'), limits=document.getElementById('documentCorpusLimits');
    let active=true, busy=false, generation=0, controller=null, expiryTimer=null;
    function clearResults() { clearTimeout(expiryTimer); expiryTimer=null; results.replaceChildren(); }
    function node(tag, text, className='') {
        const element=document.createElement(tag); element.textContent=text; element.className=className; return element;
    }
    function controls() {
        [ingest,consent,days,refresh,query,...form.querySelectorAll('button'),...listing.querySelectorAll('input,button')]
            .forEach(control => { control.disabled=!active || busy; });
        ingest.disabled=!active || busy || !getSelected() || !consent.checked;
        listing.setAttribute('aria-busy',String(busy)); results.setAttribute('aria-busy',String(busy));
        results.dataset.liveRefreshBusy=String(busy);
    }
    function original(parent, source) {
        if (!source.source_url) return;
        const url=new URL(source.source_url,location.origin);
        if (url.origin!==location.origin || !url.pathname.startsWith('/media/')) return;
        const link=node('a','Review original file'); link.href=url.pathname; parent.append(link);
    }
    function renderList(data) {
        const selected=new Set([...listing.querySelectorAll('input:checked')].map(input=>input.value));
        listing.replaceChildren(); days.max=String(data.maximum_retention_days);
        days.value=String(Math.min(Number(days.value),data.maximum_retention_days));
        limits.textContent=`Up to ${data.maximum_documents} copies, ${data.maximum_selected} selected per search, `+
            `${data.maximum_text_bytes/1024} KiB of text and ${data.maximum_index_tokens} indexed words per document, `+
            `${data.maximum_linked_records} linked records per source, ${data.maximum_owner_bytes/1048576} MiB encrypted storage per owner. `+
            `Retention is at most ${data.maximum_retention_days} days and follows any shorter Memory retention policy. `+
            'Remove retained copies before rolling back to an older app version. Protected backups have their own retention.';
        data.documents.forEach(source => {
            const card=node('article','','surface-card');
            const label=node('label','','form-check-label'), check=document.createElement('input');
            check.type='checkbox'; check.value=source.id; check.className='form-check-input me-2'; check.checked=selected.has(source.id);
            check.addEventListener('change',()=>{
                if (listing.querySelectorAll('input:checked').length>data.maximum_selected) {
                    check.checked=false; status.textContent='Select at most three private documents.';
                }
                clearResults();
            });
            label.append(check,document.createTextNode(source.document_name)); card.append(label);
            card.append(node('p',`${source.kind} · retained ${source.created_at} · expires ${source.expires_at}`,'small text-break'));
            original(card,source);
            const remove=node('button','Remove private copy','btn btn-outline-danger ms-2'); remove.type='button';
            remove.setAttribute('aria-label',`Remove private copy of ${source.document_name}`);
            remove.addEventListener('click',()=>perform(async signal=>{
                await Alfred.fetchJSON(base+source.id+'/',{method:'DELETE',signal});
                return {listing:await Alfred.fetchJSON(base,{signal}), message:'Private copy removed. The original and financial records are unchanged.'};
            }));
            card.append(remove); listing.append(card);
        });
        if (!data.documents.length) listing.append(node('p','No current private document copies. Select an original above to store one.'));
    }
    function renderResults(data) {
        data.results.forEach(hit=>{
            const card=node('article','','surface-card'); card.append(node('h3',hit.document_name,'h6'));
            const quote=node('p',hit.excerpt); quote.style.whiteSpace='pre-wrap'; card.append(quote);
            card.append(node('p',`Extracted characters ${hit.start}–${hit.end} (end excluded). Original SHA-256: ${hit.source_fingerprint}`,'small text-break'));
            card.append(node('p',`${hit.text_origin.replaceAll('_',' ')} · source checked ${data.checked_at} · copy expires ${hit.expires_at}`,'small text-break'));
            original(card,hit); results.append(card);
        });
        results.append(node('p',data.limitation,'small'));
        if (data.results.length) {
            const remaining=Math.min(...data.results.map(hit=>Date.parse(hit.expires_at)))-Date.now();
            expiryTimer=setTimeout(()=>{clearResults();status.textContent='Displayed copies expired. Refresh private knowledge before searching again.';},Math.max(0,Math.min(remaining,2147483647)));
        }
    }
    async function perform(job) {
        if (!active || busy) return;
        const ticket=++generation, request=new AbortController(); controller=request; busy=true;
        clearResults(); status.textContent='Checking private document knowledge…'; controls();
        const timer=setTimeout(()=>request.abort(),30000);
        try {
            const data=await job(request.signal);
            if (!active || ticket!==generation) return;
            if (data.listing) renderList(data.listing);
            if (data.results) renderResults(data);
            status.textContent=data.message || (data.results.length ? `${data.results.length} unverified excerpt(s).`+
                (data.more_matches ? ' More matches exist; narrow the keywords.' : '') : 'No matching excerpt. This does not prove absence from the original.');
        } catch(error) {
            if (ticket!==generation) return;
            clearResults();
            status.textContent=error.status===409 ? 'Private sources changed, expired or were cleared. Refresh and re-ingest the selected original.' :
                error.status===400 ? 'Check explicit consent, retention, keywords, selected documents and storage limits. Your query is preserved.' :
                'Encrypted document knowledge is unavailable. Existing vault data is preserved. Refresh and check your session before retrying.';
            if ([401,403].includes(error.status)) window.dispatchEvent(new Event('pagehide'));
        } finally {
            clearTimeout(timer);
            if (ticket===generation) { controller=null; busy=false; controls(); }
        }
    }
    refresh.addEventListener('click',()=>perform(async signal=>({listing:await Alfred.fetchJSON(base,{signal}),message:'Private knowledge list refreshed; sources and expiry checked.'})));
    consent.addEventListener('change',controls);
    ingest.addEventListener('click',()=>{
        const selected=getSelected();
        if (!selected || !consent.checked || !days.reportValidity()) return;
        const payload={kind:selected.kind,document_id:selected.document_id,catalog_token:selected.catalog_token,consent:true,days:Number(days.value)};
        perform(async signal=>{
            const saved=await Alfred.fetchJSON(base,{method:'POST',body:JSON.stringify(payload),signal});
            if (!saved.stored) return {message:'No copy stored: the original text is unavailable, unsupported or exceeds extraction limits.'};
            return {listing:await Alfred.fetchJSON(base,{signal}),message:'Encrypted copy stored. Explicitly select it below to search. It remains unverified extraction.'};
        });
    });
    form.addEventListener('submit',event=>{
        event.preventDefault();
        const ids=[...listing.querySelectorAll('input:checked')].map(input=>input.value);
        if (!ids.length) { status.textContent='Select one to three private documents before searching.'; return; }
        perform(signal=>Alfred.fetchJSON(base+'search/',{method:'POST',body:JSON.stringify({ids,query:query.value}),signal}));
    });
    function selectionChanged() {
        generation++; controller?.abort(); controller=null; busy=false; consent.checked=false;
        clearResults(); status.textContent='';
        listing.querySelectorAll('input:checked').forEach(input=>{input.checked=false;}); controls();
    }
    window.addEventListener('pagehide',()=>{
        active=false; selectionChanged(); listing.replaceChildren(); query.value=''; limits.textContent='';
    });
    window.addEventListener('pageshow',event=>{if(event.persisted){active=true;controls();}});
    document.addEventListener('visibilitychange',()=>{if(document.hidden) selectionChanged();});
    controls();
    return {selectionChanged};
}
