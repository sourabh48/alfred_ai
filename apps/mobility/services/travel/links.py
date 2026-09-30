"""Search/official links only. Opening a link never means ALFRED checked inventory."""
from datetime import date
from urllib.parse import urlencode

from alfred_ai.services.public_http import normalized_link
from ..travel_discovery import value
from .providers.web import public_place


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
        params = {"ss":name, "group_adults":max(1,min(int(value(state,"number_of_travelers",1)),50)),"no_rooms":max(1,(int(value(state,"number_of_travelers",1))+1)//2)}
        start, end = value(state,"available_start_date"),value(state,"available_end_date")
        try:
            if start and end and date.fromisoformat(start) < date.fromisoformat(end):
                params.update(checkin=start,checkout=end)
        except (TypeError, ValueError):
            pass
        add("hotels","Check dates and stays on Booking.com","https://www.booking.com/searchresults.html?"+urlencode(params))
        add("flights","Search Google Flights","https://www.google.com/travel/flights?"+urlencode({"q":f"Flights from {origin} to {name} {start or ''} {end or ''}"}))
        if origin:
            add("routing","Check route on Google Maps","https://www.google.com/maps/dir/?"+urlencode({"api":1,"origin":origin,"destination":name,"travelmode":"driving"}))
        for topic, text in [("permits","official permit entry requirements"),("closures","official road closure traffic advisory"),("buses","bus operator timetable")]:
            add(topic,"Search "+text,"https://www.google.com/search?"+urlencode({"q":name+" "+text}))
    add("trains","Check trains on IRCTC","https://www.irctc.co.in/nget/train-search","official")
    add("trains","Official railway schedules and enquiries","https://enquiry.indianrail.gov.in/mntes/","official")
    add("buses","Karnataka KSRTC operator search","https://www.ksrtc.in/","official")
    add("permits","Destination reference",destination.get("source"),"reference")
    return links
