"""Owned saved-trip, read-only scenario API and exact evidence invalidation."""
from copy import deepcopy
from unittest.mock import patch

from django.contrib.sessions.models import Session
from django.core.cache import cache
from django.db import connection
from django.test import Client, TestCase

from apps.expenses.models import BankAccount
from apps.mobility.models import TravelPlan, TravelPlanningSession
from tests import test_travel_affordability as fixtures


class TravelAffordabilityUITests(TestCase):
    def setUp(self):
        cache.clear();self.addCleanup(cache.clear)
        fixtures.TravelAffordabilityTests.setUp(self)
        self.client.force_login(self.user)
        self.plan=TravelPlan.objects.create(user=self.user,title='Synthetic <trip>',budget='400',
            itinerary={'budget':{'expected':'400.005','currency':'USD','scope':'whole_trip','freshness':'ESTIMATED'}})
        self.session=TravelPlanningSession.objects.create(user=self.user,plan=self.plan,title='Synthetic <trip>')
        self.url=f'/api/mobility/planner/sessions/{self.session.pk}/affordability/'

    confirmation=fixtures.TravelAffordabilityTests.confirmation

    def payload(self):
        source=self.client.get(self.url).json()
        return dict(revision=source['trip']['revision'],snapshot=source['trip']['snapshot'],confirmation=self.confirmation())

    def post(self,payload):
        return self.client.post(self.url,payload,content_type='application/json')

    def test_saved_context_is_private_exact_and_estimate_never_infers_financial_currency(self):
        response=self.client.get(self.url)
        self.assertEqual(response.status_code,200)
        self.assertEqual(response['Cache-Control'],'no-store, private')
        data=response.json()
        self.assertEqual(data['trip']['estimate'],dict(amount='400.01',currency='USD',kind='ESTIMATED_NOT_VERIFIED'))
        self.assertNotIn('currency',data['source'])
        self.assertNotIn('account_number',str(data))
        self.assertEqual(data['source']['period'],'one_month')

    def test_all_four_statuses_are_explicit_and_uncertified(self):
        for cost,label in (('400','Affordable'),('500','Tight'),('500.01','Over Budget')):
            payload=self.payload();payload['confirmation']['trip_budget']['amount']=cost
            result=self.post(payload)
            self.assertEqual(result.status_code,200,result.content[:300])
            self.assertEqual(result.json()['label'],label)
            self.assertFalse(result.json()['certified'])
        payload=self.payload();payload['confirmation']['complete']=False
        self.assertEqual(self.post(payload).json()['label'],'Insufficient Data')

    def test_authentication_cross_owner_and_unsaved_trip(self):
        payload=self.payload();self.client.force_login(self.other)
        self.assertEqual(self.client.get(self.url).status_code,404)
        self.assertEqual(self.post(payload).status_code,404)
        self.client.logout()
        self.assertIn(self.client.get(self.url).status_code,(401,403))
        self.assertIn(self.post(payload).status_code,(401,403))
        self.client.force_login(self.user)
        other=TravelPlanningSession.objects.create(user=self.user,title='Unsaved')
        self.assertEqual(self.client.get(f'/api/mobility/planner/sessions/{other.pk}/affordability/').status_code,400)

    def test_csrf_and_revoked_session_fail_closed(self):
        client=Client(enforce_csrf_checks=True);client.force_login(self.user)
        payload=self.payload()
        self.assertEqual(client.post(self.url,payload,content_type='application/json').status_code,403)
        Session.objects.filter(session_key=self.client.session.session_key).delete()
        self.assertIn(self.post(payload).status_code,(401,403))

    def test_session_revision_and_saved_content_changes_reject_old_scenarios(self):
        payload=self.payload()
        TravelPlanningSession.objects.filter(pk=self.session.pk).update(revision=99)
        self.assertEqual(self.post(payload).status_code,409)
        payload=self.payload()
        TravelPlan.objects.filter(pk=self.plan.pk).update(itinerary={'budget':{'expected':'410','currency':'USD'}})
        self.assertEqual(self.post(payload).status_code,409)

    def test_financial_evidence_updates_reject_old_confirmation(self):
        payload=self.payload()
        BankAccount.objects.filter(pk=self.account.pk).update(current_balance='999.99')
        response=self.post(payload)
        self.assertEqual(response.status_code,409)
        self.assertEqual(response.json()['code'],'source_changed')

    def test_mismatched_currency_nonfinite_missing_and_float_inputs_cannot_be_affordable(self):
        for field,value in (('currency','EUR'),('amount','NaN'),('amount',None),('amount',1.23),('amount','-0.001')):
            payload=self.payload();payload['confirmation']['trip_budget'][field]=value
            self.assertEqual(self.post(payload).json()['label'],'Insufficient Data')
        payload=self.payload();payload['confirmation']['trip_budget']['amount']='1'*10000
        self.assertEqual(self.post(payload).json()['label'],'Insufficient Data')

    def test_unknown_fields_and_malformed_scenarios_are_not_accepted(self):
        payload=self.payload();payload['send_email']=True
        self.assertEqual(self.post(payload).status_code,400)
        payload=self.payload();payload['confirmation']['private_notes']='not a financial assumption'
        self.assertEqual(self.post(payload).status_code,400)
        payload=self.payload();payload['confirmation']=[]
        self.assertEqual(self.post(payload).status_code,400)

    def test_invalidated_or_malformed_estimates_remain_unavailable(self):
        for budget in ({'expected':'NaN','currency':'USD'},{'expected':'1','currency':None},
                       {'expected':'1','currency':'USD','status':'needs_recalculation'}):
            TravelPlan.objects.filter(pk=self.plan.pk).update(itinerary={'budget':budget})
            self.assertIsNone(self.client.get(self.url).json()['trip']['estimate'])

    def test_repeated_scenarios_leave_finance_trip_and_private_data_unchanged(self):
        payload=self.payload()
        before=deepcopy((list(TravelPlan.objects.values()),list(TravelPlanningSession.objects.values())))
        def readonly(execute,sql,params,many,context):
            if not sql.lstrip().upper().startswith('UPDATE "DJANGO_SESSION"'):
                self.assertNotRegex(sql.lstrip().upper(),r'^(INSERT|UPDATE|DELETE|REPLACE|CREATE|ALTER|DROP)\b')
            return execute(sql,params,many,context)
        with connection.execute_wrapper(readonly),patch('requests.sessions.Session.request',side_effect=AssertionError('external request')):
            first=self.post(payload)
            self.assertEqual(first.json(),self.post(payload).json())
        self.assertEqual(first.status_code,200)
        self.assertEqual(before,(list(TravelPlan.objects.values()),list(TravelPlanningSession.objects.values())))
