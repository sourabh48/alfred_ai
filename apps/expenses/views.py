from collections import defaultdict
from datetime import date
import logging
import sys

from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework import status
from rest_framework.generics import ListAPIView, ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from alfred_ai.pagination import OptionalPageNumberPagination
from alfred_ai.services import record_parser_learning
from alfred_ai.services.upload_privacy import purge_uploaded_file_after_extraction, raw_upload_cleanup_enabled
from .models import BankAccount, Expense, StatementUpload
from .serializers import BankAccountSerializer, ExpenseSerializer, StatementUploadSerializer
from .services.cashflow_treatment import (
    add_expense_to_cashflow_bucket,
    classify_cashflow,
    empty_cashflow_bucket,
    rounded_cashflow_bucket,
    summarize_cashflow,
)
from .services.financial_intelligence import DISCRETIONARY_CATEGORIES, build_financial_intelligence
from .services.statement_import import parse_bank_statement, summarize_transactions
from .services.statement_lifecycle import apply_parsed_statement_upload, delete_statement_upload, queue_statement_retry, retry_statement_upload
from .services.transaction_intelligence import (
    build_reference_signature,
    build_transaction_fingerprint,
    enrich_imported_expense,
    resolve_bank_account,
    sync_account_balance,
)
from apps.loans.services import loan_intelligence_service

logger = logging.getLogger(__name__)

FLOW_GRANULARITIES = {"monthly", "quarterly", "yearly"}


def _is_unwanted_expense(expense: Expense) -> bool:
    return expense.direction == "debit" and (
        expense.is_emotional or expense.category in DISCRETIONARY_CATEGORIES
    )


def _month_key(value: date) -> tuple[int, int]:
    return value.year, value.month


def _shift_month_key(month_key: tuple[int, int], delta_months: int) -> tuple[int, int]:
    month_index = (month_key[0] * 12 + month_key[1] - 1) + delta_months
    year, zero_based_month = divmod(month_index, 12)
    return year, zero_based_month + 1


def _month_label(month_key: tuple[int, int]) -> str:
    return date(month_key[0], month_key[1], 1).strftime("%b %Y")


def _build_monthly_window(expenses: list[Expense]) -> dict:
    if expenses:
        reference_date = max(item.transaction_date for item in expenses)
    else:
        reference_date = timezone.localdate()

    buckets: dict[tuple[int, int], dict] = defaultdict(empty_cashflow_bucket)

    for expense in expenses:
        bucket = buckets[_month_key(expense.transaction_date)]
        add_expense_to_cashflow_bucket(bucket, expense)
        if _is_unwanted_expense(expense):
            bucket["unwanted_total"] += expense.amount

    reference_key = _month_key(reference_date)
    previous_key = _shift_month_key(reference_key, -1)
    reference_bucket = buckets.get(reference_key, empty_cashflow_bucket())
    previous_bucket = buckets.get(previous_key, empty_cashflow_bucket())
    ordered_keys = sorted(buckets.keys())
    recent_keys = ordered_keys[-6:] if ordered_keys else [reference_key]

    return {
        "reference_month": _month_label(reference_key),
        "previous_month": _month_label(previous_key),
        "current": rounded_cashflow_bucket(reference_bucket),
        "previous": rounded_cashflow_bucket(previous_bucket),
        "window": [
            {
                **rounded_cashflow_bucket(buckets[month_key]),
                "key": f"{month_key[0]}-{month_key[1]:02d}",
                "label": _month_label(month_key),
            }
            for month_key in recent_keys
        ],
    }


def _build_unwanted_expenses(expenses: list[Expense], monthly_window: dict) -> dict:
    flagged = [expense for expense in expenses if _is_unwanted_expense(expense)]
    category_labels = dict(Expense.CATEGORY_CHOICES)
    category_totals: dict[str, float] = defaultdict(float)
    emotional_total = 0.0
    discretionary_total = 0.0

    for expense in flagged:
        category_totals[expense.category] += expense.amount
        if expense.is_emotional:
            emotional_total += expense.amount
        if expense.category in DISCRETIONARY_CATEGORIES:
            discretionary_total += expense.amount

    total_flagged = sum(expense.amount for expense in flagged)
    current_outflow = monthly_window["current"]["outflow_total"] or 0.0
    current_unwanted = monthly_window["current"]["unwanted_total"] or 0.0
    ratio = round((current_unwanted / current_outflow) * 100, 1) if current_outflow else 0.0

    top_categories = [
        {
            "label": category_labels.get(key, key.replace("_", " ").title()),
            "amount": round(amount, 2),
        }
        for key, amount in sorted(category_totals.items(), key=lambda item: item[1], reverse=True)[:4]
    ]

    return {
        "current_month_total": round(current_unwanted, 2),
        "current_month_ratio": ratio,
        "overall_total": round(total_flagged, 2),
        "emotional_total": round(emotional_total, 2),
        "discretionary_total": round(discretionary_total, 2),
        "count": len(flagged),
        "top_categories": top_categories,
        "items": [
            {
                "id": expense.id,
                "transaction_date": expense.transaction_date.isoformat(),
                "merchant": expense.merchant or "Unspecified",
                "description": expense.description or expense.raw_description or "",
                "amount": round(expense.amount, 2),
                "category": expense.category,
                "category_label": category_labels.get(expense.category, expense.category.replace("_", " ").title()),
                "model_confidence": round(float(expense.model_confidence or 0), 3),
                "signal": (
                    "Emotional + discretionary"
                    if expense.is_emotional and expense.category in DISCRETIONARY_CATEGORIES
                    else "Emotional-spend signal"
                    if expense.is_emotional
                    else "Discretionary lifestyle spend"
                ),
            }
            for expense in sorted(flagged, key=lambda item: (item.transaction_date, item.id), reverse=True)[:8]
        ],
    }


def _dispatch_statement_retry(upload_id: int, ocr_page_limit: int) -> None:
    if any(arg in {"test", "makemigrations", "migrate"} for arg in sys.argv[1:]):
        return
    try:
        from .tasks import retry_statement_upload_task

        retry_statement_upload_task.delay(upload_id, ocr_page_limit)
    except Exception:
        logger.warning(
            "Statement background retry dispatch failed for upload %s.",
            upload_id,
            exc_info=True,
        )


def _flow_period_key(value: date, granularity: str):
    if granularity == "yearly":
        return value.year
    if granularity == "quarterly":
        return value.year, ((value.month - 1) // 3) + 1
    return value.year, value.month


def _flow_period_label(key, granularity: str) -> str:
    if granularity == "yearly":
        return str(key)
    if granularity == "quarterly":
        year, quarter = key
        return f"Q{quarter} {year}"
    year, month = key
    return date(year, month, 1).strftime("%b %Y")


def _parse_timeline_limit(raw_value) -> int:
    try:
        limit = int(raw_value or 60)
    except (TypeError, ValueError):
        return 60
    return max(10, min(limit, 200))


def _apply_timeline_filters(queryset, request):
    search = str(request.query_params.get("q") or "").strip()
    transaction_id = str(request.query_params.get("transaction_id") or "").strip()
    classification = str(request.query_params.get("classification") or "").strip()
    source = str(request.query_params.get("source") or "").strip()

    if transaction_id:
        if transaction_id.isdigit():
            queryset = queryset.filter(id=int(transaction_id))
        else:
            queryset = queryset.none()

    if classification:
        queryset = queryset.filter(classification=classification)

    if source:
        queryset = queryset.filter(source=source)

    if search:
        queryset = queryset.filter(
            Q(merchant__icontains=search)
            | Q(description__icontains=search)
            | Q(raw_description__icontains=search)
            | Q(external_reference__icontains=search)
            | Q(transaction_fingerprint__icontains=search)
            | Q(counterparty__icontains=search)
            | Q(company_name__icontains=search)
        )

    return queryset, {
        "query": search,
        "transaction_id": transaction_id,
        "classification": classification,
        "source": source,
    }


class BankAccountListCreateView(ListCreateAPIView):
    serializer_class = BankAccountSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = OptionalPageNumberPagination

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
    pagination_class = OptionalPageNumberPagination

    def get_queryset(self):
        return StatementUpload.objects.filter(user=self.request.user).order_by("-uploaded_at", "-id")


class StatementUploadDetailView(RetrieveUpdateDestroyAPIView):
    serializer_class = StatementUploadSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return StatementUpload.objects.filter(user=self.request.user)

    def perform_destroy(self, instance):
        delete_statement_upload(instance)


class ExpenseListCreateView(ListCreateAPIView):
    serializer_class = ExpenseSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = OptionalPageNumberPagination

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
        base_queryset = Expense.objects.filter(user=request.user).order_by("-transaction_date", "-id")
        expenses = list(base_queryset)
        filtered_queryset, applied_filters = _apply_timeline_filters(base_queryset, request)
        filtered_expenses = list(filtered_queryset)
        limit = _parse_timeline_limit(request.query_params.get("limit"))
        visible_expenses = filtered_expenses[:limit]

        serializer = ExpenseSerializer(visible_expenses, many=True)
        monthly_window = _build_monthly_window(expenses)
        unwanted_expenses = _build_unwanted_expenses(expenses, monthly_window)

        grouped: dict[str, list[dict]] = defaultdict(list)
        summary = {
            **empty_cashflow_bucket(),
            "emotional_total": 0.0,
            "unwanted_total": 0.0,
            "unwanted_count": 0,
            "accounts_tracked": BankAccount.objects.filter(user=request.user, is_active=True).count(),
            "transaction_count": len(expenses),
        }

        for expense in expenses:
            add_expense_to_cashflow_bucket(summary, expense)
            if expense.direction == "debit" and expense.is_emotional:
                summary["emotional_total"] += expense.amount
            if _is_unwanted_expense(expense):
                summary["unwanted_total"] += expense.amount
                summary["unwanted_count"] += 1

        for payload in serializer.data:
            grouped[payload["transaction_date"]].append(payload)

        visible_treatments = {
            expense.id: classify_cashflow(expense)
            for expense in visible_expenses
        }
        timeline = [
            {
                "date": date_value,
                "items": items,
                "day_total": round(
                    sum(
                        item["amount"]
                        for item in items
                        if visible_treatments.get(item["id"]) and visible_treatments[item["id"]].counts_cashflow_outflow
                    ),
                    2,
                ),
            }
            for date_value, items in grouped.items()
        ]

        latest_upload = StatementUpload.objects.filter(user=request.user).first()
        filtered_cashflow = rounded_cashflow_bucket(summarize_cashflow(filtered_expenses))

        return Response(
            {
                "summary": {
                    key: round(value, 2) if isinstance(value, float) else value
                    for key, value in summary.items()
                },
                "timeline": timeline,
                "timeline_meta": {
                    **applied_filters,
                    "limit": limit,
                    "total_matching_count": len(filtered_expenses),
                    "visible_count": len(visible_expenses),
                    "has_more": len(filtered_expenses) > len(visible_expenses),
                    "filtered_expense_total": filtered_cashflow["expense_total"],
                    "filtered_loan_total": filtered_cashflow["loan_total"],
                    "filtered_other_total": filtered_cashflow["other_total"],
                    "filtered_outflow_total": filtered_cashflow["outflow_total"],
                    "filtered_credit_total": filtered_cashflow["bank_credit_total"],
                    "filtered_income_total": filtered_cashflow["income_total"],
                    "filtered_bank_debit_total": filtered_cashflow["bank_debit_total"],
                    "filtered_transfer_in_total": filtered_cashflow["transfer_in_total"],
                    "filtered_transfer_out_total": filtered_cashflow["transfer_out_total"],
                    "filtered_credit_card_payment_total": filtered_cashflow["credit_card_payment_total"],
                    "filtered_investment_total": filtered_cashflow["investment_total"],
                    "filtered_review_required_total": filtered_cashflow["review_required_total"],
                },
                "latest_upload": StatementUploadSerializer(latest_upload).data if latest_upload else None,
                "monthly_window": monthly_window,
                "unwanted_expenses": unwanted_expenses,
            }
        )


class ExpenseChartView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        granularity = (request.query_params.get("granularity") or "monthly").strip().lower()
        if granularity not in FLOW_GRANULARITIES:
            granularity = "monthly"

        buckets: dict = defaultdict(empty_cashflow_bucket)
        for expense in Expense.objects.filter(user=request.user).only(
            "amount",
            "classification",
            "category",
            "direction",
            "merchant",
            "description",
            "raw_description",
            "counterparty",
            "company_name",
            "transaction_date",
        ):
            add_expense_to_cashflow_bucket(
                buckets[_flow_period_key(expense.transaction_date, granularity)],
                expense,
            )

        ordered_keys = sorted(buckets.keys())

        return Response(
            {
                "granularity": granularity,
                "labels": [_flow_period_label(key, granularity) for key in ordered_keys],
                "expense_values": [round(buckets[key]["expense_total"], 2) for key in ordered_keys],
                "loan_values": [round(buckets[key]["loan_total"], 2) for key in ordered_keys],
                "other_values": [round(buckets[key]["other_total"], 2) for key in ordered_keys],
                "income_values": [round(buckets[key]["income_total"], 2) for key in ordered_keys],
                "outflow_values": [round(buckets[key]["outflow_total"], 2) for key in ordered_keys],
                "bank_debit_values": [round(buckets[key]["bank_debit_total"], 2) for key in ordered_keys],
                "bank_credit_values": [round(buckets[key]["bank_credit_total"], 2) for key in ordered_keys],
                "transfer_in_values": [round(buckets[key]["transfer_in_total"], 2) for key in ordered_keys],
                "transfer_out_values": [round(buckets[key]["transfer_out_total"], 2) for key in ordered_keys],
                "credit_card_payment_values": [round(buckets[key]["credit_card_payment_total"], 2) for key in ordered_keys],
                "investment_values": [round(buckets[key]["investment_total"], 2) for key in ordered_keys],
                "review_required_values": [round(buckets[key]["review_required_total"], 2) for key in ordered_keys],
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
        parsed = parse_bank_statement(statement_file, user=request.user)
        statement_kind = (request.data.get("statement_kind") or parsed.statement_kind or "bank_statement").strip() or "bank_statement"
        statement_file.seek(0)
        result = apply_parsed_statement_upload(
            user=request.user,
            parsed=parsed,
            statement_kind=statement_kind,
            statement_file=statement_file,
        )
        upload = result.upload
        bank_account = result.bank_account
        record_parser_learning(
            user=request.user,
            scope="statement_document",
            filename=statement_file.name,
            detected_type=statement_kind,
            text=parsed.source_text,
            field_names=[
                key
                for key, value in {
                    "bank_name": parsed.bank_name,
                    "account_holder": parsed.account_holder,
                    "account_number": parsed.account_number,
                    "statement_start": parsed.statement_start,
                    "statement_end": parsed.statement_end,
                    "preview_only": parsed.preview_only,
                    "preview_transaction_count": parsed.preview_transaction_count,
                }.items()
                if value
            ] + [item.category for item in parsed.transactions[:8]],
            parser_status=parsed.parser_status,
            confidence=parsed.confidence,
        )
        if not parsed.transactions or parsed.preview_only:
            if raw_upload_cleanup_enabled():
                payload = dict(upload.extracted_payload or {})
                payload["background_retry"] = {
                    "state": "not_queued_raw_file_deleted",
                    "reason": "raw upload deletion policy prevents background retry from retaining the source document",
                    "updated_at": timezone.now().isoformat(),
                }
                upload.extracted_payload = payload
                upload.save(update_fields=["extracted_payload"])
            else:
                queue_statement_retry(upload, reason="partial_ocr_preview_parse" if parsed.preview_only else "initial_low_confidence_parse")
                _dispatch_statement_retry(upload.id, 8)
        raw_file_retention = purge_uploaded_file_after_extraction(
            upload,
            "original_file",
            reason="statement_import_extraction_complete",
        )

        if not parsed.transactions:
            detail = f"Uploaded {statement_file.name}. Alfred classified it as {statement_kind.replace('_', ' ')} but could not confidently extract transactions yet."
            if parsed.parser_status == "failed":
                detail = (
                    f"Uploaded {statement_file.name}. Alfred could not read this PDF cleanly, "
                    + (
                        "so the raw file was deleted after the extraction attempt; re-upload a clearer copy if review needs the original."
                        if raw_file_retention.get("deleted")
                        else "so the file was stored for review and queued for a deeper background retry instead of crashing the import."
                    )
                )
            return Response(
                {
                    "detail": detail,
                    "imported_count": 0,
                    "skipped_count": 0,
                    "loan_detection": result.loan_detection,
                    "account": BankAccountSerializer(bank_account).data if bank_account else None,
                    "upload": StatementUploadSerializer(upload).data,
                    "raw_file_retention": raw_file_retention,
                    "parser_notes": parsed.parser_notes,
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

        if parsed.preview_only:
            processed_pages = max(int(parsed.processed_page_count or 0), 1)
            total_pages = max(int(parsed.total_page_count or processed_pages), processed_pages)
            return Response(
                {
                    "detail": (
                        f"Imported {result.new_import_count} OCR-preview transactions from {statement_file.name}. "
                        f"Alfred populated data from the first {processed_pages} of {total_pages} repaired page(s) "
                        + (
                            "and deleted the raw file after extraction; re-upload is needed for deeper parsing."
                            if raw_file_retention.get("deleted")
                            else "and queued deeper background parsing for the remaining pages."
                        )
                    ),
                    "imported_count": result.new_import_count,
                    "skipped_count": result.skipped_count,
                    "loan_detection": {
                        "detected_loans": result.loan_detection["detected_loans"],
                        "updated_loans": result.loan_detection["updated_loans"],
                        "new_payments": result.loan_detection["new_payments"],
                        "review_payments": result.loan_detection["review_payments"],
                    },
                    "account": BankAccountSerializer(bank_account).data if bank_account else None,
                    "upload": StatementUploadSerializer(upload).data,
                    "raw_file_retention": raw_file_retention,
                    "summary": {
                        key: round(value, 2) if isinstance(value, float) else value
                        for key, value in result.summary.items()
                    },
                    "parser_notes": parsed.parser_notes,
                },
                status=status.HTTP_201_CREATED,
            )

        return Response(
            {
                "detail": f"Imported {result.new_import_count} transactions from {statement_file.name}.",
                "imported_count": result.new_import_count,
                "skipped_count": result.skipped_count,
                "loan_detection": {
                    "detected_loans": result.loan_detection["detected_loans"],
                    "updated_loans": result.loan_detection["updated_loans"],
                    "new_payments": result.loan_detection["new_payments"],
                    "review_payments": result.loan_detection["review_payments"],
                },
                "account": BankAccountSerializer(bank_account).data if bank_account else None,
                "upload": StatementUploadSerializer(upload).data,
                "raw_file_retention": raw_file_retention,
                "summary": {
                    key: round(value, 2) if isinstance(value, float) else value
                    for key, value in result.summary.items()
                },
            },
            status=status.HTTP_201_CREATED,
        )


class StatementUploadRetryView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        upload = StatementUpload.objects.filter(user=request.user, pk=pk).first()
        if upload is None:
            return Response({"detail": "Statement upload not found."}, status=status.HTTP_404_NOT_FOUND)

        result = retry_statement_upload(upload, ocr_page_limit=int(request.data.get("ocr_page_limit") or 8))
        if result is None:
            return Response({"detail": "This upload no longer has a source file to retry."}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {
                "detail": "Statement upload retried." if result.new_import_count else "Statement upload retried, but it still needs review.",
                "imported_count": result.new_import_count,
                "skipped_count": result.skipped_count,
                "upload": StatementUploadSerializer(result.upload).data,
                "summary": {
                    key: round(value, 2) if isinstance(value, float) else value
                    for key, value in result.summary.items()
                },
            }
        )
