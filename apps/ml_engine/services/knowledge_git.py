"""Dormant ciphertext-only Git transport. No repository provisioning or credentials."""
import os
import base64
import logging
from pathlib import Path
import re
import shutil
import subprocess
import time

from .memory_key import private_directory
from .memory_sync import SyncUnavailable, SyncConflict, remaining, valid_id
from .knowledge_hub import MAX_BUNDLE


class GitKnowledgeProvider:
    def __init__(self, directory, remote, *, authorized=False, credential='', local_fixture=False, deadline=None):
        if authorized is not True:
            raise PermissionError('Private Git activation requires separate operator approval.')
        if not local_fixture and (not isinstance(remote, str) or not re.fullmatch(r'https://github\.com/[A-Za-z0-9_-]+/[A-Za-z0-9_.-]+\.git', remote)):
            raise ValueError('Use an approved existing HTTPS repository without embedded credentials.')
        if local_fixture and (not Path(remote).is_absolute() or not Path(remote).is_dir()):
            raise ValueError('Synthetic Git fixtures must be existing absolute local repositories.')
        if not local_fixture and (not isinstance(credential, str) or not re.fullmatch(r'[A-Za-z0-9_]{20,512}', credential)):
            raise SyncUnavailable('An independently approved local Git credential is required.')
        self.directory = Path(directory)
        if not self.directory.is_absolute():
            raise ValueError('Git cache requires an absolute protected directory.')
        self.git = shutil.which('git')
        if not self.git:
            raise SyncUnavailable('Git is unavailable; local knowledge is retained.')
        self.remote = str(remote)
        self.fixture = local_fixture
        self.credential = '' if local_fixture else credential
        deadline = deadline or time.monotonic() + 5
        private_directory(self.directory, deadline=deadline)
        if not (self.directory / 'HEAD').exists():
            if any(self.directory.iterdir()):
                raise SyncUnavailable('Existing non-Git cache contents are preserved.')
            self._git('init', '--bare', '.', deadline=deadline)
        if self._git('rev-parse', '--is-bare-repository', deadline=deadline).strip() != b'true':
            raise SyncUnavailable('Knowledge cache must be an isolated bare repository.')

    def _git(self, *args, deadline, body=None, allow_missing=False):
        # Ignore operator hooks, aliases, helpers and injected Git configuration.
        env = {k: v for k, v in os.environ.items() if not k.startswith(('GIT_', 'SSH_'))}
        env.update(GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull,
                   GIT_TERMINAL_PROMPT='0', GIT_ASKPASS='echo', GIT_NO_LAZY_FETCH='1')
        if self.credential:
            header = base64.b64encode(('x-access-token:' + self.credential).encode()).decode()
            # Credentials stay in the child environment, never arguments, URLs or Git configuration files.
            env.update(GIT_CONFIG_COUNT='1', GIT_CONFIG_KEY_0='http.' + self.remote + '.extraHeader',
                       GIT_CONFIG_VALUE_0='AUTHORIZATION: basic ' + header)
        command = [self.git, '-c', 'core.hooksPath=' + os.devnull, '-c', 'credential.helper=',
                   '-c', 'protocol.allow=never', '-c', 'protocol.https.allow=always',
                   '-c', 'protocol.file.allow=' + ('always' if self.fixture else 'never'),
                   '-c', 'user.name=ALFRED Knowledge', '-c', 'user.email=knowledge@alfred.invalid',
                   '-c', 'commit.gpgsign=false', '-c', 'http.followRedirects=false', *args]
        try:
            result = subprocess.run(command, cwd=self.directory, env=env, input=body, capture_output=True,
                                    timeout=remaining(deadline), creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        except (OSError, subprocess.TimeoutExpired) as exc:
            logging.getLogger(__name__).warning('Knowledge Git deferred; operation=%s; exception_type=%s', args[0], type(exc).__name__)
            raise SyncUnavailable('Git operation failed or exceeded its deadline; local knowledge is retained.') from None
        remaining(deadline)
        if result.returncode and not allow_missing:
            logging.getLogger(__name__).warning('Knowledge Git failed; operation=%s; exit_code=%s', args[0], result.returncode)
            raise SyncUnavailable('Git operation failed; local knowledge and history are retained.')
        return result.stdout if not result.returncode else None

    def _ref(self, owner):
        if not valid_id(owner, 64):
            raise PermissionError('Invalid knowledge owner.')
        return 'refs/heads/alfred-knowledge-' + owner

    def read(self, owner, *, deadline):
        ref = self._ref(owner)
        listing = self._git('ls-remote', '--refs', self.remote, ref, deadline=deadline)
        if not listing.strip():
            return None
        if not re.fullmatch(rb'[a-f0-9]{40}\t' + re.escape(ref.encode()) + rb'\s*', listing):
            raise SyncUnavailable('Remote Git reference is invalid.')
        self._git('fetch', '--no-tags', '--depth=128', '--filter=blob:limit=' + str(MAX_BUNDLE),
                  self.remote, ref, deadline=deadline)
        # Refuse further processing of an oversized cache; never delete retained history automatically.
        if sum(path.stat().st_size for path in self.directory.rglob('*') if path.is_file()) > 16 * 1024 * 1024:
            raise SyncUnavailable('Git cache exceeds its bounded review budget; local history is preserved.')
        head = self._git('rev-parse', 'FETCH_HEAD', deadline=deadline).decode().strip()
        if not valid_id(head, 40) or head != listing.split()[0].decode():
            raise SyncConflict('Remote Git changed during fetch; retry without replacing history.')
        tree_size = self._git('cat-file', '-s', head + '^{tree}', deadline=deadline)
        if not tree_size.strip().isdigit() or not 1 <= int(tree_size) <= 128:
            raise SyncUnavailable('Remote tree exceeds the single-file knowledge contract.')
        tree = self._git('ls-tree', head, deadline=deadline)
        match = re.fullmatch(rb'100644 blob ([a-f0-9]{40})\tknowledge.enc\n', tree)
        if not match:
            raise SyncUnavailable('Remote tree contains unsupported files or executable content.')
        blob = match[1].decode()
        size = self._git('cat-file', '-s', blob, deadline=deadline)
        if not size.strip().isdigit() or not 1 <= int(size) <= MAX_BUNDLE:
            raise SyncUnavailable('Remote encrypted knowledge exceeds its byte budget.')
        body = self._git('cat-file', 'blob', blob, deadline=deadline)
        history = self._git('rev-list', '--max-count=128', head, deadline=deadline).decode().splitlines()
        return {'head': head, 'body': body, 'history': history}

    def publish(self, owner, expected, body, *, deadline):
        ref = self._ref(owner)
        if not isinstance(body, bytes) or not 1 <= len(body) <= MAX_BUNDLE or (expected is not None and not valid_id(expected, 40)):
            raise ValueError('Invalid encrypted knowledge checkpoint.')
        current = self._git('ls-remote', '--refs', self.remote, ref, deadline=deadline)
        if (current.split()[0].decode() if current.strip() else None) != expected:
            raise SyncConflict('Remote Git advanced; encrypted local updates remain queued.')
        blob = self._git('hash-object', '-w', '--stdin', deadline=deadline, body=body).strip()
        tree = self._git('mktree', deadline=deadline, body=b'100644 blob ' + blob + b'\tknowledge.enc\n').decode().strip()
        parent = ['-p', expected] if expected else []
        head = self._git('commit-tree', tree, *parent, deadline=deadline,
                         body=b'Checkpoint reviewed encrypted knowledge batch\n').decode().strip()
        try:
            self._git('push', '--porcelain', self.remote, head + ':' + ref, deadline=deadline)
        except SyncUnavailable:
            raise SyncConflict('Git push failed or raced; retry queued local changes without a force push.') from None
        return head


def configured_git():
    from django.conf import settings
    return bool(settings.ALFRED_KNOWLEDGE_GIT_AUTHORIZED
                and re.fullmatch(r'https://github\.com/[A-Za-z0-9_-]+/[A-Za-z0-9_.-]+\.git', settings.ALFRED_KNOWLEDGE_GIT_REMOTE)
                and re.fullmatch(r'[A-Za-z0-9_]{20,512}', settings.ALFRED_KNOWLEDGE_GIT_TOKEN))


def git_provider(store, *, deadline):
    from django.conf import settings
    return GitKnowledgeProvider(store.directory / 'knowledge-git', settings.ALFRED_KNOWLEDGE_GIT_REMOTE,
                                authorized=settings.ALFRED_KNOWLEDGE_GIT_AUTHORIZED,
                                credential=settings.ALFRED_KNOWLEDGE_GIT_TOKEN, deadline=deadline)
