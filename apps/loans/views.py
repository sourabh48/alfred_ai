from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
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
from apps.loans.services.loan_pdf_parser import loan_pdf_parser
from apps.loans.services import loan_closure_parser, loan_intelligence_service
from apps.reports.services import reporting_service

from .models import Loan, LoanClosureDocument, LoanPaymentHistory
from .serializers import LoanClosureDocumentSerializer, LoanSerializer


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
                "behavior": {
                    "stress_score": intelligence["summary"]["stress_score"],
                    "debt_service_ratio": intelligence["summary"]["debt_service_ratio"],
                    "coach_tone": intelligence["behavior"]["coach_tone"],
                },
                "chart": {
                    "labels": intelligence["charts"]["debt_labels"],
                    "values": intelligence["charts"]["debt_values"],
                },
            }
        )


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

        parsed = loan_pdf_parser.parse_document(pdf_file)
        loans_data = parsed["loans"]

        if not loans_data:
            return Response(
                {
                    "error": "No loan data found in PDF",
                    "document_type": parsed["document_type"],
                    "parse_confidence": parsed["confidence"],
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Create loans
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
                # Update existing loan
                for key, value in loan_data.items():
                    if value:
                        setattr(existing, key, value)
                existing.save()
                created_loans.append(existing)
            else:
                # Create new loan
                loan = Loan.objects.create(
                    user=request.user,
                    **loan_data
                )
                created_loans.append(loan)

        return Response({
            "success": True,
            "message": f"Successfully imported {len(created_loans)} loan(s)",
            "document_type": parsed["document_type"],
            "parse_confidence": parsed["confidence"],
            "loans": LoanSerializer(created_loans, many=True).data
        })

    except Exception as e:
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

        parsed = loan_closure_parser.parse_document(closure_file, closure_file.name)
        closure_file.seek(0)
        verified, notes = loan_closure_parser.verify_document(loan, parsed)

        closure_amount = float(parsed["payload"].get("closure_amount") or request.data.get("final_payment_amount") or loan.remaining_balance or 0)
        closure_date_raw = parsed["payload"].get("closure_date") or request.data.get("closure_date") or timezone.localdate().isoformat()
        try:
            closure_date = date.fromisoformat(closure_date_raw)
        except ValueError:
            return Response({"detail": "Closure date could not be read from the document or request."}, status=status.HTTP_400_BAD_REQUEST)
        closure_document = LoanClosureDocument.objects.create(
            loan=loan,
            uploaded_file=closure_file,
            file_name=closure_file.name,
            extracted_text=parsed["extracted_text"],
            extracted_payload=parsed["payload"],
            verification_status="verified" if verified else "rejected",
            verification_notes=notes,
            closure_amount=closure_amount,
            closure_date=closure_date,
        )

        if not verified:
            reporting_service.create_system_ticket(
                user=request.user,
                module="loans",
                title="Rejected foreclosure document",
                summary=f"A foreclosure document for loan {loan.id} was rejected because it could not be verified against the selected loan.",
                context_payload={
                    "loan_id": loan.id,
                    "document_id": closure_document.id,
                    "reason": notes,
                },
            )
            return Response(
                {
                    "detail": notes,
                    "document": LoanClosureDocumentSerializer(closure_document, context={"request": request}).data,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            loan.is_active = False
            loan.status = "prepaid"
            loan.closed_on = closure_date
            loan.remaining_balance = 0
            loan.closure_reason = "foreclosed"
            loan.last_payment_date = closure_date
            loan.total_paid = (loan.total_paid or 0) + closure_amount
            loan.save(
                update_fields=[
                    "is_active",
                    "status",
                    "closed_on",
                    "remaining_balance",
                    "closure_reason",
                    "last_payment_date",
                    "total_paid",
                    "updated_at",
                ]
            )

            if closure_amount:
                LoanPaymentHistory.objects.create(
                    loan=loan,
                    payment_date=closure_date,
                    amount=closure_amount,
                    principal_component=closure_amount,
                    interest_component=0,
                    remaining_balance=0,
                    is_auto_detected=False,
                    detection_confidence=100,
                    detection_reason="Verified foreclosure document uploaded by the user.",
                    match_status="matched",
                )

        return Response({
            "success": True,
            "message": f"Loan from {loan.lender} has been closed using the uploaded foreclosure document.",
            "loan": LoanSerializer(loan).data,
            "document": LoanClosureDocumentSerializer(closure_document, context={"request": request}).data,
        })

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
        # 1. Active loans
        total_debt = Loan.objects.filter(
            user=request.user,
            is_active=True
        ).aggregate(total=Sum('remaining_balance'))['total'] or 0

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
        for loan in Loan.objects.filter(user=request.user, is_active=True):
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
