"""Bounded search of one explicitly selected retained extraction; no stored index or AI."""
import re
from bisect import bisect_left

from django.utils import timezone

from apps.expenses.services.statement_evidence import document_name, file_reference
from .canonical_evidence import _discovery_catalog, _load_catalog, SourceSelectionConflict
from .persistent_memory import _owner

TEXT_BYTES = 256 * 1024
PASSAGE_CHARS = 600
RESULT_LIMIT = 6
LIMITATION = ('These are unverified retained extraction excerpts, not current financial facts or answers. '
    'Extraction can omit or misread text; review the original and current corrected records. '
    'No authenticity, currency, completeness or confidence is inferred. No text is sent to a model or stored again.')


def _terms(query):
    if (not isinstance(query, str) or not 1 <= len(query.strip()) <= 128 or len(query.encode()) > 512
            or any(ord(char) < 32 or ord(char) == 127 for char in query)):
        raise ValueError('Enter up to 128 characters of search keywords.')
    terms = set(re.findall(r'\w+', query.casefold()))
    if not 1 <= len(terms) <= 8 or any(len(term) < 2 for term in terms):
        raise ValueError('Choose one to eight keywords of at least two characters.')
    return terms


def _passages(text):
    # Overlap keeps ordinary phrases spanning a passage boundary searchable.
    for start in range(0, len(text), PASSAGE_CHARS - 100):
        end = min(len(text), start + PASSAGE_CHARS)
        yield start, end, text[start:end]
        if end == len(text):
            break


def search_document(user, kind, document_id, *, query, catalog_token):
    _owner(user)
    terms = _terms(query)
    if type(document_id) is not int or document_id < 1:
        raise ValueError('Choose one document from the current source list.')
    document, _, stamp, _ = _discovery_catalog(user, kind, document_id)
    _load_catalog(catalog_token, stamp)
    source_file = document.original_file if kind == 'expense' else document.uploaded_file
    state, fingerprint, url = file_reference(source_file)
    text = getattr(document, 'extracted_text', '')
    status = ('source_unavailable' if state != 'available' else
        'extraction_unavailable' if document.parser_status not in ('parsed', 'needs_review') or not text.strip() else
        'extraction_limit' if len(text.encode()) > TEXT_BYTES else 'searched')
    matches = []
    if status == 'searched':
        positions = {term: [] for term in terms}
        for match in re.finditer(r'\w+', text):
            term = match.group().casefold()
            if term in positions:
                positions[term].append((match.start(), match.end()))
        last_end = -1
        for start, end, excerpt in _passages(text):
            found = 0; fresh = False
            for spans in positions.values():
                index = bisect_left(spans, (start, -1))
                if index < len(spans) and spans[index][1] <= end:
                    found += 1
                index = bisect_left(spans, (max(start, last_end), -1))
                fresh = fresh or index < len(spans) and spans[index][1] <= end
            if found == len(terms) and fresh:
                matches.append(dict(start=start, end=end, excerpt=excerpt))
                last_end = end
                if len(matches) > RESULT_LIMIT:
                    break
    # Recheck file, extraction, owner, links and source revision after searching.
    if _discovery_catalog(user, kind, document_id)[2] != stamp:
        raise SourceSelectionConflict()
    return dict(status=status, kind=kind, document_id=document_id, document_name=document_name(document),
        source_fingerprint=fingerprint, source_url=url, extraction_revision=stamp['source']['record'],
        checked_at=timezone.now().isoformat(), results=matches[:RESULT_LIMIT], more_matches=len(matches) > RESULT_LIMIT,
        result_limit=RESULT_LIMIT, full_text_qa=False, financial_authority=False, limitation=LIMITATION)
