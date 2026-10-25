"""Persisted discovery batches; providers are synthetic, never live inventory."""
from copy import deepcopy
from unittest.mock import patch

from django.test import TestCase, Client

from apps.mobility.models import TravelPlanningSession
from apps.mobility.planner_views import session_payload
from apps.mobility.services.travel_conversation import send_message
from apps.mobility.services.travel_discovery import candidates_for, value
from apps.mobility.services.travel.discovery import remember
from apps.mobility.services.travel_research import run_research
from apps.mobility.services.travel_catalog import DESTINATIONS
from tests import test_travel_planner as fixtures


def synthetic_pool(user, state):
    seeds = [dict(deepcopy(DESTINATIONS[1]), name=f'Synthetic candidate {i:02}',
        source='https://example.invalid/synthetic', lat=13.3+i/100) for i in range(25)]
    return candidates_for(user, state, limit=25, destinations=seeds)


class TravelCandidatePoolTests(TestCase):
    setUp = fixtures.TravelPlannerTests.setUp
    ready = fixtures.TravelPlannerTests.ready

    def researched(self):
        session = self.ready()
        pool = synthetic_pool(self.user, session.state)
        with patch('apps.mobility.services.travel.research.research_candidates', return_value=[pool[0]]+pool):
            self.assertEqual(run_research(session.research_runs.first().pk)['status'], 'ready')
        session.refresh_from_db()
        return session

    def next_batch(self, session, text='Show more destinations'):
        session = send_message(session.pk, self.user, text)
        self.assertEqual(run_research(session.research_runs.first().pk)['status'], 'ready')
        session.refresh_from_db()
        return session

    def test_pool_is_bounded_persisted_and_each_candidate_is_shown_once_per_forward_pass(self):
        session = self.researched()
        self.assertEqual(len(value(session.state, '_destination_pool')), 20)
        names = []
        for page in range(7):
            if page:
                session = self.next_batch(session)
            names.extend(d['name'] for d in session.candidates)
            self.assertLessEqual(len(session.candidates), 3)
            self.assertIsNone(value(session.state, 'selected_destination'))
        self.assertEqual(len(names), 20); self.assertEqual(len(set(names)), 20)
        before = session.research_runs.count()
        session = send_message(session.pk, self.user, 'Show more destinations')
        self.assertEqual(session.research_runs.count(), before)
        self.assertFalse(session_payload(session)['destination_pool']['has_more'])
        session = self.next_batch(session, 'Previous destinations')
        self.assertEqual(value(session.state, '_destination_offset'), 15)

    def test_only_three_candidates_are_enriched_and_internal_pool_is_not_sent_to_browser(self):
        from apps.mobility.services.travel.research import enrich_candidate
        with patch('apps.mobility.services.travel.research.enrich_candidate', wraps=enrich_candidate) as enrich:
            session = self.researched()
        self.assertEqual(enrich.call_count, 3)
        data = session_payload(session)
        self.assertEqual(data['destination_pool']['total'], 20)
        self.assertEqual(len(data['candidates']), 3)
        self.assertNotIn('_destination_pool', data['state'])
        self.assertFalse(data['destination_pool']['has_previous'])
        self.assertTrue(data['destination_pool']['has_more'])

    def test_queued_batch_is_idempotent_and_superseded_worker_cannot_replace_new_request(self):
        session = self.researched()
        session = send_message(session.pk, self.user, 'Show more destinations')
        pending = session.research_runs.first()
        revision = session.revision
        session = send_message(session.pk, self.user, 'Show more destinations')
        self.assertEqual(session.revision, revision)
        self.assertEqual(session.research_runs.first().pk, pending.pk)
        session = send_message(session.pk, self.user, 'Budget 20000')
        self.assertNotIn('_destination_pool', session.state)
        self.assertEqual(run_research(pending.pk)['status'], 'superseded')
        session.refresh_from_db(); self.assertNotIn('_destination_pool', session.state)

    def test_rejection_from_another_session_is_respected_before_next_batch(self):
        session = self.researched()
        rejected = value(session.state, '_destination_pool')[3]
        remember(self.user, rejected, 'rejected')
        session = self.next_batch(session)
        self.assertNotIn(rejected['name'], [d['name'] for d in session.candidates])
        self.assertNotIn(rejected['name'], [d['name'] for d in value(session.state, '_destination_pool')])

    def test_option_numbers_refer_to_current_batch_and_owner_session_csrf_are_required(self):
        session = self.next_batch(self.researched())
        expected = session.candidates[1]['name']
        session = send_message(session.pk, self.user, 'Choose option 2')
        self.assertEqual(value(session.state, 'selected_destination'), expected)
        url = f'/api/mobility/planner/sessions/{session.pk}/'
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.client.post(url, {'text':'Show more destinations'}).status_code, 404)
        self.assertEqual(Client().get(url).status_code, 403)
        client = Client(enforce_csrf_checks=True); client.force_login(self.user)
        self.assertEqual(client.post(url, {'text':'Show more destinations'}).status_code, 403)
        self.assertEqual(TravelPlanningSession.objects.get(pk=session.pk).user_id, self.user.pk)

    def test_rejected_remainder_keeps_last_eligible_batch_and_reports_exhaustion(self):
        session = self.researched()
        first = [d['name'] for d in session.candidates]
        for candidate in value(session.state, '_destination_pool')[3:]:
            remember(self.user, candidate, 'rejected')
        session = self.next_batch(session)
        self.assertEqual([d['name'] for d in session.candidates], first)
        self.assertEqual(session_payload(session)['destination_pool']['total'], 3)
        self.assertFalse(session_payload(session)['destination_pool']['has_more'])
        self.assertIn('No further eligible batch', session.research_runs.first().summary)
