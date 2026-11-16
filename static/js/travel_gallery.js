/* Keep photo bytes only in the current view; never in saved trips or browser storage. */
window.TravelGallery = (() => {
    const $ = id => document.getElementById(id);
    const esc = value => Alfred.escapeHtml(String(value ?? ""));
    let sessionId, key, index=0, count=0, controller, generation=0, busy=false;
    function controls() {
        $("plannerGalleryFrame").setAttribute("aria-busy",String(busy));
        $('plannerGalleryPrevious').disabled=busy || index<=0;
        $('plannerGalleryNext').disabled=busy || index+1>=count;
        $('plannerGalleryCount').textContent=count ? `${index+1} / ${count}` : '';
    }
    function clear() {
        generation++; controller?.abort(); controller=null; sessionId=null; key=null; count=0; busy=false;
        $('plannerGallery').hidden=true;
        $('plannerGalleryImage').removeAttribute('src');
        $('plannerGalleryImage').hidden=true;
        $('plannerGalleryCaption').replaceChildren();
    }
    async function load(nextIndex=0) {
        controller?.abort(); controller=new AbortController();
        const epoch=++generation;
        busy=true; index=nextIndex; controls();
        const img=$('plannerGalleryImage');
        img.hidden=true; img.removeAttribute('src');
        $('plannerGalleryCaption').replaceChildren();
        $('plannerGalleryStatus').textContent='Finding photos for this place…';
        $('plannerGalleryRetry').hidden=true;
        try {
            const data=await Alfred.fetchJSON(`/api/mobility/planner/sessions/${sessionId}/photos/?place=${encodeURIComponent(key)}&index=${index}`, {signal:controller.signal});
            if(epoch!==generation || document.hidden)return;
            count=data.count || 0;
            if(data.status==='ready' && /^data:image\/(jpeg|png|webp|gif);base64,/.test(data.image || '')) {
                img.alt=`${data.place} — photo ${index+1}`;
                img.onload=()=>{if(epoch===generation){img.hidden=false;$('plannerGalleryStatus').textContent='';}};
                img.onerror=()=>{if(epoch===generation){img.hidden=true;$('plannerGalleryStatus').textContent='This photo could not be displayed.';$('plannerGalleryRetry').hidden=false;}};
                img.src=data.image;
                Alfred.setHTMLIfChanged('plannerGalleryCaption', `${esc(data.place)} · ${(data.authors || []).map(a=>window.TravelResearchPanels.link(a.url,a.name)).join(' · ') || 'Google Maps'}`);
            } else {
                $('plannerGalleryStatus').textContent=data.message || 'No photos are available for this place yet. Your itinerary is ready below.';
                $('plannerGalleryRetry').hidden=false;
            }
        } catch(error) {
            if(epoch!==generation || error.name==='AbortError')return;
            if([401,403].includes(error.status)){clear();return;}
            count=0; $('plannerGalleryStatus').textContent=error.message || 'Photos are unavailable. Try again later.';
            $('plannerGalleryRetry').hidden=false;
        } finally {if(epoch===generation){busy=false;controls();}}
    }
    function sync(session) {
        const places=(session.gallery_places || []).filter(p=>p.selected);
        if(document.hidden || !places.length){clear();return;}
        const switched=sessionId!==session.id;
        const next=places.find(p=>!switched && p.key===key) || places[0];
        const changed=switched || key!==next.key;
        sessionId=session.id; key=next.key;
        $('plannerGallery').hidden=false;
        Alfred.setHTMLIfChanged('plannerGalleryPlace', places.map(p=>`<option value="${esc(p.key)}">${esc(p.name)}</option>`).join(''));
        $('plannerGalleryPlace').value=key;
        if(changed){count=0;load();}
    }
    document.addEventListener('DOMContentLoaded',()=>{
        $('plannerGalleryPlace')?.addEventListener('change',e=>{key=e.target.value;count=0;load();});
        $('plannerGalleryPrevious')?.addEventListener('click',()=>load(index-1));
        $('plannerGalleryNext')?.addEventListener('click',()=>load(index+1));
        $('plannerGalleryRetry')?.addEventListener('click',()=>load(0));
        $('plannerGalleryFrame')?.addEventListener('keydown',e=>{
            if(e.key==='ArrowLeft' && !busy && index>0){e.preventDefault();load(index-1);}
            if(e.key==='ArrowRight' && !busy && index+1<count){e.preventDefault();load(index+1);}
        });
    });
    return {sync,clear};
})();
