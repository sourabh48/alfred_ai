"""Explicit developer diagnostic; never accepts user context or participates in fallback."""
import os
import sys
import time

from django.conf import settings

from alfred_ai.services.public_http import PublicHTTPError, request
from .memory_sync import SyncUnavailable

MODEL = 'gemini-3.8-flash'
PROMPT = 'Synthetic connectivity test. Reply with exactly ALFRED_GEMINI_OK.'
PAYLOAD = {'query': PROMPT, 'memories': []}


class GeminiDevelopmentReasoner:
    name = 'gemini'

    def reason(self, payload, *, max_output_tokens, deadline):
        if not settings.ALFRED_GEMINI_DEV_ENABLED:
            raise SyncUnavailable('disabled')
        if not settings.DEBUG or getattr(sys, 'frozen', False):
            raise SyncUnavailable('not_development')
        if payload != PAYLOAD:
            raise SyncUnavailable('synthetic_only')
        if type(max_output_tokens) is not int or not 1 <= max_output_tokens <= 256:
            raise SyncUnavailable('invalid_budget')
        key = os.environ.get('GEMINI_API_KEY', '')
        if not key or len(key) > 512 or any(ord(c) <= 32 or ord(c) >= 127 for c in key):
            raise SyncUnavailable('missing_or_invalid_key')
        try:
            response = request('POST', f'https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent',
                headers={'x-goog-api-key': key}, json_body={
                    'contents': [{'role': 'user', 'parts': [{'text': PROMPT}]}],
                    'generationConfig': {'maxOutputTokens': max_output_tokens, 'candidateCount': 1,
                        'thinkingConfig': {'thinkingLevel': 'LOW'}}},
                max_bytes=16384, deadline=min(deadline, time.monotonic()+15))
            data = response.json()
            candidates = data['candidates']
            if data.get('promptFeedback', {}).get('blockReason') or len(candidates) != 1:
                raise ValueError()
            candidate = candidates[0]
            parts = candidate['content']['parts']
            if (candidate.get('finishReason') != 'STOP' or candidate['content'].get('role') != 'model'
                    or not isinstance(parts, list) or not 1 <= len(parts) <= 8):
                raise ValueError()
            text = []
            for part in parts:
                if not isinstance(part, dict) or not isinstance(part.get('text'), str) or set(part)-{'text', 'thought', 'thoughtSignature'}:
                    raise ValueError()
                if not part.get('thought'):
                    text.append(part['text'])
            if ''.join(text).strip() != 'ALFRED_GEMINI_OK':
                raise ValueError()
        except PublicHTTPError as exc:
            reason = exc.code if exc.code in {'timeout', 'quota_exhausted', 'authorization_failed'} else 'provider_unavailable'
            raise SyncUnavailable(reason) from None
        except (AttributeError, KeyError, TypeError, ValueError):
            raise SyncUnavailable('invalid_response') from None
        return 'ALFRED_GEMINI_OK'


def smoke_test(payload):
    result = {'provider': 'gemini', 'model': MODEL, 'synthetic_only': True}
    if payload != {}:
        return {**result, 'status': 'unavailable', 'reason': 'synthetic_only'}
    try:
        GeminiDevelopmentReasoner().reason(PAYLOAD, max_output_tokens=256, deadline=time.monotonic()+15)
    except SyncUnavailable as exc:
        return {**result, 'status': 'unavailable', 'reason': str(exc)}
    return {**result, 'status': 'ok'}
