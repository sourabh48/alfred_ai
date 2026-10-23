"""Private metadata handling. Never upload photos to a research provider."""
from datetime import datetime
from math import asin, cos, isfinite, radians, sin, sqrt

from django.utils import timezone

from .travel_catalog import lookup
from .travel_discovery import learn, profile_for


def enrich_photo(photo):
    """Read EXIF if present. User-supplied metadata always wins."""
    from PIL import Image, UnidentifiedImageError
    try:
        with photo.image.open("rb") as file:
            with Image.open(file) as image:
                exif = image.getexif()
                original = exif.get(306)
                try:
                    original = exif.get_ifd(34665).get(36867) or original
                except (KeyError, TypeError):
                    pass
                if original and not photo.taken_at:
                    try:
                        # A damaged timestamp must not discard independent GPS evidence.
                        photo.taken_at = timezone.make_aware(datetime.strptime(original, "%Y:%m:%d %H:%M:%S"))
                    except (ValueError, TypeError, OverflowError):
                        pass
                gps = exif.get_ifd(34853) if 34853 in exif else {}
                if (photo.latitude is None and photo.longitude is None and gps.get(2) and gps.get(4)
                        and gps.get(1) in {"N", "S"} and gps.get(3) in {"E", "W"}):
                    def decimal(items):
                        degrees, minutes, seconds = map(float, items)
                        if not all(map(isfinite, (degrees, minutes, seconds))) or degrees < 0 or not 0 <= minutes < 60 or not 0 <= seconds < 60:
                            raise ValueError("Invalid EXIF coordinate")
                        return degrees + minutes/60 + seconds/3600
                    lat = decimal(gps[2]) * (-1 if gps.get(1) == "S" else 1)
                    lon = decimal(gps[4]) * (-1 if gps.get(3) == "W" else 1)
                    if isfinite(lat) and isfinite(lon) and -90 <= lat <= 90 and -180 <= lon <= 180:
                        photo.latitude, photo.longitude = lat, lon
    except (OSError, ValueError, TypeError, KeyError, IndexError, OverflowError, ZeroDivisionError, UnidentifiedImageError):
        # A missing/unreadable EXIF block does not lose the uploaded photo.
        pass
    photo.save(update_fields=["taken_at", "latitude", "longitude"])
    learn_from_favorite(photo)


def learn_from_favorite(photo):
    p = profile_for(photo.user)
    if p.learning_enabled and p.media_learning_enabled and photo.is_favorite:
        for tag in photo.preference_tags:
            learn(photo.user, tag, True, f"Tagged favourite photo #{photo.id}", .45)


def near_destination(photo, destination):
    d = lookup(destination)
    if not d or photo.latitude is None or photo.longitude is None:
        return False
    if not (isfinite(photo.latitude) and isfinite(photo.longitude) and -90 <= photo.latitude <= 90 and -180 <= photo.longitude <= 180):
        return False
    a,b,c,e = map(radians, (photo.latitude, photo.longitude, d["lat"], d["lon"]))
    km = 6371*2*asin(min(1, sqrt(sin((a-c)/2)**2+cos(a)*cos(c)*sin((b-e)/2)**2)))
    return km <= 40
