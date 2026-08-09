from django import forms

from .models import CareerJobAnalysis
from .services.job_intelligence import job_intelligence


class CareerJobAnalysisChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        parts = [
            f"#{obj.id}",
            getattr(obj.user, "username", ""),
            obj.job_title or "Untitled role",
            obj.company or "Unknown company",
            obj.location or "Unknown location",
        ]
        return " | ".join(part for part in parts if part)


class CareerOpportunityOutcomeForm(forms.Form):
    analysis = CareerJobAnalysisChoiceField(
        queryset=CareerJobAnalysis.objects.none(),
        label="Job analysis",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    outcome = forms.ChoiceField(
        choices=(("accepted", "Accepted"), ("rejected", "Rejected")),
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    salary_text = forms.CharField(
        required=False,
        max_length=160,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "INR 24-30 LPA",
            }
        ),
    )
    salary_min = forms.DecimalField(
        required=False,
        min_value=0,
        decimal_places=2,
        max_digits=14,
        widget=forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
    )
    salary_max = forms.DecimalField(
        required=False,
        min_value=0,
        decimal_places=2,
        max_digits=14,
        widget=forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
    )
    salary_currency = forms.CharField(
        initial="INR",
        max_length=8,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    salary_period = forms.ChoiceField(
        choices=(("year", "Year"), ("month", "Month"), ("hour", "Hour")),
        initial="year",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    source_url = forms.URLField(
        required=True,
        widget=forms.URLInput(attrs={"class": "form-control", "placeholder": "https://"}),
    )
    location = forms.CharField(
        required=True,
        max_length=180,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Bengaluru, Karnataka, India"}),
    )
    notes = forms.CharField(
        required=False,
        max_length=1200,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 3}),
    )
    rejection_reason = forms.CharField(
        required=False,
        max_length=600,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 2}),
    )

    def __init__(self, *args, analyses_queryset=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["analysis"].queryset = analyses_queryset or CareerJobAnalysis.objects.select_related("user").order_by(
            "-updated_at",
            "-id",
        )
        self.normalized_outcome = None
        self.contract_status = None

    def clean(self):
        cleaned = super().clean()
        analysis = cleaned.get("analysis")
        outcome = cleaned.get("outcome")
        salary_text = str(cleaned.get("salary_text") or "").strip()
        salary_min = cleaned.get("salary_min")
        salary_max = cleaned.get("salary_max")
        notes = str(cleaned.get("notes") or "").strip()
        rejection_reason = str(cleaned.get("rejection_reason") or "").strip()

        if not salary_text and (salary_min is None or salary_max is None):
            self.add_error(None, "Enter either salary text or both salary minimum and salary maximum.")
        if salary_min is not None and salary_max is not None and salary_min > salary_max:
            self.add_error("salary_max", "Salary maximum must be greater than or equal to salary minimum.")
        if outcome == "accepted" and not notes:
            self.add_error("notes", "Accepted outcomes require notes.")
        if outcome == "rejected" and not rejection_reason:
            self.add_error("rejection_reason", "Rejected outcomes require a rejection reason.")
        if self.errors or analysis is None:
            return cleaned

        payload = {
            "outcome": outcome,
            "salary_text": salary_text,
            "salary_min": salary_min,
            "salary_max": salary_max,
            "salary_currency": str(cleaned.get("salary_currency") or "INR").strip().upper(),
            "salary_period": cleaned.get("salary_period") or "year",
            "source_url": cleaned.get("source_url"),
            "location": cleaned.get("location"),
            "notes": notes,
            "rejection_reason": rejection_reason,
        }
        try:
            self.normalized_outcome = job_intelligence.normalize_opportunity_outcome(analysis, payload)
        except ValueError as exc:
            raise forms.ValidationError(str(exc)) from exc

        self.contract_status = job_intelligence.opportunity_outcome_contract_status(self.normalized_outcome)
        if not self.contract_status["valid"]:
            raise forms.ValidationError(
                "Opportunity outcome is missing maturity proof: "
                + ", ".join(self.contract_status["missing"])
            )
        return cleaned

    def save(self):
        if self.normalized_outcome is None:
            raise ValueError("Cannot save an unvalidated opportunity outcome.")
        analysis = self.cleaned_data["analysis"]
        extracted_payload = dict(analysis.extracted_payload or {})
        extracted_payload["opportunity_outcome"] = self.normalized_outcome
        analysis.extracted_payload = extracted_payload
        analysis.save(update_fields=["extracted_payload", "updated_at"])
        return analysis
