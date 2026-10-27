"""Saved planning dates and explicit export-only times; no calendar subscriptions."""
from datetime import date, datetime, timedelta, timezone as utc_timezone
import json
import re
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.utils import timezone
from django.utils.crypto import salted_hmac
from rest_framework.exceptions import ValidationError

from .presentation import age_saved_facts
from .reminders import schedule

LIMIT = 300
NOTICE = 'Private planning references, not bookings or confirmed departures. Date-only entries do not establish an activity duration. No invitations, alarms or synchronization. Costs, private notes, linked documents and account data are excluded.'


def _text(value, limit=2400):
    if not isinstance(value, str) or len(value) > limit or re.search(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f\ud800-\udfff]', value):
        raise ValidationError({'detail': 'Saved calendar text is malformed or exceeds export limits. Your trip is unchanged.'})
    return value.replace('\r\n', '\n').replace('\r', '\n').replace('\\', '\\\\').replace('\n', '\\n').replace(';', '\\;').replace(',', '\\,')


def _date(raw):
    if not isinstance(raw, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', raw):
        return None
    try:
        return date.fromisoformat(raw)
    except ValueError:
        return None


def _daystamp(value):
    return value.isoformat().replace('-', '')


def _stamp(value):
    return f'{value.year:04d}'+value.strftime('%m%dT%H%M%SZ')


def _confirmed(plan, key, expected):
    fact = plan.planning_state.get(key, {})
    return expected if (isinstance(fact, dict) and fact.get('confirmed_by_user') is True
        and fact.get('value') == (expected.isoformat() if expected else None)
        and fact.get('freshness') != 'ESTIMATED' and expected) else None


def calendar_choices(plan):
    try:
        days = plan.itinerary.get('days', [])
        if not isinstance(days, list) or len(days) > 60:
            raise ValueError()
        start = _confirmed(plan, 'available_start_date', plan.start_date)
        end = _confirmed(plan, 'available_end_date', plan.end_date)
        rows, warnings, identities = [], [], set()
        total = 0
        for index, day in enumerate(days):
            items = day.get('items', [])
            if not isinstance(items, list) or len(items) > 30:
                raise ValueError()
            total += len(items)
            if total > LIMIT:
                raise ValueError()
            when = _date(day.get('date'))
            valid_date = start and when and start <= when < date.max and (when-start).days == index and (when == start or end and when <= end)
            if not valid_date:
                warnings.append(f'Day {index+1}: {len(items)} activities omitted; its saved date is missing, unsupported or not owner-confirmed.')
                continue
            for position, item in enumerate(items):
                identity = item.get('id', f'legacy:{index}:{position}')
                if not isinstance(identity, str) or not 1 <= len(identity) <= 80 or identity in identities:
                    raise ValueError()
                identities.add(identity)
                key = salted_hmac('alfred-private-calendar', f'{plan.user_id}:{plan.pk}:{identity}', algorithm='sha256').hexdigest()
                title = item.get('title', '')
                _text(title)
                if not title.strip():
                    warnings.append(f'Day {index+1}: an unnamed activity was omitted.')
                    continue
                rows.append(dict(id=key, title=title, date=when.isoformat()))
        sources = _sources(plan.itinerary)
        _text(sources, 50000)
        location = plan.itinerary.get('destination') or plan.destination or 'Location not recorded'
        _text(location)
        content = json.dumps([plan.pk, plan.user_id, plan.title, location, rows, warnings, sources], sort_keys=True, ensure_ascii=False)
        snapshot = salted_hmac('alfred-calendar-snapshot', content, algorithm='sha256').hexdigest()
        return dict(snapshot=snapshot, location=location, activities=rows, warnings=warnings)
    except (KeyError, TypeError, AttributeError, ValueError, OverflowError):
        raise ValidationError({'detail': 'Saved calendar data is malformed or exceeds 60 days,30 items per day or300 activities. No partial calendar was exported.'}) from None


def _sources(itinerary):
    aged = age_saved_facts({'itinerary': itinerary})['itinerary']
    groups = [('Trip', aged.get('sources', []))]
    stops = aged.get('stops', [])
    if not isinstance(stops, list) or len(stops) > 5:
        raise ValueError()
    groups.extend((stop['name'], stop.get('sources', [])) for stop in stops)
    if any(not isinstance(s, list) for _, s in groups) or sum(len(s) for _, s in groups) > 100:
        raise ValueError()
    lines = []
    for location, sources in groups:
        for source in sources:
            if source.get('data_type') in ('route', 'weather', 'place', 'places', 'restrictions', 'restriction', 'permits'):
                lines.append(f"{location}: {source.get('source_name', 'Unknown source')}; confidence {source.get('confidence', 'UNKNOWN')}; freshness {source.get('freshness', 'UNKNOWN')}; checked {source.get('retrieved_at') or 'not recorded'}; expires {source.get('valid_until') or source.get('expires_at') or 'not recorded'}")
    return '\n'.join(lines) or 'No activity-confirming source metadata retained.'


def _fold(line):
    parts, chunk, size = [], '', 0
    for character in line:
        width = len(character.encode('utf-8'))
        if size+width > 75:
            parts.append(chunk)
            chunk, size = ' ', 1
        chunk += character
        size += width
    return '\r\n'.join([*parts, chunk])


def itinerary_ics(plan, options):
    try:
        choices = calendar_choices(plan)
        if not choices['activities']:
            raise ValidationError({'detail': 'No named activities have owner-confirmed saved dates. Confirm and save trip dates before calendar export; no dates or times were inferred.'})
        if not isinstance(options, dict) or set(options)-{'snapshot', 'zone', 'events'}:
            raise ValueError()
        overrides = options.get('events', [])
        zone = options.get('zone', '')
        if not isinstance(zone, str) or len(zone) > 64 or not isinstance(overrides, list) or len(overrides) > 20:
            raise ValueError()
        if zone:
            ZoneInfo(zone)
        by_id, seen = {row['id']: row for row in choices['activities']}, set()
        adjustments = {}
        for override in overrides:
            if not isinstance(override, dict) or set(override)-{'id', 'confirmed', 'start', 'end', 'start_fold', 'end_fold', 'through'}:
                raise ValueError()
            key = override.get('id')
            if not isinstance(key, str) or key not in by_id or key in seen or override.get('confirmed') is not True:
                raise ValueError()
            seen.add(key)
            day = date.fromisoformat(by_id[key]['date'])
            if 'through' in override:
                if set(override) != {'id', 'confirmed', 'through'}:
                    raise ValueError()
                last = _date(override['through'])
                if not last or not day <= last < date.max or (last-day).days > 60:
                    raise ValueError()
                adjustments[key] = ('DTSTART;VALUE=DATE:'+_daystamp(day), 'DTEND;VALUE=DATE:'+_daystamp(last+timedelta(days=1)), 'Owner-confirmed last included date; end is exclusive.')
            else:
                begin, first_fold = schedule(zone, override.get('start'), override.get('start_fold'))
                finish, last_fold = schedule(zone, override.get('end'), override.get('end_fold'))
                start_time, end_time = datetime.fromisoformat(begin), datetime.fromisoformat(finish)
                if override['start'][:10] != day.isoformat() or not start_time < end_time <= start_time+timedelta(days=60):
                    raise ValueError()
                context = f"Owner-confirmed export-only times: {override['start']} to {override['end']} in {zone}; start/end occurrence {first_fold+1}/{last_fold+1}."
                adjustments[key] = ('DTSTART:'+_stamp(start_time), 'DTEND:'+_stamp(end_time), context)
        warnings = choices['warnings']
        lines = ['BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//ALFRED//Private Travel//EN', 'CALSCALE:GREGORIAN',
            'X-WR-CALNAME:'+_text(plan.title), 'X-WR-CALDESC:'+_text(NOTICE+'\n'+'\n'.join(warnings)+'\nTrip source metadata, not activity confirmation:\n'+_sources(plan.itinerary), 50000)]
        stamp = _stamp(timezone.now().astimezone(utc_timezone.utc))
        for row in choices['activities']:
            day = date.fromisoformat(row['date'])
            begin, finish, context = adjustments.get(row['id'], ('DTSTART;VALUE=DATE:'+_daystamp(day), 'DTEND;VALUE=DATE:'+_daystamp(day+timedelta(days=1)), 'Date only; exact timing and duration are unverified.'))
            lines += ['BEGIN:VEVENT', f"UID:{row['id']}@alfred.local", 'DTSTAMP:'+stamp, begin, finish,
                'SUMMARY:'+_text(row['title']), 'LOCATION:'+_text(plan.itinerary.get('destination') or plan.destination or 'Location not recorded'),
                'DESCRIPTION:'+_text('Saved planning activity, not a booking or confirmed departure. '+context+' Trip source metadata is in the calendar description.'),
                'CLASS:PRIVATE', 'TRANSP:TRANSPARENT', 'END:VEVENT']
        lines.append('END:VCALENDAR')
        result = ('\r\n'.join(_fold(line) for line in lines)+'\r\n').encode('utf-8')
        if len(result) > 1024*1024:
            raise ValueError()
        return result, len(warnings)
    except (KeyError, TypeError, AttributeError, ValueError, OverflowError, ZoneInfoNotFoundError):
        raise ValidationError({'detail': 'Calendar options or saved evidence are invalid or exceed export limits. Select explicit valid dates/times; your trip is unchanged.'}) from None
