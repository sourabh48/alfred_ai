from __future__ import annotations

from copy import deepcopy
from difflib import SequenceMatcher
import re


CLASS_DEFAULTS = {
    "hatchback": {"expected_mileage_kmpl": 19, "service_interval_km": 10000, "service_interval_days": 365, "optimal_cruising_speed_kmph": 90},
    "sedan": {"expected_mileage_kmpl": 18, "service_interval_km": 10000, "service_interval_days": 365, "optimal_cruising_speed_kmph": 95},
    "suv": {"expected_mileage_kmpl": 15, "service_interval_km": 10000, "service_interval_days": 365, "optimal_cruising_speed_kmph": 95},
    "mpv": {"expected_mileage_kmpl": 16, "service_interval_km": 10000, "service_interval_days": 365, "optimal_cruising_speed_kmph": 90},
    "commuter": {"expected_mileage_kmpl": 58, "service_interval_km": 4000, "service_interval_days": 180, "optimal_cruising_speed_kmph": 55},
    "roadster": {"expected_mileage_kmpl": 42, "service_interval_km": 5000, "service_interval_days": 180, "optimal_cruising_speed_kmph": 70},
    "retro": {"expected_mileage_kmpl": 35, "service_interval_km": 5000, "service_interval_days": 180, "optimal_cruising_speed_kmph": 75},
    "adventure": {"expected_mileage_kmpl": 30, "service_interval_km": 5000, "service_interval_days": 180, "optimal_cruising_speed_kmph": 80},
    "sport": {"expected_mileage_kmpl": 35, "service_interval_km": 4500, "service_interval_days": 180, "optimal_cruising_speed_kmph": 85},
    "cruiser": {"expected_mileage_kmpl": 38, "service_interval_km": 5000, "service_interval_days": 180, "optimal_cruising_speed_kmph": 75},
    "touring": {"expected_mileage_kmpl": 30, "service_interval_km": 6000, "service_interval_days": 180, "optimal_cruising_speed_kmph": 90},
    "scooter": {"expected_mileage_kmpl": 48, "service_interval_km": 3000, "service_interval_days": 150, "optimal_cruising_speed_kmph": 50},
    "custom": {"expected_mileage_kmpl": 35, "service_interval_km": 5000, "service_interval_days": 180, "optimal_cruising_speed_kmph": 65},
}

MANUFACTURER_GUIDANCE = {
    "Royal Enfield": {
        "source_name": "Royal Enfield Maintenance Tips",
        "source_url": "https://www.royalenfield.com/uk/en/after-sales/digital-quickstart/goan-classic-350/maintenancetips/",
    },
    "Honda": {
        "source_name": "Honda Motorcycle & Scooter India",
        "source_url": "https://www.honda2wheelersindia.com/news/honda-motorcycle-and-scooter-india-launches-new-2025-activa-scooter-bole-toh-activa",
    },
    "Suzuki": {
        "source_name": "Suzuki Access 125 Owner's Manual",
        "source_url": "https://cdn.suzukimotorcycle.co.in/public-live/user-manual/Access-125-UZ125-NR-Ride-connect-2025.pdf",
    },
    "TVS": {
        "source_name": "TVS User Manuals",
        "source_url": "https://www.tvsmotor.com/our-service/user-manual",
    },
    "Hero": {
        "source_name": "Hero Splendor Plus Support",
        "source_url": "https://www.heromotocorp.com/en-in/blogs/more-than-just-a-ride-the-hero-splendor-plus-your-everyday-partner1.html",
    },
    "Bajaj": {
        "source_name": "Bajaj Auto",
        "source_url": "https://www.bajajauto.com/bikes/pulsar/pulsar-ns200",
    },
    "Maruti Suzuki": {
        "source_name": "Maruti Suzuki Service",
        "source_url": "https://www.marutisuzuki.com/service",
    },
    "Hyundai": {
        "source_name": "Hyundai Motor India",
        "source_url": "https://www.hyundai.com/content/dam/hyundai/in/en/data/brochure/i20brochure-aug24.pdf",
    },
    "Tata": {
        "source_name": "Tata Punch Brochure",
        "source_url": "https://cars.tatamotors.com/content/dam/tml/pv/products/punch/year-2025/ice/promoting-vc/brochures/jan-2025/punch-icng-brochure.pdf",
    },
    "Yamaha": {
        "source_name": "Yamaha Motor India",
        "source_url": "https://www.yamaha-motor-india.com/yamaha-fzsfi-v4.html",
    },
    "Ather": {
        "source_name": "Ather Energy",
        "source_url": "https://www.atherenergy.com/rizta",
    },
    "Mahindra": {
        "source_name": "Mahindra Auto",
        "source_url": "https://auto.mahindra.com/suv/xuv3xo",
    },
    "Kia": {
        "source_name": "Kia India",
        "source_url": "https://www.kia.com/in/our-vehicles/sonet/showroom.html",
    },
    "KTM": {
        "source_name": "KTM India",
        "source_url": "https://www.ktmindia.com/",
    },
    "Toyota": {
        "source_name": "Toyota Bharat",
        "source_url": "https://www.toyotabharat.com/showroom/",
    },
    "MG": {
        "source_name": "MG Motor India",
        "source_url": "https://www.mgmotor.co.in/",
    },
}


OFFICIAL_BIKE_CATALOG = [
    {
        "catalog_key": "royal-enfield-hunter-350",
        "vehicle_type": "motorcycle",
        "make": "Royal Enfield",
        "model_name": "Hunter 350",
        "variant": "",
        "display_name": "Royal Enfield Hunter 350",
        "bike_class": "retro",
        "engine_cc": 349.0,
        "fuel_tank_capacity_l": 13.0,
        "expected_mileage_kmpl": 36.0,
        "service_interval_km": 5000,
        "service_interval_days": 180,
        "optimal_cruising_speed_kmph": 75,
        "official_source_name": "Royal Enfield",
        "official_source_url": "https://www.royalenfield.com/in/en/motorcycles/hunter-350/",
        "maintenance_highlights": [
            {"label": "Rear-Shock And Tyre Wear Review", "interval": "Monthly on broken city roads", "note": "Short-wheelbase city use can show rear suspension fatigue and squared-off tyre wear before owners notice a comfort drop."},
            {"label": "Clutch Feel And Heat Cycle Check", "interval": "At each service and after dense traffic weeks", "note": "Repeated stop-go use on the 350 platform often shows up first as heavier clutch feel and extra engine heat around the legs."},
        ],
        "aliases": ["hunter 350", "re hunter", "royal enfield hunter"],
    },
    {
        "catalog_key": "royal-enfield-classic-350",
        "vehicle_type": "motorcycle",
        "make": "Royal Enfield",
        "model_name": "Classic 350",
        "variant": "",
        "display_name": "Royal Enfield Classic 350",
        "bike_class": "retro",
        "engine_cc": 349.0,
        "fuel_tank_capacity_l": 13.0,
        "expected_mileage_kmpl": 35.0,
        "service_interval_km": 5000,
        "service_interval_days": 180,
        "optimal_cruising_speed_kmph": 75,
        "official_source_name": "Royal Enfield",
        "official_source_url": "https://www.royalenfield.com/in/en/motorcycles/classic-350/",
        "aliases": ["classic 350", "re classic", "royal enfield classic"],
    },
    {
        "catalog_key": "royal-enfield-meteor-350",
        "vehicle_type": "motorcycle",
        "make": "Royal Enfield",
        "model_name": "Meteor 350",
        "variant": "",
        "display_name": "Royal Enfield Meteor 350",
        "bike_class": "cruiser",
        "engine_cc": 349.0,
        "fuel_tank_capacity_l": 15.0,
        "expected_mileage_kmpl": 34.0,
        "service_interval_km": 5000,
        "service_interval_days": 180,
        "optimal_cruising_speed_kmph": 75,
        "official_source_name": "Royal Enfield",
        "official_source_url": "https://www.royalenfield.com/in/en/motorcycles/meteor/",
        "aliases": ["meteor 350", "re meteor", "royal enfield meteor"],
    },
    {
        "catalog_key": "suzuki-v-strom-sx",
        "vehicle_type": "motorcycle",
        "make": "Suzuki",
        "model_name": "V-Strom SX",
        "variant": "",
        "display_name": "Suzuki V-Strom SX",
        "bike_class": "adventure",
        "engine_cc": 249.0,
        "fuel_tank_capacity_l": 12.0,
        "expected_mileage_kmpl": 36.0,
        "service_interval_km": 5000,
        "service_interval_days": 180,
        "optimal_cruising_speed_kmph": 85,
        "official_source_name": "Suzuki Motorcycle India",
        "official_source_url": "https://www.suzukimotorcycle.co.in/product-details/v-strom-sx",
        "aliases": ["v strom sx", "v-strom", "suzuki v strom"],
    },
    {
        "catalog_key": "bajaj-pulsar-n160",
        "vehicle_type": "motorcycle",
        "make": "Bajaj",
        "model_name": "Pulsar N160",
        "variant": "",
        "display_name": "Bajaj Pulsar N160",
        "bike_class": "roadster",
        "engine_cc": 164.82,
        "fuel_tank_capacity_l": 14.0,
        "expected_mileage_kmpl": 45.0,
        "service_interval_km": 5000,
        "service_interval_days": 180,
        "optimal_cruising_speed_kmph": 75,
        "official_source_name": "Bajaj Auto",
        "official_source_url": "https://www.bajajauto.com/bikes/pulsar/pulsar-n160",
        "aliases": ["pulsar n160", "n160", "bajaj n160"],
    },
    {
        "catalog_key": "honda-sp125",
        "vehicle_type": "motorcycle",
        "make": "Honda",
        "model_name": "SP125",
        "variant": "",
        "display_name": "Honda SP125",
        "bike_class": "commuter",
        "engine_cc": 123.94,
        "fuel_tank_capacity_l": 11.2,
        "expected_mileage_kmpl": 60.0,
        "service_interval_km": 4000,
        "service_interval_days": 180,
        "optimal_cruising_speed_kmph": 60,
        "official_source_name": "Honda Motorcycle & Scooter India",
        "official_source_url": "https://www.honda2wheelersindia.com/SP125",
        "maintenance_highlights": [
            {"label": "Mileage Drift And Plug Health Check", "interval": "Monthly or when mileage drops sharply", "note": "Commuter bikes in this class usually show tune, plug, or air-filter issues first as mileage loss rather than a hard rideability fault."},
            {"label": "Brake Shoe And Cable Free-Play Review", "interval": "At each service", "note": "Urban braking wear and clutch/throttle free-play drift can creep in gradually and hurt both control and fatigue on daily commutes."},
        ],
        "aliases": ["sp125", "sp 125", "honda sp125"],
    },
    {
        "catalog_key": "tvs-raider-125",
        "vehicle_type": "motorcycle",
        "make": "TVS",
        "model_name": "Raider 125",
        "variant": "",
        "display_name": "TVS Raider 125",
        "bike_class": "commuter",
        "engine_cc": 124.8,
        "fuel_tank_capacity_l": 10.0,
        "expected_mileage_kmpl": 57.0,
        "service_interval_km": 4000,
        "service_interval_days": 180,
        "optimal_cruising_speed_kmph": 60,
        "official_source_name": "TVS Motor",
        "official_source_url": "https://www.tvsmotor.com/tvs-raider",
        "aliases": ["raider 125", "tvs raider", "raider"],
    },
    {
        "catalog_key": "hero-splendor-plus",
        "vehicle_type": "motorcycle",
        "make": "Hero",
        "model_name": "Splendor Plus",
        "variant": "",
        "display_name": "Hero Splendor Plus",
        "bike_class": "commuter",
        "engine_cc": 97.2,
        "fuel_tank_capacity_l": 9.8,
        "expected_mileage_kmpl": 70.0,
        "service_interval_km": 4000,
        "service_interval_days": 180,
        "optimal_cruising_speed_kmph": 55,
        "official_source_name": "Hero MotoCorp",
        "official_source_url": "https://www.heromotocorp.com/content/dam/hero-commerce/in/en/products/practical/content-fragments/splendor-plus/assets/updated-image/Splendor%2BBrochure.pdf",
        "aliases": ["splendor", "splendor plus", "hero splendor"],
    },
    {
        "catalog_key": "hero-xpulse-200-4v",
        "vehicle_type": "motorcycle",
        "make": "Hero",
        "model_name": "Xpulse 200 4V",
        "variant": "",
        "display_name": "Hero Xpulse 200 4V",
        "bike_class": "adventure",
        "engine_cc": 199.6,
        "fuel_tank_capacity_l": 13.0,
        "expected_mileage_kmpl": 40.0,
        "service_interval_km": 5000,
        "service_interval_days": 180,
        "optimal_cruising_speed_kmph": 80,
        "official_source_name": "Hero MotoCorp",
        "official_source_url": "https://www.heromotocorp.com/en-in/motorcycles/xpulse-200-4v.html",
        "aliases": ["xpulse", "xpulse 200", "hero xpulse"],
    },
    {
        "catalog_key": "tvs-jupiter-110",
        "vehicle_type": "scooter",
        "make": "TVS",
        "model_name": "Jupiter 110",
        "variant": "",
        "display_name": "TVS Jupiter 110",
        "bike_class": "scooter",
        "engine_cc": 109.7,
        "fuel_tank_capacity_l": 6.0,
        "expected_mileage_kmpl": 50.0,
        "service_interval_km": 3000,
        "service_interval_days": 150,
        "optimal_cruising_speed_kmph": 50,
        "official_source_name": "TVS Motor",
        "official_source_url": "https://www.tvsmotor.com/en/ao/our-products/tvs-jupiter",
        "aliases": ["jupiter", "tvs jupiter", "jupiter 110"],
    },
    {
        "catalog_key": "honda-activa-6g",
        "vehicle_type": "scooter",
        "make": "Honda",
        "model_name": "Activa 6G",
        "variant": "",
        "display_name": "Honda Activa 6G",
        "bike_class": "scooter",
        "engine_cc": 109.51,
        "fuel_tank_capacity_l": 5.3,
        "expected_mileage_kmpl": 50.0,
        "service_interval_km": 3000,
        "service_interval_days": 150,
        "optimal_cruising_speed_kmph": 50,
        "official_source_name": "Honda Motorcycle & Scooter India",
        "official_source_url": "https://www.honda2wheelersindia.com/news/honda-motorcycle-and-scooter-india-launches-new-2025-activa-scooter-bole-toh-activa",
        "maintenance_highlights": [
            {"label": "CVT Belt And Clutch Judder Watch", "interval": "At each service and when pickup feels uneven", "note": "Stop-go city use can cause early clutch glazing or belt wear that shows up as vibration before fuel efficiency noticeably changes."},
            {"label": "Front Fork And Brake-Dive Check", "interval": "After pothole-heavy months", "note": "Frequent poor-road use often shows up as fork noise, steering heaviness, or extra brake dive before a leak is obvious."},
        ],
        "aliases": ["activa", "activa 6g", "honda activa"],
    },
    {
        "catalog_key": "suzuki-access-125",
        "vehicle_type": "scooter",
        "make": "Suzuki",
        "model_name": "Access 125",
        "variant": "",
        "display_name": "Suzuki Access 125",
        "bike_class": "scooter",
        "engine_cc": 124.0,
        "fuel_tank_capacity_l": 5.3,
        "expected_mileage_kmpl": 47.0,
        "service_interval_km": 3000,
        "service_interval_days": 150,
        "optimal_cruising_speed_kmph": 52,
        "official_source_name": "Suzuki Motorcycle India",
        "official_source_url": "https://cdn.suzukimotorcycle.co.in/public-live/user-manual/Access-125-UZ125-NR-Ride-connect-2025.pdf",
        "aliases": ["access 125", "suzuki access", "access"],
    },
    {
        "catalog_key": "tvs-ntorq-125",
        "vehicle_type": "scooter",
        "make": "TVS",
        "model_name": "NTORQ 125",
        "variant": "",
        "display_name": "TVS NTORQ 125",
        "bike_class": "scooter",
        "engine_cc": 124.8,
        "fuel_tank_capacity_l": 5.8,
        "expected_mileage_kmpl": 45.0,
        "service_interval_km": 3000,
        "service_interval_days": 150,
        "optimal_cruising_speed_kmph": 58,
        "official_source_name": "TVS Motor",
        "official_source_url": "https://www.tvsmotor.com/ss/-/media/Feature/IB/Documents/Common/Owner-Manual/Ntorq-125-RE.pdf",
        "aliases": ["ntorq 125", "tvs ntorq", "ntorq"],
    },
    {
        "catalog_key": "hero-xtreme-125r",
        "vehicle_type": "motorcycle",
        "make": "Hero",
        "model_name": "Xtreme 125R",
        "variant": "",
        "display_name": "Hero Xtreme 125R",
        "bike_class": "roadster",
        "engine_cc": 124.7,
        "fuel_tank_capacity_l": 10.0,
        "expected_mileage_kmpl": 55.0,
        "service_interval_km": 4000,
        "service_interval_days": 180,
        "optimal_cruising_speed_kmph": 65,
        "official_source_name": "Hero MotoCorp",
        "official_source_url": "https://www.heromotocorp.com/en-in/motorcycles/xtreme-125r.html",
        "aliases": ["xtreme 125r", "hero xtreme", "xtreme"],
    },
    {
        "catalog_key": "maruti-suzuki-swift",
        "vehicle_type": "car",
        "make": "Maruti Suzuki",
        "model_name": "Swift",
        "variant": "",
        "display_name": "Maruti Suzuki Swift",
        "bike_class": "hatchback",
        "engine_cc": 1197.0,
        "fuel_tank_capacity_l": 37.0,
        "expected_mileage_kmpl": 24.8,
        "service_interval_km": 10000,
        "service_interval_days": 365,
        "optimal_cruising_speed_kmph": 90,
        "official_source_name": "Maruti Suzuki India",
        "official_source_url": "https://www.marutisuzuki.com/swift",
        "aliases": ["swift", "maruti swift", "swift petrol"],
    },
    {
        "catalog_key": "maruti-suzuki-dzire",
        "vehicle_type": "car",
        "make": "Maruti Suzuki",
        "model_name": "Dzire",
        "variant": "",
        "display_name": "Maruti Suzuki Dzire",
        "bike_class": "sedan",
        "engine_cc": 1197.0,
        "fuel_tank_capacity_l": 37.0,
        "expected_mileage_kmpl": 24.8,
        "service_interval_km": 10000,
        "service_interval_days": 365,
        "optimal_cruising_speed_kmph": 90,
        "official_source_name": "Maruti Suzuki India",
        "official_source_url": "https://www.marutisuzuki.com/dzire",
        "aliases": ["dzire", "maruti dzire", "swift dzire"],
    },
    {
        "catalog_key": "hyundai-creta",
        "vehicle_type": "car",
        "make": "Hyundai",
        "model_name": "Creta",
        "variant": "",
        "display_name": "Hyundai Creta",
        "bike_class": "suv",
        "engine_cc": 1497.0,
        "fuel_tank_capacity_l": 50.0,
        "expected_mileage_kmpl": 17.4,
        "service_interval_km": 10000,
        "service_interval_days": 365,
        "optimal_cruising_speed_kmph": 95,
        "official_source_name": "Hyundai Motor India",
        "official_source_url": "https://www.hyundai.com/in/en/find-a-car/creta/highlights",
        "aliases": ["creta", "hyundai creta"],
    },
    {
        "catalog_key": "tata-nexon",
        "vehicle_type": "car",
        "make": "Tata",
        "model_name": "Nexon",
        "variant": "",
        "display_name": "Tata Nexon",
        "bike_class": "suv",
        "engine_cc": 1199.0,
        "fuel_tank_capacity_l": 44.0,
        "expected_mileage_kmpl": 17.4,
        "service_interval_km": 10000,
        "service_interval_days": 365,
        "optimal_cruising_speed_kmph": 95,
        "official_source_name": "Tata Motors",
        "official_source_url": "https://cars.tatamotors.com/suv/nexon/ice.html",
        "aliases": ["nexon", "tata nexon"],
    },
    {
        "catalog_key": "hyundai-venue",
        "vehicle_type": "car",
        "make": "Hyundai",
        "model_name": "Venue",
        "variant": "",
        "display_name": "Hyundai Venue",
        "bike_class": "suv",
        "engine_cc": 1197.0,
        "fuel_tank_capacity_l": 45.0,
        "expected_mileage_kmpl": 18.0,
        "service_interval_km": 10000,
        "service_interval_days": 365,
        "optimal_cruising_speed_kmph": 95,
        "official_source_name": "Hyundai Motor India",
        "official_source_url": "https://www.hyundai.com/in/en/find-a-car/venue/highlights",
        "aliases": ["venue", "hyundai venue"],
    },
    {
        "catalog_key": "maruti-suzuki-baleno",
        "vehicle_type": "car",
        "make": "Maruti Suzuki",
        "model_name": "Baleno",
        "variant": "",
        "display_name": "Maruti Suzuki Baleno",
        "bike_class": "hatchback",
        "engine_cc": 1197.0,
        "fuel_tank_capacity_l": 37.0,
        "expected_mileage_kmpl": 22.9,
        "service_interval_km": 10000,
        "service_interval_days": 365,
        "optimal_cruising_speed_kmph": 90,
        "official_source_name": "NEXA",
        "official_source_url": "https://www.nexaexperience.com/new-age-baleno",
        "aliases": ["baleno", "maruti baleno", "nexa baleno"],
    },
    {
        "catalog_key": "hyundai-i20",
        "vehicle_type": "car",
        "make": "Hyundai",
        "model_name": "i20",
        "variant": "",
        "display_name": "Hyundai i20",
        "bike_class": "hatchback",
        "engine_cc": 1197.0,
        "fuel_tank_capacity_l": 37.0,
        "expected_mileage_kmpl": 20.0,
        "service_interval_km": 10000,
        "service_interval_days": 365,
        "optimal_cruising_speed_kmph": 90,
        "official_source_name": "Hyundai Motor India",
        "official_source_url": "https://www.hyundai.com/content/dam/hyundai/in/en/data/brochure/i20brochure-aug24.pdf",
        "aliases": ["i20", "hyundai i20", "elite i20"],
    },
    {
        "catalog_key": "tata-punch",
        "vehicle_type": "car",
        "make": "Tata",
        "model_name": "Punch",
        "variant": "",
        "display_name": "Tata Punch",
        "bike_class": "suv",
        "engine_cc": 1199.0,
        "fuel_tank_capacity_l": 37.0,
        "expected_mileage_kmpl": 18.8,
        "service_interval_km": 10000,
        "service_interval_days": 365,
        "optimal_cruising_speed_kmph": 92,
        "official_source_name": "Tata Motors",
        "official_source_url": "https://cars.tatamotors.com/content/dam/tml/pv/products/punch/year-2025/ice/promoting-vc/brochures/jan-2025/punch-icng-brochure.pdf",
        "aliases": ["punch", "tata punch"],
    },
    {
        "catalog_key": "bajaj-pulsar-ns200",
        "vehicle_type": "motorcycle",
        "make": "Bajaj",
        "model_name": "Pulsar NS200",
        "variant": "",
        "display_name": "Bajaj Pulsar NS200",
        "bike_class": "sport",
        "engine_cc": 199.5,
        "fuel_tank_capacity_l": 12.0,
        "expected_mileage_kmpl": 36.0,
        "service_interval_km": 5000,
        "service_interval_days": 180,
        "optimal_cruising_speed_kmph": 82,
        "official_source_name": "Bajaj Auto",
        "official_source_url": "https://www.bajajauto.com/bikes/pulsar/pulsar-ns200",
        "maintenance_highlights": [
            {"label": "Brake And Tyre Heat Check", "interval": "Before weekend highway runs", "note": "NS200-class riding loads front brakes and tyre shoulders harder, so heat-cycle checks matter more than on a commuter."},
            {"label": "Chain Slack And Sprocket Wear", "interval": "Every 600-800 km in rain or dust", "note": "Shorter chain-service cadence helps keep acceleration response and mileage from drifting."},
        ],
        "aliases": ["pulsar ns200", "ns200", "bajaj ns200"],
    },
    {
        "catalog_key": "tvs-apache-rtr-160-4v",
        "vehicle_type": "motorcycle",
        "make": "TVS",
        "model_name": "Apache RTR 160 4V",
        "variant": "",
        "display_name": "TVS Apache RTR 160 4V",
        "bike_class": "sport",
        "engine_cc": 159.7,
        "fuel_tank_capacity_l": 12.0,
        "expected_mileage_kmpl": 41.0,
        "service_interval_km": 4000,
        "service_interval_days": 180,
        "optimal_cruising_speed_kmph": 78,
        "official_source_name": "TVS Motor",
        "official_source_url": "https://www.tvsmotor.com/tvs-apache/apache-rtr-160-4v",
        "maintenance_highlights": [
            {"label": "Throttle Response And Idle Stability", "interval": "At each service", "note": "Early throttle roughness or idle drift can mask injector, plug, or clutch tuning issues before mileage falls sharply."},
        ],
        "aliases": ["apache rtr 160 4v", "rtr 160 4v", "tvs apache 160"],
    },
    {
        "catalog_key": "yamaha-fzs-fi-v4",
        "vehicle_type": "motorcycle",
        "make": "Yamaha",
        "model_name": "FZS FI V4",
        "variant": "",
        "display_name": "Yamaha FZS FI V4",
        "bike_class": "roadster",
        "engine_cc": 149.0,
        "fuel_tank_capacity_l": 13.0,
        "expected_mileage_kmpl": 46.0,
        "service_interval_km": 4000,
        "service_interval_days": 180,
        "optimal_cruising_speed_kmph": 72,
        "official_source_name": "Yamaha Motor India",
        "official_source_url": "https://www.yamaha-motor-india.com/yamaha-fzsfi-v4.html",
        "maintenance_highlights": [
            {"label": "Injector And Air Filter Cleanliness", "interval": "At each service and after dusty commutes", "note": "Mileage on this platform reacts quickly to clogged intake or weak fueling, so intake health is a first-line check."},
        ],
        "aliases": ["fzs fi v4", "yamaha fzs", "fzs v4"],
    },
    {
        "catalog_key": "ather-rizta",
        "vehicle_type": "scooter",
        "make": "Ather",
        "model_name": "Rizta",
        "variant": "",
        "display_name": "Ather Rizta",
        "bike_class": "scooter",
        "engine_cc": 0.0,
        "fuel_tank_capacity_l": 0.0,
        "expected_mileage_kmpl": 0.0,
        "service_interval_km": 5000,
        "service_interval_days": 180,
        "optimal_cruising_speed_kmph": 55,
        "official_source_name": "Ather Energy",
        "official_source_url": "https://www.atherenergy.com/rizta",
        "maintenance_highlights": [
            {"label": "Tyre Pressure And Regen Feel", "interval": "Weekly and before long city runs", "note": "On EV scooters, tyre drag and regen consistency affect indicated efficiency faster than engine-style service items."},
            {"label": "Charging Habit Review", "interval": "Monthly", "note": "Repeated deep-discharge or heat-heavy charging patterns can degrade real-world range before the dashboard makes it obvious."},
        ],
        "aliases": ["ather rizta", "rizta"],
    },
    {
        "catalog_key": "mahindra-xuv-3xo",
        "vehicle_type": "car",
        "make": "Mahindra",
        "model_name": "XUV 3XO",
        "variant": "",
        "display_name": "Mahindra XUV 3XO",
        "bike_class": "suv",
        "engine_cc": 1197.0,
        "fuel_tank_capacity_l": 42.0,
        "expected_mileage_kmpl": 18.2,
        "service_interval_km": 10000,
        "service_interval_days": 365,
        "optimal_cruising_speed_kmph": 92,
        "official_source_name": "Mahindra Auto",
        "official_source_url": "https://auto.mahindra.com/suv/xuv3xo",
        "maintenance_highlights": [
            {"label": "Turbo And Cooling Observation", "interval": "Before highway or hill travel", "note": "Turbo-petrol load and cooling efficiency affect drivability and cost more abruptly than on a naturally aspirated city hatch."},
        ],
        "aliases": ["xuv 3xo", "mahindra xuv 3xo", "3xo"],
    },
    {
        "catalog_key": "kia-sonet",
        "vehicle_type": "car",
        "make": "Kia",
        "model_name": "Sonet",
        "variant": "",
        "display_name": "Kia Sonet",
        "bike_class": "suv",
        "engine_cc": 1197.0,
        "fuel_tank_capacity_l": 45.0,
        "expected_mileage_kmpl": 18.4,
        "service_interval_km": 10000,
        "service_interval_days": 365,
        "optimal_cruising_speed_kmph": 90,
        "official_source_name": "Kia India",
        "official_source_url": "https://www.kia.com/in/our-vehicles/sonet/showroom.html",
        "maintenance_highlights": [
            {"label": "Brake Fluid And Alignment Review", "interval": "At each annual service", "note": "Urban stop-go use and pothole exposure show up first as brake feel, tyre wear, and steering correction."},
        ],
        "aliases": ["kia sonet", "sonet"],
    },
    {
        "catalog_key": "ktm-duke-200",
        "vehicle_type": "motorcycle",
        "make": "KTM",
        "model_name": "Duke 200",
        "variant": "",
        "display_name": "KTM Duke 200",
        "bike_class": "roadster",
        "engine_cc": 199.5,
        "fuel_tank_capacity_l": 13.4,
        "expected_mileage_kmpl": 34.0,
        "service_interval_km": 5000,
        "service_interval_days": 180,
        "optimal_cruising_speed_kmph": 82,
        "official_source_name": "KTM India",
        "official_source_url": "https://www.ktmindia.com/",
        "maintenance_highlights": [
            {"label": "Cooling And Fan-Cycle Review", "interval": "Before summer traffic commutes or spirited weekend rides", "note": "Performance-tuned singles show thermal stress earlier in dense traffic, so coolant condition and fan behavior matter more than on a low-stress commuter."},
            {"label": "Tyre Edge And Brake Heat Check", "interval": "Weekly for aggressive use", "note": "Sportier braking and cornering loads front tyres and pads faster, so early wear checks protect both grip and stopping confidence."},
        ],
        "aliases": ["ktm duke 200", "duke 200", "ktm 200"],
    },
    {
        "catalog_key": "toyota-urban-cruiser-hyryder",
        "vehicle_type": "car",
        "make": "Toyota",
        "model_name": "Urban Cruiser Hyryder",
        "variant": "",
        "display_name": "Toyota Urban Cruiser Hyryder",
        "bike_class": "suv",
        "engine_cc": 1490.0,
        "fuel_tank_capacity_l": 45.0,
        "expected_mileage_kmpl": 20.0,
        "service_interval_km": 10000,
        "service_interval_days": 365,
        "optimal_cruising_speed_kmph": 92,
        "official_source_name": "Toyota Bharat",
        "official_source_url": "https://www.toyotabharat.com/showroom/",
        "maintenance_highlights": [
            {"label": "Hybrid Battery Cooling And Filter Review", "interval": "At annual service in dusty climates", "note": "Hybrid systems are sensitive to airflow restriction around the battery cooling path, especially in dusty or pet-hair-heavy cabins."},
            {"label": "Tyre Rotation And Alignment Discipline", "interval": "Every 10,000 km or sooner on mixed city-highway use", "note": "Efficiency and steering stability on crossover hybrids degrade noticeably when alignment drift or uneven tyre wear goes unchecked."},
        ],
        "aliases": ["hyryder", "urban cruiser hyryder", "toyota hyryder"],
    },
    {
        "catalog_key": "mg-comet-ev",
        "vehicle_type": "car",
        "make": "MG",
        "model_name": "Comet EV",
        "variant": "",
        "display_name": "MG Comet EV",
        "bike_class": "hatchback",
        "engine_cc": 0.0,
        "fuel_tank_capacity_l": 0.0,
        "expected_mileage_kmpl": 0.0,
        "service_interval_km": 10000,
        "service_interval_days": 365,
        "optimal_cruising_speed_kmph": 70,
        "official_source_name": "MG Motor India",
        "official_source_url": "https://www.mgmotor.co.in/",
        "maintenance_highlights": [
            {"label": "Charging Pattern And Range Drift Audit", "interval": "Monthly", "note": "Small-city EVs show charging-habit and accessory-load effects in real-world range faster than larger battery vehicles."},
            {"label": "Tyre Drag And Brake Regen Smoothness", "interval": "Fortnightly", "note": "Low rolling resistance and smooth regen feel matter more on compact EVs where tyre drag can materially change city efficiency."},
        ],
        "aliases": ["mg comet", "comet ev", "mg comet ev"],
    },
    {
        "catalog_key": "bajaj-chetak",
        "vehicle_type": "scooter",
        "make": "Bajaj",
        "model_name": "Chetak",
        "variant": "",
        "display_name": "Bajaj Chetak",
        "bike_class": "scooter",
        "engine_cc": 0.0,
        "fuel_tank_capacity_l": 0.0,
        "expected_mileage_kmpl": 0.0,
        "service_interval_km": 5000,
        "service_interval_days": 180,
        "optimal_cruising_speed_kmph": 52,
        "official_source_name": "Bajaj Auto",
        "official_source_url": "https://www.bajajauto.com/chetak",
        "maintenance_highlights": [
            {"label": "Charge Cycle And Thermal Pattern Review", "interval": "Monthly", "note": "Frequent full-range discharge or heat-heavy fast charging can depress real-world range before the dashboard makes it obvious."},
            {"label": "Brake Drag And Tyre Efficiency Check", "interval": "Fortnightly", "note": "On heavier electric scooters, rolling resistance and light brake drag can cut range faster than riders expect."},
        ],
        "aliases": ["chetak", "bajaj chetak"],
    },
    {
        "catalog_key": "yamaha-aerox-155",
        "vehicle_type": "scooter",
        "make": "Yamaha",
        "model_name": "Aerox 155",
        "variant": "",
        "display_name": "Yamaha Aerox 155",
        "bike_class": "scooter",
        "engine_cc": 155.0,
        "fuel_tank_capacity_l": 5.5,
        "expected_mileage_kmpl": 40.0,
        "service_interval_km": 4000,
        "service_interval_days": 180,
        "optimal_cruising_speed_kmph": 68,
        "official_source_name": "Yamaha Motor India",
        "official_source_url": "https://www.yamaha-motor-india.com/yamaha-aerox155.html",
        "maintenance_highlights": [
            {"label": "CVT Response And Belt Health", "interval": "At each service", "note": "Pickup loss or vibration during quick overtakes often points to transmission wear before fuel efficiency drops."},
            {"label": "Sport Tyre Pressure Discipline", "interval": "Weekly", "note": "This platform is more sensitive to underinflation because sporty tyre sizes can drag both handling and mileage quickly."},
        ],
        "aliases": ["aerox 155", "yamaha aerox", "aerox"],
    },
    {
        "catalog_key": "ather-450x",
        "vehicle_type": "scooter",
        "make": "Ather",
        "model_name": "450X",
        "variant": "",
        "display_name": "Ather 450X",
        "bike_class": "scooter",
        "engine_cc": 0.0,
        "fuel_tank_capacity_l": 0.0,
        "expected_mileage_kmpl": 0.0,
        "service_interval_km": 5000,
        "service_interval_days": 180,
        "optimal_cruising_speed_kmph": 60,
        "official_source_name": "Ather Energy",
        "official_source_url": "https://www.atherenergy.com/450x",
        "maintenance_highlights": [
            {"label": "Battery Range Drift Watch", "interval": "Monthly", "note": "Track indicated range against actual commute coverage to catch early battery or charging-pattern degradation."},
            {"label": "Tyre Wear And Regen Smoothness", "interval": "Weekly", "note": "Uneven tyre wear and abrupt regen feel can signal efficiency and handling loss before a hard fault appears."},
        ],
        "aliases": ["ather 450x", "450x"],
    },
    {
        "catalog_key": "mahindra-scorpio-n",
        "vehicle_type": "car",
        "make": "Mahindra",
        "model_name": "Scorpio-N",
        "variant": "",
        "display_name": "Mahindra Scorpio-N",
        "bike_class": "suv",
        "engine_cc": 2198.0,
        "fuel_tank_capacity_l": 57.0,
        "expected_mileage_kmpl": 15.0,
        "service_interval_km": 10000,
        "service_interval_days": 365,
        "optimal_cruising_speed_kmph": 95,
        "official_source_name": "Mahindra Auto",
        "official_source_url": "https://auto.mahindra.com/suv/scorpio-n",
        "maintenance_highlights": [
            {"label": "Suspension And Alignment Review", "interval": "After rough-road trips", "note": "Ladder-frame SUVs can mask alignment drift until tyre wear and steering correction become expensive."},
            {"label": "Brake And Cooling Margin Check", "interval": "Before towing, hills, or family highway runs", "note": "Heavy-load use raises brake and thermal stress faster than routine city driving."},
        ],
        "aliases": ["scorpio n", "mahindra scorpio n", "scorpio-n"],
    },
    {
        "catalog_key": "kia-seltos",
        "vehicle_type": "car",
        "make": "Kia",
        "model_name": "Seltos",
        "variant": "",
        "display_name": "Kia Seltos",
        "bike_class": "suv",
        "engine_cc": 1497.0,
        "fuel_tank_capacity_l": 50.0,
        "expected_mileage_kmpl": 17.2,
        "service_interval_km": 10000,
        "service_interval_days": 365,
        "optimal_cruising_speed_kmph": 92,
        "official_source_name": "Kia India",
        "official_source_url": "https://www.kia.com/in/our-vehicles/seltos/showroom.html",
        "maintenance_highlights": [
            {"label": "Fuel-Efficiency Drift Review", "interval": "Monthly", "note": "Turbo and automatic variants can lose efficiency gradually through intake, alignment, or tyre issues before a warning appears."},
            {"label": "Cabin Filter And AC Load Check", "interval": "Seasonally", "note": "Urban comfort systems affect efficiency and long-drive fatigue more than owners usually notice."},
        ],
        "aliases": ["kia seltos", "seltos"],
    },
]


def normalize_bike_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (value or "").lower()).strip()


def list_catalog_models(vehicle_type: str | None = None) -> list[dict]:
    normalized_type = str(vehicle_type or "").strip().lower()
    items = [deepcopy(apply_class_defaults(item)) for item in OFFICIAL_BIKE_CATALOG]
    if normalized_type and normalized_type not in {"all", "any"}:
        items = [item for item in items if item.get("vehicle_type") == normalized_type]
    return items


def apply_class_defaults(data: dict) -> dict:
    bike_class = data.get("bike_class") or "custom"
    defaults = CLASS_DEFAULTS.get(bike_class, CLASS_DEFAULTS["custom"])
    merged = deepcopy(data)
    for key, value in defaults.items():
        if merged.get(key) in {None, "", 0}:
            merged[key] = value
    if not merged.get("maintenance_guidance"):
        merged["maintenance_guidance"] = build_maintenance_guidance(merged)
    return merged


def best_catalog_match(name: str) -> tuple[dict | None, float]:
    normalized = normalize_bike_name(name)
    if not normalized:
        return None, 0

    best_item = None
    best_score = 0.0
    for item in OFFICIAL_BIKE_CATALOG:
        candidates = [item["display_name"], item["model_name"], *item.get("aliases", [])]
        for candidate in candidates:
            score = SequenceMatcher(None, normalized, normalize_bike_name(candidate)).ratio()
            if normalized in normalize_bike_name(candidate) or normalize_bike_name(candidate) in normalized:
                score += 0.08
            if score > best_score:
                best_item = item
                best_score = score
    return (deepcopy(apply_class_defaults(best_item)), min(best_score, 1.0)) if best_item else (None, 0.0)


def build_profile_payload(name: str, vehicle_number: str = "", variant: str = "", make: str = "") -> dict:
    normalized_name = normalize_bike_name(name)
    normalized_make = normalize_bike_name(make)
    search_name = name if not normalized_make or normalized_name.startswith(normalized_make) else f"{make} {name}"
    match, score = best_catalog_match(search_name)
    if match and score >= 0.78:
        match["vehicle_number"] = vehicle_number
        match["usage_pattern"] = match.get("usage_pattern") or ("essential" if match.get("vehicle_type") == "car" else "personal")
        match["estimated_market_value"] = match.get("estimated_market_value") or 0
        match["monthly_income_support"] = match.get("monthly_income_support") or 0
        match["verification_status"] = "official" if score >= 0.92 else "matched"
        match["ai_notes"] = (
            f"Matched against the internal vehicle catalog with confidence {score:.2f}. "
            "Specs are catalog-backed and should still be cross-checked against the owner's manual for exact service intervals."
        )
        return match

    normalized_name = " ".join(part for part in [make.strip(), name.strip()] if part).strip() or "Custom Vehicle"
    inferred_vehicle_type = infer_vehicle_type(normalized_name)
    inferred_class = infer_bike_class(normalized_name)
    defaults = CLASS_DEFAULTS[inferred_class]
    return {
        "vehicle_type": inferred_vehicle_type,
        "catalog_key": "",
        "make": make.strip(),
        "model_name": name.strip() or normalized_name,
        "variant": variant.strip(),
        "display_name": normalized_name,
        "vehicle_number": vehicle_number,
        "bike_class": inferred_class,
        "engine_cc": None,
        "fuel_tank_capacity_l": None,
        "expected_mileage_kmpl": defaults["expected_mileage_kmpl"],
        "service_interval_km": defaults["service_interval_km"],
        "service_interval_days": defaults["service_interval_days"],
        "optimal_cruising_speed_kmph": defaults["optimal_cruising_speed_kmph"],
        "usage_pattern": "essential" if inferred_vehicle_type == "car" else "personal",
        "estimated_market_value": 0,
        "monthly_income_support": 0,
        "official_source_name": "",
        "official_source_url": "",
        "verification_status": "custom",
        "ai_notes": "No confident catalog match yet. Alfred is using class-based heuristics until more documents or usage history are available.",
        "maintenance_guidance": build_maintenance_guidance(
            {
                "make": make.strip(),
                "vehicle_type": inferred_vehicle_type,
                "bike_class": inferred_class,
                "service_interval_km": defaults["service_interval_km"],
                "service_interval_days": defaults["service_interval_days"],
                "official_source_name": "",
                "official_source_url": "",
            }
        ),
    }


def infer_bike_class(value: str) -> str:
    normalized = normalize_bike_name(value)
    if any(token in normalized for token in ["creta", "nexon", "suv", "thar", "harrier"]):
        return "suv"
    if any(token in normalized for token in ["dzire", "verna", "city", "sedan"]):
        return "sedan"
    if any(token in normalized for token in ["swift", "i20", "baleno", "altroz", "hatchback"]):
        return "hatchback"
    if any(token in normalized for token in ["ertiga", "carens", "mpv"]):
        return "mpv"
    if any(token in normalized for token in ["adventure", "adv", "strom", "himalayan"]):
        return "adventure"
    if any(token in normalized for token in ["classic", "meteor", "bullet", "hunter", "retro"]):
        return "retro"
    if any(token in normalized for token in ["cruiser", "avenger"]):
        return "cruiser"
    if any(token in normalized for token in ["raider", "sp", "shine", "splendor", "commuter"]):
        return "commuter"
    if any(token in normalized for token in ["rr", "rc", "r15", "ninja", "sport"]):
        return "sport"
    return "roadster"


def infer_vehicle_type(value: str) -> str:
    normalized = normalize_bike_name(value)
    if any(token in normalized for token in ["car", "hatchback", "sedan", "suv", "swift", "dzire", "creta", "nexon", "alto", "baleno"]):
        return "car"
    if any(token in normalized for token in ["scooter", "activa", "jupiter", "ntorq"]):
        return "scooter"
    return "motorcycle"


def build_maintenance_guidance(data: dict) -> list[dict]:
    make = (data.get("make") or "").strip()
    guidance_source = MANUFACTURER_GUIDANCE.get(make, {})
    source_name = guidance_source.get("source_name") or data.get("official_source_name") or "Official source"
    source_url = guidance_source.get("source_url") or data.get("official_source_url") or ""
    service_interval_km = data.get("service_interval_km") or CLASS_DEFAULTS["custom"]["service_interval_km"]
    service_interval_days = data.get("service_interval_days") or CLASS_DEFAULTS["custom"]["service_interval_days"]
    vehicle_type = data.get("vehicle_type") or "motorcycle"

    items = [
        {
            "label": "Periodic Service Window",
            "interval": f"Every {service_interval_km:,} km or {service_interval_days} days",
            "note": "Treat this as the primary paid-service checkpoint and tighten it if rides are dusty, stop-go heavy, or monsoon exposed.",
            "source_name": source_name,
            "source_url": source_url,
        },
        {
            "label": "Tyres, Brakes, And Pressures",
            "interval": "Before long rides and at each service",
            "note": "Track pad wear, tyre age, pressure, and wheel condition together because they move mileage, grip, and braking safety at the same time.",
            "source_name": source_name,
            "source_url": source_url,
        },
        {
            "label": "Engine / Drive Health",
            "interval": "At each service and before highway use",
            "note": "Watch oil age, filter state, chain or driveline smoothness, and idle quality before blaming mileage alone.",
            "source_name": source_name,
            "source_url": source_url,
        },
    ]
    if vehicle_type == "car":
        items.append(
            {
                "label": "Cooling, Battery, And Fluids",
                "interval": "Check quarterly or before seasonal travel",
                "note": "Cars benefit from a wider fluid checklist: coolant, battery health, brake fluid, and cabin-filter state all affect comfort and reliability.",
                "source_name": source_name,
                "source_url": source_url,
            }
        )
    else:
        items.append(
            {
                "label": "Chain / CVT / Transmission Check",
                "interval": "Every wash cycle and before touring",
                "note": "For motorcycles, keep chain clean and in spec. For scooters, listen for CVT belt or clutch behavior if pickup or mileage degrades.",
                "source_name": source_name,
                "source_url": source_url,
            }
        )
    for highlight in data.get("maintenance_highlights") or []:
        items.append(
            {
                "label": highlight.get("label", "Model-Specific Check"),
                "interval": highlight.get("interval", f"Every {service_interval_km:,} km or {service_interval_days} days"),
                "note": highlight.get("note", ""),
                "source_name": highlight.get("source_name", source_name),
                "source_url": highlight.get("source_url", source_url),
            }
        )
    return items
