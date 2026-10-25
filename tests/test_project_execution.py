"""Read-only inventory checks and failure-safe generated documentation updates."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from scripts.project_execution import ROOT, inventory, ordered, synchronize


class ProjectExecutionTests(TestCase):
    def fixture(self):
        root = Path(self.enterContext(TemporaryDirectory(prefix='alfred-docs-synthetic-')))
        for relative in ('README.md', 'docs/PROJECT_STATUS.md', 'docs/ALFRED_2_0_REQUIREMENTS.md', 'docs/EXECUTION_QUEUE.md'):
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes((ROOT / relative).read_bytes())
        return root

    def test_canonical_original_ids_remain_unique_and_views_are_current(self):
        rows = inventory((ROOT / 'docs/PROJECT_STATUS.md').read_text(encoding='utf-8'))
        self.assertEqual(len({r['id'] for r in rows}), 143)
        result = synchronize()
        self.assertEqual(sum(result['counts'].values()), 143)
        self.assertEqual(result['baseline'], sum(r['status'] == 'COMPLETE_VERIFIED' for r in rows))
        self.assertEqual(result['changed'], [])

    def test_unknown_and_duplicate_baseline_rows_fail_closed(self):
        row = '### DOC-01 — Synthetic capability\n\n**COMPLETE_VERIFIED** · Documents · P1.\n- Source: synthetic\n'
        with self.assertRaises(ValueError):
            inventory(row + row, expected=2)
        with self.assertRaises(ValueError):
            inventory(row.replace('COMPLETE_VERIFIED', 'ASSUMED_COMPLETE'), expected=1)

    def test_phase_order_keeps_unaccepted_before_partial_blocked_missing(self):
        statuses = ['NOT_IMPLEMENTED', 'PARTIALLY_IMPLEMENTED', 'BLOCKED_EXTERNAL', 'IMPLEMENTED_NOT_ACCEPTED', 'BLOCKED_APPROVAL']
        rows = [dict(id='DOC-'+str(i), prefix='DOC', priority=2, status=status) for i, status in enumerate(statuses, 1)]
        result = [r['status'] for r in ordered(rows)]
        self.assertEqual(result[0], 'IMPLEMENTED_NOT_ACCEPTED')
        self.assertEqual(result[1], 'PARTIALLY_IMPLEMENTED')
        self.assertEqual(set(result[2:4]), {'BLOCKED_EXTERNAL', 'BLOCKED_APPROVAL'})
        self.assertEqual(result[-1], 'NOT_IMPLEMENTED')

    def test_check_is_read_only_even_when_counts_are_stale(self):
        root = self.fixture()
        path = root / 'docs/PROJECT_STATUS.md'
        path.write_text(path.read_text(encoding='utf-8').replace('**COMPLETE_VERIFIED**', '**IMPLEMENTED_NOT_ACCEPTED**', 1), encoding='utf-8')
        before = {p: p.read_bytes() for p in root.rglob('*.md')}
        with self.assertRaises(ValueError):
            synchronize(root)
        self.assertEqual(before, {p: p.read_bytes() for p in root.rglob('*.md')})
        synchronize(root, write=True)
        self.assertEqual(synchronize(root)['changed'], [])

    def test_unknown_dependency_does_not_write_any_document(self):
        root = self.fixture()
        path = root / 'docs/ALFRED_2_0_REQUIREMENTS.md'
        path.write_text(path.read_text(encoding='utf-8').replace('| LOAN-07 | FIN-07 |', '| LOAN-07 | UNKNOWN-99 |'), encoding='utf-8')
        before = (root / 'README.md').read_bytes()
        with self.assertRaises(ValueError):
            synchronize(root, write=True)
        self.assertEqual((root / 'README.md').read_bytes(), before)

    def test_extension_acceptance_requires_evidence_and_survives_regeneration(self):
        root = self.fixture()
        path = root / 'docs/PROJECT_STATUS.md'
        original = path.read_text(encoding='utf-8')
        old = '| CAREER2-001 | UNACCEPTED | No full-story acceptance recorded. |'
        path.write_text(original.replace(old, '| CAREER2-001 | ACCEPTED | No evidence |'), encoding='utf-8')
        with self.assertRaises(ValueError):
            synchronize(root, write=True)
        path.write_text(original.replace(old, '| CAREER2-001 | ACCEPTED | [Synthetic reviewed source receipt](synthetic.json) |'), encoding='utf-8')
        result = synchronize(root, write=True)
        self.assertEqual(result['extensions_accepted'], 1)
        self.assertEqual(synchronize(root)['extensions_accepted'], 1)
        self.assertIn('1/13 accepted', (root / 'README.md').read_text(encoding='utf-8'))

    def test_duplicate_extension_ids_are_rejected(self):
        root = self.fixture()
        path = root / 'docs/ALFRED_2_0_REQUIREMENTS.md'
        path.write_text(path.read_text(encoding='utf-8').replace('| CAREER2-002 | Recruiter', '| CAREER2-001 | Recruiter'), encoding='utf-8')
        with self.assertRaises(ValueError):
            synchronize(root, write=True)

    def test_dependency_cycle_is_rejected_before_writes(self):
        root = self.fixture()
        path = root / 'docs/ALFRED_2_0_REQUIREMENTS.md'
        path.write_text(path.read_text(encoding='utf-8').replace('| LOAN-07 | FIN-07 |', '| LOAN-07 | LOAN-07 |'), encoding='utf-8')
        with self.assertRaises(ValueError):
            synchronize(root, write=True)

    def test_replacing_original_id_is_rejected_even_with_143_rows(self):
        root = self.fixture()
        path = root / 'docs/PROJECT_STATUS.md'
        path.write_text(path.read_text(encoding='utf-8').replace('### FIN-01 —', '### FIN-99 —'), encoding='utf-8')
        with self.assertRaises(ValueError):
            synchronize(root, write=True)

    def test_missing_original_catalog_cannot_be_silently_recreated(self):
        root = self.fixture()
        path = root / 'docs/ALFRED_2_0_REQUIREMENTS.md'
        text = path.read_text(encoding='utf-8')
        first, rest = text.split('<!-- BEGIN BASELINE INTENT INDEX -->')
        _, last = rest.split('<!-- END BASELINE INTENT INDEX -->')
        path.write_text(first + '<!-- BEGIN BASELINE INTENT INDEX -->\n<!-- END BASELINE INTENT INDEX -->' + last, encoding='utf-8')
        with self.assertRaises(ValueError):
            synchronize(root, write=True)
