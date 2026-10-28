"""Synthetic Decimal, calendar, consent and private API projection contracts."""
from copy import deepcopy
from datetime import date, datetime, timezone as dt_timezone
from unittest.mock import patch

from django.core.cache import cache
from django.db import connection
from django.test import Client, TestCase

from apps.expenses.models import BankAccount
from apps.loans.models import Loan
from apps.mobility.models import TravelPlan, TravelPlanningSession
from apps.mobility.services.travel.savings import calculate_savings, savings_source
from tests import test_travel_affordability as fixtures


class TravelSavingsTests(TestCase):
    def setUp(self):
        self.enterContext(patch('django.utils.timezone.localdate', return_value=date(2028, 1, 30)))
        self.enterContext(patch('django.utils.timezone.now', return_value=datetime(2028, 1, 30, 12, tzinfo=dt_timezone.utc)))
        cache.clear(); self.addCleanup(cache.clear)
        fixtures.TravelAffordabilityTests.setUp(self)
        self.user.monthly_income='3100.00'; self.user.save()
        self.plan=TravelPlan.objects.create(user=self.user, title='Synthetic savings')
        self.session=TravelPlanningSession.objects.create(user=self.user, plan=self.plan)
        self.url=f'/api/mobility/planner/sessions/{self.session.pk}/savings/'
        self.client.force_login(self.user)

    confirmation=fixtures.TravelAffordabilityTests.confirmation

    def assumptions(self):
        money=lambda amount:dict(amount=amount, currency='USD', verified=True)
        return dict(source_revision=savings_source(self.user)['revision'], departure='2028-03-01',
                    income_from='2028-01-01', income_until='2028-12-31', verified_on='2028-01-30', confirmed=True,
                    monthly_income=money('3100'), monthly_goals=money('310'), monthly_contribution=money('310'),
                    schedules=[dict(id=self.loan.pk, next_due='2028-01-31', final_due='', verified=True)],
                    scenarios={name:dict(income_percent='100', expense_percent='100')
                               for name in ('conservative','baseline','optimistic')})

    def calculate(self, assumptions=None, confirmation=None):
        return calculate_savings(self.user, confirmation or self.confirmation(), assumptions or self.assumptions())

    def payload(self):
        source=self.client.get(self.url).json()
        return dict(revision=source['trip']['revision'], snapshot=source['trip']['snapshot'],
                    confirmation=self.confirmation(), savings=self.assumptions())

    def post(self, data):
        return self.client.post(self.url, data, content_type='application/json')

    def test_partial_leap_months_exclusive_cutoff_and_exact_current_vs_future(self):
        a=self.assumptions(); a['departure']='2028-02-02'; a['schedules'][0]['final_due']='2028-01-31'
        result=self.calculate(a)
        self.assertEqual(result['status'],'PROJECTED_ESTIMATE'); self.assertFalse(result['certified'])
        self.assertEqual(result['current']['amounts']['available_trip_funds'],'525.00')
        self.assertEqual(result['starting_unallocated_cash'],'700.00')
        scenario=result['scenarios']['baseline']; rows=scenario['months']
        self.assertEqual([r['days'] for r in rows],[1,1])
        self.assertEqual([r['emi'] for r in rows],['25.00','0.00'])
        self.assertEqual([r['trip_allocation'] for r in rows],['10.00','10.68'])
        self.assertEqual(scenario['projected_trip_funds'],'720.68')
        self.assertEqual(rows[-1]['end_exclusive'],'2028-02-02')

    def test_historical_today_and_unbounded_dates_reject_tomorrow_has_no_income(self):
        for departure in ('2028-01-29','2028-01-30','2035-01-01','bad'):
            a=self.assumptions(); a['departure']=departure
            self.assertIsNone(self.calculate(a)['scenarios'])
        a=self.assumptions(); a['departure']='2028-01-31'
        result=self.calculate(a)['scenarios']['baseline']
        self.assertEqual(result['months'],[]); self.assertIsNone(result['required_monthly_saving'])
        self.assertEqual(result['projected_trip_funds'],'700.00')

    def test_emi_month_end_anchor_maturity_and_overlapping_loans(self):
        other=Loan.objects.create(user=self.user,principal='100',remaining_balance='100',emi='15',interest_rate=0,start_date=date(2028,1,1))
        a=self.assumptions(); a['departure']='2028-04-01'
        a['schedules'][0]['final_due']='2028-02-29'
        a['schedules'].append(dict(id=other.pk,next_due='2028-02-15',final_due='2028-03-15',verified=True))
        rows=self.calculate(a)['scenarios']['baseline']['months']
        self.assertEqual([r['emi'] for r in rows],['25.00','40.00','15.00'])

    def test_missing_foreign_duplicate_unverified_and_past_schedules_abstain(self):
        for mutate in (lambda a:a.update(schedules=[]),lambda a:a['schedules'].append(deepcopy(a['schedules'][0])),
                       lambda a:a['schedules'][0].update(id=999999),lambda a:a['schedules'][0].update(verified=False),
                       lambda a:a['schedules'][0].update(next_due='2028-01-30'),
                       lambda a:a['schedules'][0].update(final_due='2028-01-01')):
            a=self.assumptions(); mutate(a); self.assertIsNone(self.calculate(a)['scenarios'])

    def test_irregular_final_payment_cannot_be_silently_omitted(self):
        a=self.assumptions();a['departure']='2028-04-01';a['schedules'][0]['final_due']='2028-03-15'
        self.assertIsNone(self.calculate(a)['scenarios'])

    def test_zero_negative_flow_and_no_contribution_double_count(self):
        a=self.assumptions(); a['scenarios']['conservative']['income_percent']='0'
        result=self.calculate(a)['scenarios']
        self.assertLess(float(result['conservative']['projected_trip_funds']),700)
        for row in result['baseline']['months']:
            self.assertLessEqual(float(row['trip_allocation']),float(row['net_cashflow']))
        a['monthly_contribution']['amount']='0'
        self.assertEqual(self.calculate(a)['scenarios']['baseline']['projected_trip_funds'],'700.00')
        c=self.confirmation();c['spendable_cash']['amount']='0'
        result=self.calculate(a,c)['scenarios']['conservative']
        self.assertEqual(result['projected_trip_funds'],'0.00');self.assertNotEqual(result['protected_funding_deficit'],'0.00')

    def test_required_saving_rounds_up_and_capacity_remains_explicit(self):
        a=self.assumptions(); c=self.confirmation();c['trip_budget']['amount']='1000'
        r=self.calculate(a,c)['scenarios']['baseline']
        self.assertEqual(r['required_monthly_saving'],'314.85')
        self.assertEqual(r['status'],'PROJECTED_SHORTFALL')

    def test_explicit_income_effective_period_and_same_currency_required(self):
        for key,value in (('confirmed',False),('income_from','2028-02-01'),('income_until','2028-02-01'),('verified_on','2028-01-29')):
            a=self.assumptions();a[key]=value;self.assertIsNone(self.calculate(a)['scenarios'])
        for key,value in (('currency','EUR'),('currency',None),('verified',False),('amount','3101'),('amount','NaN'),('amount',1.1)):
            a=self.assumptions();a['monthly_income'][key]=value;self.assertIsNone(self.calculate(a)['scenarios'])
        self.user.monthly_income='0';self.user.save()
        self.assertIsNone(self.calculate()['scenarios'])

    def test_scenario_order_limits_nonfinite_and_malformed_input(self):
        for value in ('101','NaN','-1',None,'9'*100):
            a=self.assumptions();a['scenarios']['baseline']['income_percent']=value
            self.assertIsNone(self.calculate(a)['scenarios'])
        a=self.assumptions();a['scenarios']['conservative']['income_percent']='99';a['scenarios']['baseline']['income_percent']='90'
        self.assertIsNone(self.calculate(a)['scenarios'])
        a=self.assumptions();a['monthly_goals']['amount']='-0.001';self.assertIsNone(self.calculate(a)['scenarios'])
        a=self.assumptions();a['private_note']='not allowed';self.assertIsNone(self.calculate(a)['scenarios'])

    def test_income_expense_loan_and_cash_corrections_invalidate_old_source(self):
        for model,pk,fields in ((BankAccount,self.account.pk,dict(current_balance='999')),
                                (Loan,self.loan.pk,dict(emi='26'))):
            payload=self.payload();model.objects.filter(pk=pk).update(**fields)
            self.assertEqual(self.post(payload).status_code,409)
        payload=self.payload();type(self.user).objects.filter(pk=self.user.pk).update(monthly_income='3000')
        self.assertEqual(self.post(payload).status_code,409)
        payload=self.payload();type(self.expense).objects.filter(pk=self.expense.pk).update(amount='51')
        self.assertEqual(self.post(payload).status_code,409)

    def test_revision_authentication_owner_and_csrf(self):
        payload=self.payload();self.session.revision=2;self.session.save()
        self.assertEqual(self.post(payload).status_code,409)
        client=Client(enforce_csrf_checks=True);client.force_login(self.user)
        self.assertEqual(client.post(self.url,self.payload(),content_type='application/json').status_code,403)
        self.client.force_login(self.other);self.assertEqual(self.client.get(self.url).status_code,404)
        self.assertEqual(self.post(payload).status_code,404)
        self.client.logout();self.assertIn(self.client.get(self.url).status_code,(401,403))

    def test_private_readonly_repeat_export_no_network_and_saved_trip_invalidation(self):
        payload=self.payload()
        before=deepcopy((list(TravelPlan.objects.values()),list(TravelPlanningSession.objects.values())))
        def readonly(execute,sql,params,many,context):
            if not sql.lstrip().upper().startswith('UPDATE "DJANGO_SESSION"'):
                self.assertNotRegex(sql.lstrip().upper(),r'^(INSERT|UPDATE|DELETE|REPLACE|CREATE|ALTER|DROP)\b')
            return execute(sql,params,many,context)
        with connection.execute_wrapper(readonly),patch('requests.sessions.Session.request',side_effect=AssertionError('external request')):
            response=self.post(payload);self.assertEqual(response.status_code,200)
            self.assertEqual(response.json(),self.post(payload).json())
        self.assertEqual(response['Cache-Control'],'no-store, private')
        self.assertEqual(before,(list(TravelPlan.objects.values()),list(TravelPlanningSession.objects.values())))
        self.plan.start_date=date(2028,2,1);self.plan.save()
        self.assertEqual(self.post(payload).status_code,409)

    def test_incomplete_current_evidence_never_gets_a_projection(self):
        c=self.confirmation();c['disjoint_allocations']=False
        self.assertIsNone(self.calculate(confirmation=c)['scenarios'])
