from rest_framework import serializers

from .models import Loan, LoanClosureDocument, LoanForeclosureSnapshot, LoanImportDocument


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


class LoanSerializer(serializers.ModelSerializer):
    current_status = serializers.CharField(read_only=True)
    loan_type_label = serializers.CharField(source="get_loan_type_display", read_only=True)
    consolidated_into_id = serializers.IntegerField(source="consolidated_into.id", read_only=True)
    closure_documents_count = serializers.SerializerMethodField()
    latest_foreclosure_snapshot = serializers.SerializerMethodField()

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
            "latest_foreclosure_snapshot",
            "notes",
            "created_at",
        )
        read_only_fields = ("user", "created_at")

    def get_closure_documents_count(self, obj):
        return obj.closure_documents.count()

    def get_latest_foreclosure_snapshot(self, obj):
        snapshot = obj.foreclosure_snapshots.order_by("-updated_at", "-id").first()
        if snapshot is None:
            return None
        return LoanForeclosureSnapshotSerializer(snapshot).data

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
