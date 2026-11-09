from rest_framework import serializers

from alfred_ai.services.currency import CURRENCY_CHOICES, currency_status
from .models import BankAccount, Expense, StatementUpload
from .money import NumericMoneySerializerField
from .services.transaction_intelligence import hydrate_expense_data


class BankAccountSerializer(serializers.ModelSerializer):
    current_balance = NumericMoneySerializerField(allow_null=True, required=False)
    currency = serializers.ChoiceField(choices=CURRENCY_CHOICES, required=False, allow_null=True, allow_blank=True)
    currency_status = serializers.SerializerMethodField()
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
            "currency",
            "currency_status",
            "is_primary",
            "is_active",
            "last_synced_at",
            "created_at",
        )
        read_only_fields = ("user", "last_synced_at", "created_at")

    def get_currency_status(self, obj):
        return currency_status(obj.currency)

    def validate_currency(self, value):
        value = value or None  # blank means not recorded, never a guessed INR
        recorded = getattr(self.instance, "currency", None)
        if recorded and value != recorded and self.instance.expenses.exists():
            raise serializers.ValidationError("This account already has transactions in its recorded currency; it cannot change.")
        return value

    def validate_account_number(self, value):
        normalized = "".join(char for char in str(value) if char.isalnum())
        if not normalized:
            raise serializers.ValidationError("Account number is required.")
        return normalized


class StatementUploadSerializer(serializers.ModelSerializer):
    extracted_payload = serializers.SerializerMethodField()
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

    def get_extracted_payload(self, obj):
        payload = dict(obj.extracted_payload or {})
        if isinstance(payload.get('import_review'), dict):
            payload['import_review'] = {key: value for key, value in payload['import_review'].items()
                                        if key in ('id', 'state', 'revision', 'expires_at', 'confirmed_at', 'receipt')}
        return payload

    def get_has_transactions(self, obj):
        return bool(obj.imported_count)


class ExpenseSerializer(serializers.ModelSerializer):
    amount = NumericMoneySerializerField()
    closing_balance = NumericMoneySerializerField(allow_null=True, required=False)
    classification_label = serializers.CharField(source="get_classification_display", read_only=True)
    category_label = serializers.CharField(source="get_category_display", read_only=True)
    source_label = serializers.CharField(source="get_source_display", read_only=True)
    direction_label = serializers.CharField(source="get_direction_display", read_only=True)
    statement_upload_id = serializers.IntegerField(source="statement_upload.id", read_only=True)
    bank_account_id = serializers.IntegerField(source="bank_account.id", read_only=True)
    bank_account_display = serializers.CharField(source="bank_account.display_name", read_only=True)
    currency = serializers.ChoiceField(choices=CURRENCY_CHOICES, required=False, allow_null=True, allow_blank=True)
    currency_status = serializers.SerializerMethodField()

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
            "currency",
            "currency_status",
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

    def get_currency_status(self, obj):
        return currency_status(obj.currency)

    def validate_currency(self, value):
        value = value or None
        recorded = getattr(self.instance, "currency", None)
        if recorded and value != recorded:  # a settlement denomination is part of the posted record
            raise serializers.ValidationError("A recorded transaction currency cannot change.")
        return value

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
            # hydrate_expense_data also derives a reference from description words, which says nothing about duplicates.
            reference = attrs.get("external_reference") if getattr(self, "initial_data", {}).get("external_reference") else None
            # shortcut: no database constraint, so simultaneous requests can both pass; add one with a reviewed migration.
            if self.instance is None and reference and Expense.objects.filter(
                    user=user, bank_account=attrs.get("bank_account"), external_reference=reference, direction=attrs.get("direction"),
                    transaction_date=attrs.get("transaction_date"), amount=attrs.get("amount")).exists():
                raise serializers.ValidationError({"external_reference": "This transaction is already saved."})
        return attrs

    def validate_bank_account(self, value):
        user = getattr(self.context.get("request"), "user", None)
        if value is not None and (not user or value.user_id != user.pk):
            raise serializers.ValidationError("Choose one of your own bank accounts.")
        if (self.instance is not None and self.instance.statement_upload_id
                and getattr(value, "pk", None) != self.instance.bank_account_id):
            raise serializers.ValidationError("An imported transaction must keep its original bank account.")
        return value

    def validate_source(self, value):
        if self.instance is not None and self.instance.statement_upload_id and value != self.instance.source:
            raise serializers.ValidationError("An imported transaction must keep its original source.")
        return value

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than zero.")
        return value
