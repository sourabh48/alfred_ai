from rest_framework import serializers

from .models import Loan, LoanClosureDocument


class LoanSerializer(serializers.ModelSerializer):
    current_status = serializers.CharField(read_only=True)
    loan_type_label = serializers.CharField(source="get_loan_type_display", read_only=True)
    consolidated_into_id = serializers.IntegerField(source="consolidated_into.id", read_only=True)
    closure_documents_count = serializers.SerializerMethodField()

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
            "start_date",
            "closed_on",
            "is_active",
            "current_status",
            "status",
            "consolidation_group",
            "consolidated_into",
            "consolidated_into_id",
            "closure_reason",
            "closure_documents_count",
            "notes",
            "created_at",
        )
        read_only_fields = ("user", "created_at")

    def get_closure_documents_count(self, obj):
        return obj.closure_documents.count()

    def validate(self, attrs):
        principal = attrs.get("principal", getattr(self.instance, "principal", 0))
        emi = attrs.get("emi", getattr(self.instance, "emi", 0))
        start_date = attrs.get("start_date", getattr(self.instance, "start_date", None))
        closed_on = attrs.get("closed_on", getattr(self.instance, "closed_on", None))
        remaining_balance = attrs.get("remaining_balance", getattr(self.instance, "remaining_balance", None))
        if principal <= 0:
            raise serializers.ValidationError("Principal must be greater than zero.")
        if emi <= 0:
            raise serializers.ValidationError("EMI must be greater than zero.")
        if closed_on and start_date and closed_on < start_date:
            raise serializers.ValidationError("Closing date cannot be earlier than the loan start date.")
        if self.instance and (attrs.get("is_active") is False or closed_on):
            if not self.instance.closure_documents.filter(verification_status="verified").exists() and not attrs.get("consolidated_into"):
                raise serializers.ValidationError("A verified foreclosure or closure document is required before manually closing a loan.")

        if closed_on or (remaining_balance is not None and remaining_balance <= 0):
            attrs["is_active"] = False
        elif "is_active" not in attrs and not getattr(self.instance, "closed_on", None):
            attrs["is_active"] = True
        return attrs


class LoanClosureDocumentSerializer(serializers.ModelSerializer):
    verification_status_label = serializers.CharField(source="get_verification_status_display", read_only=True)

    class Meta:
        model = LoanClosureDocument
        fields = (
            "id",
            "loan",
            "uploaded_file",
            "file_name",
            "extracted_payload",
            "verification_status",
            "verification_status_label",
            "verification_notes",
            "closure_amount",
            "closure_date",
            "created_at",
        )
        read_only_fields = (
            "loan",
            "file_name",
            "extracted_payload",
            "verification_status",
            "verification_status_label",
            "verification_notes",
            "closure_amount",
            "closure_date",
            "created_at",
        )
