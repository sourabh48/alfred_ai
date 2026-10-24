"""Independent fictional holdout disclosed only after the retrieval policy was frozen.

Expected answers are evaluation labels, never ranker inputs or private user data.
A policy change requires a new independent holdout rather than tuning to this one.
"""
from hashlib import sha256
import json
from pathlib import Path


POLICY_COMMIT = '0651e7a9fb48d5e142ae903c6be5d7d8102730cf'
POLICY_SHA256 = '1d339250ceddeaf924f7e895e0ad58bfa264dc7b6ef4ce818f297caf8e19afb4'
FIXTURE_SHA256 = 'ee0401374fb7c15a4cec65d4a4b5ab3c1199ee3b7d6ac9e27421bc856813208e'
# Exact 1587-byte compact UTF-8 commitment, independently reviewed before tuning.
RAW = '{"id":"craft-lab-holdout-v1","records":{"pigment":"Fictional Della uses indigo ink when sketching botanical diagrams.","counterclaim":"Fictional Della avoids indigo ink when sketching botanical diagrams.","audio":"Fictional Della edits podcasts in mono to reduce file size.","loom":"Fictional Della calibrates a mechanical loom before weaving wool cloth.","old":"Fictional Della labels laboratory samples with circular stickers.","deleted":"Fictional Della designs coordinate grids for topographic maps.","foreign":"Fictional Orla develops number-theory proofs about gaps between prime numbers."},"correction":["old","Fictional Della now labels laboratory samples with triangular stickers."],"cases":[["Which ink-related statements describe Della\'s botanical diagram sketches?",["pigment","counterclaim"]],["Which audio channel configuration does Della use to edit podcasts?",["audio"]],["What does Della calibrate before weaving wool cloth?",["loom"]],["What shape of sticker does Della currently use for laboratory samples?",["corrected"]],["What conflicting statements concern Della using indigo ink for botanical sketches?",["pigment","counterclaim"]],["How does Della prepare the loom before working on wool cloth?",["loom"]],["How does Della divide latitude and longitude into map grids?",[]],["What does Orla prove about gaps between prime numbers?",[]],["How does a magnetron generate microwave radiation?",[]],["Which strokes did Della\'s rowing team practice?",[]],["What are the rules for castling in chess?",[]],["How does a kiln\'s oxygen supply affect ceramic glazing?",[]]]}'


def cohort():
    """Fail closed on altered labels, missing source or post-disclosure policy tuning."""
    raw = RAW.encode('utf-8')
    if len(raw) != 1587 or sha256(raw).hexdigest() != FIXTURE_SHA256:
        raise ValueError('Independent holdout commitment is unavailable.')
    try:
        source = Path(__file__).with_name('persistent_memory.py').read_bytes().replace(b'\r\n', b'\n')
    except OSError:
        raise ValueError('Frozen retrieval policy is unavailable.') from None
    if sha256(source).hexdigest() != POLICY_SHA256:
        raise ValueError('Changed retrieval policy requires a new independent holdout.')
    return json.loads(raw)


def availability():
    try:
        cohort()
    except ValueError:
        return False
    return True
