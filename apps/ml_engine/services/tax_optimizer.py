"""
Tax Optimization Engine
Smart tax-saving suggestions for Indian Income Tax
"""
from datetime import date
from decimal import Decimal
from typing import Dict, List, Optional
from django.utils import timezone
from apps.loans.money import loan_money, loan_money_float

from .tax_policy import calculate_income_tax, get_policy


class TaxOptimizerService:
    """
    AI-powered tax optimization for Indian users.
    Provides tax calculations, deductions, and investment suggestions under various IT Act sections.
    """

    # Tax Deductions (Old Regime)
    DEDUCTIONS = {
        '80C': {
            'name': 'Section 80C - Investments & Expenses',
            'max_limit': 150000,
            'instruments': [
                'PPF (Public Provident Fund)',
                'ELSS (Equity Linked Savings Scheme)',
                'NSC (National Savings Certificate)',
                'Tax Saver FD',
                'Life Insurance Premium',
                'Principal repayment on Home Loan',
                'Tuition Fees (2 children)',
                'NPS (Tier-1 Account) - Part of 80C',
            ]
        },
        '80CCD(1B)': {
            'name': 'Section 80CCD(1B) - Additional NPS',
            'max_limit': 50000,
            'instruments': ['NPS (Additional contribution beyond 80C)']
        },
        '80D': {
            'name': 'Section 80D - Health Insurance',
            'max_limit': 75000,  # 25K self + 50K parents (senior citizens)
            'instruments': [
                'Health Insurance Premium - Self & Family (max ₹25,000)',
                'Health Insurance Premium - Parents (max ₹50,000 if senior)',
                'Preventive Health Checkup (max ₹5,000)'
            ]
        },
        '80E': {
            'name': 'Section 80E - Education Loan Interest',
            'max_limit': None,  # No upper limit
            'instruments': ['Interest on Education Loan']
        },
        '80G': {
            'name': 'Section 80G - Donations',
            'max_limit': None,  # Percentage of income
            'instruments': ['Donations to approved charities (50-100% deductible)']
        },
        '24B': {
            'name': 'Section 24 - Home Loan Interest',
            'max_limit': 200000,  # Self-occupied property
            'instruments': ['Interest on Home Loan']
        },
        'HRA': {
            'name': 'HRA - House Rent Allowance',
            'max_limit': None,  # Complex calculation
            'instruments': ['House Rent Allowance']
        }
    }

    def calculate_tax(self, annual_income, regime: str = 'old', deductions=None, **policy_options) -> Dict:
        """Use the versioned Decimal policy; see returned year, scope and sources."""
        return calculate_income_tax(annual_income, regime, deductions, **policy_options)

    def compare_regimes(self, annual_income, deductions=None, **policy_options) -> Dict:
        """
        Compare old vs new tax regime and recommend better option.

        Args:
            annual_income: Annual gross income
            deductions: Deductions available (for old regime)

        Returns:
            Dict with comparison and recommendation
        """
        if deductions is None:
            deductions = {}

        old_regime_tax = self.calculate_tax(annual_income, 'old', deductions, **policy_options)
        new_regime_tax = self.calculate_tax(annual_income, 'new', deductions, **policy_options)

        savings = old_regime_tax['final_tax'] - new_regime_tax['final_tax']

        if savings > 0:
            recommendation = 'new'
            message = f"New regime saves you ₹{abs(savings):,.0f} annually"
        elif savings < 0:
            recommendation = 'old'
            message = f"Old regime saves you ₹{abs(savings):,.0f} annually"
        else:
            recommendation = 'either'
            message = "Both regimes result in the same tax"

        return {
            'old_regime': old_regime_tax,
            'new_regime': new_regime_tax,
            'savings': abs(savings),
            'recommendation': recommendation,
            'message': message,
            'comparison_points': self._generate_comparison_points(old_regime_tax, new_regime_tax)
        }

    def suggest_tax_saving_investments(self, user, target_savings: Optional[float] = None,
                                      *, annual_income=None, deductions=None, **policy_options) -> Dict:
        """
        Suggest tax-saving investment strategy.

        Args:
            user: Django user object
            target_savings: Desired tax savings (optional)

        Returns:
            Dict with investment suggestions
        """
        policy = get_policy('old', **policy_options)
        if annual_income is None:
            annual_income = user.confirmed_annual_income

        current_deductions = deductions or {}

        # Calculate current tax
        current_tax = self.calculate_tax(annual_income, 'old', current_deductions, **policy_options)

        # Suggest additional investments
        suggestions = []

        # 80C - Up to 1.5L
        current_80c = float(current_deductions.get('80C', 0))
        available_80c = 150000 - current_80c

        if available_80c > 0:
            suggestions.append({
                'section': '80C',
                'current_investment': current_80c,
                'max_limit': 150000,
                'available_limit': available_80c,
                'tax_benefit': available_80c * 0.3,  # Assuming 30% tax bracket
                'instruments': [
                    {
                        'name': 'ELSS Mutual Fund',
                        'recommended_amount': min(50000, available_80c),
                        'lock_in': '3 years',
                        'returns': '12-15% expected',
                        'priority': 'High'
                    },
                    {
                        'name': 'PPF',
                        'recommended_amount': min(70000, available_80c),
                        'lock_in': '15 years',
                        'returns': '7-7.5% (tax-free)',
                        'priority': 'Medium'
                    },
                    {
                        'name': 'NPS Tier-1',
                        'recommended_amount': min(50000, available_80c),
                        'lock_in': 'Till retirement',
                        'returns': '8-10% expected',
                        'priority': 'Medium'
                    }
                ]
            })

        # 80CCD(1B) - Additional 50K for NPS
        current_nps_additional = float(current_deductions.get('80CCD(1B)', 0))
        available_nps = 50000 - current_nps_additional

        if available_nps > 0:
            suggestions.append({
                'section': '80CCD(1B)',
                'current_investment': current_nps_additional,
                'max_limit': 50000,
                'available_limit': available_nps,
                'tax_benefit': available_nps * 0.3,
                'instruments': [{
                    'name': 'NPS Additional Contribution',
                    'recommended_amount': available_nps,
                    'lock_in': 'Till retirement',
                    'returns': '8-10% expected',
                    'priority': 'High'
                }]
            })

        # 80D - Health Insurance
        current_80d = float(current_deductions.get('80D', 0))
        # Assume max 75K (25K self + 50K parents if senior)
        available_80d = 75000 - current_80d

        if available_80d > 0:
            suggestions.append({
                'section': '80D',
                'current_investment': current_80d,
                'max_limit': 75000,
                'available_limit': available_80d,
                'tax_benefit': available_80d * 0.3,
                'instruments': [{
                    'name': 'Health Insurance Premium',
                    'recommended_amount': 25000,  # For self
                    'lock_in': '1 year',
                    'returns': 'Tax benefit + Health coverage',
                    'priority': 'Critical'
                }]
            })

        # Calculate total potential savings
        total_additional_investment = sum(s['available_limit'] for s in suggestions)
        total_tax_benefit = sum(s['tax_benefit'] for s in suggestions)

        # New tax with suggested investments
        new_deductions = current_deductions.copy()
        new_deductions['80C'] = 150000
        new_deductions['80CCD(1B)'] = 50000
        new_deductions['80D'] = 75000

        optimized_tax = self.calculate_tax(annual_income, 'old', new_deductions, **policy_options)

        return {
            'calculation_status': 'ESTIMATED',
            'financial_year': policy.financial_year,
            'assumptions': [
                'Only deductions confirmed for the selected financial year are used for the current tax estimate.',
                'Action-level benefits assume a 30% slab; actual overall savings use the selected tax policy.',
                'The 80D scenario assumes eligible self/family and senior-parent premiums.',
                'Investment returns and lock-in descriptions are planning references, not verified offers.',
            ],
            'current_tax': current_tax['final_tax'],
            'optimized_tax': optimized_tax['final_tax'],
            'potential_savings': current_tax['final_tax'] - optimized_tax['final_tax'],
            'required_investment': total_additional_investment,
            'roi_on_tax_savings': (total_tax_benefit / total_additional_investment * 100) if total_additional_investment > 0 else 0,
            'suggestions': suggestions,
            'action_plan': self._create_investment_action_plan(suggestions)
        }

    def calculate_hra_exemption(self, basic_salary: float, hra_received: float,
                                rent_paid: float, metro_city: bool = True) -> Dict:
        """
        Calculate HRA exemption as per IT rules.

        Args:
            basic_salary: Monthly basic salary
            hra_received: Monthly HRA received
            rent_paid: Monthly rent paid
            metro_city: Whether living in metro city

        Returns:
            Dict with HRA exemption details
        """
        # Annual values
        annual_basic = basic_salary * 12
        annual_hra = hra_received * 12
        annual_rent = rent_paid * 12

        # Three conditions for HRA exemption
        condition_1 = annual_hra  # Actual HRA received

        metro_percent = 50 if metro_city else 40
        condition_2 = annual_basic * metro_percent / 100  # 50% of basic (metro) or 40% (non-metro)

        condition_3 = annual_rent - (annual_basic * 0.1)  # Rent - 10% of basic

        # Exemption is minimum of three
        exemption = max(0, min(condition_1, condition_2, condition_3))

        taxable_hra = annual_hra - exemption

        return {
            'annual_hra_received': annual_hra,
            'condition_1_actual_hra': condition_1,
            'condition_2_percent_basic': condition_2,
            'condition_3_rent_minus_10pct': condition_3,
            'hra_exemption': exemption,
            'taxable_hra': taxable_hra,
            'tax_saved': exemption * 0.3,  # Assuming 30% bracket
            'monthly_exemption': exemption / 12,
            'recommendation': self._hra_recommendation(basic_salary, hra_received, rent_paid, metro_city)
        }

    def recorded_home_loan_payments(self, user, *, financial_year=None) -> Dict[str, float] | None:
        """Show matched repayments from the selected year separately from qualifying deductions."""
        from apps.loans.models import Loan, LoanPaymentHistory

        if financial_year is None:
            fy_start, fy_end = self._current_financial_year_bounds()
        else:
            policy = get_policy(financial_year=financial_year)
            start_year = int(policy.financial_year[:4])
            fy_start, fy_end = date(start_year, 4, 1), date(start_year + 1, 3, 31)

        home_loans = Loan.objects.filter(
            user=user, loan_type="home", verification_status="confirmed",
        ).in_rupee_totals()
        principal_total = Decimal("0")
        interest_total = Decimal("0")
        payments = LoanPaymentHistory.objects.filter(
            loan__in=home_loans,
            payment_date__range=(fy_start, min(fy_end, timezone.localdate())),
            match_status="matched",
        ).only("principal_paid", "principal_component", "interest_paid", "interest_component")
        for payment in payments:
            principal_total += loan_money(payment.principal_paid or payment.principal_component)
            interest_total += loan_money(payment.interest_paid or payment.interest_component)
        if not (principal_total or interest_total):
            return None
        return {"principal_paid": loan_money_float(principal_total), "interest_paid": loan_money_float(interest_total)}

    def _current_financial_year_bounds(self, today: date | None = None) -> tuple[date, date]:
        today = today or timezone.localdate()
        start_year = today.year if today.month >= 4 else today.year - 1
        return date(start_year, 4, 1), date(start_year + 1, 3, 31)

    def _generate_comparison_points(self, old_tax: Dict, new_tax: Dict) -> List[str]:
        """Generate key comparison points between regimes."""
        points = []

        points.append(f"Old Regime Tax: ₹{old_tax['final_tax']:,.0f}")
        points.append(f"New Regime Tax: ₹{new_tax['final_tax']:,.0f}")

        if old_tax['total_deductions'] > 0:
            points.append(f"Deductions utilized in Old Regime: ₹{old_tax['total_deductions']:,.0f}")

        points.append(f"Old Regime Effective Rate: {old_tax['effective_tax_rate']:.2f}%")
        points.append(f"New Regime Effective Rate: {new_tax['effective_tax_rate']:.2f}%")

        return points

    def _create_investment_action_plan(self, suggestions: List[Dict]) -> List[Dict]:
        """Create prioritized action plan for tax-saving investments."""
        actions = []

        for suggestion in suggestions:
            section = suggestion['section']
            available = suggestion['available_limit']

            if section == '80D':
                actions.append({
                    'priority': 1,
                    'action': 'Buy Health Insurance',
                    'amount': 25000,
                    'tax_benefit': 7500,
                    'urgency': 'High - Essential for health protection'
                })

            elif section == '80C' and available > 0:
                actions.append({
                    'priority': 2,
                    'action': 'Invest in ELSS Mutual Funds',
                    'amount': min(50000, available),
                    'tax_benefit': min(50000, available) * 0.3,
                    'urgency': 'High - Best returns with 3-year lock-in'
                })

            elif section == '80CCD(1B)':
                actions.append({
                    'priority': 3,
                    'action': 'Additional NPS Contribution',
                    'amount': 50000,
                    'tax_benefit': 15000,
                    'urgency': 'Medium - Good for retirement planning'
                })

        return sorted(actions, key=lambda x: x['priority'])

    def _hra_recommendation(self, basic: float, hra: float, rent: float, metro: bool) -> str:
        """Generate recommendation for HRA optimization."""
        ideal_rent = (basic * 0.6) if metro else (basic * 0.5)

        if rent < ideal_rent:
            return f"Consider increasing rent to ₹{ideal_rent:,.0f}/month for maximum HRA benefit"
        else:
            return "Your rent is optimized for maximum HRA exemption"


# Singleton instance
tax_optimizer = TaxOptimizerService()
