from __future__ import annotations

from collections import Counter
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
    "Ola": {
        "source_name": "Ola Electric",
        "source_url": "https://www.olaelectric.com/",
    },
    "Skoda": {
        "source_name": "Skoda Auto India",
        "source_url": "https://www.skoda-auto.co.in/",
    },
    "Volkswagen": {
        "source_name": "Volkswagen India",
        "source_url": "https://www.volkswagen.co.in/",
    },
    "Renault": {
        "source_name": "Renault India",
        "source_url": "https://www.renault.co.in/",
    },
    "Nissan": {
        "source_name": "Nissan India",
        "source_url": "https://www.nissan.in/",
    },
    "Citroen": {
        "source_name": "Citroen India",
        "source_url": "https://www.citroen.in/",
    },
    "Jeep": {
        "source_name": "Jeep India",
        "source_url": "https://www.jeep-india.com/",
    },
    "BYD": {
        "source_name": "BYD Auto India",
        "source_url": "https://bydautoindia.com/",
    },
    "Jawa": {
        "source_name": "Jawa Motorcycles",
        "source_url": "https://www.jawamotorcycles.com/",
    },
    "Yezdi": {
        "source_name": "Yezdi Motorcycles",
        "source_url": "https://www.yezdi.com/",
    },
    "Triumph": {
        "source_name": "Triumph Motorcycles India",
        "source_url": "https://www.triumphmotorcycles.in/",
    },
    "Harley-Davidson": {
        "source_name": "Harley-Davidson X440",
        "source_url": "https://www.harley-davidsonx440.com/",
    },
    "BMW": {
        "source_name": "BMW Motorrad India",
        "source_url": "https://www.bmw-motorrad.in/",
    },
    "Revolt": {
        "source_name": "Revolt Motors",
        "source_url": "https://www.revoltmotors.com/",
    },
    "Ultraviolette": {
        "source_name": "Ultraviolette",
        "source_url": "https://www.ultraviolette.com/",
    },
    "Simple Energy": {
        "source_name": "Simple Energy",
        "source_url": "https://www.simpleenergy.in/",
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
        "fuel_type": "electric",
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
        "fuel_type": "electric",
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
        "fuel_type": "electric",
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
        "fuel_type": "electric",
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
    {
        "catalog_key": "honda-city",
        "vehicle_type": "car",
        "make": "Honda",
        "model_name": "City",
        "variant": "",
        "display_name": "Honda City",
        "bike_class": "sedan",
        "engine_cc": 1498.0,
        "fuel_tank_capacity_l": 40.0,
        "expected_mileage_kmpl": 18.4,
        "service_interval_km": 10000,
        "service_interval_days": 365,
        "optimal_cruising_speed_kmph": 95,
        "official_source_name": "Honda Cars India",
        "official_source_url": "https://www.hondacarindia.com/honda-city",
        "maintenance_highlights": [
            {"label": "CVT And Brake Fluid Watch", "interval": "At annual service and before highway travel", "note": "Sedan commute and highway use can hide gradual brake-fluid age and transmission smoothness drift until ride quality drops."},
        ],
        "aliases": ["honda city", "city sedan"],
    },
    {
        "catalog_key": "maruti-suzuki-ertiga",
        "vehicle_type": "car",
        "make": "Maruti Suzuki",
        "model_name": "Ertiga",
        "variant": "",
        "display_name": "Maruti Suzuki Ertiga",
        "bike_class": "mpv",
        "engine_cc": 1462.0,
        "fuel_tank_capacity_l": 45.0,
        "expected_mileage_kmpl": 20.3,
        "service_interval_km": 10000,
        "service_interval_days": 365,
        "optimal_cruising_speed_kmph": 90,
        "official_source_name": "Maruti Suzuki India",
        "official_source_url": "https://www.marutisuzuki.com/ertiga",
        "maintenance_highlights": [
            {"label": "Loaded-Family Trip Readiness", "interval": "Before outstation travel", "note": "Seven-seat loading increases tyre, brake, suspension, and cooling pressure more than solo commute use."},
        ],
        "aliases": ["ertiga", "maruti ertiga"],
    },
    {
        "catalog_key": "ola-s1-pro",
        "vehicle_type": "scooter",
        "make": "Ola",
        "model_name": "S1 Pro",
        "variant": "",
        "display_name": "Ola S1 Pro",
        "bike_class": "scooter",
        "engine_cc": 0.0,
        "fuel_tank_capacity_l": 0.0,
        "expected_mileage_kmpl": 0.0,
        "service_interval_km": 5000,
        "service_interval_days": 180,
        "optimal_cruising_speed_kmph": 60,
        "fuel_type": "electric",
        "official_source_name": "Ola Electric",
        "official_source_url": "https://www.olaelectric.com/s1-pro",
        "maintenance_highlights": [
            {"label": "Range Drift And Tyre Drag Check", "interval": "Monthly", "note": "EV scooter range drops quickly when tyre pressure, bearing drag, brake drag, or charging heat patterns are off."},
            {"label": "Software And Charging Habit Review", "interval": "At each service touchpoint", "note": "Track software state and charge cycles with physical checks instead of treating range loss as only a battery issue."},
        ],
        "aliases": ["ola s1 pro", "s1 pro", "ola scooter"],
    },
    {
        "catalog_key": "mahindra-thar",
        "vehicle_type": "car",
        "make": "Mahindra",
        "model_name": "Thar",
        "variant": "",
        "display_name": "Mahindra Thar",
        "bike_class": "suv",
        "engine_cc": 1997.0,
        "fuel_tank_capacity_l": 57.0,
        "expected_mileage_kmpl": 15.2,
        "service_interval_km": 10000,
        "service_interval_days": 365,
        "optimal_cruising_speed_kmph": 90,
        "official_source_name": "Mahindra Auto",
        "official_source_url": "https://auto.mahindra.com/suv/thar",
        "maintenance_highlights": [
            {"label": "Off-Road Undercarriage And Alignment Review", "interval": "After trail or rough-road use", "note": "Off-road and pothole-heavy use should trigger underbody, suspension, tyre, and steering checks before routine service due dates."},
        ],
        "aliases": ["mahindra thar", "thar"],
    },
]


def _catalog_entry(
    catalog_key: str,
    vehicle_type: str,
    make: str,
    model_name: str,
    display_name: str,
    bike_class: str,
    engine_cc: float,
    fuel_tank_capacity_l: float,
    expected_mileage_kmpl: float,
    service_interval_km: int,
    service_interval_days: int,
    optimal_cruising_speed_kmph: int,
    official_source_name: str,
    official_source_url: str,
    aliases: list[str],
    *,
    variant: str = "",
    fuel_type: str = "petrol",
    maintenance_highlights: list[dict] | None = None,
) -> dict:
    return {
        "catalog_key": catalog_key,
        "vehicle_type": vehicle_type,
        "make": make,
        "model_name": model_name,
        "variant": variant,
        "display_name": display_name,
        "bike_class": bike_class,
        "engine_cc": engine_cc,
        "fuel_tank_capacity_l": fuel_tank_capacity_l,
        "expected_mileage_kmpl": expected_mileage_kmpl,
        "service_interval_km": service_interval_km,
        "service_interval_days": service_interval_days,
        "optimal_cruising_speed_kmph": optimal_cruising_speed_kmph,
        "fuel_type": fuel_type,
        "official_source_name": official_source_name,
        "official_source_url": official_source_url,
        "maintenance_highlights": maintenance_highlights or [],
        "aliases": aliases,
    }


EXTENDED_OFFICIAL_BIKE_CATALOG = [
    _catalog_entry(
        "maruti-suzuki-brezza",
        "car",
        "Maruti Suzuki",
        "Brezza",
        "Maruti Suzuki Brezza",
        "suv",
        1462.0,
        48.0,
        19.8,
        10000,
        365,
        90,
        "Maruti Suzuki India",
        "https://www.marutisuzuki.com/brezza",
        ["brezza", "maruti brezza", "vitara brezza"],
        maintenance_highlights=[
            {"label": "SUV Tyre Rotation And Alignment", "interval": "Every 10,000 km or after pothole-heavy months", "note": "Compact SUVs mask tyre shoulder wear until steering correction and road noise rise."},
        ],
    ),
    _catalog_entry(
        "hyundai-exter",
        "car",
        "Hyundai",
        "Exter",
        "Hyundai Exter",
        "suv",
        1197.0,
        37.0,
        19.4,
        10000,
        365,
        90,
        "Hyundai Motor India",
        "https://www.hyundai.com/in/en/find-a-car/exter/highlights",
        ["exter", "hyundai exter"],
        maintenance_highlights=[
            {"label": "City SUV Brake And AC Load Review", "interval": "At annual service and before summer trips", "note": "Dense city use raises brake, battery, tyre, and cabin-cooling load before a warning light appears."},
        ],
    ),
    _catalog_entry(
        "tata-harrier",
        "car",
        "Tata",
        "Harrier",
        "Tata Harrier",
        "suv",
        1956.0,
        50.0,
        16.8,
        10000,
        365,
        95,
        "Tata Motors",
        "https://cars.tatamotors.com/suv/harrier",
        ["harrier", "tata harrier"],
        fuel_type="diesel",
        maintenance_highlights=[
            {"label": "Diesel Highway Cooling And DPF Watch", "interval": "Before long highway or hill runs", "note": "Heavier diesel SUVs should keep cooling, air filter, brake fluid, and exhaust-regeneration behavior in view."},
        ],
    ),
    _catalog_entry(
        "mahindra-xuv700",
        "car",
        "Mahindra",
        "XUV700",
        "Mahindra XUV700",
        "suv",
        1997.0,
        60.0,
        15.5,
        10000,
        365,
        95,
        "Mahindra Auto",
        "https://auto.mahindra.com/suv/xuv700",
        ["xuv700", "mahindra xuv700", "xuv 700"],
        maintenance_highlights=[
            {"label": "Loaded Highway Brake And Cooling Margin", "interval": "Before long family trips", "note": "High-speed loaded use increases brake heat, tyre load, and cooling demand beyond normal commute wear."},
        ],
    ),
    _catalog_entry(
        "kia-carens",
        "car",
        "Kia",
        "Carens",
        "Kia Carens",
        "mpv",
        1497.0,
        45.0,
        17.9,
        10000,
        365,
        90,
        "Kia India",
        "https://www.kia.com/in/our-vehicles/carens/showroom.html",
        ["carens", "kia carens"],
        maintenance_highlights=[
            {"label": "Three-Row Load And Tyre Pressure Audit", "interval": "Before outstation family travel", "note": "Passenger and luggage load changes tyre pressure, braking distance, suspension load, and fuel use."},
        ],
    ),
    _catalog_entry(
        "honda-amaze",
        "car",
        "Honda",
        "Amaze",
        "Honda Amaze",
        "sedan",
        1199.0,
        35.0,
        18.6,
        10000,
        365,
        90,
        "Honda Cars India",
        "https://www.hondacarindia.com/honda-amaze",
        ["amaze", "honda amaze"],
        maintenance_highlights=[
            {"label": "CVT Smoothness And Brake Fluid Review", "interval": "At annual service", "note": "Compact sedan commute use can hide brake-fluid aging and transmission smoothness drift."},
        ],
    ),
    _catalog_entry(
        "skoda-kushaq",
        "car",
        "Skoda",
        "Kushaq",
        "Skoda Kushaq",
        "suv",
        999.0,
        50.0,
        18.0,
        10000,
        365,
        95,
        "Skoda Auto India",
        "https://www.skoda-auto.co.in/models/kushaq/kushaq",
        ["skoda kushaq", "kushaq"],
        maintenance_highlights=[
            {"label": "TSI Turbo Heat And Intake Review", "interval": "Before summer highway use", "note": "Turbo-petrol crossovers benefit from disciplined oil, coolant, intake-filter, and fan-cycle checks."},
        ],
    ),
    _catalog_entry(
        "skoda-slavia",
        "car",
        "Skoda",
        "Slavia",
        "Skoda Slavia",
        "sedan",
        999.0,
        45.0,
        19.4,
        10000,
        365,
        95,
        "Skoda Auto India",
        "https://www.skoda-auto.co.in/models/slavia/slavia",
        ["skoda slavia", "slavia"],
        maintenance_highlights=[
            {"label": "Turbo Oil And Alignment Discipline", "interval": "Every annual service or after rough-road months", "note": "Long wheelbase sedans can hide alignment drift until tyre wear and steering correction become visible."},
        ],
    ),
    _catalog_entry(
        "volkswagen-taigun",
        "car",
        "Volkswagen",
        "Taigun",
        "Volkswagen Taigun",
        "suv",
        999.0,
        50.0,
        18.1,
        10000,
        365,
        95,
        "Volkswagen India",
        "https://www.volkswagen.co.in/en/models/taigun.html",
        ["volkswagen taigun", "taigun", "vw taigun"],
        maintenance_highlights=[
            {"label": "TSI Cooling And DSG/AT Smoothness Watch", "interval": "Before highway trips and at annual service", "note": "Turbo engine load and transmission smoothness should be reviewed together when traffic and highway use are mixed."},
        ],
    ),
    _catalog_entry(
        "volkswagen-virtus",
        "car",
        "Volkswagen",
        "Virtus",
        "Volkswagen Virtus",
        "sedan",
        999.0,
        45.0,
        19.4,
        10000,
        365,
        95,
        "Volkswagen India",
        "https://www.volkswagen.co.in/en/models/virtus.html",
        ["volkswagen virtus", "virtus", "vw virtus"],
        maintenance_highlights=[
            {"label": "Sedan Highway Brake And Tyre Review", "interval": "Before long expressway runs", "note": "Stable highway use can still build brake heat and uneven tyre wear when alignment is off."},
        ],
    ),
    _catalog_entry(
        "renault-kiger",
        "car",
        "Renault",
        "Kiger",
        "Renault Kiger",
        "suv",
        999.0,
        40.0,
        19.0,
        10000,
        365,
        90,
        "Renault India",
        "https://www.renault.co.in/cars/renault-kiger.html",
        ["renault kiger", "kiger"],
        maintenance_highlights=[
            {"label": "Turbo City-Highway Intake Review", "interval": "At annual service and after dusty travel", "note": "Dusty roads and turbo use make air-filter and cooling checks more important for consistent mileage."},
        ],
    ),
    _catalog_entry(
        "renault-triber",
        "car",
        "Renault",
        "Triber",
        "Renault Triber",
        "mpv",
        999.0,
        40.0,
        18.2,
        10000,
        365,
        88,
        "Renault India",
        "https://www.renault.co.in/cars/renault-triber.html",
        ["renault triber", "triber"],
        maintenance_highlights=[
            {"label": "Flexible-Seating Load Review", "interval": "Before full-passenger trips", "note": "Passenger load changes braking, tyre pressure, and suspension wear more than empty city use."},
        ],
    ),
    _catalog_entry(
        "nissan-magnite",
        "car",
        "Nissan",
        "Magnite",
        "Nissan Magnite",
        "suv",
        999.0,
        40.0,
        19.4,
        10000,
        365,
        90,
        "Nissan India",
        "https://www.nissan.in/vehicles/new/nissan-magnite.html",
        ["nissan magnite", "magnite"],
        maintenance_highlights=[
            {"label": "Compact SUV Brake And Tyre Watch", "interval": "At each annual service", "note": "Urban pothole exposure and stop-go use should tighten tyre, alignment, and brake checks."},
        ],
    ),
    _catalog_entry(
        "citroen-c3",
        "car",
        "Citroen",
        "C3",
        "Citroen C3",
        "hatchback",
        1198.0,
        30.0,
        19.3,
        10000,
        365,
        88,
        "Citroen India",
        "https://www.citroen.in/models/c3.html",
        ["citroen c3", "c3"],
        maintenance_highlights=[
            {"label": "Comfort Suspension And Tyre Check", "interval": "After rough-road months", "note": "Soft suspension tuning can hide tyre and alignment issues until road noise or steering correction rises."},
        ],
    ),
    _catalog_entry(
        "citroen-aircross",
        "car",
        "Citroen",
        "Aircross",
        "Citroen Aircross",
        "suv",
        1199.0,
        45.0,
        17.6,
        10000,
        365,
        90,
        "Citroen India",
        "https://www.citroen.in/models/aircross.html",
        ["citroen aircross", "aircross", "c3 aircross"],
        maintenance_highlights=[
            {"label": "Five/Seven-Seat Load And Cooling Review", "interval": "Before highway family trips", "note": "Flexible seating and turbo use combine passenger-load, brake, tyre, and cooling checks."},
        ],
    ),
    _catalog_entry(
        "jeep-compass",
        "car",
        "Jeep",
        "Compass",
        "Jeep Compass",
        "suv",
        1956.0,
        60.0,
        14.9,
        10000,
        365,
        95,
        "Jeep India",
        "https://www.jeep-india.com/new-compass.html",
        ["jeep compass", "compass"],
        fuel_type="diesel",
        maintenance_highlights=[
            {"label": "4x4/All-Season Tyre And Undercarriage Review", "interval": "After rough or hill travel", "note": "Adventure-oriented SUV use should inspect underbody, tyres, brake heat, and fluid levels before waiting for annual service."},
        ],
    ),
    _catalog_entry(
        "byd-atto-3",
        "car",
        "BYD",
        "ATTO 3",
        "BYD ATTO 3",
        "suv",
        0.0,
        0.0,
        0.0,
        10000,
        365,
        95,
        "BYD Auto India",
        "https://bydautoindia.com/bydatto3",
        ["byd atto 3", "atto 3"],
        fuel_type="electric",
        maintenance_highlights=[
            {"label": "Battery Cooling And Tyre Efficiency Review", "interval": "Monthly and before highway EV trips", "note": "EV range depends heavily on tyre pressure, cabin load, charging heat, and battery thermal behavior."},
        ],
    ),
    _catalog_entry(
        "toyota-innova-hycross",
        "car",
        "Toyota",
        "Innova Hycross",
        "Toyota Innova Hycross",
        "mpv",
        1987.0,
        52.0,
        20.0,
        10000,
        365,
        92,
        "Toyota Bharat",
        "https://www.toyotabharat.com/showroom/innova-hycross/",
        ["innova hycross", "toyota hycross", "hycross"],
        fuel_type="hybrid",
        maintenance_highlights=[
            {"label": "Hybrid Family-Load Service Check", "interval": "Before loaded highway travel", "note": "Hybrid MPV use needs tyre, brake, cooling, cabin-filter, and battery-airflow checks together."},
        ],
    ),
    _catalog_entry(
        "mg-hector",
        "car",
        "MG",
        "Hector",
        "MG Hector",
        "suv",
        1451.0,
        60.0,
        14.5,
        10000,
        365,
        92,
        "MG Motor India",
        "https://www.mgmotor.co.in/vehicles/mghector",
        ["mg hector", "hector"],
        maintenance_highlights=[
            {"label": "Turbo Cooling And Large-SUV Brake Review", "interval": "Before highway travel", "note": "Larger petrol SUVs need cooling, brake, tyre, and battery checks before loaded outstation use."},
        ],
    ),
    _catalog_entry(
        "tata-tiago-ev",
        "car",
        "Tata",
        "Tiago EV",
        "Tata Tiago EV",
        "hatchback",
        0.0,
        0.0,
        0.0,
        10000,
        365,
        80,
        "Tata Motors EV",
        "https://ev.tatamotors.com/tiago/ev.html",
        ["tiago ev", "tata tiago ev"],
        fuel_type="electric",
        maintenance_highlights=[
            {"label": "Small-EV Range And Charging Habit Review", "interval": "Monthly", "note": "City EV range reacts quickly to tyre drag, AC load, charging heat, and regenerative-brake behavior."},
        ],
    ),
    _catalog_entry(
        "royal-enfield-himalayan-450",
        "motorcycle",
        "Royal Enfield",
        "Himalayan 450",
        "Royal Enfield Himalayan 450",
        "adventure",
        452.0,
        17.0,
        30.0,
        5000,
        180,
        88,
        "Royal Enfield",
        "https://www.royalenfield.com/in/en/motorcycles/himalayan/",
        ["himalayan 450", "royal enfield himalayan", "himalayan"],
        maintenance_highlights=[
            {"label": "Adventure Suspension And Spoke/Wheel Review", "interval": "After trails, ghats, or bad-road tours", "note": "Adventure use should tighten spoke/alloy, bearing, suspension, brake, and tyre checks."},
        ],
    ),
    _catalog_entry(
        "hero-karizma-xmr",
        "motorcycle",
        "Hero",
        "Karizma XMR",
        "Hero Karizma XMR",
        "sport",
        210.0,
        11.0,
        41.0,
        5000,
        180,
        82,
        "Hero MotoCorp",
        "https://www.heromotocorp.com/en-in/motorcycles/karizma-xmr.html",
        ["karizma xmr", "hero karizma", "karizma"],
        maintenance_highlights=[
            {"label": "Liquid-Cooling And Sport Brake Review", "interval": "Before summer rides and at service", "note": "Sport-commute riding can stress coolant, fan behavior, front pads, tyres, and chain more sharply than commuter use."},
        ],
    ),
    _catalog_entry(
        "honda-cb350",
        "motorcycle",
        "Honda",
        "CB350",
        "Honda CB350",
        "retro",
        348.36,
        15.2,
        35.0,
        5000,
        180,
        75,
        "Honda Motorcycle & Scooter India",
        "https://www.honda2wheelersindia.com/cb350",
        ["honda cb350", "cb350", "hness cb350", "hness"],
        maintenance_highlights=[
            {"label": "Chain, Clutch, And Brake Feel Review", "interval": "At each service and after rainy rides", "note": "Retro-roadster weight and torque make chain slack, clutch feel, brake pads, and tyre pressure first-line checks."},
        ],
    ),
    _catalog_entry(
        "suzuki-gixxer-sf-250",
        "motorcycle",
        "Suzuki",
        "Gixxer SF 250",
        "Suzuki Gixxer SF 250",
        "sport",
        249.0,
        12.0,
        38.0,
        5000,
        180,
        85,
        "Suzuki Motorcycle India",
        "https://www.suzukimotorcycle.co.in/product-details/gixxer-sf-250",
        ["gixxer sf 250", "suzuki gixxer 250", "gixxer 250"],
        maintenance_highlights=[
            {"label": "Oil-Cooling And Tyre Edge Review", "interval": "Before highway or spirited rides", "note": "Quarter-liter sport use benefits from oil, air-filter, brake-pad, tyre, and chain checks before long runs."},
        ],
    ),
    _catalog_entry(
        "tvs-apache-rr310",
        "motorcycle",
        "TVS",
        "Apache RR 310",
        "TVS Apache RR 310",
        "sport",
        312.2,
        11.0,
        33.0,
        5000,
        180,
        88,
        "TVS Motor",
        "https://www.tvsmotor.com/tvs-apache/apache-rr-310",
        ["apache rr 310", "rr310", "tvs rr310"],
        maintenance_highlights=[
            {"label": "Track/Sport Brake Heat And Cooling Review", "interval": "Before fast highway use or track days", "note": "Higher brake temperature, coolant load, chain wear, and tyre edge wear need shorter review windows."},
        ],
    ),
    _catalog_entry(
        "yamaha-r15-v4",
        "motorcycle",
        "Yamaha",
        "R15 V4",
        "Yamaha R15 V4",
        "sport",
        155.0,
        11.0,
        45.0,
        4000,
        180,
        82,
        "Yamaha Motor India",
        "https://www.yamaha-motor-india.com/yamaha-r15v4.html",
        ["yamaha r15", "r15 v4", "r15"],
        maintenance_highlights=[
            {"label": "High-Rev Chain And Brake Review", "interval": "Every service and after aggressive rides", "note": "Sporty high-rev riding exposes chain slack, pad wear, tyre pressure, and fork behavior quickly."},
        ],
    ),
    _catalog_entry(
        "ktm-390-adventure",
        "motorcycle",
        "KTM",
        "390 Adventure",
        "KTM 390 Adventure",
        "adventure",
        398.63,
        14.5,
        30.0,
        5000,
        180,
        90,
        "KTM India",
        "https://www.ktmindia.com/ktm-bikes/adventure/ktm-390-adventure-x",
        ["ktm 390 adventure", "390 adventure", "adv 390"],
        maintenance_highlights=[
            {"label": "ADV Wheel, Brake, And Cooling Review", "interval": "After off-road, ghats, or monsoon touring", "note": "Adventure riding raises suspension, wheel, brake, chain, radiator, and tyre pressure checks above routine street use."},
        ],
    ),
    _catalog_entry(
        "jawa-42",
        "motorcycle",
        "Jawa",
        "42",
        "Jawa 42",
        "retro",
        294.72,
        13.2,
        35.0,
        5000,
        180,
        75,
        "Jawa Motorcycles",
        "https://www.jawamotorcycles.com/motorcycles/42",
        ["jawa 42", "42 jawa"],
        maintenance_highlights=[
            {"label": "Liquid-Cooled Retro Heat And Brake Review", "interval": "At service and before touring", "note": "Retro commuter-touring use should track coolant, clutch feel, brake pads, chain, and tyre pressure together."},
        ],
    ),
    _catalog_entry(
        "yezdi-adventure",
        "motorcycle",
        "Yezdi",
        "Adventure",
        "Yezdi Adventure",
        "adventure",
        334.0,
        15.5,
        30.0,
        5000,
        180,
        82,
        "Yezdi Motorcycles",
        "https://www.yezdi.com/motorcycles/yezdi-adventure",
        ["yezdi adventure", "adventure yezdi"],
        maintenance_highlights=[
            {"label": "Trail And Touring Suspension Review", "interval": "After trail, ghat, or luggage-heavy rides", "note": "Adventure-bike loads bring suspension linkage, chain, spoke/alloy, brake, and tyre checks forward."},
        ],
    ),
    _catalog_entry(
        "triumph-speed-400",
        "motorcycle",
        "Triumph",
        "Speed 400",
        "Triumph Speed 400",
        "roadster",
        398.15,
        13.0,
        30.0,
        5000,
        180,
        85,
        "Triumph Motorcycles India",
        "https://www.triumphmotorcycles.in/motorcycles/classic/speed-400",
        ["triumph speed 400", "speed 400"],
        maintenance_highlights=[
            {"label": "Torque Assist Clutch And Cooling Review", "interval": "At service and before summer traffic", "note": "Modern classic roadsters should track clutch feel, coolant, front brake heat, chain, and tyre pressure closely."},
        ],
    ),
    _catalog_entry(
        "harley-davidson-x440",
        "motorcycle",
        "Harley-Davidson",
        "X440",
        "Harley-Davidson X440",
        "roadster",
        440.0,
        13.5,
        32.0,
        5000,
        180,
        78,
        "Harley-Davidson X440",
        "https://www.harley-davidsonx440.com/",
        ["harley x440", "harley-davidson x440", "x440"],
        maintenance_highlights=[
            {"label": "Oil-Cooled Single Heat And Brake Review", "interval": "Before long summer rides", "note": "Large singles benefit from oil, cooling-airflow, clutch, chain, brake, and tyre reviews before touring."},
        ],
    ),
    _catalog_entry(
        "bmw-g310-rr",
        "motorcycle",
        "BMW",
        "G 310 RR",
        "BMW G 310 RR",
        "sport",
        312.12,
        11.0,
        32.0,
        5000,
        180,
        88,
        "BMW Motorrad India",
        "https://www.bmw-motorrad.in/en/models/sport/g310rr.html",
        ["bmw g310rr", "g 310 rr", "g310 rr"],
        maintenance_highlights=[
            {"label": "Ride-Mode Brake And Cooling Review", "interval": "Before sport rides or track use", "note": "Sport use should tighten brake-fluid, pad, coolant, tyre, and chain checks."},
        ],
    ),
    _catalog_entry(
        "revolt-rv400",
        "motorcycle",
        "Revolt",
        "RV400",
        "Revolt RV400",
        "roadster",
        0.0,
        0.0,
        0.0,
        5000,
        180,
        70,
        "Revolt Motors",
        "https://www.revoltmotors.com/rv400",
        ["revolt rv400", "rv400", "rv 400"],
        fuel_type="electric",
        maintenance_highlights=[
            {"label": "Battery Range And Brake Regen Review", "interval": "Monthly", "note": "Electric motorcycle range depends on tyre pressure, regen feel, charging heat, brake drag, and bearing condition."},
        ],
    ),
    _catalog_entry(
        "ultraviolette-f77",
        "motorcycle",
        "Ultraviolette",
        "F77",
        "Ultraviolette F77",
        "sport",
        0.0,
        0.0,
        0.0,
        5000,
        180,
        95,
        "Ultraviolette",
        "https://www.ultraviolette.com/f77",
        ["ultraviolette f77", "f77", "f77 mach 2"],
        fuel_type="electric",
        maintenance_highlights=[
            {"label": "Performance-EV Battery Thermal Review", "interval": "Before high-speed rides", "note": "High-output EV use makes tyre, brake, thermal, charging, and software state checks safety-critical."},
        ],
    ),
    _catalog_entry(
        "simple-one",
        "scooter",
        "Simple Energy",
        "One",
        "Simple One",
        "scooter",
        0.0,
        0.0,
        0.0,
        5000,
        180,
        60,
        "Simple Energy",
        "https://www.simpleenergy.in/product/simpleone",
        ["simple one", "simple energy one"],
        fuel_type="electric",
        maintenance_highlights=[
            {"label": "Range, Tyre Drag, And Charging Audit", "interval": "Monthly", "note": "Long-range scooters need charge-habit, tyre, brake-drag, bearing, and thermal checks to preserve real-world range."},
        ],
    ),
    _catalog_entry(
        "tvs-iqube",
        "scooter",
        "TVS",
        "iQube",
        "TVS iQube",
        "scooter",
        0.0,
        0.0,
        0.0,
        5000,
        180,
        55,
        "TVS Motor",
        "https://www.tvsmotor.com/tvs-iqube",
        ["tvs iqube", "iqube"],
        fuel_type="electric",
        maintenance_highlights=[
            {"label": "City-EV Range And Tyre Pressure Review", "interval": "Fortnightly", "note": "Electric scooter efficiency changes quickly with tyre pressure, brake drag, payload, and AC/charging heat exposure."},
        ],
    ),
    _catalog_entry(
        "hero-xoom-160",
        "scooter",
        "Hero",
        "Xoom 160",
        "Hero Xoom 160",
        "scooter",
        156.0,
        7.0,
        42.0,
        4000,
        180,
        60,
        "Hero MotoCorp",
        "https://www.heromotocorp.com/en-in/scooters/xoom-160.html",
        ["xoom 160", "hero xoom"],
        maintenance_highlights=[
            {"label": "Maxi-Scooter CVT And Brake Review", "interval": "At each service", "note": "Larger scooters should watch CVT response, belt wear, front brake heat, tyres, and fork condition more closely."},
        ],
    ),
    _catalog_entry(
        "yamaha-fascino-125",
        "scooter",
        "Yamaha",
        "Fascino 125 Fi Hybrid",
        "Yamaha Fascino 125 Fi Hybrid",
        "scooter",
        125.0,
        5.2,
        50.0,
        3000,
        150,
        52,
        "Yamaha Motor India",
        "https://www.yamaha-motor-india.com/yamaha-fascino125fi.html",
        ["yamaha fascino", "fascino 125", "fascino"],
        fuel_type="hybrid",
        maintenance_highlights=[
            {"label": "Hybrid-Assist And CVT Smoothness Review", "interval": "At service and after stop-go months", "note": "Scooter hybrid assist and CVT behavior should be checked when pickup or mileage drifts."},
        ],
    ),
    _catalog_entry(
        "suzuki-burgman-street",
        "scooter",
        "Suzuki",
        "Burgman Street",
        "Suzuki Burgman Street",
        "scooter",
        124.0,
        5.5,
        45.0,
        3000,
        150,
        55,
        "Suzuki Motorcycle India",
        "https://www.suzukimotorcycle.co.in/product-details/burgman-street",
        ["suzuki burgman", "burgman street", "burgman"],
        maintenance_highlights=[
            {"label": "Scooter Tyre, CVT, And Fork Review", "interval": "At each service and after rough roads", "note": "Larger scooter bodies can hide CVT vibration, fork noise, and tyre drag until mileage drops."},
        ],
    ),
    _catalog_entry(
        "honda-activa-125",
        "scooter",
        "Honda",
        "Activa 125",
        "Honda Activa 125",
        "scooter",
        123.92,
        5.3,
        48.0,
        3000,
        150,
        52,
        "Honda Motorcycle & Scooter India",
        "https://www.honda2wheelersindia.com/activa125",
        ["activa 125", "honda activa 125"],
        maintenance_highlights=[
            {"label": "CVT Judder And Brake-Dive Review", "interval": "At service and after pothole-heavy months", "note": "Urban scooter use should tighten CVT, clutch, fork, brake, tyre, and bearing checks."},
        ],
    ),
]


SUPPORTED_CATALOG_SCOPE = {
    "name": "India consumer vehicle maintenance seed catalog",
    "minimum_models": 70,
    "minimum_manufacturers": 28,
    "required_vehicle_types": {"motorcycle", "scooter", "car"},
    "required_manufacturers": {
        "Ather",
        "Bajaj",
        "BMW",
        "BYD",
        "Citroen",
        "Harley-Davidson",
        "Hero",
        "Honda",
        "Hyundai",
        "Jawa",
        "Jeep",
        "Kia",
        "KTM",
        "Mahindra",
        "Maruti Suzuki",
        "MG",
        "Nissan",
        "Ola",
        "Renault",
        "Revolt",
        "Royal Enfield",
        "Simple Energy",
        "Skoda",
        "Suzuki",
        "Tata",
        "Toyota",
        "Triumph",
        "TVS",
        "Ultraviolette",
        "Volkswagen",
        "Yamaha",
        "Yezdi",
    },
}


ROUTE_MAINTENANCE_RULES = [
    {
        "key": "rough",
        "signal_key": "rough_route_logs",
        "label": "Rough-Road Inspection",
        "components": ["tyres", "alignment", "suspension", "wheel bearings", "undercarriage"],
        "priority": "high",
        "interval_factor": 0.65,
        "cost_pct": 0.22,
        "minimum_cost": 900,
        "note": "Broken roads, gravel, potholes, and trails justify an earlier tyre, alignment, suspension, and underbody check.",
    },
    {
        "key": "hill",
        "signal_key": "hill_route_logs",
        "label": "Hill/Ghat Brake And Cooling Check",
        "components": ["brakes", "brake fluid", "cooling", "clutch", "tyres"],
        "priority": "high",
        "interval_factor": 0.70,
        "cost_pct": 0.18,
        "minimum_cost": 850,
        "note": "Long climbs and descents add brake heat, cooling load, clutch load, and tyre shoulder wear.",
    },
    {
        "key": "rain",
        "signal_key": "rain_route_logs",
        "label": "Monsoon Corrosion And Brake Check",
        "components": ["brakes", "chain/CVT", "bearings", "electrical connectors", "tyres"],
        "priority": "high",
        "interval_factor": 0.72,
        "cost_pct": 0.16,
        "minimum_cost": 800,
        "note": "Rain and water exposure can contaminate brakes, wash chain lube, affect bearings, and expose weak electrical terminals.",
    },
    {
        "key": "highway",
        "signal_key": "highway_route_logs",
        "label": "Highway Heat And Fluid Review",
        "components": ["engine oil", "coolant", "brake fluid", "tyres", "battery"],
        "priority": "watch",
        "interval_factor": 0.82,
        "cost_pct": 0.12,
        "minimum_cost": 700,
        "note": "Sustained speed makes oil, cooling, tyre pressure, brake fluid, and battery health matter before the next routine date.",
    },
    {
        "key": "city",
        "signal_key": "city_stop_go_logs",
        "label": "Stop-Go Wear Review",
        "components": ["brakes", "clutch/CVT", "battery", "cooling fan", "tyre pressure"],
        "priority": "watch",
        "interval_factor": 0.86,
        "cost_pct": 0.10,
        "minimum_cost": 600,
        "note": "Repeated short trips and traffic increase clutch or CVT heat, brake wear, battery drain, and fan cycling.",
    },
    {
        "key": "load",
        "signal_key": "loaded_route_logs",
        "label": "Passenger/Cargo Load Review",
        "components": ["tyre pressure", "brakes", "suspension", "cooling", "alignment"],
        "priority": "watch",
        "interval_factor": 0.78,
        "cost_pct": 0.14,
        "minimum_cost": 750,
        "note": "Passenger, luggage, cargo, or towing load should pull tyre, brake, suspension, cooling, and alignment checks forward.",
    },
    {
        "key": "dust",
        "signal_key": "dust_route_logs",
        "label": "Dust Intake And Filter Review",
        "components": ["air filter", "cabin filter", "chain/CVT", "radiator fins", "brakes"],
        "priority": "watch",
        "interval_factor": 0.80,
        "cost_pct": 0.11,
        "minimum_cost": 650,
        "note": "Dusty routes clog intake and cabin filters, accelerate drivetrain grime, and reduce brake smoothness.",
    },
]


def _catalog_items() -> list[dict]:
    return [*OFFICIAL_BIKE_CATALOG, *EXTENDED_OFFICIAL_BIKE_CATALOG]


def normalize_bike_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (value or "").lower()).strip()


def list_catalog_models(vehicle_type: str | None = None, make: str | None = None) -> list[dict]:
    normalized_type = str(vehicle_type or "").strip().lower()
    normalized_make = normalize_bike_name(make or "")
    items = [deepcopy(apply_class_defaults(item)) for item in _catalog_items()]
    if normalized_type and normalized_type not in {"all", "any"}:
        items = [item for item in items if item.get("vehicle_type") == normalized_type]
    if normalized_make:
        items = [item for item in items if normalize_bike_name(item.get("make", "")) == normalized_make]
    return items


def list_catalog_manufacturers(vehicle_type: str | None = None) -> list[dict]:
    items = list_catalog_models(vehicle_type=vehicle_type)
    grouped: dict[str, dict] = {}
    for item in items:
        make = item.get("make", "").strip()
        if not make:
            continue
        entry = grouped.setdefault(make, {"make": make, "model_count": 0, "vehicle_types": set()})
        entry["model_count"] += 1
        if item.get("vehicle_type"):
            entry["vehicle_types"].add(item["vehicle_type"])

    return [
        {
            **entry,
            "vehicle_types": sorted(entry["vehicle_types"]),
        }
        for entry in sorted(grouped.values(), key=lambda row: row["make"].lower())
    ]


def apply_class_defaults(data: dict) -> dict:
    bike_class = data.get("bike_class") or "custom"
    defaults = CLASS_DEFAULTS.get(bike_class, CLASS_DEFAULTS["custom"])
    merged = deepcopy(data)
    is_electric = _is_electric_vehicle(merged)
    for key, value in defaults.items():
        if is_electric and key == "expected_mileage_kmpl":
            merged[key] = 0.0
            continue
        if merged.get(key) in {None, "", 0}:
            merged[key] = value
    if is_electric:
        merged["fuel_type"] = "electric"
        merged["expected_mileage_kmpl"] = 0.0
        if merged.get("fuel_tank_capacity_l") in {None, ""}:
            merged["fuel_tank_capacity_l"] = 0.0
    if not merged.get("maintenance_guidance"):
        merged["maintenance_guidance"] = build_maintenance_guidance(merged)
    return merged


def best_catalog_match(name: str) -> tuple[dict | None, float]:
    normalized = normalize_bike_name(name)
    if not normalized:
        return None, 0

    best_item = None
    best_score = 0.0
    for item in _catalog_items():
        candidates = [item["display_name"], item["model_name"], *item.get("aliases", [])]
        for candidate in candidates:
            score = SequenceMatcher(None, normalized, normalize_bike_name(candidate)).ratio()
            if normalized in normalize_bike_name(candidate) or normalize_bike_name(candidate) in normalized:
                score += 0.08
            if score > best_score:
                best_item = item
                best_score = score
    return (deepcopy(apply_class_defaults(best_item)), min(best_score, 1.0)) if best_item else (None, 0.0)


def catalog_coverage_summary() -> dict:
    items = list_catalog_models()
    manufacturer_counts = Counter(item.get("make", "") for item in items if item.get("make"))
    vehicle_type_counts = Counter(item.get("vehicle_type", "") for item in items if item.get("vehicle_type"))
    source_ready = sum(1 for item in items if item.get("official_source_url"))
    guidance_ready = sum(1 for item in items if item.get("maintenance_guidance"))
    required_manufacturers = SUPPORTED_CATALOG_SCOPE["required_manufacturers"]
    supported_manufacturers = set(manufacturer_counts)
    missing_manufacturers = sorted(required_manufacturers - supported_manufacturers)
    missing_vehicle_types = sorted(SUPPORTED_CATALOG_SCOPE["required_vehicle_types"] - set(vehicle_type_counts))
    model_count = len(items)
    completion_ready = (
        model_count >= SUPPORTED_CATALOG_SCOPE["minimum_models"]
        and len(supported_manufacturers) >= SUPPORTED_CATALOG_SCOPE["minimum_manufacturers"]
        and not missing_manufacturers
        and not missing_vehicle_types
        and source_ready == model_count
        and guidance_ready == model_count
    )
    return {
        "scope": SUPPORTED_CATALOG_SCOPE["name"],
        "completion_status": "complete_current_scope" if completion_ready else "coverage_gap",
        "model_count": model_count,
        "manufacturer_count": len(supported_manufacturers),
        "vehicle_type_counts": dict(sorted(vehicle_type_counts.items())),
        "manufacturer_counts": dict(sorted(manufacturer_counts.items())),
        "official_source_coverage_pct": round((source_ready / max(model_count, 1)) * 100),
        "maintenance_guidance_coverage_pct": round((guidance_ready / max(model_count, 1)) * 100),
        "required_manufacturers_missing": missing_manufacturers,
        "required_vehicle_types_missing": missing_vehicle_types,
    }


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


def _profile_value(data, key: str, default=None):
    if isinstance(data, dict):
        return data.get(key, default)
    return getattr(data, key, default)


def _is_electric_vehicle(data) -> bool:
    fuel_type = str(_profile_value(data, "fuel_type", "") or "").lower()
    engine_cc = _profile_value(data, "engine_cc", None)
    fuel_tank = _profile_value(data, "fuel_tank_capacity_l", None)
    return fuel_type == "electric" or (engine_cc in {0, 0.0} and fuel_tank in {0, 0.0})


def build_maintenance_guidance(data: dict) -> list[dict]:
    make = (data.get("make") or "").strip()
    guidance_source = MANUFACTURER_GUIDANCE.get(make, {})
    source_name = data.get("official_source_name") or guidance_source.get("source_name") or "Official source"
    source_url = data.get("official_source_url") or guidance_source.get("source_url") or ""
    service_interval_km = data.get("service_interval_km") or CLASS_DEFAULTS["custom"]["service_interval_km"]
    service_interval_days = data.get("service_interval_days") or CLASS_DEFAULTS["custom"]["service_interval_days"]
    vehicle_type = data.get("vehicle_type") or "motorcycle"
    is_electric = _is_electric_vehicle(data)

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
    ]
    if is_electric:
        items.append(
            {
                "label": "Battery / Motor / Software Health",
                "interval": "Monthly and before long rides",
                "note": "Track range drift, charging heat, motor noise, software state, brake regen feel, and tyre drag together.",
                "source_name": source_name,
                "source_url": source_url,
            }
        )
    else:
        items.append(
            {
                "label": "Engine / Drive Health",
                "interval": "At each service and before highway use",
                "note": "Watch oil age, filter state, chain or driveline smoothness, and idle quality before blaming mileage alone.",
                "source_name": source_name,
                "source_url": source_url,
            }
        )
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
                "label": "Final Drive / CVT / Transmission Check",
                "interval": "Every wash cycle and before touring",
                "note": (
                    "For electric two-wheelers, listen for belt, bearing, brake-drag, and motor noise. "
                    "For petrol motorcycles and scooters, keep chain or CVT behavior in spec."
                ),
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


def build_route_maintenance_guidance(profile, route_wear: dict, *, projected_next_service_cost: float = 0) -> dict:
    signals = route_wear.get("signals") or {}
    service_interval_km = route_wear.get("service_interval_km") or _profile_value(profile, "service_interval_km", None) or CLASS_DEFAULTS["custom"]["service_interval_km"]
    route_adjusted_cost = route_wear.get("route_adjusted_service_cost") or projected_next_service_cost or 0
    source_name = _profile_value(profile, "official_source_name", "") or MANUFACTURER_GUIDANCE.get(_profile_value(profile, "make", ""), {}).get("source_name", "")
    source_url = _profile_value(profile, "official_source_url", "") or MANUFACTURER_GUIDANCE.get(_profile_value(profile, "make", ""), {}).get("source_url", "")
    is_electric = _is_electric_vehicle(profile)
    actions = []
    cost_factors = []
    interval_factors = []

    for rule in ROUTE_MAINTENANCE_RULES:
        hit_count = int(signals.get(rule["signal_key"], 0) or 0)
        if hit_count <= 0:
            continue
        route_pressure_cost = round(max(route_adjusted_cost, projected_next_service_cost, rule["minimum_cost"]) * rule["cost_pct"], 2)
        estimated_min = max(rule["minimum_cost"], round(route_pressure_cost * 0.75, 2))
        estimated_max = round(max(estimated_min, route_pressure_cost * 1.85), 2)
        tightened_interval = max(int(service_interval_km * rule["interval_factor"]), 750 if _profile_value(profile, "vehicle_type", "") != "car" else 1500)
        interval_factors.append(rule["interval_factor"])
        actions.append(
            {
                "key": rule["key"],
                "label": rule["label"],
                "priority": rule["priority"],
                "next_check_km": tightened_interval,
                "estimated_cost_range": {"min": estimated_min, "max": estimated_max},
                "components": _route_components_for_vehicle(rule["components"], profile, is_electric),
                "note": rule["note"],
                "source_name": source_name,
                "source_url": source_url,
                "evidence": f"{hit_count} recent route log(s) matched {rule['key']} conditions.",
            }
        )
        cost_factors.append(
            {
                "key": rule["key"],
                "label": rule["label"],
                "matched_logs": hit_count,
                "estimated_pressure_cost": route_pressure_cost,
                "interval_factor": rule["interval_factor"],
            }
        )

    if not actions:
        actions.append(
            {
                "key": "routine",
                "label": "Routine Route Follow-Up",
                "priority": "normal",
                "next_check_km": int(service_interval_km),
                "estimated_cost_range": {"min": 0, "max": round(max(route_adjusted_cost, 0) * 0.08, 2)},
                "components": ["tyres", "brakes", "fluids" if not is_electric else "battery/charging", "lights"],
                "note": "No route condition has enough evidence to tighten the service window beyond the saved model interval.",
                "source_name": source_name,
                "source_url": source_url,
                "evidence": "No route-specific condition logs matched.",
            }
        )

    recommended_interval_km = max(
        int(service_interval_km * min(interval_factors or [1.0])),
        750 if _profile_value(profile, "vehicle_type", "") != "car" else 1500,
    )
    service_interval_tightening_pct = round(max(0, 1 - (recommended_interval_km / max(float(service_interval_km), 1.0))) * 100, 1)
    return {
        "coverage_status": "route_aware",
        "recommended_interval_km": recommended_interval_km,
        "service_interval_tightening_pct": service_interval_tightening_pct,
        "pre_trip_checklist": _pre_trip_checklist(profile, is_electric),
        "actions": actions[:7],
        "cost_factors": cost_factors[:7],
        "source_name": source_name,
        "source_url": source_url,
    }


def _route_components_for_vehicle(components: list[str], profile, is_electric: bool) -> list[str]:
    vehicle_type = _profile_value(profile, "vehicle_type", "")
    normalized = []
    for component in components:
        if is_electric and component in {"engine oil", "coolant", "air filter"}:
            replacement = "battery thermal path" if component == "coolant" else "battery/motor system"
            normalized.append(replacement)
        elif vehicle_type == "car" and component == "chain/CVT":
            normalized.append("transmission/driveline")
        else:
            normalized.append(component)
    return list(dict.fromkeys(normalized))


def _pre_trip_checklist(profile, is_electric: bool) -> list[str]:
    vehicle_type = _profile_value(profile, "vehicle_type", "")
    base = ["tyre pressure and tread", "brake feel and fluid/pad condition", "lights, horn, and documents"]
    if is_electric:
        base.insert(1, "usable range, charging plan, and battery temperature")
    elif vehicle_type == "car":
        base.insert(1, "engine oil, coolant, battery, and cabin filter")
    else:
        base.insert(1, "engine oil, chain/CVT behavior, and clutch feel")
    if vehicle_type == "car":
        base.append("spare wheel or puncture kit and emergency tools")
    else:
        base.append("puncture kit, chain lube if applicable, and rain protection")
    return base
