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
            annual_income = (getattr(user, 'monthly_income', 0) or 0) * 12

        # Calculate current deductions
        current_deductions = deductions if deductions is not None else self._calculate_current_deductions(
            user, financial_year=policy.financial_year,
        )

        # Calculate current tax
        current_tax = self.calculate_tax(annual_income, 'old', current_deductions, **policy_options)

        # Suggest additional investments
        suggestions = []

        # 80C - Up to 1.5L
        current_80c = current_deductions.get('80C', 0)
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
        current_nps_additional = current_deductions.get('80CCD(1B)', 0)
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
        current_80d = current_deductions.get('80D', 0)
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
                'Deduction eligibility must be reviewed; portfolio values are only deduction leads.',
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

    def calculate_home_loan_benefits(self, loan_principal_paid: float,
                                    loan_interest_paid: float,
                                    is_first_home: bool = True) -> Dict:
        """
        Calculate tax benefits on home loan.

        Args:
            loan_principal_paid: Principal repayment in FY
            loan_interest_paid: Interest paid in FY
            is_first_home: First time home buyer

        Returns:
            Dict with home loan tax benefits
        """
        # Principal under 80C (max 1.5L)
        principal_benefit = min(loan_principal_paid, 150000)
        principal_tax_saved = principal_benefit * 0.3  # 30% bracket

        # Interest under Section 24 (max 2L for self-occupied)
        interest_benefit = min(loan_interest_paid, 200000)
        interest_tax_saved = interest_benefit * 0.3

        # Additional benefit for first-time home buyers under 80EEA (max 1.5L additional)
        additional_benefit = 0
        if is_first_home:
            # 80EEA: Additional interest deduction up to 1.5L
            additional_interest = max(0, min(loan_interest_paid - 200000, 150000))
            additional_benefit = additional_interest
            interest_tax_saved += additional_benefit * 0.3

        total_deduction = principal_benefit + interest_benefit + additional_benefit
        total_tax_saved = total_deduction * 0.3

        return {
            'principal_paid': loan_principal_paid,
            'principal_deduction': principal_benefit,
            'principal_tax_saved': principal_tax_saved,
            'interest_paid': loan_interest_paid,
            'interest_deduction_24': interest_benefit,
            'interest_deduction_80eea': additional_benefit,
            'total_interest_deduction': interest_benefit + additional_benefit,
            'interest_tax_saved': interest_tax_saved,
            'total_deduction': total_deduction,
            'total_tax_saved': total_tax_saved,
            'effective_interest_rate': self._calculate_effective_rate(
                loan_interest_paid, total_tax_saved
            )
        }

    def _calculate_current_deductions(self, user, *, financial_year=None) -> Dict[str, float]:
        """Calculate user's current tax deductions from their financial data."""
        from apps.investments.models import Investment
        from apps.loans.models import Loan, LoanPaymentHistory

        deductions = {}
        if financial_year is None:
            fy_start, fy_end = self._current_financial_year_bounds()
        else:
            policy = get_policy(financial_year=financial_year)
            start_year = int(policy.financial_year[:4])
            fy_start, fy_end = date(start_year, 4, 1), date(start_year + 1, 3, 31)

        # 80C - Approximate from tagged tax-saving instruments already tracked in portfolio.
        qualifying_tokens = ("elss", "ppf", "nsc", "tax saver", "nps")
        investments_80c = 0
        for investment in Investment.objects.filter(user=user):
            name = f"{investment.asset_name} {investment.notes}".lower()
            if any(token in name for token in qualifying_tokens):
                investments_80c += investment.current_value or investment.invested_amount or 0

        home_loans = Loan.objects.filter(user=user, loan_type='home', verification_status='confirmed')
        home_principal_paid = Decimal("0")
        home_interest_paid = Decimal("0")
        for payment in LoanPaymentHistory.objects.filter(
            loan__in=home_loans,
            payment_date__gte=fy_start,
            payment_date__lte=fy_end,
        ).exclude(match_status="rejected").only(
            "principal_paid",
            "principal_component",
            "interest_paid",
            "interest_component",
        ):
            home_principal_paid += loan_money(payment.principal_paid or payment.principal_component)
            home_interest_paid += loan_money(payment.interest_paid or payment.interest_component)

        deductions['80C'] = loan_money_float(min(Decimal(str(investments_80c)) + home_principal_paid, Decimal("150000")))

        if home_interest_paid > 0:
            deductions['24B'] = loan_money_float(min(home_interest_paid, Decimal("200000")))

        return deductions

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

    def _calculate_effective_rate(self, interest_paid: float, tax_saved: float) -> float:
        """Calculate effective interest rate after tax benefit."""
        if interest_paid == 0:
            return 0

        effective_interest = interest_paid - tax_saved
        # Simplified calculation
        return (effective_interest / interest_paid) * 8.5  # Assuming 8.5% nominal rate


# Singleton instance
tax_optimizer = TaxOptimizerService()
