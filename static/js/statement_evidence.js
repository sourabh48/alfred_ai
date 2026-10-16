document.addEventListener('DOMContentLoaded', () => {
    const root = document.getElementById('statementEvidence');
    if (!root) return;
    const form = document.getElementById('statementEvidenceForm');
    const check = document.getElementById('statementEvidenceConfirm');
    const feedback = document.getElementById('statementEvidenceFeedback');
    let active = true, pending = false;
    async function submit(method) {
        if (!active || pending) return;
        if (method === 'DELETE' && !confirm('Withdraw confirmation? The original evidence and financial record remain intact.')) return;
        pending = true;
        form.querySelectorAll('button').forEach(button => { button.disabled = true; });
        try {
            await Alfred.fetchJSON(`/api/ai/statement-evidence/${root.dataset.record}/`, {method,
                body:JSON.stringify({revision:JSON.parse(document.getElementById('statementEvidenceRevision').textContent), confirm:method === 'DELETE' || check.checked})});
            if (active) location.reload();
        } catch (error) {
            if (active) feedback.textContent = `${error.message} Your choice is preserved. Reload and review before retrying.`;
        }
    }
    form.addEventListener('submit', event => { event.preventDefault(); submit('POST'); });
    document.getElementById('statementEvidenceRevoke').addEventListener('click', () => submit('DELETE'));
    window.addEventListener('pagehide', () => { active = false; root.replaceChildren(); document.getElementById('statementEvidenceRevision').textContent = 'null'; });
    window.addEventListener('pageshow', event => { if (event.persisted) location.reload(); });
});
