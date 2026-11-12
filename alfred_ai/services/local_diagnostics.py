"""Explicit synthetic inference checks against the fixed local Ollama listener."""
import json
import time
from http.client import HTTPConnection, HTTPException
from math import isfinite

from django.conf import settings

from apps.ml_engine.services.hybrid_intelligence import OllamaReasoner
from apps.ml_engine.services.local_embeddings import OllamaEmbeddings, EmbeddingUnavailable, KEEP_ALIVE
from apps.ml_engine.services.local_ai_limits import deadline as local_deadline, ollama_address


def _seconds(value):
    if type(value) not in (int, float) or not isfinite(value) or value < 0:
        return None
    return round(value / 1_000_000_000, 3)


def _chat_probe(reasoner, deadline):
    before = reasoner._digest(deadline=deadline)
    started = time.monotonic()
    connection = HTTPConnection(*ollama_address(), timeout=max(.001, deadline - started))
    first_token = None
    total = 0
    final = None
    buffer = b''
    body = {'model': reasoner.model, 'stream': True, 'think': False, 'keep_alive': KEEP_ALIVE,
            'options': {'num_predict': 24, 'num_ctx': 8192, 'temperature': 0},
            'messages': [{'role': 'user', 'content': 'Reply with the words ALFRED local inference is working.'}]}
    try:
        connection.request('POST', '/api/chat', json.dumps(body).encode(),
                           {'Content-Type': 'application/json', 'Accept-Encoding': 'identity'})
        response = connection.getresponse()
        if response.status != 200 or response.getheader('Content-Encoding', 'identity') != 'identity':
            raise EmbeddingUnavailable('Local inference did not complete. Check Ollama and retry.')
        while final is None and total <= 256 * 1024:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise EmbeddingUnavailable('Local inference exceeded its 30-second budget. Close other model tasks and retry.')
            sock = connection.sock or response.fp.raw._sock
            sock.settimeout(remaining)
            chunk = response.read1(8192)
            total += len(chunk)
            if not chunk or total > 256 * 1024:
                break
            buffer += chunk
            while b'\n' in buffer:
                line, buffer = buffer.split(b'\n', 1)
                if len(line) > 65536:
                    raise ValueError()
                part = json.loads(line)
                if not isinstance(part, dict) or part.get('model') != reasoner.model or part.get('error'):
                    raise ValueError()
                message = part.get('message', {})
                if (not isinstance(message, dict) or message.get('role') != 'assistant'
                        or message.get('tool_calls') or not isinstance(message.get('content'), str)):
                    raise ValueError()
                if message['content'].strip() and first_token is None:
                    first_token = round(time.monotonic() - started, 3)
                if part.get('done') is True:
                    final = part
                    break
            if len(buffer) > 65536:
                raise ValueError()
        if final is None or first_token is None or reasoner._digest(deadline=deadline) != before:
            raise ValueError()
        duration = _seconds(final.get('eval_duration'))
        count = final.get('eval_count')
        return {'state': 'running', 'detail': 'A synthetic prompt completed locally.',
                'first_token_seconds': first_token, 'load_seconds': _seconds(final.get('load_duration')),
                'output_tokens_per_second': round(count / duration, 2)
                if type(count) is int and count > 0 and duration and duration > 0 else None}
    except (OSError, HTTPException, ValueError, TypeError, KeyError, UnicodeError):
        raise EmbeddingUnavailable('Local inference failed or timed out. Open Ollama, check the selected model and retry.') from None
    finally:
        connection.close()


def benchmark_local_ai():
    deadline = local_deadline()
    results = []
    for capability, model in (('Embeddings', OllamaEmbeddings.model), ('Local chat', settings.ALFRED_MEMORY_OLLAMA_MODEL)):
        result = {'label': capability, 'model': model, 'state': 'error'}
        started = time.monotonic()
        try:
            if capability == 'Embeddings':
                OllamaEmbeddings().embed('ALFRED synthetic diagnostic sample.', deadline=deadline)
                result.update(state='running', detail='A synthetic embedding completed locally.')
            else:
                result.update(_chat_probe(OllamaReasoner(), deadline))
        except EmbeddingUnavailable:
            # Only our fixed messages are displayed; provider response text never reaches the page.
            result['detail'] = ('Inference unavailable within the 30-second budget. Open Ollama and check that this model '
                                'is installed; retry after closing other model tasks. Existing data is preserved.')
        result['elapsed_seconds'] = round(time.monotonic() - started, 3)
        results.append(result)
    try:
        loaded = OllamaEmbeddings()._request('GET', '/api/ps', deadline=deadline).get('models', [])
        if not isinstance(loaded, list):
            loaded = []
        for result in results:
            item = next((m for m in loaded if isinstance(m, dict) and m.get('name') == result['model']), {})
            for field in ('size', 'size_vram'):
                size = item.get(field)
                result[field] = size if type(size) is int and size >= 0 else None
            result['acceleration'] = ('GPU allocation observed' if result['size_vram'] else
                                      'CPU allocation observed' if result['size_vram'] == 0 and result['size'] else 'Unverified')
    except EmbeddingUnavailable:
        pass
    return results
