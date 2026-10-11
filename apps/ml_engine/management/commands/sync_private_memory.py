"""Bounded owner-opted-in provider tick; failures leave encrypted retries."""
from pathlib import Path
import time

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from alfred_ai.services.api_errors import safe_error_details
from apps.ml_engine.services.memory_sync import remaining, SyncConflict
from apps.ml_engine.services.persistent_memory import MemoryStore, _owner
from apps.ml_engine.services.memory_cloud import synchronizer, configured_provider


class Command(BaseCommand):
    help='Run a bounded owner-approved encrypted memory synchronization tick.'

    def add_arguments(self,parser):
        parser.add_argument('--seconds',type=float,default=5)

    def handle(self,**options):
        seconds=options['seconds']
        if not 0<seconds<=5: raise CommandError('Synchronization deadline must be between zero and five seconds.')
        counts={'processed':0,'failed':0,'conflicts':0}
        if not configured_provider() or (configured_provider()=='s3' and not settings.ALFRED_MEMORY_CLOUD_AUTHORIZED) or not (Path(settings.ALFRED_MEMORY_DIR)/'verified.sqlite3').exists():
            self.stdout.write('Memory synchronization disabled; no provider contact.')
            return
        deadline=time.monotonic()+seconds
        try:
            store=MemoryStore(settings.ALFRED_MEMORY_DIR,timeout=remaining(deadline))
            users=get_user_model().objects.filter(is_active=True).order_by('pk')
            count=users.count()
            # Bounded rotating batches avoid starving later owners; sync consent is checked per owner.
            offset=(int(time.time()//60)*16)%max(count,1)
            for user in users[offset:offset+16]:
                if time.monotonic()>=deadline: break
                try:
                    with store._transaction(timeout=remaining(deadline)) as db:
                        if not store._sync_state(db,_owner(user))['enabled']: continue
                    sync=synchronizer(store,user,deadline=deadline)
                    result=sync.run(user,seconds=remaining(deadline))
                    counts['processed']+=result!='disabled'
                except SyncConflict as exc:
                    counts['conflicts']+=1
                    safe_error_details(exc,'Encrypted memory synchronization requires explicit recovery.',logger_name=__name__)
                except Exception as exc:
                    counts['failed']+=1
                    safe_error_details(exc,'Encrypted local memory updates remain queued.',logger_name=__name__)
        except Exception as exc:
            counts['failed']+=1
            safe_error_details(exc,'Encrypted memory synchronization is unavailable.',logger_name=__name__)
        self.stdout.write('Memory sync processed={processed}; failed={failed}; conflicts={conflicts}'.format(**counts))
