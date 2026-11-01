"""Model files stay local, and loading one must not run code embedded in it."""
import os
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from apps.ml_engine.inference_adapters import relationship_siamese, transaction_classifier as classifier_module
from apps.ml_engine.inference_adapters.transaction_classifier import TransactionClassifierAdapter


class OfflineDefaultTests(SimpleTestCase):
    def test_model_libraries_stay_offline_without_telemetry(self):
        for name in ("HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE", "HF_HUB_DISABLE_TELEMETRY"):
            with self.subTest(name=name):
                self.assertEqual(os.environ[name], "1")


class TransactionClassifierLoadingTests(SimpleTestCase):
    def load_with(self, side_effect=None):
        adapter = TransactionClassifierAdapter()
        model = MagicMock()
        with patch.object(classifier_module, "SENTENCE_TRANSFORMERS_AVAILABLE", True), \
                patch.object(classifier_module, "SentenceTransformer", return_value=model, side_effect=side_effect, create=True) as build, \
                patch.object(adapter, "_offline_model_loading_disabled", return_value=False), \
                patch.object(adapter, "_precompute_category_embeddings"):
            adapter.load()
        return adapter, build

    def test_a_normal_run_never_downloads_the_model(self):
        _, build = self.load_with()
        self.assertIs(build.call_args.kwargs["local_files_only"], True)
        self.assertNotIn("trust_remote_code", build.call_args.kwargs)

    def test_a_missing_local_model_falls_back_to_rules(self):
        adapter, _ = self.load_with(side_effect=OSError("not cached"))
        self.assertIsNone(adapter.model)
        self.assertEqual(adapter.predict("UPI-SWIGGY-FOOD ORDER-12345", "debit")["payment_mode"], "UPI")


class SiameseLoadingTests(SimpleTestCase):
    def test_the_state_dict_loads_tensors_only(self):
        with patch.object(relationship_siamese.torch, "load", return_value={}) as loader, \
                patch.object(relationship_siamese.SiameseNet, "load_state_dict"):
            relationship_siamese.RelationshipSiameseAdapter().load()
        self.assertIs(loader.call_args.kwargs["weights_only"], True)
