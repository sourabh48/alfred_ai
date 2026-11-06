"""Deterministic documentation views of the canonical capability inventory; no network."""
import argparse
from collections import Counter
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
STATES = ('IMPLEMENTED_NOT_ACCEPTED', 'PARTIALLY_IMPLEMENTED', 'BLOCKED_APPROVAL',
          'BLOCKED_EXTERNAL', 'NOT_IMPLEMENTED', 'COMPLETE_VERIFIED')
PHASE = {STATES[0]: 'A', STATES[1]: 'B', STATES[2]: 'C', STATES[3]: 'C', STATES[4]: 'D', STATES[5]: 'DONE'}
# Owner decision 2026-11-05: AI Council work goes after every other module, whatever its phase.
OWNER_DEFERRED_MODULES = ('COUNCIL',)
MODULE_ORDER = ('FIN', 'LOAN', 'INV', 'DOC', 'AI', 'CAREER', 'TRAVEL', 'FAMILY', 'BIKE', 'COUNCIL', 'OPENAI', 'SYNC', 'RUNTIME')
GATES = {
    'LOAN-08': 'BLOCKED_EVIDENCE: independent lender/document acceptance corpus',
    'INV-02': 'BLOCKED_EVIDENCE: broader broker/layout/OCR and authorized real-account corpus; bounded receipts in EXECUTION_STATE',
    'INV-05': 'BLOCKED_EVIDENCE: bounded AMFI/Yahoo receipts in EXECUTION_STATE; remaining live terms/quota, authorized provider and real-account evidence absent; full capability unaccepted',
    'AI-10': 'BLOCKED_APPROVAL: private-history activation remains off',
    'AI-14': 'BLOCKED_EVIDENCE: eligible consented training and reviewed outcomes',
    'AI-15': 'BLOCKED_EVIDENCE: genuine per-model held-out outcomes',
    'RUNTIME-03': 'BLOCKED_EVIDENCE: sustained sign-in/scheduler observation',
    'RUNTIME-05': 'BLOCKED_EXTERNAL: independent Windows PC acceptance',
    'RUNTIME-06': 'BLOCKED_EXTERNAL: offline independent-host kit on a separate PC; same-host packaged checks 35/35',
    'RUNTIME-11':'BLOCKED_EXTERNAL: separate-user and clean-PC installs; owner accepted the diskcache residual risk 2026-11-05',
    'RUNTIME-14': 'BLOCKED_EXTERNAL: same-host synthetic M21 rehearsal PASS at 10203a3 on G:; separate PC, normal account and device-loss acceptance open',
    'RUNTIME-15': 'BLOCKED_EXTERNAL: same-host Compose run PASS at 49d622e; second LAN device, host restart and sustained schedule open',
    'FIN-07': 'BLOCKED_EVIDENCE: on the owner\'s data the prior range held in 6 of 9 walk-forward months and income evidence is missing; no accuracy claim',
    'FIN-13': 'BLOCKED_EVIDENCE: owner account check PASS 2026-11-06; CI PASS at e8ef8f4 (run 42185812614); a fresh-package check remains',
    'DOC-07': 'BLOCKED_EVIDENCE: bounded whole-extraction Q&A accepted; 111 document tests re-run PASS 2026-11-06; OCR, longer originals and an independent quality corpus remain',
    'DOC-09': 'BLOCKED_EVIDENCE: delete now removes orphaned stored files 2026-11-06 (118 tests PASS); owner check with a synthetic document remains',
    'CAREER-04': 'BLOCKED_APPROVAL: manual recruiter intake accepted; automatic mailbox access needs approved provider access and a reviewed integration',
    'CAREER-07': 'BLOCKED_EVIDENCE: interview preparation panel from the saved job match 2026-11-06 (73 backend + Chrome PASS); owner check remains',
    'TRAVEL-04': 'BLOCKED_APPROVAL: verified inter-stop routing needs an approved routing key (TRAVEL_ORS_API_KEY not configured); manual itineraries accepted',
    'TRAVEL-07': 'BLOCKED_EVIDENCE: bounded alternative-route choice accepted; independently reviewed scenic/legal route evidence absent',
    'TRAVEL-08': 'BLOCKED_EVIDENCE: owner-reviewed restriction references accepted; independently authenticated route-applicable restrictions absent',
    'TRAVEL-09': 'BLOCKED_APPROVAL: straight-line stop distance labelled 2026-11-06; road-network detours need an approved routing key',
    'TRAVEL-15': 'BLOCKED_EXTERNAL: no verified live permit or closure service; dated references shown stale with UNKNOWN confidence',
    'BIKE-03': 'BLOCKED_EVIDENCE: part windows and evidence score labelled 2026-11-06; prediction quality needs real logged service outcomes',
    'BIKE-05': 'BLOCKED_EXTERNAL: cost figures labelled estimates 2026-11-06; authoritative part compatibility and live prices need a manufacturer or dealer source',
    'OPENAI-02': 'BLOCKED_APPROVAL: OpenAI stays off; pinned model retires 2027-01-14; replacement choice waits for approval to enable',
    'RUNTIME-12': 'BLOCKED_EXTERNAL: CI runs on each master push and is read via the public API; branch protection needs signed-in GitHub access',
    'FIN-15': 'BLOCKED_EVIDENCE: investments currency slice 2026-11-06 (FX off); owner approved and applied migration investments 0006 (backup F:/ALFRED_BACKUPS/pre-fin15-migration-20261106); owner check, then banking, loans, income, budgets and travel remain',
    'FIN-06': 'BLOCKED_EVIDENCE: INR savings goals with Decimal progress implemented 2026-11-06; owner approved migration budgets 0003; owner check in the app remains',
    'COUNCIL-01': 'BLOCKED_APPROVAL: owner agreed to local auto-training 2026-11-06; it takes effect when the owner presses Approve Auto-Training in their app, then held-out outcomes follow',
    'TRAVEL-20': 'BLOCKED_EVIDENCE: private trip videos implemented 2026-11-06; owner approved and applied migration mobility 0014; owner check in the app remains',
    'AI-18': 'BLOCKED_EVIDENCE: offline Speak (Whisper base) and Read aloud (Piper VCTK) implemented 2026-11-06 with owner-approved downloads; owner check remains',
    'AI-17': 'BLOCKED_EVIDENCE: propose-then-confirm savings-goal actions implemented 2026-11-06 (owner decision); owner check remains',
    'SYNC-02': 'BLOCKED_EXTERNAL: Cloudflare R2 encrypted adapter built 2026-11-06, tested against a synthetic signed server only; owner creates a free R2 bucket and bucket-scoped token in config/local.env, then a live sync check',
    'TRAVEL-14': 'BLOCKED_APPROVAL: owner left the choice to Claude 2026-11-06; kept deferred because no free official bus inventory source exists and live booking stays off; links to verified bus websites remain',
    'INV-04': 'BLOCKED_EVIDENCE: assumed-age advice removed and guidance labelled 2026-11-06; reviewed risk-evidence definition and owner check remain',
    'FIN-17': 'BLOCKED_EXTERNAL: owner dropped the score page 2026-11-06; report uploads stay in Documents; live bureau pulls need a bureau contract',
    'FIN-16': 'BLOCKED_EVIDENCE: tax year 2026-27 rules and the notice-only Budget check implemented; page check on the owner app PASS 2026-11-06; CI PASS at e8ef8f4; reviewed actual tax cases (income unverified) remain',
    'TRAVEL-18': 'BLOCKED_APPROVAL: Google configuration/credentials and offline map scope',
}


def inventory(text, expected=143):
    pattern = r'^### ([A-Z]+-\d+) — ([^\n]+)\n\n\*\*([A-Z_]+)\*\*([^\n]*)\n(.*?)(?=^### |\Z)'
    rows = []
    for match in re.finditer(pattern, text.replace('\r\n', '\n'), re.M | re.S):
        identity, title, status, header, body = match.groups()
        if status not in STATES:
            raise ValueError('Unknown capability status: ' + identity)
        priority = re.search(r'\bP([0-3])\b', header)
        rows.append(dict(id=identity, title=title, status=status, prefix=identity.split('-')[0],
                         priority=int(priority[1]) if priority else 2, body=body))
    if len(rows) != expected or len({r['id'] for r in rows}) != expected:
        raise ValueError('Inventory must contain exactly distinct ' + str(expected) + ' original IDs.')
    return rows


def dependencies(requirements):
    section = requirements.split('## Dependency matrix\n', 1)[1].split('\n## ', 1)[0]
    return {match[1]: re.findall(r'\b[A-Z]+-\d+\b', match[2]) for match in
            re.finditer(r'^\| ([A-Z]+-\d+) \| ([^|]+) \|', section, re.M)}


def ordered(rows):
    def key(row):
        module = MODULE_ORDER.index(row['prefix']) if row['prefix'] in MODULE_ORDER else len(MODULE_ORDER)
        return (row['prefix'] in OWNER_DEFERRED_MODULES, PHASE[row['status']], module, row['priority'],
                int(row['id'].split('-')[1]))
    return sorted(rows, key=key)


def readiness(row, statuses, prerequisites):
    if row['status'] == 'COMPLETE_VERIFIED':
        return 'ACCEPTED_SCOPE_ONLY'
    if row['status'].startswith('BLOCKED_'):
        return row['status'] + ': see canonical decision'
    if row['id'] in GATES:
        return GATES[row['id']]
    missing = [identity for identity in prerequisites.get(row['id'], []) if statuses[identity] != 'COMPLETE_VERIFIED']
    if missing:
        return 'BLOCKED_DEPENDENCY: ' + ', '.join(missing)
    return 'READY_FOR_SCOPED_INSPECTION'


def replace_block(text, name, body):
    start, end = '<!-- BEGIN ' + name + ' -->', '<!-- END ' + name + ' -->'
    if text.count(start) != 1 or text.count(end) != 1 or text.index(start) > text.index(end):
        raise ValueError('Missing/duplicate generated block: ' + name)
    first, rest = text.split(start, 1)
    return first + start + '\n' + body.rstrip() + '\n' + end + rest.split(end, 1)[1]


def synchronize(root=ROOT, *, write=False, audit=None):
    tracker = root / 'docs/PROJECT_STATUS.md'
    text = tracker.read_text(encoding='utf-8')
    rows = inventory(text)
    if {r['prefix'] for r in rows} - set(MODULE_ORDER):
        raise ValueError('Unknown module; do not silently omit its dashboard totals.')
    statuses = {r['id']: r['status'] for r in rows}
    counts = Counter(statuses.values())
    requirements_path = root / 'docs/ALFRED_2_0_REQUIREMENTS.md'
    requirements = requirements_path.read_text(encoding='utf-8')
    original_ids = re.findall(r'^\| ([A-Z]+-\d+) \| [^|]+ \|$', requirements, re.M)
    if len(original_ids) != 143 or set(original_ids) != set(statuses):
        raise ValueError('Original baseline identities changed; explicit scope approval is required.')
    prerequisites = dependencies(requirements)
    if any(identity not in statuses for task, ids in prerequisites.items() for identity in [task, *ids]):
        raise ValueError('Unknown dependency ID; preserve the 143 baseline.')
    visited = set()
    def visit(identity, trail):
        if identity in trail:
            raise ValueError('Dependency cycle: ' + identity)
        if identity not in visited:
            for parent in prerequisites.get(identity, []):
                visit(parent, trail | {identity})
            visited.add(identity)
    for identity in prerequisites:
        visit(identity, set())
    extensions = re.findall(r'^\| ((?:CAREER2|TRAVEL2|INVEST2|WEALTH2)-\d+) \| (.*?) \| (.*?) \| (.*?) \|$', requirements, re.M)
    if not extensions or len({e[0] for e in extensions}) != len(extensions):
        raise ValueError('Extension identities must be explicit and unique.')
    if any(identity not in statuses for e in extensions for identity in re.findall(r'\b[A-Z]+-\d+\b', e[2])):
        raise ValueError('Unknown extension dependency.')
    extension_ids = {e[0] for e in extensions}
    ledger = re.findall(r'^\| ((?:CAREER2|TRAVEL2|INVEST2|WEALTH2)-\d+) \| ([A-Z_]+) \| (.*?) \|$', text, re.M)
    if not ledger and write:
        body = '| Extension | Status | Evidence |\n| --- | --- | --- |\n'
        body += '\n'.join('| ' + e[0] + ' | UNACCEPTED | No full-story acceptance recorded. |' for e in extensions)
        text = replace_block(text, 'EXTENSION ACCEPTANCE', body)
        ledger = [(e[0], 'UNACCEPTED', 'No full-story acceptance recorded.') for e in extensions]
    if len(ledger) != len(extensions) or {e[0] for e in ledger} != extension_ids:
        raise ValueError('Extension ledger must match the explicitly defined stories.')
    for identity, status, evidence in ledger:
        if status not in ('UNACCEPTED', 'PARTIAL', 'ACCEPTED', 'BLOCKED_APPROVAL', 'BLOCKED_EXTERNAL'):
            raise ValueError('Unknown extension status: ' + identity)
        if status == 'ACCEPTED' and not re.search(r'\[[^]]+\]\([^)]+\)', evidence):
            raise ValueError('Accepted extension requires linked source-bound evidence.')
    extension_status = {e[0]: e[1:] for e in ledger}
    accepted_extensions = sum(e[1] == 'ACCEPTED' for e in ledger)
    verified = counts['COMPLETE_VERIFIED']
    pr = re.search(r'^- \*\*PR/CI:\*\* (.+)$', text, re.M)
    if not pr:
        raise ValueError('Canonical PR/CI dashboard is missing.')
    summary = '**Baseline: ' + str(verified) + '/143 (' + format(verified / 143 * 100, '.1f') + '%) verified.**\n\n'
    summary += ' | '.join(state + ': ' + str(counts[state]) for state in STATES) + '\n\nPR/CI: ' + pr[1]
    summary += '\n\nExtensions: **' + str(accepted_extensions) + '/' + str(len(extensions)) + ' accepted**; separate source-bound story ledger.'
    modules = ['| Module | Verified | Total | Verified % | Unaccepted | Partial | Missing | Approval | External |',
               '| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |']
    for prefix in MODULE_ORDER:
        group = [r for r in rows if r['prefix'] == prefix]
        if not group:
            continue
        totals = Counter(r['status'] for r in group)
        modules.append('| ' + prefix + ' | ' + ' | '.join(str(v) for v in
            [totals[STATES[5]], len(group), format(totals[STATES[5]] / len(group) * 100, '.1f'),
             totals[STATES[0]], totals[STATES[1]], totals[STATES[4]], totals[STATES[2]], totals[STATES[3]]]) + ' |')
    queue = ['# ALFRED execution queue', '',
        'Generated from canonical status rows and the requirements dependency matrix. Regenerate with',
        '`python scripts/project_execution.py --write`; check without changes using `--check`.',
        'Use the configured SDK. No network, provider activation or feature execution occurs.', '',
        '**Selection:** `next` selects one task; explicit `sprint` continuously selects eligible scopes.',
        '`continue` resumes EXECUTION_STATE; `status` is read-only. Finish or explicitly defer',
        'local work first; CI_PENDING may coexist with independent IMPLEMENTING work.',
        'Phase A → B → C → D; module-by-module inside each phase. Skip an actually blocked',
        'item with its exact reason; do not call its acceptance complete. Later-phase',
        'prerequisite exceptions need a recorded reason. Accepted baseline rows are never requeued.',
        'Owner decision 2026-11-05: ' + ', '.join(OWNER_DEFERRED_MODULES) + ' tasks are queued after all other modules.', '',
        'Effort bands are preliminary scope estimates, not measured durations: S = bounded existing path;',
        'M = multi-path acceptance; L = broader integration, outcomes or external environment.',
        'Value P0/P1/P2/P3 is the recorded tracker priority, not an invented confidence score.',
        'B = backend/API; U = actual affected Chrome/accessibility; P = privacy/ownership/CSRF;',
        'MONEY = Decimal/reconciliation if monetary behavior changes. Add native/package/live',
        'gates where the canonical scope requires them. Full criteria/limitations/evidence remain',
        'in [PROJECT_STATUS](PROJECT_STATUS.md); product intent is in [requirements](ALFRED_2_0_REQUIREMENTS.md).', '',
        '| Order | Phase | Task / module | Status | Value / effort | Prerequisites | Required acceptance | Readiness / blocker |',
        '| ---: | --- | --- | --- | --- | --- | --- | --- |']
    next_task = None
    index = 0
    for row in ordered(rows):
        if row['status'] == STATES[5]:
            continue
        index += 1
        ready = readiness(row, statuses, prerequisites)
        if next_task is None and ready.startswith('READY_FOR_SCOPED_INSPECTION'):
            next_task = row['id']
        effort = 'L' if row['status'] != STATES[0] or ready.startswith('BLOCKED_') else 'M'
        queue.append('| ' + str(index) + ' | ' + PHASE[row['status']] + ' | ' + row['id'] + ' — ' + row['title'] + ' | ' + row['status'] +
                     ' | P' + str(row['priority']) + ' / ' + effort + ' | ' + (', '.join(prerequisites.get(row['id'], [])) or 'Scoped source/evidence inspection') +
                     ' | B/P; U if affected; MONEY if changed | ' + ready + ' |')
    queue += ['', '**Next eligible for `next` or active `sprint`: ' + str(next_task) + '.**', '',
              '## Accepted baseline — excluded from execution', '', '| ID | Capability | Status |', '| --- | --- | --- |']
    queue += ['| ' + r['id'] + ' | ' + r['title'] + ' | ' + r['status'] + ' |' for r in ordered(rows) if r['status'] == STATES[5]]
    queue += ['', '## Separate 2.0 extensions — after authorized baseline closure', '',
              'Inspect existing reuse/gaps before implementing each of the ' + str(len(extensions)) + ' defined stories.',
              'Dependencies refer to original IDs; shared look-through is counted once, not per consumer.', '',
              '| ID | Scope | Prerequisites | Acceptance | Status | Evidence |', '| --- | --- | --- | --- | --- | --- |']
    queue += ['| ' + ' | '.join([*e, *extension_status[e[0]]]) + ' |' for e in extensions]
    catalog = '| Original ID | Product intent |\n| --- | --- |\n' + '\n'.join('| ' + r['id'] + ' | ' + r['title'] + ' |' for r in rows)
    outputs = {
        tracker: replace_block(text, 'STATUS DASHBOARD', summary + '\n\n' + '\n'.join(modules)),
        root / 'README.md': replace_block((root / 'README.md').read_text(encoding='utf-8'), 'STATUS DASHBOARD', summary),
        requirements_path: replace_block(requirements, 'BASELINE INTENT INDEX', catalog),
        root / 'docs/EXECUTION_QUEUE.md': '\n'.join(queue) + '\n',
    }
    stale = [str(path.relative_to(root)) for path, data in outputs.items() if not path.exists() or path.read_text(encoding='utf-8') != data]
    if stale and not write:
        raise ValueError('Generated views are stale: ' + ', '.join(stale))
    if write:
        for path, data in outputs.items():
            if str(path.relative_to(root)) in stale:
                path.write_text(data, encoding='utf-8')
    if audit:
        receipts = []
        for row in rows:
            source = re.search(r'^- Source: (.+)$', row['body'], re.M)
            refs = re.findall(r'\]\(([^)]+)\)', source[1]) if source else []
            paths = [p for p in refs if not p.startswith(('http:', 'https:'))]
            receipts.append(dict(id=row['id'], status=row['status'],
                                 local_sources=[dict(path=p, exists=(tracker.parent / p.split('#')[0]).exists()) for p in paths],
                                 historical_or_external_references=len(refs)-len(paths)))
        audit.parent.mkdir(parents=True, exist_ok=True)
        audit.write_text(json.dumps(dict(scope='Top-level inventory/reference presence only; not code or acceptance re-audit',
            head=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip(),
            counts=dict(counts), rows=receipts), indent=2), encoding='utf-8')
    return dict(baseline=verified, denominator=143, counts=dict(counts), extensions_accepted=accepted_extensions,
                extensions_defined=len(extensions), next_task=next_task, changed=stale)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--check', action='store_true')
    mode.add_argument('--write', action='store_true')
    parser.add_argument('--audit', type=Path)
    args = parser.parse_args()
    print(json.dumps(synchronize(write=args.write, audit=args.audit), sort_keys=True))
