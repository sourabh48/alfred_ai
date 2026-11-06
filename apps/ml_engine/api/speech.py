from django.http import HttpResponse
from rest_framework.parsers import BaseParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ..services import speech


class SpeechStatusAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(speech.status())


class WavParser(BaseParser):
    media_type = "audio/wav"

    def parse(self, stream, media_type=None, parser_context=None):
        # Bounded read: the 256 KB form-body limit does not apply to this raw upload.
        return stream.read(speech.MAX_AUDIO_BYTES + 1)


class SpeechTranscribeAPI(APIView):
    """AI-18: turn one button-press recording into text; the audio is not stored."""

    permission_classes = [IsAuthenticated]
    parser_classes = [WavParser]

    def post(self, request):
        if int(request.META.get("CONTENT_LENGTH") or 0) > speech.MAX_AUDIO_BYTES:
            return Response({"detail": f"Recordings are limited to {speech.MAX_SECONDS} seconds."}, status=413)
        try:
            audio = request.data if isinstance(request.data, bytes) else b""
            return Response({"text": speech.transcribe(audio)})
        except speech.SpeechError as error:
            return Response({"detail": str(error)}, status=400)
        except speech.SpeechUnavailable as error:
            return Response({"detail": str(error)}, status=503)


class SpeechSpeakAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            audio = speech.speak(request.data.get("text"))
        except speech.SpeechError as error:
            return Response({"detail": str(error)}, status=400)
        except speech.SpeechUnavailable as error:
            return Response({"detail": str(error)}, status=503)
        response = HttpResponse(audio, content_type="audio/wav")
        response["Cache-Control"] = "no-store"
        return response
