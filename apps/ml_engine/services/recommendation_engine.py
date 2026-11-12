"""
Financial recommendation engine.

Suggestions are built only from the owner's own records. No product catalog, expected return,
premium, cover amount or credit score is assumed: where a figure would need an outside source,
the payload says "Not available".
"""
from datetime import timedelta
from decimal import Decimal, InvalidOperation
from typing import Dict, List, Optional
from django.db.models import Sum
from django.utils import timezone

from apps.expenses.money import money_float
from apps.expenses.services.financial_intelligence import resolve_canonical_financial_baseline

NOT_AVAILABLE = "Not available"
NO_RETURN_SOURCE = "Not available: no verified, dated source for expected returns is attached."
NO_PREMIUM_SOURCE = "Not available: get quotes from insurers; ALFRED does not estimate premiums or cover."


class FinancialRecommendationEngine:
    """Rule-based suitability guidance from the owner's own baseline, holdings and household."""

    # Asset classes only; no product names, returns or minimums are claimed.
    ASSET_CLASSES = {
        'EQUITY_LARGE': {'name': 'Large-cap equity', 'type': 'Equity', 'risk': 'Moderate',
                         'recommended_for': ['stable_income', 'long_term'], 'liquidity': 'High'},
        'EQUITY_MID': {'name': 'Mid-cap equity', 'type': 'Equity', 'risk': 'High',
                       'recommended_for': ['high_risk_appetite', 'long_term'], 'liquidity': 'High'},
        'DEBT': {'name': 'Debt funds or deposits', 'type': 'Debt', 'risk': 'Low',
                 'recommended_for': ['conservative', 'short_term'], 'liquidity': 'High'},
        'GOLD': {'name': 'Gold', 'type': 'Gold', 'risk': 'Moderate',
                 'recommended_for': ['diversification', 'inflation_hedge'], 'liquidity': 'High'},
        'PENSION': {'name': 'Retirement / pension account', 'type': 'Pension', 'risk': 'Low',
                    'recommended_for': ['retirement_planning', 'long_term'], 'liquidity': 'Low'},
    }

    # Protection types only; cover and premium need an insurer quote.
    PROTECTION_TYPES = {
        'TERM_LIFE': {'name': 'Term life insurance', 'type': 'Life Insurance', 'recommended_for': ['has_dependents']},
        'HEALTH_FAMILY': {'name': 'Health insurance', 'type': 'Health Insurance', 'recommended_for': ['has_family']},
        'HEALTH_CRITICAL': {'name': 'Critical illness cover', 'type': 'Health Insurance', 'recommended_for': ['has_dependents']},
    }

    def __init__(self):
        self.user_profiles = {}

    def build_user_profile(self, user) -> Dict:
        """
        Build comprehensive user profile for recommendations.

        Args:
            user: Django user object

        Returns:
            Dict with user financial profile
        """
        from apps.expenses.models import Expense
        from apps.family.models import Dependent
        from apps.loans.models import Loan
        from apps.investments.models import Investment

        profile = {
            'user_id': user.id,
            # Unknown age stays unknown; it is never defaulted.
            'age': getattr(user, 'age', None),
            'city': getattr(user, 'city', '') or '',
            'dependents': Dependent.objects.filter(user=user).count(),
        }
        baseline = resolve_canonical_financial_baseline(user)
        profile['financial_baseline'] = baseline
        profile['income'] = baseline.get('monthly_income', 0) or 0

        # Spending analysis (last 90 days)
        last_90_days = timezone.localdate() - timedelta(days=90)
        expenses = Expense.objects.in_rupee_totals().filter(
            user=user,
            direction='debit',
            transaction_date__gte=last_90_days,
        ).exclude(classification='loan')

        profile['monthly_expenses'] = float(baseline.get('observed_average_monthly_variable_spend', 0) or 0)

        # Category-wise spending
        category_spending = {}
        for category in ['food', 'shopping', 'travel', 'utilities', 'entertainment']:
            cat_total = expenses.filter(category=category).aggregate(
                total=Sum('amount')
            )['total'] or 0
            category_spending[category] = cat_total

        profile['spending_categories'] = category_spending
        profile['top_category'] = max(category_spending, key=category_spending.get) if category_spending else 'other'

        # Savings capacity
        profile['monthly_savings'] = float(baseline.get('savings_capacity', 0) or 0)
        profile['savings_rate'] = float(baseline.get('savings_rate', 0) or 0)

        # Loan analysis
        active_loans = Loan.objects.filter(user=user, is_active=True, verification_status="confirmed").in_rupee_totals()
        profile['has_loans'] = active_loans.exists()
        profile['total_emi'] = float(baseline.get('recurring_emi_burden', 0) or 0)
        profile['dti_ratio'] = float(baseline.get('debt_burden_ratio', 0) or 0)

        # Investment analysis
        investments = Investment.objects.filter(user=user).in_rupee_totals()
        profile['has_investments'] = investments.exists()
        # Current value, not cost: the Investments page keeps 'total_invested' for the amount put in.
        profile['investments_current_value'] = float(investments.aggregate(Sum('current_value'))['current_value__sum'] or 0)

        # Risk profile
        profile['risk_appetite'] = self._assess_risk_appetite(profile)

        # User persona
        profile['persona'] = self._determine_persona(profile)

        self.user_profiles[user.id] = profile
        return profile

    def _assess_risk_appetite(self, profile: Dict) -> str:
        """Assess user's risk appetite based on profile."""
        score = 0

        # Age factor, only when the owner's age is recorded
        age = profile.get('age')
        if age is None:
            pass
        elif age < 30:
            score += 3
        elif age < 40:
            score += 2
        else:
            score += 1

        # Savings rate
        if profile['savings_rate'] > 30:
            score += 3
        elif profile['savings_rate'] > 15:
            score += 2
        else:
            score += 1

        # Existing investments
        if profile['has_investments']:
            score += 2

        # DTI ratio (lower is better for risk taking); a ratio without income is not a low one
        if profile['income'] > 0 and profile['dti_ratio'] < 25:
            score += 2
        elif profile['income'] > 0 and profile['dti_ratio'] < 40:
            score += 1

        if score >= 8:
            return 'aggressive'
        elif score >= 5:
            return 'moderate'
        else:
            return 'conservative'

    def _determine_persona(self, profile: Dict) -> List[str]:
        """Determine user personas for better recommendations."""
        personas = []

        # Spending-based
        if profile['spending_categories'].get('shopping', 0) > 10000:
            personas.append('online_shopper')

        if profile['spending_categories'].get('food', 0) > 8000:
            personas.append('foodie')

        if profile['spending_categories'].get('travel', 0) > 15000:
            personas.append('frequent_traveler')

        if profile['spending_categories'].get('utilities', 0) > 5000:
            personas.append('bill_payer')

        # Income-based
        if profile['income'] > 150000:
            personas.append('high_income')
        elif profile['income'] > 75000:
            personas.append('mid_income')
        elif profile['income'] > 0:
            personas.append('budget_conscious')

        # Life stage
        if profile['dependents'] > 0:
            personas.append('has_dependents')
            personas.append('has_family')

        if (profile.get('age') or 0) > 45:
            personas.append('retirement_planning')

        # Financial behavior
        if profile['savings_rate'] > 30:
            personas.append('high_saver')

        if not profile['has_investments']:
            personas.append('investment_beginner')

        return personas

    def recommend_investments(self, user, investment_amount: Optional[float] = None,
                            time_horizon: str = 'long_term') -> Dict:
        """
        Recommend investment products based on risk profile and goals.

        Args:
            user: Django user object
            investment_amount: Amount available for investment
            time_horizon: 'short_term', 'medium_term', or 'long_term'

        Returns:
            Dict with investment recommendations
        """
        profile = self.build_user_profile(user)
        risk_appetite = profile['risk_appetite']

        amount_source = 'entered'
        if not investment_amount:
            # Half of the owner's own monthly savings capacity; never a guessed amount.
            investment_amount = Decimal(str(profile['financial_baseline'].get('savings_capacity') or 0)) / 2
            amount_source = 'half_of_monthly_savings_capacity'
        try:
            investment_amount = Decimal(str(investment_amount))
        except InvalidOperation:
            investment_amount = Decimal('0')
        if not investment_amount.is_finite() or investment_amount < 0:
            investment_amount = Decimal('0')

        recommendations = []

        for inv_id, inv in self.ASSET_CLASSES.items():
            score = 0

            # Risk alignment
            if risk_appetite == 'aggressive' and inv['risk'] in ['High', 'Moderate']:
                score += 40
            elif risk_appetite == 'moderate' and inv['risk'] in ['Moderate', 'Low']:
                score += 40
            elif risk_appetite == 'conservative' and inv['risk'] == 'Low':
                score += 40
            else:
                score += 10

            # Time horizon match
            if time_horizon == 'long_term' and 'long_term' in inv['recommended_for']:
                score += 30
            elif time_horizon == 'short_term' and 'short_term' in inv['recommended_for']:
                score += 30

            # Persona match
            matching_personas = set(profile['persona']) & set(inv['recommended_for'])
            score += len(matching_personas) * 10

            # Suggested allocation
            suggested_allocation = self._calculate_allocation(inv, risk_appetite, investment_amount)

            recommendations.append({
                'investment': inv,
                'investment_id': inv_id,
                'score': score,
                'suggested_allocation': suggested_allocation,
                'suggested_amount': money_float(investment_amount * suggested_allocation / 100),
                'expected_return': None,
                'expected_return_status': NO_RETURN_SOURCE,
                'match_reason': f"Matches your {risk_appetite} risk profile, worked out from your own records"
            })

        # Sort by score
        recommendations.sort(key=lambda x: x['score'], reverse=True)

        # Create diversified portfolio
        portfolio = self._create_diversified_portfolio(recommendations, investment_amount, risk_appetite)

        return {
            'recommendations': recommendations[:5],
            'suggested_portfolio': portfolio,
            'your_profile': {
                'risk_appetite': risk_appetite,
                'available_amount': money_float(investment_amount),
                'amount_source': amount_source,
                'time_horizon': time_horizon
            }
        }

    def recommend_insurance(self, user) -> Dict:
        """Protection needs from the owner's household records; no premium or cover is estimated."""
        profile = self.build_user_profile(user)
        recommendations = []
        for ins_id, ins in self.PROTECTION_TYPES.items():
            matching_personas = set(profile['persona']) & set(ins['recommended_for'])
            # Health cover applies to every household; life cover is essential once dependents are recorded.
            essential = ins_id == 'HEALTH_FAMILY' or (ins_id == 'TERM_LIFE' and profile['dependents'] > 0)
            score = 50 if essential else 30 * len(matching_personas)
            recommendations.append({
                'insurance': {**ins, 'premium_estimate': None, 'coverage': None, 'quote_status': NO_PREMIUM_SOURCE},
                'insurance_id': ins_id,
                'score': score,
                'is_essential': score >= 50,
                'match_reason': self._explain_insurance_match(ins, profile, matching_personas),
            })
        recommendations.sort(key=lambda x: x['score'], reverse=True)
        return {
            'recommendations': recommendations,
            'total_annual_premium': None,
            'premium_status': NO_PREMIUM_SOURCE,
            'your_profile': {
                'age': profile['age'],
                'dependents': profile['dependents'],
                'monthly_income': profile['income']
            }
        }

    def _calculate_allocation(self, investment: Dict, risk_appetite: str, total_amount: float) -> float:
        """Calculate suggested allocation percentage."""
        if risk_appetite == 'aggressive':
            if investment['risk'] == 'High':
                return 40
            elif investment['risk'] == 'Moderate':
                return 30
            else:
                return 10
        elif risk_appetite == 'moderate':
            if investment['risk'] == 'Moderate':
                return 40
            elif investment['risk'] in ['High', 'Low']:
                return 25
            return 20
        else:  # conservative
            if investment['risk'] == 'Low':
                return 50
            elif investment['risk'] == 'Moderate':
                return 30
            else:
                return 10

    def _create_diversified_portfolio(self, recommendations: List, amount: Decimal, risk: str) -> Dict:
        """Create a diversified investment portfolio."""
        portfolio = {
            'total_amount': money_float(amount),
            'allocations': [],
            'expected_return': None,
            'expected_return_status': NO_RETURN_SOURCE,
            'risk_level': risk
        }

        # Ensure diversification
        allocated = 0
        for rec in recommendations[:4]:  # Max 4 products for diversification
            alloc = rec['suggested_allocation']
            if allocated + alloc <= 100:
                portfolio['allocations'].append({
                    'product': rec['investment']['name'],
                    'amount': rec['suggested_amount'],
                    'percentage': alloc,
                })
                allocated += alloc

        return portfolio

    def _explain_insurance_match(self, insurance: Dict, profile: Dict, matching_personas: set) -> str:
        """Reasons drawn only from the owner's household and income records."""
        reasons = []
        dependents = profile.get('dependents') or 0
        if dependents and 'has_dependents' in insurance['recommended_for']:
            reasons.append(f"You have {dependents} dependent(s) recorded")
        if insurance['name'] == 'Health insurance':
            reasons.append("Medical costs can hit any household; no health cover is recorded in ALFRED")
        if not profile.get('income'):
            reasons.append("Confirm your income to judge affordability")
        return "; ".join(reasons) if reasons else "Optional; nothing in your records makes this essential"


# Singleton instance
recommendation_engine = FinancialRecommendationEngine()
