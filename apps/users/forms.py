from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import User


class AlfredSignUpForm(UserCreationForm):
    email = forms.EmailField(required=False)
    first_name = forms.CharField(required=False, max_length=150)
    last_name = forms.CharField(required=False, max_length=150)
    city = forms.CharField(required=False, max_length=100)
    country = forms.CharField(required=False, max_length=100)
    monthly_income = forms.FloatField(required=False, min_value=0)
    variable_income = forms.FloatField(required=False, min_value=0)
    rent_or_emi = forms.FloatField(required=False, min_value=0)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = (
            "username",
            "email",
            "first_name",
            "last_name",
            "city",
            "country",
            "monthly_income",
            "variable_income",
            "rent_or_emi",
            "password1",
            "password2",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            css_class = "form-control"
            if name in {"password1", "password2"}:
                field.help_text = ""
            field.widget.attrs["class"] = css_class
            field.widget.attrs.setdefault("placeholder", field.label or name.replace("_", " ").title())

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data.get("email", "")
        user.first_name = self.cleaned_data.get("first_name", "")
        user.last_name = self.cleaned_data.get("last_name", "")
        user.city = self.cleaned_data.get("city", "")
        user.country = self.cleaned_data.get("country", "")
        user.monthly_income = self.cleaned_data.get("monthly_income") or 0
        user.variable_income = self.cleaned_data.get("variable_income") or 0
        user.rent_or_emi = self.cleaned_data.get("rent_or_emi") or 0
        if commit:
            user.save()
        return user
