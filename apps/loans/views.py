import json

from django.core.serializers.json import DjangoJSONEncoder
from rest_framework.generics import ListAPIView, ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework import status
from django.utils import timezone
from django.db import transaction
from django.db.models import Sum
from datetime import date

from apps.expenses.services.financial_intelligence import build_financial_intelligence
from alfred_ai.services import record_parser_learning
from apps.reports.services import operational_logging_service
from apps.loans.services.loan_pdf_parser import loan_pdf_parser
from apps.loans.services import loan_closure_parser, loan_foreclosure_service, loan_intelligence_service
from apps.reports.services import reporting_service

from .models import Loan, LoanClosureDocument, LoanImportDocument
from .serializers import LoanClosureDocumentSerializer, LoanImportDocumentSerializer, LoanSerializer


def _json_safe(payload):
    return json.loads(json.dumps(payload, cls=DjangoJSONEncoder))


def _loan_import_parser_status(parsed: dict) -> str:
    loans_data = parsed.get("loans") or []
    confidence = float(parsed.get("confidence") or 0)
    extracted_text = (parsed.get("extracted_text") or "").strip()
    document_type = (parsed.get("document_type") or "").strip().lower()

    if loans_data:
        return "parsed"
    if extracted_text or confidence >= 0.2 or document_type not in {"", "other"}:
        return "needs_review"
    return "failed"


def _loan_import_summary(parsed: dict, created_loans: list[Loan]) -> str:
    document_type = (parsed.get("document_type") or "loan document").replace("_", " ").strip()
    if created_loans:
        return f"{len(created_loans)} loan record(s) created or updated from the uploaded {document_type}."
    if parsed.get("extracted_text"):
        return f"The {document_type} was saved, but Alfred could not extract enough structured loan rows yet."
    return f"The uploaded file was saved for review because Alfred could not read enough loan data from it."


def _create_loan_import_document(*, request, upload_file, parsed: dict, created_loans: list[Loan]):
    upload_file.seek(0)
    document = LoanImportDocument.objects.create(
        user=request.user,
        uploaded_file=upload_file,
        file_name=upload_file.name,
        document_type=(parsed.get("document_type") or "")[:40],
        parser_status=_loan_import_parser_status(parsed),
        parse_confidence=float(parsed.get("confidence") or 0),
        extracted_text=parsed.get("extracted_text") or "",
        extracted_payload=_json_safe(
            {
                "document_type": parsed.get("document_type") or "",
                "confidence": float(parsed.get("confidence") or 0),
                "loans": parsed.get("loans") or [],
            }
        ),
        summary=_loan_import_summary(parsed, created_loans),
    )
    if created_loans:
        document.linked_loans.set(created_loans)
    return document


def _closure_parser_status(parsed: dict) -> str:
    return str(parsed.get("parser_status") or ("parsed" if parsed.get("payload", {}).get("matched_keyword") else "needs_review"))


class LoanListCreateView(ListCreateAPIView):
    serializer_class = LoanSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Loan.objects.filter(user=self.request.user).order_by("-start_date", "-id")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class LoanDetailView(RetrieveUpdateDestroyAPIView):
    serializer_class = LoanSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Loan.objects.filter(user=self.request.user)


class LoanSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        intelligence = build_financial_intelligence(request.user)
        return Response(
            {
                "summary": intelligence["loan_portfolio"],
                "balance_sheet": {
                    "total_liabilities": intelligence["balance_sheet"]["total_liabilities"],
                    "pending_foreclosure_excluded_balance": intelligence["balance_sheet"]["pending_foreclosure_excluded_balance"],
                    "summary": intelligence["balance_sheet"]["summary"],
                },
                "behavior": {
                    "stress_score": intelligence["summary"]["stress_score"],
                    "debt_service_ratio": intelligence["summary"]["debt_service_ratio"],
                    "coach_tone": intelligence["behavior"]["coach_tone"],
                },
                "chart": {
                    "labels": intelligence["charts"]["debt_labels"],
                    "values": intelligence["charts"]["debt_values"],
                },
                "recent_imports": LoanImportDocumentSerializer(
                    LoanImportDocument.objects.filter(user=request.user).prefetch_related("linked_loans")[:8],
                    many=True,
                    context={"request": request},
                ).data,
                "recent_closures": LoanClosureDocumentSerializer(
                    LoanClosureDocument.objects.filter(loan__user=request.user).select_related("loan", "foreclosure_snapshot")[:6],
                    many=True,
                    context={"request": request},
                ).data,
            }
        )


class LoanImportDocumentListView(ListAPIView):
    serializer_class = LoanImportDocumentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return LoanImportDocument.objects.filter(user=self.request.user).prefetch_related("linked_loans")


class LoanConsolidationView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser]

    def post(self, request):
        loan_ids = request.data.get("loan_ids") or []
        if len(loan_ids) < 2:
            return Response({"detail": "Select at least two active loans to consolidate."}, status=status.HTTP_400_BAD_REQUEST)

        source_loans = list(Loan.objects.filter(user=request.user, pk__in=loan_ids, is_active=True).order_by("id"))
        if len(source_loans) != len(set(loan_ids)):
            return Response({"detail": "One or more selected loans are invalid or already inactive."}, status=status.HTTP_400_BAD_REQUEST)

        start_date_value = request.data.get("start_date") or timezone.localdate().isoformat()
        try:
            start_date = date.fromisoformat(start_date_value)
        except ValueError:
            return Response({"detail": "Provide a valid consolidation start date."}, status=status.HTTP_400_BAD_REQUEST)

        total_balance = sum((loan.remaining_balance if loan.remaining_balance is not None else loan.principal) for loan in source_loans)
        lender = (request.data.get("lender") or "").strip()
        if not lender:
            return Response({"detail": "Provide the new lender for the consolidated loan."}, status=status.HTTP_400_BAD_REQUEST)
        principal = float(request.data.get("principal") or total_balance or 0)
        interest_rate = float(request.data.get("interest_rate") or 0)
        emi = float(request.data.get("emi") or 0)
        tenure_months = int(request.data.get("tenure_months") or 0)
        if principal <= 0 or emi <= 0 or tenure_months <= 0:
            return Response({"detail": "Principal, EMI, and tenure must be greater than zero."}, status=status.HTTP_400_BAD_REQUEST)

        consolidated_loan = loan_intelligence_service.consolidate_loans(
            user=request.user,
            source_loans=source_loans,
            consolidated_loan_type=(request.data.get("loan_type") or "other").strip() or "other",
            lender=lender,
            loan_account_number=(request.data.get("loan_account_number") or "").strip(),
            principal=principal,
            interest_rate=interest_rate,
            emi=emi,
            tenure_months=tenure_months,
            start_date=start_date,
            notes=(request.data.get("notes") or "").strip(),
        )

        return Response(
            {
                "success": True,
                "message": f"Consolidated {len(source_loans)} loans into a new loan with {lender}.",
                "loan": LoanSerializer(consolidated_loan).data,
            },
            status=status.HTTP_201_CREATED,
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def import_loan_pdf(request):
    """Import loans from PDF (loan book or statement)."""
    try:
        if 'file' not in request.FILES:
            return Response(
                {"error": "No file provided"},
                status=status.HTTP_400_BAD_REQUEST
            )

        pdf_file = request.FILES['file']

        # Validate file type
        if not pdf_file.name.lower().endswith('.pdf'):
            return Response(
                {"error": "Only PDF files are supported"},
                status=status.HTTP_400_BAD_REQUEST
            )

        parsed = loan_pdf_parser.parse_document(pdf_file, user=request.user, filename=pdf_file.name)
        loans_data = parsed["loans"]

        with transaction.atomic():
            created_loans = []
            for loan_data in loans_data:
                loan_account_number = (loan_data.get("loan_account_number") or "").strip()
                lender = (loan_data.get("lender") or "").strip()
                principal = loan_data.get("principal", 0)

                existing = None
                if loan_account_number:
                    existing = Loan.objects.filter(
                        user=request.user,
                        loan_account_number=loan_account_number,
                    ).first()
                elif lender and principal:
                    existing = Loan.objects.filter(
                        user=request.user,
                        lender__iexact=lender,
                        principal=principal,
                    ).first()

                if existing:
                    for key, value in loan_data.items():
                        if value:
                            setattr(existing, key, value)
                    existing.save()
                    created_loans.append(existing)
                else:
                    loan = Loan.objects.create(
                        user=request.user,
                        **loan_data
                    )
                    created_loans.append(loan)

            upload_record = _create_loan_import_document(
                request=request,
                upload_file=pdf_file,
                parsed=parsed,
                created_loans=created_loans,
            )
            record_parser_learning(
                user=request.user,
                scope="loan_document",
                filename=pdf_file.name,
                detected_type=parsed.get("document_type") or "other",
                text=parsed.get("extracted_text") or "",
                field_names=sorted({key for loan in loans_data for key, value in loan.items() if value not in ("", None, 0)}),
                parser_status=upload_record.parser_status,
                confidence=parsed.get("confidence") or 0,
            )
            if not created_loans or upload_record.parser_status != "parsed":
                operational_logging_service.log(
                    user=request.user,
                    module="loans",
                    category="document",
                    scope="loan_document",
                    event_type="loan_document_needs_review",
                    severity="warning",
                    document_id=upload_record.id,
                    file_name=upload_record.file_name,
                    message="Loan document upload was saved, but Alfred could not populate fully trusted structured loan rows yet.",
                    payload={
                        "parser_status": upload_record.parser_status,
                        "parse_confidence": upload_record.parse_confidence,
                        "document_type": upload_record.document_type,
                        "linked_loans": len(created_loans),
                    },
                )

        return Response({
            "success": True,
            "message": upload_record.summary,
            "document_type": parsed["document_type"],
            "parse_confidence": parsed["confidence"],
            "loans": LoanSerializer(created_loans, many=True).data,
            "upload": LoanImportDocumentSerializer(upload_record, context={"request": request}).data,
        }, status=status.HTTP_201_CREATED)

    except Exception as e:
        if "pdf_file" in locals() and getattr(pdf_file, "name", "").lower().endswith(".pdf"):
            parsed = {
                "document_type": "other",
                "confidence": 0.0,
                "extracted_text": "",
                "loans": [],
            }
            try:
                with transaction.atomic():
                    upload_record = _create_loan_import_document(
                        request=request,
                        upload_file=pdf_file,
                        parsed=parsed,
                        created_loans=[],
                    )
                    upload_record.parser_status = "failed"
                    upload_record.summary = f"The uploaded loan PDF was saved for review after a parser failure: {e}"
                    upload_record.extracted_payload = {
                        **(upload_record.extracted_payload or {}),
                        "error": str(e),
                    }
                    upload_record.save(update_fields=["parser_status", "summary", "extracted_payload"])
                    operational_logging_service.log(
                        user=request.user,
                        module="loans",
                        category="document",
                        scope="loan_document",
                        event_type="loan_document_failed",
                        severity="error",
                        document_id=upload_record.id,
                        file_name=upload_record.file_name,
                        message="Loan document upload hit a parser failure and was kept for review.",
                        payload={"error": str(e)},
                    )
                return Response(
                    {
                        "success": False,
                        "message": upload_record.summary,
                        "document_type": "other",
                        "parse_confidence": 0,
                        "loans": [],
                        "upload": LoanImportDocumentSerializer(upload_record, context={"request": request}).data,
                    },
                    status=status.HTTP_201_CREATED,
                )
            except Exception:
                pass
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def payoff_loan(request, pk):
    """Close a loan using a foreclosure / no-due document."""
    try:
        loan = Loan.objects.get(pk=pk, user=request.user)

        if not loan.is_active:
            return Response(
                {"error": "Loan is already paid off"},
                status=status.HTTP_400_BAD_REQUEST
            )

        closure_file = request.FILES.get("file")
        if closure_file is None:
            return Response({"detail": "Upload the foreclosure or no-due document to close this loan."}, status=status.HTTP_400_BAD_REQUEST)

        parsed = loan_closure_parser.parse_document(closure_file, closure_file.name, user=request.user)
        try:
            result = loan_foreclosure_service.process_document(
                user=request.user,
                selected_loan=loan,
                closure_file=closure_file,
                parsed=parsed,
                requested_closure_amount=float(request.data.get("final_payment_amount") or 0) or None,
                requested_closure_date=(request.data.get("closure_date") or "").strip() or None,
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        closure_document = result.closure_document
        record_parser_learning(
            user=request.user,
            scope="loan_closure_document",
            filename=closure_file.name,
            detected_type="loan_closure_document",
            text=parsed.get("extracted_text") or "",
            field_names=[key for key, value in parsed.get("payload", {}).items() if value not in ("", None, 0)],
            parser_status=closure_document.parser_status,
            confidence=closure_document.parse_confidence,
        )

        if closure_document.verification_status != "verified":
            reporting_service.create_system_ticket(
                user=request.user,
                module="loans",
                title="Rejected foreclosure document",
                summary=f"A foreclosure document for loan {loan.id} was rejected because it could not be verified against the selected loan.",
                context_payload={
                    "loan_id": loan.id,
                    "document_id": closure_document.id,
                    "reason": closure_document.verification_notes,
                },
            )
            return Response(
                {
                    "detail": closure_document.verification_notes,
                    "document": LoanClosureDocumentSerializer(closure_document, context={"request": request}).data,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response({
            "success": True,
            "message": result.message,
            "loan": LoanSerializer(result.loan).data,
            "document": LoanClosureDocumentSerializer(closure_document, context={"request": request}).data,
            "reconciliation": {
                "status": getattr(result.snapshot, "reconciliation_status", "unmatched"),
                "matched_payment_total": getattr(result.snapshot, "matched_payment_total", 0),
                "notes": getattr(result.snapshot, "reconciliation_notes", ""),
                "settlement_allocation": dict((getattr(result.snapshot, "audit_payload", {}) or {}).get("settlement_allocation") or {}),
            },
        }, status=status.HTTP_200_OK if result.confirmed else status.HTTP_202_ACCEPTED)

    except Loan.DoesNotExist:
        return Response(
            {"error": "Loan not found"},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def detect_loans_from_expenses(request):
    """Auto-detect loans from expense transactions."""
    try:
        result = loan_intelligence_service.detect_loan_payments(request.user)

        return Response({
            "success": True,
            "detected_loans": result['detected_loans'],
            "updated_loans": result['updated_loans'],
            "new_payments": result['new_payments'],
            "review_payments": result['review_payments'],
            "message": f"Detected {result['detected_loans']} new loans and tracked {result['new_payments']} payments"
        })

    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def loan_metrics(request):
    """Get comprehensive loan metrics."""
    try:
        metrics = loan_intelligence_service.calculate_loan_metrics(request.user)

        return Response(metrics)

    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def calculate_networth(request):
    """Calculate user's net worth across all financial assets."""
    try:
        intelligence = build_financial_intelligence(request.user)
        balance_sheet = intelligence["balance_sheet"]
        from apps.investments.models import Investment
        from apps.expenses.models import BankAccount

        # Assets
        # 1. Cash in bank accounts
        total_cash = BankAccount.objects.filter(
            user=request.user,
            is_active=True
        ).aggregate(total=Sum('current_balance'))['total'] or 0

        # 2. Investments
        total_investments = Investment.objects.filter(
            user=request.user
        ).aggregate(total=Sum('current_value'))['total'] or 0

        # Calculate total assets
        total_assets = total_cash + total_investments

        # Liabilities
        total_debt = balance_sheet["total_liabilities"]

        # Net Worth = Assets - Liabilities
        net_worth = total_assets - total_debt

        # Get breakdown
        assets_breakdown = {
            "cash": round(total_cash, 2),
            "investments": round(total_investments, 2),
            "total": round(total_assets, 2)
        }

        liabilities_breakdown = {
            "loans": round(total_debt, 2),
            "pending_foreclosure_excluded_balance": round(balance_sheet["pending_foreclosure_excluded_balance"], 2),
            "total": round(total_debt, 2)
        }

        # Get investment breakdown by type
        investment_by_type = {}
        for inv in Investment.objects.filter(user=request.user):
            asset_type = inv.get_asset_type_display()
            if asset_type not in investment_by_type:
                investment_by_type[asset_type] = 0
            investment_by_type[asset_type] += inv.current_value

        # Get loan breakdown by type
        loan_by_type = {}
        for loan in Loan.objects.filter(user=request.user).exclude(status__in=["foreclosed", "closed", "prepaid"]):
            loan_type = loan.get_loan_type_display()
            if loan_type not in loan_by_type:
                loan_by_type[loan_type] = 0
            loan_by_type[loan_type] += (loan.remaining_balance or 0)

        # Calculate debt-to-asset ratio
        debt_to_asset_ratio = (total_debt / total_assets * 100) if total_assets > 0 else 0

        # Financial health assessment
        if net_worth > 1000000:
            health_status = "Excellent"
            message = "Strong financial position with healthy net worth"
        elif net_worth > 500000:
            health_status = "Good"
            message = "Good financial health, continue building wealth"
        elif net_worth > 100000:
            health_status = "Fair"
            message = "Moderate net worth, focus on increasing assets"
        elif net_worth > 0:
            health_status = "Needs Improvement"
            message = "Low net worth, reduce debt and increase savings"
        else:
            health_status = "Critical"
            message = "Negative net worth - debt exceeds assets. Urgent action needed"

        return Response({
            "net_worth": round(net_worth, 2),
            "assets": assets_breakdown,
            "liabilities": liabilities_breakdown,
            "investment_breakdown": {k: round(v, 2) for k, v in investment_by_type.items()},
            "loan_breakdown": {k: round(v, 2) for k, v in loan_by_type.items()},
            "metrics": {
                "debt_to_asset_ratio": round(debt_to_asset_ratio, 2),
                "asset_allocation": {
                    "cash_percentage": round((total_cash / total_assets * 100) if total_assets > 0 else 0, 2),
                    "investment_percentage": round((total_investments / total_assets * 100) if total_assets > 0 else 0, 2),
                }
            },
            "health": {
                "status": health_status,
                "message": message
            },
            "insights": [
                f"Your net worth is INR {net_worth:,.0f}",
                f"Total assets: INR {total_assets:,.0f}",
                f"Total liabilities: INR {total_debt:,.0f}",
                f"Debt-to-Asset ratio: {debt_to_asset_ratio:.1f}%"
            ]
        })

    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
