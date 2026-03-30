from collections import defaultdict

from django.db import transaction
from django.db.models import Case, F, FloatField, Sum, Value, When
from django.db.models.functions import Coalesce, TruncMonth
from rest_framework import status
from rest_framework.generics import ListAPIView, ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import BankAccount, Expense, StatementUpload
from .serializers import BankAccountSerializer, ExpenseSerializer, StatementUploadSerializer
from .services.financial_intelligence import build_financial_intelligence
from .services.statement_import import parse_bank_statement, summarize_transactions
from .services.transaction_intelligence import build_transaction_fingerprint, enrich_imported_expense, resolve_bank_account, sync_account_balance
from apps.loans.services import loan_intelligence_service


STATEMENT_ACCOUNT_TYPE_MAP = {
    "bank_statement": "savings",
    "credit_card_statement": "credit",
    "loan_statement": "other",
    "investment_statement": "investment",
    "other_statement": "other",
}


class BankAccountListCreateView(ListCreateAPIView):
    serializer_class = BankAccountSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return BankAccount.objects.filter(user=self.request.user).order_by("-is_primary", "bank_name", "account_number")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class BankAccountDetailView(RetrieveUpdateDestroyAPIView):
    serializer_class = BankAccountSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return BankAccount.objects.filter(user=self.request.user)


class StatementUploadListView(ListAPIView):
    serializer_class = StatementUploadSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return StatementUpload.objects.filter(user=self.request.user).order_by("-uploaded_at", "-id")


class ExpenseListCreateView(ListCreateAPIView):
    serializer_class = ExpenseSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Expense.objects.filter(user=self.request.user).order_by("-transaction_date", "-id")

        classification = self.request.query_params.get("classification")
        if classification:
            queryset = queryset.filter(classification=classification)

        source = self.request.query_params.get("source")
        if source:
            queryset = queryset.filter(source=source)

        bank_account = self.request.query_params.get("bank_account")
        if bank_account:
            queryset = queryset.filter(bank_account_id=bank_account)

        return queryset

    def perform_create(self, serializer):
        validated = serializer.validated_data
        expense = serializer.save(
            user=self.request.user,
            source=validated.get("source", "manual"),
            direction=validated.get("direction", "debit"),
        )
        sync_account_balance(expense.bank_account, expense.closing_balance)


class ExpenseDetailView(RetrieveUpdateDestroyAPIView):
    serializer_class = ExpenseSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Expense.objects.filter(user=self.request.user)

    def perform_update(self, serializer):
        expense = serializer.save()
        sync_account_balance(expense.bank_account, expense.closing_balance)


class ExpenseTimelineView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        expenses = list(Expense.objects.filter(user=request.user).order_by("-transaction_date", "-id"))
        serializer = ExpenseSerializer(expenses, many=True)

        grouped: dict[str, list[dict]] = defaultdict(list)
        summary = {
            "expense_total": 0.0,
            "loan_total": 0.0,
            "other_total": 0.0,
            "income_total": 0.0,
            "emotional_total": 0.0,
            "accounts_tracked": BankAccount.objects.filter(user=request.user, is_active=True).count(),
            "transaction_count": len(expenses),
        }

        for expense in expenses:
            if expense.direction == "credit":
                summary["income_total"] += expense.amount
            elif expense.classification == "expense":
                summary["expense_total"] += expense.amount
            elif expense.classification == "loan":
                summary["loan_total"] += expense.amount
            else:
                summary["other_total"] += expense.amount
            if expense.direction == "debit" and expense.is_emotional:
                summary["emotional_total"] += expense.amount

        for payload in serializer.data:
            grouped[payload["transaction_date"]].append(payload)

        timeline = [
            {
                "date": date_value,
                "items": items,
                "day_total": round(
                    sum(item["amount"] for item in items if item["direction"] == "debit"),
                    2,
                ),
            }
            for date_value, items in grouped.items()
        ]

        latest_upload = StatementUpload.objects.filter(user=request.user).first()

        return Response(
            {
                "summary": {key: round(value, 2) if isinstance(value, float) else value for key, value in summary.items()},
                "timeline": timeline,
                "latest_upload": StatementUploadSerializer(latest_upload).data if latest_upload else None,
            }
        )


class ExpenseChartView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = (
            Expense.objects.filter(user=request.user)
            .annotate(month=TruncMonth("transaction_date"))
            .values("month")
            .annotate(
                expense_total=Coalesce(
                    Sum(
                        Case(
                            When(direction="debit", classification="expense", then=F("amount")),
                            default=Value(0.0),
                            output_field=FloatField(),
                        )
                    ),
                    0.0,
                ),
                loan_total=Coalesce(
                    Sum(
                        Case(
                            When(direction="debit", classification="loan", then=F("amount")),
                            default=Value(0.0),
                            output_field=FloatField(),
                        )
                    ),
                    0.0,
                ),
                other_total=Coalesce(
                    Sum(
                        Case(
                            When(direction="debit", classification="other", then=F("amount")),
                            default=Value(0.0),
                            output_field=FloatField(),
                        )
                    ),
                    0.0,
                ),
                income_total=Coalesce(
                    Sum(
                        Case(
                            When(direction="credit", then=F("amount")),
                            default=Value(0.0),
                            output_field=FloatField(),
                        )
                    ),
                    0.0,
                ),
            )
            .order_by("month")
        )

        return Response(
            {
                "labels": [item["month"].strftime("%b %Y") for item in queryset if item["month"]],
                "expense_values": [round(item["expense_total"], 2) for item in queryset],
                "loan_values": [round(item["loan_total"], 2) for item in queryset],
                "other_values": [round(item["other_total"], 2) for item in queryset],
                "income_values": [round(item["income_total"], 2) for item in queryset],
            }
        )


class ExpenseDashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(build_financial_intelligence(request.user))


class ExpenseStatementImportView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        statement_file = request.FILES.get("statement")
        if statement_file is None:
            return Response({"detail": "Upload a statement PDF first."}, status=status.HTTP_400_BAD_REQUEST)
        if not statement_file.name.lower().endswith(".pdf"):
            return Response({"detail": "Only PDF statements are supported right now."}, status=status.HTTP_400_BAD_REQUEST)

        statement_file.seek(0)
        parsed = parse_bank_statement(statement_file)
        statement_kind = (request.data.get("statement_kind") or parsed.statement_kind or "bank_statement").strip() or "bank_statement"

        statement_file.seek(0)
        latest_closing = parsed.transactions[-1].closing_balance if parsed.transactions else None
        bank_account = resolve_bank_account(
            user=request.user,
            bank_name=parsed.bank_name,
            account_holder=parsed.account_holder,
            account_number=parsed.account_number,
            account_type=STATEMENT_ACCOUNT_TYPE_MAP.get(statement_kind, "other"),
            current_balance=latest_closing,
        )

        with transaction.atomic():
            upload = StatementUpload.objects.create(
                user=request.user,
                bank_account=bank_account,
                source=statement_kind,
                original_file=statement_file,
                file_name=statement_file.name,
                bank_name=parsed.bank_name,
                account_holder=parsed.account_holder,
                account_number=parsed.account_number,
                institution_name=parsed.bank_name,
                statement_start=parsed.statement_start,
                statement_end=parsed.statement_end,
                parser_status=parsed.parser_status,
                parse_confidence=parsed.confidence,
                extracted_payload={
                    "statement_kind": statement_kind,
                    "loan_hints": parsed.loan_hints,
                    "raw_text_excerpt": parsed.source_text[:1500],
                },
            )

            to_create: list[Expense] = []
            imported_transactions = []
            skipped_count = 0
            transaction_dates = {item.transaction_date for item in parsed.transactions}
            existing_expenses = Expense.objects.filter(
                user=request.user,
                bank_account=bank_account,
                source="bank_statement",
                transaction_date__in=transaction_dates,
            ).values(
                "transaction_fingerprint",
                "transaction_date",
                "amount",
                "direction",
                "external_reference",
            )
            existing_fingerprints = {item["transaction_fingerprint"] for item in existing_expenses if item["transaction_fingerprint"]}
            existing_reference_signatures = {
                (
                    item["transaction_date"],
                    float(item["amount"] or 0),
                    item["direction"],
                    "".join(char for char in str(item["external_reference"] or "").upper() if char.isalnum()),
                )
                for item in existing_expenses
                if item["external_reference"]
            }

            for item in parsed.transactions:
                fingerprint = build_transaction_fingerprint(
                    bank_account=bank_account,
                    transaction_date=item.transaction_date,
                    amount=item.amount,
                    direction=item.direction,
                    external_reference=item.external_reference,
                    raw_description=item.raw_description,
                    closing_balance=item.closing_balance,
                )
                reference_signature = (
                    item.transaction_date,
                    float(item.amount or 0),
                    item.direction,
                    "".join(char for char in str(item.external_reference or "").upper() if char.isalnum()),
                )
                if fingerprint in existing_fingerprints or (reference_signature[3] and reference_signature in existing_reference_signatures):
                    skipped_count += 1
                    continue
                existing_fingerprints.add(fingerprint)
                if reference_signature[3]:
                    existing_reference_signatures.add(reference_signature)

                imported_transactions.append(item)
                enriched = enrich_imported_expense(
                    user=request.user,
                    amount=item.amount,
                    classification=item.classification,
                    category=item.category,
                    payment_mode=item.payment_mode,
                    merchant=item.merchant,
                    description=item.description,
                    raw_description=item.raw_description,
                    direction=item.direction,
                    transaction_date=item.transaction_date,
                    external_reference=item.external_reference,
                    counterparty=item.counterparty,
                    company_name=item.company_name,
                )
                to_create.append(
                    Expense(
                        user=request.user,
                        bank_account=bank_account,
                        statement_upload=upload,
                        amount=item.amount,
                        classification=enriched["classification"],
                        category=enriched["category"],
                        payment_mode=enriched["payment_mode"],
                        merchant=enriched["merchant"],
                        description=enriched["description"],
                        raw_description=enriched["raw_description"],
                        transaction_date=item.transaction_date,
                        direction=enriched["direction"],
                        source="bank_statement",
                        external_reference=enriched["external_reference"],
                        transaction_fingerprint=fingerprint,
                        closing_balance=item.closing_balance,
                        counterparty=enriched["counterparty"],
                        company_name=enriched["company_name"],
                        ai_summary=enriched["ai_summary"],
                        is_emotional=enriched["is_emotional"],
                        model_confidence=enriched["model_confidence"],
                    )
                )

            Expense.objects.bulk_create(to_create)
            upload.imported_count = len(to_create)
            upload.save(update_fields=["imported_count"])
            sync_account_balance(bank_account, latest_closing)
            created_expenses = list(Expense.objects.filter(statement_upload=upload).order_by("transaction_date", "id"))
            loan_detection = loan_intelligence_service.detect_loan_payments(request.user, expenses=created_expenses)

        if not parsed.transactions:
            return Response(
                {
                    "detail": f"Uploaded {statement_file.name}. Alfred classified it as {statement_kind.replace('_', ' ')} but could not confidently extract transactions yet.",
                    "imported_count": 0,
                    "skipped_count": 0,
                    "loan_detection": {
                        "detected_loans": 0,
                        "updated_loans": 0,
                        "new_payments": 0,
                        "review_payments": 0,
                    },
                    "account": BankAccountSerializer(bank_account).data if bank_account else None,
                    "upload": StatementUploadSerializer(upload).data,
                    "summary": {
                        "expense_total": 0.0,
                        "loan_total": 0.0,
                        "other_total": 0.0,
                        "income_total": 0.0,
                        "transaction_count": 0,
                    },
                },
                status=status.HTTP_201_CREATED,
            )

        return Response(
            {
                "detail": f"Imported {len(to_create)} transactions from {statement_file.name}.",
                "imported_count": len(to_create),
                "skipped_count": skipped_count,
                "loan_detection": {
                    "detected_loans": loan_detection["detected_loans"],
                    "updated_loans": loan_detection["updated_loans"],
                    "new_payments": loan_detection["new_payments"],
                    "review_payments": loan_detection["review_payments"],
                },
                "account": BankAccountSerializer(bank_account).data if bank_account else None,
                "upload": StatementUploadSerializer(upload).data,
                "summary": {
                    key: round(value, 2) if isinstance(value, float) else value
                    for key, value in summarize_transactions(imported_transactions).items()
                },
            },
            status=status.HTTP_201_CREATED,
        )
