"""Private metadata handling. Never upload photos to a research provider."""
from datetime import datetime
from math import asin, cos, radians, sin, sqrt

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
                    photo.taken_at = timezone.make_aware(datetime.strptime(original, "%Y:%m:%d %H:%M:%S"))
                gps = exif.get_ifd(34853) if 34853 in exif else {}
                if photo.latitude is None and photo.longitude is None and gps.get(2) and gps.get(4):
                    def decimal(items):
                        return float(items[0])+float(items[1])/60+float(items[2])/3600
                    lat = decimal(gps[2]) * (-1 if gps.get(1) == "S" else 1)
                    lon = decimal(gps[4]) * (-1 if gps.get(3) == "W" else 1)
                    if -90 <= lat <= 90 and -180 <= lon <= 180:
                        photo.latitude, photo.longitude = lat, lon
        photo.save(update_fields=["taken_at", "latitude", "longitude"])
    except (OSError, ValueError, TypeError, KeyError, ZeroDivisionError, UnidentifiedImageError):
        # A missing/unreadable EXIF block does not lose the uploaded photo.
        pass
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
    a,b,c,e = map(radians, (photo.latitude, photo.longitude, d["lat"], d["lon"]))
    km = 6371*2*asin(sqrt(sin((a-c)/2)**2+cos(a)*cos(c)*sin((b-e)/2)**2))
    return km <= 40
