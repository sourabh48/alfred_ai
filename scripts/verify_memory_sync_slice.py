"""Two-process synthetic encrypted synchronization and real local Ollama proof."""
import argparse
from contextlib import ExitStack
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from apps.ml_engine.services.persistent_memory import MemoryStore, _owner
from apps.ml_engine.services.memory_sync import MemorySynchronizer, MockCloudProvider


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--phase',required=True,choices=('save','restore'))
    parser.add_argument('--proof-dir',type=Path,required=True)
    parser.add_argument('--provider',choices=('mock','s3-wire'),default='mock')
    args=parser.parse_args()
    with ExitStack() as stack: run_proof(args,stack,parser)


def run_proof(args,stack,parser):
    root=args.proof_dir.resolve(); marker=root/'synthetic-sync-proof.json'
    if args.phase=='save' and root.exists() and any(root.iterdir()):
        parser.error('Use a new empty synthetic proof directory; existing data is preserved.')
    if args.phase=='restore' and (not marker.exists() or json.loads(marker.read_text()).get('synthetic') is not True):
        parser.error('The synthetic save-phase marker is required.')
    owner=SimpleNamespace(pk=10001,created_at=datetime(2026,10,11,tzinfo=timezone.utc),is_authenticated=True)
    other=SimpleNamespace(pk=10002,created_at=owner.created_at,is_authenticated=True)
    query='Where should I go for a peaceful hiking holiday in the hills?'
    store=MemoryStore(root/('first' if args.phase=='save' else 'restart'))
    wire=None
    if args.provider=='s3-wire':
        from unittest.mock import patch
        from tests.memory_s3_fixture import PROFILE, SignedS3Fixture, LegacyS3FixtureProvider as S3MemoryProvider
        wire=SignedS3Fixture(root/'s3-wire.sqlite3')
        stack.enter_context(patch('tests.memory_s3_fixture.request',side_effect=wire.request))
        provider=S3MemoryProvider(_owner(owner),PROFILE)
    else: provider=MockCloudProvider(root/'mock-provider')
    sync=MemorySynchronizer(store,provider)
    if args.phase=='restore':
        key='sync-'+_owner(owner)+'.key'
        # Only the synthetic protected owner key is provisioned; no SQLite files are synchronized.
        destination=store.directory/key
        if destination.exists(): parser.error('Use a fresh restart vault; existing data is preserved.')
        destination.write_bytes((root/'first'/key).read_bytes())
        sync.import_checkpoint(owner,(root/'trusted-checkpoint.encrypted').read_bytes(),confirm=True)
    sync.configure(owner,enabled=True,consent=True)
    if args.phase=='save':
        identity=store.save_verified(owner,{'travel_preference':'I prefer quiet mountain destinations for hiking holidays.'},
            {'source':'synthetic owner confirmation','reference':'synthetic-sync-proof'},verified=True)
        assert sync.run(owner)=='uploaded'
        (root/'trusted-checkpoint.encrypted').write_bytes(sync.export_checkpoint(owner,confirm=True))
        marker.write_text(json.dumps({'synthetic':True,'memory_id':identity,'provider':args.provider}))
    else:
        evidence=json.loads(marker.read_text())
        assert evidence.get('provider','mock')==args.provider
        identity=evidence['memory_id']
        assert sync.run(owner)=='downloaded'
        assert store.restore_owner(owner)==1
    result=store.retrieve(owner,query,limit=1)[0]
    assert result['id']==identity and result['score']>0.3
    assert result['sensitivity']=='sensitive' and result['provenance']['reference']=='synthetic-sync-proof'
    assert store.retrieve(other,query)==[]
    with store._transaction() as db:
        row=db.execute('SELECT id,owner,record FROM memories').fetchone()
        dimensions=len(store._decode(db,*row)['embedding'])
    for path in ([root/'s3-wire.sqlite3'] if wire else (root/'mock-provider').iterdir()):
        if path.is_file():
            assert b'travel_preference' not in path.read_bytes() and b'synthetic owner confirmation' not in path.read_bytes()
    print(json.dumps({'phase':args.phase,'status':'PASS','provider':args.provider,'signed_fixture_requests':wire.calls if wire else 0,
        'embedding_dimensions':dimensions,'score':round(result['score'],6),'same_memory':True,
        'owner_isolation':'PASS','encrypted_cloud_objects':'PASS','external_cloud_calls':0}))


if __name__=='__main__': main()
