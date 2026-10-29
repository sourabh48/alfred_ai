"""Bound client-controlled work before DRF decodes bodies or negotiates media."""
import codecs
from django.conf import settings
from rest_framework.exceptions import NotAcceptable, ParseError
from rest_framework.negotiation import DefaultContentNegotiation
from rest_framework.parsers import JSONParser


class TextJSONParser(JSONParser):
    def parse(self, stream, media_type=None, parser_context=None):
        encoding = (parser_context or {}).get("encoding", settings.DEFAULT_CHARSET)
        try:
            # Empty bytes.decode() can skip codec validation; inspect the codec itself.
            if not codecs.lookup(encoding)._is_text_encoding:
                raise LookupError()
        except (LookupError, TypeError):
            raise ParseError("JSON requires a supported text encoding.") from None
        return super().parse(stream, media_type, parser_context)


class BoundedContentNegotiation(DefaultContentNegotiation):
    def get_accept_list(self, request):
        header = request.META.get("HTTP_ACCEPT", "*/*")
        if len(header) > 8192 or header.count(",") >= 64:
            raise NotAcceptable("Accept header exceeds supported negotiation limits.")
        return super().get_accept_list(request)
