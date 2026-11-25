# Travel data licensing

Checked 2026-11-25. This is not legal advice. Where an official page could not be read, the row says so, and that
licence must be read by a person before the data is used.

| Source | Licence or terms | Attribution ALFRED must show | Offline or caching | Redistribution | AI training | ALFRED today |
| --- | --- | --- | --- | --- | --- | --- |
| OpenStreetMap data (Geofabrik extracts) | ODbL 1.0 | "© OpenStreetMap contributors", linked to openstreetmap.org/copyright, in a map corner | Allowed | An adapted database used publicly must be offered under ODbL | OSMF: a "substantial extraction" training set is a Derivative Database | Not used directly |
| Protomaps builds | "ODbL Produced Work (OpenStreetMap attribution required)" | "© OpenStreetMap contributors, Protomaps" | Copy the tileset; hotlinking discouraged | Through ODbL terms | As OSM | Used; attribution present |
| OSM tile server | OSMF tile usage policy | As OSM | **Offline and "download country" prohibited** | No | n/a | Not used, correctly |
| dr5hn world dataset | ODbL-1.0 (`static/vendor/world/LICENSE`) | As listed in that LICENSE | Bundled | ODbL | n/a | Bundled |
| Google Maps Platform (tiles, Places, Routes, Weather, Air Quality) | Google Maps Platform terms | "Powered by Google" / Google logo | Restricted. Coordinates up to 30 days; other content as the code TTLs set (1 hour for routes, 1 day for places) | No | Not allowed (Google terms; not re-read here) | Complies per TRAVEL_PROVIDERS |
| Government Open Data License – India (data.gov.in, AIKOSH) | GODL-India, gazetted 13 Feb 2017 | Licensor's attribution string | Allowed | Allowed, commercial and non-commercial (secondary summaries) | Not stated | Unused. **Read the official page by hand (403 to automated reads)** |
| IMD API | Not stated publicly; AWS data has a no-commercial-use rule | IMD as source (assumed; confirm in the grant) | Ask in the request | Assume no | Assume no | Unused |
| NDMA SACHET CAP | Not stated | "Source: NDMA SACHET" plus the issuing agency in each CAP alert | Short cache until the alert's `expires` | Link to the alert, no bulk republishing | Not stated; keep out of training | Unused |
| Open-Meteo | Free API for non-commercial use only; data CC BY 4.0 | "Weather data by Open-Meteo.com" (confirm on /en/licence) | Allowed | CC BY 4.0 | Not stated | Climate in use; personal use fits |
| USGS earthquakes | US federal public domain (not re-read) | "USGS" as courtesy | Allowed | Allowed | Allowed | In use |
| Nager.Date | Per its site (not re-read) | Link | Short cache | Not checked | Not checked | In use |
| Amadeus Travel Builder | Travel Builder terms (signed 2026-11-19) | Airline's own link; no Amadeus branding misuse | Only caching needed to run; ALFRED purges after 15 minutes | No bundling | **Forbidden** | Complies (`short_keep.py`) |
| Skyscanner Travel API | Partner terms (not granted) | Skyscanner attribution if granted | Per contract | No | Per contract | Adapter waiting |
| AeroDataBox | RapidAPI plan terms (not re-read) | Per plan | Short | No | Not checked | In use, per person |
| ASI monument list | Not stated | "Archaeological Survey of India" | Possible | **Unknown; do not bundle until confirmed** | Unknown | Unused |
| NPCI Plaza Master PDFs | Not stated | "NPCI NETC Plaza Master, [month]" | Possible | **Unknown; keep it a dated local reference** | Unknown | Unused |
| MoRTH accident reports | Not stated (government publication) | "MoRTH, Road Accidents in India [year]" | Possible | Quote figures, not whole tables | Unknown | Unused |
| Survey of India maps | Geospatial Data Guidelines 2021, NGP 2022, product licence | As the licence says | Per licence | Usually restricted | Unknown | Unused |
| Bhuvan | Not read | Per terms | Unknown | Unknown | Unknown | Unused |
| State portals (ILP, Aranya Vihaara, KSRTC, ASI tickets) | Website terms | Name and link the portal | Store only our own dated quote and link | Never mirror pages | No | Dated references only |

## Rules that follow for ALFRED

1. Show OSM attribution on every offline map, every self-hosted route and every GPX export built from OSM data.
2. Never draw a Google route on the offline map; that is already enforced.
3. Keep anything without a stated reuse licence (ASI, NPCI, MoRTH, SACHET) as a local, dated reference with a source
   link and the date checked. Do not bundle it in the installer until a person confirms the licence.
4. Keep provider content out of local-model training data unless its licence allows it. Amadeus and Google
   forbid it, and the rest are unknown. This narrows the 2026-11-20 training decision for Travel content: training
   uses the owner's chats, not provider payloads.
5. Open-Meteo's free tier is non-commercial. If ALFRED is ever sold or carries ads, it needs a paid plan or another
   source.
