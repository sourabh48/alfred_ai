import os
from pathlib import Path
import threading
import unittest
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.core.cache import cache
from django.core.handlers.base import BaseHandler
from django.utils import timezone

from apps.mobility.models import TravelPlan
from apps.mobility.services.travel_research import run_research
from apps.mobility.services.travel.cache import query
from apps.mobility.services.travel.providers.base import ProviderResult
from tests.test_travel_planner import weather_fixture
from tests import test_document_review_browser as browser_support
from scripts.exercise_materialized_cache_traffic import _offline_fixture_patches


@unittest.skipUnless(browser_support.RUN_BROWSER_TESTS, "Set ALFRED_RUN_BROWSER_TESTS=true.")
class TravelPlannerBrowserTests(StaticLiveServerTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        from selenium import webdriver
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        cls.By = By
        cls.browser = browser_support.DocumentReviewBrowserTests._create_driver(webdriver)
        cls.wait = WebDriverWait(cls.browser, 25)
        cls.pending = 0
        cls.lock = threading.Lock()
        original = BaseHandler.get_response
        def tracked(handler, request):
            with cls.lock: cls.pending += 1
            try: return original(handler, request)
            finally:
                with cls.lock: cls.pending -= 1
        tracker = patch.object(BaseHandler, "get_response", tracked)
        tracker.start(); cls.addClassCleanup(tracker.stop)

    @classmethod
    def tearDownClass(cls):
        if getattr(cls, "browser", None): cls.browser.quit()
        super().tearDownClass()

    def setUp(self):
        self.browser.execute_cdp_cmd("Emulation.clearDeviceMetricsOverride", {})
        self.browser.set_window_size(1440, 1100)
        cache.clear()
        self.offline = _offline_fixture_patches()
        self.addCleanup(self.offline.close)
        self.user = get_user_model().objects.create_user("planner_browser",password="Test12345!",city="Bengaluru")
        self.client.force_login(self.user)
        def route_fixture(provider, parameters, **kwargs):
            if provider.category != "routing":
                return query(provider, parameters, **kwargs)
            now = timezone.now()
            return ProviderResult(provider.name, provider.category, success=True, status="ok", freshness="LIVE",
                confidence="LIKELY", source_url="https://openrouteservice.org/", retrieved_at=now.isoformat(),
                expires_at=(now+timedelta(days=1)).isoformat(), payload={"routes":[{
                    "distance_km":250, "duration_hours":5,
                    "geometry":{"type":"LineString", "coordinates":[parameters["start"],parameters["end"]]}}]})
        for target, kw in [
            ("apps.mobility.services.travel_research.dispatch", {"side_effect":run_research}),
            ("apps.mobility.services.travel.research.weather_result", {"side_effect":weather_fixture}),
            ("apps.mobility.services.travel.research.query", {"side_effect":route_fixture}),
            ("apps.mobility.services.travel.providers.base.request", {"side_effect":AssertionError("Browser tests must mock providers")}),
            ("apps.mobility.planner_views.map_configuration", {"return_value":{"provider":"openstreetmap","tile_url":"","attribution":"Fixture map","attribution_url":"https://www.openstreetmap.org/copyright"}}),
            ("apps.mobility.services.travel.providers.web.WikivoyageDestinations.fetch", {"return_value":({"query":{"pages":[
                {"pageid":42,"ns":0,"title":"Talakadu","coordinates":[{"lat":12.18,"lon":77.03}]},
                {"pageid":43,"ns":0,"title":"Chikmagalur","coordinates":[{"lat":13.32,"lon":75.77}]},
                {"pageid":44,"ns":0,"title":"Belur","coordinates":[{"lat":13.16,"lon":75.87}]}]}},"fixture-hash")})]:
            p=patch(target,**kw);p.start();self.addCleanup(p.stop)
        self.browser.get(self.live_server_url+"/login/")
        self.browser.add_cookie({"name":"sessionid","value":self.client.cookies["sessionid"].value,"path":"/"})
        self.artifacts=Path(os.environ.get("ALFRED_BROWSER_ARTIFACT_DIR","artifacts/browser"))/"travel-planner"
        self.artifacts.mkdir(parents=True,exist_ok=True)

    def tearDown(self):
        import json
        self.browser.save_screenshot(str(self.artifacts/(self._testMethodName+".png")))
        (self.artifacts/(self._testMethodName+"-console.json")).write_text(json.dumps(self.browser.get_log("browser"),indent=2),encoding="utf-8")
        self.browser.get("about:blank")
        self.wait.until(lambda _: self.pending == 0)
        super().tearDown()

    def text(self, ident): return self.browser.find_element(self.By.ID,ident).text

    def test_route_comparison_choice_rebuild_retry_expiry_and_reopen(self):
        from apps.mobility.models import TravelPlanningSession
        from apps.mobility.services.travel.providers.routing import OpenRouteService
        from apps.expenses.models import BankAccount, Expense
        from apps.investments.models import Investment
        from apps.loans.models import Loan
        from django.http import JsonResponse
        import json

        financial_before = [list(model.objects.values()) for model in (BankAccount, Expense, Investment, Loan)]
        def compared(provider, params, **kwargs):
            if provider.category != "routing": return query(provider, params, **kwargs)
            points = [params["start"], params["end"]]
            middle = [(points[0][0]+points[1][0])/2+0.05, (points[0][1]+points[1][1])/2]
            features = [{"geometry": {"type": "LineString", "coordinates": points},
                "properties": {"summary": {"distance": 80000, "duration": 7200}}}]
            if params.get("alternatives"):
                features.append({"geometry": {"type": "LineString", "coordinates": [points[0], middle, points[1]]},
                    "properties": {"summary": {"distance": 90000, "duration": 10800}}})
            now = timezone.now()
            return ProviderResult(provider.name, provider.category, success=True, status="ok", freshness="LIVE", confidence="LIKELY",
                source_url="https://openrouteservice.org/", retrieved_at=now.isoformat(), expires_at=(now+timedelta(days=1)).isoformat(),
                payload=OpenRouteService().normalize({"features": features}, params))

        with patch("apps.mobility.services.travel.research.query", side_effect=compared):
            self.browser.get(self.live_server_url+"/mobility/")
            self.wait.until(lambda _: "destination is optional" in self.text("plannerMessages"))
            start, end = timezone.localdate()+timedelta(days=2), timezone.localdate()+timedelta(days=4)
            self.send(f"3-day motorcycle trip from {start} to {end}. Budget 15000. Suggest me somewhere.")
            self.wait.until(lambda _: len(self.browser.find_elements(self.By.CSS_SELECTOR, ".travel-candidate")) == 3 and "Talakadu" in self.text("plannerCandidates"))
            panel = '[data-destination="Talakadu"] .travel-route-choices'
            def open_routes():
                if not self.browser.find_element(self.By.CSS_SELECTOR, panel).get_attribute("open"):
                    self.click(panel+" > summary")
            open_routes()
            self.wait.until(lambda _: "Route 2" in self.browser.find_element(self.By.CSS_SELECTOR, panel).text)
            self.assertIn("motorcycle legality", self.browser.find_element(self.By.CSS_SELECTOR, panel).text.lower())
            original = BaseHandler.get_response
            failed = []
            def unavailable(handler, request):
                if (not failed and request.method == "POST" and "/planner/sessions/" in request.path
                        and json.loads(request.body).get("action") == "route_choice"):
                    failed.append(True)
                    return JsonResponse({"detail": "Route choice temporarily unavailable; retry."}, status=503)
                return original(handler, request)
            with patch.object(BaseHandler, "get_response", unavailable):
                self.click(panel+' > div:nth-of-type(2) button[data-route-choice]')
                self.wait.until(lambda _: "temporarily unavailable" in self.text("plannerAlert"))
                self.assertTrue(self.browser.find_element(self.By.CSS_SELECTOR, panel+' > div:nth-of-type(2) button[data-route-choice]').is_enabled())
                self.click(panel+' > div:nth-of-type(2) button[data-route-choice]')
                self.wait.until(lambda _: self.browser.find_element(self.By.ID, "plannerSend").is_enabled() and not self.text("plannerAlert"))
            open_routes()
            self.assertIn("Route 2", self.browser.find_element(self.By.CSS_SELECTOR, panel).text)
            self.assertFalse(self.browser.find_element(self.By.CSS_SELECTOR, panel+' > div:nth-of-type(2) button[data-route-choice]').is_enabled())
            self.browser.save_screenshot(str(self.artifacts/"route-choice-desktop.png"))
            self.click('[data-planner-message="Choose Talakadu"]')
            self.wait.until(lambda _: self.browser.find_elements(self.By.CSS_SELECTOR, '#plannerChips [data-planner-message="Build itinerary"]'))
            self.click('#plannerChips [data-planner-message="Build itinerary"]')
            self.wait.until(lambda _: len(self.browser.find_elements(self.By.CSS_SELECTOR, ".travel-day")) == 3)
            self.browser.execute_script("arguments[0].scrollIntoView({block:'center',behavior:'instant'});", self.browser.find_element(self.By.ID, "plannerItinerary"))
            self.wait.until(lambda _: "~3.0 hours per leg" in self.text("plannerItinerary"))
            self.click("#plannerSave")
            self.wait.until(lambda _: "Travel Plan saved." in self.text("plannerAlert"))
            session = TravelPlanningSession.objects.get(user=self.user)
            chosen = next(c for c in session.candidates if c["name"] == "Talakadu")
            self.assertEqual(session.itinerary["route"]["selected_route_id"], chosen["selected_route_id"])
            before_expiry = session.itinerary
            chosen["route_result"]["expires_at"] = (timezone.now()-timedelta(seconds=1)).isoformat()
            session.save(update_fields=["candidates"])
            open_routes()
            self.click(panel+' > div:nth-of-type(1) button[data-route-choice]')
            self.wait.until(lambda _: "expired" in self.text("plannerAlert"))
            session.refresh_from_db()
            self.assertEqual(session.itinerary, before_expiry)
            self.browser.refresh()
            self.wait.until(lambda _: "Talakadu" in self.text("plannerCandidates"))
            open_routes()
            self.assertIn("Recheck Trip before choosing", self.browser.find_element(self.By.CSS_SELECTOR, panel).text)
            self.assertTrue(all(not b.is_enabled() for b in self.browser.find_elements(self.By.CSS_SELECTOR, panel+' button[data-route-choice]')))
            self.browser.execute_cdp_cmd("Emulation.setDeviceMetricsOverride", {"width":390,"height":844,"deviceScaleFactor":1,"mobile":False})
            self.browser.execute_script("arguments[0].scrollIntoView({block:'start',behavior:'instant'});", self.browser.find_element(self.By.CSS_SELECTOR, panel))
            self.browser.save_screenshot(str(self.artifacts/"route-choice-narrow.png"))
            self.assertLessEqual(self.browser.execute_script("return document.documentElement.scrollWidth"), 390)
        self.assertEqual([list(model.objects.values()) for model in (BankAccount, Expense, Investment, Loan)], financial_before)

    def send(self,text):
        self.wait.until(lambda _: self.browser.find_element(self.By.ID,"plannerSend").is_enabled())
        input=self.browser.find_element(self.By.ID,"plannerInput")
        input.clear();input.send_keys(text)
        self.click("#plannerSend")
        self.wait.until(lambda _: text in self.text("plannerMessages") and self.browser.find_element(self.By.ID,"plannerSend").is_enabled())

    def click(self,selector):
        element=self.browser.find_element(self.By.CSS_SELECTOR,selector)
        self.wait.until(lambda _: element.is_enabled())
        # WebDriver also scrolls before a native click; its scroll must finish
        # immediately instead of racing the main panel's smooth scrolling.
        self.browser.execute_script("const main=arguments[0].closest('.alfred-main');if(main)main.style.scrollBehavior='auto';arguments[0].scrollIntoView({block:'center',behavior:'instant'});",element)
        self.wait.until(lambda _: self.browser.execute_script("const e=arguments[0],r=e.getBoundingClientRect(),h=document.elementFromPoint(r.x+r.width/2,r.y+r.height/2);return h===e||e.contains(h);",element))
        element.click()

    def test_pending_action_disables_suggestions_until_response_finishes(self):
        self.browser.get(self.live_server_url+'/mobility/')
        self.wait.until(lambda _: 'destination is optional' in self.text('plannerMessages'))
        self.wait.until(lambda _: self.text('plannerPlans').strip() and self.pending==0)
        entered, release = threading.Event(), threading.Event()
        original = BaseHandler.get_response

        def delayed_list(handler,request):
            response=original(handler,request)
            if request.method=='GET' and request.path=='/api/mobility/planner/sessions/':
                entered.set(); release.wait(timeout=10)
            return response

        with patch.object(BaseHandler,'get_response',delayed_list):
            try:
                self.browser.find_element(self.By.ID,'plannerInput').send_keys('3-day quiet trip. Budget 15000.')
                self.click('#plannerSend')
                self.wait.until(lambda _: entered.is_set())
                self.assertFalse(self.browser.find_element(self.By.ID,'plannerSend').is_enabled())
                suggestions=self.browser.find_elements(self.By.CSS_SELECTOR,'[data-planner-message]')
                self.assertTrue(suggestions)
                self.assertTrue(all(not button.is_enabled() for button in suggestions))
                self.assertFalse(self.browser.find_element(self.By.ID,'plannerNew').is_enabled())
            finally:
                release.set()
            self.wait.until(lambda _: self.browser.find_element(self.By.ID,'plannerSend').is_enabled())
            self.assertTrue(all(button.is_enabled() for button in self.browser.find_elements(self.By.CSS_SELECTOR,'[data-planner-message]')))

    def test_chat_to_saved_plan_desktop_and_mobile(self):
        self.browser.set_window_size(1440,1100)
        self.browser.get(self.live_server_url+"/mobility/")
        self.wait.until(lambda _: "destination is optional" in self.text("plannerMessages"))
        self.assertFalse(self.browser.find_element(self.By.ID,"travelPlanForm").is_displayed())
        self.assertEqual(self.browser.find_element(self.By.ID,"plannerInput").tag_name,"input")
        self.send("I have holiday from 2 October to 5 October. Budget is ₹15,000. Suggest me somewhere.")
        self.wait.until(lambda _: len(self.browser.find_elements(self.By.CSS_SELECTOR,".travel-candidate"))==3 and "Talakadu" in self.text("plannerCandidates"))
        self.assertIn("Talakadu",self.text("plannerCandidates"))
        self.assertNotIn("Use that?",self.text("plannerMessages"))
        self.assertIn("15,000",self.text("plannerContext"))
        self.click("#plannerCompare")
        self.wait.until(lambda _: "Expected budget" in self.text("plannerComparison"))
        self.assertIn("Expected budget",self.text("plannerComparison"))
        self.browser.save_screenshot(str(self.artifacts/"desktop-comparison.png"))
        self.wait.until(lambda _: self.browser.find_element(self.By.ID,"plannerSend").is_enabled())
        self.click('[data-planner-message="Choose Chikmagalur"]')
        self.wait.until(lambda _: self.browser.find_elements(self.By.CSS_SELECTOR,'#plannerChips [data-planner-message="Build itinerary"]'))
        self.click('#plannerChips [data-planner-message="Build itinerary"]')
        self.wait.until(lambda _: len(self.browser.find_elements(self.By.CSS_SELECTOR,".travel-day"))==4)
        self.send("Show cheaper hotels")
        # The POST queues work on commit; wait for its polled result before
        # comparing day edits with the latest researched allowances.
        self.wait.until(lambda _: self.text("plannerResearch").startswith("Ready"))
        self.wait.until(lambda _: "Booking.com" in self.text("plannerEvidenceBody"))
        self.assertIn("Live stay pricing/availability could not be retrieved",self.text("plannerEvidenceBody"))
        self.assertIn("Search link — open to check latest availability.",self.text("plannerEvidenceBody"))
        self.assertTrue(self.browser.execute_script("return [...document.querySelectorAll('#plannerEvidence a[target=\"_blank\"]')].every(a=>a.rel.includes('noopener')&&a.rel.includes('noreferrer')&&a.protocol==='https:')"))
        self.click("#plannerLoadMap")
        self.wait.until(lambda _: self.browser.find_elements(self.By.CSS_SELECTOR,'#plannerMap .leaflet-overlay-pane path[fill="none"]'))
        self.assertIn("Map tiles are disabled",self.text("plannerMapStatus"))
        self.assertFalse(self.browser.find_elements(self.By.CSS_SELECTOR,"#plannerMap img.leaflet-tile"))
        self.assertTrue(self.browser.execute_script("return [...document.querySelectorAll('#plannerMap path:not([fill=\"none\"])')].every(p=>p.getBoundingClientRect().width<=20)"))
        self.browser.save_screenshot(str(self.artifacts/"research-map-desktop.png"))
        first=self.browser.find_element(self.By.CSS_SELECTOR,'[data-day="1"]').text
        self.send("Day 2 is too busy. Make it relaxed.")
        self.assertIn("relaxed",self.browser.find_element(self.By.CSS_SELECTOR,'[data-day="2"]').text)
        self.assertIn("Booking.com",self.text("plannerEvidenceBody"))
        self.assertEqual(first,self.browser.find_element(self.By.CSS_SELECTOR,'[data-day="1"]').text)
        self.click("#plannerSave")
        self.wait.until(lambda _: TravelPlan.objects.filter(user=self.user,status="planned").exists())
        self.wait.until(lambda _: "Travel Plan saved" in self.text("plannerAlert"))
        url=self.browser.current_url
        self.browser.get(url)
        self.wait.until(lambda _: len(self.browser.find_elements(self.By.CSS_SELECTOR,".travel-day"))==4)
        self.assertIn("relaxed",self.browser.find_element(self.By.CSS_SELECTOR,'[data-day="2"]').text)
        for width in (390,768):
            self.browser.set_window_size(width,1000)
            self.browser.execute_cdp_cmd("Emulation.setDeviceMetricsOverride",{"width":width,"height":1000,"deviceScaleFactor":1,"mobile":True})
            self.assertEqual(self.browser.execute_script("return innerWidth"),width)
            self.assertTrue(self.browser.execute_script("return document.documentElement.scrollWidth <= innerWidth+1"),f"overflow at {width}")
            self.browser.execute_script("document.getElementById('travelPlanner').scrollIntoView({behavior:'instant'})")
            self.browser.save_screenshot(str(self.artifacts/f"chat-{width}.png"))
        errors=[x for x in self.browser.get_log("browser") if x["level"]=="SEVERE" and ("TypeError" in x["message"] or "SyntaxError" in x["message"])]
        self.assertEqual(errors,[])

    def test_staff_provider_configuration_panel(self):
        self.user.is_staff = True
        self.user.save(update_fields=["is_staff"])
        self.browser.get(self.live_server_url+"/mobility/")
        self.wait.until(lambda _: "destination is optional" in self.text("plannerMessages"))
        self.send("3-day bike trip. Budget 15000.")
        self.wait.until(lambda _: self.text("plannerResearch").startswith("Ready"))
        self.click("#plannerQuota summary")
        self.click("#plannerLoadQuota")
        self.wait.until(lambda _: "brave · web" in self.text("plannerQuotaBody"))
        self.assertIn("wikivoyage · destinations",self.text("plannerQuotaBody"))
        self.assertIn("duffel · flights",self.text("plannerQuotaBody"))

    def test_date_change_keeps_edited_days_and_does_not_resurrect_old_forecast(self):
        self.browser.get(self.live_server_url + "/mobility/")
        self.wait.until(lambda _: "destination is optional" in self.text("plannerMessages"))
        self.send("Plan a 3-day bike trip from Bengaluru to Coorg. Budget 15000.")
        self.wait.until(lambda _: len(self.browser.find_elements(self.By.CSS_SELECTOR, ".travel-day")) == 3)
        self.send("Make day 2 relaxed")
        start = timezone.localdate() + timedelta(days=5)
        self.send(f"{start} to {start + timedelta(days=2)}")
        self.assertIn("Dates changed. Recheck weather", self.text("plannerItinerary"))
        self.assertIn(str(start), self.browser.find_element(self.By.CSS_SELECTOR, '[data-day="1"]').text)
        self.assertIn("relaxed", self.browser.find_element(self.By.CSS_SELECTOR, '[data-day="2"]').text)
        self.send("Build itinerary")
        self.assertIn("Dates changed. Recheck weather", self.text("plannerItinerary"))
        self.assertIn("Recheck needed", self.text("plannerResearch"))
        self.assertNotIn("current weather forecast(s) available", self.text("plannerResearch"))
        self.browser.execute_script("document.getElementById('plannerItinerary').scrollIntoView({block:'start',behavior:'instant'})")
        self.browser.save_screenshot(str(self.artifacts / "changed-dates-no-old-forecast.png"))

    def test_quick_ideas_draft_and_preferences(self):
        self.browser.set_window_size(390,1000)
        self.browser.execute_cdp_cmd("Emulation.setDeviceMetricsOverride",{"width":390,"height":1000,"deviceScaleFactor":1,"mobile":True})
        self.browser.get(self.live_server_url+"/mobility/")
        self.wait.until(lambda _: self.browser.find_elements(self.By.CSS_SELECTOR,'[data-planner-message="3-day bike trip"]'))
        self.click('[data-planner-message="3-day bike trip"]')
        self.wait.until(lambda _: "Days available" in self.text("plannerContext"))
        self.wait.until(lambda _: self.browser.find_element(self.By.ID,"plannerSend").is_enabled())
        self.click("#plannerDraft")
        self.wait.until(lambda _: TravelPlan.objects.filter(user=self.user,status="draft",destination=None).exists())
        self.browser.get(self.live_server_url+"/settings/#travelPreferences")
        self.wait.until(lambda _: self.browser.find_element(self.By.ID,"travelPreferenceForm").is_displayed())
        self.click('#travelPreferenceForm button[type="submit"]')
        self.wait.until(lambda _: "mountains: true" in self.text("travelPreferenceList"))
        self.assertTrue(self.browser.execute_script("return document.documentElement.scrollWidth <= innerWidth+1"))

    def test_preferences_wait_for_initial_load_and_save(self):
        reading, release_read, writing, release_write = (threading.Event() for _ in range(4))
        original = BaseHandler.get_response
        def delayed(handler, request):
            response = original(handler, request)
            if request.path == '/api/mobility/planner/preferences/':
                entered, release = (reading, release_read) if request.method == 'GET' else (writing, release_write)
                entered.set()
                release.wait(timeout=10)
            return response
        with patch.object(BaseHandler, 'get_response', delayed):
            try:
                self.browser.get(self.live_server_url + '/settings/#travelPreferences')
                self.wait.until(lambda _: reading.is_set())
                button = self.browser.find_element(self.By.CSS_SELECTOR, '#travelPreferenceForm button[type="submit"]')
                self.assertFalse(button.is_enabled())
                self.assertEqual(self.browser.find_element(self.By.ID, 'travelPreferences').get_attribute('aria-busy'), 'true')
                release_read.set()
                self.wait.until(lambda _: button.is_enabled())
                self.click('#travelPreferenceForm button[type="submit"]')
                self.wait.until(lambda _: writing.is_set())
                self.assertFalse(button.is_enabled())
                self.assertFalse(self.browser.find_element(self.By.ID, 'travelLearning').is_enabled())
                self.assertFalse(self.browser.find_element(self.By.ID, 'travelResetPreferences').is_enabled())
                release_write.set()
                self.wait.until(lambda _: 'mountains: true' in self.text('travelPreferenceList'))
                self.wait.until(lambda _: button.is_enabled())
                self.assertEqual(self.browser.find_element(self.By.ID, 'travelPreferences').get_attribute('aria-busy'), 'false')
            finally:
                release_read.set()
                release_write.set()

    def test_preferences_load_failure_does_not_enable_unknown_privacy_controls(self):
        from django.http import JsonResponse
        original = BaseHandler.get_response
        def unavailable(handler, request):
            if request.method == 'GET' and request.path == '/api/mobility/planner/preferences/':
                return JsonResponse({'detail': 'Preference service unavailable.'}, status=503)
            return original(handler, request)
        with patch.object(BaseHandler, 'get_response', unavailable):
            self.browser.get(self.live_server_url + '/settings/#travelPreferences')
            self.wait.until(lambda _: 'Preference service unavailable.' in self.text('travelPreferencesAlert'))
            self.assertFalse(self.browser.find_element(self.By.ID, 'travelLearning').is_enabled())
            self.assertFalse(self.browser.find_element(self.By.ID, 'travelMediaLearning').is_enabled())
            self.assertFalse(self.browser.find_element(self.By.ID, 'travelResetPreferences').is_enabled())
            self.assertEqual(self.browser.find_element(self.By.ID, 'travelPreferences').get_attribute('aria-busy'), 'false')
