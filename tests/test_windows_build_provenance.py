"""Frozen provenance uses disposable Git fixtures, never the operator checkout."""
import json
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
import unittest

from scripts.package_windows_release import source_identity, write_build_provenance, verify_build_provenance


class WindowsBuildProvenanceTests(unittest.TestCase):
    def setUp(self):
        self.temporary=TemporaryDirectory(prefix='alfred-build-source-')
        self.addCleanup(self.temporary.cleanup)
        self.root=Path(self.temporary.name)
        self.repo=self.root/'repo'; self.repo.mkdir()
        self.bundle=self.root/'bundle'; self.bundle.mkdir()
        self.hooks=self.root/'empty-hooks'; self.hooks.mkdir()
        self.git('init','--quiet')
        (self.repo/'source.py').write_text('version = 1\n')
        self.commit()

    def git(self,*args):
        return subprocess.check_output(['git','-c',f'core.hooksPath={self.hooks}',
            '-c','user.name=Synthetic Build Test','-c','user.email=build@example.invalid',*args],cwd=self.repo,text=True,stderr=subprocess.STDOUT).strip()

    def commit(self):
        self.git('add','source.py'); self.git('commit','--quiet','-m','Synthetic build source')

    def test_embedded_identity_matches_exact_commit_and_tree(self):
        source=source_identity(self.repo)
        write_build_provenance(self.bundle,source,self.repo)
        self.assertEqual(verify_build_provenance(self.bundle,self.repo),source)
        self.assertEqual(source['source_commit'],self.git('rev-parse','HEAD'))
        self.assertEqual(source['source_tree'],self.git('rev-parse','HEAD^{tree}'))
        self.assertIs(source['source_dirty'],False)

    def test_dirty_or_untracked_source_is_never_packaged(self):
        source=source_identity(self.repo)
        for file in ('source.py','untracked.py'):
            target=self.repo/file; original=target.read_bytes() if target.exists() else None
            target.write_text('version = 2\n')
            with self.assertRaises(RuntimeError): write_build_provenance(self.bundle,source,self.repo)
            self.assertFalse((self.bundle/'build-provenance.json').exists())
            if original is None: target.unlink()
            else: target.write_bytes(original)

    def test_later_commit_cannot_relabel_an_older_bundle(self):
        source=source_identity(self.repo)
        write_build_provenance(self.bundle,source,self.repo)
        original=(self.bundle/'build-provenance.json').read_bytes()
        (self.repo/'source.py').write_text('version = 2\n'); self.commit()
        with self.assertRaises(RuntimeError): verify_build_provenance(self.bundle,self.repo)
        with self.assertRaises(RuntimeError): write_build_provenance(self.bundle,source,self.repo)
        self.assertEqual((self.bundle/'build-provenance.json').read_bytes(),original)

    def test_missing_malformed_or_forged_metadata_fails_closed(self):
        path=self.bundle/'build-provenance.json'; source=source_identity(self.repo)
        with self.assertRaises(RuntimeError): verify_build_provenance(self.bundle,self.repo)
        for data in ('not json',json.dumps(source|{'source_dirty':True}),json.dumps(source|{'source_dirty':0}),
                json.dumps(source|{'schema':True}),json.dumps(source|{'source_tree':'0'*40}),json.dumps(source|{'extra':'unreviewed'})):
            path.write_text(data)
            with self.subTest(data=data), self.assertRaises(RuntimeError): verify_build_provenance(self.bundle,self.repo)
