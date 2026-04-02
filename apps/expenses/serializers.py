from rest_framework import serializers

from .models import BankAccount, Expense, StatementUpload
from .services.transaction_intelligence import hydrate_expense_data


class BankAccountSerializer(serializers.ModelSerializer):
    masked_account_number = serializers.CharField(read_only=True)
    display_name = serializers.CharField(read_only=True)

    class Meta:
        model = BankAccount
        fields = (
            "id",
            "user",
            "bank_name",
            "nickname",
            "account_holder",
            "account_number",
            "masked_account_number",
            "display_name",
            "account_type",
            "current_balance",
            "is_primary",
            "is_active",
            "last_synced_at",
            "created_at",
        )
        read_only_fields = ("user", "last_synced_at", "created_at")

    def validate_account_number(self, value):
        normalized = "".join(char for char in str(value) if char.isalnum())
        if not normalized:
            raise serializers.ValidationError("Account number is required.")
        return normalized


class StatementUploadSerializer(serializers.ModelSerializer):
    bank_account_id = serializers.IntegerField(source="bank_account.id", read_only=True)
    parser_status_label = serializers.CharField(source="get_parser_status_display", read_only=True)
    parser_notes = serializers.SerializerMethodField()
    has_transactions = serializers.SerializerMethodField()

    class Meta:
        model = StatementUpload
        fields = (
            "id",
            "bank_account_id",
            "source",
            "file_name",
            "bank_name",
            "account_holder",
            "account_number",
            "institution_name",
            "statement_start",
            "statement_end",
            "parser_status",
            "parser_status_label",
            "parser_notes",
            "parse_confidence",
            "extracted_payload",
            "imported_count",
            "has_transactions",
            "uploaded_at",
        )
        read_only_fields = fields

    def get_parser_notes(self, obj):
        payload = obj.extracted_payload or {}
        return payload.get("parser_notes", "")

    def get_has_transactions(self, obj):
        return bool(obj.imported_count)


class ExpenseSerializer(serializers.ModelSerializer):
    classification_label = serializers.CharField(source="get_classification_display", read_only=True)
    category_label = serializers.CharField(source="get_category_display", read_only=True)
    source_label = serializers.CharField(source="get_source_display", read_only=True)
    direction_label = serializers.CharField(source="get_direction_display", read_only=True)
    statement_upload_id = serializers.IntegerField(source="statement_upload.id", read_only=True)
    bank_account_id = serializers.IntegerField(source="bank_account.id", read_only=True)
    bank_account_display = serializers.CharField(source="bank_account.display_name", read_only=True)

    class Meta:
        model = Expense
        fields = (
            "id",
            "user",
            "bank_account",
            "bank_account_id",
            "bank_account_display",
            "statement_upload",
            "statement_upload_id",
            "amount",
            "classification",
            "classification_label",
            "category",
            "category_label",
            "payment_mode",
            "merchant",
            "description",
            "raw_description",
            "transaction_date",
            "direction",
            "direction_label",
            "source",
            "source_label",
            "external_reference",
            "transaction_fingerprint",
            "closing_balance",
            "timestamp",
            "counterparty",
            "company_name",
            "ai_summary",
            "is_emotional",
            "model_confidence",
        )
        read_only_fields = ("user", "statement_upload", "transaction_fingerprint", "timestamp")

    def validate(self, attrs):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if user and user.is_authenticated:
            attrs = hydrate_expense_data(
                user=user,
                payload=attrs,
                initial_data=getattr(self, "initial_data", {}),
                instance=self.instance,
            )
        return attrs

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than zero.")
        return value
