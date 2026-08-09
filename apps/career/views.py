from datetime import timedelta

from django.db.models import Count, Max
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.generics import ListAPIView, RetrieveUpdateAPIView
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from alfred_ai.services import record_parser_learning
from alfred_ai.services.materialized_cache import materialize_payload
from alfred_ai.services.upload_privacy import purge_uploaded_file_after_extraction
from apps.expenses.models import BankAccount
from apps.expenses.services.financial_intelligence import resolve_canonical_financial_baseline
from apps.integrations.services import verified_intelligence
from apps.loans.models import Loan
from apps.reports.services import operational_logging_service
from .models import CareerJobAnalysis, CareerProfile, CareerResume
from .serializers import CareerJobAnalysisSerializer, CareerProfileSerializer, CareerProjectionScenarioSerializer, CareerResumeSerializer
from .services import build_employment_income_signals, build_projection_simulation, build_salary_projection, job_intelligence, resume_intelligence


def _get_profile(user):
    profile, _ = CareerProfile.objects.get_or_create(
        user=user,
        defaults={
            "role": "Profile pending",
            "experience_years": 0,
            "skills": "",
            "last_salary": getattr(user, "monthly_income", 0) or 0,
        },
    )
    return profile


def _resume_payload_from_profile(profile) -> dict:
    return {
        "role": profile.role,
        "experience_years": profile.experience_years,
        "skills": [item.strip() for item in (profile.skills or "").split(",") if item.strip()],
    }


def _study_recommendations_payload(profile, latest_resume=None, latest_analysis=None, openings=None) -> dict:
    resume_payload = latest_resume.extracted_payload if latest_resume else _resume_payload_from_profile(profile)
    return job_intelligence.build_study_recommendations(
        profile,
        resume_payload,
        latest_analysis=latest_analysis,
        openings=openings or [],
    )


def _compensation_benchmark_payload(user, profile, *, openings=None, openings_evidence=None, latest_analysis=None, latest_resume=None, income_signals: dict | None = None, country: str = "", state: str = "") -> dict:
    role = profile.role if profile.role and profile.role != "Profile pending" else ((latest_resume.extracted_payload.get("role", "") if latest_resume else "") or "analyst")
    filter_location = ", ".join(part for part in [state, country] if part)
    location = getattr(user, "city", "") or getattr(latest_analysis, "location", "") or filter_location
    resolved_income_signals = income_signals or build_employment_income_signals(user=user, latest_resume=latest_resume, profile=profile)
    snapshot_payload = ((getattr(latest_analysis, "extracted_payload", {}) or {}).get("job_snapshot", {}) if latest_analysis else {}) or {}
    job_snapshot = None
    if latest_analysis and snapshot_payload:
        job_snapshot = job_intelligence.parse_recruiter_message(
            " ".join(
                str(item)
                for item in [
                    snapshot_payload.get("title", ""),
                    snapshot_payload.get("company", ""),
                    snapshot_payload.get("location", ""),
                ]
                if item
            )
        )
        job_snapshot.job_url = latest_analysis.job_url
        job_snapshot.apply_url = latest_analysis.apply_url or latest_analysis.job_url
        job_snapshot.company = snapshot_payload.get("company", "") or job_snapshot.company
        job_snapshot.title = snapshot_payload.get("title", "") or job_snapshot.title
        job_snapshot.location = snapshot_payload.get("location", "") or job_snapshot.location
        job_snapshot.required_skills = snapshot_payload.get("required_skills", []) or job_snapshot.required_skills
        job_snapshot.experience_years = float(snapshot_payload.get("experience_years") or job_snapshot.experience_years or 0)
        job_snapshot.salary_min = float(snapshot_payload.get("salary_min") or 0)
        job_snapshot.salary_max = float(snapshot_payload.get("salary_max") or 0)
        job_snapshot.salary_currency = snapshot_payload.get("salary_currency", "")
        job_snapshot.salary_period = snapshot_payload.get("salary_period", "")
        job_snapshot.source_kind = snapshot_payload.get("source_kind", "job_page")
        job_snapshot.source_name = latest_analysis.source_name or job_snapshot.source_name
    return job_intelligence.compensation_benchmark(
        role=role,
        location=location,
        openings=openings or [],
        job_snapshot=job_snapshot,
        openings_evidence=openings_evidence,
        current_income_annual=float(resolved_income_signals.get("annualized_compensation", 0) or 0),
    )


def _clamp(value: float, lower: float = 0.0, upper: float = 100.0) -> float:
    return max(lower, min(upper, value))


def _career_projection_payload(user, profile, macro: dict | None = None, *, latest_resume=None, income_signals: dict | None = None) -> dict:
    macro = macro or verified_intelligence.macro_context()
    return build_salary_projection(user, profile, macro=macro, latest_resume=latest_resume, income_signals=income_signals)


def _career_timing_payload(user, profile, market: dict, latest_analysis=None, latest_resume=None, income_signals: dict | None = None) -> dict:
    today = timezone.localdate()
    resolved_income_signals = income_signals or build_employment_income_signals(user=user, latest_resume=latest_resume, profile=profile)
    baseline = resolve_canonical_financial_baseline(user)
    monthly_income = float(baseline.get("monthly_income", 0) or 0)
    liquid_cash = float(baseline.get("liquid_cash", 0) or 0)
    monthly_loan_emi = float(baseline.get("recurring_emi_burden", 0) or 0)
    total_fixed_load = float(baseline.get("fixed_obligations", 0) or 0)
    emergency_months = float(baseline.get("liquid_runway_months", 0) or 0)
    fixed_load_ratio = float(baseline.get("debt_burden_ratio", 0) or 0)
    market_risk = float(market.get("risk_score", 0) or 0)
    fit_score = float(getattr(latest_analysis, "fit_score", 0) or 0) if latest_analysis else 0.0

    readiness_score = _clamp(
        100
        - market_risk
        + min(emergency_months * 9, 28)
        + (max(fit_score - 60, 0) * 0.45 if latest_analysis else 4)
        + (6 if 0 < fixed_load_ratio <= 40 else 0)
        - (16 if emergency_months < 2 else (8 if emergency_months < 4 else 0))
        - (8 if fixed_load_ratio >= 55 else 0)
    )

    if readiness_score >= 72:
        readiness_level = "favorable"
        window_start = today
        window_end = today + timedelta(days=90)
        summary = "Current conditions support a calculated career move if the role quality is strong."
        next_step = "You can push for external interviews, internal role changes, or salary negotiations in this window."
    elif readiness_score >= 52:
        readiness_level = "build"
        window_start = today + timedelta(days=45)
        window_end = today + timedelta(days=180)
        summary = "Build a little more buffer and close visible fit gaps before taking the bigger career risk."
        next_step = "Use the next review window to raise cash runway, strengthen the resume, and improve job-fit before switching."
    else:
        readiness_level = "guarded"
        window_start = today + timedelta(days=120)
        window_end = today + timedelta(days=365)
        summary = "Large career risk is better delayed until financial runway or market conditions improve."
        next_step = "Prioritize stability, savings, and targeted upskilling before attempting a high-risk move."

    moves = [
        {
            "label": "Job switch",
            "status": "go" if readiness_score >= 72 and (fit_score >= 65 or not latest_analysis) else ("prepare" if readiness_score >= 52 else "hold"),
            "note": "Best used when runway and role-fit are both strong enough to absorb a slower search cycle.",
        },
        {
            "label": "Promotion or compensation ask",
            "status": "go" if readiness_score >= 58 else "prepare",
            "note": "Lower financial risk than quitting, so this can usually happen earlier than a full switch.",
        },
        {
            "label": "Skill upgrade or certification",
            "status": "go",
            "note": "This is the safest risk to take because it improves leverage even in a weaker market.",
        },
        {
            "label": "Freelance or side-income bet",
            "status": "go" if emergency_months >= 6 and market_risk < 55 else ("prepare" if emergency_months >= 3 else "hold"),
            "note": "Best taken only when your liquid buffer can protect your base monthly obligations.",
        },
    ]

    signals = [
        f"Liquid runway is {emergency_months:.1f} months.",
        f"Fixed monthly load is {fixed_load_ratio:.1f}% of income." if monthly_income else "Income data is still incomplete, so readiness is conservative.",
        f"External market risk is {market_risk:.0f}/100.",
        f"Latest analyzed job-fit is {fit_score:.0f}/100." if latest_analysis else "No job-link fit has been analyzed yet.",
    ]
    blockers = []
    if emergency_months < 3:
        blockers.append("Increase liquid runway before making a high-volatility move.")
    if market_risk >= 55:
        blockers.append("Hiring conditions are still elevated-risk for this role.")
    if latest_analysis and fit_score < 65:
        blockers.append("Close the visible skill or experience gaps before treating the matched role as a target.")
    if not blockers:
        blockers.append("No major blocker is dominant right now, but keep evidence and runway under review.")

    return {
        "readiness_score": round(readiness_score, 1),
        "readiness_level": readiness_level,
        "window_start": window_start.isoformat(),
        "window_end": window_end.isoformat(),
        "next_review_date": (today + timedelta(days=30)).isoformat(),
        "summary": summary,
        "next_step": next_step,
        "signals": signals,
        "blockers": blockers[:4],
        "moves": moves,
        "income_source_summary": resolved_income_signals.get("source_summary", ""),
        "financial_baseline": baseline,
    }


def _career_data_pipeline_payload(profile, latest_resume, latest_analysis, projection, market, career_timing) -> dict:
    resume_payload = latest_resume.extracted_payload if latest_resume else {}
    job_payload = latest_analysis.extracted_payload if latest_analysis else {}
    manual_skill_count = len([item for item in (profile.skills or "").split(",") if item.strip()])
    evidence_count = len([item for item in [*(projection.get("evidence") or []), *(market.get("evidence") or [])] if item])
    latest_fit = job_payload.get("fit", {}).get("fit_score", getattr(latest_analysis, "fit_score", 0) if latest_analysis else 0)

    return {
        "collection": [
            f"Manual profile inputs: role '{profile.role}', {profile.experience_years:.1f} years experience, and {manual_skill_count} listed skills.",
            (
                f"Latest resume upload '{latest_resume.file_name}' with parser status {latest_resume.get_parser_status_display().lower()} and confidence {latest_resume.parse_confidence * 100:.0f}%."
                if latest_resume
                else "No resume upload is currently available, so the profile is the primary source."
            ),
            (
                f"Latest {job_payload.get('source_kind', 'job_link').replace('_', ' ')} analysis stored for {latest_analysis.job_title or 'the matched role'}."
                if latest_analysis
                else "No job-link analysis has been stored yet."
            ),
            "External evidence is pulled from verified macro, news, and job-opening sources with freshness metadata.",
        ],
        "processing": [
            f"Profile and resume skills are normalized into a comparable skill set of {len(resume_payload.get('skills', [])) or projection['projection_basis']['skills_count']} items.",
            "Job links are parsed for title, company, location, skill requirements, and experience expectations before fit scoring.",
            f"Projection mode is {projection.get('projection_mode', 'heuristic').replace('_', ' ')}. {projection.get('projection_method', '')}",
            f"Career timing then blends market risk, financial runway, fixed monthly load, and job-fit into a readiness score of {career_timing['readiness_score']}/100.",
        ],
        "verification": [
            "Resume files are stored with parser status and confidence instead of being silently trusted.",
            "Job pages are rejected if the parser cannot extract enough structure to analyze the role reliably.",
            "External records are cached with source URL, verified timestamp, and stale-after metadata.",
            "Career timing uses active bank balances and active loan obligations only, so inactive accounts or closed loans do not distort the runway.",
        ],
        "current_state": [
            f"Evidence records currently attached: {evidence_count}.",
            f"Latest career timing review date is {career_timing['next_review_date']}.",
            (
                f"Latest matched job contributes a fit score of {latest_fit}/100."
                if latest_analysis
                else "Job-fit influence is currently limited because no recent job link is stored."
            ),
        ],
    }


def _opening_filter_params(request) -> tuple[str, str]:
    return (
        str(request.query_params.get("country", "") or "").strip(),
        str(request.query_params.get("state", "") or "").strip(),
    )


def _career_dashboard_revision(user, *, country: str = "", state: str = "") -> str:
    profile = CareerProfile.objects.filter(user=user).first()
    resume_meta = CareerResume.objects.filter(user=user).aggregate(count=Count("id"), max_id=Max("id"), max_updated=Max("updated_at"))
    analysis_meta = CareerJobAnalysis.objects.filter(user=user).aggregate(count=Count("id"), max_id=Max("id"), max_created=Max("created_at"), max_updated=Max("updated_at"))
    account_meta = BankAccount.objects.filter(user=user, is_active=True).aggregate(count=Count("id"), max_id=Max("id"), max_synced=Max("last_synced_at"))
    loan_meta = Loan.objects.filter(user=user).aggregate(count=Count("id"), max_id=Max("id"))
    return "|".join(
        str(value or "")
        for value in [
            getattr(profile, "role", ""),
            getattr(profile, "experience_years", 0),
            getattr(profile, "skills", ""),
            getattr(profile, "last_salary", 0),
            resume_meta["count"], resume_meta["max_id"], resume_meta["max_updated"],
            analysis_meta["count"], analysis_meta["max_id"], analysis_meta["max_created"], analysis_meta["max_updated"],
            account_meta["count"], account_meta["max_id"], account_meta["max_synced"],
            loan_meta["count"], loan_meta["max_id"],
            country,
            state,
        ]
    )


def _career_outcome_learning_payload(user) -> dict:
    analyses = CareerJobAnalysis.objects.filter(user=user).order_by("-updated_at", "-id")
    return job_intelligence.opportunity_outcome_learning_summary(analyses)


def _job_snapshot_payload(snapshot) -> dict:
    return {
        "title": snapshot.title,
        "company": snapshot.company,
        "location": snapshot.location,
        "required_skills": snapshot.required_skills,
        "experience_years": snapshot.experience_years,
        "salary_min": snapshot.salary_min,
        "salary_max": snapshot.salary_max,
        "salary_currency": snapshot.salary_currency,
        "salary_period": snapshot.salary_period,
        "employment_type": snapshot.employment_type,
        "source_kind": snapshot.source_kind,
    }


def _analysis_parser_state(snapshot, *, source_kind: str, attachment_present: bool = False) -> tuple[str, float]:
    confidence = 0.18
    if snapshot.title:
        confidence += 0.18
    if snapshot.company:
        confidence += 0.12
    if snapshot.location:
        confidence += 0.08
    if snapshot.required_skills:
        confidence += 0.16
    if snapshot.experience_years:
        confidence += 0.08
    if snapshot.salary_min or snapshot.salary_max:
        confidence += 0.1
    if snapshot.apply_url and snapshot.apply_url.startswith("http"):
        confidence += 0.08
    if source_kind == "job_page" and snapshot.description:
        confidence += 0.1
    if attachment_present:
        confidence += 0.06
    confidence = round(min(confidence, 0.96), 2)
    parser_status = "parsed" if confidence >= 0.62 else ("needs_review" if snapshot.description or snapshot.title or snapshot.company else "failed")
    return parser_status, confidence


class CareerProfileView(RetrieveUpdateAPIView):
    serializer_class = CareerProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return _get_profile(self.request.user)


class CareerResumeListView(ListAPIView):
    serializer_class = CareerResumeSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return CareerResume.objects.filter(user=self.request.user).order_by("-created_at", "-id")


class CareerResumeUploadView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        resume_file = request.FILES.get("resume")
        if resume_file is None:
            return Response({"detail": "Upload a resume file first."}, status=status.HTTP_400_BAD_REQUEST)

        parsed = resume_intelligence.parse(resume_file, resume_file.name, user=request.user)
        resume_file.seek(0)
        resume = CareerResume.objects.create(
            user=request.user,
            uploaded_file=resume_file,
            file_name=resume_file.name,
            parser_status=parsed.parser_status,
            parse_confidence=parsed.confidence,
            extracted_text=parsed.extracted_text,
            extracted_payload=parsed.payload,
            summary=parsed.summary,
            strengths="\n".join(parsed.strengths),
            weaknesses="\n".join(parsed.weaknesses),
        )
        record_parser_learning(
            user=request.user,
            scope="resume_document",
            filename=resume_file.name,
            detected_type="resume",
            text=parsed.extracted_text,
            field_names=[key for key, value in parsed.payload.items() if value not in ("", None, 0, [])],
            parser_status=parsed.parser_status,
            confidence=parsed.confidence,
        )
        resume_intelligence.record_parse_outcome(request.user, resume_file.name, parsed)
        profile = _get_profile(request.user)
        resume_intelligence.apply_to_profile(profile, parsed)
        if parsed.parser_status != "parsed":
            operational_logging_service.log(
                user=request.user,
                module="career",
                category="document",
                scope="resume_document",
                event_type="resume_needs_review",
                severity="warning",
                document_id=resume.id,
                file_name=resume.file_name,
                message="Resume upload was saved, but Alfred still needs review before it can rely on the extracted career data.",
                payload={
                    "parser_status": parsed.parser_status,
                    "parse_confidence": parsed.confidence,
                    "summary": parsed.summary,
                },
            )
        raw_file_retention = purge_uploaded_file_after_extraction(
            resume,
            "uploaded_file",
            reason="resume_extraction_complete",
        )
        return Response(
            {
                "detail": (
                    "Resume uploaded and parsed."
                    if parsed.parser_status == "parsed"
                    else "Resume uploaded, but Alfred needs review because the text was weak, scanned, or in an unusual format."
                ),
                "resume": CareerResumeSerializer(resume, context={"request": request}).data,
                "profile": CareerProfileSerializer(profile).data,
                "raw_file_retention": raw_file_retention,
            },
            status=status.HTTP_201_CREATED,
        )


class CareerRecruiterMatchView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def post(self, request):
        message_text = (request.data.get("message_text") or "").strip()
        attachment = request.FILES.get("attachment")
        if not message_text and attachment is None:
            return Response({"detail": "Paste recruiter mail text or upload a JD attachment first."}, status=status.HTTP_400_BAD_REQUEST)

        profile = _get_profile(request.user)
        latest_resume = CareerResume.objects.filter(user=request.user).order_by("-created_at", "-id").first()
        resume_payload = latest_resume.extracted_payload if latest_resume else _resume_payload_from_profile(profile)
        macro = verified_intelligence.macro_context()
        income_signals = build_employment_income_signals(user=request.user, latest_resume=latest_resume, profile=profile)

        try:
            snapshot = job_intelligence.parse_recruiter_message(
                message_text,
                attachment=attachment,
                filename=getattr(attachment, "name", ""),
            )
        except Exception as exc:
            return Response({"detail": f"Recruiter intake could not be parsed: {exc}"}, status=status.HTTP_400_BAD_REQUEST)

        fit = job_intelligence.compare_resume_to_job(resume_payload, snapshot)
        market = job_intelligence.market_outlook(snapshot.title or profile.role, snapshot.company, macro=macro)
        openings = job_intelligence.suggest_openings(snapshot.title or profile.role, resume_payload.get("skills") or [])
        compensation = job_intelligence.compensation_benchmark(
            role=snapshot.title or profile.role,
            location=snapshot.location or getattr(request.user, "city", ""),
            openings=openings["openings"],
            job_snapshot=snapshot,
            openings_evidence=openings["evidence"],
            current_income_annual=float(income_signals.get("annualized_compensation", 0) or 0),
        )
        parser_status, confidence = _analysis_parser_state(
            snapshot,
            source_kind=snapshot.source_kind,
            attachment_present=attachment is not None,
        )
        record_parser_learning(
            user=request.user,
            scope="recruiter_document",
            filename=getattr(attachment, "name", "") or "recruiter_message.txt",
            detected_type="recruiter_message" if message_text else "jd_attachment",
            text=snapshot.description,
            field_names=[
                field_name
                for field_name, value in {
                    "title": snapshot.title,
                    "company": snapshot.company,
                    "location": snapshot.location,
                    "salary_min": snapshot.salary_min,
                    "salary_max": snapshot.salary_max,
                    "employment_type": snapshot.employment_type,
                }.items()
                if value not in ("", None, 0)
            ] + list(snapshot.required_skills[:8]),
            parser_status=parser_status,
            confidence=confidence,
        )
        analysis = CareerJobAnalysis.objects.create(
            user=request.user,
            source_name=snapshot.source_name,
            source_document_name=getattr(attachment, "name", "") or "recruiter_message.txt",
            job_url=snapshot.job_url,
            apply_url=snapshot.apply_url,
            company=snapshot.company,
            job_title=snapshot.title,
            location=snapshot.location,
            parser_status=parser_status,
            parse_confidence=confidence,
            extracted_text=snapshot.description,
            fit_score=fit["fit_score"],
            market_risk_score=market["risk_score"],
            strengths="\n".join(fit["strengths"]),
            gaps="\n".join(fit["gaps"]),
            summary=f"Recruiter intake fit score {fit['fit_score']}/100 for {snapshot.title or 'this role'} at {snapshot.company or snapshot.source_name}.",
            extracted_payload={
                "source_kind": snapshot.source_kind,
                "intake_confidence": confidence,
                "intake_message_text": message_text,
                "intake_combined_text": snapshot.description,
                "attachment_file_name": getattr(attachment, "name", ""),
                "resume_payload": resume_payload,
                "job_snapshot": _job_snapshot_payload(snapshot),
                "fit": fit,
                "compensation_benchmark": compensation,
                "intake_excerpt": snapshot.description[:2500],
            },
            evidence=[*market["evidence"], *(compensation.get("evidence") or [])][:8],
        )
        career_timing = _career_timing_payload(request.user, profile, market, analysis, latest_resume=latest_resume, income_signals=income_signals)
        study_recommendations = job_intelligence.build_study_recommendations(
            profile,
            resume_payload,
            latest_analysis=analysis,
            openings=openings["openings"],
        )
        return Response(
            {
                "analysis": CareerJobAnalysisSerializer(analysis).data,
                "job_snapshot": {
                    "source_name": snapshot.source_name,
                    "job_url": snapshot.job_url,
                    "apply_url": snapshot.apply_url,
                    "company": snapshot.company,
                    "title": snapshot.title,
                    "location": snapshot.location,
                    "required_skills": snapshot.required_skills,
                    "experience_years": snapshot.experience_years,
                    "salary_min": snapshot.salary_min,
                    "salary_max": snapshot.salary_max,
                    "salary_currency": snapshot.salary_currency,
                    "salary_period": snapshot.salary_period,
                    "employment_type": snapshot.employment_type,
                    "source_kind": snapshot.source_kind,
                },
                "fit": fit,
                "market": market,
                "career_timing": career_timing,
                "study_recommendations": study_recommendations,
                "openings": openings["openings"],
                "openings_evidence": openings["evidence"],
                "openings_source_coverage": openings.get("source_coverage", {}),
                "compensation_benchmark": compensation,
                "employment_signals": income_signals,
            }
        )


class CareerJobMatchView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser]

    def post(self, request):
        job_url = (request.data.get("job_url") or "").strip()
        if not job_url:
            return Response({"detail": "Paste a job URL first."}, status=status.HTTP_400_BAD_REQUEST)

        profile = _get_profile(request.user)
        latest_resume = CareerResume.objects.filter(user=request.user).order_by("-created_at", "-id").first()
        resume_payload = latest_resume.extracted_payload if latest_resume else _resume_payload_from_profile(profile)
        macro = verified_intelligence.macro_context()
        income_signals = build_employment_income_signals(user=request.user, latest_resume=latest_resume, profile=profile)

        try:
            job_snapshot = job_intelligence.parse_job_page(job_url)
        except Exception as exc:
            return Response({"detail": f"Job page could not be parsed: {exc}"}, status=status.HTTP_400_BAD_REQUEST)

        fit = job_intelligence.compare_resume_to_job(resume_payload, job_snapshot)
        market = job_intelligence.market_outlook(job_snapshot.title or profile.role, job_snapshot.company, macro=macro)
        openings = job_intelligence.suggest_openings(job_snapshot.title or profile.role, resume_payload.get("skills") or [])
        compensation = job_intelligence.compensation_benchmark(
            role=job_snapshot.title or profile.role,
            location=job_snapshot.location or getattr(request.user, "city", ""),
            openings=openings["openings"],
            job_snapshot=job_snapshot,
            openings_evidence=openings["evidence"],
            current_income_annual=float(income_signals.get("annualized_compensation", 0) or 0),
        )
        parser_status, parse_confidence = _analysis_parser_state(job_snapshot, source_kind=job_snapshot.source_kind)
        analysis = CareerJobAnalysis.objects.create(
            user=request.user,
            source_name=job_snapshot.source_name,
            source_document_name="job_page_url",
            job_url=job_snapshot.job_url,
            apply_url=job_snapshot.apply_url,
            company=job_snapshot.company,
            job_title=job_snapshot.title,
            location=job_snapshot.location,
            parser_status=parser_status,
            parse_confidence=parse_confidence,
            extracted_text=job_snapshot.description,
            fit_score=fit["fit_score"],
            market_risk_score=market["risk_score"],
            strengths="\n".join(fit["strengths"]),
            gaps="\n".join(fit["gaps"]),
            summary=f"Fit score {fit['fit_score']}/100 for {job_snapshot.title or 'this role'} at {job_snapshot.company or job_snapshot.source_name}.",
            extracted_payload={
                "resume_payload": resume_payload,
                "job_snapshot": _job_snapshot_payload(job_snapshot),
                "fit": fit,
                "compensation_benchmark": compensation,
            },
            evidence=[*market["evidence"], *(compensation.get("evidence") or [])][:8],
        )
        career_timing = _career_timing_payload(request.user, profile, market, analysis, latest_resume=latest_resume, income_signals=income_signals)
        study_recommendations = job_intelligence.build_study_recommendations(
            profile,
            resume_payload,
            latest_analysis=analysis,
            openings=openings["openings"],
        )
        return Response(
            {
                "analysis": CareerJobAnalysisSerializer(analysis).data,
                "job_snapshot": {
                    "source_name": job_snapshot.source_name,
                    "job_url": job_snapshot.job_url,
                    "apply_url": job_snapshot.apply_url,
                    "company": job_snapshot.company,
                    "title": job_snapshot.title,
                    "location": job_snapshot.location,
                    "required_skills": job_snapshot.required_skills,
                    "experience_years": job_snapshot.experience_years,
                    "salary_min": job_snapshot.salary_min,
                    "salary_max": job_snapshot.salary_max,
                    "salary_currency": job_snapshot.salary_currency,
                    "salary_period": job_snapshot.salary_period,
                    "employment_type": job_snapshot.employment_type,
                    "source_kind": job_snapshot.source_kind,
                },
                "fit": fit,
                "market": market,
                "career_timing": career_timing,
                "study_recommendations": study_recommendations,
                "openings": openings["openings"],
                "openings_evidence": openings["evidence"],
                "openings_source_coverage": openings.get("source_coverage", {}),
                "compensation_benchmark": compensation,
                "employment_signals": income_signals,
            }
        )


class CareerJobOutcomeView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser]

    def post(self, request, pk):
        analysis = CareerJobAnalysis.objects.filter(user=request.user, id=pk).first()
        if analysis is None:
            return Response({"detail": "Job analysis not found."}, status=status.HTTP_404_NOT_FOUND)
        try:
            outcome = job_intelligence.normalize_opportunity_outcome(analysis, request.data)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        extracted_payload = dict(analysis.extracted_payload or {})
        extracted_payload["opportunity_outcome"] = outcome
        analysis.extracted_payload = extracted_payload
        analysis.save(update_fields=["extracted_payload", "updated_at"])
        return Response(
            {
                "analysis": CareerJobAnalysisSerializer(analysis).data,
                "opportunity_outcome": outcome,
                "opportunity_outcome_learning": _career_outcome_learning_payload(request.user),
            }
        )

    patch = post


class CareerProjectionSimulationView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser]

    def post(self, request):
        serializer = CareerProjectionScenarioSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        profile = _get_profile(request.user)
        latest_resume = CareerResume.objects.filter(user=request.user).order_by("-created_at", "-id").first()
        macro = verified_intelligence.macro_context()

        return Response(
            build_projection_simulation(
                user=request.user,
                profile=profile,
                macro=macro,
                latest_resume=latest_resume,
                overrides=serializer.validated_data,
            )
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def career_projection(request):
    """Get career growth projection."""
    try:
        profile = _get_profile(request.user)
        latest_resume = CareerResume.objects.filter(user=request.user).order_by("-created_at", "-id").first()
        macro = verified_intelligence.macro_context()
        income_signals = build_employment_income_signals(user=request.user, latest_resume=latest_resume, profile=profile)
        projection = _career_projection_payload(request.user, profile, macro=macro, latest_resume=latest_resume, income_signals=income_signals)
        latest_analysis = CareerJobAnalysis.objects.filter(user=request.user).order_by("-created_at", "-id").first()
        role = profile.role if profile.role and profile.role != "Profile pending" else "analyst"
        market = job_intelligence.market_outlook(role, macro=macro)
        return Response(
            {
                **projection,
                "career_timing": _career_timing_payload(request.user, profile, market, latest_analysis, latest_resume=latest_resume, income_signals=income_signals),
                "employment_signals": income_signals,
            }
        )
    except Exception as e:
        return Response({"error": str(e)}, status=500)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def career_dashboard(request):
    _get_profile(request.user)
    country, state = _opening_filter_params(request)
    payload = materialize_payload(
        namespace="career-dashboard",
        user_id=request.user.id,
        revision=_career_dashboard_revision(request.user, country=country, state=state),
        ttl_seconds=45,
        builder=lambda: _career_dashboard_payload(request),
    )
    return Response(payload)


def _career_dashboard_payload(request) -> dict:
    profile = _get_profile(request.user)
    latest_resume = CareerResume.objects.filter(user=request.user).order_by("-created_at", "-id").first()
    latest_analysis = CareerJobAnalysis.objects.filter(user=request.user).order_by("-created_at", "-id").first()
    macro = verified_intelligence.macro_context()
    income_signals = build_employment_income_signals(user=request.user, latest_resume=latest_resume, profile=profile)
    country, state = _opening_filter_params(request)
    projection = _career_projection_payload(request.user, profile, macro=macro, latest_resume=latest_resume, income_signals=income_signals)
    role = profile.role if profile.role and profile.role != "Profile pending" else ((latest_resume.extracted_payload.get("role", "") if latest_resume else "") or "analyst")
    skills = latest_resume.extracted_payload.get("skills", []) if latest_resume else [item.strip() for item in (profile.skills or "").split(",") if item.strip()]
    market = job_intelligence.market_outlook(role, macro=macro)
    openings = job_intelligence.suggest_openings(role, skills, country=country, state=state)
    career_timing = _career_timing_payload(request.user, profile, market, latest_analysis, latest_resume=latest_resume, income_signals=income_signals)
    study_recommendations = _study_recommendations_payload(profile, latest_resume, latest_analysis, openings["openings"])
    data_pipeline = _career_data_pipeline_payload(profile, latest_resume, latest_analysis, projection, market, career_timing)
    compensation_benchmark = _compensation_benchmark_payload(
        request.user,
        profile,
        openings=openings["openings"],
        openings_evidence=openings["evidence"],
        latest_analysis=latest_analysis,
        latest_resume=latest_resume,
        income_signals=income_signals,
        country=country,
        state=state,
    )
    return {
        "profile": CareerProfileSerializer(profile).data,
        "employment_signals": income_signals,
        "projection": projection,
        "latest_resume": CareerResumeSerializer(latest_resume, context={"request": request}).data if latest_resume else None,
        "latest_job_analysis": CareerJobAnalysisSerializer(latest_analysis).data if latest_analysis else None,
        "market": market,
        "career_timing": career_timing,
        "study_recommendations": study_recommendations,
        "data_pipeline": data_pipeline,
        "openings": openings["openings"],
        "openings_evidence": openings["evidence"],
        "openings_source_coverage": openings.get("source_coverage", {}),
        "opening_filters": openings.get("filters", {}),
        "active_opening_filters": openings.get("active_filters", {"country": country, "state": state}),
        "opening_counts": {
            "total_candidates": openings.get("total_candidates", len(openings["openings"])),
            "filtered_candidates": openings.get("filtered_candidates", len(openings["openings"])),
        },
        "compensation_benchmark": compensation_benchmark,
        "opportunity_outcome_learning": _career_outcome_learning_payload(request.user),
    }
