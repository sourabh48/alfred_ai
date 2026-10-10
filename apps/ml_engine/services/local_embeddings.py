"""Bounded embedding calls to the fixed local Ollama listener; no cloud fallback."""
from http.client import HTTPConnection, HTTPException
import json
from math import isfinite, hypot


class EmbeddingUnavailable(RuntimeError):
    pass


def validate_vector(value):
    if (not isinstance(value, list) or not 1 <= len(value) <= 4096
            or any(isinstance(v, bool) or not isinstance(v, (int, float)) or not isfinite(v) or abs(v) > 1_000_000 for v in value)
            or not hypot(*value)):
        raise EmbeddingUnavailable('Local embedding response is invalid.')
    return value


class OllamaEmbeddings:
    model = 'all-minilm:latest'

    def _request(self, method, path, payload=None):
        connection = HTTPConnection('127.0.0.1', 11434, timeout=30)
        try:
            body = json.dumps(payload, allow_nan=False).encode() if payload is not None else None
            connection.request(method, path, body=body, headers={'Content-Type': 'application/json', 'Accept-Encoding': 'identity'})
            response = connection.getresponse()
            if response.status != 200 or response.getheader('Content-Encoding', 'identity') != 'identity':
                raise EmbeddingUnavailable('Local embedding service is unavailable.')
            raw = response.read(256 * 1024 + 1)
            if len(raw) > 256 * 1024:
                raise EmbeddingUnavailable('Local embedding response exceeds its limit.')
            result = json.loads(raw)
            if not isinstance(result, dict):
                raise ValueError()
            return result
        except (OSError, HTTPException, ValueError, KeyError, TypeError):
            raise EmbeddingUnavailable('Local embedding service is unavailable.') from None
        finally:
            connection.close()

    def _digest(self):
        models = self._request('GET', '/api/tags').get('models', [])
        if not isinstance(models, list) or any(not isinstance(item, dict) for item in models):
            raise EmbeddingUnavailable('Local embedding response is invalid.')
        item = next((item for item in models if item.get('name') == self.model), {})
        if item.get('remote_host') or item.get('remote_model'):
            raise EmbeddingUnavailable('A local embedding model is required.')
        digest = item.get('digest')
        if not isinstance(digest, str) or len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest):
            raise EmbeddingUnavailable('The local embedding model is unavailable.')
        return digest

    def embed(self, text):
        if not isinstance(text, str) or not text.strip() or len(text.encode('utf-8')) > 8192:
            raise ValueError('Enter a non-empty memory/query within 8192 bytes.')
        before = self._digest()
        result = self._request('POST', '/api/embed', {'model': self.model, 'input': text, 'truncate': False, 'keep_alive': '0'})
        try:
            vector = validate_vector(result['embeddings'][0])
        except (KeyError, IndexError, TypeError):
            raise EmbeddingUnavailable('Local embedding response is invalid.') from None
        if self._digest() != before:
            raise EmbeddingUnavailable('Local embedding model changed during processing.')
        return vector, f'{self.model}@{before}'
