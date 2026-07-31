"""
Financial Product Recommendation Engine
Personalized suggestions for credit cards, loans, investments, and insurance
"""
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from django.db.models import Sum
from django.utils import timezone

from apps.expenses.services.financial_intelligence import resolve_canonical_financial_baseline


class FinancialRecommendationEngine:
    """
    AI-powered recommendation engine for financial products.
    Uses collaborative filtering, content-based filtering, and rule-based logic.
    """

    # Credit Card Recommendations
    CREDIT_CARDS = {
        'HDFC_REGALIA': {
            'name': 'HDFC Bank Regalia Credit Card',
            'type': 'Premium Rewards',
            'annual_fee': 2500,
            'benefits': ['4 reward points per ₹150', 'Lounge access', 'Fuel surcharge waiver'],
            'income_required': 100000,
            'recommended_for': ['high_spender', 'frequent_traveler'],
            'category_bonuses': {'travel': 5, 'dining': 3, 'shopping': 2}
        },
        'ICICI_AMAZON': {
            'name': 'Amazon Pay ICICI Credit Card',
            'type': 'Cashback',
            'annual_fee': 0,
            'benefits': ['5% cashback on Amazon', '2% on bill payments', 'No annual fee'],
            'income_required': 30000,
            'recommended_for': ['online_shopper', 'budget_conscious'],
            'category_bonuses': {'shopping': 5, 'utilities': 2}
        },
        'SBI_ELITE': {
            'name': 'SBI Elite Credit Card',
            'type': 'Travel',
            'annual_fee': 4999,
            'benefits': ['10 reward points per ₹100', 'Complimentary lounge', 'Golf access'],
            'income_required': 150000,
            'recommended_for': ['luxury_traveler', 'high_income'],
            'category_bonuses': {'travel': 10, 'dining': 5, 'shopping': 3}
        },
        'AXIS_ACE': {
            'name': 'Axis Bank Ace Credit Card',
            'type': 'Cashback',
            'annual_fee': 0,
            'benefits': ['5% cashback on bill payments', '4% on Swiggy/Zomato', '2% on others'],
            'income_required': 25000,
            'recommended_for': ['foodie', 'bill_payer'],
            'category_bonuses': {'food': 4, 'utilities': 5, 'other': 2}
        }
    }

    # Personal Loan Products
    PERSONAL_LOANS = {
        'HDFC_PERSONAL': {
            'name': 'HDFC Personal Loan',
            'interest_rate': 10.5,
            'max_amount': 4000000,
            'tenure_months': 60,
            'processing_fee': 2.0,
            'eligibility': {'min_income': 25000, 'min_credit_score': 700}
        },
        'BAJAJ_INSTA': {
            'name': 'Bajaj Finserv Insta Personal Loan',
            'interest_rate': 11.0,
            'max_amount': 2500000,
            'tenure_months': 60,
            'processing_fee': 1.5,
            'eligibility': {'min_income': 20000, 'min_credit_score': 680}
        },
        'ICICI_INSTANT': {
            'name': 'ICICI Instant Personal Loan',
            'interest_rate': 10.75,
            'max_amount': 3500000,
            'tenure_months': 72,
            'processing_fee': 2.5,
            'eligibility': {'min_income': 30000, 'min_credit_score': 720}
        }
    }

    # Investment Products
    INVESTMENTS = {
        'EQUITY_MF_LARGE': {
            'name': 'Large Cap Equity Mutual Fund',
            'type': 'Equity MF',
            'risk': 'Moderate',
            'expected_return': 12,
            'min_investment': 500,
            'recommended_for': ['stable_income', 'long_term'],
            'liquidity': 'High'
        },
        'EQUITY_MF_MID': {
            'name': 'Mid Cap Equity Mutual Fund',
            'type': 'Equity MF',
            'risk': 'High',
            'expected_return': 15,
            'min_investment': 1000,
            'recommended_for': ['high_risk_appetite', 'long_term'],
            'liquidity': 'High'
        },
        'DEBT_FUND': {
            'name': 'Debt Mutual Fund',
            'type': 'Debt Fund',
            'risk': 'Low',
            'expected_return': 7,
            'min_investment': 500,
            'recommended_for': ['conservative', 'short_term'],
            'liquidity': 'High'
        },
        'GOLD_ETF': {
            'name': 'Gold ETF',
            'type': 'Gold',
            'risk': 'Moderate',
            'expected_return': 8,
            'min_investment': 1000,
            'recommended_for': ['diversification', 'inflation_hedge'],
            'liquidity': 'High'
        },
        'NPS': {
            'name': 'National Pension System',
            'type': 'Pension',
            'risk': 'Low-Moderate',
            'expected_return': 10,
            'min_investment': 500,
            'recommended_for': ['retirement_planning', 'tax_saving'],
            'liquidity': 'Low'
        }
    }

    # Insurance Products
    INSURANCE = {
        'TERM_LIFE': {
            'name': 'Term Life Insurance',
            'type': 'Life Insurance',
            'coverage': 10000000,
            'premium_estimate': 15000,
            'recommended_for': ['has_dependents', 'primary_earner'],
            'benefits': ['Pure protection', 'Tax benefits', 'High coverage']
        },
        'HEALTH_FAMILY': {
            'name': 'Family Health Insurance',
            'type': 'Health Insurance',
            'coverage': 500000,
            'premium_estimate': 20000,
            'recommended_for': ['has_family', 'preventive_care'],
            'benefits': ['Cashless treatment', 'No claim bonus', 'Pre-post hospitalization']
        },
        'HEALTH_CRITICAL': {
            'name': 'Critical Illness Cover',
            'type': 'Health Insurance',
            'coverage': 2000000,
            'premium_estimate': 8000,
            'recommended_for': ['family_history', 'comprehensive_protection'],
            'benefits': ['Lump sum payout', 'Covers 30+ illnesses', 'Income replacement']
        }
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
            'age': getattr(user, 'age', 30),
            'city': getattr(user, 'city', 'Mumbai'),
            'dependents': Dependent.objects.filter(user=user).count(),
        }
        baseline = resolve_canonical_financial_baseline(user)
        profile['financial_baseline'] = baseline
        profile['income'] = baseline.get('monthly_income', 0) or 0

        # Spending analysis (last 90 days)
        last_90_days = timezone.now().date() - timedelta(days=90)
        expenses = Expense.objects.filter(
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
        active_loans = Loan.objects.filter(user=user, is_active=True)
        profile['has_loans'] = active_loans.exists()
        profile['total_emi'] = float(baseline.get('recurring_emi_burden', 0) or 0)
        profile['dti_ratio'] = float(baseline.get('debt_burden_ratio', 0) or 0)

        # Investment analysis
        investments = Investment.objects.filter(user=user)
        profile['has_investments'] = investments.exists()
        profile['total_invested'] = investments.aggregate(Sum('current_value'))['current_value__sum'] or 0

        # Risk profile
        profile['risk_appetite'] = self._assess_risk_appetite(profile)

        # User persona
        profile['persona'] = self._determine_persona(profile)

        self.user_profiles[user.id] = profile
        return profile

    def _assess_risk_appetite(self, profile: Dict) -> str:
        """Assess user's risk appetite based on profile."""
        score = 0

        # Age factor
        if profile['age'] < 30:
            score += 3
        elif profile['age'] < 40:
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

        # DTI ratio (lower is better for risk taking)
        if profile['dti_ratio'] < 25:
            score += 2
        elif profile['dti_ratio'] < 40:
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
        else:
            personas.append('budget_conscious')

        # Life stage
        if profile['dependents'] > 0:
            personas.append('has_dependents')
            personas.append('has_family')

        if profile['age'] > 45:
            personas.append('retirement_planning')

        # Financial behavior
        if profile['savings_rate'] > 30:
            personas.append('high_saver')

        if not profile['has_investments']:
            personas.append('investment_beginner')

        return personas

    def recommend_credit_cards(self, user, top_n: int = 3) -> Dict:
        """
        Recommend credit cards based on user profile.

        Args:
            user: Django user object
            top_n: Number of recommendations

        Returns:
            Dict with recommended cards
        """
        profile = self.build_user_profile(user)

        recommendations = []

        for card_id, card in self.CREDIT_CARDS.items():
            score = 0

            # Income eligibility
            if profile['income'] >= card['income_required']:
                score += 30
            else:
                continue  # Skip if not eligible

            # Persona match
            matching_personas = set(profile['persona']) & set(card['recommended_for'])
            score += len(matching_personas) * 15

            # Category alignment
            top_category = profile['top_category']
            if top_category in card['category_bonuses']:
                score += card['category_bonuses'][top_category] * 5

            # Fee affordability
            if card['annual_fee'] == 0:
                score += 10
            elif card['annual_fee'] < profile['income'] * 0.05:
                score += 5

            recommendations.append({
                'card': card,
                'score': score,
                'card_id': card_id,
                'match_reason': self._explain_card_match(card, profile, matching_personas)
            })

        # Sort by score and return top N
        recommendations.sort(key=lambda x: x['score'], reverse=True)

        return {
            'recommendations': recommendations[:top_n],
            'user_profile': {
                'income': profile['income'],
                'top_spending_category': profile['top_category'],
                'personas': profile['persona']
            }
        }

    def recommend_loans(self, user, loan_amount: Optional[float] = None) -> Dict:
        """
        Recommend personal loan products.

        Args:
            user: Django user object
            loan_amount: Desired loan amount (optional)

        Returns:
            Dict with loan recommendations
        """
        profile = self.build_user_profile(user)

        recommendations = []

        # Estimate credit score (simplified)
        estimated_credit_score = 720
        if profile['dti_ratio'] < 25:
            estimated_credit_score += 30
        elif profile['dti_ratio'] > 40:
            estimated_credit_score -= 50

        for loan_id, loan in self.PERSONAL_LOANS.items():
            # Check eligibility
            if profile['income'] < loan['eligibility']['min_income']:
                continue

            if estimated_credit_score < loan['eligibility']['min_credit_score']:
                continue

            # Calculate max eligible amount
            max_eligible = min(
                loan['max_amount'],
                profile['income'] * 30  # 30x monthly income
            )

            # Calculate EMI for requested amount
            if loan_amount and loan_amount <= max_eligible:
                amount = loan_amount
            else:
                amount = max_eligible * 0.5  # Suggest 50% of max

            monthly_rate = loan['interest_rate'] / 12 / 100
            tenure = loan['tenure_months']
            emi = amount * monthly_rate * (1 + monthly_rate)**tenure / ((1 + monthly_rate)**tenure - 1)

            # Check if EMI is affordable
            affordable_emi = profile['monthly_savings'] * 0.6  # Max 60% of savings
            is_affordable = emi <= affordable_emi

            recommendations.append({
                'loan': loan,
                'loan_id': loan_id,
                'max_eligible': max_eligible,
                'suggested_amount': amount,
                'emi': round(emi, 2),
                'total_payable': round(emi * tenure, 2),
                'is_affordable': is_affordable,
                'affordability_score': min(100, (affordable_emi / emi * 100)) if emi > 0 else 0
            })

        # Sort by interest rate (lower is better)
        recommendations.sort(key=lambda x: x['loan']['interest_rate'])

        return {
            'recommendations': recommendations,
            'your_profile': {
                'estimated_credit_score': estimated_credit_score,
                'monthly_income': profile['income'],
                'affordable_emi': profile['monthly_savings'] * 0.6,
                'dti_ratio': profile['dti_ratio']
            }
        }

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

        if not investment_amount:
            investment_amount = max(profile['monthly_savings'] * 0.5, 0)

        recommendations = []

        for inv_id, inv in self.INVESTMENTS.items():
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

            # Affordability
            if investment_amount >= inv['min_investment']:
                score += 20

            # Suggested allocation
            suggested_allocation = self._calculate_allocation(inv, risk_appetite, investment_amount)

            recommendations.append({
                'investment': inv,
                'investment_id': inv_id,
                'score': score,
                'suggested_allocation': suggested_allocation,
                'suggested_amount': round(investment_amount * suggested_allocation / 100, 2),
                'monthly_sip': round(investment_amount * suggested_allocation / 100 / 12, 2),
                'expected_value_1y': round(
                    investment_amount * suggested_allocation / 100 * (1 + inv['expected_return'] / 100),
                    2
                ),
                'match_reason': f"Matches your {risk_appetite} risk profile"
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
                'available_amount': investment_amount,
                'time_horizon': time_horizon
            }
        }

    def recommend_insurance(self, user) -> Dict:
        """
        Recommend insurance products based on life stage and needs.

        Args:
            user: Django user object

        Returns:
            Dict with insurance recommendations
        """
        profile = self.build_user_profile(user)

        recommendations = []

        for ins_id, ins in self.INSURANCE.items():
            score = 0

            # Persona match
            matching_personas = set(profile['persona']) & set(ins['recommended_for'])
            score += len(matching_personas) * 30

            # Affordability
            if ins['premium_estimate'] < profile['income'] * 0.1:
                score += 20

            # Life stage
            if 'Life Insurance' in ins['type']:
                if profile['age'] < 45 and profile['dependents'] > 0:
                    score += 30

            if 'Health Insurance' in ins['type']:
                score += 20  # Always recommended

            recommendations.append({
                'insurance': ins,
                'insurance_id': ins_id,
                'score': score,
                'is_essential': score >= 50,
                'match_reason': self._explain_insurance_match(ins, profile, matching_personas)
            })

        # Sort by score
        recommendations.sort(key=lambda x: x['score'], reverse=True)

        return {
            'recommendations': recommendations,
            'total_annual_premium': sum(r['insurance']['premium_estimate'] for r in recommendations if r['is_essential']),
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

    def _create_diversified_portfolio(self, recommendations: List, amount: float, risk: str) -> Dict:
        """Create a diversified investment portfolio."""
        portfolio = {
            'total_amount': amount,
            'allocations': [],
            'expected_return': 0,
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
                    'expected_return': rec['investment']['expected_return']
                })
                allocated += alloc

        # Calculate weighted average return
        portfolio['expected_return'] = sum(
            a['expected_return'] * a['percentage'] / 100
            for a in portfolio['allocations']
        )

        return portfolio

    def _explain_card_match(self, card: Dict, profile: Dict, matching_personas: set) -> str:
        """Generate explanation for card recommendation."""
        reasons = []

        if matching_personas:
            reasons.append(f"Perfect for {', '.join(matching_personas)}")

        top_cat = profile['top_category']
        if top_cat in card['category_bonuses']:
            bonus = card['category_bonuses'][top_cat]
            reasons.append(f"{bonus}x rewards on {top_cat}")

        if card['annual_fee'] == 0:
            reasons.append("No annual fee")

        return "; ".join(reasons) if reasons else "Good general-purpose card"

    def _explain_insurance_match(self, insurance: Dict, profile: Dict, matching_personas: set) -> str:
        """Generate explanation for insurance recommendation."""
        reasons = []

        if 'has_dependents' in profile['persona'] and 'Life Insurance' in insurance['type']:
            reasons.append("Essential protection for your family")

        if insurance['premium_estimate'] < profile['income'] * 0.05:
            reasons.append("Highly affordable")

        if matching_personas:
            reasons.append(f"Recommended for {', '.join(matching_personas)}")

        return "; ".join(reasons) if reasons else "Good coverage option"


# Singleton instance
recommendation_engine = FinancialRecommendationEngine()
