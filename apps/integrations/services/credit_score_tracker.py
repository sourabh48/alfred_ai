"""
Credit Score Tracking Service
Integration with credit bureaus (CIBIL, Experian, Equifax, CRIF) for Indian users
"""
import os
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from django.utils import timezone
from django.db.models import Avg, Count, Sum


class CreditScoreTrackerService:
    """
    Track and analyze credit scores from multiple bureaus.
    Provides insights, trends, and improvement suggestions.
    """

    # Indian Credit Bureaus
    BUREAUS = {
        'CIBIL': {
            'name': 'TransUnion CIBIL',
            'url': 'https://www.cibil.com',
            'score_range': (300, 900),
            'excellent': 750,
            'good': 700,
            'fair': 650
        },
        'EXPERIAN': {
            'name': 'Experian',
            'url': 'https://www.experian.in',
            'score_range': (300, 900),
            'excellent': 750,
            'good': 700,
            'fair': 650
        },
        'EQUIFAX': {
            'name': 'Equifax',
            'url': 'https://www.equifax.co.in',
            'score_range': (300, 850),
            'excellent': 720,
            'good': 670,
            'fair': 620
        },
        'CRIF': {
            'name': 'CRIF High Mark',
            'url': 'https://www.crifhighmark.com',
            'score_range': (300, 900),
            'excellent': 750,
            'good': 700,
            'fair': 650
        }
    }

    def __init__(self):
        self.api_keys = {}
        self._load_env_credentials()

    def _load_env_credentials(self):
        for bureau in self.BUREAUS.keys():
            key = os.getenv(f"{bureau}_API_KEY", "").strip() or os.getenv(f"CREDIT_{bureau}_API_KEY", "").strip()
            secret = os.getenv(f"{bureau}_API_SECRET", "").strip() or os.getenv(f"CREDIT_{bureau}_API_SECRET", "").strip()
            if key:
                self.api_keys[bureau] = {"api_key": key, "api_secret": secret}

    def set_api_credentials(self, bureau: str, api_key: str, api_secret: str = None):
        """
        Set API credentials for a credit bureau.

        Args:
            bureau: Bureau name (CIBIL, EXPERIAN, EQUIFAX, CRIF)
            api_key: API key
            api_secret: API secret (if required)
        """
        self.api_keys[bureau.upper()] = {
            'api_key': api_key,
            'api_secret': api_secret
        }

    def _bureau_configured(self, bureau: str) -> bool:
        return bureau.upper() in self.api_keys

    def fetch_credit_score(self, user, bureau: str = 'CIBIL') -> Dict:
        """
        Fetch credit score from specified bureau.

        Args:
            user: Django user object
            bureau: Bureau name (default: CIBIL)

        Returns:
            Dict with credit score and details
        """
        bureau = bureau.upper()
        if self._bureau_configured(bureau):
            return {
                'success': False,
                'bureau': bureau,
                'integration_status': 'credentials_configured_but_not_implemented',
                'error': f'Credentials for {bureau} are configured, but the live bureau pull is not implemented in code yet.',
            }
        return self._estimate_credit_profile(user, bureau)

    def _estimate_credit_profile(self, user, bureau: str) -> Dict:
        """Estimate credit health from user-owned ALFRED data without claiming an official bureau pull."""
        from apps.loans.models import Loan
        from apps.expenses.models import BankAccount

        active_loans = Loan.objects.filter(user=user, is_active=True)
        accounts = BankAccount.objects.filter(user=user, is_active=True)
        analysis = self.analyze_score_factors(user)
        total_credit_limit = active_loans.aggregate(Sum('principal'))['principal__sum'] or 0
        total_accounts = accounts.count() + active_loans.count()
        active_accounts = accounts.count() + active_loans.count()
        min_score, max_score = self.BUREAUS[bureau]['score_range']
        score = max(min_score, min(int(analysis['overall_score']), max_score))

        return {
            'success': True,
            'bureau': bureau,
            'score': score,
            'score_kind': 'estimated',
            'integration_status': 'not_configured',
            'detail': 'This is an internal credit-health estimate derived from your ALFRED financial data. It is not an official bureau score or CIBIL pull.',
            'score_range': self.BUREAUS[bureau]['score_range'],
            'rating': self._get_rating(score, bureau),
            'last_updated': timezone.now().isoformat(),
            'factors': analysis['factors'],
            'report_summary': {
                'total_accounts': total_accounts,
                'active_accounts': active_accounts,
                'closed_accounts': 0,
                'delinquent_accounts': 0,
                'total_credit_limit': total_credit_limit,
                'credit_utilization': next(
                    (factor.get('utilization_percent', 0) for factor in analysis['factors'] if factor['name'] == 'Credit Utilization'),
                    0,
                ),
            },
        }

    def get_all_bureau_scores(self, user) -> Dict:
        """
        Fetch scores from all bureaus.

        Args:
            user: Django user object

        Returns:
            Dict with scores from all bureaus
        """
        scores = {}

        for bureau in self.BUREAUS.keys():
            result = self.fetch_credit_score(user, bureau)
            if result.get('success') and result.get('score_kind') == 'official':
                scores[bureau] = result

        if scores:
            avg_score = sum(s['score'] for s in scores.values()) / len(scores)
            return {
                'success': True,
                'scores': scores,
                'average_score': round(avg_score),
                'timestamp': timezone.now().isoformat()
            }

        return {
            'success': False,
            'error': 'No official bureau scores are available yet.',
            'detail': 'Live bureau integration is not configured. Alfred can still calculate internal credit-health factors from your own data.',
        }

    def analyze_score_factors(self, user) -> Dict:
        """
        Analyze factors affecting credit score.

        Args:
            user: Django user object

        Returns:
            Dict with detailed factor analysis
        """
        from apps.loans.models import Loan
        from apps.expenses.models import BankAccount

        analysis = {
            'factors': [],
            'strengths': [],
            'weaknesses': [],
            'improvement_suggestions': []
        }

        # 1. Payment History (35% weight)
        active_loans = Loan.objects.filter(user=user, is_active=True)
        missed_payments = sum(loan.missed_payments for loan in active_loans)

        payment_score = max(0, 100 - (missed_payments * 10))
        analysis['factors'].append({
            'name': 'Payment History',
            'weight': 35,
            'score': payment_score,
            'status': 'Good' if payment_score >= 80 else 'Needs Improvement'
        })

        if payment_score >= 80:
            analysis['strengths'].append('Consistent payment history')
        else:
            analysis['weaknesses'].append(f'Missed {missed_payments} payment(s)')
            analysis['improvement_suggestions'].append(
                'Set up auto-pay for EMIs to avoid missing payments'
            )

        # 2. Credit Utilization (30% weight)
        accounts = BankAccount.objects.filter(user=user, is_active=True)
        total_balance = accounts.aggregate(Sum('current_balance'))['current_balance__sum'] or 0
        total_loans = active_loans.aggregate(Sum('remaining_balance'))['remaining_balance__sum'] or 0

        if total_balance > 0:
            utilization = (total_loans / (total_balance + total_loans)) * 100
            utilization_score = max(0, 100 - utilization)
        else:
            utilization = 0
            utilization_score = 50

        analysis['factors'].append({
            'name': 'Credit Utilization',
            'weight': 30,
            'score': utilization_score,
            'utilization_percent': round(utilization, 1),
            'status': 'Good' if utilization < 30 else 'High'
        })

        if utilization < 30:
            analysis['strengths'].append('Low credit utilization')
        else:
            analysis['weaknesses'].append('High credit utilization')
            analysis['improvement_suggestions'].append(
                'Keep credit utilization below 30% for optimal score'
            )

        # 3. Credit Age (15% weight)
        account_dates = [item.created_at for item in accounts.only("created_at")] + [item.created_at for item in active_loans.only("created_at")]
        oldest_account_date = min(account_dates) if account_dates else timezone.now()
        account_age_months = max(0, ((timezone.now() - oldest_account_date).days // 30))
        age_score = min(100, (account_age_months / 120) * 100)  # Max score at 10 years

        analysis['factors'].append({
            'name': 'Credit Age',
            'weight': 15,
            'score': age_score,
            'age_months': account_age_months,
            'status': 'Good' if account_age_months >= 36 else 'New'
        })

        if account_age_months >= 36:
            analysis['strengths'].append('Established credit history')
        else:
            analysis['improvement_suggestions'].append(
                'Maintain accounts for longer to build credit history'
            )

        # 4. Credit Mix (10% weight)
        loan_types = active_loans.values('loan_type').distinct().count()
        mix_score = min(100, (loan_types / 3) * 100)  # Ideal: 3+ types

        analysis['factors'].append({
            'name': 'Credit Mix',
            'weight': 10,
            'score': mix_score,
            'types_count': loan_types,
            'status': 'Good' if loan_types >= 2 else 'Limited'
        })

        if loan_types >= 2:
            analysis['strengths'].append('Diverse credit portfolio')
        else:
            analysis['improvement_suggestions'].append(
                'Consider diversifying credit types (secured + unsecured)'
            )

        # 5. Recent Inquiries (10% weight)
        recent_inquiries = Loan.objects.filter(user=user, created_at__gte=timezone.now() - timedelta(days=180)).count()
        inquiry_score = max(0, 100 - (recent_inquiries * 15))

        analysis['factors'].append({
            'name': 'Recent Inquiries',
            'weight': 10,
            'score': inquiry_score,
            'count': recent_inquiries,
            'status': 'Good' if recent_inquiries <= 2 else 'High'
        })

        if recent_inquiries <= 2:
            analysis['strengths'].append('Minimal credit inquiries')
        else:
            analysis['weaknesses'].append('Multiple recent credit inquiries')
            analysis['improvement_suggestions'].append(
                'Limit credit applications to avoid multiple hard inquiries'
            )

        # Calculate weighted score
        weighted_score = sum(
            factor['score'] * factor['weight'] / 100
            for factor in analysis['factors']
        )

        # Convert to 300-900 scale
        final_score = 300 + (weighted_score / 100) * 600

        analysis['overall_score'] = round(final_score)
        analysis['rating'] = self._get_rating(final_score, 'CIBIL')

        return analysis

    def get_score_trend(self, user, months: int = 12) -> Dict:
        """
        Get credit score trend over time.

        Args:
            user: Django user object
            months: Number of months to analyze

        Returns:
            Dict with historical scores and trend
        """
        from apps.integrations.models import CreditScore

        cutoff = timezone.now() - timedelta(days=30 * months)
        official_scores = list(
            CreditScore.objects.filter(user=user, score_kind="official", fetched_at__gte=cutoff)
            .order_by("fetched_at")
            .values("score", "fetched_at")
        )
        trend = []
        previous_score = None
        for item in official_scores:
            current_score = int(item["score"])
            trend.append(
                {
                    "month": item["fetched_at"].strftime("%b %Y"),
                    "score": current_score,
                    "change": (current_score - previous_score) if previous_score is not None else 0,
                }
            )
            previous_score = current_score

        if not trend:
            return {
                "trend": [],
                "current_score": None,
                "change_12m": 0,
                "direction": "unavailable",
                "average_score": None,
                "highest_score": None,
                "lowest_score": None,
                "detail": "No official bureau history is stored yet, so Alfred is not drawing a fake trend line.",
            }

        first_score = trend[0]["score"]
        last_score = trend[-1]["score"]
        change = last_score - first_score

        return {
            "trend": trend,
            "current_score": last_score,
            "change_12m": change,
            "direction": "improving" if change > 0 else "declining" if change < 0 else "stable",
            "average_score": round(sum(t["score"] for t in trend) / len(trend)),
            "highest_score": max(t["score"] for t in trend),
            "lowest_score": min(t["score"] for t in trend),
        }

    def get_improvement_plan(self, user) -> Dict:
        """
        Generate personalized credit score improvement plan.

        Args:
            user: Django user object

        Returns:
            Dict with action plan and timeline
        """
        analysis = self.analyze_score_factors(user)
        current_score = analysis['overall_score']

        plan = {
            'current_score': current_score,
            'target_score': 750,  # Excellent range
            'estimated_timeline': '6-12 months',
            'action_items': [],
            'quick_wins': [],
            'long_term_goals': []
        }

        # Prioritize based on weaknesses
        for weakness in analysis['weaknesses']:
            if 'missed' in weakness.lower():
                plan['action_items'].append({
                    'priority': 'High',
                    'action': 'Set up auto-pay for all loans',
                    'impact': '+20-30 points',
                    'timeline': '1-3 months'
                })

            if 'utilization' in weakness.lower():
                plan['quick_wins'].append({
                    'action': 'Pay down credit card balances below 30%',
                    'impact': '+15-25 points',
                    'timeline': 'Immediate'
                })

        # Add general recommendations
        plan['action_items'].extend([
            {
                'priority': 'Medium',
                'action': 'Diversify credit mix (if needed)',
                'impact': '+10-15 points',
                'timeline': '3-6 months'
            },
            {
                'priority': 'High',
                'action': 'Maintain 100% on-time payment record',
                'impact': '+30-40 points',
                'timeline': '6-12 months'
            }
        ])

        plan['long_term_goals'] = [
            'Maintain credit age by keeping old accounts open',
            'Limit hard inquiries to 1-2 per year',
            'Keep overall debt below 40% of income',
            'Build emergency fund to avoid missed payments'
        ]

        return plan

    def compare_with_peers(self, user) -> Dict:
        """
        Compare user's credit score with demographic peers.

        Args:
            user: Django user object

        Returns:
            Dict with peer comparison
        """
        current_score = self.analyze_score_factors(user).get('overall_score', 0)
        age = getattr(user, 'age', 30)
        income = getattr(user, 'monthly_income', 75000)

        # Generate peer benchmarks
        if age < 25:
            peer_avg = 680
            peer_group = 'Under 25'
        elif age < 35:
            peer_avg = 720
            peer_group = '25-35'
        elif age < 45:
            peer_avg = 750
            peer_group = '35-45'
        else:
            peer_avg = 760
            peer_group = '45+'

        percentile = min(99, max(1, 50 + ((current_score - peer_avg) / 10)))

        return {
            'your_score': current_score,
            'comparison_basis': 'estimated_credit_health',
            'peer_group': peer_group,
            'peer_average': peer_avg,
            'percentile': round(percentile),
            'comparison': 'Above average' if current_score > peer_avg else 'Below average',
            'national_average': 715,
            'ranking': f'Top {100 - round(percentile)}%' if percentile > 50 else f'Bottom {round(percentile)}%'
        }

    def _get_rating(self, score: float, bureau: str) -> str:
        """Get rating based on score."""
        thresholds = self.BUREAUS[bureau]

        if score >= thresholds['excellent']:
            return 'Excellent'
        elif score >= thresholds['good']:
            return 'Good'
        elif score >= thresholds['fair']:
            return 'Fair'
        else:
            return 'Poor'

    def get_comprehensive_report(self, user) -> Dict:
        """
        Generate comprehensive credit report.

        Args:
            user: Django user object

        Returns:
            Complete credit report with all analyses
        """
        return {
            'user_id': user.id,
            'generated_at': timezone.now().isoformat(),
            'all_scores': self.get_all_bureau_scores(user),
            'factor_analysis': self.analyze_score_factors(user),
            'score_trend': self.get_score_trend(user, months=12),
            'improvement_plan': self.get_improvement_plan(user),
            'peer_comparison': self.compare_with_peers(user),
            'alerts': self._generate_alerts(user),
            'next_update': (timezone.now() + timedelta(days=30)).date().isoformat(),
            'bureau_status': 'official_integration_required',
        }

    def _generate_alerts(self, user) -> List[Dict]:
        """Generate important alerts for user."""
        alerts = []

        # Check for potential issues
        from apps.loans.models import Loan

        # High DTI warning
        active_loans = Loan.objects.filter(user=user, is_active=True)
        total_emi = active_loans.aggregate(Sum('emi'))['emi__sum'] or 0
        monthly_income = getattr(user, 'monthly_income', 75000)
        dti = (total_emi / monthly_income * 100) if monthly_income > 0 else 0

        if dti > 40:
            alerts.append({
                'severity': 'High',
                'type': 'DTI_WARNING',
                'message': f'Your debt-to-income ratio is {dti:.1f}%, which may negatively impact your credit score',
                'action': 'Consider debt consolidation or increasing income'
            })

        # Missed payments
        missed_payments = sum(loan.missed_payments for loan in active_loans)
        if missed_payments > 0:
            alerts.append({
                'severity': 'Critical',
                'type': 'MISSED_PAYMENT',
                'message': f'You have {missed_payments} missed payment(s) on record',
                'action': 'Set up auto-pay immediately to prevent future misses'
            })

        # Upcoming score update
        alerts.append({
            'severity': 'Info',
            'type': 'UPDATE_DUE',
            'message': 'Your next credit score update is due in 30 days',
            'action': 'Continue maintaining good financial habits'
        })

        return alerts


# Singleton instance
credit_score_service = CreditScoreTrackerService()
