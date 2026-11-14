"""Search/official links only. Opening a link never means ALFRED checked inventory."""
import re
from datetime import date
from urllib.parse import urlencode, urlsplit

from alfred_ai.services.public_http import normalized_link
from ..travel_discovery import value
from .providers.web import public_place

# Reviewed allow-list of home pages, so opening one sends nothing from the trip.
# docs/TRAVEL_PROVIDERS.md records the evidence per site and what was left out.
BOOKING_SITES_REVIEWED_ON = "2026-11-02"
BOOKING_SITES = (
    ("hotels", "Booking.com", "https://www.booking.com/"),
    ("hotels", "KTDC hotels and resorts (Kerala)", "https://www.ktdc.com/"),
    ("hotels", "KSTDC Mayura hotels (Karnataka)", "https://kstdc.co/"),
    ("flights", "Akasa Air", "https://www.akasaair.com/"),
    ("flights", "Air India Express", "https://www.airindiaexpress.com/"),
    ("flights", "SpiceJet", "https://www.spicejet.com/"),
    ("buses", "Karnataka KSRTC", "https://www.ksrtc.in/"),
    ("buses", "Kerala KSRTC", "https://www.keralartc.com/"),
    ("buses", "Tamil Nadu TNSTC", "https://www.tnstc.in/"),
    ("buses", "Telangana TGSRTC", "https://www.tgsrtcbus.in/"),
)


def booking_sites():
    return [{"category":category,"label":label,"url":url,"reviewed_on":BOOKING_SITES_REVIEWED_ON}
            for category, label, url in BOOKING_SITES
            if normalized_link(url) == url and not urlsplit(url).query and not urlsplit(url).fragment]


def stay_details(state):
    """Booking.com search fields: people, rooms and, when valid, the trip's dates."""
    people = max(1,min(int(value(state,"number_of_travelers",1)),50))
    details = {"group_adults":people,"no_rooms":(people+1)//2}
    start, end = value(state,"available_start_date"),value(state,"available_end_date")
    try:
        if start and end and date.fromisoformat(start) < date.fromisoformat(end):
            details.update(checkin=start,checkout=end)
    except (TypeError, ValueError):
        pass
    return details


def hotel_price_links(state, hotel, place):
    """Price pages for one hotel from Google. Google Hotels keeps no dates from a link (its date code is not public),
    so dates are set there; the Booking.com page carries the trip's people, rooms and dates."""
    query = f"{hotel} {place}".strip()[:150]
    return {"google_hotels_url":"https://www.google.com/travel/search?"+urlencode({"q":query}),
            "dated_booking_url":"https://www.booking.com/searchresults.html?"+urlencode({"ss":query,**stay_details(state)})}


def skyscanner_link(state):
    """Skyscanner searches by airport code, so the link exists only once both airports are known."""
    origin, destination = (str(value(state,key) or "").upper() for key in ("origin_airport","destination_airport"))
    if not re.fullmatch(r"[A-Z]{3}",origin) or not re.fullmatch(r"[A-Z]{3}",destination) or origin == destination:
        return None
    try:
        days = [date.fromisoformat(value(state,key)) for key in ("available_start_date","available_end_date") if value(state,key)]
    except (TypeError, ValueError):
        days = []
    if len(days) == 2 and days[1] < days[0]:
        days = days[:1]
    people = max(1,min(int(value(state,"number_of_travelers",1)),8))  # Skyscanner's search takes at most 8 adults
    path = "/".join([origin.lower(),destination.lower(),*(d.strftime("%y%m%d") for d in days)])
    label = "Search Skyscanner with your " + ("airports, traveller count and dates" if days else "airports and traveller count")
    return label, f"https://www.skyscanner.co.in/transport/flights/{path}/?"+urlencode({"adultsv2":people})


def external_links(state, destination):
    name = public_place(destination.get("name"))
    origin = public_place(value(state,"origin"))
    links = []
    def add(category, label, url, kind="search"):
        url = normalized_link(url)
        if url:
            links.append({"category":category,"label":label,"url":url,"kind":kind,
                "freshness":"UNKNOWN","verified_at":None,"availability":"UNKNOWN",
                "note":"Open this link to check current details and availability. ALFRED does not book or pay."})
    if name:
        add("map","Open destination on Google Maps","https://www.google.com/maps/search/?"+urlencode({"api":1,"query":name}))
        add("hotels","Search stays on Google Maps","https://www.google.com/maps/search/?"+urlencode({"api":1,"query":"hotels in "+name}))
        params = {"ss":name, **stay_details(state)}
        start, end = value(state,"available_start_date"),value(state,"available_end_date")
        details = "traveller and room counts" + (" and dates" if "checkin" in params else "")
        # A search link's label names the trip details it sends; clicking it is the owner's choice.
        add("hotels",f"Search Booking.com with your {details}","https://www.booking.com/searchresults.html?"+urlencode(params))
        sent = [text for text, present in (("start city",origin),("dates",start or end)) if present]
        add("flights","Search Google Flights"+(" with your "+" and ".join(sent) if sent else ""),"https://www.google.com/travel/flights?"+urlencode({"q":f"Flights {'from '+origin+' ' if origin else ''}to {name} {start or ''} {end or ''}".strip()}))
        if skyscanner := skyscanner_link(state):
            add("flights",*skyscanner)
        if origin:
            add("routing","Check route on Google Maps from your start city","https://www.google.com/maps/dir/?"+urlencode({"api":1,"origin":origin,"destination":name,"travelmode":"driving"}))
        for topic, text in [("permits","official permit entry requirements"),("closures","official road closure traffic advisory"),("buses","bus operator timetable")]:
            add(topic,"Search "+text,"https://www.google.com/search?"+urlencode({"q":name+" "+text}))
    add("trains","Check trains on IRCTC","https://www.irctc.co.in/nget/train-search","official")
    add("trains","Official railway schedules and enquiries","https://enquiry.indianrail.gov.in/mntes/","official")
    add("permits","Destination reference",destination.get("source"),"reference")
    return links
