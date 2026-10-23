"""Isolated owner-reported opportunity history; no employer/provider contact."""
from copy import deepcopy
from decimal import Decimal
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.utils import timezone

from apps.career.models import CareerJobAnalysis, CareerProfile
from apps.career.serializers import CareerJobAnalysisSerializer
from apps.career.services import job_intelligence
from scripts.exercise_materialized_cache_traffic import _offline_fixture_patches


class CareerOutcomeWorkflowTests(TestCase):
    def setUp(self):
        self.enterContext(override_settings(ALFRED_ABUSE_THROTTLE_DIR=self.enterContext(TemporaryDirectory(prefix='alfred-outcome-limits-'))))
        self.enterContext(_offline_fixture_patches())
        self.owner=get_user_model().objects.create_user(username='outcome-owner')
        self.other=get_user_model().objects.create_user(username='outcome-other')
        self.profile=CareerProfile.objects.create(user=self.owner,role='Synthetic analyst',experience_years=4,
            skills='SQL',last_salary='10000.01')
        self.source={'job_snapshot':{'salary_min':1000000,'salary_max':1200000,'salary_period':'year',
            'salary_currency':'INR'},'private_raw':'DO-NOT-RETURN-RAW','fit':{'fit_score':72}}
        self.row=CareerJobAnalysis.objects.create(user=self.owner,company='Synthetic Company',job_title='Analyst',
            job_url='https://example.org/synthetic-job',location='Bengaluru, Karnataka, India',
            extracted_text='PRIVATE-RAW-DOCUMENT',extracted_payload=deepcopy(self.source))
        self.url=f'/api/career/job-analyses/{self.row.pk}/outcome/'
        self.payload=dict(outcome='accepted',salary_min='110000.01',salary_max='120000.02',salary_period='month',
            salary_currency='INR',source_url=self.row.job_url,location=self.row.location,
            decided_at='2026-09-01',notes='Owner-reported synthetic decision')
        self.client.force_login(self.owner)

    def revision(self):
        self.row.refresh_from_db()
        return CareerJobAnalysisSerializer(self.row).data['updated_at']

    def test_invalid_explicit_salary_is_rejected_without_source_fallback_or_writes(self):
        for field in ('salary_min','salary_max'):
            for value in ('NaN','Infinity','-1','1e30','0.001',True,0,'not-a-number'):
                with self.subTest(field=field,value=value):
                    response=self.client.post(self.url,self.payload|{field:value},content_type='application/json')
                    self.assertEqual(response.status_code,400)
                    self.row.refresh_from_db(); self.assertEqual(self.row.extracted_payload,self.source)

    def test_owner_save_and_partial_correction_preserve_source_salary_and_profile(self):
        response=self.client.post(self.url,self.payload|{'revision':self.revision()},content_type='application/json')
        self.assertEqual(response.status_code,200)
        outcome=response.json()['opportunity_outcome']
        self.assertEqual(outcome['verification'],'owner_reported')
        self.assertEqual(Decimal(str(outcome['salary_min_annual'])),Decimal('1320000.12'))
        self.assertEqual(Decimal(str(outcome['salary_max_annual'])),Decimal('1440000.24'))
        response=self.client.patch(self.url,{'notes':'Corrected owner note','revision':self.revision()},content_type='application/json')
        self.assertEqual(response.status_code,200)
        corrected=response.json()['opportunity_outcome']
        for field in ('outcome','salary_min','salary_max','salary_period','salary_currency','decided_at','source_url','location'):
            self.assertEqual(corrected[field],outcome[field])
        self.assertEqual(corrected['notes'],'Corrected owner note')
        self.row.refresh_from_db()
        self.assertEqual({key:value for key,value in self.row.extracted_payload.items() if key!='opportunity_outcome'},self.source)
        self.profile.refresh_from_db(); self.assertEqual(self.profile.last_salary,Decimal('10000.01'))
        self.assertEqual(response.json()['opportunity']['id'],self.row.pk)

    def test_stale_revision_cannot_replace_an_outcome(self):
        original=deepcopy(self.row.extracted_payload)
        response=self.client.post(self.url,self.payload|{'revision':'2000-01-01T00:00:00Z'},content_type='application/json')
        self.assertEqual(response.status_code,409)
        self.row.refresh_from_db(); self.assertEqual(self.row.extracted_payload,original)

    def test_concurrent_source_change_cannot_be_overwritten(self):
        normalize=job_intelligence.normalize_opportunity_outcome
        def concurrent(analysis,payload):
            result=normalize(analysis,payload)
            CareerJobAnalysis.objects.filter(pk=analysis.pk).update(
                extracted_payload=self.source|{'concurrent_source':'PRESERVE'},updated_at=timezone.now())
            return result
        with patch('apps.career.views.job_intelligence.normalize_opportunity_outcome',side_effect=concurrent):
            response=self.client.post(self.url,self.payload,content_type='application/json')
        self.assertEqual(response.status_code,409)
        self.row.refresh_from_db()
        self.assertEqual(self.row.extracted_payload,self.source|{'concurrent_source':'PRESERVE'})

    def test_history_is_owner_scoped_paginated_and_excludes_raw_documents(self):
        CareerJobAnalysis.objects.create(user=self.other,company='FOREIGN-COMPANY',job_title='FOREIGN-JOB',
            job_url='https://example.org/foreign')
        for index in range(21):
            CareerJobAnalysis.objects.create(user=self.owner,company=f'Synthetic {index}',job_title='Analyst',
                job_url='https://example.org/synthetic',extracted_payload=deepcopy(self.source))
        response=self.client.get('/api/career/job-analyses/')
        self.assertEqual(response.status_code,200)
        data=response.json(); self.assertEqual(data['count'],22); self.assertEqual(len(data['results']),20)
        self.assertIsNotNone(data['next'])
        text=response.content.decode()
        for private in ('FOREIGN-COMPANY','FOREIGN-JOB','DO-NOT-RETURN-RAW','PRIVATE-RAW-DOCUMENT'):
            self.assertNotIn(private,text)
        self.assertEqual(len(self.client.get(data['next']).json()['results']),2)
        self.client.force_login(self.other)
        self.assertEqual(self.client.post(self.url,self.payload,content_type='application/json').status_code,404)
        self.client.logout()
        self.assertIn(self.client.get('/api/career/job-analyses/').status_code,(401,403))
        csrf=Client(enforce_csrf_checks=True); csrf.force_login(self.owner)
        self.assertEqual(csrf.post(self.url,self.payload,content_type='application/json').status_code,403)

    def test_salary_units_midpoint_and_invalid_date_range_or_source(self):
        payload=self.payload|{'salary_min':'1.1','salary_max':'1.2','salary_unit':'lakh','salary_period':'year'}
        result=self.client.post(self.url,payload,content_type='application/json')
        self.assertEqual(result.status_code,200)
        self.assertEqual(result.json()['opportunity_outcome']['salary_min'],110000)
        midpoint=self.client.post(self.url,self.payload|{'salary_min':'100.00','salary_max':'100.01','salary_period':'year'},content_type='application/json')
        self.assertEqual(midpoint.status_code,200)
        self.assertEqual(Decimal(str(midpoint.json()['opportunity_outcome']['salary_mid_annual'])),Decimal('100.01'))
        for invalid in ({'salary_min':'120000.03','salary_max':'110000.01'},{'decided_at':'yesterday'},
                {'decided_at':False},{'source_url':'https://user:password@example.org/job'},
                {'salary_unit':True},{'salary_unit':'unsupported'},{'salary_period':'fortnight'}):
            with self.subTest(invalid=invalid):
                self.row.refresh_from_db(); before=deepcopy(self.row.extracted_payload)
                response=self.client.post(self.url,self.payload|invalid,content_type='application/json')
                self.assertEqual(response.status_code,400)
                self.row.refresh_from_db(); self.assertEqual(self.row.extracted_payload,before)

    def test_unstructured_source_or_request_is_rejected_without_repairing_data(self):
        self.assertEqual(self.client.post(self.url,[],content_type='application/json').status_code,400)
        CareerJobAnalysis.objects.filter(pk=self.row.pk).update(extracted_payload=['RETAIN-ORIGINAL'])
        self.assertEqual(self.client.post(self.url,self.payload,content_type='application/json').status_code,400)
        self.row.refresh_from_db(); self.assertEqual(self.row.extracted_payload,['RETAIN-ORIGINAL'])
