from django.shortcuts import render
from django.contrib.auth.decorators import login_required

@login_required
def dashboard_view(request):
    return render(request, "dashboard.html")

@login_required
def insights_view(request):
    return render(request, "ai_insights.html")


@login_required
def expenses_view(request):
    return render(request, "expenses/list.html")

@login_required
def budgets_view(request):
    return render(request, "budgets/list.html")

@login_required
def loans_view(request):
    return render(request, "loans/list.html")

@login_required
def investments_view(request):
    return render(request, "investments/list.html")

@login_required
def family_view(request):
    return render(request, "family/list.html")

@login_required
def career_view(request):
    return render(request, "career/list.html")

@login_required
def behavioral_view(request):
    return render(request, "behavioral/list.html")

@login_required
def relationship_view(request):
    return render(request, "relationship/list.html")

@login_required
def risk_view(request):
    return render(request, "risk/list.html")

@login_required
def reports_view(request):
    return render(request, "reports/list.html")
