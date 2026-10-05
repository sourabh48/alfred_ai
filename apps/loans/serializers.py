from decimal import ROUND_HALF_UP
from math import isfinite

from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from .models import Loan, LoanClosureDocument, LoanForeclosureSnapshot, LoanImportDocument
from .money import loan_money, loan_money_float


class LoanForeclosureSnapshotSerializer(serializers.ModelSerializer):
    document_type_label = serializers.CharField(source="get_document_type_display", read_only=True)
    reconciliation_status_label = serializers.CharField(source="get_reconciliation_status_display", read_only=True)
    settlement_allocation = serializers.SerializerMethodField()

    class Meta:
        model = LoanForeclosureSnapshot
        fields = (
            "id",
            "document_type",
            "document_type_label",
            "lender_name",
            "borrower_name",
            "loan_account_number",
            "statement_date",
            "effective_closure_date",
            "due_by_date",
            "outstanding_principal",
            "accrued_interest",
            "foreclosure_charges",
            "taxes_gst",
            "overdue_charges",
            "total_amount_payable",
            "classification_confidence",
            "linkage_confidence",
            "linkage_notes",
            "reconciliation_status",
            "reconciliation_status_label",
            "reconciliation_confidence",
            "matched_payment_total",
            "matched_emi_transaction_ids",
            "matched_closure_transaction_ids",
            "reconciliation_notes",
            "settlement_allocation",
            "updated_at",
        )
        read_only_fields = fields

    def get_settlement_allocation(self, obj):
        return dict((obj.audit_payload or {}).get("settlement_allocation") or {})

    def to_representation(self, instance):
        data = super().to_representation(instance)
        for field in ("outstanding_principal", "accrued_interest", "foreclosure_charges", "taxes_gst",
                      "overdue_charges", "total_amount_payable", "matched_payment_total"):
            data[field] = loan_money_float(getattr(instance, field))
        return data


class LoanSerializer(serializers.ModelSerializer):
    principal = serializers.DecimalField(max_digits=14, decimal_places=2, coerce_to_string=False, rounding=ROUND_HALF_UP)
    emi = serializers.DecimalField(max_digits=14, decimal_places=2, coerce_to_string=False, rounding=ROUND_HALF_UP)
    remaining_balance = serializers.DecimalField(max_digits=14, decimal_places=2, coerce_to_string=False,
                                                rounding=ROUND_HALF_UP, required=False, allow_null=True)
    home_purchase_price = serializers.DecimalField(max_digits=14, decimal_places=2, coerce_to_string=False,
                                                  rounding=ROUND_HALF_UP, required=False)
    home_down_payment = serializers.DecimalField(max_digits=14, decimal_places=2, coerce_to_string=False,
                                                rounding=ROUND_HALF_UP, required=False)
    home_other_upfront_payments = serializers.DecimalField(max_digits=14, decimal_places=2, coerce_to_string=False,
                                                         rounding=ROUND_HALF_UP, required=False)
    confirm_estimate = serializers.BooleanField(write_only=True, required=False, default=False)
    current_status = serializers.CharField(read_only=True)
    loan_type_label = serializers.CharField(source="get_loan_type_display", read_only=True)
    consolidated_into_id = serializers.IntegerField(source="consolidated_into.id", read_only=True)
    closure_documents_count = serializers.SerializerMethodField()
    latest_foreclosure_snapshot = serializers.SerializerMethodField()
    home_upfront_cash_invested = serializers.SerializerMethodField()
    home_property_acquisition_cost = serializers.SerializerMethodField()

    class Meta:
        model = Loan
        fields = (
            "id",
            "user",
            "loan_type",
            "loan_type_label",
            "lender",
            "loan_account_number",
            "principal",
            "interest_rate",
            "emi",
            "tenure_months",
            "remaining_balance",
            "home_purchase_price",
            "home_down_payment",
            "home_other_upfront_payments",
            "home_upfront_cash_invested",
            "home_property_acquisition_cost",
            "start_date",
            "closed_on",
            "is_active",
            "current_status",
            "verification_status",
            "verification_source",
            "verified_at",
            "confirm_estimate",
            "status",
            "consolidation_group",
            "consolidated_into",
            "consolidated_into_id",
            "closure_reason",
            "closure_documents_count",
            "latest_foreclosure_snapshot",
            "notes",
            "created_at",
        )
        read_only_fields = ("user", "created_at", "verification_status", "verification_source", "verified_at")

    def create(self, validated_data):
        validated_data.pop("confirm_estimate", None)
        if validated_data.get("remaining_balance") is not None:
            validated_data.update(verification_status="confirmed", verification_source="user", verified_at=timezone.now())
        return super().create(validated_data)

    @transaction.atomic
    def update(self, instance, validated_data):
        instance = Loan.objects.select_for_update().get(pk=instance.pk, user=instance.user)
        confirm = validated_data.pop("confirm_estimate", False)
        if confirm or (instance.is_confirmed and "remaining_balance" in validated_data):
            validated_data.update(verification_status="confirmed", verification_source="user", verified_at=timezone.now())
        return super().update(instance, validated_data)

    def get_closure_documents_count(self, obj):
        return obj.closure_documents.count()

    def validate_consolidated_into(self, value):
        user = getattr(self.context.get("request"), "user", None)
        if value is not None and (not user or value.user_id != user.pk):
            raise serializers.ValidationError("Choose one of your own loans.")
        if value is not None and self.instance is not None and value.pk == self.instance.pk:
            raise serializers.ValidationError("A loan cannot be consolidated into itself.")
        return value

    def get_latest_foreclosure_snapshot(self, obj):
        snapshot = obj.foreclosure_snapshots.order_by("-updated_at", "-id").first()
        if snapshot is None:
            return None
        return LoanForeclosureSnapshotSerializer(snapshot).data

    def get_home_upfront_cash_invested(self, obj):
        return obj.resolved_home_upfront_cash_invested

    def get_home_property_acquisition_cost(self, obj):
        return obj.resolved_home_property_acquisition_cost

    def validate(self, attrs):
        if attrs.get("confirm_estimate"):
            required = {"lender", "principal", "interest_rate", "emi", "tenure_months", "remaining_balance", "start_date"}
            missing = sorted(required - attrs.keys())
            if missing:
                raise serializers.ValidationError({"confirm_estimate": f"Review and submit all loan terms: {', '.join(missing)}."})
            if attrs["remaining_balance"] is None or not attrs["lender"].strip():
                raise serializers.ValidationError("Confirm the lender and current remaining balance.")
        for name in ("principal", "interest_rate", "emi", "remaining_balance", "home_purchase_price", "home_down_payment", "home_other_upfront_payments"):
            value = attrs.get(name)
            if value is not None and (not isfinite(value) or value < 0):
                raise serializers.ValidationError({name: "Enter a finite, non-negative amount."})
        if "tenure_months" in attrs and attrs["tenure_months"] < 1:
            raise serializers.ValidationError({"tenure_months": "Tenure must be at least one month."})
        principal = attrs.get("principal", getattr(self.instance, "principal", 0))
        emi = attrs.get("emi", getattr(self.instance, "emi", 0))
        start_date = attrs.get("start_date", getattr(self.instance, "start_date", None))
        closed_on = attrs.get("closed_on", getattr(self.instance, "closed_on", None))
        remaining_balance = attrs.get("remaining_balance", getattr(self.instance, "remaining_balance", None))
        loan_type = attrs.get("loan_type", getattr(self.instance, "loan_type", "other"))
        home_purchase_price = loan_money(attrs.get("home_purchase_price", getattr(self.instance, "home_purchase_price", 0)))
        home_down_payment = loan_money(attrs.get("home_down_payment", getattr(self.instance, "home_down_payment", 0)))
        home_other_upfront_payments = loan_money(
            attrs.get("home_other_upfront_payments", getattr(self.instance, "home_other_upfront_payments", 0)) or 0
        )
        if principal <= 0:
            raise serializers.ValidationError("Principal must be greater than zero.")
        if emi <= 0 and (self.instance is None or "emi" in attrs or attrs.get("confirm_estimate")):
            raise serializers.ValidationError("EMI must be greater than zero.")
        if home_purchase_price < 0 or home_down_payment < 0 or home_other_upfront_payments < 0:
            raise serializers.ValidationError("Home-loan upfront cash fields cannot be negative.")
        if closed_on and start_date and closed_on < start_date:
            raise serializers.ValidationError("Closing date cannot be earlier than the loan start date.")
        if self.instance and (attrs.get("is_active") is False or closed_on):
            if not self.instance.closure_documents.filter(verification_status="verified").exists() and not attrs.get("consolidated_into"):
                raise serializers.ValidationError("A verified foreclosure or closure document is required before manually closing a loan.")

        if loan_type == "home" and home_purchase_price > 0:
            if home_purchase_price < loan_money(principal):
                raise serializers.ValidationError(
                    "Property purchase price cannot be lower than the financed home-loan amount. Clear the price field if the loan also covered non-property costs."
                )
            attrs["home_down_payment"] = loan_money(home_purchase_price - loan_money(principal))

        if loan_type != "home":
            attrs["home_purchase_price"] = loan_money(0)
            attrs["home_down_payment"] = loan_money(0)
            attrs["home_other_upfront_payments"] = loan_money(0)

        if closed_on or (remaining_balance is not None and remaining_balance <= 0):
            attrs["is_active"] = False
        elif "is_active" not in attrs and not getattr(self.instance, "closed_on", None):
            attrs["is_active"] = True
        return attrs

    def to_representation(self, instance):
        data = super().to_representation(instance)
        for field in ("principal", "emi", "remaining_balance", "home_purchase_price", "home_down_payment", "home_other_upfront_payments"):
            if data[field] is not None:
                data[field] = loan_money_float(data[field])
        data["home_down_payment"] = instance.resolved_home_down_payment
        data["home_upfront_cash_invested"] = instance.resolved_home_upfront_cash_invested
        data["home_property_acquisition_cost"] = instance.resolved_home_property_acquisition_cost
        return data


class LoanClosureDocumentSerializer(serializers.ModelSerializer):
    verification_status_label = serializers.CharField(source="get_verification_status_display", read_only=True)
    parser_status_label = serializers.CharField(source="get_parser_status_display", read_only=True)
    foreclosure_snapshot = serializers.SerializerMethodField()

    class Meta:
        model = LoanClosureDocument
        fields = (
            "id",
            "loan",
            "uploaded_file",
            "file_name",
            "extracted_payload",
            "parser_status",
            "parser_status_label",
            "parse_confidence",
            "verification_status",
            "verification_status_label",
            "verification_notes",
            "closure_amount",
            "closure_date",
            "foreclosure_snapshot",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "loan",
            "file_name",
            "extracted_payload",
            "parser_status",
            "parser_status_label",
            "parse_confidence",
            "verification_status",
            "verification_status_label",
            "verification_notes",
            "closure_amount",
            "closure_date",
            "created_at",
            "updated_at",
        )

    def get_foreclosure_snapshot(self, obj):
        snapshot = getattr(obj, "foreclosure_snapshot", None)
        if snapshot is None:
            return None
        return LoanForeclosureSnapshotSerializer(snapshot).data

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["closure_amount"] = loan_money_float(instance.closure_amount)
        return data


class LoanImportDocumentSerializer(serializers.ModelSerializer):
    parser_status_label = serializers.CharField(source="get_parser_status_display", read_only=True)
    file_url = serializers.SerializerMethodField()
    linked_loans = LoanSerializer(many=True, read_only=True)

    class Meta:
        model = LoanImportDocument
        fields = (
            "id",
            "file_name",
            "document_type",
            "parser_status",
            "parser_status_label",
            "parse_confidence",
            "summary",
            "extracted_payload",
            "file_url",
            "linked_loans",
            "created_at",
        )
        read_only_fields = fields

    def get_file_url(self, obj):
        request = self.context.get("request")
        if not obj.uploaded_file:
            return ""
        if request is not None:
            return request.build_absolute_uri(obj.uploaded_file.url)
        return obj.uploaded_file.url
