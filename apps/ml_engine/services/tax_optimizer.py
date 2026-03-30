"""
Tax Optimization Engine
Smart tax-saving suggestions for Indian Income Tax
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from django.utils import timezone
from django.db.models import Sum


class TaxOptimizerService:
    """
    AI-powered tax optimization for Indian users.
    Provides tax calculations, deductions, and investment suggestions under various IT Act sections.
    """

    # Income Tax Slabs for FY 2025-26 (Old Regime)
    OLD_REGIME_SLABS = [
        (250000, 0),      # Up to 2.5L - 0%
        (500000, 5),      # 2.5L - 5L - 5%
        (1000000, 20),    # 5L - 10L - 20%
        (float('inf'), 30)  # Above 10L - 30%
    ]

    # Income Tax Slabs for FY 2025-26 (New Regime)
    NEW_REGIME_SLABS = [
        (300000, 0),      # Up to 3L - 0%
        (700000, 5),      # 3L - 7L - 5%
        (1000000, 10),    # 7L - 10L - 10%
        (1200000, 15),    # 10L - 12L - 15%
        (1500000, 20),    # 12L - 15L - 20%
        (float('inf'), 30)  # Above 15L - 30%
    ]

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

    def __init__(self):
        self.cess = 4  # 4% Health and Education Cess

    def calculate_tax(self, annual_income: float, regime: str = 'old',
                     deductions: Dict[str, float] = None) -> Dict:
        """
        Calculate income tax for the given income.

        Args:
            annual_income: Annual gross income
            regime: 'old' or 'new' tax regime
            deductions: Dict of section -> amount deductions

        Returns:
            Dict with tax calculation breakdown
        """
        if deductions is None:
            deductions = {}

        slabs = self.OLD_REGIME_SLABS if regime == 'old' else self.NEW_REGIME_SLABS

        # Calculate taxable income
        if regime == 'old':
            # Old regime: Apply deductions
            total_deductions = sum(deductions.values())
            # Standard deduction
            standard_deduction = 50000
            taxable_income = annual_income - standard_deduction - total_deductions
        else:
            # New regime: No deductions except standard deduction
            standard_deduction = 75000  # Increased in new regime
            taxable_income = annual_income - standard_deduction

        # Ensure taxable income is not negative
        taxable_income = max(0, taxable_income)

        # Calculate tax slab-wise
        tax = 0
        previous_limit = 0
        slab_breakdown = []

        for limit, rate in slabs:
            if taxable_income > previous_limit:
                slab_income = min(taxable_income, limit) - previous_limit
                slab_tax = slab_income * rate / 100

                slab_breakdown.append({
                    'range': f'₹{previous_limit:,.0f} - ₹{limit:,.0f}' if limit != float('inf') else f'Above ₹{previous_limit:,.0f}',
                    'rate': rate,
                    'income_in_slab': slab_income,
                    'tax': slab_tax
                })

                tax += slab_tax
                previous_limit = limit

            if taxable_income <= limit:
                break

        # Add cess
        cess_amount = tax * self.cess / 100
        total_tax = tax + cess_amount

        # Rebate under Section 87A (if applicable)
        rebate = 0
        if regime == 'new' and taxable_income <= 700000:
            rebate = min(total_tax, 25000)  # Max rebate ₹25,000
        elif regime == 'old' and taxable_income <= 500000:
            rebate = min(total_tax, 12500)  # Max rebate ₹12,500

        final_tax = max(0, total_tax - rebate)

        return {
            'annual_income': annual_income,
            'regime': regime,
            'standard_deduction': standard_deduction,
            'total_deductions': sum(deductions.values()) if regime == 'old' else 0,
            'deduction_breakdown': deductions if regime == 'old' else {},
            'taxable_income': taxable_income,
            'base_tax': tax,
            'cess': cess_amount,
            'total_tax_before_rebate': total_tax,
            'rebate_87a': rebate,
            'final_tax': final_tax,
            'effective_tax_rate': (final_tax / annual_income * 100) if annual_income > 0 else 0,
            'slab_breakdown': slab_breakdown,
            'monthly_tax': final_tax / 12,
            'take_home_monthly': (annual_income - final_tax) / 12
        }

    def compare_regimes(self, annual_income: float, deductions: Dict[str, float] = None) -> Dict:
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

        old_regime_tax = self.calculate_tax(annual_income, 'old', deductions)
        new_regime_tax = self.calculate_tax(annual_income, 'new', {})

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

    def suggest_tax_saving_investments(self, user, target_savings: Optional[float] = None) -> Dict:
        """
        Suggest tax-saving investment strategy.

        Args:
            user: Django user object
            target_savings: Desired tax savings (optional)

        Returns:
            Dict with investment suggestions
        """
        from apps.investments.models import Investment

        annual_income = getattr(user, 'monthly_income', 50000) * 12

        # Calculate current deductions
        current_deductions = self._calculate_current_deductions(user)

        # Calculate current tax
        current_tax = self.calculate_tax(annual_income, 'old', current_deductions)

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

        optimized_tax = self.calculate_tax(annual_income, 'old', new_deductions)

        return {
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

    def _calculate_current_deductions(self, user) -> Dict[str, float]:
        """Calculate user's current tax deductions from their financial data."""
        from apps.investments.models import Investment
        from apps.loans.models import Loan

        deductions = {}

        # 80C - Approximate from tagged tax-saving instruments already tracked in portfolio.
        qualifying_tokens = ("elss", "ppf", "nsc", "tax saver", "nps")
        investments_80c = 0
        for investment in Investment.objects.filter(user=user):
            name = f"{investment.asset_name} {investment.notes}".lower()
            if any(token in name for token in qualifying_tokens):
                investments_80c += investment.current_value or investment.invested_amount or 0

        deductions['80C'] = min(investments_80c, 150000)

        # 24 - Home loan interest (mock for now)
        home_loans = Loan.objects.filter(user=user, loan_type='home', is_active=True)
        if home_loans.exists():
            # Estimate interest component (simplified)
            deductions['24B'] = 200000  # Mock value

        return deductions

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
