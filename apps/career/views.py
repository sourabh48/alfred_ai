from datetime import timedelta

from django.db.models import Sum
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.generics import ListAPIView, RetrieveUpdateAPIView
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.expenses.models import BankAccount
from apps.integrations.services import verified_intelligence
from apps.loans.models import Loan
from .models import CareerJobAnalysis, CareerProfile, CareerResume
from .serializers import CareerJobAnalysisSerializer, CareerProfileSerializer, CareerResumeSerializer
from .services import job_intelligence, resume_intelligence


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


def _clamp(value: float, lower: float = 0.0, upper: float = 100.0) -> float:
    return max(lower, min(upper, value))


def _career_projection_payload(user, profile, macro: dict | None = None) -> dict:
    current_income = getattr(user, "monthly_income", 0) or profile.last_salary or 0
    macro = macro or verified_intelligence.macro_context()
    unemployment = macro["payload"]["unemployment"].get("latest_value") or 0
    inflation = macro["payload"]["inflation"].get("latest_value") or 0
    market_return = macro["payload"]["market"].get("one_month_return_pct") or 0

    skills = [item.strip() for item in (profile.skills or "").split(",") if item.strip()]
    skills_score = min(len(skills) * 0.004, 0.02)
    experience_score = 0.012 if 2 <= profile.experience_years <= 8 else (0.008 if profile.experience_years > 8 else 0.004)
    macro_drag = max(unemployment - 5, 0) * 0.003 + max(inflation - 6, 0) * 0.002
    market_signal = 0.003 if market_return > 2 else (-0.003 if market_return < -5 else 0)
    annual_growth = min(max(0.07 + skills_score + experience_score + market_signal - macro_drag, 0.03), 0.16)

    projections = []
    for year in range(1, 6):
        projected_income = current_income * ((1 + annual_growth) ** year)
        projections.append(
            {
                "year": year,
                "projected_income": round(projected_income, 2),
                "real_income_estimate": round(projected_income / ((1 + (inflation / 100)) ** year), 2) if inflation else round(projected_income, 2),
                "confidence": max(42, round(84 - (year * 7) - (macro_drag * 100))),
            }
        )

    insights = [
        f"Modeled annual nominal growth is {annual_growth * 100:.1f}% using role history, skill density, and current macro signals.",
        f"Latest tracked India unemployment signal is {unemployment} and inflation is {inflation}.",
        "Resume and job-match data can sharpen the growth view beyond the manual profile alone.",
    ]
    if market_return < -5:
        insights.append("Recent market weakness can tighten hiring budgets. Keep a stronger interview and savings buffer.")
    elif market_return > 5:
        insights.append("Risk appetite in the market looks better than average, which can support role-switch timing.")

    return {
        "current_income": current_income,
        "projections": projections,
        "projection_basis": {
            "annual_growth_rate": round(annual_growth * 100, 2),
            "skills_count": len(skills),
            "experience_years": profile.experience_years,
            "macro_drag": round(macro_drag * 100, 2),
        },
        "macro_context": macro["payload"],
        "evidence": macro["evidence"],
        "insights": insights[:5],
    }


def _career_timing_payload(user, profile, market: dict, latest_analysis=None) -> dict:
    today = timezone.localdate()
    monthly_income = getattr(user, "monthly_income", 0) or profile.last_salary or 0
    rent_or_emi = getattr(user, "rent_or_emi", 0) or 0
    liquid_cash = (
        BankAccount.objects.filter(user=user, is_active=True)
        .exclude(account_type="credit")
        .aggregate(total=Sum("current_balance"))
        .get("total")
        or 0.0
    )
    monthly_loan_emi = Loan.objects.filter(user=user, is_active=True).aggregate(total=Sum("emi")).get("total") or 0.0
    total_fixed_load = monthly_loan_emi + rent_or_emi
    emergency_months = (liquid_cash / max(total_fixed_load, 1)) if total_fixed_load else (liquid_cash / max(monthly_income, 1) if monthly_income else 0.0)
    fixed_load_ratio = ((total_fixed_load / monthly_income) * 100) if monthly_income else 0.0
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
                f"Latest job-link analysis stored for {latest_analysis.job_title or 'the matched role'}."
                if latest_analysis
                else "No job-link analysis has been stored yet."
            ),
            "External evidence is pulled from verified macro, news, and job-opening sources with freshness metadata.",
        ],
        "processing": [
            f"Profile and resume skills are normalized into a comparable skill set of {len(resume_payload.get('skills', [])) or projection['projection_basis']['skills_count']} items.",
            "Job links are parsed for title, company, location, skill requirements, and experience expectations before fit scoring.",
            f"Projection growth blends skill density, experience, inflation, unemployment, and market-return drag into an annual growth estimate of {projection['projection_basis']['annual_growth_rate']}%.",
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


class CareerProfileView(RetrieveUpdateAPIView):
    serializer_class = CareerProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return _get_profile(self.request.user)


class CareerResumeListView(ListAPIView):
    serializer_class = CareerResumeSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return CareerResume.objects.filter(user=self.request.user)


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
        resume_intelligence.record_parse_outcome(request.user, resume_file.name, parsed)
        profile = _get_profile(request.user)
        resume_intelligence.apply_to_profile(profile, parsed)
        return Response(
            {
                "detail": (
                    "Resume uploaded and parsed."
                    if parsed.parser_status == "parsed"
                    else "Resume uploaded, but Alfred needs review because the text was weak, scanned, or in an unusual format."
                ),
                "resume": CareerResumeSerializer(resume, context={"request": request}).data,
                "profile": CareerProfileSerializer(profile).data,
            },
            status=status.HTTP_201_CREATED,
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

        try:
            job_snapshot = job_intelligence.parse_job_page(job_url)
        except Exception as exc:
            return Response({"detail": f"Job page could not be parsed: {exc}"}, status=status.HTTP_400_BAD_REQUEST)

        fit = job_intelligence.compare_resume_to_job(resume_payload, job_snapshot)
        market = job_intelligence.market_outlook(job_snapshot.title or profile.role, job_snapshot.company, macro=macro)
        analysis = CareerJobAnalysis.objects.create(
            user=request.user,
            source_name=job_snapshot.source_name,
            job_url=job_snapshot.job_url,
            apply_url=job_snapshot.apply_url,
            company=job_snapshot.company,
            job_title=job_snapshot.title,
            location=job_snapshot.location,
            fit_score=fit["fit_score"],
            market_risk_score=market["risk_score"],
            strengths="\n".join(fit["strengths"]),
            gaps="\n".join(fit["gaps"]),
            summary=f"Fit score {fit['fit_score']}/100 for {job_snapshot.title or 'this role'} at {job_snapshot.company or job_snapshot.source_name}.",
            extracted_payload={
                "resume_payload": resume_payload,
                "job_snapshot": {
                    "title": job_snapshot.title,
                    "company": job_snapshot.company,
                    "location": job_snapshot.location,
                    "required_skills": job_snapshot.required_skills,
                    "experience_years": job_snapshot.experience_years,
                },
                "fit": fit,
            },
            evidence=market["evidence"],
        )
        openings = job_intelligence.suggest_openings(job_snapshot.title or profile.role, resume_payload.get("skills") or [])
        career_timing = _career_timing_payload(request.user, profile, market, analysis)
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
                },
                "fit": fit,
                "market": market,
                "career_timing": career_timing,
                "study_recommendations": study_recommendations,
                "openings": openings["openings"],
                "openings_evidence": openings["evidence"],
            }
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def career_projection(request):
    """Get career growth projection."""
    try:
        profile = _get_profile(request.user)
        macro = verified_intelligence.macro_context()
        projection = _career_projection_payload(request.user, profile, macro=macro)
        latest_analysis = CareerJobAnalysis.objects.filter(user=request.user).order_by("-created_at", "-id").first()
        role = profile.role if profile.role and profile.role != "Profile pending" else "analyst"
        market = job_intelligence.market_outlook(role, macro=macro)
        return Response(
            {
                **projection,
                "career_timing": _career_timing_payload(request.user, profile, market, latest_analysis),
            }
        )
    except Exception as e:
        return Response({"error": str(e)}, status=500)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def career_dashboard(request):
    profile = _get_profile(request.user)
    latest_resume = CareerResume.objects.filter(user=request.user).order_by("-created_at", "-id").first()
    latest_analysis = CareerJobAnalysis.objects.filter(user=request.user).order_by("-created_at", "-id").first()
    macro = verified_intelligence.macro_context()
    projection = _career_projection_payload(request.user, profile, macro=macro)
    role = profile.role if profile.role and profile.role != "Profile pending" else ((latest_resume.extracted_payload.get("role", "") if latest_resume else "") or "analyst")
    skills = latest_resume.extracted_payload.get("skills", []) if latest_resume else [item.strip() for item in (profile.skills or "").split(",") if item.strip()]
    market = job_intelligence.market_outlook(role, macro=macro)
    openings = job_intelligence.suggest_openings(role, skills)
    career_timing = _career_timing_payload(request.user, profile, market, latest_analysis)
    study_recommendations = _study_recommendations_payload(profile, latest_resume, latest_analysis, openings["openings"])
    data_pipeline = _career_data_pipeline_payload(profile, latest_resume, latest_analysis, projection, market, career_timing)

    return Response(
        {
            "profile": CareerProfileSerializer(profile).data,
            "projection": projection,
            "latest_resume": CareerResumeSerializer(latest_resume, context={"request": request}).data if latest_resume else None,
            "latest_job_analysis": CareerJobAnalysisSerializer(latest_analysis).data if latest_analysis else None,
            "market": market,
            "career_timing": career_timing,
            "study_recommendations": study_recommendations,
            "data_pipeline": data_pipeline,
            "openings": openings["openings"],
            "openings_evidence": openings["evidence"],
        }
    )
