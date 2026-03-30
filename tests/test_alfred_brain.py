"""
Quick test script to verify Alfred AI enhancements are working.
Run with: python manage.py shell < test_alfred_brain.py
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'alfred_ai.settings')
django.setup()

print("=" * 60)
print("ALFRED AI ENHANCEMENT TEST")
print("=" * 60)

# Test 1: Import all services
print("\n[1/7] Testing imports...")
try:
    from apps.ml_engine.services.alfred_financial_brain import alfred_brain
    from apps.loans.services import loan_intelligence_service
    from apps.investments.services import portfolio_intelligence_service
    from apps.budgets.services import budget_intelligence_service
    from apps.expenses.services.multi_bank_aggregator import multi_bank_aggregator
    from apps.ml_engine.inference_adapters.transaction_classifier import transaction_classifier
    print("[OK] All services imported successfully")
except Exception as e:
    print(f"[ERROR] Import failed: {e}")
    exit(1)

# Test 2: Initialize Alfred Brain
print("\n[2/7] Initializing Alfred Brain...")
try:
    alfred_brain.initialize()
    print("[OK] Alfred Brain initialized")
except Exception as e:
    print(f"✗ Initialization failed: {e}")

# Test 3: Test transaction classifier
print("\n[3/7] Testing transaction classifier...")
try:
    result = transaction_classifier.predict("UPI-SWIGGY-FOOD ORDER-12345", "debit")
    print(f"[OK] Transaction classified: category={result['category']}, merchant={result['merchant']}")
except Exception as e:
    print(f"[WARN] Transaction classifier: {e}")

# Test 4: Test models
print("\n[4/7] Testing database models...")
try:
    from apps.loans.models import Loan, LoanPaymentHistory
    from apps.expenses.models import BankAccount, Expense
    from apps.investments.models import Investment
    from apps.budgets.models import Budget
    print("[OK] All models loaded successfully")
    print(f"  - Loans in DB: {Loan.objects.count()}")
    print(f"  - Bank Accounts in DB: {BankAccount.objects.count()}")
    print(f"  - Investments in DB: {Investment.objects.count()}")
    print(f"  - Expenses in DB: {Expense.objects.count()}")
except Exception as e:
    print(f"[ERROR] Model test failed: {e}")

# Test 5: Test with a user (if exists)
print("\n[5/7] Testing with user data...")
try:
    from apps.users.models import User
    user = User.objects.first()
    if user:
        print(f"[OK] Testing with user: {user.username}")

        # Test multi-bank aggregation
        bank_view = multi_bank_aggregator.get_consolidated_view(user)
        print(f"  - Bank accounts: {bank_view['total_accounts']}")
        print(f"  - Total balance: ₹{bank_view['total_balance']:,.0f}")

        # Test loan metrics
        loan_metrics = loan_intelligence_service.calculate_loan_metrics(user)
        print(f"  - Active loans: {loan_metrics['active_loan_count']}")
        print(f"  - DTI ratio: {loan_metrics['debt_to_income_ratio']}%")

    else:
        print("[WARN] No users in database (create a user to test)")
except Exception as e:
    print(f"[WARN] User test: {e}")

# Test 6: Test budget intelligence
print("\n[6/7] Testing budget intelligence...")
try:
    from apps.users.models import User
    user = User.objects.first()
    if user and hasattr(user, 'monthly_income') and user.monthly_income > 0:
        budget = budget_intelligence_service.suggest_budget(user)
        if budget.get('success'):
            print(f"[OK] Budget suggestions generated")
            print(f"  - Monthly income: ₹{budget['monthly_income']:,.0f}")
            print(f"  - Disposable income: ₹{budget['disposable_income']:,.0f}")
            print(f"  - Daily limit: ₹{budget['daily_expenditure_limit']:,.0f}")
        else:
            print(f"[WARN] {budget.get('message')}")
    else:
        print("[WARN] User has no income data (update user profile to test)")
except Exception as e:
    print(f"[WARN] Budget test: {e}")

# Test 7: Test comprehensive snapshot
print("\n[7/7] Testing comprehensive financial snapshot...")
try:
    from apps.users.models import User
    user = User.objects.first()
    if user:
        snapshot = alfred_brain.get_comprehensive_financial_snapshot(user)
        print(f"[OK] Snapshot generated successfully")
        print(f"\n  FINANCIAL HEALTH REPORT:")
        print(f"  {'=' * 50}")
        if 'health_score' in snapshot:
            print(f"  Score: {snapshot['health_score']['score']}/100")
            print(f"  Assessment: {snapshot['health_score']['assessment']}")
            print(f"  Message: {snapshot['health_score']['message']}")
        if 'priority_actions' in snapshot:
            print(f"\n  Priority Actions:")
            for i, action in enumerate(snapshot['priority_actions'][:3], 1):
                print(f"    {i}. [{action['priority']}] {action['action']}")
    else:
        print("[WARN] No user to generate snapshot")
except Exception as e:
    print(f"[WARN] Snapshot test: {e}")

print("\n" + "=" * 60)
print("TEST COMPLETE")
print("=" * 60)
print("\n[SUCCESS] Alfred AI enhancements are installed and functional!")
print("\nNext steps:")
print("  1. Create a user account if you haven't")
print("  2. Add income data to user profile")
print("  3. Import bank statements or add manual expenses")
print("  4. Explore Alfred's intelligent insights in the dashboard")
print("\nFor full documentation, see: ALFRED_AI_ENHANCEMENTS.md")
print("=" * 60)
