"""Private saved-coordinate export; never invent road geometry or recorded tracks."""
from decimal import Decimal, InvalidOperation
import re
from urllib.parse import urlsplit
from xml.etree.ElementTree import Element, SubElement, tostring

from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework.exceptions import ValidationError

from alfred_ai.services.public_http import normalized_link
from .presentation import age_saved_facts
from ..travel_discovery import value

NS = 'http://www.topografix.com/GPX/1/1'
LIMITATION = 'Private saved planning references, not recorded tracks or motorcycle-legal navigation. No roads, return legs or intermediate points are inferred. Recheck access and conditions.'


def _text(raw):
    if not isinstance(raw, str) or len(raw) > 2400 or re.search(r'[^\x09\x0a\x0d\x20-\ud7ff\ue000-\ufffd\U00010000-\U0010ffff]', raw):
        raise ValueError()
    return raw


def _coordinate(raw, *, latitude):
    if isinstance(raw, bool) or not isinstance(raw, (int, float, str, Decimal)) or len(str(raw)) > 64:
        raise ValueError()
    point = Decimal(str(raw))
    limit = 90 if latitude else 180
    if not point.is_finite() or not -limit <= point <= limit or (not latitude and point == 180) or abs(point.as_tuple().exponent) > 30:
        raise ValueError()
    return format(point, 'f') if point else '0'


def _coordinates(point):
    return dict(lat=_coordinate(point.get('lat'), latitude=True), lon=_coordinate(point.get('lon'), latitude=False))


def _link(raw):
    link = normalized_link(raw) if isinstance(raw, str) else ''
    return link if link and not urlsplit(link).query and not urlsplit(link).fragment else ''


def itinerary_gpx(plan):
    try:
        aged = age_saved_facts({'itinerary': plan.itinerary, 'state': plan.planning_state})
        itinerary, state = aged['itinerary'], aged['state']
        stops = itinerary.get('stops', [])
        snapshots = value(state, '_itinerary_stops', [])
        if not isinstance(stops, list) or len(stops) > 5 or not isinstance(snapshots, list) or len(snapshots) > 5:
            raise ValueError()
        if stops:
            names = [_text(s['name']) for s in stops]
            if len(set(names)) != len(names):
                raise ValueError()
            points = [next((s for s in snapshots if s.get('name') == name), {'name': name}) for name in names]
        elif snapshots:
            points = snapshots if len(snapshots) == 1 and snapshots[0].get('name') == itinerary.get('destination') else []
        else:
            selected = value(state, 'selected_location', {})
            points = [selected] if selected and selected.get('name') == itinerary.get('destination') else []
            if not points:
                features = itinerary.get('map', {}).get('features', [])
                if not isinstance(features, list) or len(features) > 100:
                    raise ValueError()
                points = [f['properties'] | dict(lon=f['geometry']['coordinates'][0], lat=f['geometry']['coordinates'][1])
                    for f in features
                    if f.get('geometry', {}).get('type') == 'Point' and f.get('properties', {}).get('kind') == 'overnight'
                    and f['properties'].get('name') == itinerary.get('destination')][:1]
        root = Element('gpx', dict(xmlns=NS, version='1.1', creator='ALFRED'))
        metadata = SubElement(root, 'metadata')
        SubElement(metadata, 'name').text = _text(plan.title)
        description = SubElement(metadata, 'desc')
        valid = []
        for point in points:
            try:
                coordinates = _coordinates(point)
            except (ValueError, InvalidOperation):
                continue
            node = SubElement(root, 'wpt', coordinates)
            SubElement(node, 'name').text = _text(point['name'])
            evidence = point.get('discovery_result') or point
            freshness = evidence.get('freshness') or point.get('source_freshness', 'UNKNOWN')
            checked = evidence.get('retrieved_at') or 'Not recorded'
            expiry = evidence.get('expires_at') or evidence.get('valid_until') or 'Not recorded'
            SubElement(node, 'desc').text = _text(f"Saved destination coordinate; location accuracy and road access unverified. Freshness: {freshness}; confidence: {evidence.get('confidence', 'UNKNOWN')}; checked: {checked}; expires: {expiry}.")
            SubElement(node, 'src').text = _text(evidence.get('provider') or 'ALFRED saved location')
            source = _link(point.get('source') or point.get('source_url'))
            if source:
                SubElement(SubElement(node, 'link', dict(href=source)), 'text').text = 'Saved location reference'
            valid.append(coordinates)
        if not valid:
            raise ValidationError({'detail': 'No valid saved destination or stop coordinates are available. Save a located destination before exporting GPX; no coordinates were inferred.'})
        # A multi-stop allowance is not verified geometry connecting its stops.
        route = None if stops or len(valid) != 1 else _route(itinerary, valid[0])
        if route:
            result, geometry = route
            node = SubElement(root, 'rte')
            SubElement(node, 'name').text = 'Saved provider route reference (one direction only)'
            SubElement(node, 'desc').text = _text(f"Provider geometry; not a recorded track or a verified motorcycle route. Checked {result['retrieved_at']}; expires {result['expires_at']}.")
            SubElement(node, 'src').text = _text(result['provider'])
            SubElement(SubElement(node, 'link', dict(href=_link(result['source_url']))), 'text').text = 'Saved routing source'
            for coordinates in geometry:
                SubElement(node, 'rtept', coordinates)
        description.text = LIMITATION + (' Current saved provider route points included.' if route else ' Waypoints only: no current verified route geometry is available; connecting these points is not road navigation.')
        if len(valid) != len(points):
            description.text += f' {len(points)-len(valid)} stops omitted because saved coordinates are missing or invalid.'
        output = tostring(root, encoding='utf-8', xml_declaration=True)
        if len(output) > 1024*1024:
            raise ValueError()
        return output
    except (KeyError, IndexError, TypeError, AttributeError, ValueError, InvalidOperation, OverflowError):
        raise ValidationError({'detail': 'Saved geographic data is malformed or exceeds GPX limits. Your trip is unchanged; no partial GPX was exported.'}) from None


def _route(itinerary, destination):
    """Only the selected, current source-backed provider line can supply route points."""
    try:
        result = itinerary.get('route_result', {})
        now = timezone.now()
        checked, expiry = (parse_datetime(str(result.get(k) or '')) for k in ('retrieved_at', 'expires_at'))
        if (result.get('success') is not True or result.get('status') != 'ok' or result.get('stale')
                or result.get('freshness') not in ('LIVE', 'RECENTLY_VERIFIED') or result.get('confidence') not in ('VERIFIED', 'LIKELY')
                or result.get('provider') != 'openrouteservice' or result.get('category') != 'routing'
                or not _link(result.get('source_url')) or not re.fullmatch('[0-9a-f]{64}', result.get('response_hash', ''))
                or not checked or not expiry or not timezone.is_aware(checked) or not timezone.is_aware(expiry) or not checked <= now < expiry
                or itinerary.get('route', {}).get('confidence') in ('UNKNOWN', 'ESTIMATED')):
            return None
        routes = result.get('payload', {}).get('routes', [])
        if not isinstance(routes, list) or len(routes) > 3:
            return None
        selected = itinerary.get('route', {}).get('selected_route_id')
        matches = [r for r in routes if selected and r.get('route_id') == selected]
        if len(matches) != 1:
            return None
        route = matches[0]
        geometry = route.get('geometry', {})
        coords = geometry.get('coordinates')
        if route.get('profile') not in ('driving-car', 'foot-walking') or geometry.get('type') != 'LineString' or not isinstance(coords, list) or not 2 <= len(coords) <= 5000:
            return None
        if any(not isinstance(p, (list, tuple)) or len(p) != 2 for p in coords):
            return None
        end = result.get('request_parameters', {}).get('end', [])
        if not isinstance(end, (list, tuple)) or len(end) != 2:
            return None
        endpoint = _coordinates(dict(lon=end[0], lat=end[1]))
        if any(Decimal(endpoint[key]) != Decimal(destination[key]) for key in ('lat', 'lon')):
            return None
        return result, [_coordinates(dict(lon=p[0], lat=p[1])) for p in coords]
    except (KeyError, IndexError, TypeError, AttributeError, ValueError, InvalidOperation, OverflowError):
        return None
