"""Local authenticated recovery checkpoints; no passwords, keys or network calls."""
import os
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from apps.ml_engine.services.memory_sync import MemorySynchronizer
from apps.ml_engine.services.persistent_memory import MemoryStore


class Command(BaseCommand):
    help='Export/import a trusted sync checkpoint locally; import requires an unused vault and its recovered owner key.'

    def add_arguments(self,parser):
        parser.add_argument('action',choices=('export','import'))
        parser.add_argument('--user',type=int,required=True)
        parser.add_argument('--file',required=True)
        parser.add_argument('--confirm',action='store_true')

    def handle(self,**options):
        try:
            path=Path(options['file'])
            if not options['confirm'] or not path.is_absolute() or any(p.is_symlink() or p.is_junction() for p in (path,*path.parents)): raise ValueError()
            user=get_user_model().objects.get(pk=options['user'],is_active=True)
            sync=MemorySynchronizer(MemoryStore(settings.ALFRED_MEMORY_DIR),None)
            if options['action']=='export':
                checkpoint=sync.export_checkpoint(user,confirm=True)
                descriptor=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
                with os.fdopen(descriptor,'wb') as stream:
                    stream.write(checkpoint); stream.flush(); os.fsync(stream.fileno())
                self.stdout.write('Trusted checkpoint exported. No memory content or recovery key was exported.')
            else:
                with path.open('rb') as stream: checkpoint=stream.read(4097)
                sync.import_checkpoint(user,checkpoint,confirm=True)
                self.stdout.write('Trusted checkpoint verified. Synchronization consent remains disabled.')
        except Exception:
            raise CommandError('Checkpoint operation failed safely; existing files, keys and memories are preserved.') from None
