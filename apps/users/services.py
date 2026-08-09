from __future__ import annotations

import logging
from pathlib import Path

from django.conf import settings
from django.core.files.storage import default_storage
from django.db import transaction
from django.db.models import Q

from alfred_ai.services.materialized_cache import invalidate_user_materialized_payloads
from apps.behavioral.models import BehavioralSignal
from apps.budgets.models import Budget
from apps.career.models import CareerJobAnalysis, CareerProfile, CareerResume, CareerResumeLearningMemory
from apps.expenses.models import BankAccount, Expense, StatementUpload
from apps.family.models import Dependent, FamilyAccountLink
from apps.integrations.models import CreditReportUpload, CreditScore, EmailConnection, VerifiedExternalInsight
from apps.investments.models import Investment, InvestmentImportDocument
from apps.loans.models import Loan, LoanClosureDocument, LoanForeclosureSnapshot, LoanImportDocument, LoanPaymentHistory
from apps.ml_engine.models.parser_memory import DocumentParserLearningMemory
from apps.mobility.models import (
    BikeConditionSnapshot,
    BikeDocument,
    BikeIssueReport,
    BikeProfile,
    BikeServiceRecord,
    FuelRefillLog,
    TravelPlan,
    TripLog,
    TripPhoto,
)
from apps.relationship.models import RelationshipProfile
from apps.reports.models import ChatGPTImport, GeneratedReport, OperationalLog, SystemTicket
from apps.risk.models import RiskSignal


logger = logging.getLogger(__name__)


def _collect_file_names(queryset, field_name: str) -> list[str]:
    names: list[str] = []
    for item in queryset.only(field_name):
        field = getattr(item, field_name, None)
        name = getattr(field, "name", "")
        if name:
            names.append(name)
    return names


def _delete_storage_files(file_names: list[str]) -> None:
    for file_name in sorted({item for item in file_names if item}):
        try:
            default_storage.delete(file_name)
        except Exception:
            logger.warning("User data reset could not remove stored file %s.", file_name, exc_info=True)


def _delete_generated_report_paths(paths: list[str]) -> None:
    for raw_path in sorted({item for item in paths if item}):
        try:
            path = Path(raw_path)
            if not path.is_absolute():
                path = Path(settings.BASE_DIR) / raw_path
            if path.exists():
                path.unlink()
        except Exception:
            logger.warning("User data reset could not remove generated artifact %s.", raw_path, exc_info=True)


def clear_user_fed_data(user) -> dict:
    career_resume_qs = CareerResume.objects.filter(user=user)
    statement_upload_qs = StatementUpload.objects.filter(user=user)
    credit_report_qs = CreditReportUpload.objects.filter(user=user)
    investment_doc_qs = InvestmentImportDocument.objects.filter(user=user)
    loan_import_qs = LoanImportDocument.objects.filter(user=user)
    loan_closure_qs = LoanClosureDocument.objects.filter(loan__user=user)
    trip_photo_qs = TripPhoto.objects.filter(user=user)
    bike_document_qs = BikeDocument.objects.filter(user=user)
    generated_report_qs = GeneratedReport.objects.filter(user=user)
    family_link_qs = FamilyAccountLink.objects.filter(Q(created_by=user) | Q(linked_user=user))
    linked_family_user_ids = set()
    for link in family_link_qs.only("created_by_id", "linked_user_id"):
        if link.created_by_id and link.created_by_id != user.id:
            linked_family_user_ids.add(link.created_by_id)
        if link.linked_user_id and link.linked_user_id != user.id:
            linked_family_user_ids.add(link.linked_user_id)

    file_names = []
    file_names.extend(_collect_file_names(career_resume_qs, "uploaded_file"))
    file_names.extend(_collect_file_names(statement_upload_qs, "original_file"))
    file_names.extend(_collect_file_names(credit_report_qs, "uploaded_file"))
    file_names.extend(_collect_file_names(investment_doc_qs, "uploaded_file"))
    file_names.extend(_collect_file_names(loan_import_qs, "uploaded_file"))
    file_names.extend(_collect_file_names(loan_closure_qs, "uploaded_file"))
    file_names.extend(_collect_file_names(trip_photo_qs, "image"))
    file_names.extend(_collect_file_names(bike_document_qs, "document_file"))
    generated_paths = list(generated_report_qs.values_list("file_path", flat=True))

    summary = {
        "career_resumes": career_resume_qs.count(),
        "career_job_analyses": CareerJobAnalysis.objects.filter(user=user).count(),
        "bank_accounts": BankAccount.objects.filter(user=user).count(),
        "statement_uploads": statement_upload_qs.count(),
        "expenses": Expense.objects.filter(user=user).count(),
        "loans": Loan.objects.filter(user=user).count(),
        "loan_import_documents": loan_import_qs.count(),
        "loan_closure_documents": loan_closure_qs.count(),
        "loan_foreclosure_snapshots": LoanForeclosureSnapshot.objects.filter(loan__user=user).count(),
        "investments": Investment.objects.filter(user=user).count(),
        "investment_import_documents": investment_doc_qs.count(),
        "vehicle_profiles": BikeProfile.objects.filter(user=user).count(),
        "vehicle_documents": bike_document_qs.count(),
        "vehicle_services": BikeServiceRecord.objects.filter(user=user).count(),
        "travel_plans": TravelPlan.objects.filter(user=user).count(),
        "trip_photos": trip_photo_qs.count(),
        "credit_reports": credit_report_qs.count(),
        "credit_scores": CreditScore.objects.filter(user=user).count(),
        "system_tickets": SystemTicket.objects.filter(user=user).count(),
        "operational_logs": OperationalLog.objects.filter(user=user).count(),
        "chatgpt_imports": ChatGPTImport.objects.filter(user=user).count(),
        "parser_memories": DocumentParserLearningMemory.objects.filter(user=user).count() + CareerResumeLearningMemory.objects.filter(user=user).count(),
        "family_account_links": family_link_qs.count(),
    }

    with transaction.atomic():
        CareerJobAnalysis.objects.filter(user=user).delete()
        career_resume_qs.delete()
        CareerResumeLearningMemory.objects.filter(user=user).delete()
        CareerProfile.objects.filter(user=user).delete()

        Expense.objects.filter(user=user).delete()
        statement_upload_qs.delete()
        BankAccount.objects.filter(user=user).delete()

        LoanPaymentHistory.objects.filter(loan__user=user).delete()
        LoanForeclosureSnapshot.objects.filter(loan__user=user).delete()
        loan_closure_qs.delete()
        loan_import_qs.delete()
        Loan.objects.filter(user=user).delete()

        investment_doc_qs.delete()
        Investment.objects.filter(user=user).delete()

        BikeIssueReport.objects.filter(user=user).delete()
        BikeServiceRecord.objects.filter(user=user).delete()
        FuelRefillLog.objects.filter(user=user).delete()
        BikeConditionSnapshot.objects.filter(user=user).delete()
        bike_document_qs.delete()
        trip_photo_qs.delete()
        TripLog.objects.filter(user=user).delete()
        TravelPlan.objects.filter(user=user).delete()
        BikeProfile.objects.filter(user=user).delete()

        CreditReportUpload.objects.filter(user=user).delete()
        CreditScore.objects.filter(user=user).delete()
        EmailConnection.objects.filter(user=user).delete()
        VerifiedExternalInsight.objects.filter(user=user).delete()

        BehavioralSignal.objects.filter(user=user).delete()
        Budget.objects.filter(user=user).delete()
        Dependent.objects.filter(user=user).delete()
        family_link_qs.delete()
        RelationshipProfile.objects.filter(user=user).delete()
        RiskSignal.objects.filter(user=user).delete()

        DocumentParserLearningMemory.objects.filter(user=user).delete()
        ChatGPTImport.objects.filter(user=user).delete()
        generated_report_qs.delete()
        SystemTicket.objects.filter(user=user).delete()
        OperationalLog.objects.filter(user=user).delete()

        user.monthly_income = 0
        user.variable_income = 0
        user.rent_or_emi = 0
        user.city = ""
        user.country = ""
        user.save(update_fields=["monthly_income", "variable_income", "rent_or_emi", "city", "country"])

    _delete_storage_files(file_names)
    _delete_generated_report_paths(generated_paths)
    invalidate_user_materialized_payloads(user.id, reason="user_data_reset")
    for linked_user_id in linked_family_user_ids:
        invalidate_user_materialized_payloads(linked_user_id, reason="family_link_user_data_reset")
    summary["profile_fields_reset"] = True
    summary["account_preserved"] = True
    summary["materialized_caches_cleared"] = True
    return summary
