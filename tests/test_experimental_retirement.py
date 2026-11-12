import importlib
import importlib.util
from pathlib import Path

from django.test import SimpleTestCase
from django.urls import Resolver404, resolve

from apps.investments.services.portfolio_intelligence import portfolio_intelligence_service
from apps.ml_engine.api import views


class ExperimentalRetirementTests(SimpleTestCase):
    def test_packaged_module_inventory_has_no_unrouted_experimental_processors(self):
        root = Path(__file__).resolve().parents[1]
        modules = {".".join(p.relative_to(root).with_suffix("").parts)
                   for p in (root / "apps").rglob("*.py") if "__pycache__" not in p.parts}
        self.assertFalse(any(name.startswith("apps.ml_engine.self_improve.") for name in modules))
        self.assertNotIn("apps.ml_engine.services.voice_assistant", modules)
        self.assertIn("apps.ml_engine.services.hybrid_intelligence", modules)
        self.assertIn("apps.ml_engine.training.orchestrator", modules)

    def test_retired_prototype_is_not_a_callable_or_routed_api(self):
        self.assertFalse(hasattr(views, "SelfImproveAPI"))
        with self.assertRaises(Resolver404):
            resolve("/api/ai/self-improve/")

    def test_unreachable_mail_scanning_is_removed(self):
        self.assertIsNone(importlib.util.find_spec("apps.integrations.services.email_integration"))
        self.assertFalse(hasattr(portfolio_intelligence_service, "scrape_email_for_investments"))
        self.assertIsNone(importlib.util.find_spec("apps.ml_engine.training.train_rl_agent"))

