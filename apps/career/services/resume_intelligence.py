from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO, StringIO
import html
from html.parser import HTMLParser
import logging
import os
import re
from typing import BinaryIO
from xml.etree import ElementTree
import zipfile

from alfred_ai.services import extract_document_text
from pypdf import PdfReader

try:
    import pdfplumber
except Exception:  # pragma: no cover - optional runtime dependency
    pdfplumber = None

SKILL_CATALOG = {
    "python", "sql", "excel", "power bi", "tableau", "django", "flask", "fastapi", "java", "javascript",
    "typescript", "react", "node", "aws", "azure", "gcp", "docker", "kubernetes", "git", "linux",
    "machine learning", "data analysis", "statistics", "forecasting", "pandas", "numpy", "scikit-learn",
    "nlp", "llm", "prompt engineering", "product management", "strategy", "finance", "risk", "operations",
    "analytics", "etl", "airflow", "spark", "hadoop", "salesforce", "seo", "content", "marketing",
    "project management", "agile", "scrum", "leadership", "communication", "stakeholder management",
    "spring", "spring boot", "spring cloud", "microservices", "rest api", "soap", "hibernate", "jpa",
    "mongodb", "oracle", "mysql", "postgresql", "kafka", "jenkins", "jira", "maven", "gradle",
    "postman", "junit", "mockito", "tomcat", "servicenow", "api gateway", "redis", "jenkins pipeline",
    "ci/cd", "ci cd", "unit testing", "integration testing", "backend development",
}

ROLE_HINTS = [
    "software engineer", "data analyst", "data scientist", "machine learning engineer", "product manager",
    "business analyst", "financial analyst", "operations analyst", "backend developer", "frontend developer",
    "full stack developer", "consultant", "project manager", "marketing manager", "sales manager",
    "java backend developer", "java developer", "backend engineer", "software developer",
]

ACHIEVEMENT_HINTS = ("improved", "reduced", "built", "launched", "led", "grew", "optimized", "delivered", "increased")
EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
PHONE_RE = re.compile(r"(?:\+91[\s-]?)?[6-9]\d{9}")
LINK_RE = re.compile(
    r"(?:(?:https?://)|(?:www\.))[^\s]+|(?:linkedin\.com/[^\s]+)|(?:github\.com/[^\s]+)",
    re.IGNORECASE,
)
YEARS_RE = re.compile(r"(\d+(?:\.\d+)?)\+?\s+(?:years?|yrs?)", re.IGNORECASE)
COMPANY_FIELD_RE = re.compile(
    r"\b(?:company|current company|employer|organization)\s*[:\-]\s*([A-Z][A-Z0-9&.,'() /-]{2,90})",
    re.IGNORECASE,
)


class _HTMLTextStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data):
        if data and data.strip():
            self.parts.append(data.strip())

    def text(self) -> str:
        return "\n".join(self.parts)


IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".tif"}
TEXTISH_EXTENSIONS = {".txt", ".md", ".csv", ".log"}
RICH_TEXT_EXTENSIONS = {".rtf", ".html", ".htm", ".xml"}
ARCHIVE_TEXT_EXTENSIONS = {".docx", ".odt"}
RESUME_FILE_EXTENSIONS = {".pdf", ".doc", ".docx", ".txt", ".md", ".rtf", ".html", ".htm", ".odt", *IMAGE_EXTENSIONS}

logger = logging.getLogger(__name__)


@dataclass
class ParsedResume:
    parser_status: str
    confidence: float
    extracted_text: str
    payload: dict
    summary: str
    strengths: list[str]
    weaknesses: list[str]


class ResumeIntelligenceService:
    def parse(self, upload: BinaryIO, filename: str = "", user=None) -> ParsedResume:
        raw_bytes = self._read_bytes(upload)
        effective_name = filename or getattr(upload, "name", "resume")
        extraction = extract_document_text(raw_bytes, effective_name)
        text = extraction.text or self._extract_text(raw_bytes, effective_name)
        normalized = " ".join(text.split())
        skills = self._extract_skills(normalized)
        links = self._extract_links(text)
        experience = self._extract_experience(normalized)
        role = self._extract_role(text)
        current_company = self._extract_current_company(text)
        email = EMAIL_RE.search(text)
        phone = PHONE_RE.search(text)
        achievements = self._achievement_density(text)

        strengths = []
        weaknesses = []
        if skills:
            strengths.append(f"Detected {len(skills)} role-relevant skills.")
        if experience >= 3:
            strengths.append(f"Resume indicates roughly {experience:.1f} years of experience.")
        if links:
            strengths.append("Resume includes portfolio or profile links.")
        if achievements >= 3:
            strengths.append("Resume has several quantified or action-oriented achievement signals.")

        if len(skills) < 5:
            weaknesses.append("Skill coverage looks narrow. Add more concrete tools, platforms, and domain keywords.")
        if achievements < 2:
            weaknesses.append("Resume is light on quantified achievements. Add outcomes with numbers where possible.")
        if not links:
            weaknesses.append("No portfolio, LinkedIn, or project link was detected.")
        if not email or not phone:
            weaknesses.append("Contact information looks incomplete or hard to detect.")
        if not text.strip():
            weaknesses.insert(0, "Resume text could not be extracted cleanly. This usually means the CV is scanned, image-based, or in an unusual export format.")
            weaknesses.insert(1, "ALFRED could not recover stable readable text from this file on this pass. A cleaner export or a manual correction may still be needed.")
        elif extraction.method:
            strengths.append(f"Primary extraction path: {extraction.method.replace('_', ' ')}.")
            if "ocr" in extraction.method:
                strengths.append("Scanned-resume OCR recovered readable text for profile extraction.")

        confidence = 0.18 if not text.strip() else max(0.45, extraction.confidence * 0.75)
        if len(normalized) >= 1200:
            confidence += 0.2
        if skills:
            confidence += 0.15
        if role:
            confidence += 0.1
        if email:
            confidence += 0.05
        if experience:
            confidence += 0.05
        confidence = self._apply_learning(user, effective_name, role, skills, confidence, bool(text.strip()))
        confidence = round(min(confidence, 0.97), 2)
        parser_status = "parsed" if text.strip() and confidence >= 0.65 else ("needs_review" if text.strip() or self._looks_like_resume_file(effective_name) else "failed")

        payload = {
            "role": role,
            "current_company": current_company,
            "skills": skills,
            "experience_years": experience,
            "email": email.group(0) if email else "",
            "phone": phone.group(0) if phone else "",
            "links": links[:8],
            "achievement_signal_count": achievements,
            "extraction_method": extraction.method,
            "extraction_notes": extraction.notes[:4],
            "raw_text_excerpt": " ".join(text.split())[:600],
            "extraction_review": extraction.review_payload,
        }
        summary = self._build_summary(role, experience, skills, strengths, weaknesses)

        return ParsedResume(
            parser_status=parser_status,
            confidence=confidence,
            extracted_text=text[:15000],
            payload=payload,
            summary=summary,
            strengths=strengths[:5],
            weaknesses=weaknesses[:5],
        )

    def apply_to_profile(self, profile, parsed: ParsedResume):
        updated_fields = []
        if parsed.payload.get("role") and (not profile.role or profile.role == "Profile pending"):
            profile.role = parsed.payload["role"][:100]
            updated_fields.append("role")
        if parsed.payload.get("experience_years") and not profile.experience_years:
            profile.experience_years = parsed.payload["experience_years"]
            updated_fields.append("experience_years")
        skills = parsed.payload.get("skills") or []
        if skills:
            merged = self._merge_skills(profile.skills, skills)
            if merged != profile.skills:
                profile.skills = merged
                updated_fields.append("skills")
        if updated_fields:
            profile.save(update_fields=updated_fields)
        return profile

    def record_parse_outcome(self, user, filename: str, parsed: ParsedResume):
        if user is None:
            return None
        from apps.career.models import CareerResumeLearningMemory

        extension, role_hint, skill_signature = self._learning_signature(filename, parsed.payload.get("role", ""), parsed.payload.get("skills") or [])
        memory, _ = CareerResumeLearningMemory.objects.get_or_create(
            user=user,
            file_extension=extension,
            role_hint=role_hint,
            skill_signature=skill_signature,
        )
        if parsed.parser_status == "parsed":
            memory.successful_count += 1
        elif parsed.parser_status == "needs_review":
            memory.review_count += 1
        else:
            memory.failed_count += 1
        total = memory.successful_count + memory.review_count + memory.failed_count
        previous_weight = max(total - 1, 0)
        memory.average_confidence = round(
            ((memory.average_confidence * previous_weight) + float(parsed.confidence or 0)) / max(total, 1),
            4,
        )
        memory.save()
        return memory

    def _read_bytes(self, upload: BinaryIO) -> bytes:
        current = upload.tell() if hasattr(upload, "tell") else None
        if hasattr(upload, "seek"):
            upload.seek(0)
        content = upload.read()
        if current is not None and hasattr(upload, "seek"):
            upload.seek(current)
        return content

    def _extract_text(self, raw_bytes: bytes, filename: str) -> str:
        extension = os.path.splitext(filename.lower())[1]
        if extension == ".pdf":
            return self._extract_pdf_text(raw_bytes)
        if extension == ".docx":
            return self._extract_docx_text(raw_bytes)
        if extension == ".odt":
            return self._extract_odt_text(raw_bytes)
        if extension in TEXTISH_EXTENSIONS:
            return self._decode_text(raw_bytes)
        if extension == ".rtf":
            return self._extract_rtf_text(raw_bytes)
        if extension in {".html", ".htm"}:
            return self._extract_html_text(raw_bytes)
        if extension in IMAGE_EXTENSIONS:
            return self._extract_image_text(raw_bytes)
        return self._decode_text_fallback(raw_bytes)

    def _extract_pdf_text(self, raw_bytes: bytes) -> str:
        texts = []
        try:
            reader = PdfReader(BytesIO(raw_bytes))
            texts.append("\n".join((page.extract_text() or "") for page in reader.pages))
            texts.append("\n".join((page.extract_text(extraction_mode="layout") or "") for page in reader.pages))
        except Exception:
            logger.warning("Resume PDF extraction via pypdf failed.", exc_info=True)

        for candidate in texts:
            if candidate and candidate.strip():
                return candidate

        if pdfplumber:
            try:
                with pdfplumber.open(BytesIO(raw_bytes)) as pdf:
                    plumber_text = "\n".join((page.extract_text() or "") for page in pdf.pages)
                    if plumber_text.strip():
                        return plumber_text
            except Exception:
                logger.warning("Resume PDF extraction via pdfplumber failed.", exc_info=True)
        return ""

    def _extract_docx_text(self, raw_bytes: bytes) -> str:
        try:
            with zipfile.ZipFile(BytesIO(raw_bytes)) as archive:
                document = archive.read("word/document.xml")
        except Exception:
            return ""
        try:
            root = ElementTree.fromstring(document)
        except ElementTree.ParseError:
            return ""
        text_parts = []
        for node in root.iter():
            if node.tag.endswith("}t") and node.text:
                text_parts.append(node.text)
        return html.unescape("\n".join(text_parts))

    def _extract_odt_text(self, raw_bytes: bytes) -> str:
        try:
            with zipfile.ZipFile(BytesIO(raw_bytes)) as archive:
                document = archive.read("content.xml")
        except Exception:
            return ""
        try:
            root = ElementTree.fromstring(document)
        except ElementTree.ParseError:
            return ""
        text_parts = []
        for node in root.iter():
            if node.text and node.text.strip():
                text_parts.append(node.text.strip())
        return html.unescape("\n".join(text_parts))

    def _extract_rtf_text(self, raw_bytes: bytes) -> str:
        text = self._decode_text(raw_bytes)
        if not text:
            return ""
        text = re.sub(r"\\'[0-9a-fA-F]{2}", " ", text)
        text = re.sub(r"\\par[d]?", "\n", text)
        text = re.sub(r"\\[a-zA-Z]+-?\d* ?", " ", text)
        text = text.replace("{", " ").replace("}", " ")
        return " ".join(html.unescape(text).split())

    def _extract_html_text(self, raw_bytes: bytes) -> str:
        text = self._decode_text(raw_bytes)
        if not text:
            return ""
        text = re.sub(r"(?is)<(script|style).*?>.*?</\\1>", " ", text)
        parser = _HTMLTextStripper()
        try:
            parser.feed(text)
            return html.unescape(parser.text())
        except Exception:
            logger.warning("Resume HTML extraction fell back to tag stripping after parser failure.", exc_info=True)
            stripped = re.sub(r"<[^>]+>", " ", text)
            return " ".join(html.unescape(stripped).split())

    def _extract_image_text(self, raw_bytes: bytes) -> str:
        return ""

    def _decode_text(self, raw_bytes: bytes) -> str:
        for encoding in ("utf-8", "utf-16", "latin-1"):
            try:
                return raw_bytes.decode(encoding)
            except UnicodeDecodeError:
                continue
        return raw_bytes.decode("latin-1", errors="ignore")

    def _decode_text_fallback(self, raw_bytes: bytes) -> str:
        text = self._decode_text(raw_bytes)
        if not text:
            return ""
        printable = sum(1 for char in text if char.isprintable() or char.isspace())
        ratio = printable / max(len(text), 1)
        return text if ratio >= 0.82 else ""

    def _looks_like_resume_file(self, filename: str) -> bool:
        return os.path.splitext((filename or "").lower())[1] in RESUME_FILE_EXTENSIONS

    def _learning_signature(self, filename: str, role: str, skills: list[str]) -> tuple[str, str, str]:
        extension = os.path.splitext((filename or "").lower())[1] or "unknown"
        role_hint = re.sub(r"[^a-z0-9+ ]", "", (role or "").strip().lower())[:100]
        normalized_skills = sorted({re.sub(r"[^a-z0-9+ ]", "", item.strip().lower()) for item in (skills or []) if item and item.strip()})
        skill_signature = "|".join(normalized_skills[:6])[:240]
        return extension, role_hint, skill_signature

    def _apply_learning(self, user, filename: str, role: str, skills: list[str], confidence: float, has_text: bool) -> float:
        if user is None:
            return confidence
        from apps.career.models import CareerResumeLearningMemory

        extension, role_hint, skill_signature = self._learning_signature(filename, role, skills)
        exact_memory = (
            CareerResumeLearningMemory.objects.filter(
                user=user,
                file_extension=extension,
                role_hint=role_hint,
                skill_signature=skill_signature,
            )
            .order_by("-last_seen_at", "-id")
            .first()
        )
        extension_memories = list(CareerResumeLearningMemory.objects.filter(user=user, file_extension=extension))
        adjusted = confidence

        if exact_memory and exact_memory.successful_count >= 2 and exact_memory.average_confidence >= 0.68 and has_text:
            adjusted += min(0.08, 0.02 + (exact_memory.successful_count * 0.01))
        elif exact_memory and exact_memory.failed_count >= 2 and not has_text:
            adjusted = min(adjusted, 0.2)

        if extension_memories:
            total_success = sum(item.successful_count for item in extension_memories)
            total_review = sum(item.review_count for item in extension_memories)
            total_failed = sum(item.failed_count for item in extension_memories)
            observed = total_success + total_review + total_failed
            if observed >= 3 and has_text:
                success_ratio = total_success / max(observed, 1)
                adjusted += min(0.05, success_ratio * 0.05)
            elif observed >= 3 and not has_text and total_failed >= total_success:
                adjusted = min(adjusted, 0.22)

        return adjusted

    def _extract_skills(self, text: str) -> list[str]:
        lowered = text.lower()
        found = []
        for skill in sorted(SKILL_CATALOG):
            if skill in lowered:
                found.append(skill.title())
        return found[:20]

    def _extract_role(self, text: str) -> str:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        for line in lines[:8]:
            if EMAIL_RE.search(line) or PHONE_RE.search(line):
                continue
            cleaned = re.sub(r"[^A-Za-z/&+ -]", "", line).strip()
            lowered = cleaned.lower()
            if 2 <= len(cleaned.split()) <= 7 and any(
                token in lowered
                for token in ("developer", "engineer", "analyst", "manager", "architect", "consultant", "specialist")
            ):
                return cleaned[:100]
        first_block = " ".join(lines[:10]).lower()
        for role in ROLE_HINTS:
            if role in first_block:
                return role.title()
        for line in lines[:8]:
            if 3 <= len(line.split()) <= 7 and not EMAIL_RE.search(line) and not PHONE_RE.search(line):
                cleaned = re.sub(r"[^A-Za-z/& -]", "", line).strip()
                if cleaned and cleaned.lower() not in {"resume", "curriculum vitae"}:
                    return cleaned[:100]
        return ""

    def _extract_experience(self, text: str) -> float:
        matches = [float(match.group(1)) for match in YEARS_RE.finditer(text)]
        return max(matches) if matches else 0.0

    def _extract_current_company(self, text: str) -> str:
        direct_match = COMPANY_FIELD_RE.search(text)
        if direct_match:
            return re.sub(r"\s+", " ", direct_match.group(1)).strip()[:120]

        lines = [line.strip() for line in text.splitlines() if line.strip()]
        for line in lines[:18]:
            if "|" not in line:
                continue
            parts = [part.strip() for part in line.split("|") if part.strip()]
            if len(parts) < 2:
                continue
            for part in parts:
                lowered = part.lower()
                if any(token in lowered for token in ("developer", "engineer", "analyst", "manager", "architect", "consultant")):
                    continue
                cleaned = re.sub(r"[^A-Za-z0-9&.,'() /-]", "", part).strip()
                if 2 <= len(cleaned.split()) <= 6:
                    return cleaned[:120]

        return ""

    def _extract_links(self, text: str) -> list[str]:
        found = []
        seen = set()
        for match in LINK_RE.findall(text):
            candidate = str(match or "").strip().rstrip(".,);]")
            if not candidate:
                continue
            lowered = candidate.lower()
            if lowered.startswith("www."):
                candidate = f"https://{candidate}"
            elif "://" not in lowered and (lowered.startswith("linkedin.com/") or lowered.startswith("github.com/")):
                candidate = f"https://{candidate}"
            key = candidate.lower()
            if key in seen:
                continue
            seen.add(key)
            found.append(candidate)
        return found[:8]

    def _achievement_density(self, text: str) -> int:
        score = 0
        lowered = text.lower()
        score += sum(lowered.count(token) for token in ACHIEVEMENT_HINTS)
        score += len(re.findall(r"\b\d+(?:\.\d+)?%|\b\d+\s*(?:crore|lakhs?|million|billion|users?|clients?)", lowered))
        return min(score, 12)

    def _build_summary(self, role: str, experience: float, skills: list[str], strengths: list[str], weaknesses: list[str]) -> str:
        role_text = role or "Role is not confidently identified yet"
        experience_text = f" about {experience:.1f} years of experience" if experience else " limited explicit experience labeling"
        skills_text = f" and {len(skills)} detected skills" if skills else " and sparse skill signals"
        summary = f"Resume suggests {role_text}{experience_text}{skills_text}."
        if strengths:
            summary += f" Strongest signals: {strengths[0]}"
        if weaknesses:
            summary += f" Main weakness: {weaknesses[0]}"
        return summary[:500]

    def _merge_skills(self, existing: str, skills: list[str]) -> str:
        merged = []
        seen = set()
        for item in [*(segment.strip() for segment in (existing or "").split(",") if segment.strip()), *skills]:
            key = item.lower()
            if key in seen:
                continue
            seen.add(key)
            merged.append(item)
        return ", ".join(merged[:30])


resume_intelligence = ResumeIntelligenceService()
