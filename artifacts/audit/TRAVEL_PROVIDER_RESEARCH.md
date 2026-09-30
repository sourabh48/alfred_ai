# Travel provider research

Reviewed 2026-09-29/30 against current official sources. Prices/quotas can change;
application limits are conservative budgets, not reserved provider allowances.
No paid/keyed calls have been performed during this continuation.

| Provider / category | Free tier / current price / key | Coverage including India | Terms, caching, attribution | Decision / fallback |
|---|---|---|---|---|
| Open-Meteo weather/geocode API | Noncommercial hosted tier: 600/min, 5k/hour, 10k/day, 300k/month; weighted queries. No key. Commercial subscription/key required; check plan price when selecting | Global, India; forecast window 16 days | CC BY 4.0; cache weather 2h, geocode 90d; declare eligible use locally | Existing adapter retained; unknown forecast outside window |
| openrouteservice directions API | Standard account/key, free 2k/day, 40/min directions | Global/India OSM coverage | Attribution + CC BY-SA 4.0; routes cached 5d; no motorcycle legality guarantee | Existing adapter retained; estimated distance fallback |
| Public Nominatim API | No key, maximum 1/sec for entire application | Global, variable address coverage | Identifying UA, caching, ODbL attribution; no autocomplete/bulk; generated apps require informed decision | Not default; Open-Meteo alternative |
| Overpass API | Public shared service not appropriate as default application backend; authorized endpoint costs/quotas operator-dependent | Global OSM, uneven India detail | ODbL; published public guideline ~10k calls/1GB per day is not entitlement. Cache 7d | Configured authorized **public HTTPS** endpoint only; community metadata, no availability |
| OSM tiles | No key; fair-use policy, no service guarantee | Global, India | Visible attribution, normal browser cache/referer; no bulk/offline prefetch | Optional browser map; provider-neutral GeoJSON |
| Wikivoyage Action API / travel discovery | No key; no per-call charge; dynamic operational rate limits, not guaranteed daily quota | Global travel guides including India; incomplete coverage | Identifying contact UA; serial bounded calls, maxlag/backoff; CC BY-SA 4.0 with article/contributor link. Cache destination metadata 14d, search leads 6h | Implement no-key discovery/search fallback. Community information, never authority for permits/availability |
| Brave Web Search API | Current Search $5/1000, $5 monthly credits; key required; advertised capacity 50 queries/sec | General web/India; coverage not guaranteed | **Storage rights require a plan explicitly granting them**; general API terms alone insufficient. Attribution for applicable credit program | Optional adapter only with paid-use and storage-rights opt-in; no assumption that caching is licensed. Fallback Wikivoyage/search links |
| SearXNG JSON API | Software has no per-call fee; instance operator costs/limits/engine rights vary; no universal free service | Depends on configured upstream engines/instance | JSON format must be enabled; public instances often disable it. Operator must authorize API use and result caching; upstream rights still apply | Optional authorized public HTTPS endpoint, explicit terms confirmation; no cloud deployment or local arbitrary fetch exception |
| Duffel stays/flights API | Key/live account; Stays access requested. Excess search USD .005 beyond 1500:1 search/order allowance; default live search 10/min | Participating inventory worldwide/India varies | Cache 15min capped by offer expiry. Terms/account restrictions apply; search result is not reservation or final availability | Existing opt-in search-only adapters retained. Not a free feed for zero-order planner. External search links when unavailable |
| Amadeus Self-Service | Current portal reports decommissioned July 17; historical free-tier prices not applicable | Historical global offering | Old indexed examples are not current access proof | Reject new integration; no fabricated API access |
| Indian Rail / IRCTC TIES | Authorized agreement; no verified anonymous free seat API, price/quota contract-dependent | India | Official information integration policy is not permission to scrape IRCTC | Unavailable adapter plus IRCTC/enquiry links; no seat/fare claims |
| Bus operators / comparison sites | No public free live API verified in this review | Operator-specific, India | Do not scrape restricted inventory | Official KSRTC/operator links and general bus search; availability UNKNOWN |
| Permit/closure authorities | No open inventory API verified | State/authority-specific | Kerala Tourism content reuse restricted; forest booking terms do not authorize bot inventory scraping | Dated reference and ranked current search leads; current opening/quotas/fees remain unverified |
| Fuel/tolls | No suitable free official live API verified | Region/road-specific | Price reference dates and formula assumptions required | Stored user fuel receipts + clearly labeled allowances; authority link/research leads |

Official sources:

- Open-Meteo [pricing](https://open-meteo.com/en/pricing), [terms](https://open-meteo.com/en/terms), [geocoding](https://open-meteo.com/en/docs/geocoding-api).
- ORS [plans](https://account.heigit.org/info/plans), [terms](https://account.heigit.org/info/tos), [API](https://giscience.github.io/openrouteservice/).
- OSM [Nominatim policy](https://operations.osmfoundation.org/policies/nominatim/), [Overpass commons](https://dev.overpass-api.de/overpass-doc/en/preface/commons.html), [tile policy](https://operations.osmfoundation.org/policies/tiles/).
- Wikimedia [API guidelines](https://foundation.wikimedia.org/wiki/Policy:Wikimedia_Foundation_API_Usage_Guidelines), [rate limits](https://www.mediawiki.org/wiki/Wikimedia_APIs/Rate_limits), [etiquette](https://www.mediawiki.org/wiki/API:Etiquette), [spatial search](https://www.mediawiki.org/wiki/Help:CirrusSearch), [travel-guide reuse](https://en.wikivoyage.org/wiki/Wikivoyage:How_to_re-use_Wikivoyage_guides).
- Brave [current pricing and storage-rights FAQ](https://brave.com/search/api/); SearXNG [JSON search API](https://docs.searxng.org/dev/search_api.html).
- Duffel [pricing](https://duffel.com/pricing), [agreement](https://duffel.com/services-agreement), [hotel search](https://duffel.com/docs/api/v2/search), [flight search](https://duffel.com/docs/api/offer-requests), [rate limits](https://help.duffel.com/hc/en-gb/articles/10229200096786-What-is-the-API-rate-limit).
- Amadeus [current portal](https://developers.amadeus.com/self-service/category/hotels); IRCTC [TIES policy](https://contents.irctc.co.in/en/TIES_Policy.pdf).
- Kerala [Chembra reference](https://www.keralatourism.org/destination/chembra-peak-wayanad/508/), [copyright](https://www.keralatourism.org/copyright), [forest terms](https://ecotourism.forest.kerala.gov.in/termsandcondition).

Keys/configuration belong only in untracked `config/local.env`. Provider fixtures
prove normalization/failure behavior, not live inventory access. Recheck terms
before configuring a paid account. No bookings, orders or payments are in scope.
