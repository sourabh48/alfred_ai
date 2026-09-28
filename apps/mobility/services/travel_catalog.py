"""Offline discovery seeds, not live availability, routing or permit claims.

Coordinates identify towns, never a user's home. Costs and road distances are
planning estimates; authoritative links are references, not scraped evidence.
"""
from math import asin, cos, radians, sin, sqrt


DESTINATIONS = [
    dict(name="Nandi Hills", lat=13.371, lon=77.684, styles=["mountains", "photography", "short rides", "scenic roads"],
         activities=["Hill-area viewpoint, subject to access", "Village food stop", "Countryside photography"], stay="A registered stay near Nandi village, if staying overnight", nightly=1500, maximum_days=2,
         source="https://chikkaballapur.nic.in/en/tourism/", authority="Chikkaballapur district", caution="Check current hill-entry hours, booking and vehicle-access rules; do not assume sunrise entry is available."),
    dict(name="Chikmagalur", lat=13.316, lon=75.773, styles=["mountains", "photography", "scenic roads", "cool weather", "quiet locations"],
         activities=["Coffee estate visit", "Mullayanagiri viewpoint", "Town food walk"], stay="Chikmagalur town or a registered coffee-estate homestay", nightly=1400,
         source="https://chikkamagaluru.nic.in/en/tourism/", authority="Chikkamagaluru district", caution="Check hill access and local permit notices; viewpoints depend on visibility."),
    dict(name="Sakleshpur", lat=12.944, lon=75.788, styles=["forests", "photography", "quiet locations", "scenic roads", "camping"],
         activities=["Manjarabad Fort", "Coffee-estate walk", "Countryside photography"], stay="Sakleshpur town or a registered estate homestay", nightly=1200,
         source="https://hassan.nic.in/en/tourism/", authority="Hassan district", caution="Use authorised campsites; forest access and trekking permissions need confirmation."),
    dict(name="Wayanad", lat=11.685, lon=76.132, styles=["mountains", "forests", "wildlife", "photography", "trekking", "cool weather"],
         activities=["Edakkal area visit", "Pookode Lake", "Local food and craft walk"], stay="Kalpetta or Sulthan Bathery", nightly=1600,
         source="https://wayanad.gov.in/en/tourism/", authority="Wayanad district", caution="Forest routes, trekking access and attraction closures require a current check."),
    dict(name="Coorg", lat=12.425, lon=75.738, styles=["mountains", "forests", "waterfalls", "photography", "cool weather", "food"],
         activities=["Raja's Seat area", "Coffee-estate visit", "Madikeri town walk"], stay="Madikeri or a registered homestay", nightly=1600,
         source="https://kodagu.nic.in/en/tourism/", authority="Kodagu district", caution="Waterfall and hill access can change with rain; check notices before leaving."),
    dict(name="Gokarna", lat=14.547, lon=74.318, styles=["beaches", "quiet locations", "photography", "slow travel"],
         activities=["Beach walk", "Town heritage walk", "Coastal photography"], stay="Gokarna town or licensed beach accommodation", nightly=1300,
         source="https://uttarakannada.nic.in/en/tourism/", authority="Uttara Kannada district", caution="Sea conditions and beach access are unverified; follow local lifeguard guidance."),
    dict(name="Hampi", lat=15.335, lon=76.46, styles=["historical places", "architecture", "photography", "culture", "budget travel"],
         activities=["Heritage precinct walk", "Riverside photography", "Local food walk"], stay="Hampi area or Hosapete", nightly=1100,
         source="https://vijayanagara.nic.in/en/tourism/", authority="Vijayanagara district", caution="Confirm monument timings and fees; allow shaded breaks in hot weather."),
    dict(name="Ooty", lat=11.411, lon=76.695, styles=["mountains", "cool weather", "photography", "slow travel"],
         activities=["Botanical garden area", "Town and lake walk", "Tea-estate visit"], stay="Ooty town", nightly=1800,
         source="https://nilgiris.nic.in/tourism/", authority="Nilgiris district", caution="Check current hill-road restrictions and any vehicle entry requirements."),
    dict(name="Puducherry", lat=11.934, lon=79.83, styles=["beaches", "architecture", "food", "culture", "photography"],
         activities=["Promenade walk", "Heritage-quarter photography", "Local food trail"], stay="Heritage quarter or town centre", nightly=1600,
         source="https://puducherry.gov.in/tourism", authority="Government of Puducherry", caution="Coastal weather and beach restrictions need rechecking."),
    dict(name="Lonavala", lat=18.754, lon=73.407, styles=["mountains", "waterfalls", "scenic roads", "photography"],
         activities=["Town viewpoints", "Local food walk", "Countryside photography"], stay="Lonavala town", nightly=1700,
         source="https://pune.gov.in/tourism/", authority="Pune district", caution="Monsoon access restrictions and viewpoint crowds vary."),
    dict(name="Rishikesh", lat=30.086, lon=78.268, styles=["mountains", "adventure", "culture", "slow travel", "camping"],
         activities=["Riverside walk", "Old-town visit", "Yoga session enquiry"], stay="Rishikesh town", nightly=1400,
         source="https://uttarakhandtourism.gov.in/destination/rishikesh", authority="Uttarakhand Tourism", caution="Adventure activities require licensed operators and current operating permission."),
    dict(name="Jaipur", lat=26.913, lon=75.787, styles=["architecture", "historical places", "food", "culture", "photography"],
         activities=["Old-city walk", "Amer area visit", "Local craft and food trail"], stay="Jaipur city", nightly=1500,
         source="https://www.tourism.rajasthan.gov.in/jaipur.html", authority="Rajasthan Tourism", caution="Confirm attraction opening hours and ticket costs; heat can limit afternoons."),
    dict(name="Darjeeling", lat=27.042, lon=88.263, styles=["mountains", "cool weather", "photography", "culture"],
         activities=["Town and tea-estate walk", "Mountain-view photography", "Local food trail"], stay="Darjeeling town", nightly=1700,
         source="https://darjeeling.gov.in/tourism/", authority="Darjeeling district", caution="Hill-road conditions and visibility need current verification."),
]

CITIES = {"bengaluru": (12.972, 77.595), "bangalore": (12.972, 77.595), "mysuru": (12.296, 76.639),
          "mysore": (12.296, 76.639), "chennai": (13.083, 80.271), "hyderabad": (17.385, 78.487),
          "mumbai": (19.076, 72.878), "pune": (18.521, 73.857), "delhi": (28.614, 77.209),
          "new delhi": (28.614, 77.209), "kolkata": (22.573, 88.364), "kochi": (9.932, 76.267)}
CITIES.update({d["name"].lower(): (d["lat"], d["lon"]) for d in DESTINATIONS})
ALIASES = {"chikkamagaluru": "Chikmagalur", "chikmagalur": "Chikmagalur", "pondicherry": "Puducherry", "kodagu": "Coorg"}
ACTIVITY_TAGS = {"Mullayanagiri viewpoint": ["trekking"], "Edakkal area visit": ["trekking"]}


def lookup(name):
    name = ALIASES.get(str(name).lower(), str(name))
    return next((dict(d) for d in DESTINATIONS if d["name"].lower() == name.lower()), None)


def approximate_road_km(origin, destination):
    coords = CITIES.get(str(origin).lower())
    if not coords:
        return None
    a, b, c, d = map(radians, (*coords, destination["lat"], destination["lon"]))
    straight = 6371 * 2 * asin(sqrt(sin((c-a)/2)**2 + cos(a)*cos(c)*sin((d-b)/2)**2))
    # Road-distance allowance, explicitly not a measured routing result.
    return max(20, round(straight * 1.35 / 10) * 10)
