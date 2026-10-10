from pathlib import Path
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import path

from alfred_ai.native_views import private_media
from alfred_ai.urls import urlpatterns as application_urls
from alfred_ai.services.upload_privacy import purge_uploaded_file_after_extraction
from apps.career.models import CareerResume


urlpatterns = [path('media/<path:path>', private_media)] + application_urls


@override_settings(ROOT_URLCONF=__name__)
class RetentionReleaseBoundaryTests(TestCase):
    def setUp(self):
        directory = self.enterContext(TemporaryDirectory(prefix='alfred-retention-boundary-'))
        self.enterContext(override_settings(MEDIA_ROOT=directory))
        self.owner = get_user_model().objects.create_user(username='synthetic-vault-owner')
        self.other = get_user_model().objects.create_user(username='synthetic-vault-other')
        self.document = CareerResume.objects.create(user=self.owner, file_name='synthetic.pdf',
            uploaded_file=SimpleUploadedFile('synthetic.pdf', b'synthetic protected evidence'), parser_status='needs_review')
        self.url = self.document.uploaded_file.url

    def test_retained_native_source_requires_exact_owner(self):
        self.assertEqual(self.client.get(self.url).status_code, 302)
        other = Client()
        other.force_login(self.other)
        self.assertEqual(other.get(self.url).status_code, 404)
        self.client.force_login(self.owner)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(b''.join(response.streaming_content), b'synthetic protected evidence')
        response.close()
        self.assertEqual(response['Cache-Control'], 'private, no-store')

    def test_native_media_traversal_and_unknown_file_are_rejected(self):
        self.client.force_login(self.owner)
        self.assertEqual(self.client.get('/media/../private.db').status_code, 404)
        self.assertEqual(self.client.get('/media/unregistered.pdf').status_code, 404)

    def test_retaining_review_source_preserves_file_and_record(self):
        before = CareerResume.objects.values().get(pk=self.document.pk)
        with override_settings(ALFRED_DELETE_SOURCE_UPLOADS_AFTER_EXTRACTION=False):
            result = purge_uploaded_file_after_extraction(self.document, 'uploaded_file', reason='review_pending')
        self.assertFalse(result['deleted'])
        self.assertEqual(CareerResume.objects.values().get(pk=self.document.pk), before)
        self.assertTrue(Path(self.document.uploaded_file.path).exists())
