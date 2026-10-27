"""Bounded private export of saved planning notes; no provider calls or private attachments."""
from html import escape
from io import BytesIO

from django.utils import timezone
from rest_framework.exceptions import APIException, ValidationError

from .presentation import age_saved_facts


class PDFUnavailable(APIException):
    status_code = 503
    default_detail = "The itinerary PDF could not be generated. Your saved trip is unchanged."


def _text(value, fallback="Not recorded"):
    if value is None or value == "":
        value = fallback
    if not isinstance(value, str) or len(value) > 2400:
        raise ValidationError({"detail": "Saved itinerary text exceeds the current PDF limits or is malformed. The saved trip is unchanged."})
    return escape(value)


def itinerary_pdf(plan):
    raw = plan.itinerary
    if not isinstance(raw, dict) or not isinstance(raw.get("days"), list) or not 1 <= len(raw["days"]) <= 60:
        raise ValidationError({"detail": "Save an itinerary with 1–60 days before exporting its PDF."})
    try:
        itinerary = age_saved_facts({"itinerary": raw})["itinerary"]
        route = itinerary.get("route", {})
        sections = [f'<h1>{_text(plan.title)}</h1>',
            '<p class="notice">PRIVATE SAVED ITINERARY — planning notes, not proof of a booking, route access or current availability. Recheck conditions before travel. Downloaded copies remain your responsibility.</p>',
            f'<p>Saved status: {_text(plan.get_status_display())}<br>Destination: {_text(plan.destination)}<br>Dates: {plan.start_date.isoformat() if plan.start_date else "Not recorded"} to {plan.end_date.isoformat() if plan.end_date else "Not recorded"}<br>Travel mode: {_text(plan.get_transport_mode_display())}</p>',
            f'<p class="small">Saved snapshot: {plan.updated_at.isoformat()}<br>Exported: {timezone.now().isoformat()}</p>',
            '<p>Costs, private packing checklists, reminder records, linked documents and chat history are excluded.</p>',
            f'<h2>Route planning note</h2><p>{_text(route.get("summary"))}<br>Status: {_text(route.get("status"), "UNVERIFIED")} · confidence: {_text(route.get("confidence"), "UNKNOWN")}<br>{_text(route.get("note"), "No route verification is established by this export.")}</p>']
        for index, day in enumerate(itinerary["days"], 1):
            if not isinstance(day, dict) or not isinstance(day.get("items"), list) or len(day["items"]) > 30:
                raise ValueError()
            sections.append(f'<h2>Day {index}: {_text(day.get("title"))}</h2><p>{_text(day.get("date"), "Date not recorded")}</p><ul>')
            for item in day["items"]:
                if not isinstance(item, dict):
                    raise ValueError()
                sections.append(f'<li><strong>{_text(item.get("title"))}</strong><br>{_text(item.get("period"))} · {_text(item.get("duration"))}</li>')
            sections.append('</ul>')
        sections.append('<h2>Retained source evidence</h2><p>These are saved source snapshots. Their dates and unknowns are retained; this export performs no live checks.</p><ul>')
        groups = [("Trip", itinerary.get("sources", []))]
        stops = itinerary.get("stops", [])
        if not isinstance(stops, list) or len(stops) > 5:
            raise ValueError()
        for stop in stops:
            if not isinstance(stop, dict):
                raise ValueError()
            groups.append((stop.get("name"), stop.get("sources", [])))
        if any(not isinstance(sources, list) for _, sources in groups) or sum(len(sources) for _, sources in groups) > 100:
            raise ValueError()
        source_count = 0
        for location, sources in groups:
            for source in sources:
                if not isinstance(source, dict):
                    raise ValueError()
                if source.get("data_type") not in ("route", "weather", "place", "places", "restriction", "restrictions", "permits"):
                    continue
                source_count += 1
                sections.append(f'<li><strong>{_text(location)}</strong>: {_text(source.get("source_name"))} · {_text(source.get("data_type"))}<br>Status: {_text(source.get("status"), "UNVERIFIED")} · confidence: {_text(source.get("confidence"), "UNKNOWN")} · freshness: {_text(source.get("freshness"), "UNKNOWN")}<br>Checked: {_text(source.get("retrieved_at"))} · expires: {_text(source.get("valid_until") or source.get("expires_at"))}</li>')
        if not source_count:
            sections.append('<li>No route, weather, place or restriction source metadata was retained.</li>')
        sections.append('</ul>')
        content = ''.join(sections)
        if len(content) > 180000:
            raise ValidationError({"detail": "This saved itinerary exceeds the current PDF size limit. It is unchanged."})
    except (KeyError, TypeError, AttributeError, ValueError):
        raise ValidationError({"detail": "The saved itinerary is malformed. Its data is retained; no partial PDF was exported."}) from None
    try:
        import fitz
        paper = fitz.paper_rect('a4')
        body = fitz.Rect(42, 42, paper.width - 42, paper.height - 54)
        def rectangle(number, filled):
            if number >= 40:
                raise ValidationError({"detail": "The saved itinerary exceeds the40-page PDF limit. No partial PDF was exported."})
            return paper, body, None
        output = BytesIO()
        story = fitz.Story(content, user_css='body{font-family:sans-serif;font-size:11pt;color:#162a42;overflow-wrap:break-word}h1{font-size:22pt}h2{font-size:15pt;color:#164e76}p,li{margin-bottom:9pt}.notice{font-weight:bold;padding:6pt}.small{font-size:9pt}li{line-height:1.35;page-break-inside:avoid}')
        with fitz.DocumentWriter(output) as writer:
            story.write(writer, rectangle)
        with fitz.open(stream=output.getvalue(), filetype='pdf') as document:
            document.set_metadata(dict(title='ALFRED private saved itinerary',author='ALFRED',creator='ALFRED'))
            for number, page in enumerate(document, 1):
                page.insert_text((42, paper.height - 28), f'ALFRED | Private itinerary | {number} / {len(document)}', fontsize=8)
            result = document.tobytes(garbage=4, deflate=True)
        if len(result) > 8*1024*1024:
            raise ValidationError({"detail": "The saved itinerary exceeds the current PDF output limit."})
        return result
    except (ImportError, RuntimeError, ValueError):
        raise PDFUnavailable() from None
