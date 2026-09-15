"""Synthetic acceptance data, created through the same endpoints as the UI."""
from django.contrib.auth import get_user_model
from django.utils import timezone


PASSWORD = "AcceptanceOnly936!"


def month_start(offset=0):
    today = timezone.localdate()
    index = today.year * 12 + today.month - 1 + offset
    return today.replace(year=index // 12, month=index % 12 + 1, day=1)


def seed_acceptance_user(client):
    response = client.post("/signup/", {
        "username": "acceptance_demo", "email": "acceptance@example.test",
        "first_name": "Asha", "last_name": "Demo", "city": "Bengaluru",
        "country": "India", "monthly_income": "80000", "variable_income": "0",
        "rent_or_emi": "20000", "password1": PASSWORD, "password2": PASSWORD,
    })
    assert response.status_code == 302, response.content[:1000]
    user = get_user_model().objects.get(username="acceptance_demo")
    client.force_login(user)

    def create(path, data):
        result = client.post(path, data, content_type="application/json")
        assert result.status_code == 201, (path, result.status_code, result.content[:2000])
        return result.json()

    account = create("/api/expenses/accounts/", {
        "bank_name": "Demo Bank", "account_number": "DEMO1001",
        "account_holder": "Asha Demo", "account_type": "savings",
        "current_balance": 150000, "is_primary": True,
    })
    loan = create("/api/loans/", {
        "loan_type": "personal", "lender": "Demo Lender", "principal": 120000,
        "interest_rate": 10, "emi": 10000, "tenure_months": 12,
        "remaining_balance": 100000, "start_date": str(month_start(-2)),
    })
    investment = create("/api/investments/", {
        "asset_type": "mutual_fund", "asset_name": "Demo Index Fund",
        "invested_amount": 100000, "current_value": 110000, "monthly_sip": 5000,
        "annual_return_rate": 8, "risk_level": "medium",
    })
    budget = create("/api/budgets/", {
        "month": month_start().strftime("%B %Y"), "base_budget": 30000,
        "inflation_adjusted": 30000,
    })
    transactions = {}
    for offset in (-2, -1, 0):
        rows = [
            ("salary", 80000, "income", "other", "credit", "Demo Employer Salary"),
            ("rent", 20000, "rent", "expense", "debit", "Monthly rent"),
            ("emi", 10000, "loan", "loan", "debit", "Demo Lender EMI"),
            ("groceries", 6000 if offset == 0 else 5000, "groceries", "expense", "debit", "Groceries"),
            ("utilities", 4000 if offset == 0 else 3000, "utilities", "expense", "debit", "Electricity and water"),
        ]
        if offset == 0:
            rows += [
                ("sip", 5000, "investment", "other", "debit", "Monthly investment"),
                ("card", 2000, "credit_card", "other", "debit", "Card payment"),
                ("transfer_out", 10000, "transfer", "other", "debit", "Own account transfer"),
                ("transfer_in", 10000, "transfer", "other", "credit", "Own account transfer"),
                ("review", 60000, "other", "other", "debit", "Unidentified payment"),
            ]
        for name, amount, category, classification, direction, description in rows:
            transactions[f"{offset}:{name}"] = create("/api/expenses/", {
                "amount": amount, "category": category, "classification": classification,
                "direction": direction, "transaction_date": str(month_start(offset)),
                "description": description, "merchant": description,
                "bank_account": account["id"], "external_reference": f"demo-{offset}-{name}",
            })
    return {"user": user, "account": account, "loan": loan,
            "investment": investment, "budget": budget, "transactions": transactions}
