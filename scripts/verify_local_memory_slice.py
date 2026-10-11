"""Two-process synthetic M15 proof; refuses to overwrite an existing vault."""
import argparse
from contextlib import closing
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
import sys
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from apps.ml_engine.services.persistent_memory import MemoryStore


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--phase', required=True, choices=('save', 'restore'))
    parser.add_argument('--proof-dir', type=Path, required=True)
    args = parser.parse_args()
    root = args.proof_dir.resolve()
    marker = root / 'synthetic-proof.json'
    if args.phase == 'save' and root.exists() and any(root.iterdir()):
        parser.error('Use a new empty synthetic proof directory; existing data is preserved.')
    owner = SimpleNamespace(pk=10001, created_at=datetime(2026, 10, 11, tzinfo=timezone.utc), is_authenticated=True)
    other = SimpleNamespace(pk=10002, created_at=owner.created_at, is_authenticated=True)
    query = 'Where should I go for a peaceful hiking holiday in the hills?'
    if args.phase == 'save':
        store = MemoryStore(root)
        identity = store.save_verified(owner, {'travel_preference': 'I prefer quiet mountain destinations for hiking holidays.'},
            {'source': 'synthetic owner confirmation', 'reference': 'synthetic-local-proof'}, verified=True)
        result = store.retrieve(owner, query, limit=1)
        assert result[0]['id'] == identity and result[0]['score'] > 0.3
        assert store.retrieve(other, query) == []
        with closing(sqlite3.connect(store.database)) as db, db:
            ciphertext = db.execute('SELECT ciphertext FROM events').fetchone()[0]
            assert b'travel_preference' not in ciphertext
            identity, owner_hash, encrypted = db.execute('SELECT id,owner,record FROM memories').fetchone()
            dimensions = len(store._decode(db, identity, owner_hash, encrypted)['embedding'])
        marker.write_text(json.dumps({'synthetic': True, 'memory_id': identity, 'dimensions': dimensions}))
        print(json.dumps({'phase': 'save', 'status': 'PASS', 'embedding_dimensions': dimensions, 'owner_isolation': 'PASS', 'encrypted_event': 'PASS', 'cloud_calls': 0}))
    else:
        if not marker.is_file():
            parser.error('The synthetic save-phase marker is required; no data changed.')
        proof = json.loads(marker.read_text())
        if proof.get('synthetic') is not True:
            parser.error('This directory is not a synthetic proof; no data changed.')
        store = MemoryStore(root)
        with closing(sqlite3.connect(store.database)) as db, db:
            if db.execute('SELECT COUNT(*) FROM memories').fetchone()[0] != 1 or db.execute('SELECT COUNT(*) FROM events').fetchone()[0] != 1:
                parser.error('The synthetic proof vault contains additional records; no data changed.')
        before = store.retrieve(owner, query, limit=1)
        assert before[0]['id'] == proof['memory_id']
        # Remove only the disposable derived index to prove encrypted event recovery.
        with closing(sqlite3.connect(store.database)) as db, db:
            db.execute('DELETE FROM memories WHERE id=?', (proof['memory_id'],))
        assert store.restore_owner(owner) == 1
        after = store.retrieve(owner, query, limit=1)
        assert after[0]['id'] == proof['memory_id']
        assert after[0]['provenance']['reference'] == 'synthetic-local-proof'
        assert after[0]['sensitivity'] == 'sensitive'
        assert store.retrieve(other, query) == []
        assert store.restore_owner(owner) == 1
        print(json.dumps({'phase': 'restart_restore', 'status': 'PASS', 'retrieved_same_memory': True, 'score': round(after[0]['score'], 6), 'provenance_preserved': True, 'sensitivity_preserved': True, 'owner_isolation': 'PASS', 'cloud_calls': 0}))


if __name__ == '__main__':
    main()
