from datetime import date, timedelta

from django.utils import timezone
from decimal import Decimal, ROUND_HALF_UP
from .money import decimal_amount


def bike_context(bike, *, end_date=None, distance_km=None):
    end = date.fromisoformat(end_date) if end_date else timezone.localdate()
    warnings = []
    service = bike.service_records.filter(user=bike.user).first()
    snapshot = bike.condition_snapshots.filter(user=bike.user).first()
    refill = bike.fuel_refill_logs.filter(user=bike.user, fuel_liters__gt=0, total_cost__gt=0).first()
    if service:
        due = service.next_service_date or (service.service_date+timedelta(days=bike.service_interval_days) if bike.service_interval_days else None)
        if due and due <= end:
            warnings.append(f"Recorded service due by {due}; review before this trip.")
        odometers = [n for n in [service.odometer_km, snapshot.odometer_km if snapshot else None, refill.odometer_km if refill else None] if n is not None]
        due_km = service.next_service_km or (service.odometer_km+bike.service_interval_km if bike.service_interval_km else None)
        if due_km and odometers and max(odometers)+(distance_km or 0) >= due_km:
            warnings.append("The planned distance reaches the recorded service mileage threshold.")
    else:
        warnings.append("No service record available for this vehicle.")
    for kind in ("insurance", "puc"):
        document = bike.documents.filter(user=bike.user, document_type=kind).order_by("-expiry_date", "-id").first()
        if not document or not document.expiry_date:
            warnings.append(f"{kind.upper()} expiry is not recorded; verify the document.")
        elif document.expiry_date <= end:
            warnings.append(f"{kind.upper()} expires {document.expiry_date}, before or during this trip.")
    issues = list(bike.issue_reports.filter(user=bike.user).exclude(status="resolved").values("title", "severity", "system")[:10])
    for issue in issues:
        warnings.append(f"Recorded {issue['severity']} {issue['system']} issue: {issue['title']}. Review before departure.")
    if snapshot:
        for part in ("overall", "engine", "brake", "tyre", "battery"):
            status = getattr(snapshot, part+"_status")
            if status != "good":
                warnings.append(f"Latest recorded {part} condition: {status} ({snapshot.captured_at.date()}).")
    return {"freshness": "USER_PROVIDED", "warnings": warnings, "known_issues": issues,
            "condition_recorded_at": snapshot.captured_at.isoformat() if snapshot else None,
            "fuel_price_per_litre": format((decimal_amount(refill.total_cost)/decimal_amount(refill.fuel_liters)).quantize(Decimal("0.01"),rounding=ROUND_HALF_UP),"f") if refill else None,
            "fuel_price_date": refill.refill_date.isoformat() if refill else None,
            "note": "Based on saved records, not a mechanical inspection or safety guarantee."}
